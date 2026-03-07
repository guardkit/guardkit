# Review Report: TASK-REV-C3F8

## Executive Summary

The AutoBuild feature orchestration failure in the vllm-profiling run (FEAT-1637) was caused by a **Python version compatibility gap** in the `_execute_wave_parallel` method. On Python 3.9+, `asyncio.CancelledError` is a `BaseException` (not `Exception`), which means it falls through both `isinstance(result, asyncio.TimeoutError)` and `isinstance(result, Exception)` checks, reaching the `else` branch that assumes a valid `TaskExecutionResult`.

The CancelledError originated from **within the worker thread's event loop** — specifically from the SDK's `query()` async generator when the Node.js CLI subprocess for TASK-FBP-007 exited unexpectedly. The error propagated through **5 consecutive `except Exception` handlers** (all of which miss `BaseException` subclasses on Python 3.9+), escaping the entire invocation chain and appearing as a raw `CancelledError` in the `gather` results.

**Important correction**: The initial SIGINT theory was **disproved** via testing. When `gather` is cancelled externally (SIGINT), `CancelledError` propagates upward — `gather` does NOT return results. The traceback at line 1564 proves `gather` returned normally, meaning the `CancelledError` is IN the results list from a child task, not from external cancellation. See [c4-sequence-diagrams.md](../../../docs/reviews/vllm-profiling/c4-sequence-diagrams.md) for full validation.

## Review Details

- **Mode**: Root Cause Analysis (Bug Investigation)
- **Depth**: Standard
- **Source**: `docs/reviews/vllm-profiling/anthropic_run_1.md`
- **Error Location**: `feature_orchestrator.py:1564`

---

## Finding 1: CancelledError Not Handled in Result Processing (CRITICAL)

**Severity**: Critical | **Priority**: P0 (blocks production runs)

### Evidence

At [feature_orchestrator.py:1514-1564](guardkit/orchestrator/feature_orchestrator.py#L1514-L1564), the result processing loop has this structure:

```python
for task_id, result in zip(task_id_mapping, parallel_results):
    if isinstance(result, asyncio.TimeoutError):      # Line 1516
        # ... handle timeout ...
    elif isinstance(result, Exception):                # Line 1546
        # ... handle general exceptions ...
    else:                                              # Line 1559
        results.append(result)
        status = "success" if result.success else "failed"  # Line 1564 - CRASH
```

On **Python 3.9+** (this run used 3.14.2), `asyncio.CancelledError` inherits from `BaseException`, NOT `Exception`:

```
CancelledError → BaseException → object
```

Therefore:
- `isinstance(CancelledError(), asyncio.TimeoutError)` → `False`
- `isinstance(CancelledError(), Exception)` → **`False`**
- Falls through to `else` branch, which calls `result.success` on a `CancelledError` object

### Root Cause

The `asyncio.gather(return_exceptions=True)` call at line 1499 correctly captures `CancelledError` as a return value (not propagated). However, the downstream result processing code only checks for `TimeoutError` and `Exception`, missing `CancelledError` (and any other `BaseException` subclass).

### Fix

```python
# At line 1515, change the check order to catch BaseException:
for task_id, result in zip(task_id_mapping, parallel_results):
    if isinstance(result, asyncio.TimeoutError):
        # ... existing timeout handling ...
    elif isinstance(result, asyncio.CancelledError):
        # Handle cancellation explicitly
        cancel_msg = f"Task {task_id} was cancelled"
        logger.warning(f"CANCELLED: {task_id} — {cancel_msg}")
        error_result = TaskExecutionResult(
            task_id=task_id,
            success=False,
            total_turns=0,
            final_decision="cancelled",
            error=cancel_msg,
        )
        results.append(error_result)
        if self._wave_display:
            self._wave_display.update_task_status(
                task_id, "cancelled", cancel_msg,
                turns=0, decision="cancelled"
            )
        self._update_feature(feature, task_id, error_result, wave_number)
    elif isinstance(result, BaseException):
        # Catch any other BaseException subclass (KeyboardInterrupt, SystemExit, etc.)
        error_result = self._create_error_result(task_id, result)
        results.append(error_result)
        if self._wave_display:
            self._wave_display.update_task_status(
                task_id, "failed", "error",
                turns=0, decision="error"
            )
        self._update_feature(feature, task_id, error_result, wave_number)
    elif isinstance(result, Exception):
        # ... existing exception handling ...
    else:
        # ... existing success handling ...
```

**File**: [feature_orchestrator.py:1515](guardkit/orchestrator/feature_orchestrator.py#L1515)

---

## Finding 2: _execute_task Doesn't Catch CancelledError (HIGH)

**Severity**: High | **Priority**: P1

### Evidence

At [feature_orchestrator.py:1894](guardkit/orchestrator/feature_orchestrator.py#L1894), the `_execute_task` method only catches `Exception`:

```python
except Exception as e:
    console.print(f"    [red]✗[/red] {task.id}: Error - {e}")
    return TaskExecutionResult(...)
```

If a `CancelledError` is raised inside the thread (e.g., from an async context manager in the SDK), it would propagate uncaught through `asyncio.to_thread()` and appear as an exception in the `gather` results.

### Fix

```python
except (Exception, asyncio.CancelledError) as e:
    console.print(f"    [red]✗[/red] {task.id}: Error - {e}")
    return TaskExecutionResult(
        task_id=task.id,
        success=False,
        total_turns=0,
        final_decision="cancelled" if isinstance(e, asyncio.CancelledError) else "error",
        error=str(e),
    )
```

**File**: [feature_orchestrator.py:1894](guardkit/orchestrator/feature_orchestrator.py#L1894)

---

## Finding 3: Root Cause of the Cancellation Event — CancelledError from Worker Thread (HIGH)

**Severity**: High | **Priority**: P1 (systemic vulnerability)

### Analysis (Revised — SIGINT theory disproved)

TASK-FBP-007 was at ~660s elapsed (of 2400s task_timeout and 1560s SDK timeout) when the failure occurred. The cancellation was **not** from a timeout and was **not** from SIGINT.

**Key evidence**: The traceback shows code executing at `feature_orchestrator.py:1564` inside `_execute_wave_parallel`. If SIGINT had cancelled the gather, `CancelledError` would have **propagated upward** (gather does NOT return results when cancelled externally). The fact that `gather` returned results proves the `CancelledError` originated from **within a child task**.

**Validated root cause**: FBP-007 used the **direct SDK path** (`_invoke_with_role` via `_invoke_player_direct`), which has a `_cancel_monitor()` background task. The `CancelledError` originated from within Event Loop #2 (worker thread) and escaped through 5 consecutive `except Exception` handlers:

1. `agent_invoker.py:1933` — `_invoke_with_role` `except Exception`
2. `agent_invoker.py:1279` — `invoke_player` `except Exception`
3. `autobuild.py:3823` — `_invoke_player_safely` `except Exception`
4. `autobuild.py:3811` — `except UNRECOVERABLE_ERRORS` (doesn't include CancelledError)
5. `feature_orchestrator.py:1894` — `_execute_task` `except Exception`

**Most likely trigger**: The SDK's `query()` async generator raises `CancelledError` when the Node.js CLI subprocess exits unexpectedly. `asyncio.timeout()` does NOT convert this to `TimeoutError` because the cancellation was not initiated by the timeout scope itself (validated via Python 3.14 testing).

### Recommendation

Add `CancelledError`-specific handling at multiple guard points, plus cancellation diagnostics:

```python
# Guard point fix pattern (apply at all 5 locations):
except (Exception, asyncio.CancelledError) as e:
    if isinstance(e, asyncio.CancelledError):
        logger.warning(f"CancelledError caught at {location}: {e}")
    # ... existing error handling ...

# Diagnostics in _execute_wave_parallel:
for tid, res in zip(task_id_mapping, parallel_results):
    if isinstance(res, asyncio.CancelledError):
        logger.error(
            f"CANCELLED: {tid} received CancelledError in wave {wave_number}. "
            f"Originated from within worker thread (not external cancellation)."
        )
```

See [C4 Sequence Diagrams](../../../docs/reviews/vllm-profiling/c4-sequence-diagrams.md) for complete flow validation.

---

## Finding 4: Independent Test Collection Errors (MEDIUM)

**Severity**: Medium | **Priority**: P2

### Evidence

Four tasks (FBP-002, FBP-003, FBP-004, FBP-005) all failed independent test verification with `classification=collection_error, confidence=high`. Each was conditionally approved because "all Player gates passed."

The pattern is consistent:
- All fail during **SDK independent test execution** (not direct pytest)
- All fail within 6.9-8.2 seconds
- All are classified as `collection_error`
- All occur in the shared worktree environment

### Root Cause Assessment

The `collection_error` classification indicates pytest failed during **test collection** (import phase), not during execution. This strongly suggests:

1. **Missing dependencies in the worktree**: The environment bootstrap installed core packages (fastapi, uvicorn, pydantic, pydantic-settings) but the test files likely import modules that were created by later waves (e.g., `from app.core.config import settings`). Since tasks run in a shared worktree, the import structure may not be fully consistent at the time independent verification runs.

2. **pytest conftest.py issues**: If a shared `conftest.py` imports modules that don't yet exist or have circular dependencies, all test collections would fail.

3. **SDK execution environment mismatch**: The independent test runner uses a separate SDK invocation. If the Python path or working directory differs from the Player's environment, imports would fail.

### Impact

The conditional approval mechanism correctly prevented these from blocking the run. However, **100% independent test failure rate** (4/4 tasks that ran independent tests) indicates a systemic environment issue, not genuine test failures. The conditional approval is functioning as designed here.

### Recommendation

- Add `PYTHONPATH` and working directory logging to independent test execution
- Consider running independent tests with `--import-mode=importlib` to avoid path issues
- Log the actual collection error output (not just classification) for debugging

---

## Finding 5: Documentation Constraint Violation (LOW)

**Severity**: Low | **Priority**: P3

### Evidence

TASK-FBP-001 created 9 files vs the 2-file maximum for "minimal" documentation level. This warning was logged but did not block execution:

```
WARNING: Documentation level constraint violated: created 9 files, max allowed 2 for minimal level
```

### Assessment

This is a soft constraint and was correctly handled as a warning. No code change needed, but the scaffolding task template could be adjusted to increase the limit for scaffolding tasks which inherently create many files.

---

## Recommendations Summary

| # | Finding | Severity | Fix Complexity | File |
|---|---------|----------|----------------|------|
| 1 | CancelledError not handled in result processing | Critical | Simple (add isinstance check) | `feature_orchestrator.py:1515` |
| 2 | _execute_task doesn't catch CancelledError | High | Simple (widen except clause) | `feature_orchestrator.py:1894` |
| 3 | No cancellation source logging | Medium | Simple (add logging) | `feature_orchestrator.py:1499` |
| 4 | Systemic independent test collection errors | Medium | Medium (environment investigation) | `coach_validator.py` |
| 5 | Documentation constraint too strict for scaffolding | Low | Trivial (config change) | Template config |

## Recommended Implementation Order

1. **Finding 1** (P0): Fix the `isinstance` check — this is the crash fix
2. **Finding 2** (P1): Widen the except clause in `_execute_task`
3. **Finding 3** (P2): Add cancellation logging for future diagnostics
4. Findings 4-5 can be addressed separately

---

## Deep-Dive Addendum (Revised Analysis)

### Deep-Dive 1: Definitive Cancellation Source (REVISED)

**Conclusion**: CancelledError originated from within the worker thread's event loop (SIGINT theory DISPROVED)

**SIGINT disproval evidence**: When `asyncio.gather` is cancelled externally (as SIGINT would cause via `Runner._on_sigint` → `main_task.cancel()`), the `CancelledError` **propagates upward** — `gather` does NOT return results in the list. This was verified via Python 3.14.2 testing:

```python
async def test_sigint_gather():
    gather_task = asyncio.ensure_future(asyncio.gather(..., return_exceptions=True))
    gather_task.cancel()
    try:
        results = await gather_task
        # NEVER REACHED — gather does NOT return results when cancelled
    except asyncio.CancelledError:
        print('PROPAGATED CancelledError')  # THIS is what happens
```

The traceback at `feature_orchestrator.py:1564` proves that `gather` returned results normally. Therefore the `CancelledError` is **in** the results list as one task's return value, not from external cancellation.

**Validated cancellation chain**:
```
SDK query() async generator → CancelledError (subprocess dies or internal task cancelled)
  → asyncio.timeout(1560s) DOES NOT CONVERT (not timeout's own cancellation)
  → CancelledError propagates through _invoke_with_role (except Exception misses it)
  → CancelledError propagates through invoke_player (except Exception misses it)
  → CancelledError propagates through _invoke_player_safely (except Exception misses it)
  → CancelledError propagates through _execute_task (except Exception misses it)
  → CancelledError exits worker thread via to_thread()
  → gather(return_exceptions=True) captures it as result value
  → Result processing: isinstance(CancelledError, Exception) → False (Python 3.9+)
  → CRASH: result.success on CancelledError object
```

**Critical insight — direct mode vulnerability**: FBP-007 used `implementation_mode=direct` (log line 684), which routes through `_invoke_player_direct` → `_invoke_with_role`. This path has a `_cancel_monitor()` background task that can kill the SDK subprocess and trigger `CancelledError`. The task-work delegation path (`_invoke_task_work_implement`) does NOT have `_cancel_monitor` and handles errors differently. This makes direct-mode tasks more vulnerable to this specific crash.

**5 unguarded exception handlers**: The `CancelledError` passes through 5 consecutive `except Exception` clauses, none of which catch `BaseException`. This is a systemic Python 3.9+ compatibility issue across the entire invocation chain. See [C4 Sequence Diagrams](../../../docs/reviews/vllm-profiling/c4-sequence-diagrams.md) for the complete annotated flow.

### Deep-Dive 2: Independent Test Collection Error Root Cause

**Conclusion**: Stale editable installs (`pip install -e .`) from previous AutoBuild runs pollute `sys.path`

The exact error from FBP-002's `coach_turn_1.json`:
```
ImportError: cannot import name 'CorrelationIdMiddleware' from 'src.core.middleware'
  (/...guardkit-examples/fastapi/.guardkit/worktrees/FEAT-BA28/src/core/middleware.py)
```

Python resolved `src.core.middleware` to a **different project's** worktree (FEAT-BA28) because:

1. **`.pth` file contamination**: Previous AutoBuild runs executed `pip install -e .` into the system Python, creating persistent `.pth` entries in site-packages (e.g., `_fastapi_health_app.pth → FEAT-BA28 root`)
2. **No PYTHONPATH in Coach SDK**: `_run_tests_via_sdk()` at [coach_validator.py:1178](guardkit/orchestrator/quality_gates/coach_validator.py#L1178) creates `ClaudeAgentOptions` with `cwd` but no `env` parameter. Without `PYTHONPATH=<worktree>`, the SDK subprocess inherits the contaminated `sys.path`
3. **Player tests pass** because the Player runs inside a Claude SDK session where the Bash tool sets `cwd`, and pytest adds `''` (cwd) at `sys.path[0]`, which has higher priority than the `.pth` entries
4. **Coach tests fail** because the fresh SDK subprocess loads `.pth` entries at Python startup before pytest can insert the worktree root

**Fix (confirmed working)**:
```python
# In coach_validator.py _run_tests_via_sdk, line ~1178:
import os as _os
current_pythonpath = _os.environ.get("PYTHONPATH", "")
worktree_str = str(self.worktree_path)
new_pythonpath = f"{worktree_str}:{current_pythonpath}" if current_pythonpath else worktree_str

options_kwargs = dict(
    cwd=str(self.worktree_path),
    allowed_tools=["Bash"],
    permission_mode="bypassPermissions",
    max_turns=1,
    env={"PYTHONPATH": new_pythonpath},  # Fix: ensure worktree root has priority
)
```

**Structural fix**: Add editable install cleanup to worktree teardown, or use per-worktree venvs instead of system Python.

### Deep-Dive 3: Fix Prototype Verification

All proposed fixes were prototyped and verified:

| Scenario | Current Code | Fixed Code |
|----------|-------------|------------|
| `CancelledError` in gather results | **CRASH** (`AttributeError`) | Handled as "cancelled" |
| `TimeoutError` in gather results | Handled correctly | Unchanged |
| `RuntimeError` in gather results | Handled correctly | Unchanged |
| `KeyboardInterrupt` in gather results | **CRASH** | Handled as "base_exception" |
| `SystemExit` in gather results | **CRASH** | Handled as "base_exception" |
| Normal `TaskExecutionResult` | Works | Unchanged |

The correct check order is: `TimeoutError` → `CancelledError` → `Exception` → `BaseException` → success result.

---

## Revised Recommendations Summary (v3 — SIGINT Disproved)

| # | Finding | Severity | Fix Complexity | File(s) |
|---|---------|----------|----------------|---------|
| 1 | CancelledError not handled in result processing | Critical | Simple | `feature_orchestrator.py:1515` |
| 2 | _execute_task doesn't catch CancelledError | High | Simple | `feature_orchestrator.py:1894` |
| 3 | 5 unguarded `except Exception` handlers miss BaseException | High | Medium (5 locations) | `agent_invoker.py:1279,1933`, `autobuild.py:3811,3823`, `feature_orchestrator.py:1894` |
| 4 | Coach SDK independent tests lack PYTHONPATH | High | Simple (add env param) | `coach_validator.py:1178` |
| 5 | Stale editable installs contaminate sys.path | Medium | Medium (cleanup on teardown) | `environment_bootstrap.py` |
| 6 | No cancellation source diagnostics logging | Medium | Simple | `feature_orchestrator.py:1499` |
| 7 | Documentation constraint too strict for scaffolding | Low | Trivial | Template config |

## Revised Implementation Order (v3)

1. **Finding 1** (P0): Add `CancelledError` and `BaseException` isinstance checks in result processing — crash fix
2. **Finding 3** (P0): Add `CancelledError` handling at all 5 guard points in the invocation chain — prevents escape
3. **Finding 4** (P1): Add `PYTHONPATH` env to Coach SDK options — fixes 100% independent test failures
4. **Finding 2** (P1): Widen except clause in `_execute_task` (overlaps with Finding 3)
5. **Finding 6** (P2): Add cancellation diagnostics logging
6. **Finding 5** (P2): Implement editable install cleanup
7. **Finding 7** (P3): Adjust scaffolding doc limits

## Supporting Artifacts

- **C4 Sequence Diagrams**: [docs/reviews/vllm-profiling/c4-sequence-diagrams.md](../../../docs/reviews/vllm-profiling/c4-sequence-diagrams.md)
  - C4 Context Diagram (Level 1): System boundaries and technology stacks
  - Sequence Diagram 1: Normal execution (FBP-006, task-work delegation)
  - Sequence Diagram 2: Failure path (FBP-007, direct SDK mode) — validated root cause
  - Sequence Diagram 3: SIGINT theory disproval with evidence
  - Sequence Diagram 4: Complete CancelledError escape path through 5 guard points

---

## Appendix

### Timeline Reconstruction

| Time (UTC) | Event |
|------------|-------|
| 08:07:02 | Feature FEAT-1637 orchestration started |
| 08:07:02 | Wave 1: TASK-FBP-001 started |
| 08:21:24 | Wave 1 completed (1 task, 1 turn) |
| 08:21:26 | Wave 2: TASK-FBP-002, FBP-004 started (parallel) |
| 08:26:42 | Wave 2 completed (both conditionally approved) |
| 08:26:51 | Wave 3: TASK-FBP-003 started |
| 08:31:59 | Wave 3 completed (conditionally approved) |
| 08:32:08 | Wave 4: TASK-FBP-005 started |
| 08:39:49 | Wave 4 completed (conditionally approved) |
| 08:39:49 | Wave 5: TASK-FBP-006, FBP-007 started (parallel) |
| 08:47:52 | TASK-FBP-006 completed (approved, 1 turn) |
| 08:50:49 | TASK-FBP-007 last progress log (660s elapsed) |
| 08:51:16 | CancelledError crash during result processing |

### Python Version Note

This is a **Python 3.9+ compatibility issue**. Prior to Python 3.9, `CancelledError` inherited from `Exception`, meaning the existing `isinstance(result, Exception)` check would have caught it. The change to `BaseException` was a deliberate upstream change to prevent accidental swallowing of cancellation signals.

### Affected Versions

- Python 3.9+ (CancelledError changed to BaseException)
- Python 3.14.2 (version used in this run)
- GuardKit: current main branch
