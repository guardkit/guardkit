"""
Wave Progress Display for Feature Orchestration.

Provides wave-level progress visualization for feature mode execution.
Implements callback-based integration with FeatureOrchestrator.

Architecture:
    - WaveProgressDisplay: Wave-level progress (coordinates waves)
    - Integration with existing ProgressDisplay: Turn-level progress (per task)
    - Callback pattern: Loose coupling with orchestrator
    - Warn strategy: Display errors don't crash orchestration

Usage:
    display = WaveProgressDisplay(total_waves=4, verbose=True)

    # Wave lifecycle
    display.start_wave(wave_number=1, task_ids=["TASK-001", "TASK-002"])
    display.update_task_status("TASK-001", "in_progress", "Turn 1/5: Player Implementation")
    display.update_task_status("TASK-001", "success", "Completed in 2 turns")
    display.complete_wave(wave_number=1, passed=2, failed=0)

    # Final summary
    display.render_final_summary(feature, wave_results, "completed")
"""

import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Dict, List, Literal, Optional, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Setup logging
logger = logging.getLogger(__name__)

# Type aliases
TaskStatus = Literal["pending", "in_progress", "success", "failed", "skipped"]
FeatureStatus = Literal["completed", "failed", "paused"]


def _handle_display_error(func):
    """
    Decorator to handle display errors with warn strategy.

    Prevents display errors from crashing the orchestration.
    Logs errors and continues execution.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"Display error in {func.__name__}: {e}")
            warnings.warn(
                f"Wave display error (continuing): {e}",
                RuntimeWarning,
                stacklevel=2
            )
            return None
    return wrapper


@dataclass
class WaveTaskStatus:
    """Status record for a single task within a wave."""
    task_id: str
    status: TaskStatus = "pending"
    details: str = ""
    turns: int = 0
    decision: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WaveRecord:
    """Record of a completed wave."""
    wave_number: int
    task_ids: List[str]
    passed: int
    failed: int
    total_turns: int
    recovered: int = 0  # Number of tasks that required state recovery
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class WaveProgressDisplay:
    """
    Rich-based wave progress visualization for feature orchestration.

    Provides wave-level progress display with:
    - Wave headers showing current wave / total waves
    - Task status updates within waves
    - Wave completion summaries
    - Final feature summary with all waves and tasks

    Attributes:
        console: Rich Console instance for output
        total_waves: Total number of waves in feature
        verbose: Whether to show detailed output
        current_wave: Current wave number (1-indexed)
        task_statuses: Dict mapping task_id to WaveTaskStatus
        wave_history: List of completed wave records
    """

    def __init__(
        self,
        total_waves: int,
        verbose: bool = False,
        console: Optional[Console] = None,
    ):
        """
        Initialize wave progress display.

        Args:
            total_waves: Total number of waves in the feature
            verbose: Show detailed task-level output
            console: Optional Rich Console instance

        Raises:
            ValueError: If total_waves < 1
        """
        if total_waves < 1:
            raise ValueError("total_waves must be at least 1")

        self.console = console or Console()
        self.total_waves = total_waves
        self.verbose = verbose

        # State tracking
        self.current_wave: Optional[int] = None
        self.current_wave_tasks: List[str] = []
        self.task_statuses: Dict[str, WaveTaskStatus] = {}
        self.wave_history: List[WaveRecord] = []
        self.start_time: Optional[datetime] = None

        logger.info(f"WaveProgressDisplay initialized: waves={total_waves}, verbose={verbose}")

    @_handle_display_error
    def start_wave(self, wave_number: int, task_ids: List[str]) -> None:
        """
        Display wave start header with task list.

        Args:
            wave_number: Wave number (1-indexed)
            task_ids: List of task IDs in this wave
        """
        if self.start_time is None:
            self.start_time = datetime.now()

        self.current_wave = wave_number
        self.current_wave_tasks = task_ids

        # Initialize task statuses for this wave
        for task_id in task_ids:
            self.task_statuses[task_id] = WaveTaskStatus(task_id=task_id)

        # Build wave header
        parallel_indicator = f"[dim](parallel: {len(task_ids)})[/dim]" if len(task_ids) > 1 else ""
        task_list = ", ".join(task_ids)

        # Display wave separator and header
        self.console.print()
        self.console.print("━" * 60)
        self.console.print(
            f"  [bold cyan]Wave {wave_number}/{self.total_waves}[/bold cyan]: "
            f"{task_list} {parallel_indicator}"
        )
        self.console.print("━" * 60)

        logger.info(f"Started wave {wave_number}: {task_ids}")

    @_handle_display_error
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        details: str = "",
        turns: int = 0,
        decision: str = "",
    ) -> None:
        """
        Update task status within current wave.

        Args:
            task_id: Task identifier
            status: Task status (pending, in_progress, success, failed, skipped)
            details: Status details (e.g., "Turn 1/5: Player Implementation")
            turns: Number of turns executed
            decision: Final decision (e.g., "approve", "feedback")
        """
        # Update status record
        if task_id in self.task_statuses:
            self.task_statuses[task_id] = WaveTaskStatus(
                task_id=task_id,
                status=status,
                details=details,
                turns=turns,
                decision=decision,
            )

        # Display status update
        status_icons = {
            "pending": "[dim]○[/dim]",
            "in_progress": "[cyan]▶[/cyan]",
            "success": "[green]✓[/green]",
            "failed": "[red]✗[/red]",
            "skipped": "[yellow]⏭[/yellow]",
        }
        icon = status_icons.get(status, "•")

        # Build display message
        if status == "in_progress":
            message = f"  {icon} {task_id}: {details}"
        elif status in ("success", "failed"):
            turns_text = f"({turns} turn{'s' if turns != 1 else ''})" if turns > 0 else ""
            decision_text = f"[dim]{decision}[/dim]" if decision else ""
            message = f"  {icon} {task_id}: {status.upper()} {turns_text} {decision_text}"
        elif status == "skipped":
            message = f"  {icon} {task_id}: SKIPPED - {details}"
        else:
            message = f"  {icon} {task_id}: {details}"

        self.console.print(message)

        logger.debug(f"Task {task_id} status: {status} - {details}")

    @_handle_display_error
    def complete_wave(
        self,
        wave_number: int,
        passed: int,
        failed: int,
        skipped: int = 0,
        recovered: int = 0,
    ) -> None:
        """
        Display wave completion summary.

        Args:
            wave_number: Wave number that completed
            passed: Number of tasks that passed
            failed: Number of tasks that failed
            skipped: Number of tasks that were skipped
            recovered: Number of tasks that required state recovery
        """
        # Calculate total turns for this wave
        total_turns = sum(
            ts.turns for ts in self.task_statuses.values()
            if ts.task_id in self.current_wave_tasks
        )

        # Record wave completion
        self.wave_history.append(WaveRecord(
            wave_number=wave_number,
            task_ids=self.current_wave_tasks,
            passed=passed,
            failed=failed,
            total_turns=total_turns,
            recovered=recovered,
        ))

        # Display wave summary
        status_icon = "[green]✓[/green]" if failed == 0 else "[red]✗[/red]"
        status_text = "PASSED" if failed == 0 else "FAILED"

        summary_parts = [f"{passed} passed"]
        if failed > 0:
            summary_parts.append(f"{failed} failed")
        if skipped > 0:
            summary_parts.append(f"{skipped} skipped")
        summary = ", ".join(summary_parts)

        self.console.print()
        self.console.print(f"  Wave {wave_number} {status_icon} {status_text}: {summary}")

        # Show verbose table if enabled
        if self.verbose and self.current_wave_tasks:
            self._display_wave_task_table()

        logger.info(f"Wave {wave_number} complete: passed={passed}, failed={failed}")

    def _display_wave_task_table(self) -> None:
        """Display detailed task table for verbose mode."""
        table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="bold",
            padding=(0, 1),
        )

        table.add_column("Task", style="cyan", width=20)
        table.add_column("Status", width=10)
        table.add_column("Turns", width=6, justify="right")
        table.add_column("Decision", width=12)

        for task_id in self.current_wave_tasks:
            ts = self.task_statuses.get(task_id)
            if ts:
                status_style = {
                    "success": "green",
                    "failed": "red",
                    "skipped": "yellow",
                }.get(ts.status, "dim")

                table.add_row(
                    ts.task_id,
                    f"[{status_style}]{ts.status.upper()}[/{status_style}]",
                    str(ts.turns) if ts.turns > 0 else "-",
                    ts.decision or "-",
                )

        self.console.print(table)

    @_handle_display_error
    def render_final_summary(
        self,
        feature_id: str,
        feature_name: str,
        status: FeatureStatus,
        total_tasks: int,
        tasks_completed: int,
        tasks_failed: int,
        total_turns: int,
        worktree_path: str,
    ) -> None:
        """
        Render final feature orchestration summary.

        Args:
            feature_id: Feature identifier
            feature_name: Feature name/title
            status: Final feature status
            total_tasks: Total number of tasks
            tasks_completed: Number of completed tasks
            tasks_failed: Number of failed tasks
            total_turns: Total turns across all tasks
            worktree_path: Path to worktree
        """
        # Calculate duration
        duration_text = ""
        if self.start_time:
            duration = datetime.now() - self.start_time
            minutes = int(duration.total_seconds() / 60)
            seconds = int(duration.total_seconds() % 60)
            duration_text = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        # Build summary header
        self.console.print()
        self.console.print("═" * 60)

        if status == "completed":
            self.console.print("[bold green]FEATURE RESULT: SUCCESS[/bold green]")
        else:
            self.console.print(f"[bold red]FEATURE RESULT: {status.upper()}[/bold red]")

        self.console.print("═" * 60)
        self.console.print()

        # Feature info
        self.console.print(f"Feature: [cyan]{feature_id}[/cyan] - {feature_name}")
        self.console.print(f"Status: [bold]{status.upper()}[/bold]")
        self.console.print(f"Tasks: {tasks_completed}/{total_tasks} completed", end="")
        if tasks_failed > 0:
            self.console.print(f" [red]({tasks_failed} failed)[/red]")
        else:
            self.console.print()
        self.console.print(f"Total Turns: {total_turns}")
        if duration_text:
            self.console.print(f"Duration: {duration_text}")
        self.console.print()

        # Wave summary table
        if self.wave_history:
            self._display_wave_summary_table()

        # Execution quality metrics (recovery statistics)
        total_tasks_executed = sum(len(wave.task_ids) for wave in self.wave_history)
        total_recovered = sum(wave.recovered for wave in self.wave_history)
        clean_executions = total_tasks_executed - total_recovered

        if total_tasks_executed > 0:
            clean_pct = (clean_executions / total_tasks_executed) * 100
            recovered_pct = (total_recovered / total_tasks_executed) * 100

            self.console.print("[bold]Execution Quality:[/bold]")
            self.console.print(f"  Clean executions: {clean_executions}/{total_tasks_executed} ({clean_pct:.0f}%)")
            if total_recovered > 0:
                self.console.print(f"  State recoveries: {total_recovered}/{total_tasks_executed} ({recovered_pct:.0f}%)")
            self.console.print()

        # Task summary table (verbose mode)
        if self.verbose and self.task_statuses:
            self._display_all_tasks_table()

        # Worktree info
        self.console.print(f"Worktree: [cyan]{worktree_path}[/cyan]")
        self.console.print(f"Branch: [cyan]autobuild/{feature_id}[/cyan]")
        self.console.print()

        # Next steps
        self.console.print("[bold]Next Steps:[/bold]")
        if status == "completed":
            self.console.print(f"  1. Review: cd {worktree_path}")
            self.console.print("  2. Diff: git diff main")
            self.console.print(f"  3. Merge: git checkout main && git merge autobuild/{feature_id}")
            self.console.print(f"  4. Cleanup: guardkit worktree cleanup {feature_id}")
        else:
            self.console.print(f"  1. Review failed tasks: cd {worktree_path}")
            self.console.print(f"  2. Check status: guardkit autobuild status {feature_id}")
            self.console.print(f"  3. Resume: guardkit autobuild feature {feature_id} --resume")

        logger.info(f"Final summary rendered: {feature_id} - {status}")

    def _display_wave_summary_table(self) -> None:
        """Display wave summary table."""
        table = Table(
            title="Wave Summary",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Wave", style="cyan", width=6, justify="center")
        table.add_column("Tasks", width=8, justify="center")
        table.add_column("Status", width=10, justify="center")
        table.add_column("Passed", width=8, justify="center")
        table.add_column("Failed", width=8, justify="center")
        table.add_column("Turns", width=8, justify="center")
        table.add_column("Recovered", width=11, justify="center")

        for wave in self.wave_history:
            status_icon = "[green]✓[/green]" if wave.failed == 0 else "[red]✗[/red]"
            status_text = "PASS" if wave.failed == 0 else "FAIL"

            table.add_row(
                str(wave.wave_number),
                str(len(wave.task_ids)),
                f"{status_icon} {status_text}",
                str(wave.passed),
                str(wave.failed) if wave.failed > 0 else "-",
                str(wave.total_turns),
                str(wave.recovered) if wave.recovered > 0 else "-",
            )

        self.console.print(table)
        self.console.print()

    def _display_all_tasks_table(self) -> None:
        """Display all tasks table for verbose mode."""
        table = Table(
            title="Task Details",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Task", style="cyan", width=20)
        table.add_column("Status", width=10)
        table.add_column("Turns", width=8, justify="center")
        table.add_column("Decision", width=15)

        for task_id, ts in self.task_statuses.items():
            status_style = {
                "success": "green",
                "failed": "red",
                "skipped": "yellow",
            }.get(ts.status, "dim")

            table.add_row(
                ts.task_id,
                f"[{status_style}]{ts.status.upper()}[/{status_style}]",
                str(ts.turns) if ts.turns > 0 else "-",
                ts.decision or "-",
            )

        self.console.print(table)
        self.console.print()


# Public API
__all__ = [
    "WaveProgressDisplay",
    "WaveTaskStatus",
    "WaveRecord",
    "TaskStatus",
    "FeatureStatus",
]
