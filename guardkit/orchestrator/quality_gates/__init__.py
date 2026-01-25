"""
Quality gates for feature-build via task-work delegation.

This module provides quality gates for the AutoBuild system by delegating to
task-work phases, achieving 100% code reuse of existing quality gates.

Architecture:
    Option D (per TASK-REV-0414): Delegates to task-work phases rather than
    reimplementing quality gates:

    Pre-Loop (via task-work --design-only):
    - Phase 1.6: Clarifying Questions
    - Phase 2: Implementation Planning
    - Phase 2.5A: Pattern Suggestions
    - Phase 2.5B: Architectural Review
    - Phase 2.7: Complexity Evaluation
    - Phase 2.8: Human Checkpoint

    Coach Validation (via task-work results):
    - Reads Phase 4.5 test results
    - Reads Phase 5 code review scores
    - Reads Phase 5.5 plan audit results
    - Runs independent test verification

Example:
    >>> from guardkit.orchestrator.quality_gates import PreLoopQualityGates, CoachValidator
    >>>
    >>> # Pre-loop: Execute design phases
    >>> gates = PreLoopQualityGates("/path/to/worktree")
    >>> result = gates.execute("TASK-001", {"no_questions": True})
    >>>
    >>> # Coach: Validate task-work results
    >>> validator = CoachValidator("/path/to/worktree")
    >>> coach_result = validator.validate("TASK-001", turn=1, task={"acceptance_criteria": [...]})
    >>> print(f"Decision: {coach_result.decision}")
"""

from guardkit.orchestrator.quality_gates.pre_loop import PreLoopQualityGates
from guardkit.orchestrator.quality_gates.task_work_interface import TaskWorkInterface
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    CoachValidationResult,
    QualityGateStatus,
    IndependentTestResult,
    RequirementsValidation,
)
from guardkit.orchestrator.quality_gates.security_checker import (
    SecurityChecker,
    SecurityFinding,
)
from guardkit.orchestrator.quality_gates.security_detection import (
    SECURITY_TAGS,
    HIGH_RISK_CATEGORIES,
    SECURITY_KEYWORDS,
    should_run_full_review,
)
from guardkit.orchestrator.quality_gates.exceptions import (
    QualityGateError,
    QualityGateBlocked,
    DesignPhaseError,
    CheckpointRejectedError,
)

__all__ = [
    # Pre-loop quality gates
    "PreLoopQualityGates",
    "TaskWorkInterface",
    # Coach validator
    "CoachValidator",
    "CoachValidationResult",
    "QualityGateStatus",
    "IndependentTestResult",
    "RequirementsValidation",
    # Security checker
    "SecurityChecker",
    "SecurityFinding",
    # Security detection
    "SECURITY_TAGS",
    "HIGH_RISK_CATEGORIES",
    "SECURITY_KEYWORDS",
    "should_run_full_review",
    # Exceptions
    "QualityGateError",
    "QualityGateBlocked",
    "DesignPhaseError",
    "CheckpointRejectedError",
]
