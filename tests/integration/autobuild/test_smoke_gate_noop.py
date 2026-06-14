"""Integration: features without smoke_gates run identically to today (TASK-SMK-F703A).

Zero-regression AC: the smoke-gate feature must not change behaviour for
features that don't configure it. This test pins that invariant.
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.worktrees import Worktree


def _make_orchestrator(tmp_path: Path) -> FeatureOrchestrator:
    return FeatureOrchestrator(
        repo_root=tmp_path,
        max_turns=1,
        worktree_manager=MagicMock(),
        quiet=True,
    )


def _make_worktree(path: Path) -> Worktree:
    return Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=path,
        base_branch="main",
    )


def _make_feature_no_smoke(task_ids_per_wave: List[List[str]]):
    feature = MagicMock()
    feature.id = "FEAT-TEST"
    feature.name = "Test Feature"
    feature.status = "in_progress"
    # AC: ``smoke_gates`` key absent → Feature.smoke_gates is None.
    feature.smoke_gates = None

    tasks = []
    for wave_task_ids in task_ids_per_wave:
        for tid in wave_task_ids:
            task = MagicMock()
            task.id = tid
            task.dependencies = []
            task.status = "pending"
            tasks.append(task)
    feature.tasks = tasks
    feature.orchestration.parallel_groups = task_ids_per_wave
    feature.execution.current_wave = 0
    feature.execution.completed_waves = []

    task_map = {t.id: t for t in tasks}
    return feature, task_map


def _succeeding_wave(wave_number: int, task_ids: List[str]) -> WaveExecutionResult:
    return WaveExecutionResult(
        wave_number=wave_number,
        task_ids=task_ids,
        results=[
            TaskExecutionResult(
                task_id=tid, success=True, total_turns=1, final_decision="approved"
            )
            for tid in task_ids
        ],
        all_succeeded=True,
    )


def test_no_smoke_gates_key_runs_unchanged(tmp_path: Path) -> None:
    """Feature without smoke_gates runs identically to pre-SMK behaviour.

    Specifically:
      - ``run_smoke_gate`` is never called
      - All waves execute in order
      - ``WaveExecutionResult.smoke_gate_result`` stays None on every wave
    """
    orchestrator = _make_orchestrator(tmp_path)
    worktree = _make_worktree(tmp_path)
    feature, task_map = _make_feature_no_smoke(
        [["TASK-001"], ["TASK-002"], ["TASK-003"]]
    )

    with (
        patch.object(orchestrator, "_preflight_check"),
        patch.object(orchestrator, "_pre_init_graphiti"),
        patch.object(orchestrator, "_bootstrap_environment"),
        patch.object(orchestrator, "_mark_wave_completed") as mock_mark,
        patch.object(
            orchestrator,
            "_execute_wave",
            side_effect=[
                _succeeding_wave(1, ["TASK-001"]),
                _succeeding_wave(2, ["TASK-002"]),
                _succeeding_wave(3, ["TASK-003"]),
            ],
        ) as mock_execute_wave,
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
            side_effect=lambda f, tid: task_map.get(tid),
        ),
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature",
        ),
        patch(
            "guardkit.orchestrator.feature_orchestrator.run_smoke_gate",
        ) as mock_run_smoke,
    ):
        results = orchestrator._wave_phase(feature, worktree)

    assert mock_execute_wave.call_count == 3, "All three waves must execute"
    assert len(results) == 3
    mock_run_smoke.assert_not_called()
    for wr in results:
        assert wr.smoke_gate_result is None
    # TASK-AB-COACHRUNPARITY01 (C1): the no-smoke-gate path still marks each
    # successful wave completed. The C1 fix moved _mark_wave_completed out of
    # _execute_wave into the smoke-gated _wave_phase call-site; this pins that
    # the move did not drop completion-marking for features without smoke gates.
    assert mock_mark.call_count == 3
