"""Custom exceptions for orchestrator components."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


# ============================================================================
# Data Classes for Agent Invocation Results
# ============================================================================


@dataclass
class TaskWorkResult:
    """Result of task-work command execution.

    Attributes:
        success: True if task-work completed successfully
        output: Parsed output from task-work (test results, coverage, etc.)
        error: Error message if task-work failed
        exit_code: Process exit code
    """

    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    exit_code: int = 0


# ============================================================================
# AgentInvoker Exceptions
# ============================================================================


class AgentInvokerError(Exception):
    """Base exception for AgentInvoker errors."""

    pass


class AgentInvocationError(AgentInvokerError):
    """Raised when SDK invocation fails."""

    pass


class PlayerReportNotFoundError(AgentInvokerError):
    """Raised when Player doesn't create report."""

    pass


class PlayerReportInvalidError(AgentInvokerError):
    """Raised when Player report JSON is malformed."""

    pass


class CoachDecisionNotFoundError(AgentInvokerError):
    """Raised when Coach doesn't create decision."""

    pass


class CoachDecisionInvalidError(AgentInvokerError):
    """Raised when Coach decision JSON is malformed."""

    pass


class SDKTimeoutError(AgentInvokerError):
    """Raised when SDK invocation times out."""

    pass


# ============================================================================
# Orchestration Exceptions
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
