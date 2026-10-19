"""The code reviewer is promised fewer tool rounds than fit, and is sent to the work.

Every code review since the step cap was added on 13 October 2026 ended at
the cap without a review (31 of 31 in the receipts), including every turn of
build FEAT-D31F. Two causes, both fixed in GuardKit:

* The prompt promised exactly the number of rounds that fit. Measured with the
  pinned deepagents and a scripted model, a run of N tool rounds takes
  ``3 + 2N`` steps: 24 steps fit 10 rounds and the prompt said 10.
* The list of files to start with was mostly GuardKit's own records: in the
  repair build, 20 of 22 names were the Coach's private records and the memory
  query log, listed before the two real source files.

No network and no model: the step measurement drives a deepagents graph with a
scripted chat model.
"""

from __future__ import annotations

from typing import Any, List

import pytest

from guardkit.orchestrator import specialist_invocations
from guardkit.orchestrator.specialist_invocations import (
    _code_reviewer_tool_rounds,
    reported_changed_files,
)


class TestPromisedRounds:
    @pytest.mark.parametrize("limit", [12, 16, 24, 32, 40, 48, 64, 100])
    def test_promised_rounds_fit_with_room_to_spare(self, limit: int) -> None:
        rounds = _code_reviewer_tool_rounds(limit)
        steps_needed = 3 + 2 * rounds
        # At least two more rounds would still have fitted.
        assert steps_needed + 4 <= limit, (limit, rounds)

    def test_the_default_cap_and_its_promise(self) -> None:
        assert specialist_invocations._CODE_REVIEWER_RECURSION_LIMIT == 40
        assert _code_reviewer_tool_rounds(40) == 14
        assert _code_reviewer_tool_rounds(24) == 8

    def test_a_tiny_cap_still_promises_one_round(self) -> None:
        assert _code_reviewer_tool_rounds(3) == 1


class TestStepsPerRoundMeasured:
    """Pins the 3 + 2N measurement against the installed deepagents."""

    @staticmethod
    def _steps_needed(rounds: int) -> int:
        deepagents = pytest.importorskip("deepagents")
        from langchain_core.language_models.fake_chat_models import (
            GenericFakeChatModel,
        )
        from langchain_core.messages import AIMessage
        from langgraph.errors import GraphRecursionError

        class _Scripted(GenericFakeChatModel):
            def bind_tools(self, tools: Any, **kwargs: Any) -> "_Scripted":
                return self

        def _script() -> List[AIMessage]:
            calls = [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "ls", "args": {"path": "/"}, "id": f"c{i}"}],
                )
                for i in range(rounds)
            ]
            return calls + [AIMessage(content="Verdict: approve")]

        for limit in range(1, 60):
            agent = deepagents.create_deep_agent(
                model=_Scripted(messages=iter(_script())), tools=[]
            )
            try:
                agent.invoke(
                    {"messages": [{"role": "user", "content": "review"}]},
                    config={"recursion_limit": limit},
                )
            except GraphRecursionError:
                continue
            return limit
        raise AssertionError("no limit up to 60 was enough")

    def test_each_round_costs_two_steps_after_three_to_start(self) -> None:
        assert [self._steps_needed(n) for n in (0, 1, 5)] == [3, 5, 13]

    def test_the_promise_fits_the_default_cap(self) -> None:
        limit = specialist_invocations._CODE_REVIEWER_RECURSION_LIMIT
        assert self._steps_needed(_code_reviewer_tool_rounds(limit)) < limit


class TestReportedFiles:
    def test_guardkit_records_are_left_out_and_modified_come_first(self) -> None:
        report = {
            "files_created": [
                ".guardkit/autobuild-private/TASK-X-002/coach_turn_1.json",
                ".guardkit/autobuild-private/build-FEAT-X/coach_project_documents_start.json",
                ".guardkit/autobuild/TASK-X-002/player_turn_1.json",
                ".guardkit/memory-query-log.jsonl",
                "apps/shelf/src/ShelfCount.tsx",
            ],
            "files_modified": [
                "apps/shelf/src/Shelf.tsx",
                "./apps/shelf/src/Shelf.test.tsx",
            ],
        }

        assert reported_changed_files(report) == [
            "apps/shelf/src/Shelf.tsx",
            "./apps/shelf/src/Shelf.test.tsx",
            "apps/shelf/src/ShelfCount.tsx",
        ]

    def test_a_name_listed_twice_is_listed_once(self) -> None:
        report = {"files_created": ["src/a.py"], "files_modified": ["src/a.py"]}
        assert reported_changed_files(report) == ["src/a.py"]

    def test_no_lists_is_still_none(self) -> None:
        assert reported_changed_files({"summary": "x"}) is None
        assert reported_changed_files(None) is None

    def test_only_records_is_an_empty_list_not_none(self) -> None:
        report = {"files_created": [".guardkit/autobuild-private/T/x.json"]}
        assert reported_changed_files(report) == []
