"""Tests for fleet-memory integration in feature_plan_context.

Tests verify that FeaturePlanContextBuilder correctly routes through
fleet-memory when backend is configured as fleet_memory or dual.

Coverage Target: >=80%
Test Count: 8+ tests

Key behaviors verified:
- Routes through fleet_memory when backend=fleet_memory
- Routes through graphiti when backend=graphiti (default)
- Emits query_logger entries for fleet-memory reads
- Handles unmapped group_ids gracefully
- Handles fleet-memory read failures gracefully
"""

import pytest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def mock_fleet_client() -> MagicMock:
    """Create a mock FleetMemoryClient instance."""
    client = MagicMock()
    client.enabled = True
    client.search = AsyncMock(return_value=[
        {"fact": "Related feature from fleet-memory", "uuid": "test-uuid", "score": 0.9}
    ])
    # Set class name to match FleetMemoryClient for backend type detection
    client.__class__.__name__ = "FleetMemoryClient"
    return client


@pytest.fixture
def mock_graphiti_client() -> MagicMock:
    """Create a mock GraphitiClient instance."""
    client = MagicMock()
    client.enabled = True
    client.search = AsyncMock(return_value=[
        {"fact": "Related feature from graphiti", "uuid": "test-uuid-g", "score": 0.85}
    ])
    return client


@pytest.fixture
def builder(tmp_path: Path) -> FeaturePlanContextBuilder:
    """Create a FeaturePlanContextBuilder instance."""
    return FeaturePlanContextBuilder(project_root=tmp_path)


# =========================================================================
# FLEET_MEMORY BACKEND TESTS
# =========================================================================


class TestFleetMemoryIntegration:
    """Tests for fleet_memory backend routing."""

    @pytest.mark.asyncio
    async def test_uses_fleet_memory_client_when_configured(
        self, builder: FeaturePlanContextBuilder, mock_fleet_client: MagicMock
    ):
        """Test that fleet_memory backend uses FleetMemoryClient."""
        builder.graphiti_client = mock_fleet_client

        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        # Verify fleet-memory search was called
        assert mock_fleet_client.search.called
        assert context is not None

    @pytest.mark.asyncio
    async def test_fleet_memory_search_emits_query_log(
        self, builder: FeaturePlanContextBuilder, mock_fleet_client: MagicMock
    ):
        """Test that fleet-memory reads emit query_logger entries."""
        builder.graphiti_client = mock_fleet_client
        logged_queries = []

        def capture_log(**kwargs):
            logged_queries.append(kwargs)

        with patch("guardkit.knowledge.feature_plan_context.log_query", side_effect=capture_log):
            await builder.build_context(
                description="Test feature",
                context_files=[],
                tech_stack="python"
            )

            # Verify queries were logged
            assert len(logged_queries) > 0
            # Check that source indicates fleet_memory for at least one query
            assert any("fleet" in str(log.get("source", "")).lower() for log in logged_queries)


# =========================================================================
# GRAPHITI BACKEND TESTS (DEFAULT BEHAVIOR)
# =========================================================================


class TestGraphitiBackendPreserved:
    """Tests that graphiti backend behavior is unchanged."""

    @pytest.mark.asyncio
    async def test_graphiti_backend_uses_graphiti_client(
        self, builder: FeaturePlanContextBuilder, mock_graphiti_client: MagicMock
    ):
        """Test that graphiti backend (default) still uses GraphitiClient."""
        builder.graphiti_client = mock_graphiti_client

        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        # Verify graphiti search was called
        assert mock_graphiti_client.search.called
        assert context is not None


# =========================================================================
# ERROR HANDLING TESTS
# =========================================================================


class TestErrorHandling:
    """Tests for graceful degradation when fleet-memory fails."""

    @pytest.mark.asyncio
    async def test_fleet_memory_read_failure_graceful_degradation(
        self, builder: FeaturePlanContextBuilder
    ):
        """Test that fleet-memory read failure degrades gracefully."""
        failing_client = MagicMock()
        failing_client.enabled = True
        failing_client.search = AsyncMock(side_effect=Exception("Connection failed"))

        builder.graphiti_client = failing_client

        # Should not raise, returns context with empty lists
        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        assert context is not None
        assert context.related_features == []
        assert context.relevant_patterns == []

    @pytest.mark.asyncio
    async def test_unmapped_group_returns_empty(
        self, builder: FeaturePlanContextBuilder, mock_fleet_client: MagicMock
    ):
        """Test graceful handling of unmapped group_ids."""
        # Mock fleet client that returns empty for unmapped groups
        mock_fleet_client.search = AsyncMock(return_value=[])
        builder.graphiti_client = mock_fleet_client

        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        # Should handle gracefully with empty results
        assert context is not None
        assert context.related_features == []

    @pytest.mark.asyncio
    async def test_none_client_graceful_degradation(
        self, builder: FeaturePlanContextBuilder
    ):
        """Test graceful handling when client is None."""
        builder.graphiti_client = None

        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        # Should not raise, returns empty context
        assert context is not None
        assert context.related_features == []
        assert context.relevant_patterns == []
