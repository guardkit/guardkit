"""Which declared skill files and documents a builder turn read.

The 29 October 2026 builder skills change: Rich asked whether the builder
uses the installed skills. Each task-work turn's ``runtime_evidence`` now
names the project's declared skill files and documents that the builder opened
with read_file, with a count each. Only declared paths, never other paths or
file contents, and the record never stops the work.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

import guardkit.orchestrator.agent_invoker as mod
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
    ToolResultEvent,
    ToolUseEvent,
)


class _ScriptedTypedHarness:
    def __init__(self, events):
        self._events = events

    @property
    def supports_resume(self):
        return False

    async def invoke(self, **kwargs):
        for event in self._events:
            yield event


def _worktree(tmp_path):
    worktree = tmp_path / "worktree"
    skill = worktree / "skills" / "react-best-practices"
    (skill / "rules").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: react-best-practices\n---\n")
    (skill / "rules" / "memo.md").write_text("# Memo\n")
    (worktree / ".agents").mkdir()
    (worktree / ".agents" / "skills").symlink_to("../skills", target_is_directory=True)
    (worktree / "docs").mkdir()
    (worktree / "docs" / "SCOPE.md").write_text("# Scope\nsecret scope sentinel\n")
    (worktree / "docs" / "undeclared.md").write_text("# Not declared\n")
    (worktree / ".guardkit").mkdir()
    (worktree / ".guardkit" / "config.yaml").write_text(
        "autobuild:\n"
        "  player:\n"
        "    skills: [skills]\n"
        "    required_documents:\n"
        "      - docs/SCOPE.md\n"
    )
    return worktree


def _read(index, path, name="read_file"):
    return ToolUseEvent(
        tool_use_id=f"read-{index}",
        name=name,
        input={"file_path": str(path), "offset": 0, "limit": 100},
    )


def _result(index, *, error=False):
    """The result of ``_read(index, ...)``: the call succeeded, or failed."""
    return ToolResultEvent(
        tool_use_id=f"read-{index}",
        content="Error: file not found" if error else "file text",
        is_error=error,
    )


def _answered(*reads):
    """Each read followed by its successful result."""
    return [event for read in reads for event in (read, _result(int(read.tool_use_id[5:])))]


async def _run_turn(tmp_path, monkeypatch, events, worktree):
    invoker = AgentInvoker(
        worktree_path=worktree, max_turns_per_agent=5, sdk_timeout_seconds=60
    )
    captured = {}

    def capture_results(
        task_id, result_data, documentation_level, *, runtime_evidence=None
    ):
        captured["runtime_evidence"] = runtime_evidence
        return tmp_path / "task_work_results.json"

    monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
    monkeypatch.setattr(
        invoker, "_build_autobuild_implementation_prompt", lambda **kwargs: "prompt"
    )
    monkeypatch.setattr(invoker, "_calculate_sdk_max_turns", lambda task_id: 150)
    monkeypatch.setattr(invoker, "_write_task_work_results", capture_results)
    harness = _ScriptedTypedHarness(
        [
            *events,
            AssistantMessageEvent(text="1 tests passed, 0 failed\nQuality gates: PASSED"),
            ResultMessageEvent(session_id=None, usage=None),
        ]
    )
    with (
        patch.object(mod, "select_harness", return_value=harness),
        patch.object(asyncio, "sleep", new=AsyncMock()),
    ):
        result = await invoker._invoke_task_work_implement("TASK-DECLARED-READS")
    assert result.success is True
    return captured["runtime_evidence"]


@pytest.mark.asyncio
async def test_turn_records_declared_skill_and_document_reads(tmp_path, monkeypatch):
    worktree = _worktree(tmp_path)
    outside = tmp_path / "outside-secret.md"
    outside.write_text("outside")
    events = [
        *_answered(
            # Read through the link dcode lists, then directly: one skill file.
            _read(1, worktree / ".agents/skills/react-best-practices/SKILL.md"),
            _read(2, worktree / "skills/react-best-practices/SKILL.md"),
            _read(3, worktree / "skills/react-best-practices/rules/memo.md"),
            _read(4, worktree / "docs/SCOPE.md"),
            _read(5, "docs/SCOPE.md"),
            # Ignored: an undeclared file, a path outside the worktree.
            _read(6, worktree / "docs/undeclared.md"),
            _read(7, outside),
        ),
        # Ignored: a listing and a write.
        ToolUseEvent(tool_use_id="ls-1", name="ls", input={"path": str(worktree / "skills")}),
        ToolUseEvent(
            tool_use_id="write-1",
            name="write_file",
            input={"file_path": str(worktree / "docs/SCOPE.md"), "content": "x"},
        ),
    ]

    evidence = await _run_turn(tmp_path, monkeypatch, events, worktree)

    assert evidence["declared_reads"] == {
        "skills": {
            "skills/react-best-practices/SKILL.md": 2,
            "skills/react-best-practices/rules/memo.md": 1,
        },
        "documents": {"docs/SCOPE.md": 2},
        "truncated": False,
    }
    encoded = str(evidence)
    for sentinel in ("undeclared.md", "outside-secret", "secret scope sentinel", str(worktree)):
        assert sentinel not in encoded


@pytest.mark.asyncio
async def test_unreadable_declarations_leave_an_empty_record_and_the_turn_goes_on(
    tmp_path, monkeypatch
):
    worktree = _worktree(tmp_path)
    (worktree / ".guardkit" / "config.yaml").write_text("autobuild: [not, a, mapping\n")

    evidence = await _run_turn(
        tmp_path, monkeypatch, _answered(_read(1, worktree / "docs/SCOPE.md")), worktree
    )

    assert evidence["declared_reads"] == {
        "skills": {},
        "documents": {},
        "truncated": False,
        "unavailable": True,
    }
    assert evidence["categories"]["read"] == 1


@pytest.mark.asyncio
async def test_only_reads_that_succeeded_are_counted(tmp_path, monkeypatch):
    """Codex review R1: a read that failed (a missing rule file here) is not a
    read. Only the declared file whose read came back without error is
    counted; a request with no result is not counted either."""
    worktree = _worktree(tmp_path)
    missing = worktree / "skills/react-best-practices/rules/missing.md"
    events = [
        _read(1, missing),
        _result(1, error=True),
        _read(2, worktree / "skills/react-best-practices/rules/memo.md"),
        _result(2),
        _read(3, worktree / "docs/SCOPE.md"),  # no result came back
    ]

    evidence = await _run_turn(tmp_path, monkeypatch, events, worktree)

    assert evidence["declared_reads"] == {
        "skills": {"skills/react-best-practices/rules/memo.md": 1},
        "documents": {},
        "truncated": False,
    }


def test_distinct_paths_are_bounded(tmp_path):
    worktree = _worktree(tmp_path)
    rules = worktree / "skills" / "react-best-practices" / "rules"
    paths = []
    for index in range(mod._DECLARED_READS_LIMIT + 5):
        (rules / f"rule-{index}.md").write_text("x")
        paths.append(str(rules / f"rule-{index}.md"))

    record = mod._declared_reads(worktree, paths)

    assert len(record["skills"]) == mod._DECLARED_READS_LIMIT
    assert record["truncated"] is True
