---
id: TASK-FBSDK-001
title: Copy task files to worktree during feature-build setup
status: backlog
created: 2026-01-18T12:15:00Z
updated: 2026-01-18T12:15:00Z
priority: critical
tags: [feature-build, worktree, state-bridge, sdk-coordination]
complexity: 4
parent_review: TASK-REV-F6CB
feature_id: FEAT-FBSDK
implementation_mode: task-work
wave: 1
conductor_workspace: feature-build-sdk-wave1-1
depends_on: []
---

# Task: Copy task files to worktree during feature-build setup

## Description

When `FeatureOrchestrator` creates a shared worktree for a feature, it doesn't copy the task markdown files from the main repository. This causes `TaskStateBridge.ensure_design_approved_state()` to fail immediately because the task files cannot be found in any state directory within the worktree.

## Root Cause

The `FeatureOrchestrator._setup_worktree()` method creates the worktree directory structure but assumes task files will be available. Since the worktree is a fresh git checkout, task files in `tasks/backlog/{feature}/` are only present if they're committed. Feature-plan tasks may not be committed yet.

## Implementation

Add task file copy logic to `FeatureOrchestrator`:

```python
def _copy_tasks_to_worktree(self, feature: Feature, worktree: Worktree) -> None:
    """Copy feature's task files to worktree.

    Args:
        feature: Feature being orchestrated
        worktree: Created worktree instance
    """
    for task in feature.tasks:
        # Find task file in main repo
        src_pattern = self.repo_root / "tasks" / "backlog" / feature.slug / f"{task.task_id}*.md"
        dst_dir = worktree.path / "tasks" / "backlog"
        dst_dir.mkdir(parents=True, exist_ok=True)

        for task_file in self.repo_root.glob(str(src_pattern)):
            dst = dst_dir / task_file.name
            if not dst.exists():
                shutil.copy2(task_file, dst)
                logger.info(f"Copied task file to worktree: {task_file.name}")
```

Call this method in `_setup_worktree()` after worktree creation.

## Files to Modify

- `guardkit/orchestrator/feature_orchestrator.py`

## Acceptance Criteria

- [ ] Task files are copied to worktree during feature-build setup
- [ ] TaskStateBridge.ensure_design_approved_state() finds task files
- [ ] Existing worktrees with committed tasks still work
- [ ] Unit tests verify task file copy logic
- [ ] Integration test confirms feature-build setup completes

## Testing Strategy

1. **Unit Test**: Mock worktree, verify copy is called
2. **Integration Test**: Run feature-build on uncommitted task, verify setup completes
3. **Edge Case**: Already committed tasks should not fail

## Related Files

- `guardkit/tasks/state_bridge.py` - Consumer of task files
- `guardkit/worktrees/manager.py` - Worktree creation

## Notes

This is a P0 blocking fix. Feature-build cannot succeed without this change.
