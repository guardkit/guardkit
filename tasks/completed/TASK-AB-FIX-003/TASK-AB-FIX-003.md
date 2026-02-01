---
id: TASK-AB-FIX-003
title: Handle Unrecoverable Errors in AutoBuild Loop Phase
status: completed
created: 2026-01-31T15:50:00Z
updated: 2026-01-31T16:35:00Z
completed: 2026-01-31T16:35:00Z
priority: high
tags: [autobuild, error-handling, fix]
task_type: implementation
parent_review: TASK-GR-REV-001
complexity: 3
depends_on: [TASK-AB-FIX-002]
previous_state: in_review
state_transition_reason: "All quality gates passed - completion approved"
completed_location: tasks/completed/TASK-AB-FIX-003/
---

# Task: Handle Unrecoverable Errors in AutoBuild Loop Phase

## Description

Add logic to the AutoBuild loop phase to check for unrecoverable errors and exit immediately instead of retrying. This is a companion to TASK-AB-FIX-002 which adds error classification.

**Root Cause (from TASK-GR-REV-001):**

The current loop phase blindly retries all failures:
```python
for turn in range(start_turn, self.max_turns + 1):
    player_result = self._invoke_player_safely(...)

    if not player_result.success:
        # Just increments turn and retries - no classification check!
        continue
```

This wastes 25 turns (90% of build time) on errors that can never be resolved.

**Solution:**

Check the `unrecoverable` flag in the player result and exit immediately when set.

## Acceptance Criteria

- [x] Add unrecoverable error check after player invocation in loop phase
- [x] Return `TurnRecord` with `decision: "error"` when detected
- [x] Log clear message about unrecoverable error
- [x] Include turn count in result for debugging
- [x] Add unit tests for unrecoverable error handling
- [x] Verify normal retry behavior still works for recoverable errors

## Implementation Summary

### Changes Made

#### File 1: `guardkit/orchestrator/autobuild.py` (lines 1095-1115)

Added unrecoverable error check in `_execute_turn` method, immediately after player invocation failure and BEFORE state recovery attempt:

```python
# Check for unrecoverable error first - exit immediately without retry (TASK-AB-FIX-003)
is_unrecoverable = player_result.report.get("unrecoverable", False)

if is_unrecoverable:
    # Unrecoverable error - fail immediately without state recovery
    logger.error(
        f"Unrecoverable error detected for {task_id} turn {turn}: {player_result.error}"
    )
    self._progress_display.complete_turn(
        "error",
        f"Unrecoverable error: {player_result.error}",
        error=player_result.error,
    )
    return TurnRecord(
        turn=turn,
        player_result=player_result,
        coach_result=None,
        decision="error",
        feedback=None,
        timestamp=timestamp,
    )
```

#### File 2: `tests/unit/test_autobuild_orchestrator.py`

Added new `TestUnrecoverableErrors` class with 3 comprehensive tests:
1. `test_execute_turn_handles_unrecoverable_error` - Verifies immediate exit without Coach invocation
2. `test_execute_turn_skips_state_recovery_for_unrecoverable` - Verifies state recovery is NOT called
3. `test_execute_turn_uses_state_recovery_for_recoverable` - Verifies normal behavior preserved

## Test Results

All 8 related tests pass:
- ✅ TestUnrecoverableErrors::test_execute_turn_handles_unrecoverable_error
- ✅ TestUnrecoverableErrors::test_execute_turn_skips_state_recovery_for_unrecoverable
- ✅ TestUnrecoverableErrors::test_execute_turn_uses_state_recovery_for_recoverable
- ✅ TestPlayerErrorClassification::test_invoke_player_safely_unrecoverable_error
- ✅ TestPlayerErrorClassification::test_invoke_player_safely_recoverable_error
- ✅ TestPlayerErrorClassification::test_invoke_player_safely_plan_not_found_is_unrecoverable
- ✅ TestPlayerErrorClassification::test_invoke_player_safely_state_validation_error_is_unrecoverable
- ✅ TestCoachValidatorPathConstruction::test_execute_turn_passes_worktree_to_coach

## Quality Gates

| Gate | Threshold | Result |
|------|-----------|--------|
| Compilation | 100% | ✅ PASS |
| Tests Pass | 100% | ✅ PASS (8/8) |
| Architectural Review | ≥60/100 | ✅ PASS (92/100) |
| Code Review | Approved | ✅ PASS (9/10) |

## Files Modified

1. `guardkit/orchestrator/autobuild.py` - Added unrecoverable check in `_execute_turn`
2. `tests/unit/test_autobuild_orchestrator.py` - Added 3 new tests

## Completion Notes

**Duration**: ~45 minutes (estimated: 45 minutes)
**Complexity**: 3/10 (simple conditional check with tests)
**Lines Changed**: +21 implementation, +144 tests

This task completes the error handling improvement chain started by TASK-GR-REV-001:
- TASK-AB-FIX-001: State bridge context fix ✅
- TASK-AB-FIX-002: Error classification in `_invoke_player_safely` ✅
- TASK-AB-FIX-003: Loop phase handling of unrecoverable errors ✅

## References

- [TASK-GR-REV-001 Review Report](.claude/reviews/TASK-GR-REV-001-review-report.md) - Recommendation 2B
- TASK-AB-FIX-002 - Prerequisite: Error classification in `_invoke_player_safely()` ✅ COMPLETE
- TASK-AB-FIX-001 - Related fix for state bridge context ✅ COMPLETE
