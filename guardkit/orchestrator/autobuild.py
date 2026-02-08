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
    ...     task_id="TASK-AB-001",
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
import hashlib
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

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
from guardkit.knowledge.graphiti_client import get_graphiti

# Import AutoBuild context loader for job-specific context (TASK-GR6-006)
from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader

# Import MCP design extractor for Phase 0 (TASK-DM-003)
from guardkit.orchestrator.mcp_design_extractor import (
    DesignData,
    DesignExtractor,
    DesignExtractionError,
    MCPUnavailableError,
)

# Setup logging
logger = logging.getLogger(__name__)


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


@dataclass
class OrchestrationResult:
    """
    Result of complete orchestration run.

    This dataclass encapsulates all information from a complete AutoBuild
    orchestration, including turn history, final decision, and worktree state.

    Attributes
    ----------
    task_id : str
        Task identifier (e.g., "TASK-AB-001")
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
    ...     task_id="TASK-AB-001",
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
    final_decision: Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "error", "pre_loop_blocked", "rate_limited", "design_extraction_failed"]
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
    ...     task_id="TASK-AB-001",
    ...     requirements="Implement feature X",
    ...     acceptance_criteria=["Criterion 1", "Criterion 2"],
    ... )
    """

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
        sdk_timeout: int = 900,
        skip_arch_review: bool = False,
        enable_perspective_reset: bool = True,
        enable_checkpoints: bool = True,
        rollback_on_pollution: bool = True,
        ablation_mode: bool = False,
        enable_context: bool = True,
        verbose: bool = False,
        context_loader: Optional[AutoBuildContextLoader] = None,
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
            SDK timeout in seconds for agent invocations (default: 600).
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
        self.skip_arch_review = skip_arch_review
        self.enable_perspective_reset = enable_perspective_reset
        self.enable_checkpoints = enable_checkpoints
        self.rollback_on_pollution = rollback_on_pollution
        self.ablation_mode = ablation_mode
        self._existing_worktree = existing_worktree  # For feature mode (TASK-FBC-001)
        # Hardcoded reset turns per architectural review (TASK-BRF-001): [3, 5]
        self.perspective_reset_turns: List[int] = [3, 5] if enable_perspective_reset else []
        self._turn_history: List[TurnRecord] = []
        self._honesty_history: List[float] = []  # Track honesty scores across turns
        self._checkpoint_manager: Optional[WorktreeCheckpointManager] = None  # Initialized lazily
        self.recovery_count: int = 0  # Track number of state recovery attempts
        # Stall detection: track (feedback_signature, criteria_passed_count) per turn (TASK-AB-SD01)
        self._feedback_history: List[Tuple[str, int]] = []

        # Context retrieval settings (TASK-GR6-006)
        self.enable_context = enable_context
        self.verbose = verbose
        self._context_loader = context_loader
        self._feature_id: Optional[str] = None  # Set during orchestration from task metadata

        # Log warning if ablation mode is active
        if self.ablation_mode:
            logger.warning(
                "⚠️ ABLATION MODE ACTIVE - Coach feedback disabled. "
                "This mode is for testing only and will produce inferior results."
            )

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
            f"verbose={self.verbose}"
        )

    def orchestrate(
        self,
        task_id: str,
        requirements: str,
        acceptance_criteria: List[str],
        base_branch: str = "main",
        task_file_path: Optional[Path] = None,
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
            Task identifier (e.g., "TASK-AB-001")
        requirements : str
            Task requirements description
        acceptance_criteria : List[str]
            List of acceptance criteria
        base_branch : str, optional
            Branch to create worktree from (default: "main")
        task_file_path : Optional[Path], optional
            Path to task file for state persistence (default: None)

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
        ...     task_id="TASK-AB-001",
        ...     requirements="Implement OAuth2 flow",
        ...     acceptance_criteria=["Support auth code flow", "Handle refresh"],
        ... )
        >>> print(result.final_decision)
        'approved'
        """
        logger.info(f"Starting orchestration for {task_id} (resume={self.resume})")

        pre_loop_result = None  # Initialize pre-loop result

        # Load task data to extract task_type for CoachValidator
        task_type: Optional[str] = None
        try:
            task_data = TaskLoader.load_task(task_id, repo_root=self.repo_root)
            task_type = task_data.get("frontmatter", {}).get("task_type")
            if task_type:
                logger.debug(f"Loaded task_type from task file: {task_type}")
        except TaskNotFoundError:
            logger.debug(f"Task file not found for {task_id}, continuing with task_type=None")
        except Exception as e:
            logger.debug(f"Failed to load task_type from task file: {e}, continuing with task_type=None")

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

            logger.info(
                f"Orchestration complete: {task_id}, decision={final_decision}, "
                f"turns={len(turn_history)}"
            )

            return result

        except RateLimitExceededError as e:
            logger.error(f"Rate limit exceeded for {task_id}: {e}")
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
                    )

                return worktree

            # Create isolated worktree (normal mode)
            worktree = self._worktree_manager.create(
                task_id=task_id,
                base_branch=base_branch,
            )

            logger.info(f"Worktree created: {worktree.path}")

            # Initialize AgentInvoker with worktree path (lazy initialization)
            if self._agent_invoker is None:
                self._agent_invoker = AgentInvoker(
                    worktree_path=worktree.path,
                    max_turns_per_agent=self.max_turns,
                    development_mode=self.development_mode,
                    sdk_timeout_seconds=self.sdk_timeout,
                    use_task_work_delegation=True,
                )

            return worktree

        except WorktreeCreationError as e:
            logger.error(f"Setup phase failed: {e}")
            raise SetupPhaseError(f"Failed to create worktree: {e}") from e

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
    ) -> Tuple[List[TurnRecord], Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "error", "design_extraction_failed"]]:
        """
        Phase 3: Execute Player↔Coach adversarial loop.

        This phase implements the core adversarial workflow where Player
        implements and Coach validates, iterating until approval or max_turns.

        Loop Structure
        --------------
        - Turn 1: Player implements from scratch
        - Turn 2+: Player addresses Coach feedback
        - Exit: Coach approves OR max_turns exceeded OR critical error

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

        Returns
        -------
        Tuple[List[TurnRecord], Literal["approved", "max_turns_exceeded", "error", "design_extraction_failed"]]
            Tuple of (turn_history, final_decision)

        Decision Logic
        --------------
        - "approved": Coach approved, ready for human review
        - "max_turns_exceeded": Loop limit reached
        - "error": Critical error occurred

        Notes
        -----
        Player errors are recorded but don't stop the loop (Coach can provide
        guidance). Coach errors or SDK timeouts cause immediate loop exit.
        """
        logger.info(f"Phase 2 (Loop): Starting adversarial turns for {task_id} from turn {start_turn}")

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

        with self._progress_display:
            for turn in range(start_turn, self.max_turns + 1):
                logger.info(f"Executing turn {turn}/{self.max_turns}")

                # Check if perspective should be reset to prevent anchoring bias
                # When reset triggered, Player receives only original requirements (no feedback)
                if self._should_reset_perspective(turn):
                    previous_feedback = None

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
                )

                turn_history.append(turn_record)
                self._turn_history = turn_history  # Keep internal copy for state

                # Capture turn state for cross-turn learning (TASK-GE-002)
                self._capture_turn_state(turn_record, acceptance_criteria, task_id=task_id)

                # Record honesty score from Coach's verification
                self._record_honesty(turn_record)

                # Display criteria progress after each turn
                self._display_criteria_progress(turn_record, acceptance_criteria)

                # Persist state after each turn
                if task_file_path:
                    self._save_state(task_file_path, worktree, "in_progress")

                # Create checkpoint after turn completes (if enabled)
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
                                return turn_history, "unrecoverable_stall"

                # Check for repeated feedback stall (TASK-AB-SD01 Mechanism 2)
                if turn_record.decision == "feedback" and turn_record.feedback:
                    criteria_passed = self._count_criteria_passed(turn_record)
                    if self._is_feedback_stalled(turn_record.feedback, criteria_passed):
                        logger.error(
                            f"Feedback stall detected for {task_id}: "
                            f"identical feedback for 3 consecutive turns "
                            f"with 0% criteria progress. "
                            f"Exiting loop early."
                        )
                        return turn_history, "unrecoverable_stall"

                # Check decision
                if turn_record.decision == "approve":
                    logger.info(f"Coach approved on turn {turn}")
                    return turn_history, "approved"

                elif turn_record.decision == "error":
                    logger.error(f"Critical error on turn {turn}")
                    return turn_history, "error"

                elif turn_record.decision == "feedback":
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

    def _execute_turn(
        self,
        turn: int,
        task_id: str,
        requirements: str,
        worktree: Worktree,
        previous_feedback: Optional[str],
        task_type: Optional[str] = None,
        skip_arch_review: bool = False,
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
        )

        # Display Player completion
        if player_result.success:
            summary = self._build_player_summary(player_result.report)
            self._progress_display.complete_turn("success", summary)
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

            # Attempt multi-layered state detection
            recovered_player_result = self._attempt_state_recovery(
                task_id=task_id,
                turn=turn,
                worktree=worktree,
                original_error=player_result.error,
            )

            if recovered_player_result:
                # State recovery succeeded - continue with recovered data
                player_result = recovered_player_result
                logger.info(
                    f"State recovery successful for {task_id} turn {turn}"
                )
                summary = self._build_player_summary(player_result.report)
                self._progress_display.complete_turn(
                    "success",
                    f"[RECOVERED] {summary}",
                )
            else:
                # State recovery failed - return error
                logger.warning(
                    f"State recovery failed for {task_id} turn {turn}"
                )
                return TurnRecord(
                    turn=turn,
                    player_result=player_result,
                    coach_result=None,
                    decision="error",
                    feedback=None,
                    timestamp=timestamp,
                )

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
            )

        self._progress_display.start_turn(turn, "Coach Validation")

        logger.debug(f"Invoking Coach for turn {turn}")
        coach_result = self._invoke_coach_safely(
            task_id=task_id,
            turn=turn,
            requirements=requirements,
            player_report=player_result.report,
            worktree=worktree,
            task_type=task_type,
            skip_arch_review=skip_arch_review,
        )

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
            )

        # Extract decision and feedback
        decision_value = coach_result.report.get("decision", "feedback")

        if decision_value == "approve":
            self._progress_display.complete_turn(
                "success",
                "Coach approved - ready for human review",
            )
            return TurnRecord(
                turn=turn,
                player_result=player_result,
                coach_result=coach_result,
                decision="approve",
                feedback=None,
                timestamp=timestamp,
            )

        else:  # feedback
            feedback_text = self._extract_feedback(coach_result.report)
            summary = (
                f"Feedback: {feedback_text[:80]}..."
                if len(feedback_text) > 80
                else f"Feedback: {feedback_text}"
            )
            self._progress_display.complete_turn("feedback", summary)

            return TurnRecord(
                turn=turn,
                player_result=player_result,
                coach_result=coach_result,
                decision="feedback",
                feedback=feedback_text,
                timestamp=timestamp,
            )

    def _finalize_phase(
        self,
        worktree: Worktree,
        final_decision: Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "error", "pre_loop_blocked", "design_extraction_failed"],
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

        # Check for blocked report in last Player report (escape hatch pattern)
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
            # Use MultiLayeredStateTracker for cascade detection
            state_tracker = MultiLayeredStateTracker(
                task_id=task_id,
                worktree_path=worktree.path,
            )

            work_state = state_tracker.capture_state(turn=turn)

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
            synthetic_report = self._build_synthetic_report(work_state, original_error)

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
    ) -> Dict[str, Any]:
        """
        Build synthetic Player report from detected work state.

        Creates a report structure compatible with existing Coach validation,
        including all detected files and test results.

        Parameters
        ----------
        work_state : WorkState
            Detected work state
        original_error : Optional[str]
            Original error for context

        Returns
        -------
        Dict[str, Any]
            Synthetic Player report
        """
        report = {
            "task_id": "",  # Filled by caller
            "turn": work_state.turn_number,
            "files_modified": work_state.files_modified,
            "files_created": work_state.files_created,
            "tests_written": work_state.tests_written,
            "tests_run": work_state.test_count > 0,
            "tests_passed": work_state.tests_passed,
            "test_output_summary": (
                work_state.test_results.output_summary
                if work_state.test_results
                else ""
            ),
            "implementation_notes": (
                f"[RECOVERED via {work_state.detection_method}] "
                f"Original error: {original_error or 'Unknown'}"
            ),
            "concerns": [
                f"Player failed with error: {original_error or 'Unknown'}",
                f"Work recovered via {work_state.detection_method}",
            ],
            "requirements_addressed": [],  # Cannot determine from detection
            "requirements_remaining": [],  # Cannot determine from detection
            "_recovery_metadata": {
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
        }

        return report

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

    def _is_feedback_stalled(
        self,
        feedback: str,
        criteria_passed_count: int,
        threshold: int = 3,
    ) -> bool:
        """
        Detect repeated identical feedback with zero criteria progress (TASK-AB-SD01).

        Tracks Coach feedback signatures across turns and returns True when
        the same feedback repeats for ``threshold`` consecutive turns with
        no change in the number of passing acceptance criteria.

        Parameters
        ----------
        feedback : str
            Current Coach feedback text
        criteria_passed_count : int
            Number of acceptance criteria currently passing
        threshold : int, optional
            Number of consecutive identical turns before stall (default: 3)

        Returns
        -------
        bool
            True if feedback stall detected, False otherwise
        """
        feedback_sig = hashlib.md5(
            feedback.strip().lower().encode()
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
            logger.warning(
                f"Feedback stall: identical feedback (sig={feedback_sig}) "
                f"for {threshold} turns with {counts[0]} criteria passing"
            )
            return True

        return False

    def _count_criteria_passed(self, turn_record: TurnRecord) -> int:
        """
        Count acceptance criteria verified as passing from Coach report (TASK-AB-SD01).

        Parameters
        ----------
        turn_record : TurnRecord
            Completed turn record

        Returns
        -------
        int
            Number of criteria with 'verified' status
        """
        if not turn_record.coach_result or not turn_record.coach_result.report:
            return 0

        verification = turn_record.coach_result.report.get(
            "acceptance_criteria_verification", {}
        )
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
    ) -> None:
        """
        Capture turn state to Graphiti for cross-turn learning (TASK-GE-002).

        This method creates a TurnStateEntity from the completed turn and
        stores it in Graphiti for retrieval by subsequent turns.

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

        Notes
        -----
        This enables cross-turn learning by allowing Turn N to query
        what happened in Turn N-1, including:
        - What was attempted and the outcome
        - Coach feedback for improvement
        - Blockers encountered
        - Lessons learned

        The capture is fire-and-forget with graceful degradation - if
        Graphiti is unavailable, execution continues without blocking.
        """
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

            # Capture to Graphiti (async call, fire-and-forget with graceful degradation)
            graphiti = get_graphiti()
            if graphiti and graphiti.enabled:
                # Run async capture in the event loop
                asyncio.create_task(capture_turn_state(graphiti, entity))
                logger.debug(f"Turn state capture initiated for turn {turn_record.turn}")
            else:
                logger.debug("Graphiti disabled, skipping turn state capture")

        except Exception as e:
            # Graceful degradation - log and continue
            logger.warning(f"Error capturing turn state: {e}")

    def _extract_feature_id(self, task_id: str) -> str:
        """
        Extract feature ID from task ID.

        Examples:
            TASK-GE-001 -> FEAT-GE
            TASK-ABC-123 -> FEAT-ABC
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

        # Try to extract prefix from task_id (e.g., TASK-GE-001 -> GE)
        match = re.match(r"TASK-([A-Z]+)-", task_id.upper())
        if match:
            return f"FEAT-{match.group(1)}"

        # Fallback: use self._feature_id if available
        if hasattr(self, "_feature_id") and self._feature_id:
            return self._feature_id

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

        honesty_data = turn_record.coach_result.report.get("honesty_verification", {})
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
                    status = "CLAIMED"
                    icon = "?"
                else:
                    status = "INCOMPLETE"
                    icon = "-"
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

    def _invoke_player_safely(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[str],
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

            # Retrieve job-specific context if enabled (TASK-GR6-006)
            context_prompt = ""
            if self.enable_context and self._context_loader is not None:
                try:
                    context_result = loop.run_until_complete(
                        self._context_loader.get_player_context(
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

            result = loop.run_until_complete(
                self._agent_invoker.invoke_player(
                    task_id=task_id,
                    turn=turn,
                    requirements=requirements,
                    feedback=feedback,
                    max_turns=self.max_turns,  # Enable escape hatch pattern
                    context=context_prompt,  # Pass job-specific context (TASK-GR6-006)
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

        # Retrieve job-specific context for Coach if enabled (TASK-GR6-006)
        context_prompt = ""
        if self.enable_context and self._context_loader is not None:
            try:
                # Create event loop if needed
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                context_result = loop.run_until_complete(
                    self._context_loader.get_coach_context(
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

        # Try lightweight CoachValidator first (Option D architecture)
        try:
            logger.info(f"Using CoachValidator for {task_id} turn {turn}")

            # Use the actual worktree path (supports both single-task and feature mode)
            # In single-task mode: worktree.path = .guardkit/worktrees/TASK-001
            # In feature mode: worktree.path = .guardkit/worktrees/FEAT-ABC
            # CoachValidator will look for: worktree.path/.guardkit/autobuild/{task_id}/task_work_results.json
            validator = CoachValidator(str(worktree.path), task_id=task_id)
            validation_result = validator.validate(
                task_id=task_id,
                turn=turn,
                task={
                    "acceptance_criteria": acceptance_criteria or [],
                    "task_type": task_type,
                },
                skip_arch_review=skip_arch_review,
            )

            duration = time.time() - start_time

            # Save Coach decision to file
            validator.save_decision(validation_result)

            # Convert CoachValidationResult to AgentInvocationResult
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

            # Fallback to SDK invocation if CoachValidator fails
            try:
                # AgentInvoker.invoke_coach is actually synchronous despite the
                # async def signature - it raises NotImplementedError until SDK available
                import asyncio

                # Create event loop if needed
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    self._agent_invoker.invoke_coach(
                        task_id=task_id,
                        turn=turn,
                        requirements=requirements,
                        player_report=player_report,
                    )
                )
                return result

            except NotImplementedError as sdk_error:
                # SDK not yet available - expected during Phase 1a
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

    def _build_player_summary(self, report: Dict[str, Any]) -> str:
        """
        Build summary string from Player report.

        Parameters
        ----------
        report : Dict[str, Any]
            Player report JSON

        Returns
        -------
        str
            Formatted summary for display
        """
        files_modified = len(report.get("files_modified", []))
        files_created = len(report.get("files_created", []))
        tests_written = len(report.get("tests_written", []))
        tests_passed = report.get("tests_passed", False)

        return (
            f"{files_created} files created, {files_modified} modified, "
            f"{tests_written} tests ({'passing' if tests_passed else 'failing'})"
        )

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

    def _build_summary_details(
        self,
        turn_history: List[TurnRecord],
        final_decision: Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "error", "pre_loop_blocked", "design_extraction_failed"],
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

        elif final_decision == "unrecoverable_stall":
            return (
                f"Unrecoverable stall detected after {len(turn_history)} turn(s).\n"
                f"AutoBuild cannot make forward progress.\n"
                f"Worktree preserved for inspection.\n"
                f"Suggested action: Review task_type classification and acceptance criteria."
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
        final_decision: Literal["approved", "max_turns_exceeded", "unrecoverable_stall", "error", "pre_loop_blocked", "design_extraction_failed"],
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

        elif final_decision == "unrecoverable_stall":
            return (
                f"Unrecoverable stall detected after {len(turn_history)} turn(s). "
                f"AutoBuild cannot make forward progress."
            )

        elif final_decision == "pre_loop_blocked":
            return "Pre-loop quality gates blocked execution"

        elif final_decision == "design_extraction_failed":
            return "Phase 0 design extraction failed - MCP tools unavailable or design URL invalid"

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
                )

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
    ...     task_id="TASK-AB-001",
    ...     worktree_path=Path(".guardkit/worktrees/TASK-AB-001"),
    ...     loop_result=orchestration_result,
    ... )
    >>> print(result["status"])
    'in_review'
    >>> print(result["next_steps"])
    ['Review changes: cd .guardkit/worktrees/TASK-AB-001', ...]
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
