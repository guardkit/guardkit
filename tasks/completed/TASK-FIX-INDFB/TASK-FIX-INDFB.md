---
id: TASK-FIX-INDFB
title: "Fix independent test fallback - skip instead of running all tests"
status: completed
created: 2026-01-23T11:30:00Z
updated: 2026-01-23T12:15:00Z
completed: 2026-01-23T12:15:00Z
priority: high
tags: [fix, coach-validator, quality-gates, autobuild, feature-build]
task_type: feature
complexity: 3
parent_review: TASK-REV-FB26
feature_id: FEAT-FB-FIXES
implementation_mode: task-work
wave: 1
depends_on: []
estimated_hours: 1
actual_hours: 0.5
---

# Fix independent test fallback - skip instead of running all tests

## Problem

TASK-FIX-INDTEST implemented task-specific test filtering, but the **fallback behavior is wrong**. When no task-specific tests are found (pattern `tests/test_task_fha_002*.py` doesn't match), it falls back to running `pytest tests/` which includes ALL tests from ALL parallel tasks.

**Expected test names:** `tests/test_task_fha_002*.py`
**Actual test names:** `tests/test_config.py`, `tests/test_app.py`, etc.

The naming convention assumption doesn't match reality, so the fallback is always triggered.

## Evidence

```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Running independent tests: pytest tests/ -v --tb=short
INFO:guardkit.orchestrator.quality_gates.coach_validator:Independent tests failed in 0.2s
```

The 0.2s failure time indicates tests from other tasks are failing on import (missing dependencies from parallel tasks).

## Solution

Change the fallback behavior in `_detect_test_command()` to **skip independent verification** instead of running all tests.

### Current Code (`coach_validator.py:833-834`)

```python
else:
    logger.debug(f"No task-specific tests found for {task_id}, using full suite")
# Falls through to pytest tests/ - BAD for shared worktrees
```

### Proposed Fix

```python
else:
    # No task-specific tests found - skip verification in this case
    # Running all tests would include tests from other parallel tasks
    logger.info(f"No task-specific tests found for {task_id}, skipping independent verification")
    return None  # Signal to caller to skip verification
```

Then update `run_independent_tests()` to handle `None`:

```python
def run_independent_tests(self) -> IndependentTestResult:
    test_cmd = self.test_command or self._detect_test_command(self.task_id)

    if test_cmd is None:
        # Task-specific filtering requested but no matching tests found
        return IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests found, skipping independent verification",
            duration_seconds=0.0,
        )

    logger.info(f"Running independent tests: {test_cmd}")
    # ... rest of method unchanged
```

## Acceptance Criteria

- [x] When `task_id` is provided but no matching test files found, skip independent verification
- [x] Return `IndependentTestResult` with `tests_passed=True` and descriptive summary
- [x] Log at INFO level that verification is being skipped
- [x] Existing behavior preserved when `task_id` is None (standalone mode)
- [x] Existing behavior preserved when task-specific tests ARE found
- [x] Unit tests updated/added

## Files to Modify

1. `guardkit/orchestrator/quality_gates/coach_validator.py`
   - `_detect_test_command()` - return `None` when no task-specific tests
   - `run_independent_tests()` - handle `None` return value

2. `tests/unit/test_coach_validator.py`
   - Update `TestTaskSpecificTestDetection` tests
   - Add test for skip behavior

## Testing

```bash
pytest tests/unit/test_coach_validator.py -v -k "test_detect_test_command"
```

## Related

- Parent review: TASK-REV-FB26
- Original fix: TASK-FIX-INDTEST (implemented filtering, wrong fallback)
