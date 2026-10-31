"""
AutoBuild CLI commands.

This module provides Click commands for AutoBuild orchestration, implementing
the CLI layer for Phase 1a of the AutoBuild system.

Example:
    $ guardkit autobuild task TASK-AB-001
    $ guardkit autobuild task TASK-AB-001 --max-turns 10 --verbose
    $ guardkit autobuild status TASK-AB-001
"""

import json
import logging
import os
import subprocess
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
from guardkit.orchestrator.agent_invoker import DEFAULT_SDK_TIMEOUT
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    FeatureOrchestrationError,
)
from guardkit.orchestrator.feature_loader import (
    FeatureLoader,
    FeatureNotFoundError,
    FeatureValidationError,
)
from guardkit.orchestrator.feature_complete import (
    FeatureCompleteOrchestrator,
    FeatureCompleteResult,
    FeatureCompleteError,
)
from guardkit.orchestrator.instrumentation.emitter import (
    CompositeBackend,
    JSONLFileBackend,
)
from guardkit.tasks.task_loader import TaskLoader
from guardkit.worktrees import WorktreeManager, Worktree
from guardkit.lib.project_git import run_git

console = Console()
logger = logging.getLogger(__name__)


# ============================================================================
# SDK Pre-flight Check
# ============================================================================


def _check_sdk_available() -> tuple[bool, str | None]:
    """
    Check if Claude Agent SDK is available.

    This function attempts to import the Claude Agent SDK to verify
    it is installed and accessible. Used for fail-fast validation
    before starting orchestration.

    Returns
    -------
    tuple[bool, str | None]
        ``(True, None)`` when the SDK imports cleanly.
        ``(False, str(error))`` when the import fails; the second element is
        the underlying ``ImportError`` message so callers can surface it
        (e.g. ``"No module named 'mcp.types'"`` in a namespace-shadow incident).
    """
    try:
        from claude_agent_sdk import query  # noqa: F401

        return (True, None)
    except ImportError as e:
        return (False, str(e))


def _require_sdk() -> None:
    """
    Require SDK availability or exit with helpful message.

    Commands reach this through :func:`_require_sdk_for_selected_harness`,
    which calls it only when the run will use the SDK. If the SDK is not
    available, it prints the underlying ``ImportError`` message and
    installation guidance before exiting with code 1. Surfacing the real
    error avoids the opaque "SDK not available" banner that hid the
    ``No module named 'mcp.types'`` symptom in TASK-REV-MCPS.

    Raises
    ------
    SystemExit
        Exits with code 1 if SDK is not available.
    """
    available, err = _check_sdk_available()
    if not available:
        console.print("[red]Error: Claude Agent SDK import failed[/red]")
        console.print()
        console.print(f"[yellow]Underlying error:[/yellow] {err}")
        console.print()
        console.print("Most common causes:")
        console.print(
            "  • Missing install: "
            "[cyan]pip install claude-agent-sdk[/cyan] or "
            "[cyan]pip install guardkit-py[autobuild][/cyan]"
        )
        console.print(
            "  • A namespace collision (an internal module shadows a "
            "transitive dep)."
        )
        console.print(
            "    If the error above names a submodule like 'mcp.types' or "
            "'anyio.X',"
        )
        console.print("    see .claude/rules/namespace-hygiene.md.")
        console.print()
        console.print("For more diagnostics: [dim]guardkit doctor[/dim]")
        sys.exit(1)


def _require_sdk_for_selected_harness() -> None:
    """Require the Claude Agent SDK only when this run will actually use it.

    Why this is conditional (2026-09-11): a command must not demand a
    dependency the work it is about to do will never use. The build system's
    default harness is guardkit's own DeepAgents/LangGraph factory, which never
    imports ``claude_agent_sdk``; the SDK is used only when it is asked for by
    name with ``GUARDKIT_HARNESS=sdk``. The unconditional check had never
    bitten because the SDK happens to be installed in the operator's own
    environment — a repository's sandbox, which installs the factory and not
    the SDK, is the first place the harness default has ever actually
    mattered, and there the check refused every build in under a second.

    Which harness this run will use is answered by the selector's own
    :func:`~guardkit.orchestrator.harness.selector.resolve_harness_name`, the
    same function :func:`select_harness` asks when it builds the harness, so
    the default is never re-implemented here.

    Raises
    ------
    SystemExit
        Exit code 1 when the SDK was asked for by name and cannot be imported
        (the banner and wording of :func:`_require_sdk`, unchanged). Exit code
        3 when ``GUARDKIT_HARNESS`` names a harness that does not exist, so a
        typo is refused here in one sentence instead of failing later and
        deeper inside the orchestrator, after the build's worktree and branch
        have been made.
    """
    from guardkit.orchestrator.harness.selector import (
        SUPPORTED_HARNESSES,
        resolve_harness_name,
    )

    harness = resolve_harness_name()

    if harness not in SUPPORTED_HARNESSES:
        expected = " or ".join(repr(h) for h in SUPPORTED_HARNESSES)
        console.print(
            f"[red]Error: GUARDKIT_HARNESS is set to {harness!r}, which is not "
            f"a harness this build system has. Expected {expected}.[/red]"
        )
        sys.exit(3)

    if harness == "sdk":
        _require_sdk()


# ============================================================================
# Base-branch detection (TASK-FIX-WTBC)
# ============================================================================


def _detect_base_branch(
    default: str = "main", cwd: Optional[Path] = None
) -> str:
    """
    Read the current branch of ``cwd`` (defaults to the process cwd).

    When ``guardkit autobuild task``/``feature`` is invoked from a git
    worktree on a non-main branch, the inner ``autobuild/<id>`` worktree must
    branch from the caller's HEAD, not from main, to preserve fixture-branch
    isolation (TASK-REV-HM09 §2). This helper reads the calling cwd's current
    branch so the CLI can pass it through to ``orchestrate(base_branch=...)``.

    Parameters
    ----------
    default : str, optional
        Branch to return when detection fails or HEAD is detached
        (default: ``"main"``).
    cwd : Optional[Path], optional
        Directory to inspect. ``None`` (default) inspects the process cwd —
        the right behaviour for the create path. ``_find_worktree`` passes the
        worktree path to read *its* branch for status display.

    Returns
    -------
    str
        The current branch name, or ``default`` when ``git rev-parse`` fails
        or reports a detached HEAD (``"HEAD"``).
    """
    try:
        result = run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            check=True,
        )
        branch = result.stdout.strip()
        # Detached HEAD reports the literal "HEAD" — fall back to default.
        if branch and branch != "HEAD":
            return branch
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return default


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
    default="claude-opus-5-5",
    help="Claude model to use",
    show_default=True,
)
@click.option(
    "--coach-model",
    "coach_model",
    default=None,
    help=(
        "Optional model override for the Coach role. When set, Coach (and "
        "coach_test) invocations route to this model while Player and "
        "specialist invocations stay on --model. TASK-FIX-COACHBUDG01 / "
        "TASK-HMIG-013 — substrate-quality lever for the F17 verdict-"
        "emission reliability gap. Example: --model qwen36-workhorse "
        "--coach-model gemma4:26b."
    ),
)
@click.option(
    "--base-branch",
    "base_branch",
    default=None,
    help=(
        "Branch to create the worktree from. "
        "Precedence: --base-branch > current branch of the calling cwd > 'main'. "
        "Defaults to the cwd's current branch so autobuild run from a non-main "
        "worktree branches from that worktree's HEAD (TASK-FIX-WTBC)."
    ),
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
    help="SDK timeout in seconds. Defaults to task frontmatter autobuild.sdk_timeout or 1200",
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
    "--ablation",
    "ablation_mode",
    is_flag=True,
    default=False,
    help="Run in ablation mode (no Coach feedback) for testing Block research findings",
)
@click.option(
    "--enable-context/--no-context",
    "enable_context",
    default=True,
    help="Enable/disable memory context retrieval (default: enabled)",
)
@click.option(
    "--timeout-multiplier",
    "timeout_multiplier",
    default=None,
    type=float,
    help=(
        "Timeout multiplier for all autobuild timeouts (default: auto-detect). "
        "Auto-detects 4.0 for localhost/vLLM backends. "
        "Override via GUARDKIT_TIMEOUT_MULTIPLIER env var."
    ),
)
@click.pass_context
@handle_cli_errors
def task(
    ctx,
    task_id: str,
    max_turns: int,
    model: str,
    coach_model: Optional[str],
    base_branch: Optional[str],
    verbose: bool,
    resume: bool,
    mode: Optional[str],
    sdk_timeout: Optional[int],
    no_pre_loop: bool,
    skip_arch_review: bool,
    no_checkpoints: bool,
    ablation_mode: bool,
    enable_context: bool,
    timeout_multiplier: Optional[float],
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
        guardkit autobuild task TASK-AB-001 --model claude-sonnet-5-5
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
        1: Task file not found, or GUARDKIT_HARNESS=sdk with the SDK missing
        2: Orchestration error
        3: Invalid arguments (including an unknown GUARDKIT_HARNESS value)
    """
    # Pre-flight check: require the Claude Agent SDK before any work, but only
    # when this run is the one that uses it (2026-09-11 — see
    # _require_sdk_for_selected_harness).
    _require_sdk_for_selected_harness()

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

    # Resolve SDK timeout: CLI flag > task frontmatter > default
    effective_sdk_timeout = sdk_timeout
    sdk_timeout_is_override = sdk_timeout is not None
    if effective_sdk_timeout is None:
        sdk_timeout_is_override = "sdk_timeout" in autobuild_config
        effective_sdk_timeout = autobuild_config.get(
            "sdk_timeout", DEFAULT_SDK_TIMEOUT
        )
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

    # Display warning banner if ablation mode is active
    if ablation_mode:
        console.print()
        console.print("[bold red]" + "="*80 + "[/bold red]")
        console.print("[bold red]⚠️  ABLATION MODE ACTIVE[/bold red]")
        console.print("[bold red]" + "="*80 + "[/bold red]")
        console.print("[yellow]Coach feedback is DISABLED. This mode is for testing only.[/yellow]")
        console.print("[yellow]Expected outcomes:[/yellow]")
        console.print("[yellow]  • Higher failure rate (no feedback loop)[/yellow]")
        console.print("[yellow]  • Lower code quality (no architectural review)[/yellow]")
        console.print("[yellow]  • More turns needed (no guidance toward convergence)[/yellow]")
        console.print("[yellow]This validates Block AI research findings.[/yellow]")
        console.print("[bold red]" + "="*80 + "[/bold red]")
        console.print()

    # TASK-FIX-VL05: Resolve timeout multiplier
    from guardkit.orchestrator.agent_invoker import detect_timeout_multiplier

    effective_timeout_multiplier = timeout_multiplier
    if effective_timeout_multiplier is None:
        effective_timeout_multiplier = detect_timeout_multiplier()
    logger.info(f"Timeout multiplier: {effective_timeout_multiplier}x")

    # Display startup banner
    resume_text = " [yellow](Resuming)[/yellow]" if resume else ""
    mode_display = effective_mode.upper()
    pre_loop_display = "[red]OFF[/red]" if no_pre_loop else "[green]ON[/green]"
    ablation_display = "[red]ENABLED[/red]" if ablation_mode else "[green]DISABLED[/green]"
    multiplier_display = (
        f"\nTimeout Multiplier: [yellow]{effective_timeout_multiplier}x[/yellow]"
        if effective_timeout_multiplier != 1.0
        else ""
    )
    if not ctx_obj.get("quiet", False):
        console.print(
            Panel(
                f"[bold]AutoBuild Task Orchestration[/bold]\n\n"
                f"Task: [cyan]{task_id}[/cyan]\n"
                f"Max Turns: {max_turns}\n"
                f"Model: {model}\n"
                f"Mode: [magenta]{mode_display}[/magenta]\n"
                f"Pre-Loop: {pre_loop_display}\n"
                f"Ablation: {ablation_display}\n"
                f"SDK Timeout: {effective_sdk_timeout}s{multiplier_display}{resume_text}",
                title="GuardKit AutoBuild",
                border_style="blue",
            )
        )

    # Phase 2: Initialize orchestrator
    # Note: enable_pre_loop defaults to True for task-build, --no-pre-loop disables it
    enable_pre_loop = not no_pre_loop
    enable_checkpoints = not no_checkpoints

    logger.info(
        f"Initializing orchestrator (enable_pre_loop={enable_pre_loop}, "
        f"skip_arch_review={effective_skip_arch_review}, "
        f"enable_checkpoints={enable_checkpoints}, "
        f"ablation_mode={ablation_mode}, "
        f"timeout_multiplier={effective_timeout_multiplier})"
    )

    # Create instrumentation emitter (TASK-OBS-4899)
    events_dir = Path(".guardkit/autobuild") / task_id
    emitter = CompositeBackend(backends=[JSONLFileBackend(events_dir=events_dir)])

    try:
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=max_turns,
            resume=resume,
            enable_pre_loop=enable_pre_loop,
            development_mode=effective_mode,
            sdk_timeout=effective_sdk_timeout,
            sdk_timeout_is_override=sdk_timeout_is_override,
            skip_arch_review=effective_skip_arch_review,
            enable_checkpoints=enable_checkpoints,
            ablation_mode=ablation_mode,
            enable_context=enable_context,
            timeout_multiplier=effective_timeout_multiplier,
            model=model,  # TASK-FIX-MODELPLUMB: thread --model to harness construction (load-bearing for LangGraph)
            coach_model=coach_model,  # TASK-FIX-COACHBUDG01: optional per-role override for Coach
            emitter=emitter,  # TASK-OBS-4899
        )

        # Resolve base branch: --base-branch > cwd HEAD > "main" (TASK-FIX-WTBC)
        effective_base_branch = base_branch or _detect_base_branch()
        logger.info(f"Base branch for worktree: {effective_base_branch}")

        # Phase 3: Execute orchestration
        logger.info(f"Starting orchestration for {task_id} (resume={resume})")
        result = orchestrator.orchestrate(
            task_id=task_id,
            requirements=task_data["requirements"],
            acceptance_criteria=task_data["acceptance_criteria"],
            base_branch=effective_base_branch,
            task_file_path=task_data.get("file_path"),  # Pass task file for state persistence
        )

        # Phase 4: Display results
        _display_result(result, verbose=verbose)

        # Exit with appropriate code
        sys.exit(0 if result.success else 2)

    finally:
        # Emitter lifecycle: flush and close (TASK-OBS-4899)
        import asyncio
        try:
            asyncio.run(emitter.flush())
        except Exception as exc:
            logger.warning("Failed to flush emitter: %s", exc)
        try:
            asyncio.run(emitter.close())
        except Exception as exc:
            logger.warning("Failed to close emitter: %s", exc)


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
    "--model",
    default="claude-opus-5-5",
    help="Claude model to use",
    show_default=True,
)
@click.option(
    "--coach-model",
    "coach_model",
    default=None,
    help=(
        "Optional model override for the Coach role. When set, Coach (and "
        "coach_test) invocations route to this model while Player and "
        "specialist invocations stay on --model. TASK-FIX-COACHBUDG01 / "
        "TASK-HMIG-013 — substrate-quality lever for the F17 verdict-"
        "emission reliability gap. Example: --model qwen36-workhorse "
        "--coach-model gemma4:26b."
    ),
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
    "--refresh",
    is_flag=True,
    help=(
        "Rebase worktree onto the base branch before resuming (implies "
        "--resume). Refresh uses the base branch already on this machine: "
        "fetch it yourself first if you need the remote's latest. Target "
        "resolution: local <base> when it is ahead of origin/<base> "
        "(unpushed operator fixes) or no origin/<base> is here, else "
        "origin/<base>. Runs with --autostash so autobuild artifacts don't "
        "abort the rebase."
    ),
)
@click.option(
    "--task",
    "specific_task",
    default=None,
    help="Run specific task within feature (e.g., TASK-AUTH-001)",
)
@click.option(
    "--base-branch",
    "base_branch",
    default=None,
    help=(
        "Branch to create the shared feature worktree from. "
        "Precedence: --base-branch > current branch of the calling cwd > 'main'. "
        "Defaults to the cwd's current branch so autobuild run from a non-main "
        "worktree branches from that worktree's HEAD (TASK-FIX-WTBC)."
    ),
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
    help="SDK timeout in seconds. Defaults to feature YAML autobuild.sdk_timeout or 1200",
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
@click.option(
    "--enable-context/--no-context",
    "enable_context",
    default=True,
    help="Enable/disable memory context retrieval (default: enabled)",
)
@click.option(
    "--task-timeout",
    "task_timeout",
    default=2400,
    type=int,
    help=(
        "Per-task timeout in seconds for wave execution (default: 2400 = 40 min). "
        "A located review finding can add one builder turn (the repair turn), "
        "so leave room for two turns. See docs/deep-dives/autobuild_local_vllm.md."
    ),
    show_default=True,
)
@click.option(
    "--timeout-multiplier",
    "timeout_multiplier",
    default=None,
    type=float,
    help=(
        "Timeout multiplier for all autobuild timeouts (default: auto-detect). "
        "Auto-detects 4.0 for localhost/vLLM backends. "
        "Override via GUARDKIT_TIMEOUT_MULTIPLIER env var."
    ),
)
@click.option(
    "--max-parallel",
    "max_parallel",
    default=None,
    type=int,
    help=(
        "Max parallel tasks per wave (default: auto-detect). "
        "Precedence: GUARDKIT_MAX_PARALLEL_TASKS env var > this flag > "
        "feature-YAML orchestration.recommended_parallel > auto-detect "
        "(TASK-AB-WAVECTL01). The feature-YAML tier may only LOWER the "
        "auto-detect result, never raise it. Auto-detect defaults to 1 for "
        "local backends (TASK-VPT-001: reduced from 2 due to KV cache "
        "contention; the YAML cannot raise this cap), unlimited otherwise."
    ),
)
@click.option(
    "--max-parallel-strategy",
    "max_parallel_strategy",
    default="static",
    type=click.Choice(["static", "dynamic"]),
    help=(
        "Strategy for max_parallel: 'static' uses fixed value (default), "
        "'dynamic' checks GPU memory before each wave (TASK-VRF-006)."
    ),
)
@click.option(
    "--skip-validation",
    "skip_validation",
    is_flag=True,
    help="Skip pre-flight frontmatter validation (not recommended).",
)
@click.option(
    "--task-log-interval",
    "task_log_interval",
    default=60,
    type=int,
    help="Seconds between per-task progress log snapshots (default: 60)",
    show_default=True,
)
@click.pass_context
@handle_cli_errors
def feature(
    ctx,
    feature_id: str,
    max_turns: int,
    model: str,
    coach_model: Optional[str],
    resume: bool,
    fresh: bool,
    refresh: bool,
    specific_task: Optional[str],
    base_branch: Optional[str],
    verbose: bool,
    sdk_timeout: Optional[int],
    enable_pre_loop: Optional[bool],
    enable_context: bool,
    task_timeout: int,
    timeout_multiplier: Optional[float],
    max_parallel: Optional[int],
    max_parallel_strategy: str,
    skip_validation: bool,
    task_log_interval: int,
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
        guardkit autobuild feature FEAT-A1B2 --task TASK-AUTH-002
        guardkit autobuild feature FEAT-A1B2 --resume
        guardkit autobuild feature FEAT-A1B2 --refresh
        guardkit autobuild feature FEAT-A1B2 --fresh

    \b
    Resume Behavior:
        - If incomplete state detected and no flags: prompts user to resume, update, or start fresh
        - --resume: skip prompt, resume from last saved state
        - --refresh: rebase worktree onto the base branch already on this
          machine (fetch it yourself first), then resume (implies --resume)
        - --fresh: skip prompt, start from scratch (clears previous state)
        - Cannot use both --resume/--refresh and --fresh together

    \b
    Workflow:
        1. Load feature file from .guardkit/features/
        2. Validate all task markdown files exist
        3. Create shared worktree for entire feature
        4. Execute tasks wave by wave (respecting parallel_groups)
        5. Update feature YAML after each task
        6. Preserve worktree for human review

    \b
    Preflight Warnings (TASK-GK-PR-001):
        Before wave 1 dispatch, the orchestrator probes every queued task's
        ## Files to Modify declarations against the filesystem. If any path
        does not resolve under repo_root or worktree_path you will see:

            WARNING: TYPO in TASK-XXX line N (## Files to Modify):
              declared: src/example/typo.py
              not on disk under repo_root or worktree_path
              closest matches (top 3):
                - src/example/real.py (similarity 0.74)

        Default behaviour is non-blocking — orchestration proceeds and
        plan-audit catches the typo at Player turn 1. To abort instead,
        set ``preflight_strict: true`` in the feature YAML.

    \b
    Exit Codes:
        0: Success (all tasks completed)
        1: Feature file not found, or GUARDKIT_HARNESS=sdk with the SDK missing
        2: Orchestration error
        3: Validation error, or an unknown GUARDKIT_HARNESS value
    """
    # Pre-flight check: require the Claude Agent SDK before any work, but only
    # when this run is the one that uses it (2026-09-11 — see
    # _require_sdk_for_selected_harness).
    _require_sdk_for_selected_harness()

    # Inherit verbose from parent if set (ctx.obj can be None in testing)
    ctx_obj = ctx.obj or {}
    verbose = verbose or ctx_obj.get("verbose", False)

    # Validate mutually exclusive flags
    if resume and fresh:
        console.print("[red]Error: Cannot use both --resume and --fresh flags together[/red]")
        console.print("\nChoose one:")
        console.print("  --resume   Resume from last saved state")
        console.print("  --refresh  Rebase on latest main and resume")
        console.print("  --fresh    Start from scratch, ignoring saved state")
        sys.exit(3)

    if refresh and fresh:
        console.print("[red]Error: Cannot use both --refresh and --fresh flags together[/red]")
        console.print("\nChoose one:")
        console.print("  --refresh  Rebase on latest main and resume")
        console.print("  --fresh    Start from scratch, ignoring saved state")
        sys.exit(3)

    # Resolve max_parallel: env var > CLI flag > feature-YAML > auto-detect.
    # The env/flag/auto-detect tiers are resolved here; the feature-YAML tier
    # (orchestration.recommended_parallel) is applied by FeatureOrchestrator
    # once the feature file is loaded, only when the value below came from
    # auto-detect — the recorded source makes that distinction possible —
    # and only to LOWER it, never raise it (TASK-AB-WAVECTL01).
    from guardkit.orchestrator.parallel_strategy import (
        PARALLEL_SOURCE_AUTO_DETECT,
        PARALLEL_SOURCE_ENV,
        PARALLEL_SOURCE_FLAG,
        MaxParallelMode,
        ParallelConfig,
    )

    env_max_parallel = os.environ.get("GUARDKIT_MAX_PARALLEL_TASKS")
    max_parallel_source = PARALLEL_SOURCE_AUTO_DETECT
    if env_max_parallel is not None:
        max_parallel = int(env_max_parallel)
        max_parallel_source = PARALLEL_SOURCE_ENV
    elif max_parallel is not None:
        max_parallel_source = PARALLEL_SOURCE_FLAG
    else:
        # Auto-detect: default to 1 for local backends (TASK-VPT-001: was 2, reduced due to KV cache contention)
        from guardkit.orchestrator.agent_invoker import detect_timeout_multiplier
        detected_multiplier = timeout_multiplier if timeout_multiplier is not None else detect_timeout_multiplier()
        if detected_multiplier > 1.0:
            max_parallel = 1

    # TASK-VRF-006: Build ParallelConfig from CLI args
    if max_parallel_strategy == "dynamic":
        parallel_config = ParallelConfig(
            mode=MaxParallelMode.DYNAMIC,
            static_value=max_parallel,  # fallback when GPU pressure is UNKNOWN
            source=max_parallel_source,
        )
    else:
        parallel_config = ParallelConfig(
            mode=MaxParallelMode.STATIC,
            static_value=max_parallel,
            source=max_parallel_source,
        )

    logger.info(
        f"Starting feature orchestration: {feature_id} "
        f"(max_turns={max_turns}, "
        f"resume={resume}, fresh={fresh}, refresh={refresh}, "
        f"sdk_timeout={sdk_timeout}, enable_pre_loop={enable_pre_loop}, "
        f"timeout_multiplier={timeout_multiplier}, max_parallel={max_parallel}, "
        f"max_parallel_strategy={max_parallel_strategy})"
    )

    # Create instrumentation emitter (TASK-INST-013)
    events_dir = Path(".guardkit/autobuild") / feature_id
    emitter = CompositeBackend(backends=[JSONLFileBackend(events_dir=events_dir)])

    try:
        # Initialize feature orchestrator
        orchestrator = FeatureOrchestrator(
            repo_root=Path.cwd(),
            max_turns=max_turns,
            resume=resume,
            fresh=fresh,
            refresh=refresh,
            verbose=verbose,
            quiet=ctx_obj.get("quiet", False),
            sdk_timeout=sdk_timeout,
            enable_pre_loop=enable_pre_loop,
            enable_context=enable_context,
            task_timeout=task_timeout,
            timeout_multiplier=timeout_multiplier,
            max_parallel=max_parallel,
            parallel_config=parallel_config,
            skip_validation=skip_validation,
            emitter=emitter,
            task_log_interval=task_log_interval,
            model=model,  # TASK-FIX-LGFM: thread --model to per-task AutoBuildOrchestrator (load-bearing for LangGraph)
            coach_model=coach_model,  # TASK-FIX-COACHBUDG01: optional per-role override for Coach
        )

        # Resolve base branch: --base-branch > cwd HEAD > "main" (TASK-FIX-WTBC)
        effective_base_branch = base_branch or _detect_base_branch()
        logger.info(f"Base branch for feature worktree: {effective_base_branch}")

        # Execute feature orchestration
        result = orchestrator.orchestrate(
            feature_id=feature_id,
            base_branch=effective_base_branch,
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

    finally:
        # Emitter lifecycle: flush and close (TASK-INST-013)
        import asyncio
        try:
            asyncio.run(emitter.flush())
        except Exception as exc:
            logger.warning("Failed to flush emitter: %s", exc)
        try:
            asyncio.run(emitter.close())
        except Exception as exc:
            logger.warning("Failed to close emitter: %s", exc)


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
    help="Accepted for existing commands; completion is never refused",
)
@click.option(
    "--verify",
    is_flag=True,
    help=(
        "Re-run the project's test suite in the merge-target repo after "
        "completion and report the result"
    ),
)
@click.option(
    "--verify-cmd",
    default=None,
    help=(
        "Explicit verification command (implies --verify). Default "
        "resolution: feature smoke_gates.command, else the project's "
        "declared full check (.guardkit/config.yaml toolchain)"
    ),
)
@click.option(
    "--verify-timeout",
    type=int,
    default=None,
    help="Seconds before the verification run is killed (default: 600)",
)
@click.pass_context
@handle_cli_errors
def complete(
    ctx,
    feature_id: str,
    dry_run: bool,
    force: bool,
    verify: bool,
    verify_cmd: Optional[str],
    verify_timeout: Optional[int],
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
        guardkit autobuild complete FEAT-A1B2 --verify
        guardkit autobuild complete FEAT-A1B2 --verify-cmd "make test"

    \b
    Workflow:
        1. Validation: Verify feature exists and is ready
        2. Completion: Mark incomplete tasks as complete (TASK-FC-002)
        3. Archival: Archive feature and cleanup worktree (TASK-FC-003)
        4. Handoff: Display review instructions (TASK-FC-004)
        5. Verification (if --verify): re-run the test suite (TASK-AB-VERIFYCLI01)

    \b
    Exit Codes:
        0: Success (feature completed; the tests did not fail, if requested)
        1: Feature not found
        2: Completion error
        3: Validation error
        4: Completed, but the project's tests ran and FAILED
    """
    verify = verify or verify_cmd is not None
    logger.info(
        f"Starting feature completion: {feature_id} "
        f"(dry_run={dry_run}, force={force}, verify={verify})"
    )

    try:
        repo_root = Path.cwd()

        # Resolve the verification command BEFORE completion — the archival
        # phase owns the feature YAML the smoke command lives in.
        verify_plan = None
        if verify:
            verify_plan = _resolve_completion_verification(
                repo_root, feature_id, verify_cmd
            )

        # Initialize completion orchestrator
        orchestrator = FeatureCompleteOrchestrator(
            repo_root=repo_root,
            dry_run=dry_run,
            force=force,
        )

        # Execute completion
        result = orchestrator.complete(feature_id=feature_id)

        # Display summary
        _display_complete_result(result)

        if not result.success:
            sys.exit(2)

        # Post-completion verification (TASK-AB-VERIFYCLI01). Report-only:
        # a failure never un-completes anything.
        if verify:
            command, source, declaration = verify_plan
            if dry_run:
                console.print(
                    f"[yellow]--dry-run:[/yellow] would verify via "
                    f"{source}: [cyan]{command or '(none found)'}[/cyan]"
                )
                sys.exit(0)
            from guardkit.orchestrator.completion_verification import (
                DEFAULT_VERIFY_TIMEOUT,
                run_completion_verification,
            )

            verification = run_completion_verification(
                repo_root,
                command,
                source,
                declaration=declaration,
                timeout=verify_timeout or DEFAULT_VERIFY_TIMEOUT,
            )
            _display_verification_result(verification)

            # Report-only towards completion (nothing un-completes); the
            # process exits 4 only when the project's tests ran and failed.
            sys.exit(4 if verification.status == "failed" else 0)
        sys.exit(0)

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

    # Detect the worktree's own branch for display (or default to main).
    base_branch = _detect_base_branch(cwd=worktree_path)

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
                f"Tasks: {result.tasks_completed} approved, {result.tasks_deferred} deferred; deferred work not executed"
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


def _resolve_completion_verification(
    repo_root: Path,
    feature_id: str,
    verify_cmd: Optional[str],
):
    """Resolve the post-completion verification plan (TASK-AB-VERIFYCLI01).

    Shares ``resolve_verify_command`` with the slash-command workflow's
    verify step — one implementation, two entry points
    (cli-wrapper-shares-client-acquisition-path).
    """
    from guardkit.orchestrator.completion_verification import resolve_verify_command

    smoke_command = None
    if not verify_cmd:
        try:
            feature = FeatureLoader.load_feature(feature_id, repo_root=repo_root)
            if feature.smoke_gates is not None:
                smoke_command = feature.smoke_gates.command
        except Exception:
            # Command resolution is best-effort: fall through to the
            # declared check; the verification itself still runs.
            logger.debug(
                "Could not load feature %s for smoke command resolution",
                feature_id,
                exc_info=True,
            )
    return resolve_verify_command(
        repo_root, smoke_command=smoke_command, override=verify_cmd
    )


def _display_verification_result(verification) -> None:
    """Render the verification outcome.

    The verdict line derives from ``verification.status`` — the enforcement
    source — never from "the completion succeeded"
    (display-must-derive-from-enforcement-source-not-proxy). Command and
    output text are markup-escaped: pytest parametrized IDs (``test[x-y]``)
    read as Rich tags otherwise and get silently dropped from the display.
    """
    from rich.markup import escape

    console.print()
    if verification.status == "passed":
        console.print(
            Panel(
                f"[green]✓ Post-completion verification passed[/green]\n\n"
                f"Command: [cyan]{escape(verification.command)}[/cyan]\n"
                f"Ran in: [cyan]{escape(verification.cwd)}[/cyan]\n"
                f"Result: {escape(verification.detail)}",
                title="Verification Passed",
                border_style="green",
            )
        )
        return
    label = (
        "FAILED" if verification.status == "failed" else "UNVERIFIED"
    )
    body = (
        f"[red]✗ Post-completion verification {label}[/red]\n\n"
        f"Command: [cyan]{escape(verification.command or '(none resolved)')}[/cyan]\n"
        f"Ran in: [cyan]{escape(verification.cwd)}[/cyan]\n"
        f"Result: {escape(verification.detail)}\n\n"
        "The completion/merge is left in place — inspect and fix before "
        "shipping."
    )
    if verification.output_tail:
        body += f"\n\n[dim]{escape(verification.output_tail[-800:])}[/dim]"
    console.print(Panel(body, title=f"Verification {label}", border_style="red"))


@autobuild.command("merge")
@click.argument("feature_id")
@click.option(
    "--target",
    default="main",
    show_default=True,
    help="Branch to merge the feature branch into.",
)
@click.option(
    "--branch",
    "branch",
    default=None,
    help=(
        "The branch to merge. Without it the feature's own branch, "
        "autobuild/FEATURE_ID, is merged exactly as before. A repair "
        "build's commits live on the branch that build made, so its merge "
        "names that branch here. The report's branch field says which "
        "branch was merged."
    ),
)
@click.option(
    "--expect-main-sha",
    "expect_main_sha",
    default=None,
    help=(
        "The commit the target branch pointed at when the checks ran. "
        "If the target has moved since, the merge is refused loudly — "
        "nothing half-done."
    ),
)
@click.option(
    "--verify/--no-verify",
    "verify",
    default=True,
    show_default=True,
    help=(
        "Re-run the repo's test suite on the merged result."
    ),
)
@click.option(
    "--verify-timeout",
    type=int,
    default=600,
    show_default=True,
    help="Seconds before the post-merge verification run is killed.",
)
@click.option(
    "--in-worktree",
    "in_worktree",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help=(
        "A working folder of this repository to do the merge in — made "
        "beforehand, at the commit being joined onto. The checkout, the "
        "merge and the checks all happen there, and the repository's main "
        "copy is never switched or merged into. Without it everything "
        "happens where the command was run, exactly as before."
    ),
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Print the merge report as JSON on stdout.",
)
def merge(
    feature_id: str,
    target: str,
    branch: Optional[str],
    expect_main_sha: Optional[str],
    verify: bool,
    verify_timeout: int,
    in_worktree: Optional[Path],
    as_json: bool,
):
    """
    Merge the build's branch into the target branch — the merge word as a
    mechanism. Without --branch that is autobuild/FEATURE_ID, exactly as it
    has always been; a repair build names the branch it made.

    Run from the repository root. The branch is ALWAYS kept after merging
    (it is the rollback path). A dirty tree, a missing branch, or a target
    that has moved since the checks ran each refuse the merge before
    anything is touched. A conflict aborts cleanly and reports the files.

    With verification on, the project's full check (as declared on the
    target branch) runs once on the merged result. If it cannot run, the
    merge still happens, the report says the check was not run, and the
    command exits 4: a check that did not run is not a pass.

    \b
    Examples:
        guardkit autobuild merge FEAT-E613
        guardkit autobuild merge FEAT-E613 --expect-main-sha 3f2c1a9
        guardkit autobuild merge FEAT-E613 --branch fix/TASK-E613-FIX1-1a2b3c4d
        guardkit autobuild merge FEAT-E613 --no-verify --json

    \b
    Exit Codes:
        0: Merged (and the full check passed, when verification is on)
        1: Unexpected error
        2: Refused (dirty tree / target moved / branch missing)
        3: Conflict (merge aborted, tree left clean, branch kept)
        4: Merged, but the full check failed or could not run
    """
    from guardkit.orchestrator.merge_executor import (
        OUTCOME_CONFLICT,
        OUTCOME_MERGED,
        OUTCOME_REFUSED,
        execute_merge,
    )

    try:
        report = execute_merge(
            repo_root=Path.cwd(),
            feature_id=feature_id,
            target_branch=target,
            expect_target_sha=expect_main_sha,
            verify=verify,
            verify_timeout=verify_timeout,
            branch=branch,
            working_folder=in_worktree,
        )
    except Exception as e:  # noqa: BLE001 — the CLI boundary reports plainly
        console.print(f"[red]Unexpected error: {e}[/red]")
        logger.error(f"autobuild merge failed unexpectedly: {e}", exc_info=True)
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        for line in report.receipt_lines():
            # markup=False: pytest node ids like test[x-y] read as Rich tags
            # otherwise and get silently dropped from the display.
            console.print(line, soft_wrap=True, markup=False)

    if report.outcome == OUTCOME_REFUSED:
        sys.exit(2)
    if report.outcome == OUTCOME_CONFLICT:
        sys.exit(3)
    if report.outcome == OUTCOME_MERGED and verify and not report.verify_ok:
        sys.exit(4)
    sys.exit(0)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "autobuild",
    "task",
    "status",
    "feature",
    "complete",
    "merge",
    "_check_sdk_available",
    "_require_sdk",
]
