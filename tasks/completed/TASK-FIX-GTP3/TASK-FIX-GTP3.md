---
id: TASK-FIX-GTP3
title: Fix capture_turn_state unawaited coroutine
status: completed
created: 2026-02-09T14:00:00Z
updated: 2026-02-09T16:05:00Z
completed: 2026-02-09T16:05:00Z
priority: medium
tags: [fix, graphiti, asyncio, coroutine, autobuild]
task_type: implementation
complexity: 3
feature: FEAT-C90E
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-09T16:00:00Z
---

# Task: Fix capture_turn_state Unawaited Coroutine

## Description

Fix BUG-2 from the TASK-REV-2AA0 review: `_capture_turn_state()` in `autobuild.py` uses `asyncio.create_task()` without a running event loop, causing the coroutine to never be awaited and producing `RuntimeWarning: coroutine 'capture_turn_state' was never awaited`.

See: `.claude/reviews/TASK-REV-2AA0-review-report.md` (BUG-2: Unawaited `capture_turn_state` Coroutine)

### Current Code (autobuild.py ~line 2412)

```python
# In _capture_turn_state() - called from sync _loop_phase()
graphiti = get_graphiti()
if graphiti and graphiti.enabled:
    asyncio.create_task(capture_turn_state(graphiti, entity))  # BUG: No running loop
```

### Problem

- `asyncio.create_task()` requires a running event loop in the current thread
- `_capture_turn_state()` is called from sync `_loop_phase()` in a worker thread
- Between `loop.run_until_complete()` calls, there is no running loop
- The RuntimeError is caught at line 2417, but the coroutine object leaks (never awaited)
- Turn state data is silently NOT captured to Graphiti

### Fix

Replace `asyncio.create_task()` with `loop.run_until_complete()` using the thread's event loop:

```python
try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(capture_turn_state(graphiti, entity))
except RuntimeError:
    logger.debug("No event loop available, skipping turn state capture")
except Exception as e:
    logger.warning(f"Error capturing turn state: {e}")
```

## Acceptance Criteria

- [x] `asyncio.create_task()` replaced with `loop.run_until_complete()` in `_capture_turn_state()`
- [x] Uses `asyncio.get_event_loop()` to get the thread's current loop
- [x] RuntimeError caught gracefully (no event loop → skip with debug log)
- [x] General exceptions caught with warning log (existing behavior preserved)
- [x] Coroutine is properly awaited (no RuntimeWarning leak)
- [x] Existing tests pass (61 passed, 12 pre-existing failures from git worktree deps)
- [x] New test: capture_turn_state called successfully with event loop available
- [x] New test: capture_turn_state skipped gracefully when no event loop

## Key Files

### Must Modify
- `guardkit/orchestrator/autobuild.py` — `_capture_turn_state()` method (~line 2400-2420)

### Must Update Tests
- `tests/unit/test_autobuild_orchestrator.py` — Add tests for the fixed capture path

### Reference
- `.claude/reviews/TASK-REV-2AA0-review-report.md` — BUG-2 analysis
- `guardkit/knowledge/turn_state_operations.py` — `capture_turn_state()` definition

## Context

- Independent of TASK-FIX-GTP1 (factory) — can be done in parallel
- BUG-2 from TASK-REV-2AA0 review
- Impact: Turn state not captured to Graphiti (3 occurrences in the analyzed run)
- NOT the stall cause — correctly caught by try/except, but produces RuntimeWarning

## Test Execution Log

[Automatically populated by /task-work]
