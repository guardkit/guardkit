# C4 Sequence Diagrams: TASK-REV-C3F8 CancelledError Root Cause Validation

## C4 Context Diagram (Level 1)

```
┌────────────────────────────────────────────────────────────────┐
│                     Operating System (macOS)                    │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Python 3.14 Main Process                     │  │
│  │                                                           │  │
│  │  ┌─────────────────────┐  ┌─────────────────────────┐   │  │
│  │  │   Main Thread        │  │  Worker Thread (FBP-007)│   │  │
│  │  │                      │  │                          │   │  │
│  │  │  asyncio.run()       │  │  asyncio.new_event_loop()│  │  │
│  │  │  ┌────────────────┐  │  │  ┌──────────────────┐   │  │  │
│  │  │  │ Event Loop #1   │  │  │  │ Event Loop #2    │   │  │  │
│  │  │  │                 │  │  │  │                   │   │  │  │
│  │  │  │ gather()        │  │  │  │ run_until_complete│   │  │  │
│  │  │  │ ├─ wait_for(006)│  │  │  │ ├─ invoke_player │   │  │  │
│  │  │  │ └─ wait_for(007)│──┼──┼──│ │  ├─ timeout()  │   │  │  │
│  │  │  │                 │  │  │  │ │  └─ query()  ───┼───┼──┼──┼─── Node.js CLI
│  │  │  └────────────────┘  │  │  └──────────────────┘   │  │  │     Subprocess
│  │  └──────────────────────┘  └─────────────────────────┘   │  │     (FBP-007)
│  │                                                           │  │
│  │  ┌─────────────────────────┐                              │  │
│  │  │  Worker Thread (FBP-006) │  ── Completed successfully  │  │
│  │  └─────────────────────────┘                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### Technology Boundaries

| Boundary | From | To | Mechanism |
|----------|------|----|-----------|
| Thread boundary | Main Thread | Worker Thread | `asyncio.to_thread()` wraps sync fn in `concurrent.futures.ThreadPoolExecutor` |
| Event loop boundary | Event Loop #1 (main) | Event Loop #2 (worker) | Worker creates own loop via `asyncio.new_event_loop()` |
| Process boundary | Python process | Node.js CLI | `subprocess.Popen` (managed by `claude_agent_sdk`) |
| Async/sync boundary | async `_execute_wave_parallel` | sync `_execute_task` | `to_thread` bridges async→sync |
| Async/sync boundary | sync `_invoke_player_safely` | async `invoke_player` | `loop.run_until_complete` bridges sync→async |

---

## C4 Component Diagram (Level 2): Error Propagation Path

```
┌──────────────────────────────────────────────────────────────────┐
│                       FeatureOrchestrator                         │
│                                                                   │
│  _execute_wave() ─── sync entry point                            │
│      │                                                            │
│      └─ asyncio.run(_execute_wave_parallel())                    │
│              │                                                    │
│              └─ asyncio.gather(..., return_exceptions=True)       │
│                    │                                              │
│                    ├─ Task[FBP-006]: wait_for(to_thread(...))     │
│                    │      └─ Returns TaskExecutionResult ✓        │
│                    │                                              │
│                    └─ Task[FBP-007]: wait_for(to_thread(...))     │
│                           │                                       │
│                           └─ RETURNS CancelledError ✗             │
│                                                                   │
│  Result Processing (line 1515):                                  │
│      isinstance(CancelledError, TimeoutError)  → False           │
│      isinstance(CancelledError, Exception)     → False (Py 3.9+)│
│      else: result.success → AttributeError CRASH                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Sequence Diagram 1: Normal Execution Path (FBP-006 — Task-Work Delegation)

```
┌──────────┐  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────┐
│Main Thread│  │Event Loop #1 │  │Worker Thread   │  │Event Loop #2 │  │Node.js CLI│
│           │  │(asyncio.run) │  │(to_thread)     │  │(new_event_   │  │Subprocess │
│           │  │              │  │                │  │loop)         │  │           │
└─────┬─────┘  └──────┬───────┘  └───────┬────────┘  └──────┬───────┘  └─────┬─────┘
      │               │                  │                   │               │
      │  asyncio.run() │                  │                   │               │
      │──────────────>│                  │                   │               │
      │               │                  │                   │               │
      │               │  gather(         │                   │               │
      │               │   wait_for(      │                   │               │
      │               │    to_thread())) │                   │               │
      │               │─────────────────>│                   │               │
      │               │                  │                   │               │
      │               │                  │  _execute_task()  │               │
      │               │                  │─ ─ ─ ─ ─ ─ ─ ─ ─>│               │
      │               │                  │                   │               │
      │               │                  │  orchestrate()    │               │
      │               │                  │──────────────────>│               │
      │               │                  │                   │               │
      │               │                  │  invoke_player()  │               │
      │               │                  │  ┌────────────────┤               │
      │               │                  │  │ _invoke_task_  │               │
      │               │                  │  │ work_implement │               │
      │               │                  │  │                │               │
      │               │                  │  │ asyncio.timeout│               │
      │               │                  │  │ (sdk_timeout)  │               │
      │               │                  │  │    │           │               │
      │               │                  │  │    │  query()  │               │
      │               │                  │  │    │──────────────────────────>│
      │               │                  │  │    │           │  SDK stream  │
      │               │                  │  │    │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│
      │               │                  │  │    │  messages │               │
      │               │                  │  │    │<──────────────────────────│
      │               │                  │  │    │           │  ResultMsg   │
      │               │                  │  │    │<──────────────────────────│
      │               │                  │  │    │           │               │
      │               │                  │  │ TaskWorkResult │               │
      │               │                  │  │ (success=True) │               │
      │               │                  │  └────────────────┤               │
      │               │                  │                   │               │
      │               │                  │  AgentInvocation  │               │
      │               │                  │  Result(success)  │               │
      │               │                  │<──────────────────│               │
      │               │                  │                   │               │
      │               │  TaskExecution   │                   │               │
      │               │  Result(success) │                   │               │
      │               │<─────────────────│                   │               │
      │               │                  │                   │               │
      │  result.success│                  │                   │               │
      │  == True ✓     │                  │                   │               │
      │<──────────────│                  │                   │               │
```

---

## Sequence Diagram 2: FAILURE Path (FBP-007 — Direct SDK Mode) — VALIDATED ROOT CAUSE

```
┌──────────┐  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────┐
│Main Thread│  │Event Loop #1 │  │Worker Thread   │  │Event Loop #2 │  │Node.js CLI│
│           │  │(asyncio.run) │  │(to_thread)     │  │(worker loop) │  │Subprocess │
│           │  │              │  │                │  │              │  │(FBP-007)  │
└─────┬─────┘  └──────┬───────┘  └───────┬────────┘  └──────┬───────┘  └─────┬─────┘
      │               │                  │                   │               │
      │               │  wait_for(       │                   │               │
      │               │   to_thread(     │                   │               │
      │               │    _execute_task))│                   │               │
      │               │─────────────────>│                   │               │
      │               │                  │                   │               │
      │               │                  │  orchestrate()    │               │
      │               │                  │──────────────────>│               │
      │               │                  │                   │               │
      │               │                  │  _invoke_player_  │               │
      │               │                  │  safely()         │               │
      │               │                  │──────────────────>│               │
      │               │                  │                   │               │
      │               │                  │  invoke_player()  │               │
      │               │                  │  ┌────────────────┤               │
      │               │                  │  │ _invoke_player │               │
      │               │                  │  │ _direct()      │               │
      │               │                  │  │    │           │               │
      │               │                  │  │ _invoke_with_  │               │
      │               │                  │  │ role()         │               │
      │               │                  │  │    │           │               │
      │               │                  │  │  ┌─┴───────┐  │               │
      │               │                  │  │  │_cancel_  │  │               │
      │               │                  │  │  │monitor() │  │               │
      │               │                  │  │  │(polling  │  │               │
      │               │                  │  │  │ every 2s)│  │               │
      │               │                  │  │  └──────────┘  │               │
      │               │                  │  │    │           │               │
      │               │                  │  │ asyncio.timeout│               │
      │               │                  │  │ (1560s)        │               │
      │               │                  │  │    │           │               │
      │               │                  │  │    │  query()  │               │
      │               │                  │  │    │──────────────────────────>│
      │               │                  │  │    │           │               │
      │               │                  │  │    │           │  ... 660s     │
      │               │                  │  │    │           │  of messages  │
      │               │                  │  │    │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│
      │               │                  │  │    │           │               │
╔═══════════════════════════════════════════════════════════════════════════════════╗
║ CANCELLATION EVENT TRIGGERED                                                     ║
║                                                                                  ║
║ FBP-006 completes → gather still waiting → cancellation_events set (line 1511)  ║
║ OR: asyncio.wait_for timeout fires for FBP-007 (2400s task_timeout)             ║
║ OR: SDK subprocess dies unexpectedly → query() raises CancelledError            ║
║                                                                                  ║
║ Most likely: post-gather cleanup at line 1508-1512 sets cancellation_event      ║
║ → _cancel_monitor detects it → kills Node.js subprocess                         ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
      │               │                  │  │    │           │               │
      │               │                  │  │  ┌─┴───────┐  │               │
      │               │                  │  │  │_cancel_  │  │               │
      │               │                  │  │  │monitor   │  │               │
      │               │                  │  │  │detects   │  │               │
      │               │                  │  │  │event.set │  │               │
      │               │                  │  │  │          │  │               │
      │               │                  │  │  │_kill_    │  │               │
      │               │                  │  │  │child_    │  │  SIGTERM      │
      │               │                  │  │  │claude_   │  │──────────────>│
      │               │                  │  │  │processes │  │               │ EXIT
      │               │                  │  │  └──────────┘  │               │──┐
      │               │                  │  │    │           │               │  │
      │               │                  │  │    │ query()   │               │  │
      │               │                  │  │    │ detects   │               │  │
      │               │                  │  │    │ subprocess│               │  │
      │               │                  │  │    │ death     │               │<─┘
      │               │                  │  │    │           │               │
      │               │                  │  │    │ RAISES    │               │
      │               │                  │  │    │ Cancelled │               │
      │               │                  │  │    │ Error     │               │
      │               │                  │  │    │           │               │
      │               │                  │  │ CancelledError │               │
      │               │                  │  │ PROPAGATES thru│               │
      │               │                  │  │ asyncio.timeout│               │
      │               │                  │  │ (NOT converted │               │
      │               │                  │  │  to Timeout!)  │               │
      │               │                  │  └────────────────┤               │
      │               │                  │                   │               │
      │               │                  │  CancelledError   │               │
      │               │                  │  escapes          │               │
      │               │                  │  loop.run_until_  │               │
      │               │                  │  complete()       │               │
      │               │                  │<──────────────────│               │
      │               │                  │                   │               │
      │               │                  │  CancelledError   │               │
      │               │                  │  escapes          │               │
      │               │                  │  _invoke_player_  │               │
      │               │                  │  safely()         │               │
      │               │                  │  (except Exception│               │
      │               │                  │   DOESN'T catch   │               │
      │               │                  │   BaseException!) │               │
      │               │                  │                   │               │
      │               │                  │  CancelledError   │               │
      │               │                  │  escapes          │               │
      │               │                  │  _execute_task()  │               │
      │               │                  │  (except Exception│               │
      │               │                  │   at line 1894    │               │
      │               │                  │   DOESN'T catch   │               │
      │               │                  │   BaseException!) │               │
      │               │                  │                   │               │
      │               │  CancelledError  │                   │               │
      │               │  returned via    │                   │               │
      │               │  to_thread()     │                   │               │
      │               │<─────────────────│                   │               │
      │               │                  │                   │               │
      │               │  gather() puts   │                   │               │
      │               │  CancelledError  │                   │               │
      │               │  in results list │                   │               │
      │               │  (return_        │                   │               │
      │               │   exceptions=    │                   │               │
      │               │   True)          │                   │               │
      │               │                  │                   │               │
      │  parallel_    │                  │                   │               │
      │  results =    │                  │                   │               │
      │  [TaskExec    │                  │                   │               │
      │   Result(006),│                  │                   │               │
      │   Cancelled   │                  │                   │               │
      │   Error(007)] │                  │                   │               │
      │<──────────────│                  │                   │               │
      │               │                  │                   │               │
      │  isinstance(  │                  │                   │               │
      │   result,     │                  │                   │               │
      │   TimeoutError│                  │                   │               │
      │  ) → False    │                  │                   │               │
      │               │                  │                   │               │
      │  isinstance(  │                  │                   │               │
      │   result,     │                  │                   │               │
      │   Exception)  │                  │                   │               │
      │  → FALSE      │                  │                   │               │
      │  (Python 3.9+)│                  │                   │               │
      │               │                  │                   │               │
      │  ELSE branch: │                  │                   │               │
      │  result.success                  │                   │               │
      │  → CRASH      │                  │                   │               │
      │  AttributeError: 'CancelledError'│                   │               │
      │  object has no attribute 'success'                   │               │
      │               │                  │                   │               │
```

---

## Sequence Diagram 3: DISPROVED SIGINT Theory

This diagram shows why the SIGINT theory is **incorrect**:

```
IF SIGINT had caused the crash, the sequence would be:

┌──────────┐  ┌──────────────┐
│OS Signal │  │Event Loop #1 │
│Handler   │  │(asyncio.run) │
└─────┬─────┘  └──────┬───────┘
      │               │
      │  SIGINT       │
      │──────────────>│
      │               │
      │  Runner._on_  │
      │  sigint()     │
      │  calls        │
      │  main_task.   │
      │  cancel()     │
      │               │
      │  _Gathering   │
      │  Future.      │
      │  cancel()     │
      │               │
      │  ALL children │
      │  cancelled    │
      │               │
      │  gather does  │
      │  NOT return   │    ← KEY INSIGHT: gather itself is cancelled
      │  results!     │    ← CancelledError PROPAGATES UPWARD
      │               │    ← Code at line 1564 NEVER EXECUTES
      │  CancelledError
      │  propagates to│
      │  asyncio.run()│
      │               │
      │  DIFFERENT    │
      │  traceback!   │    ← Would show asyncio.run() at top, NOT line 1564
      │               │

BUT THE ACTUAL TRACEBACK SHOWS:
  File "feature_orchestrator.py", line 1564, in _execute_wave_parallel
      status = "success" if result.success else "failed"

This means gather RETURNED NORMALLY with results.
CancelledError is IN the results list, not propagated from gather.
Therefore: the CancelledError originated from WITHIN a child task,
           not from external cancellation of the gather itself.
```

### Evidence from Python 3.14 testing:

```python
# Test: external gather cancellation
async def test_sigint_gather():
    gather_task = asyncio.ensure_future(asyncio.gather(..., return_exceptions=True))
    gather_task.cancel()
    try:
        results = await gather_task
        # NEVER REACHED — gather does NOT return results when cancelled
    except asyncio.CancelledError:
        print('PROPAGATED CancelledError')  # THIS is what happens

# Conclusion: SIGINT → CancelledError PROPAGATES, never reaches line 1564
```

---

## Sequence Diagram 4: Validated Root Cause — CancelledError Within Worker Thread

```
┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────┐
│Event Loop #1 │  │Worker Thread   │  │Event Loop #2 │  │Node.js CLI│
│(main thread) │  │(FBP-007)      │  │(worker loop) │  │Subprocess │
└──────┬───────┘  └───────┬────────┘  └──────┬───────┘  └─────┬─────┘
       │                  │                   │               │
       │  to_thread(      │                   │               │
       │   _execute_task) │                   │               │
       │─────────────────>│                   │               │
       │                  │                   │               │
       │                  │  _invoke_player_  │               │
       │                  │  safely()         │               │
       │                  │──────────────────>│               │
       │                  │                   │               │
       │                  │  loop.run_until_  │               │
       │                  │  complete(        │               │
       │                  │   invoke_player())│               │
       │                  │                   │               │
       │                  │  _invoke_player_  │               │
       │                  │  direct()         │               │
       │                  │    │              │               │
       │                  │  _invoke_with_    │               │
       │                  │  role()           │               │
       │                  │    │              │               │
       │                  │    │ Creates:     │               │
       │                  │    │ _cancel_     │               │
       │                  │    │  monitor()   │               │
       │                  │    │ task         │               │
       │                  │    │              │               │
       │                  │    │ asyncio.     │               │
       │                  │    │ timeout(1560)│               │
       │                  │    │    │         │               │
       │                  │    │    │ query() │               │
       │                  │    │    │────────────────────────>│
       │                  │    │    │         │               │
       │                  │    │    │  ...streaming messages  │
       │                  │    │    │<────────────────────────│
       │                  │    │    │         │               │
╔══════════════════════════════════════════════════════════════════════╗
║  TRIGGER: Something raises CancelledError WITHIN the worker loop   ║
║                                                                     ║
║  Possible sources (ordered by probability):                         ║
║                                                                     ║
║  1. SDK query() internal cancellation (HIGH probability)            ║
║     - SDK's async generator has internal tasks for I/O              ║
║     - When subprocess exits unexpectedly, internal task cancelled   ║
║     - Raises CancelledError from within the async for loop          ║
║                                                                     ║
║  2. _cancel_monitor kills subprocess (MEDIUM probability)           ║
║     - If cancellation_event was set from main thread                ║
║     - monitor calls _kill_child_claude_processes()                  ║
║     - Subprocess dies → query() detects → CancelledError           ║
║                                                                     ║
║  3. asyncio.timeout scope race (LOW probability)                    ║
║     - AnyIO cancel scope from query() generator                     ║
║     - Interacts with asyncio.timeout cancel scope                   ║
║     - CancelledError "leaks" between scopes                         ║
╚══════════════════════════════════════════════════════════════════════╝
       │                  │    │    │         │               │
       │                  │    │    │ RAISES  │               │
       │                  │    │    │ Cancelled               │
       │                  │    │    │ Error   │               │
       │                  │    │    │         │               │
       │                  │    │ CancelledError               │
       │                  │    │ passes thru  │               │
       │                  │    │ asyncio.     │               │
       │                  │    │ timeout()    │               │
       │                  │    │ UNCHANGED    │               │ ← NOT converted
       │                  │    │ (only        │               │   to TimeoutError
       │                  │    │  timeout's   │               │   because it
       │                  │    │  OWN cancel  │               │   wasn't from
       │                  │    │  converts)   │               │   the timeout
       │                  │    │              │               │
       │                  │    │ except       │               │
       │                  │    │ Exception    │               │
       │                  │    │ at line 1933 │               │ ← Catches generic
       │                  │    │ ? NO!        │               │   Exception but
       │                  │    │ CancelledError               │   CancelledError
       │                  │    │ is Base      │               │   is BaseException
       │                  │    │ Exception    │               │
       │                  │    │              │               │
       │                  │  CancelledError  │               │
       │                  │  escapes invoke_ │               │
       │                  │  player()        │               │
       │                  │  (except clause  │               │
       │                  │  at line 1279    │               │ ← agent_invoker.py:1279
       │                  │  only catches    │               │   "except Exception"
       │                  │  Exception)      │               │   MISSES CancelledError
       │                  │                   │               │
       │                  │  CancelledError  │               │
       │                  │  escapes loop.   │               │
       │                  │  run_until_      │               │
       │                  │  complete()      │               │ ← autobuild.py:3787
       │                  │                   │               │   no try/except for
       │                  │                   │               │   CancelledError
       │                  │  CancelledError  │               │
       │                  │  escapes         │               │
       │                  │  _invoke_player_ │               │
       │                  │  safely()        │               │
       │                  │  (except         │               │
       │                  │  UNRECOVERABLE   │               │ ← autobuild.py:3811
       │                  │  _ERRORS misses  │               │   Does NOT include
       │                  │  CancelledError) │               │   CancelledError
       │                  │  (except         │               │
       │                  │  Exception at    │               │ ← autobuild.py:3823
       │                  │  line 3823       │               │   MISSES CancelledError
       │                  │  ALSO misses!)   │               │
       │                  │                   │               │
       │                  │  CancelledError  │               │
       │                  │  escapes         │               │
       │                  │  orchestrate()   │               │ ← No specific handler
       │                  │                   │               │
       │                  │  CancelledError  │               │
       │                  │  escapes         │               │
       │                  │  _execute_task() │               │ ← feature_orchestrator.py:1894
       │                  │  (except         │               │   "except Exception"
       │                  │  Exception       │               │   MISSES CancelledError
       │                  │  MISSES!)        │               │
       │                  │                   │               │
       │  CancelledError  │                   │               │
       │  returned via    │                   │               │
       │  to_thread       │                   │               │ ← concurrent.futures wraps
       │<─────────────────│                   │               │   thread exception as result
       │                  │                   │               │
       │  gather puts     │                   │               │
       │  CancelledError  │                   │               │
       │  in results list │                   │               │ ← return_exceptions=True
       │                  │                   │               │   captures it as value
       │  CRASH at        │                   │               │
       │  line 1564       │                   │               │
       │                  │                   │               │
```

---

## Exception Escape Analysis: 5 Missing Guard Points

The CancelledError escapes through **5 consecutive `except Exception` handlers**, none of which catch `BaseException`:

```
Guard Point 1: agent_invoker.py:1933  (_invoke_with_role)
    except Exception as exc:     ← MISSES CancelledError

Guard Point 2: agent_invoker.py:1279  (invoke_player)
    except Exception as e:       ← MISSES CancelledError

Guard Point 3: autobuild.py:3823     (_invoke_player_safely)
    except Exception as e:       ← MISSES CancelledError

Guard Point 4: autobuild.py:3811     (_invoke_player_safely)
    except UNRECOVERABLE_ERRORS: ← Tuple doesn't include CancelledError

Guard Point 5: feature_orchestrator.py:1894  (_execute_task)
    except Exception as e:       ← MISSES CancelledError

Final: feature_orchestrator.py:1546
    elif isinstance(result, Exception):  ← MISSES CancelledError in results
```

---

## Root Cause Summary

### Proximate Cause
`isinstance(result, Exception)` at line 1546 does not match `CancelledError` on Python 3.9+ because `CancelledError` inherits from `BaseException`, not `Exception`.

### Underlying Cause
A `CancelledError` raised within the worker thread's event loop (Event Loop #2) propagates through **5 unguarded exception handlers** — all use `except Exception` which misses `BaseException` subclasses on Python 3.9+. The error escapes:
1. `_invoke_with_role` → 2. `invoke_player` → 3. `_invoke_player_safely` → 4. `orchestrate()` → 5. `_execute_task` → returns via `to_thread` → captured by `gather(return_exceptions=True)` → unhandled in result processing.

### Origination (Most Likely Source)
The `CancelledError` originates from within the SDK's `query()` async generator when the Node.js CLI subprocess for FBP-007 exits unexpectedly. The `_cancel_monitor()` background task (unique to the `_invoke_with_role` path used by direct-mode tasks) or an internal SDK async task cancellation is the trigger. The `asyncio.timeout()` context manager does NOT convert this to `TimeoutError` because the cancellation was not initiated by the timeout scope itself.

### Why SIGINT Theory Was Wrong
When `asyncio.gather` itself is cancelled externally (as SIGINT would cause), `CancelledError` **propagates upward** — `gather` does NOT return results. The traceback shows code executing at line 1564 inside `_execute_wave_parallel`, which means `gather` returned results normally. The `CancelledError` is **in** the results list as one task's return value, not propagated from `gather` cancellation.
