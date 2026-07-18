"""Hermetic tests for the H-A Stage 1 MACHINE-VERIFY stage.

Spec: ``docs/ways-of-working/retire-the-coordinator-build-handoff-2026-07-17.md``
§3 Stage 1. The coach-gate three (modelled on the DD4F replay pattern):

* (a) a fixture build whose reds are IDENTICAL on base ⇒ zero charged failures
      ⇒ CLEAN;
* (b) a fixture build introducing ONE NEW red ⇒ non-empty charged failures ⇒
      CATCH naming the charged node IDs;
* (c) a fixture diff carrying a ``.guardkit/autobuild/**`` fossil ⇒ the junk
      tripwire fires (CATCH).

Everything is hermetic: temp-dir fixture worktrees + real ``git`` for the
committed-diff sweep, no network, no seats, no service.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.baseline import BaselineResult
from guardkit.orchestrator.machine_verify import (
    JUNK_HELD,
    JUNK_TRIPPED,
    LIVE_ENVIRONMENT_FAIL,
    LIVE_PASS,
    LIVE_PRODUCT_FAIL,
    LIVE_SKIPPED,
    SIGNAL_CATCH,
    SIGNAL_CLEAN,
    MachineVerifyReport,
    assemble_report,
    charged_failures_at_merge,
    committed_diff_paths,
    drive_registered_gates,
    run_machine_verify,
    sweep_committed_junk,
)


# ---------------------------------------------------------------------------
# git fixture repo
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """A tiny git repo on ``main`` with one committed file (the feature base)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    # A .gitignore that blocks the build-state fossils but keeps features/qa —
    # mirrors the api_test 96FC pin.
    (repo / ".gitignore").write_text(
        ".guardkit/worktrees/\n.guardkit/autobuild/\n", encoding="utf-8"
    )
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _feature_base(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD")


# ---------------------------------------------------------------------------
# (a) reds identical on base ⇒ CLEAN
# ---------------------------------------------------------------------------


class TestCleanOnIdenticalReds:
    def test_identical_reds_zero_charged_clean(self, fixture_repo: Path):
        base = _feature_base(fixture_repo)
        # A normal source change committed on the branch (no junk).
        (fixture_repo / "app.py").write_text("x = 2\n", encoding="utf-8")
        _git(fixture_repo, "commit", "-aqm", "feature change")

        baseline = BaselineResult(
            command="pytest",
            expected_exit=0,
            passed=False,
            exit_code=1,
            failing_node_ids=["tests/a.py::test_x", "tests/b.py::test_y"],
            failing_count=2,
        )
        # Observed reds are EXACTLY the baseline reds — pre-existing, not this
        # branch's fault.
        report = run_machine_verify(
            fixture_repo,
            observed_node_ids=["tests/a.py::test_x", "tests/b.py::test_y"],
            baseline_result=baseline,
            feature_base=base,
        )
        assert report.signal == SIGNAL_CLEAN
        assert report.charged_failures == []
        assert report.junk_verdict == JUNK_HELD
        assert report.disposition_required is False
        # No service up in a hermetic run and no registry ⇒ skipped, never a
        # branch fail.
        assert report.live_verdict == LIVE_SKIPPED


# ---------------------------------------------------------------------------
# (b) one new red ⇒ CATCH naming the charged node ids
# ---------------------------------------------------------------------------


class TestCatchOnNewRed:
    def test_new_red_is_charged_and_caught(self, fixture_repo: Path):
        base = _feature_base(fixture_repo)
        (fixture_repo / "app.py").write_text("x = 3\n", encoding="utf-8")
        _git(fixture_repo, "commit", "-aqm", "feature change")

        baseline = BaselineResult(
            command="pytest",
            expected_exit=0,
            passed=False,
            exit_code=1,
            failing_node_ids=["tests/a.py::test_x"],
            failing_count=1,
        )
        # The branch introduced tests/new.py::test_regress on top of the
        # pre-existing tests/a.py::test_x.
        report = run_machine_verify(
            fixture_repo,
            observed_node_ids=["tests/a.py::test_x", "tests/new.py::test_regress"],
            baseline_result=baseline,
            feature_base=base,
        )
        assert report.signal == SIGNAL_CATCH
        assert report.charged_failures == ["tests/new.py::test_regress"]
        assert report.junk_verdict == JUNK_HELD
        assert report.disposition_required is True
        # The receipt names the charged node id.
        receipt = "\n".join(report.receipt_lines())
        assert "tests/new.py::test_regress" in receipt
        assert "CATCH" in receipt


# ---------------------------------------------------------------------------
# (c) committed .guardkit/autobuild fossil ⇒ junk tripwire fires
# ---------------------------------------------------------------------------


class TestJunkTripwire:
    def test_committed_autobuild_fossil_trips_wire(self, fixture_repo: Path):
        base = _feature_base(fixture_repo)
        # A build-state fossil force-committed onto the branch (rode in via a
        # selective merge). ``-f`` because .gitignore blocks the path.
        fossil_dir = fixture_repo / ".guardkit" / "autobuild" / "FEAT-X"
        fossil_dir.mkdir(parents=True)
        (fossil_dir / "state.json").write_text("{}", encoding="utf-8")
        (fixture_repo / "app.py").write_text("x = 4\n", encoding="utf-8")
        _git(fixture_repo, "add", "app.py")
        _git(fixture_repo, "add", "-f", ".guardkit/autobuild/FEAT-X/state.json")
        _git(fixture_repo, "commit", "-qm", "feature + fossil")

        baseline = BaselineResult(
            command="pytest", expected_exit=0, passed=True, exit_code=0,
        )
        report = run_machine_verify(
            fixture_repo,
            observed_node_ids=[],  # suite green
            baseline_result=baseline,
            feature_base=base,
        )
        assert report.junk_verdict == JUNK_TRIPPED
        assert ".guardkit/autobuild/FEAT-X/state.json" in report.junk_paths
        # Junk alone (no charged reds) is still a CATCH — it is exactly what the
        # coordinator removed by hand.
        assert report.signal == SIGNAL_CATCH
        assert report.disposition_required is True

    def test_kept_prefixes_do_not_trip(self, fixture_repo: Path):
        base = _feature_base(fixture_repo)
        # Feature specs + qa are tracked on purpose — must NOT trip.
        feat = fixture_repo / ".guardkit" / "features"
        feat.mkdir(parents=True)
        (feat / "spec.md").write_text("# spec\n", encoding="utf-8")
        qa = fixture_repo / "qa"
        qa.mkdir()
        (qa / "known-failures.yaml").write_text("known_failures: []\n", encoding="utf-8")
        _git(fixture_repo, "add", "-A")
        _git(fixture_repo, "commit", "-qm", "feature spec + qa")

        verdict, junk = sweep_committed_junk(
            fixture_repo, committed_diff_paths(fixture_repo, base)
        )
        assert verdict == JUNK_HELD
        assert junk == []


# ---------------------------------------------------------------------------
# committed_diff_paths — deterministic, committed-only
# ---------------------------------------------------------------------------


class TestCommittedDiffPaths:
    def test_lists_committed_changes_sorted(self, fixture_repo: Path):
        base = _feature_base(fixture_repo)
        (fixture_repo / "zeta.py").write_text("z = 1\n", encoding="utf-8")
        (fixture_repo / "alpha.py").write_text("a = 1\n", encoding="utf-8")
        _git(fixture_repo, "add", "-A")
        _git(fixture_repo, "commit", "-qm", "two files")
        paths = committed_diff_paths(fixture_repo, base)
        assert paths == ["alpha.py", "zeta.py"]  # sorted, deterministic

    def test_uncommitted_working_tree_change_is_ignored(self, fixture_repo: Path):
        base = _feature_base(fixture_repo)
        # Working-tree-only change (never committed) must not appear.
        (fixture_repo / "app.py").write_text("x = 99\n", encoding="utf-8")
        assert committed_diff_paths(fixture_repo, base) == []

    def test_no_feature_base_fails_open(self, fixture_repo: Path):
        assert committed_diff_paths(fixture_repo, None) == []


# ---------------------------------------------------------------------------
# charged_failures_at_merge — the lifted computation
# ---------------------------------------------------------------------------


class TestChargedFailuresAtMerge:
    def test_none_baseline_charges_all_observed(self):
        charged = charged_failures_at_merge(
            observed_node_ids=["tests/a.py::t1", "tests/b.py::t2"],
            baseline_result=None,
        )
        assert charged == ["tests/a.py::t1", "tests/b.py::t2"]

    def test_ledger_excuses_a_failure(self):
        baseline = BaselineResult(
            command="pytest", expected_exit=0, passed=False, exit_code=1,
            failing_node_ids=["tests/a.py::t1"],
        )
        charged = charged_failures_at_merge(
            observed_node_ids=["tests/a.py::t1", "tests/b.py::t2"],
            baseline_result=baseline,
            ledger_ids={"tests/b.py::t2"},
        )
        assert charged == []

    def test_authored_file_recharges_excused_red(self):
        baseline = BaselineResult(
            command="pytest", expected_exit=0, passed=False, exit_code=1,
            failing_node_ids=["tests/a.py::t1"],
        )
        # The task authored tests/a.py → it cannot hide behind the baseline.
        charged = charged_failures_at_merge(
            observed_node_ids=["tests/a.py::t1"],
            baseline_result=baseline,
            authored_test_files=["tests/a.py"],
        )
        assert charged == ["tests/a.py::t1"]


# ---------------------------------------------------------------------------
# A5 live drive — env fail never fails the branch
# ---------------------------------------------------------------------------


class _FakeRunner:
    """Signature-binding fake gate runner (LPA-13) — no subprocess."""

    def __init__(self, exit_code: int = 0):
        self._exit_code = exit_code

    def run(self, script_path, *, cwd, env, timeout_s):
        from guardkit.orchestrator.live_gate.executor import GateRun

        return GateRun(exit_code=self._exit_code, stdout="", stderr="")


def _write_registry(repo: Path, gate_script: str = "gate.py") -> None:
    gates_dir = repo / "qa" / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    (gates_dir / gate_script).write_text("print('ok')\n", encoding="utf-8")
    (gates_dir / "registry.yaml").write_text(
        'format_version: "1.0"\n'
        "gates:\n"
        f"  - id: version\n"
        f"    path: qa/gates/{gate_script}\n"
        f"    target:\n"
        f"      base_url_env: QA_BASE_URL\n"
        f"      environment_id: local-dev\n"
        f"    pass_bar_ref: qa/pass-bar.yaml\n"
        f"    evidence_dir_pattern: qa/gates/evidence-{{date}}/shots-version\n",
        encoding="utf-8",
    )


class TestLiveDrive:
    def test_no_registry_is_skipped(self, tmp_path: Path):
        verdict, detail = drive_registered_gates(tmp_path)
        assert verdict == LIVE_SKIPPED

    def test_registry_but_no_service_is_environment_fail(self, tmp_path: Path):
        _write_registry(tmp_path)
        verdict, detail = drive_registered_gates(tmp_path, service_ready=False)
        assert verdict == LIVE_ENVIRONMENT_FAIL
        assert "version" in detail  # names the gate that would run

    def test_ready_service_all_green_is_pass(self, tmp_path: Path):
        _write_registry(tmp_path)
        verdict, detail = drive_registered_gates(
            tmp_path, service_ready=True, runner=_FakeRunner(exit_code=0)
        )
        assert verdict == LIVE_PASS

    def test_ready_service_gate_failure_is_product_fail(self, tmp_path: Path):
        _write_registry(tmp_path)
        verdict, detail = drive_registered_gates(
            tmp_path, service_ready=True, runner=_FakeRunner(exit_code=1)
        )
        assert verdict == LIVE_PRODUCT_FAIL

    def test_env_fail_never_flips_the_signal(self, tmp_path: Path):
        # A clean build with an environment_fail live drive is still CLEAN.
        report = assemble_report(
            charged_failures=[],
            junk_verdict=JUNK_HELD,
            junk_paths=[],
            live_verdict=LIVE_ENVIRONMENT_FAIL,
        )
        assert report.signal == SIGNAL_CLEAN
        assert report.disposition_required is False


# ---------------------------------------------------------------------------
# observed-reds-unavailable ⇒ forced disposition (fail toward attention)
# ---------------------------------------------------------------------------


class TestObservedUnavailable:
    def test_none_observed_forces_disposition(self, fixture_repo: Path):
        base = _feature_base(fixture_repo)
        report = run_machine_verify(
            fixture_repo,
            observed_node_ids=None,  # suite could not be re-run
            baseline_result=None,
            feature_base=base,
        )
        # Cannot prove clean-on-base ⇒ signal stays clean but disposition is
        # forced (the honest fail-toward-attention direction).
        assert report.observed_available is False
        assert report.disposition_required is True
        receipt = "\n".join(report.receipt_lines())
        assert "UNAVAILABLE" in receipt


# ---------------------------------------------------------------------------
# report serialisation
# ---------------------------------------------------------------------------


class TestReportSerialisation:
    def test_to_dict_round_trips_verdicts(self):
        report = MachineVerifyReport(
            signal=SIGNAL_CATCH,
            charged_failures=["tests/x.py::t"],
            junk_verdict=JUNK_TRIPPED,
            junk_paths=[".guardkit/autobuild/f/x"],
            live_verdict=LIVE_ENVIRONMENT_FAIL,
            feature_base="deadbeef",
        )
        d = report.to_dict()
        assert d["signal"] == SIGNAL_CATCH
        assert d["charged_failures"] == ["tests/x.py::t"]
        assert d["junk_verdict"] == JUNK_TRIPPED
        assert d["disposition_required"] is True
