---
id: TASK-FP-003
title: Add repository state check to worktree manager
status: completed
created: 2026-01-06T09:15:00Z
updated: 2026-01-07T10:00:00Z
completed: 2026-01-07T11:30:00Z
priority: medium
complexity: 3
tags: [git, worktree, error-handling]
parent_review: TASK-REV-66B4
wave: 2
dependencies: []
implementation_mode: task-work
testing_mode: tdd
workspace: fp-schema-wave2-worktree
---

# Task: Add repository state check to worktree manager

## Description

Add a check for empty repositories before attempting to create a git worktree. Currently, `git worktree add ... main` fails with "invalid reference: main" when the repository has no commits.

## Current Behavior

```
git worktree add .guardkit/worktrees/FEAT-XXX -b autobuild/FEAT-XXX main
fatal: invalid reference: main
```

This happens when:
1. Repository is freshly initialized (`git init`)
2. No commits have been made yet
3. The `main` branch doesn't exist

## Expected Behavior

```
Cannot create worktree: repository has no commits.
Create an initial commit first:
  git add . && git commit -m "Initial commit"
```

## Acceptance Criteria

- [x] Check if base branch exists before worktree creation
- [x] Check if repository has any commits (is empty)
- [x] Provide clear error message with fix instructions
- [x] Add helper method `_is_empty_repo()` to worktree manager
- [x] Add helper method `_branch_exists(branch_name)` to worktree manager
- [x] Unit tests for empty repo and missing branch scenarios

## Files to Modify

- `guardkit/worktrees/manager.py`

## Implementation

```python
def _is_empty_repo(self) -> bool:
    """Check if repository has no commits."""
    try:
        result = self._run_git(["rev-parse", "HEAD"])
        return False
    except WorktreeError:
        return True

def _branch_exists(self, branch_name: str) -> bool:
    """Check if a branch exists."""
    try:
        self._run_git(["rev-parse", "--verify", f"refs/heads/{branch_name}"])
        return True
    except WorktreeError:
        return False

def create(self, task_id: str, base_branch: str = "main") -> Worktree:
    # Add before worktree creation
    if not self._branch_exists(base_branch):
        if self._is_empty_repo():
            raise WorktreeCreationError(
                f"Cannot create worktree: repository has no commits. "
                f"Create an initial commit first: "
                f"git add . && git commit -m 'Initial commit'"
            )
        else:
            raise WorktreeCreationError(
                f"Base branch '{base_branch}' does not exist. "
                f"Available branches: {self._list_branches()}"
            )
    # ... existing worktree creation logic
```

## Test Cases

1. Empty repository → clear error with fix instructions
2. Repository with commits but missing branch → list available branches
3. Normal repository with main branch → success
4. Repository with different default branch (master) → use correct branch
