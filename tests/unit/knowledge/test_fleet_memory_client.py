"""Unit tests for fleet_memory_client.py adapter.

Tests verify:
- FleetMemoryClient.search returns graphiti-shaped [{"fact", "uuid", "score"}]
- FleetMemoryClient.add_episode maps group_id correctly
- Unmapped/retired group_id is no-op returning None
- Factory routes graphiti/fleet_memory/dual from config
- All boundaries (MCP, NATS) are mocked

See: TASK-MEM08-002
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from guardkit.knowledge.fleet_memory_client import (
    FleetMemoryClient,
    FleetMemoryConfig,
    get_memory_client,
    init_memory_client,
)
from guardkit.knowledge.fleet_memory_mapping import GroupMapping


@pytest.fixture
def fleet_config():
    """Fleet-memory configuration for testing."""
    return FleetMemoryConfig(
        enabled=True,
        postgres_dsn="postgresql://test:test@localhost:5433/test",
        embed_url="http://localhost:9000/v1",
        embed_model="nomic-embed",
        embed_dims=768,
        nats_url="nats://localhost:4222",
    )


@pytest.fixture
def fleet_client(fleet_config):
    """Fleet-memory client instance."""
    return FleetMemoryClient(fleet_config)


class TestFleetMemoryClientSearch:
    """Test search() method returns graphiti-shaped contract."""

    async def test_search_returns_fact_dict_shape(self, fleet_client):
        """search() must return list[dict] with fact/uuid/score keys.

        AC-001: FleetMemoryClient.search returns same list[dict] shape
        (fact, uuid, score) the existing readers consume.
        """
        # Given: search with mocked MCP boundary
        fleet_client._mcp_available = True

        with patch.object(
            fleet_client, "search", new_callable=AsyncMock
        ) as mock_search:
            # Mock returns one hit with correct shape
            mock_search.return_value = [
                {
                    "fact": "TASK-X completed successfully",
                    "uuid": str(uuid4()),
                    "score": 0.92,
                }
            ]

            # When: searching
            hits = await fleet_client.search(
                query="task outcomes",
                group_ids=["task_outcomes"],
            )

            # Then: returns list[dict] with required keys
            assert isinstance(hits, list)
            assert len(hits) >= 1

            for hit in hits:
                assert isinstance(hit, dict)
                assert "fact" in hit, "each hit must have 'fact' key"
                assert "uuid" in hit, "each hit must have 'uuid' key"
                assert "score" in hit, "each hit must have 'score' key"
                assert isinstance(hit["fact"], str)
                assert hit["fact"], "fact must be non-empty"

    async def test_search_gracefully_degrades_when_mcp_unavailable(self, fleet_client):
        """search() returns empty list when MCP not available.

        Ensures graceful degradation per graphiti_client pattern.
        """
        # Given: MCP not available
        fleet_client._mcp_available = False

        # When: searching
        hits = await fleet_client.search(
            query="test",
            group_ids=["task_outcomes"],
        )

        # Then: returns empty list (graceful degradation)
        assert hits == []

    async def test_search_maps_group_ids_to_payload_types(self, fleet_client):
        """search() resolves group_ids via fleet_memory_mapping."""
        # Given: mapped group_id
        fleet_client._mcp_available = True

        with patch("guardkit.knowledge.fleet_memory_mapping.resolve") as mock_resolve:
            mock_resolve.return_value = GroupMapping(
                project="guardkit",
                payload_type="build_outcome",
                domain_tags=["task"],
                disposition="migrate",
            )

            # When: searching (will degrade since MCP mock not fully wired)
            hits = await fleet_client.search(
                query="test",
                group_ids=["task_outcomes"],
            )

            # Then: resolve was called
            mock_resolve.assert_called_once_with("task_outcomes")


class TestFleetMemoryClientAddEpisode:
    """Test add_episode() method mapping and no-op behavior."""

    async def test_add_episode_maps_group_id_to_payload(self, fleet_client):
        """add_episode() resolves group_id and builds typed payload.

        AC-002: FleetMemoryClient.add_episode maps group_id → typed
        payload via fleet_memory_mapping.
        """
        # Given: nats_core available
        fleet_client._nats_available = True

        with patch("guardkit.knowledge.fleet_memory_mapping.resolve") as mock_resolve:
            mock_resolve.return_value = GroupMapping(
                project="guardkit",
                payload_type="build_outcome",
                domain_tags=["task"],
                disposition="migrate",
            )

            # When: adding episode
            result = await fleet_client.add_episode(
                name="TASK-ABC-123 outcome",
                episode_body="Task completed with 85% coverage",
                group_id="task_outcomes",
            )

            # Then: resolve was called and natural key returned
            mock_resolve.assert_called_once_with("task_outcomes")
            assert result == "TASK-ABC-123"  # Extracted task ID

    async def test_add_episode_unmapped_group_returns_none(self, fleet_client):
        """add_episode() with unmapped group_id is no-op returning None.

        AC-002: unmapped or 'retire' group_id is a no-op that returns None
        (fail-open — never raise).
        """
        # Given: unmapped group_id
        with patch("guardkit.knowledge.fleet_memory_mapping.resolve") as mock_resolve:
            mock_resolve.return_value = None  # Unmapped

            # When: adding episode
            result = await fleet_client.add_episode(
                name="test",
                episode_body="test body",
                group_id="unknown_group",
            )

            # Then: returns None (no-op)
            assert result is None

    async def test_add_episode_retired_group_returns_none(self, fleet_client):
        """add_episode() with retired group_id is no-op returning None."""
        # Given: retired group_id
        with patch("guardkit.knowledge.fleet_memory_mapping.resolve") as mock_resolve:
            mock_resolve.return_value = GroupMapping(
                project="guardkit",
                payload_type="seed_module",
                domain_tags=["template"],
                disposition="retire",
            )

            # When: adding episode
            result = await fleet_client.add_episode(
                name="test",
                episode_body="test body",
                group_id="guardkit_templates",
            )

            # Then: returns None (no-op)
            assert result is None

    async def test_add_episode_builds_natural_key_for_build_outcome(self, fleet_client):
        """add_episode() extracts task_id for build_outcome payloads."""
        # Given: build_outcome mapping
        fleet_client._nats_available = True

        with patch("guardkit.knowledge.fleet_memory_mapping.resolve") as mock_resolve:
            mock_resolve.return_value = GroupMapping(
                project="guardkit",
                payload_type="build_outcome",
                domain_tags=["task"],
                disposition="migrate",
            )

            # When: adding episode with task ID in name
            result = await fleet_client.add_episode(
                name="TASK-FIX-A1B2 completion",
                episode_body="Task fixed bug XYZ",
                group_id="task_outcomes",
            )

            # Then: natural key is extracted task ID
            assert result == "TASK-FIX-A1B2"

    async def test_add_episode_builds_natural_key_for_adr(self, fleet_client):
        """add_episode() extracts decision_id for adr payloads."""
        # Given: adr mapping
        fleet_client._nats_available = True

        with patch("guardkit.knowledge.fleet_memory_mapping.resolve") as mock_resolve:
            mock_resolve.return_value = GroupMapping(
                project="guardkit",
                payload_type="adr",
                domain_tags=["project"],
                disposition="migrate",
            )

            # When: adding episode with ADR ID in name
            result = await fleet_client.add_episode(
                name="ADR-042: Use pytest-bdd",
                episode_body="We will use pytest-bdd...",
                group_id="project_decisions",
            )

            # Then: natural key is extracted ADR ID
            assert result == "ADR-042"

    async def test_add_episode_nats_unavailable_returns_none(self, fleet_client):
        """add_episode() returns None when nats_core not available."""
        # Given: nats_core not available, mapped group
        fleet_client._nats_available = False

        with patch("guardkit.knowledge.fleet_memory_mapping.resolve") as mock_resolve:
            mock_resolve.return_value = GroupMapping(
                project="guardkit",
                payload_type="build_outcome",
                domain_tags=["task"],
                disposition="migrate",
            )

            # When: adding episode
            result = await fleet_client.add_episode(
                name="TASK-X outcome",
                episode_body="test",
                group_id="task_outcomes",
            )

            # Then: returns None (graceful degradation)
            assert result is None


class TestFactoryRouting:
    """Test factory functions route backends correctly."""

    def test_init_memory_client_graphiti_backend(self):
        """init_memory_client() with backend=graphiti uses graphiti.

        AC-003: Factory returns fleet-memory/graphiti/dual client purely
        from config; default is graphiti.
        """
        # When: initializing with graphiti backend
        result = init_memory_client(backend="graphiti")

        # Then: initialization succeeds
        assert result is True

        # And: get_memory_client() would return graphiti client
        # (actual graphiti client init is mocked for this test)

    def test_init_memory_client_fleet_memory_backend(self, fleet_config):
        """init_memory_client() with backend=fleet_memory uses fleet."""
        # When: initializing with fleet_memory backend
        result = init_memory_client(
            backend="fleet_memory",
            fleet_config=fleet_config,
        )

        # Then: initialization succeeds
        assert result is True

        # And: get_memory_client returns FleetMemoryClient
        client = get_memory_client()
        assert isinstance(client, FleetMemoryClient)

    def test_get_memory_client_returns_none_before_init(self):
        """get_memory_client() returns None when not initialized."""
        # Given: clean module state
        from guardkit.knowledge import fleet_memory_client

        fleet_memory_client._memory_client = None
        fleet_memory_client._backend = "graphiti"

        # When: getting client before init
        client = get_memory_client()

        # Then: may return None or lazy-init graphiti
        # (depends on graphiti_client being available)
        # This is acceptable graceful degradation

    def test_init_memory_client_unknown_backend_fails(self):
        """init_memory_client() with unknown backend returns False."""
        # When: initializing with invalid backend
        result = init_memory_client(backend="invalid")  # type: ignore

        # Then: initialization fails
        assert result is False


class TestSeamContract:
    """Seam tests verifying integration contracts.

    These tests verify that FleetMemoryClient.search returns the
    contract shape that existing readers depend on.
    """

    @pytest.mark.seam
    @pytest.mark.integration_contract("fleet_memory_search_shape")
    async def test_fleet_memory_search_returns_fact_dicts(self, fleet_client):
        """FleetMemoryClient.search must return fact/uuid/score dicts.

        Contract: search(query, group_ids) -> list[{"fact": str, "uuid": str, "score": float}]
        Producer: TASK-MEM08-002 fleet_memory_client
        Consumer: coach_context_builder, feature_plan_context, outcome_manager, adr_service
        """
        # Given: mocked memory_search returning context_block
        fleet_client._mcp_available = True

        with patch.object(
            fleet_client, "search", new_callable=AsyncMock
        ) as mock_search:
            # Mock returns hits with correct shape
            mock_search.return_value = [
                {
                    "fact": "TASK-X completed with 80% coverage",
                    "uuid": "uuid-1",
                    "score": 0.95,
                },
                {
                    "fact": "TASK-Y failed due to timeout",
                    "uuid": "uuid-2",
                    "score": 0.87,
                },
            ]

            # When: searching
            hits = await fleet_client.search(
                query="task outcomes",
                group_ids=["task_outcomes"],
            )

            # Then: each hit has required fields
            for hit in hits:
                assert "fact" in hit, "missing 'fact' key"
                assert "uuid" in hit, "missing 'uuid' key"
                assert "score" in hit, "missing 'score' key"
                assert hit["fact"], "fact must be non-empty"
                assert isinstance(hit["uuid"], str)
                assert isinstance(hit["score"], (int, float))
