"""B3 gate: the six rescued lpa gates execute through the runner end-to-end.

Per WS2 build-plan §B3 validation: "the six rescued lpa gates execute through
the runner end-to-end against a local deploy OR record honest environment_fail
attributions". There is no local deploy in CI (the HSBC demo machine is
UNTOUCHABLE until 07-10, and lpa is machine-bound dev-mode), so the honest
outcome here is a recorded ``environment_fail`` — exactly what the spec says is
valid validation.

lpa-platform-poc is a READ-ONLY fixture source: this test COPIES the six
rescued gate scripts + the committed F4 registry exemplar into a throwaway temp
repo and runs the runner against that. It never writes to the fixture repo. If
the sibling checkout is absent, the test skips (the committed F4 registry
exemplar is still covered by test_registry.py).
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from guardkit.orchestrator.live_gate.executor import GateRun, GateScriptRunner
from guardkit.orchestrator.live_gate.preflight import (
    BrokerDiffProvider,
    F16ChecklistProvider,
    ReservationBroker,
    SeamResult,
)
from guardkit.orchestrator.live_gate.runner import LiveGateRunner
from guardkit.qa.formats import validate_instance

_FIXED = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)

_LPA_GATES = Path(__file__).resolve().parents[3].parent / "lpa-platform-poc" / "qa" / "gates"
_LPA_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "tests" / "fixtures" / "qa_formats" / "lpa-platform-poc"
)

_SIX_GATES = [
    "gate_phase1_auth.py",
    "gate_phase2_data.py",
    "gate_phase3_lpa.py",
    "gate_phase4_claim.py",
    "gate_phase5_delegated.py",
    "gate_phase6_sweep.py",
]

pytestmark = pytest.mark.skipif(
    not _LPA_GATES.is_dir(),
    reason="lpa-platform-poc sibling checkout not present (read-only fixture source)",
)


def _stage_lpa_repo(tmp_path: Path) -> Path:
    """Copy the six read-only lpa gate scripts + F4/F3/F1 exemplars into a temp
    repo laid out the way the runner expects (qa/gates/registry.yaml etc.)."""
    gates_dir = tmp_path / "qa" / "gates"
    gates_dir.mkdir(parents=True)
    for name in _SIX_GATES:
        shutil.copy(_LPA_GATES / name, gates_dir / name)
    # committed F4 exemplar → the repo's registry.yaml (its gate paths already
    # point at qa/gates/gate_phaseN_*.py — the same layout we just staged).
    shutil.copy(_LPA_FIXTURE / "gates-registry.yaml", gates_dir / "registry.yaml")
    shutil.copy(_LPA_FIXTURE / "leak-sweep.yaml", tmp_path / "qa" / "leak-sweep.yaml")
    shutil.copy(
        _LPA_FIXTURE / "pass-bar-FEAT-POC-DEMO-0705.yaml",
        tmp_path / "qa" / "pass-bar-FEAT-POC-DEMO-0705.yaml",
    )
    return tmp_path


def test_six_lpa_gates_environment_fail_when_no_deploy(tmp_path):
    """Default (unconfigured) seams → honest environment_fail, no gate run."""
    repo = _stage_lpa_repo(tmp_path)
    runner = LiveGateRunner(
        repo,
        reservation_resource="gb10-gpu",
        broker_contract_ref="qa/broker.yaml",
        now_fn=lambda: _FIXED,
    )
    env = runner.run("FEAT-POC-DEMO-0705", "lpa-poc-tailnet")

    assert env.verdict == "environment_fail"
    assert env.gates == []  # short-circuit: nothing indicts the system under test
    # the envelope validates against its own F4 schema
    hist = list((repo / "qa" / "gates" / "history").glob("*.json"))
    assert len(hist) == 1
    assert validate_instance("results-envelope", hist[0]).verdict == "environment_fail"
    # instrument side is green — all six scripts are present + the bar declares
    # its five negative paths (this is genuinely an environment problem)
    assert env.preflight.instrument_ok is True


class _GreenRes(ReservationBroker):
    def check(self, resource):
        return SeamResult(ok=True, detail="lease held")


class _GreenBroker(BrokerDiffProvider):
    def diff(self, ref):
        return SeamResult(ok=True, detail="broker matches")


class _GreenF16(F16ChecklistProvider):
    def checklist(self):
        return [SeamResult(ok=True, detail="ready")]


class _FakeConnRefusedRunner(GateScriptRunner):
    """Stands in for the real subprocess when we want to prove the runner
    drives all six gates end-to-end without depending on playwright being
    installed: each gate 'runs' and fails to reach the (absent) deploy."""

    def __init__(self):
        self.ran = []

    def run(self, script_path, *, cwd, env, timeout_s) -> GateRun:
        self.ran.append(Path(script_path).name)
        return GateRun(1, "", "playwright: net::ERR_CONNECTION_REFUSED")


def test_six_lpa_gates_drive_end_to_end_when_preflight_green(tmp_path):
    """With readiness asserted (fake-green seams) the runner drives all six
    gates through the executor end-to-end; against an absent deploy each fails
    to connect → verdict fail (the gates ran, the app wasn't there)."""
    repo = _stage_lpa_repo(tmp_path)
    fake = _FakeConnRefusedRunner()
    runner = LiveGateRunner(
        repo,
        gate_runner=fake,
        reservation_broker=_GreenRes(),
        broker_diff=_GreenBroker(),
        f16_provider=_GreenF16(),
        now_fn=lambda: _FIXED,
    )
    env = runner.run("FEAT-POC-DEMO-0705", "lpa-poc-tailnet")

    assert len(fake.ran) == 6  # all six rescued gates driven through the runner
    assert set(fake.ran) == set(_SIX_GATES)
    assert len(env.gates) == 6
    assert env.verdict == "fail"  # ran, but nothing to connect to
    assert validate_instance(
        "results-envelope",
        next((repo / "qa" / "gates" / "history").glob("*.json")),
    )
