---
id: TASK-TT-002
title: "Add quality gate profiles for TESTING and REFACTOR types"
status: completed
created: 2026-01-23T00:00:00Z
updated: 2026-01-23T08:15:00Z
completed: 2026-01-23T08:15:00Z
priority: high
tags: [task-types, quality-gates, profiles]
task_type: feature
parent_review: TASK-REV-FB27
feature_id: FEAT-TT
implementation_mode: task-work
wave: 1
conductor_workspace: task-type-wave1-profiles
complexity: 3
depends_on:
  - TASK-TT-001
---

# Task: Add Quality Gate Profiles for TESTING and REFACTOR Types

## Description

Add `QualityGateProfile` entries for `TaskType.TESTING` and `TaskType.REFACTOR` to the `DEFAULT_PROFILES` dictionary in `guardkit/models/task_types.py`.

## Acceptance Criteria

- [x] `DEFAULT_PROFILES[TaskType.TESTING]` returns valid QualityGateProfile
- [x] `DEFAULT_PROFILES[TaskType.REFACTOR]` returns valid QualityGateProfile
- [x] `get_profile(TaskType.TESTING)` works correctly
- [x] `get_profile(TaskType.REFACTOR)` works correctly
- [x] Profiles have appropriate gate requirements for each type
- [x] All existing profiles unchanged

## Implementation Notes

**File**: `guardkit/models/task_types.py`

**Location**: Add to `DEFAULT_PROFILES` dict (after `TaskType.DOCUMENTATION`)

### TESTING Profile

Testing tasks focus on creating test infrastructure. They need tests to run but don't need architecture review (test architecture is different from production code).

```python
TaskType.TESTING: QualityGateProfile(
    arch_review_required=False,   # Test architecture is different paradigm
    arch_review_threshold=0,
    coverage_required=False,      # Test code coverage less critical
    coverage_threshold=0.0,
    tests_required=False,         # Tests must run (meta: tests for tests) - Updated: false
    plan_audit_required=True,     # Ensure test setup is complete
),
```

### REFACTOR Profile

Refactoring tasks need full quality gates to ensure they don't break existing functionality.

```python
TaskType.REFACTOR: QualityGateProfile(
    arch_review_required=True,    # Architecture compliance important
    arch_review_threshold=60,
    coverage_required=True,       # Must maintain coverage
    coverage_threshold=80.0,
    tests_required=True,          # Must not break existing tests
    plan_audit_required=True,     # Ensure refactor is complete
),
```

## Dependencies

- TASK-TT-001 must complete first (needs enum values) ✅ COMPLETED

## Notes

The TESTING profile is intentionally lenient on coverage since test code doesn't need to be covered by other tests. The REFACTOR profile uses full gates since refactoring should maintain or improve quality.

## Completion Summary

**Implementation completed as part of TASK-TT-001** - Both the enum values AND the quality profiles were added together in the same commit.

### Verification

- All 58 tests pass in `tests/unit/test_task_types.py`
- 100% coverage on `guardkit/models/task_types.py` (29 statements, 10 branches)
- Profiles verified at lines 201-216 in `task_types.py`

### Test Coverage for TESTING and REFACTOR Profiles

Tests that verify the profiles:
- `test_create_testing_profile` - Creates TESTING profile instance
- `test_create_refactor_profile` - Creates REFACTOR profile instance
- `test_for_type_returns_testing_profile` - Verifies `QualityGateProfile.for_type()`
- `test_for_type_returns_refactor_profile` - Verifies `QualityGateProfile.for_type()`
- `test_default_profiles_testing_configuration` - Verifies `DEFAULT_PROFILES` registry
- `test_default_profiles_refactor_configuration` - Verifies `DEFAULT_PROFILES` registry
- `test_get_profile_with_testing` - Verifies `get_profile()` function
- `test_get_profile_with_refactor` - Verifies `get_profile()` function
- `test_workflow_testing_task` - Integration test for TESTING workflow
- `test_workflow_refactor_task` - Integration test for REFACTOR workflow
