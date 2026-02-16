---
id: TASK-ABF-003
title: Add actionable context to zero-test anomaly feedback
status: completed
created: 2026-02-16T00:00:00Z
updated: 2026-02-16T12:00:00Z
completed: 2026-02-16T12:00:00Z
completed_location: tasks/completed/TASK-ABF-003/
priority: high
tags: [autobuild, enhancement, feedback, coach-validator]
task_type: feature
complexity: 2
parent_review: TASK-REV-F3BE
feature_id: FEAT-ABF
wave: 2
implementation_mode: task-work
dependencies: [TASK-ABF-001, TASK-ABF-002]
previous_state: in_review
state_transition_reason: "All acceptance criteria met, all tests passing"
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-16T12:00:00Z
---

# Task: Add actionable context to zero-test anomaly feedback

## Description

Modify the zero-test anomaly issue description in `coach_validator.py` to include the glob pattern the Coach tried and guidance on how to name test files so they are detected. The current description provides no actionable information, causing the Player to repeat the same approach and produce identical feedback signatures across turns.

## Context

From review TASK-REV-F3BE (Finding 4): The zero-test anomaly description is:
> "No task-specific tests created and no task-specific tests found via independent verification. Project-wide test suite may pass but this task contributes zero test coverage."

This gives zero guidance on: (1) what glob pattern the Coach expects, (2) that the Player's test file exists but isn't being detected, or (3) how to name test files to be found. The identical feedback hash (`36d91c7c`) across 5 turns confirms the Player received no new information to break the loop.

## Acceptance Criteria

- [x] Zero-test anomaly description includes the glob pattern that was tried
- [x] Description suggests listing test files in `task_work_results` `files_created`/`files_modified`
- [x] Description suggests the naming convention `test_{task_prefix}*.py`
- [x] Existing tests checking `category == "zero_test_anomaly"` and `severity` still pass
- [x] New test: verify description contains the glob pattern
- [x] Feedback text changes between turns when task context differs (breaks stall signatures)

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` (lines 1830-1837) - The fix location
- `guardkit/orchestrator/quality_gates/coach_validator.py` (lines 1525-1542) - `_task_id_to_pattern_prefix`
- `guardkit/orchestrator/autobuild.py` (lines 3648-3669) - Feedback extraction
- `tests/unit/test_coach_validator.py` (lines 2330-3235) - Existing zero-test anomaly tests

## Implementation Summary

### Changes Made

1. **`coach_validator.py:1775`** - Added `task_id: Optional[str] = None` parameter to `_check_zero_test_anomaly`
2. **`coach_validator.py:584-586`** - Pass `task_id=task_id` from `validate()` call site
3. **`coach_validator.py:1832-1844`** - Updated description in first anomaly branch to include:
   - The actual glob pattern searched (e.g., `tests/**/test_task_fha_002*.py`)
   - Guidance to list files in `files_created`/`files_modified`
   - The naming convention `test_{task_prefix}*.py`
4. **`test_coach_validator.py:2954-2987`** - New test `test_project_wide_pass_description_contains_glob_pattern`

## Test Execution Log

- **Run**: 2026-02-16
- **Tests**: 195 passed, 0 failed
- **New test**: `test_project_wide_pass_description_contains_glob_pattern` - PASSED
- **Regression**: All 20 zero-test anomaly tests pass unchanged
