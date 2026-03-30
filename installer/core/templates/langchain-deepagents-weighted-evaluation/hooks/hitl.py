"""Human-in-the-loop checkpoint hooks for weighted adversarial cooperation.

Provides configurable checkpoints where a human can review and override
Coach verdicts, adjust criteria weights, or halt the pipeline.

Populated by: TASK-TI-015 (HITL Checkpoint Hooks)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CheckpointAction(str, Enum):
    """Actions available at a HITL checkpoint."""

    APPROVE = "approve"
    REJECT = "reject"
    OVERRIDE = "override"
    ADJUST_WEIGHTS = "adjust_weights"
    HALT = "halt"


@dataclass
class CheckpointResult:
    """Result of a HITL checkpoint evaluation."""

    action: CheckpointAction
    reason: str = ""
    adjusted_weights: dict[str, float] | None = None
    override_verdict: dict[str, Any] | None = None


class HITLCheckpoint:
    """Human-in-the-loop checkpoint for pipeline review.

    Checkpoints are triggered based on configurable conditions:
    - Score is borderline (near acceptance threshold)
    - Maximum retries are about to be exhausted
    - Specific criteria fail despite overall passing score
    - Manual trigger via adversarial config

    Args:
        enabled: Whether HITL checkpoints are active.
        borderline_range: Score range considered borderline (e.g., 0.05 around threshold).
        trigger_on_exhaustion: Whether to checkpoint before retry exhaustion.
    """

    def __init__(
        self,
        enabled: bool = True,
        borderline_range: float = 0.05,
        trigger_on_exhaustion: bool = True,
    ) -> None:
        self._enabled = enabled
        self._borderline_range = borderline_range
        self._trigger_on_exhaustion = trigger_on_exhaustion

    @property
    def enabled(self) -> bool:
        return self._enabled

    def should_trigger(
        self,
        composite_score: float,
        acceptance_threshold: float,
        attempt: int,
        max_retries: int,
    ) -> bool:
        """Determine if a HITL checkpoint should trigger.

        Args:
            composite_score: Current weighted composite score.
            acceptance_threshold: Minimum score for acceptance.
            attempt: Current attempt number (1-indexed).
            max_retries: Maximum allowed attempts.

        Returns:
            True if checkpoint should trigger.
        """
        if not self._enabled:
            return False

        # Borderline score (within range of threshold)
        if abs(composite_score - acceptance_threshold) <= self._borderline_range:
            logger.info(
                "HITL trigger: borderline score %.3f (threshold: %.3f)",
                composite_score,
                acceptance_threshold,
            )
            return True

        # About to exhaust retries
        if self._trigger_on_exhaustion and attempt >= max_retries:
            logger.info(
                "HITL trigger: retry exhaustion (attempt %d/%d)",
                attempt,
                max_retries,
            )
            return True

        return False

    def evaluate(
        self,
        composite_score: float,
        criterion_scores: dict[str, float],
        content_preview: str,
    ) -> CheckpointResult:
        """Present checkpoint to human for evaluation.

        This is a placeholder for the full HITL implementation (TASK-TI-015).
        In the scaffold, it auto-approves to allow pipeline testing.

        Args:
            composite_score: Current composite score.
            criterion_scores: Per-criterion scores.
            content_preview: Preview of Player content.

        Returns:
            CheckpointResult with the human's decision.
        """
        logger.info(
            "HITL checkpoint (auto-approve in scaffold): score=%.3f",
            composite_score,
        )
        return CheckpointResult(
            action=CheckpointAction.APPROVE,
            reason="Auto-approved (HITL scaffold — see TASK-TI-015)",
        )
