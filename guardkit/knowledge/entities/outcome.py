"""
Task outcome entity definitions.

This module provides the data structures for capturing task outcomes
in the knowledge graph. Outcomes represent the results of completed
tasks, reviews, and pattern applications.

Public API:
    OutcomeType: Enum for different outcome types
    TaskOutcome: Dataclass for capturing task outcomes
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class OutcomeType(Enum):
    """Enum for different types of task outcomes.

    Attributes:
        TASK_COMPLETED: Task was completed successfully
        TASK_FAILED: Task failed to complete
        REVIEW_PASSED: Code review passed
        REVIEW_FAILED: Code review failed
        PATTERN_SUCCESS: Design pattern applied successfully
        PATTERN_FAILURE: Design pattern application failed
    """
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    REVIEW_PASSED = "REVIEW_PASSED"
    REVIEW_FAILED = "REVIEW_FAILED"
    PATTERN_SUCCESS = "PATTERN_SUCCESS"
    PATTERN_FAILURE = "PATTERN_FAILURE"


@dataclass
class TaskOutcome:
    """Dataclass representing the outcome of a completed task.

    This captures comprehensive information about a task's completion,
    including approach used, patterns applied, problems encountered,
    and lessons learned. Used for episode capture in Graphiti.

    Attributes:
        id: Unique outcome ID in format OUT-XXXXXXXX
        outcome_type: Type of outcome from OutcomeType enum
        task_id: Task ID that this outcome belongs to
        task_title: Human-readable title of the task
        task_requirements: Original task requirements/description
        success: Whether the outcome was successful
        summary: Brief summary of the outcome
        approach_used: Description of the approach taken (optional)
        patterns_used: List of design patterns applied (optional)
        problems_encountered: List of problems faced during work (optional)
        lessons_learned: List of lessons learned (optional)
        tests_written: Number of tests written (optional)
        test_coverage: Test coverage percentage (optional)
        review_cycles: Number of review cycles (optional)
        started_at: When work started (optional)
        completed_at: When work completed (optional)
        duration_minutes: Total duration in minutes (optional)
        feature_id: Related feature ID if applicable (optional)
        related_adr_ids: List of related ADR IDs (optional)

    Example:
        outcome = TaskOutcome(
            id="OUT-A1B2C3D4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Implement OAuth2",
            task_requirements="Add OAuth2 authentication",
            success=True,
            summary="Successfully implemented OAuth2 with PKCE"
        )
    """
    # Required fields
    id: str
    outcome_type: OutcomeType
    task_id: str
    task_title: str
    task_requirements: str
    success: bool
    summary: str

    # Optional fields with defaults
    approach_used: Optional[str] = None
    patterns_used: Optional[List[str]] = None
    problems_encountered: Optional[List[str]] = None
    lessons_learned: Optional[List[str]] = None
    tests_written: Optional[int] = None
    test_coverage: Optional[float] = None
    review_cycles: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    feature_id: Optional[str] = None
    related_adr_ids: Optional[List[str]] = None

    def to_episode_body(self) -> dict:
        """Convert outcome to episode body dictionary.

        Creates a structured dictionary representation suitable for
        storage in Graphiti as an episode body. Returns only domain data;
        metadata fields like entity_type are injected by GraphitiClient.

        Returns:
            Dictionary with all outcome fields suitable for JSON serialization
        """
        return {
            "id": self.id,
            "outcome_type": self.outcome_type.value,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "task_requirements": self.task_requirements,
            "success": self.success,
            "summary": self.summary,
            "approach_used": self.approach_used,
            "patterns_used": self.patterns_used,
            "problems_encountered": self.problems_encountered,
            "lessons_learned": self.lessons_learned,
            "tests_written": self.tests_written,
            "test_coverage": self.test_coverage,
            "review_cycles": self.review_cycles,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_minutes": self.duration_minutes,
            "feature_id": self.feature_id,
            "related_adr_ids": self.related_adr_ids
        }
