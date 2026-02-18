---
id: TASK-FIX-4415
title: Add specific Coach feedback for psycopg2 import error in asyncpg projects
status: backlog
task_type: implementation
created: 2026-02-18T16:00:00Z
updated: 2026-02-18T16:00:00Z
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
  status: pending
  coverage: null
  last_run: null
---

# Task: Add specific Coach feedback for psycopg2 import error in asyncpg projects

## Description

Even after TASK-FIX-A7F1 fixes the classification (psycopg2 → ambiguous instead of high), the Coach's feedback message should be specific and actionable when `psycopg2` appears in a project that uses `asyncpg`.

Currently, a generic "infrastructure/environment issues" feedback message misdirects the Player. The feedback should say: "Your code imports `psycopg2` — this is an asyncpg project. Remove psycopg2 imports and use asyncpg-compatible patterns."

**Source**: Recommendation R4 from TASK-REV-7EB05 review report.
**Depends on**: TASK-FIX-A7F1 (psycopg2 classification fix).

## Acceptance Criteria

- [ ] When test output contains `ModuleNotFoundError: No module named 'psycopg2'` AND the project's bootstrap includes `asyncpg` (detectable from task's `requires_infrastructure` or bootstrap package list), Coach feedback includes a specific message directing the Player to remove `psycopg2` imports
- [ ] Specific feedback message: something like "ModuleNotFoundError for 'psycopg2' — this project uses asyncpg. Remove `import psycopg2` from your code and use asyncpg-compatible database patterns instead."
- [ ] Feedback remains actionable and does not suggest mock fixtures or SQLite as solutions
- [ ] When `psycopg2` missing in a project that genuinely needs it (not asyncpg), feedback does NOT include the asyncpg-specific message
- [ ] Existing tests pass
- [ ] New test covers: asyncpg project + psycopg2 error → specific feedback message

## Implementation Notes

**Location**: Coach feedback generation, after `_classify_test_failure` in the test failure handling path.

The simplest approach: add a pattern-match check in the feedback generation. When test output contains `no module named 'psycopg2'`, check whether `asyncpg` or `sqlalchemy[asyncio]` is in the bootstrap packages (passed via task dict). If yes, append the specific message to the Coach's feedback string.

No classification change needed (that's TASK-FIX-A7F1's job). This is purely a feedback message improvement.

The task requires determining where Coach feedback strings are assembled for the test failure case — trace from `_feedback_from_tests()` or equivalent in `coach_validator.py`.
