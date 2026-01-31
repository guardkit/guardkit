---
id: TASK-AB-FIX-002
title: Add Error Classification to AutoBuild Player Invocation
status: backlog
created: 2026-01-31T15:45:00Z
updated: 2026-01-31T15:45:00Z
priority: high
tags: [autobuild, error-handling, fix]
task_type: implementation
parent_review: TASK-GR-REV-001
complexity: 4
depends_on: []
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

- [ ] Define `UNRECOVERABLE_ERRORS` tuple with error types that should not be retried
- [ ] Add specific exception handling for unrecoverable errors in `_invoke_player_safely()`
- [ ] Include `unrecoverable: True` flag in result report for these errors
- [ ] Ensure error message distinguishes recoverable vs unrecoverable
- [ ] Add unit tests for both error types
- [ ] Verify that recoverable errors still allow retries

## Implementation

### File: guardkit/orchestrator/autobuild.py

```python
from guardkit.orchestrator.exceptions import (
    PlanNotFoundError,
    TaskNotFoundError,
    StateValidationError,
)

# Unrecoverable errors that should fail immediately
UNRECOVERABLE_ERRORS = (
    PlanNotFoundError,
    TaskNotFoundError,
    StateValidationError,
)

def _invoke_player_safely(self, task_id: str, turn: int, requirements: str, feedback: Optional[str]) -> AgentInvocationResult:
    """
    Invoke player with error classification.

    Distinguishes between:
    - Unrecoverable errors: Signal to stop retrying immediately
    - Recoverable errors: Allow retry logic to continue
    """
    try:
        # ... existing invocation logic ...
        pass

    except UNRECOVERABLE_ERRORS as e:
        logger.error(f"Unrecoverable error for {task_id}: {e}")
        return AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="player",
            success=False,
            report={"unrecoverable": True},  # Signal to stop retrying
            duration_seconds=0.0,
            error=f"Unrecoverable: {str(e)}",
        )

    except Exception as e:
        # Recoverable error - allow retry
        logger.warning(f"Recoverable error for {task_id}: {e}", exc_info=True)
        return AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="player",
            success=False,
            report={"unrecoverable": False},
            duration_seconds=0.0,
            error=f"Recoverable: {str(e)}",
        )
```

## Test Requirements

- [ ] Unit test: `test_unrecoverable_error_returns_unrecoverable_flag`
- [ ] Unit test: `test_recoverable_error_allows_retry`
- [ ] Unit test: `test_plan_not_found_is_unrecoverable`
- [ ] Unit test: `test_task_not_found_is_unrecoverable`
- [ ] Unit test: `test_state_validation_error_is_unrecoverable`

## Files to Modify

1. `guardkit/orchestrator/autobuild.py` - Add error classification in `_invoke_player_safely()`
2. `tests/orchestrator/test_autobuild.py` - Add new tests

## References

- [TASK-GR-REV-001 Review Report](.claude/reviews/TASK-GR-REV-001-review-report.md) - Deep Dive 2: Error Recovery Patterns
- TASK-AB-FIX-001 - Related fix for state bridge context
- TASK-AB-FIX-003 - Companion fix for loop phase handling
