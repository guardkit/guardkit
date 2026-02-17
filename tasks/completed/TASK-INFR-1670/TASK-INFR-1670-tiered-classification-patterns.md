---
id: TASK-INFR-1670
title: Split infrastructure classification into tiered patterns with precedence rule
status: completed
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
completed: 2026-02-17T00:00:00Z
completed_location: tasks/completed/TASK-INFR-1670/
priority: high
tags: [autobuild, coach-validator, classification, infrastructure]
task_type: feature
complexity: 3
parent_review: TASK-REV-BA4B
feature_id: FEAT-INFRA
wave: 1
implementation_mode: task-work
dependencies: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-17
  tests_total: 17
  tests_passed: 17
  tests_failed: 0
organized_files:
  - TASK-INFR-1670-tiered-classification-patterns.md
---

# Task: Split infrastructure classification into tiered patterns with precedence rule

## Description

The current `_classify_test_failure` method uses a flat list of patterns (`_INFRA_FAILURE_PATTERNS`) that includes both high-confidence infrastructure indicators (ConnectionRefusedError) and ambiguous ones (ImportError). This creates a ~30% false-positive surface area where code bugs could be misclassified as infrastructure failures.

Split the patterns into two tiers and update the classification method to return both the classification and confidence level. Define a clear precedence rule for when both tiers match.

## Acceptance Criteria

- [x] `_INFRA_FAILURE_PATTERNS` split into `_INFRA_HIGH_CONFIDENCE` and `_INFRA_AMBIGUOUS` class attributes
- [x] `_classify_test_failure()` returns a tuple `(classification: str, confidence: str)` instead of just `str`
- [x] Precedence rule: high-confidence wins if ANY high-confidence pattern matches, regardless of ambiguous patterns
- [x] Return values: `("infrastructure", "high")`, `("infrastructure", "ambiguous")`, or `("code", "n/a")`
- [x] All callers of `_classify_test_failure` updated for the new return type
- [x] Feedback text still uses "infrastructure" classification for both tiers (user-facing message unchanged)
- [x] Only "high" confidence is eligible for conditional approval (used by TASK-INFR-24DB)
- [x] Existing test_coach_failure_classification.py tests updated for new return type
- [x] New tests for mixed-tier edge cases:
  - ConnectionRefusedError + ModuleNotFoundError: psycopg2 → ("infrastructure", "high")
  - ImportError only → ("infrastructure", "ambiguous")
  - AssertionError only → ("code", "n/a")

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` - Classification method, pattern lists, caller
- `tests/unit/test_coach_failure_classification.py` - Updated and new tests

## Implementation Summary

### Changes Made

**coach_validator.py:**
- Replaced `_INFRA_FAILURE_PATTERNS` flat list with `_INFRA_HIGH_CONFIDENCE` (12 patterns) and `_INFRA_AMBIGUOUS` (3 patterns)
- Updated `_classify_test_failure()` return type from `str` to `Tuple[str, str]`
- Implemented precedence rule: high-confidence checked first, wins regardless of ambiguous matches
- Updated caller at line 579 to unpack tuple: `failure_class, failure_confidence = ...`
- Added `failure_confidence` field to issues dict for downstream use

**test_coach_failure_classification.py:**
- Updated 10 existing tests for tuple return type
- Added 3 new edge-case tests (mixed tiers, ambiguous-only, code-only)
- Added `failure_confidence` assertion to feedback path integration test
- Total: 17 tests, all passing
