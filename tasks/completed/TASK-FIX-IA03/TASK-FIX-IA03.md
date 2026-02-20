---
id: TASK-FIX-IA03
title: Exclude internal artifacts from documentation constraint count
status: completed
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T02:00:00Z
completed: 2026-02-20T02:00:00Z
priority: medium
tags: [autobuild, bugfix, documentation-constraint, artifacts]
task_type: feature
complexity: 3
parent_review: TASK-REV-A515
feature_id: FEAT-AOF
wave: 1
implementation_mode: task-work
previous_state: in_review
state_transition_reason: "All acceptance criteria met, 23/23 tests passing"
completed_location: tasks/completed/TASK-FIX-IA03/
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-20T02:00:00Z
  tests_passed: 23
  tests_failed: 0
---

# Task: Exclude internal artifacts from documentation constraint count

## Description

The `_validate_file_count_constraint()` method in `guardkit/orchestrator/agent_invoker.py` counts `player_turn_N.json` (an AutoBuild internal artifact) as a user-created file. Since every task-work delegation creates this file, it always consumes one slot of the 2-file budget for "minimal" level, causing 7/12 tasks to trigger false constraint violations.

The fix is to exclude `.guardkit/autobuild/*/player_turn_*.json` and other internal artifacts from the constraint count rather than raising the numeric limit.

## Source

- Review report: `.claude/reviews/TASK-REV-A515-review-report.md` (Finding 4)
- Evidence: All 7 violations include `player_turn_1.json` in the file list

## Files Modified

- `guardkit/orchestrator/agent_invoker.py` — filter `.guardkit/autobuild/` paths before counting
- `tests/unit/test_agent_invoker.py` — updated 3 existing assertions + added 4 new artifact exclusion tests
- `tests/unit/test_agent_invoker_task_work_results.py` — updated 1 existing assertion

## Acceptance Criteria

- [x] `player_turn_N.json` excluded from documentation constraint count
- [x] All `.guardkit/autobuild/*` paths excluded from constraint count
- [x] Warning message shows "user files" count (excluding artifacts)
- [x] Unit test verifies artifact exclusion
- [x] Tasks creating command spec + test file (2 user files) no longer trigger warning at "minimal" level
