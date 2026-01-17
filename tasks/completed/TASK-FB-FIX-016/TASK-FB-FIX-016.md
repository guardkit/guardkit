---
id: TASK-FB-FIX-016
title: Increase default SDK timeout to 1800s
status: completed
created: 2026-01-13T15:45:00Z
updated: 2026-01-13T16:10:00Z
completed: 2026-01-13T16:10:00Z
priority: medium
tags:
  - feature-build
  - sdk
  - timeout
  - configuration
complexity: 2
parent_review: TASK-REV-FB11
implementation_mode: direct
estimated_minutes: 30
actual_minutes: 15
dependencies: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-01-13T16:05:00Z
  tests_passed: 239
  tests_failed: 0
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-FB-FIX-016/
organized_files:
  - TASK-FB-FIX-016.md
---

# Increase Default SDK Timeout to 1800s

## Description

Increase the default SDK timeout from 600 seconds (10 minutes) to 1800 seconds (30 minutes). With pre-loop disabled for feature-build (TASK-FB-FIX-015), the loop phase alone needs ~600-900s. A 1800s default provides adequate headroom without the 2+ hour timeout needed for full design phase.

## Objectives

- Change `DEFAULT_SDK_TIMEOUT` from 600 to 1800 in both locations
- Update documentation comments

## Acceptance Criteria

- [x] `guardkit/orchestrator/agent_invoker.py:45` changed to 1800
- [x] `guardkit/orchestrator/quality_gates/task_work_interface.py:48` changed to 1800
- [x] Environment variable `GUARDKIT_SDK_TIMEOUT` still works as override
- [x] Tests pass with new default

## Technical Approach

**Location 1**: `guardkit/orchestrator/agent_invoker.py:45`
```python
# FROM:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "600"))

# TO:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "1800"))
```

**Location 2**: `guardkit/orchestrator/quality_gates/task_work_interface.py:48`
```python
# FROM:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "600"))

# TO:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "1800"))
```

## Files Modified

- `guardkit/orchestrator/agent_invoker.py` (line 44-47)
- `guardkit/orchestrator/quality_gates/task_work_interface.py` (line 47-50)
- `tests/unit/test_agent_invoker.py` (line 131) - Updated test expectation

## Test Requirements

- [x] Verify DEFAULT_SDK_TIMEOUT is 1800
- [x] Verify environment variable override still works

## Implementation Summary

Changed `DEFAULT_SDK_TIMEOUT` from 600 to 1800 in both locations:
1. `guardkit/orchestrator/agent_invoker.py` - The main agent invoker used by AutoBuild
2. `guardkit/orchestrator/quality_gates/task_work_interface.py` - The TaskWorkInterface for design phase delegation

Also added explanatory comments referencing TASK-FB-FIX-015 to explain why 1800s is appropriate now that pre-loop is disabled.

Updated the unit test in `test_agent_invoker.py` to expect 1800 instead of 600.

Verified:
- Both modules import the new default correctly (1800)
- Environment variable override still works (tested with GUARDKIT_SDK_TIMEOUT=3600)
- All 239 tests in both test files pass

## Notes

This change complements TASK-FB-FIX-015. With pre-loop disabled, 1800s is sufficient for the loop phase. Users who enable pre-loop should use `--sdk-timeout 7200` or higher.
