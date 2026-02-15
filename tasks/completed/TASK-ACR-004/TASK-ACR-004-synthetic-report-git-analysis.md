---
id: TASK-ACR-004
title: "Extend synthetic report promise generation with git analysis"
status: completed
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T19:15:00Z
completed: 2026-02-15T19:15:00Z
priority: medium
task_type: feature
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 3
implementation_mode: task-work
complexity: 6
dependencies:
  - TASK-ACR-001
  - TASK-ACR-002
tags: [autobuild, coach, synthetic-report, git-analysis, f2-fix]
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-15T19:15:00Z
  tests_passed: 25
  tests_total: 25
completed_location: tasks/completed/TASK-ACR-004/
---

# Task: Extend synthetic report promise generation with git analysis

## Description

Currently `_build_synthetic_report()` only generates file-existence promises for `task_type == "scaffolding"`. Extend to feature/implementation tasks by analyzing git diff to detect whether acceptance criteria were likely addressed.

## Files to Modify

- `guardkit/orchestrator/autobuild.py` — `_build_synthetic_report()` (~line 2168)
- `guardkit/orchestrator/autobuild.py` — new `_generate_git_analysis_promises()` method

## Acceptance Criteria

- [x] AC-001: When git diff shows files created/modified matching patterns in acceptance criteria, generate partial promises
- [x] AC-002: Match patterns: function names, class names, test file existence, endpoint paths mentioned in criteria
- [x] AC-003: Generated promises marked with `evidence_type: "git_analysis"` for Coach to weight confidence
- [x] AC-004: Existing scaffolding file-existence promise generation unchanged
- [x] AC-005: Git analysis only runs when `_synthetic: True` and task_type is not scaffolding
- [x] AC-006: Promises from git analysis set `status: "partial"` (not "complete") to indicate lower confidence
- [x] AC-007: Unit tests verify promise generation from mock git diff output

## Implementation Notes

Extend `_generate_file_existence_promises()` pattern:
1. Get git diff since turn start (files created/modified)
2. For each acceptance criterion, check if any diff file or diff content matches keywords
3. Generate promise with `evidence_type: "git_analysis"` and `status: "partial"`
4. Coach `_match_by_promises()` should treat `status: "partial"` as verified but with lower weight

## Implementation Summary

### Files Modified

1. **guardkit/orchestrator/autobuild.py**
   - Modified `_build_synthetic_report()`: Split promise generation into two strategies (scaffolding → file-existence, non-scaffolding → git-analysis)
   - Added `_generate_git_analysis_promises()`: Matches acceptance criteria against changed files using file paths, code patterns, and keywords
   - Added `_extract_code_patterns()`: Extracts function calls, CamelCase class names (with word splitting), and endpoint paths
   - Added `_extract_criterion_keywords()`: Extracts meaningful keywords filtering stopwords
   - Added `_KEYWORD_STOPWORDS` class constant

2. **guardkit/orchestrator/quality_gates/coach_validator.py**
   - Modified `_match_by_promises()`: Added `elif` for `status == "partial"` → treats as "verified" with `[Partial confidence - {evidence_type}]` evidence prefix

3. **tests/unit/test_autobuild_synthetic_report.py**
   - Updated 2 pre-existing tests for new behavior (feature tasks now generate git-analysis promises)
   - Added 14 new tests covering all acceptance criteria

### Test Results

- test_autobuild_synthetic_report.py: 25/25 passed
- test_coach_validator.py: 184/184 passed
