---
id: TASK-FIX-01FC
title: Fall back to player report test data in state recovery
status: completed
completed: 2026-03-01T00:00:00Z
task_type: feature
parent_review: TASK-REV-A327
feature_id: FEAT-E4F5
wave: 1
implementation_mode: task-work
complexity: 2
priority: high
tags: [state-recovery, test-detection, p0, bugfix]
depends_on: []
---

# Task: Fall back to player report test data in state recovery

## Description

Fix `_state_from_player_report()` in `state_tracker.py` to fall back to the player report's test data when the CoachVerifier test re-run fails or times out. Currently, both branches of the ternary at lines 376-380 yield `test_count=0`, silently discarding the player report's `test_count` (which was 66 in the TASK-SAD-002 incident).

## Acceptance Criteria

- [x] `_state_from_player_report()` reads `test_count` from `player_report` when `test_results.tests_run` is False
- [x] `_state_from_player_report()` reads `tests_passed` from `player_report` when `test_results.tests_run` is False
- [x] All existing tests pass
- [x] Unit test: When CoachVerifier returns `tests_run=False, test_count=0` and player_report has `test_count=66, tests_passed=True`, the WorkState should have `test_count=66, tests_passed=True`
- [x] Unit test: When CoachVerifier succeeds, its results are still preferred over the player report

## Implementation Notes

- File: `guardkit/orchestrator/state_tracker.py`, lines 376-380
- Current code (broken):
  ```python
  test_count = (
      test_results.test_count
      if test_results and test_results.tests_run
      else 0  # ← Should be: player_report.get("test_count", 0)
  )
  ```
- The player_report parameter is already available in the method — it just isn't used for test data
- Also fix `tests_passed` fallback on line ~371-375 (same pattern)
- Expected interface from player report JSON: `{"test_count": int, "tests_passed": bool, "tests_written": list}`
