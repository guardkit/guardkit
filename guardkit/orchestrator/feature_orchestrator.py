"""
FeatureOrchestrator for multi-task wave execution in AutoBuild.

This module provides the FeatureOrchestrator class which coordinates the execution
of multiple tasks within a feature using wave-based dependency ordering. It creates
a single shared worktree for all tasks in a feature and reuses the existing
AutoBuildOrchestrator for individual task execution.

Architecture:
    Three-Phase Execution Pattern:
    1. Setup Phase: Load feature, validate tasks, create shared worktree
    2. Wave Phase: Execute tasks wave by wave, respecting dependencies
    3. Finalize Phase: Update feature status, preserve worktree for review

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
    >>>
    >>> orchestrator = FeatureOrchestrator(repo_root=Path.cwd())
    >>> result = orchestrator.orchestrate("FEAT-A1B2")
    >>> print(result.status)
    'completed'
"""

import asyncio
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, OrchestrationResult
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureTask,
    FeatureNotFoundError,
    FeatureValidationError,
)
from guardkit.tasks.task_loader import TaskLoader
from guardkit.worktrees import WorktreeManager, Worktree, WorktreeCreationError
from guardkit.cli.display import WaveProgressDisplay

logger = logging.getLogger(__name__)
console = Console()


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class TaskExecutionResult:
    """
    Result of executing a single task within a feature.

    Attributes
    ----------
    task_id : str
        Task identifier
    success : bool
        Whether task succeeded
    total_turns : int
        Number of turns executed
    final_decision : str
        Final orchestration decision
    error : Optional[str]
        Error message if failed
    recovery_count : int
        Number of state recovery attempts (default: 0)
    """

    task_id: str
    success: bool
    total_turns: int
    final_decision: str
    error: Optional[str] = None
    recovery_count: int = 0  # Number of state recovery attempts


@dataclass
class WaveExecutionResult:
    """
    Result of executing a wave of tasks.

    Attributes
    ----------
    wave_number : int
        Wave number (1-indexed)
    task_ids : List[str]
        Task IDs in this wave
    results : List[TaskExecutionResult]
        Results for each task
    all_succeeded : bool
        Whether all tasks in wave succeeded
    """

    wave_number: int
    task_ids: List[str]
    results: List[TaskExecutionResult]
    all_succeeded: bool


@dataclass
class FeatureOrchestrationResult:
    """
    Complete result of feature orchestration.

    Attributes
    ----------
    feature_id : str
        Feature identifier
    success : bool
        Whether all tasks succeeded
    status : str
        Final feature status
    total_tasks : int
        Total number of tasks
    tasks_completed : int
        Number of completed tasks
    tasks_failed : int
        Number of failed tasks
    wave_results : List[WaveExecutionResult]
        Results for each wave
    worktree : Worktree
        Shared worktree (preserved for review)
    error : Optional[str]
        Error message if failed
    """

    feature_id: str
    success: bool
    status: Literal["completed", "failed", "paused"]
    total_tasks: int
    tasks_completed: int
    tasks_failed: int
    wave_results: List[WaveExecutionResult]
    worktree: Worktree
    error: Optional[str] = None


# ============================================================================
# Exceptions
# ============================================================================


class FeatureOrchestrationError(Exception):
    """Base exception for feature orchestration errors."""

    pass


class WaveExecutionError(FeatureOrchestrationError):
    """Raised when a wave fails and stop_on_failure is True."""

    pass


class DependencyError(FeatureOrchestrationError):
    """Raised when task dependencies cannot be satisfied."""

    pass


# ============================================================================
# FeatureOrchestrator
# ============================================================================


class FeatureOrchestrator:
    """
    Orchestrates multi-task feature execution with wave-based dependency ordering.

    This class implements a three-phase execution pattern:
    1. Setup Phase: Load feature, validate tasks, create shared worktree
    2. Wave Phase: Execute tasks wave by wave, respecting dependencies
    3. Finalize Phase: Update feature status, preserve worktree for review

    Key Design Decisions:
    - Single shared worktree per feature (not per task)
    - Reuses AutoBuildOrchestrator for individual task execution
    - Updates feature YAML after each task completes
    - Supports stop-on-failure or continue-on-failure modes

    Attributes
    ----------
    repo_root : Path
        Repository root directory
    max_turns : int
        Maximum turns per task
    stop_on_failure : bool
        Whether to stop on first task failure
    resume : bool
        Whether to resume from saved state
    fresh : bool
        Whether to start fresh (ignore saved state)
    verbose : bool
        Whether to show detailed output
    features_dir : Path
        Directory containing feature YAML files

    Examples
    --------
    >>> orchestrator = FeatureOrchestrator(repo_root=Path.cwd())
    >>> result = orchestrator.orchestrate("FEAT-A1B2")
    >>> print(result.success)
    True
    """

    def __init__(
        self,
        repo_root: Path,
        max_turns: int = 5,
        stop_on_failure: bool = True,
        resume: bool = False,
        fresh: bool = False,
        verbose: bool = False,
        features_dir: Optional[Path] = None,
        worktree_manager: Optional[WorktreeManager] = None,
        quiet: bool = False,
        sdk_timeout: Optional[int] = None,
        enable_pre_loop: Optional[bool] = None,
    ):
        """
        Initialize FeatureOrchestrator.

        Parameters
        ----------
        repo_root : Path
            Repository root directory
        max_turns : int, optional
            Maximum turns per task (default: 5)
        stop_on_failure : bool, optional
            Stop on first task failure (default: True)
        resume : bool, optional
            Resume from saved state (default: False)
        fresh : bool, optional
            Start fresh, ignoring saved state (default: False)
        verbose : bool, optional
            Show detailed output (default: False)
        features_dir : Optional[Path], optional
            Override features directory (for testing)
        worktree_manager : Optional[WorktreeManager], optional
            Optional WorktreeManager for DI/testing
        quiet : bool, optional
            Suppress progress display (default: False)
        sdk_timeout : Optional[int], optional
            SDK timeout in seconds (60-3600). If None, uses feature YAML or task defaults.
        enable_pre_loop : Optional[bool], optional
            Enable/disable pre-loop quality gates. If None, uses cascade:
            task frontmatter > feature YAML > default (True).

        Raises
        ------
        ValueError
            If max_turns < 1 or if both resume and fresh are True
        """
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")

        if resume and fresh:
            raise ValueError("Cannot use both --resume and --fresh flags together")

        self.repo_root = Path(repo_root).resolve()
        self.max_turns = max_turns
        self.stop_on_failure = stop_on_failure
        self.resume = resume
        self.fresh = fresh
        self.verbose = verbose
        self.quiet = quiet
        self.sdk_timeout = sdk_timeout
        self.enable_pre_loop = enable_pre_loop
        self.features_dir = features_dir or self.repo_root / ".guardkit" / "features"

        # Initialize dependencies
        self._worktree_manager = worktree_manager or WorktreeManager(
            repo_root=self.repo_root
        )

        # Wave progress display (initialized during setup phase)
        self._wave_display: Optional[WaveProgressDisplay] = None

        logger.info(
            f"FeatureOrchestrator initialized: repo={self.repo_root}, "
            f"max_turns={self.max_turns}, stop_on_failure={self.stop_on_failure}, "
            f"resume={self.resume}, fresh={self.fresh}, enable_pre_loop={self.enable_pre_loop}"
        )

    def orchestrate(
        self,
        feature_id: str,
        base_branch: str = "main",
        specific_task: Optional[str] = None,
    ) -> FeatureOrchestrationResult:
        """
        Execute complete feature orchestration workflow.

        This is the main entry point for feature orchestration. It coordinates
        the three-phase execution pattern: Setup → Waves → Finalize.

        Parameters
        ----------
        feature_id : str
            Feature identifier (e.g., "FEAT-A1B2")
        base_branch : str, optional
            Branch to create worktree from (default: "main")
        specific_task : Optional[str], optional
            If provided, only execute this specific task

        Returns
        -------
        FeatureOrchestrationResult
            Complete orchestration result

        Raises
        ------
        FeatureNotFoundError
            If feature file doesn't exist
        FeatureValidationError
            If feature fails validation
        FeatureOrchestrationError
            If critical error occurs

        Examples
        --------
        >>> result = orchestrator.orchestrate("FEAT-A1B2")
        >>> print(result.status)
        'completed'
        >>>
        >>> # Run specific task only
        >>> result = orchestrator.orchestrate("FEAT-A1B2", specific_task="TASK-001")
        """
        logger.info(f"Starting feature orchestration for {feature_id}")

        try:
            # Phase 1: Setup
            feature, worktree = self._setup_phase(feature_id, base_branch)

            # Phase 2: Wave Execution
            if specific_task:
                # Execute single task mode
                wave_results = self._execute_single_task(
                    feature, worktree, specific_task
                )
            else:
                # Execute all tasks wave by wave
                wave_results = self._wave_phase(feature, worktree)

            # Phase 3: Finalize
            result = self._finalize_phase(feature, wave_results, worktree)

            logger.info(
                f"Feature orchestration complete: {feature_id}, "
                f"status={result.status}, completed={result.tasks_completed}/{result.total_tasks}"
            )

            return result

        except FeatureNotFoundError:
            raise
        except FeatureValidationError:
            raise
        except Exception as e:
            logger.error(f"Feature orchestration failed: {e}", exc_info=True)
            raise FeatureOrchestrationError(
                f"Failed to orchestrate feature {feature_id}: {e}"
            ) from e

    def _setup_phase(
        self,
        feature_id: str,
        base_branch: str,
    ) -> tuple[Feature, Worktree]:
        """
        Phase 1: Load feature, validate, create shared worktree.

        Parameters
        ----------
        feature_id : str
            Feature identifier
        base_branch : str
            Branch to create worktree from

        Returns
        -------
        tuple[Feature, Worktree]
            Loaded feature and created worktree

        Raises
        ------
        FeatureNotFoundError
            If feature file not found
        FeatureValidationError
            If validation fails
        WorktreeCreationError
            If worktree creation fails
        """
        logger.info(f"Phase 1 (Setup): Loading feature {feature_id}")

        # Display setup banner
        mode_text = (
            "[yellow]Fresh Start[/yellow]" if self.fresh else
            "[yellow]Resuming[/yellow]" if self.resume else
            "Starting"
        )
        console.print(
            Panel(
                f"[bold]AutoBuild Feature Orchestration[/bold]\n\n"
                f"Feature: [cyan]{feature_id}[/cyan]\n"
                f"Max Turns: {self.max_turns}\n"
                f"Stop on Failure: {self.stop_on_failure}\n"
                f"Mode: {mode_text}",
                title="GuardKit AutoBuild",
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
        console.print(f"  Tasks: {len(feature.tasks)}")
        console.print(f"  Waves: {len(feature.orchestration.parallel_groups)}")

        # Validate feature
        errors = FeatureLoader.validate_feature(feature, self.repo_root)
        if errors:
            error_msg = "\n".join(f"  - {e}" for e in errors)
            raise FeatureValidationError(
                f"Feature validation failed for {feature_id}:\n{error_msg}"
            )

        console.print("[green]✓[/green] Feature validation passed")

        # Initialize wave progress display
        if not self.quiet:
            self._wave_display = WaveProgressDisplay(
                total_waves=len(feature.orchestration.parallel_groups),
                verbose=self.verbose,
            )

        # Handle fresh start
        if self.fresh:
            if FeatureLoader.is_incomplete(feature):
                console.print("[yellow]⚠[/yellow] Clearing previous incomplete state")
                self._clean_state(feature)
            return self._create_new_worktree(feature, feature_id, base_branch)

        # Check for incomplete state
        if FeatureLoader.is_incomplete(feature):
            resume_point = FeatureLoader.get_resume_point(feature)

            if self.resume:
                # Explicit resume flag - proceed with resume
                console.print(
                    f"[yellow]⟳[/yellow] Resuming from incomplete state"
                )
                console.print(
                    f"  Completed tasks: {len(resume_point['completed_tasks'])}"
                )
                console.print(
                    f"  Pending tasks: {len(resume_point['pending_tasks'])}"
                )
                if resume_point['task_id']:
                    console.print(
                        f"  In-progress task: {resume_point['task_id']} "
                        f"(turn {resume_point['turn']})"
                    )

                # Reuse existing worktree if available
                if resume_point['worktree_path']:
                    worktree_path = Path(resume_point['worktree_path'])
                    if worktree_path.exists():
                        console.print(
                            f"[green]✓[/green] Using existing worktree: {worktree_path}"
                        )
                        worktree = Worktree(
                            task_id=feature_id,
                            branch_name=f"autobuild/{feature_id}",
                            path=worktree_path,
                            base_branch=base_branch,
                        )
                        return feature, worktree

                # Worktree not found, create new but keep state
                console.print("[yellow]⚠[/yellow] Previous worktree not found, creating new one")
                return self._create_new_worktree(feature, feature_id, base_branch)
            else:
                # No explicit flag - prompt user
                should_resume = self._prompt_resume(feature, resume_point)
                if should_resume:
                    self.resume = True  # Set flag for wave phase
                    if resume_point['worktree_path']:
                        worktree_path = Path(resume_point['worktree_path'])
                        if worktree_path.exists():
                            console.print(
                                f"[green]✓[/green] Using existing worktree: {worktree_path}"
                            )
                            worktree = Worktree(
                                task_id=feature_id,
                                branch_name=f"autobuild/{feature_id}",
                                path=worktree_path,
                                base_branch=base_branch,
                            )
                            return feature, worktree
                    return self._create_new_worktree(feature, feature_id, base_branch)
                else:
                    # User chose fresh start
                    console.print("[yellow]⚠[/yellow] Starting fresh, clearing previous state")
                    self._clean_state(feature)
                    return self._create_new_worktree(feature, feature_id, base_branch)

        # No incomplete state, start fresh
        return self._create_new_worktree(feature, feature_id, base_branch)

    def _create_new_worktree(
        self,
        feature: Feature,
        feature_id: str,
        base_branch: str,
    ) -> tuple[Feature, Worktree]:
        """
        Create a new worktree for feature execution.

        Parameters
        ----------
        feature : Feature
            Feature being executed
        feature_id : str
            Feature identifier
        base_branch : str
            Branch to create worktree from

        Returns
        -------
        tuple[Feature, Worktree]
            Feature and created worktree
        """
        try:
            worktree = self._worktree_manager.create(
                task_id=feature_id,
                base_branch=base_branch,
            )
            console.print(f"[green]✓[/green] Created shared worktree: {worktree.path}")
        except WorktreeCreationError as e:
            raise FeatureOrchestrationError(
                f"Failed to create worktree for {feature_id}: {e}"
            ) from e

        # Copy task files to worktree
        self._copy_tasks_to_worktree(feature, worktree)

        # Update feature with worktree path and start time
        feature.status = "in_progress"
        feature.execution.started_at = datetime.now().isoformat()
        feature.execution.worktree_path = str(worktree.path)
        feature.execution.last_updated = datetime.now().isoformat()
        FeatureLoader.save_feature(feature, self.repo_root)

        return feature, worktree

    def _copy_tasks_to_worktree(
        self,
        feature: Feature,
        worktree: Worktree,
    ) -> None:
        """
        Copy feature's task markdown files to worktree.

        This ensures TaskStateBridge can find task files in the worktree when
        running ensure_design_approved_state(). Task files are copied from the
        main repository's tasks/backlog/ directory to preserve them even if
        they're not yet committed.

        Parameters
        ----------
        feature : Feature
            Feature being orchestrated
        worktree : Worktree
            Created worktree instance

        Notes
        -----
        - Uses shutil.copy() for simple file copying (metadata preservation not needed)
        - Skips files that already exist (idempotency for committed tasks)
        - Logs warnings on copy failures but doesn't raise (error recovery pattern)
        - Discovers feature directory name from first task's file_path
        """
        if not feature.tasks:
            logger.debug("No tasks to copy to worktree")
            return

        # Extract feature directory from first task's file_path
        # Example: tasks/backlog/feature-build-sdk-coordination/TASK-FBSDK-001.md
        # -> feature-build-sdk-coordination
        first_task = feature.tasks[0]
        if not first_task.file_path:
            logger.warning(
                f"Cannot copy tasks: First task {first_task.id} has no file_path"
            )
            return

        task_file_path = Path(first_task.file_path)

        # Find "tasks" and "backlog" in the path parts
        # Example: /path/to/repo/tasks/backlog/feature-name/TASK-001.md
        parts = task_file_path.parts
        try:
            tasks_idx = parts.index("tasks")
            if tasks_idx + 1 < len(parts) and parts[tasks_idx + 1] == "backlog":
                if tasks_idx + 2 < len(parts):
                    feature_dir = parts[tasks_idx + 2]
                else:
                    logger.warning(
                        f"Cannot copy tasks: Missing feature directory in path: {task_file_path}"
                    )
                    return
            else:
                logger.warning(
                    f"Cannot copy tasks: Expected 'backlog' after 'tasks': {task_file_path}"
                )
                return
        except ValueError:
            logger.warning(
                f"Cannot copy tasks: 'tasks' directory not found in path: {task_file_path}"
            )
            return
        logger.debug(f"Detected feature directory: {feature_dir}")

        # Source: main repo's tasks/backlog/{feature_dir}/
        src_dir = self.repo_root / "tasks" / "backlog" / feature_dir

        # Destination: worktree's tasks/backlog/ (flat structure)
        dst_dir = worktree.path / "tasks" / "backlog"
        dst_dir.mkdir(parents=True, exist_ok=True)

        # Copy each task file
        copied_count = 0
        skipped_count = 0
        error_count = 0

        for task in feature.tasks:
            # Find task file in main repo
            task_pattern = f"{task.id}*.md"
            matching_files = list(src_dir.glob(task_pattern))

            if not matching_files:
                logger.warning(
                    f"Task file not found in {src_dir}: {task_pattern}"
                )
                error_count += 1
                continue

            for task_file in matching_files:
                dst_file = dst_dir / task_file.name

                # Skip if already exists (idempotency)
                if dst_file.exists():
                    logger.debug(
                        f"Skipping existing file in worktree: {task_file.name}"
                    )
                    skipped_count += 1
                    continue

                # Copy file (use copy() instead of copy2(), no metadata needed)
                try:
                    shutil.copy(task_file, dst_file)
                    logger.info(f"Copied task file to worktree: {task_file.name}")
                    copied_count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to copy {task_file.name} to worktree: {e}"
                    )
                    error_count += 1

        # Log summary
        if copied_count > 0:
            console.print(
                f"[green]✓[/green] Copied {copied_count} task file(s) to worktree"
            )
        if skipped_count > 0:
            logger.debug(f"Skipped {skipped_count} existing file(s)")
        if error_count > 0:
            logger.warning(
                f"Failed to copy {error_count} task file(s) (see logs for details)"
            )

    def _create_stub_implementation_plan(
        self,
        task_id: str,
        worktree_path: Path,
        enable_pre_loop: bool = False,
    ) -> Path:
        """
        Create stub implementation plan for feature task.

        This method generates a minimal stub plan when pre-loop is disabled
        for tasks created via /feature-plan. The stub directs implementers
        to the task file for detailed specifications.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-DM-001")
        worktree_path : Path
            Path to the worktree
        enable_pre_loop : bool, optional
            Whether pre-loop was enabled (default: False)

        Returns
        -------
        Path
            Path to the created stub plan

        Raises
        ------
        Exception
            If task cannot be loaded or stub cannot be written

        Example
        -------
        >>> orchestrator = FeatureOrchestrator()
        >>> plan_path = orchestrator._create_stub_implementation_plan(
        ...     "TASK-DM-001",
        ...     Path("/repo/.guardkit/worktrees/FEAT-XXX"),
        ...     enable_pre_loop=False
        ... )
        >>> print(plan_path)
        /repo/.guardkit/worktrees/FEAT-XXX/.claude/task-plans/TASK-DM-001-implementation-plan.md
        """
        from guardkit.orchestrator.paths import TaskArtifactPaths

        # Get preferred plan path (primary location)
        plan_path = TaskArtifactPaths.preferred_plan_path(task_id, worktree_path)

        # Skip if plan already exists (idempotency)
        if plan_path.exists():
            logger.debug(f"Stub plan already exists at {plan_path}, skipping creation")
            return plan_path

        # Load task to get title
        try:
            task_data = TaskLoader.load_task(task_id, self.repo_root)
            title = task_data.get("frontmatter", {}).get("title", "No title")
        except Exception as e:
            logger.warning(
                f"Could not load task {task_id} for stub generation: {e}. "
                "Using default title."
            )
            title = "Feature task"

        # Generate stub content
        timestamp = datetime.now().isoformat()
        stub_content = f"""# Implementation Plan: {task_id}

## Task
{title}

## Plan Status
**Auto-generated stub** - Pre-loop was skipped for this feature task.
Generated: {timestamp}

## Implementation
Follow acceptance criteria in task file.

## Notes
This plan was auto-generated because the task was created via /feature-plan
with pre-loop disabled (enable_pre_loop={enable_pre_loop}).
The detailed specifications are in the task markdown file.
"""

        # Ensure directory exists
        TaskArtifactPaths.ensure_plan_dir(worktree_path)

        # Write stub
        plan_path.write_text(stub_content, encoding="utf-8")
        logger.info(f"Created stub implementation plan: {plan_path}")

        return plan_path

    def _prompt_resume(
        self,
        feature: Feature,
        resume_point: Dict[str, Any],
    ) -> bool:
        """
        Prompt user to resume or start fresh.

        Parameters
        ----------
        feature : Feature
            Feature with incomplete state
        resume_point : Dict[str, Any]
            Resume point information

        Returns
        -------
        bool
            True to resume, False to start fresh
        """
        console.print()
        console.print(
            Panel(
                f"[yellow]Incomplete Execution Detected[/yellow]\n\n"
                f"Feature: [cyan]{feature.id}[/cyan] - {feature.name}\n"
                f"Last updated: {feature.execution.last_updated or 'Unknown'}\n"
                f"Completed tasks: {len(resume_point['completed_tasks'])}/{len(feature.tasks)}\n"
                f"Current wave: {resume_point['wave']}\n"
                + (
                    f"In-progress task: {resume_point['task_id']} (turn {resume_point['turn']})\n"
                    if resume_point['task_id']
                    else ""
                ),
                title="Resume Available",
                border_style="yellow",
            )
        )

        console.print("\nOptions:")
        console.print("  [R]esume - Continue from where you left off")
        console.print("  [F]resh  - Start over from the beginning")
        console.print()

        try:
            import sys
            if sys.stdin.isatty():
                choice = input("Your choice [R/f]: ").strip().lower() or "r"
                return choice != "f"
            else:
                # Non-interactive mode, default to resume
                console.print("[dim]Non-interactive mode, defaulting to resume[/dim]")
                return True
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled[/yellow]")
            raise FeatureOrchestrationError("User cancelled resume prompt")

    def _clean_state(self, feature: Feature) -> None:
        """
        Clean up feature state for a fresh start.

        Parameters
        ----------
        feature : Feature
            Feature to clean
        """
        # Remove existing worktree if it exists
        if feature.execution.worktree_path:
            worktree_path = Path(feature.execution.worktree_path)
            if worktree_path.exists():
                try:
                    # Create a Worktree object for cleanup
                    worktree_to_cleanup = Worktree(
                        task_id=feature.id,
                        branch_name=f"autobuild/{feature.id}",
                        path=worktree_path,
                        base_branch="main",
                    )
                    self._worktree_manager.cleanup(worktree_to_cleanup, force=True)
                    console.print(
                        f"[green]✓[/green] Cleaned up previous worktree: {worktree_path}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to cleanup worktree: {e}")
                    console.print(
                        f"[yellow]⚠[/yellow] Could not cleanup worktree: {e}"
                    )

        # Reset feature state
        FeatureLoader.reset_state(feature)
        FeatureLoader.save_feature(feature, self.repo_root)
        console.print("[green]✓[/green] Reset feature state")

    def _wave_phase(
        self,
        feature: Feature,
        worktree: Worktree,
    ) -> List[WaveExecutionResult]:
        """
        Phase 2: Execute tasks wave by wave respecting dependencies.

        Parameters
        ----------
        feature : Feature
            Feature to execute
        worktree : Worktree
            Shared worktree

        Returns
        -------
        List[WaveExecutionResult]
            Results for each wave
        """
        logger.info(f"Phase 2 (Waves): Executing {len(feature.orchestration.parallel_groups)} waves")
        wave_results = []

        console.print()
        console.print("[bold]Starting Wave Execution[/bold]")

        for wave_number, task_ids in enumerate(
            feature.orchestration.parallel_groups, 1
        ):
            # Check dependencies satisfied
            for task_id in task_ids:
                task = FeatureLoader.find_task(feature, task_id)
                if task and not self._dependencies_satisfied(task, feature):
                    raise DependencyError(
                        f"Task {task_id} has unsatisfied dependencies: {task.dependencies}"
                    )

            # Display wave start via progress display
            if self._wave_display:
                self._wave_display.start_wave(wave_number, task_ids)
            else:
                # Fallback to basic display
                console.print()
                console.print(
                    f"[bold cyan]Wave {wave_number}/{len(feature.orchestration.parallel_groups)}[/bold cyan]: "
                    f"{', '.join(task_ids)}"
                )

            wave_result = self._execute_wave(
                wave_number, task_ids, feature, worktree
            )
            wave_results.append(wave_result)

            # Display wave completion via progress display
            passed = sum(1 for r in wave_result.results if r.success)
            failed = len(wave_result.results) - passed
            skipped = sum(1 for r in wave_result.results if r.final_decision == "skipped")
            recovered = sum(1 for r in wave_result.results if r.recovery_count > 0)

            if self._wave_display:
                self._wave_display.complete_wave(wave_number, passed, failed, skipped, recovered)
            else:
                # Fallback to basic display
                status = "[green]✓ PASSED[/green]" if wave_result.all_succeeded else "[red]✗ FAILED[/red]"
                console.print(f"  Wave {wave_number} {status}: {passed} passed, {failed} failed")

            # Check for stop-on-failure
            if not wave_result.all_succeeded and self.stop_on_failure:
                console.print(
                    "[yellow]⚠[/yellow] Stopping execution (stop_on_failure=True)"
                )
                break

        return wave_results

    async def _execute_wave_parallel(
        self,
        wave_number: int,
        task_ids: List[str],
        feature: Feature,
        worktree: Worktree,
    ) -> List[TaskExecutionResult]:
        """
        Execute all tasks in a wave in parallel using asyncio.

        This method creates parallel execution tasks using asyncio.to_thread()
        to achieve true parallelism with the blocking AutoBuildOrchestrator.
        Tasks are filtered for already-completed and dependency-failed cases
        before parallel execution.

        Parameters
        ----------
        wave_number : int
            Wave number (1-indexed)
        task_ids : List[str]
            Task IDs to execute in parallel
        feature : Feature
            Parent feature
        worktree : Worktree
            Shared worktree

        Returns
        -------
        List[TaskExecutionResult]
            Results for all tasks in the wave
        """
        results = []
        tasks_to_execute = []
        task_id_mapping = []  # Track which task_id corresponds to which async task

        for task_id in task_ids:
            task = FeatureLoader.find_task(feature, task_id)
            if not task:
                results.append(
                    self._create_error_result(
                        task_id,
                        Exception(f"Task not found in feature: {task_id}")
                    )
                )
                continue

            # Skip already completed tasks (for resume)
            if task.status == "completed":
                if self._wave_display:
                    self._wave_display.update_task_status(
                        task_id, "skipped", "already completed",
                        turns=task.turns_completed, decision="already_completed"
                    )
                else:
                    console.print(f"  [dim]⏭ Skipping {task_id} (already completed)[/dim]")
                results.append(
                    TaskExecutionResult(
                        task_id=task_id,
                        success=True,
                        total_turns=task.turns_completed,
                        final_decision="already_completed",
                    )
                )
                continue

            # Skip tasks whose dependencies failed
            if not self._dependencies_satisfied(task, feature):
                if self._wave_display:
                    self._wave_display.update_task_status(
                        task_id, "skipped", "dependency failed"
                    )
                else:
                    console.print(
                        f"  [yellow]⏭ Skipping {task_id} (dependency failed)[/yellow]"
                    )
                task.status = "skipped"
                self._update_feature(feature, task_id, None, wave_number)
                results.append(
                    TaskExecutionResult(
                        task_id=task_id,
                        success=False,
                        total_turns=0,
                        final_decision="skipped",
                        error="Dependency failed",
                    )
                )
                continue

            # Mark task as started for resume tracking
            self._update_task_started(feature, task_id)

            # Display task start
            if self._wave_display:
                self._wave_display.update_task_status(
                    task_id, "in_progress", f"Executing: {task.name}"
                )
            else:
                console.print(f"  [cyan]▶[/cyan] Executing {task_id}: {task.name}")

            # Add to parallel execution queue
            tasks_to_execute.append(
                asyncio.to_thread(self._execute_task, task, feature, worktree)
            )
            task_id_mapping.append(task_id)

        # Execute all tasks in parallel if any
        if tasks_to_execute:
            parallel_results = await asyncio.gather(*tasks_to_execute, return_exceptions=True)

            # Process results and handle exceptions
            for task_id, result in zip(task_id_mapping, parallel_results):
                if isinstance(result, Exception):
                    error_result = self._create_error_result(task_id, result)
                    results.append(error_result)

                    # Update task status in display
                    if self._wave_display:
                        self._wave_display.update_task_status(
                            task_id, "failed", "error",
                            turns=0, decision="error"
                        )

                    # Update feature with error result
                    self._update_feature(feature, task_id, error_result, wave_number)
                else:
                    results.append(result)

                    # Update task status in display
                    if self._wave_display:
                        status = "success" if result.success else "failed"
                        self._wave_display.update_task_status(
                            task_id, status, result.final_decision,
                            turns=result.total_turns, decision=result.final_decision
                        )

                    # Update feature with result
                    self._update_feature(feature, task_id, result, wave_number)

        return results

    def _execute_wave(
        self,
        wave_number: int,
        task_ids: List[str],
        feature: Feature,
        worktree: Worktree,
    ) -> WaveExecutionResult:
        """
        Execute all tasks in a single wave in parallel.

        This method delegates to _execute_wave_parallel() for parallel task
        execution using asyncio. It preserves all existing display logic and
        stop-on-failure behavior.

        Parameters
        ----------
        wave_number : int
            Wave number (1-indexed)
        task_ids : List[str]
            Task IDs to execute
        feature : Feature
            Parent feature
        worktree : Worktree
            Shared worktree

        Returns
        -------
        WaveExecutionResult
            Results for this wave
        """
        # Update current wave tracking
        feature.execution.current_wave = wave_number
        feature.execution.last_updated = datetime.now().isoformat()
        FeatureLoader.save_feature(feature, self.repo_root)

        # Execute tasks in parallel
        results = asyncio.run(
            self._execute_wave_parallel(wave_number, task_ids, feature, worktree)
        )

        # Check for stop-on-failure AFTER all parallel tasks complete
        all_succeeded = all(r.success for r in results)

        # Mark wave as completed if all tasks succeeded
        if all_succeeded:
            self._mark_wave_completed(feature, wave_number)

        return WaveExecutionResult(
            wave_number=wave_number,
            task_ids=task_ids,
            results=results,
            all_succeeded=all_succeeded,
        )

    def _resolve_enable_pre_loop(
        self,
        feature: Feature,
        task_data: Dict[str, Any],
    ) -> bool:
        """
        Resolve enable_pre_loop with cascade priority.

        Priority (highest to lowest):
        1. CLI flag (self.enable_pre_loop)
        2. Task frontmatter (autobuild.enable_pre_loop)
        3. Feature YAML (autobuild.enable_pre_loop via feature config)
        4. Default (True)

        Parameters
        ----------
        feature : Feature
            Parent feature
        task_data : Dict[str, Any]
            Task data from TaskLoader

        Returns
        -------
        bool
            Resolved enable_pre_loop value
        """
        # 1. CLI flag (highest priority)
        if self.enable_pre_loop is not None:
            logger.debug(f"enable_pre_loop from CLI: {self.enable_pre_loop}")
            return self.enable_pre_loop

        # 2. Task frontmatter
        task_frontmatter = task_data.get("frontmatter", {})
        task_autobuild = task_frontmatter.get("autobuild", {})
        if "enable_pre_loop" in task_autobuild:
            value = task_autobuild["enable_pre_loop"]
            logger.debug(f"enable_pre_loop from task frontmatter: {value}")
            return value

        # 3. Feature YAML (check feature autobuild config if it exists)
        # Feature may have autobuild_config attribute with enable_pre_loop
        feature_autobuild = getattr(feature, "autobuild_config", None) or {}
        if "enable_pre_loop" in feature_autobuild:
            value = feature_autobuild["enable_pre_loop"]
            logger.debug(f"enable_pre_loop from feature YAML: {value}")
            return value

        # 4. Default: False for feature-build (feature tasks have detailed specs from feature-plan)
        logger.debug("enable_pre_loop using default for feature-build: False")
        return False

    def _execute_task(
        self,
        task: FeatureTask,
        feature: Feature,
        worktree: Worktree,
    ) -> TaskExecutionResult:
        """
        Execute single task using AutoBuildOrchestrator with shared worktree.

        Parameters
        ----------
        task : FeatureTask
            Task to execute
        feature : Feature
            Parent feature
        worktree : Worktree
            Shared worktree

        Returns
        -------
        TaskExecutionResult
            Execution result
        """
        try:
            # Load task data from markdown file
            task_data = TaskLoader.load_task(task.id, repo_root=self.repo_root)

            # Resolve SDK timeout: CLI > task frontmatter > default (1200)
            effective_sdk_timeout = self.sdk_timeout
            if effective_sdk_timeout is None:
                # Try task frontmatter autobuild.sdk_timeout
                # Note: TaskLoader returns frontmatter as nested dict, not at top level
                task_frontmatter = task_data.get("frontmatter", {})
                task_autobuild = task_frontmatter.get("autobuild", {})
                effective_sdk_timeout = task_autobuild.get("sdk_timeout", 1200)

            # Resolve enable_pre_loop: CLI > task frontmatter > feature YAML > default (False for feature-build)
            effective_enable_pre_loop = self._resolve_enable_pre_loop(feature, task_data)
            if effective_enable_pre_loop:
                logger.info(f"Task {task.id}: enable_pre_loop=True (pre-loop design phase will run)")
            else:
                logger.info(f"Task {task.id}: Pre-loop skipped (enable_pre_loop=False)")

            # Create AutoBuildOrchestrator with existing worktree
            task_orchestrator = AutoBuildOrchestrator(
                repo_root=self.repo_root,
                max_turns=self.max_turns,
                resume=False,  # Each task starts fresh in feature mode
                existing_worktree=worktree,  # Pass shared worktree
                worktree_manager=self._worktree_manager,
                sdk_timeout=effective_sdk_timeout,
                enable_pre_loop=effective_enable_pre_loop,
            )

            # Execute task orchestration
            result = task_orchestrator.orchestrate(
                task_id=task.id,
                requirements=task_data["requirements"],
                acceptance_criteria=task_data["acceptance_criteria"],
                task_file_path=task_data.get("file_path"),
            )

            status_icon = "[green]✓[/green]" if result.success else "[red]✗[/red]"
            console.print(
                f"    {status_icon} {task.id}: {result.final_decision} "
                f"({result.total_turns} turns)"
            )

            return TaskExecutionResult(
                task_id=task.id,
                success=result.success,
                total_turns=result.total_turns,
                final_decision=result.final_decision,
                error=result.error,
                recovery_count=result.recovery_count,
            )

        except Exception as e:
            console.print(f"    [red]✗[/red] {task.id}: Error - {e}")
            return TaskExecutionResult(
                task_id=task.id,
                success=False,
                total_turns=0,
                final_decision="error",
                error=str(e),
            )

    def _execute_single_task(
        self,
        feature: Feature,
        worktree: Worktree,
        task_id: str,
    ) -> List[WaveExecutionResult]:
        """
        Execute a single specific task (--task option).

        Parameters
        ----------
        feature : Feature
            Feature containing the task
        worktree : Worktree
            Shared worktree
        task_id : str
            Task ID to execute

        Returns
        -------
        List[WaveExecutionResult]
            Single-element list with the task result
        """
        task = FeatureLoader.find_task(feature, task_id)
        if not task:
            raise FeatureOrchestrationError(
                f"Task {task_id} not found in feature {feature.id}"
            )

        console.print(f"\n[bold]Single Task Mode:[/bold] {task_id}")

        result = self._execute_task(task, feature, worktree)
        self._update_feature(feature, task_id, result)

        return [
            WaveExecutionResult(
                wave_number=1,
                task_ids=[task_id],
                results=[result],
                all_succeeded=result.success,
            )
        ]

    def _create_error_result(self, task_id: str, error: Exception) -> TaskExecutionResult:
        """
        Create TaskExecutionResult from exception.

        Parameters
        ----------
        task_id : str
            Task identifier
        error : Exception
            Exception that occurred

        Returns
        -------
        TaskExecutionResult
            Error result
        """
        return TaskExecutionResult(
            task_id=task_id,
            success=False,
            total_turns=0,
            final_decision="error",
            error=str(error),
        )

    def _finalize_phase(
        self,
        feature: Feature,
        wave_results: List[WaveExecutionResult],
        worktree: Worktree,
    ) -> FeatureOrchestrationResult:
        """
        Phase 3: Update feature status and preserve worktree.

        Parameters
        ----------
        feature : Feature
            Feature to finalize
        wave_results : List[WaveExecutionResult]
            Results from wave execution
        worktree : Worktree
            Shared worktree

        Returns
        -------
        FeatureOrchestrationResult
            Complete orchestration result
        """
        logger.info(f"Phase 3 (Finalize): Updating feature {feature.id}")

        # Calculate totals
        tasks_completed = sum(
            1
            for wave in wave_results
            for r in wave.results
            if r.success
        )
        tasks_failed = sum(
            1
            for wave in wave_results
            for r in wave.results
            if not r.success
        )
        total_turns = sum(
            r.total_turns
            for wave in wave_results
            for r in wave.results
        )

        # Determine final status
        final_status: Literal["completed", "failed", "paused"]
        if tasks_failed == 0 and tasks_completed == len(feature.tasks):
            final_status = "completed"
            success = True
        elif tasks_failed > 0:
            final_status = "failed"
            success = False
        else:
            final_status = "paused"  # Partial completion (resume mode)
            success = False

        # Update feature
        feature.status = final_status
        feature.execution.completed_at = datetime.now().isoformat()
        feature.execution.total_turns = total_turns
        feature.execution.tasks_completed = tasks_completed
        feature.execution.tasks_failed = tasks_failed
        FeatureLoader.save_feature(feature, self.repo_root)

        # Preserve worktree for human review
        self._worktree_manager.preserve_on_failure(worktree)

        # Display summary
        self._display_summary(feature, wave_results, worktree, final_status)

        return FeatureOrchestrationResult(
            feature_id=feature.id,
            success=success,
            status=final_status,
            total_tasks=len(feature.tasks),
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            wave_results=wave_results,
            worktree=worktree,
            error=None if success else f"{tasks_failed} task(s) failed",
        )

    def _dependencies_satisfied(
        self,
        task: FeatureTask,
        feature: Feature,
    ) -> bool:
        """
        Check if all dependencies for a task are satisfied.

        Parameters
        ----------
        task : FeatureTask
            Task to check
        feature : Feature
            Parent feature

        Returns
        -------
        bool
            True if all dependencies completed successfully
        """
        for dep_id in task.dependencies:
            dep_task = FeatureLoader.find_task(feature, dep_id)
            if dep_task and dep_task.status != "completed":
                return False
        return True

    def _update_feature(
        self,
        feature: Feature,
        task_id: str,
        result: Optional[TaskExecutionResult],
        wave_number: Optional[int] = None,
    ) -> None:
        """
        Update task status in feature after execution.

        Parameters
        ----------
        feature : Feature
            Feature to update
        task_id : str
            Task ID to update
        result : Optional[TaskExecutionResult]
            Execution result (None for skipped tasks)
        wave_number : Optional[int]
            Current wave number (1-indexed)
        """
        task = FeatureLoader.find_task(feature, task_id)
        if not task:
            return

        if result:
            task.status = "completed" if result.success else "failed"
            task.turns_completed = result.total_turns
            task.current_turn = 0  # Reset current turn on completion
            task.completed_at = datetime.now().isoformat()
            task.result = {
                "total_turns": result.total_turns,
                "final_decision": result.final_decision,
                "error": result.error,
            }

        # Update execution counters
        feature.execution.tasks_completed = sum(
            1 for t in feature.tasks if t.status == "completed"
        )
        feature.execution.tasks_failed = sum(
            1 for t in feature.tasks if t.status == "failed"
        )

        # Update wave tracking
        if wave_number is not None:
            feature.execution.current_wave = wave_number

        # Update timestamp
        feature.execution.last_updated = datetime.now().isoformat()

        FeatureLoader.save_feature(feature, self.repo_root)

    def _update_task_started(
        self,
        feature: Feature,
        task_id: str,
    ) -> None:
        """
        Mark a task as started (in_progress).

        Parameters
        ----------
        feature : Feature
            Feature containing the task
        task_id : str
            Task ID to mark as started
        """
        task = FeatureLoader.find_task(feature, task_id)
        if not task:
            return

        task.status = "in_progress"
        task.started_at = datetime.now().isoformat()
        task.current_turn = 1  # Starting first turn
        feature.execution.last_updated = datetime.now().isoformat()

        FeatureLoader.save_feature(feature, self.repo_root)

    def _mark_wave_completed(
        self,
        feature: Feature,
        wave_number: int,
    ) -> None:
        """
        Mark a wave as completed.

        Parameters
        ----------
        feature : Feature
            Feature to update
        wave_number : int
            Wave number that completed (1-indexed)
        """
        if wave_number not in feature.execution.completed_waves:
            feature.execution.completed_waves.append(wave_number)
        feature.execution.last_updated = datetime.now().isoformat()

        FeatureLoader.save_feature(feature, self.repo_root)

    def _display_summary(
        self,
        feature: Feature,
        wave_results: List[WaveExecutionResult],
        worktree: Worktree,
        status: str,
    ) -> None:
        """
        Display final orchestration summary.

        Parameters
        ----------
        feature : Feature
            Completed feature
        wave_results : List[WaveExecutionResult]
            Execution results
        worktree : Worktree
            Shared worktree
        status : str
            Final status
        """
        # Use wave display for final summary if available
        if self._wave_display:
            self._wave_display.render_final_summary(
                feature_id=feature.id,
                feature_name=feature.name,
                status=status,
                total_tasks=len(feature.tasks),
                tasks_completed=feature.execution.tasks_completed,
                tasks_failed=feature.execution.tasks_failed,
                total_turns=feature.execution.total_turns,
                worktree_path=str(worktree.path),
            )
            return

        # Fallback to basic display
        console.print()

        if status == "completed":
            console.print(
                Panel(
                    f"[green]✓ Feature completed successfully[/green]\n\n"
                    f"Feature: [cyan]{feature.id}[/cyan] - {feature.name}\n"
                    f"Tasks: {len(feature.tasks)} completed\n"
                    f"Waves: {len(wave_results)}\n"
                    f"Total Turns: {feature.execution.total_turns}\n"
                    f"Worktree: [cyan]{worktree.path}[/cyan]",
                    title="Feature Orchestration Complete",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[red]✗ Feature execution failed[/red]\n\n"
                    f"Feature: [cyan]{feature.id}[/cyan] - {feature.name}\n"
                    f"Completed: {feature.execution.tasks_completed}/{len(feature.tasks)}\n"
                    f"Failed: {feature.execution.tasks_failed}\n"
                    f"Worktree preserved at: [cyan]{worktree.path}[/cyan]",
                    title="Feature Orchestration Failed",
                    border_style="red",
                )
            )

        # Display task summary table
        if self.verbose:
            console.print("\n[bold]Task Summary:[/bold]\n")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Task", style="cyan", width=20)
            table.add_column("Status", width=12)
            table.add_column("Turns", width=8)
            table.add_column("Decision", width=20)

            for task in feature.tasks:
                status_style = (
                    "green" if task.status == "completed"
                    else "red" if task.status == "failed"
                    else "yellow" if task.status == "skipped"
                    else "dim"
                )
                status_text = f"[{status_style}]{task.status.upper()}[/{status_style}]"
                turns = task.result.get("total_turns", "-") if task.result else "-"
                decision = task.result.get("final_decision", "-") if task.result else "-"

                table.add_row(task.id, status_text, str(turns), decision)

            console.print(table)

        # Next steps
        console.print("\n[bold]Next Steps:[/bold]")
        if status == "completed":
            console.print(f"  1. Review changes: cd {worktree.path}")
            console.print("  2. View diff: git diff main")
            console.print(f"  3. Merge if approved: git checkout main && git merge autobuild/{feature.id}")
            console.print(f"  4. Cleanup: guardkit worktree cleanup {feature.id}")
        else:
            console.print(f"  1. Review failed tasks: cd {worktree.path}")
            console.print(f"  2. Check feature status: guardkit autobuild status {feature.id}")
            console.print(f"  3. Resume after fixes: guardkit autobuild feature {feature.id} --resume")

    def _archive_phase(self, feature: Feature) -> None:
        """
        Archive feature folder after completion.

        Moves the feature folder from tasks/backlog/{slug}/ to
        tasks/completed/{date}/{slug}/ and updates feature YAML with
        archival metadata.

        Parameters
        ----------
        feature : Feature
            Completed feature to archive

        Notes
        -----
        - Handles missing folder gracefully (already archived or moved)
        - Creates dated subdirectory in tasks/completed/
        - Updates feature status to 'awaiting_merge'
        - Records archival timestamp and location
        - Tracks completion statistics (tasks_completed, tasks_failed)
        """
        logger.info(f"Archiving feature {feature.id}")
        console.print("\n[bold]Phase 4 (Archive):[/bold] Moving feature folder...")

        # Detect feature slug from tasks
        slug = self._detect_feature_slug(feature)

        # Generate today's date for archival path
        today = datetime.now().strftime("%Y-%m-%d")

        # Source and destination paths
        src = self.repo_root / "tasks" / "backlog" / slug
        dst = self.repo_root / "tasks" / "completed" / today / slug

        # Move folder if it exists
        if src.exists():
            try:
                # Create parent directory
                dst.parent.mkdir(parents=True, exist_ok=True)

                # Move folder
                shutil.move(str(src), str(dst))
                console.print(
                    f"  [green]✓[/green] Moved to: {dst.relative_to(self.repo_root)}"
                )
                logger.info(f"Moved feature folder from {src} to {dst}")
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Failed to move folder: {e}")
                logger.warning(f"Failed to move feature folder: {e}")
        else:
            console.print(
                f"  [dim]⏭ Folder already archived or not found: {src.relative_to(self.repo_root)}[/dim]"
            )
            logger.debug(f"Feature folder not found (already archived?): {src}")

        # Update feature YAML
        feature.status = "awaiting_merge"
        feature.execution.archived_at = datetime.now().isoformat()
        feature.execution.archived_to = str(dst.relative_to(self.repo_root))
        feature.execution.tasks_completed = sum(
            1 for t in feature.tasks if t.status == "completed"
        )
        feature.execution.tasks_failed = sum(
            1 for t in feature.tasks if t.status == "failed"
        )

        FeatureLoader.save_feature(feature, self.repo_root)
        console.print("[green]✓[/green] Updated feature YAML with archival metadata")
        logger.info(f"Updated feature YAML with archival metadata")

    def _detect_feature_slug(self, feature: Feature) -> str:
        """
        Detect feature slug from task file paths.

        Extracts the feature directory name (slug) from the first task's
        file_path. The slug is the directory name under tasks/backlog/.

        Parameters
        ----------
        feature : Feature
            Feature to detect slug from

        Returns
        -------
        str
            Feature slug (directory name)

        Raises
        ------
        ValueError
            If slug cannot be detected from task paths

        Example
        -------
        >>> # Task file_path: tasks/backlog/dark-mode/TASK-DM-001.md
        >>> slug = orchestrator._detect_feature_slug(feature)
        >>> print(slug)
        'dark-mode'
        """
        if not feature.tasks:
            raise ValueError(
                f"Cannot detect feature slug: No tasks in feature {feature.id}"
            )

        # Get first task's file_path
        first_task = feature.tasks[0]
        if not first_task.file_path:
            raise ValueError(
                f"Cannot detect feature slug: First task {first_task.id} has no file_path"
            )

        # Convert to Path for parsing
        task_file_path = Path(first_task.file_path)
        parts = task_file_path.parts

        # Find "tasks" and "backlog" in the path
        # Example: /path/to/repo/tasks/backlog/feature-name/TASK-001.md
        try:
            tasks_idx = parts.index("tasks")
            if (
                tasks_idx + 1 < len(parts)
                and parts[tasks_idx + 1] == "backlog"
                and tasks_idx + 2 < len(parts)
            ):
                slug = parts[tasks_idx + 2]
                logger.debug(f"Detected feature slug: {slug}")
                return slug
            else:
                raise ValueError(
                    f"Expected 'backlog' after 'tasks' in path: {task_file_path}"
                )
        except (ValueError, IndexError) as e:
            raise ValueError(
                f"Cannot detect feature slug from task path: {task_file_path}\n"
                f"Expected format: tasks/backlog/feature-slug/TASK-XXX.md\n"
                f"Error: {e}"
            )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "FeatureOrchestrator",
    "FeatureOrchestrationResult",
    "TaskExecutionResult",
    "WaveExecutionResult",
    "FeatureOrchestrationError",
    "WaveExecutionError",
    "DependencyError",
]
