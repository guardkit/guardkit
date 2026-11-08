"""A task that fails is tried once more before the next wave (Rich, 8 November
2026; build FEAT-E673 ran 277 minutes of later tasks on a failed one)."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator import task_work_scope
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.worktrees import Worktree


def _orchestrator(tmp_path: Path) -> FeatureOrchestrator:
    return FeatureOrchestrator(repo_root=tmp_path, max_turns=1, worktree_manager=MagicMock(), quiet=True)


def _worktree(path: Path) -> Worktree:
    return Worktree(task_id="FEAT-T", branch_name="autobuild/FEAT-T", path=path, base_branch="main")


def _feature(statuses: dict) -> MagicMock:
    feature = MagicMock()
    feature.id = "FEAT-T"
    feature.tasks = [MagicMock(id=task_id, status=status) for task_id, status in statuses.items()]
    return feature


def _done(task_id: str) -> TaskExecutionResult:
    return TaskExecutionResult(task_id=task_id, success=True, total_turns=1, final_decision="approved")


def _failed(task_id: str, decision: str = "error") -> TaskExecutionResult:
    return TaskExecutionResult(task_id=task_id, success=False, total_turns=1, final_decision=decision,
                               error="SDK timeout after 4320s")


def _wave(*results: TaskExecutionResult) -> WaveExecutionResult:
    return WaveExecutionResult(wave_number=3, task_ids=[r.task_id for r in results], results=list(results),
                               all_succeeded=all(r.success for r in results))


def _rerun(*results):
    return [_wave(result) for result in results]


def test_a_failed_task_is_retried_and_its_success_replaces_the_failure(tmp_path: Path) -> None:
    orch = _orchestrator(tmp_path)
    feature = _feature({"T-1": "completed", "T-2": "failed"})
    with patch.object(orch, "_execute_wave", side_effect=_rerun(_done("T-2"))) as execute:
        result = orch._retry_failed_tasks(3, feature, _worktree(tmp_path), _wave(_done("T-1"), _failed("T-2")))
    assert result.all_succeeded is True
    assert [r.task_id for r in result.results] == ["T-1", "T-2"]
    assert execute.call_count == 1
    args, kwargs = execute.call_args
    assert args[1] == ["T-2"]
    assert "SDK timeout after 4320s" in kwargs["seed_feedback"]


def test_a_task_that_fails_again_is_not_tried_a_third_time(tmp_path: Path) -> None:
    orch = _orchestrator(tmp_path)
    feature = _feature({"T-2": "failed"})
    with patch.object(orch, "_execute_wave", side_effect=_rerun(_failed("T-2", "max_turns_exceeded"))) as execute:
        result = orch._retry_failed_tasks(3, feature, _worktree(tmp_path), _wave(_failed("T-2")))
    assert result.all_succeeded is False
    assert result.results[0].final_decision == "max_turns_exceeded"
    assert execute.call_count == 1


def test_a_wave_with_no_failure_runs_nothing_more(tmp_path: Path) -> None:
    orch = _orchestrator(tmp_path)
    wave = _wave(_done("T-1"))
    with patch.object(orch, "_execute_wave") as execute:
        assert orch._retry_failed_tasks(3, _feature({"T-1": "completed"}), _worktree(tmp_path), wave) is wave
    execute.assert_not_called()


@pytest.mark.parametrize("decision", ["cancelled", "skipped", "deferred"])
def test_a_task_stopped_from_outside_is_not_retried(tmp_path: Path, decision: str) -> None:
    orch = _orchestrator(tmp_path)
    with patch.object(orch, "_execute_wave") as execute:
        orch._retry_failed_tasks(3, _feature({"T-2": "failed"}), _worktree(tmp_path), _wave(_failed("T-2", decision)))
    execute.assert_not_called()


def test_each_failed_task_gets_its_own_retry_with_its_own_event_id(tmp_path: Path) -> None:
    orch = _orchestrator(tmp_path)
    feature = _feature({"T-1": "failed", "T-2": "failed"})
    with patch.object(orch, "_execute_wave", side_effect=_rerun(_done("T-1"), _done("T-2"))) as execute:
        result = orch._retry_failed_tasks(3, feature, _worktree(tmp_path), _wave(_failed("T-1"), _failed("T-2")))
    assert result.all_succeeded is True
    attempts = [call.kwargs["attempt"] for call in execute.call_args_list]
    assert len(set(attempts)) == 2 and min(attempts) > 10


def _git_repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def test_the_only_failed_task_reopens_the_approved_part(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    _, git_dir = task_work_scope.identity(repo)
    task_work_scope._approval_stopped.add(str(git_dir))
    try:
        orch = _orchestrator(tmp_path)
        with patch.object(orch, "_execute_wave", side_effect=_rerun(_done("T-2"))):
            orch._retry_failed_tasks(3, _feature({"T-2": "failed"}), _worktree(repo), _wave(_failed("T-2")))
        assert str(git_dir) not in task_work_scope._approval_stopped
    finally:
        task_work_scope._approval_stopped.discard(str(git_dir))


def test_with_two_failed_tasks_the_approved_part_stays_stopped(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    _, git_dir = task_work_scope.identity(repo)
    task_work_scope._approval_stopped.add(str(git_dir))
    try:
        orch = _orchestrator(tmp_path)
        feature = _feature({"T-1": "failed", "T-2": "failed"})
        with patch.object(orch, "_execute_wave", side_effect=_rerun(_failed("T-1"), _failed("T-2"))):
            orch._retry_failed_tasks(3, feature, _worktree(repo), _wave(_failed("T-1"), _failed("T-2")))
        assert str(git_dir) in task_work_scope._approval_stopped
    finally:
        task_work_scope._approval_stopped.discard(str(git_dir))


def _feature_with_waves(*waves) -> tuple:
    feature = MagicMock()
    feature.id = "FEAT-T"
    feature.smoke_gates = None
    tasks = {}
    for wave in waves:
        for task_id in wave:
            tasks[task_id] = MagicMock(
                id=task_id, status="pending", dependencies=[], estimated_minutes=None,
                file_path=f"tasks/backlog/{task_id}.md", turns_completed=0,
            )
    feature.tasks = list(tasks.values())
    feature.orchestration.parallel_groups = [list(wave) for wave in waves]
    feature.execution.completed_waves = []
    return feature, tasks


def test_the_build_retries_before_the_next_wave_and_counts_the_wave_once(tmp_path: Path) -> None:
    orch = _orchestrator(tmp_path)
    feature, tasks = _feature_with_waves(["T-1"], ["T-2"])
    calls = []

    def dispatch(number, task_ids, _feature, _worktree, **kwargs):
        calls.append((number, list(task_ids), kwargs.get("seed_feedback") is not None))
        if len(calls) == 1:
            tasks["T-1"].status = "failed"
            return _wave(_failed("T-1"))
        return _wave(*[_done(task_id) for task_id in task_ids])

    with (
        patch.object(orch, "_execute_wave", side_effect=dispatch),
        patch.object(orch, "_mark_wave_completed"),
        patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"),
    ):
        results = orch._wave_phase(feature, _worktree(tmp_path))

    assert calls == [(1, ["T-1"], False), (1, ["T-1"], True), (2, ["T-2"], False)]
    assert len(results) == 2
    assert results[0].all_succeeded is True


def test_the_retry_really_runs_a_task_whose_status_is_failed(tmp_path: Path) -> None:
    """Through the real wave dispatcher: only a completed task is passed over."""
    orch = _orchestrator(tmp_path)
    feature, tasks = _feature_with_waves(["T-1"])
    tasks["T-1"].status = "failed"
    seen = []

    def run(task, _feature, _worktree, **kwargs):
        seen.append((task.id, kwargs.get("seed_feedback")))
        return _done(task.id)

    with (
        patch.object(orch, "_execute_task", side_effect=run),
        patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
              side_effect=lambda _f, task_id: tasks.get(task_id)),
        patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"),
    ):
        result = orch._retry_failed_tasks(1, feature, _worktree(tmp_path), _wave(_failed("T-1")))

    assert result.all_succeeded is True
    assert [task_id for task_id, _ in seen] == ["T-1"]
    assert "did not finish" in seen[0][1]


def test_the_failed_attempts_turn_files_are_moved_aside_before_the_retry(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    orch = _orchestrator(repo)
    task = MagicMock(id="T-1", status="failed")
    feature = MagicMock(id="FEAT-T")
    with (
        patch("guardkit.orchestrator.task_work_scope.checkout_lease") as lease,
        patch.object(orch, "_archive_previous_round", return_value=2) as archive,
        patch.object(orch, "_execute_task_owned", return_value=_done("T-1")),
        patch.object(orch, "_update_task_started"),
    ):
        lease.return_value.__enter__.return_value = MagicMock()
        orch._execute_task(task, feature, _worktree(repo), seed_feedback="try again")
        archive.assert_called_once()
        archive.reset_mock()
        task.status = "pending"
        orch._execute_task(task, feature, _worktree(repo), seed_feedback=None)
        archive.assert_not_called()
