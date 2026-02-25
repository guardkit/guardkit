---
id: TASK-FIX-ASPF-003
title: Fix misleading "not found" log when error key present
status: completed
task_type: implementation
created: 2026-02-24T23:00:00Z
completed: 2026-02-25T00:00:00Z
priority: high
tags: [coach-validator, logging, debugging]
complexity: 1
parent_review: TASK-REV-953F
feature_id: FEAT-ASPF
wave: 1
implementation_mode: direct
dependencies: []
completed_location: tasks/completed/TASK-FIX-ASPF-003/
---

# Task: Fix misleading "not found" log when error key present

## Description

In `coach_validator.py:585-586`, the log message says "Task-work results not found" when the file actually EXISTS but contains an `"error"` key. This misdirects debugging efforts.

## Current Code

```python
# coach_validator.py:585-586
if "error" in task_work_results:
    logger.warning(f"Task-work results not found for {task_id}")
```

## Fix

```python
if "error" in task_work_results:
    logger.warning(
        f"Task-work results for {task_id} contain error: "
        f"{task_work_results.get('error', 'unknown')}"
    )
```

## Files Modified

- `guardkit/orchestrator/quality_gates/coach_validator.py` — line 585-589

## Acceptance Criteria

1. Log message accurately describes the condition (error key present, not file missing) ✅
2. Error message from task_work_results is included in the log ✅
3. Existing tests still pass (230 passed) ✅
