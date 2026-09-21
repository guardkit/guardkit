"""Regression controls for Fleet result relevance and category budget granularity."""
from __future__ import annotations

import json
import sys
import types
from unittest.mock import patch

import pytest

from guardkit.knowledge.fleet_memory_client import FleetMemoryClient, FleetMemoryConfig
from guardkit.knowledge.job_context_retriever import JobContextRetriever, RetrievedContext


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
            project="guardkit",
        )
    )
    client._read_available = True
    client._store = object()
    return client


def _install_results(
    monkeypatch: pytest.MonkeyPatch,
    results: list[object],
    captured: dict[str, object] | None = None,
) -> None:
    class SearchRequest:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            if captured is not None:
                captured["request"] = kwargs

    async def search(request, store):
        if captured is not None:
            captured["store"] = store
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
@pytest.mark.parametrize("group_id", ["patterns", "unknown_group"])
async def test_explicit_retired_or_unknown_scope_never_searches_whole_store(
    monkeypatch, tmp_path, group_id
):
    client = _client(monkeypatch, tmp_path)
    captured: dict[str, object] = {}
    _install_results(
        monkeypatch,
        [_item("build_outcome:guardkit:unrelated", 0.99, "unrelated outcome")],
        captured,
    )

    assert await client.search("policy guidance", group_ids=[group_id]) == []
    assert captured == {}

@pytest.mark.asyncio
async def test_genuinely_unscoped_search_still_searches_corpus(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    captured: dict[str, object] = {}
    _install_results(
        monkeypatch,
        [_item("document:guardkit:useful", 0.81, "useful corpus document")],
        captured,
    )

    hits = await client.search("broad corpus query", group_ids=None)

    assert [hit["uuid"] for hit in hits] == ["document:guardkit:useful"]
    request = captured["request"]
    assert request["payload_types"] == []
    assert request["domain_tags"] == []

@pytest.mark.asyncio
async def test_mixed_scope_uses_only_migrated_mapping(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    captured: dict[str, object] = {}
    _install_results(
        monkeypatch,
        [_item("build_outcome:guardkit:task", 0.83, "task outcome")],
        captured,
    )

    hits = await client.search(
        "task result",
        group_ids=["patterns", "task_outcomes", "unknown_group"],
    )

    assert [hit["uuid"] for hit in hits] == ["build_outcome:guardkit:task"]
    request = captured["request"]
    assert request["payload_types"] == ["build_outcome", "document"]
    assert request["domain_tags"] == ["task"]

@pytest.mark.asyncio
async def test_search_threads_explicit_substantive_opt_in(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    captured: dict[str, object] = {}
    _install_results(
        monkeypatch,
        [_item("build_outcome:guardkit:substantive", 0.82, "actual lessons")],
        captured,
    )

    hits = await client.search(
        "task body",
        group_ids=["task_outcomes"],
        require_substantive=True,
    )

    assert [hit["uuid"] for hit in hits] == [
        "build_outcome:guardkit:substantive"
    ]
    assert captured["request"]["require_substantive"] is True

@pytest.mark.asyncio
async def test_retriever_opts_in_only_for_contextual_task_outcomes():
    class SupportingClient:
        supports_substantive_search = True

        def __init__(self):
            self.calls = []

        async def search(self, query, **kwargs):
            self.calls.append((query, kwargs))
            return [
                {
                    "fact": "actual lessons",
                    "uuid": "build_outcome:guardkit:substantive",
                    "score": 0.82,
                }
            ]

    client = SupportingClient()
    retriever = JobContextRetriever(client)

    await retriever._query_category(
        query="task body",
        group_ids=["task_outcomes"],
        budget_allocation=200,
        threshold=0.5,
        category="similar_outcomes",
    )
    await retriever._query_category(
        query="task body",
        group_ids=["project_architecture"],
        budget_allocation=200,
        threshold=0.5,
        category="architecture_context",
    )

    assert client.calls[0][1] == {
        "group_ids": ["task_outcomes"],
        "require_substantive": True,
    }
    assert client.calls[1][1] == {"group_ids": ["project_architecture"]}

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

    hits = await client.search("full task body", group_ids=["task_outcomes"])

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
        group_ids=["task_outcomes"],
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



def _rule_document(body: str, tag: str = "rules_example") -> str:
    inner = json.dumps(
        {
            "entity_type": "rule",
            "id": "example/guidance/database",
            "template_id": "example",
            "name": "Database guidance",
            "content": body,
        }
    )
    inner += "\n\n---\n_metadata:\n```json\n{}\n```"
    return json.dumps(
        {
            "content": inner,
            "domain_tags": [tag],
            "source_ref": tag,
        }
    )


@pytest.mark.asyncio
async def test_declared_document_source_returns_exact_provenance_sections(
    monkeypatch, tmp_path
):
    body = (
        "# Database guidance\n\n"
        "## Boundaries\n\n"
        "### ALWAYS\n"
        "- ✅ Use async SQLAlchemy queries and indexes.\n"
        "- Keep CRUD operations composable.\n\n"
        "## Code sample\n"
        "```python\n"
        "# not a markdown heading\n"
        "value = 1\n"
        "```\n\n"
        "## Header only\n"
    )
    client = _client(monkeypatch, tmp_path)
    captured: dict[str, object] = {}
    _install_results(
        monkeypatch,
        [_item("document:guardkit:rule-1", 0.73, _rule_document(body))],
        captured,
    )

    hits = await client.search(
        "async SQLAlchemy CRUD query",
        group_ids=[],
        document_source_tags=["rules_example"],
    )

    request = captured["request"]
    assert request["payload_types"] == ["document"]
    assert request["domain_tags"] == ["rules_example"]
    assert request["query"] == "async SQLAlchemy CRUD query"
    assert hits
    assert hits[0]["fact"].startswith("### ALWAYS\n")
    assert hits[0]["uuid"] == "document:guardkit:rule-1"
    assert hits[0]["source_ref"] == "rules_example"
    assert hits[0]["score"] == 0.73
    assert hits[0]["score_kind"] == "document"
    exact = body.encode("utf-8")[
        hits[0]["section_start_byte"] : hits[0]["section_end_byte"]
    ].decode("utf-8")
    assert exact == hits[0]["fact"]
    assert "# not a markdown heading" in next(
        hit["fact"] for hit in hits if hit["fact"].startswith("## Code sample")
    )
    assert not any(hit["fact"].startswith("## Header only") for hit in hits)

    retriever = JobContextRetriever(client)
    selected, used = retriever._trim_to_budget(hits, 709)
    assert selected and used <= 709
    assert selected[0]["fact"].startswith("### ALWAYS\n")
    rendered = RetrievedContext._format_item(None, selected[0])
    assert "Fleet source excerpt: rules_example" in rendered
    assert selected[0]["fact"] in rendered


@pytest.mark.asyncio
async def test_declared_document_source_fails_closed_on_invalid_scope(
    monkeypatch, tmp_path
):
    client = _client(monkeypatch, tmp_path)
    captured: dict[str, object] = {}
    _install_results(monkeypatch, [], captured)

    assert await client.search(
        "query", document_source_tags=["Rules_Not_Canonical"]
    ) == []
    assert captured == {}
    assert await client.search(
        "query",
        group_ids=["patterns"],
        document_source_tags=["rules_example"],
    ) == []
    assert captured == {}


@pytest.mark.asyncio
async def test_retriever_uses_declared_sources_only_for_relevant_patterns():
    class SupportingClient:
        supports_document_source_tags = True

        def __init__(self):
            self.calls = []

        async def search(self, query, **kwargs):
            self.calls.append((query, kwargs))
            return []

    client = SupportingClient()
    retriever = JobContextRetriever(
        client, relevant_pattern_document_tags=("rules_example",)
    )
    await retriever._query_category(
        "same query", ["patterns"], 709, 0.5, category="relevant_patterns"
    )
    await retriever._query_category(
        "same query", ["role_constraints"], 472, 0.5, category="role_constraints"
    )
    assert client.calls == [
        (
            "same query",
            {
                "group_ids": [],
                "document_source_tags": ["rules_example"],
            },
        ),
        ("same query", {"group_ids": ["role_constraints"]}),
    ]


def test_project_config_declares_bounded_relevant_pattern_sources(tmp_path):
    from guardkit.knowledge.autobuild_context_loader import (
        AutoBuildContextLoader,
        _load_relevant_pattern_document_tags,
    )

    config_dir = tmp_path / ".guardkit"
    config_dir.mkdir()
    config = config_dir / "config.yaml"
    config.write_text(
        "memory:\n"
        "  fleet:\n"
        "    context_sources:\n"
        "      relevant_patterns:\n"
        "        document_tags:\n"
        "          - rules_example\n"
    )
    assert _load_relevant_pattern_document_tags(tmp_path) == ("rules_example",)

    graphiti = types.SimpleNamespace(supports_document_source_tags=True)
    loader = AutoBuildContextLoader(graphiti=graphiti, worktree_path=tmp_path)
    assert loader.retriever.relevant_pattern_document_tags == ("rules_example",)

    config.write_text(
        "memory:\n"
        "  fleet:\n"
        "    context_sources:\n"
        "      relevant_patterns:\n"
        "        document_tags:\n"
        + "".join(f"          - rules_{i}\n" for i in range(9))
    )
    assert _load_relevant_pattern_document_tags(tmp_path) == ()
