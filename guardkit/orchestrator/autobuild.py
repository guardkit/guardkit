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
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

import yaml

# Import worktree components from guardkit package
from guardkit.worktrees import (
    WorktreeManager,
    Worktree,
    WorktreeCreationError,
    WorktreeMergeError,
)

# Import local orchestrator components
from guardkit.orchestrator.agent_invoker import AgentInvoker, AgentInvocationResult
from guardkit.orchestrator.phase_specialists import (
    detect_stack_template,
    render_missing_phase_list,
)
from guardkit.orchestrator.progress import ProgressDisplay
from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
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
    CoachValidationResult,
)

# Import criteria classifier for runtime command verification (TASK-CRV-537E)
from guardkit.orchestrator.quality_gates.criteria_classifier import (
    classify_acceptance_criteria,
)
from guardkit.orchestrator.quality_gates.command_failure_classifier import (
    classify_command_failure,
    build_command_failure_advisory,
    CommandFailureRecord,
)

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

# Import worktree checkpoint management for context pollution mitigation
from guardkit.orchestrator.worktree_checkpoints import (
    WorktreeCheckpointManager,
    Checkpoint,
)

# Import turn state operations for cross-turn learning (TASK-GE-002)
from guardkit.knowledge.turn_state_operations import (
    capture_turn_state,
    create_turn_state_from_autobuild,
)
from guardkit.knowledge.entities.turn_state import TurnMode
from guardkit.knowledge.graphiti_client import (
    get_graphiti,
    get_factory,
    GraphitiClientFactory,
    _suppress_httpx_cleanup_errors,
    _install_graphiti_unraisable_hook,
)

# Import AutoBuild context loader for job-specific context (TASK-GR6-006)
from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader

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
COACH_GRACE_PERIOD_SECONDS: int = 120


# ============================================================================
# Runtime Command Execution Constants (TASK-CRV-537E)
# Canonical definitions live in command_models.py; re-exported here for
# backward compatibility with existing tests and callers (TASK-RFX-7C63).
# ============================================================================

from guardkit.orchestrator.quality_gates.command_models import (  # noqa: E402
    WORKTREE_SENTINEL,
    COMMAND_TIMEOUT_SECONDS,
    COMMAND_TOTAL_TIMEOUT_SECONDS,
    _PIP_CMD_RE,
    _assert_worktree_path,
    CommandExecutionResult,
    CommandVerificationResult,
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
    "configuration_error": "env_failure",
    "pre_loop_blocked": "other",
    "unrecoverable_stall": "other",
    "player_invocation_stall": "env_failure",
    "design_extraction_failed": "other",
    "honesty_collapse": "other",
}
"""Map final_decision strings to FailureCategory controlled vocabulary values."""


# ============================================================================
# Stall Classification (TASK-FIX-7A07)
# ============================================================================

# Known stall sub-type labels. The top-level ``final_decision`` stays
# ``unrecoverable_stall`` for backward compatibility with downstream consumers;
# ``decision_subtype`` is the new dimension that names *which* stall mechanism
# fired. Sub-types can co-fire (joined with " + ") — see ``classify_stall``.
STALL_COACH_AGENT_INVOCATIONS = "coach_agent_invocations_stall"
"""Stall sub-type: Coach's agent-invocations gate rejected the Player for N
consecutive turns with identical missing-phases signature. TASK-FIX-7A07."""

STALL_CONTEXT_POLLUTION = "context_pollution_stall_no_checkpoint"
"""Stall sub-type: context-pollution rollback fired but no passing checkpoint
existed. TASK-AB-SD01."""

STALL_FEEDBACK_GENERIC = "coach_feedback_stall"
"""Stall sub-type: identical Coach feedback for N turns with zero criteria
progress, and no more specific sub-type matched."""

STALL_ENVIRONMENT = "environment_stall"
"""Stall sub-type: trailing N turns all show ``all_gates_passed=True`` (Player
quality gates clean) but ``independent_tests.tests_passed=False`` with a
``test_verification`` issue whose ``failure_classification == "infrastructure"``
and an identical ``failure_confidence``. Indicates the worktree environment is
broken (e.g. Python interpreter mismatch with ``requires-python``) rather than
a code defect or task-type misclassification. TASK-ABSR-C3D4."""


@dataclass(frozen=True)
class StallClassification:
    """Sub-classification of an ``unrecoverable_stall`` exit.

    The top-level ``final_decision`` label stays ``"unrecoverable_stall"`` for
    backward compatibility. This dataclass carries the finer-grained sub-type
    information that the summary renderer, review-summary-per-task renderer,
    and Graphiti seeding hook all consume (TASK-FIX-7A07).

    Attributes
    ----------
    decision_label : str
        Primary stall sub-type (one of ``STALL_COACH_AGENT_INVOCATIONS``,
        ``STALL_CONTEXT_POLLUTION``, ``STALL_FEEDBACK_GENERIC``).
    decision_subtype : str
        Composite label when multiple sub-types co-fire, joined by " + "
        (e.g. ``"coach_agent_invocations_stall + context_pollution_stall_no_checkpoint"``).
        Equal to ``decision_label`` when only one sub-type fired.
    missing_phases : List[str]
        Missing phase identifiers from the Coach's agent-invocations gate
        (only populated for ``coach_agent_invocations_stall``).
    expected_phases : Optional[int]
        Expected phase count (only populated for the agent-invocations case).
    actual_invocations : Optional[int]
        Actual invocation count (only populated for the agent-invocations case).
    co_fires : List[str]
        All sub-type labels that co-fired on this task. Useful for the
        review-summary per-task table and Graphiti seeding.
    """

    decision_label: str
    decision_subtype: str
    missing_phases: List[str]
    expected_phases: Optional[int]
    actual_invocations: Optional[int]
    co_fires: List[str]


def _extract_agent_invocations_violation(
    turn_record: "TurnRecord",
) -> Optional[Dict[str, Any]]:
    """Return the ``agent_invocations_violation`` issue dict for this turn,
    or ``None`` if no such issue is present.

    Walks into ``turn_record.coach_result.report["issues"]`` and returns the
    first issue whose ``category == "agent_invocations_violation"``. This is
    the schema-stable predicate used by ``classify_stall`` to detect the
    coach-agent-invocations sub-type across consecutive turns.

    Defensive against malformed TurnRecords (Mock objects in tests,
    partial state during error paths) — any shape mismatch returns ``None``
    rather than raising.

    Parameters
    ----------
    turn_record : TurnRecord
        Completed turn record.

    Returns
    -------
    Optional[Dict[str, Any]]
        The violation issue dict (with keys ``missing_phases``, ``details``,
        etc.) if present, else ``None``.
    """
    if turn_record.coach_result is None:
        return None
    try:
        report = getattr(turn_record.coach_result, "report", None) or {}
    except (AttributeError, TypeError):
        return None
    if not isinstance(report, dict):
        return None
    issues = report.get("issues")
    if not isinstance(issues, list):
        return None
    for issue in issues:
        if (
            isinstance(issue, dict)
            and issue.get("category") == "agent_invocations_violation"
        ):
            return issue
    return None


def _extract_environment_stall_signal(
    turn_record: "TurnRecord",
) -> Optional[Dict[str, Any]]:
    """Return the ``test_verification`` issue dict for this turn when the
    environment-stall pattern matches, or ``None`` otherwise (TASK-ABSR-C3D4).

    Pattern requires:
      - ``coach_result.report["validation_results"]["quality_gates"]["all_gates_passed"]`` is True
      - ``coach_result.report["validation_results"]["independent_tests"]["tests_passed"]`` is False
      - ``coach_result.report["issues"]`` contains an entry with
        ``category == "test_verification"`` and
        ``failure_classification == "infrastructure"``

    Defensive against malformed TurnRecords (Mock objects in tests, partial
    state during error paths) — any shape mismatch returns ``None`` rather
    than raising.
    """
    if turn_record.coach_result is None:
        return None
    try:
        report = getattr(turn_record.coach_result, "report", None) or {}
    except (AttributeError, TypeError):
        return None
    if not isinstance(report, dict):
        return None

    validation_results = report.get("validation_results")
    if not isinstance(validation_results, dict):
        return None
    quality_gates = validation_results.get("quality_gates")
    if not isinstance(quality_gates, dict):
        return None
    if quality_gates.get("all_gates_passed") is not True:
        return None

    independent_tests = validation_results.get("independent_tests")
    if not isinstance(independent_tests, dict):
        return None
    if independent_tests.get("tests_passed") is not False:
        return None

    issues = report.get("issues")
    if not isinstance(issues, list):
        return None
    for issue in issues:
        if (
            isinstance(issue, dict)
            and issue.get("category") == "test_verification"
            and issue.get("failure_classification") == "infrastructure"
        ):
            return issue
    return None


def classify_stall(
    turn_history: List["TurnRecord"],
    final_decision: str,
    threshold: int = 3,
    context_pollution_fired: bool = False,
) -> Optional[StallClassification]:
    """Classify the sub-type of an ``unrecoverable_stall`` exit (TASK-FIX-7A07).

    Returns ``None`` for any ``final_decision`` other than
    ``"unrecoverable_stall"`` — callers should only invoke this when the
    orchestrator exited via that code path.

    Classification rules:

    1. **coach_agent_invocations_stall** — fires when the trailing ``threshold``
       turns all carry an ``agent_invocations_violation`` issue. The detector
       walks ``coach_result.report["issues"]`` for the schema-stable category
       match; it does NOT string-match on feedback text.
    2. **context_pollution_stall_no_checkpoint** — fires when the caller
       signals that context-pollution rollback fired but no passing checkpoint
       existed (``context_pollution_fired=True``). This is detected at the
       orchestrator level because it's signalled by the early-exit at
       ``autobuild.py:_loop_phase`` line ~2007, not by turn-record content.
    3. **coach_feedback_stall** — the default fallback: identical feedback
       with zero criteria progress, no more specific sub-type matched.

    Sub-types can co-fire (e.g. both the agent-invocations stall AND the
    context-pollution stall can apply to the same task when the Player's
    inline-pytest pattern both pollutes the context and bypasses sub-agent
    invocation). ``decision_subtype`` joins co-fires with " + ".

    Parameters
    ----------
    turn_history : List[TurnRecord]
        Complete turn history for the run.
    final_decision : str
        The orchestrator's top-level decision. Must be ``"unrecoverable_stall"``
        for classification to proceed.
    threshold : int, optional
        Number of trailing turns to require for classification (default: 3,
        matching ``_is_feedback_stalled``).
    context_pollution_fired : bool, optional
        Whether the context-pollution "no passing checkpoint" exit fired for
        this task. Set by the caller based on which code path exited the loop.

    Returns
    -------
    Optional[StallClassification]
        Classification details, or ``None`` when ``final_decision`` is not
        ``"unrecoverable_stall"``.
    """
    if final_decision != "unrecoverable_stall":
        return None

    co_fires: List[str] = []
    missing_phases: List[str] = []
    expected_phases: Optional[int] = None
    actual_invocations: Optional[int] = None

    # Check coach_agent_invocations_stall: trailing N turns all have
    # agent_invocations_violation category.
    if len(turn_history) >= threshold:
        recent = turn_history[-threshold:]
        violations = [
            _extract_agent_invocations_violation(tr) for tr in recent
        ]
        if all(v is not None for v in violations):
            co_fires.append(STALL_COACH_AGENT_INVOCATIONS)
            # Use the most recent violation for the phase details.
            latest = violations[-1]
            raw_missing = latest.get("missing_phases") or (
                latest.get("details", {}).get("missing_phases")
                if isinstance(latest.get("details"), dict)
                else []
            ) or []
            # Normalise to List[str]; ``missing_phases`` is sometimes stored
            # as ``[{"phase": "4", "description": "Testing"}, ...]``.
            if raw_missing and isinstance(raw_missing[0], dict):
                missing_phases = sorted(
                    str(m.get("phase", "")) for m in raw_missing if m.get("phase")
                )
            else:
                missing_phases = sorted(str(m) for m in raw_missing)
            details = (
                latest.get("details") if isinstance(latest.get("details"), dict) else {}
            )
            expected_phases = latest.get("expected_phases") or details.get(
                "expected_phases"
            )
            actual_invocations = latest.get("actual_invocations") or details.get(
                "actual_invocations"
            )

    if context_pollution_fired:
        co_fires.append(STALL_CONTEXT_POLLUTION)

    # Check environment_stall: trailing N turns all show all_gates_passed=True
    # but independent_tests failed with infrastructure-class failure_classification
    # AND identical failure_confidence across the window. agent_invocations and
    # context_pollution take precedence per the AC, so only check when neither
    # has fired (TASK-ABSR-C3D4).
    if not co_fires and len(turn_history) >= threshold:
        recent = turn_history[-threshold:]
        env_signals = [
            _extract_environment_stall_signal(tr) for tr in recent
        ]
        if all(signal is not None for signal in env_signals):
            confidences = [
                signal.get("failure_confidence") for signal in env_signals
            ]
            if len(set(confidences)) == 1:
                co_fires.append(STALL_ENVIRONMENT)

    # Default fallback.
    if not co_fires:
        co_fires.append(STALL_FEEDBACK_GENERIC)

    decision_label = co_fires[0]
    decision_subtype = " + ".join(co_fires)

    return StallClassification(
        decision_label=decision_label,
        decision_subtype=decision_subtype,
        missing_phases=missing_phases,
        expected_phases=expected_phases,
        actual_invocations=actual_invocations,
        co_fires=co_fires,
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


# ============================================================================
# Data Models
# ============================================================================


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

    Captures whether Graphiti context was retrieved, skipped, disabled, or failed,
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
    sdk_ceiling_hit: bool = False              # TASK-VPR-003: Whether ceiling was hit
    is_configuration_error: bool = False       # TASK-ABFIX-003: True when Coach flagged a config error (e.g. invalid task_type)
    command_results: Optional[Tuple[CommandExecutionResult, ...]] = None  # TASK-RFX-528E: Structured command execution results


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
        True if Coach approved, False if max_turns or error
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
    final_decision: Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "player_invocation_stall", "error", "cancelled", "timeout", "configuration_error", "pre_loop_blocked", "rate_limited", "design_extraction_failed", "honesty_collapse"]
    turn_history: List[TurnRecord]
    worktree: Worktree
    error: Optional[str] = None
    pre_loop_result: Optional[Dict[str, Any]] = None  # Results from pre-loop quality gates
    ablation_mode: bool = False  # Track if result was from ablation mode
    recovery_count: int = 0  # Number of state recovery attempts
    design_context: Optional["DesignContext"] = None  # Phase 0 design extraction result
    # TASK-FIX-7A07: Sub-classification of ``unrecoverable_stall`` exits.
    # None when final_decision is something other than unrecoverable_stall.
    stall_classification: Optional["StallClassification"] = None


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
        sdk_timeout: int = 1200,
        skip_arch_review: bool = False,
        enable_perspective_reset: bool = True,
        enable_checkpoints: bool = True,
        rollback_on_pollution: bool = True,
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
        emitter: Optional[Any] = None,
        progress_logger: Optional[Any] = None,
        venv_python: Optional[str] = None,
        wave_changed_files: Optional[Dict[str, Any]] = None,
        wave_files_lock: Optional[threading.Lock] = None,
        honesty_early_abort_threshold: float = 0.3,
        honesty_early_abort_window: int = 3,
        model: Optional[str] = None,  # TASK-FIX-MODELPLUMB
        coach_model: Optional[str] = None,  # TASK-FIX-COACHBUDG01: per-role Coach override
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
        rollback_on_pollution : bool, optional
            Automatically rollback when context pollution detected (default: True).
            Triggers on 2+ consecutive test failures.
        enable_context : bool, optional
            Enable job-specific context retrieval from Graphiti (default: True).
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

        # TASK-FIX-FALK01: Install sys.unraisablehook once per process so the
        # cosmetic "no running event loop" traceback from graphiti-core's
        # FalkorDB driver (edge_fulltext_search GCed after the loop closes)
        # never reaches stderr. Idempotent — safe to call from every
        # AutoBuildOrchestrator(); also no-op when Graphiti is disabled, since
        # the hook only suppresses errors whose coroutine source lives in
        # graphiti_core / falkordb / redis.asyncio.
        _install_graphiti_unraisable_hook()

        self.repo_root = Path(repo_root).resolve()
        self.max_turns = max_turns
        self.resume = resume
        self.enable_pre_loop = enable_pre_loop
        self.pre_loop_options = pre_loop_options or {}
        self.development_mode = development_mode
        self.sdk_timeout = sdk_timeout
        self.timeout_multiplier = timeout_multiplier
        self.skip_arch_review = skip_arch_review
        self.enable_perspective_reset = enable_perspective_reset
        self.enable_checkpoints = enable_checkpoints
        self.rollback_on_pollution = rollback_on_pollution
        self.ablation_mode = ablation_mode
        self._emitter = emitter if emitter is not None else NullEmitter()  # TASK-INST-004
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
        self._coach_model_name: Optional[str] = coach_model
        # Hardcoded reset turns per architectural review (TASK-BRF-001): [3, 5]
        self.perspective_reset_turns: List[int] = [3, 5] if enable_perspective_reset else []
        self._turn_history: List[TurnRecord] = []
        self._honesty_history: List[float] = []  # Track honesty scores across turns
        self._checkpoint_manager: Optional[WorktreeCheckpointManager] = None  # Initialized lazily
        self.recovery_count: int = 0  # Track number of state recovery attempts
        # Stall detection: track (feedback_signature, criteria_passed_count) per turn (TASK-AB-SD01)
        self._feedback_history: List[Tuple[str, int]] = []
        # TASK-FIX-7A07: Signal from _loop_phase that context-pollution rollback
        # fired but no passing checkpoint existed. Consumed by classify_stall()
        # to emit the context_pollution_stall_no_checkpoint sub-type. Reset
        # per _loop_phase invocation.
        self._context_pollution_no_checkpoint_fired: bool = False
        # Accumulated peak criteria count across turns — criteria verified in turn N
        # remain counted in turn N+1 to prevent false stall detection (TASK-FIX-AE7E)
        self._max_criteria_passed: int = 0
        # Cumulative requirements_addressed across turns — once a criterion is
        # inferred as addressed, it remains addressed in subsequent turns to
        # prevent criteria oscillation in synthetic reports (TASK-VRF-005).
        self._cumulative_requirements_addressed: Set[str] = set()
        # Files contributing to cumulative requirements — used for staleness
        # re-validation when carry-forward is applied (TASK-CRV-9618).
        self._cumulative_source_files: Set[str] = set()

        # Context retrieval settings (TASK-GR6-006)
        self.enable_context = enable_context
        self.verbose = verbose
        self._context_loader = context_loader  # For DI/testing only; thread-local loaders used at runtime
        self._feature_id: Optional[str] = feature_id  # Passed from FeatureOrchestrator or set during orchestration
        self._cancellation_event: Optional[threading.Event] = cancellation_event  # Cooperative cancellation (TASK-ASF-007)
        self._timeout_event: Optional[threading.Event] = timeout_event  # Feature-level timeout signal (TASK-ABFIX-006)
        self._progress_logger = progress_logger  # TASK-FIX-OBS2: Per-task progress logging
        self._task_timeout: Optional[int] = task_timeout  # Feature task budget in seconds (TASK-ABFIX-006)
        # Loop-start monotonic time, set in _loop_phase when a per-turn budget is active.
        # Used by _execute_turn to refresh the pre-specialist budget guard after the Player
        # phase consumes wall (TASK-ABSR-FRSH).
        self._loop_start_time: Optional[float] = None
        self.wave_size: int = max(1, int(wave_size))  # Parallel wave context (TASK-ABFIX-005)
        # TASK-FIX-A7B2: Wave-shared map of per-task file edits, populated as
        # each Player finishes. Coach reads peer entries (everyone but self) to
        # detect source-file contention and refuse the TASK-ABFIX-005
        # conditional approval when the contention is real (not transient infra).
        # Both default to None for single-task use; FeatureOrchestrator supplies
        # them in parallel waves.
        self._wave_changed_files: Optional[Dict[str, Any]] = wave_changed_files
        self._wave_files_lock: Optional[threading.Lock] = wave_files_lock
        # Honesty rolling-average early-abort thresholds (TASK-FIX-HEAB).
        # _check_honesty_early_abort() consults these after each turn: when
        # mean(self._honesty_history[-window:]) < threshold and at least
        # ``window`` samples have accrued, the loop short-circuits with
        # final_decision="honesty_collapse" instead of burning the remaining
        # max_turns budget on what observably won't recover. Defaults match
        # the CLI/feature_orchestrator forwarding layer (cli/autobuild.py:243-263,
        # feature_orchestrator.py:534-535).
        self.honesty_early_abort_threshold: float = honesty_early_abort_threshold
        self.honesty_early_abort_window: int = honesty_early_abort_window
        # Per-turn context status tracking for progress display (TASK-FIX-GCW5)
        self._last_player_context_status: Optional[ContextStatus] = None
        self._last_coach_context_status: Optional[ContextStatus] = None
        # Per-thread Graphiti client storage (TASK-FIX-GTP2)
        self._factory: Optional[GraphitiClientFactory] = None
        # TASK-ACR-005: Store event loop reference with each loader for proper cleanup
        self._thread_loaders: Dict[int, Tuple[Optional[AutoBuildContextLoader], asyncio.AbstractEventLoop]] = {}
        # TASK-GLF-002: Suppress Graphiti operations during shutdown
        self._shutting_down: bool = False

        # Store factory reference for per-thread client creation (TASK-FIX-GTP2)
        # Replaces shared singleton pattern that caused cross-loop hangs in parallel mode
        if self.enable_context and self._context_loader is None:
            try:
                self._factory = get_factory()
                if self._factory is None:
                    # Trigger lazy-init by calling get_graphiti(), then re-fetch factory
                    get_graphiti()
                    self._factory = get_factory()
                if self._factory is not None:
                    logger.info("Stored Graphiti factory for per-thread context loading")
                else:
                    logger.info("Graphiti factory not available, context retrieval disabled")
            except ImportError:
                logger.info("Graphiti dependencies not installed, context retrieval disabled")
            except Exception as e:
                logger.info(f"Could not obtain Graphiti factory: {e}")

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
            f"rollback_on_pollution={self.rollback_on_pollution}, "
            f"ablation_mode={self.ablation_mode}, "
            f"existing_worktree={'provided' if existing_worktree else 'None'}, "
            f"enable_context={self.enable_context}, "
            f"context_loader={'provided' if self._context_loader else 'None'}, "
            f"factory={'available' if self._factory else 'None'}, "
            f"verbose={self.verbose}"
        )

    def orchestrate(
        self,
        task_id: str,
        requirements: str,
        acceptance_criteria: List[str],
        base_branch: str = "main",
        task_file_path: Optional[Path] = None,
        requires_infrastructure: Optional[List[str]] = None,
        time_budget_seconds: Optional[float] = None,
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

        # Emit task.started lifecycle event (TASK-INST-004)
        self._emit_task_started(task_id)

        pre_loop_result = None  # Initialize pre-loop result

        # Load task data to extract task_type, requires_infrastructure, and consumer_context for CoachValidator
        task_type: Optional[str] = None
        consumer_context: Optional[list] = None
        _ri_from_caller = requires_infrastructure  # Preserve explicit parameter (may be None)
        requires_infrastructure = None  # Reset; will be resolved via frontmatter then precedence
        try:
            task_data = TaskLoader.load_task(task_id, repo_root=self.repo_root)
            frontmatter = task_data.get("frontmatter", {})
            task_type = frontmatter.get("task_type")
            if task_type:
                logger.debug(f"Loaded task_type from task file: {task_type}")
            ri = frontmatter.get("requires_infrastructure")
            if isinstance(ri, list):
                requires_infrastructure = ri
                logger.debug(f"Loaded requires_infrastructure from task file: {ri}")
            consumer_context = frontmatter.get("consumer_context")
            if isinstance(consumer_context, list):
                logger.debug(f"Loaded consumer_context from task file: {consumer_context}")
        except TaskNotFoundError:
            logger.debug(f"Task file not found for {task_id}, continuing with task_type=None")
        except Exception as e:
            logger.debug(f"Failed to load task metadata from task file: {e}, continuing with defaults")

        # Precedence: explicit parameter > frontmatter > None
        if _ri_from_caller is not None:
            requires_infrastructure = _ri_from_caller
            logger.debug(f"Using requires_infrastructure from caller: {_ri_from_caller}")

        try:
            # Phase 1: Setup (or resume existing worktree)
            if self.resume and task_file_path:
                worktree, start_turn = self._resume_from_state(task_id, task_file_path)
            else:
                worktree = self._setup_phase(task_id, base_branch)
                start_turn = 1
                # Save initial state
                if task_file_path:
                    self._save_state(task_file_path, worktree, "in_progress")

            # Phase 2: Pre-Loop Quality Gates (if enabled)
            if self.enable_pre_loop and not self.resume:
                try:
                    pre_loop_result = self._pre_loop_phase(task_id, worktree)

                    # Check if checkpoint was rejected
                    if not pre_loop_result.get("checkpoint_passed", True):
                        logger.warning(f"Pre-loop checkpoint rejected for {task_id}")
                        # Emit task.failed for pre-loop rejection (TASK-INST-004)
                        self._emit_task_failed(task_id, "pre_loop_blocked")
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
            )

            # Phase 4: Finalize
            self._finalize_phase(
                worktree=worktree,
                final_decision=final_decision,
                turn_history=turn_history,
            )

            # Save final state
            if task_file_path:
                status = "in_review" if final_decision == "approved" else "blocked"
                self._save_state(task_file_path, worktree, status)

            # Build result
            success = final_decision == "approved"
            # TASK-FIX-7A07: Compute stall sub-classification for the result
            # so downstream consumers (review-summary, Graphiti seeding) can
            # surface the per-task decision_subtype without re-walking the
            # turn_history each.
            stall_classification = classify_stall(
                turn_history,
                final_decision,
                threshold=3,
                context_pollution_fired=self._context_pollution_no_checkpoint_fired,
            )
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
                stall_classification=stall_classification,
            )

            # Emit lifecycle event based on outcome (TASK-INST-004)
            if success:
                self._emit_task_completed(task_id, turn_history)
            else:
                self._emit_task_failed(task_id, final_decision)

            logger.info(
                f"Orchestration complete: {task_id}, decision={final_decision}, "
                f"turns={len(turn_history)}"
            )

            return result

        except RateLimitExceededError as e:
            logger.error(f"Rate limit exceeded for {task_id}: {e}")
            # Emit task.failed with rate_limit category (TASK-INST-004)
            self._emit_task_failed(task_id, "rate_limited")
            return OrchestrationResult(
                task_id=task_id,
                success=False,
                total_turns=len(turn_history),
                final_decision="rate_limited",
                turn_history=turn_history,
                worktree=worktree,
                error=(
                    f"Rate limit exceeded. Reset time: {e.reset_time or 'unknown'}. "
                    f"Worktree preserved at: {worktree.path}\n"
                    f"Resume with: guardkit autobuild task {task_id} --resume"
                ),
            )
        except SetupPhaseError:
            # Setup errors should propagate (can't proceed without worktree)
            raise
        except Exception as e:
            logger.error(f"Orchestration failed for {task_id}: {e}", exc_info=True)
            raise OrchestrationError(f"Orchestration failed: {e}") from e

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
                        use_task_work_delegation=True,
                        cancellation_event=self._cancellation_event,  # TASK-FIX-ASPF-004
                        timeout_multiplier=self.timeout_multiplier,  # TASK-FIX-VL05
                        venv_python=self._venv_python,  # TASK-FIX-7A05
                        model_name=self._model_name,  # TASK-FIX-MODELPLUMB
                        coach_model_name=self._coach_model_name,  # TASK-FIX-COACHBUDG01
                    )
                # TASK-FIX-OBS2: Attach progress logger to agent invoker
                if self._progress_logger and self._agent_invoker:
                    self._agent_invoker.set_progress_logger(self._progress_logger)

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
                    use_task_work_delegation=True,
                    cancellation_event=self._cancellation_event,  # TASK-FIX-ASPF-004
                    venv_python=self._venv_python,  # TASK-FIX-7A05
                    model_name=self._model_name,  # TASK-FIX-MODELPLUMB
                    coach_model_name=self._coach_model_name,  # TASK-FIX-COACHBUDG01
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
            # Non-critical failure - don't raise

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
    ) -> Tuple[List[TurnRecord], Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "player_invocation_stall", "error", "cancelled", "timeout", "configuration_error", "design_extraction_failed", "timeout_budget_exhausted", "honesty_collapse"]]:
        """
        Phase 3: Execute Player↔Coach adversarial loop.

        This phase implements the core adversarial workflow where Player
        implements and Coach validates, iterating until approval or max_turns.

        Loop Structure
        --------------
        - Turn 1: Player implements from scratch
        - Turn 2+: Player addresses Coach feedback
        - Exit: Coach approves OR max_turns exceeded OR critical error OR cancelled

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

        # TASK-FIX-7A07: Reset stall-classification signals at loop entry so
        # classify_stall() sees fresh state per task.
        self._context_pollution_no_checkpoint_fired = False

        # Track loop start time for SDK-level timeout remaining budget (TASK-ABFIX-006)
        import time as _time
        loop_start = _time.monotonic()

        # Use existing turn history if resuming
        turn_history: List[TurnRecord] = list(self._turn_history)
        previous_feedback: Optional[str] = self._get_last_feedback() if self.resume else None

        # Initialize checkpoint manager if enabled
        if self.enable_checkpoints and self._checkpoint_manager is None:
            self._checkpoint_manager = WorktreeCheckpointManager(
                worktree_path=worktree.path,
                task_id=task_id,
            )
            logger.info(
                f"Checkpoint manager initialized for {task_id} "
                f"(rollback_on_pollution={self.rollback_on_pollution})"
            )

        # Track loop start time for per-turn budget (TASK-ABFIX-004)
        loop_start_time: Optional[float] = time.monotonic() if time_budget_seconds is not None else None
        # Expose to _execute_turn so the pre-specialist budget guard can refresh
        # remaining_budget post-Player (TASK-ABSR-FRSH).
        self._loop_start_time = loop_start_time

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
                        return turn_history, "timeout_budget_exhausted"
                else:
                    remaining_budget = None

                logger.info(f"Executing turn {turn}/{self.max_turns}")

                # Check if perspective should be reset to prevent anchoring bias
                # When reset triggered, Player receives only original requirements (no feedback)
                if self._should_reset_perspective(turn):
                    previous_feedback = None
                    # TASK-RFX-B20B: Also clear session to avoid carrying
                    # prior context that perspective reset is meant to discard
                    if self._agent_invoker is not None:
                        self._agent_invoker.set_player_resume_session(None)

                # Execute single turn
                # Skip arch review when pre-loop is disabled (implement-only mode)
                # because Phase 2.5B (Architectural Review) doesn't run
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
                )

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
                    elapsed = int(_time.monotonic() - loop_start)
                    remaining = max(0, self._task_timeout - elapsed)
                    logger.info(
                        f"[{task_id}] TIMEOUT (SDK-level): sdk_timeout={self.sdk_timeout}s expired "
                        f"during turn {turn}. Feature task had {remaining}s remaining of its "
                        f"{self._task_timeout}s budget."
                    )


                # Capture turn state for cross-turn learning (TASK-GE-002, TASK-RFX-5FED)
                self._capture_turn_state(
                    turn_record, acceptance_criteria,
                    task_id=task_id, worktree_path=worktree.path,
                )

                # Record honesty score from Coach's verification
                self._record_honesty(turn_record)

                # Honesty rolling-average early-abort (TASK-FIX-HEAB).
                # When the rolling average over _honesty_early_abort_window
                # turns drops below _honesty_early_abort_threshold the loop
                # short-circuits with a "honesty_collapse" final_decision —
                # the diagnostic explains why and points at the most-flagged
                # claim. This is the autobuild-level integration the
                # original TASK-FIX-HEAB commit advertised but did not land;
                # see TASK-FIX-HEAB-FOLLOWUP.
                heab_msg = self._check_honesty_early_abort(
                    turn_history,
                    task_id=task_id,
                    worktree_path=worktree.path,
                )
                if heab_msg is not None:
                    logger.warning(
                        f"[{task_id}] HONESTY COLLAPSE after turn {turn}: {heab_msg}"
                    )
                    return turn_history, "honesty_collapse"

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
                        checkpoint = self._checkpoint_manager.create_checkpoint(
                            turn=turn,
                            tests_passed=tests_passed,
                            test_count=test_count,
                        )
                        logger.info(
                            f"Checkpoint created: {checkpoint.commit_hash[:8]} "
                            f"for turn {turn}"
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

                # Fast-exit on configuration errors (TASK-ABFIX-003)
                # The Player cannot fix task frontmatter — retrying is futile.
                if turn_record.is_configuration_error:
                    config_issue = next(
                        (i for i in (turn_record.coach_result.report.get("issues", []) if turn_record.coach_result else [])
                         if i.get("category") == "invalid_task_type"),
                        None,
                    )
                    error_detail = config_issue["description"] if config_issue else turn_record.feedback or "unknown configuration error"
                    logger.error(
                        f"Configuration error for {task_id}: {error_detail}. "
                        f"This is a task file issue — the Player cannot fix it."
                    )
                    self._progress_display.console.print(
                        f"\n[bold red]ERROR: Configuration error for {task_id}:[/bold red]\n"
                        f"  {error_detail}\n"
                        f"  [yellow]This is a task file configuration issue — the Player cannot fix it.[/yellow]\n"
                        f"  [green]Fix the task_type in the task .md file and retry.[/green]\n"
                    )
                    return turn_history, "configuration_error"

                # Create checkpoint after turn completes (if enabled)
                # Skip checkpoint for configuration errors — tests were never run (TASK-ABFIX-003)
                if self.enable_checkpoints and self._checkpoint_manager:
                    tests_passed = self._extract_tests_passed(turn_record)
                    test_count = self._extract_test_count(turn_record)

                    checkpoint = self._checkpoint_manager.create_checkpoint(
                        turn=turn,
                        tests_passed=tests_passed,
                        test_count=test_count,
                    )
                    logger.info(
                        f"Checkpoint created: {checkpoint.commit_hash[:8]} "
                        f"for turn {turn}"
                    )

                    # Check for context pollution and rollback if needed
                    if self.rollback_on_pollution:
                        if self._checkpoint_manager.should_rollback():
                            target_turn = self._checkpoint_manager.find_last_passing_checkpoint()
                            if target_turn:
                                logger.warning(
                                    f"Context pollution detected, rolling back "
                                    f"from turn {turn} to turn {target_turn}"
                                )
                                self._checkpoint_manager.rollback_to(target_turn)

                                # TASK-FIX-RBSS AC-1: clear the Player SDK session
                                # so the next turn does not resume the polluted
                                # cumulative-authoring memory of files the
                                # rollback just deleted. Mirrors the
                                # perspective-reset path above (lines 2161-2165).
                                if self._agent_invoker is not None:
                                    self._agent_invoker.set_player_resume_session(None)

                                # Update state after rollback
                                self._turn_history = turn_history[:target_turn]
                                previous_feedback = (
                                    self._turn_history[-1].feedback
                                    if self._turn_history else None
                                )

                                # Continue loop from rollback point + 1
                                logger.info(
                                    f"Continuing from turn {target_turn + 1} "
                                    f"after rollback"
                                )
                                continue
                            else:
                                # UNRECOVERABLE: No passing checkpoint ever existed (TASK-AB-SD01)
                                logger.error(
                                    f"Unrecoverable stall detected for {task_id}: "
                                    f"context pollution detected but no passing checkpoint exists. "
                                    f"Exiting loop early to avoid wasting turns."
                                )
                                # TASK-FIX-7A07: Signal classifier that this was
                                # the context-pollution code path so the
                                # per-task decision_subtype can reflect it
                                # alongside any agent-invocations co-fire.
                                self._context_pollution_no_checkpoint_fired = True
                                return turn_history, "unrecoverable_stall"

                # Check for player-invocation stall first (TASK-FIX-7A02).
                # This takes precedence over feedback stall: when the Player
                # never produced a real report for N consecutive turns, the
                # feedback stall signal (Coach rejecting synthetic reports)
                # is a symptom of the SDK-layer failure, not a task-content
                # problem. Classifying separately surfaces the real
                # underlying cause (auth/SDK env) rather than falsely
                # blaming the task's acceptance criteria.
                if self._is_player_invocation_stalled(turn_history):
                    logger.error(
                        f"Player-invocation stall detected for {task_id}: "
                        f"{len(turn_history)} turn(s), latest {3} consecutively "
                        f"failed at the SDK layer. Exiting loop early."
                    )
                    return turn_history, "player_invocation_stall"

                # Check for repeated feedback stall (TASK-AB-SD01 Mechanism 2)
                if turn_record.decision == "feedback" and turn_record.feedback:
                    criteria_passed = self._count_criteria_passed(turn_record)
                    # Accumulate peak: criteria verified in prior turns stay counted (TASK-FIX-AE7E)
                    self._max_criteria_passed = max(criteria_passed, self._max_criteria_passed)
                    if self._is_feedback_stalled(
                        turn_record.feedback,
                        self._max_criteria_passed,
                        turn_record=turn_record,
                    ):
                        logger.error(
                            f"Feedback stall detected for {task_id}: "
                            f"identical feedback with no criteria progress "
                            f"({criteria_passed} criteria passing). "
                            f"Exiting loop early."
                        )
                        return turn_history, "unrecoverable_stall"

                # Handle feedback decision
                if turn_record.decision == "feedback":
                    logger.info(f"Coach provided feedback on turn {turn}")
                    previous_feedback = turn_record.feedback
                    # Continue to next turn

                else:
                    # Should never happen (decision is Literal type)
                    logger.error(f"Invalid decision: {turn_record.decision}")
                    return turn_history, "error"

            # Reached max turns without approval
            logger.warning(f"Max turns ({self.max_turns}) exceeded for {task_id}")
            return turn_history, "max_turns_exceeded"

    def _cap_specialist_timeout(
        self,
        remaining_budget: Optional[float],
        task_id: str,
    ) -> int:
        """Cap orchestrator-invoked specialist sdk_timeout via the Player-side scaler.

        Delegates the base computation to
        ``AgentInvoker._calculate_sdk_timeout`` so the specialist receives the
        same mode/complexity multipliers the Player gets for the same task
        (TASK-FIX-CRSTL-MULT). Then applies the wall-clock clamp on top so a
        single specialist (Phase 4 test-orchestrator or Phase 5 code-reviewer)
        cannot consume the entire remaining wall budget when the scaled value
        exceeds what's left.

        Reserves ``COACH_GRACE_PERIOD_SECONDS`` so Coach still has a window to
        validate after the specialist returns. Floors at 60 s to prevent
        pathologically-low values from blocking specialists entirely
        (TASK-ABSR-WALL).

        Set ``GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable`` to short-circuit the
        wall clamp (the scaling still applies — disable means "no wall cap",
        not "no scaling"). Emergency backout only.
        """
        if os.environ.get("GUARDKIT_SPECIALIST_TIMEOUT_CAP") == "disable":
            return self._agent_invoker._calculate_sdk_timeout(
                task_id, remaining_budget=None
            )

        scaled = self._agent_invoker._calculate_sdk_timeout(
            task_id, remaining_budget=remaining_budget
        )
        if remaining_budget is None:
            return scaled
        reserved = remaining_budget - COACH_GRACE_PERIOD_SECONDS
        cap = max(60, int(reserved))
        return min(scaled, cap)

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
        timestamp = datetime.now().isoformat()

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
                    feedback=None,
                    timestamp=timestamp,
                    player_context_status=player_context_status,
                    sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                    sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                    sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', False),
                )

            # Distinguish between missing report and actual failure
            is_missing_report = (
                player_result.error and
                ("report not found" in player_result.error.lower() or
                 "PlayerReportNotFoundError" in player_result.error)
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

            # TASK-PFI-A1B2: Capture original error before potential overwrite
            _original_error = player_result.error

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
                # Write recovered data to disk so Coach reads it (TASK-FIX-ASPF-002)
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
                    "success",
                    f"[RECOVERED] {summary}",
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
                return TurnRecord(
                    turn=turn,
                    player_result=player_result,
                    coach_result=None,
                    decision="error",
                    feedback=None,
                    timestamp=timestamp,
                    player_context_status=player_context_status,
                    sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                    sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                    sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', False),
                )

        # Warn if passing synthetic report to Coach (TASK-ASF-004)
        if player_result.success and player_result.report.get("_synthetic"):
            logger.warning(
                f"[Turn {turn}] Passing synthetic report to Coach for {task_id}. "
                f"Promise matching will fail — falling through to text matching."
            )

        # Execute command_execution criteria in the worktree (TASK-CRV-537E)
        # Only when on the synthetic report path — not when Player returns
        # structured data directly.
        command_exec_results: List[CommandExecutionResult] = []
        if (
            player_result.success
            and player_result.report.get("_synthetic")
            and acceptance_criteria
            and worktree is not None
        ):
            try:
                _assert_worktree_path(worktree.path)
                command_exec_results = self._execute_command_criteria(
                    synthetic_report=player_result.report,
                    acceptance_criteria=acceptance_criteria,
                    worktree_path=worktree.path,
                )
                # TASK-RFX-528E: Inject structured results into player report
                # for Coach visibility and coach_turn_N.json persistence.
                if command_exec_results:
                    player_result.report["command_results"] = [
                        r.to_dict() for r in command_exec_results
                    ]
                    passed = sum(1 for r in command_exec_results if r.passed)
                    total = len(command_exec_results)
                    summary = f"Runtime Commands: {passed}/{total} passed"
                    logger.info(summary)
                    # TASK-RFX-528E: Show in progress display
                    self._progress_display.console.print(
                        f"   [dim]{summary}[/dim]"
                    )
            except RuntimeError:
                logger.error(
                    "Worktree path assertion failed for %s — "
                    "skipping runtime command execution",
                    task_id,
                    exc_info=True,
                )

        # Cumulative requirements_addressed high-water-mark (TASK-VRF-005)
        # with staleness validation (TASK-CRV-9618).
        if player_result.success and player_result.report:
            # Track source files for staleness checking (TASK-CRV-9618)
            current_files = set(
                player_result.report.get("files_created", [])
                + player_result.report.get("files_modified", [])
            )
            self._cumulative_source_files.update(current_files)

            # TASK-FIX-A7B2: Publish this task's edits to the wave-shared map
            # so peer Coaches in this parallel wave can detect source-file
            # contention. Update under lock to keep the snapshot stable for
            # readers. Each turn overwrites the prior entry — Coach sees the
            # latest cumulative edit set, which is the right granularity for
            # contention detection (any overlap, ever, between two in-flight
            # tasks in the same wave is real source-file contention).
            if (
                self._wave_changed_files is not None
                and self._wave_files_lock is not None
            ):
                with self._wave_files_lock:
                    self._wave_changed_files[task_id] = frozenset(
                        str(f) for f in current_files if f
                    )

            current_addressed = set(
                player_result.report.get("requirements_addressed", [])
            )
            # Requirements carried forward from previous turns (not current)
            carry_forward = self._cumulative_requirements_addressed - current_addressed

            # Staleness check: re-validate carry-forward requirements
            # against current worktree file contents (TASK-CRV-9618).
            if carry_forward and worktree is not None:
                from guardkit.orchestrator.synthetic_report import (
                    validate_requirements_staleness,
                )

                still_valid = set(
                    validate_requirements_staleness(
                        requirements=list(carry_forward),
                        source_files=list(self._cumulative_source_files),
                        worktree_path=worktree.path,
                    )
                )
                stale = carry_forward - still_valid
                if stale:
                    for req in stale:
                        logger.debug(
                            "Dropping stale requirement: %s", req[:80]
                        )
                    logger.info(
                        "Dropped %d stale requirements from carry-forward",
                        len(stale),
                    )
                carry_forward = still_valid

            # Merge: current turn + validated carry-forward
            merged = current_addressed | carry_forward
            carried_count = len(carry_forward)

            if carried_count > 0:
                logger.info(
                    "Carried forward %d requirements from previous turns",
                    carried_count,
                )

            # Update cumulative set and report
            self._cumulative_requirements_addressed = merged
            if merged:
                player_result.report["requirements_addressed"] = list(merged)
                logger.info(
                    "Cumulative requirements_addressed: %d criteria "
                    "(current turn: %d, carried: %d)",
                    len(merged),
                    len(current_addressed),
                    carried_count,
                )

        # ===== Orchestrator-side Phase 4/5 (FEAT-AB59 / TASK-OSI-006) =====
        # Replaces the Player's discretionary specialist invocations with
        # orchestrator-driven calls. Skipped for direct-mode tasks.
        if player_result.success and self._agent_invoker is not None:
            # AC#8 defensive: import inside the block so a missing module
            # in some hypothetical future packaging error skips Phase 4/5
            # rather than breaking the turn.
            try:
                from guardkit.orchestrator import specialist_invocations as _si
            except ImportError:
                _si = None
                logger.warning(
                    f"[{task_id}] specialist_invocations import failed; "
                    "skipping orchestrator-side Phase 4/5"
                )

            if _si is not None:
                impl_mode = self._agent_invoker._get_implementation_mode(task_id)

                # TASK-ABSR-CEIL: when Player hit the SDK turn ceiling the
                # codebase is provably partial — running test-orchestrator
                # on it just thrashes for the full SDK timeout, exhausts
                # the per-task wall budget, and forecloses turn-N+1 with
                # timeout_budget_exhausted. Skip Phase 4/5 and route
                # straight to Coach so the next turn can fix the missing
                # ACs. Set GUARDKIT_INVOKE_SPECIALISTS_ON_CEILING_HIT=1 to
                # restore the prior behaviour (emergency backout).
                sdk_ceiling_hit = getattr(
                    player_result, "sdk_ceiling_hit", False
                )
                ceiling_skip_disabled = (
                    os.environ.get(
                        "GUARDKIT_INVOKE_SPECIALISTS_ON_CEILING_HIT", "0"
                    ) == "1"
                )

                # Refresh remaining_budget after the Player phase. The value
                # threaded in via `remaining_budget` is the start-of-turn
                # value computed at line ~2125; the Player can consume
                # substantial wall before this guard runs, so recompute from
                # the loop-start monotonic time (TASK-ABSR-FRSH, R3).
                if (
                    remaining_budget is None
                    or self._loop_start_time is None
                    or self._task_timeout is None
                ):
                    post_player_remaining: Optional[float] = remaining_budget
                else:
                    post_player_remaining = float(self._task_timeout) - (
                        time.monotonic() - self._loop_start_time
                    )

                # Coarse budget guard (AC#6) — if the post-Player remaining
                # budget is below MIN_TURN_BUDGET_SECONDS, skip specialists
                # and write a `specialist_skipped` phase_4 block so the gate
                # still produces a well-formed validation block.
                budget_ok = (
                    post_player_remaining is None
                    or post_player_remaining >= MIN_TURN_BUDGET_SECONDS
                )

                if impl_mode == "direct":
                    logger.info(
                        f"[{task_id}] Skipping orchestrator Phase 4/5 (direct mode)"
                    )
                elif sdk_ceiling_hit and not ceiling_skip_disabled:
                    logger.info(
                        f"[{task_id}] Skipping orchestrator Phase 4/5 "
                        "(Player hit SDK turn ceiling — codebase is partial)"
                    )
                    specialist_results_path = (
                        Path(worktree.path) / ".guardkit" / "autobuild" / task_id
                        / "specialist_results.json"
                    )
                    for _phase_key, _defaults in (
                        ("phase_4", _si._PHASE_4_AGENT_FIELD_DEFAULTS),
                        ("phase_5", _si._PHASE_5_AGENT_FIELD_DEFAULTS),
                    ):
                        _si._merge_specialist_block(
                            specialist_results_path,
                            _phase_key,
                            {
                                "status": "skipped",
                                "duration_seconds": 0.0,
                                "error": "specialist_skipped: sdk_ceiling_hit",
                                **_defaults,
                            },
                        )
                    try:
                        self._agent_invoker._inject_specialist_records_into_task_work_results(
                            task_id
                        )
                    except Exception as exc:
                        logger.warning(
                            f"[{task_id}] _inject_specialist_records_into_task_work_results "
                            f"raised after sdk_ceiling_hit skip: {exc}"
                        )
                elif not budget_ok:
                    logger.info(
                        f"[{task_id}] Skipping orchestrator Phase 4/5 "
                        f"(post_player_remaining={post_player_remaining}s < "
                        f"{MIN_TURN_BUDGET_SECONDS}s)"
                    )
                    specialist_results_path = (
                        Path(worktree.path) / ".guardkit" / "autobuild" / task_id
                        / "specialist_results.json"
                    )
                    _si._merge_specialist_block(
                        specialist_results_path,
                        "phase_4",
                        {
                            "status": "skipped",
                            "duration_seconds": 0.0,
                            "error": (
                                f"specialist_skipped: budget exhausted "
                                f"(post_player_remaining={post_player_remaining}s)"
                            ),
                            **_si._PHASE_4_AGENT_FIELD_DEFAULTS,
                        },
                    )
                    try:
                        self._agent_invoker._inject_specialist_records_into_task_work_results(
                            task_id
                        )
                    except Exception as exc:
                        logger.warning(
                            f"[{task_id}] _inject_specialist_records_into_task_work_results "
                            f"raised after budget-skip: {exc}"
                        )
                else:
                    # Reuse / create a loop just like _invoke_player_safely does.
                    try:
                        _loop = asyncio.get_event_loop()
                        if _loop.is_closed():
                            raise RuntimeError("loop closed")
                    except RuntimeError:
                        _loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(_loop)

                    # Phase 4: test-orchestrator
                    # TASK-ABSR-WALL: cap specialist sdk_timeout at remaining wall
                    _phase4_start = time.monotonic()
                    phase4_result = _loop.run_until_complete(
                        _si.invoke_test_orchestrator(
                            worktree_path=worktree.path,
                            task_id=task_id,
                            sdk_timeout=self._cap_specialist_timeout(
                                remaining_budget=remaining_budget,
                                task_id=task_id,
                            ),
                            agent_invoker=self._agent_invoker,
                            cancellation_event=self._cancellation_event,
                            turn=turn,
                        )
                    )

                    # TASK-ATR-002: refresh remaining_budget post-Phase-4 so the
                    # Phase 5 cap reflects actual wall consumed by Phase 4.
                    # The original `remaining_budget` is the start-of-turn
                    # value; reusing it here would over-allocate Phase 5 by
                    # the wall Phase 4 already burned, risking post-specialist
                    # Coach overrun of the feature task_timeout.
                    if remaining_budget is not None:
                        _phase4_elapsed = time.monotonic() - _phase4_start
                        phase5_remaining: Optional[float] = max(
                            0.0, remaining_budget - _phase4_elapsed
                        )
                    else:
                        phase5_remaining = None

                    # Phase 5: code-reviewer (only if Phase 4 passed)
                    if phase4_result.status == "passed":
                        _loop.run_until_complete(
                            _si.invoke_code_reviewer(
                                worktree_path=worktree.path,
                                task_id=task_id,
                                phase4_result=phase4_result,
                                sdk_timeout=self._cap_specialist_timeout(
                                    remaining_budget=phase5_remaining,
                                    task_id=task_id,
                                ),
                                agent_invoker=self._agent_invoker,
                                cancellation_event=self._cancellation_event,
                                turn=turn,
                            )
                        )
                    else:
                        # Phase 4 failed/skipped — write a phase_5 skipped block.
                        specialist_results_path = (
                            Path(worktree.path) / ".guardkit" / "autobuild" / task_id
                            / "specialist_results.json"
                        )
                        _si._merge_specialist_block(
                            specialist_results_path,
                            "phase_5",
                            {
                                "status": "skipped",
                                "duration_seconds": 0.0,
                                "error": f"phase_4 status={phase4_result.status}",
                                **_si._PHASE_5_AGENT_FIELD_DEFAULTS,
                            },
                        )

                    # Gate-credit injection (TASK-OSI-002)
                    try:
                        self._agent_invoker._inject_specialist_records_into_task_work_results(
                            task_id
                        )
                    except Exception as exc:
                        logger.warning(
                            f"[{task_id}] _inject_specialist_records_into_task_work_results "
                            f"raised: {exc}"
                        )
        # ===== End orchestrator-side Phase 4/5 =====

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
                    feedback=None,
                    timestamp=timestamp,
                    player_context_status=player_context_status,
                    sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                    sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                    sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', False),
                    command_results=tuple(command_exec_results) if command_exec_results else None,
                )
        else:
            # No cancellation: pass the caller-provided remaining budget to Coach
            coach_remaining_budget = remaining_budget

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
                sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', False),
                command_results=tuple(command_exec_results) if command_exec_results else None,
            )

        self._progress_display.start_turn(turn, "Coach Validation")

        logger.debug(f"Invoking Coach for turn {turn}")
        # TASK-FIX-A7B2: Snapshot peer edits for source-file contention check.
        peer_changed_files_snapshot = self._snapshot_peer_changed_files(task_id)

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
            peer_changed_files=peer_changed_files_snapshot,
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
                feedback=None,
                timestamp=timestamp,
                player_context_status=player_context_status,
                coach_context_status=coach_context_status,
                sdk_turns_used=getattr(player_result, 'sdk_turns_used', None),
                sdk_max_turns=getattr(player_result, 'sdk_max_turns', None),
                sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', False),
                command_results=tuple(command_exec_results) if command_exec_results else None,
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
                sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', False),
                command_results=tuple(command_exec_results) if command_exec_results else None,
            )

        else:  # feedback
            feedback_text = self._extract_feedback(coach_result.report)
            # TASK-RFX-F7F5: Inject command failure advisory into feedback
            # when Coach is already rejecting. Environment/transient failures
            # are suppressed; only implementation/unknown failures are shown.
            if player_result.success and player_result.report:
                cmd_failures = player_result.report.get("command_failures", [])
                advisory = build_command_failure_advisory(cmd_failures)
                if advisory:
                    feedback_text = feedback_text + "\n\n" + advisory
            is_config_error = coach_result.report.get("is_configuration_error", False)
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
                sdk_ceiling_hit=getattr(player_result, 'sdk_ceiling_hit', False),
                is_configuration_error=is_config_error,
                command_results=tuple(command_exec_results) if command_exec_results else None,
            )

    def _finalize_phase(
        self,
        worktree: Worktree,
        final_decision: Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "player_invocation_stall", "error", "cancelled", "configuration_error", "pre_loop_blocked", "design_extraction_failed", "honesty_collapse"],
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
        # honesty_collapse is treated like max_turns_exceeded for this gate
        # (TASK-FIX-HEAB) — both terminate the loop with no Coach approval, so
        # any blocked_report the Player emitted is equally relevant.
        blocked_report = self._extract_blocked_report(turn_history)
        if blocked_report and final_decision in ("max_turns_exceeded", "honesty_collapse"):
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

        # Clean up per-thread Graphiti clients (TASK-FIX-GTP2)
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
            )

            # Ensure task_id is populated in report (TASK-ACR-001)
            synthetic_report["task_id"] = task_id

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
                success=True,  # Recovery succeeded
                report=synthetic_report,
                duration_seconds=0.0,
                error=None,
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

        Returns
        -------
        Dict[str, Any]
            Synthetic Player report
        """
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

        return report

    # --- Runtime command execution for command_execution criteria (TASK-CRV-537E) ---

    def _execute_command_criteria(
        self,
        synthetic_report: Dict[str, Any],
        acceptance_criteria: List[str],
        worktree_path: Path,
    ) -> List[CommandExecutionResult]:
        """Execute ``command_execution`` acceptance criteria in the worktree.

        Delegates to ``CoachValidator.verify_command_criteria()`` for the
        actual command execution and classification (TASK-RFX-7C63). This
        method handles orchestrator-level concerns: injecting passed criteria
        into ``synthetic_report["requirements_addressed"]`` and recording
        failures in ``synthetic_report["command_failures"]``.

        Parameters
        ----------
        synthetic_report : Dict[str, Any]
            The synthetic Player report to enrich.
        acceptance_criteria : List[str]
            Raw acceptance criteria text from the task.
        worktree_path : Path
            Worktree directory to use as ``cwd``.

        Returns
        -------
        List[CommandExecutionResult]
            Structured results for each executed command criterion
            (TASK-RFX-528E). Empty list if no command criteria found.
        """
        validator = CoachValidator(str(worktree_path))
        verification = validator.verify_command_criteria(
            acceptance_criteria,
            per_command_timeout=COMMAND_TIMEOUT_SECONDS,
            total_timeout=COMMAND_TOTAL_TIMEOUT_SECONDS,
        )

        # Inject passed criteria into synthetic report (orchestrator concern)
        for criterion_text in verification.passed_criteria:
            synthetic_report.setdefault("requirements_addressed", []).append(
                criterion_text
            )

        # Inject failures into synthetic report (orchestrator concern)
        for failure in verification.failures:
            synthetic_report.setdefault("command_failures", []).append(failure)

        return verification.results

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

    def _normalize_feedback_for_stall(
        self,
        feedback: str,
        turn_record: Optional["TurnRecord"] = None,
    ) -> str:
        """
        Normalize feedback text for stall detection by stripping volatile details.

        Applies regex substitutions to remove test-specific paths, line numbers,
        percentages, durations, and counts that vary between turns but represent
        the same underlying error category.

        TASK-FIX-7A07 AC-5: For ``agent_invocations_violation`` feedback, also
        fold a canonicalised representation of the violation's ``missing_phases``
        list (sorted) into the normalised output. Otherwise, a Player that
        reorders phase keys across turns could produce textually-different
        but semantically-identical feedback and bypass the stall detector.

        Parameters
        ----------
        feedback : str
            Raw Coach feedback text
        turn_record : Optional[TurnRecord]
            Completed turn record. When present, the method inspects the
            Coach's structured report for an ``agent_invocations_violation``
            issue and folds its sorted ``missing_phases`` into the signature
            input. When absent, falls back to text-only normalisation
            (preserves TASK-AB-SD01 behaviour for non-violation feedback).

        Returns
        -------
        str
            Normalized feedback with volatile details replaced by placeholders
            and, where applicable, a canonical violation fingerprint appended.
        """
        result = feedback
        for pattern, replacement in self._STALL_NORMALIZE_PATTERNS:
            result = pattern.sub(replacement, result)

        # Fold canonical violation fingerprint when the feedback came from
        # the agent-invocations gate. Without this, reordering of the
        # missing_phases list in the underlying violation would produce
        # two md5 signatures that differ despite being semantically identical.
        # When a violation is present we REPLACE the feedback text with the
        # canonical marker rather than appending to it — otherwise variant
        # renderings ("missing phases 4, 5" vs "missing phases 5, 4") still
        # propagate into the hash input.
        if turn_record is not None:
            violation = _extract_agent_invocations_violation(turn_record)
            if violation is not None:
                details = (
                    violation.get("details")
                    if isinstance(violation.get("details"), dict)
                    else {}
                )
                raw_missing = (
                    violation.get("missing_phases")
                    or details.get("missing_phases")
                    or []
                )
                if raw_missing and isinstance(raw_missing[0], dict):
                    normalised_missing = sorted(
                        str(m.get("phase", ""))
                        for m in raw_missing
                        if m.get("phase")
                    )
                else:
                    normalised_missing = sorted(str(m) for m in raw_missing)
                canonical = {
                    "category": "agent_invocations_violation",
                    "missing_phases": normalised_missing,
                    "expected_phases": violation.get("expected_phases")
                    or details.get("expected_phases"),
                    "actual_invocations": violation.get("actual_invocations")
                    or details.get("actual_invocations"),
                }
                result = "|CANONICAL|" + json.dumps(canonical, sort_keys=True)
        return result

    def _is_feedback_stalled(
        self,
        feedback: str,
        criteria_passed_count: int,
        threshold: int = 3,
        turn_record: Optional["TurnRecord"] = None,
    ) -> bool:
        """
        Detect repeated identical feedback with zero criteria progress (TASK-AB-SD01).

        Tracks Coach feedback signatures across turns and returns True when
        the same feedback repeats for ``threshold`` consecutive turns with
        no change in the number of passing acceptance criteria.

        When partial progress exists (criteria_passed_count > 0), the threshold
        is extended by 2 turns to give the Player more runway before declaring
        stall (TASK-REV-E719 Fix 3).

        Parameters
        ----------
        feedback : str
            Current Coach feedback text
        criteria_passed_count : int
            Number of acceptance criteria currently passing
        threshold : int, optional
            Number of consecutive identical turns before stall (default: 3)
        turn_record : Optional[TurnRecord]
            Current turn record used to fold canonical violation fingerprint
            into the signature when the feedback came from the
            agent-invocations gate (TASK-FIX-7A07 AC-5). When None, falls
            back to text-only normalisation.

        Returns
        -------
        bool
            True if feedback stall detected, False otherwise
        """
        normalized = self._normalize_feedback_for_stall(feedback, turn_record)
        feedback_sig = hashlib.md5(
            normalized.strip().lower().encode()
        ).hexdigest()[:8]

        self._feedback_history.append((feedback_sig, criteria_passed_count))

        if len(self._feedback_history) < threshold:
            return False

        recent = self._feedback_history[-threshold:]

        # All same feedback signature?
        sigs = {sig for sig, _ in recent}
        if len(sigs) != 1:
            return False

        # Zero criteria progress across all recent turns?
        counts = [count for _, count in recent]
        if all(c == counts[0] for c in counts):
            if counts[0] == 0:
                # True zero progress -- unrecoverable
                logger.warning(
                    f"Feedback stall: identical feedback (sig={feedback_sig}) "
                    f"for {threshold} turns with 0 criteria passing"
                )
                return True

            # Partial progress but stuck (TASK-REV-E719 Fix 3):
            # Extend threshold by 2 turns to give Player more runway.
            extended_threshold = threshold + 2
            if len(self._feedback_history) >= extended_threshold:
                extended_recent = self._feedback_history[-extended_threshold:]
                ext_sigs = {sig for sig, _ in extended_recent}
                ext_counts = [count for _, count in extended_recent]
                if len(ext_sigs) == 1:
                    if all(c == ext_counts[0] for c in ext_counts):
                        logger.warning(
                            f"Feedback stall: identical feedback (sig={feedback_sig}) "
                            f"for {extended_threshold} turns with {counts[0]} criteria "
                            f"passing (extended threshold for partial progress)"
                        )
                        return True
                    # Plateau-tolerant branch (TASK-GK-COACH-001):
                    # Tolerate exactly one count transition between turn 1 and
                    # turn 2 of the extended window; the remaining turns must
                    # be uniform AND non-zero. Closes the 0→N then plateau
                    # blind spot surfaced by FEAT-PEBR run-2
                    # (TASK-REV-PEBR-002). Bug B (TASK-GK-CV-001) is the most
                    # common trigger for this shape, but the structural blind
                    # spot exists for any non-criteria gate that plateaus
                    # after a single criteria-count climb.
                    tail = ext_counts[1:]
                    if (
                        len(tail) >= extended_threshold - 1
                        and all(c == tail[0] for c in tail)
                        and tail[0] > 0
                        and tail[0] != ext_counts[0]
                    ):
                        logger.warning(
                            f"Feedback stall: identical feedback (sig={feedback_sig}) "
                            f"for {extended_threshold - 1} consecutive turns with "
                            f"{tail[0]} criteria passing after a 1-turn count "
                            f"transition (plateau-tolerant extended threshold)"
                        )
                        return True

            logger.info(
                f"Partial progress stall warning: {counts[0]} criteria passing "
                f"but stuck for {len(self._feedback_history)} turns. "
                f"Extended threshold: {extended_threshold} turns."
            )
            return False

        return False

    def _is_player_invocation_stalled(
        self,
        turn_history: List[TurnRecord],
        threshold: int = 3,
    ) -> bool:
        """
        Detect N consecutive turns where the Player never produced a real report
        (TASK-FIX-7A02).

        Distinct from feedback stall: feedback stall fires when Coach keeps
        rejecting identical *real* Player output. This fires when the Player
        itself never ran to completion at the SDK layer — either because
        ``player_result.error`` is non-None, or because the orchestrator had
        to build a synthetic recovery report (``report["_synthetic"] is True``).

        Both conditions mean the downstream task-blaming hint
        (``"Review task_type classification..."``) is a misdiagnosis — the task
        is fine, the Player never ran.

        Parameters
        ----------
        turn_history : List[TurnRecord]
            Complete turn history for the current run.
        threshold : int, optional
            Number of trailing turns that must all be player-invocation failures
            before declaring stall (default: 3, matches ``_is_feedback_stalled``).

        Returns
        -------
        bool
            True when the trailing ``threshold`` turns are all player-invocation
            failures, False otherwise.
        """
        if len(turn_history) < threshold:
            return False

        recent = turn_history[-threshold:]
        for tr in recent:
            if not self._is_player_invocation_failure(tr):
                return False

        first_error = (
            recent[0].player_result.error
            if recent[0].player_result and recent[0].player_result.error
            else None
        )
        logger.warning(
            f"Player-invocation stall: {threshold} trailing turns failed at "
            f"the SDK layer (first-turn error: {first_error!r})"
        )
        return True

    @staticmethod
    def _is_player_invocation_failure(turn_record: TurnRecord) -> bool:
        """
        Return True when this turn's Player never produced a real report
        (TASK-FIX-7A02).

        Two cases:
        1. Player errored and recovery failed → ``turn_record.decision == "error"``
           with ``player_result.error`` set and no recovery.
        2. Player errored and state-recovery succeeded → the substituted
           ``player_result.report`` carries ``"_synthetic": True``.

        Both mean the Player never produced a real report for this turn.
        """
        if turn_record.player_result is None:
            return False

        if turn_record.player_result.error:
            return True

        report = turn_record.player_result.report or {}
        if report.get("_synthetic") is True:
            return True

        return False

    def _count_criteria_passed(self, turn_record: TurnRecord) -> int:
        """
        Count acceptance criteria verified as passing from Coach's actual decision.

        Sources the count from ``validation_results.requirements.criteria_met``
        which is the Coach validator's authoritative verified count.  This
        ensures the stall detector and Coach always agree on progress
        (TASK-CRV-90FB).

        Falls back to counting ``acceptance_criteria_verification.criteria_results``
        entries with ``status == "verified"`` when the structured path is absent
        (backward compatibility with older Coach report formats).

        Parameters
        ----------
        turn_record : TurnRecord
            Completed turn record

        Returns
        -------
        int
            Number of criteria verified by the Coach
        """
        if not turn_record.coach_result or not turn_record.coach_result.report:
            return 0

        report = turn_record.coach_result.report

        # Primary source: Coach's authoritative criteria_met (TASK-CRV-90FB)
        validation_results = report.get("validation_results", {}) or {}
        requirements = validation_results.get("requirements", {}) or {}
        criteria_met = requirements.get("criteria_met")
        if criteria_met is not None:
            return int(criteria_met)

        # Fallback: count from acceptance_criteria_verification (legacy)
        verification = report.get("acceptance_criteria_verification", {})
        criteria_results = verification.get("criteria_results", [])
        return sum(
            1 for r in criteria_results
            if r.get("status") == "verified"
        )

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
        Graphiti write has been replaced with local file persistence.

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
        TASK-RFX-5FED: Replaced blocking Graphiti capture (30s timeout per turn)
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
                verification = turn_record.coach_result.report.get(
                    "acceptance_criteria_verification", {}
                )
                criteria_results = verification.get("criteria_results", [])
                for result in criteria_results:
                    criterion_id = result.get("criterion_id", "")
                    status = result.get("status", "not_started")
                    if criterion_id:
                        ac_status[criterion_id] = status

            # Extract test metrics
            tests_passed = None
            tests_failed = None
            coverage = None
            arch_score = None

            if turn_record.coach_result and turn_record.coach_result.report:
                validation = turn_record.coach_result.report.get("validation_results", {})
                if validation.get("tests_passed"):
                    # Get test counts
                    tests_passed = self._extract_test_count(turn_record)
                    tests_failed = 0
                elif validation.get("test_output_summary"):
                    # Try to extract from output
                    tests_passed = self._extract_test_count(turn_record)
                    tests_failed = 0 if validation.get("tests_passed") else 1

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

            # TASK-RFX-5FED: Write turn state to local file (<1ms, replaces 30s Graphiti timeout)
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

    def _record_honesty(self, turn_record: TurnRecord) -> None:
        """
        Record honesty score from turn's Coach verification results.

        Extracts the honesty_verification data from the Coach report and tracks
        the score for cumulative honesty tracking across turns.

        Parameters
        ----------
        turn_record : TurnRecord
            Completed turn record with Coach results

        Notes
        -----
        If honesty scores drop below threshold (avg < 0.8 over 3+ turns),
        a warning is logged to alert about potential Player reliability issues.
        """
        if not turn_record.coach_result or not turn_record.coach_result.success:
            return

        honesty_data = turn_record.coach_result.report.get("honesty_verification")
        if honesty_data is None:
            logger.debug(
                f"Turn {turn_record.turn}: no honesty payload to record "
                f"(operator-handoff or pre-_verify_honesty short-circuit)"
            )
            return
        honesty_score = honesty_data.get("honesty_score", 1.0)

        self._honesty_history.append(honesty_score)

        # Check for sustained low honesty
        if len(self._honesty_history) >= 3:
            avg_honesty = sum(self._honesty_history[-3:]) / 3
            if avg_honesty < 0.8:
                logger.warning(
                    f"Player honesty concern: average score {avg_honesty:.2f} over last 3 turns "
                    f"(threshold: 0.8). Consider manual review."
                )

        # Log current turn's score
        discrepancy_count = honesty_data.get("discrepancy_count", 0)
        if discrepancy_count > 0:
            logger.info(
                f"Turn {turn_record.turn} honesty: {honesty_score:.2f} "
                f"({discrepancy_count} discrepancies)"
            )

    def _check_honesty_early_abort(
        self,
        turn_history: List[TurnRecord],
        *,
        task_id: str,
        worktree_path: Path,
    ) -> Optional[str]:
        """
        Decide whether the rolling honesty average has collapsed enough to
        abort the loop early (TASK-FIX-HEAB).

        Returns ``None`` when no abort is indicated. Returns an
        operator-facing diagnostic string when:

        1. ``len(self._honesty_history) >= self.honesty_early_abort_window``
           AND
        2. ``mean(self._honesty_history[-window:]) < self.honesty_early_abort_threshold``.

        The diagnostic names the rolling average, the threshold, the
        most-flagged ``player_claim`` across the window (filtered to
        Coach issues with category ``"honesty"`` or ``"claim_audit"``),
        and the number of turns saved by short-circuiting. When the
        most-flagged path matches a ``.gitignore`` rule in the worktree,
        a best-effort ``git check-ignore -v`` recommendation line is
        appended; failures of that subprocess are swallowed so the
        diagnostic always fires.

        Parameters
        ----------
        turn_history : List[TurnRecord]
            Per-turn records from the loop. Used to extract the
            most-flagged claim across ``[-window:]``.
        task_id : str
            Task identifier; included in the message for log correlation.
        worktree_path : Path
            Worktree root, used as cwd for the ``git check-ignore``
            best-effort lookup.

        Returns
        -------
        Optional[str]
            ``None`` when no abort indicated, otherwise the diagnostic
            string the loop should log before returning
            ``"honesty_collapse"``.
        """
        # Defensive lookups: tests / future callers that construct the
        # orchestrator via ``__new__`` to exercise narrow code paths
        # (e.g. tests/unit/test_autobuild_timeout_budget.py) won't have
        # set these attributes. Fall back to the same defaults the ctor
        # uses so the helper is a no-op rather than raising
        # AttributeError on those code paths.
        window = getattr(self, "honesty_early_abort_window", 3)
        threshold = getattr(self, "honesty_early_abort_threshold", 0.3)
        history = getattr(self, "_honesty_history", None) or []

        # AC-7: window precondition. Suppresses first-turn false trips.
        if len(history) < window:
            return None

        recent = history[-window:]
        rolling_avg = sum(recent) / len(recent)
        if rolling_avg >= threshold:
            return None

        abort_turn = len(history)
        max_turns = getattr(self, "max_turns", abort_turn)
        saved = max(0, max_turns - abort_turn)

        # AC-2: most-flagged player_claim across the window. Iterate the
        # tail of turn_history (its length should match the honesty
        # window when called from the loop, but slice defensively in
        # case of resume scenarios that pre-populate _honesty_history).
        claim_counter: Counter = Counter()
        for tr in turn_history[-window:]:
            coach = getattr(tr, "coach_result", None)
            if coach is None or not getattr(coach, "success", False):
                continue
            report = getattr(coach, "report", None) or {}
            issues = report.get("issues") or []
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                if issue.get("category") not in {"honesty", "claim_audit"}:
                    continue
                details = issue.get("details") or {}
                claim = details.get("player_claim")
                if claim:
                    claim_counter[claim] += 1

        top_claim: Optional[str] = None
        top_count: int = 0
        if claim_counter:
            top_claim, top_count = claim_counter.most_common(1)[0]

        lines: List[str] = [
            f"HONESTY COLLAPSE [{task_id}]: rolling avg {rolling_avg:.2f} "
            f"over last {window} turns < threshold {threshold:.2f}.",
        ]
        if top_claim is not None:
            lines.append(
                f"Most-flagged claim: '{top_claim}' "
                f"({top_count} of last {window} turns)."
            )
        lines.append(
            f"Saved {saved} turn(s) of {max_turns} "
            f"(aborted at turn {abort_turn})."
        )

        # AC-2: best-effort git check-ignore -v recommendation. Skip the
        # rec line silently on any failure (no .gitignore match, git
        # missing, subprocess error). The diagnostic must still fire.
        if top_claim is not None:
            rec = self._git_check_ignore_rec(top_claim, worktree_path)
            if rec is not None:
                lines.append(rec)

        return "\n".join(lines)

    @staticmethod
    def _git_check_ignore_rec(
        candidate_path: str, worktree_path: Path
    ) -> Optional[str]:
        """Run ``git check-ignore -v --no-index`` against ``candidate_path``.

        Returns a one-line operator recommendation when the path matches
        a ``.gitignore`` rule, or ``None`` on no-match / any error. Mirrors
        TASK-FIX-IGNR's ``--no-index`` invocation so untracked paths the
        Player keeps re-claiming surface their gitignore origin.
        """
        try:
            proc = subprocess.run(
                [
                    "git",
                    "check-ignore",
                    "-v",
                    "--no-index",
                    candidate_path,
                ],
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None
        if proc.returncode == 0 and proc.stdout.strip():
            return (
                f"Path matches a .gitignore rule "
                f"(git check-ignore -v): {proc.stdout.strip()}"
            )
        return None

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

        # Extract verifications from Coach decision
        verifications: List[CriterionVerification] = []
        if turn_record.coach_result and turn_record.coach_result.success:
            verifications_data = turn_record.coach_result.report.get("criteria_verification", [])
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
        pending_count = total_criteria - len(verifications)

        # Calculate percentage
        completion_percentage = calculate_completion_percentage(promises, verifications)

        # Display progress header
        logger.info(
            f"Criteria Progress (Turn {turn_record.turn}): "
            f"{verified_count}/{total_criteria} verified ({completion_percentage:.0f}%)"
        )

        # Log detailed status for each criterion
        for i, criterion_text in enumerate(acceptance_criteria):
            criterion_id = f"AC-{i+1:03d}"

            # Find matching promise
            promise = next((p for p in promises if p.criterion_id == criterion_id), None)
            verification = verification_map.get(criterion_id)

            if verification:
                if verification.result == VerificationResult.VERIFIED:
                    status = "VERIFIED"
                    icon = "+"
                else:
                    status = "REJECTED"
                    icon = "x"
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
                f"Criteria: {verified_count} verified, {rejected_count} rejected, {pending_count} pending",
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

        Creates a fresh GraphitiClient initialized on this thread's event loop,
        then wraps it in an AutoBuildContextLoader. Thread-local storage ensures
        each parallel worker gets its own independent client, avoiding the
        cross-loop Neo4j errors that caused hangs in FEAT-6EDD.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the current thread. The Graphiti client's Neo4j
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
        try:
            client = self._factory.get_thread_client()
            if client is None:
                self._thread_loaders[thread_id] = (None, loop)
                logger.info(f"Per-thread Graphiti client not available for thread {thread_id}")
                return None

            # Lazy initialization: if pending, initialize on THIS loop
            if getattr(client, '_pending_init', False):
                success = loop.run_until_complete(client.initialize())
                client._pending_init = False
                if not success:
                    self._thread_loaders[thread_id] = (None, loop)
                    logger.info(f"Per-thread Graphiti client init failed for thread {thread_id}")
                    return None
            elif not client.is_initialized:
                # Client exists but not initialized and not pending — try to init
                success = loop.run_until_complete(client.initialize())
                if not success:
                    self._thread_loaders[thread_id] = (None, loop)
                    logger.info(f"Per-thread Graphiti client init failed for thread {thread_id}")
                    return None

            loader = AutoBuildContextLoader(
                graphiti=client, verbose=self.verbose,
                worktree_path=getattr(self, '_active_worktree_path', None),
            )
            self._thread_loaders[thread_id] = (loader, loop)
            logger.info(f"Created per-thread context loader for thread {thread_id}")
            return loader
        except Exception as e:
            self._thread_loaders[thread_id] = (None, loop)
            logger.warning(f"Error creating per-thread context loader: {e}")
            return None

    def _cleanup_thread_loaders(self) -> None:
        """Close all per-thread Graphiti clients (TASK-FIX-GTP2, TASK-ACR-005, TASK-ACR-006).

        Called during finalization to clean up resources. Each thread-local
        GraphitiClient has its own Neo4j driver that must be closed.

        TASK-ACR-005: Uses stored event loop reference to avoid cross-loop errors.
        TASK-ACR-006: Three-branch cleanup based on loop state to prevent
        RuntimeError when locks are bound to different event loops.
        TASK-GLF-002: Sets _shutting_down flag to suppress late Graphiti operations.
        """
        self._shutting_down = True  # TASK-GLF-002: Prevent late Graphiti ops
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
                logger.debug(f"Closed per-thread Graphiti client for thread {thread_id}")
            except RuntimeError as e:
                logger.debug(f"Thread {thread_id} cleanup RuntimeError (suppressed): {e}")
            except concurrent.futures.TimeoutError:
                logger.warning(f"Thread {thread_id} cleanup timed out after 30s (suppressed)")
            except Exception as e:
                logger.warning(f"Error closing per-thread Graphiti client for thread {thread_id}: {e}")
        self._thread_loaders.clear()

    # ========================================================================
    # Instrumentation Helpers (TASK-INST-004)
    # ========================================================================

    def _emit_task_started(self, task_id: str) -> None:
        """Emit task.started lifecycle event.

        Parameters
        ----------
        task_id : str
            Task identifier being started.
        """
        event = TaskStartedEvent(
            run_id=f"run-{task_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
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
            run_id=f"run-{task_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            task_id=task_id,
            agent_role="player",
            attempt=1,
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
            run_id=f"run-{task_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            task_id=task_id,
            agent_role="player",
            attempt=1,
            timestamp=datetime.now().isoformat(),
            failure_category=failure_category,
        )
        try:
            asyncio.run(self._emitter.emit(event))
        except Exception as exc:
            logger.warning("Failed to emit task.failed event: %s", exc)

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
        When enable_context=True, retrieves job-specific context from Graphiti
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
                            tech_stack="python",  # TODO: Detect from task
                            complexity=5,  # TODO: Get from task metadata
                            previous_feedback=feedback,
                        )
                    )
                    context_prompt = context_result.prompt_text

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
                    context_prompt = ""
                    self._last_player_context_status = ContextStatus(
                        status="failed", reason=str(e)
                    )
            elif self.enable_context:
                logger.info(f"Player context retrieval skipped: no factory or loader for {task_id}")
                self._last_player_context_status = ContextStatus(
                    status="skipped", reason="no factory or loader"
                )
            else:
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
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={"unrecoverable": True},
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

    def _snapshot_peer_changed_files(
        self, task_id: str
    ) -> Optional[Dict[str, frozenset]]:
        """Return a stable snapshot of peer-task file edits in this wave.

        TASK-FIX-A7B2. Returns ``None`` when no wave-shared map is configured
        (single-task path) so the Coach knows there is no peer information to
        evaluate. Returns an empty dict when configured but no peer has
        published yet (this is the first task to finish in the wave). Returns
        a dict of ``peer_task_id -> frozenset[file]`` otherwise. The current
        task's own entry is excluded.
        """
        if (
            self._wave_changed_files is None
            or self._wave_files_lock is None
        ):
            return None
        with self._wave_files_lock:
            return {
                peer_id: files
                for peer_id, files in self._wave_changed_files.items()
                if peer_id != task_id
            }

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
        peer_changed_files: Optional[Dict[str, Any]] = None,
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
        from Graphiti to inform Coach validation decisions.
        """
        import time
        import asyncio

        start_time = time.time()

        # Retrieve job-specific context for Coach if enabled (TASK-GR6-006, TASK-FIX-GTP2)
        # Uses per-thread context loader to avoid cross-loop Neo4j errors
        context_prompt = ""
        self._last_coach_context_status = None  # Reset per invocation (TASK-FIX-GCW5)

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
                        tech_stack="python",  # TODO: Detect from task
                        complexity=5,  # TODO: Get from task metadata
                        player_report=player_report,
                    )
                )
                context_prompt = context_result.prompt_text

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
                context_prompt = ""
                self._last_coach_context_status = ContextStatus(
                    status="failed", reason=str(e)
                )
        elif self.enable_context:
            logger.info(f"Coach context retrieval skipped: no factory or loader for {task_id}")
            self._last_coach_context_status = ContextStatus(
                status="skipped", reason="no factory or loader"
            )
        else:
            self._last_coach_context_status = ContextStatus(status="disabled")

        # TASK-HMIG-008R Part B (Revision 3): branch on GUARDKIT_COACH_LEGACY.
        #
        # Default (env var unset): LLM Coach is the primary decision-maker.
        # CoachValidator runs gather_evidence to produce a CoachEvidenceBundle,
        # and the LLM Coach is invoked unconditionally via
        # self._agent_invoker.invoke_coach. The LLM Coach reads the bundle
        # (rendered into the prompt by _build_coach_prompt in Part C) and
        # writes coach_turn_N.json with approve/feedback.
        #
        # Legacy (GUARDKIT_COACH_LEGACY=1): deterministic CoachValidator is the
        # primary decision-maker (Option D / TASK-REV-0414 behaviour). The LLM
        # Coach is only invoked on validator exception. This is the
        # operator-controlled emergency-revert documented in
        # ``guardkit doctor`` and the TASK-HMIG-008R commit message.
        #
        # Per Phase 2.5 review finding #1, exception handling in the primary
        # path MUST NOT fall back to validator.validate() — that would
        # reactivate the path falsifier #1 requires to be GONE and bypass the
        # GUARDKIT_COACH_LEGACY operator-controlled revert. Unexpected
        # exceptions in gather_evidence are caught and surfaced as a synthetic
        # feedback coach_turn_N.json so the turn produces a deterministic
        # feedback decision, not silent approval and not a validator fallback.
        legacy_mode = os.environ.get("GUARDKIT_COACH_LEGACY") == "1"

        if legacy_mode:
            return self._invoke_coach_legacy(
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
                peer_changed_files=peer_changed_files,
                context_prompt=context_prompt,
                start_time=start_time,
            )

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
            peer_changed_files=peer_changed_files,
            context_prompt=context_prompt,
            start_time=start_time,
        )

    def _invoke_coach_legacy(
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
        peer_changed_files: Optional[Dict[str, Any]],
        context_prompt: str,
        start_time: float,
    ) -> AgentInvocationResult:
        """Legacy Coach flow: CoachValidator decides, LLM Coach is exception fallback.

        Pre-TASK-HMIG-008R behaviour preserved verbatim, gated on
        ``GUARDKIT_COACH_LEGACY=1``. Used as the operator-controlled
        emergency revert when the LLM Coach's leniency in canary surfaces a
        regression (Wave 3 / TASK-HMIG-009).
        """
        import time
        import asyncio

        logger.info(
            "Using CoachValidator (legacy, GUARDKIT_COACH_LEGACY=1) for "
            "%s turn %s", task_id, turn,
        )
        try:
            coach_cfg = self._load_coach_config()
            coach_test_execution = coach_cfg.get("test_execution", "sdk")
            matching_strategy = coach_cfg.get("matching_strategy", "auto")
            validator = CoachValidator(
                str(worktree.path),
                task_id=task_id,
                coach_test_execution=coach_test_execution,
                matching_strategy=matching_strategy,
                wave_size=wave_size,
                turn=turn,
                peer_changed_files=peer_changed_files,
                model_name=self._model_name,  # TASK-FIX-LGFM3
                coach_model_name=self._coach_model_name,  # TASK-FIX-COACHBUDG01
            )
            validation_result = validator.validate(
                task_id=task_id,
                turn=turn,
                task={
                    "acceptance_criteria": acceptance_criteria or [],
                    "task_type": task_type,
                    "requires_infrastructure": requires_infrastructure or [],
                    "_docker_available": validator._is_docker_available(),
                    "consumer_context": consumer_context or [],
                    "description": requirements or "",
                },
                skip_arch_review=skip_arch_review,
                context=context_prompt if context_prompt else None,
            )

            if context_prompt:
                logger.info(
                    f"[Graphiti] Coach context provided: {len(context_prompt)} chars"
                )

            duration = time.time() - start_time
            decision_path = validator.save_decision(validation_result)

            if player_report.get("command_results") and decision_path.exists():
                try:
                    with open(decision_path, "r") as f:
                        decision_data = json.load(f)
                    decision_data["command_results"] = player_report["command_results"]
                    with open(decision_path, "w") as f:
                        json.dump(decision_data, f, indent=2)
                except Exception as exc:
                    logger.debug("Failed to append command_results to coach decision: %s", exc)

            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=True,
                report=validation_result.to_dict(),
                duration_seconds=duration,
                error=None,
            )

        except Exception as e:
            logger.warning(f"CoachValidator failed, falling back to SDK: {e}")
            try:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                return loop.run_until_complete(
                    self._agent_invoker.invoke_coach(
                        task_id=task_id,
                        turn=turn,
                        requirements=requirements,
                        player_report=player_report,
                        remaining_budget=remaining_budget,
                    )
                )

            except NotImplementedError as sdk_error:
                logger.warning(f"Coach invocation not implemented: {sdk_error}")
                return AgentInvocationResult(
                    task_id=task_id,
                    turn=turn,
                    agent_type="coach",
                    success=False,
                    report={},
                    duration_seconds=time.time() - start_time,
                    error="SDK integration pending",
                )
            except Exception as sdk_error:
                logger.error(f"Coach invocation failed: {sdk_error}", exc_info=True)
                return AgentInvocationResult(
                    task_id=task_id,
                    turn=turn,
                    agent_type="coach",
                    success=False,
                    report={},
                    duration_seconds=time.time() - start_time,
                    error=f"Unexpected error: {str(sdk_error)}",
                )

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
        peer_changed_files: Optional[Dict[str, Any]],
        context_prompt: str,
        start_time: float,
    ) -> AgentInvocationResult:
        """Primary Coach flow (TASK-HMIG-008R): LLM Coach is the decision-maker.

        Per the Block adversarial-cooperation paper and the Revision 3
        architectural correction (operator-approved 2026-05-20), the LLM Coach
        is invoked unconditionally for every turn. CoachValidator runs
        ``gather_evidence`` to produce a structured ``CoachEvidenceBundle``
        which Part C will render into the Coach prompt via
        ``AgentInvoker._build_coach_prompt``.

        Exception handling per plan §3 / Phase 2.5 review finding #1:
        unexpected exceptions in ``gather_evidence`` write a synthetic
        ``feedback`` coach_turn_N.json with rationale naming the failure.
        The LLM Coach is NOT bypassed by a deterministic-validator fallback
        in this path — ``GUARDKIT_COACH_LEGACY=1`` is the sole, intentional,
        operator-controlled mechanism for reactivating ``validate()``.
        """
        import asyncio
        import time

        logger.info("Using LLM Coach (primary) for %s turn %s", task_id, turn)
        if context_prompt:
            logger.info(
                f"[Graphiti] Coach context provided: {len(context_prompt)} chars"
            )

        coach_cfg = self._load_coach_config()
        coach_test_execution = coach_cfg.get("test_execution", "sdk")
        matching_strategy = coach_cfg.get("matching_strategy", "auto")
        validator = CoachValidator(
            str(worktree.path),
            task_id=task_id,
            coach_test_execution=coach_test_execution,
            matching_strategy=matching_strategy,
            wave_size=wave_size,
            turn=turn,
            peer_changed_files=peer_changed_files,
            model_name=self._model_name,  # TASK-FIX-LGFM3
            coach_model_name=self._coach_model_name,  # TASK-FIX-COACHBUDG01
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
                },
                skip_arch_review=skip_arch_review,
                context=context_prompt if context_prompt else None,
            )
        except Exception as exc:  # noqa: BLE001 — primary path must not fall back
            logger.error(
                "gather_evidence raised in primary Coach path for %s turn %s: %s. "
                "Emitting synthetic feedback decision (no validate() fallback).",
                task_id, turn, exc, exc_info=True,
            )
            return self._emit_synthetic_coach_feedback(
                task_id=task_id,
                turn=turn,
                worktree=worktree,
                rationale=f"Evidence gathering failed: {exc}",
                start_time=start_time,
            )

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

                _sig = _inspect.signature(self._agent_invoker.invoke_coach)
                if "evidence_bundle" in _sig.parameters:
                    invoke_kwargs["evidence_bundle"] = evidence_bundle
                if "coach_context" in _sig.parameters and context_prompt:
                    invoke_kwargs["coach_context"] = context_prompt

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

            # TASK-FIX-COACHSF01: soft-fail on Coach verdict-emission failures.
            #
            # `AgentInvoker.invoke_coach` catches `CoachDecisionNotFoundError`
            # and `CoachDecisionInvalidError` internally (agent_invoker.py:
            # 1987-1997) and returns `success=False` with the exception
            # message as `error` — these never raise out of `invoke_coach`,
            # so the broader `except Exception` synthetic-feedback safety
            # net below cannot see them. Without this check the orchestrator
            # surfaces `coach_decision="error"` to the wave loop, the turn
            # hard-fails, and the Player gets no opportunity to retry.
            #
            # The failure class this catches is canary F2 at Coach level
            # (qwen36-workhorse-style substrates that discuss the Bash
            # heredoc verdict-write in prose without actually emitting the
            # tool_use block). It's a substrate-quality finding, not a
            # task-quality finding — so we convert it to a synthetic
            # feedback decision with a rationale naming the failure mode,
            # write coach_turn_N.json (so downstream consumers see a
            # consistent shape), and return success=True. The Player gets
            # a turn N+1 to retry; substrate variance may produce a real
            # verdict on the second attempt.
            #
            # Other `success=False` outcomes (`SDKTimeoutError` → "SDK
            # timeout after Xs", generic `Exception` → "Unexpected error: X")
            # are propagated unchanged: those are not verdict-emission
            # failures and the wave loop's existing handling is correct
            # for them.
            if (
                not result.success
                and result.error
                and (
                    "Coach decision not found" in result.error
                    or "Coach decision invalid" in result.error
                )
            ):
                logger.warning(
                    "Coach verdict-emission failed in primary path for %s "
                    "turn %s: %s. Emitting synthetic feedback decision "
                    "(substrate F2 at Coach level — Player will retry on "
                    "turn %s with this feedback).",
                    task_id, turn, result.error, turn + 1,
                )
                return self._emit_synthetic_coach_feedback(
                    task_id=task_id,
                    turn=turn,
                    worktree=worktree,
                    rationale=(
                        f"Coach verdict-emission failed: {result.error}. "
                        f"Likely substrate limitation (qwen36-workhorse F2 "
                        f"at Coach level). Player should retry on turn "
                        f"{turn + 1} with this feedback."
                    ),
                    start_time=start_time,
                )

            return result

        except NotImplementedError as sdk_error:
            logger.warning(
                "Coach invocation not implemented in primary path: %s. "
                "Emitting synthetic feedback decision.",
                sdk_error,
            )
            return self._emit_synthetic_coach_feedback(
                task_id=task_id,
                turn=turn,
                worktree=worktree,
                rationale=(
                    f"LLM Coach invocation not available "
                    f"(SDK integration pending): {sdk_error}. "
                    f"Set GUARDKIT_COACH_LEGACY=1 to use the deterministic "
                    f"CoachValidator path."
                ),
                start_time=start_time,
            )
        except Exception as sdk_error:  # noqa: BLE001 — surface as feedback, not fallback
            logger.error(
                "Coach invocation failed in primary path: %s. Emitting "
                "synthetic feedback decision.",
                sdk_error, exc_info=True,
            )
            return self._emit_synthetic_coach_feedback(
                task_id=task_id,
                turn=turn,
                worktree=worktree,
                rationale=f"LLM Coach invocation failed: {sdk_error}",
                start_time=start_time,
            )

    def _emit_synthetic_coach_feedback(
        self,
        *,
        task_id: str,
        turn: int,
        worktree: Worktree,
        rationale: str,
        start_time: float,
    ) -> AgentInvocationResult:
        """Write a synthetic feedback coach_turn_N.json and return its result.

        Used by the primary Coach flow (``_invoke_coach_primary``) when
        ``gather_evidence`` or ``AgentInvoker.invoke_coach`` raises an
        unexpected exception. Per Phase 2.5 review finding #1 and plan §3,
        the primary path MUST NOT fall back to ``CoachValidator.validate()`` —
        falsifier #1 ("the path autobuild._invoke_coach -> CoachValidator.validate()
        for the decision is GONE") requires that the validator never silently
        re-becomes the decision-maker on exception. ``GUARDKIT_COACH_LEGACY=1``
        remains the sole, intentional, operator-controlled revert.

        The synthetic decision schema mirrors ``CoachValidationResult.to_dict``
        closely enough that downstream consumers (autobuild's
        ``_display_criteria_progress``, ``_count_criteria_passed``) see a
        consistent shape: ``decision: "feedback"``, populated rationale,
        empty ``criteria_verification`` (no AC evaluation occurred).
        """
        import time

        duration = time.time() - start_time
        decision_dir = worktree.path / ".guardkit" / "autobuild" / task_id
        decision_dir.mkdir(parents=True, exist_ok=True)
        decision_path = decision_dir / f"coach_turn_{turn}.json"

        synthetic = {
            "task_id": task_id,
            "turn": turn,
            "decision": "feedback",
            "validation_results": {
                "quality_gates": None,
                "independent_tests": None,
                "requirements": None,
            },
            "criteria_verification": [],
            "acceptance_criteria_verification": {"criteria_results": []},
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "coach_primary_exception",
                    "description": rationale,
                }
            ],
            "rationale": rationale,
            "context_used": None,
            "approved_without_independent_tests": False,
            "is_configuration_error": False,
            "environment_conditional_approval": False,
            "honesty_verification": None,
            "coach_primary_synthetic_feedback": True,
        }
        try:
            with open(decision_path, "w") as f:
                json.dump(synthetic, f, indent=2)
            logger.info(
                "Wrote synthetic feedback decision to %s (rationale: %s)",
                decision_path, rationale,
            )
        except OSError as write_exc:
            logger.error(
                "Failed to write synthetic feedback decision to %s: %s",
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
        tests_written = len(report.get("tests_written", []))
        tests_passed = report.get("tests_passed", False)

        if not tests_required and tests_written == 0:
            tests_str = "tests not required"
        else:
            tests_str = f"{tests_written} tests ({'passing' if tests_passed else 'failing'})"

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

        # Build feedback from issues
        feedback_lines = []
        for issue in issues[:3]:  # Limit to top 3 issues
            desc = issue.get("description", "")
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

                if suggestion:
                    feedback_lines.append(f"- {desc}: {suggestion}")
                elif test_output:
                    # Use test output as the actionable detail
                    feedback_lines.append(f"- {desc}:\n  {test_output}")
                else:
                    feedback_lines.append(f"- {desc}")

        if len(issues) > 3:
            feedback_lines.append(f"... and {len(issues) - 3} more issues")

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
        ``description`` field for the summary.  ``_extract_feedback`` is
        intentionally left unchanged — the Player still receives the full,
        untruncated feedback text.

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
        severity_order: Dict[str, int] = {
            "must_fix": 0,
            "should_fix": 1,
            "warning": 2,
        }

        issues = coach_report.get("issues") or []
        if issues:
            primary = min(
                issues,
                key=lambda issue: severity_order.get(
                    issue.get("severity", "warning"), 99
                ),
            )
            description = primary.get("description", "") or ""
            if description:
                if len(description) > 80:
                    return f"Feedback: {description[:80]}..."
                return f"Feedback: {description}"

        # No issues or empty description — fall back to slicing the joined text
        if len(fallback_text) > 80:
            return f"Feedback: {fallback_text[:80]}..."
        return f"Feedback: {fallback_text}"

    def _build_environment_stall_diagnostic(
        self,
        turn_history: List["TurnRecord"],
    ) -> Optional[str]:
        """Build the environment_stall diagnostic message (TASK-ABSR-C3D4).

        Returns ``None`` when the worktree has no Python manifest — callers
        fall through to the generic stall message in that case. Reading the
        bootstrap state file and the manifest is best-effort: missing or
        unparseable inputs are silently omitted rather than raising.
        """
        n_turns = len(turn_history)

        # Resolve the worktree root for this task. The orchestrator clears
        # ``_active_worktree_path`` on finalize, so reconstruct from the
        # worktrees dir and the last turn's task_id.
        worktree_root: Optional[Path] = None
        if self._worktree_manager is not None and turn_history:
            last = turn_history[-1]
            if last.player_result and last.player_result.task_id:
                candidate = (
                    self._worktree_manager.worktrees_dir
                    / last.player_result.task_id
                )
                if candidate.exists():
                    worktree_root = candidate

        # Per the task spec: enrich only the Python-project case. If there is
        # no pyproject.toml, fall through to the generic diagnostic.
        if worktree_root is None or not (worktree_root / "pyproject.toml").exists():
            return None

        parts = [
            f"Unrecoverable stall detected after {n_turns} turn(s) [{STALL_ENVIRONMENT}].",
            "Stall driven by repeated infrastructure-class failures while all Player gates passed.",
        ]

        # Bootstrap state — best-effort.
        bootstrap_state_path = worktree_root / ".guardkit" / "bootstrap_state.json"
        if bootstrap_state_path.exists():
            try:
                state = json.loads(
                    bootstrap_state_path.read_text(encoding="utf-8")
                )
                if isinstance(state, dict):
                    fields: List[str] = []
                    if "success" in state:
                        fields.append(f"success={state.get('success')}")
                    if "installs_attempted" in state:
                        fields.append(
                            f"installs_attempted={state.get('installs_attempted')}"
                        )
                    if "installs_failed" in state:
                        fields.append(
                            f"installs_failed={state.get('installs_failed')}"
                        )
                    if fields:
                        parts.append("Bootstrap state: " + ", ".join(fields))
            except (OSError, json.JSONDecodeError, ValueError):
                pass

        # Active interpreter version.
        parts.append(f"Active Python interpreter: {platform.python_version()}")

        # requires-python from the manifest, via DetectedManifest helper.
        try:
            from guardkit.orchestrator.environment_bootstrap import (
                DetectedManifest,
            )

            manifest = DetectedManifest(
                path=worktree_root / "pyproject.toml",
                stack="python",
                is_lock_file=False,
                install_command=[],
            )
            requires_python = manifest.get_requires_python()
        except Exception:
            requires_python = None
        if requires_python:
            parts.append(f"Manifest requires-python: {requires_python}")

        parts.append(
            "Remediation: Set `bootstrap_failure_mode: block` in "
            "`.guardkit/config.yaml` (or pass `--bootstrap-failure-mode block`). "
            "Install a compatible interpreter with `uv python install <X>`, "
            "`pyenv install <X>`, or `conda create -n <name> python=<X>`."
        )
        parts.append("Worktree preserved for inspection.")

        return "\n".join(parts)

    def _build_summary_details(
        self,
        turn_history: List[TurnRecord],
        final_decision: Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "player_invocation_stall", "error", "cancelled", "timeout", "configuration_error", "pre_loop_blocked", "design_extraction_failed", "honesty_collapse"],
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
            # Check if this was a conditional approval (infrastructure-dependent)
            last_coach = turn_history[-1] if turn_history else None
            coach_report = (
                last_coach.coach_result.report
                if last_coach and last_coach.coach_result
                else None
            )
            if coach_report and coach_report.get("environment_conditional_approval"):
                # TASK-ABSR-2468: environment-class conditional approval
                # — the worktree's bootstrap was observably broken and
                # Player did everything right in the (broken) venv. Label
                # this distinctly so the human reviewer doesn't read it as
                # a generic "infra deps not configured" approval.
                return (
                    f"APPROVED with environment flag "
                    f"(known-broken bootstrap, independent tests skipped) "
                    f"after {len(turn_history)} turn(s).\n"
                    f"Worktree preserved at: {self._worktree_manager.worktrees_dir}\n"
                    f"Review and merge manually when ready.\n"
                    f"Note: Independent tests failed with environment-class "
                    f"infrastructure error (ImportError/ModuleNotFoundError) on "
                    f"a worktree whose bootstrap install is reported broken. "
                    f"Player's gates passed; the failure is environmental. "
                    f"Verify the implementation against a healthy bootstrap "
                    f"before merging."
                )
            if coach_report and coach_report.get("approved_without_independent_tests"):
                return (
                    f"APPROVED (infra-dependent, independent tests skipped) "
                    f"after {len(turn_history)} turn(s).\n"
                    f"Worktree preserved at: {self._worktree_manager.worktrees_dir}\n"
                    f"Review and merge manually when ready.\n"
                    f"Note: Independent tests were skipped due to infrastructure "
                    f"dependencies without Docker."
                )
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

        elif final_decision == "honesty_collapse":
            # TASK-FIX-HEAB: rolling-average honesty collapse short-circuits
            # the loop. The diagnostic produced by _check_honesty_early_abort
            # was logged at abort time and is the actionable artefact —
            # mirror it into the summary so terminal users see the same
            # context without grepping the log.
            n_turns = len(turn_history)
            avg = (
                sum(self._honesty_history[-self.honesty_early_abort_window:])
                / self.honesty_early_abort_window
            ) if len(self._honesty_history) >= self.honesty_early_abort_window else 0.0
            return (
                f"Honesty collapse detected after {n_turns} turn(s) "
                f"[honesty_early_abort].\n"
                f"Rolling average over last {self.honesty_early_abort_window} "
                f"turns: {avg:.2f} < threshold {self.honesty_early_abort_threshold:.2f}.\n"
                f"Worktree preserved for inspection.\n"
                f"Suggested action: inspect the most-recent Coach honesty "
                f"discrepancies and the worktree's .gitignore for "
                f"silently-excluded paths the Player keeps re-claiming."
            )

        elif final_decision == "player_invocation_stall":
            # Signal-based classification (TASK-FIX-7A02): Player never produced
            # a real report for N consecutive turns (SDK-layer failure or
            # synthetic-recovery report). Quote the first-turn error and list
            # the affected turn numbers so the summary points at the env, not
            # the task.
            player_error_turns = [
                tr for tr in turn_history
                if self._is_player_invocation_failure(tr)
            ]
            first_turn = player_error_turns[0] if player_error_turns else None
            first_error = (
                first_turn.player_result.error
                if first_turn and first_turn.player_result and first_turn.player_result.error
                else (
                    first_turn.player_result.report.get("_recovery_metadata", {}).get(
                        "detection_method"
                    ) if first_turn and first_turn.player_result else None
                ) or "unavailable"
            )
            affected_turns = ", ".join(str(tr.turn) for tr in player_error_turns)
            n_failed = len(player_error_turns)
            return (
                f"Player-invocation stall detected after {len(turn_history)} turn(s).\n"
                f"Player failed {n_failed}\u00d7 at the SDK layer before producing "
                f"any work (turns: {affected_turns}).\n"
                f"Underlying error (turn {first_turn.turn if first_turn else '?'}): "
                f"{first_error!r}\n"
                f"Worktree preserved for inspection.\n"
                f"Suggested checks:\n"
                f"  (a) `claude` is logged in on this host "
                f"(claude auth status / claude login)\n"
                f"  (b) `pip show claude-agent-sdk` matches the working "
                f"environment (version + install path)."
            )

        elif final_decision == "unrecoverable_stall":
            # Check if the stall was caused by SDK API errors (TASK-FIX-d5e6).
            # TASK-FIX-7A02: This is now the *fallback* path — the new
            # signal-based branch (player_invocation_stall) takes precedence
            # when detected. This branch preserves TASK-REV-8A08's diagnostic
            # for the case where Coach feedback text happens to carry the
            # "SDK API error" substring but the Player reports were real.
            recent_feedback = [
                tr.feedback for tr in turn_history
                if tr.feedback and tr.decision == "feedback"
            ]
            # TASK-FIX-7A07: Delegate stall sub-classification to the shared
            # classify_stall() helper. The new coach_agent_invocations_stall
            # branch takes precedence over the legacy SDK-API-error fallback
            # and the generic task-blaming hint \u2014 it names the specific
            # sub-agents the Player should invoke via the Task tool rather
            # than blaming the task's acceptance criteria.
            classification = classify_stall(
                turn_history,
                final_decision,
                threshold=3,
                context_pollution_fired=getattr(
                    self, "_context_pollution_no_checkpoint_fired", False
                ),
            )
            if (
                classification is not None
                and STALL_COACH_AGENT_INVOCATIONS in classification.co_fires
            ):
                worktree_root = (
                    self._worktree_manager.worktrees_dir
                    if self._worktree_manager is not None
                    else None
                )
                stack_template = detect_stack_template(worktree_root)
                task_id_str = (
                    turn_history[-1].player_result.task_id
                    if turn_history and turn_history[-1].player_result
                    else "{task_id}"
                )
                missing_phases_list = classification.missing_phases or ["4", "5"]
                # TASK-GK-PROF-001: pass workspace_root so Phase-3 resolution
                # consults the installed specialist set rather than the
                # hardcoded stack→specialist map.
                specialist_lines = render_missing_phase_list(
                    missing_phases_list,
                    stack_template=stack_template,
                    workspace_root=worktree_root,
                )
                specialist_block = "\n".join(
                    f"  - {line}" for line in specialist_lines
                )
                n_turns = len(turn_history)
                exp = classification.expected_phases
                actual = classification.actual_invocations
                co_fire_suffix = ""
                if len(classification.co_fires) > 1:
                    others = [
                        cf for cf in classification.co_fires
                        if cf != STALL_COACH_AGENT_INVOCATIONS
                    ]
                    co_fire_suffix = (
                        f"\nCo-fired stall sub-types: {', '.join(others)}."
                    )
                return (
                    f"Unrecoverable stall detected after {n_turns} turn(s) "
                    f"[{classification.decision_subtype}].\n"
                    f"Coach's agent-invocations gate rejected the Player's "
                    f"task-work results for {n_turns} consecutive turns "
                    f"(missing phases: {sorted(missing_phases_list)}; "
                    f"expected {exp if exp is not None else '?'}, "
                    f"actual {actual if actual is not None else '?'}).\n"
                    f"The Player appears to have completed the work inline "
                    f"without invoking the required sub-agents via the "
                    f"Task tool. Inspect "
                    f"`.guardkit/autobuild/{task_id_str}/task_work_results.json "
                    f"\u2192 agent_invocations_validation`.\n"
                    f"Remediation options:\n"
                    f"  (a) ensure the Player's system prompt mandates "
                    f"Task-tool invocation for the missing phases. "
                    f"Required specialists:\n"
                    f"{specialist_block}\n"
                    f"  (b) set `implementation_mode: direct` in the task "
                    f"frontmatter if the task's complexity does not warrant "
                    f"the specialist pipeline."
                    f"{co_fire_suffix}\n"
                    f"Worktree preserved for inspection."
                )

            # environment_stall branch: emit env-aware diagnostic naming the
            # bootstrap state, active interpreter, and requires-python
            # constraint. Falls through to the generic message when the
            # worktree has no Python manifest (TASK-ABSR-C3D4).
            if (
                classification is not None
                and STALL_ENVIRONMENT in classification.co_fires
            ):
                env_message = self._build_environment_stall_diagnostic(
                    turn_history
                )
                if env_message is not None:
                    return env_message

            # Fallback: Check if the stall was caused by SDK API errors
            # (TASK-FIX-d5e6). This preserves TASK-REV-8A08's diagnostic for
            # the case where Coach feedback text happens to carry the
            # "SDK API error" substring but the Player reports were real.
            if recent_feedback and all(
                "SDK API error" in fb for fb in recent_feedback[-3:]
            ):
                stall_hint = (
                    "Stall caused by SDK API errors \u2014 check "
                    "ANTHROPIC_BASE_URL configuration and SDK model name "
                    "compatibility (see vllm-serve.sh SERVED_MODEL_NAME)."
                )
            elif (
                classification is not None
                and STALL_CONTEXT_POLLUTION in classification.co_fires
            ):
                stall_hint = (
                    "Context pollution detected but no passing checkpoint "
                    "existed to roll back to \u2014 review the Player's "
                    "early turns for regression patterns."
                )
            else:
                stall_hint = (
                    "Review task_type classification and acceptance criteria."
                )
            return (
                f"Unrecoverable stall detected after {len(turn_history)} turn(s).\n"
                f"AutoBuild cannot make forward progress.\n"
                f"Worktree preserved for inspection.\n"
                f"Suggested action: {stall_hint}"
            )

        elif final_decision == "configuration_error":
            config_turn = next(
                (t for t in reversed(turn_history) if t.is_configuration_error), None
            )
            detail = config_turn.feedback if config_turn and config_turn.feedback else "unknown configuration error"
            return (
                f"Configuration error detected — loop exited immediately.\n"
                f"Detail: {detail}\n"
                f"Action: Fix the task_type in the task .md file and retry.\n"
                f"Worktree preserved for inspection."
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
        final_decision: Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "player_invocation_stall", "error", "cancelled", "timeout", "configuration_error", "pre_loop_blocked", "design_extraction_failed", "honesty_collapse"],
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

        elif final_decision == "honesty_collapse":
            # TASK-FIX-HEAB: rolling honesty average dropped below threshold;
            # short-circuit instead of burning the rest of max_turns.
            return (
                f"Honesty collapse: rolling avg over last "
                f"{self.honesty_early_abort_window} turns dropped below "
                f"threshold {self.honesty_early_abort_threshold:.2f} after "
                f"{len(turn_history)} turn(s)"
            )

        elif final_decision == "unrecoverable_stall":
            return (
                f"Unrecoverable stall detected after {len(turn_history)} turn(s). "
                f"AutoBuild cannot make forward progress."
            )

        elif final_decision == "configuration_error":
            config_turn = next(
                (t for t in reversed(turn_history) if t.is_configuration_error), None
            )
            if config_turn and config_turn.feedback:
                return (
                    f"Configuration error: {config_turn.feedback}. "
                    f"Fix the task_type in the task .md file and retry."
                )
            return "Configuration error in task file — fix task_type and retry"

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

        elif final_decision == "error":
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
        Resume orchestration from saved state in task frontmatter.

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
        logger.info(f"Resuming orchestration for {task_id} from {task_file_path}")

        try:
            with open(task_file_path, "r") as f:
                content = f.read()

            # Parse YAML frontmatter
            if not content.startswith("---"):
                raise SetupPhaseError("Task file missing frontmatter")

            parts = content.split("---", 2)
            if len(parts) < 3:
                raise SetupPhaseError("Invalid task file format")

            frontmatter = yaml.safe_load(parts[1])
            autobuild_state = frontmatter.get("autobuild_state", {})

            if not autobuild_state:
                raise SetupPhaseError(
                    f"No saved state found for {task_id}. "
                    "Run without --resume to start fresh."
                )

            # Restore worktree
            worktree_path = autobuild_state.get("worktree_path")
            if not worktree_path or not Path(worktree_path).exists():
                raise SetupPhaseError(
                    f"Worktree not found at {worktree_path}. "
                    "Run without --resume to start fresh."
                )

            worktree = Worktree(
                task_id=task_id,
                branch_name=f"autobuild/{task_id}",
                path=Path(worktree_path),
                base_branch=autobuild_state.get("base_branch", "main"),
            )

            # Restore turn history
            saved_turns = autobuild_state.get("turns", [])
            self._turn_history = self._deserialize_turn_history(saved_turns)

            # Initialize AgentInvoker with worktree path
            if self._agent_invoker is None:
                self._agent_invoker = AgentInvoker(
                    worktree_path=worktree.path,
                    max_turns_per_agent=self.max_turns,
                    development_mode=self.development_mode,
                    sdk_timeout_seconds=self.sdk_timeout,
                    use_task_work_delegation=True,
                    cancellation_event=self._cancellation_event,  # TASK-FIX-ASPF-004
                    venv_python=self._venv_python,  # TASK-FIX-7A05
                    model_name=self._model_name,  # TASK-FIX-MODELPLUMB
                    coach_model_name=self._coach_model_name,  # TASK-FIX-COACHBUDG01
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
        serialized = []
        for record in self._turn_history:
            serialized.append({
                "turn": record.turn,
                "decision": record.decision,
                "feedback": record.feedback,
                "timestamp": record.timestamp,
                "player_summary": (
                    record.player_result.report.get("implementation_notes", "")[:500]
                    if record.player_result.success
                    else record.player_result.error
                ),
                "player_success": record.player_result.success,
                "coach_success": record.coach_result.success if record.coach_result else False,
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

    def _extract_tests_passed(self, turn_record: TurnRecord) -> bool:
        """
        Extract test pass/fail status from turn record.

        Args:
            turn_record: Turn record with Coach validation results

        Returns:
            True if tests passed, False otherwise
        """
        if not turn_record.coach_result or not turn_record.coach_result.success:
            return False

        validation = turn_record.coach_result.report.get("validation_results", {})
        # Primary path: quality_gates.tests_passed (Coach stores results here)
        quality_gates = validation.get("quality_gates") or {}
        if "tests_passed" in quality_gates:
            value = quality_gates.get("tests_passed")
            if value is None:
                return False
            return bool(value)
        # Fallback: top-level tests_passed (backward compatibility)
        return validation.get("tests_passed", False)

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
        test_output = validation.get("test_output_summary", "")

        # Try to parse test count from output (e.g., "15 passed")
        import re
        match = re.search(r"(\d+)\s+(?:tests?\s+)?passed", test_output, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Fallback: assume some tests ran if tests_passed is True
        return 1 if validation.get("tests_passed", False) else 0


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
    # Map final_decision to task status
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
    elif loop_result.final_decision == "honesty_collapse":
        # TASK-FIX-HEAB: rolling-average honesty collapse — guide the operator
        # at the most-flagged claim and the worktree's .gitignore (the typical
        # silent-exclusion failure that motivated TASK-FIX-IGNR + this gate).
        next_steps = [
            f"Inspect Coach honesty issues: cat .guardkit/autobuild/{task_id}/coach_turn_{loop_result.total_turns}.json",
            f"Check the worktree's .gitignore: cd {worktree_path} && cat .gitignore",
            "Re-run with relaxed --honesty-early-abort-threshold once the cause is understood.",
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
