---
id: TASK-AB-FIX-002
title: Add Error Classification to AutoBuild Player Invocation
status: completed
created: 2026-01-31T15:45:00Z
updated: 2026-01-31T16:15:00Z
completed: 2026-01-31T16:15:00Z
priority: high
tags: [autobuild, error-handling, fix]
task_type: implementation
parent_review: TASK-GR-REV-001
complexity: 4
depends_on: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
completed_location: tasks/completed/TASK-AB-FIX-002/
organized_files:
  - TASK-AB-FIX-002.md
---

# Task: Add Error Classification to AutoBuild Player Invocation

## Description

Add error classification to distinguish recoverable from unrecoverable errors in `_invoke_player_safely()`. Currently, all exceptions are caught generically and wrapped in "Unexpected error" messages, causing 25 retries for errors that can never be resolved.

**Root Cause (from TASK-GR-REV-001):**

The current exception handling:
```python
except Exception as e:
    logger.error(f"Player invocation failed: {e}", exc_info=True)
    return AgentInvocationResult(
        success=False,
        error=f"Unexpected error: {str(e)}",  # No classification!
    )
```

This wraps ALL errors generically, preventing the loop phase from distinguishing recoverable (retry-worthy) from unrecoverable (fail-fast) errors.

**Solution:**

Define unrecoverable error types and handle them separately, signaling to the caller that retrying is futile.

## Acceptance Criteria

- [x] Define `UNRECOVERABLE_ERRORS` tuple with error types that should not be retried
- [x] Add specific exception handling for unrecoverable errors in `_invoke_player_safely()`
- [x] Include `unrecoverable: True` flag in result report for these errors
- [x] Ensure error message distinguishes recoverable vs unrecoverable
- [x] Add unit tests for both error types
- [x] Verify that recoverable errors still allow retries

## Implementation Summary

### Changes Made

**1. guardkit/orchestrator/autobuild.py**

Added `UNRECOVERABLE_ERRORS` constant (lines 123-132):
```python
UNRECOVERABLE_ERRORS = (
    PlanNotFoundError,
    StateValidationError,
)
```

Modified `_invoke_player_safely()` exception handling (lines 1937-1960):
- Added `except UNRECOVERABLE_ERRORS as e:` block with `report={"unrecoverable": True}`
- Updated generic Exception handler with `report={"unrecoverable": False}`
- Changed log levels: error for unrecoverable, warning for recoverable

**2. tests/unit/test_autobuild_orchestrator.py**

Added `TestPlayerErrorClassification` test class with 4 tests:
- `test_invoke_player_safely_unrecoverable_error`
- `test_invoke_player_safely_recoverable_error`
- `test_invoke_player_safely_plan_not_found_is_unrecoverable`
- `test_invoke_player_safely_state_validation_error_is_unrecoverable`

### Test Results

All 4 new tests passing:
```
tests/unit/test_autobuild_orchestrator.py::TestPlayerErrorClassification::test_invoke_player_safely_unrecoverable_error PASSED
tests/unit/test_autobuild_orchestrator.py::TestPlayerErrorClassification::test_invoke_player_safely_recoverable_error PASSED
tests/unit/test_autobuild_orchestrator.py::TestPlayerErrorClassification::test_invoke_player_safely_plan_not_found_is_unrecoverable PASSED
tests/unit/test_autobuild_orchestrator.py::TestPlayerErrorClassification::test_invoke_player_safely_state_validation_error_is_unrecoverable PASSED
```

### Quality Gates

| Gate | Status | Score |
|------|--------|-------|
| Architectural Review | ✅ | 88/100 |
| Tests Passing | ✅ | 100% |
| Code Review | ✅ | APPROVED |

## Completion Details

- **Completed By**: task-work workflow
- **Completion Date**: 2026-01-31T16:15:00Z
- **Duration**: ~30 minutes
- **Files Modified**: 2 (autobuild.py, test_autobuild_orchestrator.py)
- **Tests Added**: 4

## References

- [TASK-GR-REV-001 Review Report](.claude/reviews/TASK-GR-REV-001-review-report.md) - Deep Dive 2: Error Recovery Patterns
- TASK-AB-FIX-001 - Related fix for state bridge context
- TASK-AB-FIX-003 - Companion fix for loop phase handling
