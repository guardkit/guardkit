---
id: TASK-TT-004
title: "Add unit tests for new task types"
status: completed
created: 2026-01-23T00:00:00Z
updated: 2026-01-23T12:30:00Z
completed: 2026-01-23T12:30:00Z
priority: medium
tags: [task-types, testing, unit-tests]
task_type: testing
parent_review: TASK-REV-FB27
feature_id: FEAT-TT
implementation_mode: task-work
wave: 2
conductor_workspace: task-type-wave2-tests
complexity: 4
depends_on:
  - TASK-TT-001
  - TASK-TT-002
  - TASK-TT-003
completion_notes: |
  All acceptance criteria satisfied by existing test suite.
  Tests were implemented as part of TASK-TT-001, TASK-TT-002, TASK-TT-003.
  129 tests pass with 100% coverage on task_types.py and task_type_detector.py.
---

# Task: Add Unit Tests for New Task Types

## Description

Add comprehensive unit tests for the new `TESTING` and `REFACTOR` task types, covering:
1. Enum value creation
2. Quality gate profile retrieval
3. Task type detection keywords
4. Coach validation with new types

## Acceptance Criteria

- [x] Tests for `TaskType.TESTING` enum value
- [x] Tests for `TaskType.REFACTOR` enum value
- [x] Tests for `get_profile(TaskType.TESTING)`
- [x] Tests for `get_profile(TaskType.REFACTOR)`
- [x] Tests for `detect_task_type()` with testing keywords
- [x] Tests for `detect_task_type()` with refactor keywords
- [x] Tests for Coach `_resolve_task_type()` accepting new types
- [x] All tests pass

## Implementation Notes

### Test Files to Create/Update

1. **`tests/unit/test_task_types.py`** - Enum and profile tests
2. **`tests/unit/test_task_type_detector.py`** - Detection keyword tests
3. **`tests/unit/test_autobuild_task_type.py`** - Coach validation tests (already has some)

### Example Test Cases

```python
# test_task_types.py
def test_testing_task_type_exists():
    """TESTING enum value exists and has correct string value."""
    assert TaskType.TESTING.value == "testing"
    assert TaskType("testing") == TaskType.TESTING

def test_refactor_task_type_exists():
    """REFACTOR enum value exists and has correct string value."""
    assert TaskType.REFACTOR.value == "refactor"
    assert TaskType("refactor") == TaskType.REFACTOR

def test_testing_profile():
    """TESTING profile has appropriate quality gates."""
    profile = get_profile(TaskType.TESTING)
    assert profile.arch_review_required is False
    assert profile.coverage_required is False
    assert profile.tests_required is True
    assert profile.plan_audit_required is True

def test_refactor_profile():
    """REFACTOR profile has full quality gates."""
    profile = get_profile(TaskType.REFACTOR)
    assert profile.arch_review_required is True
    assert profile.coverage_required is True
    assert profile.tests_required is True
    assert profile.plan_audit_required is True

# test_task_type_detector.py
@pytest.mark.parametrize("title,expected", [
    ("Add unit tests for auth", TaskType.TESTING),
    ("Set up testing infrastructure", TaskType.TESTING),
    ("Create pytest fixtures", TaskType.TESTING),
    ("Refactor authentication module", TaskType.REFACTOR),
    ("Migrate to new API version", TaskType.REFACTOR),
    ("Cleanup legacy code", TaskType.REFACTOR),
])
def test_detect_new_task_types(title, expected):
    """detect_task_type correctly identifies TESTING and REFACTOR."""
    assert detect_task_type(title) == expected
```

## Dependencies

- TASK-TT-001, TASK-TT-002, TASK-TT-003 must complete first

## Notes

This task uses `task_type: testing` to verify the fix works (meta-validation).
