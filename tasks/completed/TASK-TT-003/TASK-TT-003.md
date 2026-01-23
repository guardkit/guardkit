---
id: TASK-TT-003
title: "Add testing and refactor keywords to task_type_detector"
status: completed
created: 2026-01-23T00:00:00Z
updated: 2026-01-23T00:00:00Z
completed: 2026-01-23T00:00:00Z
priority: high
tags: [task-types, detector, keywords]
task_type: feature
parent_review: TASK-REV-FB27
feature_id: FEAT-TT
implementation_mode: task-work
wave: 1
conductor_workspace: task-type-wave1-detector
complexity: 3
previous_state: in_review
state_transition_reason: "Task completed - all quality gates passed"
completed_location: tasks/completed/TASK-TT-003/
organized_files:
  - TASK-TT-003.md
---

# Task: Add Testing and Refactor Keywords to Task Type Detector

## Description

Add keyword mappings for `TaskType.TESTING` and `TaskType.REFACTOR` to the `KEYWORD_MAPPINGS` dictionary in `guardkit/lib/task_type_detector.py`. Update the priority order to check TESTING and REFACTOR appropriately.

## Acceptance Criteria

- [x] `detect_task_type("Add unit tests")` returns `TaskType.TESTING`
- [x] `detect_task_type("Set up testing infrastructure")` returns `TaskType.TESTING`
- [x] `detect_task_type("Refactor authentication module")` returns `TaskType.REFACTOR`
- [x] `detect_task_type("Migrate to new API")` returns `TaskType.REFACTOR`
- [x] Existing detection still works (infrastructure, documentation, scaffolding, feature)
- [x] Priority order prevents false matches (e.g., "setup" doesn't override "testing")

## Implementation Summary

### Files Modified

1. **guardkit/lib/task_type_detector.py**
   - Added TESTING keywords (17): pytest, unittest, jest, vitest, mocha, jasmine, test, testing, spec, e2e, end-to-end, integration test, unit test, test fixture, test setup, mock, stub
   - Added REFACTOR keywords (11): refactor, refactoring, restructure, migrate, migration, upgrade, modernize, modernization, cleanup, clean up, clean-up
   - Updated priority loop: INFRASTRUCTURE → TESTING → REFACTOR → DOCUMENTATION → SCAFFOLDING
   - Updated get_task_type_summary() with new entries
   - Updated module docstring with new priority order

2. **tests/unit/test_task_type_detector.py**
   - Added TestTestingDetection class (4 tests)
   - Added TestRefactorDetection class (5 tests)
   - Added priority order tests (6 new tests)
   - Updated existing tests for new behavior

### Test Results

- 62 tests passing (100%) in test_task_type_detector.py
- 120 tests passing (100%) total in task_types module
- All 6 acceptance criteria verified
- No regressions in existing functionality

## Quality Gates

| Gate | Status |
|------|--------|
| Compilation | ✅ PASS |
| Tests (62/62) | ✅ PASS |
| Acceptance Criteria (6/6) | ✅ PASS |
| Code Review | ✅ APPROVED |
| Architectural Review | ✅ 92/100 |

## Completion Details

- **Duration**: ~5 minutes
- **Complexity**: 3/10 (Simple)
- **Workflow**: Standard /task-work execution
- **Agents Used**: task-manager, architectural-reviewer, general-purpose, code-reviewer

## Notes

- TESTING must be checked before SCAFFOLDING to ensure "Set up testing infrastructure" returns TESTING (not SCAFFOLDING due to "setup")
- REFACTOR is checked after TESTING but before DOCUMENTATION to catch migration tasks correctly
- Part of FEAT-TT (Task Type Expansion) feature set
