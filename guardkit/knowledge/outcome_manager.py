"""
Task outcome capture and management.

This module provides functionality for capturing task outcomes
as episodes in Graphiti. All operations are designed for graceful
degradation - they will succeed even when Graphiti is unavailable.

Public API:
    capture_task_outcome: Capture a task outcome as an episode
    OutcomeManager: Class-based interface for outcome management

Example:
    from guardkit.knowledge.outcome_manager import capture_task_outcome
    from guardkit.knowledge.entities.outcome import OutcomeType

    outcome_id = await capture_task_outcome(
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-1234",
        task_title="Implement OAuth2",
        task_requirements="Add OAuth2 authentication",
        success=True,
        summary="Successfully implemented OAuth2 with PKCE"
    )
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional, List

from guardkit.knowledge.graphiti_client import get_graphiti
from guardkit.knowledge.entities.outcome import OutcomeType, TaskOutcome

logger = logging.getLogger(__name__)

# Group ID for task outcomes in Graphiti
TASK_OUTCOMES_GROUP_ID = "task_outcomes"


def _generate_outcome_id() -> str:
    """Generate a unique outcome ID.

    Returns:
        Unique ID in format OUT-XXXXXXXX (8 uppercase hex chars)
    """
    return f"OUT-{uuid.uuid4().hex[:8].upper()}"


async def capture_task_outcome(
    outcome_type: OutcomeType,
    task_id: str,
    task_title: str,
    task_requirements: str,
    success: bool,
    summary: str,
    approach_used: Optional[str] = None,
    patterns_used: Optional[List[str]] = None,
    problems_encountered: Optional[List[str]] = None,
    lessons_learned: Optional[List[str]] = None,
    tests_written: Optional[int] = None,
    test_coverage: Optional[float] = None,
    review_cycles: Optional[int] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    duration_minutes: Optional[int] = None,
    feature_id: Optional[str] = None,
    related_adr_ids: Optional[List[str]] = None,
) -> str:
    """Capture a task outcome as an episode in Graphiti.

    Creates a TaskOutcome instance and stores it in Graphiti as an episode.
    Gracefully degrades if Graphiti is unavailable - still returns the
    generated outcome ID.

    Args:
        outcome_type: Type of outcome from OutcomeType enum
        task_id: Task ID that this outcome belongs to
        task_title: Human-readable title of the task
        task_requirements: Original task requirements/description
        success: Whether the outcome was successful
        summary: Brief summary of the outcome
        approach_used: Description of the approach taken (optional)
        patterns_used: List of design patterns applied (optional)
        problems_encountered: List of problems faced (optional)
        lessons_learned: List of lessons learned (optional)
        tests_written: Number of tests written (optional)
        test_coverage: Test coverage percentage (optional)
        review_cycles: Number of review cycles (optional)
        started_at: When work started (optional)
        completed_at: When work completed (optional)
        duration_minutes: Total duration in minutes (optional)
        feature_id: Related feature ID if applicable (optional)
        related_adr_ids: List of related ADR IDs (optional)

    Returns:
        Unique outcome ID in format OUT-XXXXXXXX

    Example:
        outcome_id = await capture_task_outcome(
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Implement OAuth2",
            task_requirements="Add OAuth2 authentication",
            success=True,
            summary="Successfully implemented"
        )
    """
    # Generate unique ID
    outcome_id = _generate_outcome_id()

    # Create TaskOutcome instance
    outcome = TaskOutcome(
        id=outcome_id,
        outcome_type=outcome_type,
        task_id=task_id,
        task_title=task_title,
        task_requirements=task_requirements,
        success=success,
        summary=summary,
        approach_used=approach_used,
        patterns_used=patterns_used,
        problems_encountered=problems_encountered,
        lessons_learned=lessons_learned,
        tests_written=tests_written,
        test_coverage=test_coverage,
        review_cycles=review_cycles,
        started_at=started_at,
        completed_at=completed_at,
        duration_minutes=duration_minutes,
        feature_id=feature_id,
        related_adr_ids=related_adr_ids,
    )

    # Generate episode body
    episode_body = outcome.to_episode_body()

    # Create episode name
    episode_name = f"{outcome_id}: {task_id} - {task_title}"

    # Attempt to store in Graphiti (graceful degradation)
    client = get_graphiti()

    if client is None:
        logger.debug("[Graphiti] Client unavailable, skipping outcome capture")
        return outcome_id

    if not client.enabled:
        logger.debug("[Graphiti] Client disabled, skipping outcome capture")
        return outcome_id

    try:
        await client.add_episode(
            name=episode_name,
            episode_body=json.dumps(episode_body),
            group_id=TASK_OUTCOMES_GROUP_ID,
            source="auto_captured",
            entity_type="task_outcome"
        )
        logger.info(f"[Graphiti] Captured task outcome {outcome_id} for {task_id}")
    except Exception as e:
        logger.warning(f"[Graphiti] Failed to store outcome {outcome_id}: {e}")

    return outcome_id


class OutcomeManager:
    """Class-based interface for outcome management.

    Provides a stateful interface for managing task outcomes.
    This class wraps the module-level functions for convenience.

    Example:
        manager = OutcomeManager()
        outcome_id = await manager.capture(
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Implement OAuth2",
            task_requirements="Add OAuth2",
            success=True,
            summary="Done"
        )
    """

    async def capture(
        self,
        outcome_type: OutcomeType,
        task_id: str,
        task_title: str,
        task_requirements: str,
        success: bool,
        summary: str,
        **kwargs,
    ) -> str:
        """Capture a task outcome.

        Delegates to capture_task_outcome function.

        Args:
            outcome_type: Type of outcome from OutcomeType enum
            task_id: Task ID that this outcome belongs to
            task_title: Human-readable title of the task
            task_requirements: Original task requirements/description
            success: Whether the outcome was successful
            summary: Brief summary of the outcome
            **kwargs: Additional optional fields

        Returns:
            Unique outcome ID in format OUT-XXXXXXXX
        """
        return await capture_task_outcome(
            outcome_type=outcome_type,
            task_id=task_id,
            task_title=task_title,
            task_requirements=task_requirements,
            success=success,
            summary=summary,
            **kwargs,
        )
