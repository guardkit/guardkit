"""
AutoBuild Orchestrator for adversarial Player↔Coach workflow.

This module implements the central orchestration component for GuardKit's AutoBuild
system, coordinating isolated worktree creation, Player/Coach agent interactions,
and result integration through a three-phase execution pattern.

Architecture:
    Three-Phase Execution (from Block AI Research):
    1. Setup Phase: Create isolated worktree, initialize progress display
    2. Loop Phase: Execute adversarial Player↔Coach turns (max 5)
    3. Finalize Phase: Preserve worktree for manual review (auto_merge removed per review)

    Component Integration:
    - WorktreeManager: Isolated workspace management
    - AgentInvoker: SDK invocation for Player/Coach agents
    - ProgressDisplay: Real-time turn-by-turn visualization

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
    >>>
    >>> orchestrator = AutoBuildOrchestrator(
    ...     repo_root=Path.cwd(),
    ...     max_turns=5,
    ... )
    >>>
    >>> result = orchestrator.orchestrate(
    ...     task_id="TASK-XXX-YYYY",
    ...     requirements="Implement OAuth2 authentication",
    ...     acceptance_criteria=[
    ...         "Support authorization code flow",
    ...         "Handle token refresh",
    ...         "Include comprehensive tests",
    ...     ],
    ... )
    >>>
    >>> print(f"Status: {result.final_decision}")
    >>> print(f"Turns: {result.total_turns}")
    >>> print(f"Worktree: {result.worktree.path}")
"""

import asyncio
import concurrent.futures
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    FrozenSet,
    List,
    Literal,
    Optional,
    Tuple,
)

import yaml

# Import worktree components from guardkit package
from guardkit.worktrees import (
    WorktreeManager,
    Worktree,
    WorktreeCreationError,
    WorktreeMergeError,
)

# Import local orchestrator components
from guardkit.lib.secret_scrub import scrub_for_publication
from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
    DEFAULT_SDK_TIMEOUT,
)
from guardkit.orchestrator import evidence_repos as evidence_repos_lib
from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.failing_test_feedback import (
    MUST_FIX_MARKER,
    SUGGESTION_MARKER,
)
from guardkit.orchestrator.progress import ProgressDisplay
from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    AgentLaunchRefusedError,
    BlockedReport,
    CoachDecisionInvalidError,
    PlanNotFoundError,
    RateLimitExceededError,
    SDKTimeoutError,
    StateValidationError,
)
from guardkit.orchestrator.schemas import (
    CompletionPromise,
    CriterionVerification,
    CriterionStatus,
    VerificationResult,
    calculate_completion_percentage,
    format_promise_summary,
    format_verification_summary,
)

# Import task loading utilities
from guardkit.tasks.task_loader import TaskLoader, TaskNotFoundError

# Import quality gates for pre-loop execution
from guardkit.orchestrator.quality_gates import (
    PreLoopQualityGates,
    QualityGateBlocked,
    CheckpointRejectedError,
    CoachValidator,
)
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

# TASK-AB-COACHSUBPROC01: env > config > default (subprocess) resolution for
# the Coach's independent test-execution mode.
from guardkit.orchestrator.quality_gates.coach_validator import resolve_coach_test_execution

# Import task type models for quality gate profile resolution
from guardkit.models.task_types import TaskType, TASK_TYPE_ALIASES, get_profile as get_quality_gate_profile

# Import state detection for partial work recovery
from guardkit.orchestrator.state_detection import (
    detect_git_changes,
    detect_test_results,
    GitChangesSummary,
)
from guardkit.orchestrator.state_tracker import (
    MultiLayeredStateTracker,
    WorkState,
)
from guardkit.orchestrator.synthetic_report import (
    PLAYER_TIMED_OUT_CATEGORY,
    SHARED_WORKING_COPY_FIELD,
    TASK_WORK_TIMEOUT_CATEGORY,
    mark_shared_working_copy,
    player_no_report_no_changes_issue,
    player_timed_out_issue,
    task_work_no_changes_issue,
    task_work_timeout_issue,
    player_timeout_from_error,
    player_timeout_from_report,
)

# Import worktree checkpoint management for context pollution mitigation
from guardkit.orchestrator.worktree_checkpoints import (
    WorktreeCheckpointManager,
    Checkpoint,
    CheckpointRefused,
)

# Import turn state operations for cross-turn learning (TASK-GE-002)
from guardkit.knowledge.turn_state_operations import (
    capture_turn_state,
    create_turn_state_from_autobuild,
)
from guardkit.knowledge.entities.turn_state import TurnMode
# FEAT-MEM-09 WS-2c: fleet-memory per-thread factory (graphiti factory retired).
from guardkit.knowledge.fleet_memory_client import (
    configure_memory_project,
    get_memory_client,
    get_memory_factory,
)

# Flywheel write seam: every autobuild terminal (approved AND failed) records a
# build outcome so a future gate can read it back as a prior.
from guardkit.knowledge.outcome_manager import (
    capture_task_outcome_verified,
    OutcomeCapture,
)
from guardkit.knowledge.entities.outcome import OutcomeType

# Import AutoBuild context loader for job-specific context (TASK-GR6-006)
from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
from guardkit.orchestrator.outcome_lessons import (
    compose_outcome_lessons,
    turn_facts_from_record,
)

# Import MCP design extractor for Phase 0 (TASK-DM-003)
from guardkit.orchestrator.mcp_design_extractor import (
    DesignData,
    DesignExtractor,
    DesignExtractionError,
    MCPUnavailableError,
)

# Import instrumentation (TASK-INST-004)
from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.schemas import (
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    FailureCategory,
)

# Setup logging
logger = logging.getLogger(__name__)


# ============================================================================
# Timeout Budget Constants (TASK-ABFIX-004)
# ============================================================================

# Minimum wall-clock budget (seconds) required before starting a new turn.
# If the remaining task budget falls below this, _loop_phase exits gracefully
# with "timeout_budget_exhausted" instead of waiting for asyncio.TimeoutError.
# Override via GUARDKIT_MIN_TURN_BUDGET (TASK-ABSR-MTBC); default unchanged.
MIN_TURN_BUDGET_SECONDS: int = int(os.environ.get("GUARDKIT_MIN_TURN_BUDGET", "600"))

# Budget (seconds) granted to Coach when Player succeeds near the timeout
# boundary (i.e., when the cancellation event is set but Player returned
# success=True).  Ensures Coach always gets a fair window to validate.
#
# TASK-FIX-SPECCOCH01 (Shape B): operator-tunable via
# ``GUARDKIT_COACH_GRACE_PERIOD_SECONDS``. Default raised from 120 to
# 1500 to cover empirically-observed Coach turn-1 latencies under the
# LangGraph harness on the gemma4:26b coach (run-9 of FEAT-AOF measured
# 944s under ``--reasoning off``; the new default leaves ~50 % headroom
# for the richer ``--reasoning auto`` reasoning channel). Shape B is the
# belt-and-braces backstop for the architectural decoupling in Shape A
# (``specialist_invocations._run_specialist_with_watchdog``); if any
# code path still routes through the grace-period branch, it now has a
# realistic budget rather than the original 120 s ceiling that
# guaranteed Coach silence.
COACH_GRACE_PERIOD_SECONDS: int = int(
    os.environ.get("GUARDKIT_COACH_GRACE_PERIOD_SECONDS", "1500")
)




# ============================================================================
# AutoBuild Essential Rules (TASK-daab)
# ============================================================================

# Rules files to keep in worktree `.claude/rules/`.
# Everything else is pruned after worktree creation to reduce context size.
# ~17 KB retained vs ~63 KB total — frees ~11.5K tokens per turn.
AUTOBUILD_ESSENTIAL_RULES: frozenset = frozenset({
    "autobuild.md",
    "anti-stub.md",
    "hash-based-ids.md",
    "testing.md",
})

# Additional rules to keep when running in feature-build mode.
FEATURE_BUILD_EXTRA_RULES: frozenset = frozenset({
    "feature-build-invariants.md",
})


# ============================================================================
# Error Classification
# ============================================================================

# Unrecoverable errors that should fail immediately without retrying.
# These indicate fundamental issues that cannot be resolved by the Player.
UNRECOVERABLE_ERRORS = (
    PlanNotFoundError,
    StateValidationError,
    RateLimitExceededError,  # NEW: Stop immediately on rate limit
    # The harness refused to start the agent (its run profile failed the
    # launch check). No turn can succeed until that is resolved, so state
    # recovery, Coach review and implementation feedback would only repeat it.
    AgentLaunchRefusedError,
)


# ============================================================================
# Failure Category Mapping (TASK-INST-004)
# ============================================================================

FAILURE_CATEGORY_MAP: Dict[str, str] = {
    "max_turns_exceeded": "other",
    "error": "other",
    "timeout": "timeout",
    "timeout_budget_exhausted": "timeout",
    "rate_limited": "rate_limit",
    "cancelled": "other",
    "pre_loop_blocked": "other",
    "design_extraction_failed": "other",
}
"""Map final_decision strings to FailureCategory controlled vocabulary values."""


# ============================================================================
# Did this turn change anything? (TASK-AB-NOCHANGE01)
# ============================================================================


_TEST_RUN_ARTEFACT_PATTERNS: Tuple[re.Pattern, ...] = (
    # Files a test run drops on the way past. The generator runs tests inside
    # its own turn, so these land between the two photographs the change probe
    # takes — and a repository that does not gitignore them would make every
    # silent turn look busy, which would quietly stop the no-file-changes stall
    # from ever firing. None of them is ever work product.
    #
    # Deliberately narrow, and local to this probe: it does NOT touch the
    # shared orchestrator-managed path list the honesty check uses.
    re.compile(r"(?:.*/)?__pycache__/"),
    re.compile(r"(?:.*/)?\.pytest_cache/"),
    re.compile(r"(?:.*/)?\.mypy_cache/"),
    re.compile(r"(?:.*/)?\.ruff_cache/"),
    re.compile(r"(?:.*/)?\.hypothesis/"),
    re.compile(r"(?:.*/)?htmlcov/"),
    re.compile(r"(?:.*/)?\.coverage(?:\.[^/]*)?$"),
    re.compile(r"(?:.*/)?coverage\.(?:json|xml)$"),
    re.compile(r"(?:.*/)?[^/]*\.py[co]$"),
)
"""Paths a test run leaves behind. Never work product; never counted."""


def _is_test_run_artefact(rel_path: str) -> bool:
    """True when ``rel_path`` is something a test run dropped, not work."""
    return any(p.match(rel_path) for p in _TEST_RUN_ARTEFACT_PATTERNS)


_UNTRACKED_STAT_CAP = 5000
"""Most untracked paths the change probe will stat before giving up on the
finer signature and comparing path lists alone."""

WORKTREE_CHANGE_PROBE_TIMEOUT_S = 30
"""Ceiling on each git call in the per-turn "did anything change" measurement.

A probe that times out returns ABSENT (``None``), never "nothing changed" —
absence of a measurement must not be readable as absence of work.
"""


_APPLIED_SDK_TIMEOUT_RE = re.compile(r"SDK timeout after (\d+)s")


def _applied_sdk_timeout_seconds(error: Optional[str]) -> Optional[int]:
    """The limit a timed-out invocation ran under, read from its own error.

    The invoker writes ``"SDK timeout after <N>s: ..."`` with the limit it
    applied after scaling the base for the task. ``None`` when the error does
    not say.
    """
    if not error:
        return None
    match = _APPLIED_SDK_TIMEOUT_RE.search(str(error))
    return int(match.group(1)) if match else None


def _worktree_change_snapshot(
    worktree_path: Path,
    timeout_s: int = WORKTREE_CHANGE_PROBE_TIMEOUT_S,
    *,
    no_optional_locks: bool = False,
) -> Optional[Dict[str, str]]:
    """Take a git snapshot of everything uncommitted in ``worktree_path``.

    Returns a mapping of worktree-relative path to a short signature of that
    path's current state, or ``None`` when git could not answer (missing
    binary, non-zero exit, timeout, unreadable worktree). ``None`` means
    UNKNOWN and is never treated as "nothing changed".

    The signature is built from two cheap, deterministic sources:

    * ``git status --porcelain -uall`` — which paths differ from HEAD at all,
      including files git is not tracking yet.
    * ``git diff --numstat HEAD`` — how many lines each tracked path differs
      by — PLUS that file's size and modification time, because the line counts
      alone do not move for a one-line-for-one-line edit, and three of those in
      a row would otherwise read as three turns of no progress.

    For untracked paths git has no numstat, so size and modification time
    stand in: any write moves at least one of them.

    Paths the orchestrator owns rather than the generator — task state files,
    the build's own ``.guardkit/autobuild/`` records, installed packages,
    ``node_modules`` and friends — are filtered out with the same shared
    predicate the Player report filter uses. Without that filter every turn
    would look busy because the build writes its own bookkeeping every turn.
    The leavings of a test run (``__pycache__``, ``.coverage``, ``htmlcov`` and
    the like) are dropped for the same reason — the generator runs tests inside
    its own turn, so those land between the two photographs.

    ``no_optional_locks`` (13 October 2026) runs both git commands with
    ``GIT_OPTIONAL_LOCKS=0``, so ``git status`` never takes the index lock to
    refresh it. The progress log's snapshots use it, because they run while
    the Player is working in the same worktree and must never make one of
    its own git commands fail on a held lock.
    """
    try:
        from guardkit.orchestrator.agent_invoker import (
            _is_orchestrator_managed_path,
        )
    except ImportError:  # pragma: no cover - defensive
        logger.debug(
            "worktree change probe: orchestrator-managed path filter "
            "unavailable; treating the measurement as absent."
        )
        return None

    worktree_path = Path(worktree_path)
    if not worktree_path.exists():
        return None

    from guardkit.lib.project_git import run_git

    git_env: Optional[Dict[str, str]] = None
    if no_optional_locks:
        git_env = {"GIT_OPTIONAL_LOCKS": "0"}

    def _git(args: List[str]) -> Optional[str]:
        try:
            proc = run_git(args, cwd=worktree_path, timeout=timeout_s, env=git_env)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning(
                "worktree change probe: 'git %s' failed in %s (%s); "
                "the turn's file-change count stays absent.",
                " ".join(args), worktree_path, exc,
            )
            return None
        if proc.returncode != 0:
            logger.warning(
                "worktree change probe: 'git %s' exited %s in %s (%s); "
                "the turn's file-change count stays absent.",
                " ".join(args), proc.returncode, worktree_path,
                (proc.stderr or "").strip()[:200],
            )
            return None
        return proc.stdout

    status_out = _git(["status", "--porcelain", "-uall"])
    if status_out is None:
        return None

    snapshot: Dict[str, str] = {}
    untracked: List[str] = []
    for line in status_out.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        path_part = line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ")[-1]
        rel = path_part.strip().strip('"')
        if not rel:
            continue
        if _is_orchestrator_managed_path(rel, worktree_path):
            continue
        if _is_test_run_artefact(rel):
            continue
        snapshot[rel] = code
        if code == "??":
            untracked.append(rel)

    # Tracked paths: line-level signature so a further edit to an
    # already-changed file still registers.
    numstat_out = _git(["diff", "--numstat", "HEAD"])
    if numstat_out is None:
        return None
    for line in numstat_out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added, removed, rel = parts[0], parts[1], parts[-1].strip().strip('"')
        if not rel or _is_orchestrator_managed_path(rel, worktree_path):
            continue
        if _is_test_run_artefact(rel):
            continue
        # The line counts alone are NOT enough: a one-line-for-one-line edit
        # keeps added/removed identical, so three genuine consecutive edits
        # measured as three zero-change turns and aborted a healthy build as a
        # stall (found by review, 2026-09-01, before this ever ran a build).
        # The file's own size and timestamp move on any write, so they close
        # it. If a tool touches a file without changing it the signature moves
        # anyway — that only ever suppresses a stall, never invents one, which
        # is the direction to fail in.
        try:
            st = (worktree_path / rel).stat()
            stamp = f"{st.st_size}/{st.st_mtime_ns}"
        except OSError:
            stamp = "unreadable"
        snapshot[rel] = f"{snapshot.get(rel, '')}|{added}/{removed}|{stamp}"

    # Untracked paths: git has no diff for them, so stat stands in. Capped so
    # a worktree with a huge un-ignored tree (an npm install that landed
    # outside .gitignore, say) cannot turn a per-turn probe into a filesystem
    # walk; above the cap the path set alone carries the signal.
    if len(untracked) > _UNTRACKED_STAT_CAP:
        logger.info(
            "worktree change probe: %s untracked paths in %s exceeds the "
            "stat cap of %s; comparing the path list only.",
            len(untracked), worktree_path, _UNTRACKED_STAT_CAP,
        )
        untracked = []
    for rel in untracked:
        try:
            st = (worktree_path / rel).stat()
        except OSError:
            continue
        snapshot[rel] = f"{snapshot[rel]}|{st.st_size}/{st.st_mtime_ns}"

    return snapshot


def count_changed_paths(
    before: Optional[Dict[str, str]],
    after: Optional[Dict[str, str]],
) -> Optional[int]:
    """How many paths differ between two worktree snapshots.

    Returns ``None`` when either snapshot is absent — an unmeasured turn is
    unknown, not empty. Otherwise returns the number of paths that appeared,
    disappeared, or changed signature between the two.
    """
    if before is None or after is None:
        return None
    changed = 0
    for path in set(before) | set(after):
        if before.get(path) != after.get(path):
            changed += 1
    return changed


OUTCOME_CAPTURE_TIMEOUT_SECONDS = 20.0
"""Ceiling on the flywheel's build-outcome write at an autobuild terminal.

The write publishes over the network. The terminal is not allowed to wait on
it: if the writer has not answered within this window the build reports its
own result anyway and the missed write is logged in plain words. One attempt,
no retries — a retry loop at a terminal is a hang with better manners.

THE REAL WORST CASE, in plain words: this number plus the publish path's
hang-up bound (``harvest_publisher.PUBLISH_TEARDOWN_TIMEOUT_SECONDS``, 5s), so
about 25 seconds today. Cutting the write off does not end it instantly — the
publish still has to close its connection, and closing talks to the broker too.
That close is separately bounded for exactly this reason; without the bound it
inherits nats-py's 30-second drain default and a stalled broker holds the
build's final line for nearly a minute after this ceiling has expired."""


# The v4 contract emits every Coach finding at the constant severity
# "major" (coach_output_parser._adapt_v4_to_internal).
_FEEDBACK_SEVERITY_ORDER: Dict[str, int] = {
    "must_fix": 0,
    "critical": 0,
    "major": 1,
    "high": 1,
    "error": 1,
    "should_fix": 2,
    "minor": 3,
    "warning": 4,
}


def _feedback_issue_rank(issue: Dict[str, Any]) -> int:
    """The severity rank of an issue: rejection-level issues first."""
    return _FEEDBACK_SEVERITY_ORDER.get(issue.get("severity", "warning"), 99)


def _feedback_issue_order(issue: Dict[str, Any]) -> int:
    """The order a person and the Player are shown issues in."""
    return _feedback_issue_rank(issue)


def _feedback_issue_is_must_fix(issue: Dict[str, Any]) -> bool:
    """Whether an issue is rejection-level (must_fix, critical or major)."""
    return _feedback_issue_rank(issue) <= 1


def _player_result_timeout(result: Any) -> Optional[Dict[str, Any]]:
    """The timeout fields of a coder result that ran out of time, or ``None``.

    Reads the result's report (the timeout fields, or a rebuilt report's
    ``_recovery_metadata``) and then its error text.
    """
    if result is None:
        return None
    return player_timeout_from_report(
        getattr(result, "report", None)
    ) or player_timeout_from_error(getattr(result, "error", None))


#: Issue categories that already tell the coder its turn ran out of time.
#: Feedback that carries one of them gets no second timeout note.
_TIMEOUT_ISSUE_CATEGORIES = frozenset(
    {PLAYER_TIMED_OUT_CATEGORY, TASK_WORK_TIMEOUT_CATEGORY}
)


# ============================================================================
# Exceptions
# ============================================================================


class OrchestrationError(Exception):
    """Base exception for orchestration errors."""

    pass


class SetupPhaseError(OrchestrationError):
    """Raised when setup phase fails."""

    pass


class LoopPhaseError(OrchestrationError):
    """Raised when loop phase encounters critical error."""

    pass


class FinalizePhaseError(OrchestrationError):
    """Raised when finalize phase fails."""

    pass


class PreLoopPhaseError(OrchestrationError):
    """Raised when pre-loop quality gates fail."""

    pass


# ============================================================================
# Data Models
# ============================================================================


class DesignExtractionPhaseError(OrchestrationError):
    """Raised when Phase 0 design extraction fails.

    This error indicates that design extraction could not be completed,
    either due to MCP unavailability or extraction failure.

    Attributes
    ----------
    source : str
        Design source ('figma' or 'zeplin')
    reason : str
        Human-readable reason for failure
    """

    def __init__(self, message: str, source: Optional[str] = None, reason: Optional[str] = None):
        self.source = source
        self.reason = reason
        super().__init__(message)


@dataclass
class DesignContext:
    """
    Design context extracted from Figma or Zeplin for agent consumption.

    This dataclass captures design information extracted via MCP during Phase 0,
    providing structured context for Player and Coach agents.

    Attributes
    ----------
    elements : List[Dict[str, Any]]
        Component structure from design (what's in the design)
    tokens : Dict[str, Any]
        Design tokens: colors, spacing, typography
    constraints : Dict[str, bool]
        Prohibition checklist (12 categories for design compliance)
    visual_reference : Optional[str]
        Path or URL to reference screenshot
    summary : str
        ~3K token summary for agent context (not raw MCP data)
    source : str
        Design source: "figma" or "zeplin"
    metadata : Dict[str, Any]
        Additional metadata: file_key, node_id, extraction timestamp, hash

    Examples
    --------
    >>> context = DesignContext(
    ...     elements=[{"name": "Button", "type": "component"}],
    ...     tokens={"colors": {"primary": "#3B82F6"}},
    ...     constraints={"no_shadcn_icons": True},
    ...     visual_reference="https://figma.com/api/v1/images/...",
    ...     summary="Button component with primary/secondary variants...",
    ...     source="figma",
    ...     metadata={"file_key": "abc123", "node_id": "2:2"},
    ... )
    """

    elements: List[Dict[str, Any]]
    tokens: Dict[str, Any]
    constraints: Dict[str, bool]
    visual_reference: Optional[str]
    summary: str
    source: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class ContextStatus:
    """
    Context retrieval status for a single agent invocation.

    Captures whether memory context was retrieved, skipped, disabled, or failed,
    along with token usage and category counts for observability.

    Attributes
    ----------
    status : Literal["retrieved", "skipped", "disabled", "failed"]
        Outcome of the context retrieval attempt
    categories_count : int
        Number of context categories populated (0 if not retrieved)
    budget_used : int
        Tokens used from the context budget (0 if not retrieved)
    budget_total : int
        Total context token budget (0 if not retrieved)
    reason : Optional[str]
        Reason for skip/failure (None if retrieved successfully)
    """

    status: Literal["retrieved", "skipped", "disabled", "failed"]
    categories_count: int = 0
    budget_used: int = 0
    budget_total: int = 0
    reason: Optional[str] = None


@dataclass(frozen=True)
class TurnRecord:
    """
    Immutable record of a Player↔Coach turn.

    This dataclass captures the complete state of a single adversarial turn,
    including both Player implementation and Coach validation results.

    Attributes
    ----------
    turn : int
        Turn number (1-indexed)
    player_result : AgentInvocationResult
        Result from Player agent invocation
    coach_result : Optional[AgentInvocationResult]
        Result from Coach agent invocation (None if Player failed critically)
    decision : Literal["approve", "feedback", "error"]
        Final decision for this turn
    feedback : Optional[str]
        Coach feedback text for next turn (None if approved or error)
    timestamp : str
        ISO 8601 timestamp when turn completed
    player_context_status : Optional[ContextStatus]
        Context retrieval status for Player invocation (None if not tracked)
    coach_context_status : Optional[ContextStatus]
        Context retrieval status for Coach invocation (None if not tracked)
    files_changed_this_turn : Optional[int]
        Number of files this turn actually changed in the worktree, measured
        from git rather than taken from the Player's report. ``None`` when no
        measurement was taken (git unavailable, or the turn ended early).

    Examples
    --------
    >>> record = TurnRecord(
    ...     turn=1,
    ...     player_result=player_result,
    ...     coach_result=coach_result,
    ...     decision="feedback",
    ...     feedback="Add token refresh test",
    ...     timestamp="2025-12-23T10:30:00Z",
    ... )
    """

    turn: int
    player_result: AgentInvocationResult
    coach_result: Optional[AgentInvocationResult]
    decision: Literal["approve", "feedback", "error"]
    feedback: Optional[str]
    timestamp: str
    visual_verification: Optional[Dict[str, Any]] = None
    design_compliance: Optional[Dict[str, Any]] = None
    player_context_status: Optional[ContextStatus] = None
    coach_context_status: Optional[ContextStatus] = None
    sdk_turns_used: Optional[int] = None      # TASK-VPR-003: Actual SDK turns from ResultMessage
    sdk_max_turns: Optional[int] = None        # TASK-VPR-003: Effective SDK turn ceiling
    sdk_ceiling_hit: Optional[bool] = None     # TASK-VPR-003: Whether ceiling was hit
    # TASK-AB-NOCHANGE01: how many files this turn actually changed in the
    # worktree, measured with git before the generator ran and again after it
    # (and after the orchestrator's own Phase 4/5 specialists) finished — never
    # from the generator's report, which is exactly the thing that lies. Paths
    # the orchestrator owns (``.guardkit/autobuild/``, ``tasks/<state>/``,
    # site-packages, node_modules, ...) are filtered out via the shared
    # ``_is_orchestrator_managed_path``. ``None`` means NOT MEASURED — git could
    # not answer, or this turn ended before the measurement point. ``None`` is
    # never read as zero: an absent measurement can neither stall a task nor
    # complete one.
    files_changed_this_turn: Optional[int] = None
    # FEAT-2C42 (8 October 2026): when this turn's Player ran out of time,
    # the timeout must-fix on its own, as feedback text. A fresh-start
    # (perspective reset) turn drops all review feedback but keeps this: it is
    # a fact about how the turn ran, not review content. ``None`` otherwise.
    timeout_note: Optional[str] = None


@dataclass
class OrchestrationResult:
    """
    Result of complete orchestration run.

    This dataclass encapsulates all information from a complete AutoBuild
    orchestration, including turn history, final decision, and worktree state.

    Attributes
    ----------
    task_id : str
        Task identifier (e.g., "TASK-XXX-YYYY")
    success : bool
        True when the task is DONE — the Coach approved, or the Coach verified
        the builder's claim that the tree already satisfied it. False for
        max_turns, a stall, or an error.
    total_turns : int
        Total number of turns executed
    final_decision : Literal["approved", "max_turns_exceeded", "error"]
        Final orchestration outcome
    turn_history : List[TurnRecord]
        List of all turn records
    worktree : Worktree
        Worktree instance (preserved on all outcomes for human review)
    error : Optional[str]
        Error message if orchestration failed (None on success)

    Examples
    --------
    >>> result = OrchestrationResult(
    ...     task_id="TASK-XXX-YYYY",
    ...     success=True,
    ...     total_turns=2,
    ...     final_decision="approved",
    ...     turn_history=[record1, record2],
    ...     worktree=worktree,
    ... )
    """

    task_id: str
    success: bool
    total_turns: int
    final_decision: Literal["approved", "max_turns_exceeded", "error", "cancelled", "timeout", "pre_loop_blocked", "rate_limited", "design_extraction_failed"]
    turn_history: List[TurnRecord]
    worktree: Worktree
    error: Optional[str] = None
    pre_loop_result: Optional[Dict[str, Any]] = None  # Results from pre-loop quality gates
    ablation_mode: bool = False  # Track if result was from ablation mode
    recovery_count: int = 0  # Number of state recovery attempts
    design_context: Optional["DesignContext"] = None  # Phase 0 design extraction result


# ============================================================================
# Orchestrator
# ============================================================================


class AutoBuildOrchestrator:
    """
    Phase-based orchestration for adversarial Player↔Coach workflow.

    This class implements the central coordination logic for GuardKit's AutoBuild
    system, managing the complete lifecycle of task implementation through an
    adversarial agent loop.

    Four-Phase Execution Pattern
    -----------------------------
    1. Setup Phase: Create isolated worktree, initialize progress display
    2. Pre-Loop Phase: Execute quality gates via task-work delegation
    3. Loop Phase: Execute Player→Coach turns until approval or max_turns
    4. Finalize Phase: Preserve worktree for manual review (auto_merge removed per review)

    Quality Gates (Pre-Loop via task-work --design-only)
    ----------------------------------------------------
    - Phase 1.6: Clarifying Questions
    - Phase 2: Implementation Planning
    - Phase 2.5A: Pattern Suggestions
    - Phase 2.5B: Architectural Review (SOLID/DRY/YAGNI)
    - Phase 2.7: Complexity Evaluation
    - Phase 2.8: Human Checkpoint

    Loop Quality Gates
    ------------------
    - Max turns enforced (dynamic, based on complexity)
    - Coach approval required for success
    - Worktree preserved on all exits for human review
    - Progress displayed in real-time

    Architectural Notes
    -------------------
    - Synchronous execution (async/await removed per review - no actual concurrency)
    - Dependency injection for testability
    - Immutable turn records for audit trail
    - Graceful error handling with worktree preservation

    Attributes
    ----------
    repo_root : Path
        Repository root directory
    max_turns : int
        Maximum adversarial turns allowed
    _worktree_manager : WorktreeManager
        WorktreeManager instance
    _agent_invoker : Optional[AgentInvoker]
        AgentInvoker instance (initialized lazily with worktree path)
    _progress_display : ProgressDisplay
        ProgressDisplay instance

    Examples
    --------
    >>> orchestrator = AutoBuildOrchestrator(
    ...     repo_root=Path.cwd(),
    ...     max_turns=5,
    ... )
    >>>
    >>> result = orchestrator.orchestrate(
    ...     task_id="TASK-XXX-YYYY",
    ...     requirements="Implement feature X",
    ...     acceptance_criteria=["Criterion 1", "Criterion 2"],
    ... )
    """

    _STALL_NORMALIZE_PATTERNS = [
        (re.compile(r'\S+\.py::\S+'), 'FILE::TEST'),
        (re.compile(r'line \d+'), 'line N'),
        (re.compile(r'\d+(\.\d+)?%'), 'N%'),
        (re.compile(r'in \d+\.\d+s'), 'in Ns'),
        (re.compile(r'\d+ (passed|failed|error|errors|skipped|warnings?)'), r'N \1'),
        (re.compile(r'/\S+/worktrees/\S+/'), '/WORKTREE/'),
    ]

    def __init__(
        self,
        repo_root: Path,
        max_turns: int = 5,
        resume: bool = False,
        enable_pre_loop: bool = True,
        pre_loop_options: Optional[Dict[str, Any]] = None,
        existing_worktree: Optional[Worktree] = None,
        worktree_manager: Optional[WorktreeManager] = None,
        agent_invoker: Optional[AgentInvoker] = None,
        progress_display: Optional[ProgressDisplay] = None,
        pre_loop_gates: Optional[PreLoopQualityGates] = None,
        development_mode: str = "tdd",
        sdk_timeout: int = DEFAULT_SDK_TIMEOUT,
        skip_arch_review: bool = False,
        enable_perspective_reset: bool = True,
        enable_checkpoints: bool = True,
        ablation_mode: bool = False,
        enable_context: bool = True,
        verbose: bool = False,
        context_loader: Optional[AutoBuildContextLoader] = None,
        feature_id: Optional[str] = None,
        cancellation_event: Optional[threading.Event] = None,
        timeout_event: Optional[threading.Event] = None,
        task_timeout: Optional[int] = None,
        timeout_multiplier: Optional[float] = None,
        wave_size: int = 1,
        shares_working_copy: bool = False,
        emitter: Optional[Any] = None,
        progress_logger: Optional[Any] = None,
        venv_python: Optional[str] = None,
        model: Optional[str] = None,  # TASK-FIX-MODELPLUMB
        coach_model: Optional[str] = None,  # TASK-FIX-COACHBUDG01: per-role Coach override
        evidence_repos: Optional[List[EvidenceRepo]] = None,  # TASK-AB-XREPOEV01
        seed_feedback: Optional[str] = None,  # TASK-AB-COACHRUNPARITY01 (arm a)
        smoke_command: Optional[str] = None,  # TASK-AB-COACHRUNPARITY01 (arm b)
        smoke_expected_exit: int = 0,  # TASK-AB-COACHRUNPARITY01 (arm b)
        feature_check_repair: Optional[Any] = None,  # whole-feature repair round
        repair_round: Optional[Any] = None,  # gate-driven repair round, in memory
        sdk_timeout_is_override: Optional[bool] = None,
        expected_branch: Optional[str] = None,
        expected_branch_pinned: bool = False,
        effective_concurrency: Optional[int] = None,
    ):
        """
        Initialize AutoBuildOrchestrator.

        Parameters
        ----------
        repo_root : Path
            Repository root directory
        max_turns : int, optional
            Maximum adversarial turns (default: 5, may be overridden by pre-loop)
        resume : bool, optional
            Resume from previous state (default: False)
        enable_pre_loop : bool, optional
            Enable pre-loop quality gates via task-work delegation (default: True)
        pre_loop_options : Optional[Dict[str, Any]], optional
            Options to pass to pre-loop quality gates:
            - no_questions: Skip clarification
            - with_questions: Force clarification
            - answers: Inline answers for automation
        existing_worktree : Optional[Worktree], optional
            Use an existing worktree instead of creating a new one (for feature mode).
            When provided, _setup_phase() will reuse this worktree.
        worktree_manager : Optional[WorktreeManager], optional
            Optional WorktreeManager for DI/testing
        agent_invoker : Optional[AgentInvoker], optional
            Optional AgentInvoker for DI/testing
        progress_display : Optional[ProgressDisplay], optional
            Optional ProgressDisplay for DI/testing
        pre_loop_gates : Optional[PreLoopQualityGates], optional
            Optional PreLoopQualityGates for DI/testing
        development_mode : str, optional
            Development mode for implementation (default: "tdd").
            Valid values: "standard", "tdd", "bdd"
        sdk_timeout : int, optional
            SDK timeout in seconds for agent invocations (default: 1200).
            Valid range: 60-3600 seconds.
        skip_arch_review : bool, optional
            Skip architectural review quality gate (default: False).
            Use with caution - bypasses SOLID/DRY/YAGNI validation.
        enable_perspective_reset : bool, optional
            Enable fresh perspective reset to prevent anchoring bias (default: True).
            When enabled, Player receives only original requirements (no feedback) at
            turns 3 and 5, allowing fresh perspective and breaking anchored assumptions.
            This helps prevent the Player from becoming locked into early approaches.
        enable_checkpoints : bool, optional
            Enable worktree checkpointing for rollback (default: True).
            Creates git commits at turn boundaries for context pollution recovery.
        enable_context : bool, optional
            Enable job-specific context retrieval from the memory backend (default: True).
            When enabled, retrieves role_constraints, quality_gates, and turn_states
            for Player and Coach turns (TASK-GR6-006).
        verbose : bool, optional
            Include detailed context information in output (default: False).
            When enabled, shows budget usage and category details.
        context_loader : Optional[AutoBuildContextLoader], optional
            Optional AutoBuildContextLoader for DI/testing.
        feature_id : Optional[str], optional
            Feature ID to use for turn state capture (default: None).
            When provided, overrides regex extraction from task ID.
        cancellation_event : Optional[threading.Event], optional
            Cooperative cancellation signal from FeatureOrchestrator (default: None).
            When set, _loop_phase() exits cleanly at the next checkpoint.
        timeout_event : Optional[threading.Event], optional
            Feature-level timeout signal from FeatureOrchestrator (default: None).
            When set, _loop_phase() exits with "timeout" instead of "cancelled".
            Takes priority over cancellation_event (TASK-ABFIX-006).
        task_timeout : Optional[int], optional
            Per-task timeout in seconds from FeatureOrchestrator (default: None).
            Used for SDK-level timeout logging to show remaining feature budget.
        wave_size : int, optional
            Number of tasks executing in parallel in the current wave (default: 1).
            Passed through to CoachValidator to enable test isolation and lenient
            failure classification in parallel waves (TASK-ABFIX-005).
        shares_working_copy : bool, optional
            True when other tasks of this wave change the same working copy at
            the same time as this one (default: False). Set by the feature
            orchestrator from the wave's real concurrency, not from its size:
            a wave run one task at a time is not shared, because each task
            measures git's changes from its own starting commit. When True, a
            report rebuilt from git is never counted as this task's evidence
            (FEAT-2C42).
        emitter : Optional[EventEmitter], optional
            EventEmitter for lifecycle event instrumentation (default: NullEmitter).
            When provided, lifecycle events (task.started, task.completed,
            task.failed) are emitted during orchestration (TASK-INST-004).

        Raises
        ------
        ValueError
            If max_turns < 1

        Notes
        -----
        Dependency injection parameters enable comprehensive unit testing
        with mocks while maintaining clean production initialization.

        Pre-loop quality gates delegate to task-work --design-only, achieving
        100% code reuse of existing quality gates (TASK-REV-0414, Option D).

        The existing_worktree parameter enables feature mode where multiple
        tasks share a single worktree, added for TASK-FBC-001.

        Fresh perspective reset (TASK-BRF-001) addresses anchoring bias prevention
        by resetting context at specified turns, enabling the Player to reconsider
        the problem from first principles rather than being anchored by prior feedback.
        """
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")

        self.repo_root = Path(repo_root).resolve()
        self.max_turns = max_turns
        self.resume = resume
        self.enable_pre_loop = enable_pre_loop
        self.pre_loop_options = pre_loop_options or {}
        self.development_mode = development_mode
        self.sdk_timeout = sdk_timeout
        self._sdk_timeout_is_override = sdk_timeout_is_override
        self.timeout_multiplier = timeout_multiplier
        self.skip_arch_review = skip_arch_review
        self.enable_perspective_reset = enable_perspective_reset
        self.enable_checkpoints = enable_checkpoints
        self.ablation_mode = ablation_mode
        self._emitter = emitter if emitter is not None else NullEmitter()  # TASK-INST-004
        # TASK-OBS-9F43 AC-2: Mint run_id once per orchestration
        # All events (lifecycle + llm.call + tool.exec) share this run_id for joinability
        self._run_id = f"run-{datetime.now().strftime('%Y%m%d%H%M%S')}-{id(self)}"
        # Set when orchestrate() begins; read by the build-outcome write at
        # every terminal so the record carries when the build started and how
        # long it took.
        self._orchestrate_started_at: Optional[datetime] = None
        # The last terminal this build already wrote an outcome for. Read by
        # ONE caller — the crashed path — so a crash that happens AFTER a
        # terminal was recorded says which terminal it supersedes instead of
        # leaving two outcomes that look like two unrelated builds.
        self._last_captured_terminal: Optional[str] = None
        self._existing_worktree = existing_worktree  # For feature mode (TASK-FBC-001)
        # TASK-FIX-7A05: Python interpreter Coach uses for pytest. Sourced
        # from BootstrapResult.venv_python in the feature orchestrator so
        # Coach verifies against the same interpreter the bootstrap built.
        self._venv_python: Optional[str] = venv_python
        # TASK-FIX-MODELPLUMB: CLI --model threaded through to AgentInvoker
        # then used as default when invoke_coach / _invoke_with_role /
        # specialist invocations don't specify their own model. Load-bearing
        # for the LangGraph harness path (DeepAgents needs a real model
        # factory; model=None fails construction with "'function' object has
        # no attribute 'name'"). Decorative-but-harmless for the SDK path
        # (routes via ANTHROPIC_BASE_URL).
        self._model_name: Optional[str] = model
        # TASK-FIX-COACHBUDG01 (2026-06-06): optional per-role override for Coach.
        # When non-None, AgentInvoker routes role='coach' and role='coach_test'
        # invocations to this model while Player and specialists stay on
        # self._model_name. None preserves the pre-COACHBUDG01 behaviour
        # (Coach uses the same model as Player) for backwards compatibility.
        # Durable per-repo flip (2026-07-26): when --coach-model is omitted,
        # fall back to .guardkit/config.yaml autobuild.coach.model so a repo
        # config can carry the coach seat pairing without launch flags.
        self._coach_model_name: Optional[str] = (
            coach_model or self._load_coach_config().get("model") or None
        )
        # Hardcoded reset turns per architectural review (TASK-BRF-001): [3, 5]
        self.perspective_reset_turns: List[int] = [3, 5] if enable_perspective_reset else []
        self._turn_history: List[TurnRecord] = []
        self._checkpoint_manager: Optional[WorktreeCheckpointManager] = None  # Initialized lazily
        self.recovery_count: int = 0  # Track number of state recovery attempts

        # Context retrieval settings (TASK-GR6-006)
        self.enable_context = enable_context
        self.verbose = verbose
        self._context_loader = context_loader  # For DI/testing only; thread-local loaders used at runtime
        self._feature_id: Optional[str] = feature_id  # Passed from FeatureOrchestrator or set during orchestration
        # TASK-AB-XREPOEV01: resolved sibling repos whose writes count as task
        # evidence. Threaded into AgentInvoker (report enrichment + honesty
        # resolution), CoachValidator (independent sibling tests), and the
        # checkpoint manager (per-repo commits). Empty -> worktree-only
        # behaviour, so undeclared sibling-repo writes stay invisible (AC-003).
        self._evidence_repos: List[EvidenceRepo] = list(evidence_repos or [])
        # The admitted writer scope; orchestrate() sets it under the lease.
        self.task_work_scope = None
        # TASK-AB-COACHRUNPARITY01 (arm a): turn-1 seed feedback. When a
        # post-wave smoke gate fails, the feature orchestrator re-enters the
        # wave with the smoke error injected here so the Player's first turn
        # carries it as `previous_feedback` (see _loop_phase). Default None ->
        # identical to today for every non-retry task.
        self._seed_feedback: Optional[str] = seed_feedback
        # The branch every checkpoint must land on, pinned once by the feature
        # orchestrator at build start (build 0D7C). None: decided here, at
        # this (single) task's start.
        self._expected_branch: Optional[str] = expected_branch
        # True when the feature orchestrator pinned it, even to None (no
        # branch could be determined): then this task never re-reads HEAD.
        self._expected_branch_pinned: bool = expected_branch_pinned
        # TASK-AB-COACHRUNPARITY01 (arm b): the feature smoke command (the
        # deliverable's real runtime entry point). Threaded into CoachValidator
        # so the per-task Coach can exercise it before approving on a
        # single-task wave (the "passes pytest but does not run" oracle).
        # Default None -> no per-task runtime-parity check.
        self._smoke_command: Optional[str] = smoke_command
        # Exit code that counts as a clean standalone run (feature's
        # smoke_gates.expected_exit; default 0).
        self._smoke_expected_exit: int = smoke_expected_exit
        # Whole-feature repair round (18 October 2026): the feature
        # orchestrator's ``FeatureCheckRepair`` when this task was re-opened
        # because the project's whole-feature check failed, else None. Threaded
        # beside ``smoke_command`` into the primary Coach's validator, which
        # runs the check once per Coach turn; the loop reads that run for the
        # plain early stop (``_plan_contradicts_check_stop``). None -> every
        # turn runs exactly as before.
        self._feature_check_repair: Optional[Any] = feature_check_repair
        # Gate-driven repair round (20 October 2026): the ``RepairRound`` the
        # feature orchestrator started when it re-opened this task, handed to
        # this task's AgentInvoker for its plan audit and Coach prompt. Held in
        # memory only; None on every other task (repair_round.py).
        self._repair_round: Optional[Any] = repair_round
        # Set when a repair round's turn is approved: the non-protected files
        # the reviewer was shown on that turn (AgentInvoker.repair_round_inventory).
        self.repair_round_approved_files: Optional[FrozenSet[str]] = None
        self._cancellation_event: Optional[threading.Event] = cancellation_event  # Cooperative cancellation (TASK-ASF-007)
        self._timeout_event: Optional[threading.Event] = timeout_event  # Feature-level timeout signal (TASK-ABFIX-006)
        self._progress_logger = progress_logger  # TASK-FIX-OBS2: Per-task progress logging
        self._task_timeout: Optional[int] = task_timeout  # Feature task budget in seconds (TASK-ABFIX-006)
        # Remaining wall budget (seconds) captured at the instant a per-turn
        # budget check fails, so the finalize-phase summary/error builders can
        # report "remaining=<X>s < min=<MIN>s" instead of the generic
        # "Unknown error occurred" (TASK-FIX-TBXMSG01).
        self._timeout_budget_remaining: Optional[float] = None
        self.wave_size: int = max(1, int(wave_size))  # Parallel wave context (TASK-ABFIX-005)
        self.effective_concurrency: Optional[int] = (
            int(effective_concurrency)
            if effective_concurrency is not None
            else None
        )
        self.shares_working_copy: bool = bool(shares_working_copy)  # FEAT-2C42
        # Per-turn context status tracking for progress display (TASK-FIX-GCW5)
        self._last_player_context_status: Optional[ContextStatus] = None
        self._last_coach_context_status: Optional[ContextStatus] = None
        # Per-thread memory client storage (TASK-FIX-GTP2). FEAT-MEM-09 WS-2c:
        # holds a FleetMemoryClientFactory, which exposes get_thread_client() and
        # hands out clients with an initialize()/is_initialized/close() lifecycle,
        # so the per-thread machinery below is duck-typed.
        self._factory: Optional[Any] = None
        # TASK-ACR-005: Store event loop reference with each loader for proper cleanup
        self._thread_loaders: Dict[int, Tuple[Optional[AutoBuildContextLoader], asyncio.AbstractEventLoop]] = {}
        # Why a thread has no loader, kept beside the None loader above so the
        # per-turn memory line can say it on every turn (2026-10-04): a pair
        # of (state, reason), e.g. ("skipped at start-up", "the memory store
        # connection failed").
        self._thread_loader_skips: Dict[int, Tuple[str, str]] = {}
        # TASK-GLF-002: Suppress memory operations during shutdown
        self._shutting_down: bool = False

        # WHICH MEMORY THIS BUILD USES, SETTLED ONCE, HERE (2026-09-21).
        # Before any thread gets a client, and before anything reads or writes:
        # a name handed to this build on purpose, else the name this project
        # declares in its own .guardkit/config.yaml, else nothing — and nothing
        # means memory is off for this build, said out loud with the line to
        # add. There is no fallback name, which is what used to file every
        # project's outcomes under GuardKit's own.
        # The project's settings are read from the CANONICAL repo root — the
        # build's own working folder — which is the same copy the toolchain
        # declaration is read from (see _load_toolchain) and, since 2026-09-21,
        # the same copy the pattern-sources declaration is read from too (the
        # context loader's ``declaration_root``, below). ONE copy of one file
        # answers everything this project declares about its memory; there used
        # to be two, and two can disagree for a whole build.
        # When Forge launched this build it handed the name over on purpose
        # (``GUARDKIT_MEMORY_PROJECT``), having read it at the commit the work
        # started from. THAT NAME WINS: this read is for GuardKit used by hand,
        # with no Forge, and a stale working copy must never overrule the commit
        # the work actually started from.
        # configure_memory_project never raises: a failure to settle the name
        # is itself the answer "memory off", settled through the same path, so
        # nothing built for an earlier project in this process survives it.
        self._memory_project = configure_memory_project(self.repo_root)

        # Store factory reference for per-thread client creation (TASK-FIX-GTP2)
        # Replaces shared singleton pattern that caused cross-loop hangs in parallel mode.
        # FEAT-MEM-09 WS-2c: fleet-memory is the only backend; get_memory_factory()
        # returns None when fleet-memory is disabled, in which case context
        # retrieval is disabled for this run.
        if self.enable_context and self._context_loader is None:
            try:
                self._factory = get_memory_factory()
                if self._factory is not None:
                    logger.info(
                        "Stored fleet-memory factory for per-thread context loading"
                    )
                else:
                    logger.info(
                        "Memory factory not available, context retrieval disabled"
                    )
            except ImportError:
                logger.info(
                    "Memory dependencies not installed, context retrieval disabled"
                )
            except Exception as e:
                logger.info(f"Could not obtain memory factory: {e}")

        # Log warning if ablation mode is active
        if self.ablation_mode:
            logger.warning(
                "⚠️ ABLATION MODE ACTIVE - Coach feedback disabled. "
                "This mode is for testing only and will produce inferior results."
            )

        # TASK-FIX-7A01 / TASK-REV-E4F5 F5: emit resolved claude-agent-sdk version
        # at startup so version-skew incidents (Run 2 `rate_limit_event` bug) are
        # diagnosable from autobuild logs without a separate `pip show` round-trip.
        # Always emits exactly one INFO line — falls back to an error form if
        # the SDK isn't importable / metadata is missing.
        try:
            from importlib.metadata import version as _pkg_version
            logger.info(f"claude-agent-sdk version: {_pkg_version('claude-agent-sdk')}")
        except Exception as _sdk_ver_err:
            logger.info(f"claude-agent-sdk version: unknown (SDK not importable: {_sdk_ver_err})")

        # Initialize dependencies (DI or defaults)
        self._worktree_manager = worktree_manager or WorktreeManager(
            repo_root=self.repo_root
        )
        self._agent_invoker = agent_invoker
        self._progress_display = progress_display or ProgressDisplay(max_turns=max_turns)
        self._pre_loop_gates = pre_loop_gates  # Initialized lazily with worktree path

        logger.info(
            f"AutoBuildOrchestrator initialized: repo={self.repo_root}, "
            f"max_turns={self.max_turns}, resume={self.resume}, "
            f"enable_pre_loop={self.enable_pre_loop}, "
            f"development_mode={self.development_mode}, "
            f"sdk_timeout={self.sdk_timeout}s, "
            f"skip_arch_review={self.skip_arch_review}, "
            f"enable_perspective_reset={self.enable_perspective_reset}, "
            f"reset_turns={self.perspective_reset_turns}, "
            f"enable_checkpoints={self.enable_checkpoints}, "
            f"ablation_mode={self.ablation_mode}, "
            f"existing_worktree={'provided' if existing_worktree else 'None'}, "
            f"enable_context={self.enable_context}, "
            f"context_loader={'provided' if self._context_loader else 'None'}, "
            f"factory={'available' if self._factory else 'None'}, "
            f"verbose={self.verbose}"
        )

    def orchestrate(self, task_id, requirements, acceptance_criteria, base_branch="main", **kwargs):
        from guardkit.orchestrator.task_work_scope import checkout_lease, ScopeUnavailable
        if self._existing_worktree is None:
            saved = self._worktree_manager.worktrees_dir / task_id
            if self.resume and saved.exists():
                # Step 2 (27 October 2026): a resumed single-task build goes on
                # in the checkout it left, under the same exclusive lease.
                self._existing_worktree = Worktree(
                    task_id=task_id,
                    branch_name=self._worktree_manager._build_branch_name(task_id),
                    path=saved,
                    base_branch=base_branch,
                )
            else:
                self._existing_worktree = self._worktree_manager.create(task_id=task_id, base_branch=base_branch)
        from guardkit.orchestrator.task_work_scope import current_lease, bind_fresh_footprint
        if current_lease() is None and not self.resume:
            task_path = kwargs.get("task_file_path")
            if task_path is None:
                try:
                    task_path = TaskLoader.load_task(task_id, repo_root=self.repo_root).get("file_path")
                except TaskNotFoundError:
                    pass
            bound_repos = bind_fresh_footprint(
                self._existing_worktree.path, self.repo_root, task_path, kind="task",
                expected=None,
            )
            if self._evidence_repos and self._evidence_repos != bound_repos:
                raise ScopeUnavailable("Caller-supplied sibling footprint differs from the immutable source")
            self._evidence_repos = bound_repos
        with checkout_lease(self._existing_worktree.path, self._evidence_repos) as lease:
            self.task_work_scope = lease.admit(task_id, str(getattr(self, 'feature_id', '') or ''))
            from guardkit.orchestrator.task_work_scope import bootstrap_admitted_checkout
            bootstrap_admitted_checkout(self.task_work_scope)
            if self._agent_invoker is not None:
                self._agent_invoker.task_work_scope = self.task_work_scope
                self._agent_invoker._baseline_commit = self.task_work_scope.baseline_commit
            result = self._orchestrate_owned(task_id, requirements, acceptance_criteria, base_branch, **kwargs)
            done = result.final_decision == "approved"
            if lease.failure and done:
                raise ScopeUnavailable(lease.failure)
            if not done:
                lease.poison(f"Task {task_id} was not approved; predecessor work preserved")
            return result

    def _orchestrate_owned(
        self,
        task_id: str,
        requirements: str,
        acceptance_criteria: List[str],
        base_branch: str = "main",
        task_file_path: Optional[Path] = None,
        requires_infrastructure: Optional[List[str]] = None,
        time_budget_seconds: Optional[float] = None,
        behavioural_oracle: Optional[Any] = None,
    ) -> OrchestrationResult:
        """
        Execute complete adversarial orchestration workflow.

        This is the main entry point for AutoBuild orchestration. It coordinates
        the four-phase execution pattern: Setup → Pre-Loop → Loop → Finalize.

        Four-Phase Execution
        --------------------
        1. Setup: Create isolated worktree, initialize progress display
        2. Pre-Loop: Execute quality gates via task-work delegation (if enabled)
        3. Loop: Execute Player↔Coach turns until approval or max_turns
        4. Finalize: Preserve worktree for human review

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-XXX-YYYY")
        requirements : str
            Task requirements description
        acceptance_criteria : List[str]
            List of acceptance criteria
        base_branch : str, optional
            Branch to create worktree from (default: "main")
        task_file_path : Optional[Path], optional
            Path to task file for state persistence (default: None)
        requires_infrastructure : Optional[List[str]], optional
            Infrastructure services required (e.g., ["postgresql", "redis"]).
            When provided by the caller (e.g., FeatureOrchestrator), takes
            precedence over any value in the task file frontmatter. When None,
            falls back to frontmatter value (single-task mode).
        behavioural_oracle : Optional[Any], optional
            Declared behavioural-oracle command supplied by the caller (the
            FeatureOrchestrator threads ``feature.behavioural_oracle`` here).
            Accepts a ``BehaviouralOracle`` model, a ``{"command": ...}``
            mapping, or a bare command string. Precedence is the INVERSE of
            ``requires_infrastructure``: the task's own frontmatter
            declaration WINS, because per design §B.1 the per-task
            declaration is the escape hatch that sits above every
            feature/repo-level one. When both are absent the leg stays
            absent, exactly as before TS-lane D.1a (TS-lane D.1a).

        Returns
        -------
        OrchestrationResult
            Complete orchestration result with turn history and worktree

        Raises
        ------
        SetupPhaseError
            If worktree creation fails
        PreLoopPhaseError
            If pre-loop quality gates fail (blocked by architectural review)
        OrchestrationError
            If critical phase failure occurs

        Examples
        --------
        >>> result = orchestrator.orchestrate(
        ...     task_id="TASK-XXX-YYYY",
        ...     requirements="Implement OAuth2 flow",
        ...     acceptance_criteria=["Support auth code flow", "Handle refresh"],
        ... )
        >>> print(result.final_decision)
        'approved'
        """
        logger.info(f"Starting orchestration for {task_id} (resume={self.resume})")

        # Wall-clock start, kept for the build-outcome record written at every
        # terminal (started_at / duration_minutes).
        self._orchestrate_started_at = datetime.now()
        # A fresh run supersedes nothing: an orchestrator instance can be
        # driven more than once, and the previous run's terminal must not be
        # named by this run's crash.
        self._last_captured_terminal = None
        # Step 1 (24 October 2026): each real check's last measured state for
        # this task, carried from the Coach's own evidence as it arrives.
        # True means its last measurement failed; only a later measured pass
        # clears it, never an absent result.
        self._measured_check_failed: Dict[str, bool] = {}

        # Emit task.started lifecycle event (TASK-INST-004)
        self._emit_task_started(task_id)

        pre_loop_result = None  # Initialize pre-loop result

        # Load task data to extract task_type, requires_infrastructure, and consumer_context for CoachValidator
        task_type: Optional[str] = None
        task_title: Optional[str] = None
        consumer_context: Optional[list] = None
        _ri_from_caller = requires_infrastructure  # Preserve explicit parameter (may be None)
        requires_infrastructure = None  # Reset; will be resolved via frontmatter then precedence
        _task_bo_unset = object()
        _task_bo_raw: Any = _task_bo_unset
        _component_raw: Any = None
        try:
            task_data = TaskLoader.load_task(task_id, repo_root=self.repo_root)
            frontmatter = task_data.get("frontmatter", {})
            _task_bo_raw = (
                frontmatter["behavioural_oracle"]
                if "behavioural_oracle" in frontmatter
                else _task_bo_unset
            )
            task_type = frontmatter.get("task_type")
            if task_type:
                logger.debug(f"Loaded task_type from task file: {task_type}")
            # Human-readable name for the build-outcome record (falls back to
            # the task id when the task file is absent or has no title).
            _title = frontmatter.get("title")
            if isinstance(_title, str) and _title.strip():
                task_title = _title.strip()
            ri = frontmatter.get("requires_infrastructure")
            if isinstance(ri, list):
                requires_infrastructure = ri
                logger.debug(f"Loaded requires_infrastructure from task file: {ri}")
            consumer_context = frontmatter.get("consumer_context")
            if isinstance(consumer_context, list):
                logger.debug(f"Loaded consumer_context from task file: {consumer_context}")
            # PER-COMPONENT SEAM: the task's `component:` selector, lifted
            # beside behavioural_oracle for the same reason and validated the
            # same way — RAW here, LOUDLY outside this try. Selection is
            # explicit and never inferred from the changed-file set: a
            # mixed-touch task must be split, not silently assigned to one
            # component (design §B.2).
            _component_raw = frontmatter.get("component")
            # Writable sibling membership was frozen from admitted source
            # before this mutable task metadata was read.
        except TaskNotFoundError:
            logger.debug(f"Task file not found for {task_id}, continuing with task_type=None")
        except Exception as e:
            logger.debug(f"Failed to load task metadata from task file: {e}, continuing with defaults")
            _component_raw = None

        # PER-COMPONENT SEAM: the task's `component:` selector; a name the
        # repository does not declare means the root component.
        component: Optional[str] = self._resolve_task_component(task_id, _component_raw)

        if _task_bo_raw is not _task_bo_unset and _task_bo_raw is not None:
            # The per-task declaration outranks the feature-level one.
            behavioural_oracle = (
                {"command": _task_bo_raw}
                if isinstance(_task_bo_raw, str)
                else _task_bo_raw
            )
            logger.info(
                "Loaded behavioural_oracle from task frontmatter for %s: %r",
                task_id, behavioural_oracle,
            )

        # Precedence: explicit parameter > frontmatter > None
        if _ri_from_caller is not None:
            requires_infrastructure = _ri_from_caller
            logger.debug(f"Using requires_infrastructure from caller: {_ri_from_caller}")
        # behavioural_oracle precedence is deliberately the OTHER WAY ROUND
        # (design §B.1): the frontmatter lift above has already overwritten
        # the caller's feature-level value, because the per-task declaration
        # is the escape hatch that outranks every broader declaration.

        try:
            # Phase 1: Setup (or resume existing worktree)
            if self.resume and task_file_path:
                worktree, start_turn = self._resume_from_state(task_id, task_file_path)
                resumed_from = getattr(
                    getattr(self, "task_work_scope", None), "baseline_commit", None
                )
            else:
                worktree = self._setup_phase(task_id, base_branch)
                start_turn = 1
                resumed_from = None

                # TS-lane D.1b (design §B.4) — THE SAME PIN, and it is NOT
                # optional. ``.guardkit/config.yaml`` lives inside the target
                # repo, which means it lives inside the worktree the builder is
                # editing: without a snapshot a Player turn could rewrite
                # ``toolchain.test`` to ``true`` and green itself. Captured here,
                # pre-turn-1, from the declaration committed at the worktree's
                # HEAD (what earlier tasks of the feature finished), into the
                # Player-unreachable private dir — and the pinned copy is what
                # executes for the whole build.
                self._snapshot_toolchain_declaration(task_id, worktree)
                # The project's `launch:` block (settings and scratch folders
                # for its commands' shells), pinned at the same point for the
                # same reason. A no-op without one. NOT swallowed: a block
                # that cannot be pinned would send tool caches into the
                # worktree (``launch_declaration``).
                from guardkit.orchestrator.launch_declaration import (
                    snapshot_task_launch,
                )

                snapshot_task_launch(task_id, worktree.path, self.repo_root)

                # Save initial state
                if task_file_path:
                    self._save_state(task_file_path, worktree, "in_progress")

            # The secrets check (a safety fence), built before the first turn
            # from the commit this task starts from; None when it is not on.
            from guardkit.orchestrator.security_check import security_check_command

            self._security_command = security_check_command(
                Path(worktree.path), task_id=task_id, start_commit=resumed_from
            )

            # Project initialisation design (4 October 2026): the reviewer's
            # binding documents are captured once per build from the commit the
            # build started from, and the protected paths' committed content
            # is read. A failure to read either is logged; the task goes on.
            documents_note = self._capture_coach_project_documents(
                task_id,
                worktree,
                resume=bool(self.resume and task_file_path),
                # This orchestrator made the worktree itself: a new build.
                new_build=not (self.resume and task_file_path)
                and self._existing_worktree is None,
            ) or self._load_protected_reference(worktree)
            if documents_note is not None:
                logger.warning("Task %s: %s", task_id, documents_note)

            # Phase 2: Pre-Loop Quality Gates (if enabled)
            if self.enable_pre_loop and not self.resume:
                try:
                    pre_loop_result = self._pre_loop_phase(task_id, worktree)

                    # Check if checkpoint was rejected
                    if not pre_loop_result.get("checkpoint_passed", True):
                        logger.warning(f"Pre-loop checkpoint rejected for {task_id}")
                        # Emit task.failed for pre-loop rejection (TASK-INST-004)
                        self._emit_task_failed(task_id, "pre_loop_blocked")
                        self._capture_build_outcome(
                            task_id,
                            success=False,
                            final_decision="pre_loop_blocked",
                            turn_history=[],
                            task_title=task_title,
                            requirements=requirements,
                            error="Human checkpoint rejected implementation plan",
                        )
                        # Finalize with rejection
                        self._finalize_phase(
                            worktree=worktree,
                            final_decision="pre_loop_blocked",
                            turn_history=[],
                        )
                        return OrchestrationResult(
                            task_id=task_id,
                            success=False,
                            total_turns=0,
                            final_decision="pre_loop_blocked",
                            turn_history=[],
                            worktree=worktree,
                            error="Human checkpoint rejected implementation plan",
                            pre_loop_result=pre_loop_result,
                            ablation_mode=self.ablation_mode,
                            recovery_count=self.recovery_count,
                        )

                    # Update max_turns based on complexity from pre-loop
                    dynamic_max_turns = pre_loop_result.get("max_turns", self.max_turns)
                    if dynamic_max_turns != self.max_turns:
                        logger.info(
                            f"Updating max_turns from {self.max_turns} to {dynamic_max_turns} "
                            f"(based on complexity {pre_loop_result.get('complexity')})"
                        )
                        self.max_turns = dynamic_max_turns
                        # Update progress display with new max_turns
                        self._progress_display = ProgressDisplay(max_turns=dynamic_max_turns)

                except (QualityGateBlocked, CheckpointRejectedError) as e:
                    logger.error(f"Pre-loop quality gate blocked: {e}")
                    # Emit task.failed for quality gate block (TASK-INST-004)
                    self._emit_task_failed(task_id, "pre_loop_blocked")
                    self._capture_build_outcome(
                        task_id,
                        success=False,
                        final_decision="pre_loop_blocked",
                        turn_history=[],
                        task_title=task_title,
                        requirements=requirements,
                        error=str(e),
                    )
                    # Finalize with error
                    self._finalize_phase(
                        worktree=worktree,
                        final_decision="pre_loop_blocked",
                        turn_history=[],
                    )
                    return OrchestrationResult(
                        task_id=task_id,
                        success=False,
                        total_turns=0,
                        final_decision="pre_loop_blocked",
                        turn_history=[],
                        worktree=worktree,
                        error=str(e),
                        pre_loop_result=None,
                        ablation_mode=self.ablation_mode,
                        recovery_count=self.recovery_count,
                    )

            # Phase 3: Loop
            try:
                turn_history, final_decision = self._loop_phase(
                    task_id=task_id,
                    requirements=requirements,
                    acceptance_criteria=acceptance_criteria,
                    worktree=worktree,
                    start_turn=start_turn,
                    task_file_path=task_file_path,
                    implementation_plan=pre_loop_result.get("plan") if pre_loop_result else None,
                    task_type=task_type,
                    requires_infrastructure=requires_infrastructure,
                    consumer_context=consumer_context,
                    time_budget_seconds=time_budget_seconds,
                    behavioural_oracle=behavioural_oracle,  # TS-lane D.1a
                    component=component,  # per-component seam
                )
            finally:
                # 17 October 2026: however the loop ended (an error or
                # cancelled turn never reaches the Coach's check), protected
                # paths are left as committed before anything commits them.
                protected_exit_failure = self._restore_protected_paths(task_id, worktree)
            if protected_exit_failure is not None:
                final_decision = "error"

            # Phase 4: Finalize
            self._finalize_phase(
                worktree=worktree,
                final_decision=final_decision,
                turn_history=turn_history,
            )

            # Save final state.
            if task_file_path:
                status = "in_review" if final_decision == "approved" else "blocked"
                self._save_state(task_file_path, worktree, status)

            success = final_decision == "approved"
            result = OrchestrationResult(
                task_id=task_id,
                success=success,
                total_turns=len(turn_history),
                final_decision=final_decision,
                turn_history=turn_history,
                worktree=worktree,
                error=None
                if success
                else self._build_error_message(final_decision, turn_history),
                pre_loop_result=pre_loop_result,
                ablation_mode=self.ablation_mode,
                recovery_count=self.recovery_count,
            )

            # Emit lifecycle event based on outcome (TASK-INST-004)
            if success:
                self._emit_task_completed(task_id, turn_history)
            else:
                self._emit_task_failed(task_id, final_decision)

            # Memory flywheel: record the outcome — approved or not — so a
            # future gate can read this build back as a prior.
            self._capture_build_outcome(
                task_id,
                success=success,
                final_decision=final_decision,
                turn_history=turn_history,
                task_title=task_title,
                requirements=requirements,
                error=result.error,
            )

            logger.info(
                f"Orchestration complete: {task_id}, decision={final_decision}, "
                f"turns={len(turn_history)}"
            )

            return result

        except RateLimitExceededError as e:
            logger.error(f"Rate limit exceeded for {task_id}: {e}")
            # Emit task.failed with rate_limit category (TASK-INST-004)
            self._emit_task_failed(task_id, "rate_limited")
            # Uses the orchestrator's own turn history: the local name is not
            # guaranteed to be bound when the rate limit fires before Phase 3.
            self._capture_build_outcome(
                task_id,
                success=False,
                final_decision="rate_limited",
                turn_history=list(self._turn_history),
                task_title=task_title,
                requirements=requirements,
                error=f"Rate limit exceeded. Reset time: {e.reset_time or 'unknown'}.",
            )
            # Same reason as the capture above: ``turn_history`` is a local of
            # the try block and is not bound when the rate limit fires before
            # Phase 3. The orchestrator's own copy is always bound.
            _rate_limited_turns = list(self._turn_history)
            return OrchestrationResult(
                task_id=task_id,
                success=False,
                total_turns=len(_rate_limited_turns),
                final_decision="rate_limited",
                turn_history=_rate_limited_turns,
                worktree=worktree,
                error=(
                    f"Rate limit exceeded. Reset time: {e.reset_time or 'unknown'}. "
                    f"Worktree preserved at: {worktree.path}\n"
                    f"Resume with: guardkit autobuild task {task_id} --resume"
                ),
            )
        except SetupPhaseError as e:
            # Setup errors should propagate (can't proceed without worktree).
            # The outcome is written first: a build that could not even get a
            # worktree is exactly the prior a future gate wants to see.
            self._capture_build_outcome(
                task_id,
                success=False,
                final_decision="setup_failed",
                turn_history=list(self._turn_history),
                task_title=task_title,
                requirements=requirements,
                error=f"Setup failed before any turn ran: {e}",
            )
            raise
        except Exception as e:
            logger.error(f"Orchestration failed for {task_id}: {e}", exc_info=True)
            # A build that died mid-flight is the case a future gate most wants
            # to read back, so it is recorded before the crash propagates. The
            # capture never raises, so it cannot mask the original error.
            self._capture_build_outcome(
                task_id,
                success=False,
                final_decision="crashed",
                turn_history=list(self._turn_history),
                task_title=task_title,
                requirements=requirements,
                error=self._crash_outcome_reason(e),
            )
            raise OrchestrationError(f"Orchestration failed: {e}") from e

    def _crash_outcome_reason(self, exc: BaseException) -> str:
        """Why this build crashed — and which terminal, if any, it supersedes.

        A build can reach a terminal, write that outcome, and THEN die on the
        way out (the pass-bar refusal whose ``_finalize_phase`` throws is the
        real case). Memory then holds two records for one build. Read cold they
        look like two unrelated builds; the second is the truthful one and the
        first is the terminal it overtook, and nothing on the record said so.

        This names it, so the crash record carries its own predecessor:
        ``"... crashed after the 'qa_precondition_blocked' terminal had already
        been recorded ..."``. The line rides ``error``, which the capture seam
        puts into both the summary and the single lessons line — the field the
        writer's payload actually keeps.

        A plain crash (nothing recorded before it) reads exactly as it always
        did: nothing is invented to name.
        """
        return (
            f"Orchestration crashed: {type(exc).__name__}: {exc}"
            + self._superseded_terminal_note()
        )

    def _superseded_terminal_note(self) -> str:
        """The clause naming the terminal a crash overtakes, or "" if none."""
        superseded = self._last_captured_terminal
        if not superseded:
            return ""
        return (
            f" — this build crashed after the '{superseded}' terminal had "
            f"already been recorded, so this record supersedes that one."
        )

    def _snapshot_toolchain_declaration(
        self, task_id: str, worktree: "Worktree"
    ) -> None:
        """TS-lane D.1b: pin the repo's toolchain declaration pre-turn-1.

        Reads ``toolchain:`` from the ``.guardkit/config.yaml`` committed at
        the worktree's HEAD (the ``<repo_root>`` copy only when the worktree is
        not a git checkout), so a feature task runs the tests an earlier task
        of the feature declared, and writes it into the task-private dir
        (outside the shared worktree). ``CoachValidator`` reads only that snapshot, so the
        model can never edit its own test command mid-build (design §B.4 —
        "if the snapshot is cut from scope, the declaration must be cut with
        it").

        A no-op (writes nothing) for every repo without a ``toolchain:``
        block, so existing builds stay byte-equivalent. Never raises.

        The pinned ``language_servers`` are also kept in memory for the task,
        read at this same moment, before any builder turn (29 October 2026).
        The agent invoker passes them to the builder's ``code_references``, so
        an edit to the snapshot file, which sits in a folder the builder can
        write, changes nothing for this run (the builder tools
        design of 29 October 2026).
        """
        language_servers = None
        try:
            from guardkit.orchestrator.toolchain_declaration import (
                load_toolchain_snapshot,
                snapshot_task_toolchain,
            )

            pinned = snapshot_task_toolchain(
                task_id=task_id,
                worktree_path=worktree.path,
                repo_root=self.repo_root,
            )
            if pinned is not None:
                declaration = load_toolchain_snapshot(task_id, worktree.path)
                if declaration is not None:
                    language_servers = declaration.language_servers
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "TS-lane D.1b: toolchain snapshot failed for %s (%s) — the "
                "declaration will be absent for this task",
                task_id,
                exc,
            )
        invoker = getattr(self, "_agent_invoker", None)
        if invoker is not None:
            invoker.pin_language_servers(task_id, language_servers)

    @property
    def real_check_failed(self) -> bool:
        """Whether the project's own tests are still red for this task: their
        last measurement failed and no later measurement passed (step 1, 24
        October 2026)."""
        return any(getattr(self, "_measured_check_failed", {}).values())

    def _carry_measured_checks(
        self,
        independent: Optional["IndependentTestResult"],
    ) -> None:
        """Carry this turn's measured test result, as the Coach's evidence
        produced it (step 1, 24 October 2026).

        Tests fail on the independent run's own failure receipt and clear
        only on a later independent run that ran and passed. An absent
        result changes nothing.
        """
        try:
            self._carry_measured_checks_now(independent)
        except Exception as exc:  # noqa: BLE001 — carrying a result never ends a turn
            logger.warning("Could not carry this turn's check results: %s", exc)

    def _carry_measured_checks_now(
        self,
        independent: Optional["IndependentTestResult"],
    ) -> None:
        state = self.__dict__.setdefault("_measured_check_failed", {})
        if independent is not None and independent.failure_receipt() is not None:
            state["tests"] = True
        elif (
            independent is not None
            and independent.tests_passed is True
            and not independent.signal_absent
            and not independent.check_could_not_run
            and independent.test_command != "skipped"
        ):
            state["tests"] = False

    def _resolve_task_component(
        self, task_id: str, raw: Any
    ) -> Optional[str]:
        """PER-COMPONENT SEAM: the task's ``component:`` selector, or ``None``.

        ``None`` means the root component. A name the repository's
        ``toolchain.components`` does not declare also means the root
        component.
        """
        if not isinstance(raw, str) or not raw.strip():
            return None
        name = raw.strip()

        from guardkit.orchestrator.toolchain_declaration import (
            load_toolchain_declaration,
        )

        declaration = load_toolchain_declaration(self.repo_root)
        if declaration is None or declaration.component(name) is None:
            logger.warning(
                "Task %s selects `component: %s`, which the repository does "
                "not declare; the root component is used.",
                task_id, name,
            )
            return None
        logger.info(
            "Task %s selects component %r (cwd=%r, test=%r)",
            task_id,
            name,
            declaration.component(name).cwd,
            declaration.component(name).test,
        )
        return name

    def _setup_phase(
        self,
        task_id: str,
        base_branch: str,
    ) -> Worktree:
        """
        Phase 1: Create isolated workspace and initialize progress.

        This phase establishes the isolated environment for Player/Coach
        agent iterations.

        Steps
        -----
        1. Create git worktree via WorktreeManager (or use existing if provided)
        2. Initialize AgentInvoker with worktree path (lazy initialization)
        3. Log setup confirmation

        Parameters
        ----------
        task_id : str
            Task identifier
        base_branch : str
            Branch to create worktree from

        Returns
        -------
        Worktree
            Created or existing Worktree instance

        Raises
        ------
        SetupPhaseError
            If worktree creation fails

        Notes
        -----
        ProgressDisplay is managed as context manager in loop phase to guarantee
        cleanup even if later phases fail.

        If existing_worktree is provided (feature mode), that worktree is used
        instead of creating a new one. This enables multiple tasks to share
        a single worktree (TASK-FBC-001).
        """
        logger.info(f"Phase 1 (Setup): Creating worktree for {task_id}")

        try:
            # Use existing worktree if provided (feature mode)
            if self._existing_worktree is not None:
                logger.info(
                    f"Using existing worktree for {task_id}: {self._existing_worktree.path}"
                )
                worktree = self._existing_worktree

                # Initialize AgentInvoker with worktree path
                if self._agent_invoker is None:
                    self._agent_invoker = AgentInvoker(
                        worktree_path=worktree.path,
                        max_turns_per_agent=self.max_turns,
                        development_mode=self.development_mode,
                        sdk_timeout_seconds=self.sdk_timeout,
                        sdk_timeout_is_override=self._sdk_timeout_is_override,
                        use_task_work_delegation=True,
                        cancellation_event=self._cancellation_event,  # TASK-FIX-ASPF-004
                        timeout_multiplier=self.timeout_multiplier,  # TASK-FIX-VL05
                        venv_python=self._venv_python,  # TASK-FIX-7A05
                        model_name=self._model_name,  # TASK-FIX-MODELPLUMB
                        coach_model_name=self._coach_model_name,  # TASK-FIX-COACHBUDG01
                        evidence_repos=self._evidence_repos,  # TASK-AB-XREPOEV01
                        emitter=self._emitter,  # TASK-OBS-4899
                    )
                # TASK-FIX-OBS2: Attach progress logger to agent invoker
                if self._progress_logger and self._agent_invoker:
                    self._agent_invoker.set_progress_logger(self._progress_logger)

                # When other tasks of this wave change the working copy at the
                # same time, a report the invoker builds from git must not
                # count as this task's evidence (FEAT-2C42).
                if self._agent_invoker is not None:
                    self._agent_invoker.shared_working_copy = self.shares_working_copy

                return worktree

            # Create isolated worktree (normal mode)
            worktree = self._worktree_manager.create(
                task_id=task_id,
                base_branch=base_branch,
            )

            logger.info(f"Worktree created: {worktree.path}")

            # Prune non-essential rules to reduce context size (TASK-daab)
            self._prune_worktree_rules(worktree.path)

            # Initialize AgentInvoker with worktree path (lazy initialization)
            if self._agent_invoker is None:
                self._agent_invoker = AgentInvoker(
                    worktree_path=worktree.path,
                    max_turns_per_agent=self.max_turns,
                    development_mode=self.development_mode,
                    sdk_timeout_seconds=self.sdk_timeout,
                    sdk_timeout_is_override=self._sdk_timeout_is_override,
                    use_task_work_delegation=True,
                    cancellation_event=self._cancellation_event,  # TASK-FIX-ASPF-004
                    venv_python=self._venv_python,  # TASK-FIX-7A05
                    model_name=self._model_name,  # TASK-FIX-MODELPLUMB
                    coach_model_name=self._coach_model_name,  # TASK-FIX-COACHBUDG01
                    evidence_repos=self._evidence_repos,  # TASK-AB-XREPOEV01
                    emitter=self._emitter,  # TASK-OBS-4899
                )
            # TASK-FIX-OBS2: Attach progress logger to agent invoker
            if self._progress_logger and self._agent_invoker:
                self._agent_invoker.set_progress_logger(self._progress_logger)

            return worktree

        except WorktreeCreationError as e:
            logger.error(f"Setup phase failed: {e}")
            raise SetupPhaseError(f"Failed to create worktree: {e}") from e

    def _prune_worktree_rules(self, worktree_path: Path) -> None:
        """Remove non-essential rules from AutoBuild worktree to reduce context.

        AutoBuild loads all `.claude/rules/` files via the SDK's
        ``setting_sources=["project"]``.  Only ~17 KB of the ~63 KB total is
        relevant to autonomous code generation.  This method removes the rest,
        freeing ~11.5K tokens per Player/Coach turn.

        The pruning is safe because git worktrees have independent working
        trees — removing files here does NOT affect the main branch.

        Parameters
        ----------
        worktree_path : Path
            Filesystem path to the worktree root directory.
        """
        rules_dir = worktree_path / ".claude" / "rules"
        if not rules_dir.is_dir():
            logger.debug("No .claude/rules/ directory in worktree — skipping prune")
            return

        # Build the set of rules to keep
        keep = set(AUTOBUILD_ESSENTIAL_RULES)
        if self._existing_worktree is not None:
            # Feature-build mode: keep feature-build-invariants.md too
            keep |= FEATURE_BUILD_EXTRA_RULES

        removed_count = 0
        for item in list(rules_dir.iterdir()):
            if item.is_dir():
                shutil.rmtree(item)
                removed_count += 1
                logger.debug(f"Pruned rules directory: {item.name}/")
            elif item.name not in keep:
                item.unlink()
                removed_count += 1
                logger.debug(f"Pruned rule file: {item.name}")

        if removed_count > 0:
            remaining = [f.name for f in rules_dir.iterdir() if f.is_file()]
            logger.info(
                f"Pruned {removed_count} non-essential rules from worktree "
                f"(kept {len(remaining)}: {', '.join(sorted(remaining))})"
            )

    def _pre_loop_phase(
        self,
        task_id: str,
        worktree: Worktree,
    ) -> Dict[str, Any]:
        """
        Phase 2: Execute pre-loop quality gates via task-work delegation.

        This phase delegates to task-work --design-only to execute all design
        phases, achieving 100% code reuse of existing quality gates.

        Quality Gates Executed (via task-work --design-only)
        ----------------------------------------------------
        - Phase 1.6: Clarifying Questions
        - Phase 2: Implementation Planning
        - Phase 2.5A: Pattern Suggestions (if MCP available)
        - Phase 2.5B: Architectural Review (SOLID/DRY/YAGNI)
        - Phase 2.7: Complexity Evaluation
        - Phase 2.8: Human Checkpoint

        Parameters
        ----------
        task_id : str
            Task identifier
        worktree : Worktree
            Worktree for execution context

        Returns
        -------
        Dict[str, Any]
            Pre-loop results containing:
            - plan: Implementation plan from Phase 2
            - plan_path: Path to saved plan file
            - complexity: Complexity score (1-10)
            - max_turns: Recommended max turns based on complexity
            - checkpoint_passed: Whether Phase 2.8 approved
            - architectural_score: SOLID/DRY/YAGNI overall score

        Raises
        ------
        QualityGateBlocked
            If architectural review score is too low
        CheckpointRejectedError
            If human checkpoint rejects the design

        Notes
        -----
        This phase implements Option D (per TASK-REV-0414): Thin delegation
        layer that achieves 100% code reuse without reimplementing quality gates.
        """
        logger.info(f"Phase 2 (Pre-Loop): Executing quality gates for {task_id}")

        # Initialize pre-loop gates if not injected (lazy initialization)
        if self._pre_loop_gates is None:
            self._pre_loop_gates = PreLoopQualityGates(
                str(worktree.path),
                sdk_timeout=self.sdk_timeout,
                skip_arch_review=self.skip_arch_review,
            )

        # Execute pre-loop quality gates via task-work delegation
        # The execute() method is async, so we run it in an event loop
        result = asyncio.run(self._pre_loop_gates.execute(task_id, self.pre_loop_options))

        logger.info(
            f"Pre-loop complete: complexity={result.complexity}, "
            f"max_turns={result.max_turns}, checkpoint_passed={result.checkpoint_passed}"
        )

        # Convert PreLoopResult dataclass to dict for compatibility
        return {
            "plan": result.plan,
            "plan_path": result.plan_path,
            "complexity": result.complexity,
            "max_turns": result.max_turns,
            "checkpoint_passed": result.checkpoint_passed,
            "architectural_score": result.architectural_score,
            "clarifications": result.clarifications,
        }

            # Non-critical failure - don't raise

    def _extract_design_phase(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        task_file_path: Optional[Path] = None,
    ) -> Optional[DesignContext]:
        """
        Phase 0: Extract design data from Figma or Zeplin via MCP.

        This phase runs before pre-loop quality gates when a task has a
        `design_url` in its frontmatter. It extracts design information
        and makes it available as context for the Player-Coach loop.

        Phase 0 Execution Steps
        -----------------------
        0.1: Verify required MCP tools available (fail fast)
        0.2: Extract design data via DesignExtractor
        0.3: Store extraction metadata (timestamp, hash) in task frontmatter
        0.4: Return DesignContext for downstream use

        Parameters
        ----------
        task_id : str
            Task identifier
        task_data : Dict[str, Any]
            Task data including frontmatter
        task_file_path : Optional[Path]
            Path to task file for metadata storage

        Returns
        -------
        Optional[DesignContext]
            DesignContext if design_url present and extraction succeeded,
            None if no design_url (backward compatible)

        Raises
        ------
        DesignExtractionPhaseError
            If MCP unavailable or extraction fails

        Notes
        -----
        This phase is completely skipped for tasks without design_url,
        ensuring backward compatibility with non-design tasks.
        """
        frontmatter = task_data.get("frontmatter", {})
        design_url = frontmatter.get("design_url")

        # Skip Phase 0 entirely if no design_url present (backward compatible)
        if not design_url:
            logger.debug(f"Phase 0 skipped for {task_id}: no design_url in frontmatter")
            return None

        logger.info(f"Phase 0 (Design Extraction): Starting for {task_id}")
        logger.debug(f"Design URL: {design_url}")

        # Phase 0.1: Detect design source and verify MCP availability
        source = self._detect_design_source(design_url)
        if source is None:
            raise DesignExtractionPhaseError(
                f"Unrecognized design URL format: {design_url}. "
                "Expected Figma (figma.com) or Zeplin (zeplin.io) URL.",
                source="unknown",
                reason="unrecognized_url_format",
            )

        # Initialize DesignExtractor (lazy initialization)
        if not hasattr(self, "_design_extractor") or self._design_extractor is None:
            self._design_extractor = DesignExtractor()

        # Verify MCP tools are available (fail fast)
        if not self._design_extractor.verify_mcp_availability(source):
            raise DesignExtractionPhaseError(
                f"{source.title()} MCP tools not available. "
                f"Enable in claude_desktop_config.json. "
                f"Required tools: {self._design_extractor.FIGMA_MCP_TOOLS if source == 'figma' else self._design_extractor.ZEPLIN_MCP_TOOLS}",
                source=source,
                reason="mcp_unavailable",
            )

        logger.info(f"Phase 0.1: MCP tools verified for {source}")

        # Phase 0.2: Extract design data
        try:
            design_data = self._extract_design_data(source, design_url)
        except Exception as e:
            raise DesignExtractionPhaseError(
                f"Design extraction failed for {design_url}: {e}",
                source=source,
                reason="extraction_failed",
            ) from e

        logger.info(f"Phase 0.2: Design data extracted from {source}")

        # Generate summary for agent context (~3K tokens)
        summary = self._design_extractor.summarize_design_data(design_data)

        # Build DesignContext
        design_context = DesignContext(
            elements=design_data.elements,
            tokens=design_data.tokens,
            constraints=self._build_design_constraints(design_data),
            visual_reference=design_data.visual_reference,
            summary=summary,
            source=source,
            metadata={
                **design_data.metadata,
                "design_url": design_url,
            },
        )

        # Phase 0.3: Store extraction metadata in task frontmatter
        if task_file_path and task_file_path.exists():
            self._store_extraction_metadata(
                task_file_path, design_context, design_data
            )
            logger.info(f"Phase 0.3: Extraction metadata stored in {task_file_path}")

        logger.info(f"Phase 0.4: DesignContext created for {task_id}")

        return design_context

    def _detect_design_source(self, design_url: str) -> Optional[str]:
        """
        Detect design source (Figma or Zeplin) from URL.

        Parameters
        ----------
        design_url : str
            Design URL to analyze

        Returns
        -------
        Optional[str]
            'figma' or 'zeplin', or None if unrecognized
        """
        if "figma.com" in design_url or "figma.design" in design_url:
            return "figma"
        elif "zeplin.io" in design_url or "app.zeplin.io" in design_url:
            return "zeplin"
        return None

    def _extract_design_data(self, source: str, design_url: str) -> DesignData:
        """
        Extract design data from URL via appropriate MCP.

        Parameters
        ----------
        source : str
            Design source ('figma' or 'zeplin')
        design_url : str
            Full design URL

        Returns
        -------
        DesignData
            Extracted design data

        Raises
        ------
        DesignExtractionPhaseError
            If URL parsing or extraction fails
        """
        if source == "figma":
            file_key, node_id = self._parse_figma_url(design_url)
            return asyncio.run(self._design_extractor.extract_figma(file_key, node_id))
        elif source == "zeplin":
            project_id, screen_id = self._parse_zeplin_url(design_url)
            return asyncio.run(self._design_extractor.extract_zeplin(project_id, screen_id))
        else:
            raise DesignExtractionPhaseError(
                f"Unsupported design source: {source}",
                source=source,
                reason="unsupported_source",
            )

    def _parse_figma_url(self, url: str) -> Tuple[str, str]:
        """
        Parse Figma URL to extract file_key and node_id.

        Supports formats:
        - https://www.figma.com/file/{file_key}?node-id={node_id}
        - https://www.figma.com/design/{file_key}?node-id={node_id}
        - https://figma.com/file/{file_key}/{name}?node-id={node_id}

        Parameters
        ----------
        url : str
            Figma URL

        Returns
        -------
        Tuple[str, str]
            (file_key, node_id) in colon format

        Raises
        ------
        DesignExtractionPhaseError
            If URL cannot be parsed
        """
        # Extract file key from path
        file_key_match = re.search(r"/(?:file|design)/([a-zA-Z0-9]+)", url)
        if not file_key_match:
            raise DesignExtractionPhaseError(
                f"Could not extract file_key from Figma URL: {url}",
                source="figma",
                reason="invalid_url",
            )
        file_key = file_key_match.group(1)

        # Extract node-id from query params
        node_id_match = re.search(r"node-id=([0-9:-]+)", url)
        if not node_id_match:
            raise DesignExtractionPhaseError(
                f"Could not extract node-id from Figma URL: {url}. "
                "Include ?node-id=X:Y in the URL.",
                source="figma",
                reason="missing_node_id",
            )
        node_id = node_id_match.group(1)

        # Convert dash format to colon format (URL uses dash, MCP uses colon)
        node_id = node_id.replace("-", ":")

        return file_key, node_id

    def _parse_zeplin_url(self, url: str) -> Tuple[str, str]:
        """
        Parse Zeplin URL to extract project_id and screen_id.

        Supports formats:
        - https://app.zeplin.io/project/{project_id}/screen/{screen_id}
        - https://zeplin.io/project/{project_id}/screen/{screen_id}

        Parameters
        ----------
        url : str
            Zeplin URL

        Returns
        -------
        Tuple[str, str]
            (project_id, screen_id)

        Raises
        ------
        DesignExtractionPhaseError
            If URL cannot be parsed
        """
        # Extract project_id
        project_match = re.search(r"/project/([a-zA-Z0-9-]+)", url)
        if not project_match:
            raise DesignExtractionPhaseError(
                f"Could not extract project_id from Zeplin URL: {url}",
                source="zeplin",
                reason="invalid_url",
            )
        project_id = project_match.group(1)

        # Extract screen_id
        screen_match = re.search(r"/screen/([a-zA-Z0-9-]+)", url)
        if not screen_match:
            raise DesignExtractionPhaseError(
                f"Could not extract screen_id from Zeplin URL: {url}. "
                "Include /screen/{screen_id} in the URL.",
                source="zeplin",
                reason="missing_screen_id",
            )
        screen_id = screen_match.group(1)

        return project_id, screen_id

    def _build_design_constraints(self, design_data: DesignData) -> Dict[str, bool]:
        """
        Build prohibition checklist from design data.

        This checklist helps agents avoid common design compliance issues.

        Parameters
        ----------
        design_data : DesignData
            Extracted design data

        Returns
        -------
        Dict[str, bool]
            Constraint checklist (True = constraint applies)
        """
        # Default constraints (all False = no restrictions)
        constraints = {
            "no_shadcn_icons": False,
            "no_radix_icons": False,
            "no_lucide_icons": False,
            "no_heroicons": False,
            "custom_colors_only": False,
            "custom_spacing_only": False,
            "no_tailwind_defaults": False,
            "exact_typography": False,
            "no_animations": False,
            "no_transitions": False,
            "accessibility_required": False,
            "dark_mode_required": False,
        }

        # Infer constraints from design tokens
        if design_data.tokens.get("colors"):
            constraints["custom_colors_only"] = True

        if design_data.tokens.get("spacing"):
            constraints["custom_spacing_only"] = True

        if design_data.tokens.get("typography"):
            constraints["exact_typography"] = True

        return constraints

    def _store_extraction_metadata(
        self,
        task_file_path: Path,
        design_context: DesignContext,
        design_data: DesignData,
    ) -> None:
        """
        Store extraction metadata in task frontmatter.

        Writes timestamp and hash to enable cache invalidation
        and extraction tracking.

        Parameters
        ----------
        task_file_path : Path
            Path to task markdown file
        design_context : DesignContext
            Extracted design context
        design_data : DesignData
            Raw design data for hash calculation
        """
        try:
            content = task_file_path.read_text()

            # Parse frontmatter
            if not content.startswith("---"):
                logger.warning("Task file missing frontmatter, skipping metadata storage")
                return

            parts = content.split("---", 2)
            if len(parts) < 3:
                logger.warning("Invalid task file format, skipping metadata storage")
                return

            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2]

            # Calculate content hash for cache invalidation
            content_hash = hashlib.sha256(
                design_data.to_json().encode()
            ).hexdigest()[:16]

            # Add design_extraction metadata
            frontmatter["design_extraction"] = {
                "extracted_at": datetime.now().isoformat(),
                "design_hash": content_hash,
                "source": design_context.source,
                "elements_count": len(design_context.elements),
                "tokens_count": len(design_context.tokens),
            }

            # Write updated file
            new_content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---{body}"
            task_file_path.write_text(new_content)

        except Exception as e:
            logger.warning(f"Failed to store extraction metadata: {e}")

    def _loop_phase(
        self,
        task_id: str,
        requirements: str,
        acceptance_criteria: List[str],
        worktree: Worktree,
        start_turn: int = 1,
        task_file_path: Optional[Path] = None,
        implementation_plan: Optional[Dict[str, Any]] = None,
        task_type: Optional[str] = None,
        requires_infrastructure: Optional[List[str]] = None,
        consumer_context: Optional[list] = None,
        time_budget_seconds: Optional[float] = None,
        behavioural_oracle: Optional[Any] = None,
        component: Optional[str] = None,  # per-component seam
    ) -> Tuple[List[TurnRecord], Literal["approved", "max_turns_exceeded", "error", "cancelled", "timeout", "design_extraction_failed", "timeout_budget_exhausted"]]:
        """
        Phase 3: Execute Player↔Coach adversarial loop.

        This phase implements the core adversarial workflow where Player
        implements and Coach validates, iterating until approval or max_turns.

        Loop Structure
        --------------
        - Turn 1: Player implements from scratch — or, when the tree already
          satisfies every acceptance criterion, says so and cites where
        - Turn 2+: Player addresses Coach feedback
        - Exit: Coach approves OR the Coach verifies an "already there" claim
          OR max_turns exceeded OR critical error OR cancelled

        Parameters
        ----------
        task_id : str
            Task identifier
        requirements : str
            Task requirements
        acceptance_criteria : List[str]
            Acceptance criteria
        worktree : Worktree
            Isolated workspace
        start_turn : int, optional
            Turn to start from (default: 1, used for resume)
        task_file_path : Optional[Path], optional
            Path to task file for state persistence
        task_type : Optional[str], optional
            Task type from task frontmatter (e.g., "implementation", "refactor", "bugfix")
        requires_infrastructure : Optional[List[str]], optional
            Infrastructure services required (e.g., ["postgresql", "redis"])
        consumer_context : Optional[list], optional
            Consumer context metadata from task frontmatter for format validation
        behavioural_oracle : Optional[Any], optional
            Resolved behavioural-oracle declaration (TS-lane D.1a)

        Returns
        -------
        Tuple[List[TurnRecord], Literal["approved", "max_turns_exceeded", "error", "design_extraction_failed"]]
            Tuple of (turn_history, final_decision)

        Decision Logic
        --------------
        - "approved": Coach approved, ready for human review
        - "max_turns_exceeded": Loop limit reached
        - "error": Critical error occurred
        - "cancelled": Cooperative cancellation via threading.Event (TASK-ASF-007)

        Notes
        -----
        Player errors are recorded but don't stop the loop (Coach can provide
        guidance). Coach errors or SDK timeouts cause immediate loop exit.
        """
        logger.info(f"Phase 2 (Loop): Starting adversarial turns for {task_id} from turn {start_turn}")

        # TASK-RFX-5FED: Store worktree path for local turn state file access
        self._active_worktree_path = worktree.path

        # Why a checkpoint was refused, when one was (build 0D7C).
        self._checkpoint_refusal: Optional[str] = None
        # Why protected paths could not be put back, when they could not.
        self._protected_paths_failure: Optional[str] = None

        # Track loop start time for SDK-level timeout remaining budget (TASK-ABFIX-006)
        loop_start = time.monotonic()

        # Use existing turn history if resuming
        turn_history: List[TurnRecord] = list(self._turn_history)
        # TASK-AB-COACHRUNPARITY01 (arm a): on a fresh (non-resume) task the
        # turn-1 feedback is the smoke-gate seed (None for normal tasks). On a
        # smoke-feedback re-run the feature orchestrator constructs this
        # orchestrator with seed_feedback set, so the Player's first turn sees
        # the runtime failure the Coach's pytest missed. Perspective reset only
        # fires at turns [3, 5] (_should_reset_perspective), so a turn-1 seed
        # always survives to the Player invocation below.
        previous_feedback: Optional[str] = (
            self._get_last_feedback() if self.resume else self._seed_feedback
        )
        # Gate-driven repair round (20 October 2026): the plan audit and the
        # Coach prompt read it from the invoker; set for every loop, so an
        # ordinary task's invoker never carries another task's round.
        if self._agent_invoker is not None:
            self._agent_invoker.repair_round = self._repair_round_for_this_loop(task_id)

        # Initialize checkpoint manager if enabled
        if self.enable_checkpoints and self._checkpoint_manager is None:
            from guardkit.orchestrator.head_identity import (
                expected_checkpoint_branch,
            )

            self._checkpoint_manager = WorktreeCheckpointManager(
                worktree_path=worktree.path,
                task_id=task_id,
                evidence_repos=self._evidence_repos,  # TASK-AB-XREPOEV01 (AC-004)
                # Build 0D7C (12 October 2026): every checkpoint must land on
                # the feature branch; never commit on a detached HEAD.
                expected_branch=(
                    self._expected_branch
                    if self._expected_branch_pinned
                    else expected_checkpoint_branch(
                        getattr(worktree, "path", None),
                        getattr(worktree, "branch_name", None),
                    )
                ),
                refuse_without_branch=True,
                task_work_scope=self.task_work_scope,
            )
            logger.info(f"Checkpoint manager initialized for {task_id}")

        # 17 October 2026 (review R1): protected paths — worktree, index and
        # branch — are put back as committed under the checkpoint lock just
        # before each checkpoint's ``git add``, whatever ran since the turn's
        # own check (the Coach, another task in the wave, a shell commit).
        if (
            self._checkpoint_manager is not None
            and getattr(self, "_protected_reference", None) is not None
        ):
            def _protected_before_commit() -> None:
                failure = self._restore_protected_paths(task_id, worktree)
                if failure is not None:
                    raise CheckpointRefused(
                        failure, expected_branch="", actual_ref=None,
                        head="unknown", branch_tip=None,
                    )

            def _protected_after_stage() -> None:
                # ``git add`` can convert protected bytes through attributes
                # (text, eol, ident, an encoding): the index part again, after
                # staging and before the commit (review R1 round 3).
                from guardkit.orchestrator.protected_paths import (
                    ProtectedPathsError,
                    hold_protected_index,
                )

                try:
                    held = hold_protected_index(
                        Path(worktree.path), self._protected_reference
                    )
                except ProtectedPathsError as exc:
                    self._protected_paths_failure = f"Task {task_id} stopped: {exc}"
                    raise CheckpointRefused(
                        self._protected_paths_failure, expected_branch="",
                        actual_ref=None, head="unknown", branch_tip=None,
                    ) from exc
                if held:
                    logger.warning(
                        "[%s] Staging changed protected paths %s; their committed "
                        "entries were put back before the checkpoint commit.",
                        task_id, ", ".join(held),
                    )

            self._checkpoint_manager.before_commit = _protected_before_commit
            self._checkpoint_manager.after_stage = _protected_after_stage

        # Track loop start time for per-turn budget (TASK-ABFIX-004)
        loop_start_time: Optional[float] = time.monotonic() if time_budget_seconds is not None else None

        with self._progress_display:
            for turn in range(start_turn, self.max_turns + 1):

                # Cooperative cancellation check at TOP of loop (TASK-ASF-007)
                # Check timeout_event first — feature-level timeout takes priority (TASK-ABFIX-006)
                if self._timeout_event and self._timeout_event.is_set():
                    logger.info(
                        f"[{task_id}] TIMEOUT (feature-level): task_timeout={self._task_timeout}s expired "
                        f"at turn {turn} (before Player phase). "
                        f"SDK timeout budget was {self.sdk_timeout}s per invocation."
                    )
                    return turn_history, "timeout"
                if self._cancellation_event and self._cancellation_event.is_set():
                    logger.info(
                        f"[{task_id}] CANCELLED: cancellation_event set by wave coordinator "
                        f"(stop_on_failure) at turn {turn} (before Player phase)."
                    )
                    return turn_history, "cancelled"

                # Per-turn budget check (TASK-ABFIX-004)
                if time_budget_seconds is not None and loop_start_time is not None:
                    elapsed = time.monotonic() - loop_start_time
                    remaining_budget: Optional[float] = time_budget_seconds - elapsed
                    if remaining_budget < MIN_TURN_BUDGET_SECONDS:
                        logger.info(
                            f"Timeout budget exhausted for {task_id} at turn {turn}: "
                            f"remaining={remaining_budget:.1f}s < min={MIN_TURN_BUDGET_SECONDS}s"
                        )
                        # Capture the remaining budget so the finalize-phase
                        # summary/error builders can report the precise
                        # "remaining=<X>s < min=<MIN>s" cause (TASK-FIX-TBXMSG01).
                        self._timeout_budget_remaining = remaining_budget
                        return turn_history, "timeout_budget_exhausted"
                else:
                    remaining_budget = None

                logger.info(f"Executing turn {turn}/{self.max_turns}")

                # TASK-OBS-9F43 AC-2, AC-3: Thread run_id and current attempt to AgentInvoker
                # so llm.call and tool.exec events join with lifecycle events by run_id
                if self._agent_invoker is not None:
                    self._agent_invoker._run_id = self._run_id
                    self._agent_invoker._current_attempt = turn

                # Check if perspective should be reset to prevent anchoring bias
                # When reset triggered, Player receives only original requirements (no feedback)
                if self._should_reset_perspective(turn):
                    # All review feedback is dropped, as before, except the
                    # previous turn's timeout must-fix: a timeout is a fact
                    # about how that turn ran, not review content that could
                    # anchor the Player (FEAT-2C42: TASK-2C42-003 timed out
                    # on turn 2 and turn 3 was a reset turn). On a resumed
                    # run the history is the saved one, so this holds there
                    # too.
                    previous_feedback = (
                        getattr(turn_history[-1], "timeout_note", None)
                        if turn_history
                        else None
                    )
                    # TASK-RFX-B20B: Also clear session to avoid carrying
                    # prior context that perspective reset is meant to discard
                    if self._agent_invoker is not None:
                        self._agent_invoker.set_player_resume_session(None)

                # Execute single turn
                # Skip arch review when pre-loop is disabled (implement-only mode)
                # because Phase 2.5B (Architectural Review) doesn't run
                try:
                    turn_record = self._execute_turn(
                        turn=turn,
                        task_id=task_id,
                        requirements=requirements,
                        worktree=worktree,
                        previous_feedback=previous_feedback,
                        task_type=task_type,
                        skip_arch_review=not self.enable_pre_loop,
                        acceptance_criteria=acceptance_criteria,
                        requires_infrastructure=requires_infrastructure,
                        consumer_context=consumer_context,
                        remaining_budget=remaining_budget,
                        behavioural_oracle=behavioural_oracle,  # TS-lane D.1a
                        component=component,  # per-component seam
                    )
                finally:
                    # The Player-phase measurement never outlives its turn.
                    self._set_progress_files_measure(None)

                turn_history.append(turn_record)
                self._turn_history = turn_history  # Keep internal copy for state

                # TASK-RFX-B20B: Update session_id on AgentInvoker for next turn
                # The invoker reads _last_session_id internally when building
                # ClaudeAgentOptions, so we just set it after each turn.
                if (
                    self._agent_invoker is not None
                    and turn_record.player_result is not None
                    and turn_record.player_result.session_id is not None
                ):
                    self._agent_invoker.set_player_resume_session(
                        turn_record.player_result.session_id
                    )

                # Cooperative cancellation check after turn (TASK-ASF-007)
                # If event was set during _execute_turn (between Player/Coach),
                # the turn returns "error" — convert to "cancelled"/"timeout" exit
                # Skip if Coach approved during grace period — approval takes priority (TASK-ABFIX-004)
                # Check timeout_event first — feature-level timeout takes priority (TASK-ABFIX-006)
                if turn_record.decision != "approve":
                    if self._timeout_event and self._timeout_event.is_set():
                        logger.info(
                            f"[{task_id}] TIMEOUT (feature-level): task_timeout={self._task_timeout}s expired "
                            f"after turn {turn}. "
                            f"SDK timeout budget was {self.sdk_timeout}s per invocation."
                        )
                        return turn_history, "timeout"
                    if self._cancellation_event and self._cancellation_event.is_set():
                        logger.info(
                            f"[{task_id}] CANCELLED: cancellation_event set by wave coordinator "
                            f"(stop_on_failure) after turn {turn}."
                        )
                        return turn_history, "cancelled"

                # Detect SDK-level timeout and log layer attribution (TASK-ABFIX-006)
                if (
                    turn_record.player_result
                    and turn_record.player_result.error
                    and "SDK timeout" in turn_record.player_result.error
                    and self._task_timeout
                ):
                    elapsed = int(time.monotonic() - loop_start)
                    remaining = max(0, self._task_timeout - elapsed)
                    # The invoker scales the base limit per task (mode and
                    # complexity) and states the limit it applied in the
                    # error. Build FEAT-D31F's turn ran under 4,860 s and
                    # this line said "sdk_timeout=1800s", the base
                    # (19 October 2026).
                    applied = _applied_sdk_timeout_seconds(
                        turn_record.player_result.error
                    )
                    if applied is not None:
                        limit_said = (
                            f"sdk_timeout={applied}s expired (base "
                            f"{self.sdk_timeout}s, scaled for this task)"
                        )
                    else:
                        limit_said = (
                            f"SDK timeout expired (base sdk_timeout="
                            f"{self.sdk_timeout}s; applied limit not recorded)"
                        )
                    logger.info(
                        f"[{task_id}] TIMEOUT (SDK-level): {limit_said} "
                        f"during turn {turn}. Feature task had {remaining}s remaining of its "
                        f"{self._task_timeout}s budget."
                    )


                # Capture turn state for cross-turn learning (TASK-GE-002, TASK-RFX-5FED)
                self._capture_turn_state(
                    turn_record, acceptance_criteria,
                    task_id=task_id, worktree_path=worktree.path,
                )

                # Display criteria progress after each turn.
                # Wrap in try/except: this is a display-only helper and must
                # never fail a task. Previously a parse error inside
                # _display_criteria_progress (e.g. unknown VerificationResult
                # value from the Coach) bubbled up to orchestrate() and
                # marked the task 'error', halting stop_on_failure runs.
                # See TASK-REV-9A4B post-mortem.
                try:
                    self._display_criteria_progress(turn_record, acceptance_criteria)
                except Exception:
                    logger.exception(
                        "[%s] _display_criteria_progress failed; continuing turn "
                        "(this is a display-only helper)",
                        task_id,
                    )

                # Persist state after each turn
                if task_file_path:
                    self._save_state(task_file_path, worktree, "in_progress")

                # Check approval BEFORE cancellation (TASK-ABFIX-004)
                # Coach approval during grace period must propagate even if cancellation is set
                if turn_record.decision == "approve":
                    logger.info(f"Coach approved on turn {turn}")
                    # Still create checkpoint for approved turn (record-keeping)
                    if self.enable_checkpoints and self._checkpoint_manager:
                        tests_passed = self._extract_tests_passed(turn_record)
                        test_count = self._extract_test_count(turn_record)
                        try:
                            checkpoint = self._checkpoint_manager.create_checkpoint(
                                turn=turn,
                                tests_passed=tests_passed,
                                test_count=test_count,
                            )
                        except CheckpointRefused as refused:
                            # An approval whose work cannot be put on the
                            # branch is not a finished task (build 0D7C).
                            return turn_history, self._stop_for_checkpoint_refusal(
                                task_id, refused
                            )
                        logger.info(
                            f"Checkpoint created: {checkpoint.commit_hash[:8]} "
                            f"for turn {turn}"
                        )
                    # In a repair round, the files the reviewer was shown on
                    # the turn it approved, kept in memory for the feature
                    # orchestrator to carry to this task's next repair round.
                    self.repair_round_approved_files = (
                        getattr(self._agent_invoker, "repair_round_inventory", None)
                        if getattr(self._agent_invoker, "repair_round", None) is not None
                        else None
                    )
                    return turn_history, "approved"

                # Cooperative cancellation check after turn (TASK-ASF-007)
                # Placed after approve check so Coach-approved grace period turns propagate
                if self._cancellation_event and self._cancellation_event.is_set():
                    logger.info(
                        f"Cancellation detected after turn {turn} for {task_id}"
                    )
                    return turn_history, "cancelled"

                if turn_record.decision == "error":
                    logger.error(f"Critical error on turn {turn}")
                    return turn_history, "error"

                # Create checkpoint after turn completes (if enabled)
                # Skip checkpoint for configuration errors — tests were never run (TASK-ABFIX-003)
                if self.enable_checkpoints and self._checkpoint_manager:
                    tests_passed = self._extract_tests_passed(turn_record)
                    test_count = self._extract_test_count(turn_record)

                    try:
                        checkpoint = self._checkpoint_manager.create_checkpoint(
                            turn=turn,
                            tests_passed=tests_passed,
                            test_count=test_count,
                        )
                    except CheckpointRefused as refused:
                        return turn_history, self._stop_for_checkpoint_refusal(
                            task_id, refused
                        )
                    logger.info(
                        f"Checkpoint created: {checkpoint.commit_hash[:8]} "
                        f"for turn {turn}"
                    )


                # Handle feedback decision
                if turn_record.decision == "feedback":
                    logger.info(f"Coach provided feedback on turn {turn}")
                    previous_feedback = turn_record.feedback
                    protected_note = getattr(self, "_protected_paths_note", None)
                    if protected_note:
                        # Protected paths this turn changed were put back.
                        previous_feedback = (
                            f"{protected_note}\n\n{previous_feedback}"
                            if previous_feedback
                            else protected_note
                        )
                    # Continue to next turn

                else:
                    # Should never happen (decision is Literal type)
                    logger.error(f"Invalid decision: {turn_record.decision}")
                    return turn_history, "error"

            # Reached max turns without approval
            logger.warning(f"Max turns ({self.max_turns}) exceeded for {task_id}")
            return turn_history, "max_turns_exceeded"

    def _maybe_refresh_venv_for_manifest_change(
        self, player_result: Any, worktree: Any, turn: int
    ) -> None:
        """Reinstall the worktree's dependencies when this turn changed a manifest.

        TASK-AB-COACHVENV01: the reinstall runs before the Coach's independent
        test run, so the project's tests run against the dependencies the turn
        declared. A failed reinstall is logged; the turn goes on, and the
        project's tests say what they say.
        """
        from guardkit.orchestrator.environment_bootstrap import (
            changed_dependency_manifests,
            refresh_environment_for_changes,
            stacks_for_changed_manifests,
        )

        if worktree is None or player_result is None:
            return
        report = getattr(player_result, "report", None) or {}
        changed = list(report.get("files_modified", []) or []) + list(
            report.get("files_created", []) or []
        )
        manifests_changed = changed_dependency_manifests(
            changed, Path(worktree.path)
        )
        if not manifests_changed:
            return
        logger.info(
            "Turn %d modified dependency manifest(s) %s — refreshing worktree "
            "venv before Coach verification (TASK-AB-COACHVENV01)",
            turn,
            manifests_changed,
        )
        try:
            result = refresh_environment_for_changes(
                Path(worktree.path),
                changed,
                relevant_stacks=stacks_for_changed_manifests(changed) or None,
            )
        except Exception as exc:  # noqa: BLE001 - logged; the turn goes on
            logger.warning(
                "Worktree venv refresh failed for turn %d: %s", turn, exc,
            )
            return
        if result is None:
            return
        if not result.success:
            logger.warning(
                "Worktree venv refresh for turn %d did not succeed: %s",
                turn,
                "; ".join(
                    f"{d.stack} ({Path(d.manifest_path).name}): {d.stderr_excerpt}"
                    for d in result.failure_details
                ) or (result.error or "unknown install error"),
            )
            return
        if result.venv_python:
            self._venv_python = result.venv_python
        logger.info(
            "Worktree venv refreshed for turn %d (stacks: %s)",
            turn,
            ", ".join(result.stacks_detected),
        )

    def _set_progress_files_measure(self, measure: Optional[Any]) -> None:
        """Install or clear the progress log's files-changed measurement."""
        progress_logger = getattr(self, "_progress_logger", None)
        setter = getattr(progress_logger, "set_files_changed_measure", None)
        if callable(setter):
            try:
                setter(measure)
            except Exception as exc:  # noqa: BLE001 — never ends a turn
                logger.debug("progress log measurement not set: %s", exc)

    def _execute_turn(
        self,
        turn: int,
        task_id: str,
        requirements: str,
        worktree: Worktree,
        previous_feedback: Optional[str],
        task_type: Optional[str] = None,
        skip_arch_review: bool = False,
        acceptance_criteria: Optional[List[str]] = None,
        requires_infrastructure: Optional[List[str]] = None,
        consumer_context: Optional[list] = None,
        remaining_budget: Optional[float] = None,
        behavioural_oracle: Optional[Any] = None,
        component: Optional[str] = None,  # per-component seam
    ) -> TurnRecord:
        """
        Execute single Player→Coach turn.

        This method coordinates a complete turn cycle: Player implements,
        Coach validates, decision parsed.

        Steps
        -----
        1. Display: start_turn(turn, "Player Implementation")
        2. Invoke: Player agent with requirements + feedback
        3. Display: complete_turn(status, summary)
        4. Display: start_turn(turn, "Coach Validation")
        5. Invoke: Coach agent with Player report
        6. Display: complete_turn(status, summary)
        7. Parse: Coach decision (approve/feedback)
        8. Return: TurnRecord

        Parameters
        ----------
        turn : int
            Current turn number (1-indexed)
        task_id : str
            Task identifier
        requirements : str
            Task requirements
        worktree : Worktree
            Worktree for agent invocation
        previous_feedback : Optional[str]
            Optional feedback from previous turn
        task_type : Optional[str], optional
            Task type from task frontmatter (e.g., "implementation", "refactor", "bugfix")
        requires_infrastructure : Optional[List[str]], optional
            Infrastructure services required (e.g., ["postgresql", "redis"])
        consumer_context : Optional[list], optional
            Consumer context metadata from task frontmatter for format validation
        behavioural_oracle : Optional[Any], optional
            Resolved behavioural-oracle declaration (TS-lane D.1a)

        Returns
        -------
        TurnRecord
            Immutable TurnRecord with complete turn data

        Notes
        -----
        Error Handling:
        - Player errors: Recorded, continue to Coach for guidance (CHANGED)
        - Coach errors: Mark turn as error, will exit loop
        - SDK timeouts: Treated as errors
        """
        if self._agent_invoker is not None:
            self._agent_invoker._original_invocation_failure = None
        timestamp = datetime.now().isoformat()
        recovered_failure_error: Optional[str] = None
        # What this turn's protected-path check put back, for the next turn.
        self._protected_paths_note: Optional[str] = None

        # TASK-AB-NOCHANGE01: photograph the worktree before the generator
        # runs. The matching photograph is taken after the generator and the
        # orchestrator's own Phase 4/5 specialists have finished and before the
        # reviewer starts, so the reviewer's test run (which can leave cache
        # files behind) cannot be mistaken for work. The difference between the
        # two is the only account of what this turn changed that the generator
        # cannot write.
        files_changed_this_turn: Optional[int] = None
        pre_turn_snapshot = (
            _worktree_change_snapshot(worktree.path)
            if worktree is not None
            else None
        )
        # 13 October 2026: progress.log snapshots during the Player phase
        # read this same git measurement, because a harness that hands over
        # its tool events only after the run leaves the event counter at 0.
        # Cleared before the Coach phase, and by the caller on every exit.
        self._set_progress_files_measure(
            None
            if worktree is None or pre_turn_snapshot is None
            else lambda: count_changed_paths(
                pre_turn_snapshot,
                # Runs while the Player works: never take the index lock.
                _worktree_change_snapshot(worktree.path, no_optional_locks=True),
            )
        )

        # ===== Player Phase =====

        self._progress_display.start_turn(turn, "Player Implementation")

        logger.debug(f"Invoking Player for turn {turn}")
        player_result = self._invoke_player_safely(
            task_id=task_id,
            turn=turn,
            requirements=requirements,
            feedback=previous_feedback,
            remaining_budget=remaining_budget,  # TASK-VRF-003: Forward budget for SDK timeout capping
        )
        # Snapshot context status after invocation (TASK-FIX-GCW5)
        player_context_status = self._last_player_context_status

        # Display Player completion
        if player_result.success:
            summary = self._build_player_summary(
                player_result.report,
                tests_required=self._resolve_tests_required(task_type),
            )
            self._progress_display.complete_turn("success", summary)
            # Show context status line if context was retrieved (TASK-FIX-GCW5)
            if player_context_status and player_context_status.status != "disabled":
                from guardkit.orchestrator.progress import format_context_status
                ctx_line = format_context_status(player_context_status)
                if ctx_line:
                    self._progress_display.console.print(f"   [dim]{ctx_line}[/dim]")
        else:
            # Distinguish between missing report and actual failure
            is_missing_report = (
                player_result.error and
                ("report not found" in player_result.error.lower() or
                 "PlayerReportNotFoundError" in player_result.error)
            )

            # TASK-PFI-A1B2: Capture original error before potential overwrite
            _original_error = player_result.error
            receipt = getattr(self._agent_invoker, "_original_invocation_failure", None)
            failure = dict(receipt) if isinstance(receipt, dict) and receipt.get("task_id") == task_id else {}

            failure.update(type=failure.get("type") or player_result.report.get("error_type") or ("TimeoutError" if _player_result_timeout(player_result) else "ExecutionError"),
                           message=_original_error or "Player invocation failed", phase="player",
                           mode=self._implementation_mode(task_id),
                           task_id=task_id, turn=turn,
                           scope_id=getattr(getattr(self, "task_work_scope", None), "scope_id", None),
                           report_missing_only=bool(is_missing_report))
            player_result.report["original_failure"] = failure

            # Check for unrecoverable error first - exit immediately without retry (TASK-AB-FIX-003)
            is_unrecoverable = player_result.report.get("unrecoverable", False)

            if is_unrecoverable:
                # Unrecoverable error - fail immediately without state recovery
                logger.error(
                    f"Unrecoverable error detected for {task_id} turn {turn}: {player_result.error}"
                )
                self._progress_display.complete_turn(
                    "error",
                    f"Unrecoverable error: {player_result.error}",
                    error=player_result.error,
                )
                return TurnRecord(
                    turn=turn,
                    player_result=player_result,
                    coach_result=None,
                    decision="error",
                    feedback=self._feedback_after_turn_without_work(task_id, turn, player_result),
                    timestamp=timestamp,
                    player_context_status=player_context_status,
                    sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                    sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                    sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', None),
                )

            if is_missing_report:
                # Report missing but implementation may have succeeded
                # Use "feedback" status (⚠ yellow) instead of "error" (✗ red)
                # because the Player may have succeeded - we just can't find the report
                self._progress_display.complete_turn(
                    "feedback",
                    "Player report missing - attempting state recovery",
                )
                # Add explanatory note to console
                self._progress_display.console.print(
                    "   [dim]Note: Implementation may have succeeded; recovering state from git[/dim]"
                )
            else:
                # Actual Player failure
                self._progress_display.complete_turn(
                    "error",
                    f"Player failed: {player_result.error or 'Unknown error'}",
                    error=player_result.error,
                )

            # Attempt multi-layered state detection
            recovered_player_result = self._attempt_state_recovery(
                task_id=task_id,
                turn=turn,
                worktree=worktree,
                original_error=player_result.error,
                acceptance_criteria=acceptance_criteria,
                task_type=task_type,
                player_report=player_result.report,
            )

            if recovered_player_result:
                # State recovery succeeded - continue with recovered data
                player_result = recovered_player_result
                implementation_mode = (
                    self._agent_invoker._get_implementation_mode(task_id)
                    if self._agent_invoker is not None
                    else None
                )
                is_task_work_timeout = (
                    implementation_mode == "task-work"
                    and isinstance(_original_error, str)
                    and "task-work execution exceeded" in _original_error.lower()
                    and "timeout" in _original_error.lower()
                )

                if not is_missing_report:
                    # Recovery found useful partial state, not a successful
                    # implementation. Preserve the task-work failure receipt
                    # and keep this Player result failed so no Phase 4/5 or
                    # approval path can be inferred from passing partial tests.
                    recovered_failure_error = _original_error
                    if self._agent_invoker is not None:
                        self._agent_invoker._write_recovered_task_work_failure(
                            task_id,
                            player_result.report,
                            original_error=_original_error,
                        )
                    player_result = AgentInvocationResult(
                        task_id=player_result.task_id,
                        turn=player_result.turn,
                        agent_type=player_result.agent_type,
                        success=False,
                        report=player_result.report,
                        duration_seconds=player_result.duration_seconds,
                        error=_original_error,
                        sdk_turns_used=player_result.sdk_turns_used,
                        sdk_max_turns=player_result.sdk_max_turns,
                        sdk_ceiling_hit=player_result.sdk_ceiling_hit,
                        session_id=player_result.session_id,
                    )
                    logger.info(
                        "State recovery preserved partial task-work failure for "
                        "%s turn %s",
                        task_id,
                        turn,
                    )
                else:
                    # Existing direct/missing-report recovery contract: write
                    # recovered data so Coach can validate it.
                    if self._agent_invoker is not None:
                        self._agent_invoker._write_direct_mode_results(
                            task_id, player_result.report, success=True
                        )
                    logger.info(
                        f"State recovery successful for {task_id} turn {turn}"
                    )
                # TASK-PFI-A1B2: Log CancelledError at DEBUG when recovery succeeds
                if _original_error and _original_error.startswith("Cancelled:"):
                    logger.debug(
                        f"CancelledError caught for {task_id} (recovered: True)"
                    )
                summary = self._build_player_summary(
                    player_result.report,
                    tests_required=self._resolve_tests_required(task_type),
                )
                self._progress_display.complete_turn(
                    "feedback" if recovered_failure_error else "success",
                    (
                        f"[RECOVERED PARTIAL FAILURE] {summary}"
                        if recovered_failure_error
                        else f"[RECOVERED] {summary}"
                    ),
                )
            else:
                # State recovery failed - return error
                logger.warning(
                    f"State recovery failed for {task_id} turn {turn}"
                )
                # TASK-PFI-A1B2: Keep CancelledError at WARNING when recovery fails
                if _original_error and _original_error.startswith("Cancelled:"):
                    logger.warning(
                        f"CancelledError caught for {task_id} (recovered: False)"
                    )
                no_work_feedback = self._feedback_after_turn_without_work(
                    task_id, turn, player_result
                )
                return TurnRecord(
                    turn=turn,
                    player_result=player_result,
                    coach_result=None,
                    decision="error",
                    # FEAT-2C42 (8 October 2026): the turn still ends as an
                    # error, but it says what happened as one plain must-fix,
                    # so the next turn (a resumed run starts from this
                    # feedback) is not told nothing.
                    feedback=no_work_feedback,
                    timeout_note=(
                        no_work_feedback
                        if _player_result_timeout(player_result)
                        else None
                    ),
                    timestamp=timestamp,
                    player_context_status=player_context_status,
                    sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                    sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                    sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', None),
                )

        # Warn if passing synthetic report to Coach (TASK-ASF-004)
        if player_result.success and player_result.report.get("_synthetic"):
            logger.warning(
                f"[Turn {turn}] Passing synthetic report to Coach for {task_id}. "
                f"Promise matching will fail — falling through to text matching."
            )

        # Cooperative cancellation check BETWEEN Player and Coach (TASK-ASF-007)
        # If Player succeeded, grant Coach a grace period instead of aborting (TASK-ABFIX-004)
        if self._cancellation_event and self._cancellation_event.is_set():
            if player_result.success:
                # Player succeeded near the timeout boundary — grant Coach a grace period
                # so the successful implementation can still be validated and approved
                logger.info(
                    f"Cancellation detected for {task_id} between Player and Coach "
                    f"at turn {turn}, but Player succeeded — granting Coach grace period "
                    f"({COACH_GRACE_PERIOD_SECONDS}s)"
                )
                coach_remaining_budget: Optional[float] = float(COACH_GRACE_PERIOD_SECONDS)
            else:
                # Player failed: no benefit in invoking Coach, honour cancellation
                logger.info(
                    f"Cancellation detected for {task_id} between Player and Coach "
                    f"at turn {turn} (Player failed)"
                )
                self._progress_display.complete_turn(
                    "warning",
                    "Cancelled between Player and Coach phases",
                )
                return TurnRecord(
                    turn=turn,
                    player_result=player_result,
                    coach_result=None,
                    decision="error",
                    # A Player that ran out of time still says so, so a
                    # resumed next turn is told (FEAT-2C42). None otherwise.
                    feedback=self._player_timeout_feedback(
                        task_id, turn, player_result, recovered_failure_error
                    ) or None,
                    timestamp=timestamp,
                    player_context_status=player_context_status,
                    sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                    sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                    sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', None),
                    timeout_note=self._player_timeout_feedback(
                        task_id, turn, player_result, recovered_failure_error
                    ) or None,
                )
        else:
            # No cancellation: pass the caller-provided remaining budget to Coach
            coach_remaining_budget = remaining_budget

        # 17 October 2026: protected paths are put back to the build's
        # committed content before the Coach runs (and so before the turn's
        # checkpoint commit, which _loop_phase makes after this method
        # returns). Every path below that reaches the Coach passes here,
        # including a recovered Player turn. A failure stops the task.
        protected_failure = self._restore_protected_paths(
            task_id, worktree, player_result
        )
        if protected_failure is not None:
            self._progress_display.complete_turn(
                "error", protected_failure, error=protected_failure
            )
            return TurnRecord(
                turn=turn,
                player_result=player_result,
                coach_result=None,
                decision="error",
                feedback=None,
                timestamp=timestamp,
                player_context_status=player_context_status,
            )

        # TASK-AB-NOCHANGE01: the matching photograph (see the pre-turn one at
        # the top of this method). Taken here, before the reviewer runs, so
        # anything the reviewer's own test pass writes is outside the frame.
        files_changed_this_turn = count_changed_paths(
            pre_turn_snapshot,
            _worktree_change_snapshot(worktree.path)
            if worktree is not None
            else None,
        )
        logger.info(
            "[%s] turn %s changed %s file(s) in the worktree (git-measured).",
            task_id,
            turn,
            "an unmeasured number of"
            if files_changed_this_turn is None
            else files_changed_this_turn,
        )
        self._set_progress_files_measure(None)
        _turn_progress_logger = getattr(self, "_progress_logger", None)
        if _turn_progress_logger is not None:
            try:
                _turn_progress_logger.log_turn_changes(turn, files_changed_this_turn)
            except Exception as exc:  # noqa: BLE001 — a log line never ends a turn
                logger.debug("progress log TURN_CHANGES failed: %s", exc)

        # ===== Coach Phase =====

        # Skip Coach validation if ablation mode is active
        if self.ablation_mode:
            logger.info(f"[ABLATION] Skipping Coach validation for turn {turn} - auto-approving")
            self._progress_display.complete_turn(
                "warning",
                "[ABLATION] Skipping Coach validation - auto-approving",
            )
            return TurnRecord(
                turn=turn,
                player_result=player_result,
                coach_result=None,
                decision="approve",  # Auto-approve in ablation mode
                feedback=None,
                timestamp=timestamp,
                player_context_status=player_context_status,
                sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', None),
                files_changed_this_turn=files_changed_this_turn,
            )

        # TASK-AB-COACHVENV01: when THIS turn modified a dependency manifest,
        # reinstall into the worktree venv BEFORE the Coach's independent test
        # run, so the project's tests run against the dependencies the turn
        # declared. A failed reinstall is logged; the turn goes on.
        self._maybe_refresh_venv_for_manifest_change(player_result, worktree, turn)

        self._progress_display.start_turn(turn, "Coach Validation")

        logger.debug(f"Invoking Coach for turn {turn}")

        coach_result = self._invoke_coach_safely(
            task_id=task_id,
            turn=turn,
            requirements=requirements,
            player_report=player_result.report,
            worktree=worktree,
            acceptance_criteria=acceptance_criteria,
            task_type=task_type,
            skip_arch_review=skip_arch_review,
            requires_infrastructure=requires_infrastructure,
            consumer_context=consumer_context,
            remaining_budget=coach_remaining_budget,
            wave_size=self.wave_size,
            effective_concurrency=getattr(self, "effective_concurrency", None),
            behavioural_oracle=behavioural_oracle,  # TS-lane D.1a
            component=component,  # per-component seam
        )
        # Snapshot context status after coach invocation (TASK-FIX-GCW5)
        coach_context_status = self._last_coach_context_status

        # Parse Coach decision
        if not coach_result.success:
            self._progress_display.complete_turn(
                "error",
                "Coach failed",
                error=coach_result.error,
            )
            return TurnRecord(
                turn=turn,
                player_result=player_result,
                coach_result=coach_result,
                decision="error",
                # The reviewer failed, but the Player's turn had run out of
                # time: keep that must-fix, so a resumed next turn is still
                # told (FEAT-2C42 review, 8 October 2026). None otherwise.
                feedback=self._player_timeout_feedback(
                    task_id, turn, player_result, recovered_failure_error
                ) or None,
                timeout_note=self._player_timeout_feedback(
                    task_id, turn, player_result, recovered_failure_error
                ) or None,
                timestamp=timestamp,
                player_context_status=player_context_status,
                coach_context_status=coach_context_status,
                sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', None),
                files_changed_this_turn=files_changed_this_turn,
            )

        # Extract decision and feedback
        decision_value = coach_result.report.get("decision", "feedback")

        if decision_value == "approve":
            self._progress_display.complete_turn(
                "success",
                "Coach approved - ready for human review",
            )
            # Show coach context status line (TASK-FIX-GCW5)
            if coach_context_status and coach_context_status.status != "disabled":
                from guardkit.orchestrator.progress import format_context_status
                ctx_line = format_context_status(coach_context_status)
                if ctx_line:
                    self._progress_display.console.print(f"   [dim]{ctx_line}[/dim]")
            return TurnRecord(
                turn=turn,
                player_result=player_result,
                coach_result=coach_result,
                decision="approve",
                feedback=None,
                timestamp=timestamp,
                player_context_status=player_context_status,
                coach_context_status=coach_context_status,
                sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', None),
                files_changed_this_turn=files_changed_this_turn,
            )

        else:  # feedback
            feedback_text = self._turn_feedback_text(coach_result.report, turn)
            # FEAT-2C42 (8 October 2026): when this turn ran out of time,
            # whatever decided the feedback (the evidence gate or the model
            # reviewer), the next turn is told so first, as a must-fix with
            # a suggestion.
            # FEAT-2C42: when this turn ran out of time, the next turn is told
            # so first, once, as a must-fix with a suggestion, in the words
            # for its mode, whatever decided the feedback.
            timeout_note = self._player_timeout_feedback(
                task_id, turn, player_result, recovered_failure_error,
                coach_result.report,
            )
            if timeout_note:
                feedback_text = f"{timeout_note}\n\n{feedback_text}"
            summary = self._build_feedback_summary(coach_result.report, feedback_text)
            self._progress_display.complete_turn("feedback", summary)
            # Show coach context status line (TASK-FIX-GCW5)
            if coach_context_status and coach_context_status.status != "disabled":
                from guardkit.orchestrator.progress import format_context_status
                ctx_line = format_context_status(coach_context_status)
                if ctx_line:
                    self._progress_display.console.print(f"   [dim]{ctx_line}[/dim]")

            return TurnRecord(
                turn=turn,
                player_result=player_result,
                coach_result=coach_result,
                decision="feedback",
                feedback=feedback_text,
                timestamp=timestamp,
                player_context_status=player_context_status,
                coach_context_status=coach_context_status,
                sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', None),
                files_changed_this_turn=files_changed_this_turn,
                # Asked without the reviewer's report, so it is there even
                # when the reviewer's own timeout issue made the note above
                # unnecessary (the overridden approval).
                timeout_note=self._player_timeout_feedback(
                    task_id, turn, player_result, recovered_failure_error
                ) or None,
            )

    def _finalize_phase(
        self,
        worktree: Worktree,
        final_decision: Literal["approved", "max_turns_exceeded", "error", "cancelled", "pre_loop_blocked", "design_extraction_failed"],
        turn_history: List[TurnRecord],
    ) -> None:
        """
        Phase 4: Preserve worktree for human review.

        Per architectural review (YAGNI principle), auto_merge parameter was
        removed. All worktrees are now preserved for human review regardless
        of outcome.

        Decision Tree
        -------------
        - approved: Preserve for human review before merge
        - max_turns_exceeded: Preserve for inspection (with blocked report if available)
        - error: Preserve for debugging
        - pre_loop_blocked: Preserve for review (quality gate failure)
        - design_extraction_failed: Preserve for review (Phase 0 MCP failure)

        Parameters
        ----------
        worktree : Worktree
            Worktree to finalize
        final_decision : Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked", "design_extraction_failed"]
            Loop exit reason
        turn_history : List[TurnRecord]
            Complete turn history

        Notes
        -----
        This simplified design addresses the architectural review finding
        that auto_merge was premature optimization (YAGNI violation).

        Side Effects:
        - Preserves worktree (never auto-deletes)
        - Renders blocked report if available (escape hatch pattern)
        - Renders final summary via ProgressDisplay
        """
        logger.info(f"Phase 4 (Finalize): Preserving worktree for {worktree.task_id}")

        # Always preserve worktree for human review
        self._worktree_manager.preserve_on_failure(worktree)

        # Check for blocked report in last Player report (escape hatch pattern).
        blocked_report = self._extract_blocked_report(turn_history)
        if blocked_report and final_decision == "max_turns_exceeded":
            # Render structured blocked report
            self._progress_display.render_blocked_report(
                blocked_report=blocked_report,
                task_id=worktree.task_id,
                total_turns=len(turn_history),
            )

        # Build summary details
        details = self._build_summary_details(turn_history, final_decision)

        # Render final summary
        self._progress_display.render_summary(
            total_turns=len(turn_history),
            final_status=final_decision,
            details=details,
        )

        # Flush emitter to ensure all events are persisted (TASK-INST-004)
        try:
            asyncio.run(self._emitter.flush())
        except Exception as exc:
            logger.warning("Failed to flush emitter during finalize: %s", exc)

        # Clean up per-thread memory clients (TASK-FIX-GTP2)
        self._cleanup_thread_loaders()

        logger.info(
            f"Worktree preserved at {worktree.path} for human review. "
            f"Decision: {final_decision}"
        )

    def _extract_blocked_report(
        self,
        turn_history: List[TurnRecord],
    ) -> Optional[BlockedReport]:
        """
        Extract blocked report from the last Player report if present.

        The Player agent generates a blocked_report when approaching max turns
        without approval (escape hatch pattern). This method extracts that
        report for display.

        Parameters
        ----------
        turn_history : List[TurnRecord]
            Complete turn history

        Returns
        -------
        Optional[BlockedReport]
            BlockedReport if present in last Player report, None otherwise
        """
        if not turn_history:
            return None

        # Check the last turn's Player report
        last_turn = turn_history[-1]
        if last_turn.player_result and last_turn.player_result.success:
            try:
                return BlockedReport.from_player_report(last_turn.player_result.report)
            except Exception as e:
                logger.warning(f"Failed to extract blocked report: {e}")
                return None

        return None

    def _attempt_state_recovery(
        self,
        task_id: str,
        turn: int,
        worktree: Worktree,
        original_error: Optional[str],
        acceptance_criteria: Optional[List[str]] = None,
        task_type: Optional[str] = None,
        player_report: Optional[dict] = None,
    ) -> Optional[AgentInvocationResult]:
        """
        Attempt to recover work state when Player fails.

        This method implements the multi-layered state detection pattern to
        detect partial work even when Player fails without writing a JSON report.

        Detection Cascade:
        1. Check for Player JSON report (may exist despite failure)
        2. Detect git changes (modified/new files)
        3. Run tests to verify implementation quality

        If any work is detected, creates a synthetic AgentInvocationResult
        with the detected state, allowing the workflow to continue.

        Parameters
        ----------
        task_id : str
            Task identifier
        turn : int
            Turn number
        worktree : Worktree
            Worktree for state detection
        original_error : Optional[str]
            Original error from Player failure
        acceptance_criteria : Optional[List[str]]
            Acceptance criteria from task (for promise generation)
        task_type : Optional[str]
            Task type from frontmatter (e.g., "scaffolding", "feature")
        player_report : Optional[dict]
            Player report dict, used to extract tests_written for scoped test runs

        Returns
        -------
        Optional[AgentInvocationResult]
            Synthetic result if work detected, None if no work found
        """
        logger.info(
            f"Attempting state recovery for {task_id} turn {turn} "
            f"after Player failure: {original_error}"
        )

        # Track recovery attempt
        self.recovery_count += 1

        try:
            # Load task to extract test_scope if available
            from guardkit.tasks.task_loader import TaskLoader

            test_paths = None

            # Prefer player report test files when available
            if player_report and player_report.get("tests_written"):
                test_paths = player_report["tests_written"]
                logger.debug(f"Using player report test paths: {test_paths}")

            if test_paths is None:
                try:
                    task_data = TaskLoader.load_task(task_id, repo_root=self.repo_root)
                    test_scope = task_data.get("frontmatter", {}).get("test_scope")
                    if test_scope:
                        test_paths = [test_scope]
                        logger.debug(f"Using task-specific test scope: {test_scope}")
                except Exception as e:
                    logger.debug(f"Could not load task for test_scope extraction: {e}")
                    # Continue with full-worktree run (backward compatible)

            # Use MultiLayeredStateTracker for cascade detection
            state_tracker = MultiLayeredStateTracker(
                task_id=task_id,
                worktree_path=worktree.path,
                task_work_scope=getattr(self, "task_work_scope", None),
            )

            work_state = state_tracker.capture_state(turn=turn, test_paths=test_paths)

            if not work_state or not work_state.has_work:
                logger.info(f"No work detected in {worktree.path}")
                return None

            # Log recovery details
            logger.info(
                f"State recovery succeeded via {work_state.detection_method}: "
                f"{work_state.total_files_changed} files, "
                f"{work_state.test_count} tests "
                f"({'passing' if work_state.tests_passed else 'failing'})"
            )

            # Save detected state for audit trail
            state_tracker.save_state(work_state)

            # Build synthetic Player report from detected state
            synthetic_report = self._build_synthetic_report(
                work_state,
                original_error,
                acceptance_criteria=acceptance_criteria,
                task_type=task_type,
                worktree_path=worktree.path,
                player_timeout=(
                    player_timeout_from_report(player_report)
                    or player_timeout_from_error(original_error)
                ),
            )

            # Ensure task_id is populated in report (TASK-ACR-001)
            synthetic_report["task_id"] = task_id
            failure = (player_report or {}).get("original_failure", {})
            synthetic_report["original_failure"] = failure
            synthetic_report.setdefault("_recovery_metadata", {})["original_failure"] = failure
            synthetic_report["_recovery_metadata"]["state_recovered"] = True
            synthetic_report["scope_id"] = self.task_work_scope.scope_id
            if failure and not failure.get("report_missing_only"):
                synthetic_report["success"] = False
                synthetic_report["completed"] = False

            # TASK-CRV-1540: Enrich synthetic report with partial data from
            # response_messages if available (extracted during CancelledError)
            if self._agent_invoker is not None:
                partial = getattr(self._agent_invoker, "_last_partial_report", None)
                if partial:
                    synthetic_report["partial_data"] = partial
                    logger.info(
                        f"Enriched synthetic report with partial data: "
                        f"{partial.get('text_block_count', 0)} text blocks, "
                        f"{partial.get('tool_call_count', 0)} tool calls, "
                        f"{len(partial.get('file_modifications', []))} file mods"
                    )

            # Return as AgentInvocationResult
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=bool(failure.get("report_missing_only")),  # State recovery is not invocation success
                report=synthetic_report,
                duration_seconds=0.0,
                error=original_error if not failure.get("report_missing_only") else None,
            )

        except Exception as e:
            logger.error(f"State recovery failed: {e}", exc_info=True)
            return None

    def _build_synthetic_report(
        self,
        work_state: WorkState,
        original_error: Optional[str],
        acceptance_criteria: Optional[List[str]] = None,
        task_type: Optional[str] = None,
        worktree_path: Optional[Path] = None,
        player_timeout: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build synthetic Player report from detected work state.

        Creates a report structure compatible with existing Coach validation,
        including all detected files and test results.

        For scaffolding tasks, generates file-existence promises to enable
        promise-based criteria matching (TASK-ASF-006).

        Parameters
        ----------
        work_state : WorkState
            Detected work state
        original_error : Optional[str]
            Original error for context
        acceptance_criteria : Optional[List[str]]
            Acceptance criteria from task (for promise generation)
        task_type : Optional[str]
            Task type from frontmatter (e.g., "scaffolding", "feature")
        worktree_path : Optional[Path]
            Worktree root path for content-based requirements inference
            (TASK-FIX-ASPF-006).
        player_timeout : Optional[Dict[str, Any]]
            When the Player's turn ran out of time: ``timed_out`` and its
            timings. Kept in ``_recovery_metadata`` so the evidence gate and
            the final summary can say the turn ran out of time.

        Returns
        -------
        Dict[str, Any]
            Synthetic Player report
        """
        # Tasks that run at the same time in one wave share one working copy,
        # so git's changes may include another task's files (build FEAT-2C42,
        # 8 October 2026: a rebuilt report credited one task with its
        # neighbour's files). Git cannot tell whose change is whose, so then
        # the rebuilt report keeps its file lists but carries no promises and
        # no inferred requirements, and says why: it is never counted as this
        # task's evidence. A wave run one task at a time is not shared and
        # keeps its evidence.
        shared_working_copy = self.shares_working_copy
        if shared_working_copy or getattr(self, "task_work_scope", None) is None:
            acceptance_criteria = None

        # Determine promise generation strategy
        has_criteria = acceptance_criteria and len(acceptance_criteria) > 0
        should_generate_file_promises = (
            task_type == "scaffolding" and has_criteria
        )
        should_generate_git_promises = (
            task_type is not None
            and task_type != "scaffolding"
            and has_criteria
        )

        # Log synthetic report construction (TASK-ASF-004 + TASK-ASF-006 + TASK-ACR-004)
        if should_generate_file_promises:
            logger.warning(
                f"[Turn {work_state.turn_number}] Building synthetic report: "
                f"{len(work_state.files_created)} files created, "
                f"{len(work_state.files_modified)} files modified, "
                f"{work_state.test_count} tests. "
                f"Generating file-existence promises for scaffolding task."
            )
        elif should_generate_git_promises:
            logger.warning(
                f"[Turn {work_state.turn_number}] Building synthetic report: "
                f"{len(work_state.files_created)} files created, "
                f"{len(work_state.files_modified)} files modified, "
                f"{work_state.test_count} tests. "
                f"Generating git-analysis promises for {task_type} task."
            )
        else:
            logger.warning(
                f"[Turn {work_state.turn_number}] Building synthetic report: "
                f"{len(work_state.files_created)} files created, "
                f"{len(work_state.files_modified)} files modified, "
                f"{work_state.test_count} tests. "
                f"Note: report has no completion_promises and cannot satisfy "
                f"promise-based criteria matching."
            )

        # Delegate core report construction to shared builder (TASK-FIX-D1A3)
        from guardkit.orchestrator.synthetic_report import (
            build_synthetic_report as _shared_build_synthetic_report,
        )

        report = _shared_build_synthetic_report(
            task_id="",  # Filled by caller
            turn=work_state.turn_number,
            files_modified=work_state.files_modified,
            files_created=work_state.files_created,
            tests_written=work_state.tests_written,
            tests_passed=work_state.tests_passed,
            test_count=work_state.test_count,
            implementation_notes=(
                f"[RECOVERED via {work_state.detection_method}] "
                f"Original error: {original_error or 'Unknown'}"
            ),
            concerns=[
                f"Player failed with error: {original_error or 'Unknown'}",
                f"Work recovered via {work_state.detection_method}",
            ],
            acceptance_criteria=acceptance_criteria if should_generate_file_promises else None,
            task_type="scaffolding" if should_generate_file_promises else None,
            recovery_metadata={
                "detection_method": work_state.detection_method,
                "git_insertions": (
                    work_state.git_changes.insertions
                    if work_state.git_changes
                    else 0
                ),
                "git_deletions": (
                    work_state.git_changes.deletions
                    if work_state.git_changes
                    else 0
                ),
                "timestamp": work_state.timestamp,
                "original_error": original_error,
                **(player_timeout or {}),
            },
            worktree_path=worktree_path,
        )

        # Override test_output_summary from WorkState (shared builder defaults to "")
        if work_state.test_results:
            report["test_output_summary"] = work_state.test_results.output_summary

        # Generate git-analysis promises for non-scaffolding tasks (TASK-ACR-004)
        if should_generate_git_promises:
            git_promises = self._generate_git_analysis_promises(
                work_state, acceptance_criteria
            )
            if git_promises:
                report["completion_promises"] = git_promises
                logger.info(
                    f"Generated {len(git_promises)} git-analysis promises "
                    f"for {task_type} task synthetic report"
                )

        if shared_working_copy:
            mark_shared_working_copy(report)
            logger.warning(
                f"[Turn {work_state.turn_number}] Rebuilt report comes from "
                f"the working copy other tasks in this wave were changing at "
                f"the same time; it may include their files, so it is not counted as "
                f"this task's evidence."
            )

        return report

    # --- Runtime command execution for command_execution criteria (TASK-CRV-537E) ---

    def _generate_file_existence_promises(
        self,
        work_state: WorkState,
        acceptance_criteria: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Generate file-existence promises for scaffolding tasks.

        Thin wrapper around the shared
        ``guardkit.orchestrator.synthetic_report.generate_file_existence_promises``
        function (TASK-FIX-D1A3). Preserves the existing method signature so
        that all callers and tests remain unchanged.

        Parameters
        ----------
        work_state : WorkState
            Detected work state with files_created and files_modified
        acceptance_criteria : List[str]
            Acceptance criteria text from the task

        Returns
        -------
        List[Dict[str, Any]]
            List of completion promise dicts with ``evidence_type: "file_existence"``
            on every promise (set by the shared function).
        """
        from guardkit.orchestrator.synthetic_report import (
            generate_file_existence_promises,
        )

        return generate_file_existence_promises(
            files_created=work_state.files_created,
            files_modified=work_state.files_modified,
            acceptance_criteria=acceptance_criteria,
        )

    # --- Git-analysis promise generation (TASK-ACR-004) ---

    # Stopwords excluded from keyword extraction
    _KEYWORD_STOPWORDS = frozenset({
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "be", "as", "that", "this",
        "are", "was", "were", "been", "has", "have", "had", "do", "does",
        "did", "will", "would", "should", "can", "could", "may", "might",
        "shall", "must", "not", "no", "all", "each", "every", "any", "some",
        "when", "if", "then", "else", "into", "via", "using", "new",
    })

    def _generate_git_analysis_promises(
        self,
        work_state: WorkState,
        acceptance_criteria: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Generate git-analysis promises for feature/implementation tasks.

        Analyzes git diff data (files created/modified) to detect whether
        acceptance criteria were likely addressed. Uses keyword extraction
        and pattern matching against changed file paths and basenames.

        Unlike file-existence promises (scaffolding), these promises use
        ``status: "partial"`` to indicate lower confidence.

        Parameters
        ----------
        work_state : WorkState
            Detected work state with files_created, files_modified, git_changes
        acceptance_criteria : List[str]
            Acceptance criteria text from the task

        Returns
        -------
        List[Dict[str, Any]]
            List of completion promise dicts with structure::

                {
                    "criterion_id": "AC-001",
                    "criterion_text": "...",
                    "status": "partial" | "incomplete",
                    "evidence": "...",
                    "evidence_type": "git_analysis"
                }
        """
        changed_files = set(work_state.files_created + work_state.files_modified)
        if not changed_files:
            return []

        promises: List[Dict[str, Any]] = []
        for i, criterion_text in enumerate(acceptance_criteria):
            criterion_id = f"AC-{i+1:03d}"

            # Extract file path patterns from criterion text
            file_patterns = re.findall(r'[\w./\-]+\.\w{1,5}', criterion_text)

            # Extract code patterns (function names, class names, endpoints)
            code_patterns = self._extract_code_patterns(criterion_text)

            # Extract keywords for fuzzy matching
            keywords = self._extract_criterion_keywords(criterion_text)

            # Match against changed files
            matched_files: List[str] = []
            matched_patterns: List[str] = []

            # 1. File path matching (exact, like scaffolding)
            for pattern in file_patterns:
                for f in changed_files:
                    if f.endswith(pattern) or pattern in f:
                        if f not in matched_files:
                            matched_files.append(f)

            # 2. Code pattern matching against file basenames
            for pattern in code_patterns:
                pattern_lower = pattern.lower().lstrip("/")
                for f in changed_files:
                    f_lower = f.lower()
                    if pattern_lower in f_lower:
                        matched_patterns.append(pattern)
                        if f not in matched_files:
                            matched_files.append(f)
                        break

            # 3. Keyword matching against file basenames (fuzzy)
            if keywords and not matched_files:
                file_text = " ".join(f.lower() for f in changed_files)
                matched_kws = [kw for kw in keywords if kw in file_text]
                if len(matched_kws) >= max(1, len(keywords) * 0.3):
                    matched_patterns.extend(matched_kws[:3])

            # Build promise
            if matched_files or matched_patterns:
                evidence_parts: List[str] = []
                if matched_files:
                    file_descs = []
                    for f in matched_files[:3]:
                        action = (
                            "created"
                            if f in work_state.files_created
                            else "modified"
                        )
                        file_descs.append(f"{f} ({action})")
                    evidence_parts.append(
                        "Files: " + ", ".join(file_descs)
                    )
                if matched_patterns:
                    evidence_parts.append(
                        "Patterns: " + ", ".join(matched_patterns[:3])
                    )
                evidence = "Git-analysis detected: " + "; ".join(evidence_parts)
                status = "partial"
            else:
                evidence = "No git-analysis evidence for this criterion"
                status = "incomplete"

            promises.append({
                "criterion_id": criterion_id,
                "criterion_text": criterion_text,
                "status": status,
                "evidence": evidence,
                "evidence_type": "git_analysis",
            })

        return promises

    def _extract_code_patterns(self, text: str) -> List[str]:
        """
        Extract code patterns from criterion text.

        Detects function calls (``word()``), CamelCase class names,
        and endpoint paths (``/path/to/resource``).

        Parameters
        ----------
        text : str
            Acceptance criterion text

        Returns
        -------
        List[str]
            Extracted code patterns
        """
        patterns: List[str] = []

        # Function calls: word()
        func_matches = re.findall(r'\b(\w+)\(\)', text)
        patterns.extend(func_matches)

        # CamelCase class names (at least two segments)
        class_matches = re.findall(
            r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', text
        )
        patterns.extend(class_matches)
        # Also split CamelCase into individual lowercase words for
        # file-path matching (e.g. PaymentProcessor → payment, processor)
        for class_name in class_matches:
            words = re.findall(r'[A-Z][a-z]+', class_name)
            patterns.extend(w.lower() for w in words)

        # Endpoint paths: /path/to/resource
        endpoint_matches = re.findall(r'(/[\w/\-]+)', text)
        patterns.extend(endpoint_matches)

        return patterns

    def _extract_criterion_keywords(self, text: str) -> set:
        """
        Extract meaningful keywords from criterion text.

        Splits on non-alphanumeric characters, lowercases, and filters
        out stopwords and short words (<=3 chars).

        Parameters
        ----------
        text : str
            Acceptance criterion text

        Returns
        -------
        set
            Set of meaningful keyword strings (lowercased)
        """
        words = re.findall(r'[a-zA-Z_]\w*', text)
        return {
            w.lower()
            for w in words
            if len(w) > 3
            and w.lower() not in self._KEYWORD_STOPWORDS
            and not w.startswith("AC-")
        }

    # ========================================================================
    # Helper Methods (Error Handling, Summary Building)
    # ========================================================================

    def _should_reset_perspective(self, turn: int) -> bool:
        """
        Check if Player should receive fresh perspective (reset) on this turn.

        Fresh perspective reset prevents anchoring bias by having the Player
        receive only original requirements without prior feedback at specified
        turns. This allows the Player to reconsider the problem from first
        principles rather than being locked into early assumptions.

        Implementation (TASK-BRF-001):
        - Turn-based reset at hardcoded turns [3, 5]
        - No anchoring detection (deferred to future work per YAGNI principle)
        - Simple logging when reset occurs

        Parameters
        ----------
        turn : int
            Current turn number (1-indexed)

        Returns
        -------
        bool
            True if perspective should be reset, False otherwise

        Notes
        -----
        Reset turns are hardcoded as [3, 5] per architectural review
        recommendation to keep MVP simple and testable.
        """
        if turn in self.perspective_reset_turns:
            logger.info(
                f"Perspective reset triggered at turn {turn} (scheduled reset)"
            )
            return True
        return False

    def _repair_round_for_this_loop(self, task_id: str) -> Optional[Any]:
        """The repair round this task's turns are judged as, or ``None``."""
        return getattr(self, "_repair_round", None)

    # ------------------------------------------------------------------
    # The generator wrote nothing (TASK-AB-NOCHANGE01)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # The work was already there (TASK-AB-NOCHANGE01, part 2)
    # ------------------------------------------------------------------

    def _capture_turn_state(
        self,
        turn_record: TurnRecord,
        acceptance_criteria: List[str],
        start_time: Optional[datetime] = None,
        task_id: Optional[str] = None,
        worktree_path: Optional[Path] = None,
    ) -> None:
        """
        Capture turn state for cross-turn learning (TASK-GE-002, TASK-RFX-5FED).

        Creates a TurnStateEntity from the completed turn and saves it to a
        local JSON file for instant cross-turn context loading. The blocking
        The memory-backend write has been replaced with local file persistence.

        Parameters
        ----------
        turn_record : TurnRecord
            Completed turn record with Player and Coach results
        acceptance_criteria : List[str]
            Acceptance criteria for tracking progress
        start_time : Optional[datetime]
            Turn start time (defaults to now - duration if not provided)
        task_id : Optional[str]
            Task identifier for this turn (TASK-GR5-007)
        worktree_path : Optional[Path]
            Path to worktree for local file persistence (TASK-RFX-5FED)

        Notes
        -----
        TASK-RFX-5FED: Replaced blocking memory-backend capture (30s timeout per turn)
        with local file write (<1ms). This saves ~30s per turn (~3.5 minutes on
        a 7-turn run). Local files are read by load_turn_continuation_context().
        """
        # TASK-GLF-002: Skip capture during shutdown to avoid noisy errors
        if getattr(self, '_shutting_down', False):
            logger.debug("Skipping turn state capture (shutting down)")
            return

        try:
            # Use passed task_id or default to "unknown"
            current_task_id = task_id or "unknown"
            # Extract feature_id from task_id (e.g., TASK-GE-001 -> FEAT-GE)
            # or use a default if extraction fails
            feature_id = self._extract_feature_id(current_task_id)

            # Determine turn mode
            if turn_record.turn == 1:
                mode = TurnMode.FRESH_START
            elif self.recovery_count > 0:
                mode = TurnMode.RECOVERING_STATE
            else:
                mode = TurnMode.CONTINUING_WORK

            # Extract player summary from report
            player_summary = "Unknown"
            if turn_record.player_result and turn_record.player_result.report:
                player_summary = turn_record.player_result.report.get(
                    "summary", "Implementation attempt"
                )

            # Extract blockers from Player report
            blockers_found = []
            if turn_record.player_result and turn_record.player_result.report:
                blockers = turn_record.player_result.report.get("blockers", [])
                if isinstance(blockers, list):
                    blockers_found = blockers

            # Extract files_modified from Player report (TASK-GR5-007)
            files_modified = []
            if turn_record.player_result and turn_record.player_result.report:
                modified = turn_record.player_result.report.get("files_modified", [])
                created = turn_record.player_result.report.get("files_created", [])
                # Combine both modified and created files
                if isinstance(modified, list):
                    files_modified.extend(modified)
                if isinstance(created, list):
                    files_modified.extend(created)

            # Extract lessons and next steps from Coach feedback
            lessons = []
            what_to_try_next = None
            if turn_record.coach_result and turn_record.coach_result.report:
                coach_report = turn_record.coach_result.report
                lessons = coach_report.get("lessons", [])
                what_to_try_next = coach_report.get("focus_for_next_turn")

            # Build acceptance criteria status
            ac_status = {}
            if turn_record.coach_result and turn_record.coach_result.report:
                criteria_results = self._criteria_verifications_from_report(
                    turn_record.coach_result.report
                )
                for result in criteria_results:
                    criterion_id = result.get("criterion_id", "")
                    status = result.get("status") or result.get("result", "not_started")
                    if criterion_id:
                        ac_status[criterion_id] = status

            # Extract test metrics
            tests_passed = None
            tests_failed = None
            coverage = None
            arch_score = None

            if turn_record.coach_result and turn_record.coach_result.report:
                tests_passed, tests_failed = self._extract_test_outcome_counts(
                    turn_record
                )

                # Extract architecture score if available
                arch_review = turn_record.coach_result.report.get("architecture_review", {})
                arch_score = arch_review.get("overall_score")
                if arch_score and isinstance(arch_score, (int, float)):
                    arch_score = int(arch_score)
                else:
                    arch_score = None

            # Calculate duration
            end_time = datetime.now()
            if start_time:
                duration_seconds = int((end_time - start_time).total_seconds())
            else:
                duration_seconds = None

            # Create turn state entity
            entity = create_turn_state_from_autobuild(
                feature_id=feature_id,
                task_id=current_task_id,
                turn_number=turn_record.turn,
                player_summary=player_summary,
                player_decision=turn_record.decision if turn_record.decision != "error" else "failed",
                coach_decision=turn_record.decision,
                coach_feedback=turn_record.feedback,
                mode=mode,
                blockers_found=blockers_found,
                progress_summary=f"Turn {turn_record.turn}: {turn_record.decision}",
                acceptance_criteria_status=ac_status,
                files_modified=files_modified,  # TASK-GR5-007: Track files modified
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                coverage=coverage,
                arch_score=arch_score,
                started_at=start_time or end_time,
                completed_at=end_time,
                duration_seconds=duration_seconds,
                lessons_from_turn=lessons if isinstance(lessons, list) else [],
                what_to_try_next=what_to_try_next,
            )

            # TASK-RFX-5FED: Write turn state to local file (<1ms, replaces 30s memory-backend timeout)
            if worktree_path is not None:
                try:
                    autobuild_dir = worktree_path / ".guardkit" / "autobuild" / current_task_id
                    autobuild_dir.mkdir(parents=True, exist_ok=True)
                    state_path = autobuild_dir / f"turn_state_turn_{turn_record.turn}.json"
                    with open(state_path, "w") as f:
                        json.dump(entity.to_episode_body(), f, indent=2)
                    logger.info(f"Turn state saved to local file: {state_path}")
                except Exception as e:
                    logger.warning(f"Failed to save local turn state file: {e}")

        except Exception as e:
            # Graceful degradation - log and continue
            logger.warning(f"Error capturing turn state: {e}")

    def _stop_for_checkpoint_refusal(
        self, task_id: str, refused: CheckpointRefused
    ) -> str:
        """Stop the task because its checkpoint was refused; returns ``"error"``.

        The worktree's HEAD was off the feature branch (build 0D7C, 12 October
        2026), so committing would have put the work where the candidate
        branch never sees it. Another turn cannot fix that: the task stops,
        and the reason — expected branch, actual HEAD, branch tip — becomes
        the task's error (:meth:`_build_error_message`).
        """
        self._checkpoint_refusal = str(refused)
        logger.error("[%s] %s", task_id, refused)
        self._progress_display.console.print(
            f"\n[bold red]STOPPED: {task_id}: checkpoint refused.[/bold red]\n"
            f"  {refused}\n"
        )
        return "error"

    def _extract_feature_id(self, task_id: str) -> str:
        """
        Extract feature ID from task ID.

        Examples:
            TASK-GE-001 -> FEAT-GE
            TASK-XXX-123 -> FEAT-XXX
            TASK-FP002-001 -> FEAT-FP002
            TASK-001 -> FEAT-UNKNOWN

        Parameters
        ----------
        task_id : str
            Task identifier

        Returns
        -------
        str
            Extracted feature ID
        """
        import re

        # Fallback: use self._feature_id if available (takes precedence)
        if hasattr(self, "_feature_id") and self._feature_id:
            return self._feature_id

        # Try to extract prefix from task_id (e.g., TASK-GE-001 -> GE, TASK-FP002-001 -> FP002)
        match = re.match(r"TASK-([A-Z][A-Z0-9]*)-", task_id.upper())
        if match:
            return f"FEAT-{match.group(1)}"

        return "FEAT-UNKNOWN"

    def _display_criteria_progress(
        self,
        turn_record: TurnRecord,
        acceptance_criteria: List[str],
    ) -> None:
        """
        Display progress on acceptance criteria after each turn.

        This method extracts completion promises from the Player report and
        criteria verifications from the Coach decision, then displays a
        progress summary showing which criteria are verified, rejected,
        or still pending.

        Parameters
        ----------
        turn_record : TurnRecord
            Completed turn record with Player and Coach results
        acceptance_criteria : List[str]
            List of acceptance criteria text

        Notes
        -----
        This method is called after each turn in the loop phase to provide
        real-time visibility into criteria completion progress.
        """
        if not acceptance_criteria:
            return

        # Extract promises from Player report
        promises: List[CompletionPromise] = []
        if turn_record.player_result and turn_record.player_result.success:
            promises_data = turn_record.player_result.report.get("completion_promises", [])
            promises = [CompletionPromise.from_dict(p) for p in promises_data]

        # Extract the Coach's verdict rows when it returned them. The LLM-Coach
        # response may omit those presentation rows, so fall back to the
        # deterministic requirements verification already carried in the
        # evidence bundle. This is criterion evidence, not an inference from a
        # passing test count.
        verifications: List[CriterionVerification] = []
        if turn_record.coach_result and turn_record.coach_result.success:
            verifications_data = self._criteria_verifications_from_report(
                turn_record.coach_result.report
            )
            verifications = [CriterionVerification.from_dict(v) for v in verifications_data]

        # Build verification map for quick lookup
        verification_map = {v.criterion_id: v for v in verifications}

        # Calculate progress
        total_criteria = len(acceptance_criteria)
        verified_count = sum(
            1 for v in verifications if v.result == VerificationResult.VERIFIED
        )
        rejected_count = sum(
            1 for v in verifications if v.result == VerificationResult.REJECTED
        )
        claimed_count = sum(v.result == VerificationResult.CLAIMED for v in verification_map.values())
        pending_count = max(0, total_criteria - len(verification_map)) + sum(
            v.result == VerificationResult.PENDING for v in verification_map.values()
        )

        # Calculate percentage
        completion_percentage = calculate_completion_percentage(promises, verifications)

        # Display progress header
        logger.info(
            f"Criteria Progress (Turn {turn_record.turn}): "
            f"{verified_count}/{total_criteria} verified ({completion_percentage:.0f}%)"
        )

        # Log detailed status for each criterion
        for i, criterion_text in enumerate(acceptance_criteria):
            _, natural_id = CoachValidator._extract_ac_id(
                CoachValidator._strip_criterion_prefix(criterion_text)
            )
            criterion_id = natural_id or f"AC-{i+1:03d}"

            # Find matching promise
            promise = next((p for p in promises if p.criterion_id == criterion_id), None)
            verification = verification_map.get(criterion_id)

            if verification:
                if verification.result == VerificationResult.VERIFIED:
                    status = "VERIFIED"
                    icon = "+"
                else:
                    status = verification.result.value.upper()
                    icon = "x" if verification.result == VerificationResult.REJECTED else "?"
            elif promise:
                if promise.status == CriterionStatus.COMPLETE:
                    status = "PROMISED"
                    icon = "~"
                elif promise.status == CriterionStatus.PARTIAL:
                    status = "PARTIAL"
                    icon = "?"
                else:
                    status = "PENDING"
                    icon = " "
            else:
                status = "PENDING"
                icon = " "

            # Truncate criterion text for display
            criterion_short = (
                criterion_text[:50] + "..." if len(criterion_text) > 50 else criterion_text
            )
            logger.debug(f"  [{icon}] {criterion_id}: {status} - {criterion_short}")

        # Display summary via progress display if available
        if hasattr(self, '_progress_display') and self._progress_display:
            summary_lines = [
                f"Criteria: {verified_count} verified, {claimed_count} claimed, {rejected_count} rejected, {pending_count} pending",
            ]

            # Add rejection details if any
            for v in verifications:
                if v.result == VerificationResult.REJECTED:
                    notes_short = v.notes[:60] + "..." if len(v.notes) > 60 else v.notes
                    summary_lines.append(f"  {v.criterion_id}: {notes_short}")

            # Log summary
            for line in summary_lines[:3]:  # Limit to 3 lines for display
                logger.info(line)

    def _get_thread_local_loader(
        self,
        loop: asyncio.AbstractEventLoop,
    ) -> Optional[AutoBuildContextLoader]:
        """Get or create a context loader for the current thread (TASK-FIX-GTP2).

        Creates a fresh memory client initialized on this thread's event loop,
        then wraps it in an AutoBuildContextLoader. Thread-local storage ensures
        each parallel worker gets its own independent client, avoiding the
        cross-loop Neo4j errors that caused hangs in FEAT-6EDD.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the current thread. The memory client's Neo4j
            driver will be bound to this loop.

        Returns
        -------
        Optional[AutoBuildContextLoader]
            A thread-local loader, or None if factory unavailable or init fails.
        """
        # If a DI-provided context_loader exists, use it (for testing)
        if self._context_loader is not None:
            return self._context_loader

        if not self.enable_context or self._factory is None:
            return None

        thread_id = threading.get_ident()
        if thread_id in self._thread_loaders:
            loader, _stored_loop = self._thread_loaders[thread_id]
            return loader

        # TASK-GLF-003: Get client from factory (may be pending-init) and
        # initialize on the consumer's event loop so FalkorDB Locks are affine.
        connection_failed = ("skipped at start-up", "the memory store connection failed")
        try:
            client = self._factory.get_thread_client()
            if client is None:
                self._thread_loaders[thread_id] = (None, loop)
                # The factory gives no client when memory is off or the build
                # has no memory name; its own config says which.
                config = getattr(self._factory, "config", None)
                if config is not None and not getattr(config, "enabled", True):
                    skip = ("off", "FLEET_MEMORY_ENABLED is not set")
                elif config is not None and not getattr(config, "project", "x"):
                    skip = ("unavailable", "this build has no memory name")
                else:
                    skip = ("unavailable", "no memory client for this thread")
                self._note_loader_skip(thread_id, skip)
                logger.info(f"Per-thread memory client not available for thread {thread_id}")
                return None

            # Lazy initialization: if pending, initialize on THIS loop
            if getattr(client, '_pending_init', False):
                success = loop.run_until_complete(client.initialize())
                client._pending_init = False
                if not success:
                    self._thread_loaders[thread_id] = (None, loop)
                    self._note_loader_skip(thread_id, connection_failed)
                    logger.info(f"Per-thread memory client init failed for thread {thread_id}")
                    return None
            elif not client.is_initialized:
                # Client exists but not initialized and not pending — try to init
                success = loop.run_until_complete(client.initialize())
                if not success:
                    self._thread_loaders[thread_id] = (None, loop)
                    self._note_loader_skip(thread_id, connection_failed)
                    logger.info(f"Per-thread memory client init failed for thread {thread_id}")
                    return None

            loader = AutoBuildContextLoader(
                graphiti=client, verbose=self.verbose,
                worktree_path=getattr(self, '_active_worktree_path', None),
                # ONE COPY FOR THE WHOLE DECLARATION (2026-09-21). The memory
                # name was settled from ``self.repo_root`` — the build's own
                # working folder — and everything else this project declares
                # about its memory is now read from that same copy, rather
                # than from whichever per-task worktree happens to be active.
                # Two copies of one file could disagree for a whole build;
                # now there is one.
                declaration_root=self.repo_root,
            )
            self._thread_loaders[thread_id] = (loader, loop)
            logger.info(f"Created per-thread context loader for thread {thread_id}")
            return loader
        except Exception as e:
            self._thread_loaders[thread_id] = (None, loop)
            self._note_loader_skip(
                thread_id,
                ("skipped at start-up", f"setting up the memory reader failed: {e}"),
            )
            logger.warning(f"Error creating per-thread context loader: {e}")
            return None

    def _note_loader_skip(self, thread_id: int, skip: Tuple[str, str]) -> None:
        """Keep why this thread has no loader, for every later turn's line."""
        if getattr(self, "_thread_loader_skips", None) is None:
            self._thread_loader_skips = {}
        self._thread_loader_skips[thread_id] = skip

    def _memory_skip(self) -> Tuple[str, str]:
        """Why this turn has no memory loader: (state, reason)."""
        if not self.enable_context:
            return ("off", "context retrieval is turned off for this build")
        if self._factory is None:
            return ("unavailable", "the memory client could not be loaded")
        return (getattr(self, "_thread_loader_skips", None) or {}).get(
            threading.get_ident(),
            ("unavailable", "no memory reader for this thread"),
        )

    def _log_memory_turn(
        self,
        role: str,
        task_id: str,
        turn: int,
        *,
        result: Any = None,
        skip: Optional[Tuple[str, str]] = None,
        failure: Optional[BaseException] = None,
    ) -> None:
        """Write the one memory line for this role and turn (2026-10-04).

        ONE HONEST LINE PER TURN. It replaces the old "NO memory ... either
        nothing on record or retrieval failed" warning, which could not tell
        those apart, and the "no factory or loader" line, which lost the
        reason. It says one of four things:

        - off (why), at INFO;
        - unavailable (why), at WARNING;
        - skipped at start-up (why), at WARNING;
        - searched: N completed, M failed; K above the line, D delivered.
          WARNING if a search failed, or if records passed the line and none
          was delivered; otherwise INFO.

        Never raises: memory reporting must not stop a build.
        """
        try:
            prefix = f"[Memory] {role} {task_id} turn {turn}: "
            if failure is not None:
                detail = str(failure).strip() or type(failure).__name__
                text, warn = f"searched: failed ({detail}).", True
            elif skip is not None:
                state, reason = skip
                text, warn = f"{state} ({reason}).", state != "off"
            else:
                memory = getattr(result, "memory", None)
                if memory is None:
                    text = "unavailable (the memory reader has no client)."
                    warn = True
                else:
                    text, warn = memory.describe(), memory.needs_attention
            (logger.warning if warn else logger.info)(prefix + text)
        except Exception as exc:  # pragma: no cover - reporting must never raise
            logger.debug(f"Could not write the memory line for {task_id}: {exc}")

    def _cleanup_thread_loaders(self) -> None:
        """Close all per-thread memory clients (TASK-FIX-GTP2, TASK-ACR-005, TASK-ACR-006).

        Called during finalization to clean up resources. Each thread-local
        memory client has its own Neo4j driver that must be closed.

        TASK-ACR-005: Uses stored event loop reference to avoid cross-loop errors.
        TASK-ACR-006: Three-branch cleanup based on loop state to prevent
        RuntimeError when locks are bound to different event loops.
        TASK-GLF-002: Sets _shutting_down flag to suppress late memory operations.
        """
        self._shutting_down = True  # TASK-GLF-002: Prevent late memory ops
        for thread_id, (loader, stored_loop) in list(self._thread_loaders.items()):
            if loader is None or loader.graphiti is None:
                continue
            try:
                if stored_loop.is_running():
                    # Loop still running on worker thread — schedule close there
                    future = asyncio.run_coroutine_threadsafe(
                        loader.graphiti.close(), stored_loop
                    )
                    future.result(timeout=30)
                elif not stored_loop.is_closed():
                    # Loop stopped but open — run directly
                    stored_loop.run_until_complete(loader.graphiti.close())
                else:
                    # Loop already closed — use fresh loop
                    asyncio.run(loader.graphiti.close())
                logger.debug(f"Closed per-thread memory client for thread {thread_id}")
            except RuntimeError as e:
                logger.debug(f"Thread {thread_id} cleanup RuntimeError (suppressed): {e}")
            except concurrent.futures.TimeoutError:
                logger.warning(f"Thread {thread_id} cleanup timed out after 30s (suppressed)")
            except Exception as e:
                logger.warning(f"Error closing per-thread memory client for thread {thread_id}: {e}")
        self._thread_loaders.clear()
        if getattr(self, "_thread_loader_skips", None):
            self._thread_loader_skips.clear()

    # ========================================================================
    # Instrumentation Helpers (TASK-INST-004)
    # ========================================================================

    def _emit_task_started(self, task_id: str) -> None:
        """Emit task.started lifecycle event.

        TASK-OBS-9F43 AC-2: Uses orchestrator's shared run_id for joinability.

        Parameters
        ----------
        task_id : str
            Task identifier being started.
        """
        event = TaskStartedEvent(
            run_id=self._run_id,  # Shared run_id from orchestrator
            task_id=task_id,
            agent_role="player",
            attempt=1,
            timestamp=datetime.now().isoformat(),
        )
        try:
            asyncio.run(self._emitter.emit(event))
        except Exception as exc:
            logger.warning("Failed to emit task.started event: %s", exc)

    def _emit_task_completed(
        self,
        task_id: str,
        turn_history: List["TurnRecord"],
    ) -> None:
        """Emit task.completed lifecycle event on successful orchestration.

        TASK-OBS-9F43 AC-2: Uses orchestrator's shared run_id for joinability.

        Parameters
        ----------
        task_id : str
            Task identifier that completed.
        turn_history : List[TurnRecord]
            Complete turn history for extracting metrics.
        """
        # Determine verification status from last turn decision
        verification_status = "approved"
        if turn_history:
            last_turn = turn_history[-1]
            verification_status = getattr(last_turn, "decision", "approved") or "approved"

        # Build diff_stats summary from turn history
        diff_stats = f"+{len(turn_history)} turns"

        # Use default prompt profile
        prompt_profile = "digest+rules_bundle"

        event = TaskCompletedEvent(
            run_id=self._run_id,  # Shared run_id from orchestrator
            task_id=task_id,
            agent_role="player",
            # attempt is >= 1 by schema (ge=1); clamp for the empty-history edge.
            attempt=max(1, len(turn_history)),  # Final attempt number
            timestamp=datetime.now().isoformat(),
            turn_count=len(turn_history),
            diff_stats=diff_stats,
            verification_status=verification_status,
            prompt_profile=prompt_profile,
        )
        try:
            asyncio.run(self._emitter.emit(event))
        except Exception as exc:
            logger.warning("Failed to emit task.completed event: %s", exc)

    def _emit_task_failed(self, task_id: str, final_decision: str) -> None:
        """Emit task.failed lifecycle event on orchestration failure.

        TASK-OBS-9F43 AC-2: Uses orchestrator's shared run_id for joinability.

        Maps the final_decision to a FailureCategory using FAILURE_CATEGORY_MAP.

        Parameters
        ----------
        task_id : str
            Task identifier that failed.
        final_decision : str
            The exit condition / final decision string.
        """
        failure_category = FAILURE_CATEGORY_MAP.get(final_decision, "other")

        event = TaskFailedEvent(
            run_id=self._run_id,  # Shared run_id from orchestrator
            task_id=task_id,
            agent_role="player",
            # attempt is >= 1 by schema (ge=1); an early failure before any
            # turn completes still counts as attempt #1.
            attempt=max(1, len(self._turn_history)),
            timestamp=datetime.now().isoformat(),
            failure_category=failure_category,
        )
        try:
            asyncio.run(self._emitter.emit(event))
        except Exception as exc:
            logger.warning("Failed to emit task.failed event: %s", exc)

    # ========================================================================
    # Memory flywheel: build-outcome capture at every terminal
    # ========================================================================

    def _capture_build_outcome(
        self,
        task_id: str,
        *,
        success: bool,
        final_decision: str,
        turn_history: Optional[List["TurnRecord"]] = None,
        task_title: Optional[str] = None,
        requirements: str = "",
        error: Optional[str] = None,
    ) -> Optional[str]:
        """Publish this build's outcome to memory. Never changes the build.

        Fires at EVERY autobuild terminal — the approved one and every failed
        one. A build that failed is exactly the prior a future gate wants
        ("this was tried and it stopped here"), so failure is recorded with the
        same care as success.

        Degrade rule (the loud-degrade pattern, commit 4c99357d). Memory OFF,
        the writer unreachable, a write that publishes nothing, or a write
        slower than ``OUTCOME_CAPTURE_TIMEOUT_SECONDS`` all produce ONE plain
        log line and nothing else: no exception reaches the caller, nothing is
        retried, and the build's own verdict is untouched. A memory store that
        is down must never turn a green build red or hold a terminal open.

        WHAT THIS SEAM CAN AND CANNOT SEE. A publish is claimed only when the
        write path hands back a key for the episode. Everything under this seam
        is fail-open — the memory client catches every error and returns
        ``None``, and the outcome id is minted before any publish is attempted
        — so an absent exception is not evidence of anything. Reading the
        returned key is what keeps this log line from asserting a send that
        never happened, and it is why a DOWN broker (the likeliest real
        failure) now correctly reports NOT published.

        But the key is NOT a receipt from the store. It is the deterministic
        natural key minted locally before the send, and the publish under it is
        core NATS with no ack (``NATSClient.publish_episode`` → ``nc.publish``).
        So this seam's green line means "the bytes left this process" and
        nothing more: a dark relay, an unmapped or full stream, and a
        relay-side validation refusal all still publish cleanly from here.
        Whether the episode LANDED in the store is fleet-memory's liveness
        fence's question — see
        ``docs/ways-of-working/memory-reconnection-shipped-2026-08-03.md``.
        Do not word this log line as if it answered that.

        Fields are only the ones actually in hand at this seam. Turn count
        becomes ``review_cycles`` (each turn is one coach review). Test counts
        are deliberately NOT sent as ``tests_written``: the turn record carries
        tests *run*, which is a different number, and a wrong number in memory
        is worse than an absent one. The outcome paragraph (see
        ``outcome_lessons.compose_outcome_lessons``) is sent twice, as
        ``summary`` and as the single ``lessons_learned`` line, because the
        writer's build_outcome payload drops ``summary`` and keeps ``lessons``.

        Parameters
        ----------
        task_id : str
            Task identifier this build was for.
        success : bool
            True only for the approved terminal.
        final_decision : str
            The terminal label (e.g. "approved", "pre_loop_blocked").
        turn_history : Optional[List[TurnRecord]]
            Turns completed before the terminal (empty for early terminals).
        task_title : Optional[str]
            Human-readable task title; falls back to the task id.
        requirements : str
            The task requirements this build worked from.
        error : Optional[str]
            Why the build stopped, when it stopped without approval.

        Returns
        -------
        Optional[str]
            The outcome id when the episode was actually published to the
            broker, else None. Never proof that the store has it.
        """
        try:
            # Remember which terminal this build has now recorded, so a later
            # crash can say what it supersedes. Set on ATTEMPT, not on publish:
            # the question the crashed record answers is "was an earlier
            # terminal already reached?", which is true whether or not the
            # broker was up. "crashed" itself is never recorded here — a crash
            # cannot supersede itself.
            # Read before it is updated below: a crash names the terminal it
            # overtook (see _crash_outcome_reason).
            supersedes_note = (
                self._superseded_terminal_note() if final_decision == "crashed" else ""
            )
            if final_decision != "crashed":
                self._last_captured_terminal = final_decision

            # Inside the guard on purpose (coach residue, 2026-08-07): the
            # stated promise is "no exception reaches the caller", and these
            # two lines were one refactor away from breaking it.
            turns = list(turn_history or [])
            turn_count = len(turns)
            client = get_memory_client()
            if client is None or not getattr(client, "enabled", False):
                logger.warning(
                    "memory: build outcome NOT published for %s (ended '%s') — "
                    "memory is OFF or the client is unavailable, so this build "
                    "teaches future builds nothing. Set FLEET_MEMORY_ENABLED=true, "
                    "with FLEET_MEMORY_MCP_URL (the memory door) or "
                    "FLEET_MEMORY_PG_DSN, to enable.",
                    task_id,
                    final_decision,
                )
                return None

            completed_at = datetime.now()
            started_at = self._orchestrate_started_at
            duration_minutes: Optional[int] = None
            if started_at is not None:
                duration_minutes = max(
                    0, int((completed_at - started_at).total_seconds() // 60)
                )

            title = (task_title or "").strip() or task_id
            feature_id = self._extract_feature_id(task_id)

            # WHAT A LATER BUILD CAN USE (2026-10-04). The old sentence said
            # only that the task finished, and named the build's working
            # folder as if it were the repository. It never scored close
            # enough to any later task to be handed to its builder. This
            # paragraph carries the facts already in hand here: title,
            # feature, how it ended and why, what was asked, the files
            # changed and what the reviewer objected to. It is capped at 500
            # characters and never names the working folder.
            working_folders = [
                str(folder)
                for folder in (
                    getattr(self, "_active_worktree_path", None),
                    self.repo_root,
                )
                if folder
            ]
            # The reason is cut to 120 characters in the paragraph, which
            # would cut off a crash's note about the terminal it supersedes.
            # So that note becomes its own sentence, and the reason is the
            # crash alone.
            paragraph_error = error
            if supersedes_note and error and error.endswith(supersedes_note):
                paragraph_error = error[: -len(supersedes_note)]
            summary = compose_outcome_lessons(
                task_id=task_id,
                title=task_title,
                feature_id=feature_id,
                success=success,
                final_decision=final_decision,
                error=paragraph_error,
                requirements=requirements,
                turns=[turn_facts_from_record(t) for t in turns],
                working_folders=working_folders,
                supersedes=self._last_captured_terminal if supersedes_note else None,
            )
            if success:
                problems: Optional[List[str]] = None
            else:
                problems = [error] if error else [f"Build ended at '{final_decision}'."]

            async def _write() -> OutcomeCapture:
                return await asyncio.wait_for(
                    capture_task_outcome_verified(
                        outcome_type=(
                            OutcomeType.TASK_COMPLETED
                            if success
                            else OutcomeType.TASK_FAILED
                        ),
                        task_id=task_id,
                        task_title=title,
                        task_requirements=(requirements or "")[:4000],
                        success=success,
                        summary=summary,
                        approach_used="guardkit autobuild player/coach loop",
                        problems_encountered=problems,
                        # The writer's build_outcome payload keeps only
                        # status / duration / task_id / lessons / approach —
                        # ``summary`` is dropped on the way into the store
                        # (fleet_memory_payloads._build_outcome). So the one
                        # plain sentence a future gate needs to read back rides
                        # here as well, where it survives.
                        lessons_learned=[summary],
                        review_cycles=turn_count,
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_minutes=duration_minutes,
                        feature_id=feature_id,
                    ),
                    timeout=OUTCOME_CAPTURE_TIMEOUT_SECONDS,
                )

            capture = asyncio.run(_write())

            # The write path below this seam is fail-open all the way down:
            # ``FleetMemoryClient.add_episode`` catches everything and returns
            # None, and the outcome id is minted before any publish is tried.
            # So "no exception" is NOT evidence of a send — the broker being
            # unreachable, which is the likeliest real failure, would otherwise
            # come back here as a quiet success. Claim a publish only when the
            # write path handed back a key.
            if not capture.published:
                logger.warning(
                    "memory: build outcome NOT published for %s (ended '%s') — "
                    "%s. Nothing was sent, so this build teaches future "
                    "builds nothing. The build result is unaffected.",
                    task_id,
                    final_decision,
                    capture.detail or "the memory writer published nothing",
                )
                return None

            # Deliberately "published to the broker", not "stored": the key
            # below is minted locally and the publish carries no ack, so the
            # store's copy is not proven here. See the docstring.
            logger.info(
                "memory: build outcome %s published to the broker for %s "
                "(ended '%s') as %s — store-side landing is not proven here",
                capture.outcome_id,
                task_id,
                final_decision,
                capture.episode_key,
            )
            return capture.outcome_id
        except Exception as exc:
            # One line, no raise. Includes the timeout case — whose str() is
            # empty, so the exception TYPE is named or the line reads
            # "did not complete ()" and an operator cannot tell a timeout from
            # anything else.
            detail = str(exc).strip()
            reason = (
                f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__
            )
            logger.warning(
                "memory: build outcome NOT published for %s (ended '%s') — the "
                "memory writer did not complete (%s). The build result is "
                "unaffected.",
                task_id,
                final_decision,
                reason,
            )
            return None

    def _invoke_player_safely(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[str],
        remaining_budget: Optional[float] = None,
    ) -> AgentInvocationResult:
        """
        Invoke Player agent with comprehensive error handling.

        This helper implements the DRY principle (per architectural review)
        by centralizing Player invocation error handling.

        Parameters
        ----------
        task_id : str
            Task identifier
        turn : int
            Turn number
        requirements : str
            Task requirements
        feedback : Optional[str]
            Optional Coach feedback from previous turn

        Returns
        -------
        AgentInvocationResult
            Result (success or error)

        Notes
        -----
        Always returns a result - never raises. Errors are captured
        in the result's error field.

        Passes max_turns to enable escape hatch pattern when approaching limit.

        Context Retrieval (TASK-GR6-006):
        When enable_context=True, retrieves job-specific context from the memory backend
        including role_constraints, quality_gates, turn_states, and more.
        Context is formatted as prompt text and passed to the Player agent.
        """
        try:
            # AgentInvoker.invoke_player is actually synchronous despite the
            # async def signature - it raises NotImplementedError until SDK available
            import asyncio

            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Retrieve job-specific context if enabled (TASK-GR6-006, TASK-FIX-GTP2)
            # Uses per-thread context loader to avoid cross-loop Neo4j errors
            context_prompt = ""
            self._last_player_context_status = None  # Reset per invocation (TASK-FIX-GCW5)
            thread_loader = self._get_thread_local_loader(loop)
            if self.enable_context and thread_loader is not None:
                try:
                    context_result = loop.run_until_complete(
                        thread_loader.get_player_context(
                            task_id=task_id,
                            feature_id=self._feature_id or "",
                            turn_number=turn,
                            description=requirements,
                            complexity=5,  # TODO: Get from task metadata
                            previous_feedback=feedback,
                        )
                    )
                    context_prompt = context_result.prompt_text
                    self._log_memory_turn("builder", task_id, turn, result=context_result)

                    # Record context status for progress display (TASK-FIX-GCW5)
                    self._last_player_context_status = ContextStatus(
                        status="retrieved",
                        categories_count=len(context_result.categories_populated),
                        budget_used=context_result.budget_used,
                        budget_total=context_result.budget_total,
                    )

                    # Log verbose details if enabled
                    if self.verbose and context_result.verbose_details:
                        logger.info(f"Context retrieval details:\n{context_result.verbose_details}")

                    logger.debug(
                        f"Retrieved Player context for {task_id} turn {turn}: "
                        f"{context_result.budget_used}/{context_result.budget_total} tokens, "
                        f"{len(context_result.categories_populated)} categories"
                    )
                except Exception as e:
                    # Graceful degradation - continue without context
                    logger.warning(f"Failed to retrieve Player context for {task_id}: {e}")
                    self._log_memory_turn("builder", task_id, turn, failure=e)
                    context_prompt = ""
                    self._last_player_context_status = ContextStatus(
                        status="failed", reason=str(e)
                    )
            elif self.enable_context:
                skip = self._memory_skip()
                self._log_memory_turn("builder", task_id, turn, skip=skip)
                self._last_player_context_status = ContextStatus(
                    status="skipped", reason=skip[1]
                )
            else:
                self._log_memory_turn("builder", task_id, turn, skip=self._memory_skip())
                self._last_player_context_status = ContextStatus(status="disabled")

            result = loop.run_until_complete(
                self._agent_invoker.invoke_player(
                    task_id=task_id,
                    turn=turn,
                    requirements=requirements,
                    feedback=feedback,
                    max_turns=self.max_turns,  # Enable escape hatch pattern
                    context=context_prompt,  # Pass job-specific context (TASK-GR6-006)
                    remaining_budget=remaining_budget,  # TASK-VRF-003: Cap SDK timeout at budget
                )
            )
            return result

        except NotImplementedError as e:
            # SDK not yet available - expected during Phase 1a
            logger.warning(f"Player invocation not implemented: {e}")
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=0.0,
                error="SDK integration pending",
            )
        except asyncio.CancelledError as e:
            logger.debug(f"CancelledError caught for {task_id}: {e}")
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=0.0,
                error=f"Cancelled: {str(e)}",
            )
        except UNRECOVERABLE_ERRORS as e:
            # Unrecoverable errors - fail immediately without retrying
            logger.error(f"Unrecoverable error for {task_id}: {e}")
            report: Dict[str, Any] = {"unrecoverable": True}
            if isinstance(e, AgentLaunchRefusedError):
                report["unrecoverable_reason"] = e.reason
                report["launch_refused_profile"] = e.profile
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report=report,
                duration_seconds=0.0,
                error=f"Unrecoverable: {str(e)}",
            )
        except Exception as e:
            # Recoverable errors - may succeed on retry
            logger.warning(f"Recoverable error for {task_id}: {e}", exc_info=True)
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={"unrecoverable": False},
                duration_seconds=0.0,
                error=f"Recoverable: {str(e)}",
            )

    def _invoke_coach_safely(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
        worktree: Worktree,
        acceptance_criteria: Optional[List[str]] = None,
        task_type: Optional[str] = None,
        skip_arch_review: bool = False,
        requires_infrastructure: Optional[List[str]] = None,
        consumer_context: Optional[list] = None,
        remaining_budget: Optional[float] = None,
        wave_size: int = 1,
        behavioural_oracle: Optional[Any] = None,
        component: Optional[str] = None,  # per-component seam
        effective_concurrency: Optional[int] = None,
    ) -> AgentInvocationResult:
        """
        Invoke Coach agent with comprehensive error handling.

        This method uses the lightweight CoachValidator to validate task-work
        quality gate results, achieving 100% code reuse of existing quality gates
        (Option D architecture per TASK-REV-0414).

        Validation Flow:
        1. Try lightweight validation via CoachValidator if task-work results exist
        2. Fallback to SDK invocation if CoachValidator fails or is unavailable

        Parameters
        ----------
        task_id : str
            Task identifier
        turn : int
            Turn number
        requirements : str
            Original task requirements
        player_report : Dict[str, Any]
            Player's report from current turn
        worktree : Worktree
            Worktree instance containing the correct path. In single-task mode,
            this is the task-specific worktree. In feature mode, this is the
            shared feature worktree. Using the actual worktree.path ensures
            Coach finds task_work_results.json at the correct location.
        acceptance_criteria : Optional[List[str]]
            Task acceptance criteria for requirements validation
        task_type : Optional[str], optional
            Task type from task frontmatter (e.g., "implementation", "refactor", "bugfix")
        skip_arch_review : bool, optional
            If True, skip architectural review gate validation. Use when running
            in implement-only mode where Phase 2.5B (Architectural Review) was skipped.
            Default is False.
        requires_infrastructure : Optional[List[str]], optional
            Infrastructure services required (e.g., ["postgresql", "redis"])
        consumer_context : Optional[list], optional
            Consumer context metadata from task frontmatter for format validation
        wave_size : int, optional
            Number of tasks executing in parallel in the current wave (default: 1).
            Passed to CoachValidator to enable test isolation (TASK-ABFIX-005).
        behavioural_oracle : Optional[Any], optional
            Resolved behavioural-oracle declaration. Placed into the task dict
            handed to CoachValidator on BOTH Coach paths (TS-lane D.1a).

        Returns
        -------
        AgentInvocationResult
            Result (success or error)

        Notes
        -----
        Always returns a result - never raises. Errors are captured
        in the result's error field.

        The CoachValidator is preferred over full SDK invocation as it:
        - Reads task-work quality gate results (no reimplementation)
        - Runs independent test verification (trust but verify)
        - Validates requirements satisfaction
        - Provides approve/feedback decision

        Context Retrieval (TASK-GR6-006):
        When enable_context=True, retrieves quality_gate_configs and turn_states
        from the memory backend to inform Coach validation decisions.
        """
        import asyncio

        start_time = time.time()


        # Retrieve job-specific context for Coach if enabled (TASK-GR6-006, TASK-FIX-GTP2)
        # Uses per-thread context loader to avoid cross-loop Neo4j errors
        context_prompt = ""
        self._last_coach_context_status = None  # Reset per invocation (TASK-FIX-GCW5)

        # Project initialisation design (4 October 2026): the project's
        # binding documents, captured once per build from its source commit.
        try:
            project_documents = self._coach_documents_for_turn(task_id, worktree)
        except AgentInvocationError as exc:
            logger.warning(
                "Coach turn %s for %s goes on without the project's documents: %s",
                turn, task_id, exc,
            )
            project_documents = ()

        # Create event loop if needed (required for thread-local loader creation too)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        thread_loader = self._get_thread_local_loader(loop)
        if self.enable_context and thread_loader is not None:
            try:
                context_result = loop.run_until_complete(
                    thread_loader.get_coach_context(
                        task_id=task_id,
                        feature_id=self._feature_id or "",
                        turn_number=turn,
                        description=requirements,
                        complexity=5,  # TODO: Get from task metadata
                        player_report=player_report,
                    )
                )
                context_prompt = context_result.prompt_text
                self._log_memory_turn("reviewer", task_id, turn, result=context_result)

                # Record context status for progress display (TASK-FIX-GCW5)
                self._last_coach_context_status = ContextStatus(
                    status="retrieved",
                    categories_count=len(context_result.categories_populated),
                    budget_used=context_result.budget_used,
                    budget_total=context_result.budget_total,
                )

                # Log verbose details if enabled
                if self.verbose and context_result.verbose_details:
                    logger.info(f"Coach context retrieval details:\n{context_result.verbose_details}")

                logger.debug(
                    f"Retrieved Coach context for {task_id} turn {turn}: "
                    f"{context_result.budget_used}/{context_result.budget_total} tokens, "
                    f"{len(context_result.categories_populated)} categories"
                )
            except Exception as e:
                # Graceful degradation - continue without context
                logger.warning(f"Failed to retrieve Coach context for {task_id}: {e}")
                self._log_memory_turn("reviewer", task_id, turn, failure=e)
                context_prompt = ""
                self._last_coach_context_status = ContextStatus(
                    status="failed", reason=str(e)
                )
        elif self.enable_context:
            skip = self._memory_skip()
            self._log_memory_turn("reviewer", task_id, turn, skip=skip)
            self._last_coach_context_status = ContextStatus(
                status="skipped", reason=skip[1]
            )
        else:
            self._log_memory_turn("reviewer", task_id, turn, skip=self._memory_skip())
            self._last_coach_context_status = ContextStatus(status="disabled")

        return self._invoke_coach_primary(
            task_id=task_id,
            turn=turn,
            requirements=requirements,
            player_report=player_report,
            worktree=worktree,
            acceptance_criteria=acceptance_criteria,
            task_type=task_type,
            skip_arch_review=skip_arch_review,
            requires_infrastructure=requires_infrastructure,
            consumer_context=consumer_context,
            remaining_budget=remaining_budget,
            wave_size=wave_size,
            context_prompt=context_prompt,
            start_time=start_time,
            behavioural_oracle=behavioural_oracle,  # TS-lane D.1a
            component=component,  # per-component seam
            project_documents=project_documents,
            effective_concurrency=effective_concurrency,
        )

    #: The captured set, kept once per BUILD (keyed by the worktree's name: the
    #: task id for a single task, the feature id for a feature) in the
    #: orchestrator-private directory, so every task of a feature and any
    #: resume reuse the same commit and text.
    _COACH_DOCUMENTS_SNAPSHOT = "coach_project_documents_start.json"

    def _captured_coach_documents(self) -> Dict[str, tuple]:
        return self.__dict__.setdefault("_coach_project_documents", {})

    @staticmethod
    def _build_source_commit(worktree: Worktree) -> Tuple[str, str]:
        """The commit this build started from, and how it was found.

        The fork point of the worktree's HEAD and the base branch it was made
        from (``--base-branch``, not the caller's checkout): stable for the
        whole build, whatever the Players commit on the worktree branch. Falls
        back to HEAD, and says so, when the base branch cannot be resolved.
        Raises ``CommittedContentError`` when the worktree is not a git
        checkout.
        """
        from guardkit.lib.committed_content import CommittedContentError, git_text

        path = Path(worktree.path)
        head = git_text(path, "rev-parse", "--verify", "HEAD^{commit}").strip()
        base = getattr(worktree, "base_branch", None) or ""
        try:
            fork = git_text(path, "merge-base", head, base).strip()
            return fork, f"where the worktree branched from {base}"
        except CommittedContentError:
            return head, (
                f"the worktree's HEAD; the base branch {base!r} could not be "
                "resolved"
            )

    @classmethod
    def _coach_documents_snapshot_path(cls, worktree_path: Path) -> Path:
        from guardkit.orchestrator.paths import TaskArtifactPaths

        worktree_path = Path(worktree_path)
        return TaskArtifactPaths.private_artifact_path(
            worktree_path.name, cls._COACH_DOCUMENTS_SNAPSHOT, worktree_path
        )

    @classmethod
    def discard_coach_documents_snapshot(cls, worktree_path: Path) -> None:
        """Forget an earlier build's capture when a NEW build's worktree is made.

        The snapshot is the identity of the build it was captured for; a new
        worktree is a new build, so an older snapshot under the same name
        (kept in the main checkout's private directory) must not be reused.
        """
        try:
            snapshot = cls._coach_documents_snapshot_path(Path(worktree_path))
            if snapshot.exists():
                snapshot.unlink()
        except (OSError, TypeError) as exc:
            logger.warning(
                "Could not clear an earlier Coach documents snapshot for %s (%s)",
                worktree_path, exc,
            )

    def _reuse_coach_documents_snapshot(
        self, task_id: str, worktree: Worktree, snapshot: Path
    ) -> Optional[tuple]:
        """The build's own capture, unchanged, or ``None`` if it cannot be read.

        Codex review round 2, R1: once a build has a snapshot, that snapshot
        IS the build's commit, declaration and documents. A resumed or later
        task reuses it whatever base branch this invocation was given, and
        never replaces it. If the source revision computed now differs, the
        original is still used and the difference is noted in the turn record.
        """
        from dataclasses import replace as _replace

        from guardkit.lib.committed_content import CommittedContentError
        from guardkit.orchestrator.harness.selector import ProjectDocument

        try:
            raw = json.loads(snapshot.read_text(encoding="utf-8"))
            commit = raw["commit"]
            documents = tuple(ProjectDocument(**item) for item in raw["documents"])
        except Exception as exc:  # noqa: BLE001 — unreadable: capture again
            logger.warning(
                "The Coach documents snapshot %s could not be read (%s); reading "
                "the build's commit again", snapshot, exc,
            )
            return None
        if not all(
            hashlib.sha256(d.text.encode("utf-8")).hexdigest() == d.sha256
            for d in documents
        ):
            logger.warning(
                "The Coach documents snapshot %s does not match its own hashes; "
                "reading the build's commit again", snapshot,
            )
            return None
        try:
            now, how = self._build_source_commit(worktree)
        except (CommittedContentError, OSError):
            now, how = None, ""
        if now is not None and now != commit:
            note = (
                f"this invocation's source revision is {now[:12]} ({how}), not "
                f"the build's {commit[:12]}; the build's original capture was used"
            )
            logger.warning("Task %s: %s.", task_id, note)
            documents = tuple(
                _replace(d, captured_from=f"{d.captured_from}; {note}")
                for d in documents
            )
        return documents

    def _capture_coach_project_documents(
        self,
        task_id: str,
        worktree: Worktree,
        *,
        resume: bool = False,
        new_build: bool = False,
    ) -> Optional[str]:
        """Capture the Coach's binding documents once per build, from its commit.

        Review fixes (4 October 2026). The declaration and every document and
        instruction file are read from the COMMITTED content of the commit the
        build started from — the fork point of the worktree and its base
        branch — through the same committed-content reader the seed command
        uses (the design's one reading rule). Not the caller's checkout and not
        the worktree the Players edit.

        The capture is kept once per build. Once it exists it is the build's
        identity: every later task of a feature and any resume reuse it as it
        is, whatever base branch that invocation supplies, and it is never
        replaced. ``new_build`` (this orchestrator made the worktree itself, or
        a new feature worktree was made) discards an older build's snapshot
        first.

        Done before the pre-loop phase and the Player's first turn, so the
        budget, symbolic-link and missing-file checks stop a broken or
        over-budget declaration before any model call. Opt-in is unchanged: a
        project that declares nothing captures nothing.

        Returns ``None`` when the task may proceed, else the refusal sentence.
        """
        from dataclasses import replace as _replace

        from guardkit.lib.committed_content import CommittedContentError
        from guardkit.orchestrator.harness.selector import (
            _declares_required_documents,
            load_project_documents_at_commit,
        )

        path = getattr(worktree, "path", None)
        if not isinstance(path, (str, os.PathLike)):
            # Only a test double has no real path; a Worktree always does.
            self._captured_coach_documents()[task_id] = ()
            return None
        path = Path(path)
        snapshot = self._coach_documents_snapshot_path(path)
        if new_build:
            self.discard_coach_documents_snapshot(path)
        elif snapshot.is_file():
            reused = self._reuse_coach_documents_snapshot(task_id, worktree, snapshot)
            if reused is not None:
                self._captured_coach_documents()[task_id] = reused
                return None

        try:
            commit, how = self._build_source_commit(worktree)
        except (CommittedContentError, OSError) as exc:
            config = path / ".guardkit" / "config.yaml"
            try:
                text = config.read_text(encoding="utf-8")
            except OSError:
                text = None
            if _declares_required_documents(text):
                return (
                    "The project declares binding documents, but the commit this "
                    f"build started from could not be found ({exc}), so they "
                    "cannot be read as committed; the task was not started."
                )
            self._captured_coach_documents()[task_id] = ()
            return None

        try:
            captured = load_project_documents_at_commit(path, commit)
        except AgentInvocationError as exc:
            return str(exc)
        documents = captured.documents
        if documents:
            when = "when the build started"
            if resume:
                # A resumed task with no usable snapshot (the build began before
                # documents were declared, or the snapshot was lost).
                when = "at resume, not at task start (no task-start snapshot was found)"
                logger.warning(
                    "Task %s resumed with binding documents declared but no "
                    "task-start snapshot of them; capturing them now, at resume.",
                    task_id,
                )
            captured_from = (
                f"the committed content of {commit[:12]} ({how}), read {when}"
            )
            if captured.link_notes:
                captured_from += "; " + " ".join(captured.link_notes)
            documents = tuple(
                _replace(d, captured_from=captured_from) for d in documents
            )
        self._captured_coach_documents()[task_id] = documents
        try:
            if documents:
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                snapshot.write_text(
                    json.dumps(
                        {
                            "commit": commit,
                            "base_branch": getattr(worktree, "base_branch", None),
                            "declaration_sha256": captured.declaration_sha256,
                            "documents": [
                                {"path": d.path, "sha256": d.sha256,
                                 "text": d.text, "size": d.size,
                                 "captured_from": d.captured_from}
                                for d in documents
                            ],
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            elif snapshot.exists():
                snapshot.unlink()  # an unreadable earlier snapshot must not linger
        except OSError as exc:
            logger.warning(
                "Could not keep the Coach documents snapshot for %s (%s); the next "
                "task or a resume will read the commit again", path.name, exc,
            )
        return None

    def _load_protected_reference(self, worktree: Worktree) -> Optional[str]:
        """Read the build's protected paths from the commit it started from.

        17 October 2026. Read from the committed ``.guardkit/config.yaml`` of
        :meth:`_build_source_commit`, never from the worktree the Player can
        edit. Returns the refusal sentence when a declared path is not in that
        commit (or the commit cannot be found while paths are declared), else
        None. See ``guardkit/orchestrator/protected_paths.py``.
        """
        from guardkit.lib.committed_content import CommittedContentError
        from guardkit.orchestrator.harness.selector import _load_player_project_inputs
        from guardkit.orchestrator.protected_paths import (
            ProtectedPathsError,
            load_protected_reference,
        )

        self._protected_reference = None
        path = getattr(worktree, "path", None)
        if not isinstance(path, (str, os.PathLike)):
            return None  # only a test double has no real path
        try:
            try:
                commit, _how = self._build_source_commit(worktree)
            except (CommittedContentError, OSError) as exc:
                if _load_player_project_inputs(Path(path))["protected_paths"]:
                    return (
                        "The project declares protected paths, but the commit this "
                        f"build started from could not be found ({exc}); the task "
                        "was not started."
                    )
                return None
            from guardkit.orchestrator.head_identity import expected_checkpoint_branch

            branch = (
                self._expected_branch
                if self._expected_branch_pinned
                else expected_checkpoint_branch(
                    Path(path), getattr(worktree, "branch_name", None)
                )
            )
            self._protected_reference = load_protected_reference(
                Path(path), commit, branch
            )
        except (ProtectedPathsError, AgentInvocationError, CommittedContentError) as exc:
            return str(exc)
        return None

    def _restore_protected_paths(
        self,
        task_id: str,
        worktree: Worktree,
        player_result: Optional[AgentInvocationResult] = None,
    ) -> Optional[str]:
        """Put protected paths back as committed; the failure, or None.

        Called before the Coach runs (with the turn's ``player_result``),
        before each checkpoint commit and when the loop ends. Before the
        Coach, a change is reported in the Player report's ``concerns``
        (which the Coach reads) and kept for the next turn's feedback. A
        failure to put a path back stops the task; it is never recovered.
        """
        from guardkit.orchestrator.protected_paths import (
            ProtectedPathsError,
            restore_protected_paths,
        )

        reference = getattr(self, "_protected_reference", None)
        if reference is None or worktree is None:
            return None
        try:
            note = restore_protected_paths(Path(worktree.path), reference)
        except ProtectedPathsError as exc:
            self._protected_paths_failure = f"Task {task_id} stopped: {exc}"
            logger.error("[%s] %s", task_id, exc)
            self._progress_display.console.print(
                f"\n[bold red]STOPPED: {task_id}: protected paths could not be "
                f"put back.[/bold red]\n  {exc}\n"
            )
            return self._protected_paths_failure
        if note:
            logger.warning("[%s] %s", task_id, note)
        if note and player_result is not None:
            concerns = player_result.report.get("concerns")
            player_result.report["concerns"] = [
                *(concerns if isinstance(concerns, list) else []), note
            ]
            self._protected_paths_note = note
        return None

    def _coach_documents_for_turn(self, task_id: str, worktree: Worktree) -> tuple:
        """The captured set for this task, each marked if its worktree copy changed.

        The Coach always gets the captured text. A document whose worktree copy
        now differs (or is gone) carries the copy's hash in
        ``worktree_sha256`` so the turn record says so; the turn is not refused.
        Raises ``AgentInvocationError`` only when no capture exists yet and the
        capture made now fails.
        """
        from dataclasses import replace as _replace

        captured = self._captured_coach_documents().get(task_id)
        if captured is None:
            refusal = self._capture_coach_project_documents(task_id, worktree)
            if refusal is not None:
                raise AgentInvocationError(refusal)
            captured = self._captured_coach_documents()[task_id]
        if not captured:
            return ()
        root = Path(worktree.path)
        marked = []
        for document in captured:
            try:
                current = hashlib.sha256((root / document.path).read_bytes()).hexdigest()
            except OSError:
                current = "missing"
            marked.append(
                document
                if current == document.sha256
                else _replace(document, worktree_sha256=current)
            )
        return tuple(marked)

    def _invoke_coach_primary(
        self,
        *,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
        worktree: Worktree,
        acceptance_criteria: Optional[List[str]],
        task_type: Optional[str],
        skip_arch_review: bool,
        requires_infrastructure: Optional[List[str]],
        consumer_context: Optional[list],
        remaining_budget: Optional[float],
        wave_size: int,
        context_prompt: str,
        start_time: float,
        # TS-lane D.1a. Defaulted so a direct caller (and every existing
        # test that calls this path by hand) keeps its current signature.
        behavioural_oracle: Optional[Any] = None,
        component: Optional[str] = None,  # per-component seam
        project_documents: tuple = (),
        effective_concurrency: Optional[int] = None,
    ) -> AgentInvocationResult:
        """The Coach turn: the project's own checks, then the reviewer.

        ``CoachValidator.gather_evidence`` runs the project's checks and
        returns a ``CoachEvidenceBundle``; the reviewer (the LLM Coach) is
        invoked on every turn with it and its verdict is advice (27 October
        2026). When gathering raises, the reviewer runs without the bundle.
        A declared sibling repository's tests that ran and failed send the
        turn back before the reviewer runs (``_evidence_repo_gate``).
        """
        import asyncio

        logger.info("Using LLM Coach (primary) for %s turn %s", task_id, turn)
        if context_prompt:
            logger.info(
                f"[Memory] Coach context provided: {len(context_prompt)} chars"
            )

        coach_cfg = self._load_coach_config()
        # TASK-AB-COACHSUBPROC01: env > config > default (subprocess);
        # logs the active mode + provenance once per validator init.
        coach_test_execution = resolve_coach_test_execution(
            coach_cfg.get("test_execution")
        )
        matching_strategy = coach_cfg.get("matching_strategy", "auto")
        validator = CoachValidator(
            str(worktree.path),
            task_id=task_id,
            coach_test_execution=coach_test_execution,
            matching_strategy=matching_strategy,
            wave_size=wave_size,
            effective_concurrency=effective_concurrency,
            turn=turn,
            model_name=self._model_name,  # TASK-FIX-LGFM3
            coach_model_name=self._coach_model_name,  # TASK-FIX-COACHBUDG01
            venv_python=self._venv_python,  # TASK-FIX-COACHPYENV
            evidence_repos=self._evidence_repos,  # TASK-AB-XREPOEV01 (AC-002)
            smoke_command=self._smoke_command,  # TASK-AB-COACHRUNPARITY01 (arm b)
            smoke_expected_exit=self._smoke_expected_exit,  # TASK-AB-COACHRUNPARITY01 (arm b)
            security_command=getattr(self, "_security_command", None),
            # Whole-feature repair round only; None everywhere else.
            feature_check_repair=self._feature_check_repair,
            in_autobuild_context=True,  # WS3-S1 Q1 SPLIT (hard-abort)
            component=component,  # per-component seam
        )

        # Step 1: gather evidence bundle. Never falls back to validate() on
        # exception; instead emits a synthetic feedback decision.
        try:
            evidence_bundle = validator.gather_evidence(
                task_id=task_id,
                turn=turn,
                task={
                    "acceptance_criteria": acceptance_criteria or [],
                    "task_type": task_type,
                    "requires_infrastructure": requires_infrastructure or [],
                    "_docker_available": validator._is_docker_available(),
                    "consumer_context": consumer_context or [],
                    "description": requirements or "",
                    # TS-lane D.1a: solder the dead wire. This key is the ONLY
                    # thing CoachValidator._extract_command ever looked for,
                    # and no production caller had ever set it — the executor
                    # (_run_shell_command) was built, unit tested and
                    # unreachable. Spread conditionally so a task with no
                    # declaration still hands over the identical six-key dict
                    # it did before this line existed.
                    **(
                        {"behavioural_oracle": behavioural_oracle}
                        if behavioural_oracle
                        else {}
                    ),
                },
                skip_arch_review=skip_arch_review,
                context=context_prompt if context_prompt else None,
            )
        except Exception as exc:  # noqa: BLE001 — the turn goes on without it
            logger.error(
                "gather_evidence raised for %s turn %s: %s. The reviewer runs "
                "without the evidence bundle.",
                task_id, turn, exc, exc_info=True,
            )
            evidence_bundle = None

        if evidence_bundle is not None:
            self._carry_measured_checks(evidence_bundle.independent_tests)

        # Whole-feature repair round (18 October 2026): the bundle carries the
        # project's check — this turn's run, made in gather_evidence, and the
        # attempt that started the round. When gathering stopped early the
        # check was not run, and the record says so; the failed attempt is
        # still shown. Remembered per turn for the loop's early stop, which
        # rests on GuardKit's own run and never on the Player's word.
        self._attach_whole_feature_check(evidence_bundle, turn)

        # Coach v3 Step 1 (coach-finetune training-data enabler): persist the
        # INPUT evidence bundle in the orchestrator-private directory.
        # coach_turn_N.json records only the Coach's OUTPUT (decision/issues/
        # criteria/rationale); the CoachEvidenceBundle that DROVE the verdict was
        # never saved, which forced lossy reconstruction at harvest time and made
        # the harvest train the Coach on player_report ONLY (the train!=serve
        # mismatch). Saving it here yields production-faithful (prompt-with-bundle
        # -> verdict) pairs for every future run. Written right after
        # gather_evidence so a turn blocked by a downstream gate still records its
        # bundle. Best-effort: a write failure must never block the turn.
        # TASK-SBHO-002: relocation removes the casual read, not a determined
        # process; full enforcement = the sandbox lane.
        try:
            from guardkit.orchestrator.paths import TaskArtifactPaths

            _evidence_path = TaskArtifactPaths.private_artifact_path(
                task_id, f"coach_evidence_turn_{turn}.json", worktree.path
            )
            _evidence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_evidence_path, "w") as _evidence_f:
                json.dump(
                evidence_bundle.to_dict() if evidence_bundle is not None else None,
                _evidence_f, indent=2, default=str,
            )
            logger.debug("Persisted coach evidence bundle to %s", _evidence_path)
        except Exception as _evidence_exc:  # noqa: BLE001 — persistence must never block the turn
            logger.warning(
                "Failed to persist coach evidence bundle for %s turn %s: %s",
                task_id, turn, _evidence_exc,
            )

        # TASK-AB-XREPOEV01 (AC-002): run the Coach's independent tests in any
        # declared sibling repo, attach the results to the evidence bundle (so
        # they reach coach_turn_N.json and the Coach prompt), and block the
        # turn deterministically when a declared sibling suite failed or could
        # not run. A red sibling suite must not be approved over by the LLM
        # Coach's leniency (the BDDW-002 false-green). Shared with the legacy
        # path via _evidence_repo_gate so neither Coach implementation can
        # bypass it.
        gate_result = self._evidence_repo_gate(
            validator, task_id, turn, worktree, start_time, bundle=evidence_bundle
        )
        if gate_result is not None:
            return gate_result

        # Step 2: invoke LLM Coach via AgentInvoker, threading the bundle.
        # Part C (this PR) extends invoke_coach + _build_coach_prompt to
        # accept and render evidence_bundle; the call below tolerates Part C
        # not yet landing by guarding the kwarg behind a signature probe.
        try:
            try:
                invoke_kwargs: Dict[str, Any] = {
                    "task_id": task_id,
                    "turn": turn,
                    "requirements": requirements,
                    "player_report": player_report,
                    "remaining_budget": remaining_budget,
                }
                # TASK-HMIG-008R Part B/C: pass evidence_bundle to the SDK
                # invoker. The kwarg is consumed by Part C's extended
                # _build_coach_prompt. If Part C has not landed yet (the
                # SDK invoker still uses the legacy signature), drop the
                # kwarg so the call still works — the LLM Coach will run
                # without the structured bundle and compute honesty itself
                # from player_report, which is the pre-HMIG-008R behaviour.
                import inspect as _inspect

                try:
                    _sig = _inspect.signature(self._agent_invoker.invoke_coach)
                except Exception:  # noqa: BLE001 — call with the plain kwargs
                    _sig = _inspect.Signature()
                if "evidence_bundle" in _sig.parameters:
                    invoke_kwargs["evidence_bundle"] = evidence_bundle
                if "coach_context" in _sig.parameters and context_prompt:
                    invoke_kwargs["coach_context"] = context_prompt
                # Project initialisation design (4 October 2026): the
                # project's binding documents, never dropped silently.
                if project_documents and "project_documents" in _sig.parameters:
                    invoke_kwargs["project_documents"] = project_documents
                # The build reviewer design of 29 October 2026: located
                # findings get one repair turn only when a turn is left.
                if "turn_left" in _sig.parameters:
                    invoke_kwargs["turn_left"] = turn < self.max_turns
                # TASK-ARCH-COACHBFULL (AC-4 / AC-1): thread structured ACs into
                # the Coach prompt so the synthesis verdict can populate
                # criteria_verification per AC (the run-19 empty-array fix) and
                # the look-up pass has the criteria to check against.
                # Normalize the List[str] ACs to [{id,text}],
                # deriving the id with the SAME extractor CoachValidator uses
                # to match Player completion_promises (TASK-CVAC-001) so the
                # Coach's criterion IDs line up with the Player's. Behind a
                # signature probe so a partial rollout never breaks the call.
                if "acceptance_criteria" in _sig.parameters and acceptance_criteria:
                    structured_acs: List[Dict[str, str]] = []
                    for i, criterion_text in enumerate(acceptance_criteria):
                        try:
                            cleaned = validator._strip_criterion_prefix(
                                criterion_text
                            )
                            _, extracted_id = validator._extract_ac_id(cleaned)
                        except Exception:  # noqa: BLE001 — fall back to index ID
                            extracted_id = None
                        structured_acs.append(
                            {
                                "id": extracted_id or f"AC-{i + 1:03d}",
                                "text": str(criterion_text),
                            }
                        )
                    invoke_kwargs["acceptance_criteria"] = structured_acs

                result = asyncio.run(self._agent_invoker.invoke_coach(**invoke_kwargs))
            except RuntimeError as runtime_exc:
                # asyncio.run cannot be called when an event loop is already
                # running (e.g. in a Jupyter context or test that wraps this
                # in its own loop). Fall through to the legacy get_event_loop
                # pattern. The DeprecationWarning is acceptable in this rare
                # case — Phase 2.5 review should-address #4's primary
                # motivation is the per-turn invocation, which uses
                # asyncio.run when possible.
                if "asyncio.run() cannot be called" not in str(runtime_exc):
                    raise
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self._agent_invoker.invoke_coach(**invoke_kwargs)
                )

            # TASK-AB-CKPTGATE01: thread the deterministic gate's test signal
            # from the evidence bundle into the returned report so the
            # checkpoint layer (_extract_tests_passed) records a genuinely
            # passing turn as `pass`, not `unknown` — restoring it as a valid
            # find_last_passing_checkpoint rollback target. No-op when the
            # report already carries the signal or the bundle lacks it. The
            # synthetic-feedback returns above are intentionally NOT enriched
            # (the Coach produced no verdict there → stays UNKNOWN).
            self._merge_evidence_test_signal_into_report(
                result.report, evidence_bundle
            )
            return result

        except Exception as sdk_error:  # noqa: BLE001 — an internal crash
            logger.error(
                "Coach invocation crashed in the primary path: %s",
                sdk_error, exc_info=True,
            )
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=False,
                report={},
                duration_seconds=time.time() - start_time,
                error=f"LLM Coach invocation crashed: {sdk_error}",
            )

    def _evidence_repo_gate(
        self,
        validator: "CoachValidator",
        task_id: str,
        turn: int,
        worktree: Worktree,
        start_time: float,
        bundle: Optional["CoachEvidenceBundle"] = None,
    ) -> Optional[AgentInvocationResult]:
        """Run declared sibling-repo tests (TASK-AB-XREPOEV01 AC-002).

        Runs each declared repo's ``test_command``; attaches the results to
        ``bundle`` (so they reach ``coach_turn_N.json`` and the Coach prompt);
        and returns a feedback result when a declared suite ran and failed.
        Returns None otherwise.
        """
        try:
            results = validator.run_evidence_repo_tests()
        except Exception as exc:  # noqa: BLE001 — sibling tests must not crash Coach
            logger.warning(
                "Evidence-repo test execution failed for %s turn %s: %s "
                "(continuing without sibling-repo gate).",
                task_id, turn, exc,
            )
            return None
        if not results:
            return None
        if bundle is not None:
            try:
                bundle.evidence_repo_tests = [r.to_dict() for r in results]
            except Exception:  # noqa: BLE001 — attachment is best-effort
                pass
        blocking_reason = evidence_repos_lib.evidence_repo_tests_blocking_reason(
            results
        )
        if blocking_reason is None:
            return None
        logger.warning(
            "Sibling-repo tests block %s turn %s:\n%s",
            task_id, turn, blocking_reason,
        )
        return self._emit_synthetic_coach_feedback(
            task_id=task_id,
            turn=turn,
            worktree=worktree,
            rationale=blocking_reason,
            start_time=start_time,
        )

    def _attach_whole_feature_check(
        self, evidence_bundle: Any, turn: int
    ) -> None:
        """Give a repair-round bundle its whole-feature check record.

        Outside a whole-feature repair round this does nothing at all. Inside
        one, ``gather_evidence`` has already run the check on a complete
        gathering; when it did not (gathering stopped early, or the record
        could not be built) the record says the check was not run, with the
        attempt that started the round. Never raises.
        """
        repair = getattr(self, "_feature_check_repair", None)
        if repair is None or evidence_bundle is None:
            return
        try:
            record = getattr(evidence_bundle, "whole_feature_check", None)
            if not isinstance(record, dict):
                from guardkit.orchestrator.feature_check import (
                    whole_feature_check_record,
                )

                status = getattr(evidence_bundle, "gathering_status", None)
                reason = (
                    f"the Coach's evidence stopped early ({status}), so the "
                    "check was not run on this turn's code"
                    if status != "complete"
                    else "the check's record could not be built for this turn"
                )
                record = whole_feature_check_record(repair, skip_reason=reason)
                evidence_bundle.whole_feature_check = record
        except Exception as exc:  # noqa: BLE001 — evidence never fails a turn
            logger.warning(
                "Whole-feature check record not attached for turn %s: %s",
                turn, type(exc).__name__,
            )

    @staticmethod
    def _why_no_player_report_issues(
        task_id: str,
        turn: int,
        player_report: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Must-fix issues explaining why this turn has no coder report.

        One issue at most: the turn ran out of time (with its timings), or,
        failing that, it ended without a report in a working copy other
        tasks share. Empty when the coder wrote its own report.
        """
        if not isinstance(player_report, dict):
            return []
        timeout = player_timeout_from_report(player_report)
        if timeout:
            return [player_timed_out_issue(task_id, turn, timeout)]
        failure = player_report.get("original_failure") or player_report.get("_recovery_metadata", {}).get("original_failure")
        if isinstance(failure, dict) and failure and not failure.get("report_missing_only"):
            return [{"severity": "must_fix", "category": "player_execution_failure",
                     "description": ("The task-work attempt failed: " if failure.get("mode") == "task-work" else "") + f"{failure.get('type', 'ExecutionError')}: {failure.get('message', 'Player failed')}",
                     "suggestion": "Repair the original execution failure; recovered files do not establish completion."}]
        if player_report.get(SHARED_WORKING_COPY_FIELD):
            from guardkit.orchestrator.synthetic_report import (
                player_no_own_report_issue,
            )

            return [player_no_own_report_issue(task_id, turn)]
        return []

    def _implementation_mode(self, task_id: str) -> Optional[str]:
        """The task's implementation mode ("direct" or "task-work"), or
        ``None`` when it cannot be read."""
        if self._agent_invoker is None:
            return None
        try:
            mode = self._agent_invoker._get_implementation_mode(task_id)
        except Exception:  # noqa: BLE001 — wording only; never fail a turn
            return None
        return mode if isinstance(mode, str) else None

    def _player_timeout_feedback(
        self,
        task_id: str,
        turn: int,
        player_result: Optional[AgentInvocationResult],
        recovered_failure_error: Optional[str],
        coach_report: Optional[Dict[str, Any]] = None,
    ) -> str:
        """The timeout must-fix, as feedback text, for a turn whose Player ran
        out of time; ``""`` when it did not, or when the reviewer's report
        already carries a timeout issue (so it is said once).

        Mode-appropriate: a task-work attempt with recovered partial work
        (``recovered_failure_error``) gets the task-work issue; a direct-mode
        turn gets the "ran out of time before writing its report" issue.
        Used on the feedback return and on the reviewer-failed error return.
        The text is meant to be separated from other feedback by a blank
        line, so the feedback file reads it as its own must-fix item.
        """
        issues = (coach_report or {}).get("issues") or []
        if any(
            isinstance(issue, dict)
            and issue.get("category") in _TIMEOUT_ISSUE_CATEGORIES
            for issue in issues
        ):
            return ""
        if recovered_failure_error and not _player_result_timeout(player_result):
            original = self._why_no_player_report_issues(task_id, turn, player_result.report if player_result else {})
            if any(isinstance(i, dict) and i.get("category") == "player_execution_failure" for i in issues):
                return ""
            return self._extract_feedback({"issues": original})
        if recovered_failure_error and self._implementation_mode(task_id) != "direct":
            issue = task_work_timeout_issue(recovered_failure_error)
        else:
            details = _player_result_timeout(player_result)
            if not details or self._implementation_mode(task_id) != "direct":
                return ""
            issue = player_timed_out_issue(task_id, turn, details)
        return self._extract_feedback({"issues": [issue]})

    def _feedback_after_turn_without_work(
        self,
        task_id: str,
        turn: int,
        player_result: Optional[AgentInvocationResult],
    ) -> str:
        """One plain must-fix for a failed turn after which recovery found
        nothing: a timeout with its timings, or no report and no changes.

        A task-work attempt gets task-work wording: it does not write
        player_turn_N.json itself, so the direct-mode advice does not apply.
        """
        details = _player_result_timeout(player_result)
        original = self._why_no_player_report_issues(task_id, turn, player_result.report if player_result else {})
        if original and not details:
            return self._extract_feedback({"issues": original})
        if self._implementation_mode(task_id) == "task-work":
            issue = task_work_no_changes_issue(
                task_id, turn, details, getattr(player_result, "error", None)
            )
        elif details:
            issue = player_timed_out_issue(
                task_id, turn, details, nothing_found=True
            )
        else:
            issue = player_no_report_no_changes_issue(
                task_id, turn, getattr(player_result, "error", None)
            )
        return self._extract_feedback({"issues": [issue]})

    # R1 DE-WIRE (Rich 08-14): _bdd_authoring_sweep_gate
    # (TASK-AB-BDDAUTHOR01) removed — the factory no longer executes
    # pytest-bdd glue sweeps on any Coach path.

    def _emit_synthetic_coach_feedback(
        self,
        *,
        task_id: str,
        turn: int,
        worktree: Worktree,
        rationale: str,
        start_time: float,
        category: str = "evidence_repo_tests_failed",
    ) -> AgentInvocationResult:
        """Write a feedback coach_turn_N.json and return its result.

        Used when a declared sibling repository's tests ran and failed
        (``_evidence_repo_gate``): the turn goes back to the Player with the
        failure, and the reviewer is not run.
        """

        from guardkit.orchestrator.paths import TaskArtifactPaths

        duration = time.time() - start_time
        decision_path = TaskArtifactPaths.private_artifact_path(
            task_id, f"coach_turn_{turn}.json", worktree.path
        )
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        synthetic = {
            "task_id": task_id,
            "turn": turn,
            "decision": "feedback",
            "issues": [
                {
                    "severity": "must_fix",
                    "category": category,
                    "description": rationale,
                },
            ],
            "rationale": rationale,
            "coach_primary_synthetic_feedback": True,
        }
        try:
            with open(decision_path, "w") as f:
                json.dump(synthetic, f, indent=2)
            logger.info(
                "Wrote feedback decision to %s (rationale: %s)",
                decision_path, rationale,
            )
        except OSError as write_exc:
            logger.error(
                "Failed to write feedback decision to %s: %s",
                decision_path, write_exc,
            )

        return AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="coach",
            success=True,
            report=synthetic,
            duration_seconds=duration,
            error=None,
        )

    def _merge_evidence_test_signal_into_report(
        self,
        report: Optional[Dict[str, Any]],
        evidence_bundle: Optional["CoachEvidenceBundle"],
    ) -> Optional[Dict[str, Any]]:
        """Copy this turn's own test run into the reviewer's report.

        The reviewer's report carries only its verdict. The project's own test
        run lives in the evidence bundle; this copies its result
        (``signal_absent``, ``tests_passed``, command, summary) into
        ``report["validation_results"]["independent_tests"]`` so the checkpoint
        layer (``_extract_tests_passed``) records what the run showed, and puts
        the run's failure facts under ``SUITE_RECEIPT_KEY`` for the Player's
        feedback. An orchestrator-side enrichment, never a reviewer write.

        A field already in the report is never overwritten, except
        ``SUITE_RECEIPT_KEY``: whatever the model's report held under that key
        is removed first, so with no independent run there are none. Returns
        the (mutated) ``report``; unchanged when either argument is absent.
        """
        from guardkit.orchestrator.failing_test_feedback import SUITE_RECEIPT_KEY

        if isinstance(report, dict):
            report.pop(SUITE_RECEIPT_KEY, None)
        if not isinstance(report, dict) or evidence_bundle is None:
            return report

        validation = report.get("validation_results")
        if not isinstance(validation, dict):
            validation = {}
            report["validation_results"] = validation

        # The project's own test run (an absent run reads as UNKNOWN).
        independent = evidence_bundle.independent_tests
        if independent is not None:
            indep_dict = validation.get("independent_tests")
            if not isinstance(indep_dict, dict):
                indep_dict = {}
                validation["independent_tests"] = indep_dict
            indep_dict.setdefault("signal_absent", independent.signal_absent)
            indep_dict.setdefault("tests_passed", independent.tests_passed)
            # TASK-AB-NOCHANGE01: carry the command too. A SKIPPED independent
            # run (no tests belonging to this task were found) is recorded as
            # ``tests_passed=True`` with ``signal_absent=False``, so the pass/
            # absent pair alone reads green for a task that was never tested.
            # The command is what tells those apart, and the already-implemented
            # completion path refuses to fire without a real one.
            indep_dict.setdefault("test_command", independent.test_command)
            indep_dict.setdefault(
                "test_output_summary", independent.test_output_summary
            )
            # This turn's own failure facts (command, exit status, first
            # failing lines), taken from the run itself and never from the
            # model's report: they head the Player's feedback when the run
            # failed (build 7010, 12 October 2026).
            receipt_of = getattr(independent, "failure_receipt", None)
            receipt = receipt_of() if callable(receipt_of) else None
            if isinstance(receipt, dict):
                report[SUITE_RECEIPT_KEY] = receipt

        return report

    @staticmethod
    def _criteria_verifications_from_report(
        report: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Return actual per-criterion verification rows from a Coach report.

        Prefer rows authored in the Coach verdict. When that optional display
        field is absent or empty, use the deterministic requirements rows that
        were supplied to the Coach and threaded into validation_results.
        An absent source remains an empty list; callers must not manufacture
        verification from tests, promises, or the final decision.
        """
        coach_rows = report.get("criteria_verification")
        if isinstance(coach_rows, list) and coach_rows:
            return [row for row in coach_rows if isinstance(row, dict)]

        validation = report.get("validation_results")
        if isinstance(validation, dict):
            requirements = validation.get("requirements")
            if isinstance(requirements, dict):
                rows = requirements.get("criteria_results")
                if isinstance(rows, list):
                    requirement_rows = [
                        row for row in rows if isinstance(row, dict)
                    ]
                    if requirement_rows:
                        return requirement_rows

        legacy = report.get("acceptance_criteria_verification")
        if not isinstance(legacy, dict):
            return []
        legacy_rows = legacy.get("criteria_results")
        if not isinstance(legacy_rows, list):
            return []
        return [row for row in legacy_rows if isinstance(row, dict)]

    def _load_coach_config(self) -> Dict[str, Any]:
        """
        Load coach configuration from .guardkit/config.yaml.

        Reads ``autobuild.coach`` section from the config file.

        Returns
        -------
        Dict[str, Any]
            Coach configuration dict, or empty dict if file is missing or invalid.
        """
        config_path = self.repo_root / ".guardkit" / "config.yaml"
        if not config_path.exists():
            return {}

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                return {}
            autobuild_cfg = data.get("autobuild", {})
            if not isinstance(autobuild_cfg, dict):
                return {}
            coach_cfg = autobuild_cfg.get("coach", {})
            return coach_cfg if isinstance(coach_cfg, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to load .guardkit/config.yaml: {e}")
            return {}

    def _build_player_summary(
        self, report: Dict[str, Any], tests_required: bool = True
    ) -> str:
        """
        Build summary string from Player report.

        Parameters
        ----------
        report : Dict[str, Any]
            Player report JSON
        tests_required : bool, optional
            Whether tests are required for this task type. When False and no
            tests were written, displays "tests not required" instead of
            "0 tests (failing)". Defaults to True.

        Returns
        -------
        str
            Formatted summary for display
        """
        files_modified = len(report.get("files_modified", []))
        files_created = len(report.get("files_created", []))
        test_files_reported = len(report.get("tests_written", []))
        tests_passed = report.get("tests_passed", False)
        quality_gates = report.get("quality_gates")
        tests_run = (
            quality_gates.get("tests_run")
            if isinstance(quality_gates, dict)
            else None
        )
        has_explicit_count = (
            isinstance(tests_run, int) and not isinstance(tests_run, bool) and tests_run >= 0
        )

        if has_explicit_count:
            tests_str = f"{tests_run} tests run ({'passing' if tests_passed else 'failing'})"
        elif not tests_required and test_files_reported == 0:
            tests_str = "tests not required"
        else:
            tests_str = (
                f"{test_files_reported} test files reported "
                f"(tests reported {'passing' if tests_passed else 'failing'})"
            )

        return (
            f"{files_created} files created, {files_modified} modified, "
            f"{tests_str}"
        )

    def _resolve_tests_required(self, task_type: Optional[str]) -> bool:
        """Return whether tests are required for the given task type string.

        Resolves the task type string (including legacy aliases) to a
        QualityGateProfile and returns its tests_required flag.

        Parameters
        ----------
        task_type : Optional[str]
            Task type string from task frontmatter (e.g., "feature", "documentation").
            Supports legacy aliases used in coach_validator (e.g., "implementation").

        Returns
        -------
        bool
            True if tests are required (default for unknown/None task types),
            False for task types with tests_required=False in their profile.
        """
        if not task_type:
            return True  # Default FEATURE profile requires tests
        try:
            task_type_enum = TASK_TYPE_ALIASES.get(task_type) or TaskType(task_type)
            return get_quality_gate_profile(task_type_enum).tests_required
        except (ValueError, KeyError):
            return True  # Default to requiring tests for unknown types

    def _turn_feedback_text(
        self, coach_report: Dict[str, Any], turn: int
    ) -> str:
        """The feedback text for the Player after a ``feedback`` decision.

        The Coach's issues (:meth:`_extract_feedback`), preceded — when the
        required test command ran and failed on this turn — by a short plain
        summary copied from that run's own receipt: the turn, the command,
        its exit status and the first failing lines of its output. In build
        7010 (task three, turn four) the reviewer's prose described the
        previous turn's failure while the run in front of it had failed on
        DNS; the Player must always be able to see what this turn's run said.
        """
        from guardkit.orchestrator.failing_test_feedback import (
            SUITE_RECEIPT_KEY,
            describe_independent_suite_failure,
        )

        feedback_text = self._extract_feedback(coach_report)
        # Only the orchestrator writes this key (see SUITE_RECEIPT_KEY).
        receipt = (coach_report or {}).get(SUITE_RECEIPT_KEY)
        summary = describe_independent_suite_failure(turn, receipt)
        if summary:
            return f"{summary}\n\n{feedback_text}"
        return feedback_text

    def _extract_feedback(self, coach_report: Dict[str, Any]) -> str:
        """
        Extract feedback text from Coach decision.

        Parameters
        ----------
        coach_report : Dict[str, Any]
            Coach decision JSON

        Returns
        -------
        str
            Formatted feedback text
        """
        issues = coach_report.get("issues", [])
        if not issues:
            return coach_report.get("rationale", "No specific feedback provided")

        # The reasons the turn was rejected come first, then the rest, each
        # group in the order the Coach gave it (8 October 2026). Before this
        # the first three issues were taken in report order, and in build
        # FEAT-895D all three were honesty warnings, so the failing test,
        # the one must-fix reason, was cut as "... and N more issues" on
        # every turn. Must-fix issues are marked with MUST_FIX_MARKER so the
        # feedback file can list them under must_fix
        # (AgentInvoker._parse_coach_feedback).
        ordered = sorted(
            (issue for issue in issues if isinstance(issue, dict)),
            key=_feedback_issue_order,
        )

        # Build feedback from issues: the top three, or every one when the
        # turn goes back for the reviewer's located findings (the repair turn,
        # the build reviewer design of 29 October 2026).
        from guardkit.orchestrator.build_review import REPAIR_KEY

        limit = len(ordered) if coach_report.get(REPAIR_KEY) else 3
        feedback_lines = []
        for issue in ordered[:limit]:
            desc = issue.get("description", "")
            if _feedback_issue_is_must_fix(issue):
                desc = f"{MUST_FIX_MARKER}{desc}"
            missing = issue.get("missing_criteria", [])

            if missing:
                feedback_lines.append(f"- {desc}:")
                for criterion in missing[:5]:
                    feedback_lines.append(f"  • {criterion[:100]}")
                if len(missing) > 5:
                    feedback_lines.append(f"  ({len(missing) - 5} more)")
            else:
                suggestion = issue.get("suggestion", "")
                test_output = issue.get("test_output", "")

                if suggestion and _feedback_issue_is_must_fix(issue):
                    # On its own marked line, so the feedback file keeps it
                    # as this must-fix item's suggestion (FEAT-2C42).
                    feedback_lines.append(
                        f"- {desc}\n  {SUGGESTION_MARKER}{suggestion}"
                    )
                elif suggestion:
                    feedback_lines.append(f"- {desc}: {suggestion}")
                elif test_output:
                    # Use test output as the actionable detail
                    feedback_lines.append(f"- {desc}:\n  {test_output}")
                else:
                    feedback_lines.append(f"- {desc}")

        if len(ordered) > limit:
            feedback_lines.append(f"... and {len(ordered) - limit} more issues")

        return "\n".join(feedback_lines)

    def _build_feedback_summary(
        self, coach_report: Dict[str, Any], fallback_text: str
    ) -> str:
        """
        Build the operator-visible turn summary from the highest-severity issue.

        Background: ``coach_validator.py`` (lines 1056-1078) prepends an
        ``agent_invocations_advisory`` (severity=warning, non-blocking) to the
        issues list before returning a feedback decision.  The previous inline
        implementation sliced the *joined* feedback text produced by
        ``_extract_feedback``, which meant the advisory always appeared first in
        the 80-char window, hiding the real ``must_fix`` issue from the operator
        log.

        This method reads ``coach_report["issues"]`` directly, picks the
        highest-severity issue (must_fix > should_fix > warning), and uses its
        ``description`` field for the summary.  ``_extract_feedback`` builds
        the Player's text separately, ordered by the same rank
        (:func:`_feedback_issue_rank`), so this one-line summary and the
        first issue the Player reads agree.

        Parameters
        ----------
        coach_report : Dict[str, Any]
            Coach decision JSON (same object passed to ``_extract_feedback``).
        fallback_text : str
            The text returned by ``_extract_feedback`` (used when no issues are
            present or all descriptions are empty).

        Returns
        -------
        str
            Operator-visible summary string, e.g. ``"Feedback: Plan audit …"``.
        """
        issues = coach_report.get("issues") or []
        if issues:
            primary = min(issues, key=_feedback_issue_order)
            description = primary.get("description", "") or ""
            if description:
                if len(description) > 80:
                    return f"Feedback: {description[:80]}..."
                return f"Feedback: {description}"

        # No issues or empty description — fall back to slicing the joined text
        if len(fallback_text) > 80:
            return f"Feedback: {fallback_text[:80]}..."
        return f"Feedback: {fallback_text}"

    def _build_summary_details(
        self,
        turn_history: List[TurnRecord],
        final_decision: Literal["approved", "max_turns_exceeded", "error", "cancelled", "timeout", "timeout_budget_exhausted", "pre_loop_blocked", "design_extraction_failed"],
    ) -> str:
        """
        Build detailed summary text for final report.

        Parameters
        ----------
        turn_history : List[TurnRecord]
            Complete turn history
        final_decision : Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked", "design_extraction_failed"]
            Final orchestration decision

        Returns
        -------
        str
            Formatted summary details
        """

        if final_decision == "approved":
            return (
                f"Coach approved implementation after {len(turn_history)} turn(s).\n"
                f"Worktree preserved at: {self._worktree_manager.worktrees_dir}\n"
                f"Review and merge manually when ready."
            )

        elif final_decision == "max_turns_exceeded":
            return (
                f"Maximum turns ({self.max_turns}) reached without approval.\n"
                f"Worktree preserved for inspection.\n"
                f"Review implementation and provide manual guidance."
            )

        elif final_decision == "pre_loop_blocked":
            return (
                f"Pre-loop quality gates blocked execution.\n"
                f"Either architectural review failed or human checkpoint rejected.\n"
                f"Worktree preserved for review. Check pre_loop_result for details."
            )

        elif final_decision == "design_extraction_failed":
            return (
                f"Phase 0 design extraction failed.\n"
                f"MCP tools may be unavailable or design URL may be invalid.\n"
                f"Worktree preserved for review.\n"
                f"Suggested action: Verify MCP tools are configured in claude_desktop_config.json."
            )

        elif final_decision == "timeout":
            task_timeout_str = f"{self._task_timeout}s" if self._task_timeout else "feature budget"
            return (
                f"Task timed out (feature-level timeout) after {len(turn_history)} turn(s).\n"
                f"Feature timeout: {task_timeout_str}. SDK timeout budget: {self.sdk_timeout}s per invocation.\n"
                f"Worktree preserved for inspection.\n"
                f"Review partial implementation and resume manually if needed."
            )

        elif final_decision == "cancelled":
            return (
                f"Task cancelled via cooperative cancellation (stop_on_failure) after {len(turn_history)} turn(s).\n"
                f"Worktree preserved for inspection.\n"
                f"Review partial implementation and resume manually if needed."
            )

        elif final_decision == "timeout_budget_exhausted":
            # TASK-FIX-TBXMSG01: this is a clean, well-classified budget
            # exhaustion (the loop refused to start a turn it could not
            # finish), NOT an unknown crash. Name the cause and quote the
            # turns-used and remaining-vs-minimum so the operator does not
            # go chasing a non-existent error.
            remaining = getattr(self, "_timeout_budget_remaining", None)
            remaining_str = (
                f"remaining={remaining:.1f}s"
                if remaining is not None
                else "remaining budget unknown"
            )
            return (
                f"Time budget exhausted after {len(turn_history)} turn(s).\n"
                f"The task's wall-clock budget fell below the per-turn minimum "
                f"({remaining_str} < min={MIN_TURN_BUDGET_SECONDS}s), so no "
                f"further turn could start. This is a clean budget-exhaustion "
                f"exit, not a crash.\n"
                f"Worktree preserved for inspection.\n"
                f"Resume with a larger feature/task timeout budget if needed."
            )

        else:  # error
            error_turn = next(
                (t for t in reversed(turn_history) if t.decision == "error"), None
            )
            if error_turn:
                error_msg = (
                    error_turn.coach_result.error
                    if error_turn.coach_result
                    else error_turn.player_result.error
                )
                return (
                    f"Critical error on turn {error_turn.turn}:\n"
                    f"{error_msg}\n"
                    f"Worktree preserved for debugging."
                )
            else:
                return "Unknown error occurred. Worktree preserved for inspection."

    def _build_error_message(
        self,
        final_decision: Literal["approved", "max_turns_exceeded", "error", "cancelled", "timeout", "timeout_budget_exhausted", "pre_loop_blocked", "design_extraction_failed"],
        turn_history: List[TurnRecord],
    ) -> str:
        """
        Build error message for OrchestrationResult.

        Parameters
        ----------
        final_decision : Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked", "design_extraction_failed"]
            Final orchestration decision
        turn_history : List[TurnRecord]
            Complete turn history

        Returns
        -------
        str
            Error message (empty string for approved)
        """
        if final_decision == "max_turns_exceeded":
            return f"Maximum turns ({self.max_turns}) exceeded without approval"




        elif final_decision == "pre_loop_blocked":
            return "Pre-loop quality gates blocked execution"

        elif final_decision == "design_extraction_failed":
            return "Phase 0 design extraction failed - MCP tools unavailable or design URL invalid"

        elif final_decision == "timeout":
            task_timeout_str = f"{self._task_timeout}s" if self._task_timeout else "feature budget"
            return (
                f"Task timed out (feature-level) after {len(turn_history)} turn(s). "
                f"Feature timeout: {task_timeout_str}, SDK timeout: {self.sdk_timeout}s per invocation."
            )

        elif final_decision == "cancelled":
            return (
                f"Task cancelled via cooperative cancellation (stop_on_failure) after "
                f"{len(turn_history)} turn(s)"
            )

        elif final_decision == "timeout_budget_exhausted":
            # TASK-FIX-TBXMSG01: a clean budget exhaustion must not surface as
            # an empty error string (which reads as "no error"). Name the
            # cause and quote turns-used + remaining-vs-minimum.
            remaining = getattr(self, "_timeout_budget_remaining", None)
            remaining_str = (
                f"remaining={remaining:.1f}s"
                if remaining is not None
                else "remaining budget unknown"
            )
            return (
                f"Time budget exhausted after {len(turn_history)} turn(s): "
                f"{remaining_str} < min={MIN_TURN_BUDGET_SECONDS}s per turn"
            )

        elif final_decision == "error":
            checkpoint_refusal = getattr(self, "_checkpoint_refusal", None)
            if checkpoint_refusal:
                return checkpoint_refusal
            protected_failure = getattr(self, "_protected_paths_failure", None)
            if protected_failure:
                return protected_failure
            error_turn = next(
                (t for t in reversed(turn_history) if t.decision == "error"), None
            )
            if error_turn:
                return (
                    error_turn.coach_result.error
                    if error_turn.coach_result
                    else error_turn.player_result.error or "Unknown error"
                )
            return "Unknown error occurred"

        return ""  # No error for approved

    # ========================================================================
    # State Persistence Methods
    # ========================================================================

    def _resume_from_state(
        self,
        task_id: str,
        task_file_path: Path,
    ) -> Tuple[Worktree, int]:
        """
        Continue the retained owner without trusting saved task frontmatter.

        Parameters
        ----------
        task_id : str
            Task identifier
        task_file_path : Path
            Path to task file with saved state

        Returns
        -------
        Tuple[Worktree, int]
            Tuple of (worktree, start_turn)

        Raises
        ------
        SetupPhaseError
            If state cannot be loaded or worktree doesn't exist
        """
        scope = self.task_work_scope
        logger.info(f"Resuming orchestration for {task_id} from {task_file_path}")

        try:
            # The scope this run admitted is the continuation state.
            worktree = Worktree(
                task_id=task_id,
                branch_name=scope.repositories[0].branch,
                path=Path(scope.repositories[0].root),
                base_branch=scope.baseline_commit,
            )

            # Initialize AgentInvoker with worktree path
            if self._agent_invoker is None:
                self._agent_invoker = AgentInvoker(
                    worktree_path=worktree.path,
                    max_turns_per_agent=self.max_turns,
                    development_mode=self.development_mode,
                    sdk_timeout_seconds=self.sdk_timeout,
                    sdk_timeout_is_override=self._sdk_timeout_is_override,
                    use_task_work_delegation=True,
                    cancellation_event=self._cancellation_event,  # TASK-FIX-ASPF-004
                    venv_python=self._venv_python,  # TASK-FIX-7A05
                    model_name=self._model_name,  # TASK-FIX-MODELPLUMB
                    coach_model_name=self._coach_model_name,  # TASK-FIX-COACHBUDG01
                    evidence_repos=self._evidence_repos,  # TASK-AB-XREPOEV01
                    emitter=self._emitter,  # TASK-OBS-4899
                )
            # TASK-FIX-OBS2: Attach progress logger to agent invoker
            if self._progress_logger and self._agent_invoker:
                self._agent_invoker.set_progress_logger(self._progress_logger)

            # Calculate next turn
            start_turn = len(self._turn_history) + 1

            logger.info(
                f"Resumed from state: {len(self._turn_history)} turns completed, "
                f"starting from turn {start_turn}"
            )

            return worktree, start_turn

        except SetupPhaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to load state: {e}", exc_info=True)
            raise SetupPhaseError(f"Failed to resume: {e}") from e

    def _save_state(
        self,
        task_file_path: Path,
        worktree: Worktree,
        status: str,
    ) -> None:
        """
        Save orchestration state to task frontmatter.

        Parameters
        ----------
        task_file_path : Path
            Path to task file
        worktree : Worktree
            Current worktree
        status : str
            Task status (in_progress, in_review, blocked)
        """
        logger.debug(f"Saving state to {task_file_path}")

        try:
            with open(task_file_path, "r") as f:
                content = f.read()

            # Parse frontmatter
            if not content.startswith("---"):
                logger.warning("Task file missing frontmatter, skipping state save")
                return

            parts = content.split("---", 2)
            if len(parts) < 3:
                logger.warning("Invalid task file format, skipping state save")
                return

            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2]

            # Update status
            frontmatter["status"] = status

            # Build autobuild state
            frontmatter["autobuild_state"] = {
                "current_turn": len(self._turn_history),
                "max_turns": self.max_turns,
                "worktree_path": str(worktree.path),
                "base_branch": worktree.base_branch,
                "started_at": (
                    self._turn_history[0].timestamp
                    if self._turn_history
                    else datetime.now().isoformat()
                ),
                "last_updated": datetime.now().isoformat(),
                "turns": self._serialize_turn_history(),
            }

            # Write back
            with open(task_file_path, "w") as f:
                f.write("---\n")
                f.write(yaml.dump(frontmatter, default_flow_style=False, sort_keys=False))
                f.write("---")
                f.write(body)

            logger.debug(f"State saved: {len(self._turn_history)} turns, status={status}")

        except Exception as e:
            logger.warning(f"Failed to save state: {e}")
            # Don't raise - state persistence is best-effort

    def _serialize_turn_history(self) -> List[Dict[str, Any]]:
        """
        Serialize turn history to JSON-compatible format for YAML storage.

        Returns
        -------
        List[Dict[str, Any]]
            Serialized turn history
        """
        # TASK-AB-SECRETSCRUB01: the task file is TRACKED, so this is a
        # publication boundary — captured output (Coach feedback, Player
        # notes/errors) is scrubbed here, never at the oracle (the Coach
        # verdicts on the raw gitignored evidence). Scrub BEFORE truncation
        # so a truncation cut can never expose a partial secret.
        serialized = []
        for record in self._turn_history:
            if record.player_result.success:
                player_summary = scrub_for_publication(
                    record.player_result.report.get("implementation_notes", "")
                )
                if player_summary is not None:
                    player_summary = player_summary[:500]
            else:
                player_summary = scrub_for_publication(record.player_result.error)
            serialized.append({
                "turn": record.turn,
                "decision": record.decision,
                "feedback": scrub_for_publication(record.feedback),
                "timestamp": record.timestamp,
                "player_summary": player_summary,
                "player_success": record.player_result.success,
                "coach_success": record.coach_result.success if record.coach_result else False,
                # FEAT-2C42: kept so a resumed run landing on a fresh-start
                # turn still passes the timeout must-fix on.
                "timeout_note": scrub_for_publication(
                    getattr(record, "timeout_note", None)
                ),
            })
        return serialized

    def _deserialize_turn_history(
        self,
        saved_turns: List[Dict[str, Any]],
    ) -> List[TurnRecord]:
        """
        Deserialize turn history from saved state.

        Note: This creates minimal TurnRecord objects since we don't store
        full report data. The records are sufficient for resume logic.

        Parameters
        ----------
        saved_turns : List[Dict[str, Any]]
            Serialized turn data from frontmatter

        Returns
        -------
        List[TurnRecord]
            Deserialized turn records
        """
        records = []
        for turn_data in saved_turns:
            # Create minimal player result
            player_result = AgentInvocationResult(
                task_id="",  # Not needed for resume
                turn=turn_data.get("turn", 0),
                agent_type="player",
                success=turn_data.get("player_success", False),
                report={"implementation_notes": turn_data.get("player_summary", "")},
                duration_seconds=0.0,
                error=None if turn_data.get("player_success") else turn_data.get("player_summary"),
            )

            # Create minimal coach result if applicable
            coach_result = None
            if turn_data.get("coach_success") is not None:
                coach_result = AgentInvocationResult(
                    task_id="",
                    turn=turn_data.get("turn", 0),
                    agent_type="coach",
                    success=turn_data.get("coach_success", False),
                    report={"decision": turn_data.get("decision", "feedback")},
                    duration_seconds=0.0,
                    error=None,
                )

            record = TurnRecord(
                turn=turn_data.get("turn", 0),
                player_result=player_result,
                coach_result=coach_result,
                decision=turn_data.get("decision", "feedback"),
                feedback=turn_data.get("feedback"),
                timestamp=turn_data.get("timestamp", ""),
                timeout_note=turn_data.get("timeout_note"),
            )
            records.append(record)

        return records

    def _get_last_feedback(self) -> Optional[str]:
        """
        Get feedback from the last turn in history.

        Returns
        -------
        Optional[str]
            Last feedback text, or None if no history
        """
        if self._turn_history:
            return self._turn_history[-1].feedback
        return None

    def _extract_tests_passed(self, turn_record: TurnRecord) -> Optional[bool]:
        """
        Extract the tri-state test signal from a turn record for checkpointing.

        Returns
        -------
        Optional[bool]
            - ``True``  — a test oracle ran and passed.
            - ``False`` — a test oracle ran and failed.
            - ``None``  — UNKNOWN: no authoritative test verdict is available
              for this turn.

        Why tri-state (TASK-FIX-CKPTTESTRED01)
        --------------------------------------
        This signal feeds ``WorktreeCheckpointManager.create_checkpoint`` and,
        through it, the consecutive-failure pollution detector. The default
        Coach is now the LLM Coach (TASK-HMIG-008R), whose ``coach_result.report``
        carries ``{decision, issues, criteria_verification, rationale}`` — it
        does NOT carry ``validation_results.quality_gates``. The deterministic
        quality gate (which logs ``tests=True``) lives in the Coach evidence
        bundle, not in this report. Collapsing that absent signal to ``False``
        recorded every LLM-Coach feedback turn as ``tests: fail`` and triggered
        a spurious ``unrecoverable_stall`` from "3 consecutive test failures"
        even though tests existed and passed (FEAT-9DDE run 5).

        Returning ``None`` for an absent signal — instead of ``False`` — lets
        the pollution detector treat it as absent evidence rather than a
        failure. This is the checkpoint-layer instance of
        ``.claude/rules/absence-of-failure-is-not-success.md``. It supersedes
        the ``None → False`` coercion introduced by TASK-FIX-64EE for the
        *absent-signal* case; a genuine ``tests_passed is False`` (oracle ran
        and failed) still records as a failure.

        Args:
            turn_record: Turn record with Coach validation results

        Returns:
            Tri-state test signal (see above).
        """
        # No Coach verdict object at all (Coach invocation failed → "error"
        # turn, which returns before a checkpoint is created). Conservative
        # ``False`` preserves the existing no-coach-result contract; it does
        # not reach the pollution tally in practice.
        if not turn_record.coach_result or not turn_record.coach_result.success:
            return False

        validation = turn_record.coach_result.report.get("validation_results", {}) or {}

        # An explicitly-absent independent-test signal (the trust-but-verify
        # leg never produced a verdict — SDK/subprocess timeout or transport
        # error) is UNKNOWN, never a failure. Mirrors IndependentTestResult.
        independent = validation.get("independent_tests") or {}
        if independent.get("signal_absent") is True:
            return None

        # Primary path: quality_gates.tests_passed (deterministic Coach gate).
        quality_gates = validation.get("quality_gates") or {}
        if "tests_passed" in quality_gates:
            value = quality_gates.get("tests_passed")
            return None if value is None else bool(value)

        # The project's own test run, copied in by
        # _merge_evidence_test_signal_into_report.
        if "tests_passed" in independent:
            value = independent.get("tests_passed")
            return None if value is None else bool(value)

        # Fallback: top-level tests_passed (backward compatibility).
        if "tests_passed" in validation:
            value = validation.get("tests_passed")
            return None if value is None else bool(value)

        # No authoritative test verdict in the report (e.g. the LLM-Coach
        # path, whose report omits validation_results). UNKNOWN, not failure.
        return None

    def _extract_test_outcome_counts(
        self,
        turn_record: TurnRecord,
    ) -> Tuple[Optional[int], Optional[int]]:
        """Return observed passed/failed counts without inventing outcomes.

        A parsed pytest summary supplies observed outcome counts. Otherwise,
        only explicit integer passed/failed fields are returned independently.
        Aggregate totals and Boolean verdicts never imply a passed count:
        skipped, xfailed, errors, or an unknown split may occupy that total.
        """
        if not turn_record.coach_result or not turn_record.coach_result.success:
            return None, None

        validation = turn_record.coach_result.report.get("validation_results", {})
        if not isinstance(validation, dict):
            return None, None

        independent = validation.get("independent_tests")
        if isinstance(independent, dict) and independent.get("signal_absent") is True:
            return None, None

        def valid_count(value: Any) -> bool:
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
            )

        from guardkit.lib.pytest_summary import parse_pytest_summary

        summaries = []
        if isinstance(independent, dict):
            summaries.append(independent.get("test_output_summary"))
        summaries.append(validation.get("test_output_summary"))
        for output in summaries:
            parsed = parse_pytest_summary(output if isinstance(output, str) else None)
            if parsed.passed is not None and parsed.tests_failed is not None:
                return parsed.passed, parsed.tests_failed

        tests = validation.get("tests")
        if not isinstance(tests, dict):
            return None, None
        candidate_passed = tests.get("tests_passed")
        candidate_failed = tests.get("tests_failed")
        observed_passed = (
            candidate_passed if valid_count(candidate_passed) else None
        )
        observed_failed = (
            candidate_failed if valid_count(candidate_failed) else None
        )
        return observed_passed, observed_failed

    def _extract_test_count(self, turn_record: TurnRecord) -> int:
        """
        Extract test count from turn record.

        Args:
            turn_record: Turn record with test results

        Returns:
            Number of tests run (0 if no tests)
        """
        if not turn_record.coach_result or not turn_record.coach_result.success:
            return 0

        validation = turn_record.coach_result.report.get("validation_results", {})
        if not isinstance(validation, dict):
            return 0

        independent = validation.get("independent_tests")
        if isinstance(independent, dict) and independent.get("signal_absent") is True:
            return 0

        tests = validation.get("tests")
        if isinstance(tests, dict):
            tests_run = tests.get("tests_run")
            if (
                isinstance(tests_run, int)
                and not isinstance(tests_run, bool)
                and tests_run >= 0
            ):
                return tests_run

        from guardkit.lib.pytest_summary import parse_pytest_summary

        summaries = []
        if isinstance(independent, dict):
            summaries.append(independent.get("test_output_summary"))
        summaries.append(validation.get("test_output_summary"))
        for output in summaries:
            parsed = parse_pytest_summary(output if isinstance(output, str) else None)
            if parsed.tests_run is not None:
                return parsed.tests_run

        # A green Boolean establishes a verdict, not a count. Unknown count
        # stays zero rather than manufacturing one executed test.
        return 0


# ============================================================================
# Post-Loop Finalization Functions
# ============================================================================


def generate_summary(
    task_id: str,
    worktree_path: Path,
    loop_result: OrchestrationResult,
) -> Dict[str, Any]:
    """
    Generate summary from task-work results for AutoBuild finalization.

    This function reads the task_work_results.json file created by the Player
    agent during implementation and extracts key metrics for the final summary.

    Parameters
    ----------
    task_id : str
        Task identifier
    worktree_path : Path
        Path to worktree
    loop_result : OrchestrationResult
        Result from loop phase

    Returns
    -------
    Dict[str, Any]
        Summary containing:
        - files_created: List of created files
        - files_modified: List of modified files
        - tests_info: Test execution info
        - coverage: Coverage metrics
        - architectural_score: SOLID/DRY/YAGNI score
        - plan_audit: Plan variance info

    Notes
    -----
    Returns minimal summary if task_work_results.json doesn't exist.
    """
    results_dir = worktree_path / ".guardkit" / "autobuild" / task_id
    results_file = results_dir / "task_work_results.json"

    # Return minimal summary if file doesn't exist
    if not results_file.exists():
        logger.warning(f"task_work_results.json not found at {results_file}")
        return {
            "files_created": [],
            "files_modified": [],
            "tests_info": {},
            "coverage": {},
            "architectural_score": None,
            "plan_audit": {},
        }

    try:
        import json

        with open(results_file, "r") as f:
            results = json.load(f)

        return {
            "files_created": results.get("files_created", []),
            "files_modified": results.get("files_modified", []),
            "tests_info": results.get("tests_info", {}),
            "coverage": results.get("coverage", {}),
            "architectural_score": results.get("architectural_score"),
            "plan_audit": results.get("plan_audit", {}),
        }

    except Exception as e:
        logger.warning(f"Failed to read task_work_results.json: {e}")
        return {
            "files_created": [],
            "files_modified": [],
            "tests_info": {},
            "coverage": {},
            "architectural_score": None,
            "plan_audit": {},
        }


def finalize_autobuild(
    task_id: str,
    worktree_path: Path,
    loop_result: OrchestrationResult,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Finalize AutoBuild execution and prepare result for CLI display.

    This function maps the loop result to task status, generates summary,
    and builds next_steps guidance based on the final decision.

    Parameters
    ----------
    task_id : str
        Task identifier
    worktree_path : Path
        Path to worktree
    loop_result : OrchestrationResult
        Result from loop phase
    repo_root : Optional[Path]
        Repository root (default: None)

    Returns
    -------
    Dict[str, Any]
        Finalization result containing:
        - status: Task status (in_review/blocked)
        - worktree: Worktree path
        - next_steps: List of next steps
        - summary: Summary from generate_summary

    Examples
    --------
    >>> result = finalize_autobuild(
    ...     task_id="TASK-XXX-YYYY",
    ...     worktree_path=Path(".guardkit/worktrees/TASK-XXX-YYYY"),
    ...     loop_result=orchestration_result,
    ... )
    >>> print(result["status"])
    'in_review'
    >>> print(result["next_steps"])
    ['Review changes: cd .guardkit/worktrees/TASK-XXX-YYYY', ...]
    """
    # Map final_decision to task status.
    if loop_result.final_decision == "approved":
        status = "in_review"
    else:
        status = "blocked"

    # Generate summary from task-work results
    summary = generate_summary(task_id, worktree_path, loop_result)

    # Build next_steps based on final_decision
    next_steps = []
    if loop_result.final_decision == "approved":
        next_steps = [
            f"Review changes: cd {worktree_path}",
            "View diff: git diff main",
            "Review turn history: cat .guardkit/autobuild/{task_id}/player_turn_*.json",
            "Merge if approved: git checkout main && git merge autobuild/{task_id}",
            f"Cleanup worktree: guardkit worktree cleanup {task_id}",
        ]
    elif loop_result.final_decision == "max_turns_exceeded":
        next_steps = [
            f"Review implementation: cd {worktree_path}",
            f"Check last feedback: cat .guardkit/autobuild/{task_id}/coach_turn_{loop_result.total_turns}.json",
            "Consider manual intervention or increase max_turns",
        ]
    elif loop_result.final_decision == "pre_loop_blocked":
        next_steps = [
            "Review pre-loop results in task frontmatter",
            "Check architectural review score or checkpoint rejection reason",
            "Revise requirements or plan before retrying",
        ]
    else:  # error
        next_steps = [
            f"Review error logs: cat .guardkit/logs/{task_id}.log",
            f"Check worktree state: cd {worktree_path}",
            "Fix issues and retry",
        ]

    return {
        "status": status,
        "worktree": str(worktree_path),
        "next_steps": next_steps,
        "summary": summary,
    }


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "AutoBuildOrchestrator",
    "ContextStatus",
    "OrchestrationResult",
    "TurnRecord",
    "OrchestrationError",
    "SetupPhaseError",
    "PreLoopPhaseError",
    "LoopPhaseError",
    "FinalizePhaseError",
    "generate_summary",
    "finalize_autobuild",
]
