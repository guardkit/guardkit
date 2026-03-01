---
id: TASK-FIX-3A01
title: Include test command and error detail in Coach feedback to Player
task_type: feature
parent_review: TASK-REV-0E44
feature_id: FEAT-CTD
status: backlog
created: 2026-03-01T00:00:00+00:00
updated: 2026-03-01T00:00:00+00:00
priority: medium
tags:
  - autobuild
  - coach-validator
  - feedback
  - developer-experience
complexity: 2
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Include Test Command and Error Detail in Coach Feedback to Player

## Description

When the Coach's independent test verification fails with infrastructure or collection errors, the feedback sent to the Player is generic: "Tests failed due to infrastructure/environment issues (not code defects)." The Player cannot see which test command was run, which files failed, or what the actual error was, making it impossible to take targeted corrective action.

This is a developer experience improvement from the TASK-REV-0E44 review. Including the actual test command and error output in feedback gives the Player actionable information.

## Acceptance Criteria

- [ ] Feedback for infrastructure/collection_error failures includes the test command that was run
- [ ] Feedback includes the error detail from `test_result.test_output_summary`
- [ ] Error detail is formatted with a clear label (e.g., `Error detail:`)
- [ ] When `test_output_summary` is empty/None, feedback works without error detail (backward compatible)
- [ ] Feedback text does not exceed reasonable length (truncate output if > 500 chars)
- [ ] Unit tests cover: feedback with error detail, feedback without error detail, truncation

## Technical Context

- File: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Method: `validate()` feedback construction (lines 717-729)
- The `test_result` object (IndependentTestResult) has `test_command` and `test_output_summary` fields
- Feedback flows via `_feedback_result()` → `_extract_feedback()` → Player prompt

## Design Reference

- Review report: `.claude/reviews/TASK-REV-0E44-review-report.md` (Fix 4)

## Regression Risks

Minimal. Only changes feedback text content, no logic changes. Verify feedback string is valid and doesn't break downstream consumers.

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
