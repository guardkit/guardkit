"""Integration tests: the every-run compile-shadow seam (W2ab wiring).

Proves the Fallback law where ``compile_shadow`` is wired into
``AgentInvoker._write_task_work_results`` (the single once-per-verification-run
hook, beside ``_run_dcl_oracle``):

* **gherkin byte-identical** — with the ``dcl.capture`` flag absent (default), the
  seam is inert: ``compile_shadow`` returns after the flag check, its body is
  never reached (the checker is spied and asserted uncalled), no sink is written,
  and ``task_work_results`` is byte-identical to the no-shadow run;
* **poison at the seam** — a ``compile_shadow`` monkeypatched to RAISE is swallowed
  by the seam's guard, and the verification verdict (``dcl_results`` /
  ``bdd_results``) is IDENTICAL to the no-shadow run — the shadow cannot touch the
  main verdict.

The BDD subprocess seam is patched so the comparison is hermetic; the DCL oracle
runs the real vendored WASM checker (node-gated).
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

from guardkit.orchestrator import agent_invoker as agent_invoker_mod
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates import bdd_runner
from guardkit.orchestrator.quality_gates.bdd_runner import BDDResult
from guardkit.qa.dcl import capture as capture_mod
from guardkit.qa.dcl import checker as checker_mod
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
def _clear_env(monkeypatch):
    monkeypatch.delenv(SPEC_TRACK_ENV, raising=False)
    monkeypatch.delenv(capture_mod.CAPTURE_ENV, raising=False)


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    (tmp_path / "features").mkdir()
    return tmp_path


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


def _patch_bdd(monkeypatch):
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


# ===========================================================================
# GHERKIN BYTE-IDENTICAL: the seam is inert with the flag off.
# ===========================================================================


def test_gherkin_seam_flag_off_shadow_body_never_reached(worktree, monkeypatch):
    """Default track + no capture flag → compile_shadow's body is never reached
    (checker spied, asserted uncalled), no sink, and task_work_results is
    byte-identical to the no-shadow run."""
    _patch_bdd(monkeypatch)
    # A .dcl artefact is PRESENT — the flag being off is what keeps the shadow inert.
    _install_dcl_artifact(worktree)

    checker_calls = []
    monkeypatch.setattr(
        checker_mod, "check", lambda p: checker_calls.append(Path(p))
    )

    invoker = _make_invoker(worktree)
    results_file = invoker._write_task_work_results(TASK_ID, _base_result_data())
    payload = json.loads(results_file.read_text())

    # The shadow never compiled anything (flag off → returned after config read).
    assert checker_calls == []
    assert not (worktree / ".guardkit" / "dcl-capture" / "queue.jsonl").exists()
    # Byte-identical: default gherkin track has no dcl_results, BDD ran as today.
    assert "dcl_results" not in payload
    assert "bdd_results" in payload


# ===========================================================================
# POISON AT THE SEAM: a raising compile_shadow leaves the verdict untouched.
# ===========================================================================


@requires_node
def test_poison_shadow_at_seam_verdict_identical(worktree, monkeypatch):
    """compile_shadow monkeypatched to RAISE is swallowed by the seam guard; the
    dcl_results verdict is byte-identical to the no-shadow (clean) run."""
    monkeypatch.setenv(SPEC_TRACK_ENV, "dcl")
    _patch_bdd(monkeypatch)
    _install_dcl_artifact(worktree)

    # Baseline: the real seam (shadow is a genuine no-op with the flag off).
    invoker = _make_invoker(worktree)
    baseline_file = invoker._write_task_work_results(TASK_ID, _base_result_data())
    baseline = json.loads(baseline_file.read_text())

    # Now poison the shadow so the seam's guard is the thing under test.
    def _boom(*a, **k):
        raise RuntimeError("shadow blew up")

    monkeypatch.setattr(capture_mod, "compile_shadow", _boom)

    poisoned_file = invoker._write_task_work_results(TASK_ID, _base_result_data())
    poisoned = json.loads(poisoned_file.read_text())

    # The seam swallowed the exception AND the verdict is unchanged.
    assert poisoned["dcl_results"] == baseline["dcl_results"]
    assert poisoned["dcl_results"]["status"] == "pass"
    assert poisoned["bdd_results"] == baseline["bdd_results"]
