"""State detection module for multi-layered partial work detection.

This module provides lightweight detection functions for identifying work
performed in a worktree even when Player JSON reports are missing.

Detection Layers:
    1. Git-based detection - Detect uncommitted changes via git status/diff
    2. Test-based detection - Verify implementation quality via CoachVerifier

Architecture:
    - Uses subprocess with 5-second timeouts for git commands (per arch review)
    - Dataclass pattern for lightweight state containers
    - Works independently or with StateTracker abstraction

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.state_detection import detect_git_changes
    >>>
    >>> changes = detect_git_changes(Path(".guardkit/worktrees/TASK-001"))
    >>> if changes:
    ...     print(f"Found {len(changes.files_modified)} modified files")
    ...     print(f"Found {len(changes.files_added)} new files")
"""

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Constants for timeout handling (per architectural review)
GIT_COMMAND_TIMEOUT_SECONDS = 5
DIFF_COMMAND_TIMEOUT_SECONDS = 10


@dataclass
class GitChangesSummary:
    """Summary of git changes detected in a worktree.

    Attributes:
        files_modified: List of file paths that have been modified
        files_added: List of file paths that are new/untracked
        files_deleted: List of file paths that have been deleted
        diff_stats: Summary of diff statistics (insertions/deletions)
        insertions: Number of lines added
        deletions: Number of lines removed
        timestamp: ISO 8601 timestamp when detection was performed
    """

    files_modified: List[str] = field(default_factory=list)
    files_added: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    diff_stats: str = ""
    insertions: int = 0
    deletions: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def total_files_changed(self) -> int:
        """Total number of files with any changes."""
        return len(self.files_modified) + len(self.files_added) + len(self.files_deleted)

    @property
    def has_changes(self) -> bool:
        """True if any changes were detected."""
        return self.total_files_changed > 0


@dataclass
class TestResultsSummary:
    """Summary of test execution results.

    Attributes:
        tests_run: Whether tests were successfully executed
        tests_passed: Whether all tests passed
        test_count: Number of tests that ran
        passed_count: Number of tests that passed
        failed_count: Number of tests that failed
        output_summary: Truncated test output for context
        timestamp: ISO 8601 timestamp when tests were run
        error: Optional error message if test execution failed
    """

    tests_run: bool = False
    tests_passed: bool = False
    test_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    output_summary: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


def detect_git_changes(worktree_path: Path) -> Optional[GitChangesSummary]:
    """Detect uncommitted changes in a git worktree.

    Uses git status and git diff to detect:
    - Modified files (tracked files with changes)
    - Added files (new/untracked files)
    - Deleted files
    - Diff statistics (insertions/deletions)

    Args:
        worktree_path: Path to the git worktree directory

    Returns:
        GitChangesSummary if changes detected, None if no changes or error

    Raises:
        No exceptions - errors are logged and None is returned

    Example:
        >>> changes = detect_git_changes(Path(".guardkit/worktrees/TASK-001"))
        >>> if changes:
        ...     print(f"Modified: {changes.files_modified}")
        ...     print(f"Added: {changes.files_added}")
        ...     print(f"Insertions: {changes.insertions}, Deletions: {changes.deletions}")
    """
    worktree_path = Path(worktree_path)

    if not worktree_path.exists():
        logger.warning(f"Worktree path does not exist: {worktree_path}")
        return None

    try:
        # Get git status in porcelain format (machine-readable)
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )

        if status_result.returncode != 0:
            logger.warning(
                f"git status failed: {status_result.stderr.strip()}"
            )
            return None

        # Use rstrip() to preserve leading whitespace (important for git status format)
        status_output = status_result.stdout.rstrip()
        if not status_output:
            logger.debug(f"No changes detected in {worktree_path}")
            return None

        # Parse status output
        files_modified, files_added, files_deleted = _parse_git_status(status_output)

        # Get diff statistics
        diff_stats, insertions, deletions = _get_diff_stats(worktree_path)

        summary = GitChangesSummary(
            files_modified=files_modified,
            files_added=files_added,
            files_deleted=files_deleted,
            diff_stats=diff_stats,
            insertions=insertions,
            deletions=deletions,
            timestamp=datetime.now().isoformat(),
        )

        logger.info(
            f"Git detection: {summary.total_files_changed} files changed "
            f"(+{summary.insertions}/-{summary.deletions})"
        )

        return summary

    except subprocess.TimeoutExpired:
        logger.error(
            f"git status timed out after {GIT_COMMAND_TIMEOUT_SECONDS}s "
            f"in {worktree_path}"
        )
        return None
    except FileNotFoundError:
        logger.error("git command not found - is git installed?")
        return None
    except Exception as e:
        logger.error(f"Git detection failed: {e}", exc_info=True)
        return None


def _parse_git_status(status_output: str) -> tuple[List[str], List[str], List[str]]:
    """Parse git status porcelain output into file lists.

    Git status porcelain format:
    - XY PATH
    - X = index status, Y = work tree status
    - ?? = untracked, M = modified, A = added, D = deleted

    Args:
        status_output: Raw output from git status --porcelain

    Returns:
        Tuple of (files_modified, files_added, files_deleted)
    """
    files_modified: List[str] = []
    files_added: List[str] = []
    files_deleted: List[str] = []

    for line in status_output.split("\n"):
        if not line or len(line) < 4:
            continue

        # Status is first 2 chars, then space, then path
        status = line[:2]
        file_path = line[3:]

        # Handle renamed files (format: "R  old_path -> new_path")
        if " -> " in file_path:
            file_path = file_path.split(" -> ")[-1]

        # Untracked files
        if status == "??":
            files_added.append(file_path)
        # Modified in working tree or index
        elif "M" in status:
            files_modified.append(file_path)
        # Added to index
        elif "A" in status:
            files_added.append(file_path)
        # Deleted
        elif "D" in status:
            files_deleted.append(file_path)
        # Renamed (tracked as modified in new location)
        elif "R" in status:
            files_modified.append(file_path)

    return files_modified, files_added, files_deleted


def _get_diff_stats(worktree_path: Path) -> tuple[str, int, int]:
    """Get diff statistics (insertions/deletions) for worktree.

    Args:
        worktree_path: Path to git worktree

    Returns:
        Tuple of (diff_stats_output, insertions, deletions)
    """
    try:
        # Get diff stats against HEAD (or initial if no HEAD)
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=DIFF_COMMAND_TIMEOUT_SECONDS,
        )

        if result.returncode != 0:
            # Try diffing against initial commit if HEAD doesn't exist
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=DIFF_COMMAND_TIMEOUT_SECONDS,
            )

        diff_output = result.stdout.strip()
        insertions, deletions = _parse_diff_stats(diff_output)

        return diff_output, insertions, deletions

    except subprocess.TimeoutExpired:
        logger.warning(
            f"git diff timed out after {DIFF_COMMAND_TIMEOUT_SECONDS}s"
        )
        return "", 0, 0
    except Exception as e:
        logger.warning(f"Failed to get diff stats: {e}")
        return "", 0, 0


def _parse_diff_stats(diff_output: str) -> tuple[int, int]:
    """Parse insertions and deletions from git diff --stat output.

    The last line of git diff --stat looks like:
    "3 files changed, 42 insertions(+), 5 deletions(-)"

    Args:
        diff_output: Raw output from git diff --stat

    Returns:
        Tuple of (insertions, deletions)
    """
    insertions = 0
    deletions = 0

    if not diff_output:
        return insertions, deletions

    # Get the last line which has the summary
    lines = diff_output.strip().split("\n")
    if not lines:
        return insertions, deletions

    summary_line = lines[-1].lower()

    # Parse insertions
    import re

    ins_match = re.search(r"(\d+)\s+insertion", summary_line)
    if ins_match:
        insertions = int(ins_match.group(1))

    # Parse deletions
    del_match = re.search(r"(\d+)\s+deletion", summary_line)
    if del_match:
        deletions = int(del_match.group(1))

    return insertions, deletions


def detect_test_results(
    worktree_path: Path,
    task_id: str = "",
    turn: int = 0,
    test_paths: list[str] | None = None,
) -> Optional[TestResultsSummary]:
    """Detect test results by running tests in the worktree.

    Uses the CoachVerifier infrastructure to run tests and capture results.
    This provides independent verification of implementation quality.

    Args:
        worktree_path: Path to the git worktree directory
        task_id: Optional task identifier for logging
        turn: Optional turn number for logging
        test_paths: Optional list of test file/directory paths to scope
            the test run. When provided, pytest runs only against these
            paths instead of the entire worktree.

    Returns:
        TestResultsSummary if tests could be run, None on error

    Example:
        >>> results = detect_test_results(
        ...     Path(".guardkit/worktrees/TASK-001"),
        ...     task_id="TASK-001",
        ...     turn=2,
        ... )
        >>> if results and results.tests_run:
        ...     print(f"Tests {'passed' if results.tests_passed else 'failed'}")
        ...     print(f"{results.passed_count}/{results.test_count} passing")
    """
    worktree_path = Path(worktree_path)

    if not worktree_path.exists():
        logger.warning(f"Worktree path does not exist: {worktree_path}")
        return None

    try:
        # Import CoachVerifier for test execution
        from guardkit.orchestrator.coach_verification import CoachVerifier

        # Create verifier and run tests
        verifier = CoachVerifier(worktree_path)
        test_result = verifier._run_tests(test_paths=test_paths)

        # Parse results
        passed_count = test_result.test_count if test_result.passed else 0
        failed_count = 0 if test_result.passed else max(1, test_result.test_count)

        # Truncate output for summary
        output_summary = test_result.output[:500] if test_result.output else ""

        summary = TestResultsSummary(
            tests_run=test_result.test_count > 0,
            tests_passed=test_result.passed,
            test_count=test_result.test_count,
            passed_count=passed_count,
            failed_count=failed_count,
            output_summary=output_summary,
            timestamp=datetime.now().isoformat(),
            error=None,
        )

        logger.info(
            f"Test detection ({task_id} turn {turn}): "
            f"{summary.test_count} tests, "
            f"{'passed' if summary.tests_passed else 'failed'}"
        )

        return summary

    except ImportError as e:
        logger.warning(f"Could not import CoachVerifier: {e}")
        return TestResultsSummary(
            tests_run=False,
            tests_passed=False,
            test_count=0,
            passed_count=0,
            failed_count=0,
            output_summary="",
            timestamp=datetime.now().isoformat(),
            error=f"Import error: {e}",
        )
    except Exception as e:
        logger.warning(f"Test detection failed: {e}")
        return TestResultsSummary(
            tests_run=False,
            tests_passed=False,
            test_count=0,
            passed_count=0,
            failed_count=0,
            output_summary="",
            timestamp=datetime.now().isoformat(),
            error=str(e),
        )


__all__ = [
    "GitChangesSummary",
    "TestResultsSummary",
    "detect_git_changes",
    "detect_test_results",
]
