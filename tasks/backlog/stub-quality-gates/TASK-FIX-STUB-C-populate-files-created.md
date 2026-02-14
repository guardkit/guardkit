---
id: TASK-FIX-STUB-C
title: Populate files_created/files_modified in task-work delegation results
status: backlog
created: 2026-02-13T12:00:00Z
priority: high
tags: [autobuild, quality-gates, test-discovery, data-gap]
parent_review: TASK-REV-STUB
feature_id: FEAT-STUB-QG
implementation_mode: task-work
wave: 2
complexity: 5
task_type: bug-fix
---

# Task: Populate files_created/files_modified in task-work delegation results

## Description

When AutoBuild delegates to the task-work subprocess, the results writer does not propagate the actual `files_created` and `files_modified` lists back into `task_work_results.json`. This breaks the Coach's primary test discovery path (`_detect_tests_from_results()`), which reads these fields to find task-specific test files.

In the TASK-SP-006 case, the Player created 5+ files (including test files) but `task_work_results.json` had `files_created: []` and `files_modified: []`. The Coach fell through to the glob-based fallback, which missed the feature-named test file.

## Current Behavior

```json
// task_work_results.json (task-work delegation path)
{
  "files_created": [],    // Always empty
  "files_modified": [],   // Always empty
  "tests_written": []     // Fixed by TASK-FIX-93A1, but still empty for delegation path
}
```

## Expected Behavior

```json
// task_work_results.json (after fix)
{
  "files_created": ["guardkit/planning/system_plan.py", "tests/unit/cli/test_system_plan_cli.py"],
  "files_modified": ["guardkit/cli/main.py"],
  "tests_written": ["tests/unit/cli/test_system_plan_cli.py"]
}
```

## Files to Change

1. `guardkit/orchestrator/agent_invoker.py` — Task-work delegation results writer needs to extract file lists from subprocess output or Player report and write them to `task_work_results.json`

## Acceptance Criteria

- [ ] AC-001: `task_work_results.json` written by the task-work delegation path includes non-empty `files_created` when the Player creates files
- [ ] AC-002: `task_work_results.json` written by the task-work delegation path includes non-empty `files_modified` when the Player modifies files
- [ ] AC-003: `_detect_tests_from_results()` can find test files via the populated `files_created`/`files_modified` fields
- [ ] AC-004: Unit test: task-work delegation results writer extracts files from Player report
- [ ] AC-005: Unit test: empty file lists are written as `[]` (not omitted) for consistency
- [ ] AC-006: All existing agent_invoker tests pass without modification

## Technical Notes

- The Player report (`player_turn_N.json`) has its own `files_created` field — but it lists autobuild artifacts, not implementation files
- Need to investigate how the task-work subprocess communicates file lists back to the orchestrator
- The `_write_task_work_results()` and `_write_direct_mode_results()` writers were updated by TASK-FIX-93A1 for `tests_written` — similar pattern applies
- This fix makes TASK-FIX-93B1's recursive glob LESS critical (primary path works instead of fallback)
- Depends on P0-A being done first (so criteria verification can validate the complete pipeline)

## References

- Review report: `.claude/reviews/TASK-REV-STUB-review-report.md` (RC-3, P1-A)
- Related fix: TASK-FIX-93A1 (added `tests_written` to results writers)
- Related fix: TASK-FIX-93B1 (recursive test glob fallback)
