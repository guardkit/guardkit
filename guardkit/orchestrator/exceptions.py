"""Custom exceptions for AgentInvoker."""


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
