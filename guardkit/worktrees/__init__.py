"""Git worktree management for GuardKit AutoBuild."""

from .manager import (
    WorktreeManager,
    Worktree,
    WorktreeError,
    WorktreeCreationError,
    WorktreeMergeError,
    CommandExecutor,
    SubprocessExecutor,
)

__all__ = [
    "WorktreeManager",
    "Worktree",
    "WorktreeError",
    "WorktreeCreationError",
    "WorktreeMergeError",
    "CommandExecutor",
    "SubprocessExecutor",
]
