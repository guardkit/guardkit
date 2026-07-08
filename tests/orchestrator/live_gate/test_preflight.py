"""Pre-flight: instrument / environment split + loud seams (WS2 B3)."""

from __future__ import annotations

import textwrap
from pathlib import Path

from guardkit.orchestrator.live_gate.preflight import (
    BrokerDiffProvider,
    F16ChecklistProvider,
    InstrumentSelfCheck,
    ReservationBroker,
    SeamResult,
    UnconfiguredReservationBroker,
    run_preflight,
)
from guardkit.qa.formats.gate_registry import GateEntry, GateTarget

_T = GateTarget(base_url_env="BASE", environment_id="env")

_PASS_BAR = textwrap.dedent(
    """\
    format_version: "2.0"
    task_id: T-1
    registered_at: {sha: abcd, date: "2026-07-05"}
    auth_surface_bearing: true
    preconditions: [suite_green_vs_ledger]
    criteria:
      - id: C1
        text: "shows real name"
        class: machine
        evidence_kind: screenshot
    negative_paths:
      - wrong_credential
      - anonymous_deep_link
      - post_logout_401
      - unauthorized_403_ui
      - dependency_down_degradation
    """
)

_PASS_BAR_AUTHLESS = textwrap.dedent(
    """\
    format_version: "2.0"
    task_id: T-1
    registered_at: {sha: abcd, date: "2026-07-05"}
    auth_surface_bearing: false
    preconditions: [suite_green_vs_ledger]
    criteria:
      - id: C1
        text: "renders output"
        class: machine
        evidence_kind: json
    negative_paths:
      - dependency_down_degradation
    """
)

# Auth-bearing bar missing one required auth path — invalid by F1 schema, so
# pre-flight surfaces it as an invalid-bar instrument fault.
_PASS_BAR_MISSING_AUTH_PATH = textwrap.dedent(
    """\
    format_version: "2.0"
    task_id: T-1
    registered_at: {sha: abcd, date: "2026-07-05"}
    auth_surface_bearing: true
    preconditions: [suite_green_vs_ledger]
    criteria:
      - id: C1
        text: "shows real name"
        class: machine
        evidence_kind: screenshot
    negative_paths:
      - wrong_credential
      - anonymous_deep_link
      - post_logout_401
      - dependency_down_degradation
    """
)


def _repo_with_gate(tmp_path: Path, *, pass_bar_body: str = _PASS_BAR, script: bool = True, preflight=None) -> GateEntry:
    (tmp_path / "qa" / "gates").mkdir(parents=True)
    (tmp_path / "qa" / "pass-bar-T-1.yaml").write_text(pass_bar_body)
    if script:
        (tmp_path / "qa" / "gates" / "g1.py").write_text("print('x')")
    return GateEntry(
        id="g1",
        path="qa/gates/g1.py",
        target=_T,
        preflight=preflight or [],
        pass_bar_ref="qa/pass-bar-T-1.yaml",
        evidence_dir_pattern="qa/gates/evidence-{date}/shots-g1",
    )


class TestUnconfiguredDefaults:
    def test_all_unconfigured_is_environment_fail(self, tmp_path):
        gate = _repo_with_gate(tmp_path)
        out = run_preflight(
            [gate], repo_root=tmp_path,
            reservation_resource="gb10-gpu", broker_contract_ref="qa/broker.yaml",
        )
        assert out.instrument_ok is True  # script present, negative paths declared
        assert out.environment_ok is False
        assert out.classification == "environment_fail"
        names = {c["name"] for c in out.checks}
        assert "reservation" in names and "broker-diff" in names and "f16-checklist" in names

    def test_f16_consulted_even_without_reservation_or_broker(self, tmp_path):
        gate = _repo_with_gate(tmp_path)
        out = run_preflight([gate], repo_root=tmp_path)
        # F16 is always consulted → unconfigured → environment_fail.
        assert out.classification == "environment_fail"


class TestInstrumentFaults:
    def test_missing_script_is_instrument_fail(self, tmp_path):
        gate = _repo_with_gate(tmp_path, script=False)
        out = run_preflight([gate], repo_root=tmp_path)
        assert out.instrument_ok is False
        assert out.classification == "instrument_fail"  # instrument checked before env

    def test_missing_pass_bar_is_instrument_fail(self, tmp_path):
        (tmp_path / "qa" / "gates").mkdir(parents=True)
        (tmp_path / "qa" / "gates" / "g1.py").write_text("print('x')")
        gate = GateEntry(
            id="g1", path="qa/gates/g1.py", target=_T,
            pass_bar_ref="qa/pass-bar-T-1.yaml",
            evidence_dir_pattern="qa/gates/evidence-{date}/shots-g1",
        )
        out = run_preflight([gate], repo_root=tmp_path)
        assert out.classification == "instrument_fail"


class TestNegativePathReadiness:
    def test_auth_bearing_requires_all_five(self, tmp_path):
        # A bar missing one required auth path fails F1 schema validation → the
        # pre-flight surfaces it as an invalid-bar instrument fault.
        gate = _repo_with_gate(tmp_path, pass_bar_body=_PASS_BAR_MISSING_AUTH_PATH)
        out = run_preflight([gate], repo_root=tmp_path)
        assert out.instrument_ok is False

    def test_authless_bar_only_needs_dependency_path(self, tmp_path):
        gate = _repo_with_gate(tmp_path, pass_bar_body=_PASS_BAR_AUTHLESS)
        out = run_preflight([gate], repo_root=tmp_path)
        # instrument side is fine (authless bar validly declares just the one).
        assert out.instrument_ok is True


class _GreenReservation(ReservationBroker):
    def check(self, resource):
        return SeamResult(ok=True, detail=f"{resource} reserved")


class _GreenBrokerDiff(BrokerDiffProvider):
    def diff(self, ref):
        return SeamResult(ok=True, detail="broker matches contract")


class _GreenF16(F16ChecklistProvider):
    def checklist(self):
        return [SeamResult(ok=True, detail="tokens present"), SeamResult(ok=True, detail="model warm")]


class TestGreenPath:
    def test_all_green_seams_proceed(self, tmp_path):
        gate = _repo_with_gate(tmp_path)
        out = run_preflight(
            [gate], repo_root=tmp_path,
            reservation_broker=_GreenReservation(), broker_diff=_GreenBrokerDiff(),
            f16_provider=_GreenF16(),
            reservation_resource="gb10-gpu", broker_contract_ref="qa/broker.yaml",
        )
        assert out.classification is None  # proceed to gate execution
        assert out.instrument_ok and out.environment_ok

    def test_stub_raise_is_recorded_not_propagated(self, tmp_path):
        # A stub that raises must be caught and recorded, not crash pre-flight.
        gate = _repo_with_gate(tmp_path)
        out = run_preflight(
            [gate], repo_root=tmp_path,
            reservation_broker=UnconfiguredReservationBroker(),
            reservation_resource="gb10-gpu",
        )
        res = next(c for c in out.checks if c["name"] == "reservation")
        assert res["ok"] is False
        assert "not configured" in res["detail"]


class _GreenInstrument(InstrumentSelfCheck):
    def check(self, gate_id, preflight_names):
        return [SeamResult(ok=True, detail=f"{n} ok") for n in preflight_names]


class TestInstrumentSeam:
    def test_declared_preflight_recorded_when_no_seam(self, tmp_path):
        gate = _repo_with_gate(tmp_path, preflight=["login_helper_loads"])
        out = run_preflight([gate], repo_root=tmp_path, f16_provider=_GreenF16())
        assert any(c["name"] == "g1:instrument-declared" for c in out.checks)

    def test_seam_runs_declared_checks(self, tmp_path):
        gate = _repo_with_gate(tmp_path, preflight=["login_helper_loads"])
        out = run_preflight(
            [gate], repo_root=tmp_path, instrument_check=_GreenInstrument(),
            f16_provider=_GreenF16(),
        )
        assert any(c["name"].startswith("g1:instrument[") for c in out.checks)

    def test_to_schema_projects_preflight_result(self, tmp_path):
        gate = _repo_with_gate(tmp_path)
        out = run_preflight([gate], repo_root=tmp_path)
        schema = out.to_schema()
        assert schema.instrument_ok is True
        assert isinstance(schema.checks, list)
