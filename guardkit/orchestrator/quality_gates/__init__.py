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

    Coach evidence:
    - Runs the project's own tests and declared checks (CoachValidator)

Example:
    >>> from guardkit.orchestrator.quality_gates import PreLoopQualityGates, CoachValidator
    >>>
    >>> # Pre-loop: Execute design phases
    >>> gates = PreLoopQualityGates("/path/to/worktree")
    >>> result = gates.execute("TASK-001", {"no_questions": True})
    >>>
    >>> # Coach: run the project's own checks for a turn
    >>> validator = CoachValidator("/path/to/worktree")
    >>> bundle = validator.gather_evidence("TASK-001", turn=1, task={"acceptance_criteria": [...]})
"""

from guardkit.orchestrator.quality_gates.pre_loop import PreLoopQualityGates
from guardkit.orchestrator.quality_gates.task_work_interface import TaskWorkInterface
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
    GatheringStatus,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.orchestrator.quality_gates.exceptions import (
    QualityGateError,
    QualityGateBlocked,
    DesignPhaseError,
    CheckpointRejectedError,
)
# R1 DE-WIRE (Rich 08-14): the bdd_runner re-exports (TASK-BDD-E8954) are
# removed — bdd_runner.py stays on disk unreferenced until R2 deletes it.

__all__ = [
    # Pre-loop quality gates
    "PreLoopQualityGates",
    "TaskWorkInterface",
    # Coach validator
    "CoachValidator",
    "IndependentTestResult",
    # Coach evidence bundle (TASK-HMIG-008R Revision 3)
    "CoachEvidenceBundle",
    "GatheringStatus",
    # Exceptions
    "QualityGateError",
    "QualityGateBlocked",
    "DesignPhaseError",
    "CheckpointRejectedError",
]
