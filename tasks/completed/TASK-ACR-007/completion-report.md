# Completion Report: TASK-ACR-007

## Summary

Replaced fragile `asyncio.get_event_loop()` in `_capture_turn_state()` with robust event loop handling that uses the stored thread-local loop reference (from TASK-ACR-005) or creates a properly scoped temporary loop.

## Changes

### `guardkit/orchestrator/autobuild.py` (lines 2632-2676)

- Extracted `stored_loop` from `_thread_loaders` entry alongside the graphiti client
- Added loop selection: use stored loop if available and not closed, else create fresh one
- Wrapped `capture_turn_state()` call in `asyncio.wait_for()` with 30s timeout
- Added `try/finally` to clean up temporary loops
- Added `asyncio.TimeoutError` handling with warning log
- Removed all `asyncio.get_event_loop()` calls from the method

### `tests/unit/test_autobuild_orchestrator.py`

**Updated tests:**
- `test_capture_turn_state_uses_run_until_complete` - Removed fragile `asyncio.set_event_loop()` pattern
- `test_capture_turn_state_handles_runtime_error_gracefully` (renamed from `test_capture_turn_state_skips_when_no_event_loop`)

**New tests:**
- `test_capture_turn_state_uses_stored_loop_from_thread_loaders` - Verifies stored loop is used (AC-001)
- `test_capture_turn_state_creates_loop_when_stored_is_closed` - Verifies fresh loop fallback (AC-002)
- `test_capture_turn_state_after_worker_loop_cleanup` - Verifies capture works post-cleanup (AC-006)

## Test Results

- TestTurnStateCapture: 15/15 passed
- TestAutoBuildThreadLoaders: 7/7 passed
- Full suite: 104 passed, 12 failed (pre-existing, unrelated)

## Duration

~5 minutes (MINIMAL intensity, auto-detected from review provenance)
