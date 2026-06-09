---
id: TASK-FIX-IA03
title: Exclude internal artifacts from documentation constraint count
status: completed
created: 2026-02-20 00:00:00+00:00
updated: 2026-06-09T21:42:00+01:00
completed: 2026-06-09T21:42:00+01:00
completed_location: tasks/completed/TASK-FIX-IA03/
organized_files:
  - TASK-FIX-IA03.md
  - coverage-report.json
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
  status: pass
  coverage: null
  last_run: '2026-06-09T19:19:55+00:00'
  summary: 22 passed, 2 warnings in 3.13s (worktree FEAT-AOF, Coach independent run)
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
  base_branch: main
  started_at: '2026-06-09T18:53:45.333676'
  last_updated: '2026-06-09T19:19:55.245661'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-06-09T18:53:45.333676'
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

- [x] `player_turn_N.json` excluded from documentation constraint count
- [x] All `.guardkit/autobuild/*` paths excluded from constraint count
- [x] Warning message shows "user files" count (excluding artifacts)
- [x] Unit test verifies artifact exclusion
- [x] Tasks creating command spec + test file (2 user files) no longer trigger warning at "minimal" level

## Implementation Summary

The exclusion list `_DOC_LEVEL_EXCLUDED_PATTERNS` and helper `_is_doc_level_excluded()` had already been added under TASK-GK-DOC-001 (covering `.guardkit/autobuild/`, `.guardkit/bdd/`, `.claude/task-plans/`, and `__init__.py` markers). IA03 closes the AC-003/AC-004 gap left over from that earlier task by:

1. **Wording fix** (`guardkit/orchestrator/agent_invoker.py:8688`): warning text changed from `"created N files"` to `"created N user files"` so the filtered semantics are visible in log output.
2. **New regression suite** (`tests/unit/test_doc_level_constraint.py`, 256 lines): 22 tests covering
   - `_DOC_LEVEL_EXCLUDED_PATTERNS` contents
   - `_is_doc_level_excluded()` for absolute, relative, autobuild, bdd, task-plan, and `__init__.py` paths
   - `_validate_file_count_constraint()` boundary behaviour: 2 user files + N artifacts under "minimal" emits no warning; 3 user files emits exactly one warning; unknown / comprehensive levels skip the check; the warning preview caps at 5 files with a `...` suffix.

Coach (turn 1) ran `pytest tests/unit/test_doc_level_constraint.py -v --tb=short` independently and reported `22 passed, 2 warnings in 3.13s`, then approved with all five ACs verified.

The production code change lives on the FEAT-AOF worktree branch (`autobuild/FEAT-AOF` at commit `140a8cda`) alongside the other Wave-1 task design files; it will land on main via `/feature-complete FEAT-AOF` once GD02 and TP05 are also approved. Until then, the rule on main keeps its pre-IA03 wording, but the exclusion behaviour itself is unchanged from TASK-GK-DOC-001.

## Notes

- **Status path**: blocked → in_review (turn 1 approve) → completed.
- **Scope discipline**: only the load-bearing wording fix + tests were added. The "exclude test files from constraint" optional enhancement in the original plan was deliberately left out — keep the constraint about scope creep, not test density.
- **Sibling tasks under FEAT-AOF**: TASK-FIX-GD02 (shared-worktree git baseline) and TASK-FIX-TP05 (test execution for testing task-type) are still in `design_approved` in the worktree and gating the feature-level merge.
