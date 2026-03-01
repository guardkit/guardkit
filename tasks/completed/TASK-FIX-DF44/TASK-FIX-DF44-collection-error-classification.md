---
id: TASK-FIX-DF44
title: Add collection_error classification to Coach test failure classifier
task_type: feature
parent_review: TASK-REV-0E44
feature_id: FEAT-CTD
status: completed
created: 2026-03-01T00:00:00+00:00
updated: 2026-03-01T00:00:00+00:00
completed: 2026-03-01T00:00:00+00:00
priority: high
tags:
  - autobuild
  - coach-validator
  - classification
  - seam-fix
complexity: 4
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Add collection_error Classification to Coach Test Failure Classifier

## Description

The Coach's `_classify_test_failure()` method has no category for pytest collection errors — cases where pytest cannot even import a test file (exit code 2). Currently, a `ModuleNotFoundError` during collection falls through to `("infrastructure", "ambiguous")` because the missing module name (e.g., `"tests"`) doesn't match `_KNOWN_SERVICE_CLIENT_LIBS`.

This is Seam Failure 2 from the TASK-REV-0E44 review. Adding a specific `"collection_error"` classification enables downstream approval logic to handle this case correctly.

## Acceptance Criteria

- [x] New classification `("collection_error", "high")` returned when pytest output contains `"errors during collection"` or `"error collecting"`
- [x] Collection error detection runs BEFORE the generic `ModuleNotFoundError` check
- [x] Classification is logged at DEBUG level with the matched pattern
- [x] Normal test execution failures (assertions, exceptions) are NOT classified as collection errors
- [x] Mixed output (some collection errors + some test results) is correctly classified as collection error
- [x] Unit tests cover: collection error output, normal failure output, mixed output, empty output

## Technical Context

- File: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Method: `_classify_test_failure()` (lines 2631-2719)
- Insert BEFORE the `ModuleNotFoundError` check (line ~2651)
- Existing classifications: `infrastructure` (high/ambiguous), `code` (high/n/a), `sdk_api_error` (high)
- New classification: `collection_error` (high)
- pytest exit code 2 = collection error (vs exit code 1 = test failure)

## Design Reference

- Review report: `.claude/reviews/TASK-REV-0E44-review-report.md` (Seam Failure 2, Fix 2)
- Evidence: `coach_turn_1.json` line 16 — `"Interrupted: 2 errors during collection"`

## Regression Risks

1. New `"collection_error"` class must be handled by all consumers → verify `validate()` handles it (Fix 3 adds explicit handling)
2. False positive on legitimate collection errors (syntax errors in test files) → these ARE collection errors and should be classified as such
3. Detection patterns must not match normal failure output → test with various pytest outputs

## Implementation Notes

Added `collection_error` classification to `_classify_test_failure()` in `coach_validator.py`.
Detection patterns `"errors during collection"` and `"error collecting"` checked before the
`ModuleNotFoundError` branch. Returns `("collection_error", "high")` with DEBUG logging.

6 new unit tests added to `tests/unit/test_coach_failure_classification.py`.
All 42 tests pass.

## Test Execution Log

- Tests run: 42
- Passed: 42
- Failed: 0
- New tests added: 6
