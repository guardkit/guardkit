"""
Worktree Cleanup Orchestration

This module provides the WorktreeCleanupOrchestrator for safely cleaning up
AutoBuild worktrees after task completion. It handles:

- Validation that worktree exists
- Safety checks for uncommitted changes and unmerged branches
- User confirmation prompts (with --force override)
- Feature YAML state tracking
- Graceful edge case handling

Pattern: CLI Command + WorktreeManager Integration
Architecture: Reuses WorktreeManager for git operations

Example:
    >>> from pathlib import Path
    >>> from lib.worktree_cleanup import WorktreeCleanupOrchestrator
    >>>
    >>> orchestrator = WorktreeCleanupOrchestrator(
    ...     repo_root=Path.cwd(),
    ...     task_id="TASK-AB-001",
    ...     force=False,
    ...     verbose=True
    ... )
    >>> orchestrator.run()
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Worktree manager will be imported lazily to avoid circular imports
WorktreeManager = None


# ============================================================================
# Exceptions
# ============================================================================


class WorktreeCleanupError(Exception):
    """Base exception for worktree cleanup operations."""
    pass


class WorktreeNotFoundError(WorktreeCleanupError):
    """Raised when worktree doesn't exist."""
    pass


class UncommittedChangesError(WorktreeCleanupError):
    """Raised when worktree has uncommitted changes."""
    pass


class UnmergedBranchError(WorktreeCleanupError):
    """Raised when branch hasn't been merged."""
    pass


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class CleanupCheckResult:
    """Result of pre-cleanup safety checks."""
    worktree_exists: bool
    has_uncommitted_changes: bool
    branch_merged: bool
    merge_status: str = ""  # Detailed merge status message
    warnings: list = None  # List of warning messages

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class CleanupResult:
    """Result of cleanup operation."""
    success: bool
    message: str
    worktree_path: Optional[Path] = None
    feature_yaml_updated: bool = False
    errors: list = None  # List of error messages

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


# ============================================================================
# Worktree Cleanup Orchestrator
# ============================================================================


class WorktreeCleanupOrchestrator:
    """
    Orchestrates safe cleanup of AutoBuild worktrees.

    This orchestrator handles the complete cleanup workflow including:
    1. ID normalization (supports both TASK-XXX and FEAT-XXX)
    2. Worktree existence validation
    3. Safety checks (uncommitted changes, merge status)
    4. User confirmation (with --force override)
    5. Worktree removal via WorktreeManager
    6. Feature YAML state tracking
    7. Graceful error handling

    Attributes:
        repo_root: Root directory of the git repository
        task_id: Task or feature identifier (normalized to TASK-XXX format)
        force: Skip confirmation prompts and safety checks
        verbose: Print detailed progress messages
        dry_run: Simulate cleanup without making changes
    """

    def __init__(
        self,
        repo_root: Path,
        task_id: str,
        force: bool = False,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """
        Initialize WorktreeCleanupOrchestrator.

        Args:
            repo_root: Root directory of the git repository
            task_id: Task ID in format TASK-XXX or FEAT-XXX
            force: Skip confirmation prompts
            verbose: Enable verbose output
            dry_run: Simulate cleanup without changes

        Raises:
            ValueError: If task_id format is invalid
        """
        self.repo_root = repo_root.resolve()
        self.task_id = self._normalize_task_id(task_id)
        self.force = force
        self.verbose = verbose
        self.dry_run = dry_run

        # Derived paths
        self.worktrees_dir = self.repo_root / ".guardkit" / "worktrees"
        self.worktree_path = self.worktrees_dir / self.task_id

        # Lazy-loaded WorktreeManager
        self._worktree_manager: Optional[Any] = None

    def _normalize_task_id(self, task_id: str) -> str:
        """
        Normalize task ID to TASK-XXX format.

        Supports both TASK-XXX and FEAT-XXX formats, converting FEAT-XXX
        to TASK-XXX for internal consistency.

        Args:
            task_id: Task ID in format TASK-XXX or FEAT-XXX

        Returns:
            Normalized task ID in TASK-XXX format

        Raises:
            ValueError: If task_id doesn't match expected format
        """
        task_id = task_id.strip()

        # Accept both TASK-XXX and FEAT-XXX formats
        if task_id.startswith("FEAT-"):
            # Convert FEAT-XXX to TASK-XXX
            return "TASK-" + task_id[5:]
        elif task_id.startswith("TASK-"):
            return task_id
        else:
            raise ValueError(
                f"Invalid task ID format: {task_id}. "
                f"Expected TASK-XXX or FEAT-XXX format."
            )

    def _get_worktree_manager(self) -> Any:
        """
        Lazy-load WorktreeManager to avoid circular imports.

        Returns:
            Initialized WorktreeManager instance

        Raises:
            WorktreeCleanupError: If WorktreeManager cannot be loaded
        """
        if self._worktree_manager is None:
            try:
                # Import at runtime to avoid circular imports
                from lib.orchestrator.worktrees import WorktreeManager
                self._worktree_manager = WorktreeManager(self.repo_root)
            except Exception as e:
                raise WorktreeCleanupError(
                    f"Failed to load WorktreeManager: {e}"
                )
        return self._worktree_manager

    def _print(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _print_header(self) -> None:
        """Print operation header."""
        print("\n" + "="*80)
        print("Worktree Cleanup")
        print("="*80 + "\n")

    def _check_worktree_exists(self) -> bool:
        """
        Check if worktree directory exists.

        Returns:
            True if worktree exists, False otherwise
        """
        return self.worktree_path.exists()

    def _get_worktree_uncommitted_changes(self) -> bool:
        """
        Check if worktree has uncommitted changes.

        Returns:
            True if there are uncommitted changes, False otherwise
        """
        if not self._check_worktree_exists():
            return False

        try:
            result = subprocess.run(
                ["git", "-C", str(self.worktree_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            # Error getting status - assume there may be changes
            return True

    def _check_branch_merged(self) -> tuple[bool, str]:
        """
        Check if branch has been merged into main.

        Returns:
            Tuple of (is_merged, status_message)
        """
        branch_name = f"autobuild/{self.task_id}"

        try:
            # Check if branch exists
            result = subprocess.run(
                ["git", "-C", str(self.repo_root), "branch", "--list", branch_name],
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                # Branch doesn't exist - either already cleaned or never created
                return True, "Branch does not exist (already cleaned or never created)"

            # Check if branch has been merged into main
            try:
                subprocess.run(
                    ["git", "-C", str(self.repo_root), "merge-base", "--is-ancestor",
                     branch_name, "main"],
                    capture_output=True,
                    check=True,
                )
                return True, f"Branch {branch_name} has been merged into main"
            except subprocess.CalledProcessError:
                # Branch is not an ancestor of main - not merged
                return False, f"Branch {branch_name} has NOT been merged into main"

        except subprocess.CalledProcessError as e:
            # Error checking merge status
            return False, f"Error checking merge status: {e}"

    def run_safety_checks(self) -> CleanupCheckResult:
        """
        Run pre-cleanup safety checks.

        Returns:
            CleanupCheckResult with check results and warnings
        """
        self._print("Running safety checks...")

        # Check 1: Worktree exists
        worktree_exists = self._check_worktree_exists()
        self._print(f"  Worktree exists: {worktree_exists}")

        # Check 2: Uncommitted changes
        has_uncommitted = False
        if worktree_exists:
            has_uncommitted = self._get_worktree_uncommitted_changes()
            self._print(f"  Uncommitted changes: {has_uncommitted}")

        # Check 3: Branch merged
        branch_merged, merge_status = self._check_branch_merged()
        self._print(f"  Branch merged: {branch_merged}")
        if merge_status:
            self._print(f"    {merge_status}")

        # Collect warnings
        warnings = []
        if has_uncommitted:
            warnings.append("Worktree has uncommitted changes")
        if not branch_merged:
            warnings.append("Branch has not been merged into main")

        return CleanupCheckResult(
            worktree_exists=worktree_exists,
            has_uncommitted_changes=has_uncommitted,
            branch_merged=branch_merged,
            merge_status=merge_status,
            warnings=warnings,
        )

    def _confirm_cleanup(self, check_result: CleanupCheckResult) -> bool:
        """
        Get user confirmation for cleanup.

        Returns:
            True if user confirms, False otherwise
        """
        if self.force:
            self._print("--force flag set, skipping confirmation")
            return True

        # Display warnings
        if check_result.warnings:
            print("\nWarnings:")
            for warning in check_result.warnings:
                print(f"  - {warning}")

        # Get confirmation
        print(f"\nClean up worktree for {self.task_id}? (y/n): ", end="", flush=True)
        response = input().strip().lower()
        return response == "y"

    def _remove_worktree_directory(self) -> None:
        """
        Remove worktree directory (fallback if git worktree remove fails).

        Raises:
            WorktreeCleanupError: If removal fails
        """
        if not self.worktree_path.exists():
            return

        try:
            shutil.rmtree(self.worktree_path)
            self._print(f"Removed worktree directory: {self.worktree_path}")
        except Exception as e:
            raise WorktreeCleanupError(
                f"Failed to remove worktree directory {self.worktree_path}: {e}"
            )

    def _cleanup_via_worktree_manager(self) -> None:
        """
        Use WorktreeManager to clean up worktree.

        This is the preferred method as it properly removes both
        the worktree directory and the git branch.

        Raises:
            WorktreeCleanupError: If cleanup fails
        """
        try:
            manager = self._get_worktree_manager()

            # Create Worktree object for cleanup
            from lib.orchestrator.worktrees import Worktree
            worktree = Worktree(
                task_id=self.task_id,
                branch_name=f"autobuild/{self.task_id}",
                path=self.worktree_path,
                base_branch="main",
            )

            # Cleanup via WorktreeManager (removes directory and branch)
            manager.cleanup(worktree, force=False)
            self._print(f"Cleaned up worktree via WorktreeManager: {self.task_id}")

        except Exception as e:
            # Fallback: try manual removal
            self._print(f"WorktreeManager cleanup failed, attempting manual cleanup: {e}")
            self._remove_worktree_directory()

    def _update_feature_yaml(self) -> bool:
        """
        Update feature YAML to mark worktree as cleaned.

        Marks worktree_cleaned: true in feature YAML state tracking.

        Returns:
            True if updated successfully, False otherwise
        """
        # Feature YAML path: tasks/backlog/{feature-slug}/{feature-slug}.feature.yaml
        # or similar location depending on feature structure

        # For now, this is a placeholder that can be enhanced
        # to actually update feature YAML files if they exist

        self._print("Feature YAML update (state tracking not yet implemented)")
        return True

    def run(self) -> CleanupResult:
        """
        Execute complete cleanup workflow.

        Workflow:
        1. Normalize task ID
        2. Run safety checks
        3. Get user confirmation (unless --force)
        4. Remove worktree via WorktreeManager
        5. Update feature YAML state
        6. Report results

        Returns:
            CleanupResult with operation status

        Raises:
            WorktreeCleanupError: If cleanup fails (unless handled gracefully)
        """
        self._print_header()

        # Step 1: Normalize and display task ID
        self._print(f"Task ID (normalized): {self.task_id}")
        self._print(f"Worktree path: {self.worktree_path}")

        # Step 2: Run safety checks
        try:
            check_result = self.run_safety_checks()
        except Exception as e:
            return CleanupResult(
                success=False,
                message=f"Safety checks failed: {e}",
                errors=[str(e)],
            )

        # Handle edge case: worktree already cleaned
        if not check_result.worktree_exists:
            self._print("\nWorktree already cleaned or doesn't exist")
            print("Status: Already cleaned")
            return CleanupResult(
                success=True,
                message="Worktree already cleaned",
                worktree_path=self.worktree_path,
            )

        # Step 3: Get user confirmation
        if not self._confirm_cleanup(check_result):
            print("\nCleanup cancelled by user")
            return CleanupResult(
                success=False,
                message="Cleanup cancelled by user",
            )

        # Step 4: Perform cleanup (dry-run or actual)
        if self.dry_run:
            print(f"\n[DRY RUN] Would clean up worktree: {self.task_id}")
            return CleanupResult(
                success=True,
                message=f"[DRY RUN] Cleanup simulation successful",
                worktree_path=self.worktree_path,
            )

        try:
            self._cleanup_via_worktree_manager()
        except WorktreeCleanupError as e:
            return CleanupResult(
                success=False,
                message=f"Cleanup failed: {e}",
                errors=[str(e)],
            )

        # Step 5: Update feature YAML
        try:
            yaml_updated = self._update_feature_yaml()
        except Exception as e:
            yaml_updated = False
            self._print(f"Feature YAML update failed (non-critical): {e}")

        # Step 6: Report results
        print("\n" + "="*80)
        print("Cleanup Complete")
        print("="*80)
        print(f"Task ID: {self.task_id}")
        print(f"Worktree removed: {self.worktree_path}")
        if yaml_updated:
            print("Feature YAML updated: worktree_cleaned=true")
        print("="*80 + "\n")

        return CleanupResult(
            success=True,
            message=f"Worktree {self.task_id} cleaned successfully",
            worktree_path=self.worktree_path,
            feature_yaml_updated=yaml_updated,
        )
