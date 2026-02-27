---
id: TASK-FIX-CDF8
title: Fix "Critical error: None" cancellation display
status: completed
task_type: implementation
priority: medium
tags: [autobuild, display, bugfix, p1]
complexity: 2
parent_review: TASK-REV-5610
feature_id: FEAT-FF93
wave: 2
implementation_mode: direct
dependencies: []
completed: 2026-02-27T00:00:00Z
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-27T00:00:00Z
---

# Task: Fix "Critical error: None" Cancellation Display

## Description

When a task is cancelled due to timeout, the autobuild summary displays `Critical error: None` which is misleading. The cancellation path doesn't populate the error message field, so `None` is rendered.

Fix the summary rendering in `autobuild.py` to detect `decision="cancelled"` and display a meaningful message like "Task timed out (cancelled)" instead.

## Root Cause

In the autobuild summary rendering, the code displays `result.error` which is `None` for cancelled tasks. The cancellation is a deliberate timeout, not an error, but the display logic treats all non-success outcomes as errors.

## Implementation

In `autobuild.py` summary rendering:

```python
# When displaying task result:
if result.decision == "cancelled":
    error_display = "Task timed out (cancelled)"
elif result.error:
    error_display = f"Critical error: {result.error}"
else:
    error_display = None
```

## Acceptance Criteria

- [x] Cancelled tasks display "Task timed out (cancelled)" instead of "Critical error: None"
- [x] Actual critical errors still display correctly with the error message
- [x] Summary output is clear and actionable for debugging

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/autobuild.py` | Fix summary rendering for cancelled tasks |

## Risk Assessment

**Risk**: None — display-only change, no behavioural impact
