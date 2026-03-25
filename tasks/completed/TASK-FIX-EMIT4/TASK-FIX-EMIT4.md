---
id: TASK-FIX-EMIT4
title: Fix JSONLFileBackend asyncio.Lock cross-event-loop error
status: completed
created: 2026-03-20T23:30:00Z
updated: 2026-03-20T23:45:00Z
completed: 2026-03-20T23:45:00Z
completed_location: tasks/completed/TASK-FIX-EMIT4/
priority: low
tags: [autobuild, instrumentation, emitter, threading, P2]
parent_review: TASK-REV-8BC0
feature_id: FEAT-8BC0
implementation_mode: direct
wave: 2
complexity: 2
---

# Task: Fix JSONLFileBackend Cross-Event-Loop Lock Error

## Description

`JSONLFileBackend` at `emitter.py:165` creates an `asyncio.Lock()` that is bound to the main event loop. When parallel tasks run in worker threads (via `asyncio.to_thread()`), each thread creates its own event loop. Calling `emitter.flush()` or `emitter.emit()` from a worker thread fails with: `"<asyncio.locks.Lock object> is bound to a different event loop"`.

This causes telemetry data loss for parallel tasks and the 300-second executor join timeout warning.

## Acceptance Criteria

- [x] Replace `asyncio.Lock` with `threading.Lock` in `JSONLFileBackend.__init__()` at `emitter.py:165`
- [x] Update `emit()` and `flush()` methods to use synchronous lock acquisition (since file writes are fast and the lock is only held briefly)
- [x] Verify no other code depends on the lock being an asyncio.Lock
- [ ] Parallel task instrumentation events are persisted correctly
- [ ] The executor join timeout warning no longer appears in parallel execution logs

## Key Files

- `guardkit/orchestrator/instrumentation/emitter.py` (lines 143-206)

## Notes

Minimal change with clear scope. The `asyncio.Lock` was chosen for async coroutine safety, but since the backend is used across threads, `threading.Lock` is the correct primitive. The `emit()` and `flush()` methods will need to become synchronous or use `loop.run_in_executor()` — but since they only do fast file I/O under the lock, synchronous is simpler.
