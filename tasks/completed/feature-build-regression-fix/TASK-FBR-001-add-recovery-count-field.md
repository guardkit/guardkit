---
id: TASK-FBR-001
title: Add recovery_count field to TaskExecutionResult dataclass
status: completed
task_type: bug-fix
implementation_mode: task-work
priority: critical
complexity: 2
wave: 1
parallel_group: feature-build-regression-fix-wave1-1
created: 2026-01-25T15:35:00Z
updated: 2026-01-25T16:15:00Z
completed: 2026-01-25T16:20:00Z
parent_review: TASK-REV-FB
feature_id: FEAT-FBR
tags:
  - regression
  - bug-fix
  - autobuild
  - dataclass
dependencies: []
---

# TASK-FBR-001: Add recovery_count Field to TaskExecutionResult

## Problem Statement

The `TaskExecutionResult` dataclass in `feature_orchestrator.py` is missing the `recovery_count` field that was added to `OrchestrationResult` in TASK-PRH-003. This causes a runtime crash at line 937:

```
AttributeError: 'TaskExecutionResult' object has no attribute 'recovery_count'
```

## Root Cause

TASK-PRH-003 (commit `56bf0e63`) added `recovery_count` tracking to `OrchestrationResult` (autobuild.py) but failed to add the corresponding field to `TaskExecutionResult` (feature_orchestrator.py), despite the latter being used to aggregate wave results.

## Implementation

### Step 1: Update TaskExecutionResult Dataclass

Add `recovery_count: int = 0` to the dataclass definition at `feature_orchestrator.py:59-81`:

```python
@dataclass
class TaskExecutionResult:
    """Result of executing a single task within a feature."""
    task_id: str
    success: bool
    total_turns: int
    final_decision: str
    error: Optional[str] = None
    recovery_count: int = 0  # ADD THIS
```

### Step 2: Update TaskExecutionResult Creation Sites

Pass `recovery_count` from `OrchestrationResult` in all creation sites:

| Line | Context | Change Needed |
|------|---------|---------------|
| 1011 | already_completed | Pass `recovery_count=0` (default) |
| 1033 | skipped (dependency failed) | Pass `recovery_count=0` (default) |
| 1268 | successful orchestration | Pass `recovery_count=result.recovery_count` |
| 1278 | error case | Pass `recovery_count=0` (default) |
| 1345 | error helper | Pass `recovery_count=0` (default) |

### Step 3: Verify Line 937 Works

After adding the field, this line should work correctly:
```python
recovered = sum(1 for r in wave_result.results if r.recovery_count > 0)
```

## Acceptance Criteria

- [x] `TaskExecutionResult` dataclass has `recovery_count: int = 0` field
- [x] All creation sites of `TaskExecutionResult` pass appropriate `recovery_count` value
- [x] Line 937 no longer raises `AttributeError`
- [x] Feature-build completes wave execution without crash
- [x] Unit tests pass for `TaskExecutionResult` instantiation

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/feature_orchestrator.py` | Add field + update 5 creation sites |

## Test Plan

1. Run existing unit tests for feature_orchestrator
2. Create integration test that verifies `recovery_count` is populated
3. Run the failing scenario from `docs/reviews/feature-build/orchestrator_error.md`

## Related

- **Parent Review**: TASK-REV-FB
- **Regression Source**: TASK-PRH-003
- **Error Evidence**: `docs/reviews/feature-build/orchestrator_error.md`
