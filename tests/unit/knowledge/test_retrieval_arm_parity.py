"""Arm-parity acceptance tests through the AutoBuild context chain (TASK-ABL1-004).

FEAT-ABL-001's acceptance is stated at the chain level: the retrieval arm
switch must change *retrieval only*, never the code path. These tests drive
the composed chain

    AutoBuildContextLoader.get_player_context
        -> JobContextRetriever.retrieve (+ TaskAnalyzer)
            -> FleetMemoryClient.search
                -> (mocked) fleet_memory.retrieval fm_search/assemble_context
                -> query_logger JSONL retrieval log

for the three arm states and assert:

- unset arm: current behaviour — result completes, >=1 retrieval-log entries
  with populated per-item ``items``;
- off arm: every ``client.search`` returned ``[]``, ZERO retrieval-log
  entries, and the loader is still fully constructed (``loader.retriever is
  not None`` — NOT the ``--no-context`` / ``FLEET_MEMORY_ENABLED=false``
  nulling);
- fixture arm: the DSN is swapped at config time and every logged entry's
  ``items`` carry the mocked natural keys and scores;
- parity: off and fixture runs traverse the identical loader code path —
  both construct a ``JobContextRetriever``, neither falls into the
  ``_empty_result`` graceful-degradation branch, and both reach
  ``_build_result`` (real ``AutoBuildContextResult`` with ``context.task_id``
  set and a non-zero budget total).

Hermetic (incident-retro hard rules): an autouse fixture scrubs the FULL
FLEET_MEMORY_* env surface, the retrieval JSONL log is redirected into
``tmp_path``, the ``fleet_memory.retrieval`` store surface is mocked, and
only synthetic DSNs appear anywhere. No production code is touched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from guardkit.knowledge.autobuild_context_loader import (
    AutoBuildContextLoader,
    AutoBuildContextResult,
)
from guardkit.knowledge.fleet_memory_client import (
    FleetMemoryClient,
    FleetMemoryConfig,
    _load_fleet_config_from_env,
)
from guardkit.knowledge.job_context_retriever import JobContextRetriever

# Same mocking approach as test_fleet_memory_client.py (task requirement):
# reuse its fake fleet_memory.retrieval installer, contract-shaped result
# factory and env scrubber rather than re-implementing them (no drift).
from tests.unit.knowledge.test_fleet_memory_client import (
    _install_fake_fleet_memory_retrieval,
    _mk_result_item,
    _scrub_fleet_memory_env,
)

# Synthetic DSNs only — never live credentials (hermeticity hard rule).
_LIVE_DSN = "postgresql://user:pw@localhost:5433/live_db"
_FIXTURE_DSN = "postgresql://user:pw@localhost:5433/fixture_db"

_TASK_ID = "TASK-PARITY-1"
_FEATURE_ID = "FEAT-ABL"

# Natural keys + scores the mocked store returns for every fm_search call.
_NATURAL_KEYS = ["build_outcome:guardkit:TASK_P1", "adr:guardkit:ADR_P2"]
_EXPECTED_ITEMS = [
    {"id": "build_outcome:guardkit:TASK_P1", "score": 0.91},
    {"id": "adr:guardkit:ADR_P2", "score": 0.72},
]


def _mocked_results():
    """Fresh contract-shaped fm_search results (per test — no shared state)."""
    return [
        _mk_result_item("build_outcome:guardkit:TASK_P1", 0.91, "parity outcome one"),
        _mk_result_item("adr:guardkit:ADR_P2", 0.72, "parity adr two"),
    ]


@pytest.fixture(autouse=True)
def query_log_path(monkeypatch, tmp_path) -> Path:
    """Hermetic base: scrub the FLEET_MEMORY_* env surface and redirect the
    retrieval JSONL log into tmp_path (never the repo's .guardkit/)."""
    _scrub_fleet_memory_env(monkeypatch)
    log_path = tmp_path / "memory-query-log.jsonl"
    monkeypatch.setattr(
        "guardkit.knowledge.query_logger._get_log_path",
        lambda base_dir=None: log_path,
    )
    return log_path


def _entries(log_path: Path) -> List[Dict[str, Any]]:
    """Parse the JSONL retrieval log written during a run."""
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _make_client(
    retrieval_arm: str | None = None,
    fixture_id: str | None = None,
    dsn: str = _LIVE_DSN,
) -> FleetMemoryClient:
    """Real FleetMemoryClient with the store already 'open' (mocked seam), so
    the chain never attempts a live Postgres connection."""
    config = FleetMemoryConfig(
        enabled=True,
        postgres_dsn=dsn,
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


def _prepare_chain_client(client: FleetMemoryClient) -> "_PreparedChain":
    """Wrap a client for a chain run: record every search() return and count
    the loader's graceful-degradation branch."""
    return _PreparedChain(client)


class _PreparedChain:
    """Loader + client under observation for one chain run."""

    def __init__(self, client: FleetMemoryClient) -> None:
        self.client = client
        self.search_returns: List[List[Dict[str, Any]]] = []
        self.empty_result_calls: List[str] = []

        orig_search = client.search

        async def recording_search(*args, **kwargs):
            result = await orig_search(*args, **kwargs)
            self.search_returns.append(result)
            return result

        # Instance attribute shadows the bound method; client is test-local.
        client.search = recording_search  # type: ignore[method-assign]

        self.loader = AutoBuildContextLoader(graphiti=client)
        orig_empty = self.loader._empty_result

        def counting_empty_result(task_id: str) -> AutoBuildContextResult:
            self.empty_result_calls.append(task_id)
            return orig_empty(task_id)

        self.loader._empty_result = counting_empty_result  # type: ignore[method-assign]

    async def run(self) -> AutoBuildContextResult:
        """Drive the composed Player-context path (turn 1, no worktree: the
        turn-continuation and template-pattern branches are no-ops by design
        in EVERY arm — reaching _build_result is the parity evidence)."""
        return await self.loader.get_player_context(
            task_id=_TASK_ID,
            feature_id=_FEATURE_ID,
            turn_number=1,
            description="Implement retrieval arm parity checks",
            tech_stack="python",
        )

    def assert_full_loader_path(self, result: AutoBuildContextResult) -> None:
        """Common parity assertions: the loader was fully constructed and the
        run reached _build_result without the graceful-degradation branch."""
        assert isinstance(result, AutoBuildContextResult)
        assert self.loader.retriever is not None
        assert isinstance(self.loader.retriever, JobContextRetriever)
        assert self.empty_result_calls == []
        # _build_result evidence: real task_id + a real (non-zero) budget
        # total from the calculator (_empty_result would give 0/0).
        assert result.context.task_id == _TASK_ID
        assert result.budget_total > 0


class TestArmParityThroughLoaderChain:
    """Composed arm behaviour through AutoBuildContextLoader.get_player_context."""

    async def test_unset_arm_current_behaviour_logs_items(
        self, monkeypatch, query_log_path
    ):
        """AC-1: unset arm — the chain completes, the retriever is constructed,
        and >=1 retrieval-log entries with populated per-item ids/scores are
        written (aggregate assertion: the retriever issues several searches)."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="## Parity context block",
            coverage=0.8,
            captured=captured,
            results=_mocked_results(),
        )
        chain = _prepare_chain_client(_make_client(retrieval_arm=None))

        result = await chain.run()

        chain.assert_full_loader_path(result)
        # Retrieval genuinely reached the (mocked) store.
        assert "store" in captured
        entries = _entries(query_log_path)
        assert len(entries) >= 1
        for entry in entries:
            assert entry["operation"] == "search"
            assert entry["source"] == "fleet_memory_client"
            assert entry["items"] == _EXPECTED_ITEMS

    async def test_off_arm_empty_searches_zero_log_loader_constructed(
        self, monkeypatch, query_log_path
    ):
        """AC-2: off arm — the same call completes with the loader still fully
        constructed (NOT the --no-context / FLEET_MEMORY_ENABLED=false nulling),
        client.search returned [] for EVERY query, the mocked store was never
        touched, and the retrieval log has ZERO entries."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="## Parity context block",
            coverage=0.8,
            captured=captured,
            results=_mocked_results(),
        )
        chain = _prepare_chain_client(_make_client(retrieval_arm="off"))

        result = await chain.run()

        chain.assert_full_loader_path(result)
        # The chain really did query — several searches, all gated to [].
        assert len(chain.search_returns) >= 1
        assert all(r == [] for r in chain.search_returns)
        # fm_search was never invoked (gate precedes the store seam) ...
        assert "store" not in captured
        # ... and zero retrieval-log entries were written.
        assert _entries(query_log_path) == []
        # Off arm returns an empty-but-real context, not a degraded one.
        assert result.budget_used == 0
        assert result.categories_populated == []

    async def test_fixture_arm_logs_natural_keys_and_scores(
        self, monkeypatch, query_log_path
    ):
        """AC-3: fixture arm — the chain completes and every logged entry's
        items carry the mocked natural keys and scores (config already holds
        the swapped fixture DSN; search() needs no special handling)."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="## Fixture parity block",
            coverage=0.6,
            captured=captured,
            results=_mocked_results(),
        )
        chain = _prepare_chain_client(
            _make_client(
                retrieval_arm="fixture:v1", fixture_id="v1", dsn=_FIXTURE_DSN
            )
        )

        result = await chain.run()

        chain.assert_full_loader_path(result)
        entries = _entries(query_log_path)
        assert len(entries) >= 1
        for entry in entries:
            assert [item["id"] for item in entry["items"]] == _NATURAL_KEYS
            assert [item["score"] for item in entry["items"]] == [0.91, 0.72]
        # The synthetic DSN never leaks into the log content.
        raw = query_log_path.read_text(encoding="utf-8")
        assert _FIXTURE_DSN not in raw
        assert "user:pw" not in raw

    async def test_off_and_fixture_arms_identical_loader_path(self, monkeypatch):
        """AC-4 parity: off and fixture runs both return a real
        AutoBuildContextResult (no exception, no None) from the identical
        loader code path — both constructed a JobContextRetriever, neither
        short-circuited via the _empty_result graceful-degradation branch,
        and both reached _build_result."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="## Parity context block",
            coverage=0.7,
            captured=captured,
            results=_mocked_results(),
        )

        off_chain = _prepare_chain_client(_make_client(retrieval_arm="off"))
        fixture_chain = _prepare_chain_client(
            _make_client(
                retrieval_arm="fixture:v1", fixture_id="v1", dsn=_FIXTURE_DSN
            )
        )

        off_result = await off_chain.run()
        fixture_result = await fixture_chain.run()

        for chain, result in (
            (off_chain, off_result),
            (fixture_chain, fixture_result),
        ):
            assert result is not None
            chain.assert_full_loader_path(result)

        # Same budget envelope from the same calculator path — the arms only
        # diverge in what retrieval returned, never in how far the chain ran.
        assert off_result.budget_total == fixture_result.budget_total


class TestEnvDrivenArmContract:
    """P4 env contract end-to-end: rollouts set FLEET_MEMORY_RETRIEVAL (env
    vars, not dataclasses); _load_fleet_config_from_env() must produce the
    config that drives the chain into the asserted arm behaviour."""

    @pytest.mark.parametrize("arm_env", [None, "off", "fixture:v1"])
    async def test_env_driven_arm_end_to_end(
        self, monkeypatch, query_log_path, arm_env
    ):
        monkeypatch.setenv("FLEET_MEMORY_ENABLED", "true")
        monkeypatch.setenv("FLEET_MEMORY_PG_DSN", _LIVE_DSN)
        if arm_env is not None:
            monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", arm_env)
        if arm_env == "fixture:v1":
            monkeypatch.setenv("FLEET_MEMORY_FIXTURE_DSN_V1", _FIXTURE_DSN)

        config = _load_fleet_config_from_env()
        assert config.enabled is True

        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="## Env-driven parity block",
            coverage=0.8,
            captured=captured,
            results=_mocked_results(),
        )
        client = FleetMemoryClient(config)
        client._read_available = True
        client._store = object()
        chain = _prepare_chain_client(client)

        result = await chain.run()

        # Every arm traverses the full loader path (chain-level parity).
        chain.assert_full_loader_path(result)

        entries = _entries(query_log_path)
        if arm_env is None:
            # Live arm: current behaviour + per-item logging.
            assert config.retrieval_arm is None
            assert config.postgres_dsn == _LIVE_DSN
            assert len(entries) >= 1
            assert all(e["items"] == _EXPECTED_ITEMS for e in entries)
        elif arm_env == "off":
            assert config.retrieval_arm == "off"
            assert config.postgres_dsn == _LIVE_DSN  # off never swaps the DSN
            assert all(r == [] for r in chain.search_returns)
            assert entries == []
            assert "store" not in captured
        else:  # fixture:v1
            assert config.retrieval_arm == "fixture:v1"
            assert config.fixture_id == "v1"
            assert config.postgres_dsn == _FIXTURE_DSN  # DSN swapped by config
            assert len(entries) >= 1
            for entry in entries:
                assert [i["id"] for i in entry["items"]] == _NATURAL_KEYS
