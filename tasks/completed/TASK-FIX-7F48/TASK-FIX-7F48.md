---
id: TASK-FIX-7F48
title: Filter collect_ignore_glob paths from Coach test discovery
task_type: feature
parent_review: TASK-REV-0E44
feature_id: FEAT-CTD
status: completed
created: 2026-03-01T00:00:00+00:00
updated: 2026-03-01T12:00:00+00:00
completed: 2026-03-01T12:00:00+00:00
completed_location: tasks/completed/TASK-FIX-7F48/
priority: critical
tags:
  - autobuild
  - coach-validator
  - test-discovery
  - seam-fix
complexity: 4
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Filter collect_ignore_glob Paths from Coach Test Discovery

## Description

The Coach's `_detect_tests_from_results()` method blindly includes all files matching `test_*.py` or `*_test.py` from `task_work_results.json` without checking whether they match `collect_ignore_glob` patterns defined in the root `conftest.py`. When these files are passed as explicit pytest CLI arguments, they bypass pytest's automatic exclusion, causing collection errors.

This is Seam Failure 1 from the TASK-REV-0E44 review — the critical root cause of the TASK-EVAL-009 unrecoverable stall.

## Acceptance Criteria

- [ ] `_detect_tests_from_results()` loads `collect_ignore_glob` patterns from root `conftest.py` via AST parsing
- [ ] Test files matching any `collect_ignore_glob` pattern are excluded from the Coach's pytest command
- [ ] When no `conftest.py` exists, no filtering is applied (backward compatible)
- [ ] When `conftest.py` exists but has no `collect_ignore_glob`, no filtering is applied
- [ ] Excluded files are logged at DEBUG level with the pattern that matched
- [ ] `fnmatch` is used for pattern matching (same semantics as pytest)
- [ ] Absolute paths are normalised to relative before matching
- [ ] Unit tests cover: pattern match, no match, no conftest, empty patterns, absolute path normalisation

## Technical Context

- File: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Method: `_detect_tests_from_results()` (lines 2569-2615)
- Helper: `_normalize_to_relative()` (lines 2617-2629)
- Root conftest pattern: `collect_ignore_glob = ["guardkit/eval/workspaces/*/tests/*", "templates/*/tests/*"]`
- pytest uses `fnmatch` internally for `collect_ignore_glob` — use same function
- AST parsing approach: `ast.parse()` + `ast.walk()` to find `collect_ignore_glob` assignment

## Design Reference

- Review report: `.claude/reviews/TASK-REV-0E44-review-report.md` (Seam Failure 1, Fix 1)
- Evidence: `task_work_results.json` lines 50, 55 show workspace test files in `files_modified`

## Regression Risks

1. AST parsing could fail on complex conftest expressions → return `[]` on error (no filtering = current behaviour)
2. fnmatch semantics must match pytest behaviour → pytest uses fnmatch, so this is identical
3. Must not filter out legitimate test files → only filters against user-defined patterns

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
