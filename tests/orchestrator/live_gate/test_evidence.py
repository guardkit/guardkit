"""F5 evidence emitter/index + the loud read-the-image seam (WS2 B3)."""

from __future__ import annotations


import pytest
import yaml

from guardkit.orchestrator.live_gate.errors import LiveGateStubError
from guardkit.orchestrator.live_gate.evidence import (
    EvidenceCollector,
    UnconfiguredImageVerifier,
    ensure_evidence_dir,
)
from guardkit.qa.formats import validate_instance
from guardkit.qa.formats.gate_registry import AssertionResult, GateResult


class TestEnsureEvidenceDir:
    def test_creates_dir(self, tmp_path):
        d = ensure_evidence_dir(tmp_path / "qa" / "gates" / "evidence", "run-1")
        assert d.is_dir()
        assert d.name == "run-1"


class TestCollector:
    def test_harvest_assertions_with_evidence_ref(self):
        gr = GateResult(
            gate_id="g1",
            exit_code=0,
            assertions=[
                AssertionResult(id="a1", status="pass", evidence_ref="shots-g1/a1.png", observed="o", expected="e"),
                AssertionResult(id="a2", status="pass"),  # no evidence_ref → skipped
            ],
        )
        c = EvidenceCollector()
        c.add_from_gate_results([gr])
        assert len(c) == 1
        assert c.entries[0].artifact == "shots-g1/a1.png"
        assert c.entries[0].checkpoint_or_assertion_id == "a1"
        assert c.entries[0].inspected_by is None  # v1: not inspected

    def test_write_index_none_when_empty(self, tmp_path):
        assert EvidenceCollector().write_index(tmp_path) is None

    def test_write_index_valid_f5(self, tmp_path):
        c = EvidenceCollector()
        c.add("shots-g1/a1.png", "a1", "gate g1 assertion a1")
        out = c.write_index(tmp_path)
        assert out is not None and out.name == "EVIDENCE.yaml"
        # the written file validates as an F5 evidence-index.
        idx = validate_instance("evidence-index", out)
        assert idx.entries[0].artifact == "shots-g1/a1.png"
        # and round-trips as yaml
        data = yaml.safe_load(out.read_text())
        assert data["format_version"] == "1.0"


class TestImageVerifierSeam:
    def test_unconfigured_raises(self, tmp_path):
        with pytest.raises(LiveGateStubError, match="ImageVerifier is not configured"):
            UnconfiguredImageVerifier().inspect(tmp_path / "x.png", "should show real name")
