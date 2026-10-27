"""The SDK-level timeout line names the limit the turn actually ran under.

Build FEAT-D31F (19 October 2026): the Player's first turn ran under a
4,860-second limit (base 1,800 s x 1.5 for task-work x 1.8 for complexity 8)
and the log then said "sdk_timeout=1800s expired", the base before scaling.
The applied limit is in the Player's own error ("SDK timeout after 4860s"),
so the line now reads it from there and names the base beside it. No network,
no model.
"""

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    TurnRecord,
    _applied_sdk_timeout_seconds,
)
from guardkit.worktrees import Worktree


@pytest.fixture
def worktree() -> Mock:
    wt = Mock(spec=Worktree)
    wt.task_id = "TASK-AB-001"
    wt.path = Path("/tmp/worktrees/TASK-AB-001")
    wt.branch_name = "autobuild/TASK-AB-001"
    wt.base_branch = "main"
    return wt


def _orchestrator(tmp_path: Path, worktree: Mock) -> AutoBuildOrchestrator:
    manager = Mock()
    manager.create.return_value = worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = Path("/tmp/worktrees")
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=1,
        worktree_manager=manager,
        progress_display=display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1800,
        task_timeout=16200,
    )
    # ``orchestrate`` admits the task's scope before the loop; this test
    # drives ``_loop_phase`` directly, so it states that no scope was admitted.
    orch.task_work_scope = None
    return orch


def _timed_out_turn(error: str) -> TurnRecord:
    return TurnRecord(
        turn=1,
        player_result=AgentInvocationResult(
            task_id="TASK-AB-001",
            turn=1,
            agent_type="player",
            success=False,
            report={},
            duration_seconds=4860.0,
            error=error,
        ),
        coach_result=None,
        decision="error",
        feedback=None,
        timestamp="2026-10-19T11:31:47Z",
    )


def _sdk_level_line(orch, worktree, error, caplog) -> str:
    with patch.object(orch, "_execute_turn", return_value=_timed_out_turn(error)):
        with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.autobuild"):
            orch._loop_phase(
                task_id="TASK-AB-001",
                requirements="Implement feature",
                acceptance_criteria=["criterion 1"],
                worktree=worktree,
            )
    (line,) = [m for m in caplog.messages if "TIMEOUT (SDK-level)" in m]
    return line


def test_the_line_names_the_applied_limit_and_the_base(
    tmp_path: Path, worktree: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    orch = _orchestrator(tmp_path, worktree)
    line = _sdk_level_line(
        orch,
        worktree,
        "SDK timeout after 4860s: task-work execution exceeded 4860s timeout",
        caplog,
    )

    assert "sdk_timeout=4860s expired" in line
    assert "base 1800s" in line
    assert "sdk_timeout=1800s expired" not in line


def test_without_a_stated_limit_the_line_says_it_is_the_base(
    tmp_path: Path, worktree: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    orch = _orchestrator(tmp_path, worktree)
    line = _sdk_level_line(orch, worktree, "SDK timeout: cancelled scope", caplog)

    assert "base sdk_timeout=1800s" in line
    assert "applied limit not recorded" in line


@pytest.mark.parametrize(
    "error, expected",
    [
        ("SDK timeout after 4860s: task-work execution exceeded", 4860),
        ("SDK timeout after 600s: x", 600),
        ("SDK timeout: something", None),
        ("", None),
        (None, None),
    ],
)
def test_reading_the_applied_limit(error, expected) -> None:
    assert _applied_sdk_timeout_seconds(error) == expected
