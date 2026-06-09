---
id: TASK-FIX-COACHTESTTO
title: Coach independent-test (SDK) execution times out at 300s — trust-but-verify leg never completes
status: backlog
task_type: bugfix
created: 2026-06-09T00:00:00Z
updated: 2026-06-09T00:00:00Z
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

- [ ] **AC-1**: Root-caused — a written diagnosis of WHERE the 300s goes
  (venv bootstrap vs pytest collection vs test runtime vs SDK overhead),
  with evidence from a reproduction (a single Coach independent-test run
  instrumented with timing).
- [ ] **AC-2**: Fix applied so the Coach independent-test leg COMPLETES for
  a representative FEAT-AOF-class task within its budget — whether by
  (a) caching/reusing the bootstrap venv across the run, (b) forcing the
  subprocess path, (c) raising the timeout to a justified value, or a
  combination. The chosen lever is documented.
- [ ] **AC-3**: When the independent-test leg genuinely cannot run (e.g.
  real timeout after the fix), the Coach treats the result as **ABSENT
  SIGNAL**, not a pass — verify the evidence bundle marks
  `independent_tests` as absent/failed and the absence-of-failure guard in
  the synthesis prompt still fires (no auto-approve on the missing oracle).
- [ ] **AC-4**: Regression test for the timeout/absent-result path in
  `tests/orchestrator/` (the Coach must not approve purely on the Player's
  self-reported tests when its own independent verification did not run).

## Notes

- Surfaced during the review of run-19 snapshot commit `c48dd53b`.
- Pair with the run-19 caveat in
  `docs/state/TASK-REV-HMIG/run-19-artifacts/README.md` (caveat #1).
