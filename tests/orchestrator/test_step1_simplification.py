"""Step 1 of the factory simplification (24 October 2026).

Bookkeeping never ends work, and the approved part of a feature that did not
finish reaches Forge on GuardKit's stdout line as ``approved_head``. Real
checks that ran and failed still block.

Network-free: tmp_path git repositories only.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.feature_check import (
    STOPPED_BECAUSE_MARKER,
)
from guardkit.orchestrator.feature_loader import FeatureLoader
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.quality_gates.coach_validator import (
    IndependentTestResult,
)
from guardkit.orchestrator.task_work_scope import (
    approved_head,
    checkout_lease,
    register_fresh_checkout,
)
from guardkit.worktrees import Worktree


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("start\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    register_fresh_checkout(root, _git(root, "rev-parse", "HEAD"))
    return root


def _approve_task_a(root: Path) -> str:
    with checkout_lease(root) as lease:
        lease.admit("TASK-A", "FEAT-S1")
        (root / "a.txt").write_text("a\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "task A")
        lease.checkpoint_completed()
    return _git(root, "rev-parse", "HEAD")


# ============================================================================
# 2. Bookkeeping never ends work
# ============================================================================


def test_a_moved_head_is_not_fatal(repo: Path) -> None:
    with checkout_lease(repo) as lease:
        lease.admit("TASK-A", "FEAT-S1")
        (repo / "b.txt").write_text("b\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "the builder committed by itself")
        lease.verify()
    assert approved_head(repo) == _git(repo, "rev-parse", "HEAD")


def test_save_feature_never_raises(tmp_path: Path) -> None:
    blocker = tmp_path / "file-not-dir"
    blocker.write_text("x")
    feature = MagicMock()
    feature.id = "FEAT-S1"
    feature.file_path = blocker / "FEAT-S1.yaml"
    with patch.object(FeatureLoader, "_feature_to_dict", return_value={}):
        FeatureLoader.save_feature(feature, tmp_path)  # must not raise


def test_task_state_move_failure_keeps_the_real_path(tmp_path: Path) -> None:
    from guardkit.tasks.state_bridge import TaskStateBridge

    task_file = tmp_path / "tasks" / "backlog" / "TASK-A.md"
    task_file.parent.mkdir(parents=True)
    task_file.write_text("---\nid: TASK-A\nstatus: backlog\n---\n")
    (tmp_path / "tasks" / "design_approved").write_text("a file, not a folder")
    bridge = TaskStateBridge("TASK-A", tmp_path)
    assert bridge._move_task_to_state(task_file, "design_approved") == task_file
    assert task_file.exists()


def test_frontmatter_write_failure_does_not_raise(tmp_path: Path) -> None:
    from guardkit.tasks.state_bridge import TaskStateBridge

    bridge = TaskStateBridge("TASK-A", tmp_path)
    bridge._update_task_frontmatter(tmp_path / "missing.md", {"status": "x"})


def _feature_check_project(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "main"
    (repo_root / ".guardkit").mkdir(parents=True)
    (repo_root / ".guardkit" / "config.yaml").write_text(
        'toolchain:\n  test: "make test"\n  feature_check: "sh check.sh"\n'
    )
    worktree = tmp_path / "candidate"
    worktree.mkdir()
    return repo_root, worktree


# ============================================================================
# 3. The task's real test state, carried from the Coach's evidence
# ============================================================================


def _runner() -> AutoBuildOrchestrator:
    """A task runner with only the carried check state (no build set up)."""
    return AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)


def _failed_run() -> IndependentTestResult:
    return IndependentTestResult.from_run(
        tests_passed=False, test_command="make test",
        test_output_summary="1 failed", duration_seconds=0.1,
        output="FAILED test_x\n1 failed\n", resolved_interpreter=None,
        exit_code=1,
    )


def _passed_run() -> IndependentTestResult:
    return IndependentTestResult.from_run(
        tests_passed=True, test_command="make test",
        test_output_summary="3 passed", duration_seconds=0.1,
        output="3 passed\n", resolved_interpreter=None, exit_code=0,
    )


def _absent_run() -> IndependentTestResult:
    return IndependentTestResult.absent(
        test_command="make test", test_output_summary="timed out",
        duration_seconds=0.1, resolved_interpreter=None,
    )


def test_a_red_test_then_no_result_stays_red() -> None:
    runner = _runner()
    runner._carry_measured_checks(_failed_run())
    runner._carry_measured_checks(_absent_run())
    runner._carry_measured_checks(None)
    assert runner.real_check_failed is True


def test_a_red_test_then_a_measured_pass_clears() -> None:
    runner = _runner()
    runner._carry_measured_checks(_failed_run())
    runner._carry_measured_checks(_passed_run())
    assert runner.real_check_failed is False


def test_an_exception_ending_keeps_what_was_measured(tmp_path: Path) -> None:
    measured = SimpleNamespace(real_check_failed=True)

    def build(*_args, **_kwargs):
        measured.orchestrate = MagicMock(side_effect=RuntimeError("worker died"))
        return measured

    orchestrator = _orchestrator(tmp_path)
    task = SimpleNamespace(id="TASK-B", file_path="tasks/TASK-B.md")
    feature = MagicMock()
    feature.id = "FEAT-S1"
    with patch(
        "guardkit.orchestrator.feature_orchestrator.TaskLoader.load_task",
        return_value={"frontmatter": {}},
    ), patch(
        "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator",
        side_effect=build,
    ):
        result = orchestrator._execute_task_owned(task, feature, MagicMock())
    assert result.success is False
    assert result.real_check_failed is True


# ============================================================================
# 4. approved_head: in memory, through finalisation, onto stdout
# ============================================================================


def test_b_fails_before_admission_keeps_a(repo: Path) -> None:
    head_a = _approve_task_a(repo)
    with checkout_lease(repo) as lease:
        lease.poison("Task TASK-B was refused before admission")
    assert approved_head(repo) == head_a


def test_b_scope_record_write_failure_keeps_a(repo: Path) -> None:
    head_a = _approve_task_a(repo)
    from guardkit.orchestrator.paths import TaskArtifactPaths

    with patch.object(
        TaskArtifactPaths, "private_artifact_path", side_effect=OSError("disk full")
    ):
        with checkout_lease(repo) as lease:
            scope = lease.admit("TASK-B", "FEAT-S1")
            assert scope.task_id == "TASK-B"
            lease.poison("Task TASK-B was not approved")
    assert approved_head(repo) == head_a


def _orchestrator(tmp_path: Path) -> FeatureOrchestrator:
    repo_root = tmp_path / "main"
    repo_root.mkdir(exist_ok=True)
    return FeatureOrchestrator(
        repo_root=repo_root, max_turns=1, worktree_manager=MagicMock(), quiet=True
    )


def _feature(statuses: dict):
    feature = MagicMock()
    feature.id = "FEAT-S1"
    feature.scenarios = {}
    tasks = []
    for task_id, status in statuses.items():
        task = MagicMock()
        task.id = task_id
        task.status = status
        tasks.append(task)
    feature.tasks = tasks
    return feature


def _waves(b_real_check_failed=False, smoke_passed=None):
    results = [
        TaskExecutionResult("TASK-A", True, 1, "approved"),
        TaskExecutionResult(
            "TASK-B", False, 2, "max_turns_exceeded",
            error="not approved", real_check_failed=b_real_check_failed,
        ),
    ]
    wave = WaveExecutionResult(
        wave_number=1, task_ids=["TASK-A", "TASK-B"], results=results,
        all_succeeded=False,
    )
    if smoke_passed is not None:
        wave.smoke_gate_result = SimpleNamespace(
            passed=smoke_passed, command="make smoke", stderr="",
            exit_code=0 if smoke_passed else 1, timed_out=False,
        )
    return [wave]


def _stop_lines(out: str):
    prefix = STOPPED_BECAUSE_MARKER + " "
    return [json.loads(l[len(prefix):]) for l in out.splitlines() if l.startswith(prefix)]


def _finalize(tmp_path, repo, waves, capsys, write_feature=None):
    orchestrator = _orchestrator(tmp_path)
    worktree = Worktree(
        task_id="FEAT-S1", branch_name="autobuild/FEAT-S1", path=repo,
        base_branch="main",
    )
    feature = _feature({"TASK-A": "completed", "TASK-B": "failed"})
    with patch.object(
        FeatureLoader, "_write_feature", side_effect=write_feature or (lambda *a: None)
    ):
        result = orchestrator._finalize_phase(feature, waves, worktree)
    return result, _stop_lines(capsys.readouterr().out)


def test_a_approved_b_failed_prints_a_commit(tmp_path, repo, capsys) -> None:
    head_a = _approve_task_a(repo)
    result, lines = _finalize(tmp_path, repo, _waves(), capsys)
    assert result.success is False
    assert [line["approved_head"] for line in lines] == [head_a]
    assert lines[0]["feature_id"] == "FEAT-S1" and lines[0]["sentence"]


def test_failing_record_writes_still_give_a_result(tmp_path, repo, capsys) -> None:
    head_a = _approve_task_a(repo)
    result, lines = _finalize(
        tmp_path, repo, _waves(), capsys, write_feature=OSError("read-only")
    )
    assert result.success is False
    assert [line["approved_head"] for line in lines] == [head_a]


def _b_state(*turns) -> bool:
    """Task B's carried state after the given test runs, one per turn."""
    runner = _runner()
    for independent in turns:
        runner._carry_measured_checks(independent)
    return runner.real_check_failed


def test_b_red_test_then_no_result_withholds_approved_head(
    tmp_path, repo, capsys
) -> None:
    _approve_task_a(repo)
    red = _b_state(_failed_run(), _absent_run())
    _, lines = _finalize(tmp_path, repo, _waves(b_real_check_failed=red), capsys)
    assert lines == []


def test_b_red_test_then_pass_gives_approved_head(tmp_path, repo, capsys) -> None:
    head_a = _approve_task_a(repo)
    red = _b_state(_failed_run(), _passed_run())
    _, lines = _finalize(tmp_path, repo, _waves(b_real_check_failed=red), capsys)
    assert [line["approved_head"] for line in lines] == [head_a]


def test_red_smoke_check_withholds_approved_head(tmp_path, repo, capsys) -> None:
    _approve_task_a(repo)
    _, lines = _finalize(tmp_path, repo, _waves(smoke_passed=False), capsys)
    assert lines == []


def test_no_approved_task_prints_nothing(tmp_path, repo, capsys) -> None:
    _, lines = _finalize(tmp_path, repo, _waves(), capsys)
    assert lines == []
