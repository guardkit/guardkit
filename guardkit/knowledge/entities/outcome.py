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

    def to_episode_body(self) -> str:
        """Convert outcome to human-readable episode body.

        Creates a structured text representation suitable for
        storage in Graphiti as an episode body.

        Returns:
            Human-readable string representation of the outcome
        """
        lines = []

        # Header section
        lines.append(f"Outcome ID: {self.id}")
        lines.append(f"Outcome Type: {self.outcome_type.value}")
        lines.append(f"Task ID: {self.task_id}")
        lines.append(f"Task Title: {self.task_title}")
        lines.append(f"Success: {self.success}")
        lines.append("")

        # Requirements section
        lines.append("Requirements:")
        lines.append(self.task_requirements)
        lines.append("")

        # Summary section
        lines.append("Summary:")
        lines.append(self.summary)
        lines.append("")

        # Approach section (if provided)
        if self.approach_used:
            lines.append("Approach Used:")
            lines.append(self.approach_used)
            lines.append("")

        # Patterns section (if provided)
        if self.patterns_used:
            lines.append("Patterns Used:")
            for pattern in self.patterns_used:
                lines.append(f"  - {pattern}")
            lines.append("")

        # Problems section (if provided)
        if self.problems_encountered:
            lines.append("Problems Encountered:")
            for problem in self.problems_encountered:
                lines.append(f"  - {problem}")
            lines.append("")

        # Lessons section (if provided)
        if self.lessons_learned:
            lines.append("Lessons Learned:")
            for lesson in self.lessons_learned:
                lines.append(f"  - {lesson}")
            lines.append("")

        # Metrics section (if any metrics provided)
        metrics_lines = []
        if self.tests_written is not None:
            metrics_lines.append(f"  tests_written: {self.tests_written}")
        if self.test_coverage is not None:
            metrics_lines.append(f"  test_coverage: {self.test_coverage}")
        if self.review_cycles is not None:
            metrics_lines.append(f"  review_cycles: {self.review_cycles}")
        if self.duration_minutes is not None:
            metrics_lines.append(f"  duration_minutes: {self.duration_minutes}")

        if metrics_lines:
            lines.append("Metrics:")
            lines.extend(metrics_lines)
            lines.append("")

        # Timestamps section (if provided)
        if self.started_at or self.completed_at:
            lines.append("Timestamps:")
            if self.started_at:
                lines.append(f"  started_at: {self.started_at.isoformat()}")
            if self.completed_at:
                lines.append(f"  completed_at: {self.completed_at.isoformat()}")
            lines.append("")

        # References section (if provided)
        if self.feature_id or self.related_adr_ids:
            lines.append("References:")
            if self.feature_id:
                lines.append(f"  feature_id: {self.feature_id}")
            if self.related_adr_ids:
                lines.append(f"  related_adrs: {', '.join(self.related_adr_ids)}")
            lines.append("")

        return "\n".join(lines)
