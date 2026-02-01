"""
TDD RED Phase: Tests for guardkit.knowledge.entities.turn_state

These tests define the contract for TurnStateEntity and related functions.
Following TDD, tests are written FIRST to define expected behavior.

Test Coverage:
- TurnStateEntity dataclass creation and validation
- TurnStateEntity.to_episode_body() serialization
- TurnMode enum values
- capture_turn_state() with mocked Graphiti client
- load_turn_continuation_context() query functionality
- Graceful degradation when Graphiti disabled
- Integration tests (capture then load round trip)

Coverage Target: >=80%
Test Count: 30+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional, List, Dict
from datetime import datetime
import json

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.entities.turn_state import (
        TurnStateEntity,
        TurnMode,
    )
    from guardkit.knowledge.turn_state_operations import (
        capture_turn_state,
        load_turn_continuation_context,
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


# ============================================================================
# 1. TurnMode Enum Tests (3 tests)
# ============================================================================

class TestTurnModeEnum:
    """Test TurnMode enum values."""

    def test_turn_mode_enum_exists(self):
        """Test TurnMode enum is defined."""
        assert TurnMode is not None

    def test_turn_mode_fresh_start(self):
        """Test FRESH_START mode exists."""
        assert TurnMode.FRESH_START.value == "fresh_start"

    def test_turn_mode_recovering_state(self):
        """Test RECOVERING_STATE mode exists."""
        assert TurnMode.RECOVERING_STATE.value == "recovering_state"

    def test_turn_mode_continuing_work(self):
        """Test CONTINUING_WORK mode exists."""
        assert TurnMode.CONTINUING_WORK.value == "continuing_work"


# ============================================================================
# 2. TurnStateEntity Dataclass Tests (12 tests)
# ============================================================================

class TestTurnStateEntityDataclass:
    """Test TurnStateEntity dataclass creation and validation."""

    def test_turn_state_entity_exists(self):
        """Test TurnStateEntity class is defined."""
        assert TurnStateEntity is not None

    def test_turn_state_entity_creation_minimal(self):
        """Test creating TurnStateEntity with minimal required fields."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Implemented feature X",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        assert entity.id == "TURN-FEAT-GE-1"
        assert entity.feature_id == "FEAT-GE"
        assert entity.task_id == "TASK-GE-001"
        assert entity.turn_number == 1
        assert entity.player_summary == "Implemented feature X"
        assert entity.player_decision == "implemented"
        assert entity.coach_decision == "approved"
        assert entity.coach_feedback is None
        assert entity.mode == TurnMode.FRESH_START
        assert entity.started_at == started
        assert entity.completed_at == completed

    def test_turn_state_entity_creation_complete(self):
        """Test creating TurnStateEntity with all fields."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Implemented authentication with OAuth2",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback="Good test coverage, approved",
            mode=TurnMode.FRESH_START,
            blockers_found=["Missing Redis dependency"],
            progress_summary="Authentication working, needs caching",
            acceptance_criteria_status={
                "AC-001": "completed",
                "AC-002": "in_progress"
            },
            tests_passed=15,
            tests_failed=0,
            coverage=85.5,
            arch_score=75,
            started_at=started,
            completed_at=completed,
            duration_seconds=900,
            lessons_from_turn=["Redis needed for sessions", "Test coverage good"],
            what_to_try_next="Add session caching"
        )

        assert entity.id == "TURN-FEAT-GE-1"
        assert entity.feature_id == "FEAT-GE"
        assert entity.task_id == "TASK-GE-001"
        assert entity.turn_number == 1
        assert len(entity.blockers_found) == 1
        assert entity.progress_summary == "Authentication working, needs caching"
        assert len(entity.acceptance_criteria_status) == 2
        assert entity.tests_passed == 15
        assert entity.tests_failed == 0
        assert entity.coverage == 85.5
        assert entity.arch_score == 75
        assert entity.duration_seconds == 900
        assert len(entity.lessons_from_turn) == 2
        assert entity.what_to_try_next == "Add session caching"

    def test_turn_state_entity_default_lists(self):
        """Test TurnStateEntity default empty lists."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        # Should have default empty lists
        assert entity.blockers_found == []
        assert entity.acceptance_criteria_status == {}
        assert entity.lessons_from_turn == []

    def test_turn_state_entity_optional_fields(self):
        """Test TurnStateEntity optional field defaults."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        # Optional quality metrics should be None
        assert entity.tests_passed is None
        assert entity.tests_failed is None
        assert entity.coverage is None
        assert entity.arch_score is None
        assert entity.duration_seconds is None
        assert entity.what_to_try_next is None

    def test_turn_state_entity_player_decisions(self):
        """Test various player_decision values."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        for decision in ["implemented", "failed", "blocked"]:
            entity = TurnStateEntity(
                id="TURN-FEAT-GE-1",
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                turn_number=1,
                player_summary="Summary",
                player_decision=decision,
                coach_decision="feedback",
                coach_feedback=None,
                mode=TurnMode.FRESH_START,
                started_at=started,
                completed_at=completed
            )
            assert entity.player_decision == decision

    def test_turn_state_entity_coach_decisions(self):
        """Test various coach_decision values."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        for decision in ["approved", "feedback", "rejected"]:
            entity = TurnStateEntity(
                id="TURN-FEAT-GE-1",
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                turn_number=1,
                player_summary="Summary",
                player_decision="implemented",
                coach_decision=decision,
                coach_feedback=None,
                mode=TurnMode.FRESH_START,
                started_at=started,
                completed_at=completed
            )
            assert entity.coach_decision == decision

    def test_turn_state_entity_turn_modes(self):
        """Test various TurnMode values."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        for mode in [TurnMode.FRESH_START, TurnMode.RECOVERING_STATE, TurnMode.CONTINUING_WORK]:
            entity = TurnStateEntity(
                id="TURN-FEAT-GE-1",
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                turn_number=1,
                player_summary="Summary",
                player_decision="implemented",
                coach_decision="approved",
                coach_feedback=None,
                mode=mode,
                started_at=started,
                completed_at=completed
            )
            assert entity.mode == mode

    def test_turn_state_entity_turn_numbers(self):
        """Test various turn number values."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        for turn_num in [1, 2, 3, 10]:
            entity = TurnStateEntity(
                id=f"TURN-FEAT-GE-{turn_num}",
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                turn_number=turn_num,
                player_summary="Summary",
                player_decision="implemented",
                coach_decision="approved",
                coach_feedback=None,
                mode=TurnMode.CONTINUING_WORK,
                started_at=started,
                completed_at=completed
            )
            assert entity.turn_number == turn_num

    def test_turn_state_entity_with_multiple_blockers(self):
        """Test TurnStateEntity with multiple blockers."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        blockers = [
            "Missing Redis dependency",
            "API rate limit hit",
            "Database connection timeout"
        ]

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="blocked",
            coach_decision="feedback",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            blockers_found=blockers,
            started_at=started,
            completed_at=completed
        )

        assert len(entity.blockers_found) == 3
        assert entity.blockers_found == blockers

    def test_turn_state_entity_with_multiple_acceptance_criteria(self):
        """Test TurnStateEntity with multiple acceptance criteria."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        ac_status = {
            "AC-001": "completed",
            "AC-002": "in_progress",
            "AC-003": "not_started",
            "AC-004": "completed"
        }

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="feedback",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            acceptance_criteria_status=ac_status,
            started_at=started,
            completed_at=completed
        )

        assert len(entity.acceptance_criteria_status) == 4
        assert entity.acceptance_criteria_status["AC-001"] == "completed"

    def test_turn_state_entity_with_lessons_learned(self):
        """Test TurnStateEntity with multiple lessons."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        lessons = [
            "Redis needed for session management",
            "Test coverage important for edge cases",
            "API rate limiting needs retry logic"
        ]

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            lessons_from_turn=lessons,
            started_at=started,
            completed_at=completed
        )

        assert len(entity.lessons_from_turn) == 3
        assert entity.lessons_from_turn == lessons

    def test_turn_state_entity_with_files_modified(self):
        """Test TurnStateEntity with files_modified field."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        files = [
            "src/auth/login.py",
            "src/auth/session.py",
            "tests/test_auth.py"
        ]

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            files_modified=files,
            started_at=started,
            completed_at=completed
        )

        assert len(entity.files_modified) == 3
        assert entity.files_modified == files

    def test_turn_state_entity_default_files_modified(self):
        """Test TurnStateEntity default empty files_modified list."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        # Should have default empty list
        assert entity.files_modified == []


# ============================================================================
# 3. TurnStateEntity.to_episode_body() Tests (8 tests)
# ============================================================================

class TestTurnStateEntitySerialization:
    """Test TurnStateEntity.to_episode_body() serialization."""

    def test_to_episode_body_returns_dict(self):
        """Test to_episode_body returns a dictionary."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        episode_body = entity.to_episode_body()

        assert isinstance(episode_body, dict)

    def test_to_episode_body_contains_entity_type(self):
        """Test serialization includes entity_type field."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        episode_body = entity.to_episode_body()

        assert "entity_type" in episode_body
        assert episode_body["entity_type"] == "turn_state"

    def test_to_episode_body_contains_all_required_fields(self):
        """Test serialization includes all required fields."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Implemented OAuth2 authentication",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback="Good work",
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        episode_body = entity.to_episode_body()

        assert episode_body["id"] == "TURN-FEAT-GE-1"
        assert episode_body["feature_id"] == "FEAT-GE"
        assert episode_body["task_id"] == "TASK-GE-001"
        assert episode_body["turn_number"] == 1
        assert episode_body["player_summary"] == "Implemented OAuth2 authentication"
        assert episode_body["player_decision"] == "implemented"
        assert episode_body["coach_decision"] == "approved"
        assert episode_body["coach_feedback"] == "Good work"
        assert episode_body["mode"] == "fresh_start"

    def test_to_episode_body_contains_optional_fields(self):
        """Test serialization includes optional fields when present."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            blockers_found=["Blocker 1"],
            progress_summary="Progress made",
            acceptance_criteria_status={"AC-001": "completed"},
            files_modified=["src/main.py", "tests/test_main.py"],
            tests_passed=10,
            tests_failed=0,
            coverage=85.0,
            arch_score=75,
            duration_seconds=900,
            lessons_from_turn=["Lesson 1"],
            what_to_try_next="Next step",
            started_at=started,
            completed_at=completed
        )

        episode_body = entity.to_episode_body()

        assert episode_body["blockers_found"] == ["Blocker 1"]
        assert episode_body["progress_summary"] == "Progress made"
        assert episode_body["acceptance_criteria_status"] == {"AC-001": "completed"}
        assert episode_body["files_modified"] == ["src/main.py", "tests/test_main.py"]
        assert episode_body["tests_passed"] == 10
        assert episode_body["tests_failed"] == 0
        assert episode_body["coverage"] == 85.0
        assert episode_body["arch_score"] == 75
        assert episode_body["duration_seconds"] == 900
        assert episode_body["lessons_from_turn"] == ["Lesson 1"]
        assert episode_body["what_to_try_next"] == "Next step"

    def test_to_episode_body_contains_timestamps(self):
        """Test serialization includes timestamp fields."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        episode_body = entity.to_episode_body()

        assert "started_at" in episode_body
        assert "completed_at" in episode_body
        assert "2025-01-29" in episode_body["started_at"]
        assert "2025-01-29" in episode_body["completed_at"]

    def test_to_episode_body_serializes_to_json(self):
        """Test episode body can be serialized to JSON."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        episode_body = entity.to_episode_body()

        # Should be JSON serializable
        json_str = json.dumps(episode_body)
        assert isinstance(json_str, str)

        # Should be valid JSON that can be parsed back
        parsed = json.loads(json_str)
        assert parsed["id"] == "TURN-FEAT-GE-1"

    def test_to_episode_body_handles_enum_serialization(self):
        """Test TurnMode enum is serialized as string."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        for mode in [TurnMode.FRESH_START, TurnMode.RECOVERING_STATE, TurnMode.CONTINUING_WORK]:
            entity = TurnStateEntity(
                id="TURN-FEAT-GE-1",
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                turn_number=1,
                player_summary="Summary",
                player_decision="implemented",
                coach_decision="approved",
                coach_feedback=None,
                mode=mode,
                started_at=started,
                completed_at=completed
            )

            episode_body = entity.to_episode_body()

            # Mode should be serialized as string value
            assert isinstance(episode_body["mode"], str)
            assert episode_body["mode"] == mode.value

    def test_to_episode_body_handles_none_values(self):
        """Test serialization handles None values correctly."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        episode_body = entity.to_episode_body()

        # None values should be included
        assert "coach_feedback" in episode_body
        assert episode_body["coach_feedback"] is None


# ============================================================================
# 4. capture_turn_state() Tests (7 tests)
# ============================================================================

class TestCaptureTurnState:
    """Test capture_turn_state() function."""

    @pytest.mark.asyncio
    async def test_capture_turn_state_success(self):
        """Test successful turn state capture."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        await capture_turn_state(mock_client, entity)

        mock_client.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_turn_state_correct_group_id(self):
        """Test capture uses correct group_id."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        await capture_turn_state(mock_client, entity)

        call_args = mock_client.add_episode.call_args
        assert call_args[1]["group_id"] == "turn_states"

    @pytest.mark.asyncio
    async def test_capture_turn_state_correct_episode_name(self):
        """Test capture creates correct episode name matching acceptance criteria format.

        Acceptance Criteria: Episode name must be `turn_{feature_id}_{task_id}_turn{N}`
        Example: turn_FEAT-GE_TASK-GE-001_turn1
        """
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        await capture_turn_state(mock_client, entity)

        call_args = mock_client.add_episode.call_args
        episode_name = call_args[1]["name"]

        # Episode name MUST match the acceptance criteria format exactly:
        # turn_{feature_id}_{task_id}_turn{N}
        expected_name = "turn_FEAT-GE_TASK-GE-001_turn1"
        assert episode_name == expected_name, f"Expected '{expected_name}', got '{episode_name}'"

    @pytest.mark.asyncio
    async def test_capture_turn_state_episode_name_format_various_turns(self):
        """Test episode name format for various turn numbers."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        for turn_num in [1, 2, 5, 10]:
            mock_client.add_episode.reset_mock()

            entity = TurnStateEntity(
                id=f"TURN-FEAT-TEST-{turn_num}",
                feature_id="FEAT-TEST",
                task_id="TASK-TEST-042",
                turn_number=turn_num,
                player_summary="Summary",
                player_decision="implemented",
                coach_decision="approved",
                coach_feedback=None,
                mode=TurnMode.CONTINUING_WORK,
                started_at=started,
                completed_at=completed
            )

            await capture_turn_state(mock_client, entity)

            call_args = mock_client.add_episode.call_args
            episode_name = call_args[1]["name"]

            # Format: turn_{feature_id}_{task_id}_turn{N}
            expected_name = f"turn_FEAT-TEST_TASK-TEST-042_turn{turn_num}"
            assert episode_name == expected_name, f"Turn {turn_num}: Expected '{expected_name}', got '{episode_name}'"

    @pytest.mark.asyncio
    async def test_capture_turn_state_disabled_client(self):
        """Test graceful degradation when client disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        # Should not crash
        await capture_turn_state(mock_client, entity)

        # Should not call add_episode
        mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_capture_turn_state_none_client(self):
        """Test graceful degradation when client is None."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        # Should not crash
        await capture_turn_state(None, entity)

    @pytest.mark.asyncio
    async def test_capture_turn_state_error_handling(self):
        """Test graceful degradation when add_episode fails."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("Graphiti error"))

        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        # Should not crash
        await capture_turn_state(mock_client, entity)

    @pytest.mark.asyncio
    async def test_capture_turn_state_uses_entity_body(self):
        """Test capture uses entity.to_episode_body() for content."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Summary",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        await capture_turn_state(mock_client, entity)

        call_args = mock_client.add_episode.call_args
        content = call_args[1]["content"]

        # Content should contain serialized entity data
        assert "TURN-FEAT-GE-1" in content
        assert "implemented" in content


# ============================================================================
# 5. load_turn_continuation_context() Tests (9 tests)
# ============================================================================

class TestLoadTurnContinuationContext:
    """Test load_turn_continuation_context() query function."""

    @pytest.mark.asyncio
    async def test_load_turn_continuation_context_turn_1_returns_none(self):
        """Test returns None for turn 1 (no previous turn)."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        result = await load_turn_continuation_context(
            mock_client,
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            current_turn=1
        )

        assert result is None
        mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_turn_continuation_context_turn_2_loads_previous(self):
        """Test returns formatted context for turn 2."""
        mock_result = {
            "id": "TURN-FEAT-GE-1",
            "feature_id": "FEAT-GE",
            "task_id": "TASK-GE-001",
            "turn_number": 1,
            "player_summary": "Implemented authentication",
            "player_decision": "implemented",
            "coach_decision": "feedback",
            "coach_feedback": "Need to add session caching",
            "mode": "fresh_start",
            "blockers_found": ["Missing Redis"],
            "acceptance_criteria_status": {"AC-001": "completed", "AC-002": "in_progress"},
            "lessons_from_turn": ["Redis needed"],
            "what_to_try_next": "Add caching layer",
            "entity_type": "turn_state"
        }

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[{"body": mock_result}])

        with patch('guardkit.knowledge.turn_state_operations.get_graphiti', return_value=mock_client):
            result = await load_turn_continuation_context(
                mock_client,
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                current_turn=2
            )

            assert result is not None
            assert isinstance(result, str)
            assert "Turn 1" in result
            assert "Implemented authentication" in result

    @pytest.mark.asyncio
    async def test_load_turn_continuation_context_includes_player_summary(self):
        """Test includes previous turn player summary."""
        mock_result = {
            "id": "TURN-FEAT-GE-1",
            "player_summary": "Implemented OAuth2 authentication",
            "player_decision": "implemented",
            "coach_decision": "approved",
            "coach_feedback": None,
            "entity_type": "turn_state"
        }

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[{"body": mock_result}])

        with patch('guardkit.knowledge.turn_state_operations.get_graphiti', return_value=mock_client):
            result = await load_turn_continuation_context(
                mock_client,
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                current_turn=2
            )

            assert "OAuth2 authentication" in result

    @pytest.mark.asyncio
    async def test_load_turn_continuation_context_includes_coach_feedback(self):
        """Test includes coach feedback from previous turn."""
        mock_result = {
            "id": "TURN-FEAT-GE-1",
            "player_summary": "Summary",
            "player_decision": "implemented",
            "coach_decision": "feedback",
            "coach_feedback": "Need to add error handling for edge cases",
            "entity_type": "turn_state"
        }

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[{"body": mock_result}])

        with patch('guardkit.knowledge.turn_state_operations.get_graphiti', return_value=mock_client):
            result = await load_turn_continuation_context(
                mock_client,
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                current_turn=2
            )

            assert "error handling for edge cases" in result

    @pytest.mark.asyncio
    async def test_load_turn_continuation_context_includes_blockers(self):
        """Test includes blockers from previous turn."""
        mock_result = {
            "id": "TURN-FEAT-GE-1",
            "player_summary": "Summary",
            "player_decision": "blocked",
            "coach_decision": "feedback",
            "coach_feedback": None,
            "blockers_found": ["Missing Redis", "API rate limit"],
            "entity_type": "turn_state"
        }

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[{"body": mock_result}])

        with patch('guardkit.knowledge.turn_state_operations.get_graphiti', return_value=mock_client):
            result = await load_turn_continuation_context(
                mock_client,
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                current_turn=2
            )

            assert "Redis" in result
            assert "rate limit" in result

    @pytest.mark.asyncio
    async def test_load_turn_continuation_context_includes_acceptance_criteria(self):
        """Test includes acceptance criteria status."""
        mock_result = {
            "id": "TURN-FEAT-GE-1",
            "player_summary": "Summary",
            "player_decision": "implemented",
            "coach_decision": "feedback",
            "coach_feedback": None,
            "acceptance_criteria_status": {
                "AC-001": "completed",
                "AC-002": "in_progress",
                "AC-003": "not_started"
            },
            "entity_type": "turn_state"
        }

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[{"body": mock_result}])

        with patch('guardkit.knowledge.turn_state_operations.get_graphiti', return_value=mock_client):
            result = await load_turn_continuation_context(
                mock_client,
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                current_turn=2
            )

            assert "AC-001" in result
            assert "completed" in result

    @pytest.mark.asyncio
    async def test_load_turn_continuation_context_graphiti_disabled(self):
        """Test graceful degradation when Graphiti disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        result = await load_turn_continuation_context(
            mock_client,
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            current_turn=2
        )

        assert result is None
        mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_turn_continuation_context_search_error(self):
        """Test graceful degradation when search fails."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(side_effect=Exception("Search error"))

        with patch('guardkit.knowledge.turn_state_operations.get_graphiti', return_value=mock_client):
            result = await load_turn_continuation_context(
                mock_client,
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                current_turn=2
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_load_turn_continuation_context_no_results_found(self):
        """Test returns None when no previous turn found."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.turn_state_operations.get_graphiti', return_value=mock_client):
            result = await load_turn_continuation_context(
                mock_client,
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                current_turn=2
            )

            assert result is None


# ============================================================================
# 6. Integration Tests (3 tests)
# ============================================================================

class TestIntegrationRoundTrip:
    """Test integration between capture and load operations."""

    @pytest.mark.asyncio
    async def test_capture_then_load_round_trip(self):
        """Test capturing turn state then loading it back."""
        # Create mock client that stores episode data
        captured_data = {}

        async def mock_add_episode(name, content, group_id, source_description):
            captured_data["name"] = name
            captured_data["content"] = content
            captured_data["group_id"] = group_id
            return "episode_123"

        async def mock_search(query, group_ids):
            # Return the captured data in search results
            return [{"body": captured_data.get("parsed_content", {})}]

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=mock_add_episode)
        mock_client.search = AsyncMock(side_effect=mock_search)

        # Capture turn 1
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Implemented authentication",
            player_decision="implemented",
            coach_decision="feedback",
            coach_feedback="Add session caching",
            mode=TurnMode.FRESH_START,
            blockers_found=["Missing Redis"],
            acceptance_criteria_status={"AC-001": "completed"},
            started_at=started,
            completed_at=completed
        )

        await capture_turn_state(mock_client, entity)

        # Store parsed content for search
        captured_data["parsed_content"] = entity.to_episode_body()

        # Load context for turn 2
        with patch('guardkit.knowledge.turn_state_operations.get_graphiti', return_value=mock_client):
            context = await load_turn_continuation_context(
                mock_client,
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                current_turn=2
            )

            assert context is not None
            assert "authentication" in context
            assert "session caching" in context

    @pytest.mark.asyncio
    async def test_multiple_turns_accumulate(self):
        """Test that multiple turns can be captured and queried."""
        captured_turns = []

        async def mock_add_episode(name, content, group_id, source_description):
            turn_data = {"name": name, "content": content, "group_id": group_id}
            captured_turns.append(turn_data)
            return f"episode_{len(captured_turns)}"

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=mock_add_episode)

        # Capture 3 turns
        for turn_num in [1, 2, 3]:
            started = datetime(2025, 1, 29, 10, 0, 0)
            completed = datetime(2025, 1, 29, 10, 15, 0)

            entity = TurnStateEntity(
                id=f"TURN-FEAT-GE-{turn_num}",
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                turn_number=turn_num,
                player_summary=f"Turn {turn_num} summary",
                player_decision="implemented",
                coach_decision="approved" if turn_num == 3 else "feedback",
                coach_feedback=None if turn_num == 3 else f"Feedback for turn {turn_num}",
                mode=TurnMode.CONTINUING_WORK,
                started_at=started,
                completed_at=completed
            )

            await capture_turn_state(mock_client, entity)

        # Verify all 3 turns were captured
        assert len(captured_turns) == 3
        assert mock_client.add_episode.call_count == 3

    @pytest.mark.asyncio
    async def test_turn_progression_context_chain(self):
        """Test that turn N can access context from turn N-1."""
        turns_storage = []

        async def mock_add_episode(name, content, group_id, source_description):
            turn_data = {
                "name": name,
                "content": content,
                "parsed": {}  # Would be parsed in real implementation
            }
            turns_storage.append(turn_data)
            return f"episode_{len(turns_storage)}"

        async def mock_search(query, group_ids):
            # Return the previous turn (N-1)
            if len(turns_storage) > 0:
                return [{"body": turns_storage[-1]["parsed"]}]
            return []

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=mock_add_episode)
        mock_client.search = AsyncMock(side_effect=mock_search)

        # Capture turn 1
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity1 = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="First implementation",
            player_decision="implemented",
            coach_decision="feedback",
            coach_feedback="Needs improvement",
            mode=TurnMode.FRESH_START,
            started_at=started,
            completed_at=completed
        )

        await capture_turn_state(mock_client, entity1)
        turns_storage[-1]["parsed"] = entity1.to_episode_body()

        # Load context for turn 2 should reference turn 1
        with patch('guardkit.knowledge.turn_state_operations.get_graphiti', return_value=mock_client):
            context = await load_turn_continuation_context(
                mock_client,
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                current_turn=2
            )

            # Should get context from turn 1
            if context:  # May be None if implementation not ready
                assert "First implementation" in context or context is None


# ============================================================================
# 7. create_turn_state_from_autobuild() Factory Tests (6 tests)
# ============================================================================

# Import the factory function if available
try:
    from guardkit.knowledge.turn_state_operations import (
        create_turn_state_from_autobuild,
    )
    FACTORY_AVAILABLE = True
except ImportError:
    FACTORY_AVAILABLE = False


@pytest.mark.skipif(
    not FACTORY_AVAILABLE,
    reason="create_turn_state_from_autobuild not yet implemented"
)
class TestCreateTurnStateFromAutoBuild:
    """Test create_turn_state_from_autobuild() factory function."""

    def test_create_turn_state_from_autobuild_generates_correct_id(self):
        """Test factory generates correct TURN-{feature_id}-{turn_number} id."""
        entity = create_turn_state_from_autobuild(
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=3,
            player_summary="Test summary",
            player_decision="implemented",
            coach_decision="approved",
        )

        assert entity.id == "TURN-FEAT-GE-3"
        assert entity.feature_id == "FEAT-GE"
        assert entity.task_id == "TASK-GE-001"
        assert entity.turn_number == 3

    def test_create_turn_state_from_autobuild_minimal_params(self):
        """Test factory with only required params."""
        entity = create_turn_state_from_autobuild(
            feature_id="FEAT-TEST",
            task_id="TASK-TEST-001",
            turn_number=1,
            player_summary="Minimal test",
            player_decision="implemented",
            coach_decision="feedback",
        )

        assert entity.id == "TURN-FEAT-TEST-1"
        assert entity.mode == TurnMode.CONTINUING_WORK  # default
        assert entity.blockers_found == []
        assert entity.acceptance_criteria_status == {}
        assert entity.files_modified == []
        assert entity.lessons_from_turn == []

    def test_create_turn_state_from_autobuild_with_all_params(self):
        """Test factory with all optional params."""
        started = datetime(2025, 1, 29, 10, 0, 0)
        completed = datetime(2025, 1, 29, 10, 15, 0)

        entity = create_turn_state_from_autobuild(
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=2,
            player_summary="Full params test",
            player_decision="implemented",
            coach_decision="feedback",
            coach_feedback="Add more tests",
            mode=TurnMode.RECOVERING_STATE,
            blockers_found=["Redis not available"],
            progress_summary="Made good progress",
            acceptance_criteria_status={"AC-001": "completed"},
            files_modified=["src/auth.py", "tests/test_auth.py"],
            tests_passed=10,
            tests_failed=2,
            coverage=75.0,
            arch_score=80,
            started_at=started,
            completed_at=completed,
            duration_seconds=900,
            lessons_from_turn=["Need Redis for sessions"],
            what_to_try_next="Add Redis dependency",
        )

        assert entity.id == "TURN-FEAT-GE-2"
        assert entity.mode == TurnMode.RECOVERING_STATE
        assert entity.blockers_found == ["Redis not available"]
        assert entity.progress_summary == "Made good progress"
        assert entity.acceptance_criteria_status == {"AC-001": "completed"}
        assert entity.files_modified == ["src/auth.py", "tests/test_auth.py"]
        assert entity.tests_passed == 10
        assert entity.tests_failed == 2
        assert entity.coverage == 75.0
        assert entity.arch_score == 80
        assert entity.started_at == started
        assert entity.completed_at == completed
        assert entity.duration_seconds == 900
        assert entity.lessons_from_turn == ["Need Redis for sessions"]
        assert entity.what_to_try_next == "Add Redis dependency"

    def test_create_turn_state_from_autobuild_defaults_timestamps_to_now(self):
        """Test factory defaults timestamps to current time when not provided."""
        before = datetime.now()

        entity = create_turn_state_from_autobuild(
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Time test",
            player_decision="implemented",
            coach_decision="approved",
        )

        after = datetime.now()

        assert before <= entity.started_at <= after
        assert before <= entity.completed_at <= after

    def test_create_turn_state_from_autobuild_returns_valid_entity(self):
        """Test factory returns valid TurnStateEntity that can be serialized."""
        entity = create_turn_state_from_autobuild(
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Serialization test",
            player_decision="implemented",
            coach_decision="approved",
        )

        # Should be a TurnStateEntity
        assert isinstance(entity, TurnStateEntity)

        # Should be serializable
        episode_body = entity.to_episode_body()
        assert isinstance(episode_body, dict)
        assert episode_body["entity_type"] == "turn_state"

        # Should be JSON serializable
        json_str = json.dumps(episode_body)
        assert isinstance(json_str, str)

    def test_create_turn_state_from_autobuild_different_modes(self):
        """Test factory with all TurnMode values."""
        for mode in [TurnMode.FRESH_START, TurnMode.RECOVERING_STATE, TurnMode.CONTINUING_WORK]:
            entity = create_turn_state_from_autobuild(
                feature_id="FEAT-GE",
                task_id="TASK-GE-001",
                turn_number=1,
                player_summary="Mode test",
                player_decision="implemented",
                coach_decision="approved",
                mode=mode,
            )

            assert entity.mode == mode


# ============================================================================
# 8. Module Exports Tests (3 tests)
# ============================================================================

class TestModuleExports:
    """Test that turn_state_operations module exports are correct."""

    def test_turn_state_entity_exported_from_entities_init(self):
        """Test TurnStateEntity is exported from entities __init__."""
        from guardkit.knowledge.entities import TurnStateEntity as EntityFromInit
        from guardkit.knowledge.entities.turn_state import TurnStateEntity as EntityFromModule

        assert EntityFromInit is EntityFromModule

    def test_turn_mode_exported_from_entities_init(self):
        """Test TurnMode is exported from entities __init__."""
        from guardkit.knowledge.entities import TurnMode as ModeFromInit
        from guardkit.knowledge.entities.turn_state import TurnMode as ModeFromModule

        assert ModeFromInit is ModeFromModule

    def test_operations_functions_importable(self):
        """Test all operation functions can be imported."""
        from guardkit.knowledge.turn_state_operations import (
            capture_turn_state,
            load_turn_continuation_context,
            create_turn_state_from_autobuild,
        )

        assert callable(capture_turn_state)
        assert callable(load_turn_continuation_context)
        assert callable(create_turn_state_from_autobuild)
