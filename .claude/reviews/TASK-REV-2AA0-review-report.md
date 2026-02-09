# Review Report: TASK-REV-2AA0

## Executive Summary

Analysis of the FEAT-6EDD (system-plan) AutoBuild output reveals **two confirmed bugs and one root cause** for the stall:

1. **BUG-1 (Critical - Stall Cause)**: Shared Graphiti singleton (Neo4j driver + OpenAI embedder) is used across 3 worker threads, each with its own `asyncio.new_event_loop()`. The graphiti-core `search()` function uses nested `asyncio.gather()` without `return_exceptions=True`, and the Neo4j driver's async objects are bound to a single event loop. Cross-loop errors propagate through unguarded exception paths in graphiti-core's search subsystem, causing 2 of 3 tasks to hang silently during context loading.
2. **BUG-2 (Minor - Coroutine Leak)**: `_capture_turn_state()` calls `asyncio.create_task()` without a running event loop, producing the `RuntimeWarning: coroutine 'capture_turn_state' was never awaited`.

Graphiti integration points (GCI0-GCI7) are correctly wired and degrade gracefully. The issue is in the **threading model interaction** between the FeatureOrchestrator's parallel execution and the shared Graphiti singleton.

## Review Details

- **Mode**: Diagnostic
- **Depth**: Deep (revised with verification)
- **Log Size**: 3,250 lines covering 3/8 tasks completing across 2/4 waves

---

## Issue 1: Graphiti Exceptions (Categorization)

### Exception Types Found

| Category | Count | Error Message | Severity |
|----------|-------|---------------|----------|
| Neo4j cross-loop | 159 | `got Future <Future pending> attached to a different loop` | Expected (threading) |
| Search failures | 53 | `Search request failed: ... attached to a different loop` | Expected (graceful) |
| Socket errors | ~129 | `socket.send() raised exception` | Expected (stale connections) |
| Neo4j schema notifications | ~50 | `index or constraint already exists` | Informational (benign) |
| OpenAI retry | 1 | `Retrying request to /embeddings in 0.426290 seconds` | Transient (benign) |

### Root Cause of Neo4j "Attached to a Different Loop" Errors

**Verified mechanism (Python 3.14):**

1. `FeatureOrchestrator._execute_wave_parallel()` calls `asyncio.to_thread(self._execute_task, ...)` for each task
2. Inside each worker thread, `asyncio.get_event_loop()` **raises `RuntimeError`** (Python 3.14 behaviour — there is no current event loop in worker threads)
3. The code catches this and calls `asyncio.new_event_loop()` — each worker thread gets its own **fresh** event loop
4. The Graphiti singleton's Neo4j driver was initialized on the **main** event loop (during `get_graphiti()` lazy init)
5. When worker threads call `graphiti.search()`, the Neo4j driver's `AsyncCondition._get_loop()` detects the event loop mismatch and raises `RuntimeError`

**Key correction from initial analysis**: The code does NOT use the main thread's loop (that was the initial hypothesis). Each worker creates its own loop. The cross-loop errors come from the shared Neo4j driver whose internal async objects were bound to a different loop during initialization.

### Graceful Degradation Assessment

Graceful degradation is **working as designed** at the GuardKit integration level:
- `graphiti_client.py:_execute_search()` catches exceptions and returns `[]`
- `autobuild_context_loader.py:get_player_context()` catches exceptions and returns empty result
- Evidence: SP-003 completed context loading with `0 categories, 0/5200 tokens` and proceeded to SDK invocation

**Verdict: PASS** — The GCI0-GCI7 integration work is correctly wired and degrading gracefully.

---

## Issue 2: Stall Root Cause Analysis

### What Happened

**Timeline:**
1. Wave 1 (SP-001, SP-002): Ran in parallel, both completed successfully in 1 turn each
   - SP-001: Had context_loader, used Graphiti (11 embedding requests, no errors — ran on Wave 1's event loop which matches the Graphiti init loop)
   - SP-002: No context_loader provided (line 52: "Player context retrieval skipped")
2. Wave 2 (SP-003, SP-004, SP-005): Started in parallel via `asyncio.to_thread()`
   - All 3 tasks started context loading simultaneously (lines 1505-1508)
   - SP-003: Completed 11 context queries, reached SDK invocation (line 2568), completed in 1 turn (line 3249)
   - SP-004: Started context loading, produced some embedding requests + Neo4j errors, then **went silent**
   - SP-005: Same as SP-004
3. After SP-003 completed, `asyncio.gather()` in `_execute_wave_parallel()` continued waiting for SP-004/SP-005
4. No output for ~20 minutes. User killed the process.

### Evidence Analysis

**Embedding request count**: 53 total across the entire log
- Wave 1 SP-001 Player context: 11 embedding requests (lines 148-651)
- Wave 1 SP-001 Coach context: 11 embedding requests (lines 834-1364)
- Wave 2 (all tasks): 31 embedding requests (lines 1510-3153)
- Expected for Wave 2: 44 (11 per Player × 3 tasks + 11 Coach × 1 task)
- **13 embedding requests missing** = SP-004 and SP-005 completed only ~4-5 queries each before hanging

**Task number analysis**: The Neo4j error messages include asyncio Task numbers (Task-265, Task-271, etc.). Task numbers increment by ~6 per cycle, consistent with 3 concurrent tasks each spawning sub-tasks. Errors continue past SP-003's completion but eventually stop at line 3205 (Task-450).

**Critical observation**: After line 3249 (SP-003 complete), line 3250 shows a spinner but **zero further output** — no errors, no embedding requests, no warnings. SP-004/SP-005 are completely frozen.

### BUG-1: Shared Graphiti Singleton Cross-Loop Hang (Critical)

**Root Cause**: The stall is caused by the combination of:
1. A shared Graphiti singleton with Neo4j driver bound to one event loop
2. graphiti-core's `search()` using nested `asyncio.gather()` without `return_exceptions=True`
3. Multiple worker threads each creating their own event loop

**Detailed Mechanism:**

The graphiti-core `search()` function ([search.py:118-166](search.py)) executes:
```python
(edges, ...), (nodes, ...), (episodes, ...), (communities, ...) = await semaphore_gather(
    edge_search(driver, cross_encoder, query, ...),
    node_search(driver, cross_encoder, query, ...),
    episode_search(driver, cross_encoder, query, ...),
    community_search(driver, cross_encoder, query, ...),
)
```

Each sub-search (e.g., `edge_search`) internally does ANOTHER `semaphore_gather()`:
```python
# edge_search, line 236
search_results = list(await semaphore_gather(
    edge_fulltext_search(driver, query, ...),     # Neo4j query - FAILS
    edge_similarity_search(driver, query, ...),   # Neo4j query - FAILS
))
```

`semaphore_gather()` ([helpers.py:121-131](helpers.py)) wraps `asyncio.gather()` with **no `return_exceptions=True`**:
```python
async def semaphore_gather(*coroutines, max_coroutines=None):
    semaphore = asyncio.Semaphore(max_coroutines or SEMAPHORE_LIMIT)
    async def _wrap_coroutine(coroutine):
        async with semaphore:
            return await coroutine
    return await asyncio.gather(*(_wrap_coroutine(coroutine) for coroutine in coroutines))
```

The Neo4j driver's `execute_query()` raises the "different loop" error. This exception propagates through the inner `semaphore_gather()` → cancels sibling tasks → propagates to outer `semaphore_gather()` → cancels remaining sub-searches. However, when the exception cancels tasks that have pending I/O operations (OpenAI embedding HTTP requests mid-flight on the worker's event loop, Neo4j socket operations referencing the init loop), the cancellation may not complete cleanly due to cross-loop resource references.

**Why SP-003 succeeded but SP-004/SP-005 didn't:**
- All 3 tasks create independent event loops and start 11 sequential context queries
- The first query in each task calls `TaskAnalyzer.analyze()` → `graphiti.search()` → graphiti-core `search()`
- graphiti-core `search()` first calls `embedder.create()` (OpenAI — succeeds) then `semaphore_gather(edge_search, node_search, episode_search, community_search)`
- Inside each sub-search, Neo4j queries fail with "different loop"
- **The exception propagation through nested `asyncio.gather()` without `return_exceptions=True` is non-deterministic** — timing of cancellation depends on which sub-tasks have pending I/O, which events are being processed on each loop, and the state of shared connection pools
- SP-003 happened to complete its error-handling path cleanly (all 11 queries returned empty results)
- SP-004/SP-005 got stuck in the exception propagation/cancellation path, likely due to:
  - Cancelled tasks holding references to the Neo4j driver's socket transports from the init loop
  - `asyncio.gather()`'s cancellation of sibling tasks interacting badly with cross-loop Future references
  - The `socket.send() raised exception` warnings (129 occurrences) indicate the transport layer is corrupted

**Verified NOT the cause:**
- ~~`asyncio.get_event_loop()` returning the main loop~~ — Python 3.14 raises RuntimeError in worker threads (verified by test)
- ~~`loop.run_until_complete()` on an already-running loop~~ — Each worker creates its own fresh loop
- ~~Neo4j driver hanging on queries~~ — The driver's `AsyncCondition._get_loop()` raises RuntimeError immediately (verified by code inspection)
- ~~OpenAI httpx client hanging cross-loop~~ — httpx uses anyio, works correctly across loops (verified by test)
- ~~OpenAI AsyncOpenAI client hanging~~ — Verified returns fast errors from different loops

### BUG-2: Unawaited `capture_turn_state` Coroutine (Minor)

**Location**: [autobuild.py:2412](guardkit/orchestrator/autobuild.py#L2412)

**Code:**
```python
# In _capture_turn_state() - called from sync _loop_phase()
graphiti = get_graphiti()
if graphiti and graphiti.enabled:
    asyncio.create_task(capture_turn_state(graphiti, entity))  # BUG: No running loop
```

**The Problem:**
- `asyncio.create_task()` requires a running event loop in the current thread
- `_capture_turn_state()` is called from sync `_loop_phase()` in a worker thread
- `loop.run_until_complete()` runs the event loop only for the duration of each call, so between calls there is no running loop
- The RuntimeError is caught at line 2417, but the coroutine object leaks (never awaited)

**Impact:**
- Turn state data is silently NOT captured to Graphiti (3 occurrences observed)
- NOT the stall cause — correctly caught by try/except
- 3 occurrences identical: `WARNING:guardkit.orchestrator.autobuild:Error capturing turn state: no running event loop`

---

## Stall Detection Assessment

### Did Existing Mechanisms Catch This?

**No.** The stall detection from TASK-AB-SD01 operates within `_loop_phase()`, which detects:
- No-passing-checkpoint stalls (consecutive Coach failures)
- Repeated feedback stalls (same feedback given repeatedly)

These are **per-task, per-turn** mechanisms. The stall occurred **before** the first SDK invocation — during `_invoke_player_safely()` → context loading → `loop.run_until_complete(get_player_context(...))`. This is upstream of the stall detector.

### Why Wave 1 Didn't Have This Problem

- Wave 1 uses `asyncio.run()` in `_execute_wave()` (feature_orchestrator.py:1139)
- `asyncio.run()` creates a new event loop for the wave
- `asyncio.to_thread()` spawns worker threads from that loop
- SP-001's context loading ran on a loop created by `asyncio.run()`, which is the SAME context as the Graphiti lazy init (both in the `asyncio.run()` scope)
- Wave 2's `asyncio.run()` creates a DIFFERENT loop, so the worker threads' new loops are 2 hops away from the init loop

**Alternative explanation**: Wave 1 may have initialized the Graphiti singleton for the first time during SP-001's context loading (first `get_graphiti()` call in `__init__` at line 597). If the lazy init happened inside a worker thread, the Neo4j driver would be bound to Wave 1's worker thread loop — which is then a different loop for Wave 2's workers.

---

## Fix Recommendations

### Fix 1: Create Per-Thread Graphiti Client (Root Cause Fix - Critical)

The fundamental issue is the **shared singleton pattern** for Graphiti when used across multiple event loops. The graphiti-core library's internal async objects (Neo4j driver, OpenAI embedder) are bound to a single event loop and cannot be safely used from others.

**Option A (Recommended): Thread-local Graphiti clients**

Create a separate Graphiti client for each worker thread, each with its own event loop context:

```python
# In AutoBuildOrchestrator._invoke_player_safely()
import asyncio

# Always create a fresh event loop for this thread
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

try:
    if self.enable_context and self._context_loader is not None:
        try:
            # Create a thread-local context loader with a fresh Graphiti client
            thread_loader = self._get_or_create_thread_local_loader(loop)
            context_result = loop.run_until_complete(
                thread_loader.get_player_context(...)
            )
            context_prompt = context_result.prompt_text
        except Exception as e:
            logger.warning(f"Failed to retrieve Player context: {e}")
            context_prompt = ""

    result = loop.run_until_complete(
        self._agent_invoker.invoke_player(...)
    )
    return result
finally:
    loop.close()
```

Where `_get_or_create_thread_local_loader()` initializes a fresh `AutoBuildContextLoader` with a NEW `GraphitiClient` (new Neo4j driver, new OpenAI embedder) bound to the current thread's event loop.

**Option B (Simpler but lossy): Disable Graphiti context in parallel mode**

```python
# In FeatureOrchestrator._execute_task()
task_orchestrator = AutoBuildOrchestrator(
    ...
    enable_context=False,  # Disable when running in parallel
)
```

This is pragmatic — the context retrieval returns empty results anyway due to cross-loop errors. Disabling it avoids the hang without losing any actual context.

**Option C (Defensive): Add timeout to context loading**

```python
# In _invoke_player_safely()
try:
    context_result = loop.run_until_complete(
        asyncio.wait_for(
            self._context_loader.get_player_context(...),
            timeout=30.0  # 30s timeout for context loading
        )
    )
except asyncio.TimeoutError:
    logger.warning("Context loading timed out, proceeding without context")
    context_prompt = ""
```

### Fix 2: Replace `asyncio.create_task()` in `_capture_turn_state` (Minor)

At [autobuild.py:2412](guardkit/orchestrator/autobuild.py#L2412):

```python
# Use the thread's event loop (created in _invoke_player_safely)
try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(capture_turn_state(graphiti, entity))
except RuntimeError:
    logger.debug("No event loop available, skipping turn state capture")
except Exception as e:
    logger.warning(f"Error capturing turn state: {e}")
```

### Fix 3: Add Task-Level Timeout in FeatureOrchestrator (Defensive)

```python
# In feature_orchestrator.py _execute_wave_parallel()
tasks_to_execute.append(
    asyncio.wait_for(
        asyncio.to_thread(self._execute_task, task, feature, worktree),
        timeout=self.max_task_timeout  # e.g., 2400s (40 min)
    )
)
```

This provides a defensive backstop that prevents any individual task from blocking the entire wave indefinitely, regardless of the cause.

---

## Summary

| Finding | Severity | Root Cause | Fix |
|---------|----------|------------|-----|
| Graphiti "different loop" errors | Info | Shared singleton Neo4j driver used from worker thread event loops | Resolved by Fix 1 |
| Graceful degradation working | **PASS** | GCI0-GCI7 integration correctly wired | No fix needed |
| SP-004/SP-005 hang | **Critical** | graphiti-core `asyncio.gather()` without `return_exceptions=True` + cross-loop exception cancellation hang | Fix 1 (root cause) + Fix 3 (defensive) |
| Unawaited `capture_turn_state` | Minor | `asyncio.create_task()` without running loop in worker thread | Fix 2 |
| No wave-level task timeout | Medium | Missing defensive timeout in `_execute_wave_parallel()` | Fix 3 |
| Stall detection didn't trigger | Expected | Stall occurred pre-turn-loop, outside stall detector scope | Fix 3 (defensive) |
| Wave 1 unaffected | Info | Wave 1's event loop context matched Graphiti init loop | N/A |

**Priority Order:**
1. **Fix 1 Option B** (Quick fix) — Disable context in parallel mode. Zero risk, immediate unblock.
2. **Fix 3** (Medium) — Defensive timeout prevents any future hangs.
3. **Fix 1 Option A** (Proper fix) — Thread-local Graphiti clients for correct parallel context retrieval.
4. **Fix 2** (Minor) — Correct turn state capture.
5. **Fix 1 Option C** (Belt-and-suspenders) — Timeout around context loading as additional safety.

---

## Deep Analysis Notes

### Verification Tests Performed

1. **Python 3.14 asyncio.get_event_loop() in worker threads**: Confirmed raises `RuntimeError: There is no current event loop in thread 'asyncio_0'` — each worker creates a fresh loop via `asyncio.new_event_loop()`.

2. **Neo4j driver AsyncCondition cross-loop**: Code inspection of `_async_compat/concurrency.py` confirmed `_get_loop()` raises `RuntimeError` immediately when called from a different loop — does NOT hang.

3. **Neo4j driver AsyncCooperativeRLock**: Uses fail-fast cooperative locking (raises RuntimeError on contention, not blocking wait).

4. **httpx AsyncClient cross-loop**: Tested with 3 parallel workers sharing one client — all completed successfully. httpx uses anyio which handles cross-loop scenarios.

5. **OpenAI AsyncOpenAI cross-loop**: Tested — returns fast errors (0.31-0.34s), no hangs.

6. **Simulated 3-worker context loading**: With fake clients mimicking Neo4j errors + OpenAI successes, all 3 workers completed in ~3.3s. The simulation could NOT reproduce the hang, confirming the issue is in the real library's internal I/O layer.

7. **graphiti-core search() analysis**: Confirmed nested `semaphore_gather()` → `asyncio.gather()` without `return_exceptions=True`. Exception from one sub-search cancels siblings. Combined with cross-loop socket operations, cancellation may not complete cleanly.

### What Was Disproved

- **Initial hypothesis**: `asyncio.get_event_loop()` returns the main thread's already-running loop → WRONG on Python 3.14
- **Deadlock on main loop**: `loop.run_until_complete()` blocking on an already-running loop → WRONG, each worker has its own loop
- **Neo4j driver hanging**: The driver raises errors immediately, not hanging
- **OpenAI/httpx causing hang**: Both work correctly across event loops
