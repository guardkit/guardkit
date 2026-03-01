---
id: TASK-FIX-DF44
title: Add collection_error classification to Coach test failure classifier
task_type: feature
parent_review: TASK-REV-0E44
feature_id: FEAT-CTD
status: backlog
created: 2026-03-01T00:00:00+00:00
updated: 2026-03-01T00:00:00+00:00
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

- [ ] New classification `("collection_error", "high")` returned when pytest output contains `"errors during collection"` or `"error collecting"`
- [ ] Collection error detection runs BEFORE the generic `ModuleNotFoundError` check
- [ ] Classification is logged at DEBUG level with the matched pattern
- [ ] Normal test execution failures (assertions, exceptions) are NOT classified as collection errors
- [ ] Mixed output (some collection errors + some test results) is correctly classified as collection error
- [ ] Unit tests cover: collection error output, normal failure output, mixed output, empty output

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

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
