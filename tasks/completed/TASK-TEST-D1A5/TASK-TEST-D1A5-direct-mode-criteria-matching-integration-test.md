---
id: TASK-TEST-D1A5
title: Add integration test for direct mode criteria matching
status: completed
created: 2026-02-19T00:00:00Z
updated: 2026-02-19T00:00:00Z
completed: 2026-02-19T00:00:00Z
priority: medium
tags: [autobuild, direct-mode, coach-validator, testing, integration-test]
task_type: testing
complexity: 4
parent_review: TASK-REV-F248
feature_id: FEAT-DM-FIX
wave: 2
dependencies: [TASK-FIX-D1A3]
implementation_mode: task-work
completed_location: tasks/completed/TASK-TEST-D1A5/
test_results:
  status: passed
  tests_total: 4
  tests_passed: 4
  tests_failed: 0
  coverage: null
  last_run: 2026-02-19T00:00:00Z
organized_files:
  - TASK-TEST-D1A5-direct-mode-criteria-matching-integration-test.md
---

# Task: Add integration test for direct mode criteria matching

## Description

Add an integration test that exercises the full path: direct mode invocation -> synthetic report generation -> Coach validation for a scaffolding task with file-existence acceptance criteria. This path was identified as untested by Q1 in the SFT-001 diagnostic diagrams and confirmed as broken by TASK-REV-F248.

## Root Cause Reference

- TASK-REV-F248 Finding 8: Q1 from diagnostic diagrams confirmed in the wild
- Untested code path allowed TASK-ASF-006 and TASK-ACR-004 fixes to silently skip direct mode

## Implementation Plan

### Test 1: Direct mode scaffolding task with file-existence AC

```python
def test_direct_mode_scaffolding_criteria_matching():
    """Verify Coach can verify acceptance criteria from direct mode synthetic reports.

    This is the Q1 bug path from SFT-001 diagnostic diagrams.
    End-to-end: synthetic report -> _synthetic flag -> file-existence promises -> Coach approval.
    """
    # Setup: scaffolding task with file-existence acceptance criteria
    # Act: Create synthetic report via build_synthetic_report() with files matching AC
    # Assert: Coach validate_requirements() returns all_criteria_met=True
```

### Test 2: Direct mode results include _synthetic flag

```python
def test_direct_mode_results_include_synthetic_flag():
    """Verify _write_direct_mode_results sets _synthetic: True for synthetic reports."""
```

### Test 3: Coach enters file-existence path for direct mode synthetic

```python
def test_coach_uses_file_existence_for_direct_mode_synthetic():
    """Verify Coach validate_requirements() enters file-existence path
    when task_work_results has _synthetic: True with completion_promises."""
```

### Test 4: Regression -- task-work mode unaffected

```python
def test_task_work_mode_criteria_matching_unchanged():
    """Verify task-work mode (agent-written reports) still works as before."""
```

## Acceptance Criteria

- [x] Test for direct mode scaffolding criteria matching passes
- [x] Test for `_synthetic` flag in direct mode results passes
- [x] Test for Coach file-existence path activation passes
- [x] Regression test for task-work mode passes
- [x] All existing tests still pass

## Files Created

- `tests/unit/test_direct_mode_criteria_matching.py` (NEW - 4 tests)

## Completion Notes

All 4 integration tests implemented and passing. The tests exercise the full Q1 bug path:
`build_synthetic_report()` -> `_synthetic` flag propagation -> `completion_promises` -> Coach `validate_requirements()` file-existence fast-fail path.

Existing test suite (50 related tests) confirmed unaffected.
