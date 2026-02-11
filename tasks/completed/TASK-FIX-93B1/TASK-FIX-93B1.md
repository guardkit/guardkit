---
id: TASK-FIX-93B1
title: "Fix non-recursive test glob pattern in Coach independent test detection"
status: completed
updated: 2026-02-11T23:10:00Z
completed: 2026-02-11T23:10:00Z
completed_location: tasks/completed/TASK-FIX-93B1/
created: 2026-02-11T22:00:00Z
priority: high
tags: [autobuild, quality-gates, zero-test-anomaly, coach-validator, bug-fix]
task_type: feature
complexity: 3
parent_review: TASK-REV-93E1
fix_id: FIX-93E1-B
---

# Task: Fix Non-Recursive Test Glob Pattern (FIX-93E1-B, P0)

## Description

The Coach's fallback test glob pattern at `coach_validator.py:1354` uses a flat pattern `tests/test_{prefix}*.py` that does not recurse into subdirectories. This causes the Coach to miss task-specific tests located in nested directories like `tests/health/`, `tests/api/`, `tests/unit/`, etc.

This is the **P0 fix** from TASK-REV-93E1. It directly prevents the `test_command="skipped"` condition that triggers the zero-test anomaly on revert turns, and works on disk state (not Player self-reports), making it the most reliable fix.

## Root Cause

`_detect_test_command()` (coach_validator.py:1307-1396) has two detection strategies:
1. **Primary**: `_detect_tests_from_results()` — extracts test files from `files_created`/`files_modified` in task_work_results
2. **Fallback**: Glob pattern `tests/test_{prefix}*.py` on disk

The fallback glob only searches the flat `tests/` directory. When tests are in nested directories (e.g., `tests/health/test_task_db_006_database_health.py`), the glob misses them and returns None, causing `run_independent_tests()` to return `test_command="skipped"`.

## Change Required

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Location**: Line 1354

```python
# Before:
pattern = f"tests/test_{task_prefix}*.py"

# After:
pattern = f"tests/**/test_{task_prefix}*.py"
```

Python's `Path.glob("**/...")` matches zero or more subdirectories. On Python 3.14 (current), symlink loop safety is built-in. Performance overhead is negligible (~10-50ms for 1000+ test files).

## Acceptance Criteria

- [x] AC-001: The glob pattern at `_detect_test_command()` line 1354 uses `tests/**/test_{task_prefix}*.py` (recursive)
- [x] AC-002: Test files in nested directories (e.g., `tests/health/test_task_db_006*.py`) are correctly found by the fallback glob
- [x] AC-003: Test files in the flat `tests/` directory (e.g., `tests/test_task_foo*.py`) are still correctly found (zero subdirs match for `**`)
- [x] AC-004: Existing tests in `TestTaskSpecificTestDetection` pass without modification (13/13)
- [x] AC-005: New tests verify recursive glob behavior for nested test directories (6 new tests)
- [x] AC-006: No regressions in existing zero-test anomaly tests (38/38 passing)

## Regression Constraints (Must Not Regress)

| Prior Fix | Risk | Notes |
|-----------|------|-------|
| TASK-FIX-CEE8b | LOW | Recursive glob means `test_command != "skipped"` more often → CEE8b early return fires correctly |
| TASK-FIX-ACA7a | LOW | `test_command` won't be "skipped" when nested tests exist → ACA7a condition fails correctly |
| All others | NONE | Glob pattern is isolated in `_detect_test_command()` fallback |

## Test Plan

1. Existing `TestDetectTestCommand` tests must pass unchanged
2. New tests:
   - Test that `tests/health/test_task_foo_001*.py` is found by recursive glob
   - Test that `tests/api/test_task_foo_001*.py` is found by recursive glob
   - Test that `tests/test_task_foo_001*.py` (flat) is still found
   - Test that no matches returns None (existing behavior preserved)
3. Run full zero-test anomaly test suites to verify no regressions

## Key Files

| File | Role |
|------|------|
| `guardkit/orchestrator/quality_gates/coach_validator.py:1354` | The glob pattern to fix |
| `tests/unit/test_coach_validator.py` | Test file for Coach validator |

## Reference

- Review report: `.claude/reviews/TASK-REV-93E1-review-report.md` (AC-003, AC-007, AC-009)
- Parent review: TASK-REV-93E1
