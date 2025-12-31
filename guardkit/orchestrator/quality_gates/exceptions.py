"""
Exceptions for quality gates module.

This module defines exceptions for quality gate failures during
pre-loop execution.
"""


class QualityGateError(Exception):
    """Base exception for quality gate errors."""

    pass


class QualityGateBlocked(QualityGateError):
    """
    Raised when a quality gate blocks task execution.

    This exception indicates that the task cannot proceed to the
    adversarial loop because a quality gate was not satisfied.

    Attributes
    ----------
    reason : str
        Human-readable explanation of why the gate blocked execution
    gate_name : str
        Name of the gate that blocked (e.g., "architectural_review")
    details : dict
        Additional context about the failure
    """

    def __init__(
        self,
        reason: str,
        gate_name: str = "unknown",
        details: dict = None,
    ):
        self.reason = reason
        self.gate_name = gate_name
        self.details = details or {}
        super().__init__(f"Quality gate '{gate_name}' blocked: {reason}")


class DesignPhaseError(QualityGateError):
    """
    Raised when design phase execution fails.

    This exception indicates that task-work --design-only failed to
    complete successfully.

    Attributes
    ----------
    phase : str
        The phase that failed (e.g., "2.5B", "2.7")
    error : str
        Error message from the failed phase
    """

    def __init__(self, phase: str, error: str):
        self.phase = phase
        self.error = error
        super().__init__(f"Design phase {phase} failed: {error}")


class CheckpointRejectedError(QualityGateError):
    """
    Raised when human checkpoint rejects the design.

    This exception indicates that a human reviewer rejected the
    implementation plan at Phase 2.8.

    Attributes
    ----------
    reason : str
        Reason provided by the reviewer for rejection
    """

    def __init__(self, reason: str = "Design rejected at checkpoint"):
        self.reason = reason
        super().__init__(reason)
