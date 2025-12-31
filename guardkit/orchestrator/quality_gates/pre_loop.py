"""
Pre-loop quality gates for AutoBuild via task-work delegation.

This module provides the PreLoopQualityGates class that executes quality gates
before the Player-Coach adversarial loop by delegating to task-work --design-only.

Architecture:
    Implements Option D (per TASK-REV-0414): 100% code reuse by delegating to
    existing task-work quality gates rather than reimplementing them.

    Delegation Flow:
    1. PreLoopQualityGates.execute() called by AutoBuild orchestrator
    2. Delegates to TaskWorkInterface.execute_design_phase()
    3. Which invokes task-work --design-only (Phases 1.6, 2, 2.5A, 2.5B, 2.7, 2.8)
    4. Results extracted for adversarial loop configuration

Example:
    >>> from guardkit.orchestrator.quality_gates import PreLoopQualityGates
    >>>
    >>> gates = PreLoopQualityGates("/path/to/worktree")
    >>> result = gates.execute("TASK-001", {"no_questions": True})
    >>>
    >>> # Pass plan to Player agent
    >>> player_prompt = f"Implement according to: {result['plan']}"
    >>>
    >>> # Use dynamic max_turns based on complexity
    >>> for turn in range(result['max_turns']):
    ...     pass  # Player-Coach loop
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from guardkit.orchestrator.quality_gates.task_work_interface import (
    TaskWorkInterface,
    DesignPhaseResult,
)
from guardkit.orchestrator.quality_gates.exceptions import (
    QualityGateBlocked,
    CheckpointRejectedError,
)

logger = logging.getLogger(__name__)


@dataclass
class PreLoopResult:
    """
    Result from pre-loop quality gates execution.

    This dataclass contains all outputs needed by the adversarial loop,
    including the implementation plan, complexity-based max_turns,
    and checkpoint decision.

    Attributes
    ----------
    plan : Dict[str, Any]
        Implementation plan from task-work Phase 2
    plan_path : Optional[str]
        Path to the saved plan file
    complexity : int
        Complexity score (1-10) from Phase 2.7
    max_turns : int
        Maximum turns for adversarial loop (based on complexity)
    checkpoint_passed : bool
        Whether human checkpoint (Phase 2.8) approved
    architectural_score : Optional[int]
        SOLID/DRY/YAGNI overall score from Phase 2.5B
    clarifications : Dict[str, Any]
        User clarification decisions from Phase 1.6
    """

    plan: Dict[str, Any]
    plan_path: Optional[str]
    complexity: int
    max_turns: int
    checkpoint_passed: bool
    architectural_score: Optional[int] = None
    clarifications: Dict[str, Any] = field(default_factory=dict)


class PreLoopQualityGates:
    """
    Execute pre-loop quality gates by delegating to task-work --design-only.

    This class provides a thin orchestration layer that delegates to task-work
    for all design phases, achieving 100% code reuse of existing quality gates.

    Delegation Flow:
    1. Build task-work command arguments with passthrough flags
    2. Invoke TaskWorkInterface.execute_design_phase()
    3. Extract outputs needed for adversarial loop
    4. Determine max_turns based on complexity score

    Quality Gates Executed (via task-work --design-only):
    - Phase 1.6: Clarifying Questions (complexity-gated)
    - Phase 2: Implementation Planning
    - Phase 2.5A: Pattern Suggestions (if MCP available)
    - Phase 2.5B: Architectural Review (SOLID/DRY/YAGNI)
    - Phase 2.7: Complexity Evaluation
    - Phase 2.8: Human Checkpoint (complexity-gated)

    Attributes
    ----------
    worktree_path : Path
        Path to the git worktree
    _interface : TaskWorkInterface
        Interface for delegating to task-work

    Example
    -------
    >>> gates = PreLoopQualityGates("/path/to/worktree")
    >>> result = gates.execute("TASK-001", {"no_questions": True})
    >>>
    >>> print(f"Complexity: {result.complexity}/10")
    >>> print(f"Max turns: {result.max_turns}")
    >>> print(f"Checkpoint: {'Passed' if result.checkpoint_passed else 'Failed'}")
    """

    # Complexity-to-max_turns mapping
    # Lower complexity = fewer iterations needed
    COMPLEXITY_TURNS_MAP = {
        (1, 3): 3,   # Simple: 3 turns max
        (4, 6): 5,   # Medium: 5 turns max
        (7, 10): 7,  # Complex: 7 turns max
    }

    def __init__(
        self,
        worktree_path: str,
        interface: Optional[TaskWorkInterface] = None,
    ):
        """
        Initialize PreLoopQualityGates.

        Parameters
        ----------
        worktree_path : str
            Path to the git worktree where quality gates should execute
        interface : Optional[TaskWorkInterface]
            Optional interface for dependency injection (testing)
        """
        self.worktree_path = Path(worktree_path)
        self._interface = interface or TaskWorkInterface(self.worktree_path)

        logger.debug(f"PreLoopQualityGates initialized for worktree: {worktree_path}")

    def execute(
        self,
        task_id: str,
        options: Dict[str, Any],
    ) -> PreLoopResult:
        """
        Run pre-loop quality gates via task-work delegation.

        Delegates to: /task-work TASK-XXX --design-only
        Which executes: Phases 1.6, 2, 2.5A, 2.5B, 2.7, 2.8

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        options : Dict[str, Any]
            Options to pass through to task-work:
            - no_questions: Skip Phase 1.6 clarification
            - with_questions: Force Phase 1.6 clarification
            - answers: Inline answers for automation
            - docs: Documentation level
            - defaults: Use default answers

        Returns
        -------
        PreLoopResult
            Result containing plan, complexity, max_turns, and checkpoint status

        Raises
        ------
        QualityGateBlocked
            If architectural review score is below threshold
        CheckpointRejectedError
            If human checkpoint rejects the design

        Example
        -------
        >>> result = gates.execute("TASK-001", {"no_questions": True})
        >>> print(f"Plan ready: {bool(result.plan)}")
        >>> print(f"Max turns: {result.max_turns}")
        """
        logger.info(f"Executing pre-loop quality gates for {task_id}")

        # Execute design phases via task-work delegation
        design_result = self._interface.execute_design_phase(task_id, options)

        # Check if checkpoint was rejected
        if design_result.checkpoint_result == "rejected":
            raise CheckpointRejectedError(
                reason="Human checkpoint rejected the implementation plan"
            )

        # Extract and return results needed for adversarial loop
        return self._extract_pre_loop_results(task_id, design_result)

    def _extract_pre_loop_results(
        self,
        task_id: str,
        result: DesignPhaseResult,
    ) -> PreLoopResult:
        """
        Extract outputs needed for Player-Coach loop.

        Parameters
        ----------
        task_id : str
            Task identifier
        result : DesignPhaseResult
            Result from task-work design phase

        Returns
        -------
        PreLoopResult
            Extracted and formatted results
        """
        complexity_score = result.complexity.get("score", 5)
        max_turns = self._determine_max_turns(complexity_score)

        arch_score = result.architectural_review.get("score")

        logger.info(
            f"Pre-loop results extracted: complexity={complexity_score}, "
            f"max_turns={max_turns}, arch_score={arch_score}"
        )

        return PreLoopResult(
            plan=result.implementation_plan,
            plan_path=result.plan_path,
            complexity=complexity_score,
            max_turns=max_turns,
            checkpoint_passed=result.checkpoint_result in ("approved", "skipped"),
            architectural_score=arch_score,
            clarifications=result.clarifications,
        )

    def _determine_max_turns(self, complexity: int) -> int:
        """
        Determine max_turns based on complexity score from task-work.

        Lower complexity tasks need fewer iterations to complete,
        while complex tasks may need more rounds of Player-Coach feedback.

        Parameters
        ----------
        complexity : int
            Complexity score (1-10) from Phase 2.7

        Returns
        -------
        int
            Maximum turns for adversarial loop

        Mapping
        -------
        - Complexity 1-3 (Simple): 3 turns max - quick iterations
        - Complexity 4-6 (Medium): 5 turns max - standard iterations
        - Complexity 7-10 (Complex): 7 turns max - more iterations allowed
        """
        for (low, high), turns in self.COMPLEXITY_TURNS_MAP.items():
            if low <= complexity <= high:
                logger.debug(
                    f"Complexity {complexity} mapped to {turns} turns "
                    f"(range {low}-{high})"
                )
                return turns

        # Default to 5 if complexity is out of expected range
        logger.warning(f"Unexpected complexity {complexity}, defaulting to 5 turns")
        return 5

    def validate_prerequisites(self, task_id: str) -> bool:
        """
        Validate that all prerequisites are met for pre-loop execution.

        This method checks that the task file exists and has the necessary
        structure for quality gate execution.

        Parameters
        ----------
        task_id : str
            Task identifier

        Returns
        -------
        bool
            True if prerequisites are met, False otherwise
        """
        # Check if worktree exists
        if not self.worktree_path.exists():
            logger.error(f"Worktree does not exist: {self.worktree_path}")
            return False

        # Check if tasks directory exists
        tasks_dir = self.worktree_path / "tasks"
        if not tasks_dir.exists():
            logger.warning(f"Tasks directory not found in worktree: {tasks_dir}")
            # This might be okay if task is in a different location
            pass

        return True

    @property
    def supported_options(self) -> Dict[str, str]:
        """
        Return supported options that can be passed through to task-work.

        Returns
        -------
        Dict[str, str]
            Dictionary mapping option names to descriptions
        """
        return {
            "no_questions": "Skip Phase 1.6 clarification questions",
            "with_questions": "Force Phase 1.6 clarification even for simple tasks",
            "answers": "Inline answers for automation (format: '1:Y 2:N 3:JWT')",
            "defaults": "Use default answers without prompting",
            "docs": "Documentation level (minimal/standard/comprehensive)",
        }
