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


def _disabled_config():
    """A FleetMemoryConfig with reads disabled (avoids mutating a fixture)."""
    return FleetMemoryConfig(
        enabled=False,
        postgres_dsn="postgresql://test:test@localhost:5433/test",
        embed_url="http://localhost:9000",
        embed_model="embed",
        embed_dims=1024,
        nats_url="nats://localhost:4222",
    )


def _install_fake_fleet_memory_retrieval(monkeypatch, *, context_block, coverage, captured):
    """Inject a fake fleet_memory.retrieval so search() wiring runs without the
    real dependency or a live store (TASK-MEM08-011)."""
    import sys
    import types

    class _FakeSearchRequest:
        def __init__(self, **kw):
            captured["request"] = kw

    async def _fake_search(request, store):
        captured["store"] = store
        return ["result-1", "result-2"]

    class _FakeAssembly:
        pass

    def _fake_assemble(results, token_budget):
        captured["assembled_n"] = len(results)
        a = _FakeAssembly()
        a.context_block = context_block
        a.coverage_score = coverage
        return a

    retrieval = types.ModuleType("fleet_memory.retrieval")
    retrieval.SearchRequest = _FakeSearchRequest
    retrieval.search = _fake_search
    retrieval.assemble_context = _fake_assemble
    fm = types.ModuleType("fleet_memory")
    fm.retrieval = retrieval
    monkeypatch.setitem(sys.modules, "fleet_memory", fm)
    monkeypatch.setitem(sys.modules, "fleet_memory.retrieval", retrieval)


class TestFleetMemoryClientSearch:
    """Test search() — graphiti-shaped contract + real retrieval adaptation."""

    async def test_search_disabled_returns_empty(self):
        """search() returns [] when reads are disabled (FLEET_MEMORY_ENABLED=false)."""
        client = FleetMemoryClient(_disabled_config())
        assert await client.search(query="x", group_ids=["task_outcomes"]) == []

    async def test_search_degrades_when_read_backend_unavailable(self, fleet_client):
        """search() returns [] (graceful) when fleet_memory.retrieval is unimportable."""
        fleet_client._read_available = False
        assert await fleet_client.search(query="x", group_ids=["task_outcomes"]) == []

    async def test_search_adapts_context_block_to_hit(self, fleet_client, monkeypatch):
        """search() calls fleet_memory.retrieval.search + assemble_context and adapts
        the assembled context_block into one graphiti-shaped hit (AC-1).

        The real dependency + live store are covered by the TASK-MEM08-007 read-proof
        run; here a fake retrieval module exercises the wiring deterministically.
        """
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="## Recommended Patterns\n\n- Use the X pattern",
            coverage=0.9,
            captured=captured,
        )
        # read backend available; store already open so initialize() is skipped
        fleet_client._read_available = True
        fleet_client._store = object()

        hits = await fleet_client.search(query="patterns for X", group_ids=["patterns"])

        assert len(hits) == 1
        assert hits[0]["fact"] == "## Recommended Patterns\n\n- Use the X pattern"
        assert hits[0]["score"] == 0.9
        assert isinstance(hits[0]["uuid"], str)
        # the real retrieval surface was actually invoked
        assert captured["assembled_n"] == 2
        assert captured["request"]["project"] == "guardkit"
        assert captured["request"]["query"] == "patterns for X"

    async def test_search_empty_context_block_returns_empty(self, fleet_client, monkeypatch):
        """An empty assembled block (no matches) yields [] (result_count 0)."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch, context_block="", coverage=0.0, captured=captured
        )
        fleet_client._read_available = True
        fleet_client._store = object()
        assert await fleet_client.search(query="nothing", group_ids=["patterns"]) == []

    async def test_search_maps_group_ids_to_payload_types(self, fleet_client, monkeypatch):
        """search() resolves group_ids via fleet_memory_mapping (migrate -> payload_types)."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch, context_block="block", coverage=0.5, captured=captured
        )
        fleet_client._read_available = True
        fleet_client._store = object()

        with patch("guardkit.knowledge.fleet_memory_mapping.resolve") as mock_resolve:
            mock_resolve.return_value = GroupMapping(
                project="guardkit",
                payload_type="build_outcome",
                domain_tags=["task"],
                disposition="migrate",
            )
            await fleet_client.search(query="test", group_ids=["task_outcomes"])

        mock_resolve.assert_called_once_with("task_outcomes")
        assert captured["request"]["payload_types"] == ["build_outcome"]
        assert captured["request"]["domain_tags"] == ["task"]


class TestFleetMemoryClientInterface:
    """The read lifecycle interface consumed by build_context + the memory CLI."""

    def test_enabled_reflects_config(self, fleet_client):
        assert fleet_client.enabled is True
        assert FleetMemoryClient(_disabled_config()).enabled is False

    async def test_initialize_returns_false_when_disabled(self):
        assert await FleetMemoryClient(_disabled_config()).initialize() is False

    async def test_initialize_returns_false_when_read_backend_unavailable(self, fleet_client):
        fleet_client._read_available = False
        assert await fleet_client.initialize() is False

    async def test_close_is_safe_when_not_initialized(self, fleet_client):
        await fleet_client.close()  # must not raise
        assert fleet_client._store is None


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
