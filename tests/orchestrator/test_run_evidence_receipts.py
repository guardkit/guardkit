"""Repair 7: the baseline probe, smoke command and whole-feature check records.

Each declared command GuardKit runs outside the Coach carries the same run
record as the Coach's own check. Real commands in a real git worktree; the
suite-wide fence keeps Docker out of reach.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from guardkit.orchestrator.baseline import BaselineResult, read_baseline_from_worktree
from guardkit.orchestrator.feature_check import FeatureCheckAttempt, run_feature_check_command
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureOrchestration,
    FeatureTask,
    SmokeGates,
)
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.run_evidence import (
    NOT_DECLARED,
    NOT_LOOKED_UP,
    SOURCE_CHANGED,
    SOURCE_UNCHANGED,
    request_from_repo,
    requested,
)
from guardkit.orchestrator.smoke_gates import run_smoke_gate
from guardkit.worktrees import Worktree


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def wt(tmp_path) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    (root / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _declare(root: Path, block: dict) -> None:
    (root / ".guardkit").mkdir(parents=True, exist_ok=True)
    (root / ".guardkit" / "config.yaml").write_text(yaml.safe_dump({"toolchain": block}))


def test_smoke_command_record_without_a_request_says_not_looked_up(wt):
    result = run_smoke_gate(SmokeGates(after_wave="all", command="true"), cwd=wt, wave_number=1)
    record = result.run_evidence
    assert result.passed
    assert record["execution_root"] == str(wt)
    assert record["source"]["verdict"] == SOURCE_UNCHANGED
    assert record["environment_inventory"] == {"status": NOT_LOOKED_UP}


def test_smoke_command_uses_the_request_set_around_it(wt, tmp_path):
    repo_root = tmp_path / "main-checkout"
    _declare(repo_root, {"environment_inventory": "printf inv"})
    with requested(request_from_repo("smoke command", repo_root, feature="FEAT-X", wave=2)):
        result = run_smoke_gate(
            SmokeGates(after_wave="all", command="printf x > made.txt"), cwd=wt, wave_number=2
        )
    record = result.run_evidence
    assert record["command_kind"] == "smoke command"
    assert record["observer"]["feature"] == "FEAT-X" and record["observer"]["wave"] == 2
    assert record["environment_inventory"]["output"] == "inv"
    # A file the command made is reported as made; the source it started
    # with did not change.
    assert record["source"]["verdict"] == (
        f"{SOURCE_UNCHANGED}; 1 files created during the command"
    )
    assert record["source"]["changed_paths"] is None
    assert record["source"]["files_created_during_the_command"] == {
        "paths": ["made.txt"], "total": 1, "truncated": False,
    }


def test_a_timed_out_smoke_command_is_still_recorded(wt):
    result = run_smoke_gate(
        SmokeGates(after_wave="all", command="sleep 5", timeout=1), cwd=wt, wave_number=1
    )
    assert result.timed_out
    assert result.run_evidence["source"]["verdict"] == SOURCE_UNCHANGED


def test_whole_feature_check_carries_the_record(wt, tmp_path):
    repo_root = tmp_path / "main-checkout"
    _declare(repo_root, {"feature_check": "true"})
    run = run_feature_check_command(
        "true",
        cwd=wt,
        timeout=30,
        evidence=request_from_repo("whole-feature check", repo_root, feature="FEAT-X"),
    )
    assert run["exit_code"] == 0
    record = run["run_evidence"]
    assert record["environment_inventory"] == {"status": NOT_DECLARED}
    attempt = FeatureCheckAttempt(
        attempt=1, command="true", candidate_sha="x", passed=True, run_evidence=record
    )
    out = attempt.to_dict()
    assert out["run_evidence"]["command_kind"] == "whole-feature check"
    json.dumps(out)


def _feature(command: str) -> Feature:
    return Feature(
        id="FEAT-X",
        name="F",
        description="d",
        created="2026-10-12T00:00:00Z",
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
        smoke_gates=SmokeGates(after_wave="all", command=command, expected_exit=0),
    )


def test_baseline_probe_record_is_written_with_the_run_record(wt, tmp_path):
    repo_root = tmp_path / "main-checkout"
    _declare(repo_root, {"environment_inventory": "printf 'pkg 1.0'"})
    orch = FeatureOrchestrator(
        repo_root=repo_root,
        worktree_manager=MagicMock(),
        task_timeout=3000,
        timeout_multiplier=1.0,
        max_turns=5,
    )
    feature = _feature(f'"{sys.executable}" -m pytest -q -p no:cacheprovider test_ok.py')
    orch._run_baseline_probe(
        feature,
        Worktree(task_id="FEAT-X", branch_name="autobuild/FEAT-X", path=wt, base_branch="main"),
    )

    measured = orch._measured_baseline
    assert measured is not None and measured.passed
    record = measured.run_evidence
    assert record["command_kind"] == "baseline probe"
    assert record["observer"]["feature"] == "FEAT-X"
    assert record["environment_inventory"]["output"] == "pkg 1.0"
    assert record["source"]["before"]["head"] == _git(wt, "rev-parse", "HEAD").strip()

    loaded = read_baseline_from_worktree(wt)
    assert loaded is not None
    assert loaded.run_evidence["command_kind"] == "baseline probe"


def test_baseline_record_round_trips_and_old_records_read_empty():
    old = BaselineResult.from_dict({"command": "x", "passed": True, "exit_code": 0})
    assert old.run_evidence == {}
    new = BaselineResult(
        command="x", expected_exit=0, passed=True, exit_code=0, run_evidence={"a": 1}
    )
    assert BaselineResult.from_dict(new.to_dict()).run_evidence == {"a": 1}
