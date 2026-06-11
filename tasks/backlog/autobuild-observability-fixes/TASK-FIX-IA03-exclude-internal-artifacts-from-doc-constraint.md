---
id: TASK-FIX-IA03
title: Exclude internal artifacts from documentation constraint count
status: in_review
created: 2026-02-20 00:00:00+00:00
updated: 2026-02-20 00:00:00+00:00
priority: medium
tags:
- autobuild
- bugfix
- documentation-constraint
- artifacts
task_type: feature
complexity: 3
parent_review: TASK-REV-A515
feature_id: FEAT-AOF
wave: 1
implementation_mode: task-work
autobuild:
  task_timeout: 4800
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 3
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
  base_branch: main
  started_at: '2026-06-11T15:26:06.861626'
  last_updated: '2026-06-11T16:24:24.265385'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Critical honesty discrepancy: The player claimed to modify ''tests/unit/test_agent_invoker.py'',
      but the file does not exist on disk (path_exists=False). This caused a ''partial_honesty_abort'',
      preventing any tests or quality gates from running.: Ensure that all files listed
      in ''files_modified'' are actually created and present in the workspace before
      submitting the report.'
    timestamp: '2026-06-11T15:26:06.861626'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Critical honesty discrepancy: The Player claimed to have implemented/tested
      specific test functions (e.g., `test_validate_file_count_counts_only_real_code`)
      that do not exist on disk (path_exists=False).: Ensure all files and test functions
      are correctly created, staged in git, and exist on disk before claiming completion.

      - The gathering process aborted (`partial_honesty_abort`), meaning no authoritative
      test results, coverage, or BDD verification were produced to validate the implementation.:
      Resolve the honesty discrepancies and ensure the test suite runs successfully
      so that the orchestrator can complete the evidence gathering.'
    timestamp: '2026-06-11T15:34:21.396216'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-06-11T15:51:52.389796'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Exclude internal artifacts from documentation constraint count

## Description

The `_validate_file_count_constraint()` method in `guardkit/orchestrator/agent_invoker.py` counts `player_turn_N.json` (an AutoBuild internal artifact) as a user-created file. Since every task-work delegation creates this file, it always consumes one slot of the 2-file budget for "minimal" level, causing 7/12 tasks to trigger false constraint violations.

The fix is to exclude `.guardkit/autobuild/*/player_turn_*.json` and other internal artifacts from the constraint count rather than raising the numeric limit.

## Source

- Review report: `.claude/reviews/TASK-REV-A515-review-report.md` (Finding 4)
- Evidence: All 7 violations include `player_turn_1.json` in the file list

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py`

## Implementation Plan

### Step 1: Add internal artifact filter to `_validate_file_count_constraint`

```python
def _validate_file_count_constraint(self, task_id, documentation_level, files_created):
    max_files = DOCUMENTATION_LEVEL_MAX_FILES.get(documentation_level)
    if max_files is None:
        return

    # Exclude internal AutoBuild artifacts from count
    user_files = [
        f for f in files_created
        if "/.guardkit/autobuild/" not in f
        and ".guardkit/autobuild/" not in f
    ]

    actual_count = len(user_files)
    if actual_count > max_files:
        files_preview = user_files[:5]
        suffix = "..." if len(user_files) > 5 else ""
        logger.warning(
            f"[{task_id}] Documentation level constraint violated: "
            f"created {actual_count} user files, max allowed {max_files} "
            f"for {documentation_level} level. Files: {files_preview}{suffix}"
        )
```

### Step 2: Consider excluding test files from constraint (optional)

Test files are quality artefacts, not scope creep. If the constraint is meant to prevent documentation bloat, test files arguably shouldn't count. This is an optional enhancement — discuss with reviewers.

## Acceptance Criteria

- [ ] `player_turn_N.json` excluded from documentation constraint count
- [ ] All `.guardkit/autobuild/*` paths excluded from constraint count
- [ ] Warning message shows "user files" count (excluding artifacts)
- [ ] Unit test verifies artifact exclusion
- [ ] Tasks creating command spec + test file (2 user files) no longer trigger warning at "minimal" level
