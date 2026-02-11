---
id: TASK-FIX-ACA7a
title: Fix zero-test anomaly bypass via project-wide test pass
status: completed
created: 2026-02-11T00:00:00Z
updated: 2026-02-11T12:00:00Z
completed: 2026-02-11T12:05:00Z
completed_location: tasks/completed/TASK-FIX-ACA7a/
priority: high
tags: [bugfix, quality-gates, zero-test-anomaly, autobuild]
task_type: bugfix
complexity: 4
parent_review: TASK-REV-ACA7
---

# Task: Fix Zero-Test Anomaly Bypass via Project-Wide Test Pass

## Description

BUG-1 from TASK-REV-ACA7: Feature tasks can be approved with zero task-specific tests despite `zero_test_blocking=True` when the project's existing test suite passes.

### Root Cause

When a feature task goes through the task-work delegation path, the stream parser captures "Quality gates: PASSED" from the Player's output (because the existing project test suite passes). This writes `all_passed=True` and non-zero `tests_passed` count to `task_work_results.json`. The zero-test anomaly check at `coach_validator.py:1403` sees `tests_passed_count > 0` (from existing tests) and doesn't trigger, even though the specific task contributed zero new tests.

The defense-in-depth check (CEE8b) correctly identifies the independent test verification as "skipped" (no task-specific tests found via glob), but falls through to the existing anomaly check which doesn't trigger because of project-wide numbers.

### Reproduction

TASK-DOC-004 in FEAT-CEE8 Run 3 (`docs/reviews/fastapi_test/api_docs_3.md`):
- Task type: feature, profile: `zero_test_blocking=True`
- Player: "0 tests (failing)" — zero task-specific tests
- Coach: `tests=True, ALL_PASSED=True` — project test suite (218 tests) passes
- Independent verification: "No task-specific tests found" with glob `tests/test_task_doc_004*.py`
- Result: Approved despite contributing zero test coverage

### Affected Code

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_check_zero_test_anomaly()` (lines 1354-1419)

## Acceptance Criteria

- [x] AC-001: `_check_zero_test_anomaly()` detects when `tests_written` is empty AND independent verification returned `test_command="skipped"`
- [x] AC-002: Blocking error returned for profiles with `zero_test_blocking=True` in the above case
- [x] AC-003: Warning returned for profiles with `zero_test_blocking=False` in the above case
- [x] AC-004: No false positives for tasks that DO create tests (e.g., TASK-DOC-002 with 1 test)
- [x] AC-005: No false positives for tasks with `tests_required=False` (scaffolding, testing profiles)
- [x] AC-006: Existing zero-test anomaly tests still pass (no regressions)

## Implementation Notes

### Proposed Fix

Add a second check in `_check_zero_test_anomaly()` after the existing `all_passed` check (line 1396):

```python
# After the independent_tests early return (line 1396):
tests_written = task_work_results.get("tests_written", [])
if (
    len(tests_written) == 0
    and independent_tests
    and independent_tests.test_command == "skipped"
):
    severity = "error" if profile.zero_test_blocking else "warning"
    return [{
        "severity": severity,
        "category": "zero_test_anomaly",
        "description": (
            "No task-specific tests created and no task-specific tests found "
            "via independent verification. Project-wide test suite may pass "
            "but this task contributes zero test coverage."
        ),
    }]
```

### Test File

`tests/unit/test_coach_validator_zero_test.py` (extend existing tests in `TestZeroTestBlockingConfiguration`)
