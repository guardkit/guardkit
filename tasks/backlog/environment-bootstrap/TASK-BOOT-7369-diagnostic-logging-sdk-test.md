---
id: TASK-BOOT-7369
title: Add diagnostic logging for SDK test environment
status: backlog
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
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
  status: pending
  coverage: null
  last_run: null
---

# Task: Add diagnostic logging for SDK test environment

## Description

Add DEBUG-level logging in CoachValidator to capture the raw test output and classification decision for post-mortem debugging. This enables auditing why a particular test failure was classified as it was.

See: `.claude/reviews/TASK-REV-4D57-review-report.md` (Revision 3) — R7.

## Acceptance Criteria

- [ ] `_run_tests_via_sdk()` logs raw test output at DEBUG level (first 2000 chars)
- [ ] `_classify_test_failure()` logs the classification decision and which pattern matched
- [ ] Log messages include task_id for correlation
- [ ] No change to INFO-level logging verbosity
- [ ] Existing tests continue to pass

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_run_tests_via_sdk()`, `_classify_test_failure()`
