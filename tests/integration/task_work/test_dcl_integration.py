"""Integration tests: the DCL oracle wiring in the task-work results writer.

Phase D (design §1 / D1). Proves:

* **byte-no-op** — with the switch absent (default gherkin track), the DCL path
  is dead: no ``dcl_results`` key, and the BDD oracle still runs, unconditioned;
* dcl track + no ``.dcl`` artefact → ``dcl_results`` absent (absence discipline),
  chain proceeds;
* dcl track + a ``@task``-tagged ``.dcl`` → ``dcl_results`` populated (status
  ``pass``) from the real vendored checker.

The BDD subprocess seam is patched so the byte-no-op comparison is hermetic; the
DCL oracle runs the real WASM checker (node-gated).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates import bdd_runner
from guardkit.orchestrator.quality_gates.bdd_runner import BDDResult
from guardkit.qa.spec_track import SPEC_TRACK_ENV

_FIXTURES = _REPO_ROOT / "tests" / "fixtures" / "dcl"

requires_node = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the vendored WASM DCL checker",
)

TASK_ID = "TASK-STAT-001"

_PASS_FEATURE = """\
Feature: Stats

  @task:TASK-STAT-001
  Scenario: Stats are reported
    Given a running service
    When the operator asks for stats
    Then the stats are returned
"""


def _base_result_data() -> dict:
    return {
        "tests_passed": 5,
        "tests_failed": 0,
        "coverage": 90.0,
        "quality_gates_passed": True,
        "files_modified": [],
        "files_created": [],
        "phases": {},
    }


def _make_invoker(worktree: Path) -> AgentInvoker:
    return AgentInvoker(
        worktree_path=worktree, max_turns_per_agent=5, sdk_timeout_seconds=60
    )


@pytest.fixture(autouse=True)
def _clear_track_env(monkeypatch):
    monkeypatch.delenv(SPEC_TRACK_ENV, raising=False)


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    (tmp_path / "features").mkdir()
    return tmp_path


def _write_feature(worktree: Path, name: str, body: str) -> Path:
    fp = worktree / "features" / name
    fp.write_text(body, encoding="utf-8")
    return fp


def _install_dcl_artifact(worktree: Path, dcl_name: str = "capability.dcl") -> None:
    feat = worktree / "features" / "stats-endpoint"
    feat.mkdir(parents=True, exist_ok=True)
    body = (_FIXTURES / dcl_name).read_text(encoding="utf-8")
    (feat / "stats-endpoint.dcl").write_text(
        f"// @task:{TASK_ID}\n{body}", encoding="utf-8"
    )
    bind = worktree / "qa" / "dcl"
    bind.mkdir(parents=True, exist_ok=True)
    shutil.copy(_FIXTURES / "binding.yaml", bind / "binding.yaml")


# --- byte-no-op: default gherkin track --------------------------------------


def test_gherkin_track_no_dcl_results_and_bdd_untouched(worktree, monkeypatch):
    """Switch absent → NO dcl_results key, and the BDD oracle still ran.

    This is the byte-no-op proof: on the default track the DCL diff is dead and
    task_work_results is produced exactly as before — the BDD oracle is invoked,
    unconditioned, and its key is the only oracle key present.
    """
    _write_feature(worktree, "stats.feature", _PASS_FEATURE)
    # A .dcl artefact is even PRESENT — but the default track must ignore it.
    _install_dcl_artifact(worktree)

    bdd_called = {"n": 0}

    def fake_run(task_id, worktree_path, **kwargs):
        bdd_called["n"] += 1
        assert task_id == TASK_ID
        return BDDResult(
            scenarios_passed=1,
            scenarios_failed=0,
            scenarios_pending=0,
            failures=[],
            pending=[],
            feature_files=["features/stats.feature"],
            tag=f"@task:{TASK_ID}",
        )

    monkeypatch.setattr(bdd_runner, "run_bdd_for_task", fake_run)

    invoker = _make_invoker(worktree)
    results_file = invoker._write_task_work_results(TASK_ID, _base_result_data())
    payload = json.loads(results_file.read_text())

    # BDD path ran, unconditioned, exactly as today.
    assert bdd_called["n"] == 1
    assert "bdd_results" in payload
    assert payload["bdd_results"]["scenarios_passed"] == 1
    # DCL path is dead on the default track.
    assert "dcl_results" not in payload


# --- dcl track, no artefact --------------------------------------------------


def test_dcl_track_no_artifact_absent_key_chain_proceeds(worktree, monkeypatch):
    """dcl track but no @task-tagged .dcl → dcl_results absent; BDD still runs."""
    monkeypatch.setenv(SPEC_TRACK_ENV, "dcl")
    _write_feature(worktree, "stats.feature", _PASS_FEATURE)

    def fake_run(task_id, worktree_path, **kwargs):
        return BDDResult(
            scenarios_passed=1,
            scenarios_failed=0,
            scenarios_pending=0,
            failures=[],
            pending=[],
            feature_files=["features/stats.feature"],
            tag=f"@task:{TASK_ID}",
        )

    monkeypatch.setattr(bdd_runner, "run_bdd_for_task", fake_run)

    invoker = _make_invoker(worktree)
    results_file = invoker._write_task_work_results(TASK_ID, _base_result_data())
    payload = json.loads(results_file.read_text())

    assert "dcl_results" not in payload  # absence discipline
    assert "bdd_results" in payload  # chain proceeds untouched


# --- dcl track, real artefact ------------------------------------------------


@requires_node
def test_dcl_track_with_artifact_populates_dcl_results(worktree, monkeypatch):
    monkeypatch.setenv(SPEC_TRACK_ENV, "dcl")
    _install_dcl_artifact(worktree)

    invoker = _make_invoker(worktree)
    results_file = invoker._write_task_work_results(TASK_ID, _base_result_data())
    payload = json.loads(results_file.read_text())

    assert "dcl_results" in payload
    dcl = payload["dcl_results"]
    assert dcl["status"] == "pass"
    assert dcl["compile_ok"] is True
    assert dcl["run_ids"]
    assert dcl["task_id"] == TASK_ID


@requires_node
def test_dcl_track_broken_artifact_reports_compile_error(worktree, monkeypatch):
    monkeypatch.setenv(SPEC_TRACK_ENV, "dcl")
    _install_dcl_artifact(worktree, dcl_name="broken.dcl")

    invoker = _make_invoker(worktree)
    results_file = invoker._write_task_work_results(TASK_ID, _base_result_data())
    payload = json.loads(results_file.read_text())

    assert "dcl_results" in payload
    assert payload["dcl_results"]["status"] == "compile_error"
    assert payload["dcl_results"]["errors"]
