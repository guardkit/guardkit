---
id: TASK-FIX-GTP1
title: Create thread-safe Graphiti client factory
status: completed
created: 2026-02-09T14:00:00Z
updated: 2026-02-09T18:30:00Z
completed: 2026-02-09T18:30:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed, code review approved"
priority: critical
tags: [fix, graphiti, threading, singleton, factory, parallel]
task_type: implementation
complexity: 6
feature: FEAT-C90E
test_results:
  status: passed
  coverage: 44
  tests_passed: 100
  tests_failed: 0
  tests_skipped: 2
  last_run: 2026-02-09T18:00:00Z
---

# Task: Create Thread-Safe Graphiti Client Factory

## Description

Replace the module-level Graphiti singleton pattern in `guardkit/knowledge/graphiti_client.py` with a thread-safe client factory that creates per-thread `GraphitiClient` instances. This is the root cause fix for BUG-1 identified in the TASK-REV-2AA0 review.

### Problem

The current singleton pattern (`get_graphiti()` → `_graphiti: Optional[GraphitiClient]`) creates a single `GraphitiClient` whose internal Neo4j driver and OpenAI embedder are bound to one event loop. When `FeatureOrchestrator` runs tasks in parallel via `asyncio.to_thread()`, each worker thread creates its own event loop. The shared singleton's Neo4j driver raises cross-loop errors, which propagate through graphiti-core's unguarded `asyncio.gather()` (no `return_exceptions=True`), causing non-deterministic hangs.

See: `.claude/reviews/TASK-REV-2AA0-review-report.md` (BUG-1: Shared Graphiti Singleton Cross-Loop Hang)

### Solution

Introduce a `GraphitiClientFactory` that:
1. Stores configuration (from `load_graphiti_config()`) at module level (config is thread-safe — frozen dataclass)
2. Creates fresh `GraphitiClient` instances on demand via `create_client()`
3. Manages thread-local client storage via `threading.local()` for `get_thread_client()`
4. Preserves the existing `get_graphiti()` API for backward compatibility (returns a thread-local client)
5. Provides `create_client()` for explicit per-scope client creation

### Design

```python
import threading
from typing import Optional

class GraphitiClientFactory:
    """Thread-safe factory for creating GraphitiClient instances.

    Stores shared configuration and creates per-thread clients.
    Each client gets its own Neo4j driver and OpenAI embedder,
    bound to whatever event loop is current in the calling thread.
    """

    def __init__(self, config: GraphitiConfig):
        self._config = config  # Frozen dataclass, thread-safe
        self._thread_local = threading.local()

    def create_client(self) -> GraphitiClient:
        """Create a new GraphitiClient (not yet initialized).

        Caller is responsible for calling await client.initialize()
        in the appropriate async context.
        """
        return GraphitiClient(self._config)

    async def create_and_init_client(self) -> Optional[GraphitiClient]:
        """Create and initialize a new GraphitiClient.

        Returns None if initialization fails.
        """
        client = self.create_client()
        success = await client.initialize()
        return client if success else None

    def get_thread_client(self) -> Optional[GraphitiClient]:
        """Get or lazily create a client for the current thread.

        Uses threading.local() for automatic per-thread storage.
        Returns None if factory config is disabled or init fails.
        """
        client = getattr(self._thread_local, 'client', None)
        if client is not None:
            return client
        # Lazy init for this thread
        ...


# Module-level factory (replaces _graphiti singleton)
_factory: Optional[GraphitiClientFactory] = None

def get_graphiti() -> Optional[GraphitiClient]:
    """Get a Graphiti client for the current thread.

    Backward-compatible API. Now returns a thread-local client
    instead of a shared singleton.
    """
    if _factory is None:
        _try_lazy_init_factory()
    if _factory is not None:
        return _factory.get_thread_client()
    return None

def get_factory() -> Optional[GraphitiClientFactory]:
    """Get the factory for explicit client creation."""
    ...
```

## Acceptance Criteria

- [ ] `GraphitiClientFactory` class created in `graphiti_client.py`
- [ ] `create_client()` returns a new uninitialized `GraphitiClient`
- [ ] `create_and_init_client()` returns initialized client or None
- [ ] `get_thread_client()` returns per-thread client via `threading.local()`
- [ ] `get_graphiti()` backward-compatible — returns thread-local client
- [ ] `get_factory()` exposed for explicit factory access
- [ ] `init_graphiti()` updated to create factory instead of singleton
- [ ] `_try_lazy_init()` updated to create factory
- [ ] Old `_graphiti` singleton variable removed
- [ ] Thread-local clients initialized lazily (only when first accessed from a thread)
- [ ] Config validation unchanged (frozen `GraphitiConfig` dataclass)
- [ ] All existing tests pass (update mocks to patch factory instead of singleton)
- [ ] New tests for thread-safety: concurrent `get_thread_client()` from multiple threads
- [ ] New test: different threads get different client instances
- [ ] New test: same thread gets same client instance (cached)
- [ ] New test: `create_client()` always returns fresh instance

## Key Files

### Must Modify
- `guardkit/knowledge/graphiti_client.py` — Core change: add factory, update singleton functions

### Must Update Tests
- `tests/unit/test_graphiti_client.py` — Existing singleton tests
- `tests/unit/test_graphiti_lazy_init.py` — Lazy init tests (TASK-FIX-GCW6)
- `tests/unit/test_graphiti_client_lifecycle.py` — Lifecycle tests (TASK-FIX-GCI0)

### Reference
- `.claude/reviews/TASK-REV-2AA0-review-report.md` — Root cause analysis and fix recommendations
- `docs/reviews/graphiti_baseline/graphiti_docs_index.md` — Graphiti documentation index

## Context

- Root cause: TASK-REV-2AA0 BUG-1 (shared singleton cross-loop hang)
- Prerequisite for: TASK-FIX-GTP2 (AutoBuild migration), TASK-FIX-GTP5 (call site migration)
- Related: TASK-FIX-GCW6 (lazy-init), TASK-FIX-GCI0 (lifecycle fixes)
- 36 production call sites across 18 files depend on `get_graphiti()`

## Implementation Notes

### Key Constraints
1. `GraphitiConfig` is already a frozen dataclass — safe to share across threads
2. `GraphitiClient.__init__()` takes a config but doesn't connect — connection happens in `initialize()`
3. `initialize()` is async — creates Neo4j driver + OpenAI embedder bound to the current event loop
4. Each worker thread in `FeatureOrchestrator` creates its own event loop via `asyncio.new_event_loop()`
5. Thread-local init must happen in the thread's event loop context (via `loop.run_until_complete()`)

### Backward Compatibility
- `get_graphiti()` must continue to work unchanged for all 24 LOW-risk main-thread call sites
- Single-threaded usage (CLI commands, non-parallel AutoBuild) should see no behavior change
- The factory is transparent — callers still get a `GraphitiClient` instance

## Completion Summary

### Files Modified (5)
- `guardkit/knowledge/graphiti_client.py` — Added `GraphitiClientFactory` class (~115 lines), replaced module-level `_graphiti` singleton with `_factory` + `_factory_init_attempted`, rewrote `init_graphiti()`, `_try_lazy_init()`, `get_graphiti()`, added `get_factory()`
- `guardkit/knowledge/__init__.py` — Added `GraphitiClientFactory`, `get_factory` to imports and `__all__`
- `tests/knowledge/conftest.py` — Updated `reset_graphiti_singleton` autouse fixture from `_graphiti` to `_factory`/`_factory_init_attempted`
- `tests/knowledge/test_graphiti_client.py` — Updated `TestSingletonPattern` class for factory API
- `tests/knowledge/test_graphiti_lazy_init.py` — Full rewrite for factory pattern

### Files Created (1)
- `tests/knowledge/test_graphiti_client_factory.py` — 16 thread-safety tests (factory creation, thread-local client, multi-thread isolation, async init, get_factory)

### Quality Gates
| Gate | Result |
|------|--------|
| Compilation | PASS |
| Tests | 100 passed, 2 skipped, 0 failed |
| Regressions | 0 (18/18 GCI0 lifecycle tests passing) |
| Coverage (new code) | >85% (3 lines uncovered — generic exception handler) |
| Code Review | APPROVED (3 low-priority suggestions, no blockers) |
| Plan Audit | 0 scope violations |

### Acceptance Criteria Status
- [x] `GraphitiClientFactory` class created in `graphiti_client.py`
- [x] `create_client()` returns a new uninitialized `GraphitiClient`
- [x] `create_and_init_client()` returns initialized client or None
- [x] `get_thread_client()` returns per-thread client via `threading.local()`
- [x] `get_graphiti()` backward-compatible — returns thread-local client
- [x] `get_factory()` exposed for explicit factory access
- [x] `init_graphiti()` updated to create factory instead of singleton
- [x] `_try_lazy_init()` updated to create factory
- [x] Old `_graphiti` singleton variable removed
- [x] Thread-local clients initialized lazily (only when first accessed from a thread)
- [x] Config validation unchanged (frozen `GraphitiConfig` dataclass)
- [x] All existing tests pass (update mocks to patch factory instead of singleton)
- [x] New tests for thread-safety: concurrent `get_thread_client()` from multiple threads
- [x] New test: different threads get different client instances
- [x] New test: same thread gets same client instance (cached)
- [x] New test: `create_client()` always returns fresh instance
