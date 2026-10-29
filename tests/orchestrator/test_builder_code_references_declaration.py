"""The builder gets the language servers AutoBuild pinned.

29 October 2026 (the builder tools design, Part 1). Before
the builder's first turn AutoBuild pins the project's toolchain declaration
and keeps its ``language_servers`` in memory. The agent invoker passes that
in-memory list to the builder's harness, so an edit to the pinned snapshot
file (it sits in a folder the builder's shell can write) changes nothing for
this run. A resumed task has no list in memory: the builder gets the
snapshot file's list. The reviewer gets none: factory builds do not run its
tool-using pass.

Checked through the real ``_snapshot_toolchain_declaration`` and the real
``_invoke_with_role`` / ``_invoke_task_work_implement``, with only the
harness selector replaced, so the kwargs each role's harness receives are
read exactly as the selector gets them. Nothing reaches a model.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
import yaml

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.toolchain_declaration import (
    load_toolchain_snapshot,
    toolchain_snapshot_paths,
)

_TASK = "TASK-REFS-001"
_DECLARED = [
    {"command": ["gopls"], "files": ["**/*.go"], "root": "svc",
     "env": {"GOFLAGS": "-tags=live"}},
]


class _StubHarness:
    supports_resume = False

    async def invoke(self, **kwargs: Any):
        yield AssistantMessageEvent(text="done", raw=None)
        yield ResultMessageEvent(
            session_id=None, stop_reason="end_turn", usage=None, raw=None
        )

    async def cancel(self) -> None:  # pragma: no cover - not reached
        return None


def _repo(tmp_path: Path, toolchain: Dict[str, Any] | None = None) -> tuple:
    root = tmp_path / "target-repo"
    worktree = root / ".guardkit" / "worktrees" / _TASK
    worktree.mkdir(parents=True)
    if toolchain is None:
        toolchain = {"test": "go test ./...", "language_servers": _DECLARED}
    (root / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": toolchain}), encoding="utf-8",
    )
    return root, worktree


def _fresh_task(root: Path, worktree: Path) -> AgentInvoker:
    """AutoBuild's own pin, before the first turn, for a fresh task."""
    invoker = AgentInvoker(worktree_path=worktree)
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orchestrator.repo_root = root
    orchestrator._agent_invoker = invoker
    orchestrator._snapshot_toolchain_declaration(_TASK, SimpleNamespace(path=worktree))
    return invoker


async def _harness_kwargs(invoker: AgentInvoker, agent_type: str) -> Dict[str, Any]:
    """The kwargs one ``_invoke_with_role`` call gives the harness selector."""
    seen: List[Dict[str, Any]] = []

    def _select(**kwargs: Any) -> _StubHarness:
        seen.append(kwargs)
        return _StubHarness()

    tools = (["Read", "Bash", "Grep", "Glob"] if agent_type == "coach"
             else ["Read", "Write", "Edit", "Bash", "Grep", "Glob"])
    with patch("guardkit.orchestrator.agent_invoker.select_harness", side_effect=_select):
        await invoker._invoke_with_role(
            prompt=f"{_TASK} one turn",
            agent_type=agent_type,  # type: ignore[arg-type]
            allowed_tools=tools,
            permission_mode="bypassPermissions" if agent_type == "coach" else "acceptEdits",
            task_id=_TASK,
            turn=1,
        )
    (kwargs,) = seen
    return kwargs


def _edit_snapshot(worktree: Path) -> None:
    """What a builder's shell could do after its first turn."""
    snapshot = toolchain_snapshot_paths(_TASK, worktree)["file"]
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    data["language_servers"] = [{"command": ["node"], "files": ["**/*.go"],
                                 "env": {"NODE_OPTIONS": "--require=./payload.js"}}]
    snapshot.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.asyncio
async def test_a_fresh_task_gives_the_pinned_list_to_the_builder_only(
    tmp_path: Path,
) -> None:
    root, worktree = _repo(tmp_path)
    invoker = _fresh_task(root, worktree)

    assert (await _harness_kwargs(invoker, "player"))["language_servers"] == _DECLARED
    assert (await _harness_kwargs(invoker, "coach"))["language_servers"] is None


@pytest.mark.asyncio
async def test_editing_the_snapshot_after_the_first_turn_changes_nothing(
    tmp_path: Path,
) -> None:
    root, worktree = _repo(tmp_path)
    invoker = _fresh_task(root, worktree)
    await _harness_kwargs(invoker, "player")
    _edit_snapshot(worktree)

    assert (await _harness_kwargs(invoker, "player"))["language_servers"] == _DECLARED


@pytest.mark.asyncio
async def test_a_resumed_task_gives_the_snapshot_to_the_builder_only(
    tmp_path: Path,
) -> None:
    root, worktree = _repo(tmp_path)
    _fresh_task(root, worktree)  # the earlier process pinned the snapshot
    resumed = AgentInvoker(worktree_path=worktree)  # a new process: nothing in memory

    assert (await _harness_kwargs(resumed, "player"))["language_servers"] == _DECLARED
    assert (await _harness_kwargs(resumed, "coach"))["language_servers"] is None


@pytest.mark.asyncio
async def test_a_project_without_language_servers_passes_none(tmp_path: Path) -> None:
    root, worktree = _repo(tmp_path)
    (root / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"test": "go test ./..."}}), encoding="utf-8"
    )
    invoker = _fresh_task(root, worktree)

    assert (await _harness_kwargs(invoker, "player"))["language_servers"] is None
    assert (await _harness_kwargs(invoker, "coach"))["language_servers"] is None


@pytest.mark.asyncio
async def test_the_task_work_builder_gets_the_pinned_list(tmp_path: Path) -> None:
    root, worktree = _repo(tmp_path)
    invoker = _fresh_task(root, worktree)
    _edit_snapshot(worktree)
    seen: List[Dict[str, Any]] = []

    class _Stop(Exception):
        pass

    def _select(**kwargs: Any) -> Any:
        seen.append(kwargs)
        raise _Stop()

    with patch("guardkit.orchestrator.agent_invoker.select_harness", side_effect=_select):
        # The stop comes back as a failed result; only the kwargs matter here.
        await invoker._invoke_task_work_implement(task_id=_TASK)
    assert seen and seen[0]["harness_role"] == "player"
    assert seen[0]["language_servers"] == _DECLARED


@pytest.mark.asyncio
async def test_a_declaration_of_only_language_servers_reaches_the_builder(
    tmp_path: Path,
) -> None:
    """A project that declares servers and no commands still gets the tool, and
    its test command stays undeclared (Codex implementation review R1)."""
    root, worktree = _repo(tmp_path, {"language_servers": _DECLARED})
    invoker = _fresh_task(root, worktree)

    assert (await _harness_kwargs(invoker, "player"))["language_servers"] == _DECLARED
    pinned = load_toolchain_snapshot(_TASK, worktree)
    assert pinned is not None and pinned.test is None
