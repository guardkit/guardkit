---
id: TASK-DMRF-002
title: Improve state recovery has_work logic
status: completed
task_type: implementation
created: 2026-01-25T17:00:00Z
updated: 2026-01-25T17:30:00Z
completed_at: 2026-01-25T17:40:00Z
priority: high
complexity: 2
parent_review: TASK-REV-3EC5
feature_id: FEAT-DMRF
wave: 1
implementation_mode: task-work
dependencies: []
tags: [autobuild, state-recovery, robustness]
previous_state: in_review
workflow_mode: minimal
intensity_level: minimal
intensity_reason: "Task from review (parent_review=TASK-REV-3EC5), complexity=2/10"
completed_location: tasks/completed/TASK-DMRF-002/
organized_files: ["TASK-DMRF-002.md"]
---

# Task: Improve state recovery has_work logic

## Description

Fix the `has_work` logic in state recovery to correctly identify work when a Player report exists, even if `files_modified` and `files_created` are empty arrays.

## Problem

State recovery successfully loads the Player report, but then `has_work` returns False because:
- `files_modified` is empty
- `files_created` is empty
- `test_count` is 0

This causes valid work to be discarded.

**Evidence from logs**:
```
INFO:state_tracker:Loaded Player report from .../player_turn_1.json  # SUCCESS
INFO:autobuild:No work detected in .../worktrees/FEAT-F392           # PARADOX
```

## Acceptance Criteria

- [x] Modify `WorkState.has_work` to return True if Player report was loaded successfully
- [x] Add `player_report_loaded` flag to WorkState
- [x] Update `MultiLayeredStateTracker.capture_state()` to set this flag
- [x] When Player report exists, trust its contents even if file arrays are empty
- [x] Add unit tests for the new logic

## Implementation Summary

### Changes Made

1. **Added `player_report_loaded` field to WorkState** (line 98)
   - Type: `bool = False`
   - Purpose: Track when Player report successfully loaded
   - Backward compatible default

2. **Updated `has_work` property logic** (lines 113-115)
   - New priority: Check `player_report_loaded` first
   - If True, trust Player report (return True)
   - Otherwise, fall back to file/test detection

3. **Updated `_state_from_player_report()`** (line 385)
   - Sets `player_report_loaded=True` when creating WorkState from Player report
   - Ensures flag is set for proper detection

4. **Added 15 new unit tests**
   - TestPlayerReportLoadedFlag (4 tests)
   - TestHasWorkWithPlayerReportLoaded (8 tests)
   - TestPlayerReportLoadedIntegration (5 tests)

### Files Modified

- `guardkit/orchestrator/state_tracker.py` (2 locations changed)
- `tests/unit/test_state_tracker.py` (15 new tests added)

### Test Results

- Total tests: 42
- Passed: 42 (100%)
- Failed: 0
- Coverage: Not analyzed (MINIMAL intensity)

### Quality Gates

- ✅ Compilation: PASSED
- ✅ All tests passing: PASSED (42/42)
- ✅ Lint check: PASSED (no critical issues)
- ✅ Security: PASSED (no vulnerabilities)

## Related Files

- `guardkit/orchestrator/state_tracker.py` - Main implementation
- `guardkit/orchestrator/state_detection.py` - Detection logic (not modified)
- `tests/unit/test_state_tracker.py` - Tests
