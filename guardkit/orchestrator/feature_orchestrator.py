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
import json
import logging
import os
import re
import resource
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, OrchestrationResult
from guardkit.orchestrator.agent_invoker import DEFAULT_SDK_TIMEOUT
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureTask,
    FeatureNotFoundError,
    FeatureValidationError,
    SmokeGates,
    derive_bootstrap_extras,
)
from guardkit.orchestrator import evidence_repos as evidence_repos_lib
from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.run_evidence import request_from_repo
from guardkit.orchestrator.smoke_gates import (
    SmokeGateResult,
    run_smoke_gate,
    should_fire_for_wave,
)
from guardkit.orchestrator.stale_test_attribution import (
    extract_failing_test_lines,
    smoke_gate_header,
    stale_test_notes,
)
from guardkit.orchestrator.repair_round import RepairRound, begin_repair_round
from guardkit.orchestrator.feature_check import (
    FeatureCheckAttempt,
    FeatureCheckOutcome,
    FeatureCheckRepair,
    stopped_because_line,
    build_feature_check_feedback,
    candidate_sha as feature_check_candidate_sha,
    feature_request_words,
    load_feature_check_declaration,
    merge_not_checked,
    parse_project_check_line,
    resolve_max_retries as feature_check_max_retries,
    run_feature_check_command,
    scenario_titles as feature_scenario_titles,
    tail_lines as feature_check_tail,
    write_feature_check_receipt,
    OUTCOME_COULD_NOT_RUN as FEATURE_CHECK_COULD_NOT_RUN,
    OUTCOME_FAILED as FEATURE_CHECK_FAILED,
    OUTCOME_PASSED as FEATURE_CHECK_PASSED,
    FAILURE_KIND_COULD_NOT_START,
    FAILURE_KIND_EXIT_NONZERO,
    FAILURE_KIND_TIMED_OUT,
    PUBLIC_LABEL as FEATURE_CHECK_LABEL,
    output_size as feature_check_output_size,
)
from guardkit.orchestrator.code_checks import (
    build_code_checks_summary,
    latest_review_record as code_checks_latest_review,
    summarise_task as summarise_code_checks_task,
    write_code_checks_summary,
)

from guardkit.orchestrator.feature_validator import (
    validate_feature_preflight,
    validate_feature_environment,
    format_preflight_report,
)
from guardkit.orchestrator.environment_bootstrap import (
    ProjectEnvironmentDetector,
    EnvironmentBootstrapper,
    BootstrapResult,
    _create_worktree_uv_sources_symlinks,
    _resolve_uv_sources_symlinks,
)
from guardkit.orchestrator.toolchain_declaration import ToolchainDeclarationError
from guardkit.models.task_types import TaskType, normalise_task_type
from guardkit.tasks.task_loader import TaskLoader
from guardkit.orchestrator.parallel_strategy import (
    MaxParallelMode,
    ParallelConfig,
    apply_feature_recommended_parallel,
    bound_concurrency,
    collect_wave_task_paths,
    resolve_max_parallel,
    tasks_run_at_the_same_time,
)
from guardkit.worktrees import (
    WorktreeManager,
    Worktree,
    WorktreeCreationError,
    warn_pth_leaks,
)
from guardkit.cli.display import WaveProgressDisplay

# Import instrumentation (TASK-INST-004)
from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.schemas import (
    FeatureCheckAttemptEvent,
    WaveCompletedEvent,
)
from guardkit.lib.project_git import run_git

logger = logging.getLogger(__name__)
console = Console()

#: What ``--refresh`` says, here and in its help text (13 October 2026).
REFRESH_USES_LOCAL_BASE = (
    "Refresh uses the base branch already on this machine: fetch it yourself "
    "first if you need the remote's latest."
)


def _path_as_told_from(path: Path, root: Path) -> str:
    """Where a file is, said from ``root``. Never raises.

    Inside ``root`` this is the plain relative path. A file that is NOT under
    ``root`` is said by the steps from ``root`` to it, and failing that in
    full.
    """
    try:
        return str(Path(path).relative_to(root))
    except Exception:  # noqa: BLE001 — a path is never worth a build
        pass
    try:
        return os.path.relpath(str(path), str(root))
    except Exception:  # noqa: BLE001
        return str(path)


def _estimate_timeout_factor() -> float:
    """Safety factor applied to a task's own ``estimated_minutes`` when
    deriving the per-task timeout floor (red-baseline retro, L12 item 3).

    A large task budgeted below its own estimate is guaranteed to time out,
    and the timeout MASKS the real failure (FEAT-VOICE-003 run 1: the 113-min
    UI task was budgeted below its own estimate — the flat 50-min floor timed
    it out mid-run,
    hiding the true — test — failure until run 2). Default 1.5×; operator
    policy via ``GUARDKIT_AUTOBUILD_ESTIMATE_TIMEOUT_FACTOR``. A non-positive
    or unparseable value falls back to the default.
    """
    raw = os.environ.get("GUARDKIT_AUTOBUILD_ESTIMATE_TIMEOUT_FACTOR", "1.5")
    try:
        factor = float(raw)
    except (TypeError, ValueError):
        return 1.5
    return factor if factor > 0 else 1.5


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
    sdk_ceiling_hits: int = 0                                       # TASK-VPR-003
    sdk_total_invocations: int = 0                                  # TASK-VPR-003
    sdk_turns_per_invocation: List[int] = field(default_factory=list)  # TASK-VPR-003
    # TASK-FPTC-003: Reason string for tasks short-circuited as deferred (e.g.
    # operator_handoff). Populated only when ``final_decision == "deferred"``;
    # surfaced in the wave-summary banner so the operator knows what to do.
    deferred_reason: Optional[str] = None
    error_type: Optional[str] = None
    # Step 1 (24 October 2026): a real test or conformance command (such as
    # lint) is still red for this task, carried from the task runner, which
    # records each check's measured result from the Coach's own evidence.
    # A failed task with this set withholds the approved part.
    real_check_failed: bool = False


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
    smoke_gate_result : Optional[SmokeGateResult]
        Outcome of the feature-level smoke gate fired after this wave, if
        the feature had ``smoke_gates`` configured AND ``should_fire_for_wave``
        matched this wave. ``None`` when no gate fired. See TASK-SMK-F703A.
    """

    wave_number: int
    task_ids: List[str]
    results: List[TaskExecutionResult]
    all_succeeded: bool
    smoke_gate_result: Optional["SmokeGateResult"] = None


@dataclass
class SmokeGatePhaseOutcome:
    """Outcome of the post-wave smoke-gate phase (TASK-AB-COACHRUNPARITY01).

    Returned by :meth:`FeatureOrchestrator._run_post_wave_smoke_gate`, which
    owns the bounded smoke-feedback-retry loop. Keeping the retry loop in a
    helper that returns this object (rather than mutating the caller's
    ``wave_results`` list) keeps the wave-enumerate loop readable and the
    retry logic unit-testable.

    Attributes
    ----------
    terminate : bool
        ``True`` when the wave-enumerate loop should ``break`` (smoke failed
        terminally — exit-5 gate-not-wired or retries exhausted). ``False`` to continue to
        the next wave (smoke passed, possibly after a retry).
    final_wave_result : WaveExecutionResult
        The wave result that should replace ``wave_results[-1]`` — the FINAL
        attempt's result, carrying the final ``smoke_gate_result``. Replacing
        (never appending) is what keeps the outcome classifier from
        double-counting a re-run wave's tasks/turns.
    """

    terminate: bool
    final_wave_result: WaveExecutionResult


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
    tasks_deferred: int = 0


# ============================================================================
# Exceptions
# ============================================================================


class FeatureOrchestrationError(Exception):
    """Base exception for feature orchestration errors."""

    pass


# ============================================================================
# Bootstrap failure-mode config loader (TASK-FIX-7A04)
# ============================================================================

# ============================================================================
# Late-approval reconciliation (TASK-ATR-003)
# ============================================================================
#
# `asyncio.to_thread` cannot be hard-cancelled; when the feature timer fires
# while the worker thread is mid-`subprocess.run(pytest)`, the thread keeps
# running and may write `coach_turn_<N>.json` with `decision=approve` *after*
# `asyncio.gather` has already collected `TimeoutError`. The two layers
# disagree on the same task. `LATE_APPROVAL_GRACE_S` is the window inside
# which a Coach approval is treated as authoritative over the timer fire.
#
# Mirrors the env-var pattern of `MIN_TURN_BUDGET_SECONDS` in autobuild.py.
LATE_APPROVAL_GRACE_S: int = int(
    os.environ.get("GUARDKIT_LATE_APPROVAL_GRACE", "60")
)


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
    - A failed task never stops later waves or other tasks, including the
      tasks that depend on it (cull, 27 October 2026)

    Attributes
    ----------
    repo_root : Path
        Repository root directory
    max_turns : int
        Maximum turns per task
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
        resume: bool = False,
        fresh: bool = False,
        refresh: bool = False,
        verbose: bool = False,
        features_dir: Optional[Path] = None,
        worktree_manager: Optional[WorktreeManager] = None,
        quiet: bool = False,
        sdk_timeout: Optional[int] = None,
        enable_pre_loop: Optional[bool] = None,
        enable_context: bool = True,
        task_timeout: int = 2400,
        timeout_multiplier: Optional[float] = None,
        max_parallel: Optional[int] = None,
        parallel_config: Optional["ParallelConfig"] = None,
        skip_validation: bool = False,
        emitter: Optional[Any] = None,
        task_log_interval: int = 60,
        model: Optional[str] = None,
        coach_model: Optional[str] = None,
    ):
        """
        Initialize FeatureOrchestrator.

        Parameters
        ----------
        repo_root : Path
            Repository root directory
        max_turns : int, optional
            Maximum turns per task (default: 5)
        resume : bool, optional
            Resume from saved state (default: False)
        fresh : bool, optional
            Start fresh, ignoring saved state (default: False)
        refresh : bool, optional
            Rebase worktree onto latest base branch before resuming
            (default: False). Implies resume=True. Mutually exclusive
            with fresh.
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
        enable_context : bool, optional
            Enable/disable memory context retrieval (default: True).
        task_timeout : int, optional
            Per-task timeout in seconds for wave execution (default: 2400, i.e. 40 min).
            Prevents any single task from blocking an entire wave indefinitely.
        timeout_multiplier : Optional[float], optional
            Multiplier for all timeout values (default: auto-detect).
            When None, auto-detects from ANTHROPIC_BASE_URL (4.0 for localhost).
            Scales task_timeout and is passed through to AgentInvoker for SDK timeouts.
            (TASK-FIX-VL05)
        max_parallel : Optional[int], optional
            Maximum number of parallel tasks per wave (default: None = unlimited).
            When set, uses an asyncio.Semaphore to limit concurrent task execution
            within each wave. Useful for local/vLLM backends with limited resources.
        skip_validation : bool, optional
            Skip pre-flight frontmatter validation (default: False).
            When True, bypasses the frontmatter field and task_type checks
            that run before worktree creation.
        task_log_interval : int, optional
            Seconds between per-task progress log snapshots (default: 60).
            Each parallel task writes to .guardkit/autobuild/{task_id}/progress.log.

        Raises
        ------
        ValueError
            If max_turns < 1 or if both resume and fresh are True
        """
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")

        if resume and fresh:
            raise ValueError("Cannot use both --resume and --fresh flags together")

        if refresh and fresh:
            raise ValueError("Cannot use both --refresh and --fresh flags together")

        # --refresh implies --resume
        if refresh:
            resume = True

        # TASK-FIX-VL05: Detect and apply timeout multiplier for local backends
        from guardkit.orchestrator.agent_invoker import detect_timeout_multiplier

        self.timeout_multiplier = (
            timeout_multiplier if timeout_multiplier is not None
            else detect_timeout_multiplier()
        )

        self.repo_root = Path(repo_root).resolve()
        self.max_turns = max_turns
        # TASK-AB-XREPOEV01: declared sibling evidence repos, resolved in
        # _setup_phase from the loaded feature. Empty until then.
        self._evidence_repos_resolved: List[EvidenceRepo] = []
        # TASK-FIX-LGFM: thread --model from `guardkit autobuild feature` CLI
        # down to every per-task AutoBuildOrchestrator. Load-bearing for the
        # LangGraph harness path (DeepAgents needs a real model factory;
        # model=None fails construction). Sibling of TASK-FIX-MODELPLUMB which
        # closed the same path for the `task` subcommand.
        self.model = model
        # TASK-FIX-COACHBUDG01 (2026-06-06): optional per-role override for Coach.
        # When set, Coach (and coach_test) invocations route to this model while
        # Player and specialists stay on self.model. Substrate-quality lever for
        # the F17 verdict-emission reliability gap (HMIG-013, swap Coach to
        # gemma4:26b while Player stays on qwen36-workhorse).
        self.coach_model = coach_model
        # TASK-AB-COACHRUNPARITY01 (arm a): bounded retry budget for the
        # post-wave smoke gate. On a smoke failure
        # the wave is re-entered with the smoke stderr fed back to the Player
        # as turn-1 feedback, up to this many extra rounds, before the feature
        # terminates. Default 1 keeps the blast radius minimal (one feedback
        # round); 0 restores the legacy immediate-terminate behaviour.
        try:
            self._smoke_gate_max_retries = max(
                0, int(os.environ.get("GUARDKIT_SMOKE_GATE_MAX_RETRIES", "1"))
            )
        except (TypeError, ValueError):
            self._smoke_gate_max_retries = 1
        # B9 correction (2026-09-19): bounded retry budget for the
        # whole-feature check that runs after the last wave. On a failure the
        # LAST wave is re-entered with the check's own output, the request's
        # words and the scenario titles fed back to the Player as turn-1
        # feedback, up to this many extra rounds. Default 1; 0 means the first
        # failure is final. Same shape as the smoke gate's budget above.
        self._feature_check_max_retries = feature_check_max_retries()
        # The whole-feature repair round's FeatureCheckRepair, set only for the
        # length of that round's ``_execute_wave`` call (18 October 2026).
        # ``_execute_wave`` threads it to each task beside ``smoke_command``;
        # every other wave sees None.
        self._feature_check_repair_for_wave: Optional[FeatureCheckRepair] = None
        # Per task, the non-protected files its gate-driven repair rounds
        # showed the reviewer on the turns it approved, in memory only (20
        # October 2026; repair_round.py). The next re-open carries them.
        self._repair_approvals: Dict[str, Set[str]] = {}
        self.resume = resume
        self.fresh = fresh
        self.refresh = refresh
        self.verbose = verbose
        self.quiet = quiet
        self.sdk_timeout = sdk_timeout
        self.enable_pre_loop = enable_pre_loop
        self.enable_context = enable_context
        # TASK-ABSR-FLOR: Floor task_timeout at 3000s before the multiplier.
        # Run-3 J004-011 used 2235s of the 2400s default budget (92%) and Coach
        # then ran in a poisoned worktree, producing parallel_contention. The
        # 3000s floor gives 765s of wall headroom for per-turn rate variance.
        # Override (or disable, by setting to 0) via the
        # GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR env var. Read at construction
        # time (not module import) so tests can monkeypatch the env per-test.
        task_timeout_floor = int(
            os.environ.get("GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR", "3000")
        )
        floored_task_timeout = max(task_timeout_floor, task_timeout)
        self.task_timeout = int(floored_task_timeout * self.timeout_multiplier)
        self.max_parallel = max_parallel
        self._parallel_config = parallel_config if parallel_config is not None else ParallelConfig.from_legacy(max_parallel)
        self.skip_validation = skip_validation
        self._emitter = emitter if emitter is not None else NullEmitter()  # TASK-INST-004
        self.task_log_interval = task_log_interval  # TASK-FIX-OBS2
        self.features_dir = features_dir or self.repo_root / ".guardkit" / "features"

        # Raise file descriptor limit for parallel task execution
        self._raise_fd_limit()

        # Initialize dependencies
        self._worktree_manager = worktree_manager or WorktreeManager(
            repo_root=self.repo_root
        )

        # Wave progress display (initialized during setup phase)
        self._wave_display: Optional[WaveProgressDisplay] = None

        # TASK-FIX-7A05: Python interpreter produced by the most recent
        # bootstrap (set in :meth:`_bootstrap_environment`). Threaded into
        # every AutoBuildOrchestrator so Coach's pytest runs against the
        # same interpreter the Player's install targeted.
        self._bootstrap_venv_python: Optional[str] = None

        logger.info(
            f"FeatureOrchestrator initialized: repo={self.repo_root}, "
            f"max_turns={self.max_turns}, "
            f"resume={self.resume}, fresh={self.fresh}, refresh={self.refresh}, "
            f"enable_pre_loop={self.enable_pre_loop}, "
            f"enable_context={self.enable_context}, task_timeout={self.task_timeout}s"
            f"{f', timeout_multiplier={self.timeout_multiplier}x' if self.timeout_multiplier != 1.0 else ''}"
            f"{f', max_parallel={self.max_parallel}' if self.max_parallel is not None else ''}"
        )

    def _raise_fd_limit(self, target: int = 4096) -> None:
        """
        Raise the file descriptor soft limit for parallel task execution.

        Each parallel AutoBuild task consumes ~60-90 file descriptors (Claude Code
        subprocess + Neo4j + OpenAI + git + runtime). With 3+ parallel tasks, the
        macOS default soft limit of 256 is insufficient, causing [Errno 24] crashes.

        Parameters
        ----------
        target : int, optional
            Target soft limit (default: 4096)
        """
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            if soft >= target:
                return
            new_soft = min(target, hard) if hard != resource.RLIM_INFINITY else target
            resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, hard))
            logger.info(f"Raised file descriptor limit: {soft} → {new_soft}")
        except (ValueError, OSError) as e:
            logger.warning(f"Could not raise file descriptor limit: {e}")

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
            # Build 0D7C (12 October 2026): the branch every task's
            # checkpoints must land on, pinned once before the first wave.
            self._feature_branch_pinned = False
            self._pinned_feature_branch(worktree)

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

    def _pinned_feature_branch(self, worktree: Worktree) -> Optional[str]:
        """The branch every task's checkpoints must land on (build 0D7C).

        Read once, at the build's start, before any agent has run: HEAD's
        branch then, else the worktree's declared branch
        (``head_identity.expected_checkpoint_branch``). Later calls return the
        pinned value and never look at HEAD again.
        """
        if not getattr(self, "_feature_branch_pinned", False):
            from guardkit.orchestrator.head_identity import (
                expected_checkpoint_branch,
            )

            self._feature_branch = expected_checkpoint_branch(
                getattr(worktree, "path", None),
                getattr(worktree, "branch_name", None),
            )
            self._feature_branch_pinned = True
        return self._feature_branch

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
            "[yellow]Refreshing & Resuming[/yellow]" if self.refresh else
            "[yellow]Resuming[/yellow]" if self.resume else
            "Starting"
        )
        console.print(
            Panel(
                f"[bold]AutoBuild Feature Orchestration[/bold]\n\n"
                f"Feature: [cyan]{feature_id}[/cyan]\n"
                f"Max Turns: {self.max_turns}\n"
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

        # TASK-AB-WAVECTL01: apply the feature-YAML tier of the max-parallel
        # precedence chain (env > CLI flag > feature-YAML recommended_parallel
        # > auto-detect) ONCE, before any resolve_max_parallel call site, so
        # the wave-banner resolution (log=False) and the executor resolution
        # keep consuming the identical decision — see
        # .claude/rules/display-must-derive-from-enforcement-source-not-proxy.md.
        # Operator-set values (env/flag) pass through unchanged, and the YAML
        # may only LOWER an auto-detected value (never raise the TASK-VPT-001
        # local cap of 1); the chosen source is logged by the executor's
        # authoritative resolution.
        self._parallel_config = apply_feature_recommended_parallel(
            self._parallel_config,
            feature.orchestration.recommended_parallel,
        )

        # The immutable source declaration is resolved after actual fresh
        # creation, before setup writes and Player admission.
        self._evidence_repos_resolved = []

        # Pre-flight frontmatter validation (TASK-FIX-7537)
        if not self.skip_validation:
            preflight_result = validate_feature_preflight(feature, self.repo_root)

            # Env-level preflight: catch pytest-bdd ↔ tagged feature gap before
            # any SDK turn burns (TASK-FIX-BDDM-2). Purely additive — folds
            # any errors/warnings into the same report-and-bail path below.
            env_result = validate_feature_environment(feature, self.repo_root)
            preflight_result.errors.extend(env_result.errors)
            preflight_result.warnings.extend(env_result.warnings)

            # Display warnings (alias suggestions) even if valid
            if preflight_result.has_warnings:
                for warning in preflight_result.warnings:
                    console.print(
                        f"[yellow]![/yellow] {warning.task_id}: {warning.message}"
                    )
                    if warning.suggestion:
                        console.print(f"    Suggestion: {warning.suggestion}")

            # Fail on errors
            if preflight_result.has_errors:
                report = format_preflight_report(preflight_result)
                raise FeatureValidationError(report)

            console.print("[green]✓[/green] Pre-flight validation passed")

        # Initialize wave progress display
        if not self.quiet:
            self._wave_display = WaveProgressDisplay(
                total_waves=len(feature.orchestration.parallel_groups),
                verbose=self.verbose,
            )

        # Handle fresh start
        #
        # TASK-FIX-FRESHCLEAN01: --fresh is unconditional. The previous
        # ``is_incomplete`` guard skipped cleanup for terminal
        # (completed / merged / planned) features, so a stale worktree and
        # ``autobuild/<id>`` branch survived and ``_create_new_worktree``
        # failed with "branch already exists" — while the still-``completed``
        # tasks would have been skipped as already-done even if it hadn't.
        # ``_clean_state`` is idempotent (it no-ops when there is nothing to
        # clean), so running it for every ``--fresh`` is safe and matches the
        # flag's contract ("Start from scratch, ignoring saved state").
        if self.fresh:
            self._warn_unmerged_before_fresh(feature_id, base_branch)
            console.print("[yellow]⚠[/yellow] Clearing previous state (--fresh)")
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

                        # Refresh worktree if --refresh flag is set
                        if self.refresh:
                            self._refresh_worktree(worktree, base_branch)

                        # Re-establish the environment on resume: this early
                        # return bypasses Phase 1.5, leaving
                        # _bootstrap_venv_python unset — Coach + smoke gates
                        # then fall back to PATH pytest (system python) and
                        # spawn-based tests (sys.executable -m ...) fail with
                        # ModuleNotFoundError. Both calls are idempotent
                        # (hash-match skip still resolves the venv
                        # interpreter via _resolve_skip_venv_python).
                        self._arrange_uv_sources_symlinks(worktree)
                        self._bootstrap_environment(worktree, feature=feature)

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

                            # Refresh worktree if user chose update+resume
                            if self.refresh:
                                self._refresh_worktree(worktree, base_branch)

                            # Same resume-path environment re-establishment
                            # as the --resume branch above (idempotent).
                            self._arrange_uv_sources_symlinks(worktree)
                            self._bootstrap_environment(
                                worktree, feature=feature
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
            # A new feature worktree is a new build: an older build's capture
            # of the Coach's binding documents (same name) must not be reused.
            AutoBuildOrchestrator.discard_coach_documents_snapshot(worktree.path)
        except WorktreeCreationError as e:
            raise FeatureOrchestrationError(
                f"Failed to create worktree for {feature_id}: {e}"
            ) from e

        from guardkit.orchestrator.task_work_scope import bind_fresh_footprint, checkout_lease
        self._evidence_repos_resolved = bind_fresh_footprint(
            worktree.path, self.repo_root, feature.file_path,
            kind="feature", expected=feature.evidence_repos,
        )
        with checkout_lease(worktree.path, self._evidence_repos_resolved):
            return self._prepare_fresh_worktree(feature, feature_id, base_branch, worktree)

    def _prepare_fresh_worktree(self, feature, feature_id, base_branch, worktree):
        # WS3-S3 §1.3: capture the feature-base commit (the pre-wave-1 creation
        # commit) BEFORE any task copy / wave commit mutates the tree, so 2b/2d
        # config reads and CONFIG_TAMPER resolve against the un-launderable
        # referent (NOT the per-task _record_baseline HEAD). Fail-open.
        try:
            from guardkit.orchestrator.seam_checks import record_feature_base
            sha = record_feature_base(
                Path(worktree.path), feature_id, Path(worktree.path), base_branch
            )
            if sha:
                logger.debug("WS3-S3: recorded feature-base %s for %s", sha[:8], feature_id)
        except Exception as exc:  # noqa: BLE001 — never block worktree creation
            logger.warning("WS3-S3: feature-base capture failed for %s: %s", feature_id, exc)

        # Copy task files to worktree
        self._copy_tasks_to_worktree(feature, worktree)

        # TASK-FIX-AB61: Pre-arrange any [tool.uv.sources] sibling-path
        # symlinks before bootstrap. Idempotent on --resume / --fresh.
        self._arrange_uv_sources_symlinks(worktree)

        # Phase 1.5: Bootstrap environment (detect + install dependencies)
        self._bootstrap_pending = True

        # Update feature with worktree path and start time
        feature.status = "in_progress"
        feature.execution.started_at = datetime.now().isoformat()
        feature.execution.worktree_path = str(worktree.path)
        feature.execution.last_updated = datetime.now().isoformat()
        FeatureLoader.save_feature(feature, self.repo_root)

        return feature, worktree

    def _resolve_refresh_target(
        self,
        worktree_path: Path,
        base_branch: str,
    ) -> tuple[str, str]:
        """Resolve which ref ``--refresh`` should rebase the worktree onto.

        Resolution order (red-baseline retro, L12 item 4):

          1. **Local ``<base_branch>``** when it exists AND is ahead of
             ``origin/<base_branch>``. Operators routinely fix a red baseline
             on their *local* main and deliberately leave it unpushed;
             rebasing onto a stale ``origin/main`` would bring none of the fix
             and conflict (the FEAT-VOICE-003 ``--refresh`` failure).
          2. **``origin/<base_branch>``** otherwise (the pushed baseline, the
             historical default).

        Returns ``(target_ref, human_description)``. With no
        ``origin/<base_branch>`` on this machine, the local branch is used
        (the refresh fetches nothing). Any other git probe failure falls back
        to ``origin/<base_branch>`` — the historical behaviour.
        """
        import subprocess

        def _run(args: List[str]) -> subprocess.CompletedProcess:
            return run_git(
                [*args],
                cwd=worktree_path,
                check=False,
            )

        local_exists = (
            _run(["rev-parse", "--verify", "--quiet", base_branch]).returncode == 0
        )
        remote_exists = (
            _run(["rev-parse", "--verify", "--quiet", f"origin/{base_branch}"]).returncode
            == 0
        )
        if local_exists and not remote_exists:
            # Nothing has been fetched for the base branch on this machine,
            # and the refresh no longer fetches: the local branch is the base.
            return base_branch, f"local {base_branch} (no origin/{base_branch} here)"
        if local_exists:
            ahead = _run(
                ["rev-list", "--count", f"origin/{base_branch}..{base_branch}"]
            )
            try:
                ahead_count = int(ahead.stdout.strip()) if ahead.returncode == 0 else 0
            except ValueError:
                ahead_count = 0
            if ahead_count > 0:
                return base_branch, (
                    f"local {base_branch} (ahead of origin/{base_branch} by "
                    f"{ahead_count} unpushed commit(s))"
                )
        return f"origin/{base_branch}", f"origin/{base_branch}"

    def _describe_worktree_git_state(
        self,
        worktree_path: Path,
    ) -> tuple[bool, str]:
        """Truthfully describe the worktree's git state after a rebase abort.

        Red-baseline retro (L12 item 5b): the old code printed "worktree may
        be in inconsistent state" *unconditionally* on any abort hiccup, even
        when the abort had restored the worktree cleanly (the FEAT-VOICE-003
        false alarm). This checks the *actual* state — whether a rebase is
        still in progress and where HEAD points — and reports what it found.

        Returns ``(is_clean, message)``.
        """
        import subprocess

        def _run(args: List[str]) -> subprocess.CompletedProcess:
            return run_git(
                [*args],
                cwd=worktree_path,
                check=False,
            )

        def _rebase_dir_exists(name: str) -> bool:
            raw = _run(["rev-parse", "--git-path", name]).stdout.strip()
            if not raw:
                return False
            p = Path(raw)
            if not p.is_absolute():
                p = worktree_path / p
            return p.exists()

        in_progress = _rebase_dir_exists("rebase-merge") or _rebase_dir_exists(
            "rebase-apply"
        )
        head = _run(["rev-parse", "--short", "HEAD"]).stdout.strip() or "unknown"
        if in_progress:
            return False, (
                f"rebase IS still in progress (HEAD at {head}); manual cleanup "
                f"needed: cd {worktree_path} && git rebase --abort"
            )
        return True, (
            f"verified restored: no rebase in progress, HEAD at {head}"
        )

    def _refresh_worktree(
        self,
        worktree: Worktree,
        base_branch: str = "main",
    ) -> None:
        """
        Refresh worktree by rebasing onto the latest base branch.

        Fetches nothing: it rebases the worktree's branch onto the base branch
        as it already is on this machine (13 October 2026: the factory runs no
        git command that reaches another repository; fetch it yourself first
        if you need the remote's latest). The target is the ref the operator
        most likely fixed (see :meth:`_resolve_refresh_target`):
        **local ``<base_branch>`` when it is ahead of ``origin/<base_branch>``**,
        otherwise ``origin/<base_branch>``. The rebase runs with
        ``--autostash`` so an unstaged autobuild-managed artifact (e.g.
        ``.guardkit/autobuild/**/checkpoints.json``) does not abort it. On
        conflict the rebase is aborted and the worktree's *actual* state is
        verified and reported (never an unverified "inconsistent state"
        assertion). Red-baseline retro (L12 items 4 + 5).

        Parameters
        ----------
        worktree : Worktree
            Worktree to refresh
        base_branch : str, optional
            Base branch to rebase onto (default: "main"). The effective target
            is resolved by :meth:`_resolve_refresh_target`.

        Raises
        ------
        FeatureOrchestrationError
            If the rebase has conflicts
        """
        import subprocess

        worktree_path = worktree.path

        # Step 1: no fetch (13 October 2026). The factory runs no git command
        # that reaches another repository, so the refresh rebases onto the
        # base branch as it already is on this machine.
        console.print(f"[cyan]↻[/cyan] {REFRESH_USES_LOCAL_BASE}")

        # Step 2: Resolve the rebase target (item 4 — prefer local base when
        # it holds the operator's unpushed fix).
        target_ref, target_desc = self._resolve_refresh_target(
            worktree_path, base_branch
        )

        # Step 3: Rebase onto the resolved target. --autostash (item 5a)
        # stashes any dirty tracked state (the autobuild checkpoints.json
        # class) before rebasing and restores it afterwards — including on
        # abort — so a dirty worktree no longer blows the rebase up.
        console.print(f"[cyan]↻[/cyan] Rebasing onto {target_desc}...")
        try:
            run_git(
                ["rebase", "--autostash", target_ref],
                cwd=worktree_path,
                check=True,
            )
            console.print(
                f"[green]✓[/green] Successfully rebased onto {target_desc}"
            )
        except subprocess.CalledProcessError:
            # Rebase failed (likely conflicts) -- abort to restore clean state.
            console.print(
                "[red]✗[/red] Rebase conflicts detected, aborting rebase..."
            )
            run_git(
                ["rebase", "--abort"],
                cwd=worktree_path,
                check=False,
            )
            # Item 5b: verify the ACTUAL state rather than asserting it.
            is_clean, state_msg = self._describe_worktree_git_state(worktree_path)
            if is_clean:
                console.print(f"[green]✓[/green] Rebase aborted — {state_msg}")
            else:
                console.print(f"[yellow]⚠[/yellow] {state_msg}")

            raise FeatureOrchestrationError(
                f"Rebase onto {target_ref} failed due to conflicts "
                f"({state_msg}).\n"
                f"To resolve manually:\n"
                f"  cd {worktree_path}\n"
                f"  git rebase {target_ref}\n"
                f"  # resolve conflicts\n"
                f"  git rebase --continue"
            )

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
        # -> feature-build-sdk-coordination. A path of any other form has no
        # feature directory to copy from, so nothing is copied.
        parts = Path(feature.tasks[0].file_path or "").parts
        tasks_idx = parts.index("tasks") if "tasks" in parts else -1
        if not (
            tasks_idx >= 0
            and tasks_idx + 2 < len(parts)
            and parts[tasks_idx + 1] == "backlog"
        ):
            return
        feature_dir = parts[tasks_idx + 2]
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

    def _arrange_uv_sources_symlinks(self, worktree: Worktree) -> None:
        """
        Pre-create symlinks for ``[tool.uv.sources]`` sibling-path entries
        so uv resolves the same files from the worktree as it would from
        the source repo (TASK-FIX-AB61).

        Both pyprojects must exist for this to do anything useful. Missing
        ``pyproject.toml`` on either side, no ``[tool.uv.sources]`` table,
        or only non-path-typed entries (``git`` / ``index`` / ``workspace``
        / ``url``) → silent no-op.

        Symlink-creation OSErrors are surfaced with a hint that names the
        symlink path, target, and OS error.
        """
        source_pyproject = self.repo_root / "pyproject.toml"
        worktree_pyproject = worktree.path / "pyproject.toml"
        if not source_pyproject.exists() or not worktree_pyproject.exists():
            return

        symlinks = _resolve_uv_sources_symlinks(
            source_pyproject_path=source_pyproject,
            worktree_pyproject_path=worktree_pyproject,
        )
        if not symlinks:
            return

        for symlink_path, target_path in symlinks:
            logger.info(
                "creating uv-sources symlink: %s -> %s",
                symlink_path,
                target_path,
            )

        try:
            _create_worktree_uv_sources_symlinks(symlinks)
        except OSError as exc:
            failed = symlinks[0]
            raise FeatureOrchestrationError(
                f"Failed to create uv-sources symlink "
                f"{failed[0]} -> {failed[1]}: {exc}. "
                f"Verify filesystem permissions on the worktree parent and "
                f"that the target path is readable. See TASK-FIX-AB61."
            ) from exc

    def _bootstrap_environment(
        self,
        worktree: Worktree,
        feature: Optional[Feature] = None,
    ) -> Optional[BootstrapResult]:
        """
        Detect and install project dependencies in the worktree.

        Called after worktree creation (Phase 1.5) and between waves.
        Failed installs and an interpreter that does not meet a manifest's
        ``requires-python`` are warnings, never a stop (step 2, 26 October
        2026): when the project's tests then cannot start, the reviewer is
        told "The project's tests could not be run: <reason>".

        Parameters
        ----------
        worktree : Worktree
            Shared worktree to scan and install into.
        feature : Optional[Feature]
            Feature being bootstrapped. When provided, ``bootstrap_extras``
            (operator-declared or auto-detected from a pytest smoke gate)
            are threaded into the Python pyproject install command so
            test deps live in the worktree's venv. Optional for
            backward-compatibility with call sites that haven't been
            updated. (TASK-GK-BS-001)

        Returns
        -------
        Optional[BootstrapResult]
            Bootstrap result, or None when no manifests were found or an
            unexpected error occurred.

        Raises
        ------
        FeatureOrchestrationError
            When the toolchain declaration cannot be read.
        """
        try:
            python_extras: tuple[str, ...] = ()
            if feature is not None:
                python_extras = tuple(
                    derive_bootstrap_extras(feature, worktree.path)
                )
                if python_extras:
                    logger.info(
                        "Bootstrap will install Python extras: %s",
                        list(python_extras),
                    )
            detector = ProjectEnvironmentDetector(
                worktree.path,
                python_extras=python_extras,
            )
            manifests = detector.detect()

            if not manifests:
                logger.debug("No dependency manifests found in worktree")
                return None

            stacks = sorted(set(m.stack for m in manifests))
            console.print(f"[cyan]\u2699[/cyan] Bootstrapping environment: {', '.join(stacks)}")

            bootstrapper = EnvironmentBootstrapper(worktree.path)
            result = bootstrapper.bootstrap(manifests)

            if result.skipped and result.success:
                console.print("[green]\u2713[/green] Environment already bootstrapped (hash match)")
            elif result.installs_failed == 0:
                console.print(
                    f"[green]\u2713[/green] Environment bootstrapped: {', '.join(result.stacks_detected)}"
                )
            else:
                console.print(
                    f"[yellow]\u26a0[/yellow] Environment bootstrap partial: "
                    f"{result.installs_attempted - result.installs_failed}/{result.installs_attempted} succeeded"
                )

            # TASK-FIX-7A05: capture the bootstrap interpreter so downstream
            # AutoBuildOrchestrator / Coach pytest invocations use it
            # instead of whatever ``pytest`` is on the shell PATH. Logged at
            # INFO so the startup / per-wave log clearly states which
            # interpreter Coach will verify against.
            if result.venv_python:
                self._bootstrap_venv_python = result.venv_python
                console.print(
                    f"[cyan]⚙[/cyan] Coach will verify using interpreter: "
                    f"{result.venv_python}"
                )
                logger.info(
                    "Coach pytest interpreter set from bootstrap venv: %s",
                    result.venv_python,
                )
            else:
                # Non-Python project (or Python project without a venv)
                # preserves prior PATH-pytest behavior for Coach.
                logger.debug(
                    "Bootstrap produced no venv interpreter — Coach will use "
                    "PATH pytest / sys.executable fallback"
                )

            return result
        except ToolchainDeclarationError as e:
            # Follow-up fixes 2026-10-13 (3b): an unreadable declaration or a
            # refused component ``cwd`` would otherwise drop the declaration
            # and guess the install. Stop the build in every failure mode.
            logger.error("Bootstrap hard-fail (toolchain declaration): %s", e)
            console.print(
                f"[red]\u2717[/red] Bootstrap hard-fail: toolchain declaration\n{e}"
            )
            raise FeatureOrchestrationError(str(e)) from e
        except Exception as e:
            logger.warning(f"Environment bootstrap failed: {e}")
            console.print(f"[yellow]\u26a0[/yellow] Environment bootstrap failed: {e}")
            return None

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
        console.print("  [U]pdate - Rebase on latest main, then resume")
        console.print("  [F]resh  - Start over from the beginning")
        console.print()

        try:
            import sys
            if sys.stdin.isatty():
                choice = input("Your choice [R/u/f]: ").strip().lower() or "r"
                if choice == "f":
                    return False
                elif choice == "u":
                    self.refresh = True
                    return True
                else:
                    return True
            else:
                # Non-interactive mode, default to resume
                console.print("[dim]Non-interactive mode, defaulting to resume[/dim]")
                return True
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled[/yellow]")
            raise FeatureOrchestrationError("User cancelled resume prompt")

    def _warn_unmerged_before_fresh(
        self,
        feature_id: str,
        base_branch: str,
    ) -> None:
        """
        Warn when ``--fresh`` is about to discard unmerged autobuild work.

        ``--fresh`` is destructive by design ("ignoring saved state"), but the
        never-auto-merge spirit — humans own merges — means the operator should
        be told what is being thrown away. If the ``autobuild/<feature_id>``
        branch holds commits not reachable from ``base_branch``, emit a WARNING
        naming the count before ``_clean_state`` deletes the branch.

        Read-only and warning-only: every git call is wrapped so a failure here
        can never abort the cleanup that follows (mirrors the pth-leak scan
        guard in ``_clean_state``).

        Parameters
        ----------
        feature_id : str
            Feature identifier, used to derive the ``autobuild/<id>`` branch.
        base_branch : str
            Branch the autobuild commits would need to be merged into.
        """
        import subprocess

        branch_name = f"autobuild/{feature_id}"
        try:
            # Only warn if the branch actually exists.
            verify = run_git(
                ["rev-parse", "--verify", "--quiet",
                 f"refs/heads/{branch_name}"],
                cwd=self.repo_root,
            )
            if verify.returncode != 0:
                return

            # Count commits on the branch not reachable from base_branch.
            result = run_git(
                ["rev-list", "--count", f"{base_branch}..{branch_name}"],
                cwd=self.repo_root,
            )
            if result.returncode != 0:
                return

            unmerged = int((result.stdout or "").strip() or "0")
            if unmerged > 0:
                console.print(
                    f"[yellow]⚠[/yellow] --fresh will discard {unmerged} "
                    f"unmerged commit(s) on branch '{branch_name}' not in "
                    f"'{base_branch}'. Merge or cherry-pick them first if you "
                    f"need them."
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("unmerged-work warn hook failed, suppressing: %s", exc)

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
                # TASK-FIX-FF62 (Layer 3 / FEAT-FFC6): warn on dangling
                # editable .pth references in parent venvs before the
                # worktree path becomes meaningless. Read-only and
                # warning-only — wrapped in try/except so a buggy
                # scanner can never abort cleanup.
                try:
                    warn_pth_leaks(
                        repo_root=self.repo_root,
                        worktree_path=worktree_path,
                        console=console,
                    )
                except Exception as scanner_exc:  # noqa: BLE001
                    logger.debug(
                        "pth-leak warn hook failed, suppressing: %s",
                        scanner_exc,
                    )

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
        logger.info(
            f"Phase 2 (Waves): Executing {len(feature.orchestration.parallel_groups)} waves "
            f"(task_timeout={self.task_timeout}s)"
        )
        wave_results = []

        # Resolve every queued task's EFFECTIVE per-task budget once, before
        # wave 1 (TASK-FIX-TTO01). Both the wave-0 warnings and the
        # once-per-run banner below read this same map, so the number the
        # banner declares is the number `asyncio.wait_for` will enforce.
        effective_task_timeouts = self._resolve_wave_task_timeouts(feature)

        console.print()
        console.print(
            f"[bold]Starting Wave Execution[/bold] "
            f"[dim]({self._format_task_timeout_banner(effective_task_timeouts)})"
            f"[/dim]"
        )

        for wave_number, task_ids in enumerate(
            feature.orchestration.parallel_groups, 1
        ):
            # Inter-wave bootstrap: re-detect and install new dependencies
            # (e.g., Wave 1 may have created pyproject.toml that Wave 2 needs)
            if wave_number > 1:
                self._bootstrap_pending = True

            # A task whose dependency did not complete still runs, on what
            # the checkout holds (cull, 27 October 2026).

            # Display wave start via progress display.
            # TASK-FIX-MAXPARALLEL01: resolve the effective max_parallel (read
            # only, log=False — the authoritative log is emitted by the
            # dispatcher in _execute_wave_parallel) so the "(parallel: K)"
            # banner reflects the concurrency the executor will actually
            # enforce, not the wave size.
            if self._wave_display:
                display_max_parallel = resolve_max_parallel(
                    self._parallel_config,
                    wave_number=wave_number,
                    wave_size=len(task_ids),
                    log=False,
                    # Same mapping the dispatcher resolves with (cached), so
                    # the banner never says two while one runs.
                    wave_task_paths=self._wave_task_paths(
                        wave_number, task_ids, feature, worktree
                    ),
                )
                self._wave_display.start_wave(
                    wave_number, task_ids, max_parallel=display_max_parallel
                )
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

            # Step 2 (26 October 2026): a failed or timed-out task no longer
            # stops later waves. A worker still running after its time limit
            # holds the checkout's writer lock, so the next writer waits for it.

            # Feature-level smoke gate (TASK-SMK-F703A). Fires AFTER a wave
            # completes successfully and BEFORE the next wave starts, catching
            # composition failures the per-task Player-Coach loop is blind to.
            # Placement is between-waves, never per-task — per-task smoke is
            # the per-task Coach with extra steps.
            #
            # TASK-AB-COACHRUNPARITY01 (arm a): the gate is no longer a hard
            # terminator. On a failure the helper
            # re-enters the wave with the smoke stderr fed back to the Player as
            # turn-1 feedback, bounded by _smoke_gate_max_retries, before
            # terminating. The helper REPLACES wave_results[-1] (never appends),
            # so the outcome classifier counts the wave once.
            if feature.smoke_gates is not None and should_fire_for_wave(
                feature.smoke_gates, wave_number
            ):
                outcome = self._run_post_wave_smoke_gate(
                    wave_number, task_ids, feature, worktree, wave_result
                )
                wave_result = outcome.final_wave_result
                wave_results[-1] = wave_result
                if outcome.terminate:
                    break

            # TASK-AB-COACHRUNPARITY01 (C1): mark the wave completed only AFTER
            # the smoke phase resolves — gated on task success AND smoke success
            # (or no smoke gate fired for this wave). This is the single place
            # completion is persisted; _execute_wave no longer does it. A wave
            # whose tasks pass but whose smoke gate fails is therefore never
            # recorded as completed on disk, so a resume cannot skip an
            # unverified wave.
            smoke_blocked = (
                wave_result.smoke_gate_result is not None
                and not wave_result.smoke_gate_result.passed
            )
            if wave_result.all_succeeded and not smoke_blocked:
                self._mark_wave_completed(feature, wave_number)

        # The whole-feature check, after the last wave (B9 correction,
        # 2026-09-19). Everything above proves the parts. This proves the
        # FEATURE does what the person asked, at the surface they use, using
        # the one command the project declared for exactly that.
        self._run_feature_check(feature, worktree, wave_results)

        return wave_results

    def _write_code_checks_summary(
        self, feature: Feature, worktree: Worktree
    ) -> Optional[Path]:
        """One summary of what the code checks did, beside the whole-feature
        record, written once at the end of the build.

        Per task: the LAST review's result for each check, whether the
        builder's file list was recorded, and how many shell commands ran.
        Nothing here refuses anything and nothing here raises — a build is
        never failed by a summary of itself.
        """
        try:
            from guardkit.orchestrator.paths import TaskArtifactPaths

            root = Path(worktree.path)
            task_rows: List[Dict[str, Any]] = []
            for task in getattr(feature, "tasks", None) or []:
                task_id = str(getattr(task, "id", "") or "")
                if not task_id:
                    continue
                review: Any = None
                review_path: Optional[str] = None
                found = code_checks_latest_review(
                    TaskArtifactPaths.task_private_dir(task_id, root)
                )
                if found is not None:
                    try:
                        review = json.loads(found.read_text(encoding="utf-8"))
                    except Exception as exc:  # noqa: BLE001 — unreadable is absence
                        logger.debug(
                            "code checks: %s could not be read: %s", found, exc
                        )
                        review = None
                    else:
                        # Where the record is SAID to be, and nothing else.
                        # In every worktree-backed build the private records
                        # sit outside the worktree on purpose (see
                        # TaskArtifactPaths.task_private_dir), so a path
                        # relative to the worktree cannot be made and asking
                        # for one used to throw the record itself away.
                        review_path = _path_as_told_from(found, root)
                results: Any = None
                for directory in self._autobuild_candidate_dirs(task_id):
                    candidate = directory / "task_work_results.json"
                    if not candidate.exists():
                        continue
                    try:
                        results = json.loads(candidate.read_text(encoding="utf-8"))
                        break
                    except (OSError, ValueError):
                        continue
                task_rows.append(
                    summarise_code_checks_task(
                        task_id,
                        review_record=review,
                        task_results=results,
                        review_record_path=review_path,
                    )
                )
            summary = build_code_checks_summary(
                feature_id=getattr(feature, "id", ""),
                tasks=task_rows,
                groups=[],
            )
            path = write_code_checks_summary(summary, root)
            if path is not None:
                logger.info("What the code checks did: %s", path)
            return path
        except Exception as exc:  # noqa: BLE001 — a summary never fails a build
            logger.warning(
                "The code-checks summary could not be written: %s", exc
            )
            return None

    def _feature_check_skip_reason(
        self,
        feature: Feature,
        wave_results: List[WaveExecutionResult],
    ) -> Optional[str]:
        """Why the whole-feature check should not run, in words, or ``None``.

        The check describes a FINISHED build. A build that stopped early, or
        whose tests failed, or whose own smoke gate already failed, explains
        its own red — running the check over a half-built working copy would
        only add noise to it.
        """
        planned_waves = len(feature.orchestration.parallel_groups)
        if not wave_results:
            return "no wave ran"
        if len(wave_results) < planned_waves:
            return (
                f"the build stopped after wave {len(wave_results)} of "
                f"{planned_waves}"
            )
        if any(not wr.all_succeeded for wr in wave_results):
            return "a task in the build failed"
        if any(
            wr.smoke_gate_result is not None and not wr.smoke_gate_result.passed
            for wr in wave_results
        ):
            return "a smoke gate already failed this build"
        return None

    # -----------------------------------------------------------------------
    # The whole-feature check (B9 correction, 2026-09-19)
    # -----------------------------------------------------------------------

    def _run_feature_check(
        self,
        feature: Feature,
        worktree: Worktree,
        wave_results: List[WaveExecutionResult],
    ) -> Optional[FeatureCheckOutcome]:
        """Prove the finished feature at its delivered surface, then repair.

        Plain words: the build says every task passed. Before anybody is
        offered a merge card, run the one command this project declared for
        its finished features and see whether the thing the person asked for
        actually works. If it does not, hand the Player the command's own
        output, the words of the request and the scenarios the feature
        promised, re-enter the LAST wave, and try again — a bounded number of
        times. When the budget is spent, this feature is failed: a failed gate
        result on the last wave, and that wave un-marked so a resume re-runs
        it, so the finaliser records ``failed`` and Forge never offers the
        card.

        Returns ``None`` when nothing ran: a build that did not finish (it has
        its own answer already), or a project that declared no check.
        """
        skip_reason = self._feature_check_skip_reason(feature, wave_results)
        if skip_reason is not None:
            logger.info(
                "Whole-feature check skipped: %s, so this build already has "
                "its own answer",
                skip_reason,
            )
            return None

        declaration = load_feature_check_declaration(self.repo_root)
        if declaration is None:
            outcome = FeatureCheckOutcome(
                feature_id=feature.id,
                status="not_declared",
                declared=False,
                reason=(
                    "this project declares no `toolchain.feature_check` "
                    "command in .guardkit/config.yaml, so nothing checked the "
                    "finished feature as a whole"
                ),
            )
            try:
                write_feature_check_receipt(outcome, Path(worktree.path))
            except Exception as exc:  # noqa: BLE001 — a receipt never fails a build
                logger.warning(
                    "Whole-feature check receipt could not be written: %s", exc
                )
            return outcome

        last_wave = wave_results[-1]
        wave_number = last_wave.wave_number
        task_ids = list(last_wave.task_ids)
        titles = feature_scenario_titles(feature)
        request_words = feature_request_words(feature, Path(worktree.path))
        attempts: List[FeatureCheckAttempt] = []
        retries_remaining = self._feature_check_max_retries
        attempt_number = 0

        while True:
            attempt_number += 1
            attempt = self._one_feature_check_attempt(
                attempt_number, declaration, feature, worktree
            )
            attempts.append(attempt)
            if not attempt.passed and not attempt.could_not_run:
                # Recorded now, before the budget test, so the last attempt
                # is recorded too and a repair round never hides a failure.
                self._record_failed_feature_check_attempt(
                    feature,
                    declaration,
                    attempt,
                    wave_number,
                    repair_follows=retries_remaining > 0,
                )

            if attempt.passed:
                logger.info(
                    "Whole-feature check PASSED on attempt %d: %s",
                    attempt_number,
                    FEATURE_CHECK_LABEL,
                )
                if not self.quiet:
                    console.print(
                        f"[green]✓ Whole-feature check passed[/green] "
                        f"({FEATURE_CHECK_LABEL})",
                        markup=True,
                    )
                return self._finish_feature_check(
                    feature, worktree, declaration, attempts, wave_results,
                    status=FEATURE_CHECK_PASSED,
                )

            if attempt.could_not_run:
                # The third outcome (21 September 2026). The project said in so
                # many words that its check could not run, so there is nothing
                # for a builder to repair: no repair round, no failed gate
                # result, and every example goes on the not-checked list with
                # the reason instead of being recorded as passed.
                logger.warning(
                    "The whole-feature check COULD NOT RUN: %s",
                    attempt.could_not_run_reason,
                )
                if not self.quiet:
                    console.print(
                        "[yellow]⚠ The project's check could not run: "
                        f"{attempt.could_not_run_reason}[/yellow]",
                        markup=True,
                    )
                return self._finish_feature_check(
                    feature, worktree, declaration, attempts, wave_results,
                    status=FEATURE_CHECK_COULD_NOT_RUN,
                )

            if retries_remaining <= 0:
                return self._finish_feature_check(
                    feature, worktree, declaration, attempts, wave_results,
                    status=FEATURE_CHECK_FAILED,
                )

            retries_remaining -= 1
            feedback = build_feature_check_feedback(
                attempt, request_words=request_words, titles=titles
            )
            console.print(
                f"[yellow]↻ The whole-feature check failed[/yellow] — "
                f"re-entering wave {wave_number} with the check's output as "
                f"Player feedback (retry {attempt_number}/"
                f"{self._feature_check_max_retries}).",
                markup=True,
            )
            # The Coach of each repair turn sees the project's check: the
            # attempt that failed and, on a single-task wave, its own run of
            # the check on the turn's code through this same attempt runner
            # (18 October 2026). Only this round gets it.
            failed_attempt_number = attempt_number
            self._feature_check_repair_for_wave = FeatureCheckRepair(
                failed_attempt=attempt,
                request_words=request_words,
                run=lambda: self._one_feature_check_attempt(
                    failed_attempt_number, declaration, feature, worktree
                ),
            )
            try:
                wave_result = self._execute_wave(
                    wave_number,
                    task_ids,
                    feature,
                    worktree,
                    seed_feedback=feedback,
                    attempt=attempt_number,
                )
            finally:
                self._feature_check_repair_for_wave = None
            wave_results[-1] = wave_result
            last_wave = wave_result
            if self._wave_display:
                passed = sum(1 for r in wave_result.results if r.success)
                failed = len(wave_result.results) - passed
                skipped = sum(
                    1 for r in wave_result.results
                    if r.final_decision == "skipped"
                )
                recovered = sum(
                    1 for r in wave_result.results if r.recovery_count > 0
                )
                self._wave_display.complete_wave(
                    wave_number, passed, failed, skipped, recovered
                )
            if not wave_result.all_succeeded:
                # The repair round itself did not pass its own Coach. There is
                # nothing left to re-check: the feature is failed, and the
                # tasks' own failure is already the ledger's answer.
                logger.error(
                    "The repair round for the whole-feature check did not "
                    "pass its own checks, so this feature is failed."
                )
                return self._finish_feature_check(
                    feature, worktree, declaration, attempts, wave_results,
                    status=FEATURE_CHECK_FAILED,
                )

    def _one_feature_check_attempt(self, attempt_number, declaration, feature, worktree):
        return self._checked_writer(worktree, self._one_feature_check_attempt_owned,
                                    attempt_number, declaration, feature, worktree)

    def _one_feature_check_attempt_owned(
        self,
        attempt_number: int,
        declaration: Any,
        feature: Feature,
        worktree: Worktree,
    ) -> FeatureCheckAttempt:
        """One pass of the declared command."""
        sha = feature_check_candidate_sha(Path(worktree.path))

        env_extra = {
            "GUARDKIT_FEATURE_ID": str(feature.id),
            "GUARDKIT_FEATURE_RECORD": str(
                getattr(feature, "file_path", "") or ""
            ),
            "GUARDKIT_WORKTREE": str(worktree.path),
            "GUARDKIT_CANDIDATE_SHA": sha,
        }
        logger.info(
            "Running the whole-feature check (attempt %d): %s (cwd=%s, "
            "timeout=%ds)",
            attempt_number,
            FEATURE_CHECK_LABEL,
            worktree.path,
            declaration.timeout,
        )
        run = run_feature_check_command(
            declaration.command,
            cwd=Path(worktree.path),
            timeout=declaration.timeout,
            env_extra=env_extra,
            venv_python=self._bootstrap_venv_python,
            evidence=request_from_repo(
                "whole-feature check", self.repo_root,
                feature=str(feature.id), attempt=attempt_number,
            ),
            # The project's `launch:` settings and scratch folders, read from
            # the main checkout like the check command itself.
            launch_root=self.repo_root,
        )
        exit_code = run["exit_code"]
        timed_out = bool(run["timed_out"])
        # Everything the project's one line said, read defensively. Central
        # code carries this text and never reads, compares or judges it.
        line = parse_project_check_line(run["stdout"])

        # The three outcomes, in the order they decide (21 September 2026).
        # A timeout is a failure whatever the output says: a command cut off
        # part-way has not finished telling anyone anything. Otherwise the
        # project's own words decide "could not run" — a command that says
        # nothing and exits non-zero is "failed", never "could not run".
        failure_kind: Optional[str] = None
        if timed_out:
            outcome = FEATURE_CHECK_FAILED
            failure_reason = f"timed out after {declaration.timeout}s"
            failure_kind = FAILURE_KIND_TIMED_OUT
        elif line.could_not_run:
            outcome = FEATURE_CHECK_COULD_NOT_RUN
            failure_reason = None
        elif exit_code == 0:
            outcome = FEATURE_CHECK_PASSED
            failure_reason = None
        elif exit_code is None:
            outcome = FEATURE_CHECK_FAILED
            failure_reason = "the command could not start"
            failure_kind = FAILURE_KIND_COULD_NOT_START
        else:
            outcome = FEATURE_CHECK_FAILED
            failure_reason = f"exit={exit_code}, expected=0"
            failure_kind = FAILURE_KIND_EXIT_NONZERO
            if run.get("environment_note"):
                failure_reason = f"{failure_reason}. {run['environment_note']}"
        passed = outcome == FEATURE_CHECK_PASSED
        # Sizes only: the per-attempt warning and event publish no output.
        stdout_bytes, stdout_lines = feature_check_output_size(run["stdout"])
        stderr_bytes, stderr_lines = feature_check_output_size(run["stderr"])

        not_checked = merge_not_checked([], line.not_checked)
        return FeatureCheckAttempt(
            attempt=attempt_number,
            command=declaration.command,
            candidate_sha=sha,
            passed=passed,
            outcome=outcome,
            exit_code=exit_code,
            timed_out=timed_out,
            duration_seconds=float(run["duration_seconds"]),
            stdout_tail=feature_check_tail(run["stdout"]),
            stderr_tail=feature_check_tail(run["stderr"]),
            failure_reason=failure_reason,
            could_not_run_reason=line.could_not_run_reason,
            not_checked=not_checked,
            # How many examples nothing looked at. It is the MERGED list,
            # which counts a name once however many sources named it, plus
            # the entries the project named but its own line could not carry.
            # Adding the two sources' lengths counted the same example twice:
            # both kept builds of 19 September say 14 beside seven names
            # (found while driving stage B, corrected 21 September 2026).
            not_checked_total=(
                len(not_checked)
                + max(line.not_checked_total - len(line.not_checked), 0)
            ),
            observations=line.observations,
            observations_total=line.observations_total,
            notes=list(line.notes),
            scenarios_covered=(line.scenarios_covered if passed else []),
            run_evidence=dict(run.get("run_evidence") or {}),
            ran_at=datetime.now().isoformat(),
            failure_kind=failure_kind,
            stdout_bytes=stdout_bytes,
            stdout_lines=stdout_lines,
            stderr_bytes=stderr_bytes,
            stderr_lines=stderr_lines,
        )

    def _record_failed_feature_check_attempt(
        self,
        feature: Feature,
        declaration: Any,
        attempt: FeatureCheckAttempt,
        wave_number: int,
        repair_follows: bool,
    ) -> None:
        """Say at once that one attempt of the whole-feature check failed.

        Build FEAT-1F44 (13 October 2026): a failed attempt was only a
        console line until the final record was written, so the failure was
        invisible in the log, in events.jsonl and on disk for 50 minutes while
        the repair round ran. This leaves a WARNING in the log and one
        ``FeatureCheckAttemptEvent`` in events.jsonl as soon as it happens.

        Neither carries the declared command or any of its output: both can
        hold a credential, and both are published beyond the sandbox. The
        check is named by a fixed label, the failure by a fixed word, and the
        output by its size. ``declaration`` is accepted for the caller's
        symmetry; its command is never read here. The full output stays in
        the final record and the Player's feedback, unchanged.

        Neither half can fail the build.
        """
        failure_kind = attempt.failure_kind or (
            FAILURE_KIND_TIMED_OUT if attempt.timed_out
            else FAILURE_KIND_COULD_NOT_START if attempt.exit_code is None
            else FAILURE_KIND_EXIT_NONZERO
        )
        try:
            logger.warning(
                "Whole-feature check attempt %d failed (%s): "
                "failure_kind=%s exit_code=%s timed_out=%s "
                "duration_seconds=%.1f repair_follows=%s "
                "stdout_bytes=%d stdout_lines=%d "
                "stderr_bytes=%d stderr_lines=%d",
                attempt.attempt,
                FEATURE_CHECK_LABEL,
                failure_kind,
                attempt.exit_code,
                attempt.timed_out,
                attempt.duration_seconds,
                repair_follows,
                attempt.stdout_bytes,
                attempt.stdout_lines,
                attempt.stderr_bytes,
                attempt.stderr_lines,
            )
        except Exception:  # noqa: BLE001 — a log line never fails a build
            pass

        sha = str(attempt.candidate_sha or "")
        if not re.fullmatch(r"[0-9a-f]{7,64}", sha):
            sha = "unknown"
        try:
            event = FeatureCheckAttemptEvent(
                run_id=f"run-{feature.id}",
                feature_id=feature.id,
                task_id=feature.id,
                agent_role="router",
                attempt=attempt.attempt,
                timestamp=datetime.now().isoformat(),
                check_attempt=attempt.attempt,
                failure_kind=failure_kind,
                exit_code=attempt.exit_code,
                timed_out=attempt.timed_out,
                duration_seconds=max(float(attempt.duration_seconds), 0.0),
                candidate_sha=sha,
                wave_number=wave_number,
                repair_follows=repair_follows,
                stdout_bytes=attempt.stdout_bytes,
                stdout_lines=attempt.stdout_lines,
                stderr_bytes=attempt.stderr_bytes,
                stderr_lines=attempt.stderr_lines,
            )
            asyncio.run(self._emitter.emit(event))
        except Exception as exc:  # noqa: BLE001 — telemetry never fails a build
            # The exception's type only: a validation message quotes inputs.
            logger.warning(
                "Failed to emit the whole-feature check attempt event: %s",
                type(exc).__name__,
            )

    def _finish_feature_check(
        self,
        feature: Feature,
        worktree: Worktree,
        declaration: Any,
        attempts: List[FeatureCheckAttempt],
        wave_results: List[WaveExecutionResult],
        *,
        status: str,
    ) -> FeatureCheckOutcome:
        """Write the receipt and, on a FAILURE only, fail the feature.

        The failure rail: a failed gate result on the last wave (which the
        finaliser already reads as a failed feature) and that wave un-marked
        on disk, so a resume re-runs it rather than skipping an unproven wave.

        A check that COULD NOT RUN takes neither rail: it is not a pass and it
        is not a fault of the build, so it writes its record, says why, and
        leaves the build's own result alone.
        """
        last_attempt = attempts[-1]
        passed = status == FEATURE_CHECK_PASSED
        could_not_run = status == FEATURE_CHECK_COULD_NOT_RUN
        reason: Optional[str]
        if passed:
            reason = None
        elif could_not_run:
            reason = (
                "the project's check could not run: "
                f"{last_attempt.could_not_run_reason}"
            )
        else:
            reason = last_attempt.failure_reason
        not_checked = list(last_attempt.not_checked)
        not_checked_total = last_attempt.not_checked_total
        if could_not_run:
            # Nothing was looked at, so every example the feature promised is
            # named as not checked, with the project's own reason.
            everything = merge_not_checked(
                not_checked,
                [
                    {
                        "name": title,
                        "reason": str(last_attempt.could_not_run_reason or ""),
                    }
                    for title in feature_scenario_titles(feature)
                ],
                # The check could not run, so that is why each of these was
                # not checked.
                later_reason_wins=True,
            )
            not_checked = everything
            not_checked_total = max(not_checked_total, len(everything))
        outcome = FeatureCheckOutcome(
            feature_id=feature.id,
            status=status,
            declared=True,
            command=declaration.command,
            timeout=declaration.timeout,
            attempts=attempts,
            reason=reason,
            not_checked=not_checked,
            not_checked_total=not_checked_total,
            observations=list(last_attempt.observations),
            observations_total=last_attempt.observations_total,
            could_not_run_reason=(
                last_attempt.could_not_run_reason if could_not_run else None
            ),
            notes=list(last_attempt.notes),
        )
        try:
            receipt_path = write_feature_check_receipt(
                outcome, Path(worktree.path)
            )
        except Exception as exc:  # noqa: BLE001 — a receipt never fails a build
            logger.warning(
                "Whole-feature check receipt could not be written: %s", exc
            )
            receipt_path = None

        if passed or could_not_run:
            return outcome

        summary = (
            f"the whole-feature check failed ({last_attempt.failure_reason}) "
            f"after {len(attempts)} attempt(s): {FEATURE_CHECK_LABEL}"
        )
        last = wave_results[-1] if wave_results else None
        if last is not None:
            last.smoke_gate_result = SmokeGateResult(
                passed=False,
                exit_code=(
                    -1 if last_attempt.timed_out
                    else (
                        last_attempt.exit_code
                        if last_attempt.exit_code is not None
                        else 1
                    )
                ),
                stdout=last_attempt.stdout_tail,
                stderr=summary,
                timed_out=last_attempt.timed_out,
                command=(
                    "whole-feature check (toolchain.feature_check): "
                    f"{FEATURE_CHECK_LABEL}"
                ),
                timeout=declaration.timeout,
                after_wave=last.wave_number,
            )
            self._unmark_wave_completed(feature, last.wave_number)
        logger.error(
            "Whole-feature check FAILED, so this feature is marked failed: "
            "%s%s",
            summary,
            f" (receipt: {receipt_path})" if receipt_path else "",
        )
        if not self.quiet:
            console.print(f"[red]✗ {summary}[/red]", markup=True)
        return outcome

    def _build_smoke_feedback(
        self,
        smoke_result: "SmokeGateResult",
        feature: Feature,
        worktree_root: Optional[Path] = None,
        wave_task_ids: Optional[List[str]] = None,
    ) -> str:
        """Compose Player-facing feedback from a failed post-wave smoke gate.

        TASK-AB-COACHRUNPARITY01 (arm a). Frames the smoke failure as a
        runtime-parity defect ("passes pytest but does not run") so the Player
        fixes the real runtime entry point — the failure mode the per-task
        Coach's pytest run is structurally blind to (pytest puts the worktree
        root on ``sys.path``; a standalone ``python <module>`` invocation does
        not). Includes the command, the failure reason, and a stderr tail.

        TASK-AB-STALEATTRIB01: when the smoke command is recognisably a
        test-runner invocation, the failure is framed as "a test in the
        feature smoke suite failed under this task's changes" (naming the
        failing tests when parseable) instead of the runs-standalone import
        framing. And when a failing test's file was authored by an earlier
        (non-wave) task, the feedback names that task and grants a
        narrowly-scoped stale-assertion permission. All attribution fails
        OPEN (``path-string-mismatch-is-not-dishonesty.md``) — unmatched /
        ambiguous / missing records leave the framing unchanged, and the red
        signal is never suppressed.
        """
        reason = (
            f"timed out after {smoke_result.timeout}s"
            if smoke_result.timed_out
            else (
                f"exit={smoke_result.exit_code}, "
                f"expected={feature.smoke_gates.expected_exit}"
            )
        )
        stderr_tail = "\n".join(
            (smoke_result.stderr or "").rstrip().splitlines()[-40:]
        )
        # TASK-AB-STALEATTRIB01: parse pytest failing-test node IDs from the
        # combined runner output (pytest writes the short summary to stdout).
        combined_output = "\n".join(
            part
            for part in (smoke_result.stdout, smoke_result.stderr)
            if part
        )
        failing_lines = extract_failing_test_lines(combined_output)

        # TASK-AB-REVIEWCLEAN01 (item 6): framing wording lives in
        # stale_test_attribution.smoke_gate_header (shared with the per-task
        # parity guard's rationale composer).
        header = smoke_gate_header(smoke_result.command)

        failing_section = (
            "Failing tests:\n" + "\n".join(failing_lines) + "\n\n"
            if failing_lines
            else ""
        )
        feedback = (
            header
            + f"Smoke command:\n{smoke_result.command}\n\n"
            + f"Result: {reason}\n\n"
            + failing_section
            + f"stderr (last 40 lines):\n{stderr_tail or '(empty)'}"
        )

        # TASK-AB-STALEATTRIB01: authorship join — the wave's own tasks are
        # "current" (they receive this feedback); only an earlier/other task
        # is attributable. Fails OPEN on any miss/ambiguity/exception.
        notes = stale_test_notes(
            failing_lines, worktree_root, set(wave_task_ids or [])
        )
        if notes:
            feedback += "\n\n" + "\n\n".join(notes)
        return feedback

    def _run_post_wave_smoke_gate(
        self,
        wave_number: int,
        task_ids: List[str],
        feature: Feature,
        worktree: Worktree,
        wave_result: WaveExecutionResult,
    ) -> SmokeGatePhaseOutcome:
        """Run the post-wave smoke gate with a bounded feedback-retry loop.

        TASK-AB-COACHRUNPARITY01 (arm a). Owns the retry loop extracted from the
        wave-enumerate loop so the control flow stays readable and the retry
        logic is unit-testable. The caller is the wave-enumerate loop; this
        helper is tightly coupled to it (it calls back into ``_execute_wave``)
        and must not be invoked from any other context.

        Behaviour, per smoke result:

        * **passed** (the declared ``expected_exit``): return
          ``terminate=False`` (continue to the next wave).
        * **failed, real**, retries remaining: feed the smoke stderr back to the
          Player as turn-1 ``seed_feedback`` and re-execute the wave (attempt N),
          then loop to re-run the gate.
        * **failed, real**, retries exhausted: emit the existing terminate
          banner + stderr tail and return ``terminate=True``.

        Returns
        -------
        SmokeGatePhaseOutcome
            ``terminate`` (whether the wave-enumerate loop should break) and
            ``final_wave_result`` (the result to replace ``wave_results[-1]``).
        """
        retries_remaining = self._smoke_gate_max_retries
        attempt = 0
        while True:
            smoke_result = self._checked_writer(worktree, run_smoke_gate,
                feature.smoke_gates,
                cwd=Path(worktree.path),
                wave_number=wave_number,
                venv_python=self._bootstrap_venv_python,
                evidence=request_from_repo(
                    "smoke command", self.repo_root,
                    feature=str(feature.id), wave=wave_number,
                ),
            )
            wave_result.smoke_gate_result = smoke_result

            if smoke_result.passed:
                return SmokeGatePhaseOutcome(
                    terminate=False, final_wave_result=wave_result
                )

            # Smoke gate FAILED.
            # Real failure (timeout or wrong exit code).
            if retries_remaining <= 0:
                # Retries exhausted (or disabled): terminate, preserving the
                # worktree. Existing terminate banner + stderr tail (TASK-SGER-001).
                reason = (
                    f"timed out after {smoke_result.timeout}s"
                    if smoke_result.timed_out
                    else (
                        f"exit={smoke_result.exit_code}, "
                        f"expected={feature.smoke_gates.expected_exit}"
                    )
                )
                console.print(
                    f"[red]✗ Smoke gate failed after wave {wave_number}[/red] "
                    f"({reason}). Subsequent waves not started; worktree "
                    f"preserved at {worktree.path}."
                )
                stderr_tail = "\n".join(
                    (smoke_result.stderr or "").rstrip().splitlines()[-20:]
                )
                if stderr_tail:
                    console.print(
                        f"[red]stderr (last 20 lines):[/red]\n{stderr_tail}"
                    )
                return SmokeGatePhaseOutcome(
                    terminate=True, final_wave_result=wave_result
                )

            # Retry: feed the smoke error back to the Player and re-enter the
            # wave. Bounded by _smoke_gate_max_retries.
            retries_remaining -= 1
            attempt += 1
            smoke_feedback = self._build_smoke_feedback(
                smoke_result,
                feature,
                worktree_root=Path(worktree.path),
                wave_task_ids=task_ids,
            )
            console.print(
                f"[yellow]↻ Smoke gate failed after wave {wave_number}[/yellow] "
                f"— re-entering the wave with the runtime error as Player "
                f"feedback (retry {attempt}/{self._smoke_gate_max_retries})."
            )
            if self._wave_display:
                # The re-entered wave runs under the same rule as the first
                # pass, so the banner asks the resolver rather than printing
                # the wave size (read only, log=False — the dispatcher emits
                # the authoritative log). The answer is the cached one, so it
                # cannot differ from what the executor enforces.
                retry_max_parallel = resolve_max_parallel(
                    self._parallel_config,
                    wave_number=wave_number,
                    wave_size=len(task_ids),
                    log=False,
                    wave_task_paths=self._wave_task_paths(
                        wave_number, task_ids, feature, worktree
                    ),
                )
                self._wave_display.start_wave(
                    wave_number, task_ids, max_parallel=retry_max_parallel
                )
            wave_result = self._execute_wave(
                wave_number, task_ids, feature, worktree,
                seed_feedback=smoke_feedback, attempt=attempt,
            )
            # Refresh the wave-completion display for the re-run (S1).
            if self._wave_display:
                passed = sum(1 for r in wave_result.results if r.success)
                failed = len(wave_result.results) - passed
                skipped = sum(
                    1 for r in wave_result.results
                    if r.final_decision == "skipped"
                )
                recovered = sum(
                    1 for r in wave_result.results if r.recovery_count > 0
                )
                self._wave_display.complete_wave(
                    wave_number, passed, failed, skipped, recovered
                )

            # Loop: re-run the smoke gate against the re-executed wave.

    async def _execute_wave_parallel(
        self,
        wave_number: int,
        task_ids: List[str],
        feature: Feature,
        worktree: Worktree,
        seed_feedback: Optional[str] = None,
        smoke_command: Optional[str] = None,
        smoke_expected_exit: int = 0,
        feature_check_repair: Optional[FeatureCheckRepair] = None,
    ) -> List[TaskExecutionResult]:
        """
        Execute all tasks in a wave in parallel using asyncio.

        This method creates parallel execution tasks using asyncio.to_thread()
        to achieve true parallelism with the blocking AutoBuildOrchestrator.
        Already-completed tasks are skipped before parallel execution.

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
        # (task, timeout, keyword arguments) for each task to run, turned
        # into calls once the wave's real concurrency is known.
        queued_calls: List[Tuple[Any, Any, Dict[str, Any]]] = []
        task_id_mapping = []  # Track which task_id corresponds to which async task
        cancellation_events: Dict[str, threading.Event] = {}  # Per-task cancellation (TASK-ASF-007)
        timeout_events: Dict[str, threading.Event] = {}  # Per-task feature-level timeout (TASK-ABFIX-006)
        per_task_timeouts: Dict[str, int] = {}  # Resolved per-task timeout (TASK-ATR-001)
        # The repair round each re-opened task starts (20 October 2026).
        repair_rounds: Dict[str, RepairRound] = {}

        # Track wave start time for per-task budget propagation (TASK-ABFIX-004)
        wave_start_time = time.monotonic()

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

            # Skip already completed tasks (for resume) — but NEVER on a
            # gate-driven re-entry of this wave.
            #
            # 19 September 2026, found by driving the real runner: a task is
            # marked completed as soon as its Coach approves, BEFORE the
            # post-wave gates run. Every gate that re-enters the wave with
            # feedback (the smoke gate, the whole-feature
            # check) therefore found all of its tasks "already completed",
            # skipped them, ran no Player turn, and re-ran the gate against an
            # unchanged candidate: the repair loop looked wired and repaired
            # nothing. ``seed_feedback`` is non-None only on such a re-entry,
            # and the feedback is addressed to exactly these tasks, so they are
            # re-opened and run again with it.
            if task.status == "completed" and seed_feedback is not None:
                logger.info(
                    "Re-opening %s for a gate-driven re-entry of wave %s "
                    "(it was approved, and the gate that ran after it failed)",
                    task_id, wave_number,
                )
                task.status = "in_progress"
                # The repair round writes the same turn file names again, so
                # the round that was just approved is moved aside first, names
                # unchanged, into round-<N>/ (18 October 2026). Never fails.
                # Queue only the intent. Fingerprints and baseline are captured
                # by the actual writer after checkout ownership is acquired.
                repair_rounds[task_id] = True
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

            # TASK-FPTC-003: operator_handoff short-circuit. Tasks the
            # orchestrator must hand off to a human operator are never
            # dispatched into the Player↔Coach loop — they are reported as
            # deferred (terminal-but-not-failed) and the wave continues.
            # This branch is the earliest possible check: before
            # _update_task_started, before timeout resolution, before the
            # AutoBuildOrchestrator is constructed, before any SDK budget
            # burns.
            deferred_result = self._maybe_defer_operator_handoff(
                task, feature, wave_number
            )
            if deferred_result is not None:
                results.append(deferred_result)
                continue

            # The actual checkout owner marks this task started at admission.

            # Display task start
            if self._wave_display:
                self._wave_display.update_task_status(
                    task_id, "in_progress", f"Executing: {task.name}"
                )
            else:
                console.print(f"  [cyan]▶[/cyan] Executing {task_id}: {task.name}")

            # Create per-task cancellation and timeout events (TASK-ASF-007, TASK-ABFIX-006)
            cancel_event = threading.Event()
            timeout_event = threading.Event()
            cancellation_events[task_id] = cancel_event
            timeout_events[task_id] = timeout_event

            # Add to parallel execution queue, wrapped with per-task timeout.
            # Compute remaining budget at the moment this task is queued (TASK-ABFIX-004).
            # Per-task timeout may be overridden via frontmatter.autobuild.task_timeout (TASK-ATR-001).
            # wave_size = total tasks in the wave, used by Coach for isolation (TASK-ABFIX-005).
            try:
                task_data_for_timeout = TaskLoader.load_task(task_id, repo_root=self.repo_root)
                effective_task_timeout = self._resolve_task_timeout(
                    task_data_for_timeout,
                    task_id,
                    estimated_minutes=getattr(task, "estimated_minutes", None),
                )
            except Exception as e:
                logger.warning(
                    f"[{task_id}] Could not pre-load task data for timeout "
                    f"resolution: {e}; using feature-level "
                    f"task_timeout={self.task_timeout}s"
                )
                effective_task_timeout = self.task_timeout
            per_task_timeouts[task_id] = effective_task_timeout

            elapsed_at_queue = time.monotonic() - wave_start_time
            task_budget = max(0.0, effective_task_timeout - elapsed_at_queue)
            # The call is built after the loop, once it is known whether the
            # tasks of this wave will really run at the same time.
            queued_calls.append((
                task,
                effective_task_timeout,
                dict(
                    cancellation_event=cancel_event,
                    timeout_event=timeout_event,
                    time_budget_seconds=task_budget,
                    wave_size=len(task_ids),
                    effective_task_timeout=effective_task_timeout,
                    seed_feedback=seed_feedback,  # TASK-AB-COACHRUNPARITY01 (arm a)
                    smoke_command=smoke_command,  # TASK-AB-COACHRUNPARITY01 (arm b)
                    smoke_expected_exit=smoke_expected_exit,  # TASK-AB-COACHRUNPARITY01 (arm b)
                    # Whole-feature repair round only; absent otherwise, so
                    # every other wave's call is exactly as before.
                    **(
                        {"feature_check_repair": feature_check_repair}
                        if feature_check_repair is not None
                        else {}
                    ),
                    # A re-opened task only; absent otherwise.
                    **(
                        {"repair_round": repair_rounds[task_id]}
                        if task_id in repair_rounds
                        else {}
                    ),
                ),
            ))
            task_id_mapping.append(task_id)

        # Execute all tasks in parallel if any, respecting max_parallel limit
        if queued_calls:
            # TASK-VRF-006: Resolve max_parallel via strategy (supports static/dynamic/per-wave)
            effective_max_parallel = resolve_max_parallel(
                self._parallel_config,
                wave_number=wave_number,
                wave_size=len(task_ids),
                # Two tasks that would work on the same area of the
                # repository do not run at the same time. Same mapping the
                # display banner above resolved with.
                wave_task_paths=self._wave_task_paths(
                    wave_number, task_ids, feature, worktree
                ),
            )

            # Do this wave's tasks really change the working copy at the
            # same time? Only then can git not tell their changes apart
            # (FEAT-2C42). A wave of several tasks run one at a time
            # (max_parallel 1, or tasks on the same area) is not shared:
            # each task measures from its own starting commit.
            shares_working_copy = tasks_run_at_the_same_time(
                len(queued_calls), effective_max_parallel
            )

            async def _dispatch_queued_call(
                task: FeatureTask,
                task_id: str,
                call_timeout: int,
                call_kwargs: Dict[str, Any],
            ) -> TaskExecutionResult:
                # This coroutine is awaited only after bound_concurrency has
                # acquired the real semaphore slot.
                try:
                    admitted = asyncio.Event()
                    loop = asyncio.get_running_loop()
                    worker = asyncio.create_task(asyncio.to_thread(
                        self._execute_task, task, feature, worktree,
                        shares_working_copy=False,
                        admission_event=lambda: loop.call_soon_threadsafe(admitted.set), **call_kwargs,
                    ))
                    # The time limit starts at admission. A worker that ends
                    # without ever being admitted ends the wait too.
                    admission = asyncio.ensure_future(admitted.wait())
                    await asyncio.wait(
                        {worker, admission}, return_when=asyncio.FIRST_COMPLETED
                    )
                    admission.cancel()
                    return await asyncio.wait_for(asyncio.shield(worker), timeout=call_timeout)
                except asyncio.TimeoutError:
                    for event_name in ("cancellation_event", "timeout_event"):
                        event = call_kwargs.get(event_name)
                        if event is not None:
                            event.set()
                    raise

            tasks_to_execute = [
                _dispatch_queued_call(
                    task,
                    task_id,
                    call_timeout,
                    call_kwargs,
                )
                for (task, call_timeout, call_kwargs), task_id in zip(
                    queued_calls, task_id_mapping
                )
            ]

            # Apply concurrency bound if max_parallel is set.
            # TASK-FIX-MAXPARALLEL01: extracted to parallel_strategy.bound_concurrency
            # so the wrapping logic is unit-testable in isolation (AC-4). Behaviour
            # is identical to the previous inline semaphore loop.
            tasks_to_execute = bound_concurrency(
                tasks_to_execute, effective_max_parallel
            )

            # TASK-CEF-004: Log gather start for cancellation diagnostics
            # TASK-ATR-001: Show per-task timeouts (may differ via frontmatter override)
            timeouts_summary = ", ".join(
                f"{tid}={per_task_timeouts.get(tid, self.task_timeout)}s"
                for tid in task_id_mapping
            )
            logger.info(
                f"Starting parallel gather for wave {wave_number}: "
                f"tasks={task_id_mapping}, task_timeout={self.task_timeout}s "
                f"(per-task=[{timeouts_summary}])"
            )

            parallel_results = None
            try:
                parallel_results = await asyncio.gather(*tasks_to_execute, return_exceptions=True)
            finally:
                # Set timeout_event for tasks that timed out BEFORE general cancellation (TASK-ABFIX-006).
                # This lets AutoBuildOrchestrator._loop_phase distinguish "timeout" from "cancelled".
                if parallel_results is not None:
                    for tid, res in zip(task_id_mapping, parallel_results):
                        if isinstance(res, asyncio.TimeoutError) and tid in timeout_events:
                            timeout_events[tid].set()

                # Signal ALL threads to stop after gather completes (TASK-ASF-007)
                # Safe: completed threads have already exited; timed-out threads
                # will see the event at their next cancellation checkpoint.
                for event in cancellation_events.values():
                    event.set()

            # Process results and handle exceptions
            for task_id, result in zip(task_id_mapping, parallel_results):
                if isinstance(result, asyncio.TimeoutError):
                    # A late writable Coach artifact cannot settle the still-running
                    # worker or replace the original deadline failure.
                    # TASK-ATR-001: Use per-task resolved timeout for messages
                    effective_task_timeout = per_task_timeouts.get(task_id, self.task_timeout)
                    timeout_msg = (
                        f"Task {task_id} timed out after {effective_task_timeout}s "
                        f"({effective_task_timeout // 60} min)"
                    )
                    # TASK-FIX-OBS2: Read last state from per-task progress log
                    progress_log = (
                        self.repo_root / ".guardkit" / "autobuild" / task_id / "progress.log"
                    )
                    last_state = ""
                    if progress_log.exists():
                        try:
                            lines = progress_log.read_text().strip().splitlines()
                            last_state = f" Last log: {lines[-1]}" if lines else ""
                        except Exception:
                            pass
                    # TASK-FIX-LATEAPPR R3: dropped the hardcoded
                    # ``SDK timeout budget was {sdk_timeout}s per
                    # invocation`` clause. After TASK-FIX-CRSTL-MULT the
                    # actual per-specialist timeout is scaled by
                    # complexity and printed verbatim into the per-task
                    # ``progress.log`` as ``[<task_id>] SDK timeout: <N>s``.
                    # The hardcoded ``self.sdk_timeout`` (orchestrator
                    # base, default 1200s) was misleading whenever CRSTL
                    # scaling kicked in.
                    logger.warning(
                        f"TIMEOUT (feature-level): task_timeout={effective_task_timeout}s expired "
                        f"for {task_id}. See per-invocation '[{task_id}] SDK timeout: <N>s' "
                        f"lines in progress.log for actual values applied."
                        f"{last_state}"
                    )
                    logger.warning(timeout_msg)
                    error_result = TaskExecutionResult(
                        task_id=task_id,
                        success=False,
                        total_turns=0,
                        final_decision="timeout",
                        error=timeout_msg,
                    )
                    results.append(error_result)

                    # Update task status in display with TIMEOUT status
                    if self._wave_display:
                        self._wave_display.update_task_status(
                            task_id, "timeout", timeout_msg,
                            turns=0, decision="timeout"
                        )

                    # Update feature with timeout result
                    self._update_feature(feature, task_id, error_result, wave_number)

                elif isinstance(result, asyncio.CancelledError):
                    # TASK-CEF-004: Cancellation diagnostics logging
                    elapsed = time.monotonic() - wave_start_time
                    cancel_event_set = cancellation_events.get(task_id, threading.Event()).is_set()
                    timeout_event_set = timeout_events.get(task_id, threading.Event()).is_set()
                    logger.error(
                        f"CANCELLED: {task_id} received CancelledError in wave {wave_number}. "
                        f"Elapsed: {elapsed:.1f}s, "
                        f"cancellation_event={cancel_event_set}, "
                        f"timeout_event={timeout_event_set}. "
                        f"CancelledError originated from within worker thread "
                        f"(not external cancellation — gather returned results normally)."
                    )
                    cancel_msg = f"Task {task_id} was cancelled"
                    error_result = TaskExecutionResult(
                        task_id=task_id,
                        success=False,
                        total_turns=0,
                        final_decision="cancelled",
                        error=cancel_msg,
                    )
                    results.append(error_result)

                    # Update task status in display
                    if self._wave_display:
                        self._wave_display.update_task_status(
                            task_id, "cancelled", cancel_msg,
                            turns=0, decision="cancelled"
                        )

                    # Update feature with cancelled result
                    self._update_feature(feature, task_id, error_result, wave_number)

                elif isinstance(result, Exception):
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

                elif isinstance(result, BaseException):
                    base_msg = f"Task {task_id} failed with {type(result).__name__}: {result}"
                    logger.error(f"BASE_EXCEPTION: {task_id} — {base_msg}")
                    error_result = TaskExecutionResult(
                        task_id=task_id,
                        success=False,
                        total_turns=0,
                        final_decision="error",
                        error=base_msg,
                    )
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
                        # TASK-VPR-003: Pass SDK turn data to display
                        _sdk_turns = result.sdk_turns_per_invocation[-1] if result.sdk_turns_per_invocation else None
                        _sdk_max = None
                        _sdk_hit = False
                        if result.sdk_turns_per_invocation:
                            # Use last invocation's data for display
                            _sdk_hit = result.sdk_ceiling_hits > 0
                        self._wave_display.update_task_status(
                            task_id, status, result.final_decision,
                            turns=result.total_turns, decision=result.final_decision,
                            sdk_turns_used=_sdk_turns,
                            sdk_ceiling_hit=_sdk_hit,
                        )

                    # Update feature with result
                    self._update_feature(feature, task_id, result, wave_number)

        return results

    @staticmethod
    def _per_task_smoke_command(
        feature: Feature, wave_number: int
    ) -> Tuple[Optional[str], int]:
        """Per-task runtime-parity command for ``wave_number``, gated on scope.

        TASK-FIX-PARITYWAVE01. The per-task runtime-parity check (arm b of
        TASK-AB-COACHRUNPARITY01) is a *preview* of the post-wave smoke gate:
        before the per-task Coach approves a single-task wave it runs the
        feature's ``smoke_gates.command`` (the deliverable's real runtime
        entry point) and overrides approve->feedback on a ran-and-failed
        result. That preview must only run for waves where the post-wave gate
        itself fires — otherwise a *later* wave's smoke command (whose CLI
        subcommand does not exist until that wave's deliverable lands) is run
        against an *earlier* wave's deliverable, producing an exit-2
        ``No such command`` the task cannot fix.

        Returns ``(None, 0)`` — an absent signal / no-op per arm b's
        ``ran=False`` safety — when no smoke gate is configured OR the gate
        does not fire for this wave (``should_fire_for_wave``). Delegates to
        ``should_fire_for_wave`` for ALL ``after_wave`` forms (int / list /
        ``"all"`` / unset), matching the post-wave gate's scope exactly.
        """
        if feature.smoke_gates is None or not should_fire_for_wave(
            feature.smoke_gates, wave_number
        ):
            return None, 0
        return feature.smoke_gates.command, feature.smoke_gates.expected_exit

    def _execute_wave(
        self,
        wave_number: int,
        task_ids: List[str],
        feature: Feature,
        worktree: Worktree,
        seed_feedback: Optional[str] = None,
        attempt: int = 0,
    ) -> WaveExecutionResult:
        """
        Execute all tasks in a single wave in parallel.

        This method delegates to _execute_wave_parallel() for parallel task
        execution using asyncio. It preserves all existing display logic.

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
        seed_feedback : Optional[str]
            TASK-AB-COACHRUNPARITY01 (arm a). Turn-1 feedback injected into
            every task's Player in this wave run. Non-None only on a
            smoke-gate re-run, carrying the smoke stderr so the Player fixes
            the runtime failure the Coach's pytest missed.
        attempt : int
            TASK-AB-COACHRUNPARITY01 (arm a, S2). 0 for the first execution of
            this wave, 1+ for smoke-feedback re-runs. Suffixed onto the
            ``wave.completed`` telemetry ``wave_id`` so a re-run emits a
            distinct, non-duplicate event (TASK-INST-004 consumers key on it).

        Returns
        -------
        WaveExecutionResult
            Results for this wave

        Notes
        -----
        TASK-AB-COACHRUNPARITY01 (C1): this method no longer calls
        ``_mark_wave_completed``. Marking a wave completed persists
        ``completed_waves`` to disk; doing it here (the instant tasks pass)
        would record a wave as completed *before* its post-wave smoke gate has
        run, so a smoke failure + retry (or a crash in that window) would let a
        resume skip an unverified wave. The wave-enumerate loop now marks
        completion only after the smoke phase resolves successfully.
        """
        # Update current wave tracking
        feature.execution.current_wave = wave_number
        feature.execution.last_updated = datetime.now().isoformat()
        FeatureLoader.save_feature(feature, self.repo_root)

        # TASK-AB-COACHRUNPARITY01 (arm b) + TASK-FIX-PARITYWAVE01: the
        # deliverable's runtime entry point, derived once here (this method
        # already holds `feature`) and threaded to the per-task Coach as a
        # plain string. `_execute_task` stays ignorant of the smoke-gate
        # config object. The derivation is gated on the smoke gate's
        # `after_wave` scope so a *later* wave's smoke command is never run as
        # a per-task parity preview against an *earlier* wave's deliverable
        # (which would exit-2 `No such command` and block the task to
        # max_turns — FEAT-HARV wave-2 walker vs the wave-3 `memory harvest`
        # CLI). `should_fire_for_wave` already gates the post-wave gate at the
        # wave-loop site; the per-task preview reuses the same scope.
        smoke_command, smoke_expected_exit = self._per_task_smoke_command(
            feature, wave_number
        )
        # Whole-feature repair round only (18 October 2026): set by
        # _run_feature_check for the length of this call, None otherwise.
        feature_check_repair = getattr(
            self, "_feature_check_repair_for_wave", None
        )

        # Execute tasks in parallel
        results = asyncio.run(
            self._execute_wave_parallel(
                wave_number, task_ids, feature, worktree,
                seed_feedback=seed_feedback,
                smoke_command=smoke_command,
                smoke_expected_exit=smoke_expected_exit,
                **(
                    {"feature_check_repair": feature_check_repair}
                    if feature_check_repair is not None
                    else {}
                ),
            )
        )

        all_succeeded = all(r.success for r in results)

        # NOTE (C1): wave-completion marking moved to the wave-enumerate loop,
        # gated on smoke-gate success. See the class/method docstring above.

        # Emit wave.completed event (TASK-INST-004). S2: a smoke-feedback
        # re-run (attempt > 0) gets a distinct wave_id suffix so consumers see
        # both executions instead of a duplicate-id collision.
        wave_event_id = (
            f"wave-{wave_number}" if attempt == 0
            else f"wave-{wave_number}-retry-{attempt}"
        )
        tasks_completed_count = sum(1 for r in results if r.success)
        task_failures_count = sum(1 for r in results if not r.success)
        try:
            asyncio.run(
                self._emit_wave_completed(
                    feature_id=feature.id,
                    wave_id=wave_event_id,
                    wave_number=wave_number,
                    worker_count=len(task_ids),
                    queue_depth_start=len(task_ids),
                    queue_depth_end=len(task_ids) - len(results),
                    tasks_completed=tasks_completed_count,
                    task_failures=task_failures_count,
                    rate_limit_count=0,
                    p95_task_latency_ms=None,
                    run_id=f"run-{feature.id}",
                    task_id=feature.id,
                )
            )
        except Exception as exc:
            logger.warning("Failed to emit wave.completed event: %s", exc)

        return WaveExecutionResult(
            wave_number=wave_number,
            task_ids=task_ids,
            results=results,
            all_succeeded=all_succeeded,
        )

    # ========================================================================
    # Instrumentation Helpers (TASK-INST-004)
    # ========================================================================

    async def _emit_wave_completed(
        self,
        feature_id: str,
        wave_id: str,
        wave_number: int,
        worker_count: int,
        queue_depth_start: int,
        queue_depth_end: int,
        tasks_completed: int,
        task_failures: int,
        rate_limit_count: int,
        p95_task_latency_ms: Optional[float],
        run_id: str,
        task_id: str,
    ) -> None:
        """Emit wave.completed lifecycle event.

        Parameters
        ----------
        feature_id : str
            Parent feature identifier.
        wave_id : str
            Unique wave identifier (distinct per wave).
        wave_number : int
            Wave number (1-indexed).
        worker_count : int
            Number of concurrent workers.
        queue_depth_start : int
            Queue depth at wave start.
        queue_depth_end : int
            Queue depth at wave end.
        tasks_completed : int
            Number of successfully completed tasks.
        task_failures : int
            Number of failed tasks.
        rate_limit_count : int
            Number of rate limit events in wave.
        p95_task_latency_ms : Optional[float]
            95th percentile task latency.
        run_id : str
            Run identifier.
        task_id : str
            Task/feature identifier for event.
        """
        event = WaveCompletedEvent(
            run_id=run_id,
            feature_id=feature_id,
            task_id=task_id,
            agent_role="router",
            attempt=1,
            timestamp=datetime.now().isoformat(),
            wave_id=wave_id,
            worker_count=worker_count,
            queue_depth_start=queue_depth_start,
            queue_depth_end=queue_depth_end,
            tasks_completed=tasks_completed,
            task_failures=task_failures,
            rate_limit_count=rate_limit_count,
            p95_task_latency_ms=p95_task_latency_ms,
        )
        await self._emitter.emit(event)

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

    def _task_estimate_floor_seconds(
        self, estimated_minutes: Optional[int]
    ) -> int:
        """Estimate-derived per-task timeout floor, or ``0`` when absent.

        ``estimated_minutes × 60 × factor × multiplier`` (red-baseline retro,
        L12 item 3). Returns ``0`` for a missing / non-positive estimate so
        callers can ``max()`` it against the feature default without effect.
        """
        if estimated_minutes is None or estimated_minutes <= 0:
            return 0
        return int(
            estimated_minutes * 60 * _estimate_timeout_factor()
            * self.timeout_multiplier
        )

    def _wave_task_paths(
        self,
        wave_number: int,
        task_ids: List[str],
        feature: Feature,
        worktree: Worktree,
    ) -> Dict[str, Optional[List[str]]]:
        """The paths every task in this wave says it will touch.

        One entry per task, in wave order, mapping the task's id to the
        repository-relative paths it declares, or ``None`` when it declares
        none. ``resolve_max_parallel`` uses this to run a wave one task at a
        time when two of its tasks would work on the same area.

        Read once per wave and remembered, so the read-only display banner
        and the dispatcher's authoritative decision are made from the same
        answer and can never disagree. Never raises: anything unreadable
        leaves a task as "did not say", which is the safe side.
        """
        cache = getattr(self, "_wave_task_paths_cache", None)
        if cache is None:
            cache = {}
            self._wave_task_paths_cache = cache

        key = (wave_number, tuple(task_ids))
        if key in cache:
            return cache[key]

        task_files: Dict[str, Path] = {}
        for task_id in task_ids:
            task = FeatureLoader.find_task(feature, task_id)
            file_path = getattr(task, "file_path", None) if task else None
            if file_path:
                task_files[task_id] = Path(file_path)

        try:
            paths = collect_wave_task_paths(
                task_ids,
                Path(worktree.path),
                task_files=task_files,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Wave %d: could not read what its tasks will touch (%s); "
                "treating every task as having declared nothing.",
                wave_number,
                exc,
            )
            paths = {task_id: None for task_id in task_ids}

        cache[key] = paths
        return paths

    def _resolve_wave_task_timeouts(self, feature: Feature) -> Dict[str, int]:
        """Resolve the EFFECTIVE per-task timeout for every queued task.

        TASK-FIX-TTO01. One pass over ``orchestration.parallel_groups`` before
        wave 1, so the run can DECLARE the budgets it will actually enforce
        instead of only the feature-level default.

        A task is absent from the map only when ``FeatureLoader.find_task``
        cannot find it in the feature. A task that IS found but whose markdown
        fails to load still gets a budget resolved and stored (the load error is
        swallowed to an empty dict, and the budget falls back to the feature
        default and ``estimated_minutes``). This method never raises.

        Returns
        -------
        Dict[str, int]
            ``task_id -> effective per-task timeout in seconds``, in
            wave/dispatch order.
        """
        resolved: Dict[str, int] = {}
        for task_ids in feature.orchestration.parallel_groups:
            for task_id in task_ids:
                if task_id in resolved:
                    continue
                task = FeatureLoader.find_task(feature, task_id)
                if task is None:
                    continue
                try:
                    task_data = TaskLoader.load_task(
                        task_id, repo_root=self.repo_root
                    )
                except Exception:
                    task_data = {}
                resolved[task_id] = self._resolve_task_timeout(
                    task_data,
                    task_id,
                    estimated_minutes=getattr(task, "estimated_minutes", None),
                )
        return resolved

    def _format_task_timeout_banner(
        self, effective_timeouts: Optional[Dict[str, int]] = None
    ) -> str:
        """Build the once-per-run task-budget banner text (TASK-FIX-TTO01).

        The banner is the run's single declaration of its own per-task budget
        and is consumed downstream (the build monitor derives its wedge window
        from it). Before this fix it printed ``self.task_timeout`` — the
        feature-level DEFAULT — so a task carrying
        ``frontmatter.autobuild.task_timeout`` (or one raised to its
        estimate-derived floor) ran on a budget the banner never mentioned.

        The declared number is now the LARGEST effective per-task budget, and
        the feature default plus the per-task breakdown are named alongside it.
        Over-declaring only delays a wedge call; under-declaring puts a watcher
        INSIDE guardkit's own timeout, so the max is the honest direction.
        """
        effective = effective_timeouts or {}
        declared = max(
            [self.task_timeout, *effective.values()]
        ) if effective else self.task_timeout
        text = f"task timeout: {declared // 60} min"
        if declared != self.task_timeout:
            text += f"; feature default: {self.task_timeout // 60} min"
        if effective:
            pairs = ", ".join(
                f"{task_id}={seconds}s" for task_id, seconds in effective.items()
            )
            text += f"; effective per-task: {pairs}"
        return text

    def _resolve_task_timeout(
        self,
        task_data: Dict[str, Any],
        task_id: str,
        estimated_minutes: Optional[int] = None,
    ) -> int:
        """
        Resolve the per-task feature-level timeout (TASK-ATR-001).

        Resolution order:
            1. ``frontmatter.autobuild.task_timeout`` (explicit per-task
               override — the operator's deliberate budget; honoured verbatim
               ONLY down to the min-turn floor below, which silently raises any
               override under ``MIN_TURN_BUDGET_SECONDS × max_turns``
               — 3000s at defaults — and logs a WARNING when it does)
            2. ``max(self.task_timeout, estimate-derived floor)`` — the
               feature-level default, RAISED to the task's own
               ``estimated_minutes``-derived floor when that is larger
               (red-baseline retro, L12 item 3). The flat feature floor alone
               guaranteed timeouts on the large tasks these features routinely
               carry, and a timeout masks whatever the real failure is.

        ``estimated_minutes`` is taken from the feature YAML's ``FeatureTask``
        (passed by the caller); when absent it falls back to a task-markdown
        ``frontmatter.estimated_minutes`` if present.

        When the explicit override is present, the raw frontmatter value is
        multiplied by ``self.timeout_multiplier`` and floored at
        ``MIN_TURN_BUDGET_SECONDS * self.max_turns`` to guarantee at least one
        minimum-budget turn per max-turn slot. Non-positive or non-integer
        overrides are rejected with a warning and the feature-level default
        (with the estimate floor applied) is used instead. An explicit
        override is NOT raised to the estimate floor — it is the operator's
        choice.

        Successful overrides / floor-raises are logged at INFO so operators
        can audit the per-task budget that was applied.
        """
        frontmatter = task_data.get("frontmatter", {}) or {}
        autobuild_cfg = frontmatter.get("autobuild", {}) or {}

        # Resolve the estimate: explicit arg (feature YAML) wins; else a
        # task-markdown frontmatter value if the author put one there.
        est = estimated_minutes
        if est is None:
            raw_est = frontmatter.get("estimated_minutes")
            try:
                est = int(raw_est) if raw_est is not None else None
            except (TypeError, ValueError):
                est = None
        estimate_floor = self._task_estimate_floor_seconds(est)

        if "task_timeout" not in autobuild_cfg:
            resolved = self.task_timeout
            if estimate_floor > resolved:
                logger.info(
                    f"[{task_id}] Raising task_timeout to estimate-derived "
                    f"floor: estimated_minutes={est} × 60 × "
                    f"{_estimate_timeout_factor()} × multiplier="
                    f"{self.timeout_multiplier} = {estimate_floor}s "
                    f"(feature default was {self.task_timeout}s)"
                )
                resolved = estimate_floor
            return resolved

        raw = autobuild_cfg.get("task_timeout")
        try:
            override_int = int(raw)
        except (TypeError, ValueError):
            logger.warning(
                f"[{task_id}] Invalid frontmatter.autobuild.task_timeout="
                f"{raw!r} (must be a positive integer); falling back to "
                f"feature-level task_timeout={self.task_timeout}s"
            )
            return max(self.task_timeout, estimate_floor)

        if override_int <= 0:
            logger.warning(
                f"[{task_id}] frontmatter.autobuild.task_timeout="
                f"{override_int}s must be > 0; falling back to "
                f"feature-level task_timeout={self.task_timeout}s"
            )
            return max(self.task_timeout, estimate_floor)

        from guardkit.orchestrator.autobuild import MIN_TURN_BUDGET_SECONDS

        multiplied = int(override_int * self.timeout_multiplier)
        floor = MIN_TURN_BUDGET_SECONDS * self.max_turns
        resolved = max(multiplied, floor)

        # The grammar up to "(feature default was ...s)" is CONSUMED DOWNSTREAM
        # (the build monitor's per-task budget parser) — do not reorder it.
        message = (
            f"[{task_id}] Per-task task_timeout override active: "
            f"frontmatter={override_int}s × multiplier={self.timeout_multiplier} "
            f"= {multiplied}s, floored at {floor}s → {resolved}s "
            f"(feature default was {self.task_timeout}s)"
        )
        if multiplied < floor:
            # TASK-FIX-TTO01: the min-turn floor SWALLOWED the operator's
            # budget. At defaults the floor is 600s × 5 turns = 3000s, which is
            # also the usual feature default — so the resolved number is
            # indistinguishable from "the override never applied". Say so, at
            # WARNING, and name the escape hatch.
            logger.warning(
                message
                + f" — NOT honoured verbatim: the min-turn floor "
                f"(GUARDKIT_MIN_TURN_BUDGET={MIN_TURN_BUDGET_SECONDS}s × "
                f"max_turns={self.max_turns} = {floor}s) RAISED it, so the "
                f"requested {override_int}s budget is not in force. Lower "
                f"GUARDKIT_MIN_TURN_BUDGET or --max-turns to express a "
                f"per-task budget below {floor}s."
            )
        else:
            logger.info(message)
        return resolved

    def _execute_task(self, task, feature, worktree, **kwargs):
        from guardkit.orchestrator.task_work_scope import checkout_lease, ScopeUnavailable
        admitted = kwargs.pop("admission_event", None)
        def cancelled():
            return any(
                event is not None and event.is_set() for event in
                (kwargs.get("cancellation_event"), kwargs.get("timeout_event"))
            )
        try:
            with checkout_lease(worktree.path, self._evidence_repos_resolved, cancelled=cancelled) as lease:
                if cancelled():
                    lease.poison("Task admission cancelled before Player; work preserved")
                    return TaskExecutionResult(task_id=task.id, success=False, total_turns=0,
                        final_decision="cancelled", error="Task admission cancelled before Player")
                if kwargs.get("repair_round") is True:
                    archived = self._archive_previous_round(task.id, worktree)
                    kwargs["repair_round"] = begin_repair_round(
                        worktree.path, (archived + 1) if archived else None,
                        kwargs.get("seed_feedback"),
                        approved_by_earlier_repairs=getattr(self, "_repair_approvals", {}).get(task.id, ()),
                    )
                lease.admit(task.id, feature.id, getattr(kwargs.get('repair_round'), 'round_number', 'repair') if kwargs.get('repair_round') else 'initial')
                # The full lease serializes this once-per-wave preparation.
                # Product files generated by installers stay in this scope.
                if getattr(self, "_bootstrap_pending", False):
                    # Cleared first: an install that fails is reported once
                    # for the wave, not again for every later task.
                    self._bootstrap_pending = False
                    self._bootstrap_environment(worktree, feature=feature)
                self._update_task_started(feature, task.id)
                kwargs['shares_working_copy'] = False
                if admitted:
                    admitted()
                result = self._execute_task_owned(task, feature, worktree, **kwargs)
                stopped = any(event is not None and event.is_set() for event in
                              (kwargs.get("timeout_event"), kwargs.get("cancellation_event")))
                if stopped and result.success:
                    result.success = False
                    result.final_decision = "timeout" if kwargs.get("timeout_event") and kwargs["timeout_event"].is_set() else "cancelled"
                    result.error = "Writer completed after cancellation; work preserved without approval"
                if not result.success or stopped:
                    lease.poison(f"Task {task.id} was not approved or was cancelled; preserved predecessor work")
                return result
        except ScopeUnavailable as exc:
            return TaskExecutionResult(task_id=task.id, success=False, total_turns=0,
                                       final_decision="error", error=str(exc))
        finally:
            if admitted:
                admitted()

    def _approved_head_for_offer(
        self,
        worktree,
        wave_results,
        *,
        tasks_completed: int,
        smoke_gate_failed: bool,
        feature_check_error: Optional[str],
    ) -> Optional[str]:
        """The last approved commit of a feature that did not finish, when
        Forge may offer it (step 1, 24 October 2026).

        Present only when at least one task completed and no real check is
        still failed: the smoke check, the whole-feature verdict, or a task
        whose last Coach verdict carried a test run that ran and failed. A
        missing measurement is not a failure. Nothing is rerun or read from
        disk: the head is the one kept in memory when the last task approval
        completed.
        """
        if tasks_completed < 1 or smoke_gate_failed or feature_check_error:
            return None
        latest: Dict[str, TaskExecutionResult] = {}
        for wave in wave_results:
            for result in wave.results:
                latest[result.task_id] = result
        if any(getattr(r, "real_check_failed", False) for r in latest.values()):
            return None
        from guardkit.orchestrator.task_work_scope import approved_head

        return approved_head(worktree.path)

    def _checked_writer(self, worktree, callback, *args, **kwargs):
        """Run a feature-level check as the checkout's one writer.

        Step 2 (26 October 2026): what the check leaves behind never refuses
        the next writer or fails the feature; it is put back where it can be,
        and logged.
        """
        from guardkit.orchestrator.task_work_scope import checkout_lease, boundary_snapshot
        with checkout_lease(worktree.path, self._evidence_repos_resolved) as lease:
            before = boundary_snapshot(lease)
            result = callback(*args, **kwargs)
            if boundary_snapshot(lease) != before:
                self._undo_check_side_effects(lease, before)
            return result

    @staticmethod
    def _undo_check_side_effects(lease, before) -> bool:
        """Put back what a feature check changed in files that were clean
        before it ran, and say so; True when the boundary is whole again.

        A check runs the project's own commands, and those leave things behind:
        FEAT-3BA8's coverage run combined a committed ``.coverage.<host>.pid…``
        file away and wrote ``.coverage`` (step 1 measurement, 26 October
        2026). The check never writes product work, so its changes are undone,
        not kept. Anything that cannot be put back exactly (a moved HEAD, a
        changed index, or a file that was already changed before the check) is
        left as it is and logged. Never raises.
        """
        from guardkit.orchestrator.task_work_scope import _dirty, _git, boundary_snapshot

        try:
            now = boundary_snapshot(lease)
            plan = []
            for (_, root, _), (head, index, payload), (head_now, index_now, payload_now) in zip(
                lease.repositories, before, now
            ):
                if head != head_now or index != index_now:
                    logger.warning(
                        "The feature check moved HEAD or changed the index in %s; "
                        "left as it is, the build goes on", root,
                    )
                    return False
                was = {path: rest for path, *rest in payload}
                is_now = {path: rest for path, *rest in payload_now}
                if any(is_now.get(path) != rest for path, rest in was.items()):
                    logger.warning(
                        "The feature check changed work that was already changed in %s; "
                        "left as it is, the build goes on", root,
                    )
                    return False
                for path in _dirty(root):
                    if path in was:
                        continue
                    tracked = bool(_git(root, "ls-tree", "--name-only", "HEAD", "--", path))
                    plan.append((root, path, tracked))
            for root, path, tracked in plan:
                if tracked:
                    _git(root, "checkout", "HEAD", "--", path)
                else:
                    (Path(root) / path).unlink(missing_ok=True)
            if boundary_snapshot(lease) != before:
                return False
        except Exception as exc:  # noqa: BLE001 — logged, the build goes on
            logger.warning("Could not put back what the feature check changed (%s)", exc)
            return False
        logger.warning(
            "The feature check changed %d file(s) that were clean before it ran (%s); "
            "they were put back and the build goes on",
            len(plan), ", ".join(path for _, path, _ in plan),
        )
        return True

    def _execute_task_owned(
        self,
        task: FeatureTask,
        feature: Feature,
        worktree: Worktree,
        cancellation_event: Optional[threading.Event] = None,
        timeout_event: Optional[threading.Event] = None,
        time_budget_seconds: Optional[float] = None,
        wave_size: int = 1,
        effective_task_timeout: Optional[int] = None,
        seed_feedback: Optional[str] = None,
        smoke_command: Optional[str] = None,
        smoke_expected_exit: int = 0,
        shares_working_copy: bool = False,
        feature_check_repair: Optional[FeatureCheckRepair] = None,
        repair_round: Optional[RepairRound] = None,
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
        cancellation_event : Optional[threading.Event], optional
            Cooperative cancellation signal (default: None).
            When set, AutoBuildOrchestrator exits cleanly at next checkpoint.
        timeout_event : Optional[threading.Event], optional
            Feature-level timeout signal (default: None).
            When set, AutoBuildOrchestrator exits with "timeout" decision (TASK-ABFIX-006).
        wave_size : int, optional
            Number of tasks executing in parallel in the current wave (default: 1).
            Passed to AutoBuildOrchestrator for Coach test isolation (TASK-ABFIX-005).
        effective_task_timeout : Optional[int], optional
            Per-task feature-level timeout resolved at queue site (TASK-ATR-001).
            When provided, this value (which may include a frontmatter override)
            is forwarded to AutoBuildOrchestrator so the SDK-timeout logging
            line reflects the actual envelope wrapping the task. When None,
            falls back to ``self.task_timeout``.

        Returns
        -------
        TaskExecutionResult
            Execution result
        """
        # TASK-FIX-OBS2: Create per-task progress logger for diagnostics
        from guardkit.orchestrator.progress_logger import TaskProgressLogger
        progress_logger = TaskProgressLogger(
            task_id=task.id,
            repo_root=self.repo_root,
            interval=self.task_log_interval,
        )
        task_start_time = time.time()
        # Set once the task runner exists, so an exception ending still
        # carries what it measured (step 1, 24 October 2026).
        task_orchestrator: Optional[AutoBuildOrchestrator] = None

        try:
            # Load task data from markdown file
            task_data = TaskLoader.load_task(task.id, repo_root=self.repo_root)

            # Resolve SDK timeout: CLI > task frontmatter > configured base.
            # The environment-backed default is a scalable base; an explicit
            # CLI/task value remains a fixed override.
            effective_sdk_timeout = self.sdk_timeout
            sdk_timeout_is_override = self.sdk_timeout is not None
            if effective_sdk_timeout is None:
                # Try task frontmatter autobuild.sdk_timeout
                # Note: TaskLoader returns frontmatter as nested dict, not at top level
                task_frontmatter = task_data.get("frontmatter", {})
                task_autobuild = task_frontmatter.get("autobuild", {})
                sdk_timeout_is_override = "sdk_timeout" in task_autobuild
                effective_sdk_timeout = task_autobuild.get(
                    "sdk_timeout", DEFAULT_SDK_TIMEOUT
                )

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
                sdk_timeout_is_override=sdk_timeout_is_override,
                # Pinned at build start; a task that starts anywhere else is
                # refused at its checkpoint (build 0D7C).
                expected_branch=self._pinned_feature_branch(worktree),
                expected_branch_pinned=True,
                enable_pre_loop=effective_enable_pre_loop,
                enable_context=self.enable_context,
                feature_id=feature.id,
                cancellation_event=cancellation_event,  # Cooperative cancellation (TASK-ASF-007)
                timeout_event=timeout_event,  # Feature-level timeout signal (TASK-ABFIX-006)
                task_timeout=(  # TASK-ATR-001: prefer queue-site resolved value (frontmatter override aware)
                    effective_task_timeout
                    if effective_task_timeout is not None
                    else self.task_timeout
                ),
                timeout_multiplier=self.timeout_multiplier,  # TASK-FIX-VL05
                wave_size=wave_size,  # Parallel wave context (TASK-ABFIX-005)
                # FEAT-2C42: True only when other tasks of the wave change
                # the working copy at the same time as this one.
                shares_working_copy=shares_working_copy,
                emitter=self._emitter,  # Forward emitter to task orchestrator (TASK-INST-013)
                progress_logger=progress_logger,  # TASK-FIX-OBS2: Per-task progress logging
                venv_python=self._bootstrap_venv_python,  # TASK-FIX-7A05
                # TASK-FIX-LGFM: thread --model down to LangGraph harness via
                # AgentInvoker. Without this, model=None reaches LangGraphHarness
                # and DeepAgents falls back to Anthropic (auth error under llama-swap).
                model=self.model,
                # TASK-FIX-COACHBUDG01: per-role Coach model override
                coach_model=self.coach_model,
                # TASK-AB-XREPOEV01: declared sibling evidence repos
                evidence_repos=self._evidence_repos_resolved,
                # TASK-AB-COACHRUNPARITY01 (arm a): turn-1 smoke-feedback seed.
                # Non-None only on a smoke-gate re-run of this wave.
                seed_feedback=seed_feedback,
                # TASK-AB-COACHRUNPARITY01 (arm b): the deliverable's real
                # runtime entry point, threaded in as a plain command string
                # (NOT the feature smoke-gate config — this per-task layer must
                # stay ignorant of the between-wave gate machinery; see
                # test_autobuild_smoke_placement). The per-task Coach runs it
                # only on a single-task wave; the wave_size guard lives in
                # CoachValidator.gather_evidence.
                smoke_command=smoke_command,
                smoke_expected_exit=smoke_expected_exit,
                # Whole-feature repair round (18 October 2026): the project's
                # check for the per-task Coach, beside smoke_command; the
                # single-task-wave guard lives in CoachValidator.
                feature_check_repair=feature_check_repair,
                # Gate-driven repair round (20 October 2026), in memory only.
                repair_round=repair_round,
            )

            # Execute task orchestration
            result = task_orchestrator.orchestrate(
                task_id=task.id,
                requirements=task_data["requirements"],
                acceptance_criteria=task_data["acceptance_criteria"],
                task_file_path=task_data.get("file_path"),
                requires_infrastructure=task.requires_infrastructure,
                time_budget_seconds=time_budget_seconds,
                # TS-lane D.1a: the feature-level declared behavioural oracle.
                # A task's own frontmatter declaration overrides this inside
                # orchestrate() (design §B.1 — the per-task escape hatch wins).
                behavioural_oracle=feature.behavioural_oracle,
            )

            # A repair round the reviewer approved: its files are carried, in
            # memory, to this task's next repair round.
            self._remember_repair_approvals(task.id, task_orchestrator)

            # TASK-FIX-OBS2: Log completion
            elapsed = time.time() - task_start_time
            progress_logger.log_complete(elapsed, result.final_decision)

            status_icon = "[green]✓[/green]" if result.success else "[red]✗[/red]"
            console.print(
                f"    {status_icon} {task.id}: {result.final_decision} "
                f"({result.total_turns} turns)"
            )

            # TASK-VPR-003: Compute SDK ceiling metrics from turn history
            sdk_ceiling_hits = sum(
                1 for tr in result.turn_history
                if tr.sdk_ceiling_hit
            )
            sdk_total_invocations = len([
                tr for tr in result.turn_history
                if tr.player_result and tr.player_result.success
            ])
            sdk_turns_list = [
                tr.sdk_turns_used for tr in result.turn_history
                if tr.sdk_turns_used is not None
            ]

            return TaskExecutionResult(
                task_id=task.id,
                success=result.success,
                total_turns=result.total_turns,
                final_decision=result.final_decision,
                error=result.error,
                recovery_count=result.recovery_count,
                sdk_ceiling_hits=sdk_ceiling_hits,
                sdk_total_invocations=sdk_total_invocations,
                sdk_turns_per_invocation=sdk_turns_list,
                real_check_failed=(
                    not result.success and task_orchestrator.real_check_failed
                ),
            )

        except (Exception, asyncio.CancelledError) as e:
            decision = "cancelled" if isinstance(e, asyncio.CancelledError) else "error"
            if isinstance(e, asyncio.CancelledError):
                logger.warning(f"CancelledError caught at _execute_task for {task.id}: {e}")
            # TASK-FIX-OBS2: Log error/cancellation with last known state
            elapsed = time.time() - task_start_time
            progress_logger.log_timeout(elapsed, f"decision={decision}, error={e}")
            console.print(f"    [red]✗[/red] {task.id}: {decision.upper()} - {e}")
            return TaskExecutionResult(
                task_id=task.id,
                success=False,
                total_turns=0,
                final_decision=decision,
                error=str(e),
                real_check_failed=bool(
                    task_orchestrator is not None
                    and task_orchestrator.real_check_failed
                ),
            )
        finally:
            progress_logger.close()

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

    def _create_error_result(self, task_id: str, error: BaseException) -> TaskExecutionResult:
        """
        Create TaskExecutionResult from exception.

        Parameters
        ----------
        task_id : str
            Task identifier
        error : BaseException
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
            error_type=type(error.__cause__ or error).__name__,
        )

    # ------------------------------------------------------------------
    # Late-approval reconciliation helpers (TASK-ATR-003)
    # ------------------------------------------------------------------

    def _remember_repair_approvals(self, task_id: str, task_orchestrator: Any) -> None:
        """Keep the files a repair round's approving turn showed the reviewer.

        Read from the task's own orchestrator, in memory
        (``AutoBuildOrchestrator.repair_round_approved_files``); ``None`` when
        the task was not in a repair round or the round was not approved.
        Only this task's files, and never a protected one. Never raises.
        """
        try:
            approved = getattr(task_orchestrator, "repair_round_approved_files", None)
            if approved:
                self.__dict__.setdefault("_repair_approvals", {}).setdefault(
                    task_id, set()
                ).update(str(path) for path in approved)
        except Exception as exc:  # noqa: BLE001 — a record never fails a build
            logger.warning(
                "[%s] The repair round's approved files could not be kept: %s",
                task_id, type(exc).__name__,
            )

    def _archive_previous_round(self, task_id: str, worktree: Worktree) -> Optional[int]:
        """Move a re-opened task's turn files into ``round-<N>/`` (18 Oct 2026).

        Covers the task's public and private folders: the ones
        ``_autobuild_candidate_dirs`` lists, plus this worktree's own public
        folder and ``task_private_dir``. See ``turn_rounds``. Returns the
        round number used, or ``None`` when nothing was moved. Never raises.
        """
        try:
            from guardkit.orchestrator.paths import TaskArtifactPaths
            from guardkit.orchestrator.turn_rounds import archive_turn_files

            folders = list(self._autobuild_candidate_dirs(task_id))
            worktree_path = Path(worktree.path)
            folders.append(TaskArtifactPaths.autobuild_dir(task_id, worktree_path))
            folders.append(TaskArtifactPaths.task_private_dir(task_id, worktree_path))
            return archive_turn_files(task_id, folders)
        except Exception as exc:  # noqa: BLE001 — a record never fails a build
            logger.warning(
                "[%s] The earlier round's turn files could not be kept: %s",
                task_id, exc,
            )
            return None

    def _autobuild_candidate_dirs(self, task_id: str) -> list[Path]:
        """
        Return every ``.guardkit/autobuild/<task_id>`` dir Coach may have
        written to.

        For direct-mode runs Coach writes under
        ``self.repo_root/.guardkit/autobuild/<task_id>/``. For
        worktree-backed runs (every ``FEAT-*`` autobuild) it writes under
        ``self.repo_root/.guardkit/worktrees/<feature_id>/.guardkit/autobuild/<task_id>/``.

        TASK-SBHO-002: Coach verdict (coach_turn_N.json) now also lives in the
        orchestrator-private directory (``.guardkit/autobuild-private/<task_id>/``)
        which is added to the candidate list so late-approval checks still find it.

        TASK-FIX-LATEAPPR: late-approval reconciliation and the
        APPROVED_LATE audit-path glob both need to see both shapes, so
        the candidate-dirs walk is centralised here. The list is
        additive — direct-mode runs continue to see exactly the
        repo-root path.
        """
        candidates: list[Path] = [
            self.repo_root / ".guardkit" / "autobuild" / task_id,
        ]
        worktrees_root = self.repo_root / ".guardkit" / "worktrees"
        if worktrees_root.exists():
            try:
                for wt_dir in worktrees_root.iterdir():
                    if not wt_dir.is_dir():
                        continue
                    candidates.append(
                        wt_dir / ".guardkit" / "autobuild" / task_id
                    )
            except OSError as exc:
                logger.debug(
                    f"[{task_id}] worktrees iter skipped: {exc}"
                )
        # TASK-SBHO-002: also check private dirs (coach verdict location).
        candidates.extend(
            p / ".guardkit" / "autobuild-private" / task_id
            for p in [self.repo_root]
            + (list(worktrees_root.iterdir()) if worktrees_root.exists() else [])
            if p.is_dir()
        )
        return candidates

    def _latest_coach_turn_path(self, task_id: str) -> Optional[Path]:
        """
        Return the most-recent ``coach_turn_*.json`` for ``task_id`` across
        every direct/worktree autobuild dir, or ``None`` if none exist.

        Used by both ``_check_late_approval`` (read decision + mtime delta)
        and the APPROVED_LATE audit-log block (record source path +
        mtime delta). Never raises.
        """
        coach_files: list[Path] = []
        for d in self._autobuild_candidate_dirs(task_id):
            if not d.exists():
                continue
            try:
                coach_files.extend(d.glob("coach_turn_*.json"))
            except OSError as exc:
                logger.debug(
                    f"[{task_id}] coach_turn glob skipped in {d}: {exc}"
                )
        if not coach_files:
            return None
        try:
            return max(coach_files, key=lambda p: p.stat().st_mtime)
        except OSError as exc:
            logger.debug(
                f"[{task_id}] coach_turn stat skipped: {exc}"
            )
            return None

    def _check_late_approval(
        self, task_id: str, timer_fire_time: float
    ) -> Optional[str]:
        """
        Read-only peek at the latest ``coach_turn_*.json`` for a task.

        Returns the Coach ``decision`` string if the file's mtime is within
        ``LATE_APPROVAL_GRACE_S`` seconds of ``timer_fire_time`` — i.e. the
        Coach decision was written close enough to the feature timer fire
        that we should treat it as the authoritative outcome for the task,
        even though the per-wave ``asyncio.gather`` already collected a
        ``TimeoutError``. Returns ``None`` for any error or absence; never
        raises.

        TASK-FIX-LATEAPPR: the search now walks every direct-mode and
        worktree-backed ``.guardkit/autobuild/<task_id>/`` dir via
        ``_autobuild_candidate_dirs`` / ``_latest_coach_turn_path`` so
        worktree-backed ``FEAT-*`` runs reclassify correctly.

        Parameters
        ----------
        task_id : str
            Task identifier whose autobuild dir to inspect.
        timer_fire_time : float
            Wall time (``time.time()``) the feature timer fired. The mtime
            delta is the absolute difference, so a Coach write that landed
            slightly *after* the timer fire is included.

        Returns
        -------
        Optional[str]
            ``"approve"`` / ``"feedback"`` / ``"reject"`` if a recent
            ``coach_turn_*.json`` was found within the grace window;
            ``None`` otherwise.
        """
        try:
            latest = self._latest_coach_turn_path(task_id)
            if latest is None:
                return None
            mtime_delta = abs(latest.stat().st_mtime - timer_fire_time)
            if mtime_delta > LATE_APPROVAL_GRACE_S:
                return None
            return json.loads(latest.read_text()).get("decision")
        except Exception as exc:
            # TASK-FIX-CTOUT01: Promote from DEBUG to WARNING with
            # exc_info. Silent swallowing here is how Layer 4 (late-
            # approval reconciliation) failed invisibly in run-3 of
            # TASK-HMIG-010 — the GD02 wave summary divergence
            # (outer=timeout, inner=approved) reached human review
            # before any operator noticed the bookkeeping miss because
            # the DEBUG line never surfaced under INFO-level logging.
            # See .claude/rules/harness-cancellation-contract.md.
            logger.warning(
                f"[{task_id}] _check_late_approval failed: {exc}",
                exc_info=exc,
            )
            return None

    def _read_total_turns(self, task_id: str) -> Optional[int]:
        """
        Recover ``turn_number`` from the latest ``turn_state_turn_*.json``.

        Used by the late-approval reclassification path so the synthesised
        ``TaskExecutionResult`` carries an accurate ``total_turns`` even
        though the gather slot held a ``TimeoutError`` and the worker
        thread's return value was discarded. Returns ``None`` on any
        error; never raises.
        """
        try:
            autobuild_dir = (
                self.repo_root / ".guardkit" / "autobuild" / task_id
            )
            if not autobuild_dir.exists():
                return None
            state_files = sorted(
                autobuild_dir.glob("turn_state_turn_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not state_files:
                return None
            data = json.loads(state_files[0].read_text())
            value = data.get("turn_number")
            return int(value) if value is not None else None
        except Exception as exc:
            logger.debug(
                f"[{task_id}] _read_total_turns skipped: {exc}"
            )
            return None

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

        # Task identities have one latest disposition, including gate repairs.
        tasks_completed = sum(t.status == "completed" for t in feature.tasks)
        tasks_deferred = sum(t.status == "deferred" for t in feature.tasks)
        tasks_failed = sum(t.status == "failed" for t in feature.tasks)
        total_turns = sum(
            r.total_turns
            for wave in wave_results
            for r in wave.results
        )

        # Detect smoke gate failure (TASK-SMK-F703A). A failed smoke gate
        # halts execution with all tasks-run-so-far passing, so the default
        # "paused" branch would mis-classify the outcome.
        smoke_gate_failed = any(
            wr.smoke_gate_result is not None and not wr.smoke_gate_result.passed
            for wr in wave_results
        )

        # Determine final status
        final_status: Literal["completed", "failed", "paused"]
        if tasks_failed == 0 and tasks_completed + tasks_deferred == len(feature.tasks) and not smoke_gate_failed:
            final_status = "completed"
            success = True
        elif tasks_failed > 0 or smoke_gate_failed:
            final_status = "failed"
            success = False
        else:
            final_status = "paused"  # Partial completion (resume mode)
            success = False

        # What the per-task code checks did, in one summary beside the
        # whole-feature record (21 September 2026). Never raises, and a build
        # is never failed by it.
        self._write_code_checks_summary(feature, worktree)
        # What each task's final review left (the build reviewer design of 29
        # October 2026), at most ten, beside it for the merge card. Never
        # raises, and a build is never failed by it.
        from guardkit.orchestrator.build_review import write_feature_notes

        write_feature_notes(
            getattr(feature, "id", ""),
            [str(getattr(task, "id", "") or "") for task in getattr(feature, "tasks", None) or []
             if getattr(task, "id", None)],
            Path(worktree.path),
        )

        # When the whole-feature check failed during the wave phase, the
        # feature is already failed by its gate result — say WHY in the
        # result's own words rather than letting it read as a smoke gate.
        feature_check_error: Optional[str] = None
        for wave in wave_results:
            gate = wave.smoke_gate_result
            if (
                gate is not None
                and not gate.passed
                and str(gate.command).startswith("whole-feature check (")
            ):
                feature_check_error = gate.stderr or "the whole-feature check failed"
                break

        # Update feature
        feature.status = final_status
        feature.execution.completed_at = datetime.now().isoformat()
        feature.execution.total_turns = total_turns
        feature.execution.tasks_completed = tasks_completed
        feature.execution.tasks_deferred = tasks_deferred
        feature.execution.tasks_failed = tasks_failed
        FeatureLoader.save_feature(feature, self.repo_root)

        # Preserve worktree for human review
        self._worktree_manager.preserve_on_failure(worktree)

        # A failed task that stopped with one plain sentence (an environment
        # gap: a tool the project declares is missing from the build
        # environment, 23 October 2026) gives the feature its reason, when no
        # feature-level reason above already did. The same one stdout line as
        # the whole-feature check's early stop carries it to Forge.
        approved_head = (
            None
            if success
            else self._approved_head_for_offer(
                worktree,
                wave_results,
                tasks_completed=tasks_completed,
                smoke_gate_failed=smoke_gate_failed,
                feature_check_error=feature_check_error,
            )
        )
        # Display summary
        self._display_summary(feature, wave_results, worktree, final_status)

        orchestration_result = FeatureOrchestrationResult(
            feature_id=feature.id,
            success=success,
            status=final_status,
            total_tasks=len(feature.tasks),
            tasks_completed=tasks_completed,
            tasks_deferred=tasks_deferred,
            tasks_failed=tasks_failed,
            wave_results=wave_results,
            worktree=worktree,
            error=(
                None
                if success
                else (
                    feature_check_error
                    if feature_check_error is not None
                    else (
                        "smoke gate failed between waves"
                        if smoke_gate_failed and tasks_failed == 0
                        else f"{tasks_failed} task(s) failed"
                    )
                )
            ),
        )

        # Step 1 (24 October 2026): the approved part of a feature that did
        # not finish goes to Forge on stdout, which survives a failed record
        # write.
        if approved_head:
            try:
                print(
                    stopped_because_line(
                        feature.id,
                        orchestration_result.error or "the feature did not finish",
                        approved_head,
                    ),
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001 — a line never fails a build
                logger.warning(
                    "The approved part's stdout line could not be written: %s",
                    type(exc).__name__,
                )

        # TASK-ABE-003: Generate structured review summary
        try:
            from guardkit.orchestrator.review_summary import ReviewSummaryGenerator

            summary_dir = self.repo_root / ".guardkit" / "autobuild" / feature.id
            generator = ReviewSummaryGenerator(output_dir=summary_dir)
            summary_result = generator.generate(orchestration_result)
            if summary_result.success:
                console.print(
                    f"[green]✓[/green] Review summary: {summary_result.output_path}"
                )
        except Exception as exc:
            logger.warning("Review summary generation failed: %s", exc)

        return orchestration_result

    # ========================================================================
    # TASK-FPTC-003: operator_handoff skip branch
    # ========================================================================

    DEFERRED_OPERATOR_HANDOFF_REASON = (
        "operator follow-up — runtime verification required"
    )

    def _read_task_type_from_frontmatter(
        self, task_id: str
    ) -> Optional[str]:
        """
        Resolve the canonical ``task_type`` for a task from its on-disk
        frontmatter.

        Returns the canonical TaskType value string (e.g. ``"operator_handoff"``)
        when the file declares one, ``None`` when the task file cannot be
        loaded or has no ``task_type`` key. Aliases are resolved via
        ``normalise_task_type``; unknown values fall back to ``"feature"``
        with a warning, matching the loader's behaviour. Loader errors are
        caught and logged so the orchestrator falls through to normal
        dispatch rather than crashing on a missing/corrupt task file.
        """
        try:
            task_data = TaskLoader.load_task(task_id, repo_root=self.repo_root)
        except Exception as exc:
            logger.warning(
                "[%s] operator_handoff probe: TaskLoader.load_task failed (%s); "
                "treating as non-handoff",
                task_id,
                exc,
            )
            return None

        frontmatter = task_data.get("frontmatter") or {}
        raw = frontmatter.get("task_type")
        if raw is None:
            return None
        return normalise_task_type(str(raw))

    def _maybe_defer_operator_handoff(
        self,
        task: FeatureTask,
        feature: Feature,
        wave_number: int,
    ) -> Optional[TaskExecutionResult]:
        """
        Short-circuit dispatch for ``task_type: operator_handoff`` tasks.

        AC-FPTC-003-01: This branch fires before any worktree setup,
        before any timeout resolution, before any AutoBuildOrchestrator
        construction, before any SDK budget burn. The task is reported
        as deferred (terminal-but-not-failed), the wave continues, and
        the deferred entry is surfaced on stdout with task ID, title,
        and reason string so the operator knows what to follow up on.

        Returns a ``TaskExecutionResult`` with ``final_decision="deferred"``
        when the task should be skipped, or ``None`` when normal dispatch
        should proceed.
        """
        canonical_type = self._read_task_type_from_frontmatter(task.id)
        if canonical_type != TaskType.OPERATOR_HANDOFF.value:
            return None

        reason = self.DEFERRED_OPERATOR_HANDOFF_REASON
        title = task.name or task.id

        # AC-FPTC-003-03: surface a deferred entry with task ID, title,
        # and reason on the wave-summary stdout banner (the surface the
        # orchestrator already uses). The wave display also gets a
        # reasoned skip update so its task panel reflects the outcome.
        if self._wave_display:
            self._wave_display.update_task_status(
                task.id,
                "skipped",
                f"DEFERRED — {reason}",
            )
        else:
            console.print(
                f"  [yellow]⏸ Deferred {task.id}[/yellow]: "
                f"{title} — {reason}"
            )

        deferred_result = TaskExecutionResult(
            task_id=task.id,
            success=True,  # terminal-but-not-failed — feature run does not fail
            total_turns=0,
            final_decision="deferred",
            error=None,
            deferred_reason=reason,
        )

        # Persist the deferred outcome via the standard update path so
        # downstream consumers (e.g. /feature-complete TASK-FPTC-005)
        # see ``task.status == "deferred"`` and the deferred_reason in
        # ``task.result``.
        self._update_feature(feature, task.id, deferred_result, wave_number)

        logger.info(
            "[%s] operator_handoff skip: deferred (no Player/Coach invocation, "
            "no SDK budget burn). reason=%r",
            task.id,
            reason,
        )

        return deferred_result

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
            # TASK-FPTC-003: deferred is terminal-but-not-failed. Preserve
            # the explicit "deferred" status in the saved feature state so
            # /feature-complete (TASK-FPTC-005) can find it without
            # round-tripping through the success flag.
            if result.final_decision == "deferred":
                task.status = "deferred"
            else:
                task.status = "completed" if result.success else "failed"
            task.turns_completed = result.total_turns
            task.current_turn = 0  # Reset current turn on completion
            task.completed_at = datetime.now().isoformat()
            task.result = {
                "total_turns": result.total_turns,
                "final_decision": result.final_decision,
                "error": result.error,
                "deferred_reason": result.deferred_reason,
                "real_check_failed": result.real_check_failed,
            }

        # Update execution counters
        feature.execution.tasks_deferred = sum(t.status == "deferred" for t in feature.tasks)
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

    def _unmark_wave_completed(
        self,
        feature: Feature,
        wave_number: int,
    ) -> None:
        """Take back a wave's "completed" record, and save that.

        Used when a gate that runs AFTER the wave was recorded complete then
        fails the build. Leaving the record in place would let a later resume
        skip the wave — and so skip the gate that failed.

        Parameters
        ----------
        feature : Feature
            Feature to update
        wave_number : int
            Wave number to un-record (1-indexed)
        """
        if wave_number not in feature.execution.completed_waves:
            return
        feature.execution.completed_waves.remove(wave_number)
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
                tasks_deferred=feature.execution.tasks_deferred,
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
                    f"Tasks: {feature.execution.tasks_completed} approved, {feature.execution.tasks_deferred} deferred; deferred work not executed\n"
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
                    else "red" if task.status in ("failed", "timeout")
                    else "yellow" if task.status == "skipped"
                    else "dim"
                )
                status_text = f"[{status_style}]{task.status.upper()}[/{status_style}]"
                turns = task.result.get("total_turns", "-") if task.result else "-"
                decision = task.result.get("final_decision", "-") if task.result else "-"

                table.add_row(task.id, status_text, str(turns), decision)

            console.print(table)

        # Smoke gate summary (TASK-SMK-F703A). Only rendered when at least
        # one wave fired a smoke gate, so features without smoke_gates stay
        # visually identical to today.
        fired = [wr for wr in wave_results if wr.smoke_gate_result is not None]
        if fired:
            console.print("\n[bold]Smoke Gates:[/bold]")
            for wr in fired:
                sgr = wr.smoke_gate_result
                if sgr.passed:
                    console.print(
                        f"  [green]✓[/green] After wave {wr.wave_number}: "
                        f"[dim]{sgr.command}[/dim] (exit={sgr.exit_code})"
                    )
                elif sgr.timed_out:
                    console.print(
                        f"  [red]✗[/red] After wave {wr.wave_number} "
                        f"[red](timed out after {sgr.timeout}s)[/red]: "
                        f"[dim]{sgr.command}[/dim]"
                    )
                else:
                    console.print(
                        f"  [red]✗[/red] After wave {wr.wave_number} "
                        f"[red](exit={sgr.exit_code})[/red]: "
                        f"[dim]{sgr.command}[/dim]"
                    )

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
        feature.execution.tasks_deferred = sum(t.status == "deferred" for t in feature.tasks)
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
]
