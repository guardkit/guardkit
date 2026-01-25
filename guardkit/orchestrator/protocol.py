"""
Orchestrator protocol for dependency injection.

This module defines the OrchestratorProtocol interface, implementing the
Dependency Inversion Principle from the architectural review recommendation #4.

Example:
    >>> from typing import Protocol
    >>> from guardkit.orchestrator.protocol import OrchestratorProtocol
    >>>
    >>> def execute_task(orchestrator: OrchestratorProtocol, task_id: str):
    ...     result = orchestrator.orchestrate(task_id, "requirements", ["criteria"])
"""

from pathlib import Path
from typing import List, Protocol

from guardkit.orchestrator.autobuild import OrchestrationResult


# ============================================================================
# Orchestrator Protocol
# ============================================================================


class OrchestratorProtocol(Protocol):
    """
    Protocol for orchestrator implementations.

    This protocol defines the interface that all orchestrator implementations
    must satisfy, enabling dependency injection and testability.

    Benefits
    --------
    - Dependency Inversion Principle (depend on abstraction, not concrete class)
    - Enables mocking in tests without inheritance
    - Clear interface contract
    - Type safety with mypy/pyright

    Methods
    -------
    orchestrate(task_id, requirements, acceptance_criteria, base_branch) -> OrchestrationResult
        Execute complete orchestration workflow

    Examples
    --------
    >>> def run_autobuild(
    ...     orchestrator: OrchestratorProtocol,
    ...     task_id: str
    ... ) -> OrchestrationResult:
    ...     return orchestrator.orchestrate(
    ...         task_id=task_id,
    ...         requirements="Build feature X",
    ...         acceptance_criteria=["Criterion 1"],
    ...     )
    """

    def orchestrate(
        self,
        task_id: str,
        requirements: str,
        acceptance_criteria: List[str],
        base_branch: str = "main",
    ) -> OrchestrationResult:
        """
        Execute complete orchestration workflow.

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

        Returns
        -------
        OrchestrationResult
            Complete orchestration result with turn history and worktree
        """
        ...


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "OrchestratorProtocol",
]
