# DECISION-COACHTESTTO — Coach independent tests bypass the LLM under the LangGraph harness

**Status:** ACCEPTED (implemented)
**Date:** 2026-06-09
**Task:** TASK-FIX-COACHTESTTO (parent: TASK-HMIG-010)
**Commit:** `a0de34154`

---

## Context

The Coach's "trust but verify" leg re-runs the task's pytest suite independently
of the Player (`CoachValidator.run_independent_tests`). In run-19 of FEAT-AOF
(2026-06-09), that independent-test run **timed out at 300s on every one of the
three tasks** under the LangGraph harness:

```
ERROR:guardkit.orchestrator.quality_gates.coach_validator:SDK coach test execution timed out after 300s
```

Diagnosis (`docs/state/TASK-FIX-COACHTESTTO/diagnosis.md`) traced the 300s to the
**LLM agent turn, not pytest or venv setup**. The SDK-first path
(`_run_tests_via_sdk`) dispatches the pytest run as a one-turn LLM invocation:
the coach-test model is asked to call `Bash`, run pytest, and report, and that
whole turn is bounded by `self.test_timeout` (300s). Against a slow local model
the turn never completes. Run-19 logs show the bootstrap venv was already pinned
and ready, pytest itself runs in ~2.6s, and the only activity inside the window
is the LLM `POST /v1/responses` call followed by the 300s timeout — a >100×
latency gap (2.6s subprocess vs 300s LLM-mediated).

The existing SDK-disable guard `_is_custom_api_base()` only inspects
`ANTHROPIC_BASE_URL`, which the LangGraph harness does not set (it configures its
model endpoint through the LangGraph/OpenAI-compatible channel), so the SDK path
was wrongly selected. The consequence is a silently-degraded safeguard: with no
independent result, first-pass approval rested on the Player's self-reported test
outcome plus the deterministic non-test gates — the exact absent-oracle situation
`.claude/rules/absence-of-failure-is-not-success.md` warns against.

This is orthogonal to TASK-ARCH-COACHSPLIT (verdict synthesis, which worked in
run-19); it is an independent-test-**execution** / substrate issue.

## Decision

Force the deterministic **subprocess** path for the Coach's independent tests
whenever the LangGraph harness is active — no model in the loop. Add
`CoachValidator._is_langgraph_harness()` (a `GUARDKIT_HARNESS == "langgraph"`
check) to the `use_sdk` dispatch guard in `run_independent_tests`. The subprocess
path runs the *same* pinned bootstrap-venv interpreter in the *same* worktree in
seconds. The SDK/harness path is retained only for Anthropic-hosted SDK runs.

Companion decision (absence-of-failure): when the independent-test oracle does
**not** complete (SDK timeout, SDK API error, subprocess/isolated-test timeout,
or generic execution error), mark the result
`IndependentTestResult.signal_absent = True` (with `tests_passed = False`, so it
can never read as a pass) and surface it as **ABSENT SIGNAL** via a 6th
absence-of-failure guard in the Coach synthesis prompt — never approve on the
Player's self-report when the Coach's own verification did not run.

## Rationale

- **Removes the root cause rather than masking it.** The LLM-mediated run was the
  sole latency source; the subprocess path is >100× faster (2.6s vs 300s) and
  eliminates the timeout failure mode entirely. Raising the timeout would only
  slow the symptom.
- **No environment-parity loss.** The only benefit the SDK path offered over
  subprocess was interpreter/environment parity, and the subprocess path already
  runs the same pinned bootstrap-venv interpreter in the same worktree
  (interpreter/env pinning landed in TASK-FIX-COACHPYENV). Bypassing the LLM
  costs nothing.
- **`_is_langgraph_harness` is the missing complement.** `_is_custom_api_base`
  disables the SDK path for the `ANTHROPIC_BASE_URL` case; `_is_langgraph_harness`
  is the `GUARDKIT_HARNESS` complement that `_is_custom_api_base` structurally
  cannot catch, because LangGraph configures its endpoint outside
  `ANTHROPIC_BASE_URL`.
- **Absent ≠ pass.** Marking non-completion as `signal_absent` keeps the
  trust-but-verify leg honest: a benign run-19 (Player tests genuinely passed)
  must not be allowed to normalise silently approving on a missing oracle.

## Consequences / Implementation

Confirmed in the tree today:

- `guardkit/orchestrator/quality_gates/coach_validator.py`
  - `CoachValidator._is_langgraph_harness()` (line 4142) —
    `GUARDKIT_HARNESS`-based gate, documented as the LangGraph complement to
    `_is_custom_api_base()` (line 4137).
  - `use_sdk` dispatch guard in `run_independent_tests` now includes
    `and not self._is_langgraph_harness()` (line 4672), alongside the pre-existing
    `and not self._is_custom_api_base()` (line 4671).
  - `IndependentTestResult.signal_absent: bool = False` field (line 1037,
    documented lines 1017–1029); set `True` on every non-completion path.
- `guardkit/orchestrator/agent_invoker.py`
  - 6th absence-of-failure guard "INDEPENDENT-TEST ABSENT GUARD" rendered by
    `_render_absence_of_failure_guards()` (def line 3418; guard text line 3477),
    citing `.claude/rules/absence-of-failure-is-not-success.md`.
- Tests: `tests/orchestrator/test_coach_independent_test_timeout.py` (new, AC-4);
  `tests/orchestrator/test_coach_zero_cardinality_guard.py` extended to assert the
  6th guard.

## References

- **Task:** `tasks/completed/2026-06/TASK-FIX-COACHTESTTO-coach-independent-test-execution-timeout.md`
- **Diagnosis:** `docs/state/TASK-FIX-COACHTESTTO/diagnosis.md`
- **Commit:** `a0de34154` — "fix(TASK-FIX-COACHTESTTO): Coach independent tests bypass LLM under LangGraph; mark non-completion ABSENT"
- **Rule (companion, absence-of-failure):** `.claude/rules/absence-of-failure-is-not-success.md`
- **Related tasks:** TASK-ARCH-COACHSPLIT (verdict synthesis — orthogonal),
  TASK-FIX-COACHPYENV (interpreter/env pinning that made subprocess parity-safe),
  TASK-HMIG-010 (LangGraph harness migration parent)
