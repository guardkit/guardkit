---
id: TASK-FB-FIX-002
title: "Add plan existence validation in pre-loop"
status: completed
created: 2026-01-10T11:45:00Z
updated: 2026-01-10T14:30:00Z
completed: 2026-01-10T14:30:00Z
priority: high
implementation_mode: task-work
wave: 1
conductor_workspace: fb-fix-wave1-2
complexity: 3
parent_task: TASK-REV-FB04
tags:
  - feature-build
  - pre-loop
  - validation
---

# TASK-FB-FIX-002: Add Plan Existence Validation in Pre-Loop

## Summary

Add validation in `PreLoopQualityGates` to verify the implementation plan file exists before returning success, preventing the broken state where pre-loop claims success but no plan exists.

## Problem

Currently, pre-loop returns success even when `plan_path=None` or the file doesn't exist. This causes the Player agent to fail later with "Implementation plan not found".

## Target File

`guardkit/orchestrator/quality_gates/pre_loop.py`

## Requirements

1. After design phase execution, validate plan file exists
2. If plan is missing, raise `QualityGateBlocked` with actionable error message
3. Log the plan path for debugging
4. Update `PreLoopResult` to require non-None `plan_path`

## Acceptance Criteria

- [x] Pre-loop raises `QualityGateBlocked` if plan file doesn't exist
- [x] Error message includes expected plan path(s)
- [x] Error message suggests running `task-work --design-only` manually
- [x] Successful pre-loop logs the plan path
- [x] Unit tests cover both success and failure cases

## Implementation Notes

### Validation Location

Add validation in `_extract_pre_loop_results()`:

```python
def _extract_pre_loop_results(
    self,
    task_id: str,
    result: DesignPhaseResult,
) -> PreLoopResult:
    # Validate plan exists
    plan_path = result.plan_path
    if not plan_path:
        raise QualityGateBlocked(
            f"Design phase did not return plan path for {task_id}. "
            "The task-work --design-only execution may have failed."
        )

    if not Path(plan_path).exists():
        raise QualityGateBlocked(
            f"Implementation plan not found at {plan_path} for {task_id}. "
            "Run task-work --design-only manually to debug."
        )

    logger.info(f"Pre-loop validated plan exists at: {plan_path}")

    # ... rest of extraction
```

### Alternative: Check Multiple Paths

If plan can be at multiple locations, check all and use first found:

```python
from guardkit.orchestrator.paths import TaskArtifactPaths  # From TASK-FB-FIX-003

plan_path = TaskArtifactPaths.find_plan(task_id, self.worktree_path)
if not plan_path:
    expected = TaskArtifactPaths.implementation_plan(task_id, self.worktree_path)
    raise QualityGateBlocked(
        f"Implementation plan not found for {task_id}. "
        f"Expected at one of: {[str(p) for p in expected]}"
    )
```

## Test Strategy

1. **Test plan exists**: Mock file system, verify success
2. **Test plan missing**: Mock file system with no plan, verify `QualityGateBlocked` raised
3. **Test error message**: Verify message is actionable

## Dependencies

- None (can run in parallel with TASK-FB-FIX-001)
- Optional: TASK-FB-FIX-003 for centralized paths (can inline paths initially)

## Estimated Effort

1 hour

## Implementation Summary

### Changes Made

1. **guardkit/orchestrator/quality_gates/pre_loop.py** (`_extract_pre_loop_results()`)
   - Added validation for `plan_path` being None (raises `QualityGateBlocked` with `gate_name="plan_generation"`)
   - Added validation for plan file existence (raises `QualityGateBlocked` with `gate_name="plan_validation"`)
   - Added logging for successful plan validation
   - Error messages include task ID, plan path, and suggestion to run `task-work --design-only` manually

2. **tests/unit/test_pre_loop_delegation.py**
   - Added `mock_plan_file` fixture to create actual plan files for tests
   - Updated `mock_design_result` fixture to use real plan file paths
   - Added new `TestPlanValidation` class with 6 tests:
     - `test_raises_when_plan_path_is_none`
     - `test_raises_when_plan_file_missing`
     - `test_error_message_suggests_manual_debug`
     - `test_success_when_plan_file_exists`
     - `test_validation_checks_path_before_existence`
     - `test_empty_string_plan_path_treated_as_missing`
   - Updated existing tests to use `mock_plan_file` fixture for valid plan paths

### Test Results

All 57 tests pass (includes 6 new plan validation tests).
