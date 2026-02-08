---
id: TASK-FIX-ITDF
title: Fix independent test detection to find Player-created tests
status: backlog
created: 2026-02-08T15:30:00Z
updated: 2026-02-08T15:30:00Z
priority: high
task_type: feature
complexity: 5
dependencies: []
parent_review: TASK-REV-53B1
tags: [autobuild, coach-validator, quality-gates, test-detection]
---

# Fix Independent Test Detection to Find Player-Created Tests

## Problem

The Coach's independent test detection (`coach_validator.py:971-1039`) only searches for one glob pattern: `tests/test_{task_prefix}*.py` (e.g., `tests/test_task_dm_008*.py`). This pattern misses all Player-created tests because Players name tests based on the module being tested, not the task ID.

**Evidence from FEAT-D4CE**: 0/8 tasks had independent test verification performed. The Coach logged "No task-specific tests found for TASK-DM-XXX, skipping independent verification" for every feature task, despite the Player creating test files like:
- `tests/orchestrator/test_mcp_design_extractor.py` (DM-002)
- `tests/orchestrator/test_phase0_design_extraction.py` (DM-003)
- `tests/unit/test_browser_verifier.py` (DM-005)
- `tests/unit/design/test_design_change_detector.py` (DM-008)

## Root Cause

`_detect_test_command()` uses a single glob pattern that requires test files to contain the task ID in the filename. The Player's /task-work session names tests after the module, not the task. When no match is found, the method returns `None`, which is treated as "pass" with a misleading "Independent verification confirmed" message.

## Acceptance Criteria

### Detection Improvements
- [ ] After failing the task-ID glob pattern, fall back to checking the Player's git change list for test files (files matching `test_*.py` or `*_test.py` in the created/modified file list)
- [ ] Use the Player report's `files_created` and `files_modified` lists (from `player_turn_N.json`) to identify candidate test files
- [ ] Only run detected test files that are within the worktree (security: don't run arbitrary paths)
- [ ] Log which detection method found the tests (task-ID pattern vs git change list)

### Misleading Message Fix
- [ ] When tests are skipped (test_command="skipped"), the rationale must NOT say "Independent verification confirmed"
- [ ] Use distinct rationale messages:
  - Tests verified: "All quality gates passed. Independent verification confirmed: N tests passed."
  - Tests skipped (no tests found): "All quality gates passed. Independent verification skipped: no task-specific tests found."
  - Tests skipped (not required): "All quality gates passed. Tests not required for scaffolding task."

### Safety
- [ ] Do not break the existing task-ID pattern detection (keep it as primary)
- [ ] Fall back gracefully if Player report is not available
- [ ] Do not run tests from other parallel tasks (filter to files in the Player's change set only)

## Implementation Notes

### Files to Modify
- `guardkit/orchestrator/quality_gates/coach_validator.py`:
  - `_detect_test_command()` (~line 971): Add git change list fallback
  - `validate()` (~line 629): Fix rationale message based on actual verification status
  - `run_independent_tests()` (~line 819): Pass Player report data to detection

### Data Available
- Player report at `.guardkit/autobuild/{task_id}/player_turn_{N}.json` contains:
  - `files_created`: list of file paths
  - `files_modified`: list of file paths
- These can be filtered for test file patterns (`test_*.py`, `*_test.py`)

### Test Strategy
- Unit tests for `_detect_test_command()` with both detection paths
- Unit test for rationale message generation with all three states
- Integration test: mock Player report with test files, verify detection works

## Constraints

- Must not break existing task-ID-based detection (keep as primary)
- Must not introduce cross-task test execution (critical for shared worktree safety)
- Must not increase Coach validation time significantly
