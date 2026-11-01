"""
Integration tests for TASK-BOOT-3CAF: Inter-wave bootstrap hook.

Verifies that _wave_phase() in FeatureOrchestrator marks a bootstrap as due
between waves, so the project's declared install runs again before Wave 2
when a file it serves changed. (1 November 2026: the tests of installs
inferred from manifests were removed with the inference; installs come only
from the project's declaration.)
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


# ============================================================================
# Helpers
# ============================================================================


def _make_orchestrator(tmp_path: Path) -> FeatureOrchestrator:
    """Create a minimal FeatureOrchestrator for testing."""
    mock_wm = MagicMock()
    return FeatureOrchestrator(
        repo_root=tmp_path,
        max_turns=1,
        worktree_manager=mock_wm,
        quiet=True,
    )


def _make_worktree(path: Path):
    """Create a minimal Worktree."""
    from guardkit.worktrees import Worktree

    return Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=path,
        base_branch="main",
    )


def _make_feature(task_ids_per_wave: List[List[str]]):
    """
    Create a minimal Feature mock with given wave structure.

    Parameters
    ----------
    task_ids_per_wave : List[List[str]]
        e.g. [["TASK-001"], ["TASK-002"]] for 2 waves
    """
    feature = MagicMock()
    feature.id = "FEAT-TEST"
    feature.name = "Test Feature"
    feature.status = "in_progress"

    # Build task list
    tasks = []
    for wave_idx, wave_task_ids in enumerate(task_ids_per_wave, 1):
        for tid in wave_task_ids:
            task = MagicMock()
            task.id = tid
            task.name = f"Task {tid}"
            task.status = "pending"
            task.dependencies = []
            task.turns_completed = 0
            task.current_turn = 0
            task.result = None
            task.file_path = f"tasks/backlog/test-feature/{tid}.md"
            # `_resolve_wave_task_timeouts` compares this against numbers, so
            # a MagicMock's auto-attribute raises TypeError. None is the real
            # "no estimate given" value and takes the default-timeout path.
            task.estimated_minutes = None
            tasks.append(task)

    feature.tasks = tasks
    feature.orchestration.parallel_groups = task_ids_per_wave

    # Execution tracking
    feature.execution.current_wave = 0
    feature.execution.completed_waves = []
    feature.execution.last_updated = None
    feature.execution.tasks_completed = 0
    feature.execution.tasks_failed = 0

    # find_task helper
    task_map = {t.id: t for t in tasks}

    return feature, task_map


def _successful_task_result(task_id: str) -> TaskExecutionResult:
    """Create a successful TaskExecutionResult."""
    return TaskExecutionResult(
        task_id=task_id,
        success=True,
        total_turns=1,
        final_decision="approved",
    )


def _successful_wave_result(
    wave_number: int, task_ids: List[str]
) -> WaveExecutionResult:
    """Create a successful WaveExecutionResult."""
    return WaveExecutionResult(
        wave_number=wave_number,
        task_ids=task_ids,
        results=[_successful_task_result(tid) for tid in task_ids],
        all_succeeded=True,
    )


# ============================================================================
# Tests: Inter-Wave Bootstrap Hook
# ============================================================================


class TestInterWaveBootstrapHook:
    """Tests that _wave_phase calls _bootstrap_environment between waves."""

    def test_bootstrap_called_before_wave_2(self, tmp_path: Path) -> None:
        """_bootstrap_environment is called before Wave 2 starts."""
        orchestrator = _make_orchestrator(tmp_path)
        worktree = _make_worktree(tmp_path)
        feature, task_map = _make_feature([["TASK-001"], ["TASK-002"]])

        pending_at_wave=[]
        def dispatch(number, task_ids, *args):
            pending_at_wave.append(bool(getattr(orchestrator, "_bootstrap_pending", False)))
            orchestrator._bootstrap_pending=False  # The admitted task consumes it.
            return _successful_wave_result(number, task_ids)

        with (
            patch.object(orchestrator, "_bootstrap_environment") as mock_bootstrap,
            patch.object(
                orchestrator,
                "_execute_wave",
                side_effect=dispatch,
            ),
            patch.object(orchestrator, "_mark_wave_completed"),
            patch(
                "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
                side_effect=lambda f, tid: task_map.get(tid),
            ),
            patch(
                "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature",
            ),
        ):
            results = orchestrator._wave_phase(feature, worktree)

        # Queue construction cannot run a checkout writer. The first
        # admitted task consumes exactly one pending bootstrap per new wave.
        mock_bootstrap.assert_not_called()
        assert pending_at_wave == [False, True]
        assert len(results) == 2

    def test_bootstrap_not_called_for_wave_1(self, tmp_path: Path) -> None:
        """_bootstrap_environment is NOT called before the first wave."""
        orchestrator = _make_orchestrator(tmp_path)
        worktree = _make_worktree(tmp_path)
        feature, task_map = _make_feature([["TASK-001"]])

        with (
            patch.object(orchestrator, "_bootstrap_environment") as mock_bootstrap,
            patch.object(
                orchestrator,
                "_execute_wave",
                return_value=_successful_wave_result(1, ["TASK-001"]),
            ),
            patch.object(orchestrator, "_mark_wave_completed"),
            patch(
                "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
                side_effect=lambda f, tid: task_map.get(tid),
            ),
            patch(
                "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature",
            ),
        ):
            results = orchestrator._wave_phase(feature, worktree)

        # Bootstrap should NOT be called for a single-wave feature
        mock_bootstrap.assert_not_called()
        assert len(results) == 1

    def test_bootstrap_called_before_each_subsequent_wave(
        self, tmp_path: Path
    ) -> None:
        """_bootstrap_environment is called before waves 2, 3, and 4."""
        orchestrator = _make_orchestrator(tmp_path)
        worktree = _make_worktree(tmp_path)
        feature, task_map = _make_feature(
            [["TASK-001"], ["TASK-002"], ["TASK-003"], ["TASK-004"]]
        )

        pending_at_wave=[]
        def dispatch(number, task_ids, *args):
            pending_at_wave.append(bool(getattr(orchestrator, "_bootstrap_pending", False)))
            orchestrator._bootstrap_pending=False
            return _successful_wave_result(number, task_ids)

        with (
            patch.object(orchestrator, "_bootstrap_environment") as mock_bootstrap,
            patch.object(
                orchestrator,
                "_execute_wave",
                side_effect=dispatch,
            ),
            patch.object(orchestrator, "_mark_wave_completed"),
            patch(
                "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
                side_effect=lambda f, tid: task_map.get(tid),
            ),
            patch(
                "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature",
            ),
        ):
            results = orchestrator._wave_phase(feature, worktree)

        mock_bootstrap.assert_not_called()
        assert pending_at_wave == [False, True, True, True]
        assert len(results) == 4
