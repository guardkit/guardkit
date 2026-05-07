---
id: TASK-GK-CR-001
title: Populate requirements validation on Coach gate-fail short-circuit
status: backlog
created: 2026-05-07 00:00:00+00:00
updated: 2026-05-07 00:00:00+00:00
priority: high
priority_band: P0
task_type: feature
parent_review: TASK-REV-PEBR-001
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-1-analysis.md
implementation_mode: task-work
wave: 1
complexity: 6
estimated_minutes: 115
dependencies: []
tags:
  - autobuild
  - coach-evaluator
  - criteria-verification
  - stall-detector
  - regression-fix
  - P0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Populate requirements validation on Coach gate-fail short-circuit

## Description

When any required quality gate fails,
`CoachValidator._feedback_from_gates` is called and immediately returns
a `CoachResult` with `requirements=None`
([guardkit/orchestrator/quality_gates/coach_validator.py:1080-1086](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L1080-L1086)).
The `_validate_requirements` step never runs, so
`coach_result.report.validation_results.requirements` is null
(visible in `coach_turn_*.json:14` for the FEAT-PEBR run).

Downstream this zeroes out `_count_criteria_passed`
([guardkit/orchestrator/autobuild.py:4106-4140](../../../guardkit/orchestrator/autobuild.py#L4106-L4140)),
which keeps `criteria_passed` permanently at 0 across turns. The stall
detector at `autobuild.py:3998-4000` then trips after exactly 3 turns
of identical feedback because the threshold-extension path
(`autobuild.py:4002-4017`) is gated on `counts[0] > 0`.

This is **stage 4 of the deterministic stall chain** (see review
report AC-3 / AC-6). Even with TASK-GK-AC-001 fixing the primary root
cause, this short-circuit is a defence-in-depth liability — any future
gate-failure mode (honesty check, security gate, etc.) that produces
identical feedback will hit the same zero-criteria lock-in.

## Acceptance Criteria

- [ ] AC-1: When `_feedback_from_gates` is the return path, the
  resulting `CoachResult.requirements` is populated by running the
  same logic as the all-gates-pass path
  (`_match_by_promises` / `_hybrid_fallback` / `_match_by_text` —
  see `coach_validator.py:2598-2683`). It must NOT influence the
  Coach `decision` (still `feedback`) or
  `quality_gates.all_gates_passed` (still `False`).
- [ ] AC-2: Six call sites currently pass `requirements=requirements`
  into the gate-fail return paths
  (`coach_validator.py:1378, 1406, 1453, 1482, 1540`,
  plus the main `_feedback_from_gates` exit). All six must produce a
  non-None `RequirementsValidation` when the Player report contains
  `completion_promises` or `requirements_addressed`.
- [ ] AC-3: After this fix, replaying the FEAT-PEBR turn-1
  task_work_results.json through the Coach produces
  `validation_results.requirements.criteria_met == 6` (Player reported
  all 6 ACs complete) AND `decision == "feedback"` (gate still failed
  — bug #1 not yet fixed in this PR).
- [ ] AC-4: With criteria_met=6 surfacing,
  `autobuild._count_criteria_passed` returns 6 (was 0). The stall
  detector's extended-threshold path becomes reachable.
- [ ] AC-5: Existing tests in `tests/quality_gates/test_coach_validator.py`
  that assert `decision=feedback` on gate fail continue to pass —
  this is purely additive behaviour.
- [ ] AC-6: New regression test reproduces the FEAT-PEBR scenario
  (gate-fail + 6 ACs reported complete) and asserts
  `criteria_met=6, decision="feedback", criteria_passed_in_stall_detector=6`.
- [ ] AC-7: All modified files pass project-configured lint/format
  checks with zero errors.

## Test requirements

- Unit test: gate-fail path with `completion_promises` populated →
  requirements.criteria_met matches the promise count.
- Unit test: gate-fail path with no Player promises but
  `requirements_addressed` populated → `_match_by_text` fallback fires
  and criteria_met populates.
- Unit test: gate-fail path with neither → requirements stays None
  (current behaviour preserved for old Player report formats).
- Integration test: Coach `decision` and `all_gates_passed` are
  unchanged by this fix (criteria reporting must NOT promote a gate
  fail to a pass).

## Implementation notes

### Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py`:
  - The main gate-fail return at lines 1080-1086
  - Five additional gate-fail return sites at lines 1378, 1406,
    1453, 1482, 1540 (each currently passes
    `requirements=requirements` — verify the upstream `requirements`
    var is the validated one, not None)
  - Possibly `_feedback_from_gates` itself if requirements
    construction is centralised there
- `tests/quality_gates/test_coach_validator.py` — add the four new
  test methods per AC-1/2/3/6

### Recommended approach

Hoist the requirements validation step to BEFORE the gate-fail
short-circuit:

```python
# 1. Quality-gate evaluation (unchanged)
gates_status = self._evaluate_quality_gates(...)

# NEW: Always validate requirements, regardless of gate outcome.
# Used for criteria_passed reporting only — does NOT affect decision.
requirements = self._validate_requirements_for_reporting(
    task_work_results=task_work_results,
    acceptance_criteria=acceptance_criteria,
    turn=turn,
)

# 2. Gate fail → feedback (now with requirements populated)
if not gates_status.all_gates_passed:
    return self._feedback_from_gates(
        ...,
        requirements=requirements,  # NEW: was implicitly None
    )
```

`_validate_requirements_for_reporting` is a new wrapper around the
existing `_match_by_promises` / `_hybrid_fallback` / `_match_by_text`
calls (already used at `coach_validator.py:2598-2683`) — extract that
logic so it's callable from both paths.

### Critical regression guard

`coach_result.decision` must NEVER be promoted from `feedback` to
`approve` solely because requirements happen to all pass. The
`all_gates_passed` flag remains the sole gate on `decision`. Add an
explicit assertion in the new code path:

```python
assert gates_status.all_gates_passed or coach_result.decision == "feedback"
```

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/quality_gates/test_coach_validator.py -x -v
PYTHONPATH=. python -m pytest tests/orchestrator/test_autobuild.py -x -v -k stall
ruff check guardkit/orchestrator/quality_gates/coach_validator.py
```

## Out of scope

- Fixing the underlying gate failure (TASK-GK-AC-001).
- Stall detector logic changes (autobuild.py — the existing
  extended-threshold path is correct; this task just unblocks it).
- Reordering `issues` for operator display (TASK-GK-FB-001).
