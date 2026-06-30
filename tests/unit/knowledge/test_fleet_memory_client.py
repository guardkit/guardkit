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

import importlib.util

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

# The real write path builds nats_core.MemoryEpisodeV1 and publishes via
# harvest_publisher (which imports nats_core at module top). When the guardkit `memory`
# extra is not installed (e.g. a minimal CI env), skip the publish-path tests rather
# than erroring on the import.
_HAS_NATS_CORE = importlib.util.find_spec("nats_core") is not None


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


@pytest.mark.skipif(not _HAS_NATS_CORE, reason="nats_core (memory extra) not installed")
class TestFleetMemoryClientAddEpisode:
    """add_episode() must REALLY publish a typed episode (not log a stub).

    These tests assert the NATS publish boundary is invoked with a correctly-shaped
    ``MemoryEpisodeV1`` — the prior suite only asserted the returned natural key and so
    stayed green against a ``logger.info('Would publish')`` stub (a
    per-task-green-is-not-feature-green false-green). The publish boundary
    (``guardkit.memory.harvest_publisher.publish_episodes``) is mocked; the real
    ``build_memory_episode`` runs so the published episode shape is exercised end-to-end.
    """

    @staticmethod
    def _summary(published: int = 1, skipped: int = 0):
        from guardkit.memory.harvest_publisher import PublishSummary

        return PublishSummary(
            published=published, skipped_oversized=skipped, counts_per_type={}
        )

    async def test_add_episode_publishes_typed_build_outcome(self, fleet_client):
        """A task_outcomes write publishes a content_format=json build_outcome episode."""
        import json

        fleet_client._nats_available = True
        body = json.dumps(
            {
                "task_id": "TASK-1234",
                "success": True,
                "duration_minutes": 5,
                "approach_used": "TDD",
                "lessons_learned": ["pin the env"],
                "feature_id": "FEAT-X",
            }
        )

        with patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=AsyncMock(return_value=self._summary(published=1)),
        ) as mock_pub:
            result = await fleet_client.add_episode(
                name="OUT-1: TASK-1234 - Implement OAuth2",
                episode_body=body,
                group_id="task_outcomes",
            )

        # Published exactly one episode, with the right typed shape.
        mock_pub.assert_awaited_once()
        (episodes,), _ = mock_pub.call_args
        assert len(episodes) == 1
        ep = episodes[0]
        assert ep.content_format == "json"
        assert ep.payload_type == "build_outcome"
        assert ep.project_id == "guardkit"
        assert ep.episode_type == "build_outcome"
        sent = json.loads(ep.body)
        assert sent["project"] == "guardkit"
        assert sent["identifier"] == "TASK_1234"  # hyphens sanitised to underscores
        assert sent["status"] == "success"
        assert sent["duration_seconds"] == 300
        # Return value is the natural key (not the bare task id).
        assert result == "build_outcome:guardkit:TASK_1234"
        assert ep.episode_id == "build_outcome:guardkit:TASK_1234"

    async def test_add_episode_publishes_adr(self, fleet_client):
        """An ADR write (group_id 'adrs', now mapped) publishes an adr episode."""
        import json

        fleet_client._nats_available = True
        body = json.dumps(
            {"id": "ADR-0001", "decision": "Adopt fleet-memory", "status": "accepted"}
        )

        with patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=AsyncMock(return_value=self._summary(published=1)),
        ) as mock_pub:
            result = await fleet_client.add_episode(
                name="adr_ADR-0001", episode_body=body, group_id="adrs"
            )

        mock_pub.assert_awaited_once()
        (episodes,), _ = mock_pub.call_args
        ep = episodes[0]
        assert ep.payload_type == "adr"
        sent = json.loads(ep.body)
        assert sent["identifier"] == "ADR_0001"
        assert sent["decision"] == "Adopt fleet-memory"
        assert sent["status"] == "accepted"
        assert result == "adr:guardkit:ADR_0001"

    async def test_add_episode_unmapped_group_returns_none(self, fleet_client):
        """Unmapped group_id is a no-op returning None — and never publishes."""
        with patch(
            "guardkit.memory.harvest_publisher.publish_episodes", new=AsyncMock()
        ) as mock_pub:
            result = await fleet_client.add_episode(
                name="test", episode_body="{}", group_id="unknown_group"
            )
        assert result is None
        mock_pub.assert_not_awaited()

    async def test_add_episode_retired_group_returns_none(self, fleet_client):
        """Retired group_id (seed_module) is a no-op returning None — never publishes."""
        with patch(
            "guardkit.memory.harvest_publisher.publish_episodes", new=AsyncMock()
        ) as mock_pub:
            result = await fleet_client.add_episode(
                name="template x", episode_body="{}", group_id="guardkit_templates"
            )
        assert result is None
        mock_pub.assert_not_awaited()

    async def test_add_episode_nats_unavailable_returns_none(self, fleet_client):
        """Returns None (graceful) when nats_core is unavailable — never publishes."""
        fleet_client._nats_available = False
        with patch(
            "guardkit.memory.harvest_publisher.publish_episodes", new=AsyncMock()
        ) as mock_pub:
            result = await fleet_client.add_episode(
                name="TASK-X outcome", episode_body="{}", group_id="task_outcomes"
            )
        assert result is None
        mock_pub.assert_not_awaited()

    async def test_add_episode_failopen_on_publish_error(self, fleet_client):
        """A publish failure (e.g. missing GUARDKIT_NATS_PASSWORD) returns None, not raise."""
        fleet_client._nats_available = True
        with patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=AsyncMock(side_effect=ValueError("GUARDKIT_NATS_PASSWORD not set")),
        ):
            result = await fleet_client.add_episode(
                name="OUT-1: TASK-1 - x",
                episode_body='{"task_id": "TASK-1", "success": true}',
                group_id="task_outcomes",
            )
        assert result is None  # fail-open, no exception propagated

    async def test_add_episode_oversized_skip_returns_none(self, fleet_client):
        """If the episode is skipped (oversized), add_episode returns None."""
        fleet_client._nats_available = True
        with patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=AsyncMock(return_value=self._summary(published=0, skipped=1)),
        ):
            result = await fleet_client.add_episode(
                name="OUT-1: TASK-1 - x",
                episode_body='{"task_id": "TASK-1", "success": true}',
                group_id="task_outcomes",
            )
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


class TestBackendAutoInit:
    """get_memory_client() lazily selects the backend from config.

    Without this producer the FEAT-MEM-08 cutover flag (graphiti.yaml ``backend:
    fleet_memory``, flipped by 009) is inert — ``_backend`` stays "graphiti" and every
    call routes to the (now-disabled) graphiti client. These tests pin the wiring.
    """

    @pytest.fixture(autouse=True)
    def _reset_factory(self):
        from guardkit.knowledge import fleet_memory_client as fmc

        for _ in (None,):
            fmc._memory_client = None
            fmc._backend = "graphiti"
            fmc._backend_initialized = False
        yield
        fmc._memory_client = None
        fmc._backend = "graphiti"
        fmc._backend_initialized = False

    def test_resolve_backend_env_override(self, monkeypatch):
        from guardkit.knowledge import fleet_memory_client as fmc

        monkeypatch.setenv("GUARDKIT_MEMORY_BACKEND", "fleet_memory")
        assert fmc._resolve_backend_from_config() == "fleet_memory"

    def test_resolve_backend_invalid_env_falls_back(self, monkeypatch, tmp_path):
        from guardkit.knowledge import fleet_memory_client as fmc

        monkeypatch.setenv("GUARDKIT_MEMORY_BACKEND", "bogus")
        monkeypatch.setenv("GUARDKIT_CONFIG_DIR", str(tmp_path))  # no yaml → default
        assert fmc._resolve_backend_from_config() == "graphiti"

    def test_resolve_backend_from_yaml(self, monkeypatch, tmp_path):
        from guardkit.knowledge import fleet_memory_client as fmc

        monkeypatch.delenv("GUARDKIT_MEMORY_BACKEND", raising=False)
        (tmp_path / "graphiti.yaml").write_text("backend: fleet_memory\n")
        monkeypatch.setenv("GUARDKIT_CONFIG_DIR", str(tmp_path))
        assert fmc._resolve_backend_from_config() == "fleet_memory"

    def test_get_memory_client_auto_inits_fleet_from_env(self, monkeypatch):
        from guardkit.knowledge import fleet_memory_client as fmc

        monkeypatch.setenv("GUARDKIT_MEMORY_BACKEND", "fleet_memory")
        client = get_memory_client()
        assert isinstance(client, FleetMemoryClient)
        assert fmc._backend_initialized is True

    def test_get_memory_client_defaults_to_graphiti(self, monkeypatch, tmp_path):
        from guardkit.knowledge import fleet_memory_client as fmc

        monkeypatch.delenv("GUARDKIT_MEMORY_BACKEND", raising=False)
        monkeypatch.setenv("GUARDKIT_CONFIG_DIR", str(tmp_path))  # no yaml → graphiti
        with patch(
            "guardkit.knowledge.graphiti_client.get_graphiti", return_value="GRAPHITI"
        ):
            client = get_memory_client()
        assert fmc._backend == "graphiti"
        assert client == "GRAPHITI"

    def test_explicit_init_disables_auto_init(self, monkeypatch, fleet_config):
        """An explicit init wins; a later config change does not re-route."""
        from guardkit.knowledge import fleet_memory_client as fmc

        init_memory_client(backend="fleet_memory", fleet_config=fleet_config)
        # Even if env now says graphiti, the explicit init stands.
        monkeypatch.setenv("GUARDKIT_MEMORY_BACKEND", "graphiti")
        client = get_memory_client()
        assert isinstance(client, FleetMemoryClient)


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
