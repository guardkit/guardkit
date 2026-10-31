"""Repair 7: the smoke command and whole-feature check records.

Each declared command GuardKit runs outside the Coach carries the same run
record as the Coach's own check. Real commands in a real git worktree; the
suite-wide fence keeps Docker out of reach.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from guardkit.orchestrator.feature_check import FeatureCheckAttempt, run_feature_check_command
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureOrchestration,
    FeatureTask,
    SmokeGates,
)
from guardkit.orchestrator.run_evidence import (
    NOT_DECLARED,
    NOT_LOOKED_UP,
    SOURCE_CHANGED,
    SOURCE_UNCHANGED,
    request_from_repo,
)
from guardkit.orchestrator.smoke_gates import run_smoke_gate


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


def test_smoke_command_uses_the_request_it_is_given(wt, tmp_path):
    repo_root = tmp_path / "main-checkout"
    _declare(repo_root, {"environment_inventory": "printf inv"})
    result = run_smoke_gate(
        SmokeGates(after_wave="all", command="printf x > made.txt"),
        cwd=wt,
        wave_number=2,
        evidence=request_from_repo("smoke command", repo_root, feature="FEAT-X", wave=2),
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


def test_a_blocked_declaration_read_never_holds_the_smoke_command(wt, tmp_path, monkeypatch):
    """Round 4, R10: the declaration is read inside the record's begin phase,
    behind its bound; the smoke command's own result is unchanged."""
    import threading
    import time

    from guardkit.orchestrator import toolchain_declaration

    release = threading.Event()

    def _blocked(_root):
        release.wait()
        return None

    monkeypatch.setattr(toolchain_declaration, "load_toolchain_declaration", _blocked)
    try:
        for command, passed in (("true", True), ("false", False)):
            started = time.monotonic()
            result = run_smoke_gate(
                SmokeGates(after_wave="all", command=command),
                cwd=wt,
                wave_number=1,
                evidence=request_from_repo("smoke command", tmp_path, feature="FEAT-X"),
            )
            elapsed = time.monotonic() - started
            assert result.passed is passed
            assert elapsed < 15, f"took {elapsed:.1f}s"
            inventory = result.run_evidence["environment_inventory"]["status"]
            assert inventory.startswith("not recorded: timed out reading the toolchain declaration")
    finally:
        release.set()
