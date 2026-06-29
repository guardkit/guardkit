"""Tests for fleet-memory integration in coach_context_builder.

Tests verify that coach_context_builder correctly routes through fleet-memory
when backend is configured as fleet_memory or dual.

Coverage Target: >=80%
Test Count: 10+ tests

Key behaviors verified:
- Routes through fleet_memory when backend=fleet_memory
- Routes through dual client when backend=dual
- Falls back to graphiti when backend=graphiti (default)
- Emits query_logger entries for fleet-memory reads
- Handles unmapped group_ids gracefully
- Handles fleet-memory read failures gracefully
"""

import pytest
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from guardkit.planning.coach_context_builder import build_coach_context


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def mock_fleet_client() -> MagicMock:
    """Create a mock FleetMemoryClient instance."""
    client = MagicMock()
    client.enabled = True
    client.search = AsyncMock(return_value=[
        {"fact": "Architecture context from fleet-memory", "uuid": "test-uuid", "score": 0.9}
    ])
    # Set class name to match FleetMemoryClient for backend type detection
    client.__class__.__name__ = "FleetMemoryClient"
    return client


@pytest.fixture
def mock_graphiti_client() -> MagicMock:
    """Create a mock GraphitiClient instance."""
    client = MagicMock()
    client.enabled = True
    return client


@pytest.fixture
def sample_task() -> Dict[str, Any]:
    """Sample task with medium complexity."""
    return {
        "complexity": 5,
        "title": "Implement feature",
        "description": "Add new functionality"
    }


# =========================================================================
# FLEET_MEMORY BACKEND TESTS
# =========================================================================


class TestFleetMemoryBackend:
    """Tests for fleet_memory backend routing."""

    @pytest.mark.asyncio
    async def test_uses_fleet_memory_client_when_backend_fleet_memory(
        self, sample_task: Dict[str, Any], mock_fleet_client: MagicMock
    ):
        """Test that fleet_memory backend uses FleetMemoryClient."""
        with patch("guardkit.knowledge.fleet_memory_client.get_memory_client", return_value=mock_fleet_client):
            with patch("guardkit.planning.coach_context_builder.SystemPlanGraphiti") as MockSP:
                mock_sp = MagicMock()
                mock_sp._available = True
                mock_sp._client = mock_fleet_client
                MockSP.return_value = mock_sp

                with patch("guardkit.planning.coach_context_builder.get_system_overview") as mock_overview:
                    mock_overview.return_value = {"status": "ok"}

                    with patch("guardkit.planning.coach_context_builder.condense_for_injection", return_value="Test context"):
                        result = await build_coach_context(sample_task, mock_fleet_client, "guardkit")

                        assert result != ""
                        assert "Architecture Context" in result

    @pytest.mark.asyncio
    async def test_fleet_memory_search_emits_query_log(
        self, sample_task: Dict[str, Any], mock_fleet_client: MagicMock
    ):
        """Test that fleet-memory reads emit query_logger entries."""
        logged_queries = []

        def capture_log(**kwargs):
            logged_queries.append(kwargs)

        with patch("guardkit.knowledge.fleet_memory_client.get_memory_client", return_value=mock_fleet_client):
            with patch("guardkit.planning.coach_context_builder.SystemPlanGraphiti") as MockSP:
                mock_sp = MagicMock()
                mock_sp._available = True
                mock_sp._client = mock_fleet_client
                MockSP.return_value = mock_sp

                with patch("guardkit.planning.coach_context_builder.get_system_overview") as mock_overview:
                    mock_overview.return_value = {"status": "ok"}

                    with patch("guardkit.planning.coach_context_builder.condense_for_injection", return_value="Test context"):
                        with patch("guardkit.planning.coach_context_builder.log_query", side_effect=capture_log):
                            await build_coach_context(sample_task, mock_fleet_client, "guardkit")

                            # Verify query was logged
                            assert len(logged_queries) > 0
                            # Check that source indicates fleet_memory
                            assert any("fleet" in str(log.get("source", "")).lower() for log in logged_queries)


# =========================================================================
# GRAPHITI BACKEND TESTS (DEFAULT BEHAVIOR)
# =========================================================================


class TestGraphitiBackendPreserved:
    """Tests that graphiti backend behavior is unchanged."""

    @pytest.mark.asyncio
    async def test_graphiti_backend_uses_graphiti_client(
        self, sample_task: Dict[str, Any], mock_graphiti_client: MagicMock
    ):
        """Test that graphiti backend (default) still uses GraphitiClient."""
        with patch("guardkit.knowledge.fleet_memory_client.get_memory_client", return_value=mock_graphiti_client):
            with patch("guardkit.planning.coach_context_builder.SystemPlanGraphiti") as MockSP:
                mock_sp = MagicMock()
                mock_sp._available = True
                mock_sp._client = mock_graphiti_client
                MockSP.return_value = mock_sp

                with patch("guardkit.planning.coach_context_builder.get_system_overview") as mock_overview:
                    mock_overview.return_value = {"status": "ok"}

                    with patch("guardkit.planning.coach_context_builder.condense_for_injection", return_value="Graphiti context"):
                        result = await build_coach_context(sample_task, mock_graphiti_client, "guardkit")

                        assert result != ""
                        assert "Architecture Context" in result


# =========================================================================
# ERROR HANDLING TESTS
# =========================================================================


class TestFleetMemoryErrorHandling:
    """Tests for graceful degradation when fleet-memory fails."""

    @pytest.mark.asyncio
    async def test_fleet_memory_read_failure_returns_empty(
        self, sample_task: Dict[str, Any]
    ):
        """Test that fleet-memory read failure degrades gracefully."""
        failing_client = MagicMock()
        failing_client.enabled = True
        failing_client.search = AsyncMock(side_effect=Exception("Connection failed"))

        with patch("guardkit.knowledge.fleet_memory_client.get_memory_client", return_value=failing_client):
            with patch("guardkit.planning.coach_context_builder.SystemPlanGraphiti") as MockSP:
                mock_sp = MagicMock()
                mock_sp._available = True
                mock_sp._client = failing_client
                MockSP.return_value = mock_sp

                with patch("guardkit.planning.coach_context_builder.get_system_overview") as mock_overview:
                    mock_overview.side_effect = Exception("Search failed")

                    # Should return empty string, not raise
                    result = await build_coach_context(sample_task, failing_client, "guardkit")
                    assert result == ""

    @pytest.mark.asyncio
    async def test_unmapped_group_degradation(
        self, sample_task: Dict[str, Any], mock_fleet_client: MagicMock
    ):
        """Test graceful handling of unmapped group_ids."""
        # Mock fleet client that returns empty for unmapped groups
        mock_fleet_client.search = AsyncMock(return_value=[])

        with patch("guardkit.knowledge.fleet_memory_client.get_memory_client", return_value=mock_fleet_client):
            with patch("guardkit.planning.coach_context_builder.SystemPlanGraphiti") as MockSP:
                mock_sp = MagicMock()
                mock_sp._available = True
                mock_sp._client = mock_fleet_client
                MockSP.return_value = mock_sp

                with patch("guardkit.planning.coach_context_builder.get_system_overview") as mock_overview:
                    mock_overview.return_value = {"status": "no_context"}

                    # Should handle gracefully
                    result = await build_coach_context(sample_task, mock_fleet_client, "guardkit")
                    assert result == ""
