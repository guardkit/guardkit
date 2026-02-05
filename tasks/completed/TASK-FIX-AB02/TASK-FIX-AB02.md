---
id: TASK-FIX-AB02
title: Serialize git checkpoint operations for shared worktrees
status: completed
created: 2026-02-05T17:00:00Z
updated: 2026-02-05T18:00:00Z
completed: 2026-02-05T18:00:00Z
priority: high
tags: [autobuild, bugfix, concurrency]
parent_review: TASK-REV-5796
task_type: bugfix
complexity: 4
implementation_mode: task-work
---

# Task: Serialize git checkpoint operations for shared worktrees

## Problem Statement

When multiple tasks in a wave share the same worktree (feature mode), `create_checkpoint()` in `guardkit/orchestrator/worktree_checkpoints.py:292` runs `git add -A` concurrently. This causes `index.lock` conflicts:

```
fatal: Unable to create '.git/worktrees/FEAT-CR01/index.lock': File exists.
```

TASK-CR-002 and TASK-CR-003 failed due to this race condition during FEAT-CR01 execution.

## Acceptance Criteria

- [x] Git operations in `create_checkpoint()` are serialized when multiple tasks share a worktree
- [x] No `index.lock` errors when running parallel tasks in the same worktree
- [x] Performance impact is minimal (checkpoints are fast operations)
- [x] Existing single-task AutoBuild behaviour unchanged
- [x] Unit tests cover concurrent checkpoint creation scenario

## Implementation Notes

### Recommended approach: Sequential checkpoint phase

In the feature orchestrator (`feature_orchestrator.py`), after all parallel tasks complete their Player/Coach loop for a turn, run checkpoints sequentially rather than allowing them to run concurrently. This is the cleanest architectural fix.

### Alternative: File-based lock with retry

Add a lock mechanism in `WorktreeCheckpointManager.create_checkpoint()`:

```python
import fcntl

lock_path = self.worktree_path / ".guardkit-git.lock"
with open(lock_path, 'w') as lock_file:
    fcntl.flock(lock_file, fcntl.LOCK_EX)
    try:
        self.git_executor.execute(["git", "add", "-A"], cwd=self.worktree_path)
        self.git_executor.execute(["git", "commit", "-m", message, "--allow-empty"], cwd=self.worktree_path)
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
```

### Files likely affected

- `guardkit/orchestrator/worktree_checkpoints.py` - Add lock or serialization
- `guardkit/orchestrator/feature_orchestrator.py` - If using sequential checkpoint approach
- `tests/orchestrator/test_worktree_checkpoints.py` - Add concurrency tests
