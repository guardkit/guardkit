---
id: TASK-BOOT-7369
title: Add diagnostic logging for SDK test environment
status: completed
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
completed: 2026-02-17T00:00:00Z
priority: medium
tags: [autobuild, coach-validator, observability, logging]
task_type: feature
complexity: 1
parent_review: TASK-REV-4D57
feature_id: FEAT-BOOT
wave: 3
implementation_mode: direct
dependencies: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-17
completed_location: tasks/completed/TASK-BOOT-7369/
organized_files:
  - TASK-BOOT-7369.md
---

# Task: Add diagnostic logging for SDK test environment

## Description

Add DEBUG-level logging in CoachValidator to capture the raw test output and classification decision for post-mortem debugging. This enables auditing why a particular test failure was classified as it was.

See: `.claude/reviews/TASK-REV-4D57-review-report.md` (Revision 3) — R7.

## Acceptance Criteria

- [x] `_run_tests_via_sdk()` logs raw test output at DEBUG level (first 2000 chars)
- [x] `_classify_test_failure()` logs the classification decision and which pattern matched
- [x] Log messages include task_id for correlation
- [x] No change to INFO-level logging verbosity
- [x] Existing tests continue to pass

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_run_tests_via_sdk()`, `_classify_test_failure()`

## Implementation

Added 3 `logger.debug(...)` calls in `_run_tests_via_sdk()` (one per branch: `bash_is_error is True`, `bash_is_error is False`, `else`), each logging the first 2000 chars of raw output tagged with `self.task_id`.

Added `logger.debug(...)` calls in `_classify_test_failure()` at each return point, logging the classification decision and (where applicable) the matched pattern — all tagged with `self.task_id`.

## Test Results

- 228 unit tests passed (0 failures, 0 errors)
- Compilation: OK
