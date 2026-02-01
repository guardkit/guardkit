---
id: TASK-VAL-WAVE-001
title: Add intra-wave dependency validation at feature load time
status: completed
created: 2026-02-01T00:00:00Z
updated: 2026-02-01T06:55:00Z
completed: 2026-02-01T06:55:00Z
priority: medium
tags: [feature-orchestration, validation, dependency-resolution, quality-gate]
task_type: feature
parent_review: TASK-REV-DEP1
complexity: 4
completed_location: tasks/completed/TASK-VAL-WAVE-001/
organized_files: [
  "TASK-VAL-WAVE-001.md"
]
---

# Task: Add intra-wave dependency validation at feature load time

## Description

Add validation in `FeatureLoader` to detect intra-wave dependency conflicts before orchestration begins. This prevents the confusing `DependencyError` at runtime by catching invalid configurations early with a clear error message.

## Background

From review TASK-REV-DEP1: When TASK-GR-PRE-003-D (depends on TASK-GR-PRE-003-C) was placed in the same wave as TASK-GR-PRE-003-C in FEAT-GR-MVP.yaml, the orchestrator correctly rejected the configuration with a `DependencyError`. However, this error occurred at runtime rather than at feature load time, making it harder to diagnose.

## Acceptance Criteria

- [x] Add `validate_parallel_groups()` method to `FeatureLoader`
- [x] Detect when any task depends on another task in the same parallel group
- [x] Return clear error messages identifying the specific conflict
- [x] Call validation during feature loading (before orchestration)
- [x] Add unit tests for validation logic
- [x] Update documentation

## Implementation Summary

### Files Modified

1. **`guardkit/orchestrator/feature_loader.py`**
   - Added `validate_parallel_groups()` static method (lines 737-768)
   - Integrated call into `validate_feature()` method (lines 684-686)

2. **`tests/unit/test_feature_loader.py`**
   - Added `TestIntraWaveDependencyValidation` class with 11 comprehensive tests

### Key Implementation Details

```python
@staticmethod
def validate_parallel_groups(feature: Feature) -> List[str]:
    """Validate that no task depends on another in same parallel group."""
    errors = []
    for wave_num, task_ids in enumerate(feature.orchestration.parallel_groups, 1):
        wave_set = set(task_ids)
        for task_id in task_ids:
            task = FeatureLoader.find_task(feature, task_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id in wave_set:
                        errors.append(
                            f"Wave {wave_num}: {task_id} depends on {dep_id} "
                            f"but both are in the same parallel group. "
                            f"Move {task_id} to a later wave."
                        )
    return errors
```

### Error Message Format

```
Wave 1: TASK-SC-002 depends on TASK-SC-001 but both are in the same parallel group. Move TASK-SC-002 to a later wave.
```

## Test Results

- **101/101 tests passing** (0 regressions)
- **11 new tests** for intra-wave validation
- **Coverage**: All code paths tested

## Quality Gates

| Gate | Status |
|------|--------|
| Compilation | ✅ Pass |
| Tests Passing | ✅ 101/101 (100%) |
| Code Review | ✅ Approved |

## Completion Details

- **Duration**: ~10 minutes
- **Complexity**: 4/10 (as estimated)
- **Intensity**: LIGHT (parent_review provenance)
- **Workflow**: /task-work → /task-complete

## References

- Review report: [TASK-REV-DEP1 Review Report](../../.claude/reviews/TASK-REV-DEP1-review-report.md)
- Feature loader: [feature_loader.py](../../guardkit/orchestrator/feature_loader.py)
- Feature orchestrator: [feature_orchestrator.py](../../guardkit/orchestrator/feature_orchestrator.py)
