---
id: TASK-AQG-002
title: Make zero-test anomaly configurable as blocking for feature-type tasks
status: completed
created: 2026-02-10T20:30:00Z
updated: 2026-02-10T21:00:00Z
completed: 2026-02-10T21:00:00Z
priority: medium
task_type: feature
tags: [autobuild, coach, quality-gates, zero-test, test-detection]
parent_review: TASK-REV-7972
feature_id: FEAT-AQG
complexity: 4
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Make Zero-Test Anomaly Configurable as Blocking

## Description

The zero-test anomaly detection (`_check_zero_test_anomaly()` at coach_validator.py:1246-1291) currently returns a WARNING but never blocks approval. In FEAT-FP-002, all 11 tasks reported `0 tests` — 7 were feature-type tasks where tests ARE required. Only 1 of the 7 triggered the anomaly warning, and it was still approved.

The anomaly should be configurable: for feature-type tasks where `tests_required=True`, a zero-test result should optionally block approval (controlled by quality gate profile configuration).

## Root Cause

1. `_check_zero_test_anomaly()` only returns warnings, never errors
2. The anomaly fires inconsistently — only when `all_passed=true AND tests_passed=0 AND coverage=null` (all three conditions). If the Player reports non-null coverage or non-zero tests_passed in its JSON but the orchestrator extracts 0, the anomaly won't fire.
3. No quality gate profile flag to control whether zero-test is blocking vs warning

## Implementation Plan

1. **`guardkit/orchestrator/quality_gates/coach_validator.py`**:
   - Add `zero_test_blocking` field to quality gate profiles (default: `false` for backward compatibility)
   - When `zero_test_blocking=true` and `tests_required=true`, make `_check_zero_test_anomaly()` return an error instead of a warning
   - An error from this check should prevent approval

2. **Quality gate profile updates**:
   - `feature` profile: set `zero_test_blocking: true`
   - `documentation` profile: keep `zero_test_blocking: false`
   - `testing` profile: keep `zero_test_blocking: false`

3. **Independent test verification improvement**:
   - When `No task-specific tests found`, log the glob patterns that were tried
   - This helps diagnose whether the issue is test naming vs no tests

## Acceptance Criteria

- [x] AC1: Quality gate profiles have `zero_test_blocking` configuration field
- [x] AC2: Feature-type tasks with zero tests detected get a blocking error (not just warning)
- [x] AC3: Documentation/testing-type tasks are unaffected (zero tests still allowed)
- [x] AC4: Backward compatible — default `zero_test_blocking: false` preserves current behavior
- [x] AC5: Unit tests cover: blocking enabled + zero tests, blocking disabled + zero tests, non-zero tests

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` (anomaly check + profiles)
- `tests/unit/test_coach_validator.py` (new tests)
