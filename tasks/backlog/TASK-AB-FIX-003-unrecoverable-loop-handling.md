---
id: TASK-AB-FIX-003
title: Handle Unrecoverable Errors in AutoBuild Loop Phase
status: backlog
created: 2026-01-31T15:50:00Z
updated: 2026-01-31T15:50:00Z
priority: high
tags: [autobuild, error-handling, fix]
task_type: implementation
parent_review: TASK-GR-REV-001
complexity: 3
depends_on: [TASK-AB-FIX-002]
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

- [ ] Add unrecoverable error check after player invocation in loop phase
- [ ] Return `AutoBuildResult` with `final_decision: "unrecoverable_error"` when detected
- [ ] Log clear message about unrecoverable error
- [ ] Include turn count in result for debugging
- [ ] Add unit tests for unrecoverable error handling
- [ ] Verify normal retry behavior still works for recoverable errors

## Implementation

### File: guardkit/orchestrator/autobuild.py

```python
async def _run_loop_phase(self, task_id: str, ...) -> AutoBuildResult:
    """Run the Player-Coach loop with unrecoverable error handling."""

    for turn in range(start_turn, self.max_turns + 1):
        # Invoke player
        player_result = self._invoke_player_safely(
            task_id=task_id,
            turn=turn,
            requirements=requirements,
            feedback=feedback,
        )

        # Check for unrecoverable error - exit immediately
        if not player_result.success:
            if player_result.report and player_result.report.get("unrecoverable"):
                logger.error(
                    f"Unrecoverable error at turn {turn} for {task_id}: {player_result.error}"
                )
                return AutoBuildResult(
                    task_id=task_id,
                    success=False,
                    final_decision="unrecoverable_error",
                    total_turns=turn,
                    error=player_result.error,
                    metadata={"unrecoverable": True, "stopped_at_turn": turn},
                )

        # ... rest of existing loop logic for recoverable failures ...
```

## Test Requirements

- [ ] Unit test: `test_loop_exits_on_unrecoverable_error`
- [ ] Unit test: `test_loop_continues_on_recoverable_error`
- [ ] Unit test: `test_unrecoverable_result_contains_turn_info`
- [ ] Integration test: Verify with actual PlanNotFoundError scenario

## Files to Modify

1. `guardkit/orchestrator/autobuild.py` - Add unrecoverable check in loop phase
2. `tests/orchestrator/test_autobuild.py` - Add new tests

## References

- [TASK-GR-REV-001 Review Report](.claude/reviews/TASK-GR-REV-001-review-report.md) - Recommendation 2B
- TASK-AB-FIX-002 - Prerequisite: Error classification in `_invoke_player_safely()`
- TASK-AB-FIX-001 - Related fix for state bridge context
