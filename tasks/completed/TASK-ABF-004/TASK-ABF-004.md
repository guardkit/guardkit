---
id: TASK-ABF-004
title: Add cumulative git diff fallback for test detection
status: completed
created: 2026-02-16T00:00:00Z
updated: 2026-02-16T12:45:00Z
completed: 2026-02-16T12:45:00Z
completed_location: tasks/completed/TASK-ABF-004/
priority: medium
tags: [autobuild, enhancement, test-detection, coach-validator]
task_type: feature
complexity: 5
parent_review: TASK-REV-F3BE
feature_id: FEAT-ABF
wave: 2
implementation_mode: task-work
dependencies: [TASK-ABF-001, TASK-ABF-002]
previous_state: in_review
state_transition_reason: "All quality gates passed and acceptance criteria verified"
test_results:
  status: passed
  total: 199
  passed: 199
  failed: 0
  new_tests: 4
  last_run: 2026-02-16T12:30:00Z
---

# Task: Add cumulative git diff fallback for test detection

## Description

Add a tertiary fallback in `coach_validator.py`'s `_detect_test_command` method that uses a cumulative git diff (from the task's first checkpoint parent to HEAD) to find test files created during the current task's lifetime. This handles the case where checkpoint commits make test files invisible to both the primary detection (from `task_work_results`) and the fallback glob pattern.

## Context

From review TASK-REV-F3BE (Rec 1): After each turn, `git add -A && git commit` commits all files including tests. On subsequent turns, `git diff --name-only HEAD` only shows changes since the LAST checkpoint, not since the task started. The cumulative diff looks across ALL checkpoints for the current task, finding test files that were created in any previous turn.

**IMPORTANT**: Do NOT use a broad `glob("tests/**/test_*.py")` approach. In shared worktrees (feature mode), multiple tasks run in the same worktree. A broad glob would pick up test files from OTHER parallel tasks with unresolved dependencies. This concern is documented at `coach_validator.py:1557-1560`. The cumulative diff is safe because it only finds files changed during the current task's turns.

## Acceptance Criteria

- [x] Tertiary fallback activates only when primary detection AND task-ID glob both fail
- [x] Uses `git diff --name-only <first-checkpoint-parent> HEAD` to find all changed files
- [x] Filters to test files matching `test_*.py` or `*_test.py` patterns
- [x] Verifies test files still exist in the worktree (not deleted)
- [x] Returns `pytest <files> -v --tb=short` command if test files found
- [x] Does NOT find test files from other tasks in shared worktrees
- [x] Handles missing checkpoint gracefully (returns None, falls through)
- [x] New test: finds test files across checkpoint boundaries
- [x] New test: does NOT find test files from pre-task commits
- [x] New test: handles no checkpoint commits gracefully
- [x] Existing tests pass without modification

## Implementation Summary

### Files Modified

1. **guardkit/orchestrator/quality_gates/coach_validator.py**
   - Added `_find_first_checkpoint_parent()` helper method (lines 1545-1600)
     - Reads `.guardkit/autobuild/{task_id}/checkpoints.json`
     - Gets first checkpoint's `commit_hash`
     - Returns parent via `git rev-parse {hash}~1`
     - Returns None gracefully on any error
   - Added tertiary cumulative diff fallback in `_detect_test_command()` (lines 1670-1700)
     - Runs `git diff --name-only {parent} HEAD`
     - Filters to test files that exist on disk
     - Returns pytest command if tests found

2. **tests/unit/test_coach_validator.py**
   - Added `TestCumulativeDiffFallback` class with 4 tests (lines 3993-4115)

## Test Execution Log

```
Compilation: PASSED
Tests: 199/199 PASSED (100%)
New tests: 4/4 PASSED
  - test_cumulative_diff_finds_tests_across_checkpoints: PASSED
  - test_cumulative_diff_excludes_pre_task_files: PASSED
  - test_cumulative_diff_handles_no_checkpoints: PASSED
  - test_cumulative_diff_handles_git_failure: PASSED
Regressions: None
Code Review: APPROVED
```
