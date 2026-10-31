"""State detection module for multi-layered partial work detection.

This module provides lightweight detection functions for identifying work
performed in a worktree even when Player JSON reports are missing.

Detection Layers:
    1. Git-based detection - Detect uncommitted changes via git status/diff
    (The test run through CoachVerifier's hard-coded pytest was removed on
    1 November 2026; ``TestResultsSummary`` stays as the record's shape.)

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
from guardkit.lib.project_git import run_git

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


def detect_git_changes(worktree_path: Path, task_work_scope=None) -> Optional[GitChangesSummary]:
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
    from guardkit.orchestrator.task_work_scope import collect_changes
    changed = collect_changes(task_work_scope)
    return GitChangesSummary(files_modified=changed['modified'], files_added=changed['created'], files_deleted=changed['deleted'])


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
        result = run_git(
            ["diff", "--stat", "HEAD"],
            cwd=worktree_path,
            timeout=DIFF_COMMAND_TIMEOUT_SECONDS,
        )

        if result.returncode != 0:
            # Try diffing against initial commit if HEAD doesn't exist
            result = run_git(
                ["diff", "--stat"],
                cwd=worktree_path,
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


__all__ = [
    "GitChangesSummary",
    "TestResultsSummary",
    "detect_git_changes",
]
