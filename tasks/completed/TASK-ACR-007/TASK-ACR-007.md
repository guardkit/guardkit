---
id: TASK-ACR-007
title: "Fix event loop handling in turn state capture"
status: completed
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T14:30:00Z
completed: 2026-02-15T14:30:00Z
completed_location: tasks/completed/TASK-ACR-007/
priority: high
task_type: feature
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-ACR-005
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
tags: [autobuild, asyncio, turn-state, f3-fix]
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-15T14:15:00Z
  tests_passed: 22
  tests_failed: 0
organized_files:
  - TASK-ACR-007.md
  - completion-report.md
---

# Task: Fix event loop handling in turn state capture

## Description

Replace the fragile `asyncio.get_event_loop()` pattern in `_capture_turn_state()` with a robust approach that uses the stored thread-local loop reference or creates a properly scoped temporary loop.

## Files Modified

- `guardkit/orchestrator/autobuild.py` — `_capture_turn_state()` (lines 2632-2676)
- `tests/unit/test_autobuild_orchestrator.py` — `TestTurnStateCapture` class (3 new tests, 2 updated)

## Acceptance Criteria

- [x] AC-001: Uses thread-local loader's stored loop reference if available (from TASK-ACR-005)
- [x] AC-002: If no loop available, creates a fresh one with `asyncio.new_event_loop()` scoped to the operation
- [x] AC-003: Temporary loops are always cleaned up after use (try/finally)
- [x] AC-004: Timeout of 30s to prevent blocking the main loop
- [x] AC-005: No `asyncio.get_event_loop()` calls remain in `_capture_turn_state()`
- [x] AC-006: Unit test verifies turn state capture works after worker loop cleanup
