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
)
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    FeatureOrchestrationError,
)
from guardkit.orchestrator.feature_loader import (
    FeatureNotFoundError,
    FeatureValidationError,
)
from guardkit.orchestrator.feature_complete import (
    FeatureCompleteOrchestrator,
    FeatureCompleteResult,
    FeatureCompleteError,
)
from guardkit.tasks.task_loader import TaskLoader
from guardkit.worktrees import WorktreeManager, Worktree

console = Console()
logger = logging.getLogger(__name__)


# ============================================================================
# SDK Pre-flight Check
# ============================================================================


def _check_sdk_available() -> bool:
    """
    Check if Claude Agent SDK is available.

    This function attempts to import the Claude Agent SDK to verify
    it is installed and accessible. Used for fail-fast validation
    before starting orchestration.

    Returns
    -------
    bool
        True if SDK is importable, False otherwise.
    """
    try:
        from claude_agent_sdk import query  # noqa: F401

        return True
    except ImportError:
        return False


def _require_sdk() -> None:
    """
    Require SDK availability or exit with helpful message.

    This function should be called at the start of commands that
    require the Claude Agent SDK. If the SDK is not available,
    it prints installation instructions and exits with code 1.

    Raises
    ------
    SystemExit
        Exits with code 1 if SDK is not available.
    """
    if not _check_sdk_available():
        console.print("[red]Error: Claude Agent SDK not available[/red]")
        console.print()
        console.print("AutoBuild requires the Claude Agent SDK.")
        console.print()
        console.print("To install:")
        console.print("  [cyan]pip install claude-agent-sdk[/cyan]")
        console.print("  # OR")
        console.print("  [cyan]pip install guardkit-py[autobuild][/cyan]")
        console.print()
        console.print("For more info: [dim]guardkit doctor[/dim]")
        sys.exit(1)


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
@click.option(
    "--mode",
    type=click.Choice(["standard", "tdd", "bdd"], case_sensitive=False),
    default=None,
    help="Development mode (standard, tdd, or bdd). Defaults to task frontmatter autobuild.mode or 'tdd'",
)
@click.option(
    "--sdk-timeout",
    "sdk_timeout",
    default=None,
    type=int,
    help="SDK timeout in seconds (60-3600). Defaults to task frontmatter autobuild.sdk_timeout or 900",
)
@click.option(
    "--no-pre-loop",
    "no_pre_loop",
    is_flag=True,
    default=False,
    help=(
        "Skip design phase (Phases 1.6-2.8) before Player-Coach loop. "
        "NOTE: Enabled by default for task-build because standalone tasks "
        "often need design clarification. Disable for simple bug fixes or "
        "tasks with detailed implementation notes. Saves 60-90 min. "
        "See: docs/guides/guardkit-workflow.md#pre-loop-decision-guide"
    ),
)
@click.option(
    "--skip-arch-review",
    "skip_arch_review",
    is_flag=True,
    default=False,
    help="Skip architectural review quality gate (use with caution)",
)
@click.option(
    "--no-checkpoints",
    "no_checkpoints",
    is_flag=True,
    default=False,
    help="Disable worktree checkpointing (not recommended - disables rollback)",
)
@click.option(
    "--no-rollback",
    "no_rollback",
    is_flag=True,
    default=False,
    help="Disable automatic rollback on context pollution (manual rollback still available)",
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
    mode: Optional[str],
    sdk_timeout: Optional[int],
    no_pre_loop: bool,
    skip_arch_review: bool,
    no_checkpoints: bool,
    no_rollback: bool,
):
    """
    Execute AutoBuild orchestration for a task.

    This command creates an isolated worktree and runs the Player/Coach
    adversarial loop. The Player **delegates** to `task-work --implement-only`
    to leverage the full subagent infrastructure and quality gates.

    \b
    Delegation Architecture:
        PreLoop: task-work --design-only (Phases 2-2.8)
        Loop:    task-work --implement-only --mode=MODE (Phases 3-5.5)
        Coach:   Validates task-work quality gate results

    \b
    Development Modes (--mode flag):
        tdd:      Red-Green-Refactor cycle (default)
        standard: Traditional implementation
        bdd:      Behavior-driven (requires RequireKit)

    \b
    Examples:
        guardkit autobuild task TASK-AB-001
        guardkit autobuild task TASK-AB-001 --mode=standard
        guardkit autobuild task TASK-AB-001 --max-turns 10 --verbose
        guardkit autobuild task TASK-AB-001 --model claude-opus-4-5-20251101
        guardkit autobuild task TASK-AB-001 --resume

    \b
    Quality Gate Reuse (100% code reuse):
        Player delegates to task-work for:
        - Phase 2.5B: Architectural Review
        - Phase 4.5: Test Enforcement Loop
        - Phase 5: Code Review
        - Phase 5.5: Plan Audit

    \b
    Workflow:
        1. Load task file from tasks/backlog or tasks/in_progress
        2. Create isolated worktree in .guardkit/worktrees/ (or resume existing)
        3. PreLoop: task-work --design-only (planning + approval)
        4. Loop: Player delegates to task-work --implement-only (iterative)
        5. Coach: Validates quality gate results, approves or provides feedback
        6. Preserve worktree for human review (never auto-merges)

    \b
    Resume Mode (--resume):
        Continue from last saved state if orchestration was interrupted.
        State is stored in task frontmatter as 'autobuild_state'.

    \b
    Exit Codes:
        0: Success (Coach approved)
        1: Task file not found or SDK not available
        2: Orchestration error
        3: Invalid arguments
    """
    # Pre-flight check: Ensure SDK is available before any work
    _require_sdk()

    # Inherit verbose from parent if set (ctx.obj can be None in testing)
    ctx_obj = ctx.obj or {}
    verbose = verbose or ctx_obj.get("verbose", False)

    # Phase 1: Load task file
    logger.info(f"Loading task {task_id}")
    task_data = TaskLoader.load_task(task_id, repo_root=Path.cwd())

    # Resolve development mode: CLI flag > task frontmatter > default (tdd)
    # Note: TaskLoader returns frontmatter as nested dict, not at top level
    task_frontmatter = task_data.get("frontmatter", {})
    autobuild_config = task_frontmatter.get("autobuild", {})
    effective_mode = mode
    if effective_mode is None:
        effective_mode = autobuild_config.get("mode", "tdd")
    logger.info(f"Development mode: {effective_mode}")

    # Validate and resolve SDK timeout: CLI flag > task frontmatter > default (900)
    if sdk_timeout is not None and not (60 <= sdk_timeout <= 3600):
        raise click.BadParameter(
            "SDK timeout must be between 60 and 3600 seconds",
            param_hint="'--sdk-timeout'",
        )
    effective_sdk_timeout = sdk_timeout
    if effective_sdk_timeout is None:
        effective_sdk_timeout = autobuild_config.get("sdk_timeout", 900)
    logger.info(f"SDK timeout: {effective_sdk_timeout}s")

    # Resolve skip_arch_review: CLI flag > task frontmatter > default (False)
    effective_skip_arch_review = skip_arch_review
    if not effective_skip_arch_review:
        effective_skip_arch_review = autobuild_config.get("skip_arch_review", False)
    logger.info(f"Skip architectural review: {effective_skip_arch_review}")

    # Display warning if skipping architectural review
    if effective_skip_arch_review:
        console.print("[yellow]⚠️  Warning: Architectural review will be skipped[/yellow]")
        console.print("[dim]   This bypasses SOLID/DRY/YAGNI validation.[/dim]")
        console.print("[dim]   Use only for legacy code or special circumstances.[/dim]")
        console.print()

    # Display startup banner
    resume_text = " [yellow](Resuming)[/yellow]" if resume else ""
    mode_display = effective_mode.upper()
    pre_loop_display = "[red]OFF[/red]" if no_pre_loop else "[green]ON[/green]"
    if not ctx_obj.get("quiet", False):
        console.print(
            Panel(
                f"[bold]AutoBuild Task Orchestration[/bold]\n\n"
                f"Task: [cyan]{task_id}[/cyan]\n"
                f"Max Turns: {max_turns}\n"
                f"Model: {model}\n"
                f"Mode: [magenta]{mode_display}[/magenta]\n"
                f"Pre-Loop: {pre_loop_display}\n"
                f"SDK Timeout: {effective_sdk_timeout}s{resume_text}",
                title="GuardKit AutoBuild",
                border_style="blue",
            )
        )

    # Phase 2: Initialize orchestrator
    # Note: enable_pre_loop defaults to True for task-build, --no-pre-loop disables it
    enable_pre_loop = not no_pre_loop
    enable_checkpoints = not no_checkpoints
    rollback_on_pollution = not no_rollback and enable_checkpoints  # Can't rollback without checkpoints

    logger.info(
        f"Initializing orchestrator (enable_pre_loop={enable_pre_loop}, "
        f"skip_arch_review={effective_skip_arch_review}, "
        f"enable_checkpoints={enable_checkpoints}, "
        f"rollback_on_pollution={rollback_on_pollution})"
    )
    orchestrator = AutoBuildOrchestrator(
        repo_root=Path.cwd(),
        max_turns=max_turns,
        resume=resume,
        enable_pre_loop=enable_pre_loop,
        development_mode=effective_mode,
        sdk_timeout=effective_sdk_timeout,
        skip_arch_review=effective_skip_arch_review,
        enable_checkpoints=enable_checkpoints,
        rollback_on_pollution=rollback_on_pollution,
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
@click.option(
    "--sdk-timeout",
    "sdk_timeout",
    default=None,
    type=int,
    help="SDK timeout in seconds (60-3600). Defaults to feature YAML autobuild.sdk_timeout or 900",
)
@click.option(
    "--enable-pre-loop/--no-pre-loop",
    "enable_pre_loop",
    default=None,
    help=(
        "Enable/disable design phase (Phases 1.6-2.8) before Player-Coach loop. "
        "NOTE: Disabled by default for feature-build because tasks from /feature-plan "
        "already have detailed specs. Enable for tasks needing architectural design. "
        "Adds 60-90 min per task. See: docs/guides/guardkit-workflow.md#pre-loop-decision-guide"
    ),
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
    sdk_timeout: Optional[int],
    enable_pre_loop: Optional[bool],
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
        1: Feature file not found or SDK not available
        2: Orchestration error
        3: Validation error
    """
    # Pre-flight check: Ensure SDK is available before any work
    _require_sdk()

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

    # Validate SDK timeout if provided
    if sdk_timeout is not None and not (60 <= sdk_timeout <= 3600):
        raise click.BadParameter(
            "SDK timeout must be between 60 and 3600 seconds",
            param_hint="'--sdk-timeout'",
        )

    logger.info(
        f"Starting feature orchestration: {feature_id} "
        f"(max_turns={max_turns}, stop_on_failure={stop_on_failure}, resume={resume}, fresh={fresh}, "
        f"sdk_timeout={sdk_timeout}, enable_pre_loop={enable_pre_loop})"
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
            sdk_timeout=sdk_timeout,
            enable_pre_loop=enable_pre_loop,
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
# Complete Command
# ============================================================================


@autobuild.command()
@click.argument("feature_id")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Simulate completion without making changes",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force completion even if tasks are incomplete",
)
@click.pass_context
@handle_cli_errors
def complete(
    ctx,
    feature_id: str,
    dry_run: bool,
    force: bool,
):
    """
    Complete all tasks in a feature and archive it.

    This command marks all incomplete tasks as complete, archives the feature
    YAML, cleans up resources, and displays handoff instructions for human review.

    \b
    Examples:
        guardkit autobuild complete FEAT-A1B2
        guardkit autobuild complete FEAT-A1B2 --dry-run
        guardkit autobuild complete FEAT-A1B2 --force

    \b
    Workflow:
        1. Validation: Verify feature exists and is ready
        2. Completion: Mark incomplete tasks as complete (TASK-FC-002)
        3. Archival: Archive feature and cleanup worktree (TASK-FC-003)
        4. Handoff: Display review instructions (TASK-FC-004)

    \b
    Exit Codes:
        0: Success (feature completed)
        1: Feature not found
        2: Completion error
        3: Validation error
    """
    logger.info(
        f"Starting feature completion: {feature_id} "
        f"(dry_run={dry_run}, force={force})"
    )

    try:
        # Initialize completion orchestrator
        orchestrator = FeatureCompleteOrchestrator(
            repo_root=Path.cwd(),
            dry_run=dry_run,
            force=force,
        )

        # Execute completion
        result = orchestrator.complete(feature_id=feature_id)

        # Display summary
        _display_complete_result(result)

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

    except FeatureCompleteError as e:
        console.print(f"[red]Completion error: {e}[/red]")
        logger.error(f"Feature completion error: {e}")
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


def _display_complete_result(result: FeatureCompleteResult) -> None:
    """
    Display feature completion result with Rich formatting.

    Parameters
    ----------
    result : FeatureCompleteResult
        Completion result
    """
    console.print()  # Blank line

    if result.success:
        console.print(
            Panel(
                f"[green]✓ Feature completed successfully[/green]\n\n"
                f"Feature: [cyan]{result.feature_id}[/cyan]\n"
                f"Status: {result.status}\n"
                f"Tasks: {result.tasks_completed}/{result.total_tasks} completed"
                + (
                    f"\nWorktree: [cyan]{result.worktree_path}[/cyan]"
                    if result.worktree_path
                    else ""
                ),
                title="Feature Completion Complete",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]✗ Feature completion failed[/red]\n\n"
                f"Feature: [cyan]{result.feature_id}[/cyan]\n"
                f"Status: {result.status}\n"
                f"Error: {result.error or 'N/A'}",
                title="Feature Completion Failed",
                border_style="red",
            )
        )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "autobuild",
    "task",
    "status",
    "feature",
    "complete",
    "_check_sdk_available",
    "_require_sdk",
]
