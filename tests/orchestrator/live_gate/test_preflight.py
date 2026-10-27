"""Pre-flight: the reachability checklist decides whether gates run (WS2 B3).

Since the cull (27 October 2026) pre-flight is the reachability checklist
only; the instrument, negative-path, reservation and broker checks are gone.
"""

from __future__ import annotations

from guardkit.orchestrator.live_gate.preflight import (
    F16ChecklistProvider,
    SeamResult,
    gate_address_refusal,
    run_preflight,
)
from guardkit.qa.formats.gate_registry import GateEntry, GateTarget

_T = GateTarget(base_url_env="BASE", environment_id="env")


def _gate() -> GateEntry:
    return GateEntry(
        id="g1",
        path="qa/gates/g1.py",
        target=_T,
        pass_bar_ref="qa/pass-bar-T-1.yaml",
        evidence_dir_pattern="qa/gates/evidence-{date}/shots-g1",
    )


class _Checklist(F16ChecklistProvider):
    def __init__(self, *results: SeamResult) -> None:
        self._results = list(results)

    def checklist(self):
        return self._results


class TestRunPreflight:
    def test_green_checklist_proceeds(self):
        out = run_preflight([_gate()], f16_provider=_Checklist(SeamResult(True, "up")))
        assert out.classification is None
        assert out.checks == [
            {"name": "f16-checklist[0]", "category": "environment", "ok": True, "detail": "up"}
        ]

    def test_a_red_check_is_environment_fail(self):
        out = run_preflight(
            [_gate()],
            f16_provider=_Checklist(SeamResult(True, "up"), SeamResult(False, "down")),
        )
        assert out.classification == "environment_fail"

    def test_default_checklist_with_unset_address_is_environment_fail(self, monkeypatch):
        monkeypatch.delenv("BASE", raising=False)
        out = run_preflight([_gate()])
        assert out.classification == "environment_fail"
        assert "not set" in out.checks[0]["detail"]

    def test_to_schema_projects_preflight_result(self):
        out = run_preflight([_gate()], f16_provider=_Checklist(SeamResult(True, "up")))
        schema = out.to_schema()
        assert schema.instrument_ok is True
        assert schema.checks == out.checks


class TestGateAddressRefusal:
    def test_an_address_carrying_credentials_is_refused_by_name(self):
        refusal = gate_address_refusal("BASE", "http://user:secret@host")
        assert refusal is not None
        assert "BASE" in refusal and "secret" not in refusal

    def test_any_other_address_is_not_refused(self):
        assert gate_address_refusal("BASE", "http://127.0.0.1:8080") is None
        assert gate_address_refusal("BASE", "localhost:8080") is None
