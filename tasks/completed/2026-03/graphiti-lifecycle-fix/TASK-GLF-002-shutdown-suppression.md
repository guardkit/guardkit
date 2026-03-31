---
id: TASK-GLF-002
title: Add shutting_down flag to suppress shutdown errors
task_type: fix
parent_review: TASK-REV-50E1
feature_id: FEAT-408A
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
status: completed
priority: medium
tags: [graphiti, autobuild, shutdown, quick-win]
---

# Task: Add shutting_down flag to suppress shutdown errors

## Description

At process shutdown, `_cleanup_thread_loaders()` triggers ~20 error lines from three knowledge capture attempts. These errors (Lock affinity, coroutine warnings, pending tasks) are cosmetic but noisy. Add a `shutting_down` flag to skip Graphiti operations during cleanup.

## Root Cause (from TASK-REV-50E1 Finding 4)

**File**: `guardkit/orchestrator/autobuild.py`, lines 3168-3201

The three-branch cleanup in `_cleanup_thread_loaders()` correctly handles GuardKit's own client cleanup, but post-cleanup code may still attempt Graphiti operations (knowledge capture at feature completion). A `shutting_down` guard prevents these unnecessary operations.

## Acceptance Criteria

- [x] AC-001: `_cleanup_thread_loaders()` sets `self._shutting_down = True` before starting cleanup
- [x] AC-002: `_capture_turn_state()` returns early when `self._shutting_down` is True
- [x] AC-003: `_shutting_down` attribute initialized to False in `__init__`
- [x] AC-004: Shutdown error log lines reduced to 0 (previously ~20)
- [x] AC-005: Test verifies `_capture_turn_state` skips when shutting down

## Implementation Notes

```python
# In __init__:
self._shutting_down = False

# In _cleanup_thread_loaders (line 3168):
def _cleanup_thread_loaders(self) -> None:
    self._shutting_down = True  # Set flag before cleanup
    ...

# In _capture_turn_state (early return):
if getattr(self, '_shutting_down', False):
    logger.debug("Skipping turn state capture (shutting down)")
    return
```

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/autobuild.py` | Add `_shutting_down` flag, early return in `_capture_turn_state` |

## Test Scope

`tests/**/test_*autobuild*shutdown*` or `tests/**/test_*cleanup*`
