# TASK-FIX-COACHTESTTO — Root-cause diagnosis (AC-1)

> Coach independent-test (SDK) execution times out at 300s under the
> LangGraph harness — the trust-but-verify leg never completes.

## Summary (where the 300s goes)

The 300s budget is consumed almost entirely by the **LLM agent turn**, not by
pytest, not by venv bootstrap, and not by test collection. Under the LangGraph
harness the Coach's "independent" test run is dispatched as a *one-turn LLM
agent invocation* (`_run_tests_via_sdk`): the local model is asked to call the
`Bash` tool, run pytest, read the output, and summarise it. The whole turn is
wrapped in `async with asyncio.timeout(self.test_timeout)` (300s). With a slow
local model (`gemma4:31b` coach-test model on `promaxgb10-41b1:9000`) that turn
does not complete within 300s, so the leg returns
`IndependentTestResult(tests_passed=False, ...)` with a "timed out" summary on
every task.

This is **orthogonal** to TASK-ARCH-COACHSPLIT (the verdict-synthesis fix
worked, 3/3 first-pass approvals). It is an independent-test *execution* issue.

## Evidence from run-19

Invocation (`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-19.md:1-5`):

```
GUARDKIT_HARNESS=langgraph \
  ... --fresh --model qwen36-workhorse --coach-model gemma4:31b \
  --task-timeout 4800 --sdk-timeout 3600 --no-context
```

The independent-test window for each task (`...run-19.md:195-198`):

```
INFO ...coach_validator: Coach SDK test command pinned to bootstrap interpreter:
     .../FEAT-AOF/.venv/bin/python -m pytest tests/unit/test_doc_level_constraint.py -v --tb=short
INFO httpx: HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
ERROR ...coach_validator: SDK coach test execution timed out after 300s
INFO  ...coach_validator: SDK independent tests failed in 300.0s
```

Three independent observations pin the cause:

1. **venv bootstrap is NOT the cost.** The command was already pinned to a
   ready interpreter — `.../FEAT-AOF/.venv/bin/python -m pytest …`. The venv
   existed and was resolved *before* the timed window opened (TASK-FIX-COACHPYENV
   bootstrap had already run). No bootstrap happens inside the 300s.
2. **The only activity in the window is the LLM call.** The single
   `POST .../v1/responses` (the agent-turn request to the local model) returns
   200 OK, and then nothing else logs until the 300s timeout fires. The harness
   is waiting on the model to drive the Bash tool / return — that wait is the
   300s.
3. **pytest itself is trivially fast.** The exact file
   (`tests/unit/test_doc_level_constraint.py`) runs in single-digit seconds via
   subprocess. A representative orchestrator test file measured locally:

   ```
   $ python -m pytest tests/orchestrator/test_coach_evidence_bundle.py -q
   16 passed in 2.03s
   # subprocess wall-clock: 2.6s   (budget: 300s)
   ```

   The subprocess path is >100× faster than the timed-out LLM-mediated path on
   comparable input. The delta is pure LLM-turn overhead.

## Why `_is_custom_api_base()` did not already force subprocess

`run_independent_tests` already disables the SDK path for custom API bases:

```python
use_sdk = (
    self._coach_test_execution == "sdk"
    and not requires_infra
    and not self._is_custom_api_base()   # checks ANTHROPIC_BASE_URL only
)
```

`_is_custom_api_base()` inspects **`ANTHROPIC_BASE_URL`**. Under the LangGraph
harness the model endpoint is configured through the LangGraph/OpenAI-compatible
channel (`promaxgb10-41b1:9000`), **not** `ANTHROPIC_BASE_URL`, so
`_is_custom_api_base()` returns `False`, `use_sdk` stays `True`, and the
LLM-mediated SDK path is selected — straight into the 300s timeout. The existing
guard simply has no awareness of the LangGraph substrate.

## Secondary finding (not the root cause)

`--sdk-timeout 3600` was supplied, but the Coach independent-test path uses
`CoachValidator.test_timeout` (default **300s**), which is independent of the
agent SDK timeout. So even though the operator raised the SDK timeout to 3600s,
the Coach test leg still capped at 300s. Raising `test_timeout` is therefore
*not* the right lever — it would only make a slow, LLM-mediated run complete
slowly; it would not remove the dependency on the model.

## Consequence (the safeguard that quietly degraded)

With the leg timing out, first-pass approval rested on the **Player's
self-reported** test outcome plus the deterministic non-test gates (coverage /
honesty / plan_audit / arch_review). The Coach's own independent pytest verdict
was absent. It was benign in run-19 (the Player's tests really did pass), but it
is exactly the absent-oracle situation
`.claude/rules/absence-of-failure-is-not-success.md` warns about and must not be
the silent steady state. Critically, a timeout produced
`IndependentTestResult(tests_passed=False)` with `gathering_status="complete"`,
so neither the existing zero-cardinality guards nor the gathering-status guard
fired — the LLM Coach saw a populated "failed" result it could (and did) read
past.

## Chosen fix levers

- **AC-2 — force the subprocess path under LangGraph.** Add
  `_is_langgraph_harness()` (reads `GUARDKIT_HARNESS`) to the `use_sdk` guard so
  the deterministic subprocess path (`<venv_python> -m pytest …`) runs instead
  of an LLM turn. This removes the root cause entirely rather than masking it:
  the subprocess runs the *same* pinned interpreter in the *same* worktree, in
  seconds, with no model in the loop. (Option (b) in the task; (a) venv-cache is
  moot — venv was already ready; (c) raise-timeout only slows the symptom.)
- **AC-3 — mark genuine non-completion as ABSENT SIGNAL.** Add
  `signal_absent: bool` to `IndependentTestResult`, set `True` on every
  timeout/transport-error path (SDK timeout, SDK API error, subprocess timeout,
  isolated-test timeout, generic execution error). Add a sixth
  absence-of-failure guard so the LLM Coach treats an absent independent-test
  oracle as ABSENT (surface as feedback) rather than approving on the Player's
  self-report. `tests_passed` stays `False` on these paths so the result can
  never read as a pass.

## Files touched

- `guardkit/orchestrator/quality_gates/coach_validator.py`
  (`IndependentTestResult`, `_is_langgraph_harness`, `run_independent_tests`
  dispatch, `_run_tests_via_sdk`, `_run_isolated_tests`).
- `guardkit/orchestrator/agent_invoker.py`
  (`_render_absence_of_failure_guards` — guard #6).
- `tests/orchestrator/test_coach_independent_test_timeout.py` (new, AC-4).
