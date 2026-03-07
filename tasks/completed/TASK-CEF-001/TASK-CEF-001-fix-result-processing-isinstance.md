---
id: TASK-CEF-001
title: Fix result processing isinstance checks for CancelledError
status: completed
updated: 2026-03-07T15:05:00Z
completed: 2026-03-07T15:05:00Z
completed_location: tasks/completed/TASK-CEF-001/
task_type: implementation
created: 2026-03-07T14:00:00Z
priority: critical
tags: [bug-fix, asyncio, python-3.9-compat, cancelled-error]
complexity: 3
parent_review: TASK-REV-C3F8
feature_id: FEAT-CEF1
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Fix result processing isinstance checks for CancelledError

## Description

Fix the `_execute_wave_parallel` result processing loop in `feature_orchestrator.py` to handle `CancelledError` and other `BaseException` subclasses. Currently, on Python 3.9+, `CancelledError` (a `BaseException`) falls through both `isinstance(result, asyncio.TimeoutError)` and `isinstance(result, Exception)` checks, reaching the `else` branch which assumes a valid `TaskExecutionResult` and crashes with `AttributeError`.

## Requirements

1. Add `isinstance(result, asyncio.CancelledError)` check AFTER `TimeoutError` but BEFORE `Exception`
2. Add `isinstance(result, BaseException)` check AFTER `Exception` to catch `KeyboardInterrupt`, `SystemExit`, etc.
3. Create `TaskExecutionResult` with `final_decision="cancelled"` for CancelledError
4. Create `TaskExecutionResult` with `final_decision="error"` for other BaseException types
5. Update wave display status for cancelled/error results
6. Call `_update_feature()` for all new result types

## Affected Files

- `guardkit/orchestrator/feature_orchestrator.py` — lines 1514-1581 (`_execute_wave_parallel` result processing)

## Acceptance Criteria

- [x] AC-1: `CancelledError` in gather results produces `TaskExecutionResult(success=False, final_decision="cancelled")`
- [x] AC-2: `KeyboardInterrupt` in gather results produces `TaskExecutionResult(success=False, final_decision="error")`
- [x] AC-3: `SystemExit` in gather results produces `TaskExecutionResult(success=False, final_decision="error")`
- [x] AC-4: `TimeoutError` handling unchanged (existing behavior preserved)
- [x] AC-5: `Exception` handling unchanged (existing behavior preserved)
- [x] AC-6: Normal `TaskExecutionResult` handling unchanged
- [x] AC-7: Unit tests cover all 6 result type scenarios
- [x] AC-8: Check order is: TimeoutError → CancelledError → Exception → BaseException → success

## Implementation Hint

```python
# Replace the elif chain at lines 1514-1581:
for task_id, result in zip(task_id_mapping, parallel_results):
    if isinstance(result, asyncio.TimeoutError):
        # ... existing timeout handling (unchanged) ...
    elif isinstance(result, asyncio.CancelledError):
        cancel_msg = f"Task {task_id} was cancelled"
        logger.warning(f"CANCELLED: {task_id} — {cancel_msg}")
        error_result = TaskExecutionResult(
            task_id=task_id, success=False, total_turns=0,
            final_decision="cancelled", error=cancel_msg,
        )
        results.append(error_result)
        if self._wave_display:
            self._wave_display.update_task_status(
                task_id, "cancelled", cancel_msg, turns=0, decision="cancelled"
            )
        self._update_feature(feature, task_id, error_result, wave_number)
    elif isinstance(result, Exception):
        # ... existing exception handling (unchanged) ...
    elif isinstance(result, BaseException):
        error_result = self._create_error_result(task_id, result)
        results.append(error_result)
        if self._wave_display:
            self._wave_display.update_task_status(
                task_id, "failed", "error", turns=0, decision="error"
            )
        self._update_feature(feature, task_id, error_result, wave_number)
    else:
        # ... existing success handling (unchanged) ...
```
