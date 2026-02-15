---
id: TASK-ACR-007
title: "Fix event loop handling in turn state capture"
status: backlog
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T10:00:00Z
priority: high
task_type: feature
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-ACR-005
tags: [autobuild, asyncio, turn-state, f3-fix]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix event loop handling in turn state capture

## Description

Replace the fragile `asyncio.get_event_loop()` pattern in `_capture_turn_state()` with a robust approach that uses the stored thread-local loop reference or creates a properly scoped temporary loop.

## Files to Modify

- `guardkit/orchestrator/autobuild.py` — `_capture_turn_state()` (~line 2628)

## Acceptance Criteria

- [ ] AC-001: Uses thread-local loader's stored loop reference if available (from TASK-ACR-005)
- [ ] AC-002: If no loop available, creates a fresh one with `asyncio.new_event_loop()` scoped to the operation
- [ ] AC-003: Temporary loops are always cleaned up after use (try/finally)
- [ ] AC-004: Timeout of 30s to prevent blocking the main loop
- [ ] AC-005: No `asyncio.get_event_loop()` calls remain in `_capture_turn_state()`
- [ ] AC-006: Unit test verifies turn state capture works after worker loop cleanup

## Implementation Notes

```python
def _capture_turn_state(self, ...):
    # Get stored loop for this thread
    tid = threading.get_ident()
    loader, stored_loop = _thread_loaders.get(tid, (None, None))

    if stored_loop and not stored_loop.is_closed():
        loop = stored_loop
        created_loop = False
    else:
        loop = asyncio.new_event_loop()
        created_loop = True

    try:
        result = loop.run_until_complete(
            asyncio.wait_for(self._async_capture(...), timeout=30)
        )
    finally:
        if created_loop:
            loop.close()
```
