---
id: TASK-AQG-004
title: Fix httpx async client cleanup errors in per-thread Graphiti clients
status: completed
created: 2026-02-10T20:30:00Z
updated: 2026-02-10T22:00:00Z
completed: 2026-02-10T22:00:00Z
priority: low
task_type: feature
tags: [graphiti, asyncio, httpx, cleanup, event-loop]
parent_review: TASK-REV-7972
feature_id: FEAT-AQG
complexity: 3
wave: 2
implementation_mode: task-work
dependencies: []
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met, tests passing"
---

# Task: Fix httpx Async Client Cleanup Errors

## Description

During FEAT-FP-002 Wave 4, two `ERROR:asyncio:Task exception was never retrieved` errors appeared (success log lines 2145-2212). These are `RuntimeError: Event loop is closed` errors from httpx `AsyncClient.aclose()` trying to close connections on an already-closed event loop.

## Root Cause

When `asyncio.run()` is used in `get_thread_client()` to initialize the Graphiti client, it creates a temporary event loop. After `asyncio.run()` completes, the loop is closed. If the Graphiti `add_episode()` call during turn state capture spawns background cleanup tasks (via httpx's connection pooling), those tasks try to close connections on the already-closed loop.

## Implementation Summary

### Changes Made

1. **`guardkit/knowledge/graphiti_client.py`**:
   - Added `_suppress_httpx_cleanup_errors(loop)` function that installs a custom exception handler
   - Handler silences `RuntimeError('Event loop is closed')` from httpx `AsyncClient.aclose()`, passes all other exceptions through
   - Refactored `get_thread_client()` from `asyncio.run()` to `asyncio.new_event_loop()` + `loop.run_until_complete()` + `loop.close()` for explicit loop lifecycle control
   - Applied handler before `run_until_complete()` so it's active during cleanup

2. **`guardkit/orchestrator/autobuild.py`**:
   - Applied `_suppress_httpx_cleanup_errors(loop)` in `_capture_turn_state()` before `loop.run_until_complete()`
   - Updated imports to include `_suppress_httpx_cleanup_errors`

### Tests

- 6 new tests in `TestHttpxCleanupErrorSuppression`:
  - `test_suppresses_event_loop_closed_error`
  - `test_propagates_other_runtime_errors`
  - `test_propagates_non_runtime_errors`
  - `test_propagates_context_without_exception`
  - `test_preserves_original_handler`
  - `test_handler_installed_during_get_thread_client`
- 5 updated tests in `TestUnawaitedCoroutineWarningFix` (adapted to `asyncio.new_event_loop()` approach)
- 27 total factory tests passing
- 18 autobuild turn state capture tests passing
- 0 regressions

## Acceptance Criteria

- [x] AC1: No `ERROR:asyncio:Task exception was never retrieved` errors during normal AutoBuild execution
- [x] AC2: Turn state capture still works correctly
- [x] AC3: No regressions in per-thread Graphiti client tests

## Key Files

- `guardkit/knowledge/graphiti_client.py` (cleanup path)
- `guardkit/orchestrator/autobuild.py` (`_capture_turn_state`)
- `tests/knowledge/test_graphiti_client_factory.py` (verify)
