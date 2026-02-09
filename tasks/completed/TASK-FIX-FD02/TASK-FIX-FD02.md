---
id: TASK-FIX-FD02
title: Unify capture_turn_state client storage with thread loaders
status: completed
created: 2026-02-09T22:00:00Z
updated: 2026-02-09T23:05:00Z
completed: 2026-02-09T23:05:00Z
completed_location: tasks/completed/TASK-FIX-FD02/
priority: high
tags: [fix, graphiti, threading, cross-loop, capture-turn-state, dual-storage]
task_type: implementation
complexity: 4
feature: null
parent_review: TASK-REV-B9E1
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-09T23:00:00Z
  tests_passed: 32
  tests_failed: 0
---

# Task: Unify capture_turn_state Client Storage with Thread Loaders

## Description

Fix BUG-3 from TASK-REV-B9E1: `_capture_turn_state()` and `_get_thread_local_loader()` use two independent client storage mechanisms, causing redundant Neo4j client creation and cross-loop errors on every capture call in worker threads.

### Problem (BUG-3: Dual Client Storage)

Two separate storage paths exist in `AutoBuildOrchestrator`:

1. **`_get_thread_local_loader()`** (autobuild.py:2652-2674):
   - Creates client via `self._factory.create_client()` + `loop.run_until_complete(client.initialize())`
   - Client is initialized on the worker thread's actual event loop (correct)
   - Stores in `self._thread_loaders[thread_id]` (a Python dict)

2. **`_capture_turn_state()`** (autobuild.py:2419-2421):
   - Gets client via `self._factory.get_thread_client()`
   - `get_thread_client()` uses `threading.local()` storage (`self._thread_local.client`)
   - This is **independent** from `_thread_loaders` — the correctly-initialized client is invisible

When `_capture_turn_state` calls `get_thread_client()` and finds no client in thread-local storage, it creates a new one via `asyncio.run()` (graphiti_client.py:1479). This:
1. Creates a temporary event loop for initialization
2. Initializes the Neo4j driver (bound to the temporary loop)
3. Destroys the temporary loop
4. Returns the client (Neo4j driver now bound to a dead loop)

Then `_capture_turn_state` at line 2427 calls `asyncio.get_event_loop()` → gets the worker thread's actual loop (different from the dead one) → `loop.run_until_complete()` → Neo4j driver creates futures on the dead loop → **cross-loop error**.

### Solution

**Option A (Recommended)**: Retrieve the Graphiti client from `_thread_loaders` in `_capture_turn_state()`:

```python
# In _capture_turn_state(), replace lines 2419-2424:
graphiti = None
if self._factory is not None:
    thread_id = threading.get_ident()
    loader = self._thread_loaders.get(thread_id)
    if loader is not None and loader.graphiti is not None:
        graphiti = loader.graphiti
if graphiti is None:
    # Fallback to module-level get_graphiti() for non-factory usage
    graphiti = get_graphiti()
```

**Option B**: Register the client in both storage mechanisms by having `_get_thread_local_loader()` call `self._factory.set_thread_client(client)` after initialization. This keeps the existing `_capture_turn_state` code unchanged but couples the two storage mechanisms.

**Recommendation**: Option A — it's simpler, eliminates the redundant client creation entirely, and doesn't require changes to the factory API.

## Acceptance Criteria

- [x] `_capture_turn_state()` retrieves its Graphiti client from `self._thread_loaders` (same storage as `_get_thread_local_loader`)
- [x] No more redundant `get_thread_client()` call creating a second Neo4j client per thread
- [x] No more cross-loop errors in capture_turn_state (verified by checking no `asyncio.run()` in the capture path)
- [x] Fallback to `get_graphiti()` preserved for non-factory usage (backward compatibility)
- [x] Graceful degradation when `_thread_loaders` has no entry for current thread
- [x] Unit tests: verify client is retrieved from thread_loaders, verify no factory.get_thread_client() call, verify fallback path
- [x] No regressions in existing `TestTurnStateCapture` tests (12 tests)
- [x] No regressions in existing `TestPerThreadGraphiti` tests (20 tests, was 16 before FD02 additions)

## Key Files

- `guardkit/orchestrator/autobuild.py` — Lines 2419-2424 in `_capture_turn_state()`
- `tests/unit/test_autobuild_orchestrator.py` — Existing tests + new tests

## Context

- Review: TASK-REV-B9E1 (P1 fix, BUG-3)
- Review report: `.claude/reviews/TASK-REV-B9E1-review-report.md` Section 7a
- Related: TASK-FIX-GTP2 (original per-thread migration) and TASK-FIX-GTP3 (capture_turn_state scheduling fix)
- The dual storage emerged because GTP2 added `_thread_loaders` for Player/Coach context, while `_capture_turn_state` was independently using `get_thread_client()` (GTP3 changed scheduling but kept the same client retrieval)

## Dependencies

None — independent of TASK-FIX-FD01, can be done in parallel.
