"""F8 disposition lifecycle + attribution semantics (WS2 session B4).

Covers: red enumeration, DF-017 §2.1 closure enforcement, the attribution ->
wire / counts-against-feature / routing mappings, and ST-09 revisions.
"""

from __future__ import annotations

import pytest

from guardkit.orchestrator.live_gate.disposition import (
    UndispositionedRedError,
    assert_run_closed,
    build_disposition_record,
    counts_against_feature,
    iter_reds,
    make_disposition,
    revise_attribution,
    routing_for,
    undispositioned_reds,
    wire_disposition,
)
from guardkit.qa.formats.gate_registry import AssertionResult, GateResult, SweepResult


def _gate(gate_id, *assertions):
    return GateResult(
        gate_id=gate_id,
        exit_code=0 if all(a.status == "pass" for a in assertions) else 1,
        assertions=list(assertions),
    )


class TestIterReds:
    def test_only_failed_assertions_are_reds(self):
        gate = _gate(
            "g1",
            AssertionResult(id="C1", status="pass"),
            AssertionResult(id="C2", status="fail", observed="x", expected="y"),
        )
        reds = iter_reds([gate])
        assert [r.failure_id for r in reds] == ["g1:C2"]
        assert reds[0].kind == "assertion"
        assert reds[0].observed == "x" and reds[0].expected == "y"

    def test_sweep_leaks_are_reds(self):
        reds = iter_reds([], SweepResult(surfaces_checked=2, leaks=["Paul Jones"]))
        assert reds[0].failure_id == "sweep:Paul Jones"
        assert reds[0].kind == "sweep_leak"

    def test_green_run_has_no_reds(self):
        gate = _gate("g1", AssertionResult(id="C1", status="pass"))
        assert iter_reds([gate], SweepResult(surfaces_checked=1, leaks=[])) == []


class TestClosureEnforcement:
    def test_undispositioned_red_blocks_close(self):
        gate = _gate("g1", AssertionResult(id="C2", status="fail"))
        reds = iter_reds([gate])
        with pytest.raises(UndispositionedRedError) as exc:
            assert_run_closed(reds, None)
        assert "g1:C2" in str(exc.value)

    def test_dispositioned_red_closes(self):
        gate = _gate("g1", AssertionResult(id="C2", status="fail"))
        reds = iter_reds([gate])
        record = build_disposition_record(
            "run-1",
            [make_disposition("g1:C2", "C2", "app", "defect_fixed", fix_ref="abc123")],
        )
        assert undispositioned_reds(reds, record) == []
        assert_run_closed(reds, record)  # does not raise

    def test_partial_disposition_still_blocks(self):
        gate = _gate(
            "g1",
            AssertionResult(id="C2", status="fail"),
            AssertionResult(id="C3", status="fail"),
        )
        reds = iter_reds([gate])
        record = build_disposition_record(
            "run-1", [make_disposition("g1:C2", "C2", "app", "defect_fixed")]
        )
        missing = undispositioned_reds(reds, record)
        assert [r.failure_id for r in missing] == ["g1:C3"]
        with pytest.raises(UndispositionedRedError):
            assert_run_closed(reds, record)


class TestAttributionSemantics:
    @pytest.mark.parametrize(
        "attribution,wire",
        [
            ("app", "counts"),
            ("backend", "counts"),
            ("contract_gap", "counts"),
            ("instrument", "instrument"),
            ("environment", "environment"),
        ],
    )
    def test_wire_disposition_collapse(self, attribution, wire):
        assert wire_disposition(attribution) == wire

    @pytest.mark.parametrize(
        "attribution,counts",
        [
            ("app", True),
            ("backend", True),
            ("contract_gap", True),
            ("instrument", False),
            ("environment", False),
        ],
    )
    def test_counts_against_feature(self, attribution, counts):
        assert counts_against_feature(attribution) is counts

    def test_routing_counts_is_route_and_notify(self):
        # A feature defect is routed and notified — never silently retried.
        assert routing_for("app") == "route_and_notify"
        assert routing_for("backend") == "route_and_notify"
        assert routing_for("contract_gap") == "route_and_notify"

    def test_routing_instrument_environment_is_auto_rerun(self):
        assert routing_for("instrument") == "auto_rerun"
        assert routing_for("environment") == "auto_rerun"


class TestRevisions:
    def test_revision_records_prior_and_updates_current(self):
        failure = make_disposition("f1", "deadline_spike", "backend", "accommodation_documented")
        revised = revise_attribution(
            failure,
            corrected_to="environment",
            evidence="quiet-GPU controlled rerun passed 35/35 in 3m33s",
            date="2026-07-05",
        )
        assert revised.attribution == "environment"
        assert len(revised.revisions) == 1
        rev = revised.revisions[0]
        assert rev.prior_attribution == "backend"
        assert rev.corrected_to == "environment"
        assert "quiet-GPU" in rev.evidence
        # original is untouched (frozen copy semantics)
        assert failure.attribution == "backend"
        assert failure.revisions == []
