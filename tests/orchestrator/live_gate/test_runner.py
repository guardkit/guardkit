"""Runner orchestration + verdict derivation + envelope emission (WS2 B3)."""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from guardkit.orchestrator.live_gate.executor import GateRun, GateScriptRunner
from guardkit.orchestrator.live_gate.preflight import (
    BrokerDiffProvider,
    F16ChecklistProvider,
    ReservationBroker,
    SeamResult,
)
from guardkit.orchestrator.live_gate.runner import LiveGateRunner, derive_verdict
from guardkit.orchestrator.live_gate.sweep import PageTextFetcher
from guardkit.qa.formats import validate_instance
from guardkit.qa.formats.gate_registry import AssertionResult, GateResult, SweepResult

_FIXED = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# derive_verdict (pure)
# ---------------------------------------------------------------------------


class TestDeriveVerdict:
    def _pass_gate(self):
        return GateResult(gate_id="g", exit_code=0, assertions=[AssertionResult(id="a", status="pass")])

    def _fail_gate(self):
        return GateResult(gate_id="g", exit_code=1, assertions=[AssertionResult(id="a", status="fail")])

    def test_preflight_shortcircuit_wins(self):
        assert derive_verdict("environment_fail", [self._pass_gate()], None) == "environment_fail"
        assert derive_verdict("instrument_fail", [], None) == "instrument_fail"

    def test_all_pass_is_pass(self):
        assert derive_verdict(None, [self._pass_gate()], SweepResult(surfaces_checked=2, leaks=[])) == "pass"

    def test_failed_gate_is_fail(self):
        assert derive_verdict(None, [self._pass_gate(), self._fail_gate()], None) == "fail"

    def test_sweep_leak_is_fail(self):
        assert derive_verdict(None, [self._pass_gate()], SweepResult(surfaces_checked=1, leaks=["x"])) == "fail"

    def test_sweep_unavailable_is_environment_fail(self):
        assert derive_verdict(None, [self._pass_gate()], None, sweep_unavailable=True) == "environment_fail"


# ---------------------------------------------------------------------------
# Fakes (signature-binding)
# ---------------------------------------------------------------------------


class _CannedRunner(GateScriptRunner):
    def __init__(self, by_suffix):
        self._by_suffix = by_suffix

    def run(self, script_path, *, cwd, env, timeout_s) -> GateRun:
        for suffix, result in self._by_suffix.items():
            if str(script_path).endswith(suffix):
                return result
        return GateRun(0, json.dumps({"assertions": [{"id": "a", "status": "pass"}]}), "")


class _GreenRes(ReservationBroker):
    def check(self, resource):
        return SeamResult(ok=True, detail="ok")


class _GreenBroker(BrokerDiffProvider):
    def diff(self, ref):
        return SeamResult(ok=True, detail="ok")


class _GreenF16(F16ChecklistProvider):
    def checklist(self):
        return [SeamResult(ok=True, detail="ok")]


class _FetcherClean(PageTextFetcher):
    def fetch(self, persona, surface):
        return "Donald Donor real data"


_PASS_BAR = textwrap.dedent(
    """\
    format_version: "2.0"
    task_id: T-1
    registered_at: {sha: abcd, date: "2026-07-05"}
    auth_surface_bearing: true
    preconditions: [suite_green_vs_ledger]
    criteria:
      - {id: C1, text: "shows real name", class: machine, evidence_kind: screenshot}
    negative_paths: [wrong_credential, anonymous_deep_link, post_logout_401, unauthorized_403_ui, dependency_down_degradation]
    """
)


def _build_repo(tmp_path: Path, *, with_sweep_gate: bool = False, gate_stdout: str | None = None) -> Path:
    (tmp_path / "qa" / "gates").mkdir(parents=True)
    (tmp_path / "qa" / "pass-bar-T-1.yaml").write_text(_PASS_BAR)
    (tmp_path / "qa" / "gates" / "g1.py").write_text("print('x')")
    gates = [
        {
            "id": "g1",
            "path": "qa/gates/g1.py",
            "target": {"base_url_env": "BASE", "environment_id": "env"},
            "pass_bar_ref": "qa/pass-bar-T-1.yaml",
            "evidence_dir_pattern": "qa/gates/evidence-{date}/shots-g1",
        }
    ]
    if with_sweep_gate:
        (tmp_path / "qa" / "gates" / "g6.py").write_text("print('x')")
        (tmp_path / "qa" / "leak-sweep.yaml").write_text(
            textwrap.dedent(
                """\
                format_version: "1.0"
                personas: [{id: donor, login_role: donor, credentials_ref: R}]
                deny: {identity_strings: ["Paul Jones"]}
                surfaces: [{route: /insights, claimed_by: F, scope: full_page}]
                """
            )
        )
        gates.append(
            {
                "id": "g6",
                "path": "qa/gates/g6.py",
                "target": {"base_url_env": "BASE", "environment_id": "env"},
                "leak_sweep_manifest_ref": "qa/leak-sweep.yaml",
                "pass_bar_ref": "qa/pass-bar-T-1.yaml",
                "evidence_dir_pattern": "qa/gates/evidence-{date}/shots-g6",
            }
        )
    registry = {"format_version": "1.0", "gates": gates}
    import yaml

    (tmp_path / "qa" / "gates" / "registry.yaml").write_text(yaml.safe_dump(registry))
    return tmp_path


class TestRunnerEnvironmentFail:
    def test_unconfigured_seams_short_circuit_environment_fail(self, tmp_path):
        repo = _build_repo(tmp_path)
        runner = LiveGateRunner(
            repo, reservation_resource="gb10-gpu", now_fn=lambda: _FIXED,
        )
        env = runner.run("FEAT-X", "gb10")
        assert env.verdict == "environment_fail"
        assert env.gates == []  # no gate ran on the short-circuit
        # envelope written to history and validates against its own schema
        hist = repo / "qa" / "gates" / "history"
        written = list(hist.glob("*.json"))
        assert len(written) == 1
        validated = validate_instance("results-envelope", written[0])
        assert validated.verdict == "environment_fail"
        # evidence dir created automatically (empty → no index ref)
        assert (repo / "qa" / "gates" / "evidence" / env.run_id).is_dir()
        assert env.evidence_index_ref is None


class TestRunnerPass:
    def test_green_preflight_and_gates_pass(self, tmp_path):
        repo = _build_repo(tmp_path)
        runner = LiveGateRunner(
            repo,
            gate_runner=_CannedRunner({"g1.py": GateRun(0, json.dumps(
                {"assertions": [{"id": "C1", "status": "pass", "evidence_ref": "shots-g1/c1.png"}]}
            ), "")}),
            reservation_broker=_GreenRes(), broker_diff=_GreenBroker(), f16_provider=_GreenF16(),
            reservation_resource="gb10-gpu", broker_contract_ref="qa/broker.yaml",
            now_fn=lambda: _FIXED,
        )
        env = runner.run("FEAT-X", "gb10")
        assert env.verdict == "pass"
        assert len(env.gates) == 1
        # evidence index written from the assertion's evidence_ref
        assert env.evidence_index_ref is not None
        idx_path = repo / env.evidence_index_ref
        assert validate_instance("evidence-index", idx_path)

    def test_failed_gate_yields_fail(self, tmp_path):
        repo = _build_repo(tmp_path)
        runner = LiveGateRunner(
            repo,
            gate_runner=_CannedRunner({"g1.py": GateRun(1, "GATE FAILED", "boom")}),
            reservation_broker=_GreenRes(), broker_diff=_GreenBroker(), f16_provider=_GreenF16(),
            reservation_resource="gb10-gpu",
            now_fn=lambda: _FIXED,
        )
        env = runner.run("FEAT-X", "gb10")
        assert env.verdict == "fail"


class TestRunnerSweep:
    def test_surface_gate_clean_sweep_passes(self, tmp_path):
        repo = _build_repo(tmp_path, with_sweep_gate=True)
        runner = LiveGateRunner(
            repo,
            gate_runner=_CannedRunner({}),
            page_text_fetcher=_FetcherClean(),
            reservation_broker=_GreenRes(), broker_diff=_GreenBroker(), f16_provider=_GreenF16(),
            now_fn=lambda: _FIXED,
        )
        env = runner.run("FEAT-X", "gb10")
        assert env.sweep is not None
        assert env.sweep.leaks == []
        assert env.verdict == "pass"

    def test_surface_gate_without_fetcher_is_environment_fail(self, tmp_path):
        repo = _build_repo(tmp_path, with_sweep_gate=True)
        runner = LiveGateRunner(
            repo,
            gate_runner=_CannedRunner({}),
            # no page_text_fetcher → sweep un-runnable
            reservation_broker=_GreenRes(), broker_diff=_GreenBroker(), f16_provider=_GreenF16(),
            now_fn=lambda: _FIXED,
        )
        env = runner.run("FEAT-X", "gb10")
        assert env.verdict == "environment_fail"
