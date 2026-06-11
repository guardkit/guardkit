---
id: TASK-FIX-TP05
title: Add independent test execution for testing task type
status: in_review
created: 2026-02-20 00:00:00+00:00
updated: 2026-02-20 00:00:00+00:00
priority: low
tags:
- autobuild
- enhancement
- quality-gates
- testing-profile
task_type: feature
complexity: 4
parent_review: TASK-REV-A515
feature_id: FEAT-AOF
wave: 2
implementation_mode: task-work
dependencies:
- TASK-FIX-TS04
autobuild:
  task_timeout: 4800
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
  base_branch: main
  started_at: '2026-06-11T16:56:44.586640'
  last_updated: '2026-06-11T17:11:15.127616'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-06-11T16:56:44.586640'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Add independent test execution for testing task type

## Description

Tasks with `task_type: testing` currently have `tests_required=False` in their quality gate profile. This means the Coach skips independent test verification — the Player writes test files but nobody confirms they actually pass.

While avoiding circularity (testing a test task's tests) is a valid concern, the Coach should at minimum execute the newly written test files to verify they pass. This catches import errors, syntax issues, and missing fixtures without introducing philosophical circularity.

## Source

- Review report: `.claude/reviews/TASK-REV-A515-review-report.md` (Finding 5, R5)
- Evidence: TASK-RK01-013 and TASK-RK01-014 both created test files that were never independently verified

## Files to Modify

- `guardkit/models/task_types.py` — Update TESTING profile
- `guardkit/orchestrator/quality_gates/coach_validator.py` — May need test execution logic for testing tasks

## Implementation Plan

### Step 1: Enable `tests_required=True` for TESTING profile

In `guardkit/models/task_types.py`:

```python
TaskType.TESTING: QualityGateProfile(
    arch_review_required=False,
    arch_review_threshold=0,
    coverage_required=False,
    coverage_threshold=0.0,
    tests_required=True,   # Changed from False
    plan_audit_required=True,
    zero_test_blocking=False,  # Don't block on zero tests — task may be writing the first tests
),
```

### Step 2: Verify Coach handles testing tasks correctly

The Coach's `run_independent_tests` method should run `pytest` against the test files the Player created. Verify that:
- It finds the test files from `tests_written` in the player report
- It executes them and reports results
- Failures produce actionable feedback (not circular "write tests for your tests")

### Step 3: Handle edge case — test infrastructure tasks

Some testing tasks create test infrastructure (conftest.py, fixtures) that aren't independently runnable. The Coach feedback for these should note that conftest.py files provide fixtures for other tests rather than requesting standalone test execution.

## Risk Assessment

- **Low risk**: If tests fail, the Player gets feedback and can fix them (standard adversarial loop)
- **No circularity**: We're verifying that the written tests pass, not asking the Player to write tests for its tests
- **Graceful degradation**: If no test runner is available, `tests_required=True` with `zero_test_blocking=False` means the task isn't blocked

## Acceptance Criteria

- [ ] TESTING profile has `tests_required=True`
- [ ] Coach independently executes test files written by testing tasks
- [ ] Test failures produce actionable Coach feedback
- [ ] `zero_test_blocking` remains False (don't block if no test runner available)
- [ ] Tasks that only create test infrastructure (conftest.py) don't false-fail
- [ ] Unit test verifies the updated profile
