---
id: TASK-FBP-002
title: Add progress heartbeat logging during SDK invocations
status: completed
created: 2025-01-15T12:00:00Z
updated: 2025-01-15T14:45:00Z
completed: 2025-01-15T14:45:00Z
priority: high
tags: [feature-build, performance, ux, logging]
parent_task: TASK-REV-FB14
implementation_mode: task-work
wave: 1
conductor_workspace: feature-build-performance-wave1-heartbeat
complexity: 3
previous_state: in_review
state_transition_reason: All quality gates passed, human review approved
completed_location: tasks/completed/TASK-FBP-002/
---

# Task: Add Progress Heartbeat Logging During SDK Invocations

## Description

Add periodic progress logging during long-running SDK invocations to eliminate the perception of "stalling". Currently, SDK output only appears after completion, making 10-20+ minute operations appear frozen.

## Context

From TASK-REV-FB14 analysis:
- SDK invocations can run 10-20+ minutes
- No output during execution creates perception of "stalling"
- Users cannot assess progress or intervene

## Acceptance Criteria

- [x] Heartbeat logs every 30 seconds during SDK invocations
- [x] Log format: `[TASK-XXX] {phase} in progress... ({N}s elapsed)`
- [x] Heartbeat properly cancelled when SDK completes
- [x] Works for both Player and Coach invocations
- [x] Works for design phase (task-work --design-only) invocations
- [x] Unit tests verify heartbeat timing and cleanup (6 tests added)
- [x] No interference with SDK operation

## Implementation Notes

### Target Files
- `guardkit/orchestrator/agent_invoker.py` - Player/Coach invocations
- `guardkit/orchestrator/quality_gates/task_work_interface.py` - Design phase

### Key Implementation

```python
async def _invoke_with_heartbeat(
    self,
    task_id: str,
    phase: str,
    invoke_coro,
):
    """Wrap SDK invocation with periodic heartbeat logging."""
    async def heartbeat():
        elapsed = 0
        while True:
            await asyncio.sleep(30)
            elapsed += 30
            logger.info(f"[{task_id}] {phase} in progress... ({elapsed}s elapsed)")

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        result = await invoke_coro
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    return result
```

### Usage in invoke_player()

```python
result = await self._invoke_with_heartbeat(
    task_id=task_id,
    phase="Player implementation",
    invoke_coro=self._invoke_task_work_implement(task_id, mode),
)
```

### Test Cases

1. `test_heartbeat_fires_at_interval` - Verify 30s interval
2. `test_heartbeat_cancelled_on_completion` - Verify cleanup
3. `test_heartbeat_cancelled_on_error` - Verify cleanup on exception
4. `test_heartbeat_log_format` - Verify log message format
