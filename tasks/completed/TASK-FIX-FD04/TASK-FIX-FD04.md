---
id: TASK-FIX-FD04
title: Fix unawaited coroutine warning in get_thread_client error path
status: completed
created: 2026-02-09T22:00:00Z
updated: 2026-02-09T22:00:00Z
completed: 2026-02-09T23:30:00Z
priority: low
tags: [fix, graphiti, coroutine, warning, cleanup, cosmetic]
task_type: implementation
complexity: 2
feature: null
parent_review: TASK-REV-B9E1
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-09T23:30:00Z
  tests_passed: 20
  tests_failed: 0
  new_tests: 4
---

# Task: Fix Unawaited Coroutine Warning in get_thread_client Error Path

## Description

Fix the `RuntimeWarning: coroutine 'GraphitiClient.initialize' was never awaited` at `graphiti_client.py:1489`. This is the P4 (cosmetic) fix from TASK-REV-B9E1.

### Problem

When `asyncio.run(client.initialize())` at line 1479 fails due to FD exhaustion (`[Errno 24]`), the failure occurs during event loop creation (specifically `os.pipe()` for the selector event loop self-pipe), **before** the coroutine is scheduled. The coroutine object `client.initialize()` was created as a Python object but never started. When Python's garbage collector collects this unawaited coroutine, it emits:

```
graphiti_client.py:1489: RuntimeWarning: coroutine 'GraphitiClient.initialize' was never awaited
```

### Solution

Restructured `get_thread_client()` to separate coroutine creation from `asyncio.run()` invocation, allowing explicit cleanup in the error path:

```python
# In get_thread_client(), lines 1477-1490:
else:
    coro = client.initialize()
    try:
        success = asyncio.run(coro)
        if success:
            self._thread_local.client = client
            logger.info("Graphiti factory: thread client initialized successfully")
            return client
        else:
            logger.info("Graphiti factory: thread client init failed")
            return None
    except Exception as e:
        coro.close()  # Suppress RuntimeWarning by explicitly closing
        logger.info(f"Graphiti factory: thread client init error: {e}")
        return None
```

**Note**: `asyncio.run()` may have already consumed (and failed) the coroutine before raising. Calling `coro.close()` on an already-consumed coroutine is a no-op (safe). If it was never consumed, `close()` prevents the RuntimeWarning.

## Acceptance Criteria

- [x] No `RuntimeWarning: coroutine was never awaited` when `asyncio.run()` fails during initialization
- [x] Coroutine explicitly closed via `coro.close()` in the exception handler
- [x] Normal operation (successful init) unaffected
- [x] Unit tests: verify no warning emitted when asyncio.run raises OSError
- [x] No regressions in existing GraphitiClientFactory tests

## Files Changed

- `guardkit/knowledge/graphiti_client.py` -- `get_thread_client()` lines 1477-1490
- `tests/knowledge/test_graphiti_client_factory.py` -- Added `TestUnawaitedCoroutineWarningFix` (4 tests)

## Context

- Review: TASK-REV-B9E1 (P4 fix)
- Review report: `.claude/reviews/TASK-REV-B9E1-review-report.md` Section 7c
- This only triggers during FD exhaustion (or other event loop creation failures)
- After TASK-FIX-FD01 raises the FD limit, this will rarely occur, but it's good hygiene

## Dependencies

None -- independent, low priority.
