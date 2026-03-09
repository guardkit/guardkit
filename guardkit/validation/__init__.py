"""
Validation modules for GuardKit.

Provides pre-flight validation for acceptance criteria, backend detection,
and feasibility checking.
"""

from guardkit.validation.ac_validator import (
    ACValidationResult,
    ACWarning,
    BackendKind,
    InfeasiblePattern,
    VLLM_INFEASIBLE_PATTERNS,
    format_validation_report,
    validate_acceptance_criteria,
)

__all__ = [
    "validate_acceptance_criteria",
    "format_validation_report",
    "ACValidationResult",
    "ACWarning",
    "BackendKind",
    "InfeasiblePattern",
    "VLLM_INFEASIBLE_PATTERNS",
]
