"""
Review CLI commands.

This module provides Click commands for task review with optional
knowledge capture integration.

Example:
    $ guardkit review TASK-REV-001
    $ guardkit review TASK-REV-001 --mode=architectural
"""

import logging
from pathlib import Path

import click
from rich.console import Console

from guardkit.cli.decorators import handle_cli_errors
from guardkit.tasks.task_loader import TaskLoader

console = Console()
logger = logging.getLogger(__name__)


@click.command("review")
@click.argument("task_id")
@click.option(
    "--mode",
    type=click.Choice(
        ["architectural", "code-quality", "decision", "technical-debt", "security"],
        case_sensitive=False,
    ),
    default="architectural",
    help="Review mode (default: architectural)",
    show_default=True,
)
@click.option(
    "--depth",
    type=click.Choice(["quick", "standard", "comprehensive"], case_sensitive=False),
    default="standard",
    help="Review depth (default: standard)",
    show_default=True,
)
@click.option(
    "--enable-context/--no-context",
    "enable_context",
    default=True,
    help="Enable/disable memory context retrieval (default: enabled)",
)
@click.pass_context
@handle_cli_errors
def review(
    ctx,
    task_id: str,
    mode: str,
    depth: str,
    enable_context: bool,
):
    """
    Execute a review for a task.

    Loads the task and displays review context.

    \b
    Examples:
        guardkit review TASK-REV-001
        guardkit review TASK-REV-001 --mode=security
        guardkit review TASK-REV-001 --mode=decision --depth=comprehensive

    \b
    Exit Codes:
        0: Success
        1: Task not found
        2: Review error
    """
    # Load task (raises if not found -> exit code 1 via handle_cli_errors)
    logger.info(f"Loading task {task_id}")
    TaskLoader.load_task(task_id, repo_root=Path.cwd())

    # Display review info
    ctx_obj = ctx.obj or {}
    if not ctx_obj.get("quiet", False):
        console.print(f"[bold]Review:[/bold] [cyan]{task_id}[/cyan]")
        console.print(f"[bold]Mode:[/bold] {mode}")
        console.print(f"[bold]Depth:[/bold] {depth}")
        if not enable_context:
            console.print(
                "[bold]Context:[/bold] [yellow]Disabled[/yellow]"
            )
        console.print()

    logger.info(f"Review complete for {task_id}")


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "review",
]
