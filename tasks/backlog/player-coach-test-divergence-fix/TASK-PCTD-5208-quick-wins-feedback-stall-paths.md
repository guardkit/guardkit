---
id: TASK-PCTD-5208
title: "Quick wins: feedback enhancement, stall normalization, path deduplication"
status: backlog
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: high
tags: [autobuild, coach-validator, stall-detection, feedback, quick-win]
task_type: feature
complexity: 4
parent_review: TASK-REV-D7B2
feature_id: FEAT-27F2
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Quick wins — feedback enhancement, stall normalization, path deduplication

## Description

Bundle of three low-effort, high-impact fixes identified in TASK-REV-D7B2 review that address the symptoms of the Player/Coach test divergence infinite loop. These are independent of the root cause fix (R5/Wave 3) and provide immediate value.

### R1: Enhance Coach feedback with error context

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py:1802-1842`

Modify `_summarize_test_output()` to include error classification, first traceback line, and full summary line (not just keyword-matched last lines). Current limit of 3 lines / 500 chars discards tracebacks that contain the actual error information.

### R2: Normalize feedback text for stall detection

**File**: `guardkit/orchestrator/autobuild.py:2619-2699`

Add `_normalize_feedback_for_stall()` method that strips variable details (test file paths, class names, line numbers, percentages, durations, test counts) before computing the MD5 hash in `_is_feedback_stalled()`. This ensures semantically identical feedback (same error category, different test class names) hashes to the same signature.

### R3: Fix duplicate path deduplication in test detection

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py:1775-1800`

Add `_normalize_to_relative()` method that converts absolute paths to relative (stripping worktree prefix) before `set()` deduplication in `_detect_tests_from_results()`. Currently, mixed absolute/relative paths from `TaskWorkStreamParser` defeat `set()` dedup.

## Acceptance Criteria

- [ ] `_summarize_test_output()` returns error type (e.g., "ImportError", "ConnectionRefusedError") and first traceback frame, up to 10 lines / 1000 chars
- [ ] `_normalize_feedback_for_stall()` strips test paths, class names, line numbers, percentages, durations, and test counts
- [ ] `_is_feedback_stalled()` uses normalized feedback for MD5 hash computation
- [ ] `_normalize_to_relative()` converts absolute paths under worktree to relative
- [ ] `_detect_tests_from_results()` uses normalized relative paths for deduplication
- [ ] Unit tests for `_summarize_test_output()` with various pytest output formats
- [ ] Unit tests for `_normalize_feedback_for_stall()` with identical-category/different-detail feedback
- [ ] Unit tests for `_normalize_to_relative()` with abs/rel/external paths
- [ ] Unit tests for `_detect_tests_from_results()` with mixed abs/rel duplicate paths
- [ ] Stall detection regression test: replay TASK-DB-003 turn sequence and verify stall fires at Turn 5

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — R1 (_summarize_test_output) and R3 (_detect_tests_from_results)
- `guardkit/orchestrator/autobuild.py` — R2 (_is_feedback_stalled, _normalize_feedback_for_stall)

## Implementation Notes

See `.claude/reviews/TASK-REV-D7B2-review-report.md` for:
- R1 proposed implementation at the "R1: Include Error Context" section
- R2 proposed implementation with regex patterns at the "R2: Normalize Feedback" section
- R3 proposed implementation with `_normalize_to_relative()` at the "R3: Fix Duplicate Path" section
- Appendix B: Stall detection state trace proving R2 would catch stall at Turn 5

## Test Execution Log
[Automatically populated by /task-work]
