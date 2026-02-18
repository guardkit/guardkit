---
id: TASK-FIX-4415
title: Add specific Coach feedback for psycopg2 import error in asyncpg projects
status: completed
task_type: implementation
created: 2026-02-18T16:00:00Z
updated: 2026-02-18T17:30:00Z
completed: 2026-02-18T17:30:00Z
priority: low
tags: [autobuild, coach-validator, feedback-quality, psycopg2]
complexity: 3
parent_review: TASK-REV-7EB05
feature_id: FEAT-REV7EB05-fixes
wave: 2
implementation_mode: task-work
related_tasks:
  - TASK-REV-7EB05
  - TASK-FIX-A7F1
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-18T17:00:00Z
completed_location: tasks/completed/TASK-FIX-4415/
---

# Task: Add specific Coach feedback for psycopg2 import error in asyncpg projects

## Description

Even after TASK-FIX-A7F1 fixes the classification (psycopg2 → ambiguous instead of high), the Coach's feedback message should be specific and actionable when `psycopg2` appears in a project that uses `asyncpg`.

Currently, a generic "infrastructure/environment issues" feedback message misdirects the Player. The feedback should say: "Your code imports `psycopg2` — this is an asyncpg project. Remove psycopg2 imports and use asyncpg-compatible patterns."

**Source**: Recommendation R4 from TASK-REV-7EB05 review report.
**Depends on**: TASK-FIX-A7F1 (psycopg2 classification fix).

## Acceptance Criteria

- [x] When test output contains `ModuleNotFoundError: No module named 'psycopg2'` AND the project's bootstrap includes `asyncpg` (detectable from task's `requires_infrastructure` or bootstrap package list), Coach feedback includes a specific message directing the Player to remove `psycopg2` imports
- [x] Specific feedback message: something like "ModuleNotFoundError for 'psycopg2' — this project uses asyncpg. Remove `import psycopg2` from your code and use asyncpg-compatible database patterns instead."
- [x] Feedback remains actionable and does not suggest mock fixtures or SQLite as solutions
- [x] When `psycopg2` missing in a project that genuinely needs it (not asyncpg), feedback does NOT include the asyncpg-specific message
- [x] Existing tests pass
- [x] New test covers: asyncpg project + psycopg2 error → specific feedback message

## Implementation Notes

**Location**: Coach feedback generation, after `_classify_test_failure` in the test failure handling path.

The simplest approach: add a pattern-match check in the feedback generation. When test output contains `no module named 'psycopg2'`, check whether `asyncpg` or `sqlalchemy[asyncio]` is in the bootstrap packages (passed via task dict). If yes, append the specific message to the Coach's feedback string.

No classification change needed (that's TASK-FIX-A7F1's job). This is purely a feedback message improvement.

The task requires determining where Coach feedback strings are assembled for the test failure case — trace from `_feedback_from_tests()` or equivalent in `coach_validator.py`.

## Implementation Summary

### Changes Made

**`guardkit/orchestrator/quality_gates/coach_validator.py`**
- Added `_is_psycopg2_asyncpg_mismatch(test_output, task)` helper method that detects when psycopg2 is the missing module and asyncpg/sqlalchemy[asyncio] is in the project's bootstrap
- Modified feedback generation block to check for psycopg2/asyncpg mismatch before falling back to generic infrastructure message

**`tests/unit/test_coach_failure_classification.py`**
- Added `TestIsPsycopg2AsyncpgMismatch` class (7 unit tests for the helper)
- Added `test_psycopg2_error_in_asyncpg_project_gives_specific_feedback` (integration test for AC1-AC3)
- Added `test_psycopg2_error_without_asyncpg_project_uses_generic_feedback` (AC4)
- Fixed pre-existing test failure `test_mixed_high_and_ambiguous_returns_high` (used psycopg2 which TASK-FIX-A7F1 removed from `_KNOWN_SERVICE_CLIENT_LIBS`)

### Test Results
- 36/36 tests pass in `test_coach_failure_classification.py`
- 205/205 tests pass in `test_coach_validator.py`
