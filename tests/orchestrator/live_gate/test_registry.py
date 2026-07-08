"""F4 registry load + selection with risk ordering (WS2 B3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.orchestrator.live_gate.errors import LiveGateError
from guardkit.orchestrator.live_gate.registry import (
    load_registry,
    registry_path_for,
    select_gates,
)
from guardkit.qa.formats import QAFormatError
from guardkit.qa.formats.gate_registry import GateEntry, GateRegistry, GateTarget, LastGreen

_T = GateTarget(base_url_env="BASE", environment_id="env")


def _gate(gid, green=True) -> GateEntry:
    return GateEntry(
        id=gid,
        path=f"qa/gates/{gid}.py",
        target=_T,
        pass_bar_ref="qa/pass-bar-X.yaml",
        evidence_dir_pattern=f"qa/gates/evidence-{{date}}/shots-{gid}",
        last_green=LastGreen(date="2026-07-05", sha="abcd") if green else None,
    )


def _registry(*gates) -> GateRegistry:
    return GateRegistry(format_version="1.0", gates=list(gates))


class TestSelectGates:
    def test_default_selects_all_never_exercised_first(self):
        reg = _registry(_gate("g1", green=True), _gate("g2", green=False), _gate("g3", green=True))
        sel = select_gates(reg)
        # g2 (never-green) first, then registry order.
        assert [g.id for g in sel] == ["g2", "g1", "g3"]

    def test_requested_subset_filters(self):
        reg = _registry(_gate("g1"), _gate("g2"), _gate("g3"))
        sel = select_gates(reg, ["g3", "g1"])
        assert {g.id for g in sel} == {"g3", "g1"}
        assert len(sel) == 2

    def test_unknown_requested_id_raises(self):
        reg = _registry(_gate("g1"))
        with pytest.raises(LiveGateError, match="unknown gate id"):
            select_gates(reg, ["nope"])

    def test_stable_order_when_all_green(self):
        reg = _registry(_gate("g1"), _gate("g2"))
        assert [g.id for g in select_gates(reg)] == ["g1", "g2"]


class TestLoadRegistry:
    def test_load_lpa_exemplar(self):
        # The committed lpa F4 exemplar (renamed to registry.yaml on disk in a
        # target repo) loads and carries the six rescued gates.
        path = Path("tests/fixtures/qa_formats/lpa-platform-poc/gates-registry.yaml")
        reg = load_registry(path)
        assert len(reg.gates) == 6
        assert any(g.leak_sweep_manifest_ref for g in reg.gates)  # the sweep gate

    def test_missing_registry_raises_loudly(self, tmp_path):
        with pytest.raises(QAFormatError):
            load_registry(tmp_path / "nope.yaml")

    def test_registry_path_for(self, tmp_path):
        assert registry_path_for(tmp_path) == tmp_path / "qa" / "gates" / "registry.yaml"
