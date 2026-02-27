---
id: TASK-VPR-002
title: Add ISO timestamps to autobuild log events
status: completed
completed: 2026-02-27T00:00:00Z
updated: 2026-02-27T00:00:00Z
previous_state: in_review
state_transition_reason: "All quality gates passed, task completed"
priority: medium
complexity: 3
tags: [autobuild, logging, observability, timestamps]
parent_review: TASK-REV-C960
feature_id: FEAT-VPR
wave: 1
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-VPR-002/
organized_files:
  - TASK-VPR-002-add-iso-timestamps-to-autobuild-logs.md
---

# Task: Add ISO Timestamps to AutoBuild Log Events

## Description

Add ISO 8601 timestamps to key autobuild log events to enable easier timing analysis without requiring heartbeat gap analysis.

## Context

TASK-REV-C960 Finding R5: The current log uses relative elapsed timers per SDK invocation but lacks absolute timestamps. Adding timestamps to key events would make timing analysis significantly easier, enable Docker stall detection, and improve debugging of production runs.

## Acceptance Criteria

- [x] ISO 8601 timestamps added to: wave start, wave end, turn start, turn end, Coach decision, task completion
- [x] Timestamp format: `2026-02-27T14:30:00.000Z` (UTC with milliseconds)
- [x] Timestamps appear in both verbose and non-verbose output modes
- [x] Log format: `[2026-02-27T14:30:00.000Z] Wave 1/4: TASK-DB-001`
- [x] Existing log structure and readability preserved
- [x] Unit tests verify timestamp presence in log output
- [x] All existing tests continue to pass

## Implementation Summary

### Files Modified
- `guardkit/orchestrator/progress.py` — Added `get_iso_timestamp()` utility function, timestamps in turn start/end events and logger output
- `guardkit/cli/display.py` — Added timestamps to wave start/end, task completion (success/failed/skipped/timeout) events

### Files Created
- `tests/unit/test_iso_timestamps.py` — 24 unit tests covering timestamp format, turn events, wave events, task completion, verbose/non-verbose modes

### Test Results
- 24 new tests: ALL PASSED
- 78 existing progress/display tests: ALL PASSED (zero regressions)
