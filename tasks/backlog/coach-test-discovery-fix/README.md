# Coach Test Discovery Fix (FEAT-CTD)

**Parent Review**: [TASK-REV-0E44](../../../.claude/reviews/TASK-REV-0E44-review-report.md)
**Status**: Backlog
**Tasks**: 5 (3 in Wave 1, 2 in Wave 2)
**Total Complexity**: 16/50

## Problem

AutoBuild FEAT-4296 stalled on TASK-EVAL-009 (Graphiti Storage) with `UNRECOVERABLE_STALL` after 3 turns. The implementation was complete (46 tests, 100% coverage, all gates passed) but the Coach's independent test verification included workspace template test files that fail at pytest collection time. Four technology seam failures created an unbreakable feedback loop.

## Solution

Fix the four seams in priority order:

1. **Filter excluded paths** — Respect `collect_ignore_glob` in test discovery (prevents the root cause)
2. **Classify collection errors** — Distinguish collection errors from execution failures
3. **Expand approval path** — Conditionally approve when collection errors + all gates pass
4. **Improve feedback** — Give the Player actionable error details
5. **Remediate** — Complete TASK-EVAL-009 and resume FEAT-4296

## Tasks

| Wave | Task | Title | Priority | Complexity |
|------|------|-------|----------|------------|
| 1 | TASK-FIX-7F48 | Filter collect_ignore_glob paths | Critical | 4 |
| 1 | TASK-FIX-DF44 | Add collection_error classification | High | 4 |
| 1 | TASK-FIX-3A01 | Improve feedback detail | Medium | 2 |
| 2 | TASK-FIX-1D70 | Expand conditional approval | High | 3 |
| 2 | TASK-FIX-7D71 | Remediate TASK-EVAL-009 | High | 3 |
