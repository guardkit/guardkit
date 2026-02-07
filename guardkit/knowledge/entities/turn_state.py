"""
Turn state entity definition.

This module provides the TurnStateEntity dataclass for capturing the state
at the end of each feature-build turn. Turn state episodes enable cross-turn
learning by providing context about what was attempted, what worked, what
failed, and what to try next.

Public API:
    TurnMode: Enum for different turn modes (fresh_start, recovering_state, continuing_work)
    TurnStateEntity: Dataclass for capturing turn state

Example:
    from guardkit.knowledge.entities.turn_state import TurnStateEntity, TurnMode
    from datetime import datetime

    turn_state = TurnStateEntity(
        id="TURN-FEAT-GE-1",
        feature_id="FEAT-GE",
        task_id="TASK-GE-001",
        turn_number=1,
        player_summary="Implemented OAuth2 authentication",
        player_decision="implemented",
        coach_decision="approved",
        coach_feedback=None,
        mode=TurnMode.FRESH_START,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )

    # Store in Graphiti
    episode_body = turn_state.to_episode_body()
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class TurnMode(Enum):
    """Mode describing how the turn started.

    Values:
        FRESH_START: First turn of a task, starting from scratch
        RECOVERING_STATE: Resuming after crash/timeout, recovering previous state
        CONTINUING_WORK: Normal continuation from previous turn

    Example:
        mode = TurnMode.FRESH_START
        assert mode.value == "fresh_start"
    """

    FRESH_START = "fresh_start"
    RECOVERING_STATE = "recovering_state"
    CONTINUING_WORK = "continuing_work"


@dataclass
class TurnStateEntity:
    """Captures the state at the end of each feature-build turn.

    This entity captures everything that happened during a turn, including:
    - What the Player implemented/attempted
    - The Coach's decision and feedback
    - Progress on acceptance criteria
    - Quality metrics (tests, coverage, arch score)
    - Lessons learned and next steps

    This information is critical for cross-turn learning, allowing Turn N
    to understand what happened in Turn N-1 and avoid repeating mistakes.

    Attributes:
        id: Turn identifier (TURN-{feature_id}-{turn_number})
        feature_id: Feature identifier (e.g., "FEAT-GE")
        task_id: Task identifier (e.g., "TASK-GE-001")
        turn_number: Turn number (1-indexed)

        player_summary: What Player implemented/attempted this turn
        player_decision: Player's final decision ("implemented" | "failed" | "blocked")
        coach_decision: Coach's decision ("approved" | "feedback" | "rejected")
        coach_feedback: Specific feedback if not approved

        mode: How the turn started (TurnMode enum)
        blockers_found: List of blockers encountered
        progress_summary: Brief description of progress made

        acceptance_criteria_status: Status of each acceptance criterion
            Format: {"criterion_1": "completed", "criterion_2": "in_progress"}

        files_modified: List of files created or modified during this turn

        tests_passed: Number of tests that passed
        tests_failed: Number of tests that failed
        coverage: Test coverage percentage (0-100)
        arch_score: Architectural review score (0-100)

        started_at: When this turn started
        completed_at: When this turn completed
        duration_seconds: Turn duration in seconds

        lessons_from_turn: Lessons learned during this turn
        what_to_try_next: Suggested focus for the next turn

    Example:
        turn_state = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Implemented authentication with OAuth2",
            player_decision="implemented",
            coach_decision="feedback",
            coach_feedback="Add session caching",
            mode=TurnMode.FRESH_START,
            blockers_found=["Missing Redis"],
            acceptance_criteria_status={"AC-001": "completed"},
            tests_passed=15,
            tests_failed=0,
            coverage=85.5,
            started_at=datetime(2025, 1, 29, 10, 0, 0),
            completed_at=datetime(2025, 1, 29, 10, 15, 0)
        )
    """

    # Identity
    id: str  # TURN-{feature_id}-{turn_number}
    feature_id: str
    task_id: str
    turn_number: int

    # What happened
    player_summary: str  # What Player implemented/attempted
    player_decision: str  # "implemented" | "failed" | "blocked"
    coach_decision: str  # "approved" | "feedback" | "rejected"
    coach_feedback: Optional[str]  # Specific feedback if not approved

    # Mode and state
    mode: TurnMode  # State machine mode

    # Timing (required)
    started_at: datetime
    completed_at: datetime

    # Progress tracking (optional with defaults)
    blockers_found: List[str] = field(default_factory=list)
    progress_summary: str = ""  # Brief description of progress made

    # Acceptance criteria tracking
    acceptance_criteria_status: Dict[str, str] = field(default_factory=dict)
    # Format: {"criterion_1": "completed", "criterion_2": "in_progress", "criterion_3": "not_started"}

    # Files modified during this turn
    files_modified: List[str] = field(default_factory=list)

    # Quality metrics (optional)
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    coverage: Optional[float] = None
    arch_score: Optional[int] = None
    duration_seconds: Optional[int] = None

    # Learning (optional with defaults)
    lessons_from_turn: List[str] = field(default_factory=list)
    what_to_try_next: Optional[str] = None

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Creates a dictionary representation suitable for storage
        in Graphiti as an episode body. Returns only domain data;
        metadata fields like entity_type are injected by GraphitiClient.

        Returns:
            Dictionary containing all turn state fields.

        Example:
            body = turn_state.to_episode_body()
            assert body["mode"] == "fresh_start"  # enum serialized as string
        """
        return {
            "id": self.id,
            "feature_id": self.feature_id,
            "task_id": self.task_id,
            "turn_number": self.turn_number,
            "player_summary": self.player_summary,
            "player_decision": self.player_decision,
            "coach_decision": self.coach_decision,
            "coach_feedback": self.coach_feedback,
            "mode": self.mode.value,  # Serialize enum as string
            "blockers_found": self.blockers_found,
            "progress_summary": self.progress_summary,
            "acceptance_criteria_status": self.acceptance_criteria_status,
            "files_modified": self.files_modified,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "coverage": self.coverage,
            "arch_score": self.arch_score,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "lessons_from_turn": self.lessons_from_turn,
            "what_to_try_next": self.what_to_try_next
        }
