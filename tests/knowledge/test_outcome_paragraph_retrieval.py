"""A retrieved build outcome reaches the builder as its paragraph (2026-10-04).

Before, the outcomes category handed over the store's whole record as escaped
JSON, and costed it that way: about 220 tokens of fixed fields before the
paragraph, so at most one outcome fitted in the share. Now an outcome with a
``lessons`` paragraph becomes ``{"content", "uuid", "score"}`` before the
relevance line and the trimming run. Nothing else changes.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardkit.knowledge.job_context_retriever import JobContextRetriever
from guardkit.knowledge.task_analyzer import TaskPhase

LESSONS = (
    'TASK-AB12-003 "Add active count endpoint" (feature FEAT-AB12): approved by '
    "the reviewer on turn 1. Files changed: src/users/router.py."
)


def _record(lessons=LESSONS, task="TASK-AB12-003"):
    return json.dumps(
        {
            "approach": "guardkit autobuild player/coach loop",
            "domain_tags": ["task"],
            "duration_seconds": 600,
            "identifier": task.replace("-", "_"),
            "lessons": lessons,
            "natural_key": f"build_outcome:demo:{task.replace('-', '_')}",
            "project": "demo",
            "source_ref": "FEAT-AB12",
            "status": "success",
            "supersedes": [],
            "task_id": task,
            "version": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _hit(fact, key="build_outcome:demo:TASK_AB12_003", score=0.8):
    return {"fact": fact, "uuid": key, "score": score}


def _retriever(hits):
    client = MagicMock()
    client.search = AsyncMock(return_value=hits)
    client.supports_substantive_search = True
    return JobContextRetriever(client, cache_ttl=0)


@pytest.mark.asyncio
async def test_an_outcome_becomes_its_paragraph():
    retriever = _retriever([_hit(_record())])
    items, tokens = await retriever._query_category(
        "query", ["task_outcomes"], 2000, 0.5, category="similar_outcomes"
    )
    assert items == [
        {"content": LESSONS, "uuid": "build_outcome:demo:TASK_AB12_003", "score": 0.8}
    ]
    # Costed as the paragraph, not the escaped record.
    assert tokens == retriever._estimate_tokens(items[0])
    assert tokens < retriever._estimate_tokens(_hit(_record())) // 2


@pytest.mark.asyncio
async def test_the_paragraph_is_what_is_trimmed_to_the_share():
    """Three outcomes that fit only as paragraphs: all three are delivered.
    As whole records, the same share holds one."""
    hits = [
        _hit(_record(task=f"TASK-AB12-00{n}"), key=f"k{n}", score=0.9 - n / 100)
        for n in range(1, 4)
    ]
    one_record = JobContextRetriever(MagicMock())._estimate_tokens(hits[0])
    share = one_record + 10  # room for one whole record, not two

    paragraphs, _ = await _retriever(hits)._query_category(
        "query", ["task_outcomes"], share, 0.5, category="similar_outcomes"
    )
    assert [item["uuid"] for item in paragraphs] == ["k1", "k2", "k3"]


@pytest.mark.asyncio
async def test_the_relevance_line_still_applies():
    items, _ = await _retriever([_hit(_record(), score=0.3)])._query_category(
        "query", ["task_outcomes"], 2000, 0.5, category="similar_outcomes"
    )
    assert items == []


@pytest.mark.asyncio
async def test_an_outcome_without_lessons_is_left_alone():
    blank = _hit(_record(lessons=""))
    not_json = _hit("plain text outcome", key="other")
    items, _ = await _retriever([blank, not_json])._query_category(
        "query", ["task_outcomes"], 4000, 0.5, category="similar_outcomes"
    )
    assert items == [blank, not_json]


@pytest.mark.asyncio
async def test_other_categories_are_untouched():
    hit = _hit(_record())
    for group, category in (
        ("feature_specs", "feature_context"),
        ("project_architecture", "architecture_context"),
        ("failure_patterns", "warnings"),
    ):
        items, _ = await _retriever([hit])._query_category(
            "query", [group], 4000, 0.5, category=category
        )
        assert items == [hit], category


@pytest.mark.asyncio
async def test_the_prompt_shows_the_paragraph_as_plain_text():
    retriever = _retriever([_hit(_record())])
    context = await retriever.retrieve(
        {"id": "TASK-AB12-004", "description": "query", "is_autobuild": True},
        phase=TaskPhase.IMPLEMENT,
    )
    outcomes = context.to_prompt().split("### ✅ Similar Outcomes\n", 1)[1]
    outcomes = outcomes.split("\n\n", 1)[0]
    assert outcomes == f"- {LESSONS}"


@pytest.mark.asyncio
async def test_a_failed_category_query_is_counted():
    client = MagicMock()
    client.search = AsyncMock(side_effect=RuntimeError("store down"))
    retriever = JobContextRetriever(client, cache_ttl=0)
    items, tokens = await retriever._query_category(
        "query", ["task_outcomes"], 2000, 0.5, category="similar_outcomes"
    )
    assert (items, tokens) == ([], 0)
    await retriever._query_turn_states("FEAT-AB12", "TASK-AB12-001", 500, 0.5)
    assert retriever.failed_reads == 2
