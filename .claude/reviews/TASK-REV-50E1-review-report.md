# Review Report: TASK-REV-50E1 (Revised)

## Executive Summary

AutoBuild Run 4 for FEAT-AC1A (Seam-First Testing Strategy) was a **strong success**: 11/11 tasks completed across 3 waves in 43m 35s with 91% clean execution rate. The ~53 error/warning lines are **cosmetic** — caused by Graphiti/FalkorDB async lifecycle mismanagement — and do not indicate data loss, corruption, or functional failure.

**Revision Note**: This report has been revised with deep source code analysis. All root causes are now traced to specific code locations with high confidence. The original analysis was mostly correct; this revision adds precision and corrects the TASK-SFT-010 finding (not a filesystem race — it's a design gap in direct mode SDK report handling).

## Review Details

- **Mode**: Architectural / Error Analysis (Revised — Deep Dive)
- **Depth**: Comprehensive (source code analysis)
- **Source**: `docs/reviews/autobuild-fixes/run_4_success_with_errors.md` (2,732 lines)
- **Code examined**: `feature_orchestrator.py`, `autobuild.py`, `graphiti_client.py`, `agent_invoker.py`, `state_tracker.py`, `paths.py`

---

## Finding 1: FalkorDB/Graphiti Async Event Loop Lifecycle (Root Cause)

**Severity**: Medium (noisy but non-blocking)
**Confidence**: HIGH — traced through 4 source files

### Root Cause: Three Separate Event Loop Creation Points

The fundamental issue is that **three different code paths create and destroy event loops**, and the Graphiti client's FalkorDB driver retains internal `asyncio.Lock` objects bound to the first loop it encounters:

#### 1a. `GraphitiClientFactory.get_thread_client()` — The Primary Contaminator

**File**: [graphiti_client.py:1627-1632](guardkit/knowledge/graphiti_client.py#L1627-L1632)

```python
loop = asyncio.new_event_loop()
_suppress_httpx_cleanup_errors(loop)
try:
    success = loop.run_until_complete(coro)  # coro = client.initialize()
finally:
    loop.close()  # ← Loop dies, but FalkorDB driver retains Lock objects from it
if success:
    self._thread_local.client = client  # ← Client persists with dead-loop Locks
```

`client.initialize()` ([graphiti_client.py:489-574](guardkit/knowledge/graphiti_client.py#L489-L574)) calls `await self._graphiti.build_indices_and_constraints()`, which creates Redis connection pool Locks bound to this temporary loop. When the loop closes, the client is retained but its internal Locks are orphaned.

#### 1b. `_preflight_check()` — Health Check Loop Contamination

**File**: [feature_orchestrator.py:959-966](guardkit/orchestrator/feature_orchestrator.py#L959-L966)

```python
loop = asyncio.new_event_loop()
try:
    healthy = loop.run_until_complete(
        asyncio.wait_for(client._check_health(), timeout=5.0)
    )
finally:
    loop.close()  # ← Second temporary loop, also dies
```

The health check calls `_check_health()` ([graphiti_client.py:465-487](guardkit/knowledge/graphiti_client.py#L465-L487)) which runs `self._graphiti.search("health_check_test")`. If the client was initialized in a PRIOR loop (via `get_thread_client()`), this search attempts to use Lock objects from that prior loop — causing the "Lock bound to different event loop" error.

#### 1c. `asyncio.run()` per Wave — Loop-Per-Wave Pattern

**File**: [feature_orchestrator.py:1337](guardkit/orchestrator/feature_orchestrator.py#L1337)

```python
results = asyncio.run(
    self._execute_wave_parallel(wave_number, task_ids, feature, worktree)
)
```

Each wave gets a **completely new event loop** via `asyncio.run()`. Within each wave, `asyncio.to_thread()` spawns worker threads that create their own per-thread loops via `_get_thread_local_loader()` ([autobuild.py:3114-3166](guardkit/orchestrator/autobuild.py#L3114-L3166)):

```python
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
thread_loader = self._get_thread_local_loader(loop)
```

This creates yet another event loop. If `get_thread_client()` is called from within this loop, the factory creates ANOTHER temporary loop for initialization (see 1a), then the client is used on the thread's loop — causing Lock affinity mismatch.

### The Event Loop Chain (Traced)

```
1. _preflight_check()     → loop_A (created, health check, CLOSED)
2. _pre_init_graphiti()    → calls get_thread_client()
   └─ get_thread_client()  → loop_B (created, client.initialize(), CLOSED)
      └─ FalkorDB driver Locks ← bound to loop_B (now dead)
3. asyncio.run(wave_1)    → loop_C (created)
   └─ asyncio.to_thread() → worker thread
      └─ _get_thread_local_loader() → loop_D (created)
         └─ Attempts Graphiti ops with Locks bound to loop_B → ERROR
4. asyncio.run(wave_2)    → loop_E (created, loop_C CLOSED)
   └─ Same pattern, same errors
```

### Error Manifestations

| Error Type | Root Cause | Code Path |
|-----------|-----------|-----------|
| "Event loop is closed" | `loop.run_until_complete()` on a closed loop | `_capture_turn_state` using `stored_loop` that's been closed |
| "Lock bound to different event loop" | FalkorDB Lock from loop_B used on loop_D | Any Graphiti operation after initialization |
| "no running event loop" | Accessing loop after `asyncio.run()` completes | Shutdown cleanup, knowledge capture |
| "coroutine never awaited" | `graphiti.search()` spawns `semaphore_gather` coroutines, loop closes mid-flight | Shutdown only |
| "Task was destroyed but pending" | `build_indices_and_constraints` background tasks abandoned | Shutdown only |

---

## Finding 2: `_capture_turn_state` Ignores `enable_context` Flag

**Severity**: Medium (causes unnecessary errors every turn)
**Confidence**: HIGH — exact code location identified

### The Gap

**File**: [autobuild.py:2883-2895](guardkit/orchestrator/autobuild.py#L2883-L2895)

```python
graphiti = None
stored_loop = None
if self._factory is not None:
    thread_id = threading.get_ident()
    entry = self._thread_loaders.get(thread_id)
    if entry is not None:
        loader, stored_loop = entry
        if loader is not None and loader.graphiti is not None:
            graphiti = loader.graphiti
if graphiti is None:
    graphiti = get_graphiti()  # Fallback to module-level
if graphiti and graphiti.enabled:  # ← Only checks .enabled, NOT self.enable_context
    ...
```

The method checks `graphiti.enabled` (which is True — the client connected successfully during initialization) but **never checks `self.enable_context`** (which is False — set by the health check failure).

### Evidence from Code

Compare with how `_invoke_player_safely` correctly checks `enable_context` ([autobuild.py:3261](guardkit/orchestrator/autobuild.py#L3261)):

```python
if self.enable_context and thread_loader is not None:  # ← Correct pattern
```

And `_get_thread_local_loader` also checks it ([autobuild.py:3140](guardkit/orchestrator/autobuild.py#L3140)):

```python
if not self.enable_context or self._factory is None:  # ← Correct pattern
    return None
```

But `_capture_turn_state` uses the WRONG check. This is why turn state capture fires on every task even when `enable_context=False`, producing 11 "Episode creation request failed" warnings.

### Fix

Add `self.enable_context` check at [autobuild.py:2895](guardkit/orchestrator/autobuild.py#L2895):

```python
if graphiti and graphiti.enabled and self.enable_context:  # ← Add enable_context
```

---

## Finding 3: TASK-SFT-010 Player Report — NOT a Race Condition

**Severity**: Low (recovered successfully, but root cause was misidentified in initial report)
**Confidence**: HIGH — complete code path traced

### Corrected Sequence of Events

1. **SDK invocation**: Direct mode Player invoked via `_invoke_with_role()` ([agent_invoker.py:2493](guardkit/orchestrator/agent_invoker.py#L2493))
2. **SDK completes**: SDK session finishes (run log line 1846)
3. **Report load attempt**: `_retry_with_backoff` tries to load `player_turn_1.json` ([agent_invoker.py:2509-2516](guardkit/orchestrator/agent_invoker.py#L2509-L2516)) — 3 retries at 0.1/0.2/0.4s — **ALL FAIL** because the SDK in direct mode doesn't write `player_turn_N.json`
4. **`PlayerReportNotFoundError` raised**: Caught at [agent_invoker.py:2537](guardkit/orchestrator/agent_invoker.py#L2537)
5. **Error handler writes reports**: `_write_direct_mode_results()` and `_write_player_report_for_direct_mode()` ([agent_invoker.py:2542-2555](guardkit/orchestrator/agent_invoker.py#L2542-L2555)) write **error** reports to both paths — run log lines 1977-1978
6. **State recovery triggered**: AutoBuild detects Player failure, invokes `MultiLayeredStateTracker` ([autobuild.py:2125-2130](guardkit/orchestrator/autobuild.py#L2125-L2130))
7. **State tracker finds the ERROR report**: The state_tracker loads `player_turn_1.json` (run log line 1985) — but this is the **error report written by the error handler**, not the SDK's original output
8. **Synthetic report built**: State recovery succeeds via `player_report` detection method, but with 0 files and 0 tests (run log line 1988)

### Root Cause (Corrected)

This is **NOT** a filesystem race condition. It is a **design gap in direct mode**: the SDK subprocess does not write `player_turn_N.json` — it writes its results in a different format. The `_retry_with_backoff` correctly determines the file doesn't exist. The error handler then writes a minimal error report which the state tracker later finds.

The key evidence is run log line 1988: `State recovery succeeded via player_report: 0 files, 0 tests (failing)` — the state tracker found 0 files and 0 tests despite the SDK actually having completed work. This is because it loaded the error handler's minimal report `{"task_id": "TASK-SFT-010", "turn": 1}`, not the SDK's actual output.

### Impact

The state recovery mechanism works (no task failure), but the synthetic report passed to the Coach is hollow — it contains no real data about what the Player did. The Coach then correctly requests another turn, and Turn 2 succeeds normally. **1 wasted turn**.

### Fix

The direct mode invocation should either:
- **(a)** Have the SDK write its report to the expected `player_turn_N.json` path, OR
- **(b)** Parse the SDK's actual output format in `_load_agent_report` for direct mode tasks, OR
- **(c)** Extract the SDK's results from its conversation output (the `_invoke_with_role` response) and construct `player_turn_N.json` from that

---

## Finding 4: `_cleanup_thread_loaders` Three-Branch Strategy

**Severity**: Low (working correctly, minor gap)
**Confidence**: HIGH

### What Works

The three-branch cleanup at [autobuild.py:3178-3201](guardkit/orchestrator/autobuild.py#L3178-L3201) is well-designed:

```python
if stored_loop.is_running():
    # Branch 1: Schedule close on the running loop
    future = asyncio.run_coroutine_threadsafe(loader.graphiti.close(), stored_loop)
    future.result(timeout=30)
elif not stored_loop.is_closed():
    # Branch 2: Loop stopped but not closed — run directly
    stored_loop.run_until_complete(loader.graphiti.close())
else:
    # Branch 3: Loop already closed — create fresh loop
    asyncio.run(loader.graphiti.close())
```

### The Gap

Branch 3 (`asyncio.run(loader.graphiti.close())`) creates a FRESH event loop, but `loader.graphiti.close()` internally calls `self._graphiti.close()` which tries to close the FalkorDB driver. The driver's cleanup methods may try to release Locks that are bound to the original (now-dead) loop, causing "Lock bound to different event loop" errors in the fresh loop.

The `try/except RuntimeError` on line 3195 correctly suppresses this, so it's handled — but the error is still logged at DEBUG level, contributing to the noise.

---

## Finding 5: Coach Feedback Patterns

**Severity**: Informational
**Confidence**: HIGH

### Multi-Turn Task Breakdown

| Task | Turns | Reason for Extra Turns |
|------|-------|----------------------|
| TASK-SFT-001 | 1 | Clean pass |
| TASK-SFT-002 | 2 | AC-005, AC-006 missing ("Decision captures", "Consequences list") |
| TASK-SFT-003 | 1 | Clean pass |
| TASK-SFT-004 | 1 | Clean pass |
| TASK-SFT-005 | 1 | Clean pass |
| TASK-SFT-006 | 2 | Missing test: "`guardkit task create` with title creates a task file" |
| TASK-SFT-007 | 1 | Clean pass |
| TASK-SFT-008 | 1 | Clean pass |
| TASK-SFT-009 | 3 | Turn 1: AC not met; Turn 2: zero-test anomaly rejection; Turn 3: approved |
| TASK-SFT-010 | 2 | Direct mode report gap (see Finding 3) |
| TASK-SFT-011 | 1 | Clean pass |

### Efficiency Metrics

- **Single-turn completion**: 7/11 tasks (64%)
- **Two-turn completion**: 3/11 tasks (27%)
- **Three-turn completion**: 1/11 tasks (9%)
- **Average turns per task**: 1.45
- **Turn efficiency**: 16 total turns / 11 tasks = good

### Notable Coach Behaviors

1. **Zero-test anomaly detection** (TASK-SFT-009 turn 2): Coach correctly rejected a task where quality gates all passed but no task-specific tests were created. Excellent.

2. **Acceptance criteria strictness** (TASK-SFT-002): Coach rejected because specific phrasing from ACs wasn't present. Appropriately strict for ADR-type tasks.

3. **Missing test detection** (TASK-SFT-006): Coach caught a missing CLI test. Player addressed it on turn 2.

---

## Finding 6: Data Loss / Corruption Assessment

**Severity**: None (no risk)
**Confidence**: HIGH

### Evidence

1. **All 11 tasks completed successfully** with correct worktree state
2. **All git checkpoints created** (confirmed by checkpoint logs for each task)
3. **Turn state capture succeeded** despite episode linking failures — core entity data stored
4. **Shutdown errors are read-only operations** — `build_indices_and_constraints` (idempotent index creation), `node_fulltext_search`, `node_similarity_search` (search queries)
5. **No write operations failed** — episode creation warnings are supplementary data

### Conclusion

Zero data loss risk. The Graphiti knowledge graph may have incomplete episode linking for some tasks, but this is supplementary data, not critical state. All task artifacts, git state, and quality gate records are intact.

---

## Finding 7: Overall AutoBuild Reliability Assessment

**Rating**: 8.5/10

### Strengths

| Metric | Value | Assessment |
|--------|-------|------------|
| Task completion | 11/11 (100%) | Excellent |
| Clean execution | 10/11 (91%) | Very good |
| Average turns | 1.45/task | Efficient |
| Duration | 43m 35s | Reasonable for 11 tasks |
| State recovery | 1/1 success | Robust |
| Coach accuracy | 100% (all rejections valid) | Excellent |
| Quality gate effectiveness | High | Zero-test anomaly caught |

### Weaknesses

| Issue | Impact | Priority | Finding |
|-------|--------|----------|---------|
| Graphiti event loop lifecycle | Noisy logs, no functional impact | HIGH (noise) | F1 |
| `_capture_turn_state` ignores `enable_context` | 11 unnecessary Graphiti ops per run | MEDIUM | F2 |
| Direct mode doesn't produce Player report | 1 wasted turn per affected task | MEDIUM | F3 |
| Shutdown cleanup hits Lock affinity errors | Suppressed but logged | LOW | F4 |

---

## Recommendations (Revised with Source Code Evidence)

### R1: Fix `GraphitiClientFactory.get_thread_client()` Event Loop Lifecycle (HIGH)

**Problem**: [graphiti_client.py:1627-1632](guardkit/knowledge/graphiti_client.py#L1627-L1632) creates a temporary loop for `client.initialize()`, closes it, but the FalkorDB driver's internal Locks remain bound to the dead loop.

**Root Cause**: `build_indices_and_constraints()` called during `initialize()` creates Redis connection pool Locks. These Locks cannot survive loop destruction.

**Fix Options (in order of recommendation)**:

**(a) Lazy initialization within the consumer's loop (RECOMMENDED)**

Don't create a temporary loop in `get_thread_client()`. Instead, return an uninitialized client and let the consumer initialize it within their own loop context:

```python
# In get_thread_client(): Skip loop creation, mark client as "pending init"
client = GraphitiClient(config=self.config)
self._thread_local.client = client
return client

# In _get_thread_local_loader() or first use: Initialize within the active loop
if not client.is_initialized:
    await client.initialize()  # Now runs in the consumer's loop
```

This ensures all FalkorDB Locks are created on the loop that will actually use them.

**(b) Per-wave client recreation**

At the start of each `_execute_wave_parallel()`, discard old clients and create fresh ones within the wave's `asyncio.run()` loop:

```python
# At start of _execute_wave_parallel()
self._factory.reset_thread_clients()  # Clear all cached clients
```

**(c) Persistent event loop thread**

Create a single dedicated thread with its own persistent event loop for ALL Graphiti operations. All callers use `asyncio.run_coroutine_threadsafe()` to dispatch to this thread.

**Confidence**: HIGH — this is the root cause of all Lock affinity errors.

### R2: Add `enable_context` Guard to `_capture_turn_state` (MEDIUM)

**Problem**: [autobuild.py:2895](guardkit/orchestrator/autobuild.py#L2895) checks `graphiti.enabled` but not `self.enable_context`.

**Fix**: One-line change:

```python
# Line 2895: Change from:
if graphiti and graphiti.enabled:
# To:
if graphiti and graphiti.enabled and self.enable_context:
```

**Impact**: Eliminates 11 unnecessary Graphiti operations per run when health check has disabled context.

**Confidence**: HIGH — the pattern is already correctly used in `_invoke_player_safely` (line 3261) and `_get_thread_local_loader` (line 3140).

### R3: Fix Direct Mode Player Report Generation (MEDIUM)

**Problem**: Direct mode SDK invocation ([agent_invoker.py:2493-2499](guardkit/orchestrator/agent_invoker.py#L2493-L2499)) doesn't produce `player_turn_N.json`. The `_retry_with_backoff` ([agent_invoker.py:2509](guardkit/orchestrator/agent_invoker.py#L2509)) correctly fails to find it, triggering state recovery and wasting a turn.

**Fix**: After `_invoke_with_role()` completes, extract the SDK's results from its response and construct `player_turn_N.json` BEFORE attempting `_load_agent_report`:

```python
# After _invoke_with_role() (line 2499):
# 1. Extract SDK results from conversation output
sdk_report = self._extract_report_from_sdk_response(sdk_result)

# 2. Write player_turn_N.json from SDK results
if sdk_report:
    self._write_player_report_for_direct_mode(task_id, turn, sdk_report, success=True)

# 3. Now load it (will succeed immediately)
report = self._load_agent_report(task_id, turn, "player")
```

**Alternative**: Have the direct mode SDK prompt include instructions to write its report to the expected path.

**Confidence**: HIGH — the root cause is definitively not a filesystem race.

### R4: Suppress Known Shutdown Errors (LOW)

**Problem**: Shutdown produces ~20 error lines from three knowledge capture attempts.

**Fix**: Add a `shutting_down` flag to `_cleanup_thread_loaders` ([autobuild.py:3168](guardkit/orchestrator/autobuild.py#L3168)):

```python
def _cleanup_thread_loaders(self) -> None:
    self._shutting_down = True  # Set flag before cleanup
    for thread_id, (loader, stored_loop) in list(self._thread_loaders.items()):
        ...
```

Then in `_capture_turn_state`, skip when shutting down:

```python
if getattr(self, '_shutting_down', False):
    return
```

**Confidence**: HIGH — straightforward guard pattern.

### R5: Health Check Without Client Initialization (LOW)

**Problem**: `_preflight_check()` ([feature_orchestrator.py:930-1001](guardkit/orchestrator/feature_orchestrator.py#L930-L1001)) runs health check on a fully initialized client, which creates the loop contamination described in F1.

**Fix**: Split health check into two phases:
1. **Connection test**: Simple TCP/Redis ping (no Lock creation)
2. **Full initialization**: Deferred to first wave (per R1)

This makes the health check truly lightweight and non-contaminating.

**Confidence**: MEDIUM — depends on whether FalkorDB driver supports a lightweight ping without full initialization.

---

## Appendix: Error Count Summary

| Error Type | Count (mid-run) | Count (shutdown) | Total | Root Cause |
|-----------|-----------------|------------------|-------|-----------|
| "Event loop is closed" | ~11 | 3 | ~14 | F1 (1a) |
| "Lock bound to different event loop" | ~11 | 1 | ~12 | F1 (1a + 1b) |
| "no running event loop" | 0 | ~8 | ~8 | F1 (1c) |
| "Task was destroyed but pending" | 0 | 3 | 3 | F1 (1c) |
| "coroutine never awaited" | 0 | 5 | 5 | F1 (1c) |
| Episode creation warnings | ~11 | 0 | ~11 | F2 |
| **Total** | **~33** | **~20** | **~53** | |

**Note**: Mid-run errors occur once per task during `_capture_turn_state` (Finding 2). Shutdown errors occur during three knowledge capture/cleanup attempts after feature completion (Finding 4). The Episode creation warnings would be eliminated by R2 alone.

## Appendix: Recommendation Priority Matrix

| Rec | Effort | Impact | Priority | Eliminates |
|-----|--------|--------|----------|-----------|
| R1 | Medium | High | HIGH | ~26 errors (Lock + loop errors) |
| R2 | Trivial | Medium | MEDIUM | 11 Episode creation warnings |
| R3 | Medium | Medium | MEDIUM | 1 wasted turn per direct-mode task |
| R4 | Low | Low | LOW | ~20 shutdown errors |
| R5 | Medium | Low | LOW | Prevents future loop contamination |

**Quick wins**: R2 is a one-line fix. R4 is ~5 lines. Together they eliminate ~31 of ~53 errors.
**Strategic fix**: R1 is the root cause fix that eliminates the fundamental event loop lifecycle problem.
