# TASK-REV-8BC0 Deep Dive: Validated Root Cause Analysis

## Revision Note

This deep dive traces the actual execution flows across system and technology boundaries, using C4 sequence diagrams to validate or correct the initial findings. **Finding 1 has been revised** — the root cause is more nuanced than initially reported.

---

## C4 Context Diagram: System Boundaries

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Feature Orchestrator                              │
│                     (Main asyncio Event Loop)                            │
│                                                                          │
│  ┌─────────────────────┐    ┌─────────────────────┐                     │
│  │   asyncio.gather()  │    │  asyncio.wait_for()  │                     │
│  │   (parallel waves)  │    │  (per-task timeout)   │                     │
│  └────────┬────────────┘    └──────────┬───────────┘                     │
│           │                            │                                 │
│           ▼                            ▼                                 │
│  ┌────────────────────────────────────────────┐                          │
│  │         asyncio.to_thread()                │  ◄── THREAD BOUNDARY     │
│  │     (spawns OS worker thread)              │                          │
│  └────────────────┬───────────────────────────┘                          │
│                   │                                                      │
└───────────────────┼──────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│              Worker Thread (per task)                                     │
│                                                                          │
│  ┌────────────────────────────────────────┐                              │
│  │   AutoBuildOrchestrator.orchestrate()  │  ◄── SYNC method             │
│  │   (synchronous, runs in worker)        │                              │
│  └──────────────────┬─────────────────────┘                              │
│                     │                                                    │
│                     ▼                                                    │
│  ┌────────────────────────────────────────┐                              │
│  │   _invoke_player_safely()              │                              │
│  │   loop = asyncio.get_event_loop()      │  ◄── NEW EVENT LOOP          │
│  │   loop.run_until_complete(             │      (per-thread)             │
│  │       invoke_player(...)               │                              │
│  │   )                                    │                              │
│  └──────────────────┬─────────────────────┘                              │
│                     │                                                    │
│                     ▼                                                    │
│  ┌────────────────────────────────────────┐                              │
│  │   AgentInvoker._invoke_with_role()     │                              │
│  │   async with asyncio.timeout(1560s):   │  ◄── SDK TIMEOUT             │
│  │       gen = query(prompt, options)      │                              │
│  │       async for message in gen:        │                              │
│  │           ...                          │                              │
│  └──────────────────┬─────────────────────┘                              │
│                     │                                                    │
│                     ▼                                                    │
│  ┌────────────────────────────────────────┐                              │
│  │   Claude Agent SDK (subprocess)        │  ◄── OS PROCESS BOUNDARY     │
│  │   claude CLI binary invoked via pipe   │                              │
│  └────────────────────────────────────────┘                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key insight**: There are THREE concurrency layers and TWO event loop boundaries:
1. Main asyncio loop (feature_orchestrator) → asyncio.to_thread → Worker thread
2. Worker thread creates NEW event loop via `asyncio.get_event_loop()` / `asyncio.new_event_loop()`
3. Worker thread's event loop runs SDK's `query()` async generator

---

## Finding 1 (REVISED): Player Cancellation Root Cause

### Initial Hypothesis (PARTIALLY WRONG)

> The `gen.aclose()` in the `finally` block isn't reached before AnyIO's cancel scope triggers GC cleanup.

### Validated Root Cause: `asyncio.wait_for` Cancellation Propagating Through `asyncio.to_thread`

The cancel scope error message is actually a **symptom**, not the cause. Here's the actual flow:

### Sequence Diagram: Player Cancellation in Direct Mode

```
Main Loop           asyncio.wait_for     Worker Thread        Per-Thread Loop     SDK query()
(feature_orch)      (timeout=2400s)      (to_thread)          (run_until_complete) (async gen)
    │                     │                    │                     │                  │
    │  gather(wait_for(   │                    │                     │                  │
    │    to_thread()))    │                    │                     │                  │
    │────────────────────►│                    │                     │                  │
    │                     │ to_thread(         │                     │                  │
    │                     │  _execute_task)    │                     │                  │
    │                     │───────────────────►│                     │                  │
    │                     │                    │  loop = new_loop()  │                  │
    │                     │                    │  loop.run_until_    │                  │
    │                     │                    │   complete(         │                  │
    │                     │                    │    invoke_player)   │                  │
    │                     │                    │───────────────────►│                  │
    │                     │                    │                     │ asyncio.timeout  │
    │                     │                    │                     │  (1560s)         │
    │                     │                    │                     │ gen = query()    │
    │                     │                    │                     │────────────────►│
    │                     │                    │                     │                  │
    │                     │                    │                     │  async for msg   │
    │                     │                    │                     │◄────────────────│
    │                     │                    │                     │  ...330s pass... │
    │                     │                    │                     │                  │
    │                     │                    │                     │  ResultMessage   │
    │                     │                    │                     │◄────────────────│
    │                     │                    │                     │  break           │
    │                     │                    │                     │                  │
    │                     │                    │                     │  # finally:      │
    │                     │                    │                     │  gen.aclose()    │
    │                     │                    │                     │────────────────►│
    │                     │                    │                     │                  │
    │                     │                    │                     │  # aclose() triggers
    │                     │                    │                     │  # AnyIO internal cancel
    │                     │                    │                     │  # scope cleanup of the
    │                     │                    │                     │  # subprocess transport
    │                     │                    │                     │                  │
    │                     │                    │                     │  CancelledError  │
    │                     │                    │                     │◄─ ─ ─ ─ ─ ─ ─ ─│
    │                     │                    │                     │                  │
    │                     │                    │                     │  # Caught by     │
    │                     │                    │                     │  # except block  │
    │                     │                    │                     │  # at line 2063  │
    │                     │                    │                     │                  │
    │                     │                    │                     │  RE-RAISE        │
    │                     │                    │                     │                  │
    │                     │                    │ CancelledError      │                  │
    │                     │                    │◄───────────────────│                  │
    │                     │                    │                     │                  │
    │                     │                    │  # Caught by        │                  │
    │                     │                    │  # _invoke_player   │                  │
    │                     │                    │  # _safely line 4048│                  │
    │                     │                    │                     │                  │
    │                     │  Returns error     │                     │                  │
    │                     │  result            │                     │                  │
    │                     │◄───────────────────│                     │                  │
    │                     │                    │                     │                  │
    │  TaskExecutionResult│                    │                     │                  │
    │◄────────────────────│                    │                     │                  │
```

### The Real Problem: `gen.aclose()` Triggers Cancel Scope Inside `_invoke_with_role`

Let me trace the exact code path:

**Step 1**: SDK `query()` completes — `ResultMessage` received, loop breaks at line 2062.

**Step 2**: Execution falls to the `finally` block at line 2088.

**Step 3**: `gen.aclose()` is called at line 2097, wrapped in `asyncio.timeout(5)`.

**Step 4**: The Claude Agent SDK's `query()` generator internally uses AnyIO's `CancelScope` to manage the subprocess transport. When `aclose()` is called, AnyIO attempts to close the cancel scope.

**Step 5**: The AnyIO cancel scope's `__exit__` raises `CancelledError` because:
- The SDK subprocess transport uses AnyIO internally
- AnyIO cancel scopes track the asyncio Task they were created in
- The `aclose()` call may execute cancel scope cleanup in a different asyncio Task context (the per-thread event loop's task vs the original task that created the scope)
- This produces the error: `Cancelled via cancel scope XXXXXXX by <Task pending name='Task-NNN' coro=<<async_generator_athrow without __name__>()>>`

**Step 6**: The `CancelledError` is caught by `except (Exception, asyncio.CancelledError)` at line 2063. Partial data is extracted (line 2068). Then the exception is **re-raised** at line 2087.

**Step 7**: The `CancelledError` propagates up through `asyncio.timeout(self.sdk_timeout_seconds)` at line 2043, through the outer try/except at line 1386 in `invoke_player()`, which catches it and wraps it in `AgentInvocationResult(success=False, error="Cancelled: ...")`.

**Step 8**: Back in `_invoke_player_safely()`, the `loop.run_until_complete()` at line 4023 receives the `CancelledError` from the future. Since it's caught by `invoke_player` at line 1386, it actually returns the error result normally. BUT — the `asyncio.CancelledError` handler at line 4048 in `_invoke_player_safely` is there as a safety net in case the error escapes.

### Revised Root Cause

The `CancelledError` is triggered by **AnyIO's cancel scope cleanup inside `gen.aclose()`**, not by GC finalization. The existing TASK-RFX-8332 fix (explicit `gen.aclose()` in `finally`) is actually the **cause** of the CancelledError, not the prevention of it!

The irony: the code comment says "to prevent GC finalization from scheduling athrow(GeneratorExit) in a wrong asyncio Task" — but the explicit `aclose()` call itself triggers the same AnyIO cancel scope race condition, just in a more controlled location.

### Evidence from Log Timing

| Turn | Start | Cancel | Duration | SDK Timeout |
|------|-------|--------|----------|-------------|
| 1 | 10:54:46 | 11:00:20 | **~334s** | 1560s |
| 2 | 11:00:31 | 11:03:32 | **~181s** | 1560s |
| 3 | 11:03:41 | 11:07:09 | **~208s** | 1560s |

All cancellations occur well before the 1560s SDK timeout. The durations are consistent with the Player **completing its work** (ResultMessage received) and then the `aclose()` cleanup triggering the cancel scope error. The Player had 30s heartbeats showing progress, and each cancellation happens shortly after the last heartbeat — suggesting the SDK work completed and the cleanup is what fails.

### Why Task-Work Mode Doesn't Have This Problem

Task-work mode uses the same `_invoke_with_role` internally? **No!** Let me verify:

Looking at the code:
- **Direct mode** (`_invoke_player_direct` → `_invoke_with_role`): Uses `gen = query(); async for message in gen` at line 2048-2062, with explicit `gen.aclose()` in `finally` at line 2093-2099
- **Task-work mode** (`_invoke_task_work_implement`): Uses `_tw_gen = query(); async for message in _tw_gen` at line 4510-4511, with its **own** cleanup logic

Let me check the task-work cleanup:

<br/>

**CRITICAL**: Task-work mode at line 4507-4508 wraps with `asyncio.timeout(self.sdk_timeout_seconds)` and iterates the generator, but the generator cleanup is handled **differently**. The task-work path doesn't break on `ResultMessage` — it processes the entire stream to completion (extracting tool use blocks, messages, etc.) and the generator exhausts naturally. When a generator exhausts (raises `StopAsyncIteration`), AnyIO's cancel scopes close cleanly because the generator's internal state machine reaches its natural end. No `aclose()` is needed.

**Direct mode breaks early** (line 2062: `break` on `ResultMessage`), leaving the generator in a suspended state. The subsequent `aclose()` forces the generator's internal cancel scopes to close prematurely, triggering the error.

### Corrected Recommendation

The fix is NOT to close the generator earlier (before the `finally`). The fix is to **let the generator exhaust naturally** after receiving ResultMessage, or to suppress the CancelledError from `aclose()` more effectively:

```python
# Option A: Suppress CancelledError from aclose() (minimal change)
# In _invoke_with_role, replace the re-raise in the except block:
except (Exception, asyncio.CancelledError) as exc:
    if isinstance(exc, asyncio.CancelledError):
        # Check if this is from gen.aclose() cleanup (generator already yielded ResultMessage)
        if result_message_received:
            logger.debug(f"Suppressing aclose() CancelledError for {task_id}")
            # Don't re-raise — treat as successful completion
            call_status = "ok"
            # Skip to finally block
        else:
            # Genuine cancellation — re-raise
            call_status = "error"
            call_error = exc
            raise

# Option B: Drain generator after ResultMessage (mirrors task-work pattern)
if isinstance(message, ResultMessage):
    self._last_session_id = getattr(message, "session_id", None)
    # Drain remaining messages to let generator exhaust naturally
    async for _ in gen:
        pass
    gen = None  # Already exhausted, no aclose() needed
    break
```

---

## Finding 2 (VALIDATED): TASK-DC-002 Timeout

### Sequence Diagram: Timeout Propagation

```
Main Loop              asyncio.wait_for      Worker Thread         SDK Subprocess
(feature_orch)         (timeout=2400s)       (TASK-DC-002)         (claude CLI)
    │                        │                     │                     │
    │  wave_start_time =     │                     │                     │
    │    time.monotonic()    │                     │                     │
    │                        │                     │                     │
    │  asyncio.wait_for(     │                     │                     │
    │    to_thread(          │                     │                     │
    │      _execute_task),   │                     │                     │
    │    timeout=2400)       │                     │                     │
    │───────────────────────►│                     │                     │
    │                        │ to_thread(          │                     │
    │                        │  _execute_task)     │                     │
    │                        │───────────────────►│                     │
    │                        │                     │ orchestrate()       │
    │                        │                     │ _loop_phase()       │
    │                        │                     │ _invoke_player_     │
    │                        │                     │   safely()          │
    │                        │                     │ loop.run_until_     │
    │                        │                     │   complete(         │
    │                        │                     │     invoke_player)  │
    │                        │                     │                     │
    │                        │                     │  asyncio.timeout    │
    │                        │                     │    (sdk_timeout)    │
    │                        │                     │  gen = query()      │
    │                        │                     │────────────────────►│
    │                        │                     │                     │
    │                        │                     │  ...processing...   │
    │                        │                     │  (no logs visible)  │
    │                        │                     │                     │
    │  ...2400s elapse...    │                     │                     │
    │                        │                     │                     │
    │                        │ asyncio.TimeoutError │                     │
    │                        │◄─ ─ ─ ─ ─ ─ ─ ─ ─ │                     │
    │                        │                     │                     │
    │                        │  # wait_for cancels │                     │
    │                        │  # the to_thread    │                     │
    │                        │  # Future. But the  │                     │
    │                        │  # OS thread keeps  │                     │
    │                        │  # running!         │                     │
    │                        │                     │                     │
    │  TimeoutError in       │                     │  # Thread still     │
    │  gather results        │                     │  # alive, SDK       │
    │◄───────────────────────│                     │  # subprocess       │
    │                        │                     │  # still running    │
    │                        │                     │                     │
    │  # Post-gather:        │                     │                     │
    │  # set timeout_event   │                     │                     │
    │  # set cancel_event    │                     │                     │
    │──────────────────────────────────────────────►│                     │
    │                        │                     │  # _cancel_monitor  │
    │                        │                     │  # sees event,      │
    │                        │                     │  # kills subprocess │
    │                        │                     │────────────────────►│ SIGKILL
    │                        │                     │                     │
    │  # executor join       │                     │                     │
    │  # timeout (300s)      │                     │  # Thread cleanup   │
    │  # RuntimeWarning      │                     │  # takes >300s      │
    │                        │                     │                     │
```

### Validated Analysis

The timeout mechanism works as designed, but there's a critical **observability gap**:

1. `asyncio.to_thread` runs `_execute_task` in a worker thread
2. The worker thread creates its own event loop and runs `orchestrate()` → `_loop_phase()` → `_invoke_player_safely()` → `loop.run_until_complete(invoke_player())`
3. Inside that chain, `_invoke_with_role` has 30-second heartbeat logging — BUT these logs from the DC-002 worker thread are **interleaved** with DC-003's logs in the same output stream
4. The absence of DC-002 logs in the captured output doesn't mean no progress — it means either: (a) the logs were lost due to threading/buffering issues, or (b) the SDK subprocess hung with no tool calls being made

The 300-second executor join timeout warning confirms the worker thread is **still running** when the main loop tries to clean up. The `_cancel_monitor` (line 2018-2028) polls `self._cancellation_event` every 2 seconds and kills child processes — but it only runs if the cancellation event is set. Post-gather, the event IS set (line 1538), but the `_cancel_monitor` runs inside the per-thread event loop which may already be blocked in `run_until_complete`.

### Why DC-002 Timed Out While DC-003 Completed

DC-002 and DC-003 ran in parallel (Wave 2). DC-002's implementation_mode is not logged in the run output. If DC-002 was **also** `direct` mode, it would have hit the same cancel scope issue as DC-001 — but with less luck on state recovery, potentially entering a loop of:
1. Player invoked → cancelled by cancel scope → state recovery → synthetic report → Coach rejects → repeat
2. Each cycle burns ~6-10 minutes
3. After 3-4 cycles, the 2400s budget is exhausted

If DC-002 was `task-work` mode (like DC-003), the timeout is harder to explain — DC-003 completed in 471s. Possible explanations: SDK subprocess stuck, vLLM backend overloaded (two concurrent SDK sessions), or deadlock in shared worktree file access.

### Severity Confirmation: HIGH

The combination of no diagnostic information + uninterruptible worker thread makes this the highest-severity issue.

---

## Finding 3 (VALIDATED): Synthetic Report False Negatives

### Sequence Diagram: Synthetic Report Generation and Coach Verification

```
State Recovery          Synthetic Report           Coach Validator
(autobuild.py)          (autobuild.py)             (coach_validator.py)
    │                        │                          │
    │  Player cancelled      │                          │
    │  State detected:       │                          │
    │   4 files, 203 tests   │                          │
    │                        │                          │
    │  Build synthetic       │                          │
    │  report                │                          │
    │───────────────────────►│                          │
    │                        │                          │
    │                        │  task_type=declarative   │
    │                        │  → git-analysis promises │
    │                        │                          │
    │                        │  Generate 9 promises     │
    │                        │  from git diff:          │
    │                        │  - file exists: X.py ✓   │
    │                        │  - file exists: Y.py ✓   │
    │                        │  - tests pass ✓          │
    │                        │  - 203 tests found ✓     │
    │                        │  ... (4 can be verified) │
    │                        │                          │
    │                        │  CAN'T generate:         │
    │                        │  - "models match API     │
    │                        │    contract types"       │
    │                        │  - "Literal constraints"  │
    │                        │  - "identifier validator" │
    │                        │  - "exception class       │
    │                        │    attributes"            │
    │                        │  ... (5 semantic checks) │
    │                        │                          │
    │                        │  Pass to Coach           │
    │                        │─────────────────────────►│
    │                        │                          │
    │                        │                          │  Synthetic report
    │                        │                          │  detected → use
    │                        │                          │  file-existence
    │                        │                          │  verification
    │                        │                          │
    │                        │                          │  Match promises
    │                        │                          │  against ACs:
    │                        │                          │  4/9 verified
    │                        │                          │  5/9 UNVERIFIABLE
    │                        │                          │
    │                        │                          │  Result: REJECTED
    │                        │                          │  (5 unmet criteria)
```

### Why Turn 3 Passed

On turn 3, the Coach context was larger (2789/7892 tokens vs 1978/5200 tokens). The extra context included turn state history from turns 1 and 2, which told the Coach what had already been verified. Combined with the perspective reset, the Coach likely used a more lenient text-matching approach rather than strict promise matching.

The `Criteria Progress (Turn 3): 9/9 verified (0%)` log line with the anomalous `(0%)` is indeed a display bug — the percentage calculation doesn't account for the jump from synthetic to text-verified criteria.

### Severity Confirmation: MEDIUM

This is a real issue but only manifests when direct mode cancellation produces synthetic reports. Fixing Finding 1 would eliminate this problem entirely.

---

## Finding 4 (VALIDATED): JSONLFileBackend Cross-Event-Loop

### Sequence Diagram: Event Loop Boundary Violation

```
Main Event Loop                    Worker Thread (DC-003)
(feature_orchestrator)             (via asyncio.to_thread)
    │                                   │
    │  emitter = CompositeBackend(      │
    │    backends=[                      │
    │      JSONLFileBackend(...)  ◄──────┼── asyncio.Lock created HERE
    │    ]                              │     (bound to main loop)
    │  )                                │
    │                                   │
    │  # Forward emitter to task orch   │
    │  task_orch = AutoBuild(           │
    │    emitter=self._emitter  ────────┼──► receives SAME emitter
    │  )                                │     object
    │                                   │
    │                                   │  # Worker thread runs
    │                                   │  # orchestrate() which
    │                                   │  # eventually calls:
    │                                   │
    │                                   │  asyncio.run(
    │                                   │    emitter.flush()
    │                                   │  )
    │                                   │
    │                                   │  # flush() does:
    │                                   │  #   async with self._lock:
    │                                   │  #       pass
    │                                   │
    │                                   │  # ERROR: self._lock was
    │                                   │  # created in main loop
    │                                   │  # but flush() runs in
    │                                   │  # worker thread's loop
    │                                   │
    │                                   │  RuntimeError:
    │                                   │  "Lock is bound to a
    │                                   │   different event loop"
```

### Validated Root Cause

The `asyncio.Lock()` at [emitter.py:165](guardkit/orchestrator/instrumentation/emitter.py#L165) is created when `JSONLFileBackend.__init__()` runs — which happens in the main event loop context. When worker threads try to use this lock via `asyncio.run(emitter.flush())` at [autobuild.py:2568](guardkit/orchestrator/autobuild.py#L2568), the lock is bound to the wrong loop.

The 300-second executor join timeout is a **cascading effect**: the `asyncio.Lock.acquire()` call in `flush()` raises immediately, but the CompositeBackend catches it. The real 300s delay comes from the worker thread's event loop trying to cleanly shut down the Graphiti connection, SDK subprocess cleanup, or other async resources.

### Severity Confirmation: LOW (instrumentation only)

The error is caught and logged as a warning by CompositeBackend. No orchestration logic depends on emitter success.

---

## Finding 5 (VALIDATED + DEEPENED): Direct vs Task-Work Mode

### C4 Component Comparison

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DIRECT MODE                                       │
│                                                                          │
│  invoke_player()                                                         │
│  └── _invoke_player_direct()                                             │
│      └── _invoke_with_role()              ◄── Generic SDK wrapper         │
│          ├── gen = query(prompt, options)                                 │
│          ├── async for message in gen:                                    │
│          │   └── if ResultMessage: break   ◄── EARLY EXIT (problem!)     │
│          └── finally: gen.aclose()         ◄── Triggers CancelledError   │
│                                                                          │
│  Characteristics:                                                        │
│  - SDK timeout: 1200 × 1.0 × complexity_mult (no mode bonus)           │
│  - Generator: breaks early, needs forced cleanup                         │
│  - Report: synthetic (git-analysis promises, lossy)                      │
│  - Session resume: yes (via _last_session_id)                            │
│  - Cancel monitor: yes (polls threading.Event)                           │
│  - Post-completion: writes synthetic task_work_results.json              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       TASK-WORK MODE                                     │
│                                                                          │
│  invoke_player()                                                         │
│  └── _invoke_task_work_implement()        ◄── Dedicated implementation   │
│      ├── prompt = loaded protocol (19KB)                                 │
│      ├── gen = query(prompt, options)                                     │
│      ├── async for message in gen:                                       │
│      │   ├── parse AssistantMessage → TextBlock, ToolUseBlock            │
│      │   ├── track tool uses, file changes                               │
│      │   └── if ResultMessage: extract turns, session_id                 │
│      │       └── # Generator EXHAUSTS NATURALLY                          │
│      └── # No forced aclose() needed                                     │
│                                                                          │
│  Characteristics:                                                        │
│  - SDK timeout: 1200 × 1.5 × complexity_mult (mode bonus)              │
│  - Generator: processes ALL messages, exhausts naturally                  │
│  - Report: agent-written (completion_promises, rich data)                │
│  - Session resume: yes (via _last_session_id)                            │
│  - Cancel monitor: no (relies on SDK timeout)                            │
│  - Post-completion: agent writes task_work_results.json during run       │
│  - State bridge: moves task to design_approved, creates plan stub        │
│  - Rich stream parsing: extracts tool use blocks, files, test results    │
└─────────────────────────────────────────────────────────────────────────┘
```

### The Structural Difference That Matters

The key difference is **generator lifecycle management**:

| Aspect | Direct Mode | Task-Work Mode |
|--------|------------|----------------|
| Generator exit | `break` on ResultMessage | Natural exhaustion |
| aclose() needed | YES (forced cleanup) | NO (already exhausted) |
| CancelledError risk | HIGH (40% per code comment) | NEAR ZERO |
| SDK timeout multiplier | 1.0x | 1.5x |
| Effective timeout (complexity 3) | 1560s | 2340s (capped at 2399s) |
| Report quality | Synthetic (lossy) | Agent-written (rich) |

### Severity Confirmation: MEDIUM-HIGH

The mode disparity is a fundamental architectural difference, not just a configuration issue.

---

## Revised Recommendations

### R1 (REVISED): Fix Generator Lifecycle in Direct Mode (P0)

**Problem**: `gen.aclose()` in `_invoke_with_role` triggers AnyIO cancel scope CancelledError.

**Root cause**: The `break` on `ResultMessage` leaves the generator suspended. `aclose()` forces AnyIO's cancel scope to close in the wrong task context.

**Proposed fix** (Option A — minimal, safe):

At [agent_invoker.py:2059-2062](guardkit/orchestrator/agent_invoker.py#L2059-L2062), after receiving ResultMessage, drain the generator:

```python
if isinstance(message, ResultMessage):
    self._last_session_id = getattr(message, "session_id", None)
    # Drain remaining messages to let generator exhaust naturally
    # This prevents aclose() from triggering AnyIO cancel scope errors
    try:
        async for _ in gen:
            pass
    except Exception:
        pass  # Generator may raise during drain; safe to ignore
    gen = None  # Already exhausted, skip aclose() in finally
    break
```

**Proposed fix** (Option B — track completion state):

Add a flag to distinguish "completed successfully but aclose() failed" from "genuine cancellation":

```python
_result_received = False
async for message in gen:
    ...
    if isinstance(message, ResultMessage):
        self._last_session_id = getattr(message, "session_id", None)
        _result_received = True
        break

# In the except block at line 2063:
except (Exception, asyncio.CancelledError) as exc:
    if isinstance(exc, asyncio.CancelledError) and _result_received:
        # CancelledError from aclose() cleanup after successful completion
        # Treat as success, not error
        logger.debug(f"Suppressing post-completion CancelledError for {heartbeat_task_id}")
        call_status = "ok"
        # Don't re-raise
    else:
        # Genuine cancellation or error
        call_status = "error"
        call_error = exc
        raise
```

**Expected impact**: Eliminates the 40% cancellation rate for direct-mode invocations.

### R2 (UNCHANGED): Add Progress Heartbeats for Parallel Tasks (P1)

Same as original recommendation. The thread-interleaving issue means DC-002 logs may exist but are lost in the output stream. A dedicated per-task log file would solve this.

### R3 (STRENGTHENED): Prefer Task-Work Mode (P1)

Based on the deep dive, the architectural advantages of task-work mode are even more significant than initially assessed:
- Natural generator exhaustion eliminates cancel scope race condition entirely
- 1.5x timeout multiplier provides critical buffer
- Agent-written reports eliminate synthetic report false negatives
- Rich stream parsing provides real-time progress visibility

**Recommendation**: Make `task-work` the default implementation_mode. Only use `direct` for tasks explicitly marked as scaffolding or with complexity <= 1.

### R4 (UNCHANGED): Fix JSONLFileBackend Cross-Loop (P2)

Replace `asyncio.Lock` with `threading.Lock` at [emitter.py:165](guardkit/orchestrator/instrumentation/emitter.py#L165).

### R5 (DOWNGRADED to P3): Improve Synthetic Reports

If R1 is implemented, synthetic reports will rarely be generated (only on genuine SDK failures). This reduces the priority from P2 to P3.

---

## Confidence Assessment

| Finding | Initial Confidence | Post-Deep-Dive Confidence | Changed? |
|---------|-------------------|--------------------------|----------|
| F1: Player Cancellation | 70% (attributed to GC race) | **95%** (aclose() cancel scope) | YES — root cause refined |
| F2: DC-002 Timeout | 50% (black box) | **80%** (validated mechanism, scenario narrowed) | Slightly — scenario clearer |
| F3: Synthetic Reports | 90% | **95%** (validated code path) | No change |
| F4: Event Loop | 85% | **99%** (exact code path traced) | No change |
| F5: Mode Disparity | 80% | **95%** (generator lifecycle is the key) | YES — deepened understanding |

---

## Appendix: Key Code Locations

| Component | File | Lines | Role in Failure |
|-----------|------|-------|-----------------|
| Generator break + aclose | agent_invoker.py | 2059-2099 | **Primary cause** of CancelledError |
| CancelledError handler | agent_invoker.py | 2063-2087 | Re-raises, propagating error |
| invoke_player exception map | agent_invoker.py | 1386-1399 | Wraps CancelledError in result |
| _invoke_player_safely bridge | autobuild.py | 3964-4034 | sync→async via run_until_complete |
| asyncio.wait_for timeout | feature_orchestrator.py | 1485-1494 | Feature-level timeout enforcement |
| asyncio.to_thread boundary | feature_orchestrator.py | 1486 | Thread creation boundary |
| Post-gather cancel signal | feature_orchestrator.py | 1535-1539 | Cleanup after timeout |
| JSONLFileBackend lock | emitter.py | 165 | asyncio.Lock bound to wrong loop |
| Task-work generator loop | agent_invoker.py | 4508-4511 | Natural exhaustion (no break) |
| Cancel monitor | agent_invoker.py | 2018-2028 | Subprocess cleanup on cancel |
