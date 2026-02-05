---
id: TASK-AB-SD01
title: "Add unrecoverable stall detection to AutoBuild loop"
status: completed
completed: 2026-02-05T00:00:00Z
priority: high
task_type: feature
complexity: 5
parent_review: TASK-REV-D4B1
wave: 1
implementation_mode: task-work
completed_location: tasks/completed/TASK-AB-SD01/
tags:
  - autobuild
  - stall-detection
  - loop-exit
  - quality-of-life
---

## Description

Add early exit logic to the AutoBuild Player-Coach loop when an unrecoverable stall is detected. Currently, when `should_rollback()` fires but `find_last_passing_checkpoint()` returns `None` (no turn ever passed), the loop silently continues until MAX_TURNS_EXCEEDED — wasting turns and compute.

This task implements two stall detection mechanisms:

1. **No-passing-checkpoint exit**: When context pollution is detected but no passing checkpoint exists, exit immediately with `unrecoverable_stall` status
2. **Repeated identical feedback exit**: When Coach gives identical feedback N consecutive turns with 0% criteria progress, exit early

## Evidence

See [TASK-REV-D4B1 review report](.claude/reviews/TASK-REV-D4B1-review-report.md) Finding 5.

In the FEAT-CR01 failure, this would have saved 53 of 55 wasted turns (~48 minutes of compute).

## Files Modified

1. `guardkit/orchestrator/autobuild.py` — Added stall detection in `_loop_phase()`, new `_is_feedback_stalled()` and `_count_criteria_passed()` methods, extended type signatures and status handling
2. `guardkit/orchestrator/progress.py` — Extended `FinalStatus` type and `status_colors` for `unrecoverable_stall`
3. `tests/unit/test_autobuild_stall_detection.py` — NEW: 18 unit tests covering both stall mechanisms

## Acceptance Criteria

- [x] When `should_rollback()=True` and `find_last_passing_checkpoint()=None`, loop exits with `unrecoverable_stall`
- [x] When identical Coach feedback repeats 3+ turns with 0% criteria progress, loop exits early
- [x] `unrecoverable_stall` status is handled in feature_orchestrator (same as `max_turns_exceeded`)
- [x] Progress display shows clear message for `unrecoverable_stall`
- [x] Worktree preserved for inspection on stall exit
- [x] Unit tests cover both stall detection mechanisms
- [x] Unit tests verify loop exits early (not at MAX_TURNS)
- [x] Existing rollback-to-passing-checkpoint behaviour is unchanged
