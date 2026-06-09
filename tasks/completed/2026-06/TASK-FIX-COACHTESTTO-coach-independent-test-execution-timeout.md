---
id: TASK-FIX-COACHTESTTO
title: Coach independent-test (SDK) execution times out at 300s — trust-but-verify leg never completes
status: completed
task_type: bugfix
created: 2026-06-09T00:00:00Z
updated: 2026-06-09T12:05:00Z
completed: 2026-06-09T12:05:00Z
completed_location: tasks/completed/2026-06/
previous_state: in_review
state_transition_reason: "Task complete — all 4 ACs satisfied, quality gate passed (zero regressions)"
priority: medium
complexity: 4
parent_task: TASK-HMIG-010
related: [TASK-ARCH-COACHSPLIT, TASK-FIX-COACHPYENV, TASK-OPS-COACH31B]
implementation_mode: task-work
---

# Task: Coach independent-test execution times out at 300s (trust-but-verify leg never completes)

## Why this task exists

Run-19 (FEAT-AOF, 2026-06-09) was a full success — 3/3 first-pass Coach
approvals via the new D-3 toolless grammar synthesis. **But the Coach's
independent test execution timed out on every one of the three tasks**:

```
ERROR:guardkit.orchestrator.quality_gates.coach_validator:SDK coach test execution timed out after 300s
```

(`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-19.md:197,540,545`)

The consequence is a quietly-degraded safeguard: the Coach's "trust but
verify" independent pytest run (`CoachValidator.run_independent_tests`)
produced **no result** on any task, so first-pass approval rested on the
**Player's self-reported** test outcome plus the deterministic non-test
gates (coverage / honesty / plan_audit / arch_review) — not on the Coach
independently re-running the tests. That is exactly the kind of
absent-oracle situation `.claude/rules/absence-of-failure-is-not-success.md`
warns about; it happened to be benign in run-19 (the Player's tests really
did pass and the other gates were green), but it should not be the silent
steady state.

This is **orthogonal to TASK-ARCH-COACHSPLIT** (the verdict-synthesis fix
worked); it is an independent-test-execution / environment issue.

## Investigation starting points

- `CoachValidator.run_independent_tests` (`guardkit/orchestrator/quality_gates/coach_validator.py`)
  — the SDK-first path (`_run_tests_via_sdk`) vs the subprocess fallback,
  and the `test_timeout` / 300s bound. Why 300s, and is it the SDK turn
  budget or a pytest wall-clock?
- **venv bootstrap cost**: TASK-FIX-COACHPYENV wired a bootstrap venv for
  the Coach test interpreter. If each independent-test run rebuilds /
  resolves a venv in the fresh `--fresh` worktree, 300s may be eaten by
  environment setup before pytest even starts. Measure the split.
- **SDK overhead**: the SDK-first execution path routes the pytest run
  through the harness; under the LangGraph substrate that may add latency
  or not honour the 300s the way the subprocess path does. Consider
  forcing the subprocess path for independent tests, or raising the bound.

## Acceptance criteria

- [x] **AC-1**: Root-caused — a written diagnosis of WHERE the 300s goes
  (venv bootstrap vs pytest collection vs test runtime vs SDK overhead),
  with evidence from a reproduction (a single Coach independent-test run
  instrumented with timing).
- [x] **AC-2**: Fix applied so the Coach independent-test leg COMPLETES for
  a representative FEAT-AOF-class task within its budget — whether by
  (a) caching/reusing the bootstrap venv across the run, (b) forcing the
  subprocess path, (c) raising the timeout to a justified value, or a
  combination. The chosen lever is documented.
- [x] **AC-3**: When the independent-test leg genuinely cannot run (e.g.
  real timeout after the fix), the Coach treats the result as **ABSENT
  SIGNAL**, not a pass — verify the evidence bundle marks
  `independent_tests` as absent/failed and the absence-of-failure guard in
  the synthesis prompt still fires (no auto-approve on the missing oracle).
- [x] **AC-4**: Regression test for the timeout/absent-result path in
  `tests/orchestrator/` (the Coach must not approve purely on the Player's
  self-reported tests when its own independent verification did not run).

## Outcome (2026-06-09, task-work)

**Root cause** (AC-1, full writeup in
[`docs/state/TASK-FIX-COACHTESTTO/diagnosis.md`](../../docs/state/TASK-FIX-COACHTESTTO/diagnosis.md)):
the 300s budget is consumed by the **LLM agent turn**, not pytest/venv. Under
`GUARDKIT_HARNESS=langgraph` the SDK path (`_run_tests_via_sdk`) runs pytest
through a one-turn LLM invocation against a slow local model; the whole turn is
bounded by `test_timeout` (300s) and never completes. Run-19 log evidence: the
test command was already pinned to the ready `.venv` interpreter (no bootstrap
in the window), the only activity is the `POST /v1/responses` LLM call, then
the 300s timeout. The existing SDK-disable guard `_is_custom_api_base()` only
inspects `ANTHROPIC_BASE_URL`, which LangGraph does not set, so the SDK path
was wrongly selected. Reproduction: the same class of test file runs in **2.6s**
via subprocess vs **300s** timeout via the LLM path (>100×).

**Fix levers chosen**:
- **AC-2 — force subprocess under LangGraph** (option (b)). New
  `CoachValidator._is_langgraph_harness()` added to the `use_sdk` guard in
  `run_independent_tests`. Subprocess runs the *same* pinned interpreter in the
  *same* worktree in seconds with no model in the loop — removes the root cause
  rather than masking it. (Option (a) moot — venv already ready; (c) only slows
  the symptom; the coach path uses `test_timeout=300`, independent of
  `--sdk-timeout`.)
- **AC-3 — mark non-completion as ABSENT**. New `signal_absent: bool` field on
  `IndependentTestResult`, set `True` (with `tests_passed=False`) on every
  non-completion path (SDK timeout, SDK API error, subprocess timeout,
  isolated-test timeout, generic execution error). New 6th absence-of-failure
  guard ("INDEPENDENT-TEST ABSENT GUARD") in
  `agent_invoker._render_absence_of_failure_guards` so the LLM Coach surfaces an
  absent oracle as feedback instead of approving on the Player's self-report.
  Aligns with `.claude/rules/absence-of-failure-is-not-success.md`.

**Files changed**:
- `guardkit/orchestrator/quality_gates/coach_validator.py` —
  `IndependentTestResult.signal_absent`, `_is_langgraph_harness()`, `use_sdk`
  guard, `signal_absent=True` on all 5 non-completion paths.
- `guardkit/orchestrator/agent_invoker.py` — guard #6 in
  `_render_absence_of_failure_guards` (+ docstring).
- `tests/orchestrator/test_coach_independent_test_timeout.py` — new (AC-4).
- `tests/orchestrator/test_coach_zero_cardinality_guard.py` — extended the
  guard-count assertion to include guard #6.

**Quality gate**: new regression suite 19 passed / 1 skipped (the SDK-timeout
test is skipped on Python < 3.11 because `_run_tests_via_sdk` uses
`asyncio.timeout()`, 3.11+ only — production/run-19 is 3.11+). Verified via
baseline `comm` diff that the change introduces **zero new test failures**; all
remaining failures in the broader suite are pre-existing Python-3.10
`asyncio.timeout` incompatibilities and pre-existing dead-task-ID-reference debt
unrelated to this task.

## Notes

- Surfaced during the review of run-19 snapshot commit `c48dd53b`.
- Pair with the run-19 caveat in
  `docs/state/TASK-REV-HMIG/run-19-artifacts/README.md` (caveat #1).
