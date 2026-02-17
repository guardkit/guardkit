---
id: TASK-BOOT-F9C4
title: Promote known service-client library ModuleNotFoundErrors to high confidence
status: completed
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T12:00:00Z
completed: 2026-02-17T12:00:00Z
priority: medium
tags: [autobuild, coach-validator, classification, infrastructure]
task_type: feature
complexity: 2
parent_review: TASK-REV-4D57
feature_id: FEAT-BOOT
wave: 3
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  tests_run: 27
  tests_passed: 27
  last_run: 2026-02-17T12:00:00Z
completed_location: tasks/completed/TASK-BOOT-F9C4/
---

# Task: Promote known service-client library ModuleNotFoundErrors to high confidence

## Description

When `_classify_test_failure()` matches `ModuleNotFoundError` (ambiguous), check if the missing module is a known database/service client library. If so, promote to high confidence.

Currently, `ModuleNotFoundError: No module named 'sqlalchemy'` returns `("infrastructure", "ambiguous")`. It should return `("infrastructure", "high")` because sqlalchemy is a known database client library whose absence indicates a missing dependency install, not a code defect.

See: `.claude/reviews/TASK-REV-4D57-review-report.md` (Revision 3) — Finding 4 and R6.

## Naming Convention

The list is `_KNOWN_SERVICE_CLIENT_LIBS`, NOT `_INFRA_MODULES`. These are project dependencies that happen to be database/service client libraries. The distinction: `ModuleNotFoundError: No module named 'requests'` should remain ambiguous; `ModuleNotFoundError: No module named 'sqlalchemy'` should be high confidence.

## Acceptance Criteria

- [x] New class-level constant `_KNOWN_SERVICE_CLIENT_LIBS` in CoachValidator with: `psycopg2`, `asyncpg`, `pymongo`, `redis`, `psycopg`, `sqlalchemy`, `motor`, `aioredis`, `cassandra`
- [x] `_classify_test_failure()` promotes ambiguous `ModuleNotFoundError` to high confidence when the missing module matches a known service-client library
- [x] `ModuleNotFoundError: No module named 'requests'` still returns `("infrastructure", "ambiguous")`
- [x] `ModuleNotFoundError: No module named 'sqlalchemy'` returns `("infrastructure", "high")`
- [x] Unit tests for both promotion and non-promotion cases
- [x] Existing classification tests continue to pass

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_classify_test_failure()`, `_KNOWN_SERVICE_CLIENT_LIBS`
- `tests/unit/test_coach_failure_classification.py` — existing tests + new cases
