"""A refused agent launch stops the task at once (factory reliability repair 3).

B463 task two: the harness refused to start the Player because its reused run
profile held something unexpected. Each refusal was then handled like an
implementation failure — state recovery, a synthetic report, the Coach and
feedback asking for code — for four turns.

These tests drive the real seams: ``AutoBuildOrchestrator._loop_phase`` →
``_invoke_player_safely`` → the real ``AgentInvoker.invoke_player`` → the
task-work or direct invoker → the harness. Only the harness (the thing that
refuses) and task-file plumbing are replaced.

The harness error is a stand-in with the same shape as guardkitfactory's
``PlayerLaunchRefused``: GuardKit recognises it by ``failure_kind`` and does
not import the harness package.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    AgentLaunchRefusedError,
    find_agent_launch_refusal,
)
from guardkit.orchestrator.harness import HarnessAdapter
from guardkit.worktrees import Worktree

_TASK = "TASK-LAUNCH-001"
_ENTRY = {
    "path": "guardkit-player/notes.json",
    "type": "file",
    "size": 20,
    "sha256": hashlib.sha256(b"remember-this-secret").hexdigest(),
}


class _HarnessLaunchRefused(RuntimeError):
    """Same shape as guardkitfactory's PlayerLaunchRefused."""

    failure_kind = "agent_launch_refused"

    def __init__(self, message: str, *, profile: str, entries: list) -> None:
        super().__init__(message)
        self.profile = profile
        self.entries = tuple(dict(entry) for entry in entries)


def _refusal() -> _HarnessLaunchRefused:
    return _HarnessLaunchRefused(
        "dcode Player: run profile contains unexpected configuration or nonempty "
        f"memory; unexpected profile entries: {_ENTRY['path']} (file, "
        f"size={_ENTRY['size']}, sha256={_ENTRY['sha256']})",
        profile="/profiles/run",
        entries=[_ENTRY],
    )


class _RaisingHarness(HarnessAdapter):
    def __init__(self, error: BaseException) -> None:
        self.error = error
        self.calls = 0

    async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
        self.calls += 1
        raise self.error
        yield  # pragma: no cover - makes this an async generator

    @property
    def supports_resume(self) -> bool:
        return False


@pytest.fixture(autouse=True)
def _routine_fleet_route(m0_routine_fleet_route):
    """Declare the routine local-fleet route; no model is ever reached."""


@pytest.fixture
def worktree(tmp_path: Path) -> Mock:
    wt = Mock(spec=Worktree)
    wt.task_id = _TASK
    wt.path = tmp_path / "worktree"
    wt.path.mkdir(parents=True)
    wt.branch_name = f"autobuild/{_TASK}"
    wt.base_branch = "main"
    return wt


@pytest.fixture
def display() -> Mock:
    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    return progress


def _orchestrator(tmp_path: Path, worktree: Mock, display: Mock, invoker: AgentInvoker):
    manager = Mock()
    manager.create.return_value = worktree
    manager.worktrees_dir = worktree.path.parent
    return AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=4,
        agent_invoker=invoker,
        progress_display=display,
        worktree_manager=manager,
        enable_pre_loop=False,
        enable_checkpoints=False,
        enable_context=False,
    )


def _recovered(task_id, turn, **_kwargs) -> AgentInvocationResult:
    """What B463's state recovery produced: a synthetic report for the Coach."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=True,
        report={
            "task_id": task_id,
            "turn": turn,
            "_synthetic": True,
            "files_modified": [],
            "files_created": [],
            "tests_passed": False,
        },
        duration_seconds=0.0,
    )


def _coach_feedback(*, task_id, turn, **_kwargs) -> AgentInvocationResult:
    """The implementation feedback B463's Coach returned on each refused turn."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "task_id": task_id,
            "turn": turn,
            "decision": "feedback",
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "missing_requirement",
                    "description": "0/1 acceptance criteria verified",
                }
            ],
            "rationale": "Implement the endpoint",
        },
        duration_seconds=0.0,
    )


def _run_loop(tmp_path, worktree, display, mode: str, error: BaseException):
    invoker = AgentInvoker(
        worktree_path=worktree.path,
        sdk_timeout_seconds=60,
        use_task_work_delegation=True,
        model_name="qwen36-workhorse",
    )
    harness = _RaisingHarness(error)
    orchestrator = _orchestrator(tmp_path, worktree, display, invoker)
    coach = AsyncMock(side_effect=AssertionError("the Coach must not run"))
    with patch(
        "guardkit.orchestrator.agent_invoker.select_harness", return_value=harness
    ), patch.object(
        invoker, "_get_implementation_mode", return_value=mode
    ), patch.object(
        invoker, "_ensure_design_approved_state", return_value=None
    ), patch.object(
        invoker, "invoke_coach", coach
    ), patch.object(
        orchestrator, "_attempt_state_recovery", side_effect=_recovered
    ) as recovery, patch.object(
        orchestrator, "_invoke_coach_safely", side_effect=_coach_feedback
    ) as coach_safely:
        turns, decision = orchestrator._loop_phase(
            task_id=_TASK,
            requirements="Add the endpoint",
            acceptance_criteria=["The endpoint answers"],
            worktree=worktree,
        )
    return turns, decision, harness, recovery, coach_safely, coach, orchestrator


@pytest.mark.parametrize("mode", ["task-work", "direct"])
def test_one_launch_refusal_stops_the_task(tmp_path, worktree, display, mode):
    turns, decision, harness, recovery, coach_safely, coach, orchestrator = _run_loop(
        tmp_path, worktree, display, mode, _refusal()
    )

    # One refusal, one turn — not four turns of recovery and Coach feedback.
    assert harness.calls == 1
    assert decision == "error"
    assert len(turns) == 1
    turn = turns[0]
    assert turn.decision == "error"
    assert turn.coach_result is None
    assert turn.feedback is None
    recovery.assert_not_called()
    coach_safely.assert_not_called()
    coach.assert_not_called()

    # The reason and the inventory reach the task's result.
    result = turn.player_result
    assert result.success is False
    assert result.report["unrecoverable"] is True
    assert result.report["unrecoverable_reason"] == "agent launch refused"
    assert result.report["launch_refused_entries"] == [_ENTRY]
    assert result.report["launch_refused_profile"] == "/profiles/run"
    assert result.error.startswith("Unrecoverable: agent launch refused: ")
    assert _ENTRY["path"] in result.error and _ENTRY["sha256"] in result.error
    message = orchestrator._build_error_message("error", turns)
    assert "agent launch refused" in message and _ENTRY["path"] in message


@pytest.mark.parametrize("mode", ["task-work", "direct"])
def test_other_invocation_errors_behave_as_before(tmp_path, worktree, display, mode):
    """A different harness error still goes through state recovery and the Coach."""
    turns, decision, harness, recovery, coach_safely, _, _ = _run_loop(
        tmp_path, worktree, display, mode, RuntimeError("model server reset the connection")
    )

    # Unchanged behaviour: every turn is recovered, reviewed and retried.
    # (The orchestrator's own test specialist also calls the harness in
    # task-work mode, so the harness sees at least one call per turn.)
    assert len(turns) > 1 and harness.calls >= len(turns)
    assert recovery.call_count == len(turns)
    assert coach_safely.call_count == len(turns)
    assert all(turn.player_result.report.get("_synthetic") for turn in turns)
    assert all("unrecoverable_reason" not in turn.player_result.report for turn in turns)
    original = recovery.call_args_list[0].kwargs["original_error"]
    assert "model server reset the connection" in original
    assert "agent launch refused" not in original


def test_unrelated_error_raised_from_none_is_not_a_refusal():
    """An error raised ``from None`` while handling a refusal is not a refusal."""
    try:
        try:
            raise _refusal()
        except RuntimeError:
            raise ValueError("unrelated bookkeeping failure") from None
    except ValueError as unrelated:
        assert unrelated.__context__ is not None
        assert find_agent_launch_refusal(unrelated) is None
    try:
        try:
            raise _refusal()
        except RuntimeError:
            raise ValueError("raised while handling, context kept")
    except ValueError as implicit:
        assert find_agent_launch_refusal(implicit) is implicit.__context__


def test_refusal_is_found_through_a_wrapper():
    """Direct mode wraps harness errors; the refusal is still recognised."""
    refusal = _refusal()
    try:
        try:
            raise refusal
        except RuntimeError as inner:
            raise AgentInvocationError("SDK invocation failed for player") from inner
    except AgentInvocationError as wrapped:
        assert find_agent_launch_refusal(wrapped) is refusal
    assert find_agent_launch_refusal(RuntimeError("other")) is None

    mapped = AgentLaunchRefusedError.from_refusal(refusal)
    assert mapped.reason == "agent launch refused"
    assert mapped.entries == [_ENTRY]
    assert str(mapped).startswith("agent launch refused: dcode Player:")


def test_the_real_harness_refusal_is_recognised_when_installed():
    """When guardkitfactory is importable, its own type carries the marker."""
    harness = pytest.importorskip("guardkitfactory.harness")
    refused_type = getattr(harness, "PlayerLaunchRefused", None)
    if refused_type is None:
        pytest.skip("installed guardkitfactory predates PlayerLaunchRefused")
    error = refused_type("dcode Player: refused", profile="/p", entries=[_ENTRY])
    assert isinstance(error, harness.LangGraphHarnessError)
    assert find_agent_launch_refusal(error) is error
    assert AgentLaunchRefusedError.from_refusal(error).entries == [_ENTRY]
