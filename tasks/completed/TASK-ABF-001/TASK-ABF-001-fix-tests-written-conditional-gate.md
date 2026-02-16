---
id: TASK-ABF-001
title: Fix tests_written unconditional population
status: completed
created: 2026-02-16T00:00:00Z
updated: 2026-02-16T00:00:00Z
completed: 2026-02-16T12:00:00Z
priority: high
tags: [autobuild, bug-fix, data-quality, agent-invoker]
task_type: feature
complexity: 3
parent_review: TASK-REV-F3BE
feature_id: FEAT-ABF
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-16T12:00:00Z
  tests_passed: 464
  tests_failed: 0
---

# Task: Fix tests_written unconditional population

## Description

Remove the `if tests_info:` gate in `agent_invoker.py` that prevents `tests_written` from being populated when the Player doesn't include a `tests_info` block in `task_work_results.json`. This causes the Coach's zero-test anomaly check to see `tests_written=[]` even when test files exist in `files_created`/`files_modified`.

## Context

From review TASK-REV-F3BE (Finding 5): The `tests_written` field at `agent_invoker.py:1480-1492` is only populated inside an `if tests_info:` block. When the Player doesn't write `tests_info` (common in early turns), `tests_written` stays as `[]` regardless of whether test files appear in the file lists.

The direct mode synthetic report at `agent_invoker.py:1778-1784` already populates `tests_written` unconditionally from git changes. This fix aligns the task-work delegation path with that existing behavior.

## Acceptance Criteria

- [x] `tests_written` is populated from `files_created` + `files_modified` regardless of whether `tests_info` exists
- [x] `tests_info` fields (`tests_run`, `tests_passed`, `test_output_summary`) remain conditional on `tests_info` existing
- [x] Test file detection matches both `test_*.py` and `*_test.py` patterns
- [x] Existing tests pass without modification
- [x] New unit test: `tests_written` populated when `tests_info` absent but test files in `files_created`
- [x] New unit test: `tests_written` empty when no test files in file lists (regardless of `tests_info`)

## Implementation Summary

### Changes Made

**1. Production Fix** (`guardkit/orchestrator/agent_invoker.py:1488-1493`)
- Moved `tests_written` population outside the `if tests_info:` block
- Now always populated from `files_created` + `files_modified` regardless of `tests_info`
- Improved test file detection: uses `Path(f).name` to match filename only (not directory path)
- Matches both `test_*.py` prefix and `*_test.py` suffix patterns

**2. New Unit Tests** (`tests/unit/test_agent_invoker.py`)
- `test_tests_written_populated_when_tests_info_absent` - AC5
- `test_tests_written_empty_when_no_test_files_in_lists` - AC6
- `test_tests_written_detects_both_test_patterns` - AC3

### Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| `test_agent_invoker.py` | 381 | All passing |
| `test_agent_invoker_task_work_results.py` | 83 | All passing |
| Total | 464 | All passing |

## Key Files

- `guardkit/orchestrator/agent_invoker.py` (lines 1488-1493) - The fix location
- `tests/unit/test_agent_invoker.py` - New tests added to TestCreatePlayerReportFromTaskWork class
