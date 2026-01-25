"""Schema definitions for Promise-Based Completion Verification in AutoBuild.

This module provides dataclasses for the promise-based completion verification system
that enables explicit, verifiable contracts between Player and Coach agents.

The Player makes explicit promises about completing acceptance criteria, and the Coach
systematically verifies each promise. This structured approach improves traceability
and enables meaningful progress tracking.

Architecture:
    Player → CompletionPromise → Coach → CriterionVerification → Decision

Example:
    >>> from guardkit.orchestrator.schemas import (
    ...     CompletionPromise,
    ...     CriterionVerification,
    ...     CriterionStatus,
    ...     VerificationResult,
    ... )
    >>>
    >>> # Player creates promises for each acceptance criterion
    >>> promise = CompletionPromise(
    ...     criterion_id="AC-001",
    ...     criterion_text="OAuth2 authentication flow works correctly",
    ...     status=CriterionStatus.COMPLETE,
    ...     evidence="Implemented OAuth2 flow in src/auth/oauth.py with PKCE support",
    ...     test_file="tests/test_oauth.py",
    ...     implementation_files=["src/auth/oauth.py", "src/auth/tokens.py"],
    ... )
    >>>
    >>> # Coach verifies each promise
    >>> verification = CriterionVerification(
    ...     criterion_id="AC-001",
    ...     result=VerificationResult.VERIFIED,
    ...     notes="Tests pass, implementation matches requirements",
    ... )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CriterionStatus(str, Enum):
    """Status of a completion promise for a criterion.

    Simplified from 3 states to 2 per YAGNI principle.
    Player either completed the criterion or not.

    Attributes:
        COMPLETE: Player claims to have satisfied this criterion
        INCOMPLETE: Player has not yet satisfied this criterion
    """

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class VerificationResult(str, Enum):
    """Coach verification result for a criterion.

    Simplified from 3 states to 2 per YAGNI principle.
    Coach either verifies the promise or rejects it.

    Attributes:
        VERIFIED: Coach confirms the criterion is satisfied
        REJECTED: Coach determined the criterion is not satisfied
    """

    VERIFIED = "verified"
    REJECTED = "rejected"


@dataclass
class CompletionPromise:
    """Player's promise about completing one acceptance criterion.

    This dataclass represents an explicit contract from the Player about
    satisfying a specific acceptance criterion. The Player provides evidence
    of completion, which the Coach will verify.

    Attributes:
        criterion_id: Unique identifier for the criterion (e.g., "AC-001")
        criterion_text: Full text of the acceptance criterion
        status: Whether the Player claims this criterion is complete
        evidence: Description of what the Player did to satisfy this criterion
        test_file: Optional path to the test file that validates this criterion
        implementation_files: List of files modified/created for this criterion

    Examples:
        >>> promise = CompletionPromise(
        ...     criterion_id="AC-001",
        ...     criterion_text="Token refresh handles expiry edge case",
        ...     status=CriterionStatus.COMPLETE,
        ...     evidence="Added token refresh with 5-minute buffer before expiry",
        ...     test_file="tests/test_token_refresh.py",
        ...     implementation_files=["src/auth/tokens.py"],
        ... )
        >>> promise.to_dict()
        {'criterion_id': 'AC-001', 'criterion_text': '...', ...}
    """

    criterion_id: str  # e.g., "AC-001"
    criterion_text: str  # Full acceptance criterion text
    status: CriterionStatus
    evidence: str  # What Player did to satisfy this
    test_file: Optional[str] = None  # Test file path if applicable
    implementation_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "criterion_id": self.criterion_id,
            "criterion_text": self.criterion_text,
            "status": self.status.value,
            "evidence": self.evidence,
            "test_file": self.test_file,
            "implementation_files": self.implementation_files,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompletionPromise":
        """Create from dictionary.

        Args:
            data: Dictionary with promise data (typically from JSON)

        Returns:
            CompletionPromise instance

        Examples:
            >>> data = {
            ...     "criterion_id": "AC-001",
            ...     "criterion_text": "OAuth2 flow works",
            ...     "status": "complete",
            ...     "evidence": "Implemented in oauth.py",
            ... }
            >>> promise = CompletionPromise.from_dict(data)
            >>> promise.criterion_id
            'AC-001'
        """
        return cls(
            criterion_id=data.get("criterion_id", ""),
            criterion_text=data.get("criterion_text", ""),
            status=CriterionStatus(data.get("status", "incomplete")),
            evidence=data.get("evidence", ""),
            test_file=data.get("test_file"),
            implementation_files=data.get("implementation_files", []),
        )


@dataclass
class CriterionVerification:
    """Coach's verification of one completion promise.

    Simplified per architectural review - removed redundant fields.
    The Coach verifies each promise and provides notes explaining the decision.

    Attributes:
        criterion_id: Links to the corresponding CompletionPromise
        result: Whether the Coach verified or rejected the promise
        notes: Coach's reasoning and observations

    Examples:
        >>> verification = CriterionVerification(
        ...     criterion_id="AC-001",
        ...     result=VerificationResult.VERIFIED,
        ...     notes="Tests pass, implementation follows requirements exactly",
        ... )
        >>> verification.to_dict()
        {'criterion_id': 'AC-001', 'result': 'verified', 'notes': '...'}
    """

    criterion_id: str  # Links to CompletionPromise
    result: VerificationResult
    notes: str  # Coach's reasoning

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "criterion_id": self.criterion_id,
            "result": self.result.value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CriterionVerification":
        """Create from dictionary.

        Args:
            data: Dictionary with verification data (typically from JSON)

        Returns:
            CriterionVerification instance

        Examples:
            >>> data = {
            ...     "criterion_id": "AC-001",
            ...     "result": "verified",
            ...     "notes": "Tests pass",
            ... }
            >>> verification = CriterionVerification.from_dict(data)
            >>> verification.result
            <VerificationResult.VERIFIED: 'verified'>
        """
        return cls(
            criterion_id=data.get("criterion_id", ""),
            result=VerificationResult(data.get("result", "rejected")),
            notes=data.get("notes", ""),
        )


# ============================================================================
# Utility Functions
# ============================================================================


def calculate_completion_percentage(
    promises: List[CompletionPromise],
    verifications: List[CriterionVerification],
) -> float:
    """Calculate the percentage of criteria that are verified complete.

    This utility function computes progress based on how many promises
    have been verified by the Coach.

    Args:
        promises: List of Player's completion promises
        verifications: List of Coach's verifications

    Returns:
        Percentage (0.0 to 100.0) of criteria verified complete

    Examples:
        >>> promises = [
        ...     CompletionPromise("AC-001", "Criterion 1", CriterionStatus.COMPLETE, "Done"),
        ...     CompletionPromise("AC-002", "Criterion 2", CriterionStatus.COMPLETE, "Done"),
        ... ]
        >>> verifications = [
        ...     CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
        ... ]
        >>> calculate_completion_percentage(promises, verifications)
        50.0
    """
    if not promises:
        return 0.0

    # Build map of verifications by criterion_id
    verification_map = {v.criterion_id: v for v in verifications}

    # Count verified criteria
    verified_count = sum(
        1
        for p in promises
        if p.criterion_id in verification_map
        and verification_map[p.criterion_id].result == VerificationResult.VERIFIED
    )

    return (verified_count / len(promises)) * 100.0


def format_promise_summary(promises: List[CompletionPromise]) -> str:
    """Format a summary of completion promises for display.

    Args:
        promises: List of Player's completion promises

    Returns:
        Formatted string summary

    Examples:
        >>> promises = [
        ...     CompletionPromise("AC-001", "OAuth flow", CriterionStatus.COMPLETE, "Done"),
        ...     CompletionPromise("AC-002", "Token refresh", CriterionStatus.INCOMPLETE, "WIP"),
        ... ]
        >>> print(format_promise_summary(promises))
        Completion Promises:
          [COMPLETE] AC-001: OAuth flow
          [INCOMPLETE] AC-002: Token refresh
    """
    if not promises:
        return "No completion promises"

    lines = ["Completion Promises:"]
    for p in promises:
        status_marker = "COMPLETE" if p.status == CriterionStatus.COMPLETE else "INCOMPLETE"
        # Truncate criterion text if too long
        criterion_short = p.criterion_text[:50] + "..." if len(p.criterion_text) > 50 else p.criterion_text
        lines.append(f"  [{status_marker}] {p.criterion_id}: {criterion_short}")

    return "\n".join(lines)


def format_verification_summary(verifications: List[CriterionVerification]) -> str:
    """Format a summary of criterion verifications for display.

    Args:
        verifications: List of Coach's verifications

    Returns:
        Formatted string summary

    Examples:
        >>> verifications = [
        ...     CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
        ...     CriterionVerification("AC-002", VerificationResult.REJECTED, "Missing edge case"),
        ... ]
        >>> print(format_verification_summary(verifications))
        Verification Results:
          [VERIFIED] AC-001: Good
          [REJECTED] AC-002: Missing edge case
    """
    if not verifications:
        return "No verifications"

    lines = ["Verification Results:"]
    for v in verifications:
        result_marker = "VERIFIED" if v.result == VerificationResult.VERIFIED else "REJECTED"
        # Truncate notes if too long
        notes_short = v.notes[:50] + "..." if len(v.notes) > 50 else v.notes
        lines.append(f"  [{result_marker}] {v.criterion_id}: {notes_short}")

    return "\n".join(lines)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "CriterionStatus",
    "VerificationResult",
    "CompletionPromise",
    "CriterionVerification",
    "calculate_completion_percentage",
    "format_promise_summary",
    "format_verification_summary",
]
