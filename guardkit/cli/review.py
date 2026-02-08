"""
Review CLI commands.

This module provides Click commands for task review with optional
knowledge capture integration.

Example:
    $ guardkit review TASK-REV-001
    $ guardkit review TASK-REV-001 --capture-knowledge
    $ guardkit review TASK-REV-001 --mode=architectural -ck
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

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
    "--capture-knowledge",
    "-ck",
    "capture_knowledge",
    is_flag=True,
    default=False,
    help="Trigger knowledge capture after review completes",
)
@click.option(
    "--enable-context/--no-context",
    "enable_context",
    default=True,
    help="Enable/disable Graphiti context retrieval (default: enabled)",
)
@click.pass_context
@handle_cli_errors
def review(
    ctx,
    task_id: str,
    mode: str,
    depth: str,
    capture_knowledge: bool,
    enable_context: bool,
):
    """
    Execute a review for a task with optional knowledge capture.

    Loads the task, displays review context, and optionally triggers
    knowledge capture after the review completes.

    \b
    Examples:
        guardkit review TASK-REV-001
        guardkit review TASK-REV-001 --capture-knowledge
        guardkit review TASK-REV-001 --mode=security -ck
        guardkit review TASK-REV-001 --mode=decision --depth=comprehensive -ck

    \b
    Knowledge Capture (--capture-knowledge / -ck):
        After the review completes, triggers an abbreviated knowledge capture
        session with 3-5 context-specific questions generated from the review
        findings. Captured knowledge is linked to the task for searchability.

        Graceful degradation: if Graphiti is unavailable, capture is skipped
        with a message (no crash).

    \b
    Exit Codes:
        0: Success
        1: Task not found
        2: Review error
    """
    # Load task
    logger.info(f"Loading task {task_id}")
    task_data = TaskLoader.load_task(task_id, repo_root=Path.cwd())

    task_frontmatter = task_data.get("frontmatter", {})

    # Build task context for review
    task_context = {
        "task_id": task_id,
        "title": task_frontmatter.get("title", task_id),
        "review_mode": mode,
        "depth": depth,
    }

    # When context is disabled, suppress capture-knowledge too
    if not enable_context and capture_knowledge:
        logger.info("--no-context disables --capture-knowledge")
        capture_knowledge = False

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
        if capture_knowledge:
            console.print(
                "[bold]Knowledge Capture:[/bold] [green]Enabled[/green]"
            )
        console.print()

    # Store enable_context in task_context for downstream use
    task_context["enable_context"] = enable_context

    # Build review findings from task content
    review_findings = {
        "mode": mode,
        "findings": [],
        "depth": depth,
    }

    # Run knowledge capture if flag is set (already suppressed if --no-context)
    if capture_knowledge:
        _run_capture(task_context, review_findings)

    logger.info(f"Review complete for {task_id}")


def _run_capture(
    task_context: dict,
    review_findings: dict,
) -> None:
    """
    Run knowledge capture after review completes.

    Imports run_review_capture lazily and executes it. Handles both
    sync and async contexts gracefully.

    Parameters
    ----------
    task_context : dict
        Task metadata including task_id and review_mode
    review_findings : dict
        Review results including mode and findings
    """
    try:
        from guardkit.knowledge.review_knowledge_capture import run_review_capture

        result = asyncio.run(
            run_review_capture(
                task_context=task_context,
                review_findings=review_findings,
                capture_knowledge=True,
            )
        )

        if result.get("capture_executed"):
            findings_count = result.get("findings_count", 0)
            review_mode = result.get("review_mode", "unknown")
            console.print(
                f"[green][Knowledge Capture] Captured insights from "
                f"{review_mode} review ({findings_count} finding(s))[/green]"
            )
        elif "error" in result:
            console.print(
                f"[yellow][Knowledge Capture] Skipped: {result['error']}[/yellow]"
            )
        else:
            console.print(
                "[yellow][Knowledge Capture] Skipped (no capture executed)[/yellow]"
            )

    except Exception as e:
        logger.warning(f"Knowledge capture failed: {e}")
        console.print(
            f"[yellow][Knowledge Capture] Skipped ({e})[/yellow]"
        )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "review",
    "_run_capture",
]
