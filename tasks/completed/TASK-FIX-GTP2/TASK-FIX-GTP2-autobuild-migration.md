---
id: TASK-FIX-GTP2
title: Migrate AutoBuild orchestrator to per-thread Graphiti clients
status: completed
created: 2026-02-09T14:00:00Z
updated: 2026-02-09T16:30:00Z
completed: 2026-02-09T16:30:00Z
completed_location: tasks/completed/TASK-FIX-GTP2/
priority: critical
tags: [fix, graphiti, autobuild, threading, migration]
task_type: implementation
complexity: 5
feature: FEAT-C90E
depends_on: [TASK-FIX-GTP1]
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-09T16:30:00Z
  new_tests: 16
  total_passing: 93
---

# Task: Migrate AutoBuild Orchestrator to Per-Thread Graphiti Clients

## Description

Update `AutoBuildOrchestrator` to create per-thread Graphiti clients instead of sharing the singleton when running in parallel worker threads. This is the primary consumer of the factory from TASK-FIX-GTP1 and directly fixes the cross-loop hang observed in the FEAT-6EDD AutoBuild run.

See: `.claude/reviews/TASK-REV-2AA0-review-report.md` (Fix 1, Option A: Thread-local Graphiti clients)

### Current Flow (Broken in Parallel)

1. `AutoBuildOrchestrator.__init__()` calls `get_graphiti()` → returns singleton
2. Creates `AutoBuildContextLoader(graphiti=singleton_client)`
3. `_invoke_player_safely()` creates a thread-local event loop
4. Calls `loop.run_until_complete(self._context_loader.get_player_context(...))`
5. Singleton's Neo4j driver bound to init loop → cross-loop error → potential hang

### New Flow (Per-Thread)

1. `AutoBuildOrchestrator.__init__()` stores factory reference (or gets it from `get_factory()`)
2. `_invoke_player_safely()` creates a thread-local event loop
3. Gets/creates a thread-local Graphiti client via factory
4. Creates a thread-local `AutoBuildContextLoader` with the thread-local client
5. Calls `loop.run_until_complete(thread_loader.get_player_context(...))`
6. Neo4j driver initialized on THIS thread's loop → no cross-loop issues

### Key Call Sites in AutoBuild

| Location | Line | Current | New |
|----------|------|---------|-----|
| `__init__()` | ~597 | `get_graphiti()` singleton | Store factory ref |
| `_invoke_player_safely()` | ~2661 | `self._context_loader` (shared) | Thread-local loader |
| `_invoke_coach_safely()` | ~2700 | `self._context_loader` (shared) | Thread-local loader |
| `_capture_turn_state()` | ~2409 | `get_graphiti()` singleton | Thread-local client (see also GTP3) |

## Acceptance Criteria

- [x] `AutoBuildOrchestrator.__init__()` no longer calls `get_graphiti()` for the singleton
- [x] Factory reference stored (from `get_factory()` or passed in)
- [x] `_invoke_player_safely()` creates/gets thread-local Graphiti client via factory
- [x] Thread-local `AutoBuildContextLoader` created with thread-local client
- [x] `_invoke_coach_safely()` uses same thread-local pattern
- [x] `_capture_turn_state()` uses thread-local client (coordinate with TASK-FIX-GTP3)
- [x] Single-threaded AutoBuild (non-parallel) still works correctly
- [x] Context loading works in parallel: each worker gets independent context
- [x] Graceful degradation preserved: factory unavailable → no context (not crash)
- [x] Existing AutoBuild tests pass (update mocks for factory pattern)
- [x] New test: parallel workers get independent clients
- [x] New test: context loading succeeds with per-thread clients (mocked Neo4j)

## Key Files

### Must Modify
- `guardkit/orchestrator/autobuild.py` — `__init__()`, `_invoke_player_safely()`, `_invoke_coach_safely()`, `_capture_turn_state()`
- `guardkit/knowledge/autobuild_context_loader.py` — May need minor update for per-thread creation

### Must Update Tests
- `tests/unit/test_autobuild_orchestrator.py` — Mock factory instead of singleton
- `tests/unit/test_autobuild_context_loader.py` — Context loader tests

### Reference
- `.claude/reviews/TASK-REV-2AA0-review-report.md` — Fix 1 Option A
- `docs/reviews/graphiti_baseline/graphiti_docs_index.md` — Graphiti documentation

## Context

- Depends on: TASK-FIX-GTP1 (factory must exist first)
- This is the CRITICAL path fix — directly resolves the parallel hang
- The `AutoBuildContextLoader` wraps `JobContextRetriever` wraps `GraphitiClient` — all need to be per-thread
- `_invoke_player_safely()` already creates a per-thread event loop (lines 2652-2656)
- Can be done in parallel with TASK-FIX-GTP5 (other call sites)

## Implementation Notes

### Thread-Local Pattern

```python
def _get_thread_local_loader(self, loop: asyncio.AbstractEventLoop) -> Optional[AutoBuildContextLoader]:
    """Get or create a context loader for the current thread.

    Creates a fresh GraphitiClient initialized on this thread's event loop,
    then wraps it in an AutoBuildContextLoader.
    """
    if not self.enable_context or self._factory is None:
        return None

    # Thread-local storage for the loader
    thread_id = threading.get_ident()
    if thread_id not in self._thread_loaders:
        client = self._factory.create_client()
        # Initialize on this thread's loop
        success = loop.run_until_complete(client.initialize())
        if success:
            loader = AutoBuildContextLoader(graphiti=client, ...)
            self._thread_loaders[thread_id] = loader
        else:
            self._thread_loaders[thread_id] = None

    return self._thread_loaders.get(thread_id)
```

### Cleanup

Thread-local clients should be closed when the orchestrator completes. Add cleanup in `_finalize_phase()` or a dedicated cleanup method.

## Test Execution Log

[Automatically populated by /task-work]
