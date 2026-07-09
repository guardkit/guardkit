"""Cross-repo contract seam test for CALLSITE_DRIFT (WS3-S3 2b).

The ``.claude/rules/harness-cancellation-contract.md`` CI-guard pattern applied
to the new seam check: the guardkit post-wave gate depends on the **real
installed** ``guardkitfactory.wiring.analyze_wiring`` result carrying a
``callsite_drift`` key, and on the Python dialect populating the new query
fields (``imports_query`` / ``function_signature_query`` / ``call_site_query``).
A factory version skew that drops the contract must fail HERE, in CI seconds,
not silently degrade to absent-signal on a live autobuild run.

``pytest.importorskip`` skips cleanly without the ``[autobuild]`` extra.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.seam]

wiring = pytest.importorskip("guardkitfactory.wiring")

from guardkitfactory.wiring.callsite_drift import analyze_callsite_drift  # noqa: E402
from guardkitfactory.wiring.env_tamper import analyze_env_tamper  # noqa: E402


def _write(root: Path, rel: str, content: str) -> str:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return rel


class TestCallsiteDriftContract:
    def test_analyze_wiring_returns_callsite_drift_key(self, tmp_path):
        svc = _write(tmp_path, "src/svc.py", "def build(a, b):\n    return 1\n")
        result = wiring.analyze_wiring([svc], tmp_path, "feature")
        assert result is not None
        assert "callsite_drift" in result, (
            "guardkitfactory.wiring.analyze_wiring dropped the 'callsite_drift' "
            "key the WS3-S3 2b gate depends on"
        )
        cd = result["callsite_drift"]
        assert "status" in cd and "findings" in cd and "apertures_run" in cd

    def test_dialect_exposes_callsite_drift_query_fields(self):
        py = wiring.get_dialect("python")
        assert py is not None
        for field_name in ("imports_query", "function_signature_query", "call_site_query"):
            assert hasattr(py, field_name), (
                f"WiringDialect dropped '{field_name}' CALLSITE_DRIFT needs"
            )
            assert getattr(py, field_name), f"Python dialect must populate {field_name}"
        assert py.smoke_test(), "new seam queries must compile in smoke_test()"


class TestCallsiteDriftApertures:
    def test_aperture_b_dd4f_shape_fires(self, tmp_path):
        _write(tmp_path, "pkg/api.py",
               "def compose(*, db_path, nats_client, config):\n    return 1\n")
        _write(tmp_path, "pkg/serve.py",
               "from pkg.api import compose\n"
               "def serve(c, p):\n    return compose(client=c, sqlite_pool=p, config=1)\n")
        r = analyze_callsite_drift(["pkg/serve.py"], tmp_path, "feature")
        assert r["ran"] is True
        assert any(f["form"] == "unknown_kwarg" and f["aperture"] == "B"
                   for f in r["findings"])

    def test_aperture_a_needs_baseline(self, tmp_path):
        _write(tmp_path, "pkg/api.py", "def fn(a, y=None):\n    return 1\n")
        _write(tmp_path, "pkg/caller.py",
               "from pkg.api import fn\n"
               "def c():\n    return fn(a=1, x=2)\n")
        baseline = {"pkg/api.py": b"def fn(a, x=None):\n    return 1\n"}
        r = analyze_callsite_drift(["pkg/api.py"], tmp_path, "feature",
                                   baseline_sources=baseline)
        assert "A" in r["apertures_run"]
        assert any(f["file"].endswith("caller.py") for f in r["findings"])


class TestEnvTamperContract:
    """ENVTAMPER-b (SYS_MODULES_TAMPER) seam: the env_tamper key + ABL-001 fire."""

    def test_analyze_wiring_returns_env_tamper_key(self, tmp_path):
        svc = _write(tmp_path, "src/svc.py", "def build(a):\n    return 1\n")
        result = wiring.analyze_wiring([svc], tmp_path, "feature")
        assert result is not None
        assert "env_tamper" in result, (
            "analyze_wiring dropped the 'env_tamper' key ENVTAMPER-b depends on"
        )
        assert wiring.get_dialect("python").env_tamper_query

    def test_abl001_shape_fires(self, tmp_path):
        _write(tmp_path, "pkg/__init__.py",
               "import sys, types\n"
               "sys.modules['nats_core'] = types.ModuleType('nats_core')\n")
        r = analyze_env_tamper(["pkg/__init__.py"], tmp_path, "feature")
        assert r["ran"] is True
        assert any(f["module_key"] == "nats_core" for f in r["findings"])


class TestAdvisoryDisposition:
    """§8: CALLSITE_DRIFT + SYS_MODULES_TAMPER stay ADVISORY until promotion."""

    def test_new_kinds_are_not_turn_rejecting(self):
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        result = {
            "status": "complete",
            "mocked_seam": {"status": "skipped_no_acceptance_files", "findings": []},
            "ctor_arity": {"status": "skipped_no_composition_root", "findings": []},
            "callsite_drift": {"status": "ran", "findings": [
                {"pattern": "CALLSITE_DRIFT", "form": "unknown_kwarg",
                 "file": "x.py", "lineno": 1}]},
            "env_tamper": {"status": "ran", "findings": [
                {"pattern": "SYS_MODULES_TAMPER", "file": "y.py", "lineno": 2}]},
        }
        turn_rejecting = FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result)
        assert turn_rejecting == [], (
            "CALLSITE_DRIFT / SYS_MODULES_TAMPER must stay advisory (§8 promotion "
            "gate not yet passed) — never turn-rejecting on first landing"
        )
