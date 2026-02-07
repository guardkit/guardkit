"""
Failed approach episode entity definitions.

This module provides the data structures for capturing failed approaches
in the knowledge graph. Failed approaches represent attempted solutions
that didn't work, along with prevention guidance to avoid repeating
the same mistakes.

Public API:
    Severity: Enum for failure severity levels
    FailedApproachEpisode: Dataclass for capturing failed approaches

Example Usage:
    from guardkit.knowledge.entities.failed_approach import (
        FailedApproachEpisode,
        Severity,
    )

    failure = FailedApproachEpisode(
        id="FAIL-SUBPROCESS",
        approach="Using subprocess.run() to invoke guardkit task-work",
        symptom="subprocess.CalledProcessError: Command not found",
        root_cause="CLI command doesn't exist - task-work is a slash command",
        fix_applied="Use SDK query() to invoke '/task-work TASK-XXX'",
        prevention="Check ADR-FB-001 before implementing task-work invocation",
        context="feature-build",
        severity=Severity.CRITICAL
    )
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class Severity(Enum):
    """Enum for failure severity levels.

    Severity indicates the impact of the failure on development time
    and the importance of preventing recurrence.

    Attributes:
        LOW: Minor inconvenience, <15 minutes to resolve
        MEDIUM: Noticeable delay, 15-60 minutes to resolve
        HIGH: Significant impact, 1-4 hours to resolve
        CRITICAL: Major blocker, >4 hours or repeated occurrences
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _default_datetime_now() -> datetime:
    """Factory function for datetime.now() default value.

    Required because dataclass field defaults must be immutable or
    use default_factory.

    Returns:
        Current datetime
    """
    return datetime.now()


@dataclass
class FailedApproachEpisode:
    """Dataclass representing a failed approach with prevention guidance.

    This captures comprehensive information about an approach that was
    tried and failed, including how to prevent making the same mistake
    in the future. Used for episode capture in Graphiti.

    Attributes:
        id: Unique failure ID in format FAIL-{hash} or FAIL-{descriptive_name}
        approach: What was tried (the failed approach)
        symptom: What went wrong (error message or behavior observed)
        root_cause: Why it failed (underlying reason)
        fix_applied: How it was resolved (what worked instead)
        prevention: How to avoid in future (key learning for prevention)
        context: Where this happened (feature-build, task-work, etc.)
        task_id: Task ID where this occurred (optional)
        feature_id: Feature ID where this occurred (optional)
        file_path: File path involved if relevant (optional)
        related_adrs: List of ADR IDs to check (optional)
        similar_failures: List of related failure IDs (optional)
        occurrences: How many times this happened (default: 1)
        first_occurred: When this first happened (default: now)
        last_occurred: When this last happened (default: now)
        severity: How severe is this failure (default: MEDIUM)
        time_to_fix_minutes: How long to resolve in minutes (optional)

    Example:
        failure = FailedApproachEpisode(
            id="FAIL-A1B2C3D4",
            approach="Using subprocess for task-work invocation",
            symptom="Command not found error",
            root_cause="CLI command doesn't exist",
            fix_applied="Use SDK query() method",
            prevention="Check ADR-FB-001 before implementing",
            context="feature-build"
        )
    """
    # Required fields - core identity and description
    id: str
    approach: str
    symptom: str
    root_cause: str
    fix_applied: str
    prevention: str
    context: str

    # Optional context fields
    task_id: Optional[str] = None
    feature_id: Optional[str] = None
    file_path: Optional[str] = None

    # Related knowledge fields (default empty lists)
    related_adrs: List[str] = field(default_factory=list)
    similar_failures: List[str] = field(default_factory=list)

    # Tracking fields
    occurrences: int = 1
    first_occurred: datetime = field(default_factory=_default_datetime_now)
    last_occurred: datetime = field(default_factory=_default_datetime_now)

    # Severity and metrics
    severity: Severity = Severity.MEDIUM
    time_to_fix_minutes: Optional[int] = None

    def to_episode_body(self) -> Dict[str, Any]:
        """Convert failed approach to episode body dictionary.

        Creates a structured dictionary representation suitable for
        storage in Graphiti as an episode body. Returns only domain data;
        metadata fields like entity_type are injected by GraphitiClient.

        Returns:
            Dictionary with all failure fields suitable for JSON serialization
        """
        return {
            "id": self.id,
            "approach": self.approach,
            "symptom": self.symptom,
            "root_cause": self.root_cause,
            "fix_applied": self.fix_applied,
            "prevention": self.prevention,
            "context": self.context,
            "task_id": self.task_id,
            "feature_id": self.feature_id,
            "file_path": self.file_path,
            "related_adrs": self.related_adrs,
            "similar_failures": self.similar_failures,
            "occurrences": self.occurrences,
            "first_occurred": self.first_occurred.isoformat(),
            "last_occurred": self.last_occurred.isoformat(),
            "severity": self.severity.value,
            "time_to_fix_minutes": self.time_to_fix_minutes
        }
