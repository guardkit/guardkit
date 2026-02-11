---
id: TASK-FIX-93A1
title: "Add tests_written field to both task_work_results.json writers"
status: completed
created: 2026-02-11T22:00:00Z
completed: 2026-02-11T23:30:00Z
priority: medium
tags: [autobuild, quality-gates, zero-test-anomaly, agent-invoker, defense-in-depth]
task_type: feature
complexity: 4
parent_review: TASK-REV-93E1
fix_id: FIX-93E1-A
---

# Task: Add tests_written to Both Results Writers (FIX-93E1-A, P1)

## Description

Neither `_write_direct_mode_results()` nor `_write_task_work_results()` in `agent_invoker.py` writes the `tests_written` field to `task_work_results.json`. The Coach's `_check_zero_test_anomaly()` reads `task_work_results.get("tests_written", [])` at line 1574, which always returns `[]` regardless of execution path.

This is a **defense-in-depth** fix. The primary protection against false zero-test anomalies is FIX-93E1-B (recursive glob, TASK-FIX-93B1). This fix provides an additional escape hatch when:
- `_detect_tests_from_results()` returns None (Player reported 0 files on a revert turn)
- The recursive glob also fails (test files don't match the `test_{prefix}*` naming pattern)
- But the Player DID create tests (reported in `tests_written` in the player report)

## Acceptance Criteria

- [x] AC-001: `_write_direct_mode_results()` includes `tests_written` in the results dict
- [x] AC-002: `_write_task_work_results()` includes `tests_written` in the results dict
- [x] AC-003: When Player reports `tests_written: ["tests/health/test_router.py"]`, Coach's `_check_zero_test_anomaly()` sees `tests_written: ["tests/health/test_router.py"]` (not `[]`)
- [x] AC-004: When Player reports no tests (`tests_written: []`), Coach still sees `tests_written: []` (no change in behavior)
- [x] AC-005: `tests_written` is deduplicated (no duplicate entries) in both writers
- [x] AC-006: Existing tests pass without modification
- [x] AC-007: New tests verify `tests_written` is written to results JSON for both paths (11 new tests, exceeds 4 minimum)
- [x] AC-008: No regressions in zero-test anomaly tests

## Changes Made

### Change 1: Direct Mode Results Writer
**File**: `guardkit/orchestrator/agent_invoker.py:2267`
Added `"tests_written": sorted(list(set(tests_written))),` to the results dict.

### Change 2: Task-Work Delegation Results Writer
**File**: `guardkit/orchestrator/agent_invoker.py:3168`
Added `"tests_written": sorted(list(set(result_data.get("tests_written", [])))),` to the results dict.

## Tests Added: 11

| Test File | Class | Count |
|-----------|-------|-------|
| `test_agent_invoker_task_work_results.py` | `TestTaskWorkResultsTestsWritten` | 5 |
| `test_agent_invoker.py` | `TestDirectModeRouting` (93A1 section) | 4 |
| `test_coach_validator.py` | `TestTestsWrittenEndToEnd` | 2 |

## Test Results

- 83 passed in `test_agent_invoker_task_work_results.py` (78 existing + 5 new, 0 regressions)
- 28 passed in `test_agent_invoker.py` DirectMode tests (24 existing + 4 new, 0 regressions)
- 37 passed in `test_coach_validator.py` zero-test anomaly tests (35 existing + 2 new, 0 regressions)

## Reference

- Review report: `.claude/reviews/TASK-REV-93E1-review-report.md`
- Parent review: TASK-REV-93E1
