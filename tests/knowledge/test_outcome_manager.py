"""
TDD RED Phase: Tests for guardkit.knowledge.outcome_manager

These tests are written to FAIL initially (RED phase of TDD).
Implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- OutcomeType enum values and validation
- TaskOutcome dataclass creation and defaults
- TaskOutcome.to_episode_body() serialization
- capture_task_outcome() with mocked Graphiti client
- capture_task_outcome() graceful degradation when disabled
- find_similar_task_outcomes() search functionality
- ID generation format (OUT-XXXXXXXX)
- Error handling and graceful degradation
- Edge cases (empty fields, missing data, invalid inputs)

Coverage Target: >=80%
Test Count: 40+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, List
from datetime import datetime
import json

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.entities.outcome import (
        OutcomeType,
        TaskOutcome,
    )
    from guardkit.knowledge.outcome_manager import (
        capture_task_outcome,
        OutcomeManager,
    )
    from guardkit.knowledge.outcome_queries import (
        OutcomeQueries,
        find_similar_task_outcomes,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


# ============================================================================
# 1. OutcomeType Enum Tests (6 tests)
# ============================================================================

class TestOutcomeTypeEnum:
    """Test OutcomeType enum values and validation."""

    def test_outcome_type_enum_exists(self):
        """Test OutcomeType enum is defined."""
        assert OutcomeType is not None

    def test_outcome_type_task_completed(self):
        """Test TASK_COMPLETED enum value."""
        assert OutcomeType.TASK_COMPLETED is not None
        assert OutcomeType.TASK_COMPLETED.value == "TASK_COMPLETED"

    def test_outcome_type_task_failed(self):
        """Test TASK_FAILED enum value."""
        assert OutcomeType.TASK_FAILED is not None
        assert OutcomeType.TASK_FAILED.value == "TASK_FAILED"

    def test_outcome_type_review_passed(self):
        """Test REVIEW_PASSED enum value."""
        assert OutcomeType.REVIEW_PASSED is not None
        assert OutcomeType.REVIEW_PASSED.value == "REVIEW_PASSED"

    def test_outcome_type_review_failed(self):
        """Test REVIEW_FAILED enum value."""
        assert OutcomeType.REVIEW_FAILED is not None
        assert OutcomeType.REVIEW_FAILED.value == "REVIEW_FAILED"

    def test_outcome_type_pattern_success(self):
        """Test PATTERN_SUCCESS enum value."""
        assert OutcomeType.PATTERN_SUCCESS is not None
        assert OutcomeType.PATTERN_SUCCESS.value == "PATTERN_SUCCESS"

    def test_outcome_type_pattern_failure(self):
        """Test PATTERN_FAILURE enum value."""
        assert OutcomeType.PATTERN_FAILURE is not None
        assert OutcomeType.PATTERN_FAILURE.value == "PATTERN_FAILURE"


# ============================================================================
# 2. TaskOutcome Dataclass Tests (12 tests)
# ============================================================================

class TestTaskOutcomeDataclass:
    """Test TaskOutcome dataclass creation and defaults."""

    def test_task_outcome_creation_minimal(self):
        """Test creating TaskOutcome with minimal required fields."""
        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test Task",
            task_requirements="Implement feature X",
            success=True,
            summary="Task completed successfully"
        )

        assert outcome.id == "OUT-a1b2c3d4"
        assert outcome.outcome_type == OutcomeType.TASK_COMPLETED
        assert outcome.task_id == "TASK-1234"
        assert outcome.task_title == "Test Task"
        assert outcome.task_requirements == "Implement feature X"
        assert outcome.success is True
        assert outcome.summary == "Task completed successfully"

    def test_task_outcome_creation_complete(self):
        """Test creating TaskOutcome with all fields."""
        started = datetime(2025, 1, 1, 10, 0, 0)
        completed = datetime(2025, 1, 1, 12, 30, 0)

        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Implement OAuth2",
            task_requirements="Add OAuth2 authentication with PKCE",
            success=True,
            summary="OAuth2 implemented successfully with all tests passing",
            approach_used="Used standard OAuth2 library with custom PKCE implementation",
            patterns_used=["Strategy Pattern", "Factory Pattern"],
            problems_encountered=["CORS issues", "Token refresh race condition"],
            lessons_learned=["Always validate redirect URIs", "Use exponential backoff"],
            tests_written=15,
            test_coverage=92.5,
            review_cycles=2,
            started_at=started,
            completed_at=completed,
            duration_minutes=150,
            feature_id="FEAT-AUTH",
            related_adr_ids=["ADR-001", "ADR-002"]
        )

        assert outcome.id == "OUT-a1b2c3d4"
        assert outcome.approach_used == "Used standard OAuth2 library with custom PKCE implementation"
        assert outcome.patterns_used == ["Strategy Pattern", "Factory Pattern"]
        assert outcome.problems_encountered == ["CORS issues", "Token refresh race condition"]
        assert outcome.lessons_learned == ["Always validate redirect URIs", "Use exponential backoff"]
        assert outcome.tests_written == 15
        assert outcome.test_coverage == 92.5
        assert outcome.review_cycles == 2
        assert outcome.started_at == started
        assert outcome.completed_at == completed
        assert outcome.duration_minutes == 150
        assert outcome.feature_id == "FEAT-AUTH"
        assert outcome.related_adr_ids == ["ADR-001", "ADR-002"]

    def test_task_outcome_default_values(self):
        """Test TaskOutcome default values for optional fields."""
        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test Task",
            task_requirements="Requirements",
            success=True,
            summary="Summary"
        )

        # Optional fields should have sensible defaults
        assert outcome.approach_used is None or outcome.approach_used == ""
        assert outcome.patterns_used is None or outcome.patterns_used == []
        assert outcome.problems_encountered is None or outcome.problems_encountered == []
        assert outcome.lessons_learned is None or outcome.lessons_learned == []
        assert outcome.tests_written is None or outcome.tests_written == 0
        assert outcome.test_coverage is None or outcome.test_coverage == 0.0
        assert outcome.review_cycles is None or outcome.review_cycles == 0
        assert outcome.feature_id is None or outcome.feature_id == ""
        assert outcome.related_adr_ids is None or outcome.related_adr_ids == []

    def test_task_outcome_failed_task(self):
        """Test creating TaskOutcome for a failed task."""
        outcome = TaskOutcome(
            id="OUT-f1a2b3c4",
            outcome_type=OutcomeType.TASK_FAILED,
            task_id="TASK-5678",
            task_title="Failed Task",
            task_requirements="Implement feature Y",
            success=False,
            summary="Task failed due to architectural issues"
        )

        assert outcome.success is False
        assert outcome.outcome_type == OutcomeType.TASK_FAILED

    def test_task_outcome_review_passed(self):
        """Test creating TaskOutcome for a passed review."""
        outcome = TaskOutcome(
            id="OUT-r1e2v3i4",
            outcome_type=OutcomeType.REVIEW_PASSED,
            task_id="TASK-9999",
            task_title="Code Review",
            task_requirements="Review authentication module",
            success=True,
            summary="Code review passed with minor suggestions"
        )

        assert outcome.outcome_type == OutcomeType.REVIEW_PASSED
        assert outcome.success is True

    def test_task_outcome_id_format(self):
        """Test TaskOutcome ID format validation (OUT-XXXXXXXX)."""
        outcome = TaskOutcome(
            id="OUT-12345678",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test",
            task_requirements="Test",
            success=True,
            summary="Test"
        )

        assert outcome.id.startswith("OUT-")
        assert len(outcome.id) == 12  # OUT- + 8 chars

    def test_task_outcome_duration_calculation(self):
        """Test duration_minutes is correctly set."""
        started = datetime(2025, 1, 1, 10, 0, 0)
        completed = datetime(2025, 1, 1, 12, 30, 0)

        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test",
            task_requirements="Test",
            success=True,
            summary="Test",
            started_at=started,
            completed_at=completed,
            duration_minutes=150
        )

        assert outcome.duration_minutes == 150

    def test_task_outcome_with_empty_lists(self):
        """Test TaskOutcome with empty lists for optional fields."""
        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test",
            task_requirements="Test",
            success=True,
            summary="Test",
            patterns_used=[],
            problems_encountered=[],
            lessons_learned=[],
            related_adr_ids=[]
        )

        assert outcome.patterns_used == []
        assert outcome.problems_encountered == []
        assert outcome.lessons_learned == []
        assert outcome.related_adr_ids == []

    def test_task_outcome_with_zero_metrics(self):
        """Test TaskOutcome with zero values for metrics."""
        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test",
            task_requirements="Test",
            success=True,
            summary="Test",
            tests_written=0,
            test_coverage=0.0,
            review_cycles=0,
            duration_minutes=0
        )

        assert outcome.tests_written == 0
        assert outcome.test_coverage == 0.0
        assert outcome.review_cycles == 0
        assert outcome.duration_minutes == 0


# ============================================================================
# 3. TaskOutcome.to_episode_body() Tests (8 tests)
# ============================================================================

class TestTaskOutcomeEpisodeSerialization:
    """Test TaskOutcome.to_episode_body() serialization."""

    def test_to_episode_body_basic(self):
        """Test basic serialization to episode body."""
        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test Task",
            task_requirements="Requirements",
            success=True,
            summary="Summary"
        )

        episode_body = outcome.to_episode_body()

        assert isinstance(episode_body, str)
        assert len(episode_body) > 0
        assert "OUT-a1b2c3d4" in episode_body
        assert "TASK-1234" in episode_body
        assert "Test Task" in episode_body

    def test_to_episode_body_contains_all_fields(self):
        """Test serialization includes all populated fields."""
        started = datetime(2025, 1, 1, 10, 0, 0)
        completed = datetime(2025, 1, 1, 12, 30, 0)

        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="OAuth2 Implementation",
            task_requirements="Add OAuth2 with PKCE",
            success=True,
            summary="Successfully implemented",
            approach_used="Used standard OAuth2 library",
            patterns_used=["Strategy Pattern"],
            problems_encountered=["CORS issues"],
            lessons_learned=["Validate redirect URIs"],
            tests_written=15,
            test_coverage=92.5,
            review_cycles=2,
            started_at=started,
            completed_at=completed,
            duration_minutes=150,
            feature_id="FEAT-AUTH",
            related_adr_ids=["ADR-001"]
        )

        episode_body = outcome.to_episode_body()

        # Check all fields are present
        assert "OAuth2 Implementation" in episode_body
        assert "Add OAuth2 with PKCE" in episode_body
        assert "Used standard OAuth2 library" in episode_body
        assert "Strategy Pattern" in episode_body
        assert "CORS issues" in episode_body
        assert "Validate redirect URIs" in episode_body
        assert "15" in episode_body or "tests_written: 15" in episode_body
        assert "92.5" in episode_body or "test_coverage: 92.5" in episode_body
        assert "FEAT-AUTH" in episode_body
        assert "ADR-001" in episode_body

    def test_to_episode_body_format(self):
        """Test episode body format is human-readable."""
        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test Task",
            task_requirements="Requirements",
            success=True,
            summary="Summary"
        )

        episode_body = outcome.to_episode_body()

        # Should be structured text (not just JSON dump)
        assert "\n" in episode_body  # Has line breaks
        # Should contain field labels
        assert any(label in episode_body.lower() for label in ["task", "outcome", "summary"])

    def test_to_episode_body_handles_none_values(self):
        """Test serialization handles None values gracefully."""
        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test Task",
            task_requirements="Requirements",
            success=True,
            summary="Summary",
            approach_used=None,
            patterns_used=None,
            problems_encountered=None,
            lessons_learned=None,
            feature_id=None,
            related_adr_ids=None
        )

        episode_body = outcome.to_episode_body()

        # Should not crash and should produce valid output
        assert isinstance(episode_body, str)
        assert len(episode_body) > 0

    def test_to_episode_body_handles_empty_lists(self):
        """Test serialization handles empty lists."""
        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test Task",
            task_requirements="Requirements",
            success=True,
            summary="Summary",
            patterns_used=[],
            problems_encountered=[],
            lessons_learned=[],
            related_adr_ids=[]
        )

        episode_body = outcome.to_episode_body()

        assert isinstance(episode_body, str)
        assert len(episode_body) > 0

    def test_to_episode_body_includes_timestamps(self):
        """Test serialization includes timestamp information."""
        started = datetime(2025, 1, 1, 10, 0, 0)
        completed = datetime(2025, 1, 1, 12, 30, 0)

        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test Task",
            task_requirements="Requirements",
            success=True,
            summary="Summary",
            started_at=started,
            completed_at=completed,
            duration_minutes=150
        )

        episode_body = outcome.to_episode_body()

        # Should include timestamp information
        assert "2025" in episode_body or "150" in episode_body

    def test_to_episode_body_success_false(self):
        """Test serialization for failed outcomes."""
        outcome = TaskOutcome(
            id="OUT-f1a2b3c4",
            outcome_type=OutcomeType.TASK_FAILED,
            task_id="TASK-1234",
            task_title="Failed Task",
            task_requirements="Requirements",
            success=False,
            summary="Task failed"
        )

        episode_body = outcome.to_episode_body()

        assert "failed" in episode_body.lower() or "success: false" in episode_body.lower()

    def test_to_episode_body_special_characters(self):
        """Test serialization handles special characters."""
        outcome = TaskOutcome(
            id="OUT-a1b2c3d4",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Test with \"quotes\" and 'apostrophes'",
            task_requirements="Requirements with <tags> & symbols",
            success=True,
            summary="Summary with\nnewlines\tand\ttabs"
        )

        episode_body = outcome.to_episode_body()

        # Should handle special characters without crashing
        assert isinstance(episode_body, str)
        assert len(episode_body) > 0


# ============================================================================
# 4. capture_task_outcome() Tests (10 tests)
# ============================================================================

class TestCaptureTaskOutcome:
    """Test capture_task_outcome() function."""

    @pytest.mark.asyncio
    async def test_capture_task_outcome_success(self):
        """Test successful outcome capture with Graphiti enabled."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test Task",
                task_requirements="Requirements",
                success=True,
                summary="Summary"
            )

            assert outcome_id is not None
            assert outcome_id.startswith("OUT-")
            assert len(outcome_id) == 12
            mock_client.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_task_outcome_generates_unique_id(self):
        """Test that each capture generates a unique outcome ID."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id1 = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Task 1",
                task_requirements="Req 1",
                success=True,
                summary="Summary 1"
            )

            outcome_id2 = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-5678",
                task_title="Task 2",
                task_requirements="Req 2",
                success=True,
                summary="Summary 2"
            )

            assert outcome_id1 != outcome_id2
            assert outcome_id1.startswith("OUT-")
            assert outcome_id2.startswith("OUT-")

    @pytest.mark.asyncio
    async def test_capture_task_outcome_with_all_fields(self):
        """Test capture with all optional fields populated."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        started = datetime(2025, 1, 1, 10, 0, 0)
        completed = datetime(2025, 1, 1, 12, 30, 0)

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="OAuth2 Implementation",
                task_requirements="Add OAuth2",
                success=True,
                summary="Implemented successfully",
                approach_used="Standard library",
                patterns_used=["Strategy"],
                problems_encountered=["CORS"],
                lessons_learned=["Validate URIs"],
                tests_written=15,
                test_coverage=92.5,
                review_cycles=2,
                started_at=started,
                completed_at=completed,
                duration_minutes=150,
                feature_id="FEAT-AUTH",
                related_adr_ids=["ADR-001"]
            )

            assert outcome_id is not None
            mock_client.add_episode.assert_called_once()

            # Verify episode body was constructed correctly
            call_args = mock_client.add_episode.call_args
            episode_body = call_args[1]['episode_body']
            assert "OAuth2 Implementation" in episode_body
            assert "Standard library" in episode_body

    @pytest.mark.asyncio
    async def test_capture_task_outcome_graphiti_disabled(self):
        """Test graceful degradation when Graphiti disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test Task",
                task_requirements="Requirements",
                success=True,
                summary="Summary"
            )

            # Should still generate ID but not call add_episode
            assert outcome_id is not None
            assert outcome_id.startswith("OUT-")
            mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_capture_task_outcome_graphiti_none(self):
        """Test graceful degradation when Graphiti client is None."""
        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=None):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test Task",
                task_requirements="Requirements",
                success=True,
                summary="Summary"
            )

            # Should still generate ID
            assert outcome_id is not None
            assert outcome_id.startswith("OUT-")

    @pytest.mark.asyncio
    async def test_capture_task_outcome_graphiti_error(self):
        """Test graceful degradation when Graphiti raises error."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("Graphiti error"))

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test Task",
                task_requirements="Requirements",
                success=True,
                summary="Summary"
            )

            # Should handle error gracefully and still return ID
            assert outcome_id is not None
            assert outcome_id.startswith("OUT-")

    @pytest.mark.asyncio
    async def test_capture_task_outcome_episode_name_format(self):
        """Test that episode name is correctly formatted."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test Task",
                task_requirements="Requirements",
                success=True,
                summary="Summary"
            )

            call_args = mock_client.add_episode.call_args
            episode_name = call_args[1]['name']

            # Episode name should include outcome ID and task info
            assert "OUT-" in episode_name
            assert "TASK-1234" in episode_name or "Test Task" in episode_name

    @pytest.mark.asyncio
    async def test_capture_task_outcome_group_id(self):
        """Test that correct group_id is used for episode."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test Task",
                task_requirements="Requirements",
                success=True,
                summary="Summary"
            )

            call_args = mock_client.add_episode.call_args
            group_id = call_args[1]['group_id']

            # Should use a task outcomes group
            assert "task" in group_id.lower() or "outcome" in group_id.lower()

    @pytest.mark.asyncio
    async def test_capture_task_outcome_failed_task(self):
        """Test capturing outcome for a failed task."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_FAILED,
                task_id="TASK-1234",
                task_title="Failed Task",
                task_requirements="Requirements",
                success=False,
                summary="Task failed due to X"
            )

            assert outcome_id is not None
            mock_client.add_episode.assert_called_once()

            # Episode should reflect failure
            call_args = mock_client.add_episode.call_args
            episode_body = call_args[1]['episode_body']
            assert "failed" in episode_body.lower() or "success: false" in episode_body.lower()

    @pytest.mark.asyncio
    async def test_capture_task_outcome_return_value(self):
        """Test that capture returns the generated outcome ID."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test Task",
                task_requirements="Requirements",
                success=True,
                summary="Summary"
            )

            # Should return the outcome ID (not episode ID)
            assert outcome_id.startswith("OUT-")
            assert outcome_id != "episode_123"


# ============================================================================
# 5. find_similar_task_outcomes() Tests (8 tests)
# ============================================================================

class TestFindSimilarTaskOutcomes:
    """Test find_similar_task_outcomes() search functionality."""

    @pytest.mark.asyncio
    async def test_find_similar_task_outcomes_basic(self):
        """Test basic semantic search for similar outcomes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"id": "1", "content": "OAuth2 implementation", "score": 0.95},
            {"id": "2", "content": "Authentication setup", "score": 0.87},
        ])

        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=mock_client):
            results = await find_similar_task_outcomes(
                task_requirements="Implement OAuth2 authentication",
                limit=5
            )

            assert isinstance(results, list)
            assert len(results) <= 5
            mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_similar_task_outcomes_with_limit(self):
        """Test search respects limit parameter."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"id": str(i), "content": f"Result {i}", "score": 0.9 - i*0.1}
            for i in range(10)
        ])

        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=mock_client):
            results = await find_similar_task_outcomes(
                task_requirements="Test query",
                limit=3
            )

            # Should only return 3 results
            assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_find_similar_task_outcomes_graphiti_disabled(self):
        """Test graceful degradation when Graphiti disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=mock_client):
            results = await find_similar_task_outcomes(
                task_requirements="Test query",
                limit=5
            )

            # Should return empty list
            assert results == []
            mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_similar_task_outcomes_graphiti_none(self):
        """Test graceful degradation when Graphiti client is None."""
        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=None):
            results = await find_similar_task_outcomes(
                task_requirements="Test query",
                limit=5
            )

            # Should return empty list
            assert results == []

    @pytest.mark.asyncio
    async def test_find_similar_task_outcomes_empty_query(self):
        """Test search with empty query string."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=mock_client):
            results = await find_similar_task_outcomes(
                task_requirements="",
                limit=5
            )

            # Should handle empty query gracefully
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_find_similar_task_outcomes_no_results(self):
        """Test search when no similar outcomes found."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=mock_client):
            results = await find_similar_task_outcomes(
                task_requirements="Very unique task requirements",
                limit=5
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_find_similar_task_outcomes_search_error(self):
        """Test graceful degradation when search raises error."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(side_effect=Exception("Search error"))

        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=mock_client):
            results = await find_similar_task_outcomes(
                task_requirements="Test query",
                limit=5
            )

            # Should handle error gracefully
            assert results == []

    @pytest.mark.asyncio
    async def test_find_similar_task_outcomes_group_id(self):
        """Test that search uses correct group_id."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=mock_client):
            await find_similar_task_outcomes(
                task_requirements="Test query",
                limit=5
            )

            call_args = mock_client.search.call_args
            group_ids = call_args[1]['group_ids']

            # Should search in task outcomes group
            assert isinstance(group_ids, list)
            assert any("task" in g.lower() or "outcome" in g.lower() for g in group_ids)


# ============================================================================
# 6. OutcomeManager Class Tests (Optional - if class-based API exists)
# ============================================================================

class TestOutcomeManagerClass:
    """Test OutcomeManager class if it exists."""

    def test_outcome_manager_exists(self):
        """Test OutcomeManager class is defined."""
        # This test will fail if OutcomeManager is not implemented as a class
        # but succeeds if it's implemented as module-level functions
        try:
            assert OutcomeManager is not None
        except NameError:
            # If OutcomeManager doesn't exist as a class, that's okay
            # (implementation may use module-level functions instead)
            pytest.skip("OutcomeManager not implemented as class (using functions)")


# ============================================================================
# 7. Edge Cases and Error Handling (6 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_capture_outcome_with_very_long_summary(self):
        """Test capture with very long summary text."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        long_summary = "x" * 10000  # 10,000 characters

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test",
                task_requirements="Test",
                success=True,
                summary=long_summary
            )

            # Should handle long text without issues
            assert outcome_id is not None

    @pytest.mark.asyncio
    async def test_capture_outcome_with_many_patterns(self):
        """Test capture with many patterns used."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        many_patterns = [f"Pattern {i}" for i in range(100)]

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test",
                task_requirements="Test",
                success=True,
                summary="Test",
                patterns_used=many_patterns
            )

            assert outcome_id is not None

    @pytest.mark.asyncio
    async def test_capture_outcome_with_unicode_characters(self):
        """Test capture with Unicode characters."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.outcome_manager.get_graphiti', return_value=mock_client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-1234",
                task_title="Test with 中文 and émojis 🎉",
                task_requirements="Requirements with Ñoño",
                success=True,
                summary="Summary with Ελληνικά"
            )

            assert outcome_id is not None

    @pytest.mark.asyncio
    async def test_find_outcomes_with_zero_limit(self):
        """Test search with limit of 0."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=mock_client):
            results = await find_similar_task_outcomes(
                task_requirements="Test",
                limit=0
            )

            # Should handle zero limit gracefully
            assert results == []

    @pytest.mark.asyncio
    async def test_find_outcomes_with_large_limit(self):
        """Test search with very large limit."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"id": str(i), "content": f"Result {i}", "score": 0.9}
            for i in range(50)
        ])

        with patch('guardkit.knowledge.outcome_queries.get_graphiti', return_value=mock_client):
            results = await find_similar_task_outcomes(
                task_requirements="Test",
                limit=1000
            )

            # Should handle large limit
            assert isinstance(results, list)

    def test_outcome_type_enum_membership(self):
        """Test OutcomeType enum membership checks."""
        assert OutcomeType.TASK_COMPLETED in OutcomeType
        assert OutcomeType.TASK_FAILED in OutcomeType
        assert OutcomeType.REVIEW_PASSED in OutcomeType
        assert OutcomeType.REVIEW_FAILED in OutcomeType
        assert OutcomeType.PATTERN_SUCCESS in OutcomeType
        assert OutcomeType.PATTERN_FAILURE in OutcomeType
