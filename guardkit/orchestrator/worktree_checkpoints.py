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
import re
import shutil
import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Protocol, Tuple

from guardkit.orchestrator.evidence_repos import EvidenceRepo

logger = logging.getLogger(__name__)

# TASK-AB-XREPOEV01: bound sibling-repo git commits. The commit runs while
# holding a cross-process fcntl lock on the shared sibling repo, so an
# unbounded `git add -A`/`commit` (slow disk, network mount, git hang) would
# deadlock every other task that shares that repo. The worktree checkpoint
# itself keeps its legacy no-timeout behaviour.
_EVIDENCE_GIT_TIMEOUT_S: int = 120


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
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """Execute git command with error handling.

        Args:
            command: Git command as list (e.g., ["git", "add", "-A"])
            cwd: Working directory for command execution
            check: Whether to raise on non-zero exit code
            timeout: Optional seconds before the subprocess is killed. None
                means no timeout (legacy worktree behaviour). Set for
                sibling-repo commits, which hold a cross-process fcntl lock
                and must not be able to deadlock the turn (TASK-AB-XREPOEV01).

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
            subprocess.TimeoutExpired: If timeout is set and exceeded
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
        from_prior_run: True if this checkpoint was loaded from a prior
            orchestration session's ``checkpoints.json`` (e.g. on ``[R]esume``).
            Such checkpoints are preserved for forensic inspection but do not
            count toward the consecutive-failures threshold in
            ``should_rollback()``. Always False for checkpoints written by the
            current run. Defaults to False so old JSON files without this
            field deserialise correctly (TASK-FIX-F4A3).
    """

    turn: int
    commit_hash: str
    timestamp: str
    tests_passed: bool
    test_count: int = 0
    message: str = ""
    from_prior_run: bool = False
    # TASK-AB-XREPOEV01: per-declared-sibling-repo checkpoint commit hashes,
    # keyed by repo name (e.g. {"guardkitfactory": "<sha>"}). Empty for
    # worktree-only checkpoints and for checkpoints written before evidence
    # support existed -- the default keeps old checkpoints.json deserialising
    # via ``Checkpoint(**data)``.
    evidence_commits: Dict[str, str] = field(default_factory=dict)

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
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """Execute git command with subprocess.

        Args:
            command: Git command as list
            cwd: Working directory
            check: Raise on non-zero exit
            timeout: Optional seconds before the subprocess is killed
                (None = no timeout, legacy behaviour).

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
            subprocess.TimeoutExpired: If timeout is set and exceeded
        """
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=check,
                timeout=timeout,
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
        evidence_repos: Optional[List[EvidenceRepo]] = None,
    ):
        """Initialize WorktreeCheckpointManager.

        Args:
            worktree_path: Path to git worktree
            task_id: Task identifier
            git_executor: Optional git executor (default: SubprocessGitExecutor)
            evidence_repos: Optional declared sibling repos
                (TASK-AB-XREPOEV01). When provided, every checkpoint also
                commits each repo's working tree so approved sibling-repo work
                is versioned (closes the BDDW-002 hazard: approved factory
                work that was never committed anywhere, one ``git clean`` from
                breaking merged main). Default None -> worktree-only
                checkpoints, unchanged behaviour.
        """
        self.worktree_path = Path(worktree_path)
        self.task_id = task_id
        self.git_executor = git_executor or SubprocessGitExecutor()
        self.evidence_repos: List[EvidenceRepo] = list(evidence_repos or [])
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

        # TASK-AB-XREPOEV01 (AC-004): also commit each declared sibling repo so
        # approved sibling-repo work is versioned, not left as uncommitted
        # working-tree edits. Best-effort and per-repo isolated: a failure in
        # one repo must never abort the worktree checkpoint that already
        # landed.
        evidence_commits = self._checkpoint_evidence_repos(turn, tests_passed)

        return Checkpoint(
            turn=turn,
            commit_hash=commit_hash,
            timestamp=datetime.now().isoformat(),
            tests_passed=tests_passed,
            test_count=test_count,
            message=message,
            evidence_commits=evidence_commits,
        )

    def _checkpoint_evidence_repos(
        self, turn: int, tests_passed: bool
    ) -> Dict[str, str]:
        """Commit each declared sibling repo's working tree at this turn.

        Returns a ``{repo_name: commit_hash}`` map for the repos that were
        successfully committed. Each repo is committed under its own
        ``.guardkit-git.lock`` so parallel features writing to the same
        sibling repo cannot collide on ``index.lock``. Best-effort: any
        per-repo failure is logged and skipped, never raised -- AC-004's
        explicit-disclaim fallback is honoured by logging the gap.
        """
        evidence_commits: Dict[str, str] = {}
        if not self.evidence_repos:
            return evidence_commits

        status = "pass" if tests_passed else "fail"
        message = (
            f"[guardkit-checkpoint] {self.task_id} turn {turn} "
            f"(sibling evidence, tests: {status})"
        )
        for repo in self.evidence_repos:
            try:
                commit = self._commit_one_evidence_repo(repo, message)
                if commit is not None:
                    evidence_commits[repo.name] = commit
                    logger.info(
                        "Checkpointed sibling repo %s at %s (turn %d)",
                        repo.name,
                        commit[:8],
                        turn,
                    )
                else:
                    logger.warning(
                        "Sibling repo %s NOT checkpointed at turn %d "
                        "(no git HEAD / commit failed); its state is "
                        "UNVERSIONED for this turn.",
                        repo.name,
                        turn,
                    )
            except Exception as exc:  # noqa: BLE001 -- never abort the checkpoint
                logger.warning(
                    "Sibling repo %s checkpoint failed at turn %d: %s "
                    "(state UNVERSIONED for this turn).",
                    repo.name,
                    turn,
                    exc,
                )
        return evidence_commits

    def _commit_one_evidence_repo(
        self, repo: EvidenceRepo, message: str
    ) -> Optional[str]:
        """``git add -A && git commit`` one sibling repo under its own lock.

        Returns the new commit hash, or None when the repo is not a usable git
        repository. The commit lands on the repo's CURRENT branch (no branch
        switch -- switching the operator's shared sibling repo is the riskier
        option the task flagged; an additive commit is recoverable, a branch
        switch is disruptive).
        """
        if not repo.root.exists():
            return None

        repo_lock_path = repo.root / ".guardkit-git.lock"
        try:
            repo_lock_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

        with open(repo_lock_path, "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                # Bounded so a hung git cannot hold the cross-process lock
                # indefinitely and stall every task sharing this repo.
                self.git_executor.execute(
                    ["git", "add", "-A"],
                    cwd=repo.root,
                    check=False,
                    timeout=_EVIDENCE_GIT_TIMEOUT_S,
                )
                self.git_executor.execute(
                    ["git", "commit", "-m", message, "--allow-empty"],
                    cwd=repo.root,
                    check=False,
                    timeout=_EVIDENCE_GIT_TIMEOUT_S,
                )
                result = self.git_executor.execute(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo.root,
                    check=False,
                    timeout=_EVIDENCE_GIT_TIMEOUT_S,
                )
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Sibling repo %s git commit timed out after %ds; state "
                    "UNVERSIONED for this turn.",
                    repo.name,
                    _EVIDENCE_GIT_TIMEOUT_S,
                )
                return None
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

        commit = (result.stdout or "").strip()
        return commit or None

    def rollback_to(self, turn: int) -> bool:
        """Rollback worktree to checkpoint at specified turn.

        This method performs a hard reset to the git commit at the specified
        turn, discarding all changes made in subsequent turns. Before the
        reset it snapshots per-turn audit JSONs (``coach_turn_*.json``,
        ``player_turn_*.json``, ``turn_state_turn_*.json``) for turns
        ``> turn`` to ``_rollback_archive/`` so the forensic audit trail of
        the polluted turns survives the reset (TASK-FIX-RBSS AC-3).

        Note:
            This method is **filesystem-only by design**. Resetting the
            Player SDK resume session is the *caller*'s responsibility —
            see ``autobuild.py`` rollback branch which calls
            ``AgentInvoker.set_player_resume_session(None)`` immediately
            after this method returns (TASK-FIX-RBSS AC-1, AC-7). Without
            that caller-side reset the next turn resumes the polluted
            cumulative-authoring memory and re-emits the file claims the
            rollback just deleted, defeating the rollback's purpose.

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
            # TASK-FIX-RBSS AC-3: snapshot per-turn audit JSONs for turns
            # > target_turn before `git reset --hard` discards them. Audit
            # archival is best-effort: a snapshot failure must not block
            # the rollback itself (the SDK-session reset that follows is
            # load-bearing for recovery; archival is forensic hygiene).
            try:
                self._archive_post_target_audit_files(turn)
            except Exception as archive_error:  # noqa: BLE001
                logger.warning(
                    f"[rollback] Audit-trail archive failed (continuing "
                    f"with reset): {archive_error}"
                )

            # Hard reset to checkpoint commit
            self.git_executor.execute(
                ["git", "reset", "--hard", checkpoint.commit_hash],
                cwd=self.worktree_path,
            )

            # TASK-AB-XREPOEV01 (AC-004): reset declared sibling repos to the
            # hash they were committed at in THIS target checkpoint. Guarded:
            # only repos with a recorded hash in the target are reset (we never
            # hard-reset a sibling repo to an unknown state); best-effort so a
            # sibling reset failure cannot break the worktree rollback that
            # already succeeded.
            self._rollback_evidence_repos(checkpoint)

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

    def should_rollback(self, consecutive_failures: int = 3) -> bool:
        """Detect if rollback is needed based on test failure patterns.

        This method analyzes recent checkpoint history to detect context pollution.
        The primary indicator is consecutive test failures, suggesting accumulated
        broken state.

        Checkpoints loaded from a prior orchestration session (``from_prior_run``)
        are excluded — they cannot be evidence of pollution accumulating in the
        current run, and counting them would trigger a spurious context-pollution
        short-circuit on turn 1 of any ``[R]esume`` (TASK-FIX-F4A3).

        Args:
            consecutive_failures: Number of consecutive failures to trigger rollback
                                 (default: 3, allows recovery from incomplete sessions)

        Returns:
            True if rollback should be triggered, False otherwise
        """
        current_run = [cp for cp in self.checkpoints if not cp.from_prior_run]

        if len(current_run) < consecutive_failures:
            return False

        # Check last N current-run checkpoints for consecutive failures
        recent = current_run[-consecutive_failures:]
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

    def _rollback_evidence_repos(self, checkpoint: Checkpoint) -> None:
        """Hard-reset declared sibling repos to their hash in ``checkpoint``.

        Only repos with a recorded ``evidence_commits[name]`` in the target
        checkpoint are reset -- we never hard-reset a shared sibling repo to a
        state we did not record. Best-effort: a sibling reset failure is logged
        and skipped so the (already-completed) worktree rollback stands.

        Repos declared now but absent from the target checkpoint (e.g. the
        checkpoint predates a config change) are surfaced as a WARNING: their
        sibling state is NOT rolled back, which the operator must know.
        """
        if not self.evidence_repos:
            return

        rolled_back: List[str] = []
        not_rolled_back: List[str] = []
        for repo in self.evidence_repos:
            target = checkpoint.evidence_commits.get(repo.name)
            if not target:
                not_rolled_back.append(repo.name)
                logger.warning(
                    "Rollback: sibling repo %s has no recorded commit in the "
                    "target checkpoint (turn %d); its state is NOT rolled back.",
                    repo.name,
                    checkpoint.turn,
                )
                continue
            try:
                self.git_executor.execute(
                    ["git", "reset", "--hard", target],
                    cwd=repo.root,
                    check=False,
                    timeout=_EVIDENCE_GIT_TIMEOUT_S,
                )
                rolled_back.append(repo.name)
                logger.info(
                    "Rollback: reset sibling repo %s to %s (turn %d)",
                    repo.name,
                    target[:8],
                    checkpoint.turn,
                )
            except Exception as exc:  # noqa: BLE001 -- never break the rollback
                not_rolled_back.append(repo.name)
                logger.warning(
                    "Rollback: failed to reset sibling repo %s to %s: %s",
                    repo.name,
                    target[:8],
                    exc,
                )

        # Summary line so an operator diagnosing a worktree/sibling mismatch can
        # see at a glance which repos diverged from the rolled-back worktree.
        if not_rolled_back:
            logger.warning(
                "Rollback turn %d: sibling repos rolled back=%s; NOT rolled "
                "back=%s (worktree and these repos may be inconsistent).",
                checkpoint.turn,
                rolled_back or "[]",
                not_rolled_back,
            )

    # Audit JSONs the rollback wipes when their committing turn is rolled
    # away by ``git reset --hard``. Pattern groups: 1=turn number.
    _AUDIT_FILE_PATTERNS: ClassVar[Tuple[Tuple[str, "re.Pattern[str]"], ...]] = (
        ("coach", re.compile(r"^coach_turn_(\d+)\.json$")),
        ("player", re.compile(r"^player_turn_(\d+)\.json$")),
        ("turn_state", re.compile(r"^turn_state_turn_(\d+)\.json$")),
    )

    def _archive_post_target_audit_files(self, target_turn: int) -> int:
        """Snapshot per-turn audit JSONs for turns > ``target_turn``.

        Copies every ``coach_turn_<N>.json``, ``player_turn_<N>.json`` and
        ``turn_state_turn_<N>.json`` under ``.guardkit/autobuild/<task>/``
        whose turn number is strictly greater than ``target_turn`` into
        ``.guardkit/autobuild/<task>/_rollback_archive/turn_<target>_<ts>/``
        before the caller's ``git reset --hard`` would otherwise destroy
        them. Also writes a defensive ``.gitignore`` inside
        ``_rollback_archive/`` so the archived files self-exclude from any
        future ``git add -A`` checkpoint commit — that prevents subsequent
        rollbacks from recursively wiping prior archives even when the
        consumer project's root ``.gitignore`` does not list the archive
        path (TASK-FIX-RBSS AC-5).

        Audit-trail archival is best-effort. The caller is expected to
        catch any exception and continue with the reset — the SDK-session
        reset that follows is load-bearing; this is forensic hygiene.

        Args:
            target_turn: Rollback target. Files for turns ``> target_turn``
                are archived; the target turn itself is preserved by the
                git reset and does not need archival.

        Returns:
            Number of files archived. Zero is a valid no-op (e.g. test
            fixtures with no per-turn JSONs on disk).
        """
        if not self._autobuild_dir.exists():
            return 0

        rollback_archive_dir = self._autobuild_dir / "_rollback_archive"
        rollback_archive_dir.mkdir(parents=True, exist_ok=True)

        # Defensive in-directory .gitignore so the snapshots are never
        # picked up by `git add -A` in the next checkpoint, regardless of
        # what the project's root .gitignore says. ``!.gitignore`` keeps
        # the marker file itself committable so the directory's intent is
        # discoverable in git history.
        archive_gitignore = rollback_archive_dir / ".gitignore"
        if not archive_gitignore.exists():
            archive_gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")

        timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        snapshot_dir = rollback_archive_dir / f"turn_{target_turn}_{timestamp}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        archived_count = 0
        # Iterate only top-level files in the autobuild dir; we explicitly
        # do NOT descend into _rollback_archive/ so we cannot pick up
        # prior snapshots.
        for entry in self._autobuild_dir.iterdir():
            if not entry.is_file():
                continue
            for _kind, pattern in self._AUDIT_FILE_PATTERNS:
                match = pattern.match(entry.name)
                if not match:
                    continue
                try:
                    file_turn = int(match.group(1))
                except ValueError:
                    break
                if file_turn <= target_turn:
                    break
                try:
                    shutil.copy2(entry, snapshot_dir / entry.name)
                    archived_count += 1
                except OSError as copy_error:
                    logger.warning(
                        f"[rollback] Failed to archive {entry.name}: "
                        f"{copy_error}"
                    )
                break

        logger.info(
            f"[rollback] Archived {archived_count} audit file(s) to "
            f"_rollback_archive/{snapshot_dir.name}/"
        )
        return archived_count

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

            # Anything loaded from disk at session-start is by definition from a
            # prior orchestration session — tag accordingly so the pollution
            # detector excludes them (TASK-FIX-F4A3). The persisted value is
            # ignored: a checkpoint that was "current" in the previous session
            # is "prior" in this one.
            for cp in self.checkpoints:
                cp.from_prior_run = True

            prior_run_count = len(self.checkpoints)
            if prior_run_count > 0:
                logger.info(
                    f"Loaded {prior_run_count} checkpoints from "
                    f"{self._checkpoints_file} "
                    f"(tagged from_prior_run; excluded from pollution detection)"
                )
            else:
                logger.info(
                    f"Loaded 0 checkpoints from {self._checkpoints_file}"
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
