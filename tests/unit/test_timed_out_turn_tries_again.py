"""A coder attempt that only ran out of time gets another turn while the task's
budget holds one (build FEAT-E673, 7 November 2026: task 005 ended after its
first 4,320 s attempt with 10,076 s of its budget and four turns left)."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, TurnRecord
from guardkit.worktrees import Worktree

ADVICE = "- MUST FIX: Your last task-work attempt ran out of time; start with the smallest change."


def _orchestrator(tmp_path: Path, task_timeout):
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    manager = Mock()
    manager.worktrees_dir = tmp_path
    return AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=5,
        worktree_manager=manager,
        progress_display=display,
        enable_pre_loop=False,
        enable_context=False,
        enable_checkpoints=False,
        sdk_timeout=1800,
        task_timeout=task_timeout,
    )


def _worktree(tmp_path: Path):
    wt = Mock(spec=Worktree)
    wt.task_id, wt.path, wt.branch_name, wt.base_branch = "TASK-T-005", tmp_path, "b", "main"
    return wt


def _timed_out(turn: int, report=None) -> TurnRecord:
    result = AgentInvocationResult(
        task_id="TASK-T-005", turn=turn, agent_type="player", success=False,
        report=report or {}, duration_seconds=4320.0,
        error="SDK timeout after 4320s: task-work execution exceeded 4320s timeout",
    )
    return TurnRecord(turn=turn, player_result=result, coach_result=None, decision="error",
                      feedback=ADVICE, timestamp="2026-11-07T18:57:15Z")


def _approved(turn: int) -> TurnRecord:
    return TurnRecord(turn=turn, player_result=None, coach_result=None, decision="approve",
                      feedback=None, timestamp="2026-11-07T20:10:00Z")


def _run(orch, wt, turns):
    with patch.object(orch, "_execute_turn", side_effect=turns) as execute:
        history, decision = orch._loop_phase(
            task_id="TASK-T-005", requirements="r", acceptance_criteria=["c"], worktree=wt
        )
    return history, decision, execute


def test_a_timed_out_attempt_with_budget_left_tries_again_from_its_advice(tmp_path: Path) -> None:
    orch = _orchestrator(tmp_path, task_timeout=14400)
    history, decision, execute = _run(orch, _worktree(tmp_path), [_timed_out(1), _approved(2)])
    assert decision == "approved"
    assert len(history) == 2
    assert execute.call_args_list[1].kwargs.get("previous_feedback") == ADVICE


def test_a_budget_shorter_than_another_attempt_ends_the_task(tmp_path: Path) -> None:
    orch = _orchestrator(tmp_path, task_timeout=4000)
    history, decision, _ = _run(orch, _worktree(tmp_path), [_timed_out(1), _approved(2)])
    assert decision == "error"
    assert len(history) == 1


@pytest.mark.parametrize("task_timeout, report", [(None, None), (14400, {"unrecoverable": True})])
def test_no_budget_or_an_unrecoverable_failure_ends_the_task(tmp_path: Path, task_timeout, report) -> None:
    orch = _orchestrator(tmp_path, task_timeout=task_timeout)
    history, decision, _ = _run(orch, _worktree(tmp_path), [_timed_out(1, report), _approved(2)])
    assert decision == "error"
    assert len(history) == 1
