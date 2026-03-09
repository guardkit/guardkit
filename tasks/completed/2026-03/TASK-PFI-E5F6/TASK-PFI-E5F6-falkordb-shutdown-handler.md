---
id: TASK-PFI-E5F6
title: Add FalkorDB connection pool shutdown handler
status: completed
created: 2026-03-09T21:10:00Z
updated: 2026-03-09T22:20:00Z
completed: 2026-03-09T22:20:00Z
priority: low
tags: [autobuild, falkordb, graphiti, shutdown, error-handling]
complexity: 2
parent_review: TASK-REV-D326
feature_id: FEAT-PFI
wave: 2
implementation_mode: direct
dependencies: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
completed_location: tasks/completed/2026-03/TASK-PFI-E5F6/
---

# Task: Add FalkorDB Connection Pool Shutdown Handler

## Description

The post-fix FEAT-2AAA run surfaced 2 ERROR-level logs during shutdown:

```
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Buffer is closed.
ERROR:asyncio:Task exception was never retrieved
  redis.exceptions.RedisError: Buffer is closed.
```

Root cause: graphiti-core schedules `build_indices_and_constraints()` as a fire-and-forget background task during `add_episode()`. When the main event loop shuts down, the Redis connection pool closes before this task completes.

## Acceptance Criteria

- [x] FalkorDB background tasks (`build_indices_and_constraints`) are cancelled gracefully before connection pool shutdown
- [x] No `Buffer is closed` ERROR-level logs during normal shutdown
- [x] No impact on FalkorDB operations during normal execution
- [x] Test: verify clean shutdown with and without pending FalkorDB tasks

## Implementation Summary

### Changes Made

**`guardkit/knowledge/graphiti_client.py`**:

1. **Enhanced `close()`** — Calls `_cancel_pending_background_tasks()` before closing connection pool
2. **Added `_cancel_pending_background_tasks()`** — Best-effort cancellation of graphiti-core background tasks
3. **Added `_is_graphiti_background_task()`** — Identifies tasks by source filename and task name
4. **Extended `_suppress_httpx_cleanup_errors()`** — Also suppresses `RedisError("Buffer is closed.")`
5. **Added `_is_redis_buffer_closed()`** — String-based type check, no hard redis dependency

### Tests Added (13 new tests)

- `TestCloseWithBackgroundTasks` (3 tests) in `test_graphiti_client.py`
- `TestFalkorDBShutdownErrorSuppression` (2 tests) in `test_graphiti_client_factory.py`
- `TestIsRedisBufferClosed` (6 tests) in `test_graphiti_client_factory.py`
- `TestIsGraphitiBackgroundTask` (2 tests) in `test_graphiti_client_factory.py`

### Quality Gates

- Compilation: ✅
- Tests: 116/116 passing (100%)
