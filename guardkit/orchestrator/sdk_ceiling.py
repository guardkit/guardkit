"""
SDK Turn Ceiling Monitoring utilities (TASK-VPR-003).

Pure functions for ceiling detection logic and summary generation.
Tracks when Player invocations hit the SDK turn limit and provides
aggregated metrics for feature completion summaries.

Key Concepts:
    - SDK turn ceiling: The maximum turns allowed per SDK invocation
      (50 for local backends, 100 for remote via _effective_sdk_max_turns)
    - Ceiling hit: When turns_used >= max_turns for an invocation
    - Warning threshold: 60% ceiling hit rate triggers a warning

Usage:
    >>> from guardkit.orchestrator.sdk_ceiling import (
    ...     SdkTurnRecord, compute_ceiling_summary, detect_ceiling_hit,
    ... )
    >>> record = SdkTurnRecord(task_id="TASK-001", turns_used=50, max_turns=50)
    >>> record.ceiling_hit
    True
    >>> summary = compute_ceiling_summary([record])
    >>> summary.ceiling_hit_rate
    100.0
"""

from dataclasses import dataclass
from typing import List, Optional


# Warning threshold: emit warning when ceiling hit rate exceeds this percentage
CEILING_WARNING_THRESHOLD = 60.0


@dataclass(frozen=True)
class SdkTurnRecord:
    """Record of SDK turns for a single Player invocation.

    Attributes
    ----------
    task_id : str
        Task identifier for this invocation
    turns_used : int
        Actual SDK turns consumed (from ResultMessage.num_turns)
    max_turns : int
        SDK turn ceiling for this invocation (from _effective_sdk_max_turns)
    """

    task_id: str
    turns_used: int
    max_turns: int

    @property
    def ceiling_hit(self) -> bool:
        """Whether this invocation hit the SDK turn ceiling."""
        return self.turns_used >= self.max_turns


@dataclass(frozen=True)
class CeilingSummary:
    """Summary of SDK turn ceiling metrics across invocations.

    Attributes
    ----------
    total_invocations : int
        Total number of Player invocations with SDK turn data
    ceiling_hits : int
        Number of invocations that hit the ceiling
    records : tuple[SdkTurnRecord, ...]
        Individual invocation records (frozen tuple for immutability)
    """

    total_invocations: int
    ceiling_hits: int
    records: tuple

    @property
    def ceiling_hit_rate(self) -> float:
        """Ceiling hit rate as percentage (0-100).

        Returns 0.0 when there are no invocations to avoid division by zero.
        """
        if self.total_invocations == 0:
            return 0.0
        return (self.ceiling_hits / self.total_invocations) * 100

    @property
    def exceeds_warning_threshold(self) -> bool:
        """Whether ceiling hit rate exceeds 60% warning threshold.

        Uses strict greater-than (>) so exactly 60% does NOT trigger.
        """
        return self.ceiling_hit_rate > CEILING_WARNING_THRESHOLD


def compute_ceiling_summary(records: List[SdkTurnRecord]) -> CeilingSummary:
    """Compute ceiling summary from a list of SDK turn records.

    Aggregates individual invocation records into a summary with
    total invocations, ceiling hit count, and the hit rate percentage.

    Args:
        records: List of SDK turn records from Player invocations

    Returns:
        CeilingSummary with aggregated metrics

    Examples:
        >>> records = [
        ...     SdkTurnRecord(task_id="TASK-001", turns_used=50, max_turns=50),
        ...     SdkTurnRecord(task_id="TASK-002", turns_used=30, max_turns=50),
        ... ]
        >>> summary = compute_ceiling_summary(records)
        >>> summary.ceiling_hits
        1
        >>> summary.ceiling_hit_rate
        50.0
    """
    ceiling_hits = sum(1 for r in records if r.ceiling_hit)
    return CeilingSummary(
        total_invocations=len(records),
        ceiling_hits=ceiling_hits,
        records=tuple(records),
    )


def detect_ceiling_hit(
    turns_used: Optional[int], max_turns: Optional[int]
) -> bool:
    """Detect whether an invocation hit the SDK turn ceiling.

    Handles None values gracefully - returns False when data is unavailable.

    Args:
        turns_used: Actual SDK turns used (from ResultMessage.num_turns)
        max_turns: SDK turn ceiling (from _effective_sdk_max_turns)

    Returns:
        True if ceiling was hit (turns_used >= max_turns),
        False otherwise or if either value is None

    Examples:
        >>> detect_ceiling_hit(50, 50)
        True
        >>> detect_ceiling_hit(30, 50)
        False
        >>> detect_ceiling_hit(None, 50)
        False
    """
    if turns_used is None or max_turns is None:
        return False
    return turns_used >= max_turns
