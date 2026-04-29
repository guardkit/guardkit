---
id: TASK-FIX-SG05
title: "smoke_gates: distinguish pytest exit 5 (no tests collected) from exit 1 (tests failed) in gate reporting"
status: completed
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
completed: 2026-04-29T00:00:00Z
completed_location: tasks/completed/TASK-FIX-SG05/
previous_state: in_review
state_transition_reason: "Task completed; quality gates passed (19/19 smoke-gate tests + 132/132 broader orchestrator+autobuild tests)"
priority: medium
task_type: bugfix
complexity: 3
dependencies: []
related_tasks: []
tags: [smoke-gates, orchestrator, pytest, exit-codes, reporting]
---

# smoke_gates: Distinguish pytest Exit 5 (No Tests Collected) from Exit 1 (Tests Failed)

## Description

The `guardkit/orchestrator/smoke_gates.py` module currently treats every non-zero
pytest exit code as `FAILED`. This conflates two meaningfully different situations:

- **Exit 1** — tests ran and at least one failed. This is a genuine regression.
- **Exit 5** — pytest collected zero tests (the marker expression matched nothing).
  This is a gate-configuration gap, not a code regression.

The distinction matters because when exit 5 is surfaced as a test failure, the
orchestrator preserves the worktree and reports `FEATURE RESULT: FAILED`, giving
the impression that the feature implementation is broken — when in fact it is
correct and the gate was simply never wired to a test.

**Evidence from study-tutor post-mortem (TASK-DSP-008, 2026-04-29):**

```
INFO:guardkit.orchestrator.smoke_gates:Running smoke gate after wave 5:
    pytest -m "feat-ph1-002 and smoke" -x --no-cov
WARNING:guardkit.orchestrator.smoke_gates:Smoke gate failed after wave 5
    (exit=5, expected=0)
✗ Smoke gate failed after wave 5 (exit=5, expected=0).
  Subsequent waves not started; worktree preserved at ...
```

All six implementation tasks (TASK-DSP-001..006) were approved; no test actually
failed. The smoke gate's marker expression (`feat-ph1-002 and smoke`) matched
zero tests because neither marker was registered in `pyproject.toml` and no test
file carried either marker. The real FEAT-PH1-002 implementation was functionally
complete; the autobuild run was mis-reported as failed.

Cross-repo provenance: this task was filed following the review at
`study-tutor/.claude/reviews/TASK-DSP-008-review-report.md` and its originating
task `study-tutor/tasks/backlog/deterministic-session-planner/TASK-DSP-008-smoke-gate-failure-review.md`.

## File Under Change

`guardkit/orchestrator/smoke_gates.py`

Confirm the exact location before editing — it resolves to this path from the
import `guardkit.orchestrator.smoke_gates` observed in orchestrator logs.

## Acceptance Criteria

- [ ] `smoke_gates` maps pytest exit codes to distinct outcome states:
  - exit 0 → `PASSED` (unchanged)
  - exit 1 → `FAILED` (tests ran and failed — unchanged semantics)
  - exit 5 → `GATE_NOT_WIRED` (new outcome class; see note on naming below)
  - exit 2 / 3 / 4 → existing handling preserved (interrupted / internal errors /
    usage error — keep current behaviour)
- [ ] The `GATE_NOT_WIRED` outcome surfaces a human-readable hint in both the
  console output and the autobuild history log, for example:
  > "Smoke gate matched 0 tests — verify that markers are registered in
  > pyproject.toml and that at least one test carries the marker expression."
- [ ] The failure-message string changes when exit=5:
  - Current: `Smoke gate failed after wave N (exit=5, expected=0)`
  - Required: something like `Smoke gate unwired after wave N (exit=5 — no tests
    collected); treating as config gap, not regression`
- [ ] The exit-5 outcome is **configurable per feature** via the feature spec or
  orchestrator config. Suggested knob: `smoke_gate_exit5_is_hard_fail: bool`
  (default `false`, i.e. soft warning). A project that wants strict gate
  enforcement can set this to `true` to treat an unwired gate as a hard failure.
- [ ] Unit tests cover all three primary outcome paths — exit 0, exit 1, exit 5 —
  at minimum, including the configurable hard-fail vs. soft-warning behaviour.
- [ ] The autobuild history log line for an exit-5 result is distinct from a
  genuine exit-1 failure, so post-mortems can immediately tell the two apart.

## Naming Discussion

`GATE_NOT_WIRED` clearly communicates the problem domain. Alternative: `BLOCKED_CONFIG`
(more general). The implementer should pick whichever integrates cleanly with the
existing `smoke_gates` outcome enum/constants and GuardKit's reporting vocabulary,
and document the rationale briefly in a code comment.

## Default Behaviour Rationale

Recommend **soft warning by default** (feature autobuild continues, wave is not
failed, worktree is not preserved solely for this reason). Rationale: an unwired
gate is a gap in test authoring, not a signal that the implementation is broken.
Hard-failing by default would block every feature that forgets to add smoke tests
before wiring the gate — which is a common authoring order. Teams that want strict
enforcement can opt in via config.

## Constraints

- Do NOT change exit-1 semantics — a genuine test failure must still fail the gate.
- Do NOT alter the exit-0 success path.
- The configurable knob should be per-feature (feature spec or orchestrator config),
  not a global switch, so individual features can override the default.

## See Also (Not in AC — Potential Follow-Up)

A **feature-spec lint / pre-flight check** that, before Wave 1 starts, runs the
smoke gate command in dry-run / collection-only mode (`pytest --collect-only -q`)
and warns if zero tests would be selected. This would catch the same class of gap
one phase earlier (planning / pre-build) rather than at Wave-N execution. Consider
creating a follow-up task for this once the exit-5 distinction is implemented.

## Technical Notes

- pytest exit codes reference: https://docs.pytest.org/en/stable/reference/exit-codes.html
- The log import path seen in study-tutor logs: `guardkit.orchestrator.smoke_gates`
- Confirmed source file: `guardkit/orchestrator/smoke_gates.py`
- The orchestrator also writes to an autobuild history log — ensure that path is
  updated alongside the console message, so both are consistent.

## Implementation Summary

Added a new `gate_not_wired` axis to `SmokeGateResult` so pytest exit code 5
(no tests collected) is reported distinctly from exit code 1 (tests ran and
failed). Default behaviour is a soft warning: `passed=True` and the feature
build continues, with a yellow console warning and a WARNING-level log line
that carries the actionable hint about marker registration. Per-feature opt-in
to strict enforcement is via a new `exit5_is_hard_fail: bool = False` field on
the `SmokeGates` Pydantic model — when True, `passed` flips to False but
`gate_not_wired` stays True so post-mortems still land on the marker-config
diagnosis rather than a generic test-failure.

### Files changed

- `guardkit/orchestrator/feature_loader.py` — added `exit5_is_hard_fail` field to `SmokeGates` (default `False`).
- `guardkit/orchestrator/smoke_gates.py` — added `PYTEST_EXIT_NO_TESTS_COLLECTED=5` constant, `GATE_NOT_WIRED_HINT`, `gate_not_wired` field on `SmokeGateResult`, and three-way exit-code routing (passed / unwired-soft / unwired-hard / failed) in `run_smoke_gate`.
- `guardkit/orchestrator/feature_orchestrator.py` — distinct console wording for exit 5: red blocking message under `exit5_is_hard_fail=True`, yellow warning + continue under default soft mode.
- `tests/unit/orchestrator/test_smoke_gates_exit5.py` (new) — 6 unit tests covering exit 0 / 1 / 5-soft / 5-hard / exit5-as-expected, plus a pin on `PYTEST_EXIT_NO_TESTS_COLLECTED == 5` to catch silent constant drift.

### Approach

Decision-tree refactor inside `run_smoke_gate` — the existing single-line
`passed = proc.returncode == config.expected_exit` was replaced with a
four-branch routing keyed on (matched_expected, gate_not_wired,
exit5_is_hard_fail). Each branch picks both the `passed` value AND a distinct
log line, so the WARNING-level message string is the canonical diagnostic
surface; the orchestrator's console output mirrors it for the human
post-mortem. `gate_not_wired` is a defaulted dataclass field, so all existing
`SmokeGateResult(...)` constructors in tests and the orchestrator stay
backwards-compatible without modification.

### Lessons

- The "expected_exit=5" branch matters: a feature that genuinely declares exit 5
  as success (e.g. a deliberately-empty marker as a sanity check) must NOT be
  flagged as unwired — `gate_not_wired` is a function of `(returncode == 5 AND
  returncode != expected_exit)`, not of `returncode == 5` alone.
- Adding a defaulted field to both the Pydantic config (`SmokeGates`) and the
  dataclass result (`SmokeGateResult`) is fully backwards-compatible — the 132
  existing orchestrator+autobuild tests passed without any constructor edits.
- Originating evidence: study-tutor TASK-DSP-008 post-mortem, where a marker
  expression `feat-ph1-002 and smoke` matched zero tests because neither marker
  was registered in `pyproject.toml` and no test carried either marker. The
  feature was functionally complete; the autobuild was mis-reported as failed.

### Test results

19/19 smoke-gate tests pass (6 new + 13 existing). 132/132 broader
orchestrator + autobuild tests pass with no regressions.

## Notes

- Cross-repo provenance: `study-tutor/.claude/reviews/TASK-DSP-008-review-report.md`
  and `study-tutor/tasks/backlog/deterministic-session-planner/TASK-DSP-008-smoke-gate-failure-review.md`
  are the originating context for this task.
- Follow-up candidate (already noted in task body, deliberately out of AC):
  feature-spec lint that runs `pytest --collect-only -q` at planning time so
  the same class of gap is caught one phase earlier.
