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


def _harness_yielding(events: List[Any], final_text: str = _FINAL_TEXT) -> Any:
    """A harness that replays a fixed event sequence, then a terminal result.

    A callable in the sequence is run instead of yielded, so a replay can
    make the file a successful write made.
    """

    class ReplayHarness:
        supports_resume = False

        async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
            for event in events:
                if callable(event):
                    event()
                    continue
                yield event
            yield AssistantMessageEvent(text=final_text, raw=None)
            yield ResultMessageEvent(session_id=None, raw=None)

        async def cancel(self) -> None:
            return None

    return ReplayHarness()


async def _run(
    invoker: Any, task_id: str, events: List[Any], final_text: str = _FINAL_TEXT
) -> dict:
    harness = _harness_yielding(events, final_text)
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


# ---------------------------------------------------------------------------
# Only writes that worked are listed, and scratch files never are
# (3 October 2026)
#
# FEAT-D586 and FEAT-E592 each lost an attempt because the list was filled
# when the builder ASKED to write: a throwaway script aimed at /tmp was
# refused (outside the worktree) yet stayed listed, and the honesty check
# called it fabricated. The local builder delivers every tool use and then
# every tool result (a refused write is a ToolMessage with status "error",
# so ``is_error=True``); the hosted builder delivers a typed use per block,
# the raw message holding the same blocks, and later the results.
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> None:
    import subprocess

    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _git_invoker(tmp_path: Path) -> Any:
    """An invoker whose worktree is a real git checkout."""
    invoker = _make_invoker(tmp_path)
    _git("init", "--initial-branch=main", cwd=invoker.worktree_path)
    return invoker


def _use(call_id: str, name: str, path: Any) -> ToolUseEvent:
    return ToolUseEvent(
        tool_use_id=call_id,
        name=name,
        input={"file_path": str(path), "content": "x = 1\n"},
    )


def _ok(call_id: str) -> ToolResultEvent:
    return ToolResultEvent(tool_use_id=call_id, content="Updated file")


def _refused(call_id: str) -> ToolResultEvent:
    return ToolResultEvent(
        tool_use_id=call_id,
        content="Error: refusing to write: outside the worktree.",
        is_error=True,
    )


def _put(path: Path) -> Any:
    def run() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n")

    return run


class TestOnlyWritesThatWorkedAreListed:
    @pytest.mark.asyncio
    async def test_local_refused_write_and_failed_edit_are_not_listed(
        self, tmp_path: Path
    ) -> None:
        invoker = _make_invoker(tmp_path)
        wt = invoker.worktree_path
        events = [
            _put(wt / "src" / "b.py"),
            _use("c1", "write_file", "/tmp/verify_e592_002.py"),
            _use("c2", "edit_file", wt / "src" / "a.py"),
            _use("c3", "write_file", wt / "src" / "b.py"),
            _refused("c1"),
            ToolResultEvent(
                tool_use_id="c2",
                content="Error: String not found in file",
                is_error=True,
            ),
            _ok("c3"),
        ]

        record = await _run(invoker, "TASK-LOCAL-REFUSED", events)

        assert record["files_created"] == ["src/b.py"]
        assert record["files_modified"] == []
        assert record["files_authored"] == ["src/b.py"]
        assert record["files_authored_tracking"] == "tracked"

    @pytest.mark.asyncio
    async def test_failed_write_retried_to_the_same_path_is_listed_once(
        self, tmp_path: Path
    ) -> None:
        invoker = _make_invoker(tmp_path)
        wt = invoker.worktree_path
        events = [
            _use("c1", "write_file", wt / "src" / "retry.py"),
            _use("c2", "write_file", wt / "src" / "retry.py"),
            _refused("c1"),
            _ok("c2"),
        ]

        record = await _run(invoker, "TASK-RETRY", events)

        assert record["files_created"] == ["src/retry.py"]
        assert record["files_authored"] == ["src/retry.py"]

    @pytest.mark.asyncio
    async def test_write_with_no_result_is_kept_as_before(
        self, tmp_path: Path
    ) -> None:
        invoker = _make_invoker(tmp_path)
        events = [_use("c1", "write_file", invoker.worktree_path / "src" / "n.py")]

        record = await _run(invoker, "TASK-UNANSWERED", events)

        assert record["files_created"] == ["src/n.py"]
        assert record["files_authored"] == ["src/n.py"]

    @pytest.mark.asyncio
    async def test_hosted_delivery_lists_only_writes_that_worked(
        self, tmp_path: Path
    ) -> None:
        """Through the real SDK harness: the raw message still carries the
        refused Write and the failed Edit, and neither may reach the list."""
        claude_agent_sdk = pytest.importorskip("claude_agent_sdk")
        from claude_agent_sdk import (
            AssistantMessage,
            ResultMessage,
            TextBlock,
            ToolResultBlock,
            ToolUseBlock,
            UserMessage,
        )

        from guardkit.orchestrator.harness import ClaudeSDKHarness

        invoker = _make_invoker(tmp_path)
        wt = invoker.worktree_path

        def write(call_id: str, name: str, path: Any) -> Any:
            return ToolUseBlock(
                id=call_id, name=name, input={"file_path": str(path), "content": ""}
            )

        messages = [
            AssistantMessage(
                content=[
                    write("tu-1", "Write", "/tmp/verify_sdk.py"),
                    write("tu-2", "Edit", wt / "src" / "a.py"),
                    write("tu-3", "Write", wt / "src" / "b.py"),
                    write("tu-4", "Write", wt / "src" / "c.py"),
                ],
                model="test-model",
            ),
            UserMessage(
                content=[
                    ToolResultBlock(tool_use_id="tu-1", content="denied", is_error=True),
                    ToolResultBlock(tool_use_id="tu-2", content="not found", is_error=True),
                    ToolResultBlock(tool_use_id="tu-3", content="ok"),
                    ToolResultBlock(tool_use_id="tu-4", content="busy", is_error=True),
                ]
            ),
            # The builder retries the failed write to the same path.
            AssistantMessage(
                content=[write("tu-5", "Write", wt / "src" / "c.py")],
                model="test-model",
            ),
            UserMessage(content=[ToolResultBlock(tool_use_id="tu-5", content="ok")]),
            AssistantMessage(content=[TextBlock(text=_FINAL_TEXT)], model="m"),
            ResultMessage(
                subtype="success",
                duration_ms=1,
                duration_api_ms=1,
                is_error=False,
                num_turns=1,
                session_id="sess-1",
                total_cost_usd=0.0,
            ),
        ]

        async def fake_query(*args: Any, **kwargs: Any) -> Any:
            for message in messages:
                yield message

        harness = ClaudeSDKHarness(
            sdk_timeout_seconds=60,
            allowed_tools=["Write", "Edit"],
            permission_mode="acceptEdits",
            max_turns=10,
        )
        with patch.object(claude_agent_sdk, "query", fake_query), patch(
            "guardkit.orchestrator.agent_invoker.select_harness",
            return_value=harness,
        ):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-HOSTED-REFUSED", mode="standard"
            )

        assert result.success is True
        record = json.loads(
            (
                wt / ".guardkit" / "autobuild" / "TASK-HOSTED-REFUSED"
                / "task_work_results.json"
            ).read_text()
        )
        assert record["files_created"] == ["src/b.py", "src/c.py"]
        assert record["files_modified"] == []
        assert record["files_authored"] == ["src/b.py", "src/c.py"]
        # The returned result carries the same lists.
        assert result.output["files_created"] == ["src/b.py", "src/c.py"]
        assert "files_modified" not in result.output


class TestScratchFolder:
    def test_found_in_a_plain_checkout_and_a_linked_worktree(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.paths import builder_scratch_dir

        repo = tmp_path / "repo"
        repo.mkdir()
        _git("init", "--initial-branch=main", cwd=repo)
        _git("-c", "user.email=t@e", "-c", "user.name=T",
             "commit", "--allow-empty", "-m", "base", cwd=repo)
        assert builder_scratch_dir(repo) == repo / ".git" / "guardkit-scratch"

        linked = tmp_path / "worktrees" / "FEAT-X"
        _git("worktree", "add", str(linked), cwd=repo)
        scratch = builder_scratch_dir(linked)
        assert scratch == repo / ".git" / "worktrees" / "FEAT-X" / "guardkit-scratch"

        # Removing the worktree removes its scratch folder too.
        scratch.mkdir()
        (scratch / "verify.py").write_text("x = 1\n")
        _git("worktree", "remove", "--force", str(linked), cwd=repo)
        assert not scratch.exists()

        assert builder_scratch_dir(tmp_path / "not-a-checkout") is None

    @pytest.mark.asyncio
    async def test_scratch_writes_and_scratch_claims_are_not_listed(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.paths import builder_scratch_dir

        invoker = _git_invoker(tmp_path)
        wt = invoker.worktree_path
        scratch = builder_scratch_dir(wt)
        script = scratch / "verify_created_per_day.py"
        events = [
            _put(script),
            _put(wt / "src" / "service.py"),
            _use("c1", "write_file", script),
            _use("c2", "edit_file", scratch / "notes.txt"),
            _use("c3", "write_file", wt / "src" / "service.py"),
            _ok("c1"),
            _ok("c2"),
            _ok("c3"),
        ]

        record = await _run(
            invoker,
            "TASK-SCRATCH",
            events,
            # A scratch path named in the builder's own words is harmless too.
            final_text=f"Created: {script}\n" + _FINAL_TEXT,
        )

        listed = (
            set(record["files_created"])
            | set(record["files_modified"])
            | set(record["files_authored"])
        )
        assert listed == {"src/service.py"}

    def test_dotdot_out_of_the_scratch_folder_is_still_listed(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.agent_invoker import TaskWorkStreamParser
        from guardkit.orchestrator.paths import builder_scratch_dir

        worktree = tmp_path / "wt"
        worktree.mkdir()
        _git("init", "--initial-branch=main", cwd=worktree)
        scratch = builder_scratch_dir(worktree)
        parser = TaskWorkStreamParser(worktree_root=worktree)
        parser.record_tool_request(
            "c1", "write_file", {"file_path": f"{scratch}/../../src/app.py"}
        )
        parser.record_tool_result("c1", is_error=False)

        # It lands in the worktree, so it is a project file and stays listed
        # (spelt as the builder gave it, relative to the worktree).
        assert parser.to_result()["files_created"] == [
            ".git/guardkit-scratch/../../src/app.py"
        ]

    def test_the_builder_is_told_where_the_scratch_folder_is(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.paths import builder_scratch_dir

        invoker = _git_invoker(tmp_path)
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-SCRATCH", mode="standard", turn=1
        )

        assert f"Put throwaway scripts in `{builder_scratch_dir(invoker.worktree_path)}`" in prompt
        assert "{scratch_folder}" not in prompt

        (tmp_path / "plain").mkdir()
        plain = _make_invoker(tmp_path / "plain")
        assert "throwaway scripts" not in plain._build_autobuild_implementation_prompt(
            task_id="TASK-SCRATCH", mode="standard", turn=1
        )
