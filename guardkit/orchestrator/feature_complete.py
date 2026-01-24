"""
FeatureCompleteOrchestrator for parallel task completion.

This module provides the FeatureCompleteOrchestrator class which coordinates
the completion of all tasks within a feature using parallel execution.

Architecture:
    Three-Phase Execution Pattern:
    1. Setup Phase: Load feature, validate tasks
    2. Completion Phase: Complete tasks in parallel
    3. Finalize Phase: Update feature status, generate report

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.feature_complete import FeatureCompleteOrchestrator
    >>>
    >>> orchestrator = FeatureCompleteOrchestrator(repo_root=Path.cwd())
    >>> result = orchestrator.complete_feature("FEAT-A1B2")
    >>> print(result.completed_count)
    12
"""

import asyncio
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureTask,
    FeatureNotFoundError,
)

logger = logging.getLogger(__name__)
console = Console()


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class TaskCompleteResult:
    """
    Result of completing a single task.

    Attributes
    ----------
    task_id : str
        Task identifier
    success : bool
        Whether task completed successfully
    error : Optional[str]
        Error message if failed
    """

    task_id: str
    success: bool
    error: Optional[str] = None


@dataclass
class FeatureCompleteResult:
    """
    Complete result of feature completion orchestration.

    Attributes
    ----------
    feature_id : str
        Feature identifier
    total_tasks : int
        Total number of tasks in feature
    completed_count : int
        Number of tasks successfully completed
    failed_count : int
        Number of tasks that failed
    skipped_count : int
        Number of tasks already completed (skipped)
    results : List[TaskCompleteResult]
        Individual task completion results
    """

    feature_id: str
    total_tasks: int
    completed_count: int
    failed_count: int
    skipped_count: int
    results: List[TaskCompleteResult]


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
    Orchestrates parallel completion of all tasks in a feature.

    This class implements a three-phase execution pattern:
    1. Setup Phase: Load feature, validate tasks
    2. Completion Phase: Complete tasks in parallel
    3. Finalize Phase: Update feature status, generate report

    Key Design Decisions:
    - Parallel execution using asyncio.gather()
    - Error isolation (one task failure doesn't block others)
    - Feature-specific organization (tasks/completed/{date}/{feature-slug}/)
    - Progress reporting with rich console

    Attributes
    ----------
    repo_root : Path
        Repository root directory
    features_dir : Path
        Directory containing feature YAML files
    verbose : bool
        Whether to show detailed output

    Examples
    --------
    >>> orchestrator = FeatureCompleteOrchestrator(repo_root=Path.cwd())
    >>> result = orchestrator.complete_feature("FEAT-A1B2")
    >>> print(f"{result.completed_count}/{result.total_tasks} tasks completed")
    12/12 tasks completed
    """

    def __init__(
        self,
        repo_root: Path,
        features_dir: Optional[Path] = None,
        verbose: bool = False,
    ):
        """
        Initialize FeatureCompleteOrchestrator.

        Parameters
        ----------
        repo_root : Path
            Repository root directory
        features_dir : Optional[Path], optional
            Override features directory (for testing)
        verbose : bool, optional
            Show detailed output (default: False)
        """
        self.repo_root = Path(repo_root).resolve()
        self.features_dir = features_dir or self.repo_root / ".guardkit" / "features"
        self.verbose = verbose

        logger.info(
            f"FeatureCompleteOrchestrator initialized: repo={self.repo_root}, "
            f"verbose={self.verbose}"
        )

    def complete_feature(self, feature_id: str) -> FeatureCompleteResult:
        """
        Execute complete feature completion workflow.

        This is the main entry point for feature completion orchestration.
        It coordinates the three-phase execution pattern: Setup → Complete → Finalize.

        Parameters
        ----------
        feature_id : str
            Feature identifier (e.g., "FEAT-A1B2")

        Returns
        -------
        FeatureCompleteResult
            Complete orchestration result

        Raises
        ------
        FeatureNotFoundError
            If feature file doesn't exist
        FeatureCompleteError
            If critical error occurs

        Examples
        --------
        >>> result = orchestrator.complete_feature("FEAT-A1B2")
        >>> print(result.completed_count)
        12
        """
        logger.info(f"Starting feature completion for {feature_id}")

        try:
            # Phase 1: Setup
            feature = self._setup_phase(feature_id)

            # Phase 2: Completion
            results = self._completion_phase(feature)

            # Phase 3: Finalize
            final_result = self._finalize_phase(feature, results)

            logger.info(
                f"Feature completion complete: {feature_id}, "
                f"completed={final_result.completed_count}/{final_result.total_tasks}"
            )

            return final_result

        except FeatureNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Feature completion failed: {e}", exc_info=True)
            raise FeatureCompleteError(
                f"Failed to complete feature {feature_id}: {e}"
            ) from e

    def _setup_phase(self, feature_id: str) -> Feature:
        """
        Phase 1: Load feature and validate.

        Parameters
        ----------
        feature_id : str
            Feature identifier

        Returns
        -------
        Feature
            Loaded feature

        Raises
        ------
        FeatureNotFoundError
            If feature file not found
        """
        logger.info(f"Phase 1 (Setup): Loading feature {feature_id}")

        # Display setup banner
        console.print(
            Panel(
                f"[bold]Feature Task Completion[/bold]\n\n"
                f"Feature: [cyan]{feature_id}[/cyan]",
                title="GuardKit Feature Complete",
                border_style="blue",
            )
        )

        # Load feature
        feature = FeatureLoader.load_feature(
            feature_id,
            repo_root=self.repo_root,
            features_dir=self.features_dir,
        )

        console.print(f"[green]✓[/green] Loaded feature: {feature.name}")
        console.print(f"  Total tasks: {len(feature.tasks)}")

        # Count pending tasks
        pending_tasks = [t for t in feature.tasks if t.status != "completed"]
        console.print(f"  Pending completion: {len(pending_tasks)}")

        return feature

    def _completion_phase(self, feature: Feature) -> List[TaskCompleteResult]:
        """
        Phase 2: Complete tasks in parallel.

        Parameters
        ----------
        feature : Feature
            Feature to complete

        Returns
        -------
        List[TaskCompleteResult]
            Results for all tasks
        """
        logger.info(f"Phase 2 (Completion): Completing tasks in parallel")

        # Execute async completion
        results = asyncio.run(self._complete_tasks_parallel(feature))

        return results

    async def _complete_tasks_parallel(
        self, feature: Feature
    ) -> List[TaskCompleteResult]:
        """
        Complete all tasks in a feature in parallel using asyncio.

        This method creates parallel execution tasks using asyncio.to_thread()
        to achieve true parallelism with the blocking file operations.
        Tasks are filtered for already-completed cases before parallel execution.

        Parameters
        ----------
        feature : Feature
            Parent feature

        Returns
        -------
        List[TaskCompleteResult]
            Results for all tasks in the feature
        """
        results = []
        pending_tasks = [t for t in feature.tasks if t.status != "completed"]

        if not pending_tasks:
            console.print("[dim]No tasks to complete (all already completed)[/dim]")
            # Return empty list - already completed tasks are skipped
            return results

        console.print(f"\n[bold]Completing {len(pending_tasks)} tasks...[/bold]")

        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task_progress = progress.add_task(
                f"Completing tasks...", total=len(pending_tasks)
            )

            # Create completion coroutines
            tasks_to_execute = [
                asyncio.to_thread(self._complete_single_task, task, feature)
                for task in pending_tasks
            ]

            # Execute in parallel with error isolation
            parallel_results = await asyncio.gather(
                *tasks_to_execute, return_exceptions=True
            )

            # Process results and handle exceptions
            for task, result in zip(pending_tasks, parallel_results):
                if isinstance(result, Exception):
                    error_result = TaskCompleteResult(
                        task_id=task.id,
                        success=False,
                        error=str(result),
                    )
                    results.append(error_result)
                    logger.error(
                        f"Task {task.id} completion failed: {result}", exc_info=result
                    )
                else:
                    results.append(result)

                progress.update(task_progress, advance=1)

        return results

    def _complete_single_task(
        self, task: FeatureTask, feature: Feature
    ) -> TaskCompleteResult:
        """
        Complete a single task (runs in thread).

        This method moves the task file to the completed directory,
        organized under feature-specific folder.

        Parameters
        ----------
        task : FeatureTask
            Task to complete
        feature : Feature
            Parent feature

        Returns
        -------
        TaskCompleteResult
            Completion result
        """
        try:
            feature_slug = self._extract_feature_slug(feature.id)
            date_str = datetime.now().strftime("%Y-%m-%d")

            # Create target directory: tasks/completed/{date}/{feature-slug}/
            target_dir = (
                self.repo_root / "tasks" / "completed" / date_str / feature_slug
            )
            target_dir.mkdir(parents=True, exist_ok=True)

            # Find task file
            task_file = self._find_task_file(task.id)
            if not task_file:
                logger.warning(f"Task file not found: {task.id}")
                return TaskCompleteResult(
                    task_id=task.id,
                    success=False,
                    error="Task file not found",
                )

            # Move task file
            target_file = target_dir / task_file.name
            shutil.move(str(task_file), str(target_file))

            if self.verbose:
                console.print(f"  [green]✓[/green] Completed {task.id}")

            return TaskCompleteResult(
                task_id=task.id,
                success=True,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to complete task {task.id}: {e}", exc_info=True)
            return TaskCompleteResult(
                task_id=task.id,
                success=False,
                error=str(e),
            )

    def _extract_feature_slug(self, feature_id: str) -> str:
        """
        Extract feature slug from feature ID.

        Examples:
        - FEAT-A1B2 → feat-a1b2
        - FEAT-AUTH-001 → feat-auth-001

        Parameters
        ----------
        feature_id : str
            Feature identifier

        Returns
        -------
        str
            Feature slug (lowercase, with hyphens)
        """
        return feature_id.lower()

    def _find_task_file(self, task_id: str) -> Optional[Path]:
        """
        Find task file in standard locations.

        Searches in order:
        1. tasks/in_review/
        2. tasks/in_progress/
        3. tasks/backlog/

        Parameters
        ----------
        task_id : str
            Task identifier

        Returns
        -------
        Optional[Path]
            Path to task file, or None if not found
        """
        search_dirs = ["in_review", "in_progress", "backlog"]

        for dir_name in search_dirs:
            search_dir = self.repo_root / "tasks" / dir_name
            if not search_dir.exists():
                continue

            # Use rglob for recursive search (handles feature subdirectories)
            for task_file in search_dir.rglob(f"{task_id}*.md"):
                logger.debug(f"Found task {task_id} at {task_file}")
                return task_file

        return None

    def _finalize_phase(
        self, feature: Feature, results: List[TaskCompleteResult]
    ) -> FeatureCompleteResult:
        """
        Phase 3: Update feature status and generate report.

        Parameters
        ----------
        feature : Feature
            Feature to finalize
        results : List[TaskCompleteResult]
            Task completion results

        Returns
        -------
        FeatureCompleteResult
            Complete orchestration result
        """
        logger.info(f"Phase 3 (Finalize): Updating feature {feature.id}")

        # Calculate totals
        completed_count = sum(1 for r in results if r.success and r.error is None)
        failed_count = sum(1 for r in results if not r.success)
        skipped_count = len(feature.tasks) - len(
            [t for t in feature.tasks if t.status != "completed"]
        )

        # Display summary
        console.print()
        if failed_count == 0:
            console.print(
                Panel(
                    f"[green]✓ Feature tasks completed successfully[/green]\n\n"
                    f"Feature: [cyan]{feature.id}[/cyan] - {feature.name}\n"
                    f"Completed: {completed_count} tasks\n"
                    f"Skipped: {skipped_count} tasks (already completed)",
                    title="Feature Completion Complete",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[yellow]⚠ Feature completion finished with errors[/yellow]\n\n"
                    f"Feature: [cyan]{feature.id}[/cyan] - {feature.name}\n"
                    f"Completed: {completed_count} tasks\n"
                    f"Failed: {failed_count} tasks\n"
                    f"Skipped: {skipped_count} tasks",
                    title="Feature Completion Complete",
                    border_style="yellow",
                )
            )

        # Display failed tasks if any
        if failed_count > 0 and self.verbose:
            console.print("\n[bold red]Failed Tasks:[/bold red]")
            for result in results:
                if not result.success:
                    console.print(f"  [red]✗[/red] {result.task_id}: {result.error}")

        return FeatureCompleteResult(
            feature_id=feature.id,
            total_tasks=len(feature.tasks),
            completed_count=completed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            results=results,
        )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "FeatureCompleteOrchestrator",
    "FeatureCompleteResult",
    "TaskCompleteResult",
    "FeatureCompleteError",
]
