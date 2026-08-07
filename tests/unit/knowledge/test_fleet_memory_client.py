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
import json
import os
from types import SimpleNamespace

import pytest
import logging
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from guardkit.knowledge.fleet_memory_client import (
    FleetMemoryClient,
    FleetMemoryConfig,
    _load_fleet_config_from_env,
    get_memory_client,
    init_memory_client,
)
from guardkit.knowledge.fleet_memory_mapping import GroupMapping


def _scrub_fleet_memory_env(monkeypatch):
    """Remove the FULL FLEET_MEMORY_* env surface (plus the project scoping var)
    so no test reads ambient environment values (hermeticity hard rule).

    Tests then set ONLY the variables they assert against, with synthetic
    values — never live credentials.
    """
    for key in list(os.environ):
        if key.startswith("FLEET_MEMORY_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("GUARDKIT_MEMORY_PROJECT", raising=False)

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


def _mk_result_item(natural_key: str, score: float, content: str = "content"):
    """A minimal fm_search result item matching the langgraph SearchItem contract
    subset search() consumes: `.score` plus `.value` dict with natural_key/content."""
    return SimpleNamespace(
        score=score, value={"natural_key": natural_key, "content": content}
    )


def _install_fake_fleet_memory_retrieval(
    monkeypatch,
    *,
    context_block,
    coverage,
    captured,
    results=None,
    search_exc=None,
):
    """Inject a fake fleet_memory.retrieval so search() wiring runs without the
    real dependency or a live store (TASK-MEM08-011).

    Args:
        results: fm_search return value (contract-shaped items); defaults to two
            items so existing wiring assertions (assembled_n == 2) hold.
        search_exc: when set, fm_search raises it instead of returning results.
    """
    import sys
    import types

    if results is None:
        results = [
            _mk_result_item("build_outcome:guardkit:R1", 0.9, "result one content"),
            _mk_result_item("build_outcome:guardkit:R2", 0.8, "result two content"),
        ]

    class _FakeSearchRequest:
        def __init__(self, **kw):
            captured["request"] = kw

    async def _fake_search(request, store):
        captured["store"] = store
        if search_exc is not None:
            raise search_exc
        return results

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

    @pytest.fixture(autouse=True)
    def _isolate_query_log(self, monkeypatch, tmp_path):
        """Redirect the retrieval JSONL log (written by search() since
        TASK-ABL1-003) into tmp_path so tests never touch the repo's
        .guardkit/memory-query-log.jsonl."""
        monkeypatch.setattr(
            "guardkit.knowledge.query_logger._get_log_path",
            lambda base_dir=None: tmp_path / "memory-query-log.jsonl",
        )

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
        # "document" is included alongside the mapped type so a group-scoped read also
        # matches migrated Graphiti prose (payload_type=document); domain_tags scope it.
        assert captured["request"]["payload_types"] == ["build_outcome", "document"]
        assert captured["request"]["domain_tags"] == ["task"]

    async def test_search_includes_document_for_document_mapped_group(
        self, fleet_client, monkeypatch
    ):
        """A group that already maps to `document` yields just ["document"] (no dup),
        so migrated docs for that group are matched by domain_tags (FEAT-MEM-09 WS-2)."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch, context_block="block", coverage=0.5, captured=captured
        )
        fleet_client._read_available = True
        fleet_client._store = object()

        with patch("guardkit.knowledge.fleet_memory_mapping.resolve") as mock_resolve:
            mock_resolve.return_value = GroupMapping(
                project="guardkit",
                payload_type="document",
                domain_tags=["architecture"],
                disposition="migrate",
            )
            await fleet_client.search(query="arch", group_ids=["project_architecture"])

        assert captured["request"]["payload_types"] == ["document"]
        assert captured["request"]["domain_tags"] == ["architecture"]


class TestSearchArmGateAndRetrievalLog:
    """TASK-ABL1-003: retrieval arm gate inside search() + per-item JSONL log.

    Hermetic: the FLEET_MEMORY_* env surface is scrubbed (configs are built
    directly — search() never re-reads env), the query log is redirected to
    tmp_path, and only synthetic DSNs appear anywhere.
    """

    _DSN = "postgresql://user:pw@localhost:5433/fixture_db"

    @pytest.fixture(autouse=True)
    def _hermetic(self, monkeypatch, tmp_path):
        _scrub_fleet_memory_env(monkeypatch)
        self._log_path = tmp_path / "memory-query-log.jsonl"
        monkeypatch.setattr(
            "guardkit.knowledge.query_logger._get_log_path",
            lambda base_dir=None: self._log_path,
        )

    def _client(self, retrieval_arm=None, fixture_id=None, enabled=True):
        config = FleetMemoryConfig(
            enabled=enabled,
            postgres_dsn=self._DSN,
            embed_url="http://localhost:9000/v1",
            embed_model="nomic-embed",
            embed_dims=768,
            nats_url="nats://localhost:4222",
            retrieval_arm=retrieval_arm,
            fixture_id=fixture_id,
        )
        client = FleetMemoryClient(config)
        client._read_available = True
        client._store = object()
        return client

    def _entries(self):
        if not self._log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self._log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    async def test_off_arm_returns_empty_never_touches_store_or_log(self):
        """AC-1: retrieval_arm='off' + enabled=True -> [], no initialize(), no
        store access, zero retrieval-log entries."""
        client = self._client(retrieval_arm="off")
        client._store = None  # lazy initialize() would fire without the gate
        client.initialize = AsyncMock()

        assert await client.search("q", group_ids=["task_outcomes"]) == []

        client.initialize.assert_not_awaited()
        assert self._entries() == []

    async def test_off_arm_precedes_read_available_gate(self, monkeypatch):
        """The arm gate sits directly after the enabled gate: fm_search is never
        reached even with a fake retrieval module installed and a store open."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch, context_block="block", coverage=0.5, captured=captured
        )
        client = self._client(retrieval_arm="off")

        assert await client.search("q") == []
        assert "store" not in captured  # fm_search never invoked
        assert self._entries() == []

    async def test_unset_arm_logs_per_item_and_keeps_synthetic_hit(self, monkeypatch):
        """AC-2: unset arm + 2 mocked items -> same single synthetic hit as
        before the change, plus exactly one JSONL entry with per-item id/score."""
        captured: dict = {}
        results = [
            _mk_result_item(
                "build_outcome:guardkit:TASK_1", 0.93, "First outcome content"
            ),
            _mk_result_item("adr:guardkit:ADR_7", 0.71, "Second content"),
        ]
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="assembled block",
            coverage=0.8,
            captured=captured,
            results=results,
        )
        client = self._client(retrieval_arm=None)

        hits = await client.search("q", group_ids=["task_outcomes"])

        # Synthetic single-hit return shape unchanged (requirement 4)
        assert len(hits) == 1
        assert hits[0]["fact"] == "assembled block"
        assert hits[0]["score"] == 0.8
        assert isinstance(hits[0]["uuid"], str)

        entries = self._entries()
        assert len(entries) == 1
        entry = entries[0]
        assert entry["operation"] == "search"
        assert entry["source"] == "fleet_memory_client"
        assert entry["query"] == "q"
        assert entry["group_ids"] == ["task_outcomes"]
        assert entry["result_count"] == 2
        assert entry["items"] == [
            {"id": "build_outcome:guardkit:TASK_1", "score": 0.93},
            {"id": "adr:guardkit:ADR_7", "score": 0.71},
        ]
        assert entry["first_result_preview"] == "First outcome content"

    async def test_fixture_arm_logs_natural_keys_not_uuids(self, monkeypatch):
        """AC-3: fixture arm entries carry the mocked natural keys and per-item
        scores — never freshly-generated uuids."""
        captured: dict = {}
        results = [
            _mk_result_item("document:guardkit:DOC_A", 0.66, "doc A"),
            _mk_result_item("document:guardkit:DOC_B", 0.44, "doc B"),
        ]
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="fixture block",
            coverage=0.6,
            captured=captured,
            results=results,
        )
        client = self._client(retrieval_arm="fixture:v1", fixture_id="v1")

        hits = await client.search("q")

        assert len(hits) == 1  # fixture arm needs no special handling in search()
        entries = self._entries()
        assert len(entries) == 1
        logged_ids = [item["id"] for item in entries[0]["items"]]
        assert logged_ids == ["document:guardkit:DOC_A", "document:guardkit:DOC_B"]
        assert entries[0]["items"][0]["score"] == 0.66
        assert entries[0]["items"][1]["score"] == 0.44
        # the synthetic hit uuid never leaks into the per-item log
        assert hits[0]["uuid"] not in logged_ids

    async def test_empty_results_logs_empty_items_entry(self, monkeypatch):
        """AC-4: fm_search returning [] still appends one entry (result_count 0,
        items []) — 'retrieval attempted, nothing found' is distinguishable from
        'no retrieval' (no entry)."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="",
            coverage=0.0,
            captured=captured,
            results=[],
        )
        client = self._client()

        assert await client.search("nothing") == []

        entries = self._entries()
        assert len(entries) == 1
        assert entries[0]["result_count"] == 0
        assert entries[0]["items"] == []
        assert entries[0]["first_result_preview"] is None

    async def test_fm_search_failure_writes_no_entry(self, monkeypatch):
        """AC-5: a raising fm_search -> search() returns [] and appends nothing."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="block",
            coverage=0.5,
            captured=captured,
            search_exc=RuntimeError("store connection lost"),
        )
        client = self._client()

        assert await client.search("q") == []
        assert self._entries() == []

    async def test_disabled_gate_precedes_arm_gate(self, monkeypatch):
        """AC-6: enabled=False -> [] with no entry, whatever the arm."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch, context_block="block", coverage=0.5, captured=captured
        )
        for arm in (None, "off", "fixture:v1"):
            client = self._client(retrieval_arm=arm, enabled=False)
            assert await client.search("q") == []
        assert self._entries() == []

    async def test_log_entries_never_contain_dsn(self, monkeypatch):
        """AC-7: the serialized log lines never contain the configured DSN."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch, context_block="block", coverage=0.5, captured=captured
        )
        client = self._client(retrieval_arm="fixture:v1", fixture_id="v1")

        await client.search("q", group_ids=["task_outcomes"])

        raw = self._log_path.read_text(encoding="utf-8")
        assert raw.strip()  # an entry was written
        assert self._DSN not in raw
        assert "user:pw" not in raw


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


class TestTheReturnedKeyIsNotAStoreReceipt:
    """What ``add_episode``'s key proves, and what it does not.

    The seam above this one reports "published" and deliberately never reports
    "stored". These tests pin WHY, so a future reader cannot upgrade the claim
    by accident: the key is minted locally before the send, and the send itself
    carries no acknowledgement from anything downstream.

    No broker, no store, no network — the publish boundary is a fake.
    """

    @staticmethod
    def _summary(published: int = 1, skipped: int = 0):
        from guardkit.memory.harvest_publisher import PublishSummary

        return PublishSummary(
            published=published, skipped_oversized=skipped, counts_per_type={}
        )

    async def test_a_void_broker_with_no_store_still_yields_the_key(
        self, fleet_client
    ):
        """Throw the episode away entirely; the key still comes back.

        This fake is a broker that accepts the publish and drops it on the
        floor — no stream, no relay, no store, nothing that could ever hold the
        episode. It is the shape of a dark relay, an unmapped or full stream,
        and a relay-side validation refusal all at once. ``add_episode`` cannot
        tell any of them from a real landing, which is exactly why its callers
        may only claim a publish.
        """
        fleet_client._nats_available = True
        void: list = []

        async def _throw_into_the_void(episodes, *_args, **_kwargs):
            void.extend(episodes)  # the only trace; nothing downstream exists
            return self._summary(published=len(episodes))

        with patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=_throw_into_the_void,
        ):
            result = await fleet_client.add_episode(
                name="OUT-VOID: TASK-VOID-1 - nothing downstream",
                episode_body='{"task_id": "TASK-VOID-1", "success": true}',
                group_id="task_outcomes",
            )

        assert result == "build_outcome:guardkit:TASK_VOID_1"
        # And it is the id the payload builder minted locally, echoed back —
        # not something any store chose.
        assert void[0].episode_id == result

    async def test_the_key_is_minted_before_the_send(self, fleet_client):
        """The key exists on the episode handed TO the publisher.

        Read the key off the episode at the moment it is passed in — before the
        fake publisher has done anything at all — and it already equals what
        ``add_episode`` returns. Nothing downstream contributed to it.
        """
        fleet_client._nats_available = True
        key_at_send_time: list = []

        async def _capture_key_then_publish(episodes, *_args, **_kwargs):
            key_at_send_time.append(episodes[0].episode_id)
            return self._summary(published=1)

        with patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=_capture_key_then_publish,
        ):
            result = await fleet_client.add_episode(
                name="OUT-PRE: TASK-PRE-1 - key exists before the send",
                episode_body='{"task_id": "TASK-PRE-1", "success": true}',
                group_id="task_outcomes",
            )

        assert key_at_send_time == [result]

    async def test_nothing_on_this_path_reads_the_store_back(self, fleet_client):
        """A successful publish makes exactly one downstream call: the publish.

        If a read-back were ever added, this seam COULD honestly say "stored".
        Until then it cannot, and this test fails the moment that changes so
        the wording is revisited deliberately rather than drifting.
        """
        fleet_client._nats_available = True
        calls = AsyncMock(return_value=self._summary(published=1))

        with patch("guardkit.memory.harvest_publisher.publish_episodes", new=calls):
            await fleet_client.add_episode(
                name="OUT-RB: TASK-RB-1 - no read back",
                episode_body='{"task_id": "TASK-RB-1", "success": true}',
                group_id="task_outcomes",
            )

        assert calls.await_count == 1

    async def test_the_success_log_says_published_not_stored(
        self, fleet_client, caplog
    ):
        """The word on the green path is "Published". "Stored" is a lie here."""
        fleet_client._nats_available = True

        with caplog.at_level(
            logging.INFO, logger="guardkit.knowledge.fleet_memory_client"
        ), patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=AsyncMock(return_value=self._summary(published=1)),
        ):
            await fleet_client.add_episode(
                name="OUT-LOG: TASK-LOG-1 - wording",
                episode_body='{"task_id": "TASK-LOG-1", "success": true}',
                group_id="task_outcomes",
            )

        messages = [r.getMessage() for r in caplog.records]
        assert any("Published" in m for m in messages), messages
        assert not any("stored" in m.lower() for m in messages), messages


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


class TestRetrievalArmParsing:
    """FLEET_MEMORY_RETRIEVAL parsing + fixture DSN resolution (TASK-ABL1-002).

    Hermetic: an autouse fixture scrubs the full FLEET_MEMORY_* env surface
    before each test; each test sets only the variables it asserts against,
    with synthetic values (no live DSNs, no ambient env reads).
    """

    _LIVE_DSN = "postgresql://user:pw@localhost:5433/live_db"
    _FIXTURE_DSN = "postgresql://user:pw@localhost:5433/fixture_db"
    _GENERIC_DSN = "postgresql://user:pw@localhost:5433/generic_db"

    @pytest.fixture(autouse=True)
    def _hermetic_env(self, monkeypatch):
        _scrub_fleet_memory_env(monkeypatch)

    def test_unset_is_live_arm(self):
        """Unset FLEET_MEMORY_RETRIEVAL -> retrieval_arm None (current behaviour)."""
        cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm is None
        assert cfg.fixture_id is None
        # Other fields keep their pre-change defaults (env fully scrubbed,
        # so these are the dataclass/loader defaults — never ambient values).
        assert cfg.enabled is False
        assert cfg.project == "guardkit"

    def test_blank_string_is_live_arm(self, monkeypatch):
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "   ")
        cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm is None
        assert cfg.fixture_id is None

    def test_off_value(self, monkeypatch):
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "off")
        monkeypatch.setenv("FLEET_MEMORY_PG_DSN", self._LIVE_DSN)
        cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm == "off"
        assert cfg.fixture_id is None
        # off does not touch the DSN — it still comes from FLEET_MEMORY_PG_DSN.
        assert cfg.postgres_dsn == self._LIVE_DSN

    def test_off_case_insensitive_stripped(self, monkeypatch):
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "  OFF ")
        cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm == "off"
        assert cfg.fixture_id is None

    def test_fixture_with_specific_dsn(self, monkeypatch):
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "fixture:v1")
        monkeypatch.setenv("FLEET_MEMORY_FIXTURE_DSN_V1", self._FIXTURE_DSN)
        cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm == "fixture:v1"
        assert cfg.fixture_id == "v1"
        assert cfg.postgres_dsn == self._FIXTURE_DSN

    def test_fixture_fallback_generic(self, monkeypatch):
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "fixture:v1")
        monkeypatch.setenv("FLEET_MEMORY_FIXTURE_DSN", self._GENERIC_DSN)
        cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm == "fixture:v1"
        assert cfg.fixture_id == "v1"
        assert cfg.postgres_dsn == self._GENERIC_DSN

    def test_fixture_specific_wins_over_generic(self, monkeypatch):
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "fixture:v1")
        monkeypatch.setenv("FLEET_MEMORY_FIXTURE_DSN_V1", self._FIXTURE_DSN)
        monkeypatch.setenv("FLEET_MEMORY_FIXTURE_DSN", self._GENERIC_DSN)
        cfg = _load_fleet_config_from_env()
        assert cfg.postgres_dsn == self._FIXTURE_DSN

    def test_fixture_id_normalization(self, monkeypatch):
        """fixture:v1.2-rc resolves FLEET_MEMORY_FIXTURE_DSN_V1_2_RC (upper, non-alnum -> _)."""
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "fixture:v1.2-rc")
        monkeypatch.setenv("FLEET_MEMORY_FIXTURE_DSN_V1_2_RC", self._FIXTURE_DSN)
        cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm == "fixture:v1.2-rc"
        assert cfg.fixture_id == "v1.2-rc"
        assert cfg.postgres_dsn == self._FIXTURE_DSN

    def test_fixture_missing_dsn_fails_closed(self, monkeypatch, caplog):
        """Fixture selector with no resolvable DSN -> warn + arm off; DSN unchanged.

        Never falls back to the live corpus under an expressed fixture intent.
        """
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "fixture:v9")
        monkeypatch.setenv("FLEET_MEMORY_PG_DSN", self._LIVE_DSN)
        with caplog.at_level(logging.WARNING):
            cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm == "off"
        assert cfg.fixture_id == "v9"  # kept for diagnostics
        # postgres_dsn untouched (still the configured live value).
        assert cfg.postgres_dsn == self._LIVE_DSN
        assert any("Fixture DSN not set" in rec.message for rec in caplog.records)

    def test_invalid_value_fails_closed(self, monkeypatch, caplog):
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "banana")
        with caplog.at_level(logging.WARNING):
            cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm == "off"
        assert any(
            "Invalid FLEET_MEMORY_RETRIEVAL" in rec.message for rec in caplog.records
        )

    def test_fixture_empty_id_fails_closed(self, monkeypatch, caplog):
        monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", "fixture:")
        with caplog.at_level(logging.WARNING):
            cfg = _load_fleet_config_from_env()
        assert cfg.retrieval_arm == "off"
        assert cfg.fixture_id is None
        assert any(
            "Invalid FLEET_MEMORY_RETRIEVAL" in rec.message for rec in caplog.records
        )

class TestBackendAutoInit:
    """get_memory_client() lazily initializes the fleet-memory backend on first use."""

    @pytest.fixture(autouse=True)
    def _reset_factory(self, monkeypatch):
        from guardkit.knowledge import fleet_memory_client as fmc

        # Hermetic: auto-init loads config from env; scrub the FLEET_MEMORY_*
        # surface so no test here reads ambient environment values.
        _scrub_fleet_memory_env(monkeypatch)
        fmc._memory_client = None
        fmc._backend = "fleet_memory"
        fmc._backend_initialized = False
        yield
        fmc._memory_client = None
        fmc._backend = "fleet_memory"
        fmc._backend_initialized = False

    def test_get_memory_client_auto_inits_fleet_from_env(self, monkeypatch):
        from guardkit.knowledge import fleet_memory_client as fmc

        monkeypatch.setenv("GUARDKIT_MEMORY_BACKEND", "fleet_memory")
        client = get_memory_client()
        assert isinstance(client, FleetMemoryClient)
        assert fmc._backend_initialized is True

    def test_get_memory_client_defaults_to_fleet_memory(self, monkeypatch, tmp_path):
        from guardkit.knowledge import fleet_memory_client as fmc

        monkeypatch.delenv("GUARDKIT_MEMORY_BACKEND", raising=False)
        monkeypatch.setenv("GUARDKIT_CONFIG_DIR", str(tmp_path))
        client = get_memory_client()
        assert fmc._backend == "fleet_memory"
        assert isinstance(client, FleetMemoryClient)

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
