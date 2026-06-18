"""Cross-repo contract seam test for the guardkit↔guardkitfactory wiring gate.

TASK-AB-WIREGATE01. CI enforcement for the migrated-contract-boundary meta-rule
(``.claude/rules/namespace-hygiene.md`` /
``.claude/rules/evidence-boundary-narrower-than-write-surface.md`` /
``.claude/rules/harness-cancellation-contract.md``): the post-wave wiring gate
in guardkit (``FeatureOrchestrator._run_post_wave_wiring_gate``) depends on the
``guardkitfactory.wiring.analyze_wiring`` result carrying a ``ctor_arity`` key
(and on ``mocked_seam[*].authored_this_turn`` for the seam half). If a
guardkitfactory version skew drops the ctor-arity contract, that dependency must
fail **here, in seconds, in CI** — not silently degrade to absent-signal on a
live autobuild run (the false-green this whole task exists to close).

Unlike the mocked unit tests in ``tests/unit/orchestrator/test_wiring_gate.py``,
this module exercises the **real installed** ``guardkitfactory.wiring`` end to
end over a FEAT-POC-006-shaped worktree.

* ``pytest.importorskip`` makes the module skip cleanly in a dev venv without
  the ``[autobuild]`` extra (no guardkitfactory) — opt-in for the seam CI job.
* Fast: one ``analyze_wiring`` call over a tiny tmp worktree. No LLM, no GB10.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.seam]

wiring = pytest.importorskip("guardkitfactory.wiring")

from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator


_SERVICE = (
    "class VoiceService:\n"
    "    def __init__(self, transport, config):\n"
    "        self.transport = transport\n"
)


def _write(root: Path, rel: str, content: str) -> str:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return rel


class TestWiringResultContract:
    """The result-dict shape guardkit's gate consumes must be present."""

    def test_analyze_wiring_returns_ctor_arity_key(self, tmp_path):
        svc = _write(tmp_path, "src/svc.py", _SERVICE)
        result = wiring.analyze_wiring([svc], tmp_path, "feature")
        assert result is not None
        # The contract guardkit's gate reads. Missing key = version skew.
        assert "ctor_arity" in result, (
            "guardkitfactory.wiring.analyze_wiring dropped the 'ctor_arity' "
            "key the post-wave wiring gate depends on"
        )
        assert "mocked_seam" in result
        assert "status" in result["ctor_arity"]
        assert "findings" in result["ctor_arity"]

    def test_dialect_exposes_ctor_arity_query_fields(self):
        py = wiring.get_dialect("python")
        assert py is not None
        for field_name in (
            "composition_root_markers",
            "constructor_signature_query",
            "constructor_call_query",
            "param_self_names",
            "param_default_node_types",
            "param_splat_node_types",
            "param_required_node_types",
            "arg_keyword_node_types",
            "arg_splat_node_types",
        ):
            assert hasattr(py, field_name), (
                f"WiringDialect dropped '{field_name}' the ctor-arity probe needs"
            )
        # Python populates them (day-one stack).
        assert py.constructor_signature_query
        assert py.composition_root_markers


class TestEndToEndCtorArityThroughGate:
    """The real factory output flows through guardkit's collector correctly."""

    def test_feat_poc_006_shape_produces_turn_rejecting_findings(self, tmp_path):
        svc = _write(tmp_path, "src/voice/service.py", _SERVICE)
        main = _write(
            tmp_path,
            "main.py",
            "from src.voice.service import VoiceService\n"
            "def build():\n    return VoiceService(transport)\n",
        )
        test = _write(
            tmp_path,
            "tests/integration/test_router.py",
            "from unittest.mock import AsyncMock\n"
            "def test_router():\n"
            "    return AsyncMock(spec=VoiceService)\n",
        )
        result = wiring.analyze_wiring([svc, main, test], tmp_path, "feature")

        # The real factory output, fed through guardkit's collector, must yield
        # BOTH a mocked-primary-seam and a ctor-arity turn-rejecting finding.
        findings = FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result)
        patterns = {f["pattern"] for f in findings}
        assert "MOCKED_SEAM" in patterns
        assert "CTOR_ARITY" in patterns

    def test_clean_wiring_yields_no_turn_rejecting_findings(self, tmp_path):
        svc = _write(tmp_path, "src/voice/service.py", _SERVICE)
        main = _write(
            tmp_path,
            "main.py",
            "from src.voice.service import VoiceService\n"
            "def build():\n    return VoiceService(transport, config)\n",
        )
        result = wiring.analyze_wiring([svc, main], tmp_path, "feature")
        findings = FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result)
        assert findings == []
