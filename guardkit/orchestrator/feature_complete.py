"""
Feature completion orchestrator for AutoBuild feature mode.

This module provides the FeatureCompleteOrchestrator class which coordinates
the completion of all tasks in a feature, followed by archival and handoff
instructions for human review.

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.feature_complete import FeatureCompleteOrchestrator
    >>>
    >>> orchestrator = FeatureCompleteOrchestrator(repo_root=Path.cwd())
    >>> result = orchestrator.complete("FEAT-A1B2")
    >>> print(result.status)
    'completed'
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureNotFoundError,
    FeatureValidationError,
)
from guardkit.worktrees import WorktreeManager, Worktree

logger = logging.getLogger(__name__)
console = Console()


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class FeatureCompleteResult:
    """
    Result of feature completion orchestration.

    Attributes
    ----------
    feature_id : str
        Feature identifier
    success : bool
        Whether completion succeeded
    status : str
        Final feature status (completed/failed)
    tasks_completed : int
        Number of completed tasks
    total_tasks : int
        Total number of tasks
    worktree_path : Optional[str]
        Path to preserved worktree
    error : Optional[str]
        Error message if failed
    """

    feature_id: str
    success: bool
    status: str
    tasks_completed: int
    total_tasks: int
    worktree_path: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Exceptions
# ============================================================================


class FeatureCompleteError(Exception):
    """Base exception for feature completion errors."""

    pass


# ============================================================================
# FeatureCompleteOrchestrator
# ============================================================================


class FeatureCompleteOrchestrator:
    """
    Orchestrates feature completion workflow.

    This class implements a four-phase completion pattern:
    1. Validation: Verify feature exists and is ready for completion
    2. Completion: Mark all incomplete tasks as complete (TASK-FC-002)
    3. Archival: Archive feature and cleanup resources (TASK-FC-003)
    4. Handoff: Display handoff instructions for human review (TASK-FC-004)

    Attributes
    ----------
    repo_root : Path
        Repository root directory
    features_dir : Path
        Directory containing feature YAML files
    dry_run : bool
        Whether to simulate without making changes
    force : bool
        Whether to force completion even if tasks incomplete

    Examples
    --------
    >>> orchestrator = FeatureCompleteOrchestrator(repo_root=Path.cwd())
    >>> result = orchestrator.complete("FEAT-A1B2")
    >>> print(result.success)
    True
    """

    def __init__(
        self,
        repo_root: Path,
        features_dir: Optional[Path] = None,
        worktree_manager: Optional[WorktreeManager] = None,
        dry_run: bool = False,
        force: bool = False,
    ):
        """
        Initialize FeatureCompleteOrchestrator.

        Parameters
        ----------
        repo_root : Path
            Repository root directory
        features_dir : Optional[Path], optional
            Override features directory (for testing)
        worktree_manager : Optional[WorktreeManager], optional
            Optional WorktreeManager for DI/testing
        dry_run : bool, optional
            Simulate without making changes (default: False)
        force : bool, optional
            Force completion even if tasks incomplete (default: False)
        """
        self.repo_root = Path(repo_root).resolve()
        self.features_dir = features_dir or self.repo_root / ".guardkit" / "features"
        self.dry_run = dry_run
        self.force = force

        # Initialize dependencies
        self._worktree_manager = worktree_manager or WorktreeManager(
            repo_root=self.repo_root
        )

        logger.info(
            f"FeatureCompleteOrchestrator initialized: repo={self.repo_root}, "
            f"dry_run={self.dry_run}, force={self.force}"
        )

    def complete(self, feature_id: str) -> FeatureCompleteResult:
        """
        Execute complete feature completion workflow.

        This is the main entry point for feature completion. It coordinates
        the four-phase completion pattern: Validation → Completion → Archival → Handoff.

        Parameters
        ----------
        feature_id : str
            Feature identifier (e.g., "FEAT-A1B2")

        Returns
        -------
        FeatureCompleteResult
            Complete completion result

        Raises
        ------
        FeatureNotFoundError
            If feature file doesn't exist
        FeatureValidationError
            If feature fails validation
        FeatureCompleteError
            If critical error occurs

        Examples
        --------
        >>> result = orchestrator.complete("FEAT-A1B2")
        >>> print(result.status)
        'completed'
        """
        logger.info(f"Starting feature completion for {feature_id}")

        try:
            # Phase 1: Validation
            feature, worktree = self._validate_phase(feature_id)

            # Phase 2: Completion (TASK-FC-002 - placeholder)
            self._completion_phase(feature)

            # Phase 3: Archival (TASK-FC-003 - placeholder)
            self._archival_phase(feature, worktree)

            # Phase 4: Handoff (TASK-FC-004)
            self._handoff_phase(feature, worktree)

            # Build result
            result = FeatureCompleteResult(
                feature_id=feature.id,
                success=True,
                status="completed",
                tasks_completed=len(feature.tasks),
                total_tasks=len(feature.tasks),
                worktree_path=str(worktree.path) if worktree else None,
            )

            logger.info(f"Feature completion successful: {feature_id}")
            return result

        except FeatureNotFoundError:
            raise
        except FeatureValidationError:
            raise
        except Exception as e:
            logger.error(f"Feature completion failed: {e}", exc_info=True)
            raise FeatureCompleteError(
                f"Failed to complete feature {feature_id}: {e}"
            ) from e

    def _validate_phase(
        self, feature_id: str
    ) -> tuple[Feature, Optional[Worktree]]:
        """
        Phase 1: Validate feature exists and is ready for completion.

        Parameters
        ----------
        feature_id : str
            Feature identifier

        Returns
        -------
        tuple[Feature, Optional[Worktree]]
            Loaded feature and worktree (if exists)

        Raises
        ------
        FeatureNotFoundError
            If feature file not found
        FeatureValidationError
            If validation fails
        FeatureCompleteError
            If feature not ready for completion
        """
        logger.info(f"Phase 1 (Validation): Validating feature {feature_id}")

        console.print(f"\n[bold cyan]Phase 1:[/bold cyan] Validating feature {feature_id}")

        # Load feature
        feature = FeatureLoader.load_feature(
            feature_id,
            repo_root=self.repo_root,
            features_dir=self.features_dir,
        )

        console.print(f"[green]✓[/green] Loaded feature: {feature.name}")
        console.print(f"  Tasks: {len(feature.tasks)}")
        console.print(f"  Status: {feature.status}")

        # Check if feature is already completed
        if feature.status == "completed" and not self.force:
            console.print("[yellow]⚠[/yellow] Feature already completed")
            if not self.dry_run:
                raise FeatureCompleteError(
                    f"Feature {feature_id} is already completed. Use --force to re-complete."
                )

        # Check if all tasks are completed (unless --force)
        if not self.force:
            incomplete_tasks = [
                task for task in feature.tasks if task.status != "completed"
            ]
            if incomplete_tasks:
                console.print(
                    f"[yellow]⚠[/yellow] {len(incomplete_tasks)} task(s) not completed:"
                )
                for task in incomplete_tasks:
                    console.print(f"  - {task.id}: {task.status}")
                if not self.dry_run:
                    raise FeatureCompleteError(
                        f"Cannot complete feature {feature_id}: {len(incomplete_tasks)} task(s) incomplete. "
                        "Use --force to override."
                    )

        # Find worktree if it exists
        worktree = None
        if feature.execution.worktree_path:
            worktree_path = Path(feature.execution.worktree_path)
            if worktree_path.exists():
                worktree = Worktree(
                    task_id=feature_id,
                    branch_name=f"autobuild/{feature_id}",
                    path=worktree_path,
                    base_branch="main",
                )
                console.print(f"[green]✓[/green] Found worktree: {worktree.path}")
            else:
                console.print("[yellow]⚠[/yellow] Worktree path not found (may have been cleaned up)")

        console.print("[green]✓[/green] Validation complete\n")

        return feature, worktree

    def _completion_phase(self, feature: Feature) -> None:
        """
        Phase 2: Mark all incomplete tasks as complete.

        This is a placeholder for TASK-FC-002 implementation.

        Parameters
        ----------
        feature : Feature
            Feature to complete
        """
        logger.info(f"Phase 2 (Completion): Placeholder for TASK-FC-002")

        console.print("[bold cyan]Phase 2:[/bold cyan] Task Completion")
        console.print("[dim]  → Placeholder for TASK-FC-002[/dim]")
        console.print("[dim]  → Will mark incomplete tasks as complete[/dim]\n")

    def _archival_phase(self, feature: Feature, worktree: Optional[Worktree]) -> None:
        """
        Phase 3: Archive feature and cleanup resources.

        This is a placeholder for TASK-FC-003 implementation.

        Parameters
        ----------
        feature : Feature
            Feature to archive
        worktree : Optional[Worktree]
            Worktree to cleanup (if exists)
        """
        logger.info(f"Phase 3 (Archival): Placeholder for TASK-FC-003")

        console.print("[bold cyan]Phase 3:[/bold cyan] Archival")
        console.print("[dim]  → Placeholder for TASK-FC-003[/dim]")
        console.print("[dim]  → Will archive feature YAML[/dim]")
        console.print("[dim]  → Will cleanup worktree[/dim]\n")

    def _handoff_phase(self, feature: Feature, worktree: Optional[Worktree]) -> None:
        """
        Phase 4: Display handoff instructions for human review.

        Parameters
        ----------
        feature : Feature
            Completed feature
        worktree : Optional[Worktree]
            Worktree (if still exists)
        """
        logger.info(f"Phase 4 (Handoff): Displaying merge instructions")

        console.print("[bold cyan]Phase 4:[/bold cyan] Handoff Instructions\n")

        if worktree:
            self._display_handoff(feature, worktree)
        else:
            console.print("[yellow]⚠[/yellow] Worktree not available for merge instructions")

    def _display_handoff(self, feature: Feature, worktree: Worktree) -> None:
        """
        Display merge instructions for user.

        Shows clear merge instructions including:
        - Branch information (source → target)
        - Worktree location
        - GUI tool instructions (GitKraken, Fork, Tower, Sourcetree)
        - CLI direct merge instructions
        - CLI PR creation instructions
        - Cleanup command

        Parameters
        ----------
        feature : Feature
            Completed feature
        worktree : Worktree
            Worktree containing the merged changes
        """
        console.print()
        console.print(Panel(
            f"[bold cyan]Branch:[/bold cyan] {worktree.branch_name} → {worktree.base_branch}\n"
            f"[bold cyan]Worktree:[/bold cyan] {worktree.path}\n\n"
            f"[bold]Use your preferred tool to complete the merge:[/bold]\n\n"
            f"  [dim]GitKraken/Fork/Tower/Sourcetree:[/dim]\n"
            f"    1. Open the worktree folder\n"
            f"    2. Create PR or merge to {worktree.base_branch}\n\n"
            f"  [dim]Command Line (direct merge):[/dim]\n"
            f"    git checkout {worktree.base_branch}\n"
            f"    git merge --no-ff {worktree.branch_name}\n"
            f"    git push\n\n"
            f"  [dim]Command Line (GitHub PR):[/dim]\n"
            f"    gh pr create --base {worktree.base_branch} --head {worktree.branch_name}\n\n"
            f"[bold yellow]After merge:[/bold yellow]\n"
            f"  guardkit worktree cleanup {feature.id}",
            title="📋 READY FOR MERGE",
            border_style="green"
        ))


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "FeatureCompleteOrchestrator",
    "FeatureCompleteResult",
    "FeatureCompleteError",
]
