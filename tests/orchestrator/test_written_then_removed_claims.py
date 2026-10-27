"""What the builder wrote and then removed again is recorded as such.

13 October 2026, first web fixture proof (build FEAT-40E8, task 001, turn 4):
the builder wrote ``apps/web/src/zzprobe.test.tsx``, edited it, and removed
it, never naming it. The honesty check that once raised over that file was
removed in the cull of 27 October 2026; what remains is the record: harness
events feed the parser, ``_create_player_report_from_task_work`` writes the
final report and rewrites ``task_work_results.json``, and a write confirmed by
its own result and then removed is listed as ``files_written_then_removed``,
kept in ``files_authored`` and left out of ``files_created``. A tracked file
the builder deleted keeps its authorship.
"""

from __future__ import annotations

import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from unittest.mock import patch

import pytest

from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    ResultMessageEvent,
    ToolResultEvent,
    ToolUseEvent,
)
from tests.task_scope_fixtures import admitted_task

PROBE = "apps/web/src/zzprobe.test.tsx"
TRACKED = "apps/web/src/App.tsx"

_FINAL_TEXT = "10 tests passed, 0 tests failed\nAll quality gates passed"


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


@contextmanager
def _invoker(tmp_path: Path, task_id: str) -> Iterator[Any]:
    """An invoker over a real git checkout holding one committed file, built
    while the task is admitted on the checkout (as in a build), so the
    invoker reads what changed from git."""
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    worktree = tmp_path / "worktree"
    (worktree / "apps" / "web" / "src").mkdir(parents=True)
    (worktree / TRACKED).write_text("export const App = () => null;\n")
    _git("init", "--initial-branch=main", cwd=worktree)
    _git("add", "-A", cwd=worktree)
    _git("commit", "-m", "base", cwd=worktree)
    with admitted_task(worktree, task_id, register=True):
        yield AgentInvoker(
            worktree_path=worktree, max_turns_per_agent=30, sdk_timeout_seconds=60
        )


def _harness(events: List[Any], final_text: str) -> Any:
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


def _use(call_id: Optional[str], name: str, path: Path) -> ToolUseEvent:
    return ToolUseEvent(
        tool_use_id=call_id,  # type: ignore[arg-type]
        name=name,
        input={"file_path": str(path), "content": "it('probe', () => {});\n"},
    )


def _ok(call_id: str) -> ToolResultEvent:
    return ToolResultEvent(tool_use_id=call_id, content="Updated file")


def _put(path: Path) -> Any:
    def run() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("it('probe', () => {});\n")

    return run


def _remove(path: Path) -> Any:
    return lambda: path.unlink()


async def _whole_path(
    invoker: Any, task_id: str, events: List[Any], final_text: str = _FINAL_TEXT
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Harness events → parser → final report; returns (report, results)."""
    with patch(
        "guardkit.orchestrator.agent_invoker.select_harness",
        return_value=_harness(events, final_text),
    ):
        result = await invoker._invoke_task_work_implement(
            task_id=task_id, mode="standard"
        )
    assert result.success is True
    invoker._create_player_report_from_task_work(task_id, 1, result)
    folder = invoker.worktree_path / ".guardkit" / "autobuild" / task_id
    report = json.loads((folder / "player_turn_1.json").read_text())
    record = json.loads((folder / "task_work_results.json").read_text())
    return report, record


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_confirmed_write_then_deleted_is_recorded_as_written_then_removed(
    tmp_path: Path,
) -> None:
    with _invoker(tmp_path, "TASK-CONFIRMED") as invoker:
        probe = invoker.worktree_path / PROBE
        report, record = await _whole_path(
            invoker,
            "TASK-CONFIRMED",
            [_put(probe), _use("c1", "write_file", probe), _ok("c1"), _remove(probe)],
        )

    for final in (report, record):
        assert final["files_written_then_removed"] == [PROBE]
        assert PROBE in final["files_authored"]
        assert PROBE not in final["files_created"]


# ---------------------------------------------------------------------------
# Authorship is never shortened
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_tracked_file_the_builder_deleted_keeps_its_authorship(
    tmp_path: Path,
) -> None:
    with _invoker(tmp_path, "TASK-TRACKED-DELETE") as invoker:
        tracked = invoker.worktree_path / TRACKED
        report, record = await _whole_path(
            invoker,
            "TASK-TRACKED-DELETE",
            [_use("c1", "write_file", tracked), _ok("c1"), _remove(tracked)],
        )

    for final in (report, record):
        assert TRACKED in final["files_modified"]
        assert TRACKED in final["files_authored"]
        assert final.get("files_written_then_removed", []) == []
