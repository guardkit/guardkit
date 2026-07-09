"""Wave-0 baseline-green probe (red-baseline retro, L12 item 1).

After bootstrap / before wave 1, the orchestrator runs the feature smoke
command once, records baseline.json, and warns (report-only) when the base
suite is already red — so a pre-existing failure is a wave-0 warning, never
attributed to the first task's Coach.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from guardkit.orchestrator.baseline import read_baseline_from_worktree
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureOrchestration,
    FeatureTask,
    SmokeGates,
)
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.worktrees import Worktree


def _orchestrator(tmp_path):
    return FeatureOrchestrator(
        repo_root=tmp_path,
        worktree_manager=MagicMock(),
        task_timeout=3000,
        timeout_multiplier=1.0,
        max_turns=5,
    )


def _feature(smoke_command):
    return Feature(
        id="FEAT-X",
        name="F",
        description="d",
        created="2026-07-09T00:00:00Z",
        status="in_progress",
        complexity=5,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-A-001", name="a",
                file_path=Path("tasks/backlog/TASK-A-001.md"),
                complexity=3, dependencies=[], status="pending",
                implementation_mode="task-work", estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-A-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
        smoke_gates=SmokeGates(after_wave="all", command=smoke_command, expected_exit=0),
    )


def _worktree(path):
    return Worktree(
        task_id="FEAT-X", branch_name="autobuild/FEAT-X",
        path=path, base_branch="main",
    )


def test_red_baseline_records_and_warns(tmp_path, caplog):
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_slice.py").write_text(
        "def test_home():\n    assert 'english' == 'maths'\n"
    )
    orch = _orchestrator(tmp_path)
    feature = _feature("python -m pytest -q test_slice.py")

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    baseline = orch._measured_baseline
    assert baseline is not None
    assert baseline.passed is False
    assert any("test_home" in nid for nid in baseline.failing_node_ids)

    # baseline.json persisted under the feature dir.
    loaded = read_baseline_from_worktree(wt)
    assert loaded is not None and loaded.passed is False

    # Wave-0 warning fired (report-only).
    assert any(
        "not attributable to any task" in r.getMessage() for r in caplog.records
    )


def test_green_baseline_records_no_warning(tmp_path, caplog):
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    orch = _orchestrator(tmp_path)
    feature = _feature("python -m pytest -q test_ok.py")

    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(feature, _worktree(wt))

    assert orch._measured_baseline is not None
    assert orch._measured_baseline.passed is True
    assert not any(
        "not attributable to any task" in r.getMessage() for r in caplog.records
    )


def test_no_smoke_gates_skips_probe(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    orch = _orchestrator(tmp_path)
    feature = _feature("python -m pytest -q")
    feature.smoke_gates = None

    orch._run_baseline_probe(feature, _worktree(wt))
    assert orch._measured_baseline is None
    assert read_baseline_from_worktree(wt) is None
