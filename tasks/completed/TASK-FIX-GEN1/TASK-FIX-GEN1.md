---
id: TASK-FIX-GEN1
title: Fix direct-mode generator lifecycle to eliminate CancelledError
status: completed
created: 2026-03-20T23:30:00Z
updated: 2026-03-21T00:00:00Z
completed: 2026-03-21T00:00:00Z
priority: high
tags: [autobuild, direct-mode, cancel-scope, generator, sdk, P0]
parent_review: TASK-REV-8BC0
feature_id: FEAT-8BC0
implementation_mode: task-work
wave: 1
complexity: 4
completed_location: tasks/completed/TASK-FIX-GEN1/
organized_files:
  - TASK-FIX-GEN1.md
---

# Task: Fix Direct-Mode Generator Lifecycle to Eliminate CancelledError

## Description

The `_invoke_with_role()` method in `agent_invoker.py` breaks out of the SDK `query()` async generator on `ResultMessage` (line 2062), leaving the generator suspended. The subsequent `gen.aclose()` in the `finally` block (line 2097) triggers AnyIO's cancel scope cleanup, which raises `CancelledError` because the cancel scope exits in a different asyncio Task context.

This causes a 40% failure rate on direct-mode Player invocations (per code comment at line 2091). State recovery mitigates data loss but wastes 1-2 turns per task.

## Root Cause

See deep dive: `.claude/reviews/TASK-REV-8BC0-deep-dive.md`, Finding 1 (REVISED).

The sequence is:
1. `async for message in gen` → receives `ResultMessage` → `break` (line 2062)
2. Generator is now **suspended** (not exhausted)
3. `finally` block calls `gen.aclose()` (line 2097)
4. `aclose()` triggers AnyIO cancel scope `__exit__` in wrong Task context
5. `CancelledError` raised → caught at line 2063 → **re-raised** at line 2087
6. Propagates up as `AgentInvocationResult(success=False, error="Cancelled: ...")`

## Acceptance Criteria

- [x] Direct-mode Player invocations no longer raise CancelledError from generator cleanup
- [x] The fix handles both successful completion (ResultMessage received) and genuine cancellation
- [x] Task-work mode behaviour is unchanged (already works correctly)
- [x] Existing tests pass; add regression test for the cancel scope scenario
- [x] The `_invoke_with_role` method at `agent_invoker.py:2039-2099` is modified

## Implementation (Option A — Drain Generator)

After receiving `ResultMessage`, the generator is drained to natural exhaustion:

```python
if isinstance(message, ResultMessage):
    self._last_session_id = getattr(message, "session_id", None)
    # TASK-FIX-GEN1: Drain remaining messages so the generator
    # exhausts naturally, preventing aclose() CancelledError.
    try:
        async for _ in gen:
            pass
    except Exception:
        pass  # safe to ignore during drain
    gen = None  # exhausted; skip aclose() in finally
    break
```

This mirrors how task-work mode already works — natural generator exhaustion avoids AnyIO cancel scope errors.

## Files Changed

- `guardkit/orchestrator/agent_invoker.py` (lines 2059-2073)
- `tests/unit/test_generator_close_fix.py` (3 new tests added)

## Test Results

- test_generator_close_fix.py: 12/12 passed
- test_agent_invoker.py + related: 464/464 passed
- No regressions introduced

## Key Files

- `guardkit/orchestrator/agent_invoker.py` (lines 2039-2099, 2063-2087)

## Notes

This is the highest-priority fix from the TASK-REV-8BC0 review. The 40% failure rate on direct-mode invocations means every direct-mode task wastes 1-2 turns.
