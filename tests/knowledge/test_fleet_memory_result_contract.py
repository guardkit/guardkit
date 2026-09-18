"""Regression controls for Fleet result relevance and category budget granularity."""
from __future__ import annotations

import json
import sys
import types
from unittest.mock import patch

import pytest

from guardkit.knowledge.fleet_memory_client import FleetMemoryClient, FleetMemoryConfig
from guardkit.knowledge.job_context_retriever import JobContextRetriever


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> FleetMemoryClient:
    monkeypatch.setattr(FleetMemoryClient, "_check_nats_available", lambda self: False)
    monkeypatch.setattr(
        "guardkit.knowledge.query_logger._get_log_path",
        lambda base_dir=None: tmp_path / "memory-query-log.jsonl",
    )
    client = FleetMemoryClient(
        FleetMemoryConfig(
            enabled=True,
            postgres_dsn="postgresql://fixture:fixture@invalid/memory",
            embed_url="http://invalid:9000",
            embed_model="fixture",
            embed_dims=8,
            nats_url="nats://disabled.invalid:1",
        )
    )
    client._read_available = True
    client._store = object()
    return client


def _install_results(monkeypatch: pytest.MonkeyPatch, results: list[object]) -> None:
    class SearchRequest:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def search(request, store):
        return results

    retrieval = types.ModuleType("fleet_memory.retrieval")
    retrieval.SearchRequest = SearchRequest
    retrieval.search = search
    fleet_memory = types.ModuleType("fleet_memory")
    fleet_memory.retrieval = retrieval
    monkeypatch.setitem(sys.modules, "fleet_memory", fleet_memory)
    monkeypatch.setitem(sys.modules, "fleet_memory.retrieval", retrieval)


def _item(key: str, score: object, content: object) -> object:
    return types.SimpleNamespace(
        score=score,
        value={"natural_key": key, "content": content},
    )


@pytest.mark.asyncio
async def test_search_returns_actual_result_relevance_and_identity(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    _install_results(
        monkeypatch,
        [
            _item("document:guardkit:short", 0.91, "short strong context"),
            _item("document:guardkit:long", 0.62, "second relevant context"),
        ],
    )

    hits = await client.search("full task body", group_ids=["patterns"])

    assert hits == [
        {
            "fact": "short strong context",
            "uuid": "document:guardkit:short",
            "score": 0.91,
        },
        {
            "fact": "second relevant context",
            "uuid": "document:guardkit:long",
            "score": 0.62,
        },
    ]


@pytest.mark.asyncio
async def test_search_caps_valid_hits_and_uses_zero_for_malformed_scores(
    monkeypatch, tmp_path
):
    client = _client(monkeypatch, tmp_path)
    _install_results(
        monkeypatch,
        [
            _item("blank", 0.99, ""),
            _item("none", None, "first"),
            _item("nan", float("nan"), "second"),
            _item("bad", "not-a-score", "third"),
        ],
    )

    hits = await client.search("q", num_results=2)

    assert [hit["uuid"] for hit in hits] == ["none", "nan"]
    assert [hit["score"] for hit in hits] == [0.0, 0.0]
    entry = json.loads((tmp_path / "memory-query-log.jsonl").read_text().strip())
    assert entry["items"][1]["score"] == 0.0
    assert entry["items"][2]["score"] == 0.0
    assert entry["items"][3]["score"] == 0.0


@pytest.mark.asyncio
async def test_retriever_filters_on_source_relevance_not_budget_fill(
    monkeypatch, tmp_path
):
    client = _client(monkeypatch, tmp_path)
    _install_results(
        monkeypatch,
        [_item("document:guardkit:relevant", 0.88, "compact useful context")],
    )
    retriever = JobContextRetriever(client)

    results, tokens = await retriever._query_category(
        query="full task body",
        group_ids=["patterns"],
        budget_allocation=200,
        threshold=0.5,
        category="relevant_patterns",
    )

    assert [item["uuid"] for item in results] == ["document:guardkit:relevant"]
    assert tokens > 0


def test_budget_packing_skips_oversized_item_and_keeps_smaller_results():
    retriever = JobContextRetriever(object())
    oversized = {"fact": "x" * 500, "uuid": "large", "score": 0.99}
    small_one = {"fact": "useful one", "uuid": "one", "score": 0.90}
    small_two = {"fact": "useful two", "uuid": "two", "score": 0.80}

    trimmed, tokens = retriever._trim_to_budget(
        [oversized, small_one, small_two], budget=80
    )

    assert [item["uuid"] for item in trimmed] == ["one", "two"]
    assert 0 < tokens <= 80
