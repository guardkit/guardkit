"""
AutoBuild CLI commands.

This module provides Click commands for AutoBuild orchestration, implementing
the CLI layer for Phase 1a of the AutoBuild system.

Example:
    $ guardkit autobuild task TASK-AB-001
    $ guardkit autobuild task TASK-AB-001 --max-turns 10 --verbose
    $ guardkit autobuild status TASK-AB-001
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from guardkit.cli.decorators import handle_cli_errors
from guardkit.orchestrator import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    FeatureOrchestrationResult,
    FeatureOrchestrationError,
)
from guardkit.orchestrator.feature_loader import (
    FeatureNotFoundError,
    FeatureValidationError,
)
from guardkit.tasks.task_loader import TaskLoader
from guardkit.worktrees import WorktreeManager, Worktree

console = Console()
logger = logging.getLogger(__name__)


# ============================================================================
# AutoBuild Command Group
# ============================================================================


@click.group()
def autobuild():
    """
    AutoBuild commands for adversarial task execution.

    AutoBuild implements Player↔Coach adversarial workflow in isolated
    worktrees, providing automated implementation with human oversight.
    """
    pass


# ============================================================================
# Task Command
# ============================================================================


@autobuild.command()
@click.argument("task_id")
@click.option(
    "--max-turns",
    default=5,
    type=int,
    help="Maximum adversarial turns (default: 5)",
    show_default=True,
)
@click.option(
    "--model",
    default="claude-sonnet-4-5-20250929",
    help="Claude model to use",
    show_default=True,
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed turn-by-turn output",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from last saved state",
)
@click.pass_context
@handle_cli_errors
def task(
    ctx,
    task_id: str,
    max_turns: int,
    model: str,
    verbose: bool,
    resume: bool,
):
    """
    Execute AutoBuild orchestration for a task.

    This command creates an isolated worktree, runs the Player/Coach
    adversarial loop, and preserves the worktree for human review.

    \b
    Examples:
        guardkit autobuild task TASK-AB-001
        guardkit autobuild task TASK-AB-001 --max-turns 10 --verbose
        guardkit autobuild task TASK-AB-001 --model claude-opus-4-5-20251101
        guardkit autobuild task TASK-AB-001 --resume

    \b
    Workflow:
        1. Load task file from tasks/backlog or tasks/in_progress
        2. Create isolated worktree in .guardkit/worktrees/ (or resume existing)
        3. Execute Player→Coach adversarial turns
        4. Persist state to task frontmatter after each turn
        5. Preserve worktree for human review (approval or debugging)

    \b
    Resume Mode (--resume):
        Continue from last saved state if orchestration was interrupted.
        State is stored in task frontmatter as 'autobuild_state'.

    \b
    Exit Codes:
        0: Success (Coach approved)
        1: Task file not found
        2: Orchestration error
        3: Invalid arguments
    """
    # Inherit verbose from parent if set (ctx.obj can be None in testing)
    ctx_obj = ctx.obj or {}
    verbose = verbose or ctx_obj.get("verbose", False)

    # Display startup banner
    mode_text = "[yellow]Resuming[/yellow]" if resume else "Starting"
    if not ctx_obj.get("quiet", False):
        console.print(
            Panel(
                f"[bold]AutoBuild Task Orchestration[/bold]\n\n"
                f"Task: [cyan]{task_id}[/cyan]\n"
                f"Max Turns: {max_turns}\n"
                f"Model: {model}\n"
                f"Mode: {mode_text}",
                title="GuardKit AutoBuild",
                border_style="blue",
            )
        )

    # Phase 1: Load task file
    logger.info(f"Loading task {task_id}")
    task_data = TaskLoader.load_task(task_id, repo_root=Path.cwd())

    # Phase 2: Initialize orchestrator
    logger.info("Initializing orchestrator")
    orchestrator = AutoBuildOrchestrator(
        repo_root=Path.cwd(),
        max_turns=max_turns,
        resume=resume,
    )

    # Phase 3: Execute orchestration
    logger.info(f"Starting orchestration for {task_id} (resume={resume})")
    result = orchestrator.orchestrate(
        task_id=task_id,
        requirements=task_data["requirements"],
        acceptance_criteria=task_data["acceptance_criteria"],
        task_file_path=task_data.get("file_path"),  # Pass task file for state persistence
    )

    # Phase 4: Display results
    _display_result(result, verbose=verbose)

    # Exit with appropriate code
    sys.exit(0 if result.success else 2)


# ============================================================================
# Status Command (Simplified per Architectural Review)
# ============================================================================


@autobuild.command()
@click.argument("task_id")
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed worktree information",
)
@click.pass_context
@handle_cli_errors
def status(ctx, task_id: str, verbose: bool):
    """
    Show AutoBuild status for a task.

    This command checks if a worktree exists for the given task and
    displays its path and branch information.

    \b
    Examples:
        guardkit autobuild status TASK-AB-001
        guardkit autobuild status TASK-AB-001 --verbose

    \b
    Information Displayed:
        - Worktree existence
        - Worktree path
        - Branch name
        - Base branch (with --verbose)

    \b
    Exit Codes:
        0: Always (worktree exists or not)
    """
    # Inherit verbose from parent if set (ctx.obj can be None in testing)
    ctx_obj = ctx.obj or {}
    verbose = verbose or ctx_obj.get("verbose", False)

    # Initialize worktree manager
    worktree_manager = WorktreeManager(repo_root=Path.cwd())

    # Check if worktree exists (simplified per architectural review)
    worktree = _find_worktree(worktree_manager, task_id)

    if not worktree:
        console.print(
            f"[yellow]No AutoBuild worktree found for {task_id}[/yellow]\n"
        )
        console.print(
            "[dim]Run `guardkit autobuild task {task_id}` to create one[/dim]"
        )
        sys.exit(0)

    # Display worktree status (simplified - no state loading in MVP)
    _display_status(worktree, verbose=verbose)

    sys.exit(0)


# ============================================================================
# Feature Command
# ============================================================================


@autobuild.command()
@click.argument("feature_id")
@click.option(
    "--max-turns",
    default=5,
    type=int,
    help="Maximum adversarial turns per task (default: 5)",
    show_default=True,
)
@click.option(
    "--stop-on-failure/--no-stop-on-failure",
    default=True,
    help="Stop feature execution on first task failure",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from last saved state",
)
@click.option(
    "--fresh",
    is_flag=True,
    help="Start fresh, ignoring any saved state",
)
@click.option(
    "--task",
    "specific_task",
    default=None,
    help="Run specific task within feature (e.g., TASK-AUTH-001)",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed turn-by-turn output",
)
@click.pass_context
@handle_cli_errors
def feature(
    ctx,
    feature_id: str,
    max_turns: int,
    stop_on_failure: bool,
    resume: bool,
    fresh: bool,
    specific_task: Optional[str],
    verbose: bool,
):
    """
    Execute AutoBuild for all tasks in a feature.

    This command loads a feature file from .guardkit/features/FEAT-XXX.yaml,
    creates a shared worktree, and executes tasks wave by wave respecting
    dependency ordering.

    \b
    Examples:
        guardkit autobuild feature FEAT-A1B2
        guardkit autobuild feature FEAT-A1B2 --max-turns 10
        guardkit autobuild feature FEAT-A1B2 --no-stop-on-failure
        guardkit autobuild feature FEAT-A1B2 --task TASK-AUTH-002
        guardkit autobuild feature FEAT-A1B2 --resume
        guardkit autobuild feature FEAT-A1B2 --fresh

    \b
    Resume Behavior:
        - If incomplete state detected and no flags: prompts user to resume or start fresh
        - --resume: skip prompt, resume from last saved state
        - --fresh: skip prompt, start from scratch (clears previous state)
        - Cannot use both --resume and --fresh together

    \b
    Workflow:
        1. Load feature file from .guardkit/features/
        2. Validate all task markdown files exist
        3. Create shared worktree for entire feature
        4. Execute tasks wave by wave (respecting parallel_groups)
        5. Update feature YAML after each task
        6. Preserve worktree for human review

    \b
    Exit Codes:
        0: Success (all tasks completed)
        1: Feature file not found
        2: Orchestration error
        3: Validation error
    """
    # Inherit verbose from parent if set (ctx.obj can be None in testing)
    ctx_obj = ctx.obj or {}
    verbose = verbose or ctx_obj.get("verbose", False)

    # Validate mutually exclusive flags
    if resume and fresh:
        console.print("[red]Error: Cannot use both --resume and --fresh flags together[/red]")
        console.print("\nChoose one:")
        console.print("  --resume  Resume from last saved state")
        console.print("  --fresh   Start from scratch, ignoring saved state")
        sys.exit(3)

    logger.info(
        f"Starting feature orchestration: {feature_id} "
        f"(max_turns={max_turns}, stop_on_failure={stop_on_failure}, resume={resume}, fresh={fresh})"
    )

    try:
        # Initialize feature orchestrator
        orchestrator = FeatureOrchestrator(
            repo_root=Path.cwd(),
            max_turns=max_turns,
            stop_on_failure=stop_on_failure,
            resume=resume,
            fresh=fresh,
            verbose=verbose,
            quiet=ctx_obj.get("quiet", False),
        )

        # Execute feature orchestration
        result = orchestrator.orchestrate(
            feature_id=feature_id,
            specific_task=specific_task,
        )

        # Exit with appropriate code
        sys.exit(0 if result.success else 2)

    except FeatureNotFoundError as e:
        console.print(f"[red]Feature not found: {e}[/red]")
        logger.error(f"Feature not found: {e}")
        sys.exit(1)

    except FeatureValidationError as e:
        console.print(f"[red]Feature validation failed:[/red]\n{e}")
        logger.error(f"Feature validation failed: {e}")
        sys.exit(3)

    except FeatureOrchestrationError as e:
        console.print(f"[red]Orchestration error: {e}[/red]")
        logger.error(f"Feature orchestration error: {e}")
        sys.exit(2)


# ============================================================================
# Helper Functions
# ============================================================================


def _display_result(result: OrchestrationResult, verbose: bool = False) -> None:
    """
    Display orchestration result with Rich formatting.

    Parameters
    ----------
    result : OrchestrationResult
        Orchestration result
    verbose : bool, optional
        Show detailed turn history (default: False)
    """
    console.print()  # Blank line

    if result.success:
        console.print(
            Panel(
                f"[green]✓ Task completed successfully[/green]\n\n"
                f"Total turns: {result.total_turns}\n"
                f"Worktree: [cyan]{result.worktree.path}[/cyan]\n"
                f"Branch: [cyan]{result.worktree.branch_name}[/cyan]",
                title="Orchestration Complete",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]✗ Task failed[/red]\n\n"
                f"Reason: {result.final_decision}\n"
                f"Total turns: {result.total_turns}\n"
                f"Error: {result.error or 'N/A'}\n"
                f"Worktree preserved at: [cyan]{result.worktree.path}[/cyan]",
                title="Orchestration Failed",
                border_style="red",
            )
        )

    # Display turn history if verbose
    if verbose and result.turn_history:
        console.print("\n[bold]Turn History:[/bold]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Turn", style="cyan", width=6)
        table.add_column("Decision", width=12)
        table.add_column("Details", width=60)

        for turn in result.turn_history:
            decision_style = (
                "green"
                if turn.decision == "approve"
                else "red" if turn.decision == "error" else "yellow"
            )
            decision = f"[{decision_style}]{turn.decision.upper()}[/{decision_style}]"

            # Build details
            if turn.decision == "approve":
                details = "Implementation approved"
            elif turn.decision == "error":
                error = (
                    turn.coach_result.error
                    if turn.coach_result
                    else turn.player_result.error
                )
                error_msg = error or "Unknown error"
                details = f"Error: {error_msg[:50]}..." if len(error_msg) > 50 else f"Error: {error_msg}"
            else:  # feedback
                feedback = turn.feedback or "No feedback"
                details = feedback[:50] + "..." if len(feedback) > 50 else feedback

            table.add_row(str(turn.turn), decision, details)

        console.print(table)


def _display_status(worktree: Worktree, verbose: bool = False) -> None:
    """
    Display worktree status.

    Simplified per architectural review - just shows worktree existence
    and path. State loading deferred to future wave.

    Parameters
    ----------
    worktree : Worktree
        Worktree instance
    verbose : bool, optional
        Show extended information (default: False)
    """
    console.print(
        Panel(
            f"[bold]Task:[/bold] [cyan]{worktree.task_id}[/cyan]\n"
            f"[bold]Worktree:[/bold] [cyan]{worktree.path}[/cyan]\n"
            f"[bold]Branch:[/bold] [cyan]{worktree.branch_name}[/cyan]"
            + (
                f"\n[bold]Base Branch:[/bold] [cyan]{worktree.base_branch}[/cyan]"
                if verbose
                else ""
            ),
            title="AutoBuild Worktree Status",
            border_style="blue",
        )
    )


def _find_worktree(
    manager: WorktreeManager, task_id: str
) -> Optional[Worktree]:
    """
    Find worktree for task ID.

    Simplified implementation per architectural review - checks if
    worktree directory exists under .guardkit/worktrees/.

    Parameters
    ----------
    manager : WorktreeManager
        WorktreeManager instance
    task_id : str
        Task identifier

    Returns
    -------
    Optional[Worktree]
        Worktree if found, None otherwise
    """
    worktree_path = manager.worktrees_dir / task_id

    if not worktree_path.exists():
        return None

    # Build Worktree instance from discovered path
    branch_name = f"autobuild/{task_id}"

    # Detect base branch from git (or default to main)
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        base_branch = result.stdout.strip() or "main"
    except Exception:
        base_branch = "main"

    return Worktree(
        task_id=task_id,
        branch_name=branch_name,
        path=worktree_path,
        base_branch=base_branch,
    )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "autobuild",
    "task",
    "status",
]
