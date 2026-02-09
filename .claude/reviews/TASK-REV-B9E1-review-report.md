# Review Report: TASK-REV-B9E1

## Executive Summary

Analysis of the second FEAT-6EDD (system-plan) AutoBuild run reveals a **single root cause** for the failure:

**The macOS `maxfiles` soft limit is 256 file descriptors** — far too low for running 3 parallel AutoBuild tasks, each of which spawns a Claude Code CLI subprocess (which itself spawns child processes), plus Neo4j connections, OpenAI HTTP connections, git operations, and file I/O.

The per-thread Graphiti migration (GTP1-GTP6) **worked correctly** — no cross-loop hangs occurred, which was the critical bug in run 1. However, it also **contributed marginally** to FD pressure by opening additional Neo4j connections (7 total vs 1 in the singleton model). The real culprit is the system ulimit, not the Graphiti threading change.

### Key Findings

| Finding | Status | Impact |
|---------|--------|--------|
| Root cause: macOS `maxfiles` soft limit = 256 | CONFIRMED | Critical |
| Per-thread Graphiti migration working correctly | CONFIRMED | Positive |
| No cross-loop hangs (BUG-1 from run 1 fixed) | CONFIRMED | Positive |
| BUG-3: Dual client storage in capture_turn_state | **NEW BUG** | Medium |
| BUG-4: Factory init race condition in Wave 1 | **NEW BUG** | Low |
| Unawaited coroutine (BUG-2 residual) | PARTIAL FIX | Low |
| Neo4j retry storm amplifies FD exhaustion | OBSERVED | Medium |
| SP-004 succeeded due to timing (late FD exhaustion) | CONFIRMED | Informational |

## Review Details

- **Mode**: Diagnostic
- **Depth**: Deep
- **Log Size**: 1,322 lines covering 5/8 tasks across 2/4 waves
- **Run Duration**: 20m 52s (12:00:33 → 12:21:25)
- **Previous Review**: TASK-REV-2AA0 (run 1 — Graphiti cross-loop hang)

---

## 1. Error Categorization

### All Errors in Output Log

| Category | Count | Error Message | Severity |
|----------|-------|---------------|----------|
| FD exhaustion (subprocess) | 2 | `OSError: [Errno 24] Too many open files` at `os.pipe()` | **Critical** |
| FD exhaustion (Neo4j connect) | ~22 | `Failed to establish connection ... [Errno 24] Too many open files` | High |
| FD exhaustion (git) | 2 | `Git change detection failed: [Errno 24] Too many open files` | Medium |
| FD exhaustion (Graphiti init) | 2 | `Graphiti factory: thread client init error: [Errno 24]` | Medium |
| Neo4j cross-loop (capture_turn_state) | 2 | `got Future <Future pending> attached to a different loop` | Low (graceful) |
| DNS resolution failure | ~8 | `Failed to resolve 'us.i.posthog.com'` | Low (telemetry) |
| Event loop cleanup | 2 | `_UnixSelectorEventLoop has no attribute '_ssock'` | Low (cosmetic) |
| Unawaited coroutine | 1 | `coroutine 'GraphitiClient.initialize' was never awaited` | Low |
| Neo4j schema notifications | ~56 | `index or constraint already exists` | Informational |

### Error Timeline

1. **12:00:33** — Feature orchestration starts, Wave 1 begins (SP-001, SP-002)
2. **12:10:32** — Wave 1 completes successfully (2/2 passed)
3. **12:10:32** — Wave 2 begins: SP-003, SP-004, SP-005 in parallel (3 SDK subprocesses + 3 Graphiti clients)
4. **~12:20:00** — SP-004 Coach approved; capture_turn_state triggers Neo4j retries → [Errno 24] appears
5. **Lines 934-966** — 11 Neo4j retry warnings with `[Errno 24]`, then DNS failures
6. **Line 1045** — SP-005: `Git change detection failed: [Errno 24]`
7. **Line 1077** — SP-005: `Graphiti factory: thread client init error: [Errno 24]`
8. **Line 1096** — SP-005: `Orchestration failed` — checkpoint `git add -A` → `os.pipe()` → `[Errno 24]`
9. **Line 1155** — SP-003: `Git change detection failed: [Errno 24]`
10. **Line 1187** — SP-003: `Graphiti factory: thread client init error: [Errno 24]`
11. **Line 1203** — SP-003: `Orchestration failed` — same checkpoint path
12. **Line 1256** — SP-004: `Graphiti factory: thread client initialized successfully` (FDs freed after SP-003/005 died)
13. **Line 1282** — SP-004: Completes successfully

---

## 2. Root Cause: `[Errno 24] Too many open files`

### The 256 FD Budget

```
macOS launchctl limit maxfiles: 256 (soft) / unlimited (hard)
kern.maxfilesperproc: 245760
```

The **soft limit of 256** is the effective per-process limit. A process can raise it to the hard limit, but GuardKit does not currently do this.

### FD Budget Analysis for Wave 2

Each parallel AutoBuild task consumes file descriptors from:

| Resource | FDs per task | Notes |
|----------|-------------|-------|
| Claude Code CLI subprocess | ~30-50 | Popen pipes (stdin/stdout/stderr) + child's own FDs |
| Neo4j bolt connection (Graphiti) | ~4-8 | TCP socket + TLS + internal pipes |
| OpenAI/httpx connections | ~4-6 | HTTPS connections for embeddings |
| Git operations | ~6-10 | Subprocess pipes per git command |
| Python runtime | ~10-15 | Logging, imports, stdlib |
| Event loop self-pipe | ~2 | asyncio selector event loop |

**Approximate total per task**: 60-90 FDs

**Wave 2 (3 parallel tasks)**: 180-270 FDs
**Plus shared resources**: Python runtime, logging, parent process = ~30-50
**Total estimated**: 210-320 FDs
**Available**: 256

The 256 FD limit is at the **exact breaking point** for 3 parallel tasks.

### Why Wave 1 Succeeded

Wave 1 ran only 2 parallel tasks (SP-001, SP-002), and SP-002 had `factory=None` (no Graphiti client). Budget: ~150-180 FDs — comfortably under 256.

### Crash Point

Both SP-003 and SP-005 crashed at identical locations:

```
autobuild.py:1526 → _loop_phase()
  → checkpoint_manager.create_checkpoint()
    → _execute_git_checkpoint()
      → git_executor.execute(["git", "add", "-A"])
        → subprocess.run() → Popen() → _get_handles()
          → os.pipe()  ← OSError: [Errno 24]
```

The crash occurs **after** the Player and Coach both completed successfully — the orchestrator fails when trying to create a git checkpoint (which requires opening a subprocess to run `git add`).

### Neo4j Retry Amplification

When FDs approach 256, Neo4j connection attempts fail with `[Errno 24]`. The Neo4j driver retries these connections (with ~1s exponential backoff), and each retry attempt tries to open new sockets, further amplifying the FD pressure. 11 retry warnings were logged before the system stabilized (lines 934-966).

After the retries exhaust the Neo4j retry budget, DNS resolution also starts failing (`[Errno 8] nodename nor servname provided, or not known`), suggesting the system's DNS resolver socket cache is also affected by FD exhaustion.

---

## 3. Per-Thread Graphiti Migration Assessment (GTP Fixes)

### GTP1: GraphitiClientFactory — WORKING CORRECTLY

Evidence:
- **7 "Connected to Neo4j" messages** — each per-thread client successfully connected
- **3 "thread client initialized successfully" messages** — factory lazy-init worked for Wave 1 threads and SP-004
- **2 "thread client init error: [Errno 24]"** — SP-003 and SP-005 thread clients failed due to FD exhaustion (NOT a factory bug)
- **1 late "thread client initialized successfully"** at line 1256 — SP-004's client initialized after SP-003/005 freed their FDs

### GTP2: AutoBuild Per-Thread Migration — WORKING CORRECTLY

Evidence:
- All 3 Wave 2 tasks initialized with `factory=available` (line 517/521/525)
- `Stored Graphiti factory for per-thread context loading` logged 3 times (one per task)
- Per-thread context loaders created on unique threads: `thread 13035925504`, `thread 6165262336`, `thread 6148435968`

### GTP3: capture_turn_state Fix — PARTIAL FIX (cross-loop errors remain due to BUG-3)

Evidence at line 447:
```
ERROR:graphiti_core.driver.neo4j_driver:Error executing Neo4j query:
Task <Task pending name='Task-462' coro=<capture_turn_state() running at ...turn_state_operations.py:108>>
got Future <Future pending> attached to a different loop
```

This is `capture_turn_state` for SP-001 in Wave 1. The GTP3 fix correctly replaced `asyncio.create_task()` with `loop.run_until_complete()` — the scheduling mechanism is now correct. However, deep verification revealed the root cause is **BUG-3 (dual client storage)**: `_capture_turn_state()` retrieves its Graphiti client via `self._factory.get_thread_client()` (threading.local storage), which is a different storage path from `_get_thread_local_loader()` (dict storage at `self._thread_loaders`). The correctly-initialized client from `_get_thread_local_loader` is invisible to `get_thread_client()`, so a new client is created via `asyncio.run()` (temporary loop), and its Neo4j driver is bound to that now-dead loop. See Section 7a for full analysis.

**Impact**: Low per-occurrence (graceful degradation), but occurs on **every** capture_turn_state call in worker threads. Also creates unnecessary Neo4j connections, adding ~4-8 FDs per redundant client.

### GTP4: Defensive Timeout — IN PLACE

Evidence:
- `task_timeout=2400s` logged at startup (line 3)
- `Starting Wave Execution (task timeout: 40 min)` displayed (line 51)
- No timeout triggered (tasks either completed or failed via [Errno 24] before 40 min)

### GTP5 (call-site migration) and GTP6 (docs) — Not directly observable in logs, but no issues detected.

### Migration Impact on FD Budget

The per-thread model creates **more** Neo4j connections than the singleton model:
- **Singleton (run 1)**: 1 Neo4j connection shared (but caused cross-loop hangs)
- **Per-thread (run 2)**: Up to 7 Neo4j connections (2 Wave 1 threads + 3 Wave 2 threads + capture_turn_state + lazy-init)

Each Neo4j connection uses ~4-8 FDs (TCP socket + TLS + internal buffers). The per-thread model adds approximately **24-48 extra FDs** compared to a singleton.

**Verdict**: The per-thread migration **is correct and necessary** (it fixed the critical hang from run 1), but it does contribute to FD pressure. The right fix is raising the ulimit, not reverting to the singleton.

---

## 4. Cross-Loop Errors Assessment

### Run 1 (TASK-REV-2AA0): 159 cross-loop errors → infinite hang
### Run 2 (this review): 2 cross-loop errors → graceful degradation, no hang

The cross-loop errors in run 2 are limited to `capture_turn_state` (SP-001 Wave 1), which uses the factory's client (initialized on the main thread's loop) from a worker thread. This is a residual issue from the factory's `get_thread_client()` code path when the thread has a running async loop — it defers initialization but the existing client's driver is bound to a different loop.

**This is NOT the same bug as run 1.** Run 1's cross-loop errors were in `graphiti-core search()` which caused silent hangs. Run 2's are in `capture_turn_state()` which degrades gracefully.

---

## 5. SP-004 Success Analysis

### Why SP-004 Succeeded While SP-003/SP-005 Failed

**Timeline evidence:**

1. All 3 tasks started at 12:10:32 (within 7ms of each other)
2. SP-004's Player completed first: `SDK completed: turns=31` (line 897, ~10 min runtime)
3. SP-005's Player completed second: `SDK completed: turns=36` (line 1040, ~10 min runtime)
4. SP-003's Player completed last: `SDK completed: turns=50` (line 1150, ~11 min runtime, hit max turns)

**FD exhaustion timing:**

The [Errno 24] errors first appear at line 934 — this is **after SP-004's Coach completed** but **during SP-004's capture_turn_state**. By this point:
- SP-004: Player done, Coach done, entering checkpoint phase
- SP-005: Player still running (SDK active)
- SP-003: Player still running (SDK active)

SP-004 got lucky: its checkpoint (`git add`, `git commit`) executed **before** FDs were fully exhausted. SP-005 and SP-003 hit the checkpoint **after** FD exhaustion had taken hold.

**Key insight:** SP-004 succeeded because:
1. It had the fewest SDK turns (31 vs 36/50), so it completed first
2. Its checkpoint ran before the Neo4j retry storm consumed remaining FDs
3. After SP-005's orchestration failed (line 1096), some FDs were freed
4. SP-004's Graphiti thread client then initialized successfully (line 1256)

### SP-004 Completed Successfully Despite 0 Categories

All 3 Wave 2 tasks retrieved `0 categories, 0/5200 tokens` from Graphiti context. This means the knowledge graph had no relevant entries for these tasks. The context loading worked correctly — it just returned empty results.

---

## 6. Comparison with Run 1 (TASK-REV-2AA0)

| Aspect | Run 1 | Run 2 |
|--------|-------|-------|
| **Failure mode** | Infinite hang (killed after ~20 min) | Fast fail with [Errno 24] (~11 min) |
| **Root cause** | Shared Graphiti singleton + cross-loop hang in graphiti-core | macOS ulimit 256 FD soft limit |
| **Cross-loop errors** | 159 (cascading, caused hang) | 2 (isolated, graceful degradation) |
| **Unawaited coroutines** | Yes (BUG-2) | 1 (residual in GraphitiClient.initialize) |
| **Wave 1** | 2 passed | 2 passed (identical) |
| **Wave 2** | 1 passed (SP-003), 2 hung (SP-004, SP-005) | 1 passed (SP-004), 2 failed (SP-003, SP-005) |
| **Graphiti context** | Some categories retrieved | 0 categories (empty knowledge graph?) |
| **GTP fixes effective?** | N/A (pre-fix) | YES — no hangs, per-thread clients work |
| **Recoverability** | No (required kill -9) | Yes (fast fail, can resume) |

**Progress assessment**: Run 2 is a significant improvement over run 1:
- The critical hang is fixed
- Failures are fast and recoverable
- The root cause is an environment configuration issue, not a code bug

---

## 7. Residual Issues and Newly Discovered Bugs

### 7a. BUG-3: Dual Client Storage Paths in capture_turn_state (NEW)

**Severity: Medium** — causes cross-loop errors on every `capture_turn_state` call in worker threads.

Deep verification revealed that `_capture_turn_state()` and `_get_thread_local_loader()` use **two completely separate client storage mechanisms**, so a client initialized on the correct loop by one is invisible to the other:

1. **`_get_thread_local_loader()`** (autobuild.py:2652-2674): Creates a client via `self._factory.create_client()` + `loop.run_until_complete(client.initialize())` on the worker thread's event loop. Stores the resulting loader in `self._thread_loaders[thread_id]` (a Python dict keyed by `threading.get_ident()`).

2. **`_capture_turn_state()`** (autobuild.py:2419-2421): Gets a client via `self._factory.get_thread_client()` which uses `threading.local()` storage (`self._thread_local.client`). This is a **completely separate** storage mechanism from `_thread_loaders`.

Because the client created by `_get_thread_local_loader` is stored in `_thread_loaders` but NOT in `_factory._thread_local`, when `_capture_turn_state` calls `get_thread_client()`, it finds no client in thread-local and creates a **new** one. This new client is initialized via `asyncio.run()` (graphiti_client.py:1479), which:
1. Creates a temporary event loop
2. Initializes the Neo4j driver (bound to that temporary loop)
3. Destroys the temporary loop
4. Returns the client (whose Neo4j driver is now bound to a dead loop)

Then `_capture_turn_state` at line 2427 calls `asyncio.get_event_loop()`, which returns the worker thread's actual loop (a different one), and calls `loop.run_until_complete(capture_turn_state(graphiti, entity))`. The Neo4j driver tries to create futures on the dead loop → cross-loop error.

**Fix**: In `_capture_turn_state()`, retrieve the client from `self._thread_loaders[thread_id]` (same storage as `_get_thread_local_loader`) instead of from `self._factory.get_thread_client()`. Or alternatively, have `_get_thread_local_loader()` also register its client with `self._factory.set_thread_client()`.

### 7b. BUG-4: Factory Initialization Race Condition in Wave 1 (NEW)

**Severity: Low** — causes SP-002 to run without Graphiti context in Wave 1.

The FeatureOrchestrator does NOT call `init_graphiti()` before launching tasks. The first `AutoBuildOrchestrator.__init__()` to call `get_graphiti()` triggers lazy initialization of the global factory via `_try_lazy_init()`. In parallel Wave 1:

- SP-001 and SP-002 both start via `asyncio.to_thread()` in parallel
- SP-002's `__init__` ran first and called `get_graphiti()` → triggered lazy init → but `get_factory()` returned `None` at that point (factory not yet created because `_try_lazy_init()` defers in async context)
- SP-001's `__init__` ran after the factory was available → got `factory=available`

Evidence from logs: SP-002 shows `factory=None`, SP-001 shows `factory=available`.

**Impact**: Low. SP-002 ran without Graphiti context but completed successfully. The race only affects the first wave when no `init_graphiti()` is called before task dispatch.

**Fix**: Call `init_graphiti()` in `FeatureOrchestrator.__init__()` before dispatching any tasks, ensuring the factory is ready for all parallel workers.

### 7c. Unawaited Coroutine in GraphitiClient.initialize (Line 1089)

```
graphiti_client.py:1489: RuntimeWarning: coroutine 'GraphitiClient.initialize' was never awaited
```

This occurs in `get_thread_client()` at the `except Exception` handler (line 1487-1489). When `asyncio.run(client.initialize())` fails with `[Errno 24]`, the event loop's self-pipe (`os.pipe()`) cannot be created. `asyncio.run()` raises the error before the coroutine is scheduled. The coroutine object `client.initialize()` was created as a Python object but never started → Python's GC emits `RuntimeWarning` when collecting it.

**Impact**: Low. Cosmetic warning that only appears when FD exhaustion prevents initialization. No resource leak.

**Fix**: Wrap in explicit coroutine cleanup:
```python
except Exception as e:
    # asyncio.run() may have failed before scheduling the coroutine.
    # Close the unawaited coroutine to suppress RuntimeWarning.
    coro = client.initialize()
    coro.close()
    logger.info(f"Graphiti factory: thread client init error: {e}")
    return None
```
Note: This requires restructuring to separate coroutine creation from `asyncio.run()` invocation.

### 7d. Event Loop Cleanup Warning

```
AttributeError: '_UnixSelectorEventLoop' object has no attribute '_ssock'
```

This occurs when `asyncio.run()` in `get_thread_client()` creates and tears down an event loop, but the cleanup happens after FD exhaustion has corrupted the event loop's internal state (the self-pipe couldn't be created).

**Impact**: None (cosmetic during error path).

---

## 8. Fix Recommendations (Priority Ordered)

### P0 (Critical) — Raise macOS File Descriptor Limit

**Problem**: macOS default `maxfiles` soft limit is 256, insufficient for parallel AutoBuild.

**Fix**: Add `resource.setrlimit()` at process startup.

**Implementation**:
```python
import resource
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
if soft < 4096:
    resource.setrlimit(resource.RLIMIT_NOFILE, (min(4096, hard), hard))
```

**Location options:**
1. **In `FeatureOrchestrator.__init__`** (recommended) — targeted, only affects parallel execution
2. **In `guardkit` CLI entrypoint** — broader scope, protects all commands
3. **Both** — belt and suspenders

**Estimated FD budget at 4096:**
- 3 parallel tasks × ~90 FDs = ~270
- Shared resources: ~50
- Total: ~320 / 4096 = 7.8% utilization (comfortable)

### P1 (Medium) — Fix capture_turn_state Dual Client Storage (BUG-3)

**Problem**: `_capture_turn_state()` calls `self._factory.get_thread_client()` which uses `threading.local()` storage, but `_get_thread_local_loader()` stores its client in `self._thread_loaders[thread_id]` (a dict). These are independent storage mechanisms. The client in `_thread_loaders` was initialized on the correct loop, but `_capture_turn_state` can't see it and creates a new client via `asyncio.run()` (temporary loop) → cross-loop error every time.

**Fix options (choose one):**
1. **(Recommended)** In `_capture_turn_state()`, retrieve the Graphiti client from `self._thread_loaders[thread_id].graphiti` instead of from `self._factory.get_thread_client()`. This reuses the client that was already correctly initialized on the worker thread's loop.
2. In `_get_thread_local_loader()`, after creating the client, also call `self._factory.set_thread_client(client)` to register it in both storage mechanisms.

**Files**: `guardkit/orchestrator/autobuild.py` lines 2419-2424

### P2 (Low) — Pre-initialize Graphiti Factory Before Parallel Dispatch (BUG-4)

**Problem**: No `init_graphiti()` call before parallel task dispatch. First task to call `get_graphiti()` triggers lazy-init, but in worker threads `_try_lazy_init()` defers connection (detects running loop from `asyncio.to_thread()`). Race condition causes SP-002 to see `factory=None`.

**Fix**: Call `init_graphiti()` in `FeatureOrchestrator` (or `_execute_wave_parallel()`) BEFORE dispatching any tasks via `asyncio.to_thread()`. This ensures the global factory is ready for all workers.

**Files**: `guardkit/orchestrator/feature_orchestrator.py`

### P3 (Low) — Suppress Neo4j Retry Storm During FD Exhaustion

**Problem**: When FDs are exhausted, Neo4j retries 11 times (~10s total), each attempt wasting time and potentially preventing FD recovery.

**Fix**: Catch `[Errno 24]` specifically in the Graphiti client layer and fail fast instead of retrying. The Neo4j driver's retry logic can be configured via `max_transaction_retry_time`.

### P4 (Cosmetic) — Fix Unawaited Coroutine Warning

**Problem**: `get_thread_client()` line 1479-1489 can produce `RuntimeWarning: coroutine was never awaited` when `asyncio.run()` fails before scheduling the coroutine (e.g., `os.pipe()` fails with Errno 24 during event loop self-pipe creation).

**Fix**: Restructure `get_thread_client()` to separate coroutine creation from `asyncio.run()`:
```python
coro = client.initialize()
try:
    success = asyncio.run(coro)
    ...
except Exception as e:
    coro.close()  # Suppress RuntimeWarning
    logger.info(f"Graphiti factory: thread client init error: {e}")
    return None
```

---

## 9. Assessment Summary

### Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| Categorise all errors in the output log | DONE (Section 1) |
| Determine root cause of [Errno 24] | DONE — macOS maxfiles soft limit = 256 (Section 2) |
| Assess per-thread Graphiti migration (GTP fixes) | DONE — Working correctly (Section 3) |
| Determine if per-thread clients contribute to FD exhaustion | DONE — Marginal contribution (+24-48 FDs), not primary cause (Section 3) |
| Check for cross-loop errors | DONE — 2 isolated, graceful (vs 159 in run 1) (Section 4) |
| Check for unawaited coroutine warnings | DONE — 1 residual in error path (Section 7a) |
| Verify defensive timeout is in place | DONE — 2400s/40min confirmed (Section 3) |
| Compare with first run (TASK-REV-2AA0) | DONE (Section 6) |
| Provide fix recommendations | DONE — 5 fixes, P0-P4 priority (Section 8) |
| Assess whether ulimit needs adjusting | DONE — YES, raise to 4096 minimum (Section 8) |

### Overall Assessment

The GTP fixes (FEAT-C90E) **successfully resolved** the critical cross-loop hang from run 1. The second run failed primarily due to an **environment limitation** (macOS FD soft limit = 256), not a fundamental code bug.

However, deep verification uncovered two additional code-level bugs:
- **BUG-3** (dual client storage): `_capture_turn_state` creates redundant Graphiti clients because it uses a different storage mechanism than `_get_thread_local_loader`, causing cross-loop errors on every capture call.
- **BUG-4** (factory race): No pre-initialization before parallel dispatch means the first wave has a race condition where some tasks may not get the Graphiti factory.

**Recommendation**: Implement P0 (raise FD limit) + P1 (fix dual storage) together, then re-run FEAT-6EDD. P0 alone would allow tasks to complete, but P1 eliminates needless cross-loop errors and redundant Neo4j connections. P2-P4 are quality improvements.
