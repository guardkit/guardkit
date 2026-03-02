---
id: TASK-FIX-8595
title: Scope state recovery tests to task-specific files
status: backlog
task_type: feature
parent_review: TASK-REV-A327
feature_id: FEAT-E4F5
wave: 3
implementation_mode: task-work
complexity: 3
priority: medium
tags: [state-recovery, test-scoping, p2]
depends_on:
  - TASK-FIX-01FC
---

# Task: Scope state recovery tests to task-specific files

## Description

When a player report is available during state recovery, extract test file paths from the report's `tests_written` field rather than running the full worktree test suite. This makes state recovery test runs faster, more accurate, and less likely to timeout.

## Acceptance Criteria

- [ ] When player report has `tests_written` list, use those paths for CoachVerifier test run
- [ ] Fall back to full worktree run when player report is unavailable or has no `tests_written`
- [ ] All existing tests pass
- [ ] Unit test: Verify test_paths are extracted from player report when available
- [ ] Unit test: Verify fallback to None (full run) when player report lacks tests_written

## Implementation Notes

- File: `guardkit/orchestrator/autobuild.py`, lines 2214-2220
- Current code tries to extract `test_scope` from task frontmatter, but this is rarely set
- Player report reliably contains `tests_written: ["tests/unit/knowledge/test_architecture_entities.py", ...]`
- Add before the existing test_scope extraction:
  ```python
  # Prefer player report test files when available
  if player_report and player_report.get("tests_written"):
      test_paths = player_report["tests_written"]
  ```
- This depends on TASK-FIX-01FC being complete (player report data used in state recovery)
