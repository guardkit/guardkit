---
id: TASK-DMRF-002
title: Improve state recovery has_work logic
status: backlog
task_type: implementation
created: 2026-01-25T17:00:00Z
priority: high
complexity: 2
parent_review: TASK-REV-3EC5
feature_id: FEAT-DMRF
wave: 1
implementation_mode: task-work
dependencies: []
tags: [autobuild, state-recovery, robustness]
---

# Task: Improve state recovery has_work logic

## Description

Fix the `has_work` logic in state recovery to correctly identify work when a Player report exists, even if `files_modified` and `files_created` are empty arrays.

## Problem

State recovery successfully loads the Player report, but then `has_work` returns False because:
- `files_modified` is empty
- `files_created` is empty
- `test_count` is 0

This causes valid work to be discarded.

**Evidence from logs**:
```
INFO:state_tracker:Loaded Player report from .../player_turn_1.json  # SUCCESS
INFO:autobuild:No work detected in .../worktrees/FEAT-F392           # PARADOX
```

## Acceptance Criteria

- [ ] Modify `WorkState.has_work` to return True if Player report was loaded successfully
- [ ] Add `player_report_loaded` flag to WorkState
- [ ] Update `MultiLayeredStateTracker.capture_state()` to set this flag
- [ ] When Player report exists, trust its contents even if file arrays are empty
- [ ] Add unit tests for the new logic

## Implementation Notes

**Files to modify**:
- `guardkit/orchestrator/state_tracker.py`
- `guardkit/orchestrator/state_detection.py`

**Suggested approach**:

```python
@dataclass
class WorkState:
    # ... existing fields ...
    player_report_loaded: bool = False

    @property
    def has_work(self) -> bool:
        # If we loaded a Player report, trust it
        if self.player_report_loaded:
            return True

        # Otherwise, fall back to file/test detection
        return (
            len(self.files_modified) > 0 or
            len(self.files_created) > 0 or
            self.test_count > 0
        )
```

## Testing

1. Create WorkState with `player_report_loaded=True` but empty file arrays
2. Verify `has_work` returns True
3. Verify backward compatibility when flag is False

## Related Files

- `guardkit/orchestrator/state_tracker.py` - Main implementation
- `guardkit/orchestrator/state_detection.py` - Detection logic
- `tests/unit/orchestrator/test_state_tracker.py` - Tests
