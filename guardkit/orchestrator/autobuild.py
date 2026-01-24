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
import logging
import sys
from dataclasses import dataclass
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
    SDKTimeoutError,
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

# Setup logging
logger = logging.getLogger(__name__)


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
    final_decision: Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked"]
    turn_history: List[TurnRecord]
    worktree: Worktree
    error: Optional[str] = None
    pre_loop_result: Optional[Dict[str, Any]] = None  # Results from pre-loop quality gates


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
        enable_checkpoints: bool = True,
        rollback_on_pollution: bool = True,
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
        enable_checkpoints : bool, optional
            Enable worktree checkpointing for rollback (default: True).
            Creates git commits at turn boundaries for context pollution recovery.
        rollback_on_pollution : bool, optional
            Automatically rollback when context pollution detected (default: True).
            Triggers on 2+ consecutive test failures.

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
        self.enable_checkpoints = enable_checkpoints
        self.rollback_on_pollution = rollback_on_pollution
        self._existing_worktree = existing_worktree  # For feature mode (TASK-FBC-001)
        self._turn_history: List[TurnRecord] = []
        self._honesty_history: List[float] = []  # Track honesty scores across turns
        self._checkpoint_manager: Optional[WorktreeCheckpointManager] = None  # Initialized lazily

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
            f"enable_checkpoints={self.enable_checkpoints}, "
            f"rollback_on_pollution={self.rollback_on_pollution}, "
            f"existing_worktree={'provided' if existing_worktree else 'None'}"
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
            )

            logger.info(
                f"Orchestration complete: {task_id}, decision={final_decision}, "
                f"turns={len(turn_history)}"
            )

            return result

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
    ) -> Tuple[List[TurnRecord], Literal["approved", "max_turns_exceeded", "error"]]:
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
        Tuple[List[TurnRecord], Literal["approved", "max_turns_exceeded", "error"]]
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
            # Player failed - attempt state detection for recovery
            self._progress_display.complete_turn(
                "error",
                "Player failed - attempting state recovery",
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
        final_decision: Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked"],
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

        Parameters
        ----------
        worktree : Worktree
            Worktree to finalize
        final_decision : Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked"]
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

            result = loop.run_until_complete(
                self._agent_invoker.invoke_player(
                    task_id=task_id,
                    turn=turn,
                    requirements=requirements,
                    feedback=feedback,
                    max_turns=self.max_turns,  # Enable escape hatch pattern
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
        except Exception as e:
            logger.error(f"Player invocation failed: {e}", exc_info=True)
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=0.0,
                error=f"Unexpected error: {str(e)}",
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
        """
        import time

        start_time = time.time()

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
        final_decision: Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked"],
    ) -> str:
        """
        Build detailed summary text for final report.

        Parameters
        ----------
        turn_history : List[TurnRecord]
            Complete turn history
        final_decision : Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked"]
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
        final_decision: Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked"],
        turn_history: List[TurnRecord],
    ) -> str:
        """
        Build error message for OrchestrationResult.

        Parameters
        ----------
        final_decision : Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked"]
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
