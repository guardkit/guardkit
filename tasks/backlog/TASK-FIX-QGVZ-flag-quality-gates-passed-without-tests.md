---
id: TASK-FIX-QGVZ
title: Flag quality gates passed with zero test execution for feature tasks
status: backlog
created: 2026-02-08T15:30:00Z
updated: 2026-02-08T15:30:00Z
priority: medium
task_type: feature
complexity: 4
dependencies: []
parent_review: TASK-REV-53B1
tags: [autobuild, coach-validator, quality-gates]
---

# Flag Quality Gates Passed With Zero Test Execution for Feature Tasks

## Problem

In FEAT-D4CE, 4/8 feature tasks reported `all_passed: true` with `tests_passed: 0` and `coverage: null`. The Coach approved all of them without question. This means the Player's /task-work session self-reported quality gate success without actually running tests, and the Coach accepted this at face value.

**Evidence**: DM-002, DM-003, DM-004, DM-008 all show:
```json
{
  "tests_passing": true,
  "tests_passed": 0,
  "tests_failed": 0,
  "coverage": null,
  "all_passed": true
}
```

## Acceptance Criteria

- [ ] Coach validator adds a check: if `all_passed: true` AND `tests_passed == 0` AND `coverage is None` AND task type is `feature`, log a warning
- [ ] The warning should be included in the Coach's validation issues (not block approval, but flag it)
- [ ] Coach rationale should mention the anomaly: "Quality gates reported as passed but no tests were executed"
- [ ] Add a `zero_test_warning` field to `CoachValidationResult` for downstream visibility

## Implementation Notes

### Files to Modify
- `guardkit/orchestrator/quality_gates/coach_validator.py`:
  - In `verify_quality_gates()`: Add zero-test check after quality gate evaluation
  - In `validate()`: Include warning in issues list and adjust rationale

### Test Strategy
- Unit test: feature task with `all_passed: true, tests_passed: 0, coverage: null` → warning issued
- Unit test: scaffolding task with same data → no warning (tests not required)
- Unit test: feature task with `all_passed: true, tests_passed: 5` → no warning
- Unit test: warning appears in Coach decision JSON output

## Constraints

- This is a warning, not a blocker — do not change the approval decision
- Must work with existing quality gate profiles
- Must not affect scaffolding, documentation, or testing task types
