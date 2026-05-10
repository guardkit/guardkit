"""Integration test: task-work writes bdd_results into task_work_results.json.

Coverage Target: AC for TASK-BDD-E8954

Verifies that when ``AgentInvoker._write_task_work_results`` writes the
results JSON, the BDD oracle is consulted and its three-state outcome is
embedded under the ``bdd_results`` key. The pytest-bdd subprocess seam is
patched so this remains a hermetic, fast test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates import bdd_runner
from guardkit.orchestrator.quality_gates.bdd_runner import (
    BDDResult,
    FailureDetail,
    PendingDetail,
)


_PASS_FEATURE = """\
Feature: Login

  @task:TASK-001
  Scenario: User logs in
    Given a valid user
    When the user logs in
    Then the user is greeted
"""


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    (tmp_path / "features").mkdir()
    return tmp_path


def _write_feature(worktree: Path, name: str, body: str) -> Path:
    fp = worktree / "features" / name
    fp.write_text(body, encoding="utf-8")
    return fp


def _make_invoker(worktree: Path) -> AgentInvoker:
    # The constructor performs no SDK setup at import time; we only need the
    # worktree to exercise _write_task_work_results.
    return AgentInvoker(worktree_path=worktree, max_turns_per_agent=5, sdk_timeout_seconds=60)


def test_bdd_results_written_to_task_work_json(worktree: Path, monkeypatch):
    """AC: bdd_results object in task_work_results.json includes all three counters."""
    _write_feature(worktree, "login.feature", _PASS_FEATURE)

    # Stub bdd_runner.run_bdd_for_task — we are testing wiring, not pytest-bdd.
    fake_result = BDDResult(
        scenarios_passed=2,
        scenarios_failed=1,
        scenarios_pending=1,
        failures=[FailureDetail("features/login.feature", "Bad path", "Then x", "boom")],
        pending=[PendingDetail("features/login.feature", "Future scenario", "When future")],
        feature_files=["features/login.feature"],
        tag="@task:TASK-001",
    )

    def fake_run(task_id, worktree_path, **kwargs):
        assert task_id == "TASK-001"
        assert Path(worktree_path) == worktree
        return fake_result

    # Patch on the qualified path imported by agent_invoker._run_bdd_oracle.
    monkeypatch.setattr(bdd_runner, "run_bdd_for_task", fake_run)

    invoker = _make_invoker(worktree)
    result_data = {
        "tests_passed": 12,
        "tests_failed": 0,
        "coverage": 82.0,
        "quality_gates_passed": True,
        "files_modified": [],
        "files_created": [],
        "phases": {},
    }

    results_file = invoker._write_task_work_results("TASK-001", result_data)

    assert results_file.exists()
    payload = json.loads(results_file.read_text())

    assert "bdd_results" in payload
    bdd = payload["bdd_results"]
    # All three counters present (per AC).
    assert bdd["scenarios_passed"] == 2
    assert bdd["scenarios_failed"] == 1
    assert bdd["scenarios_pending"] == 1
    assert bdd["failures"][0]["scenario_name"] == "Bad path"
    assert bdd["pending"][0]["scenario_name"] == "Future scenario"
    assert bdd["tag"] == "@task:TASK-001"


def test_bdd_results_absent_when_no_feature_files(worktree: Path, monkeypatch):
    """When no .feature files exist, bdd_results key MUST NOT appear (silent skip)."""
    # No .feature file written; runner returns None.
    invoker = _make_invoker(worktree)
    result_data = {
        "tests_passed": 5,
        "tests_failed": 0,
        "coverage": 90.0,
        "quality_gates_passed": True,
        "files_modified": [],
        "files_created": [],
        "phases": {},
    }

    results_file = invoker._write_task_work_results("TASK-001", result_data)
    payload = json.loads(results_file.read_text())

    assert "bdd_results" not in payload  # absence == identical to today


def test_bdd_runner_exception_does_not_break_writer(worktree: Path, monkeypatch):
    """A raising bdd_runner must be swallowed — task_work_results.json must still be written."""
    _write_feature(worktree, "login.feature", _PASS_FEATURE)

    def boom(*_args, **_kwargs):
        raise RuntimeError("pytest-bdd exploded")

    monkeypatch.setattr(bdd_runner, "run_bdd_for_task", boom)

    invoker = _make_invoker(worktree)
    result_data = {
        "tests_passed": 1,
        "tests_failed": 0,
        "coverage": 80.0,
        "quality_gates_passed": True,
        "files_modified": [],
        "files_created": [],
        "phases": {},
    }

    results_file = invoker._write_task_work_results("TASK-001", result_data)
    payload = json.loads(results_file.read_text())

    # Wiring degrades gracefully — bdd_results omitted, but file is written.
    assert results_file.exists()
    assert "bdd_results" not in payload


# ---------------------------------------------------------------------------
# TASK-AB-001: orchestrator threads python_executable through to bdd_runner
# ---------------------------------------------------------------------------


def _make_fake_python(worktree: Path, name: str) -> Path:
    """Create an executable placeholder under <worktree>/.venv/bin/<name>."""
    venv_bin = worktree / ".venv" / "bin"
    venv_bin.mkdir(parents=True, exist_ok=True)
    fake = venv_bin / name
    fake.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake.chmod(0o755)
    return fake


def test_orchestrator_passes_worktree_python3_to_bdd_runner(worktree: Path, monkeypatch):
    """AC: when <worktree>/.venv/bin/python3 exists, it is forwarded as python_executable."""
    _write_feature(worktree, "login.feature", _PASS_FEATURE)
    expected_python = _make_fake_python(worktree, "python3")

    captured: dict = {}

    def fake_run(task_id, worktree_path, **kwargs):
        captured["task_id"] = task_id
        captured["worktree_path"] = worktree_path
        captured["kwargs"] = kwargs
        return None

    monkeypatch.setattr(bdd_runner, "run_bdd_for_task", fake_run)

    invoker = _make_invoker(worktree)
    invoker._run_bdd_oracle("TASK-001")

    assert captured["kwargs"]["python_executable"] == str(expected_python)


def test_orchestrator_falls_back_to_python_when_python3_missing(
    worktree: Path, monkeypatch
):
    """Resolution order: python3 → python → None."""
    _write_feature(worktree, "login.feature", _PASS_FEATURE)
    expected_python = _make_fake_python(worktree, "python")

    captured: dict = {}

    def fake_run(task_id, worktree_path, **kwargs):
        captured["kwargs"] = kwargs
        return None

    monkeypatch.setattr(bdd_runner, "run_bdd_for_task", fake_run)

    invoker = _make_invoker(worktree)
    invoker._run_bdd_oracle("TASK-001")

    assert captured["kwargs"]["python_executable"] == str(expected_python)


def test_orchestrator_passes_none_when_no_venv_and_logs_warning(
    worktree: Path, monkeypatch, caplog
):
    """No .venv/bin/python[3] → python_executable=None plus a logged warning."""
    _write_feature(worktree, "login.feature", _PASS_FEATURE)

    captured: dict = {}

    def fake_run(task_id, worktree_path, **kwargs):
        captured["kwargs"] = kwargs
        return None

    monkeypatch.setattr(bdd_runner, "run_bdd_for_task", fake_run)

    invoker = _make_invoker(worktree)
    with caplog.at_level("WARNING", logger="guardkit.orchestrator.agent_invoker"):
        invoker._run_bdd_oracle("TASK-001")

    assert captured["kwargs"]["python_executable"] is None
    assert any(
        "BDD oracle running against system pytest" in record.getMessage()
        for record in caplog.records
    )
