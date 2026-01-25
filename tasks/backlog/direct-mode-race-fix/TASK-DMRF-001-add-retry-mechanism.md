---
id: TASK-DMRF-001
title: Add retry mechanism to direct mode report loading
status: backlog
task_type: implementation
created: 2026-01-25T17:00:00Z
priority: high
complexity: 3
parent_review: TASK-REV-3EC5
feature_id: FEAT-DMRF
wave: 1
implementation_mode: task-work
dependencies: []
tags: [autobuild, direct-mode, race-condition, robustness]
---

# Task: Add retry mechanism to direct mode report loading

## Description

Add a retry/polling mechanism to the `_invoke_player_direct` method in `agent_invoker.py` to handle the filesystem buffering race condition where the Player report file is written but not immediately visible.

## Problem

The direct mode path writes `player_turn_N.json` via the SDK subprocess, then immediately checks `report_path.exists()`. Due to filesystem buffering, the file may not be visible yet, causing false "report not found" errors.

**Evidence**: State recovery successfully loads the same file milliseconds later.

## Acceptance Criteria

- [ ] Add retry loop with exponential backoff to `_load_agent_report` when called from direct mode
- [ ] Maximum 3 retries with delays of 100ms, 200ms, 400ms
- [ ] Add small delay (100ms) after file write before first read attempt
- [ ] Log retry attempts at DEBUG level
- [ ] Only apply retry logic to direct mode path (not task-work delegation)
- [ ] Add unit tests for retry behavior

## Implementation Notes

**File to modify**: `guardkit/orchestrator/agent_invoker.py`

**Method to modify**: `_invoke_player_direct` (around line 654-665)

**Suggested approach**:

```python
async def _invoke_player_direct(self, task_id, turn, requirements, feedback, max_turns):
    # ... existing SDK invocation ...

    # After writing player report, add delay before loading
    await asyncio.sleep(0.1)  # 100ms for filesystem sync

    # Retry loop for report loading
    max_retries = 3
    for attempt in range(max_retries):
        try:
            report = self._load_agent_report(task_id, turn, "player")
            break
        except PlayerReportNotFoundError:
            if attempt < max_retries - 1:
                delay = 0.1 * (2 ** attempt)  # 100ms, 200ms, 400ms
                logger.debug(f"Report not found, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                raise
```

## Testing

1. Mock `Path.exists()` to return False then True
2. Verify retry happens with correct delays
3. Verify no retry in task-work delegation path
4. Verify exception raised after max retries

## Related Files

- `guardkit/orchestrator/agent_invoker.py` - Main implementation
- `tests/unit/orchestrator/test_agent_invoker.py` - Tests
