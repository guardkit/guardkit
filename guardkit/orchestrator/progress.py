"""
Progress Display for AutoBuild Orchestrator

Provides real-time turn-by-turn progress visualization using Rich library.
Implements Facade Pattern wrapping Rich components with simplified interface.

Architecture:
    • Facade Pattern wrapping Rich library
    • Minimal state tracking (turn lifecycle + errors only)
    • Warn strategy for display errors (never crash orchestration)
    • Context manager support for cleanup

Usage:
    with ProgressDisplay(max_turns=5) as display:
        display.start_turn(turn=1, phase="Player Implementation")
        # ... turn execution ...
        display.update_turn(message="Writing tests...")
        # ... more work ...
        display.complete_turn(status="success", summary="3 files, 2 tests")

        display.start_turn(turn=2, phase="Coach Validation")
        # ... validation ...
        display.complete_turn(status="feedback", summary="2 issues found")

        display.render_summary(
            total_turns=2,
            final_status="approved",
            details="All requirements met"
        )
"""

import logging
import warnings
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Literal, Optional
from functools import wraps

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.table import Table
from rich.panel import Panel
from rich import box

# Setup logging
logger = logging.getLogger(__name__)

# Type aliases
TurnStatus = Literal["in_progress", "success", "feedback", "error"]
FinalStatus = Literal["approved", "max_turns_exceeded", "error"]


def _handle_display_error(func):
    """
    Decorator to handle display errors with warn strategy.

    Prevents display errors from crashing the orchestration.
    Logs errors and continues execution.

    Args:
        func: Function to wrap with error handling

    Returns:
        Wrapped function that catches and logs display errors
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"Display error in {func.__name__}: {e}")
            warnings.warn(
                f"Progress display error (continuing): {e}",
                RuntimeWarning,
                stacklevel=2
            )
            return None
    return wrapper


class ProgressDisplay:
    """
    Rich-based progress visualization for AutoBuild orchestration.

    Provides turn-by-turn progress display with:
    • Real-time status updates during Player/Coach execution
    • Turn-level success/feedback indicators
    • Final summary with complete turn history
    • Error display without crashing orchestration

    State Tracking (Minimal - per architectural review):
    • Turn ID and phase name
    • Start/end timestamps per turn
    • Turn status (in_progress/success/feedback/error)
    • Error messages (if any)

    Attributes:
        console: Rich Console instance for output
        max_turns: Maximum number of turns (for progress calculation)
        current_turn: Current turn number (1-indexed)
        turn_history: List of completed turn records
        _progress: Rich Progress instance (when turn active)
        _task_id: Rich Task ID for current turn

    Examples:
        >>> with ProgressDisplay(max_turns=5) as display:
        ...     display.start_turn(1, "Player Implementation")
        ...     display.update_turn("Writing tests...")
        ...     display.complete_turn("success", "3 files created")
    """

    def __init__(
        self,
        max_turns: int = 5,
        console: Optional[Console] = None,
        **kwargs
    ):
        """
        Initialize progress display.

        Args:
            max_turns: Maximum number of turns for progress calculation
            console: Optional Rich Console instance (creates new if None)
            **kwargs: Additional configuration options (reserved for future use)

        Raises:
            ValueError: If max_turns < 1
        """
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")

        self.console = console or Console()
        self.max_turns = max_turns
        self.current_turn: Optional[int] = None
        self.turn_history: List[Dict] = []

        # Rich components (initialized per turn)
        self._progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None

        logger.info(f"ProgressDisplay initialized with max_turns={max_turns}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self._cleanup()
        return False  # Don't suppress exceptions

    def _cleanup(self):
        """Clean up Rich progress resources."""
        if self._progress is not None:
            try:
                self._progress.stop()
            except Exception as e:
                logger.debug(f"Error stopping progress: {e}")
            finally:
                self._progress = None
                self._task_id = None

    def start_turn(self, turn: int, phase: str) -> None:
        """
        Start a new turn with progress display.

        Args:
            turn: Turn number (1-indexed)
            phase: Phase name (e.g., "Player Implementation", "Coach Validation")

        Raises:
            ValueError: If turn number is invalid

        Examples:
            >>> display.start_turn(1, "Player Implementation")
            >>> display.start_turn(2, "Coach Validation")
        """
        # Validate before decorator (so ValueError propagates)
        if turn < 1 or turn > self.max_turns:
            raise ValueError(f"Invalid turn number: {turn} (max: {self.max_turns})")

        self._start_turn_impl(turn, phase)

    @_handle_display_error
    def _start_turn_impl(self, turn: int, phase: str) -> None:
        """Internal implementation of start_turn with error handling."""

        # Clean up previous turn if active
        if self._progress is not None:
            self._cleanup()

        self.current_turn = turn

        # Create Rich progress bar
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
            transient=False  # Keep completed progress visible
        )

        # Start progress and add task
        self._progress.start()
        description = f"Turn {turn}/{self.max_turns}: {phase}"
        self._task_id = self._progress.add_task(
            description,
            total=100,
            completed=0
        )

        # Record turn start
        self.turn_history.append({
            "turn": turn,
            "phase": phase,
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "error": None
        })

        logger.info(f"Started turn {turn}: {phase}")

    @_handle_display_error
    def update_turn(self, message: str, progress: Optional[int] = None) -> None:
        """
        Update current turn with status message.

        Args:
            message: Status message to display
            progress: Optional progress percentage (0-100)

        Examples:
            >>> display.update_turn("Writing tests...")
            >>> display.update_turn("Running tests...", progress=50)
        """
        if self._progress is None or self._task_id is None:
            logger.warning("update_turn called without active turn")
            return

        # Update description
        turn_num = self.current_turn or 0
        description = f"Turn {turn_num}/{self.max_turns}: {message}"
        self._progress.update(self._task_id, description=description)

        # Update progress if provided
        if progress is not None:
            if not 0 <= progress <= 100:
                logger.warning(f"Invalid progress value: {progress}")
            else:
                self._progress.update(self._task_id, completed=progress)

        logger.debug(f"Turn {turn_num} update: {message}")

    @_handle_display_error
    def complete_turn(
        self,
        status: TurnStatus,
        summary: str,
        error: Optional[str] = None
    ) -> None:
        """
        Complete current turn with final status.

        Args:
            status: Turn status (success/feedback/error)
            summary: Summary message (e.g., "3 files, 2 tests")
            error: Optional error message (for status="error")

        Examples:
            >>> display.complete_turn("success", "3 files created, 2 tests passing")
            >>> display.complete_turn("feedback", "2 issues found: HTTPS, token refresh")
            >>> display.complete_turn("error", "Build failed", error="pytest exited with code 1")
        """
        if self._progress is None or self._task_id is None:
            logger.warning("complete_turn called without active turn")
            return

        # Complete progress bar
        self._progress.update(self._task_id, completed=100)

        # Status indicators
        status_icons = {
            "success": "✓",
            "feedback": "⚠",
            "error": "✗",
            "in_progress": "⏳"
        }
        icon = status_icons.get(status, "•")

        # Color coding
        status_colors = {
            "success": "green",
            "feedback": "yellow",
            "error": "red",
            "in_progress": "blue"
        }
        color = status_colors.get(status, "white")

        # Display completion message
        message = f"[{color}]{icon}[/{color}] {summary}"
        if error:
            message += f"\n   [red]Error: {error}[/red]"

        self.console.print(f"  {message}")

        # Update turn history
        if self.turn_history and self.turn_history[-1]["turn"] == self.current_turn:
            self.turn_history[-1].update({
                "status": status,
                "summary": summary,
                "ended_at": datetime.now().isoformat(),
                "error": error
            })

        # Cleanup progress
        self._cleanup()

        logger.info(f"Completed turn {self.current_turn}: {status} - {summary}")

    @_handle_display_error
    def handle_error(self, error_message: str, turn: Optional[int] = None) -> None:
        """
        Display error message with context.

        Args:
            error_message: Error description
            turn: Optional turn number (uses current_turn if None)

        Examples:
            >>> display.handle_error("SDK timeout after 30 seconds")
            >>> display.handle_error("Player crashed", turn=2)
        """
        turn_num = turn or self.current_turn or 0

        error_panel = Panel(
            f"[red]Error in Turn {turn_num}:[/red]\n\n{error_message}",
            border_style="red",
            box=box.ROUNDED
        )

        self.console.print(error_panel)

        # Update turn history if turn is active
        if (
            self.turn_history and
            self.turn_history[-1]["turn"] == turn_num and
            self.turn_history[-1]["status"] == "in_progress"
        ):
            self.turn_history[-1].update({
                "status": "error",
                "error": error_message,
                "ended_at": datetime.now().isoformat()
            })

        logger.error(f"Turn {turn_num} error: {error_message}")

    @_handle_display_error
    def render_summary(
        self,
        total_turns: int,
        final_status: FinalStatus,
        details: str
    ) -> None:
        """
        Render final summary table with complete turn history.

        Args:
            total_turns: Total number of turns executed
            final_status: Final orchestration status
            details: Additional details (e.g., "All requirements met")

        Examples:
            >>> display.render_summary(
            ...     total_turns=3,
            ...     final_status="approved",
            ...     details="All requirements met, tests passing"
            ... )
        """
        # Create summary table
        table = Table(
            title=f"AutoBuild Summary ({final_status.upper()})",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )

        table.add_column("Turn", style="cyan", width=6)
        table.add_column("Phase", style="white", width=25)
        table.add_column("Status", style="white", width=12)
        table.add_column("Summary", style="white")

        # Add rows from history
        status_icons = {
            "success": "[green]✓[/green]",
            "feedback": "[yellow]⚠[/yellow]",
            "error": "[red]✗[/red]",
            "in_progress": "[blue]⏳[/blue]"
        }

        for record in self.turn_history:
            icon = status_icons.get(record["status"], "•")
            table.add_row(
                str(record["turn"]),
                record["phase"],
                f"{icon} {record['status']}",
                record.get("summary", record.get("error", "—"))
            )

        # Display table
        self.console.print()
        self.console.print(table)

        # Display final status panel
        status_colors = {
            "approved": "green",
            "max_turns_exceeded": "yellow",
            "error": "red"
        }
        color = status_colors.get(final_status, "white")

        final_panel = Panel(
            f"[{color}]Status: {final_status.upper()}[/{color}]\n\n{details}",
            border_style=color,
            box=box.ROUNDED
        )

        self.console.print()
        self.console.print(final_panel)

        logger.info(f"Summary rendered: {final_status} after {total_turns} turns")


# Public API
__all__ = [
    "ProgressDisplay",
    "TurnStatus",
    "FinalStatus"
]
