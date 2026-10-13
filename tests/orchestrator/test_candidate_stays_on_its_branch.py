"""Keep the candidate on its branch (12 October 2026, build 0D7C).

0D7C finished with its checkout detached at a later checkpoint while its
branch still named an older commit: a checkpoint had committed on a detached
HEAD, so the work never reached the branch and the merge guard refused the
candidate. Who detached it is not known. Pinned here, on real git repositories:

* the checkpoint, under its existing lock, proceeds when HEAD is on the
  feature branch (even after another task's checkpoint advanced it),
  re-attaches the branch when HEAD is detached exactly at its tip, and
  otherwise refuses, naming the expected branch, the actual HEAD and the tip;
* a refused checkpoint stops the task with that reason;
* every agent invocation records HEAD before and after, with the invocations
  that overlapped it, and never stops anything;
* GuardKit's own branch checkouts for a merge leave a line in a build
  worktree's record, and nothing anywhere else.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from contextlib import aclosing
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest

from guardkit.orchestrator import head_identity
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, TurnRecord
from guardkit.orchestrator.head_identity import (
    ATTRIBUTION_ALONE,
    ATTRIBUTION_OVERLAPPING,
    expected_checkpoint_branch,
    invocation_finished,
    invocation_started,
    observe_invocation,
    read_entries,
    record_git_operation,
)
from guardkit.orchestrator.worktree_checkpoints import (
    CheckpointRefused,
    GitCommandExecutor,
    WorktreeCheckpointManager,
)
from guardkit.worktrees.manager import Worktree, WorktreeManager

BRANCH = "autobuild/FEAT-0D7C"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A build worktree on the feature branch, with two commits."""
    path = tmp_path / "wt"
    path.mkdir()
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "factory@example.invalid")
    _git(path, "config", "user.name", "Factory Test")
    (path / "app.txt").write_text("base\n")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "base")
    _git(path, "checkout", "-q", "-b", BRANCH)
    (path / "app.txt").write_text("feature start\n")
    _git(path, "commit", "-q", "-am", "feature start")
    (path / ".guardkit" / "autobuild").mkdir(parents=True)
    return path


def _manager(worktree: Path, task_id: str) -> WorktreeCheckpointManager:
    return WorktreeCheckpointManager(
        worktree_path=worktree, task_id=task_id, expected_branch=BRANCH
    )


def _tip(worktree: Path) -> str:
    return _git(worktree, "rev-parse", f"refs/heads/{BRANCH}")


def _head(worktree: Path) -> str:
    return _git(worktree, "rev-parse", "HEAD")


def _attached(worktree: Path) -> str:
    proc = subprocess.run(
        ["git", "symbolic-ref", "-q", "HEAD"], cwd=worktree,
        capture_output=True, text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


# ---------------------------------------------------------------------------
# At the checkpoint
# ---------------------------------------------------------------------------


def test_positive_control_another_tasks_checkpoint_during_an_invocation(
    worktree: Path,
) -> None:
    """Parallel tasks share the worktree; the branch advancing is normal."""
    task_a = _manager(worktree, "TASK-0D7C-001")
    task_b = _manager(worktree, "TASK-0D7C-002")
    before = _tip(worktree)

    token = invocation_started(worktree, role="player", task_id="TASK-0D7C-001", turn=1)
    (worktree / "b.txt").write_text("task b's work\n")
    task_b.create_checkpoint(turn=1, tests_passed=True)
    (worktree / "a.txt").write_text("task a's work\n")
    end = invocation_finished(token)

    # The branch moved under task A's invocation; recorded, never a stop.
    assert end["head_changed"] is True
    assert end["symbolic_ref_changed"] is False
    assert [op["task_id"] for op in end["git_operations_during"]] == [
        "TASK-0D7C-002"
    ]

    checkpoint = task_a.create_checkpoint(turn=1, tests_passed=True)

    assert _attached(worktree) == f"refs/heads/{BRANCH}"
    assert _tip(worktree) == checkpoint.commit_hash
    assert _git(worktree, "rev-list", "--count", f"{before}..{BRANCH}") == "2"
    assert "a.txt" in _git(worktree, "show", "--name-only", "--format=", "HEAD")


def test_detached_exactly_at_the_tip_is_reattached_with_a_warning(
    worktree: Path, caplog: pytest.LogCaptureFixture
) -> None:
    tip = _tip(worktree)
    _git(worktree, "checkout", "-q", "--detach")
    (worktree / "work.txt").write_text("the turn's work\n")

    with caplog.at_level(logging.WARNING):
        checkpoint = _manager(worktree, "TASK-0D7C-003").create_checkpoint(
            turn=1, tests_passed=True
        )

    assert _attached(worktree) == f"refs/heads/{BRANCH}"
    assert _tip(worktree) == checkpoint.commit_hash
    assert _git(worktree, "rev-parse", f"{checkpoint.commit_hash}^") == tip
    assert any(
        "re-attached" in r.getMessage() and BRANCH in r.getMessage()
        for r in caplog.records
    )
    operations = [
        e["operation"] for e in read_entries(worktree)
        if e.get("event") == "git_operation"
    ]
    assert any(op.startswith(f"re-attach {BRANCH}") for op in operations)


def test_detached_elsewhere_is_refused_naming_both_identities(
    worktree: Path,
) -> None:
    tip = _tip(worktree)
    _git(worktree, "checkout", "-q", "--detach", "HEAD~1")
    elsewhere = _head(worktree)
    (worktree / "work.txt").write_text("the turn's work\n")

    with pytest.raises(CheckpointRefused) as refused:
        _manager(worktree, "TASK-0D7C-003").create_checkpoint(
            turn=1, tests_passed=True
        )

    message = str(refused.value)
    assert f"Expected branch: {BRANCH}." in message
    assert f"Actual HEAD: detached at {elsewhere}." in message
    assert f"Branch tip: {tip}." in message
    # Nothing was committed: not on the branch, and not on the detached HEAD.
    assert _tip(worktree) == tip
    assert _head(worktree) == elsewhere
    assert _attached(worktree) == ""
    assert refused.value.branch_tip == tip
    assert refused.value.head == elsewhere


def test_another_branch_is_refused_naming_both_identities(
    worktree: Path,
) -> None:
    tip = _tip(worktree)
    _git(worktree, "checkout", "-q", "-b", "somebody-elses")

    with pytest.raises(CheckpointRefused) as refused:
        _manager(worktree, "TASK-0D7C-003").create_checkpoint(
            turn=2, tests_passed=None
        )

    message = str(refused.value)
    assert f"Expected branch: {BRANCH}." in message
    assert f"Actual HEAD: refs/heads/somebody-elses at {tip}." in message
    assert f"Branch tip: {tip}." in message
    assert _git(worktree, "rev-parse", "refs/heads/somebody-elses") == tip


def test_normal_serial_turns_are_unchanged_but_for_one_read(
    tmp_path: Path,
) -> None:
    """On the branch: one symbolic-ref read, then add, commit, rev-parse.

    Since 13 October 2026 one read sits between add and commit: the list of
    staged private records, empty here, so nothing is unstaged.
    """
    executor = Mock(spec=GitCommandExecutor)

    def _execute(command: List[str], cwd: Path, check: bool = True, timeout=None):
        if command[:2] == ["git", "symbolic-ref"]:
            return Mock(returncode=0, stdout=f"refs/heads/{BRANCH}\n", stderr="")
        if command[:3] == ["git", "diff", "--cached"]:
            return Mock(returncode=0, stdout="", stderr="")
        return Mock(returncode=0, stdout="abc123def456\n", stderr="")

    executor.execute.side_effect = _execute
    manager = WorktreeCheckpointManager(
        worktree_path=tmp_path,
        task_id="TASK-0D7C-001",
        git_executor=executor,
        expected_branch=BRANCH,
    )
    with patch.object(manager, "_save_checkpoints"):
        for turn in (1, 2):
            manager.create_checkpoint(turn=turn, tests_passed=True)

    commands = [c.args[0][:2] for c in executor.execute.call_args_list]
    assert commands == [
        ["git", "symbolic-ref"], ["git", "add"], ["git", "diff"],
        ["git", "commit"], ["git", "rev-parse"],
    ] * 2
    assert [cp.turn for cp in manager.checkpoints] == [1, 2]


def test_the_record_is_never_committed(worktree: Path) -> None:
    invocation_finished(
        invocation_started(worktree, role="player", task_id="TASK-0D7C-001", turn=1)
    )
    checkpoint = _manager(worktree, "TASK-0D7C-001").create_checkpoint(
        turn=1, tests_passed=True
    )
    committed = _git(worktree, "ls-tree", "-r", "--name-only", checkpoint.commit_hash)
    assert "head-identity.jsonl" not in committed
    assert (worktree / head_identity.RECORD_RELATIVE_PATH).is_file()


# ---------------------------------------------------------------------------
# A refused checkpoint stops the task
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decision", ["approve", "feedback"])
def test_a_refused_checkpoint_stops_the_task_with_its_reason(
    worktree: Path, decision: str
) -> None:
    _git(worktree, "checkout", "-q", "--detach", "HEAD~1")
    display = MagicMock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    orchestrator = AutoBuildOrchestrator(
        repo_root=worktree,
        max_turns=5,
        worktree_manager=Mock(),
        agent_invoker=Mock(),
        progress_display=display,
        pre_loop_gates=MagicMock(),
    )
    orchestrator._checkpoint_manager = _manager(worktree, "TASK-0D7C-003")
    turn_record = TurnRecord(
        turn=1,
        player_result=Mock(success=True, report={}, error=None),
        coach_result=AgentInvocationResult(
            task_id="TASK-0D7C-003", turn=1, agent_type="coach", success=True,
            report={"decision": decision, "rationale": "r", "issues": []},
            duration_seconds=1.0, error=None,
        ),
        decision=decision,
        feedback=None if decision == "approve" else "- fix it",
        timestamp="2026-10-12T21:40:00Z",
    )
    calls = []

    def _turn(*args, **kwargs):
        calls.append(1)
        return turn_record

    with patch.object(orchestrator, "_execute_turn", side_effect=_turn), \
            patch.object(orchestrator, "_capture_turn_state"), \
            patch.object(orchestrator, "_record_honesty"), \
            patch.object(orchestrator, "_display_criteria_progress"):
        history, final = orchestrator._loop_phase(
            task_id="TASK-0D7C-003",
            requirements="r",
            acceptance_criteria=["AC1"],
            worktree=Worktree(
                task_id="FEAT-0D7C", branch_name=BRANCH, path=worktree,
                base_branch="main",
            ),
        )

    assert final == "error"
    assert len(calls) == 1
    message = orchestrator._build_error_message(final, history)
    assert message.startswith("Checkpoint refused for TASK-0D7C-003 turn 1")
    assert f"Expected branch: {BRANCH}." in message


def test_the_declared_branch_wins_and_head_is_used_only_without_one(
    worktree: Path,
) -> None:
    assert expected_checkpoint_branch(worktree, BRANCH) == BRANCH
    assert expected_checkpoint_branch(worktree, "autobuild/other") == "autobuild/other"
    assert expected_checkpoint_branch(worktree, None) == BRANCH
    _git(worktree, "checkout", "-q", "--detach")
    assert expected_checkpoint_branch(worktree, BRANCH) == BRANCH
    assert expected_checkpoint_branch(worktree.parent / "missing", None) is None


def _feature_orchestrator():
    from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

    orchestrator = FeatureOrchestrator.__new__(FeatureOrchestrator)
    orchestrator._feature_branch_pinned = False
    return orchestrator


def test_a_later_task_starting_on_main_is_refused(worktree: Path) -> None:
    """The branch is pinned at build start; HEAD moving later is not adopted."""
    feature = _feature_orchestrator()
    declared = Worktree(
        task_id="FEAT-0D7C", branch_name=BRANCH, path=worktree, base_branch="main"
    )
    assert feature._pinned_feature_branch(declared) == BRANCH

    _git(worktree, "checkout", "-q", "main")  # an agent switched it mid-build
    pinned = feature._pinned_feature_branch(declared)
    assert pinned == BRANCH

    later_task = WorktreeCheckpointManager(
        worktree_path=worktree, task_id="TASK-0D7C-004",
        expected_branch=pinned, refuse_without_branch=True,
    )
    with pytest.raises(CheckpointRefused) as refused:
        later_task.create_checkpoint(turn=1, tests_passed=True)
    assert "Actual HEAD: refs/heads/main at" in str(refused.value)
    assert f"Expected branch: {BRANCH}." in str(refused.value)


def test_a_task_orchestrator_uses_the_pinned_branch_not_head(
    worktree: Path,
) -> None:
    """A task starting on main with the pinned branch passed in is refused."""
    _git(worktree, "checkout", "-q", "main")
    display = MagicMock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    orchestrator = AutoBuildOrchestrator(
        repo_root=worktree, max_turns=3, worktree_manager=Mock(),
        agent_invoker=Mock(), progress_display=display,
        pre_loop_gates=MagicMock(), expected_branch=BRANCH,
    )
    record = TurnRecord(
        turn=1,
        player_result=Mock(success=True, report={}, error=None),
        coach_result=AgentInvocationResult(
            task_id="TASK-0D7C-004", turn=1, agent_type="coach", success=True,
            report={"decision": "approve", "rationale": "r", "issues": []},
            duration_seconds=1.0, error=None,
        ),
        decision="approve", feedback=None, timestamp="2026-10-12T21:40:00Z",
    )
    with patch.object(orchestrator, "_execute_turn", return_value=record), \
            patch.object(orchestrator, "_capture_turn_state"), \
            patch.object(orchestrator, "_record_honesty"), \
            patch.object(orchestrator, "_display_criteria_progress"):
        history, final = orchestrator._loop_phase(
            task_id="TASK-0D7C-004", requirements="r", acceptance_criteria=["AC1"],
            worktree=Worktree(task_id="FEAT-0D7C", branch_name=BRANCH,
                              path=worktree, base_branch="main"),
        )
    assert final == "error"
    assert "Actual HEAD: refs/heads/main" in orchestrator._build_error_message(
        final, history
    )


def test_a_resume_on_an_agent_made_branch_is_refused_naming_both(
    worktree: Path,
) -> None:
    """A resumed build whose worktree was left on a branch an agent made."""
    _git(worktree, "checkout", "-q", "-b", "agent-made")
    feature = _feature_orchestrator()
    pinned = feature._pinned_feature_branch(Worktree(
        task_id="FEAT-0D7C", branch_name=BRANCH, path=worktree, base_branch="main"
    ))
    assert pinned == BRANCH

    with pytest.raises(CheckpointRefused) as refused:
        WorktreeCheckpointManager(
            worktree_path=worktree, task_id="TASK-0D7C-002",
            expected_branch=pinned, refuse_without_branch=True,
        ).create_checkpoint(turn=1, tests_passed=True)
    message = str(refused.value)
    assert f"Expected branch: {BRANCH}." in message
    assert "Actual HEAD: refs/heads/agent-made at" in message
    assert _git(worktree, "rev-parse", "refs/heads/agent-made") == _tip(worktree)


def test_a_feature_pinned_to_no_branch_is_not_re_read_per_task(
    worktree: Path,
) -> None:
    """Pinned to None at build start: a later task refuses, never reads HEAD."""
    display = MagicMock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    orchestrator = AutoBuildOrchestrator(
        repo_root=worktree, max_turns=3, worktree_manager=Mock(),
        agent_invoker=Mock(), progress_display=display,
        pre_loop_gates=MagicMock(),
        expected_branch=None, expected_branch_pinned=True,
    )
    record = TurnRecord(
        turn=1,
        player_result=Mock(success=True, report={}, error=None),
        coach_result=AgentInvocationResult(
            task_id="TASK-0D7C-004", turn=1, agent_type="coach", success=True,
            report={"decision": "approve", "rationale": "r", "issues": []},
            duration_seconds=1.0, error=None,
        ),
        decision="approve", feedback=None, timestamp="2026-10-12T21:40:00Z",
    )
    tip = _tip(worktree)
    with patch.object(orchestrator, "_execute_turn", return_value=record), \
            patch.object(orchestrator, "_capture_turn_state"), \
            patch.object(orchestrator, "_record_honesty"), \
            patch.object(orchestrator, "_display_criteria_progress"):
        history, final = orchestrator._loop_phase(
            task_id="TASK-0D7C-004", requirements="r", acceptance_criteria=["AC1"],
            worktree=Worktree(task_id="FEAT-0D7C", branch_name=BRANCH,
                              path=worktree, base_branch="main"),
        )
    assert final == "error"
    assert "no feature branch was determined" in (
        orchestrator._build_error_message(final, history)
    )
    assert _tip(worktree) == tip


def test_orchestrate_pins_after_setup_and_before_the_first_wave(
    worktree: Path,
) -> None:
    from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

    feature = FeatureOrchestrator.__new__(FeatureOrchestrator)
    declared = Worktree(
        task_id="FEAT-0D7C", branch_name=BRANCH, path=worktree, base_branch="main"
    )
    order = []

    def _setup(feature_id, base_branch):
        order.append("setup")
        return MagicMock(id="FEAT-0D7C"), declared

    def _wave(feature_obj, wt):
        order.append(("wave", feature._feature_branch_pinned, feature._feature_branch))
        return []

    real_pin = FeatureOrchestrator._pinned_feature_branch

    def _pin(self, wt):
        if not self._feature_branch_pinned:
            order.append("pin")
        return real_pin(self, wt)

    with patch.object(feature, "_setup_phase", side_effect=_setup), \
            patch.object(feature, "_wave_phase", side_effect=_wave), \
            patch.object(feature, "_finalize_phase", return_value=MagicMock()), \
            patch.object(FeatureOrchestrator, "_pinned_feature_branch", _pin):
        feature.orchestrate("FEAT-0D7C")

    assert order == ["setup", "pin", ("wave", True, BRANCH)]


def test_no_branch_known_refuses_rather_than_skipping(
    worktree: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _git(worktree, "checkout", "-q", "--detach")
    tip = _tip(worktree)
    with caplog.at_level(logging.ERROR):
        branch = expected_checkpoint_branch(worktree, None)
    assert branch is None
    assert any("No feature branch" in r.getMessage() for r in caplog.records)

    with pytest.raises(CheckpointRefused, match="no feature branch was determined"):
        WorktreeCheckpointManager(
            worktree_path=worktree, task_id="TASK-0D7C-001",
            expected_branch=branch, refuse_without_branch=True,
        ).create_checkpoint(turn=1, tests_passed=True)
    assert _head(worktree) == tip


# ---------------------------------------------------------------------------
# Before and after every invocation (evidence only)
# ---------------------------------------------------------------------------


def test_the_record_lists_overlapping_invocations(worktree: Path) -> None:
    player_a = invocation_started(worktree, role="player", task_id="TASK-A", turn=1)
    reviewer_b = invocation_started(
        worktree, role="specialist:code-reviewer", task_id="TASK-B", turn=1
    )
    _git(worktree, "checkout", "-q", "--detach")  # somebody detaches HEAD
    end_b = invocation_finished(reviewer_b)
    end_a = invocation_finished(player_a)
    later = invocation_started(worktree, role="coach", task_id="TASK-A", turn=1)
    end_later = invocation_finished(later)

    assert end_b["symbolic_ref_changed"] is True
    assert end_b["attribution"] == ATTRIBUTION_OVERLAPPING
    assert [o["task_id"] for o in end_b["overlapping_invocations"]] == ["TASK-A"]
    assert [o["role"] for o in end_a["overlapping_invocations"]] == [
        "specialist:code-reviewer"
    ]
    assert end_a["attribution"] == ATTRIBUTION_OVERLAPPING
    assert end_a["before"]["symbolic_ref"] == f"refs/heads/{BRANCH}"
    assert end_a["symbolic_ref"] is None
    # Finished before it began: not overlapping. And nothing changed.
    assert end_later["overlapping_invocations"] == []
    assert end_later["attribution"] is None


def test_stale_unfinished_starts_are_not_counted_as_overlapping(
    worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash, an earlier process or another build leaves a start with no end."""
    dead = subprocess.Popen(["true"])
    dead.wait()
    path = worktree / head_identity.RECORD_RELATIVE_PATH
    stale = [
        {"event": "invocation_start", "invocation_id": "crashed", "at": 1.0,
         "pid": dead.pid, "session": "x", "build_id": None, "role": "player"},
        {"event": "invocation_start", "invocation_id": "earlier-process",
         "at": 2.0, "pid": __import__("os").getpid(), "session": "not-this-one",
         "build_id": None, "role": "player"},
        {"event": "invocation_start", "invocation_id": "other-build", "at": 3.0,
         "pid": 1, "session": "y", "build_id": "BUILD-OLD", "role": "player"},
    ]
    path.write_text("".join(json.dumps(e) + "\n" for e in stale))
    monkeypatch.setenv("GUARDKIT_RUN_OWNER", "BUILD-NOW")

    live = invocation_started(worktree, role="coach", task_id="TASK-B", turn=1)
    mine = invocation_started(worktree, role="player", task_id="TASK-A", turn=1)
    end = invocation_finished(mine)

    assert [o["task_id"] for o in end["overlapping_invocations"]] == ["TASK-B"]
    invocation_finished(live)


def test_observing_a_stream_passes_events_and_never_stops(worktree: Path) -> None:
    async def _agent():
        yield "first"
        _git(worktree, "checkout", "-q", "--detach")  # the agent's shell
        yield "second"

    async def _run() -> List[str]:
        seen = []
        async with aclosing(
            observe_invocation(
                _agent(), worktree, role="player", task_id="TASK-A", turn=3
            )
        ) as stream:
            async for event in stream:
                seen.append(event)
        return seen

    assert asyncio.run(_run()) == ["first", "second"]
    entries = read_entries(worktree)
    assert [e["event"] for e in entries] == ["invocation_start", "invocation_end"]
    assert entries[1]["symbolic_ref_changed"] is True
    assert entries[1]["attribution"] == ATTRIBUTION_ALONE
    assert entries[1]["turn"] == 3


def test_a_closed_stream_still_records_its_end(worktree: Path) -> None:
    closed = []

    async def _agent():
        try:
            yield "only"
            yield "never read"
        finally:
            closed.append(True)

    async def _run() -> None:
        async with aclosing(
            observe_invocation(_agent(), worktree, role="coach", task_id="TASK-A")
        ) as stream:
            async for _ in stream:
                break

    asyncio.run(_run())
    assert closed == [True]
    assert [e["event"] for e in read_entries(worktree)] == [
        "invocation_start", "invocation_end",
    ]


def test_nothing_is_recorded_outside_a_build_worktree(tmp_path: Path) -> None:
    assert invocation_started(tmp_path, role="player") is None
    assert record_git_operation(tmp_path, actor="x", operation="y") is False
    assert not (tmp_path / head_identity.RECORD_RELATIVE_PATH).exists()


# ---------------------------------------------------------------------------
# GuardKit's own merge checkout leaves a line in a build worktree's record
# ---------------------------------------------------------------------------


def test_the_merge_checkout_is_recorded_in_a_build_worktree(worktree: Path) -> None:
    invocation_finished(
        invocation_started(worktree, role="player", task_id="TASK-A", turn=1)
    )
    manager = WorktreeManager.__new__(WorktreeManager)
    manager.repo_root = worktree
    manager._run_git = Mock()

    manager.merge(
        Worktree(task_id="FEAT-0D7C", branch_name=BRANCH, path=worktree,
                 base_branch="main"),
        target_branch="main",
        working_folder=worktree,
    )

    lines = [e for e in read_entries(worktree) if e.get("event") == "git_operation"]
    assert len(lines) == 1
    assert lines[0]["actor"] == "guardkit WorktreeManager.merge"
    assert lines[0]["operation"] == f"checkout main to merge {BRANCH}"
    assert lines[0]["task_id"] == "FEAT-0D7C"
    assert lines[0]["symbolic_ref"] == f"refs/heads/{BRANCH}"


def test_a_merge_in_a_main_copy_writes_no_record(worktree: Path) -> None:
    """No agent record there, so it is not a build worktree: nothing written."""
    manager = WorktreeManager.__new__(WorktreeManager)
    manager.repo_root = worktree
    manager._run_git = Mock()

    manager.merge(
        Worktree(task_id="FEAT-0D7C", branch_name=BRANCH, path=worktree,
                 base_branch="main"),
        target_branch="main",
    )

    assert not (worktree / head_identity.RECORD_RELATIVE_PATH).exists()


def test_a_held_record_lock_drops_the_line_within_the_deadline(worktree: Path, caplog) -> None:
    """Implementation review round 1, R4: the head-identity record is written
    around every invocation and inside checkpoint serialisation, so another
    process holding its lock must never hold either up for long."""
    import sys
    import time

    record = head_identity.record_path(worktree)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.touch()
    holder = subprocess.Popen(
        [
            sys.executable, "-c",
            "import fcntl, sys, time\n"
            "f = open(sys.argv[1], 'a')\n"
            "fcntl.flock(f, fcntl.LOCK_EX)\n"
            "print('held', flush=True)\n"
            "time.sleep(30)\n",
            str(record),
        ],
        stdout=subprocess.PIPE, text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "held"
        started = time.monotonic()
        with caplog.at_level(logging.WARNING):
            written = head_identity.record_git_operation(
                worktree, actor="test", operation="checkpoint", task_id="TASK-X"
            )
            token = head_identity.invocation_started(worktree, role="player", task_id="TASK-X")
            finished = head_identity.invocation_finished(token)
        elapsed = time.monotonic() - started

        assert written is False
        assert finished["record_status"] == head_identity.NOT_RECORDED_BUSY
        assert elapsed < 8, f"three busy writes took {elapsed:.1f}s"
        assert head_identity.NOT_RECORDED_BUSY in caplog.text
    finally:
        holder.kill()
        holder.wait()

    # With the lock free again, lines are written as before.
    assert head_identity.record_git_operation(
        worktree, actor="test", operation="checkpoint", task_id="TASK-X"
    ) is True


# ---------------------------------------------------------------------------
# Implementation review round 3, R8: the record's own I/O is bounded
# ---------------------------------------------------------------------------


async def _two_events():
    yield "a"
    yield "b"


def _observe(worktree: Path) -> list:
    async def _run():
        seen = []
        async with aclosing(
            head_identity.observe_invocation(
                _two_events(), worktree, role="player", task_id="TASK-R8-001", turn=1
            )
        ) as stream:
            async for event in stream:
                seen.append(event)
        return seen

    return asyncio.run(_run())


def _invocation_and_checkpoint(worktree: Path):
    import time

    started = time.monotonic()
    seen = _observe(worktree)
    (worktree / "work.txt").write_text("the task's work\n")
    checkpoint = _manager(worktree, "TASK-R8-001").create_checkpoint(turn=1, tests_passed=True)
    return seen, checkpoint, time.monotonic() - started


def _bound_for_one_turn() -> float:
    # start + end of the invocation, the checkpoint's git operation lines:
    # each bounded; generous slack for slow machines.
    return 4 * (3.0 + 0.5) + 6


def test_a_fifo_in_the_records_place_never_blocks_a_turn(worktree: Path) -> None:
    import os

    record = head_identity.record_path(worktree)
    record.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(record)

    seen, checkpoint, elapsed = _invocation_and_checkpoint(worktree)

    assert seen == ["a", "b"]
    assert elapsed < _bound_for_one_turn(), f"took {elapsed:.1f}s"
    assert _tip(worktree) == checkpoint.commit_hash
    assert _attached(worktree) == f"refs/heads/{BRANCH}"
    assert "work.txt" in _git(worktree, "show", "--name-only", "--format=", "HEAD")


@pytest.mark.parametrize("stalled", ["write", "read"])
def test_a_stalled_record_read_or_write_never_blocks_a_turn(
    worktree: Path, monkeypatch, stalled: str
) -> None:
    """A hung filesystem: the record's lock-and-write, or its read, never
    returns. Stalled at every primitive the record could use."""
    import os
    import pathlib
    import threading

    release = threading.Event()

    def _is_record(fd_or_path) -> bool:
        try:
            name = (
                os.readlink(f"/proc/self/fd/{fd_or_path}")
                if isinstance(fd_or_path, int)
                else str(fd_or_path)
            )
        except OSError:
            return False
        return name.endswith("head-identity.jsonl")

    # A record with a line in it, so reading it really reads.
    head_identity.record_git_operation(worktree, actor="test", operation="seed")
    if stalled == "write":
        real_flock, real_write = head_identity.fcntl.flock, os.write

        def _flock(fd, op):
            target = fd if isinstance(fd, int) else fd.fileno()
            if op & head_identity.fcntl.LOCK_EX and _is_record(target):
                release.wait()
            return real_flock(fd, op)

        def _write(fd, data):
            if _is_record(fd):
                release.wait()
            return real_write(fd, data)

        monkeypatch.setattr(head_identity.fcntl, "flock", _flock)
        monkeypatch.setattr(head_identity.os, "write", _write)
    else:
        real_read, real_read_text = os.read, pathlib.Path.read_text

        def _read(fd, n):
            if _is_record(fd):
                release.wait()
            return real_read(fd, n)

        def _read_text(self, *a, **k):
            if _is_record(self):
                release.wait()
            return real_read_text(self, *a, **k)

        monkeypatch.setattr(head_identity.os, "read", _read)
        monkeypatch.setattr(pathlib.Path, "read_text", _read_text)
    try:
        seen, checkpoint, elapsed = _invocation_and_checkpoint(worktree)
    finally:
        release.set()

    assert seen == ["a", "b"]
    assert elapsed < _bound_for_one_turn(), f"took {elapsed:.1f}s"
    assert _tip(worktree) == checkpoint.commit_hash
    assert "work.txt" in _git(worktree, "show", "--name-only", "--format=", "HEAD")


# ---------------------------------------------------------------------------
# Implementation review round 4, R12: incomplete history is never "alone"
# ---------------------------------------------------------------------------


def _move_head(worktree: Path) -> None:
    _git(worktree, "commit", "-q", "--allow-empty", "-m", "moved by someone")


def test_unreadable_history_makes_the_attribution_unknown(worktree: Path) -> None:
    import os

    token = invocation_started(worktree, role="player", task_id="TASK-R12-A", turn=1)
    _move_head(worktree)
    record = head_identity.record_path(worktree)
    os.chmod(record, 0)
    try:
        end = invocation_finished(token)
    finally:
        os.chmod(record, 0o644)

    assert end["head_changed"] is True
    assert end["attribution"].startswith(head_identity.ATTRIBUTION_UNKNOWN)
    assert end["attribution"] != head_identity.ATTRIBUTION_ALONE
    assert end["history_coverage"].startswith("not recorded")


def test_an_active_invocation_outside_the_read_tail_makes_it_unknown(
    worktree: Path, monkeypatch
) -> None:
    other = invocation_started(worktree, role="coach", task_id="TASK-R12-B", turn=1)
    for n in range(20):  # push B's start line out of a small tail
        head_identity.record_git_operation(
            worktree, actor="test", operation=f"padding {n}", task_id="TASK-R12-PAD"
        )
    monkeypatch.setattr(head_identity, "_READ_TAIL_BYTES", 1500)
    token = invocation_started(worktree, role="player", task_id="TASK-R12-A", turn=1)
    _move_head(worktree)

    end = invocation_finished(token)

    assert end["history_coverage"] == head_identity.HISTORY_TRUNCATED
    assert end["attribution"].startswith(head_identity.ATTRIBUTION_UNKNOWN)
    assert "TASK-R12-B" not in [o["task_id"] for o in end["overlapping_invocations"]]
    invocation_finished(other)


def test_complete_history_still_names_the_overlap(worktree: Path) -> None:
    other = invocation_started(worktree, role="coach", task_id="TASK-R12-B", turn=1)
    token = invocation_started(worktree, role="player", task_id="TASK-R12-A", turn=1)
    _move_head(worktree)

    end = invocation_finished(token)

    assert end["history_coverage"] == head_identity.HISTORY_COMPLETE
    assert end["attribution"] == head_identity.ATTRIBUTION_OVERLAPPING
    assert [o["task_id"] for o in end["overlapping_invocations"]] == ["TASK-R12-B"]
    invocation_finished(other)
