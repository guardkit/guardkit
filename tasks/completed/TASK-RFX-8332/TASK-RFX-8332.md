---
id: TASK-RFX-8332
title: Fix CancelledError on direct-mode Player invocations via explicit generator close
status: completed
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T22:10:00Z
completed: 2026-03-09T22:10:00Z
completed_location: tasks/completed/TASK-RFX-8332/
priority: high
complexity: 5
wave: 2
implementation_mode: task-work
parent_review: TASK-REV-A8C6
feature_id: FEAT-RFX
tags: [autobuild, cancelled-error, sdk, async]
dependencies: []
---

# Task: Fix CancelledError on Direct-Mode Player Invocations

## Description

Fix the CancelledError that hits 40% of direct-mode Player invocations by explicitly closing the `query()` async generator in the finally block, preventing GC finalization from scheduling `athrow(GeneratorExit)` in a wrong asyncio Task.

## Root Cause (90% Confidence)

The `query()` async generator from `claude_agent_sdk` creates an anyio TaskGroup with a cancel scope bound to the current asyncio Task. When `_invoke_with_role` returns after breaking from `async for`, the generator reference is dropped. Python's GC finalizer schedules `athrow(GeneratorExit)` in a new asyncio Task (Task-101), which tries to exit the cancel scope entered in the original Task, causing `RuntimeError` + `CancelledError`.

Direct mode is affected because `_invoke_with_role` creates background tasks (`_cancel_monitor`, `_safe_emit`) that affect event loop scheduling, and has an intermediate function boundary that allows the generator reference to be dropped before cleanup completes. Task-work delegation mode (`_invoke_task_work_implement`) runs the entire `query()` lifecycle inline without these interference patterns.

## Acceptance Criteria

- [x] `_invoke_with_role` (agent_invoker.py ~line 2012) holds explicit reference to `query()` generator
- [x] `_invoke_with_role` finally block calls `await gen.aclose()` with 5-second timeout
- [x] aclose() is wrapped in `suppress(Exception)` to prevent secondary failures
- [x] The task-work SDK call site (agent_invoker.py ~line 4448) has the same fix applied
- [x] `_install_sdk_cleanup_handler` is preserved as defense-in-depth
- [x] CancelledError handling in `invoke_player` (line ~1361) still works correctly as fallback
- [x] Unit tests verify generator is explicitly closed on normal exit (break on ResultMessage)
- [x] Unit tests verify generator is explicitly closed on exception path
- [x] Unit tests verify 5s timeout prevents blocking on unresponsive subprocess

## Implementation Sketch

```python
# In _invoke_with_role:
gen: Optional[AsyncIterator] = None
try:
    with measure_latency() as latency:
        try:
            async with asyncio.timeout(self.sdk_timeout_seconds):
                async with async_heartbeat(...):
                    gen = query(prompt=prompt, options=options)
                    async for message in gen:
                        response_messages.append(message)
                        if isinstance(message, ResultMessage):
                            break
        except (Exception, asyncio.CancelledError) as exc:
            ...
            raise
finally:
    if gen is not None:
        with suppress(Exception):
            try:
                async with asyncio.timeout(5):
                    await gen.aclose()
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
    # ... rest of existing finally block
```

## Risks

- `aclose()` may wait up to 5s for subprocess termination (mitigated by timeout)
- Double-close is safe (`aclose()` on closed generator is a no-op per PEP 525)
- 10% residual risk from edge cases with subprocess cleanup timing
