"""
Git worktree management for AutoBuild isolated task workspaces.

This module provides the WorktreeManager class for managing the lifecycle of
git worktrees used by the AutoBuild system. Each task gets an isolated worktree
for Player/Coach agent iterations, ensuring parallel execution and safe rollback.

Example:
    >>> from pathlib import Path
    >>> from guardkit.worktrees import WorktreeManager
    >>>
    >>> manager = WorktreeManager(repo_root=Path.cwd())
    >>> worktree = manager.create("TASK-AB-001")
    >>> # ... work in worktree ...
    >>> manager.merge(worktree)  # Success path
    >>> # OR
    >>> manager.preserve_on_failure(worktree)  # Failure path
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional


# ============================================================================
# Exceptions
# ============================================================================


class WorktreeError(Exception):
    """Base exception for worktree operations."""
    pass


class WorktreeCreationError(WorktreeError):
    """Raised when worktree creation fails."""
    pass


class WorktreeMergeError(WorktreeError):
    """Raised when worktree merge fails."""
    pass


# ============================================================================
# Command Executor Protocol (Dependency Injection)
# ============================================================================


class CommandExecutor(Protocol):
    """
    Protocol for executing shell commands.

    This protocol enables dependency injection and mocking in tests,
    satisfying the Dependency Inversion Principle from the architectural review.
    """

    def run(
        self,
        args: list[str],
        cwd: Optional[Path] = None,
        check: bool = True,
        capture_output: bool = True,
        text: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Execute a command with specified arguments.

        Args:
            args: Command and arguments to execute
            cwd: Working directory for command execution
            check: Whether to raise exception on non-zero exit code
            capture_output: Whether to capture stdout/stderr
            text: Whether to decode output as text

        Returns:
            CompletedProcess instance with execution results

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
        """
        ...


class SubprocessExecutor:
    """
    Concrete implementation of CommandExecutor using subprocess.

    This is the default production executor that runs actual shell commands.
    """

    def run(
        self,
        args: list[str],
        cwd: Optional[Path] = None,
        check: bool = True,
        capture_output: bool = True,
        text: bool = True,
    ) -> subprocess.CompletedProcess:
        """Execute command using subprocess.run()."""
        return subprocess.run(
            args,
            cwd=cwd,
            check=check,
            capture_output=capture_output,
            text=text,
        )


# ============================================================================
# Data Models
# ============================================================================


@dataclass(frozen=True)
class Worktree:
    """
    Immutable representation of a git worktree for a task.

    Attributes:
        task_id: Unique identifier for the task (e.g., "TASK-AB-001")
        branch_name: Git branch name for this worktree
        path: Filesystem path to the worktree directory
        base_branch: The branch this worktree was created from
    """

    task_id: str
    branch_name: str
    path: Path
    base_branch: str

    def __post_init__(self):
        """Validate worktree data after initialization."""
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if not self.branch_name:
            raise ValueError("branch_name cannot be empty")
        if not isinstance(self.path, Path):
            raise ValueError("path must be a Path instance")
        if not self.base_branch:
            raise ValueError("base_branch cannot be empty")


# ============================================================================
# Worktree Manager
# ============================================================================


class WorktreeManager:
    """
    Manages git worktree lifecycle for AutoBuild tasks.

    This class handles creation, merging, cleanup, and preservation of git
    worktrees used for isolated task execution in the AutoBuild workflow.

    Each task gets its own worktree in .guardkit/worktrees/{task_id}/ with
    a branch named autobuild/{task_id}.

    Attributes:
        repo_root: Root directory of the git repository
        worktrees_dir: Directory where worktrees are created
        executor: Command executor for running git commands

    Example:
        >>> manager = WorktreeManager(Path.cwd())
        >>> worktree = manager.create("TASK-AB-001", base_branch="main")
        >>> # ... do work in worktree ...
        >>> manager.merge(worktree, target_branch="main")
    """

    def __init__(
        self,
        repo_root: Path,
        executor: Optional[CommandExecutor] = None,
    ):
        """
        Initialize WorktreeManager.

        Args:
            repo_root: Root directory of the git repository
            executor: Command executor for git operations (defaults to SubprocessExecutor)

        Raises:
            WorktreeError: If repo_root is not a valid git repository
        """
        self.repo_root = repo_root.resolve()
        self.worktrees_dir = self.repo_root / ".guardkit" / "worktrees"
        self.executor = executor or SubprocessExecutor()

        # Validate git repository
        self._validate_git_repo()

    def _validate_git_repo(self) -> None:
        """
        Validate that repo_root is a valid git repository.

        Raises:
            WorktreeError: If repo_root is not a git repository
        """
        try:
            self._run_git(["rev-parse", "--git-dir"])
        except subprocess.CalledProcessError as e:
            raise WorktreeError(
                f"Not a git repository: {self.repo_root}\n"
                f"Git error: {e.stderr if e.stderr else str(e)}"
            )

    def _run_git(
        self,
        args: list[str],
        cwd: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        """
        Execute a git command with error handling.

        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory (defaults to repo_root)

        Returns:
            CompletedProcess with command results

        Raises:
            WorktreeError: If git command fails
        """
        full_args = ["git"] + args
        working_dir = cwd if cwd is not None else self.repo_root

        try:
            return self.executor.run(
                full_args,
                cwd=working_dir,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise WorktreeError(
                f"Git command failed: {' '.join(full_args)}\n"
                f"Exit code: {e.returncode}\n"
                f"Stderr: {e.stderr if e.stderr else '(none)'}"
            )

    def _build_branch_name(self, task_id: str) -> str:
        """
        Build branch name for a task's worktree.

        This helper method implements the DRY principle by centralizing
        branch name construction logic.

        Args:
            task_id: Task identifier

        Returns:
            Branch name in format: autobuild/{task_id}
        """
        return f"autobuild/{task_id}"

    def create(
        self,
        task_id: str,
        base_branch: str = "main",
    ) -> Worktree:
        """
        Create an isolated git worktree for a task.

        Creates a new branch from base_branch and a worktree directory under
        .guardkit/worktrees/{task_id}/. This provides an isolated workspace
        for Player/Coach agent iterations.

        Args:
            task_id: Unique identifier for the task
            base_branch: Branch to create worktree from (default: "main")

        Returns:
            Worktree instance with path and branch information

        Raises:
            WorktreeCreationError: If worktree creation fails

        Example:
            >>> worktree = manager.create("TASK-AB-001")
            >>> print(worktree.path)
            /path/to/repo/.guardkit/worktrees/TASK-AB-001
            >>> print(worktree.branch_name)
            autobuild/TASK-AB-001
        """
        branch_name = self._build_branch_name(task_id)
        worktree_path = self.worktrees_dir / task_id

        # Ensure worktrees directory exists
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

        # Create worktree with new branch
        try:
            self._run_git([
                "worktree", "add",
                str(worktree_path),
                "-b", branch_name,
                base_branch
            ])
        except WorktreeError as e:
            raise WorktreeCreationError(
                f"Failed to create worktree for {task_id}: {e}"
            )

        return Worktree(
            task_id=task_id,
            branch_name=branch_name,
            path=worktree_path,
            base_branch=base_branch,
        )

    def merge(
        self,
        worktree: Worktree,
        target_branch: str = "main",
    ) -> None:
        """
        Merge worktree branch into target branch.

        This integrates the work done in the worktree back into the main
        codebase. Uses --no-ff to create a merge commit for traceability.

        Args:
            worktree: Worktree to merge
            target_branch: Branch to merge into (default: "main")

        Raises:
            WorktreeMergeError: If merge fails or has conflicts

        Example:
            >>> manager.merge(worktree, target_branch="main")
        """
        # Switch to target branch
        try:
            self._run_git(["checkout", target_branch])
        except WorktreeError as e:
            raise WorktreeMergeError(
                f"Failed to checkout {target_branch}: {e}"
            )

        # Merge with --no-ff for explicit merge commit
        try:
            self._run_git([
                "merge", "--no-ff",
                "-m", f"Merge {worktree.task_id} from AutoBuild",
                worktree.branch_name
            ])
        except WorktreeError as e:
            # Check for merge conflicts
            try:
                status = self._run_git(["status", "--porcelain"])
                if status.stdout and "UU" in status.stdout:
                    raise WorktreeMergeError(
                        f"Merge conflicts in {worktree.task_id}. "
                        f"Resolve manually or use preserve_on_failure()"
                    )
            except WorktreeError:
                pass  # Status check failed, just report original error

            raise WorktreeMergeError(
                f"Merge failed for {worktree.task_id}: {e}"
            )

    def cleanup(
        self,
        worktree: Worktree,
        force: bool = False,
    ) -> None:
        """
        Remove worktree directory and branch.

        This cleans up after successful merge or when abandoning work.

        Args:
            worktree: Worktree to remove
            force: Force removal even if worktree has uncommitted changes

        Raises:
            WorktreeError: If cleanup fails

        Example:
            >>> manager.cleanup(worktree)
            >>> # Worktree directory and branch are now removed
            >>>
            >>> # Or force removal if worktree has uncommitted changes
            >>> manager.cleanup(worktree, force=True)
        """
        # Remove worktree directory
        try:
            remove_args = ["worktree", "remove", str(worktree.path)]
            if force:
                remove_args.append("--force")
            self._run_git(remove_args)
        except WorktreeError as e:
            raise WorktreeError(
                f"Failed to remove worktree for {worktree.task_id}: {e}"
            )

        # Delete branch
        try:
            delete_flag = "-D" if force else "-d"
            self._run_git(["branch", delete_flag, worktree.branch_name])
        except WorktreeError as e:
            raise WorktreeError(
                f"Failed to delete branch {worktree.branch_name}: {e}"
            )

    def preserve_on_failure(self, worktree: Worktree) -> None:
        """
        Preserve worktree for manual inspection after failure.

        This keeps the worktree directory and branch intact so developers
        can investigate failures, debug issues, or manually recover work.

        The worktree is not removed - it remains in .guardkit/worktrees/
        for human review.

        Args:
            worktree: Worktree to preserve

        Example:
            >>> try:
            ...     manager.merge(worktree)
            ... except WorktreeMergeError:
            ...     manager.preserve_on_failure(worktree)
            ...     # Worktree kept for manual inspection
        """
        # Don't remove anything - just log preservation message
        # This is a no-op that signals intent to preserve
        # The worktree remains in .guardkit/worktrees/ for human review

        # Note: If you add logging in future, do it here
        # logger.info(f"Preserving worktree for {worktree.task_id} at {worktree.path}")
        pass
