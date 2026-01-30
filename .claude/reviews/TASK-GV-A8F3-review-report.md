# Review Report: TASK-GV-A8F3

## Architectural Review: Graphiti Async Event Loop Issue

**Task ID**: TASK-GV-A8F3
**Review Mode**: Architectural
**Depth**: Standard
**Date**: 2026-01-29
**Status**: REVIEW_COMPLETE

---

## Executive Summary

The root cause of the search failures has been **confirmed**: the `_run_async()` helper in [graphiti.py:56-70](guardkit/cli/graphiti.py#L56-L70) creates a **new event loop** via `asyncio.run()` for each CLI command invocation, but the `graphiti-core` library's Neo4j driver maintains internal state (Futures, connection pools) tied to the event loop where `Graphiti` was first initialized.

When `guardkit graphiti verify` executes:
1. `_run_async(client.initialize())` creates Loop A, initializes driver
2. `_run_async(client.search(...))` creates Loop B
3. Search fails with "Future attached to a different loop" because the Neo4j driver's internal Futures were created in Loop A

**Impact**: All search operations fail (100% failure rate on verification queries). Seeding may have partially failed for the same reason, though episodes with simpler async paths may have succeeded.

**Recommended Fix**: Option 1 - Single Event Loop Pattern (best architecture)

---

## Finding 1: Root Cause Confirmed - Event Loop Mismatch

### Evidence

From [graphiti_verify.md:73-74](docs/reviews/graphiti/graphiti_verify.md#L73-L74):
```
ERROR:graphiti_core.driver.neo4j_driver:Error executing Neo4j query: Task <Task pending name='Task-112'
coro=<semaphore_gather.<locals>._wrap_coroutine() running at .../graphiti_core/helpers.py:129>
cb=[gather.<locals>._done_callback() at .../asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop
```

The error originates from `graphiti_core/helpers.py:129` inside `semaphore_gather`, indicating that:
1. The graphiti-core library uses `asyncio.gather()` with semaphore limiting internally
2. The gather creates Futures bound to the current event loop at creation time
3. When `asyncio.run()` creates a new loop, these Futures cannot be awaited

### Current Architecture (Problematic)

```
CLI Command                    Event Loop        graphiti-core State
-----------                    ----------        -------------------
seed command      →  asyncio.run()  →  Loop A  →  initialize() → creates driver with Loop A Futures
status command    →  asyncio.run()  →  Loop B  →  initialize() → NEW driver with Loop B Futures
verify command    →  asyncio.run()  →  Loop C  →  initialize() → NEW driver with Loop C Futures
                                                  search()     → uses Loop C Futures ← still fails!
```

Wait - this analysis reveals that even within a single command, we're creating new event loops. Let me trace the actual flow in `verify`:

```python
# In verify() command (graphiti.py:241-320)
client, settings = _get_client_and_config()  # Creates NEW GraphitiClient
initialized = _run_async(client.initialize())  # Creates Loop X, initializes
# ...
results = _run_async(client.search(...))  # Creates Loop Y → FAILS!
```

The issue is that **each `_run_async()` call creates a new event loop**, not just each CLI command.

### Architectural Score: 35/100

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| SOLID - Single Responsibility | 7/10 | `_run_async()` correctly abstracts sync/async bridging |
| SOLID - Open/Closed | 3/10 | Cannot extend without modifying core pattern |
| SOLID - Dependency Inversion | 4/10 | High coupling to asyncio.run() behavior |
| DRY | 8/10 | Helper avoids code duplication |
| YAGNI | 8/10 | No over-engineering |
| Async Architecture | 2/10 | Fundamentally broken for stateful clients |
| Total | 35/100 | Critical architectural flaw |

---

## Finding 2: Impact Assessment - Seeding Also Affected

### Evidence

The seeding workflow in [seeding.py:1173-1249](guardkit/knowledge/seeding.py#L1173-L1249) uses the same `_run_async()` pattern through the CLI:

```python
# In seed command (graphiti.py:90-169)
client, settings = _get_client_and_config()
initialized = _run_async(client.initialize())  # Loop A
result = _run_async(seed_all_system_context(client, force=force))  # Loop B → may fail
```

However, inside `seed_all_system_context`, all calls are `await client.add_episode(...)` which share the same event loop (Loop B). The issue would occur if:
1. `initialize()` and `seed_all_system_context()` use different loops (they do)
2. The Neo4j driver caches connections or Futures from initialization

**Conclusion**: Seeding likely **partially succeeds** because:
- `add_episode()` calls are all within the same `seed_all_system_context()` coroutine
- The new event loop (Loop B) triggers fresh driver connections
- But knowledge may not be searchable due to incomplete async processing

The verification output shows 0 results for all queries despite seeding "completing", suggesting the seeded data either:
- Was not fully committed due to async failures
- Was committed but indices weren't properly built in the new loop context

---

## Finding 3: Solution Evaluation

### Option 1: Single Event Loop Pattern (Recommended)

**Approach**: Maintain a single event loop per CLI command invocation.

```python
# graphiti.py
def _run_command_async(async_fn):
    """Run an async function with a single event loop for the entire command."""
    return asyncio.run(async_fn())

@graphiti.command()
def verify(verbose: bool):
    """Verify seeded knowledge with test queries."""
    async def _verify():
        client, settings = _get_client_and_config()
        try:
            initialized = await client.initialize()
            if not initialized or not client.enabled:
                return

            # All operations share the same event loop
            for query, group_ids, expected_term in test_queries:
                results = await client.search(query, group_ids=group_ids, num_results=3)
                # ... process results
        finally:
            await client.close()

    _run_command_async(_verify)
```

| Pros | Cons |
|------|------|
| Correct async architecture | Requires refactoring all commands |
| Single event loop, no Future mismatches | More verbose command implementations |
| Matches graphiti-core examples | Cannot easily call from sync context mid-command |
| Clean resource management with try/finally | |

**Effort**: Medium (4-6 hours)
**Risk**: Low
**Architecture Score**: 85/100

### Option 2: Event Loop Reuse in `_run_async()`

**Approach**: Reuse or get the running event loop instead of creating new ones.

```python
def _run_async(coro):
    """Run an async coroutine, reusing existing event loop if available."""
    try:
        loop = asyncio.get_running_loop()
        # Already in async context - can't use run_until_complete
        # This path doesn't work for Click CLI
    except RuntimeError:
        loop = None

    if loop is None:
        # Create once and reuse
        if not hasattr(_run_async, '_loop') or _run_async._loop.is_closed():
            _run_async._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_run_async._loop)
        return _run_async._loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)
```

| Pros | Cons |
|------|------|
| Minimal code change | Global mutable state (cached loop) |
| Backwards compatible API | Loop may become closed, need cleanup |
| Quick fix | Doesn't address resource cleanup |
| | Can leak resources between commands |

**Effort**: Low (1-2 hours)
**Risk**: Medium (state management complexity)
**Architecture Score**: 55/100

### Option 3: Fresh Client Per Operation

**Approach**: Create a new `GraphitiClient` for each CLI command, initialize within a single `asyncio.run()`.

```python
@graphiti.command()
def verify(verbose: bool):
    async def run_verify():
        settings = load_graphiti_config()
        config = GraphitiConfig(...)
        client = GraphitiClient(config)

        try:
            await client.initialize()
            # All operations in same event loop
            for query, ... in test_queries:
                results = await client.search(...)
        finally:
            await client.close()

    asyncio.run(run_verify())
```

| Pros | Cons |
|------|------|
| Clean resource lifecycle | Repeated initialization cost |
| No shared state issues | Code duplication across commands |
| Simple mental model | Indices rebuilt each time |

**Effort**: Medium (3-4 hours)
**Risk**: Low
**Architecture Score**: 70/100

### Option 4: Use `asyncio.get_event_loop()` Pattern

**Approach**: Use deprecated but functional `get_event_loop()` pattern.

```python
def _run_async(coro):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)
```

| Pros | Cons |
|------|------|
| Very simple | `get_event_loop()` deprecated in Python 3.10+ |
| One-line change | May create new loop anyway |
| | Still has lifecycle issues |

**Effort**: Minimal (15 minutes)
**Risk**: High (deprecation, inconsistent behavior)
**Architecture Score**: 40/100

---

## Recommendation: Option 1 - Single Event Loop Pattern

**Justification**:

1. **Correct Architecture**: Matches all graphiti-core documentation examples which use `asyncio.run(main())` pattern with a single async function containing all operations.

2. **Resource Management**: Enables proper `try/finally` cleanup with `await client.close()`.

3. **Future-Proof**: Won't break with Python async changes or graphiti-core updates.

4. **Testability**: Async functions are easier to test than sync-wrapped async.

5. **Performance**: Avoids repeated Neo4j connection establishment and index building.

### Implementation Approach

1. **Refactor CLI Commands**: Convert each Click command to call a single async function via `asyncio.run()`.

2. **Create Async Command Functions**: For each command (seed, status, verify, seed-adrs), create `_cmd_seed()`, `_cmd_status()`, etc.

3. **Remove `_run_async()` Helper**: Replace with direct `asyncio.run()` calls.

4. **Update Tests**: Ensure CLI tests work with new async structure.

### Example Implementation Sketch

```python
# guardkit/cli/graphiti.py

async def _cmd_verify(verbose: bool) -> None:
    """Async implementation of verify command."""
    console.print("[bold blue]Graphiti Verification[/bold blue]")

    if not is_seeded():
        console.print("[yellow]System context not seeded.[/yellow]")
        return

    settings = load_graphiti_config()
    config = GraphitiConfig(
        enabled=settings.enabled,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
    )
    client = GraphitiClient(config)

    try:
        console.print(f"Connecting to Neo4j at {settings.neo4j_uri}...")
        initialized = await client.initialize()

        if not initialized or not client.enabled:
            console.print("[yellow]Graphiti not available.[/yellow]")
            return

        console.print("[green]Connected[/green]")

        test_queries = [...]
        passed = 0
        failed = 0

        for query, group_ids, expected_term in test_queries:
            try:
                results = await client.search(query, group_ids=group_ids, num_results=3)
                if results:
                    passed += 1
                    console.print(f"[green]✓[/green] {query}")
                else:
                    passed += 1
                    console.print(f"[yellow]✓[/yellow] {query} (no results)")
            except Exception as e:
                failed += 1
                console.print(f"[red]✗[/red] {query}")
                if verbose:
                    console.print(f"    Error: {e}")

        console.print(f"\nResults: {passed} passed, {failed} failed")
    finally:
        await client.close()


@graphiti.command()
@click.option("--verbose", "-v", is_flag=True)
def verify(verbose: bool):
    """Verify seeded knowledge with test queries."""
    asyncio.run(_cmd_verify(verbose))
```

---

## Decision Matrix

| Option | Architecture Score | Effort | Risk | Recommendation |
|--------|-------------------|--------|------|----------------|
| 1. Single Event Loop | 85/100 | Medium | Low | **Recommended** |
| 2. Loop Reuse | 55/100 | Low | Medium | Acceptable workaround |
| 3. Fresh Client | 70/100 | Medium | Low | Good alternative |
| 4. get_event_loop | 40/100 | Minimal | High | Not recommended |

---

## Files Affected

| File | Changes Required |
|------|-----------------|
| [guardkit/cli/graphiti.py](guardkit/cli/graphiti.py) | Refactor all commands to single-async pattern |
| [tests/knowledge/test_graphiti_client.py](tests/knowledge/test_graphiti_client.py) | Update tests for async CLI structure (if needed) |

**No changes needed**:
- [guardkit/knowledge/graphiti_client.py](guardkit/knowledge/graphiti_client.py) - Client code is correct
- [guardkit/knowledge/seeding.py](guardkit/knowledge/seeding.py) - Seeding logic is correct (pure async)

---

## Acceptance Criteria Status

From task TASK-GV-A8F3:

| Criterion | Status | Notes |
|-----------|--------|-------|
| Root cause confirmed with evidence | ✅ Complete | Event loop mismatch in `_run_async()` |
| Impact on seeding documented | ✅ Complete | Seeding shares same issue pattern |
| 2+ solutions evaluated with pros/cons | ✅ Complete | 4 options evaluated |
| Recommended fix selected with justification | ✅ Complete | Option 1 - Single Event Loop |
| Implementation task created | ⏳ Pending | Decision checkpoint |

---

## Appendix A: Error Stack Trace Analysis

The full error message from [graphiti_verify.md:73-120](docs/reviews/graphiti/graphiti_verify.md#L73-L120):

```
ERROR:graphiti_core.driver.neo4j_driver:Error executing Neo4j query:
Task <Task pending name='Task-112' coro=<semaphore_gather.<locals>._wrap_coroutine()
running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:129>
cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]>
got Future <Future pending> attached to a different loop
```

This tells us:
1. **Location**: `graphiti_core/helpers.py:129` - Inside the library's `semaphore_gather` helper
2. **Task Name**: `Task-112` - High task number indicates many prior async operations
3. **Callback**: `gather._done_callback` - Part of asyncio.gather() chain
4. **Error Type**: Classic event loop mismatch - Future created in Loop A, awaited in Loop B

---

## Appendix B: graphiti-core Documentation Reference

From Context7 documentation for graphiti-core:

> Initializes the Graphiti framework using the default Neo4j database driver. This function sets up the connection, builds necessary indices and constraints, and ensures the Graphiti instance is ready for use.
>
> ```python
> async def main():
>     graphiti = Graphiti(uri="bolt://localhost:7687", ...)
>     try:
>         await graphiti.build_indices_and_constraints()
>         # ... all operations here
>     finally:
>         await graphiti.close()
>
> asyncio.run(main())
> ```

The canonical pattern is a **single** `asyncio.run()` with all operations inside one async function.

---

## Review Metadata

- **Reviewer**: architectural-reviewer (via /task-review)
- **Duration**: ~45 minutes
- **Files Analyzed**: 6
- **Code Patterns Evaluated**: 4 solution options
- **Next Steps**: Decision checkpoint
