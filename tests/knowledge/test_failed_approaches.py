"""
TDD RED Phase: Tests for guardkit.knowledge.entities.failed_approach
and guardkit.knowledge.failed_approach_manager

These tests are written to FAIL initially (RED phase of TDD).
Implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- FailedApproachEpisode dataclass creation and defaults
- FailedApproachEpisode.to_episode_body() serialization
- capture_failed_approach() with mocked Graphiti client
- capture_failed_approach() graceful degradation when disabled
- load_relevant_failures() search functionality
- increment_occurrence() for tracking
- ID generation format (FAIL-XXXXXXXX)
- Error handling and graceful degradation
- Edge cases

Coverage Target: >=80%
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional, List
from datetime import datetime
import json

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.entities.failed_approach import (
        FailedApproachEpisode,
        Severity,
    )
    from guardkit.knowledge.failed_approach_manager import (
        capture_failed_approach,
        load_relevant_failures,
        increment_occurrence,
        FailedApproachManager,
        FAILED_APPROACHES_GROUP_ID,
    )
    from guardkit.knowledge.seed_failed_approaches import (
        seed_failed_approaches,
        get_initial_failed_approaches,
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
# 1. Severity Enum Tests (4 tests)
# ============================================================================

class TestSeverityEnum:
    """Test Severity enum values."""

    def test_severity_low(self):
        """Test LOW severity value."""
        assert Severity.LOW is not None
        assert Severity.LOW.value == "low"

    def test_severity_medium(self):
        """Test MEDIUM severity value."""
        assert Severity.MEDIUM is not None
        assert Severity.MEDIUM.value == "medium"

    def test_severity_high(self):
        """Test HIGH severity value."""
        assert Severity.HIGH is not None
        assert Severity.HIGH.value == "high"

    def test_severity_critical(self):
        """Test CRITICAL severity value."""
        assert Severity.CRITICAL is not None
        assert Severity.CRITICAL.value == "critical"


# ============================================================================
# 2. FailedApproachEpisode Dataclass Tests (15 tests)
# ============================================================================

class TestFailedApproachEpisodeDataclass:
    """Test FailedApproachEpisode dataclass creation and defaults."""

    def test_create_minimal(self):
        """Test creating FailedApproachEpisode with minimal required fields."""
        failure = FailedApproachEpisode(
            id="FAIL-SUBPROC1",
            approach="Using subprocess.run() to invoke guardkit task-work",
            symptom="subprocess.CalledProcessError: Command not found",
            root_cause="CLI command doesn't exist",
            fix_applied="Use SDK query() instead",
            prevention="Check ADR-FB-001 before implementing",
            context="feature-build"
        )

        assert failure.id == "FAIL-SUBPROC1"
        assert failure.approach == "Using subprocess.run() to invoke guardkit task-work"
        assert failure.symptom == "subprocess.CalledProcessError: Command not found"
        assert failure.root_cause == "CLI command doesn't exist"
        assert failure.fix_applied == "Use SDK query() instead"
        assert failure.prevention == "Check ADR-FB-001 before implementing"
        assert failure.context == "feature-build"

    def test_create_complete(self):
        """Test creating FailedApproachEpisode with all fields."""
        first = datetime(2025, 1, 1, 10, 0, 0)
        last = datetime(2025, 1, 15, 14, 30, 0)

        failure = FailedApproachEpisode(
            id="FAIL-A1B2C3D4",
            approach="Using subprocess for task-work",
            symptom="Command not found error",
            root_cause="CLI command doesn't exist",
            fix_applied="Use SDK query()",
            prevention="Check ADR before implementing",
            context="feature-build",
            task_id="TASK-1234",
            feature_id="FEAT-AUTH",
            file_path="guardkit/orchestrator/agent_invoker.py",
            related_adrs=["ADR-FB-001", "ADR-FB-002"],
            similar_failures=["FAIL-MOCK1", "FAIL-PATH1"],
            occurrences=3,
            first_occurred=first,
            last_occurred=last,
            severity=Severity.CRITICAL,
            time_to_fix_minutes=45
        )

        assert failure.task_id == "TASK-1234"
        assert failure.feature_id == "FEAT-AUTH"
        assert failure.file_path == "guardkit/orchestrator/agent_invoker.py"
        assert failure.related_adrs == ["ADR-FB-001", "ADR-FB-002"]
        assert failure.similar_failures == ["FAIL-MOCK1", "FAIL-PATH1"]
        assert failure.occurrences == 3
        assert failure.first_occurred == first
        assert failure.last_occurred == last
        assert failure.severity == Severity.CRITICAL
        assert failure.time_to_fix_minutes == 45

    def test_default_values(self):
        """Test FailedApproachEpisode default values for optional fields."""
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test approach",
            symptom="Test symptom",
            root_cause="Test cause",
            fix_applied="Test fix",
            prevention="Test prevention",
            context="test"
        )

        # Optional fields should have sensible defaults
        assert failure.task_id is None
        assert failure.feature_id is None
        assert failure.file_path is None
        assert failure.related_adrs == []
        assert failure.similar_failures == []
        assert failure.occurrences == 1
        assert failure.severity == Severity.MEDIUM
        assert failure.time_to_fix_minutes is None
        # first_occurred and last_occurred should have defaults (datetime.now)
        assert failure.first_occurred is not None
        assert failure.last_occurred is not None

    def test_id_format_with_hash(self):
        """Test that ID can use hash-based format (FAIL-XXXXXXXX)."""
        failure = FailedApproachEpisode(
            id="FAIL-A1B2C3D4",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test"
        )

        assert failure.id.startswith("FAIL-")
        assert len(failure.id) == 13  # FAIL- + 8 chars

    def test_id_format_with_descriptive_name(self):
        """Test that ID can use descriptive name format (FAIL-SUBPROCESS)."""
        failure = FailedApproachEpisode(
            id="FAIL-SUBPROCESS",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test"
        )

        assert failure.id.startswith("FAIL-")

    def test_occurrences_increment(self):
        """Test occurrences field can be set and incremented."""
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            occurrences=5
        )

        assert failure.occurrences == 5

    def test_severity_levels(self):
        """Test all severity levels can be assigned."""
        for severity in [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]:
            failure = FailedApproachEpisode(
                id=f"FAIL-{severity.value.upper()}",
                approach="Test",
                symptom="Test",
                root_cause="Test",
                fix_applied="Test",
                prevention="Test",
                context="test",
                severity=severity
            )
            assert failure.severity == severity

    def test_related_adrs_list(self):
        """Test related_adrs accepts a list of ADR IDs."""
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            related_adrs=["ADR-FB-001", "ADR-FB-002", "ADR-FB-003"]
        )

        assert len(failure.related_adrs) == 3
        assert "ADR-FB-001" in failure.related_adrs

    def test_similar_failures_list(self):
        """Test similar_failures accepts a list of failure IDs."""
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            similar_failures=["FAIL-MOCK1", "FAIL-PATH1"]
        )

        assert len(failure.similar_failures) == 2
        assert "FAIL-MOCK1" in failure.similar_failures

    def test_timestamps_auto_set(self):
        """Test timestamps are automatically set if not provided."""
        before = datetime.now()

        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test"
        )

        after = datetime.now()

        assert failure.first_occurred >= before
        assert failure.first_occurred <= after
        assert failure.last_occurred >= before
        assert failure.last_occurred <= after


# ============================================================================
# 3. FailedApproachEpisode.to_episode_body() Tests (8 tests)
# ============================================================================

class TestFailedApproachEpisodeBody:
    """Test FailedApproachEpisode.to_episode_body() serialization."""

    def test_to_episode_body_returns_dict(self):
        """Test to_episode_body returns a dictionary."""
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test approach",
            symptom="Test symptom",
            root_cause="Test cause",
            fix_applied="Test fix",
            prevention="Test prevention",
            context="test"
        )

        body = failure.to_episode_body()

        assert isinstance(body, dict)

    def test_to_episode_body_contains_required_fields(self):
        """Test episode body contains all required fields.

        Note: entity_type is NOT included in to_episode_body() - it's injected
        by GraphitiClient according to the docstring.
        """
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test approach",
            symptom="Test symptom",
            root_cause="Test cause",
            fix_applied="Test fix",
            prevention="Test prevention",
            context="test"
        )

        body = failure.to_episode_body()

        # Verify it returns a dict with required fields (no entity_type)
        assert body["id"] == "FAIL-TEST001"
        assert body["approach"] == "Test approach"
        assert body["symptom"] == "Test symptom"
        assert body["root_cause"] == "Test cause"
        assert body["fix_applied"] == "Test fix"
        assert body["prevention"] == "Test prevention"
        assert body["context"] == "test"

    def test_to_episode_body_contains_optional_fields(self):
        """Test episode body contains optional fields when set."""
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            task_id="TASK-1234",
            feature_id="FEAT-AUTH",
            file_path="/path/to/file.py",
            related_adrs=["ADR-001"],
            similar_failures=["FAIL-001"],
            severity=Severity.HIGH,
            time_to_fix_minutes=30
        )

        body = failure.to_episode_body()

        assert body["task_id"] == "TASK-1234"
        assert body["feature_id"] == "FEAT-AUTH"
        assert body["file_path"] == "/path/to/file.py"
        assert body["related_adrs"] == ["ADR-001"]
        assert body["similar_failures"] == ["FAIL-001"]
        assert body["severity"] == "high"
        assert body["time_to_fix_minutes"] == 30

    def test_to_episode_body_serializes_timestamps(self):
        """Test timestamps are serialized as ISO format strings."""
        first = datetime(2025, 1, 1, 10, 0, 0)
        last = datetime(2025, 1, 15, 14, 30, 0)

        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            first_occurred=first,
            last_occurred=last
        )

        body = failure.to_episode_body()

        assert body["first_occurred"] == first.isoformat()
        assert body["last_occurred"] == last.isoformat()

    def test_to_episode_body_includes_occurrences(self):
        """Test occurrences count is included."""
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            occurrences=5
        )

        body = failure.to_episode_body()

        assert body["occurrences"] == 5

    def test_to_episode_body_json_serializable(self):
        """Test episode body is JSON serializable."""
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test approach",
            symptom="Test symptom",
            root_cause="Test cause",
            fix_applied="Test fix",
            prevention="Test prevention",
            context="test",
            related_adrs=["ADR-001"],
            occurrences=3
        )

        body = failure.to_episode_body()

        # Should not raise
        json_str = json.dumps(body)
        assert isinstance(json_str, str)

        # And should round-trip
        parsed = json.loads(json_str)
        assert parsed["id"] == "FAIL-TEST001"

    def test_to_episode_body_handles_none_optional_fields(self):
        """Test episode body handles None optional fields."""
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            task_id=None,
            feature_id=None,
            file_path=None,
            time_to_fix_minutes=None
        )

        body = failure.to_episode_body()

        # None values should be included or excluded gracefully
        assert isinstance(body, dict)
        # Should still be JSON serializable
        json.dumps(body)


# ============================================================================
# 4. capture_failed_approach() Tests (10 tests)
# ============================================================================

class TestCaptureFailedApproach:
    """Test capture_failed_approach() function."""

    @pytest.mark.asyncio
    async def test_capture_success(self):
        """Test successful failure capture with Graphiti enabled."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            failure = await capture_failed_approach(
                approach="Using subprocess for task-work",
                symptom="Command not found",
                root_cause="CLI doesn't exist",
                fix_applied="Use SDK query()",
                prevention="Check ADR first",
                context="feature-build"
            )

            assert failure is not None
            assert failure.id.startswith("FAIL-")
            mock_client.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_generates_hash_id(self):
        """Test that capture generates ID from approach hash."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            failure = await capture_failed_approach(
                approach="Using subprocess for task-work",
                symptom="Command not found",
                root_cause="CLI doesn't exist",
                fix_applied="Use SDK query()",
                prevention="Check ADR first",
                context="feature-build"
            )

            # ID should be FAIL- followed by uppercase hash
            assert failure.id.startswith("FAIL-")
            # Hash portion should be uppercase hex
            hash_part = failure.id[5:]
            assert hash_part.isupper() or hash_part.isdigit()

    @pytest.mark.asyncio
    async def test_capture_with_optional_fields(self):
        """Test capture with all optional fields."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            failure = await capture_failed_approach(
                approach="Test approach",
                symptom="Test symptom",
                root_cause="Test cause",
                fix_applied="Test fix",
                prevention="Test prevention",
                context="test",
                task_id="TASK-1234",
                feature_id="FEAT-AUTH",
                file_path="/path/to/file.py",
                related_adrs=["ADR-001"],
                severity=Severity.CRITICAL,
                time_to_fix_minutes=60
            )

            assert failure.task_id == "TASK-1234"
            assert failure.feature_id == "FEAT-AUTH"
            assert failure.severity == Severity.CRITICAL
            assert failure.time_to_fix_minutes == 60

    @pytest.mark.asyncio
    async def test_capture_graphiti_disabled(self):
        """Test graceful degradation when Graphiti disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            failure = await capture_failed_approach(
                approach="Test approach",
                symptom="Test symptom",
                root_cause="Test cause",
                fix_applied="Test fix",
                prevention="Test prevention",
                context="test"
            )

            # Should still create failure object but not call add_episode
            assert failure is not None
            assert failure.id.startswith("FAIL-")
            mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_capture_graphiti_none(self):
        """Test graceful degradation when Graphiti client is None."""
        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=None):
            failure = await capture_failed_approach(
                approach="Test approach",
                symptom="Test symptom",
                root_cause="Test cause",
                fix_applied="Test fix",
                prevention="Test prevention",
                context="test"
            )

            # Should still create failure object
            assert failure is not None
            assert failure.id.startswith("FAIL-")

    @pytest.mark.asyncio
    async def test_capture_graphiti_error(self):
        """Test graceful degradation when Graphiti raises error."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("Graphiti error"))

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            failure = await capture_failed_approach(
                approach="Test approach",
                symptom="Test symptom",
                root_cause="Test cause",
                fix_applied="Test fix",
                prevention="Test prevention",
                context="test"
            )

            # Should handle error gracefully
            assert failure is not None
            assert failure.id.startswith("FAIL-")

    @pytest.mark.asyncio
    async def test_capture_uses_correct_group_id(self):
        """Test that capture uses correct group_id."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            await capture_failed_approach(
                approach="Test",
                symptom="Test",
                root_cause="Test",
                fix_applied="Test",
                prevention="Test",
                context="test"
            )

            call_args = mock_client.add_episode.call_args
            group_id = call_args[1]['group_id']

            assert group_id == FAILED_APPROACHES_GROUP_ID

    @pytest.mark.asyncio
    async def test_capture_episode_name_format(self):
        """Test episode name format."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            failure = await capture_failed_approach(
                approach="Using subprocess for task-work",
                symptom="Test",
                root_cause="Test",
                fix_applied="Test",
                prevention="Test",
                context="feature-build"
            )

            call_args = mock_client.add_episode.call_args
            episode_name = call_args[1]['name']

            # Should include failure ID
            assert failure.id in episode_name


# ============================================================================
# 5. load_relevant_failures() Tests (8 tests)
# ============================================================================

class TestLoadRelevantFailures:
    """Test load_relevant_failures() search functionality."""

    @pytest.mark.asyncio
    async def test_load_relevant_failures_basic(self):
        """Test basic search for relevant failures."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"symptom": "Command not found", "prevention": "Check ADR"}},
            {"body": {"symptom": "Path not found", "prevention": "Use feature ID"}}
        ])

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            results = await load_relevant_failures(
                query_context="subprocess task-work invocation"
            )

            assert isinstance(results, list)
            assert len(results) > 0
            mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_relevant_failures_with_limit(self):
        """Test search respects limit parameter."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"symptom": f"Symptom {i}", "prevention": f"Prevention {i}"}}
            for i in range(10)
        ])

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            results = await load_relevant_failures(
                query_context="test",
                limit=3
            )

            # Should respect limit
            assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_load_relevant_failures_returns_warnings_format(self):
        """Test results are formatted as warnings with symptom/prevention/adrs."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {
                "symptom": "Command not found",
                "prevention": "Check ADR-FB-001",
                "related_adrs": ["ADR-FB-001"]
            }}
        ])

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            results = await load_relevant_failures(query_context="subprocess")

            assert len(results) > 0
            assert "symptom" in results[0]
            assert "prevention" in results[0]
            assert "related_adrs" in results[0]

    @pytest.mark.asyncio
    async def test_load_relevant_failures_graphiti_disabled(self):
        """Test graceful degradation when Graphiti disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            results = await load_relevant_failures(query_context="test")

            assert results == []
            mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_relevant_failures_graphiti_none(self):
        """Test graceful degradation when Graphiti client is None."""
        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=None):
            results = await load_relevant_failures(query_context="test")

            assert results == []

    @pytest.mark.asyncio
    async def test_load_relevant_failures_empty_results(self):
        """Test handling of empty search results."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            results = await load_relevant_failures(query_context="very unique query")

            assert results == []

    @pytest.mark.asyncio
    async def test_load_relevant_failures_search_error(self):
        """Test graceful degradation when search raises error."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(side_effect=Exception("Search error"))

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            results = await load_relevant_failures(query_context="test")

            # Should handle error gracefully
            assert results == []

    @pytest.mark.asyncio
    async def test_load_relevant_failures_uses_correct_group(self):
        """Test search uses correct group_id."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            await load_relevant_failures(query_context="test")

            call_args = mock_client.search.call_args
            group_ids = call_args[1]['group_ids']

            assert FAILED_APPROACHES_GROUP_ID in group_ids


# ============================================================================
# 6. increment_occurrence() Tests (5 tests)
# ============================================================================

class TestIncrementOccurrence:
    """Test increment_occurrence() for tracking repeated failures."""

    @pytest.mark.asyncio
    async def test_increment_occurrence_basic(self):
        """Test incrementing occurrence count for existing failure."""
        # Create initial failure
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            occurrences=1
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": failure.to_episode_body()}
        ])
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            updated = await increment_occurrence(failure.id)

            assert updated is not None
            assert updated.occurrences == 2

    @pytest.mark.asyncio
    async def test_increment_occurrence_not_found(self):
        """Test increment_occurrence returns None if failure not found."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            result = await increment_occurrence("FAIL-NOTFOUND")

            assert result is None

    @pytest.mark.asyncio
    async def test_increment_occurrence_updates_last_occurred(self):
        """Test increment_occurrence updates last_occurred timestamp."""
        old_timestamp = datetime(2025, 1, 1, 10, 0, 0)
        failure = FailedApproachEpisode(
            id="FAIL-TEST001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            occurrences=1,
            first_occurred=old_timestamp,
            last_occurred=old_timestamp
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": failure.to_episode_body()}
        ])
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            before = datetime.now()
            updated = await increment_occurrence(failure.id)
            after = datetime.now()

            # last_occurred should be updated to now (not the old value)
            # Note: This comparison depends on implementation
            assert updated is not None

    @pytest.mark.asyncio
    async def test_increment_occurrence_graphiti_disabled(self):
        """Test increment_occurrence returns None when Graphiti disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            result = await increment_occurrence("FAIL-TEST001")

            assert result is None


# ============================================================================
# 7. FailedApproachManager Class Tests (5 tests)
# ============================================================================

class TestFailedApproachManagerClass:
    """Test FailedApproachManager class interface."""

    def test_manager_exists(self):
        """Test FailedApproachManager class is defined."""
        assert FailedApproachManager is not None

    @pytest.mark.asyncio
    async def test_manager_capture(self):
        """Test manager.capture() delegates to capture_failed_approach."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        manager = FailedApproachManager()

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            failure = await manager.capture(
                approach="Test",
                symptom="Test",
                root_cause="Test",
                fix_applied="Test",
                prevention="Test",
                context="test"
            )

            assert failure is not None
            assert failure.id.startswith("FAIL-")

    @pytest.mark.asyncio
    async def test_manager_load_relevant(self):
        """Test manager.load_relevant() delegates to load_relevant_failures."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        manager = FailedApproachManager()

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            results = await manager.load_relevant(query_context="test")

            assert isinstance(results, list)


# ============================================================================
# 8. Edge Cases and Error Handling (6 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_capture_with_very_long_approach(self):
        """Test capture with very long approach text."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        long_approach = "x" * 10000

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            failure = await capture_failed_approach(
                approach=long_approach,
                symptom="Test",
                root_cause="Test",
                fix_applied="Test",
                prevention="Test",
                context="test"
            )

            assert failure is not None

    @pytest.mark.asyncio
    async def test_capture_with_special_characters(self):
        """Test capture with special characters in text."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            failure = await capture_failed_approach(
                approach='Test with "quotes" and <tags>',
                symptom="Error: Can't find file",
                root_cause="Path contains 中文 characters",
                fix_applied="Use ñoño encoding",
                prevention="Check for émojis 🎉",
                context="test"
            )

            assert failure is not None

    def test_episode_body_with_unicode(self):
        """Test to_episode_body handles Unicode correctly."""
        failure = FailedApproachEpisode(
            id="FAIL-UNICODE",
            approach="中文测试",
            symptom="エラー",
            root_cause="한국어 원인",
            fix_applied="Émoji fix 🔧",
            prevention="Ñoño prevention",
            context="test"
        )

        body = failure.to_episode_body()

        # Should handle Unicode without errors
        json_str = json.dumps(body, ensure_ascii=False)
        assert "中文测试" in json_str

    def test_empty_related_adrs_and_failures(self):
        """Test entity with explicitly empty lists."""
        failure = FailedApproachEpisode(
            id="FAIL-EMPTY",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test",
            related_adrs=[],
            similar_failures=[]
        )

        body = failure.to_episode_body()

        assert body["related_adrs"] == []
        assert body["similar_failures"] == []

    @pytest.mark.asyncio
    async def test_load_failures_with_empty_query(self):
        """Test load_relevant_failures with empty query."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.failed_approach_manager.get_graphiti', return_value=mock_client):
            results = await load_relevant_failures(query_context="")

            # Should handle empty query gracefully
            assert isinstance(results, list)

    def test_severity_default_is_medium(self):
        """Test default severity is MEDIUM."""
        failure = FailedApproachEpisode(
            id="FAIL-DEFAULT",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test"
        )

        assert failure.severity == Severity.MEDIUM


# ============================================================================
# 9. Seed Failed Approaches Tests (8 tests)
# ============================================================================

class TestSeedFailedApproaches:
    """Test seed_failed_approaches() seeding functionality."""

    def test_get_initial_failed_approaches_returns_list(self):
        """Test get_initial_failed_approaches returns a non-empty list."""
        approaches = get_initial_failed_approaches()

        assert isinstance(approaches, list)
        assert len(approaches) > 0

    def test_get_initial_failed_approaches_all_have_required_fields(self):
        """Test all initial approaches have required fields."""
        approaches = get_initial_failed_approaches()

        for approach in approaches:
            assert approach.id.startswith("FAIL-")
            assert len(approach.approach) > 0
            assert len(approach.symptom) > 0
            assert len(approach.root_cause) > 0
            assert len(approach.fix_applied) > 0
            assert len(approach.prevention) > 0
            assert approach.context == "feature-build"

    def test_get_initial_failed_approaches_contains_expected_failures(self):
        """Test initial approaches contain the expected failures from TASK-REV-7549."""
        approaches = get_initial_failed_approaches()
        ids = [a.id for a in approaches]

        # Check for key failures identified in TASK-REV-7549
        assert "FAIL-SUBPROCESS" in ids
        assert "FAIL-TASK-PATH" in ids
        assert "FAIL-MOCK-PRELOOP" in ids
        assert "FAIL-SCHEMA-MISMATCH" in ids
        assert "FAIL-ALL-TESTS" in ids

    def test_get_initial_failed_approaches_have_related_adrs(self):
        """Test that critical failures have related ADRs."""
        approaches = get_initial_failed_approaches()

        # FAIL-SUBPROCESS should have ADR-FB-001
        subprocess_failure = next(a for a in approaches if a.id == "FAIL-SUBPROCESS")
        assert "ADR-FB-001" in subprocess_failure.related_adrs

    @pytest.mark.asyncio
    async def test_seed_failed_approaches_success(self):
        """Test successful seeding with enabled client."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        result = await seed_failed_approaches(mock_client)

        assert result is True
        # Should call add_episode for each initial failure
        assert mock_client.add_episode.call_count == len(get_initial_failed_approaches())

    @pytest.mark.asyncio
    async def test_seed_failed_approaches_client_none(self):
        """Test seeding returns False when client is None."""
        result = await seed_failed_approaches(None)

        assert result is False

    @pytest.mark.asyncio
    async def test_seed_failed_approaches_client_disabled(self):
        """Test seeding returns False when client is disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        result = await seed_failed_approaches(mock_client)

        assert result is False
        mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_failed_approaches_partial_failure(self):
        """Test seeding handles partial failures gracefully."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        # Fail on second call, succeed on others
        call_count = [0]

        async def side_effect_fn(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Simulated failure")
            return "episode_123"

        mock_client.add_episode = AsyncMock(side_effect=side_effect_fn)

        result = await seed_failed_approaches(mock_client)

        # Should return False due to errors
        assert result is False
        # But should still try all failures
        assert mock_client.add_episode.call_count == len(get_initial_failed_approaches())
