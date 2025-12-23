"""Custom exceptions for orchestrator components."""


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
