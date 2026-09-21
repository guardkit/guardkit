"""The builder's file list reaches the record, and says when it did not.

2026-09-21. Until today ``files_authored`` was filled only from
``event.raw.content`` — the hosted builder's shape. The local builder yields a
typed ``ToolUseEvent`` per tool call and carries no ``raw``, so its list came
out empty on every task while it wrote real files. The kept 19 September build
``build-FEAT-DBE3-20260919000749`` shows it: every task's record has
``files_authored: []`` beside a runtime-evidence write count of 6 to 12.

The tool names and argument shapes below are not invented. They are what the
kept builds' preserved tool streams hold
(``~/forge-state/receipts/build-FEAT-*/worktrees/*/.guardkit/autobuild/TASK-*/
sdk_debug/turn_*/messages.jsonl``): ``write_file`` with ``file_path`` and
``content``, ``edit_file`` with ``file_path``, ``old_string`` and
``new_string``, ``execute`` with ``command`` — and every one of the 158 write
paths in those streams absolute and rooted at the task's worktree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List
from unittest.mock import patch

import pytest

from guardkit.orchestrator.authored_files import (
    NOT_CHECKED_REASON,
    STATUS_TRACKED,
    STATUS_UNKNOWN,
    read_authored_files,
)
from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    ResultMessageEvent,
    ToolResultEvent,
    ToolUseEvent,
)


_FINAL_TEXT = (
    "10 tests passed, 0 tests failed\n"
    "Coverage: 85.2%\n"
    "All quality gates passed"
)


def _make_invoker(tmp_path: Path) -> Any:
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    worktree = tmp_path / "worktree"
    worktree.mkdir(exist_ok=True)
    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=30,
        sdk_timeout_seconds=60,
    )


def _harness_yielding(events: List[Any]) -> Any:
    """A harness that replays a fixed event sequence, then a terminal result."""

    class ReplayHarness:
        supports_resume = False

        async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
            for event in events:
                yield event
            yield AssistantMessageEvent(text=_FINAL_TEXT, raw=None)
            yield ResultMessageEvent(session_id=None, raw=None)

        async def cancel(self) -> None:
            return None

    return ReplayHarness()


async def _run(invoker: Any, task_id: str, events: List[Any]) -> dict:
    harness = _harness_yielding(events)
    with patch(
        "guardkit.orchestrator.agent_invoker.select_harness",
        return_value=harness,
    ):
        result = await invoker._invoke_task_work_implement(
            task_id=task_id, mode="standard"
        )
    assert result.success is True
    record = (
        invoker.worktree_path
        / ".guardkit"
        / "autobuild"
        / task_id
        / "task_work_results.json"
    )
    assert record.exists(), "the run wrote no task_work_results.json"
    return json.loads(record.read_text())


def _local_builder_events(worktree: Path) -> List[Any]:
    """The event sequence the local builder yields for one small task."""
    return [
        ToolUseEvent(
            tool_use_id="call-1",
            name="write_file",
            input={
                "file_path": str(worktree / "src" / "users" / "service.py"),
                "content": "def counts_per_day():\n    return []\n",
            },
        ),
        ToolResultEvent(tool_use_id="call-1", content="ok"),
        ToolUseEvent(
            tool_use_id="call-2",
            name="edit_file",
            input={
                "file_path": str(worktree / "src" / "users" / "router.py"),
                "old_string": "pass",
                "new_string": "return service.counts_per_day()",
            },
        ),
        ToolResultEvent(tool_use_id="call-2", content="ok"),
        ToolUseEvent(
            tool_use_id="call-3",
            name="execute",
            input={"command": "python -m pytest tests/users"},
        ),
        ToolResultEvent(tool_use_id="call-3", content="3 passed"),
        ToolUseEvent(
            tool_use_id="call-4",
            name="execute",
            input={"command": "git status --short"},
        ),
        ToolResultEvent(tool_use_id="call-4", content=""),
    ]


# ---------------------------------------------------------------------------
# The reading rule
# ---------------------------------------------------------------------------


class TestReadingRule:
    def test_non_empty_list_is_tracked(self) -> None:
        files, status = read_authored_files({"files_authored": ["a.py"]})
        assert files == ["a.py"]
        assert status == STATUS_TRACKED

    def test_empty_list_with_tracked_marker_is_tracked(self) -> None:
        files, status = read_authored_files(
            {"files_authored": [], "files_authored_tracking": "tracked"}
        )
        assert files == []
        assert status == STATUS_TRACKED

    def test_empty_list_with_no_marker_is_unknown(self) -> None:
        _files, status = read_authored_files({"files_authored": []})
        assert status == STATUS_UNKNOWN

    def test_empty_list_marked_not_tracked_is_unknown(self) -> None:
        _files, status = read_authored_files(
            {"files_authored": [], "files_authored_tracking": "not_tracked"}
        )
        assert status == STATUS_UNKNOWN

    def test_missing_key_is_the_legacy_branch(self) -> None:
        files, status = read_authored_files({"files_created": ["a.py"]})
        assert files == []
        assert status == "no_key"

    def test_kept_wrong_build_record_reads_as_unknown(self) -> None:
        """The shape every task of the kept 19 September wrong build has."""
        record = {
            "files_authored": [],
            "files_created": ["src/users/service.py"],
            "files_modified": [],
            "runtime_evidence": {"categories": {"write": 6, "execute": 10}},
        }
        files, status = read_authored_files(record)
        assert files == []
        assert status == STATUS_UNKNOWN


# ---------------------------------------------------------------------------
# The real event loop
# ---------------------------------------------------------------------------


class TestRealEventLoop:
    @pytest.mark.asyncio
    async def test_local_builder_typed_events_reach_the_list(
        self, tmp_path: Path
    ) -> None:
        invoker = _make_invoker(tmp_path)
        events = _local_builder_events(invoker.worktree_path)

        record = await _run(invoker, "TASK-LOCAL-WRITE", events)

        assert record["files_authored_tracking"] == "tracked"
        # Absolute paths from the tool call, recorded relative to the task's
        # working folder — the form every reader of this list expects.
        assert record["files_authored"] == [
            "src/users/router.py",
            "src/users/service.py",
        ]
        assert record["files_created"] == ["src/users/service.py"]
        assert record["files_modified"] == ["src/users/router.py"]
        # Two shell commands ran; a file one of them wrote would not be in the
        # list above, and the count says so.
        assert record["shell_command_tool_uses"] == 2

        files, status = read_authored_files(record)
        assert status == STATUS_TRACKED
        assert files == ["src/users/router.py", "src/users/service.py"]

    @pytest.mark.asyncio
    async def test_no_tool_events_is_not_tracked(self, tmp_path: Path) -> None:
        invoker = _make_invoker(tmp_path)

        record = await _run(invoker, "TASK-NO-TOOLS", [])

        assert record["files_authored"] == []
        assert record["files_authored_tracking"] == "not_tracked"
        assert record["shell_command_tool_uses"] == 0
        _files, status = read_authored_files(record)
        assert status == STATUS_UNKNOWN

    @pytest.mark.asyncio
    async def test_shell_only_run_is_tracked_and_empty(
        self, tmp_path: Path
    ) -> None:
        """Tool events seen, no write among them: the list is empty and MEANT."""
        invoker = _make_invoker(tmp_path)
        events = [
            ToolUseEvent(
                tool_use_id="call-1",
                name="read_file",
                input={"file_path": str(invoker.worktree_path / "README.md")},
            ),
            ToolResultEvent(tool_use_id="call-1", content="..."),
            ToolUseEvent(
                tool_use_id="call-2",
                name="execute",
                input={"command": "python -m pytest"},
            ),
            ToolResultEvent(tool_use_id="call-2", content="1 passed"),
        ]

        record = await _run(invoker, "TASK-SHELL-ONLY", events)

        assert record["files_authored"] == []
        assert record["files_authored_tracking"] == "tracked"
        assert record["shell_command_tool_uses"] == 1
        _files, status = read_authored_files(record)
        assert status == STATUS_TRACKED

    @pytest.mark.asyncio
    async def test_hosted_builder_names_still_tracked(
        self, tmp_path: Path
    ) -> None:
        """The hosted builder's ``Write``/``Edit`` names go the same way."""
        invoker = _make_invoker(tmp_path)
        events = [
            ToolUseEvent(
                tool_use_id="call-1",
                name="Write",
                input={
                    "file_path": str(invoker.worktree_path / "src" / "a.py"),
                    "content": "x = 1\n",
                },
            ),
            ToolResultEvent(tool_use_id="call-1", content="ok"),
            ToolUseEvent(
                tool_use_id="call-2",
                name="Edit",
                input={
                    "file_path": str(invoker.worktree_path / "src" / "b.py"),
                    "old_string": "a",
                    "new_string": "b",
                },
            ),
            ToolResultEvent(tool_use_id="call-2", content="ok"),
        ]

        record = await _run(invoker, "TASK-HOSTED-WRITE", events)

        assert record["files_authored_tracking"] == "tracked"
        assert record["files_authored"] == ["src/a.py", "src/b.py"]
        assert record["files_created"] == ["src/a.py"]
        assert record["files_modified"] == ["src/b.py"]


# ---------------------------------------------------------------------------
# The path form
# ---------------------------------------------------------------------------


class TestPathForm:
    def test_absolute_inside_the_worktree_becomes_relative(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.agent_invoker import TaskWorkStreamParser

        parser = TaskWorkStreamParser(worktree_root=tmp_path)
        parser._track_tool_call(
            "write_file",
            {"file_path": str(tmp_path / "src" / "users" / "service.py")},
        )
        assert parser.to_result()["files_authored"] == [
            "src/users/service.py"
        ]

    def test_path_outside_the_worktree_is_kept_as_it_is(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.agent_invoker import TaskWorkStreamParser

        parser = TaskWorkStreamParser(worktree_root=tmp_path / "worktree")
        parser._track_tool_call("write_file", {"file_path": "/tmp/scratch.py"})
        assert parser.to_result()["files_authored"] == ["/tmp/scratch.py"]

    def test_relative_path_is_kept_as_it_is(self, tmp_path: Path) -> None:
        from guardkit.orchestrator.agent_invoker import TaskWorkStreamParser

        parser = TaskWorkStreamParser(worktree_root=tmp_path)
        parser._track_tool_call("edit_file", {"file_path": "src/users/crud.py"})
        assert parser.to_result()["files_authored"] == ["src/users/crud.py"]

    def test_non_write_tool_is_not_tracked(self, tmp_path: Path) -> None:
        from guardkit.orchestrator.agent_invoker import TaskWorkStreamParser

        parser = TaskWorkStreamParser(worktree_root=tmp_path)
        parser._track_tool_call(
            "read_file", {"file_path": str(tmp_path / "src" / "a.py")}
        )
        parser._track_tool_call("execute", {"command": "ls"})
        assert "files_authored" not in parser.to_result()


# ---------------------------------------------------------------------------
# What the detectors say when the list was never recorded
# ---------------------------------------------------------------------------


class TestDetectorsOnUnknown:
    def test_wiring_and_stub_scan_say_not_checked(self, tmp_path: Path) -> None:
        from guardkit.orchestrator.quality_gates import coach_validator as cv

        wiring = cv._run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=[],
            task_type="feature",
            stack_template="python",
            authored_status=STATUS_UNKNOWN,
        )
        assert wiring is not None
        assert wiring["wiring"]["status"] == "not_checked"
        assert wiring["wiring"]["findings"] is None
        assert wiring["wiring"]["reason"] == NOT_CHECKED_REASON
        assert wiring["mocked_seam"]["status"] == "not_checked"

        stub = cv._compute_stub_scan(
            worktree_path=tmp_path,
            authored_files=[],
            task_type="feature",
            authored_status=STATUS_UNKNOWN,
        )
        assert stub is not None
        assert stub["status"] == "not_checked"
        assert stub["findings"] is None
        assert stub["reason"] == NOT_CHECKED_REASON

    def test_tracked_empty_list_still_gates_out_quietly(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.quality_gates import coach_validator as cv

        assert (
            cv._run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=[],
                task_type="feature",
                stack_template="python",
                authored_status=STATUS_TRACKED,
            )
            is None
        )
        assert (
            cv._compute_stub_scan(
                worktree_path=tmp_path,
                authored_files=[],
                task_type="feature",
                authored_status=STATUS_TRACKED,
            )
            is None
        )


class TestStaleTestAttribution:
    def test_unrecorded_list_names_no_author(self, tmp_path: Path) -> None:
        from guardkit.orchestrator import stale_test_attribution as sta

        autobuild = tmp_path / ".guardkit" / "autobuild" / "TASK-A"
        autobuild.mkdir(parents=True)
        (autobuild / "task_work_results.json").write_text(
            json.dumps(
                {
                    "files_authored": [],
                    "files_created": ["tests/test_thing.py"],
                    "files_modified": ["tests/test_thing.py"],
                }
            )
        )

        assert (
            sta.find_authoring_task(
                "tests/test_thing.py", tmp_path, current_task_ids=["TASK-B"]
            )
            is None
        )

    def test_tracked_list_still_names_its_author(self, tmp_path: Path) -> None:
        from guardkit.orchestrator import stale_test_attribution as sta

        autobuild = tmp_path / ".guardkit" / "autobuild" / "TASK-A"
        autobuild.mkdir(parents=True)
        (autobuild / "task_work_results.json").write_text(
            json.dumps(
                {
                    "files_authored": ["tests/test_thing.py"],
                    "files_authored_tracking": "tracked",
                }
            )
        )

        assert (
            sta.find_authoring_task(
                "tests/test_thing.py", tmp_path, current_task_ids=["TASK-B"]
            )
            == "TASK-A"
        )
