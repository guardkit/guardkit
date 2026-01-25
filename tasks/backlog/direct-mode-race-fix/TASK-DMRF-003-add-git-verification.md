---
id: TASK-DMRF-003
title: Add git detection as verification step
status: backlog
task_type: implementation
created: 2026-01-25T17:00:00Z
priority: medium
complexity: 2
parent_review: TASK-REV-3EC5
feature_id: FEAT-DMRF
wave: 2
implementation_mode: task-work
dependencies:
  - TASK-DMRF-001
  - TASK-DMRF-002
tags: [autobuild, git-detection, verification]
---

# Task: Add git detection as verification step

## Description

Modify `_create_player_report_from_task_work` to always run git detection as a verification step, not just as a fallback when `task_work_results.json` is missing.

## Problem

Currently, git detection only runs when `task_work_results.json` doesn't exist. If the file exists but contains empty `files_modified`/`files_created` arrays, git changes are not captured.

## Acceptance Criteria

- [ ] Always run `_detect_git_changes()` after reading `task_work_results.json`
- [ ] Merge git-detected files with existing arrays (union, not replacement)
- [ ] Log when git detection adds files not in the original report
- [ ] Add unit tests for the verification step

## Implementation Notes

**File to modify**: `guardkit/orchestrator/agent_invoker.py`

**Method to modify**: `_create_player_report_from_task_work` (around line 1270-1393)

**Suggested approach**:

```python
def _create_player_report_from_task_work(self, task_id, turn, task_work_result):
    # ... existing report initialization ...

    # Read from task_work_results.json if exists
    if task_work_results_path.exists():
        # ... existing parsing ...

    # ALWAYS verify/enrich with git detection
    git_changes = self._detect_git_changes()
    if git_changes:
        original_modified = set(report["files_modified"])
        original_created = set(report["files_created"])

        git_modified = set(git_changes.get("modified", []))
        git_created = set(git_changes.get("created", []))

        # Merge (union)
        report["files_modified"] = list(original_modified | git_modified)
        report["files_created"] = list(original_created | git_created)

        # Log additions
        new_modified = git_modified - original_modified
        new_created = git_created - original_created
        if new_modified or new_created:
            logger.info(
                f"Git detection added: {len(new_modified)} modified, "
                f"{len(new_created)} created files"
            )

    # ... rest of method ...
```

## Testing

1. Create `task_work_results.json` with empty arrays
2. Mock git changes to return files
3. Verify Player report contains git-detected files
4. Verify union logic (no duplicates)

## Related Files

- `guardkit/orchestrator/agent_invoker.py` - Main implementation
- `tests/unit/orchestrator/test_agent_invoker.py` - Tests
