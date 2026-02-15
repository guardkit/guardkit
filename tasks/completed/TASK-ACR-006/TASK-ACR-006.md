---
id: TASK-ACR-006
title: "Fix thread-safe Graphiti client cleanup"
status: completed
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T12:30:00Z
completed: 2026-02-15T12:30:00Z
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
  status: passed
  coverage: targeted
  last_run: 2026-02-15T12:30:00Z
  test_count: 17
  pass_count: 17
  fail_count: 0
completed_location: tasks/completed/TASK-ACR-006/
---

# Task: Fix thread-safe Graphiti client cleanup

## Description

Replace `_cleanup_thread_loaders()` in `autobuild.py` which currently creates a new event loop on the main thread and tries to close Graphiti clients bound to worker thread loops. This causes `RuntimeError: asyncio.locks.Lock is bound to a different event loop`.

Use the stored loop references from TASK-ACR-005 to close each client on its original loop.

## Files Modified

- `guardkit/orchestrator/autobuild.py` — `_cleanup_thread_loaders()` + `import concurrent.futures`

## Files Created

- `tests/unit/test_cleanup_thread_safe.py` — 10 tests for three-branch cleanup logic

## Acceptance Criteria

- [x] AC-001: Uses stored event loop reference for each thread's loader (from TASK-ACR-005)
- [x] AC-002: If original loop is still running, schedules close on it
- [x] AC-003: If original loop is closed, uses `asyncio.run()` (Python 3.10+) for cleanup
- [x] AC-004: Catches and suppresses `RuntimeError` for already-closed loops without blocking other cleanups
- [x] AC-005: Cleanup has a timeout (30s) to prevent indefinite hanging
- [x] AC-006: Zero `RuntimeError: no running event loop` errors in test execution
- [x] AC-007: Zero `Lock is bound to a different event loop` errors in test execution
- [x] AC-008: Unit test simulates cross-thread cleanup and verifies no errors

## Implementation Summary

Replaced single-strategy cleanup with three-branch logic based on event loop state:

```python
if stored_loop.is_running():
    future = asyncio.run_coroutine_threadsafe(loader.graphiti.close(), stored_loop)
    future.result(timeout=30)
elif not stored_loop.is_closed():
    stored_loop.run_until_complete(loader.graphiti.close())
else:
    asyncio.run(loader.graphiti.close())
```

Added explicit `RuntimeError` and `concurrent.futures.TimeoutError` suppression.
