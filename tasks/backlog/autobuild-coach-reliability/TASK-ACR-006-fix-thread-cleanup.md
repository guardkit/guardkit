---
id: TASK-ACR-006
title: "Fix thread-safe Graphiti client cleanup"
status: backlog
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T10:00:00Z
priority: high
task_type: feature
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-ACR-005
tags: [autobuild, asyncio, thread-safety, cleanup, f3-fix]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix thread-safe Graphiti client cleanup

## Description

Replace `_cleanup_thread_loaders()` in `autobuild.py` which currently creates a new event loop on the main thread and tries to close Graphiti clients bound to worker thread loops. This causes `RuntimeError: asyncio.locks.Lock is bound to a different event loop`.

Use the stored loop references from TASK-ACR-005 to close each client on its original loop.

## Files to Modify

- `guardkit/orchestrator/autobuild.py` — `_cleanup_thread_loaders()`

## Acceptance Criteria

- [ ] AC-001: Uses stored event loop reference for each thread's loader (from TASK-ACR-005)
- [ ] AC-002: If original loop is still running, schedules close on it
- [ ] AC-003: If original loop is closed, uses `asyncio.run()` (Python 3.10+) for cleanup
- [ ] AC-004: Catches and suppresses `RuntimeError` for already-closed loops without blocking other cleanups
- [ ] AC-005: Cleanup has a timeout (30s) to prevent indefinite hanging
- [ ] AC-006: Zero `RuntimeError: no running event loop` errors in test execution
- [ ] AC-007: Zero `Lock is bound to a different event loop` errors in test execution
- [ ] AC-008: Unit test simulates cross-thread cleanup and verifies no errors

## Implementation Notes

```python
def _cleanup_thread_loaders(self):
    for tid, (loader, original_loop) in _thread_loaders.items():
        if loader is None:
            continue
        try:
            if original_loop.is_running():
                # Schedule close on the original loop
                future = asyncio.run_coroutine_threadsafe(
                    loader.graphiti.close(), original_loop
                )
                future.result(timeout=30)
            elif not original_loop.is_closed():
                original_loop.run_until_complete(loader.graphiti.close())
            else:
                # Loop already closed - use fresh loop
                asyncio.run(loader.graphiti.close())
        except Exception as e:
            logger.warning("Cleanup error for thread %d: %s", tid, e)
```
