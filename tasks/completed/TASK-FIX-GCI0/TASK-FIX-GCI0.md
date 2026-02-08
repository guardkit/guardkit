---
id: TASK-FIX-GCI0
title: Fix Graphiti client lifecycle issues at command integration points
status: completed
task_type: fix
created: 2026-02-08T23:30:00Z
updated: 2026-02-08T23:55:00Z
completed: 2026-02-08T23:55:00Z
priority: critical
parent_review: TASK-REV-C7EB
tags: [graphiti, client-lifecycle, fix, prerequisite]
complexity: 3
wave: 0
dependencies: []
---

# Fix Graphiti Client Lifecycle at Command Integration Points

## CRITICAL: No Stubs Policy

**All code written for this task MUST be fully functional.** No placeholder methods, no TODO comments. Every fix must be verified with tests.

## Background: The GCW6 Lazy-Init Mechanism

TASK-FIX-GCW6 added lazy initialization to `get_graphiti()` so the singleton auto-initializes from config when first accessed. The mechanism in `graphiti_client.py:1429-1524` works as follows:

```python
def get_graphiti() -> Optional[GraphitiClient]:
    """Sync function. Returns initialized client or None."""
    if _graphiti is not None:
        return _graphiti
    if not _graphiti_init_attempted:
        return _try_lazy_init()
    return None

def _try_lazy_init() -> Optional[GraphitiClient]:
    """Attempts initialization. Handles sync/async contexts differently."""
    # ...
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # CASE A: Already in async context — can't use asyncio.run()
        # Creates client but DEFERS connection (self._connected = False)
        _graphiti = client
        return client  # ← client.enabled returns False, self._graphiti is None
    else:
        # CASE B: No running loop — uses asyncio.run(client.initialize())
        # Fully connected client
        success = asyncio.run(client.initialize())
        # ...
```

**The problem**: When `get_graphiti()` is called from a sync `__init__` that happens to be inside an async context (common in async frameworks), the client is created but **never connected**. The `enabled` property returns `False` (it checks `config.enabled AND _connected`), and internal methods like `_execute_search()` and `_create_episode()` check `self._graphiti` (the graphiti-core instance) which is `None` — so operations silently return empty results.

## Three Issues Found

### Issue 1: SYNTAX ERROR — `await` on sync function (graphiti_context_loader.py)

**File**: `installer/core/commands/lib/graphiti_context_loader.py:151`

```python
# CURRENT (BROKEN):
graphiti = await get_graphiti()  # TypeError: get_graphiti() is sync, not async

# FIX:
graphiti = get_graphiti()
```

`get_graphiti()` is a **sync function** returning `Optional[GraphitiClient]`. Using `await` on a non-awaitable raises `TypeError`. This breaks the entire `_get_retriever()` function, which means `load_task_context()` and `load_task_context_sync()` are both non-functional.

**Impact**: Blocks TASK-FIX-GCI1 (wire Graphiti into /task-work). The bridge module is broken as-is.

### Issue 2: Deferred init in InteractiveCaptureSession.__init__ (interactive_capture.py)

**File**: `guardkit/knowledge/interactive_capture.py:98-102`

```python
# CURRENT (VULNERABLE):
def __init__(self):
    self._graphiti = get_graphiti()  # Called in sync __init__
    # If in async context → deferred init → client.enabled = False
    # _save_captured_knowledge() checks self._graphiti is None (passes)
    # but client._graphiti is None → add_episode() returns None silently
```

When `InteractiveCaptureSession` is constructed from an async context (which is the case for both `run_session()` and `run_abbreviated()`), `_try_lazy_init()` enters Case A (deferred connection). The client exists but `_connected = False` and the internal `_graphiti` (graphiti-core instance) is `None`.

The `_save_captured_knowledge()` method at line 343 checks `if self._graphiti is None:` — this passes because the **client object** exists. But when it calls `await client.add_episode()`, the internal `_create_episode()` finds `self._graphiti is None` (the graphiti-core instance) and returns `None`. Knowledge capture silently fails.

**Impact**: Blocks TASK-FIX-GCI2 (run_abbreviated implementation). Even with a working `run_abbreviated()`, captured knowledge won't persist.

### Issue 3: Deferred init in FeaturePlanContextBuilder.__init__ (feature_plan_context.py)

**File**: `guardkit/knowledge/feature_plan_context.py:283-301`

```python
# CURRENT (VULNERABLE):
def __init__(self, project_root: Path):
    from .graphiti_client import get_graphiti
    self.graphiti_client = get_graphiti()  # Same deferred init problem
```

Same pattern as Issue 2. When constructed from async context, `self.graphiti_client` is a deferred client. `build_context()` checks `self.graphiti_client is not None and self.graphiti_client.enabled` — since `enabled` returns `False` (not connected), context enrichment is silently skipped. `seed_feature_spec()` (GCI4) would also silently fail.

**Impact**: Blocks TASK-FIX-GCI4 (feature spec seeding). Also means existing `build_context()` context enrichment silently does nothing when called from async.

## Fixes Required

### Fix 1: Remove `await` from sync function call

```python
# installer/core/commands/lib/graphiti_context_loader.py:151
# BEFORE:
graphiti = await get_graphiti()
# AFTER:
graphiti = get_graphiti()
```

### Fix 2: Lazy property for InteractiveCaptureSession

Replace eager `get_graphiti()` in `__init__` with a lazy property that defers the call to first use (which is always inside an async method that can handle initialization):

```python
# guardkit/knowledge/interactive_capture.py

def __init__(self):
    """Initialize the InteractiveCaptureSession."""
    self._graphiti_client: Optional[Any] = None  # Lazy-initialized
    self._graphiti_resolved = False
    self._analyzer = KnowledgeGapAnalyzer()
    self._captured: List[CapturedKnowledge] = []

@property
def _graphiti(self):
    """Lazy-resolve Graphiti client on first access."""
    if not self._graphiti_resolved:
        self._graphiti_client = get_graphiti()
        self._graphiti_resolved = True
    return self._graphiti_client
```

**Why lazy property, not deferred async init**: The `_save_captured_knowledge()` method and `run_session()` already handle `self._graphiti is None` gracefully. The lazy property just ensures `get_graphiti()` is called at first use rather than construction time, giving the lazy-init mechanism the best chance to fully initialize (if called from sync context) or at least consistently return the client (if called from async context).

**Note**: The deferred-init issue (Case A in `_try_lazy_init`) still applies if the lazy property is first accessed from an async context. However, this is no worse than the current situation, and the existing `_connected` guards ensure graceful degradation. A deeper fix (async-aware initialization) is out of scope for this task.

### Fix 3: Lazy property for FeaturePlanContextBuilder

Same pattern as Fix 2:

```python
# guardkit/knowledge/feature_plan_context.py

def __init__(self, project_root: Path):
    if project_root is None:
        raise TypeError("project_root cannot be None")
    self.project_root = project_root

    from .feature_detector import FeatureDetector
    self.feature_detector = FeatureDetector(project_root)
    self._graphiti_client_resolved = False
    self._graphiti_client_cache: Optional[Any] = None

@property
def graphiti_client(self):
    """Lazy-resolve Graphiti client on first access."""
    if not self._graphiti_client_resolved:
        from .graphiti_client import get_graphiti
        self._graphiti_client_cache = get_graphiti()
        self._graphiti_client_resolved = True
    return self._graphiti_client_cache

@graphiti_client.setter
def graphiti_client(self, value):
    """Allow explicit setting (for testing)."""
    self._graphiti_client_cache = value
    self._graphiti_client_resolved = True
```

**Important**: `graphiti_client` is accessed as an attribute throughout `feature_plan_context.py` (e.g., `self.graphiti_client.search()`). Converting to a property is backwards-compatible — all existing access patterns work unchanged. The setter ensures tests can inject mock clients.

## Broader Context: Why Deferred Init Exists

The `_try_lazy_init()` deferred path (Case A) was a pragmatic choice in GCW6: when `get_graphiti()` is called from inside a running event loop, `asyncio.run()` would raise `RuntimeError`. The client is returned unconnected as a compromise.

For a **full** fix of the async lifecycle, we'd need either:
1. An async `aget_graphiti()` that awaits `client.initialize()` directly
2. A protocol where deferred clients auto-connect on first async operation

This is **out of scope** for this task. The fixes here ensure:
- The syntax error is removed (Issue 1)
- Client resolution is deferred to first use, not constructor time (Issues 2 & 3)
- All existing graceful degradation patterns continue to work

## Acceptance Criteria

- [x] `graphiti_context_loader.py:151` — `await` removed from `get_graphiti()` call
- [x] `interactive_capture.py` — `__init__` no longer calls `get_graphiti()`; lazy property used instead
- [x] `feature_plan_context.py` — `__init__` no longer calls `get_graphiti()`; lazy property used instead
- [x] All existing code that accesses `self._graphiti` (interactive_capture) or `self.graphiti_client` (feature_plan_context) continues to work without changes
- [x] Tests: mock injection still works via constructor or setter
- [x] Tests: lazy property returns `None` when Graphiti unavailable (graceful degradation)
- [x] Tests: lazy property returns client when available
- [x] No regressions in existing tests for interactive_capture or feature_plan_context

## Files to Modify

- `installer/core/commands/lib/graphiti_context_loader.py` — Fix `await` syntax error
- `guardkit/knowledge/interactive_capture.py` — Lazy property for `_graphiti`
- `guardkit/knowledge/feature_plan_context.py` — Lazy property for `graphiti_client`
- Tests for all three files

## Files for Reference (read before implementing)

- `guardkit/knowledge/graphiti_client.py:1429-1524` — `_try_lazy_init()` and `get_graphiti()` (THE MECHANISM)
- `guardkit/knowledge/graphiti_client.py:370-375` — `enabled` property (checks `_connected`)
- `guardkit/knowledge/graphiti_client.py:505-525` — `_execute_search()` guards
- `guardkit/knowledge/graphiti_client.py:607-628` — `_create_episode()` guards
- `tasks/completed/TASK-FIX-GCW6/TASK-FIX-GCW6.md` — The lazy-init task that introduced these patterns

## Relationship to Other GCI Tasks

This is a **Wave 0 prerequisite** — must be completed before:
- **GCI1**: Depends on `graphiti_context_loader.py` working (Issue 1 is a hard blocker)
- **GCI2**: Depends on `_save_captured_knowledge()` actually storing to Graphiti (Issue 2)
- **GCI4**: Depends on `FeaturePlanContextBuilder.graphiti_client` being usable (Issue 3)
