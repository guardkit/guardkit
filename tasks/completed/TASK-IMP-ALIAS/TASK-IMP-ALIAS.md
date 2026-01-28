---
id: TASK-IMP-ALIAS
title: Add task_type alias support in CoachValidator
status: completed
task_type: feature
created: 2026-01-28T12:45:00Z
updated: 2026-01-28T13:30:00Z
completed: 2026-01-28T14:00:00Z
completed_location: tasks/completed/TASK-IMP-ALIAS/
priority: medium
tags:
- coach-validator
- task-type
- backward-compatibility
- defensive-coding
complexity: 3
parent_review: TASK-REV-FMT2
previous_state: in_review
state_transition_reason: "Code review approved, all quality gates passed"
organized_files:
- TASK-IMP-ALIAS.md
- code-review.md
---

# Task: Add task_type Alias Support in CoachValidator

## Summary

Add alias mapping in `CoachValidator._resolve_task_type()` to gracefully handle legacy `task_type` values that are not in the `TaskType` enum. This is a defensive measure to prevent validation failures for the 161+ task files using `task_type: implementation`.

## Background

From TASK-REV-FMT2 review findings:
- 161 task files use `task_type: implementation` (not a valid enum value)
- 4 task files use `task_type: bug-fix` or `bug_fix`
- 2 task files use `task_type: benchmark`
- Valid enum values are: `scaffolding`, `feature`, `infrastructure`, `documentation`, `testing`, `refactor`

## Requirements

Add alias mapping that converts legacy values to valid TaskType enum values:

```python
TASK_TYPE_ALIASES = {
    "implementation": TaskType.FEATURE,
    "bug-fix": TaskType.FEATURE,
    "bug_fix": TaskType.FEATURE,
    "benchmark": TaskType.TESTING,
    "research": TaskType.DOCUMENTATION,
}
```

## Acceptance Criteria

- [x] Add `TASK_TYPE_ALIASES` constant at module level in `coach_validator.py`
- [x] Update `_resolve_task_type()` to check aliases before raising ValueError
- [x] Log info message when alias is used (for transparency)
- [x] Add unit tests for alias resolution
- [x] Existing tests continue to pass

## Implementation Completed

**Files Modified:**
1. `guardkit/orchestrator/quality_gates/coach_validator.py`
   - Added `TASK_TYPE_ALIASES` constant (lines 46-54)
   - Updated `_resolve_task_type()` method (lines 305-355)

**Files Created:**
1. `tests/unit/test_coach_validator_aliases.py` - 13 unit tests

## Test Results

- 13 new alias tests: PASSED
- 95 existing coach_validator tests: PASSED
- Total: 108/108 tests passing (100%)

## Quality Gate Results

| Gate | Threshold | Result |
|------|-----------|--------|
| Compilation | 100% | ✅ Passed |
| Tests Passing | 100% | ✅ 108/108 |
| Architectural Review | ≥60/100 | ✅ 92/100 |
| Code Review | Pass | ✅ Approved |

## Related

- Review: TASK-REV-FMT2
- Report: `.claude/reviews/TASK-REV-FMT2-review-report.md`
