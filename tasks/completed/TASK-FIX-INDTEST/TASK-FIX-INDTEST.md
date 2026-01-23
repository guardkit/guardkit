---
id: TASK-FIX-INDTEST
title: "Fix independent test verification for shared worktrees"
status: completed
created: 2026-01-24T00:35:00Z
updated: 2026-01-23T17:00:00Z
completed: 2026-01-23T17:00:00Z
priority: high
tags: [fix, coach-validator, quality-gates, testing, parallel, autobuild]
task_type: feature
complexity: 4
parent_review: TASK-REV-FB25
feature_id: FEAT-FB-FIXES
implementation_mode: task-work
wave: 1
depends_on: []
estimated_hours: 2-4
actual_hours: 1.5
previous_state: in_review
state_transition_reason: "All quality gates passed, implementation verified"
completed_location: tasks/completed/TASK-FIX-INDTEST/
---

# Fix independent test verification for shared worktrees

## Problem

When running parallel tasks in a shared worktree (feature-build), the Coach's independent test verification runs `pytest tests/` which discovers ALL tests from ALL tasks, not just the specific task being validated.

### Evidence from logs:
```
Quality gate evaluation complete: tests=True (required=True), coverage=True (required=True), ALL_PASSED=True
Running independent tests: pytest tests/ -v --tb=short
Independent tests failed in 0.3s
WARNING: Independent test verification failed for TASK-FHA-002
```

### Failure pattern:
- task-work reports `tests=True` (task-specific tests passed)
- Coach runs `pytest tests/` (discovers ALL tests)
- 0.3s failure time suggests immediate import/discovery error
- Tests from other parallel tasks have unmet dependencies

## Root Cause

In `guardkit/orchestrator/quality_gates/coach_validator.py`, the `_detect_test_command()` method always returns `pytest tests/` without task-specific filtering:

```python
def _detect_test_command(self) -> str:
    # Check for Python projects
    if (self.worktree_path / "pytest.ini").exists():
        return "pytest tests/ -v --tb=short"
    if (self.worktree_path / "pyproject.toml").exists():
        return "pytest tests/ -v --tb=short"
    ...
    return "pytest tests/ -v --tb=short"  # Default
```

## Solution Options

### Option A: Task-specific test filtering (Recommended)

Add task_id parameter to `_detect_test_command()` and filter tests:

```python
def _detect_test_command(self, task_id: Optional[str] = None) -> str:
    """Auto-detect test command, optionally scoped to a specific task."""

    # For parallel/shared worktrees, try task-specific patterns first
    if task_id:
        # Convert TASK-FHA-002 -> task_fha_002 for pattern matching
        task_prefix = task_id.replace("-", "_").lower()
        task_test_patterns = [
            f"tests/test_{task_prefix}*.py",
            f"tests/**/test_{task_prefix}*.py",
            f"tests/{task_prefix}/**/*.py",
        ]
        for pattern in task_test_patterns:
            matching_files = list(self.worktree_path.glob(pattern))
            if matching_files:
                # Use specific files instead of directory
                files_str = " ".join(str(f.relative_to(self.worktree_path)) for f in matching_files)
                return f"pytest {files_str} -v --tb=short"

    # Fallback to default behavior
    return self._detect_default_test_command()
```

### Option B: Skip independent verification for parallel mode

Trust task-work results when running in parallel/shared worktree:

```python
def _run_independent_tests(self) -> Tuple[bool, str]:
    """Run independent test verification."""

    # Skip for parallel execution (shared worktree)
    if self._is_shared_worktree():
        logger.info("Skipping independent tests for shared worktree (trust task-work)")
        return True, "Skipped for parallel execution"

    # Normal verification
    return self._execute_tests()
```

### Option C: pytest mark-based filtering

Use pytest markers to tag task-specific tests:

```python
# In test files:
@pytest.mark.task_fha_002
def test_something():
    ...

# In coach_validator:
return f"pytest tests/ -m {task_marker} -v --tb=short"
```

## Recommendation

**Option A** is recommended because:
1. Maintains independent verification (trust but verify)
2. Works with existing test file naming conventions
3. No changes required to test files
4. Minimal invasiveness

## Acceptance Criteria

- [x] Independent test verification only runs task-specific tests in shared worktrees
- [x] Single-task worktrees continue to run `pytest tests/` (existing behavior)
- [x] Test command detection logs which tests will be run
- [x] Tests from other parallel tasks are not discovered
- [x] Unit tests added for task-specific filtering

## Implementation Notes

### Files to modify:
1. `guardkit/orchestrator/quality_gates/coach_validator.py`
   - `_detect_test_command()` method
   - `_run_independent_tests()` method (pass task_id)

### Test file:
`tests/unit/test_coach_validator.py`

### Key changes:
1. Add `task_id` parameter to `CoachValidator.__init__()`
2. Pass `task_id` to `_detect_test_command()`
3. Implement task-specific test file pattern matching
4. Add fallback to full test suite if no task-specific tests found

## Testing

```bash
# Run existing tests
pytest tests/unit/test_coach_validator.py -v

# Add test cases:
# test_detect_test_command_with_task_id()
# test_detect_test_command_falls_back_to_full_suite()
# test_independent_tests_task_specific()
```

## Related

- Parent review: TASK-REV-FB25
- Related fix: TASK-FIX-COVNULL (coverage None handling)
- Previous fixes: TASK-FIX-ARIMPL (arch review skip - WORKING)

---

## Implementation Summary

**Completed**: 2026-01-23

### Changes Made

1. **`guardkit/orchestrator/quality_gates/coach_validator.py`**:
   - Added `task_id: Optional[str] = None` parameter to `__init__()`
   - Added `_task_id_to_pattern_prefix()` helper method for ID conversion
   - Modified `_detect_test_command()` to accept optional `task_id` parameter
   - Implemented task-specific test file pattern matching: `tests/test_{task_prefix}*.py`
   - Updated `run_independent_tests()` to pass `self.task_id` to `_detect_test_command()`
   - Preserves fallback to full test suite when no task-specific tests found

2. **`guardkit/orchestrator/autobuild.py`** (line 1630):
   - Updated `CoachValidator` instantiation to pass `task_id` parameter

3. **`tests/unit/test_coach_validator.py`**:
   - Added `TestTaskSpecificTestDetection` class with 10 comprehensive tests

### Test Results

```
pytest tests/unit/test_coach_validator.py -v
======================== 92 passed, 1 warning in 1.72s =========================
```

### Code Review Score

**85/100** (PASS)
- Correctness: 25/25
- Maintainability: 22/25
- Test Coverage: 23/25
- Architecture: 15/25

### Plan Audit

0 violations - implementation matches planned changes exactly.
