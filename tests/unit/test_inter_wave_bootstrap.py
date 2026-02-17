"""
Integration tests for TASK-BOOT-3CAF: Inter-wave bootstrap hook.

Verifies that _wave_phase() in FeatureOrchestrator calls
_bootstrap_environment() between waves so that dependencies created
during Wave 1 (e.g. pyproject.toml) are installed before Wave 2 runs.

Coverage Target: >=85%
Test Count: 8 tests
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    BootstrapResult,
    DetectedManifest,
)
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

        with (
            patch.object(orchestrator, "_preflight_check"),
            patch.object(orchestrator, "_pre_init_graphiti"),
            patch.object(orchestrator, "_bootstrap_environment") as mock_bootstrap,
            patch.object(
                orchestrator,
                "_execute_wave",
                side_effect=[
                    _successful_wave_result(1, ["TASK-001"]),
                    _successful_wave_result(2, ["TASK-002"]),
                ],
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

        # Bootstrap should be called exactly once (before wave 2)
        mock_bootstrap.assert_called_once_with(worktree)
        assert len(results) == 2

    def test_bootstrap_not_called_for_wave_1(self, tmp_path: Path) -> None:
        """_bootstrap_environment is NOT called before the first wave."""
        orchestrator = _make_orchestrator(tmp_path)
        worktree = _make_worktree(tmp_path)
        feature, task_map = _make_feature([["TASK-001"]])

        with (
            patch.object(orchestrator, "_preflight_check"),
            patch.object(orchestrator, "_pre_init_graphiti"),
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

        with (
            patch.object(orchestrator, "_preflight_check"),
            patch.object(orchestrator, "_pre_init_graphiti"),
            patch.object(orchestrator, "_bootstrap_environment") as mock_bootstrap,
            patch.object(
                orchestrator,
                "_execute_wave",
                side_effect=[
                    _successful_wave_result(i, [f"TASK-00{i}"])
                    for i in range(1, 5)
                ],
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

        # Bootstrap called 3 times: before waves 2, 3, and 4
        assert mock_bootstrap.call_count == 3
        mock_bootstrap.assert_has_calls(
            [call(worktree), call(worktree), call(worktree)]
        )
        assert len(results) == 4


class TestInterWaveBootstrapDedup:
    """Tests that hash-based dedup prevents redundant installs between waves."""

    def test_no_redundant_install_when_manifests_unchanged(
        self, tmp_path: Path
    ) -> None:
        """When manifests haven't changed between waves, no install runs."""
        (tmp_path / "requirements.txt").write_text("flask\n")

        orchestrator = _make_orchestrator(tmp_path)
        worktree = _make_worktree(tmp_path)

        # First call: installs (hash miss)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result1 = orchestrator._bootstrap_environment(worktree)

        assert result1 is not None
        assert result1.skipped is False
        assert result1.installs_attempted == 1

        # Second call: skips (hash hit — manifest unchanged)
        with patch("subprocess.run") as mock_run:
            result2 = orchestrator._bootstrap_environment(worktree)

        mock_run.assert_not_called()
        assert result2 is not None
        assert result2.skipped is True

    def test_installs_when_new_manifest_appears(self, tmp_path: Path) -> None:
        """When a new manifest appears between waves, install runs again."""
        (tmp_path / "requirements.txt").write_text("flask\n")

        orchestrator = _make_orchestrator(tmp_path)
        worktree = _make_worktree(tmp_path)

        # First call: installs requirements.txt
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result1 = orchestrator._bootstrap_environment(worktree)

        assert result1 is not None
        assert result1.skipped is False

        # Simulate Wave 1 creating a new manifest (package.json)
        (tmp_path / "package.json").write_text('{"name":"app"}\n')

        # Second call: detects new manifest, installs again
        with patch("subprocess.run", return_value=mock_result):
            result2 = orchestrator._bootstrap_environment(worktree)

        assert result2 is not None
        assert result2.skipped is False
        # Should have attempted 2 installs (requirements.txt + package.json)
        assert result2.installs_attempted == 2

    def test_installs_when_manifest_content_changes(self, tmp_path: Path) -> None:
        """When manifest content changes between waves, install runs again."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("flask\n")

        orchestrator = _make_orchestrator(tmp_path)
        worktree = _make_worktree(tmp_path)

        # First call: installs
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result1 = orchestrator._bootstrap_environment(worktree)

        assert result1 is not None
        assert result1.skipped is False

        # Simulate Wave 1 adding a dependency to requirements.txt
        req_file.write_text("flask\nsqlalchemy\n")

        # Second call: content changed, installs again
        with patch("subprocess.run", return_value=mock_result):
            result2 = orchestrator._bootstrap_environment(worktree)

        assert result2 is not None
        assert result2.skipped is False
        assert result2.installs_attempted == 1


class TestInterWaveBootstrapGreenfield:
    """End-to-end scenario: Wave 1 creates pyproject.toml, Wave 2 needs it."""

    def test_greenfield_scenario_wave1_creates_manifest(
        self, tmp_path: Path
    ) -> None:
        """
        Greenfield scenario: worktree starts empty, Wave 1 creates
        pyproject.toml, inter-wave bootstrap detects and installs it
        before Wave 2 starts.
        """
        orchestrator = _make_orchestrator(tmp_path)
        worktree = _make_worktree(tmp_path)

        # Before any waves: no manifests
        result_before = orchestrator._bootstrap_environment(worktree)
        assert result_before is None  # No manifests found

        # Simulate Wave 1 creating pyproject.toml (scaffolding task)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\ndependencies = ["sqlalchemy"]\n'
        )

        # Inter-wave bootstrap: detects and installs the new manifest
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result_after = orchestrator._bootstrap_environment(worktree)

        # Verify bootstrap detected and installed
        assert result_after is not None
        assert result_after.skipped is False
        assert result_after.success is True
        assert "python" in result_after.stacks_detected
        assert result_after.installs_attempted == 1
        assert result_after.installs_failed == 0

        # Verify the install command was run
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "pip" in " ".join(call_args[0][0])

    def test_greenfield_no_redundant_install_wave3(self, tmp_path: Path) -> None:
        """
        After bootstrap installs in Wave 2, Wave 3 doesn't reinstall
        if the manifest hasn't changed.
        """
        orchestrator = _make_orchestrator(tmp_path)
        worktree = _make_worktree(tmp_path)

        # Simulate Wave 1 creating pyproject.toml
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\ndependencies = ["sqlalchemy"]\n'
        )

        # Inter-wave bootstrap before Wave 2: installs
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result_wave2 = orchestrator._bootstrap_environment(worktree)
        assert result_wave2 is not None
        assert result_wave2.skipped is False

        # Inter-wave bootstrap before Wave 3: skips (hash match)
        with patch("subprocess.run") as mock_run:
            result_wave3 = orchestrator._bootstrap_environment(worktree)
        mock_run.assert_not_called()
        assert result_wave3 is not None
        assert result_wave3.skipped is True
