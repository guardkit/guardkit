---
id: TASK-CEF-004
title: Add cancellation diagnostics logging
status: completed
task_type: implementation
created: 2026-03-07T14:00:00Z
completed: 2026-03-07T16:00:00Z
completed_location: tasks/completed/TASK-CEF-004/
priority: medium
tags: [diagnostics, logging, asyncio, cancelled-error]
complexity: 2
parent_review: TASK-REV-C3F8
feature_id: FEAT-CEF1
wave: 2
implementation_mode: direct
dependencies: [TASK-CEF-001]
---

# Task: Add cancellation diagnostics logging

## Description

Add detailed cancellation diagnostics logging to `_execute_wave_parallel` so that future `CancelledError` occurrences can be traced to their source. Log the task state, elapsed time, and cancellation context when a `CancelledError` appears in gather results.

## Requirements

1. Log gather start with task IDs and wave number
2. After gather, log any `CancelledError` results with elapsed time and task context
3. Log whether cancellation_event was set at time of error
4. Log whether timeout_event was set at time of error
5. Include the invocation path (task-work vs direct) in diagnostics

## Affected Files

- `guardkit/orchestrator/feature_orchestrator.py` — `_execute_wave_parallel()`, near line 1499 (before gather) and line 1515 (result processing)

## Acceptance Criteria

- [x] AC-1: Gather start logged with wave number and task IDs
- [x] AC-2: CancelledError results include elapsed time since wave start
- [x] AC-3: CancelledError results include cancellation_event state
- [x] AC-4: CancelledError results include timeout_event state
- [x] AC-5: No logging changes for normal success/failure paths

## Implementation Hint

```python
# Before gather (around line 1497):
logger.info(
    f"Starting parallel gather for wave {wave_number}: "
    f"tasks={task_id_mapping}, task_timeout={self.task_timeout}s"
)

# In result processing, after CancelledError isinstance check:
if isinstance(result, asyncio.CancelledError):
    elapsed = time.monotonic() - wave_start_time
    cancel_event_set = cancellation_events.get(task_id, threading.Event()).is_set()
    timeout_event_set = timeout_events.get(task_id, threading.Event()).is_set()
    logger.error(
        f"CANCELLED: {task_id} received CancelledError in wave {wave_number}. "
        f"Elapsed: {elapsed:.1f}s, "
        f"cancellation_event={cancel_event_set}, "
        f"timeout_event={timeout_event_set}. "
        f"CancelledError originated from within worker thread "
        f"(not external cancellation — gather returned results normally)."
    )
```
