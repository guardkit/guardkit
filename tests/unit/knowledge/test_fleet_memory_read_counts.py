"""The memory client counts its reads: completed and failed (2026-10-04).

A failed read returns an empty list, exactly like a search that found
nothing. The two counters are what let the per-turn memory line tell them
apart. A read skipped on purpose counts as neither.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from guardkit.knowledge.fleet_memory_client import FleetMemoryClient, FleetMemoryConfig


@pytest.fixture
def stand_in(monkeypatch):
    state = SimpleNamespace(connect_fails=False, search_fails=False)

    class StoreContext:
        def __init__(self, settings):
            pass

        async def __aenter__(self):
            if state.connect_fails:
                raise ConnectionError("refused")
            return object()

        async def __aexit__(self, *exc):
            return False

    async def search(request, store):
        if state.search_fails:
            raise RuntimeError("search broke")
        return [SimpleNamespace(score=0.9, value={"natural_key": "k", "content": "c"})]

    retrieval = types.ModuleType("fleet_memory.retrieval")
    retrieval.SearchRequest = lambda **fields: fields
    retrieval.search = search
    settings = types.ModuleType("fleet_memory.settings")
    settings.Settings = lambda **fields: fields
    store = types.ModuleType("fleet_memory.store")
    store.async_store_context = StoreContext
    package = types.ModuleType("fleet_memory")
    package.retrieval, package.settings, package.store = retrieval, settings, store
    for name, module in (("fleet_memory", package), ("fleet_memory.retrieval", retrieval),
                         ("fleet_memory.settings", settings), ("fleet_memory.store", store)):
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr("guardkit.knowledge.query_logger.log_query", lambda **kw: None)
    return state


def _client(**overrides):
    config = dict(enabled=True, project="demo", postgres_dsn="postgresql://t:t@localhost:1/x")
    config.update(overrides)
    return FleetMemoryClient(FleetMemoryConfig(**config))


@pytest.mark.asyncio
async def test_a_completed_search_is_counted_with_or_without_results(stand_in):
    client = _client()
    assert len(await client.search("q", group_ids=["task_outcomes"])) == 1
    assert client.reads == {"completed": 1, "failed": 0}


@pytest.mark.asyncio
async def test_a_failed_lazy_connection_is_a_failed_read(stand_in):
    stand_in.connect_fails = True
    client = _client()
    assert await client.search("q", group_ids=["task_outcomes"]) == []
    assert client.reads == {"completed": 0, "failed": 1}


@pytest.mark.asyncio
async def test_a_search_error_is_a_failed_read(stand_in):
    stand_in.search_fails = True
    client = _client()
    assert await client.search("q", group_ids=["task_outcomes"]) == []
    assert client.reads == {"completed": 0, "failed": 1}


@pytest.mark.asyncio
async def test_a_refused_request_is_a_failed_read(stand_in):
    client = _client(project=None)  # no memory name: the client refuses
    assert await client.search("q", group_ids=["task_outcomes"]) == []
    client2 = _client()
    assert await client2.search("q", document_source_tags="not-a-list") == []
    assert client.reads["failed"] == 1 and client2.reads["failed"] == 1


@pytest.mark.asyncio
async def test_reads_skipped_on_purpose_count_as_neither(stand_in):
    off = _client(enabled=False)
    arm_off = _client(retrieval_arm="off")
    retired = _client()
    await off.search("q", group_ids=["task_outcomes"])
    await arm_off.search("q", group_ids=["task_outcomes"])
    await retired.search("q", group_ids=["role_constraints"])
    for client in (off, arm_off, retired):
        assert client.reads == {"completed": 0, "failed": 0}
