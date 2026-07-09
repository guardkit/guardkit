"""Attribution-aware verdict assembly (WS2 session B4).

instrument_fail / environment_fail as first-class POST-attribution verdicts;
enrich_envelope snapping onto a B3 envelope.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from guardkit.orchestrator.live_gate.disposition import (
    UndispositionedRedError,
    build_disposition_record,
    iter_reds,
    make_disposition,
)
from guardkit.orchestrator.live_gate.verdict import assemble_run_verdict, enrich_envelope
from guardkit.qa.formats.gate_registry import (
    AssertionResult,
    GateResult,
    PreflightResult,
    ResultsEnvelope,
)

_FIXED = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc).isoformat()


def _fail_gate(gate_id="g1", assertion_id="C2"):
    return GateResult(
        gate_id=gate_id,
        exit_code=1,
        assertions=[AssertionResult(id=assertion_id, status="fail")],
    )


def _record(run_id, *dispositions):
    return build_disposition_record(run_id, list(dispositions))


class TestAssembleRunVerdict:
    def test_no_reds_is_pass(self):
        assert assemble_run_verdict([], None) == "pass"

    def test_no_reds_unavailable_sweep_is_environment_fail(self):
        assert assemble_run_verdict([], None, sweep_unavailable=True) == "environment_fail"

    def test_preflight_shortcircuit_wins(self):
        # even with reds present, a pre-flight classification is authoritative
        reds = iter_reds([_fail_gate()])
        assert (
            assemble_run_verdict(reds, None, preflight_classification="instrument_fail")
            == "instrument_fail"
        )

    def test_counts_red_is_fail(self):
        reds = iter_reds([_fail_gate()])
        record = _record("r", make_disposition("g1:C2", "C2", "app", "defect_fixed"))
        assert assemble_run_verdict(reds, record) == "fail"

    def test_all_environment_is_environment_fail(self):
        reds = iter_reds([_fail_gate()])
        record = _record(
            "r", make_disposition("g1:C2", "C2", "environment", "accommodation_documented")
        )
        assert assemble_run_verdict(reds, record) == "environment_fail"

    def test_all_instrument_is_instrument_fail(self):
        reds = iter_reds([_fail_gate()])
        record = _record("r", make_disposition("g1:C2", "C2", "instrument", "instrument_fixed"))
        assert assemble_run_verdict(reds, record) == "instrument_fail"

    def test_counts_dominates_environment(self):
        gate = GateResult(
            gate_id="g1",
            exit_code=1,
            assertions=[
                AssertionResult(id="C2", status="fail"),
                AssertionResult(id="C3", status="fail"),
            ],
        )
        reds = iter_reds([gate])
        record = _record(
            "r",
            make_disposition("g1:C2", "C2", "environment", "accommodation_documented"),
            make_disposition("g1:C3", "C3", "backend", "defect_fixed"),
        )
        # a real feature defect wins outright even alongside an environment red
        assert assemble_run_verdict(reds, record) == "fail"

    def test_environment_dominates_instrument_when_mixed(self):
        gate = GateResult(
            gate_id="g1",
            exit_code=1,
            assertions=[
                AssertionResult(id="C2", status="fail"),
                AssertionResult(id="C3", status="fail"),
            ],
        )
        reds = iter_reds([gate])
        record = _record(
            "r",
            make_disposition("g1:C2", "C2", "instrument", "instrument_fixed"),
            make_disposition("g1:C3", "C3", "environment", "accommodation_documented"),
        )
        assert assemble_run_verdict(reds, record) == "environment_fail"

    def test_undispositioned_red_raises(self):
        reds = iter_reds([_fail_gate()])
        with pytest.raises(UndispositionedRedError):
            assemble_run_verdict(reds, None)


def _envelope(verdict, gates, sweep=None):
    return ResultsEnvelope(
        format_version=ResultsEnvelope.CURRENT_FORMAT_VERSION,
        run_id="FEAT-X-gb10-20260708T120000Z",
        feature_id="FEAT-X",
        target_env="gb10",
        started=_FIXED,
        finished=_FIXED,
        preflight=PreflightResult(checks=[], instrument_ok=True),
        gates=gates,
        sweep=sweep,
        verdict=verdict,
    )


class TestEnrichEnvelope:
    def test_pass_envelope_untouched(self):
        env = _envelope("pass", [GateResult(gate_id="g1", exit_code=0, assertions=[AssertionResult(id="C1", status="pass")])])
        out = enrich_envelope(env, None)
        assert out.verdict == "pass"
        assert out.dispositions_ref is None

    def test_preflight_shortcircuit_untouched(self):
        # no gates ran → nothing to re-attribute; environment_fail preserved
        env = _envelope("environment_fail", [])
        out = enrich_envelope(env, None)
        assert out.verdict == "environment_fail"
        assert out.dispositions_ref is None

    def test_fail_reattributed_to_environment(self):
        env = _envelope("fail", [_fail_gate()])
        record = _record(
            env.run_id,
            make_disposition("g1:C2", "C2", "environment", "accommodation_documented"),
        )
        out = enrich_envelope(env, record, dispositions_ref="qa/dispositions-r.yaml")
        assert out.verdict == "environment_fail"
        assert out.dispositions_ref == "qa/dispositions-r.yaml"

    def test_fail_with_unbinned_red_raises(self):
        env = _envelope("fail", [_fail_gate()])
        with pytest.raises(UndispositionedRedError):
            enrich_envelope(env, None)
