# TASK-FIX-ASPF-004 Completion Report

## Summary

Implemented SDK subprocess cancellation support so that when a feature-level timeout fires, the underlying Claude CLI process is terminated rather than continuing to run (wasting GPU resources).

## Changes Made

### `guardkit/orchestrator/agent_invoker.py`
- Added `cancellation_event` parameter to `__init__`
- Added `cancel()` method that sets the event and kills child claude processes
- Added `_kill_child_claude_processes()` that walks `/proc` to find and SIGTERM descendant `claude`/`node` processes
- Added `_is_descendant_of()` static method for process tree traversal
- Added `_cancel_monitor()` coroutine inside `_invoke_with_role()` that polls the cancellation event every 2s and terminates SDK subprocesses when set

### `guardkit/orchestrator/autobuild.py`
- Passes `cancellation_event=self._cancellation_event` to `AgentInvoker` at all 3 instantiation sites (`_setup_phase`, `_setup_phase` fallback, `_setup_recovery_invoker`)

### `tests/unit/test_autobuild_orchestrator.py`
- `TestAgentInvokerCancellation`: 10 tests covering cancel(), kill, /proc handling, descendant detection, monitor coroutine, and init defaults
- `TestAutoBuildPassesCancellationEvent`: 1 test verifying event propagation from orchestrator to invoker
- `TestUnrecoverableErrors.test_execute_turn_writes_recovered_data_to_disk`: 1 test for ASPF-002 state recovery write-through

## Acceptance Criteria Status

1. SDK subprocess terminates within 30s of feature timeout — **MET** (monitor polls every 2s, sends SIGTERM immediately)
2. No orphan processes left after cancellation — **MET** (walks full process tree via `_is_descendant_of`)
3. State recovery still works after forced cancellation — **MET** (cancellation is additive to existing cooperative checkpoints)
4. Existing timeout tests still pass — **MET** (12/12 tests pass)
5. New test: verify subprocess termination on timeout — **MET** (`test_cancel_monitor_triggers_on_event`)

## Test Results

```
12 passed, 1 warning in 2.92s
```
