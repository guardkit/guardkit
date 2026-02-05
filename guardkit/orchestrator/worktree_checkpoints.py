"""Worktree checkpoint and rollback manager for context pollution mitigation.

This module implements a git-based checkpoint/rollback system for AutoBuild worktrees,
addressing the context pollution problem identified in Block AI Research findings.

Architecture:
    - Checkpoint Creation: git commits at turn boundaries
    - Rollback Mechanism: git reset --hard to previous checkpoints
    - Pollution Detection: Analyze test failure patterns across turns
    - Persistence: JSON checkpoint history for audit trail

Design Patterns:
    - CommandExecutor Protocol: Testable git operations (DRY + ISP)
    - Dataclass Pattern: Lightweight checkpoint state containers
    - State Management Pattern: JSON serialization for persistence

Problem:
    The current implementation uses the same worktree across all turns. If turn 1
    creates broken code, turn 2 inherits that state, potentially polluting subsequent
    attempts. Block research emphasizes isolated context windows.

Solution:
    Optional worktree checkpointing that creates git commits at turn boundaries,
    allowing rollback when accumulated state is causing problems.

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.worktree_checkpoints import WorktreeCheckpointManager
    >>>
    >>> manager = WorktreeCheckpointManager(
    ...     worktree_path=Path(".guardkit/worktrees/TASK-001"),
    ...     task_id="TASK-001",
    ... )
    >>>
    >>> # Create checkpoint after turn completes
    >>> checkpoint = manager.create_checkpoint(turn=1, tests_passed=True)
    >>> print(f"Created checkpoint: {checkpoint.commit_hash[:8]}")
    >>>
    >>> # Detect pollution and rollback if needed
    >>> if manager.should_rollback():
    ...     target_turn = manager.find_last_passing_checkpoint()
    ...     if target_turn:
    ...         manager.rollback_to(target_turn)
"""

import fcntl
import json
import logging
import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ============================================================================
# Protocols & ABC
# ============================================================================


class GitCommandExecutor(Protocol):
    """Protocol for git command execution (DRY + ISP from architectural review).

    This protocol enables dependency injection and testability by abstracting
    git operations behind an interface.

    Methods:
        execute: Execute a git command and return output
    """

    def execute(
        self,
        command: List[str],
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Execute git command with error handling.

        Args:
            command: Git command as list (e.g., ["git", "add", "-A"])
            cwd: Working directory for command execution
            check: Whether to raise on non-zero exit code

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
        """
        ...


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class Checkpoint:
    """Immutable checkpoint record for a worktree state.

    This dataclass captures a snapshot of worktree state at turn completion,
    including git commit hash for rollback and test status for pollution detection.

    Attributes:
        turn: Turn number (1-indexed)
        commit_hash: Git commit SHA for rollback
        timestamp: ISO 8601 timestamp when checkpoint created
        tests_passed: Whether tests passed at this checkpoint
        test_count: Number of tests run (0 if no tests)
        message: Checkpoint commit message
    """

    turn: int
    commit_hash: str
    timestamp: str
    tests_passed: bool
    test_count: int = 0
    message: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            JSON-serializable dictionary
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Checkpoint":
        """Create Checkpoint from dictionary.

        Args:
            data: Dictionary with checkpoint fields

        Returns:
            Checkpoint instance
        """
        return cls(**data)


# ============================================================================
# Git Command Executor
# ============================================================================


class SubprocessGitExecutor:
    """Production git command executor using subprocess.

    This implementation provides the real git execution for production use,
    while the Protocol enables test mocking.
    """

    def execute(
        self,
        command: List[str],
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Execute git command with subprocess.

        Args:
            command: Git command as list
            cwd: Working directory
            check: Raise on non-zero exit

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
        """
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=check,
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Git command failed: {' '.join(command)}\n"
                f"Exit code: {e.returncode}\n"
                f"Stdout: {e.stdout}\n"
                f"Stderr: {e.stderr}"
            )
            raise


# ============================================================================
# Checkpoint Manager
# ============================================================================


class WorktreeCheckpointManager:
    """Manages git-based checkpoints for worktree rollback.

    This class implements the checkpoint/rollback mechanism for AutoBuild worktrees,
    providing context pollution mitigation through git state snapshots.

    Architecture:
        - Checkpoints: Git commits at turn boundaries
        - Rollback: git reset --hard to previous commit
        - Detection: Analyze test failure patterns
        - Persistence: JSON file for checkpoint history
        - Concurrency: File-based locking for shared worktrees

    When multiple tasks share a worktree (feature mode), git operations in
    create_checkpoint() are serialized using a file-based lock to prevent
    index.lock conflicts.

    Attributes:
        worktree_path: Path to git worktree
        task_id: Task identifier
        checkpoints: List of checkpoint records
        git_executor: Git command executor (injectable for testing)

    Example:
        >>> manager = WorktreeCheckpointManager(
        ...     worktree_path=Path(".guardkit/worktrees/TASK-001"),
        ...     task_id="TASK-001",
        ... )
        >>>
        >>> # After each turn:
        >>> checkpoint = manager.create_checkpoint(
        ...     turn=1,
        ...     tests_passed=True,
        ...     test_count=15,
        ... )
        >>>
        >>> # Check for pollution and rollback if needed:
        >>> if manager.should_rollback():
        ...     target = manager.find_last_passing_checkpoint()
        ...     if target:
        ...         manager.rollback_to(target)
    """

    # Class-level thread locks keyed by resolved worktree path.
    # Ensures threads coordinate before acquiring the file lock.
    _thread_locks: ClassVar[Dict[str, threading.Lock]] = {}
    _thread_locks_guard: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        worktree_path: Path,
        task_id: str,
        git_executor: Optional[GitCommandExecutor] = None,
    ):
        """Initialize WorktreeCheckpointManager.

        Args:
            worktree_path: Path to git worktree
            task_id: Task identifier
            git_executor: Optional git executor (default: SubprocessGitExecutor)
        """
        self.worktree_path = Path(worktree_path)
        self.task_id = task_id
        self.git_executor = git_executor or SubprocessGitExecutor()
        self.checkpoints: List[Checkpoint] = []

        # Checkpoint persistence path
        self._autobuild_dir = (
            self.worktree_path / ".guardkit" / "autobuild" / task_id
        )
        self._checkpoints_file = self._autobuild_dir / "checkpoints.json"

        # Git lock file path for serializing git operations across tasks
        self._git_lock_path = self.worktree_path / ".guardkit-git.lock"

        # Load existing checkpoints if available
        self._load_checkpoints()

    def create_checkpoint(
        self,
        turn: int,
        tests_passed: bool,
        test_count: int = 0,
    ) -> Checkpoint:
        """Create a checkpoint commit at current worktree state.

        This method stages all changes and creates a git commit with a
        standardized checkpoint message. The commit serves as a rollback point.

        Git operations (add, commit, rev-parse) are serialized using a
        file-based lock to prevent index.lock conflicts when multiple tasks
        share the same worktree in feature mode.

        Args:
            turn: Turn number (1-indexed)
            tests_passed: Whether tests passed at this turn
            test_count: Number of tests run (0 if no tests)

        Returns:
            Checkpoint record with commit hash

        Raises:
            subprocess.CalledProcessError: If git commands fail
        """
        logger.info(
            f"Creating checkpoint for {self.task_id} turn {turn} "
            f"(tests: {'pass' if tests_passed else 'fail'}, count: {test_count})"
        )

        # Serialize git operations to prevent index.lock conflicts
        # when multiple tasks share the same worktree.
        checkpoint = self._create_checkpoint_locked(turn, tests_passed, test_count)

        self.checkpoints.append(checkpoint)
        self._save_checkpoints()

        logger.info(
            f"Created checkpoint: {checkpoint.commit_hash[:8]} for turn {turn} "
            f"({len(self.checkpoints)} total)"
        )

        return checkpoint

    def _get_thread_lock(self) -> threading.Lock:
        """Get or create a thread lock for this worktree path.

        Returns a threading.Lock shared by all managers with the same
        resolved worktree path, ensuring threads coordinate before
        acquiring the file lock.

        Returns:
            threading.Lock for this worktree path
        """
        key = str(self.worktree_path.resolve())
        with self._thread_locks_guard:
            if key not in self._thread_locks:
                self._thread_locks[key] = threading.Lock()
            return self._thread_locks[key]

    def _create_checkpoint_locked(
        self,
        turn: int,
        tests_passed: bool,
        test_count: int,
    ) -> Checkpoint:
        """Execute git checkpoint operations under a file-based lock.

        Uses a two-level locking strategy:
        1. threading.Lock - coordinates threads in the same process
        2. fcntl.flock - coordinates across processes (if needed)

        Args:
            turn: Turn number (1-indexed)
            tests_passed: Whether tests passed at this turn
            test_count: Number of tests run

        Returns:
            Checkpoint record with commit hash

        Raises:
            subprocess.CalledProcessError: If git commands fail
        """
        thread_lock = self._get_thread_lock()

        with thread_lock:
            # Ensure lock file parent directory exists
            self._git_lock_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._git_lock_path, "w") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    return self._execute_git_checkpoint(
                        turn, tests_passed, test_count
                    )
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)

    def _execute_git_checkpoint(
        self,
        turn: int,
        tests_passed: bool,
        test_count: int,
    ) -> Checkpoint:
        """Execute the git add/commit/rev-parse sequence.

        This method contains the actual git operations, extracted for clarity.
        It must only be called while holding the worktree git lock.

        Args:
            turn: Turn number (1-indexed)
            tests_passed: Whether tests passed at this turn
            test_count: Number of tests run

        Returns:
            Checkpoint record with commit hash
        """
        # Stage all changes (including untracked files)
        self.git_executor.execute(
            ["git", "add", "-A"],
            cwd=self.worktree_path,
        )

        # Create checkpoint commit message
        status = "pass" if tests_passed else "fail"
        message = f"[guardkit-checkpoint] Turn {turn} complete (tests: {status})"

        # Create commit (allow empty for turns with no changes)
        self.git_executor.execute(
            ["git", "commit", "-m", message, "--allow-empty"],
            cwd=self.worktree_path,
        )

        # Get commit hash
        result = self.git_executor.execute(
            ["git", "rev-parse", "HEAD"],
            cwd=self.worktree_path,
        )
        commit_hash = result.stdout.strip()

        return Checkpoint(
            turn=turn,
            commit_hash=commit_hash,
            timestamp=datetime.now().isoformat(),
            tests_passed=tests_passed,
            test_count=test_count,
            message=message,
        )

    def rollback_to(self, turn: int) -> bool:
        """Rollback worktree to checkpoint at specified turn.

        This method performs a hard reset to the git commit at the specified
        turn, discarding all changes made in subsequent turns.

        Args:
            turn: Turn number to rollback to (1-indexed)

        Returns:
            True if rollback succeeded, False if checkpoint not found

        Raises:
            subprocess.CalledProcessError: If git reset fails
        """
        checkpoint = self._find_checkpoint(turn)
        if not checkpoint:
            logger.warning(f"No checkpoint found for turn {turn}")
            return False

        logger.info(
            f"Rolling back {self.task_id} to turn {turn} "
            f"(commit: {checkpoint.commit_hash[:8]})"
        )

        try:
            # Hard reset to checkpoint commit
            self.git_executor.execute(
                ["git", "reset", "--hard", checkpoint.commit_hash],
                cwd=self.worktree_path,
            )

            # Remove checkpoints after rollback point
            self.checkpoints = [cp for cp in self.checkpoints if cp.turn <= turn]
            self._save_checkpoints()

            logger.info(
                f"Rollback successful to turn {turn}, "
                f"{len(self.checkpoints)} checkpoints remaining"
            )
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Rollback failed: {e}")
            raise

    def should_rollback(self, consecutive_failures: int = 2) -> bool:
        """Detect if rollback is needed based on test failure patterns.

        This method analyzes recent checkpoint history to detect context pollution.
        The primary indicator is consecutive test failures, suggesting accumulated
        broken state.

        Args:
            consecutive_failures: Number of consecutive failures to trigger rollback
                                 (default: 2 per acceptance criteria)

        Returns:
            True if rollback should be triggered, False otherwise
        """
        if len(self.checkpoints) < consecutive_failures:
            return False

        # Check last N checkpoints for consecutive failures
        recent = self.checkpoints[-consecutive_failures:]
        all_failing = all(not cp.tests_passed for cp in recent)

        if all_failing:
            logger.warning(
                f"Context pollution detected: {consecutive_failures} consecutive "
                f"test failures in turns {[cp.turn for cp in recent]}"
            )
            return True

        return False

    def find_last_passing_checkpoint(self) -> Optional[int]:
        """Find the most recent checkpoint with passing tests.

        This method scans checkpoints in reverse order to find the last clean
        state for rollback.

        Returns:
            Turn number of last passing checkpoint, or None if none found
        """
        for checkpoint in reversed(self.checkpoints):
            if checkpoint.tests_passed:
                logger.info(
                    f"Found last passing checkpoint at turn {checkpoint.turn} "
                    f"(commit: {checkpoint.commit_hash[:8]})"
                )
                return checkpoint.turn

        logger.warning("No passing checkpoints found in history")
        return None

    def get_checkpoint(self, turn: int) -> Optional[Checkpoint]:
        """Get checkpoint for specific turn.

        Args:
            turn: Turn number

        Returns:
            Checkpoint if found, None otherwise
        """
        return self._find_checkpoint(turn)

    def get_checkpoint_count(self) -> int:
        """Get total number of checkpoints.

        Returns:
            Checkpoint count
        """
        return len(self.checkpoints)

    def clear_checkpoints(self) -> None:
        """Clear all checkpoints (use with caution).

        This method removes all checkpoint history. Use only for testing or
        when starting fresh.
        """
        logger.warning(f"Clearing all checkpoints for {self.task_id}")
        self.checkpoints = []
        self._save_checkpoints()

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _find_checkpoint(self, turn: int) -> Optional[Checkpoint]:
        """Find checkpoint by turn number.

        Args:
            turn: Turn number

        Returns:
            Checkpoint if found, None otherwise
        """
        for checkpoint in self.checkpoints:
            if checkpoint.turn == turn:
                return checkpoint
        return None

    def _save_checkpoints(self) -> None:
        """Save checkpoint history to JSON file.

        Persists checkpoints to .guardkit/autobuild/{task_id}/checkpoints.json
        for resume capability and audit trail.
        """
        try:
            self._autobuild_dir.mkdir(parents=True, exist_ok=True)

            data = {
                "task_id": self.task_id,
                "checkpoints": [cp.to_dict() for cp in self.checkpoints],
                "last_updated": datetime.now().isoformat(),
            }

            with open(self._checkpoints_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(
                f"Saved {len(self.checkpoints)} checkpoints to {self._checkpoints_file}"
            )

        except Exception as e:
            logger.warning(f"Failed to save checkpoints: {e}")
            # Don't raise - persistence is best-effort

    def _load_checkpoints(self) -> None:
        """Load checkpoint history from JSON file.

        Loads existing checkpoints from .guardkit/autobuild/{task_id}/checkpoints.json
        if available. Used during initialization and resume.
        """
        if not self._checkpoints_file.exists():
            logger.debug(f"No checkpoint file found at {self._checkpoints_file}")
            return

        try:
            with open(self._checkpoints_file, "r") as f:
                data = json.load(f)

            checkpoints_data = data.get("checkpoints", [])
            self.checkpoints = [Checkpoint.from_dict(cp) for cp in checkpoints_data]

            logger.info(
                f"Loaded {len(self.checkpoints)} checkpoints from "
                f"{self._checkpoints_file}"
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in checkpoint file: {e}")
            self.checkpoints = []
        except Exception as e:
            logger.warning(f"Failed to load checkpoints: {e}")
            self.checkpoints = []


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "Checkpoint",
    "WorktreeCheckpointManager",
    "GitCommandExecutor",
    "SubprocessGitExecutor",
]
