"""One honest memory line per role and turn, from the real call sites (2026-10-04).

Every builder and reviewer turn used to end, when nothing came back, with
"NO memory ... either nothing on record or retrieval failed". It could not say
which, because a client that was never made, a connection that failed at
start-up, a failed search, a cached result and a search that found nothing
all looked the same. Now each turn writes one line saying which.

These tests drive the orchestrator's real ``_invoke_player_safely`` and
``_invoke_coach_safely`` with the real memory client factory, client,
context loader and retriever. Only fleet-memory's own store and search are
replaced, by a stand-in module, so no database or network is touched. In
every case the build carries on (fail-open) and both roles get the line.
"""

from __future__ import annotations

import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.knowledge.fleet_memory_client import (
    FleetMemoryClientFactory,
    FleetMemoryConfig,
)

AUTOBUILD = "guardkit.orchestrator.autobuild"
TASK = "TASK-AB12-002"


class StandInFleetMemory:
    """Stands in for the ``fleet_memory`` package: its store and its search."""

    def __init__(self) -> None:
        self.connect_fails = False
        self.answer: Callable[[dict], list] = lambda request: []
        self.searches: List[dict] = []

    def install(self, monkeypatch) -> None:
        stand_in = self

        class StoreContext:
            def __init__(self, settings):
                pass

            async def __aenter__(self):
                if stand_in.connect_fails:
                    raise ConnectionError("connection refused")
                return object()

            async def __aexit__(self, *exc):
                return False

        class SearchRequest:
            def __init__(self, **fields):
                self.fields = fields

        async def search(request, store):
            stand_in.searches.append(request.fields)
            return stand_in.answer(request.fields)

        package = types.ModuleType("fleet_memory")
        retrieval = types.ModuleType("fleet_memory.retrieval")
        retrieval.SearchRequest = SearchRequest
        retrieval.search = search
        settings = types.ModuleType("fleet_memory.settings")
        settings.Settings = lambda **fields: SimpleNamespace(**fields)
        store = types.ModuleType("fleet_memory.store")
        store.async_store_context = StoreContext
        package.retrieval, package.settings, package.store = retrieval, settings, store
        for name, module in (
            ("fleet_memory", package),
            ("fleet_memory.retrieval", retrieval),
            ("fleet_memory.settings", settings),
            ("fleet_memory.store", store),
        ):
            monkeypatch.setitem(sys.modules, name, module)
        # The client logs each search to a file in the current folder; not here.
        monkeypatch.setattr(
            "guardkit.knowledge.query_logger.log_query", lambda **kwargs: None
        )


def hit(key: str, score: float, content: str = "a short outcome"):
    return SimpleNamespace(score=score, value={"natural_key": key, "content": content})


@pytest.fixture
def memory(monkeypatch) -> StandInFleetMemory:
    stand_in = StandInFleetMemory()
    stand_in.install(monkeypatch)
    return stand_in


def build(tmp_path: Path, *, enabled=True, project: Optional[str] = "demo"):
    """A real orchestrator whose memory comes from a real client factory."""
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    factory = FleetMemoryClientFactory(
        FleetMemoryConfig(
            enabled=enabled,
            postgres_dsn="postgresql://test:test@localhost:1/none",
            project=project,
        )
    )
    invoker = MagicMock()
    invoker.invoke_player = AsyncMock(
        return_value=MagicMock(success=True, error=None, report={"summary": "done"})
    )
    invoker.invoke_coach = AsyncMock(
        return_value=MagicMock(success=True, error=None, report={"decision": "approve"})
    )
    with patch(f"{AUTOBUILD}.get_memory_factory", return_value=factory):
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path, max_turns=3, enable_context=True, context_loader=None,
            worktree_manager=MagicMock(), agent_invoker=invoker,
            progress_display=MagicMock(), enable_checkpoints=False,
        )
    return orchestrator, invoker


def builder_turn(orchestrator, turn):
    return orchestrator._invoke_player_safely(TASK, turn, "Count active users.", None)


def reviewer_turn(orchestrator, turn, tmp_path):
    worktree = MagicMock()
    worktree.path = tmp_path
    return orchestrator._invoke_coach_safely(
        task_id=TASK, turn=turn, requirements="Count active users.",
        player_report={"summary": "done"}, worktree=worktree,
    )


def memory_lines(caplog) -> List[tuple]:
    return [
        (record.levelname, record.getMessage())
        for record in caplog.records
        if record.name == AUTOBUILD
        and record.getMessage().startswith(("[Memory] builder ", "[Memory] reviewer "))
    ]


def two_turns_both_roles(orchestrator, tmp_path, caplog):
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=AUTOBUILD):
        results = []
        for turn in (1, 2):
            results.append(builder_turn(orchestrator, turn))
            results.append(reviewer_turn(orchestrator, turn, tmp_path))
    return results, memory_lines(caplog)


# ---------------------------------------------------------------- start-up


def test_connection_failure_at_start_up_is_said_on_every_turn(tmp_path, memory, caplog):
    memory.connect_fails = True
    orchestrator, invoker = build(tmp_path)

    results, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    why = "skipped at start-up (the memory store connection failed)."
    assert lines == [
        ("WARNING", f"[Memory] builder {TASK} turn 1: {why}"),
        ("WARNING", f"[Memory] reviewer {TASK} turn 1: {why}"),
        ("WARNING", f"[Memory] builder {TASK} turn 2: {why}"),
        ("WARNING", f"[Memory] reviewer {TASK} turn 2: {why}"),
    ]
    # Fail-open: the builder still ran on both turns, and nothing searched.
    assert invoker.invoke_player.await_count == 2
    assert results[0].success is True
    assert memory.searches == []
    assert orchestrator._last_player_context_status.reason == "the memory store connection failed"


def test_memory_turned_off_says_off(tmp_path, memory, caplog):
    orchestrator, invoker = build(tmp_path, enabled=False)

    _, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    assert lines[0] == ("INFO", f"[Memory] builder {TASK} turn 1: off (FLEET_MEMORY_ENABLED is not set).")
    assert lines[1] == ("INFO", f"[Memory] reviewer {TASK} turn 1: off (FLEET_MEMORY_ENABLED is not set).")
    assert len(lines) == 4
    assert invoker.invoke_player.await_count == 2


def test_context_turned_off_for_the_build_says_off(tmp_path, memory, caplog):
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    invoker = MagicMock()
    invoker.invoke_player = AsyncMock(return_value=MagicMock(success=True, error=None, report={}))
    orchestrator = AutoBuildOrchestrator(
        repo_root=tmp_path, max_turns=3, enable_context=False,
        worktree_manager=MagicMock(), agent_invoker=invoker,
        progress_display=MagicMock(), enable_checkpoints=False,
    )
    with caplog.at_level(logging.INFO, logger=AUTOBUILD):
        builder_turn(orchestrator, 1)
    assert memory_lines(caplog) == [
        ("INFO", f"[Memory] builder {TASK} turn 1: off (context retrieval is turned off for this build).")
    ]


def test_a_build_with_no_memory_name_says_unavailable(tmp_path, memory, caplog):
    orchestrator, invoker = build(tmp_path, project=None)

    _, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    why = "unavailable (this build has no memory name)."
    assert lines == [
        ("WARNING", f"[Memory] builder {TASK} turn 1: {why}"),
        ("WARNING", f"[Memory] reviewer {TASK} turn 1: {why}"),
        ("WARNING", f"[Memory] builder {TASK} turn 2: {why}"),
        ("WARNING", f"[Memory] reviewer {TASK} turn 2: {why}"),
    ]
    assert invoker.invoke_player.await_count == 2


# ---------------------------------------------------------------- searched
#
# With no project declaration, a turn makes seven reads: the history check,
# feature specs, task outcomes, architecture, failure patterns, domain
# knowledge and turn history. Patterns and the three retired builder/reviewer
# groups return without searching, so they count as neither.


def test_a_failed_search_then_the_same_call_again_searches_again(tmp_path, memory, caplog):
    def broken(request):
        raise RuntimeError("store went away")

    memory.answer = broken
    orchestrator, invoker = build(tmp_path)

    with caplog.at_level(logging.INFO, logger=AUTOBUILD):
        builder_turn(orchestrator, 1)
        first_searches = len(memory.searches)
        builder_turn(orchestrator, 1)  # the same call, well inside five minutes

    line = f"[Memory] builder {TASK} turn 1: searched: 0 completed, 7 failed; 0 above the line (0.50), 0 delivered."
    assert memory_lines(caplog) == [("WARNING", line), ("WARNING", line)]
    # No cache: the second call searched the store again.
    assert first_searches == 7
    assert len(memory.searches) == 14
    assert invoker.invoke_player.await_count == 2


def test_partial_failure(tmp_path, memory, caplog):
    def outcomes_broken(request):
        if "build_outcome" in request["payload_types"]:
            raise RuntimeError("outcomes partition unavailable")
        return []

    memory.answer = outcomes_broken
    orchestrator, _ = build(tmp_path)

    _, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    assert lines[0] == (
        "WARNING",
        f"[Memory] builder {TASK} turn 1: searched: 6 completed, 1 failed; 0 above the line (0.50), 0 delivered.",
    )
    assert lines[1][0] == "WARNING" and lines[1][1].startswith(f"[Memory] reviewer {TASK} turn 1: searched: 6 completed, 1 failed")
    assert len(lines) == 4


def test_a_successful_empty_search(tmp_path, memory, caplog):
    orchestrator, _ = build(tmp_path)

    _, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    # Turn 2 has no local turn-state file here, so loading the previous turn
    # falls back to one more memory search, and the line counts it.
    assert lines == [
        ("INFO", f"[Memory] {role} {TASK} turn {turn}: searched: {reads} completed, 0 failed; 0 above the line (0.50), 0 delivered.")
        for turn, reads in ((1, 7), (2, 8))
        for role in ("builder", "reviewer")
    ]


def _reported_reads(line: str) -> int:
    counts = line.split("searched: ", 1)[1].split(";", 1)[0]  # "8 completed, 0 failed"
    completed, failed = (int(part.split()[0]) for part in counts.split(", "))
    return completed + failed


def test_each_line_counts_exactly_the_store_calls_of_its_own_call(tmp_path, memory, caplog):
    """Reported reads equal the real store calls, call by call, on both turns."""
    orchestrator, _ = build(tmp_path)
    calls = []
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=AUTOBUILD):
        for turn in (1, 2):
            before = len(memory.searches)
            builder_turn(orchestrator, turn)
            calls.append(len(memory.searches) - before)
            before = len(memory.searches)
            reviewer_turn(orchestrator, turn, tmp_path)
            calls.append(len(memory.searches) - before)

    lines = memory_lines(caplog)
    assert calls == [7, 7, 8, 8]
    assert [_reported_reads(text) for _, text in lines] == calls


def test_a_failure_only_in_the_previous_turn_lookup_is_reported(tmp_path, memory, caplog):
    """Turn 2's fallback search for the previous turn's state fails, and only
    it. The line says so for each role, and each role's own failure is counted
    once, in its own line, not hidden from the next."""

    def continuation_broken(request):
        if request["query"].startswith("turn_state "):
            raise RuntimeError("turn-state lookup failed")
        return []

    memory.answer = continuation_broken
    orchestrator, invoker = build(tmp_path)

    _, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    ok = "searched: 7 completed, 0 failed; 0 above the line (0.50), 0 delivered."
    broken = "searched: 7 completed, 1 failed; 0 above the line (0.50), 0 delivered."
    assert lines == [
        ("INFO", f"[Memory] builder {TASK} turn 1: {ok}"),
        ("INFO", f"[Memory] reviewer {TASK} turn 1: {ok}"),
        ("WARNING", f"[Memory] builder {TASK} turn 2: {broken}"),
        ("WARNING", f"[Memory] reviewer {TASK} turn 2: {broken}"),
    ]
    # Fail-open: the builder still ran on both turns.
    assert invoker.invoke_player.await_count == 2
    assert sum(r["query"].startswith("turn_state ") for r in memory.searches) == 2


def test_everything_below_the_line(tmp_path, memory, caplog):
    memory.answer = lambda request: [hit("build_outcome:demo:TASK_X", 0.3)]
    orchestrator, _ = build(tmp_path)

    _, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    assert lines[0] == (
        "INFO",
        f"[Memory] builder {TASK} turn 1: searched: 7 completed, 0 failed; 0 above the line (0.50), 0 delivered.",
    )
    assert all(level == "INFO" for level, _ in lines)


def test_above_the_line_and_delivered(tmp_path, memory, caplog):
    memory.answer = lambda request: [hit("build_outcome:demo:TASK_X", 0.8)]
    orchestrator, _ = build(tmp_path)

    _, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    level, text = lines[0]
    assert level == "INFO"
    # Six searched categories each kept the one record.
    assert text == f"[Memory] builder {TASK} turn 1: searched: 7 completed, 0 failed; 6 above the line (0.50), 6 delivered."


def test_above_the_line_but_nothing_delivered_is_a_warning(tmp_path, memory, caplog):
    too_big = "x" * 40_000  # far larger than any category's share
    memory.answer = lambda request: [hit("build_outcome:demo:TASK_X", 0.9, too_big)]
    orchestrator, invoker = build(tmp_path)

    _, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    assert lines[0] == (
        "WARNING",
        f"[Memory] builder {TASK} turn 1: searched: 7 completed, 0 failed; 6 above the line (0.50), 0 delivered.",
    )
    assert all(level == "WARNING" for level, _ in lines)
    assert len(lines) == 4
    assert invoker.invoke_player.await_count == 2


def test_the_old_no_memory_warning_is_gone(tmp_path, memory, caplog):
    orchestrator, _ = build(tmp_path)
    with caplog.at_level(logging.INFO):
        builder_turn(orchestrator, 1)
        reviewer_turn(orchestrator, 1, tmp_path)
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "NO memory" not in text
    assert "no factory or loader" not in text


def test_a_retrieval_that_raises_says_searched_failed(tmp_path, memory, caplog):
    orchestrator, invoker = build(tmp_path)
    with patch(
        "guardkit.knowledge.job_context_retriever.JobContextRetriever.retrieve",
        AsyncMock(side_effect=RuntimeError("analyzer blew up")),
    ):
        _, lines = two_turns_both_roles(orchestrator, tmp_path, caplog)

    assert lines[0] == ("WARNING", f"[Memory] builder {TASK} turn 1: searched: failed (analyzer blew up).")
    assert lines[1] == ("WARNING", f"[Memory] reviewer {TASK} turn 1: searched: failed (analyzer blew up).")
    assert len(lines) == 4
    assert invoker.invoke_player.await_count == 2


def test_delivered_and_populated_categories_read_one_list():
    """Every list category of the retrieved context is in the shared list, so
    the 'delivered' count and the populated-category list cannot drift apart."""
    import dataclasses
    import typing

    from guardkit.knowledge.autobuild_context_loader import (
        CONTEXT_CATEGORIES,
        AutoBuildContextLoader,
    )
    from guardkit.knowledge.job_context_retriever import RetrievedContext

    list_fields = [
        f.name
        for f in dataclasses.fields(RetrievedContext)
        if typing.get_origin(typing.get_type_hints(RetrievedContext)[f.name]) is list
    ]
    assert list(CONTEXT_CATEGORIES) == list_fields

    context = RetrievedContext("TASK-AB12-001", 0, 0, *[[] for _ in range(6)])
    for name in CONTEXT_CATEGORIES:
        setattr(context, name, [{"content": name}])
    loader = AutoBuildContextLoader(graphiti=None)
    assert loader._get_populated_categories(context) == list(CONTEXT_CATEGORIES)
    assert loader._memory_report(context, (0, 0)).delivered == len(CONTEXT_CATEGORIES)
