---
id: TASK-AB-F55D
title: Implement WorktreeManager class
status: backlog
created: 2025-12-23T07:22:00Z
updated: 2025-12-23T07:22:00Z
priority: high
tags: [autobuild, git, worktree, isolation]
complexity: 5
parent_review: TASK-REV-47D2
wave: 1
conductor_workspace: autobuild-phase1a-wave1-2
implementation_mode: task-work
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Implement WorktreeManager class

## Description

Create `guardkit/orchestrator/worktrees.py` with a `WorktreeManager` class that manages the git worktree lifecycle for AutoBuild tasks, providing isolated workspaces for Player/Coach agent iterations.

## Parent Review

This task was generated from review task TASK-REV-47D2.

**Review Recommendation**: Modular architecture with separated WorktreeManager component for reusability and testability.

## Acceptance Criteria

- [ ] Create `guardkit/orchestrator/worktrees.py` module
- [ ] Implement `WorktreeManager` class with methods: `create()`, `merge()`, `cleanup()`, `preserve_on_failure()`
- [ ] Worktree creation uses branch naming: `autobuild/{task_id}`
- [ ] Worktree path: `.guardkit/worktrees/{task_id}/`
- [ ] Merge functionality integrates worktree branch to main
- [ ] Cleanup removes worktree directory and branch
- [ ] Failure preservation keeps worktree for manual inspection
- [ ] Unit tests with ≥80% coverage
- [ ] Error handling for git command failures

## Implementation Details

### Class Structure

```python
from pathlib import Path
from dataclasses import dataclass
import subprocess

@dataclass
class Worktree:
    task_id: str
    branch: str
    path: Path

class WorktreeManager:
    """Manages git worktree lifecycle for AutoBuild tasks"""

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path.cwd()
        self.worktree_base = self.repo_root / ".guardkit" / "worktrees"
        self.worktree_base.mkdir(parents=True, exist_ok=True)

    def create(self, task_id: str) -> Worktree:
        """Create isolated git worktree for task"""
        branch = f"autobuild/{task_id}"
        path = self.worktree_base / task_id

        # Create branch from current HEAD
        subprocess.run(["git", "branch", branch], check=True)

        # Create worktree
        subprocess.run([
            "git", "worktree", "add", str(path), branch
        ], check=True)

        return Worktree(task_id=task_id, branch=branch, path=path)

    def merge(self, worktree: Worktree) -> None:
        """Merge worktree branch to main"""
        # Switch to main
        subprocess.run(["git", "checkout", "main"], check=True)

        # Merge branch
        subprocess.run(["git", "merge", worktree.branch], check=True)

        # Cleanup after successful merge
        self.cleanup(worktree)

    def cleanup(self, worktree: Worktree) -> None:
        """Remove worktree directory and branch"""
        # Remove worktree
        subprocess.run([
            "git", "worktree", "remove", str(worktree.path)
        ], check=True)

        # Delete branch
        subprocess.run(["git", "branch", "-d", worktree.branch], check=True)

    def preserve_on_failure(self, worktree: Worktree) -> None:
        """Preserve worktree for manual inspection"""
        # Don't remove - just log for human review
        print(f"⚠️  Worktree preserved for review: {worktree.path}")
        print(f"   Branch: {worktree.branch}")
        print(f"   To inspect: cd {worktree.path}")
```

### Error Handling

```python
class WorktreeError(Exception):
    """Raised when worktree operation fails"""
    pass

def create(self, task_id: str) -> Worktree:
    try:
        # ... creation logic ...
    except subprocess.CalledProcessError as e:
        raise WorktreeError(f"Failed to create worktree for {task_id}: {e}")
```

## Test Strategy

### Unit Tests (tests/unit/test_worktree_manager.py)

```python
import pytest
from pathlib import Path
from guardkit.orchestrator.worktrees import WorktreeManager, Worktree

@pytest.fixture
def temp_repo(tmp_path):
    """Create temporary git repo for testing"""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    # Create initial commit
    (repo / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True)
    return repo

def test_worktree_creates_branch(temp_repo):
    manager = WorktreeManager(repo_root=temp_repo)
    worktree = manager.create("TASK-042")
    assert worktree.branch == "autobuild/TASK-042"
    assert worktree.path.exists()

def test_worktree_cleanup_removes_directory(temp_repo):
    manager = WorktreeManager(repo_root=temp_repo)
    worktree = manager.create("TASK-042")
    manager.cleanup(worktree)
    assert not worktree.path.exists()

def test_worktree_merge_integrates_changes(temp_repo):
    manager = WorktreeManager(repo_root=temp_repo)
    worktree = manager.create("TASK-042")

    # Make change in worktree
    test_file = worktree.path / "test.txt"
    test_file.write_text("test content")
    subprocess.run(["git", "add", "."], cwd=worktree.path, check=True)
    subprocess.run(["git", "commit", "-m", "Test"], cwd=worktree.path, check=True)

    # Merge
    manager.merge(worktree)

    # Verify change in main
    assert (temp_repo / "test.txt").exists()
```

## Files to Create

- `guardkit/orchestrator/__init__.py`
- `guardkit/orchestrator/worktrees.py`
- `tests/unit/test_worktree_manager.py`

## Dependencies

- Python 3.10+
- Git 2.20+ (for worktree support)

## Estimated Effort

3-4 hours

## Implementation Mode

**task-work** - Requires implementation, testing, and quality gates
