---
id: TASK-FIX-TDPR
title: Refactor test detection to use Player file list as primary source
status: in_review
created: 2026-02-08T16:30:00Z
updated: 2026-02-08T16:30:00Z
priority: high
task_type: feature
complexity: 4
dependencies: [TASK-FIX-ITDF]
parent_review: TASK-REV-53B1
tags: [autobuild, coach-validator, quality-gates, test-detection, refactor]
---

# Refactor Test Detection to Use Player File List as Primary Source

## Problem

TASK-FIX-ITDF added a Player report fallback to `_detect_test_command()`, but this is a workaround — the architecture is inverted. The primary detection path (`tests/test_{task_prefix}*.py` glob) has **never matched** a Player-created test file because Players name tests after the module being tested (e.g., `test_browser_verifier.py`), not the task ID (e.g., `test_task_dm_005.py`).

The current flow is:
1. Try task-ID glob (never matches) → fail
2. Fall back to reading Player report from disk (re-reads data already available in memory)
3. Give up

The correct flow should be:
1. Extract test files from `task_work_results` (already loaded in memory during validation)
2. If no results available, fall back to task-ID glob as last resort

## Root Cause

`_detect_test_command()` was designed around an assumed naming convention that Players don't follow. The workaround reads Player reports from disk, but `task_work_results.json` — which contains the same `files_created`/`files_modified` lists — is **already loaded** in the `validate()` call chain and could be passed directly.

## Acceptance Criteria

### Invert Detection Priority
- [ ] `_detect_test_command()` accepts `task_work_results: Optional[Dict]` parameter
- [ ] Primary detection: extract test files from `task_work_results["files_created"]` + `task_work_results["files_modified"]`
- [ ] Secondary detection (fallback): task-ID glob pattern (kept for edge cases where results aren't available)
- [ ] Remove `_detect_tests_from_player_report()` method (redundant — same data is in `task_work_results`)

### Pass Data Through Call Chain
- [ ] `validate()` passes `task_work_results` to `run_independent_tests()`
- [ ] `run_independent_tests()` passes `task_work_results` to `_detect_test_command()`
- [ ] No additional file I/O — uses data already in memory

### Test Updates
- [ ] Update `TestPlayerReportFallbackDetection` tests to test the new primary path
- [ ] Remove tests for `_detect_tests_from_player_report()` (method deleted)
- [ ] Add tests for: task_work_results provided with test files → detected
- [ ] Add tests for: task_work_results not provided → falls back to glob
- [ ] Add tests for: task_work_results provided with no test files → falls back to glob
- [ ] Verify no regressions in existing test suite

## Implementation Notes

### Files to Modify
- `guardkit/orchestrator/quality_gates/coach_validator.py`:
  - `_detect_test_command()`: Accept `task_work_results` param, use as primary source
  - `run_independent_tests()`: Accept and forward `task_work_results`
  - `validate()`: Pass `task_work_results` through to `run_independent_tests()`
  - Delete `_detect_tests_from_player_report()` method
- `tests/unit/test_coach_validator.py`:
  - Refactor `TestPlayerReportFallbackDetection` → `TestPrimaryTestDetection`
  - Update test fixtures to pass `task_work_results` instead of mocking player report files

### Data Already Available
`task_work_results` dict (loaded from `.guardkit/autobuild/{task_id}/task_work_results.json`) contains:
```json
{
  "files_created": ["tests/unit/test_browser_verifier.py", "src/browser.py"],
  "files_modified": ["tests/unit/test_existing.py"],
  "quality_gates": { "all_passed": true, "tests_passed": 5 }
}
```

This is already loaded in `validate()` at the point where `run_independent_tests()` is called.

### Why This Is Better
1. **No extra file I/O** — `_detect_tests_from_player_report()` reads Player report files from disk; this uses data already in memory
2. **Single source of truth** — `task_work_results` is the canonical record of what the Player did
3. **Simpler code** — removes a method, reduces branching
4. **Correct architecture** — primary path uses real data, fallback uses heuristic glob

## Constraints

- Must not break existing test detection for non-autobuild scenarios (when `task_work_results` is None)
- Task-ID glob must remain as fallback, not be deleted entirely
- Must not change the `validate()` return type or public API
