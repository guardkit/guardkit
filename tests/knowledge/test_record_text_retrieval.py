"""Decision records and documents reach the builder as plain text (2026-10-23).

Fleet memory stores each record as its whole payload in JSON, and every search
hit carries that JSON string as ``fact``. The architecture category asks for
``adr`` and ``document`` records, and printed them through a JSON dump, so a
decision's text reached the builder as escaped JSON inside JSON, and was
costed that way against the small architecture share. Now both become plain
text (``{"content", "uuid", "score"}``) before the relevance line and the
trimming run, as build outcomes already did. Anything that cannot be decoded
is left as it came.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardkit.knowledge.job_context_retriever import (
    JobContextRetriever,
    RetrievedContext,
    _record_as_text,
)

DECISION = "Use one shared workspace for every package, managed by its own tool."
CONTEXT = "Several packages share models; separate installs drifted apart."
CONSEQUENCES = "One lock file; every package is installed together."
BODY = "## Layout\n\nThe service has three layers: routes, services and stores."


def _stored(payload: dict) -> str:
    """The ``content`` string exactly as fleet-memory's writer stores it:
    ``json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":"))``.
    ``payload_type`` is a class variable, so it is not in the dump."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _adr_payload(**overrides) -> dict:
    payload = {
        "alternatives": ["Separate installs per package", "One flat package"],
        "consequences": CONSEQUENCES,
        "context": CONTEXT,
        "decision": DECISION,
        "domain_tags": ["architecture"],
        "identifier": "ADR_DEMO_001",
        "project": "demo",
        "source_ref": "docs/architecture/decisions/ADR-DEMO-001.md",
        "status": "accepted",
        "supersedes": [],
        "title": "One shared workspace",
        "version": 1,
    }
    payload.update(overrides)
    return payload


def _document_payload(**overrides) -> dict:
    payload = {
        "content": BODY,
        "domain_tags": ["architecture"],
        "identifier": "architecture_overview",
        "project": "demo",
        "source_ref": "docs/architecture/ARCHITECTURE.md",
        "supersedes": [],
        "version": 1,
    }
    payload.update(overrides)
    return payload


def _hit(fact: str, key: str, score: float = 0.8) -> dict:
    """The hit shape the fleet memory client returns for every record."""
    return {"fact": fact, "uuid": key, "score": score}


def _retriever(hits):
    client = MagicMock()
    client.search = AsyncMock(return_value=hits)
    return JobContextRetriever(client, cache_ttl=0)


def _architecture_prompt(items) -> str:
    return RetrievedContext(
        task_id="TASK-DEMO-001",
        budget_used=0,
        budget_total=4000,
        feature_context=[],
        similar_outcomes=[],
        relevant_patterns=[],
        architecture_context=items,
        warnings=[],
        domain_knowledge=[],
    ).to_prompt()


async def _architecture(hits, budget=2000):
    retriever = _retriever(hits)
    items, tokens = await retriever._query_category(
        "query",
        list(JobContextRetriever.ARCHITECTURE_GROUP_IDS),
        budget,
        0.5,
        category="architecture_context",
    )
    return retriever, items, tokens


@pytest.mark.asyncio
async def test_a_decision_record_reaches_the_builder_as_plain_text():
    hit = _hit(_stored(_adr_payload()), "adr:demo:ADR_DEMO_001")
    retriever, items, tokens = await _architecture([hit])

    assert len(items) == 1
    text = items[0]["content"]
    assert text.splitlines() == [
        "Decision record ADR_DEMO_001: One shared workspace (accepted)",
        f"Decision: {DECISION}",
        "Full record: docs/architecture/decisions/ADR-DEMO-001.md",
    ]
    # Compact (31 October 2026): context, consequences and alternatives stay in
    # the source file the record names.
    assert CONTEXT not in text and CONSEQUENCES not in text
    assert items[0]["uuid"] == "adr:demo:ADR_DEMO_001"

    prompt = _architecture_prompt(items)
    assert DECISION in prompt
    assert '\\"' not in prompt and '{"' not in prompt
    # Costed as the text, which is smaller than the escaped record.
    assert tokens == retriever._estimate_tokens(items[0])
    assert tokens < retriever._estimate_tokens(hit)


@pytest.mark.asyncio
async def test_a_document_reaches_the_builder_as_plain_text():
    hit = _hit(_stored(_document_payload()), "document:demo:architecture_overview")
    _, items, _ = await _architecture([hit])

    assert items[0]["content"] == f"Document: architecture_overview\n{BODY}"
    prompt = _architecture_prompt(items)
    assert "The service has three layers" in prompt
    assert '\\"' not in prompt and '{"' not in prompt


@pytest.mark.asyncio
async def test_more_records_fit_the_share_as_text():
    hits = [
        _hit(_stored(_adr_payload(identifier=f"ADR_DEMO_00{n}")), f"adr:demo:{n}", 0.9)
        for n in range(1, 4)
    ]
    one_record = JobContextRetriever(MagicMock())._estimate_tokens(hits[0])
    budget = one_record + one_record // 2  # one escaped record, not two
    _, items, tokens = await _architecture(hits, budget=budget)
    assert len(items) >= 2
    assert tokens <= budget


def test_a_record_without_a_typed_key_is_recognised_by_its_fields():
    adr = _record_as_text(_hit(_stored(_adr_payload()), "0b8e-random"))
    doc = _record_as_text(_hit(_stored(_document_payload()), "0b8e-random"))
    assert adr["content"].startswith("Decision record ADR_DEMO_001: One shared workspace")
    assert doc["content"].endswith(BODY)


def test_missing_optional_fields_are_left_out():
    payload = _adr_payload(
        title=None, context=None, consequences=None, alternatives=None, source_ref=None
    )
    text = _record_as_text(_hit(_stored(payload), "adr:demo:x"))["content"]
    assert text == f"Decision record ADR_DEMO_001 (accepted)\nDecision: {DECISION}"


@pytest.mark.parametrize(
    "fact",
    [
        "not json at all {",
        '"a bare json string"',
        "[1, 2, 3]",
        _stored(_document_payload(content=None)),
        _stored(_adr_payload(decision="  ")),
    ],
)
def test_undecodable_or_empty_records_fall_back_unchanged(fact):
    for key in ("adr:demo:x", "document:demo:x"):
        hit = _hit(fact, key)
        assert _record_as_text(hit) is hit


def test_other_record_types_are_left_alone():
    warning = _hit(
        _stored({"message": "Watch the lock", "severity": "high", "source_ref": "x"}),
        "warning:demo:w1",
    )
    assert _record_as_text(warning) is warning
    section = {**_hit(BODY, "document:demo:rules"), "score_kind": "document"}
    assert _record_as_text(section) is section


@pytest.mark.asyncio
async def test_undecodable_content_still_reaches_the_builder():
    hit = _hit("plain prose fact from another backend", "adr:demo:x")
    _, items, _ = await _architecture([hit])
    assert items == [hit]
    assert "plain prose fact from another backend" in _architecture_prompt(items)


def test_the_real_writer_shape_when_fleet_memory_is_installed():
    models = pytest.importorskip("fleet_memory.payloads.models")
    payload = models.ADRPayload(
        project="demo",
        identifier="ADR_DEMO_001",
        source_ref="docs/adr.md",
        decision=DECISION,
        status="accepted",
        title="One shared workspace",
        context=CONTEXT,
    )
    fact = json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":"))
    text = _record_as_text(_hit(fact, payload.natural_key))["content"]
    assert f"Decision: {DECISION}" in text and "Full record: docs/adr.md" in text
    assert CONTEXT not in text
    assert "{" not in text


# ---------------------------------------------------------------------------
# The budget charges the rendered text, not its JSON form
# ---------------------------------------------------------------------------

# Multi-line and non-ASCII: JSON escapes each line break as two characters
# and each of these letters as six, so a JSON-based charge is far higher.
NON_ASCII_BODY = "Ünïcödé façade — naïve café.\nZweite Zeile: Grüße.\nДругая строка."


def _rendered_document(body: str) -> tuple:
    """A stored document whose rendered text has an even length, and that
    text, so the charge is exactly ``len(text) / 2`` tokens."""
    hit = _hit(_stored(_document_payload(content=body)), "document:demo:doc")
    text = _record_as_text(hit)["content"]
    if len(text) % JobContextRetriever.CHARS_PER_TOKEN:
        body += "."
        hit = _hit(_stored(_document_payload(content=body)), "document:demo:doc")
        text = _record_as_text(hit)["content"]
    return hit, text


@pytest.mark.asyncio
async def test_a_rendered_document_fits_a_share_of_exactly_its_text():
    hit, text = _rendered_document(NON_ASCII_BODY)
    assert "\n" in text and "Ü" in text
    exact = len(text) // JobContextRetriever.CHARS_PER_TOKEN

    _, items, tokens = await _architecture([hit], budget=exact)
    assert [i["content"] for i in items] == [text]
    assert tokens == exact

    _, items, tokens = await _architecture([hit], budget=exact - 1)
    assert items == [] and tokens == 0


@pytest.mark.asyncio
async def test_a_rendered_decision_record_is_charged_on_its_text():
    payload = _adr_payload(
        context="Zeile eins: Gründe.\nLigne deux : raisons économiques.",
        decision="Behalte één database — überall.",
    )
    hit = _hit(_stored(payload), "adr:demo:x")
    text = _record_as_text(hit)["content"]
    exact = len(text) // JobContextRetriever.CHARS_PER_TOKEN
    _, items, tokens = await _architecture([hit], budget=exact)
    assert [i["content"] for i in items] == [text]
    assert tokens == exact
    # The JSON form of the same item would not have fitted.
    assert len(json.dumps(items[0])) // JobContextRetriever.CHARS_PER_TOKEN > exact


def test_other_items_keep_the_json_charge():
    retriever = JobContextRetriever(MagicMock())
    plain = {"content": NON_ASCII_BODY, "uuid": "k", "score": 0.9}
    assert retriever._estimate_tokens(plain) == max(
        1, len(json.dumps(plain, default=str)) // JobContextRetriever.CHARS_PER_TOKEN
    )



# ---------------------------------------------------------------------------
# Decisions searched apart, with their own cut-off (31 October 2026)
# ---------------------------------------------------------------------------
# Measured on 43 recorded tasks that cite 67 decisions: one shared search gave
# the builder 30 of them; documents took most of the results, and the 0.5 cut-off
# fell where the cited decisions score.


def _by_group(decisions, documents):
    """A memory whose decision group and document group answer differently."""

    async def search(query, group_ids=None, **kwargs):
        if group_ids == ["project_decisions"]:
            return decisions
        if group_ids == ["project_architecture"]:
            return documents
        return []

    client = MagicMock()
    client.search = AsyncMock(side_effect=search)
    return JobContextRetriever(client, cache_ttl=0)


async def _architecture_apart(decisions, documents, budget=2000, threshold=0.5):
    retriever = _by_group(decisions, documents)
    items, tokens = await retriever._query_category(
        "query",
        list(JobContextRetriever.ARCHITECTURE_GROUP_IDS),
        budget,
        threshold,
        category="architecture_context",
    )
    return retriever, items, tokens


def test_the_decision_group_reads_the_tag_decision_records_carry():
    from guardkit.knowledge.fleet_memory_mapping import resolve

    # guardkit memory seed, /system-arch and /system-plan tag them ``architecture``.
    assert "architecture" in resolve("project_decisions").domain_tags


@pytest.mark.asyncio
async def test_decisions_come_first_and_documents_keep_their_place():
    adr = _hit(_stored(_adr_payload()), "adr:demo:ADR_DEMO_001", score=0.6)
    doc = _hit(_stored(_document_payload()), "document:demo:overview", score=0.9)
    retriever, items, tokens = await _architecture_apart([adr, doc], [doc])

    assert [i["uuid"] for i in items] == ["adr:demo:ADR_DEMO_001", "document:demo:overview"]
    assert tokens == sum(retriever._estimate_tokens(i) for i in items)
    searched = [c.kwargs.get("group_ids") for c in retriever.graphiti.search.call_args_list]
    assert searched == [["project_decisions"], ["project_architecture"]]


@pytest.mark.asyncio
async def test_the_decisions_only_cut_off_is_045():
    near = _hit(_stored(_adr_payload()), "adr:demo:near", score=0.47)
    below = _hit(_stored(_adr_payload()), "adr:demo:below", score=0.44)
    doc = _hit(_stored(_document_payload()), "document:demo:overview", score=0.47)
    _, items, _ = await _architecture_apart([near, below], [doc], threshold=0.5)

    # A decision at 0.47 reaches the builder; a document at 0.47 still does not.
    assert [i["uuid"] for i in items] == ["adr:demo:near"]


@pytest.mark.asyncio
async def test_untyped_records_keep_the_category_threshold():
    untyped = {"fact": "plain prose from another backend", "uuid": "x", "score": 0.47}
    _, items, _ = await _architecture_apart([untyped], [], threshold=0.5)
    assert items == []


@pytest.mark.asyncio
async def test_decisions_and_documents_share_one_allocation():
    adr = _hit(_stored(_adr_payload()), "adr:demo:ADR_DEMO_001", score=0.9)
    doc = _hit(_stored(_document_payload()), "document:demo:overview", score=0.9)
    retriever, _, _ = await _architecture_apart([adr], [doc])
    decision_tokens = retriever._estimate_tokens(_record_as_text(adr))

    # Room for the decision only: the document waits for spare capacity.
    _, items, tokens = await _architecture_apart([adr], [doc], budget=decision_tokens)
    assert [i["uuid"] for i in items] == ["adr:demo:ADR_DEMO_001"]
    assert tokens == decision_tokens


@pytest.mark.asyncio
async def test_other_categories_search_as_before():
    retriever = _by_group([], [])
    await retriever._query_category(
        "query", ["patterns"], 500, 0.5, category="relevant_patterns"
    )
    assert [c.kwargs.get("group_ids") for c in retriever.graphiti.search.call_args_list] == [
        ["patterns"]
    ]
