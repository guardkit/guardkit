"""Tests for DualWriteClient - dual-write mode for Graphiti + fleet-memory.

TASK-MEM08-004: Validates that writes go to both backends under `dual` mode,
with graceful degradation when fleet-memory fails.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from guardkit.knowledge.fleet_memory_client import (
    DualWriteClient,
    FleetMemoryClient,
    FleetMemoryConfig,
)


@pytest.fixture
def mock_graphiti_client():
    """Mock GraphitiClient."""
    client = AsyncMock()
    client.enabled = True
    client.add_episode = AsyncMock(return_value="graphiti-uuid-123")
    return client


@pytest.fixture
def mock_fleet_client():
    """Mock FleetMemoryClient."""
    client = MagicMock(spec=FleetMemoryClient)
    client.add_episode = AsyncMock(return_value="task-001")
    return client


@pytest.fixture
def dual_client(mock_graphiti_client, mock_fleet_client):
    """Create DualWriteClient with mocked backends."""
    return DualWriteClient(
        graphiti_client=mock_graphiti_client,
        fleet_client=mock_fleet_client
    )


@pytest.mark.asyncio
async def test_dual_write_both_backends_called(dual_client, mock_graphiti_client, mock_fleet_client):
    """Under dual mode, add_episode writes to both Graphiti and fleet-memory."""
    result = await dual_client.add_episode(
        name="TASK-001 outcome",
        episode_body="Task completed successfully",
        group_id="task_outcomes",
        source="test",
    )

    # Both backends should be called
    mock_graphiti_client.add_episode.assert_called_once()
    mock_fleet_client.add_episode.assert_called_once()

    # Graphiti result returned (it's authoritative)
    assert result == "graphiti-uuid-123"


@pytest.mark.asyncio
async def test_fleet_write_failure_graceful_degradation(dual_client, mock_graphiti_client, mock_fleet_client):
    """Fleet-memory write failure does not fail the overall operation."""
    # Fleet-memory fails
    mock_fleet_client.add_episode = AsyncMock(side_effect=Exception("NATS connection failed"))

    # Should not raise, Graphiti write succeeds
    result = await dual_client.add_episode(
        name="TASK-001 outcome",
        episode_body="Task completed",
        group_id="task_outcomes",
    )

    # Graphiti still called and result returned
    mock_graphiti_client.add_episode.assert_called_once()
    assert result == "graphiti-uuid-123"


@pytest.mark.asyncio
async def test_graphiti_write_failure_propagates(dual_client, mock_graphiti_client, mock_fleet_client):
    """Graphiti write failure propagates (it's authoritative)."""
    # Graphiti fails
    mock_graphiti_client.add_episode = AsyncMock(side_effect=Exception("Graphiti down"))

    # Should raise (Graphiti is authoritative)
    with pytest.raises(Exception, match="Graphiti down"):
        await dual_client.add_episode(
            name="TASK-001 outcome",
            episode_body="Task completed",
            group_id="task_outcomes",
        )

    # Fleet-memory should NOT be called if Graphiti fails first
    mock_fleet_client.add_episode.assert_not_called()


@pytest.mark.asyncio
async def test_retired_group_skips_fleet_write(dual_client, mock_graphiti_client, mock_fleet_client):
    """Retired groups write to Graphiti only, skip fleet-memory."""
    # product_knowledge is a retired group
    result = await dual_client.add_episode(
        name="Product context",
        episode_body="GuardKit features...",
        group_id="product_knowledge",
    )

    # Graphiti called
    mock_graphiti_client.add_episode.assert_called_once()

    # Fleet-memory NOT called (retired group)
    mock_fleet_client.add_episode.assert_not_called()

    assert result == "graphiti-uuid-123"


@pytest.mark.asyncio
async def test_search_delegates_to_graphiti(dual_client, mock_graphiti_client):
    """Search operations delegate to Graphiti (reads not migrated yet)."""
    mock_graphiti_client.search = AsyncMock(return_value=[{"fact": "test"}])

    results = await dual_client.search(
        query="test query",
        group_ids=["task_outcomes"],
    )

    mock_graphiti_client.search.assert_called_once_with(
        query="test query",
        group_ids=["task_outcomes"],
        num_results=10,
        scope=None,
    )
    assert results == [{"fact": "test"}]
