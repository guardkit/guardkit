---
id: TASK-FIX-CEE8a
title: Fix direct mode test count propagation in _write_direct_mode_results
status: completed
created: 2026-02-10T15:00:00Z
updated: 2026-02-11T12:00:00Z
completed: 2026-02-11T12:00:00Z
completed_location: tasks/completed/TASK-FIX-CEE8a/
priority: high
tags: [autobuild, agent-invoker, direct-mode, bug-fix]
task_type: feature
complexity: 3
parent_review: TASK-REV-CEE8
test_results:
  status: passing
  coverage: null
  last_run: 2026-02-11T12:00:00Z
  tests_added: 6
  tests_total: 24
---

# Task: Fix direct mode test count propagation in _write_direct_mode_results

## Description

The `_write_direct_mode_results()` method in `agent_invoker.py` reads `tests_passed_count` from the Player report (line 2251), but this field is never set by direct mode Players. Direct mode Players follow `PLAYER_REPORT_SCHEMA` which defines `tests_passed` as a boolean. The `tests_passed_count` field only exists on the task-work delegation path (set at line 1531 by `_build_player_report`).

This causes `quality_gates.tests_passed` to always be `0` for direct mode tasks, triggering the zero-test anomaly check as a false positive when combined with the `feature` profile's `zero_test_blocking=True`.

## Root Cause

- **File**: `guardkit/orchestrator/agent_invoker.py`
- **Line**: 2251
- **Code**: `"tests_passed": player_report.get("tests_passed_count", 0)`
- **Problem**: `tests_passed_count` never exists in direct mode Player reports
- **Review**: `.claude/reviews/TASK-REV-CEE8-review-report.md` (Finding 1)

## Implementation Plan

### Change 1: Derive test count from available Player report data

**File**: `guardkit/orchestrator/agent_invoker.py`, lines 2236-2257

Replace the current test info extraction block with:

```python
# Extract test info from Player report
tests_run = player_report.get("tests_run", False)
tests_passed = player_report.get("tests_passed", False)
tests_written = player_report.get("tests_written", [])

# Derive test count: use tests_passed_count if available (task-work path),
# otherwise derive from tests_written list length when tests_passed is True
tests_passed_count = player_report.get("tests_passed_count", 0)
if tests_passed_count == 0 and tests_passed and tests_written:
    tests_passed_count = len(tests_written)
```

Then update the quality_gates dict to use `tests_passed_count`.

## Acceptance Criteria

- [x] AC-001: Direct mode Player with `tests_passed=True, tests_written=["a.py", "b.py"]` produces `quality_gates.tests_passed=2`
- [x] AC-002: Direct mode Player with `tests_passed=False, tests_written=["a.py"]` produces `quality_gates.tests_passed=0`
- [x] AC-003: Direct mode Player with `tests_passed=True, tests_written=[]` produces `quality_gates.tests_passed=0`
- [x] AC-004: Task-work path with `tests_passed_count=12` still produces `quality_gates.tests_passed=12` (no regression)
- [x] AC-005: All existing `test_write_direct_mode_results_*` tests pass
- [x] AC-006: All existing `TestZeroTestBlockingConfiguration` tests pass (no regression)

## Constraints

- Do NOT modify `_write_task_work_results()` (task-work delegation path)
- Do NOT modify `PLAYER_REPORT_SCHEMA`
- Do NOT modify `_check_zero_test_anomaly()` (that's TASK-FIX-CEE8b)
- Preserve `tests_passed_count` field usage for the task-work path (backward compatibility)
- Do NOT change null-handling behavior from TASK-FIX-64EE
