"""Cross-repo contract seam test for CALLSITE_DRIFT (WS3-S3 2b).

The ``.claude/rules/harness-cancellation-contract.md`` CI-guard pattern applied
to the new seam check: the guardkit post-wave gate depends on the **real
installed** ``guardkitfactory.wiring.analyze_wiring`` result carrying a
``callsite_drift`` key, and on the Python dialect populating the new query
fields (``imports_query`` / ``function_signature_query`` / ``call_site_query``).
A factory version skew that drops the contract must fail HERE, in CI seconds,
not silently degrade to absent-signal on a live autobuild run.

The classes needing the cross-repo analyzer skip individually without the
``[autobuild]`` extra; TestAdvisoryDisposition needs nothing optional and runs
in the main suite. See the note above the helpers for why that matters.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.seam]

# The import guard is DELIBERATELY NOT at module level.
#
# It used to be, and the cost was that this whole file ran in NO continuous
# integration job at all: the main workflow deliberately does not install the
# `autobuild` extra (so `guardkitfactory` is absent and a module-level
# importorskip skipped every test here), and this file was never added to the
# seam workflow that does install it. Every test below passed by never running.
#
# That is the exact failure this file's own subject matter is about — a check
# that is green because it never looked. Found 2026-08-21 while promoting
# aperture B, by simulating the main workflow's environment and watching the
# file report "1 skipped, 0 executed".
#
# So: the classes that genuinely need the cross-repo analyzer ask for it
# themselves and skip individually, and TestAdvisoryDisposition — which uses
# nothing but plain dictionaries and guardkit's own code — runs in the main
# suite where it belongs. This file is also now listed in the seam workflow so
# the analyzer-dependent classes run somewhere too.


def _wiring():
    """The optional cross-repo analyzer, or an individual skip."""
    return pytest.importorskip("guardkitfactory.wiring")


def _analyze_callsite_drift():
    _wiring()
    from guardkitfactory.wiring.callsite_drift import analyze_callsite_drift

    return analyze_callsite_drift


def _analyze_env_tamper():
    _wiring()
    from guardkitfactory.wiring.env_tamper import analyze_env_tamper

    return analyze_env_tamper


def _write(root: Path, rel: str, content: str) -> str:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return rel


class TestCallsiteDriftContract:
    def test_analyze_wiring_returns_callsite_drift_key(self, tmp_path):
        svc = _write(tmp_path, "src/svc.py", "def build(a, b):\n    return 1\n")
        result = _wiring().analyze_wiring([svc], tmp_path, "feature")
        assert result is not None
        assert "callsite_drift" in result, (
            "guardkitfactory.wiring.analyze_wiring dropped the 'callsite_drift' "
            "key the WS3-S3 2b gate depends on"
        )
        cd = result["callsite_drift"]
        assert "status" in cd and "findings" in cd and "apertures_run" in cd

    def test_dialect_exposes_callsite_drift_query_fields(self):
        py = _wiring().get_dialect("python")
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
        r = _analyze_callsite_drift()(["pkg/serve.py"], tmp_path, "feature")
        assert r["ran"] is True
        assert any(f["form"] == "unknown_kwarg" and f["aperture"] == "B"
                   for f in r["findings"])

    def test_aperture_a_needs_baseline(self, tmp_path):
        _write(tmp_path, "pkg/api.py", "def fn(a, y=None):\n    return 1\n")
        _write(tmp_path, "pkg/caller.py",
               "from pkg.api import fn\n"
               "def c():\n    return fn(a=1, x=2)\n")
        baseline = {"pkg/api.py": b"def fn(a, x=None):\n    return 1\n"}
        r = _analyze_callsite_drift()(["pkg/api.py"], tmp_path, "feature",
                                   baseline_sources=baseline)
        assert "A" in r["apertures_run"]
        assert any(f["file"].endswith("caller.py") for f in r["findings"])


class TestEnvTamperContract:
    """ENVTAMPER-b (SYS_MODULES_TAMPER) seam: the env_tamper key + ABL-001 fire."""

    def test_analyze_wiring_returns_env_tamper_key(self, tmp_path):
        svc = _write(tmp_path, "src/svc.py", "def build(a):\n    return 1\n")
        result = _wiring().analyze_wiring([svc], tmp_path, "feature")
        assert result is not None
        assert "env_tamper" in result, (
            "analyze_wiring dropped the 'env_tamper' key ENVTAMPER-b depends on"
        )
        assert _wiring().get_dialect("python").env_tamper_query

    def test_abl001_shape_fires(self, tmp_path):
        _write(tmp_path, "pkg/__init__.py",
               "import sys, types\n"
               "sys.modules['nats_core'] = types.ModuleType('nats_core')\n")
        r = _analyze_env_tamper()(["pkg/__init__.py"], tmp_path, "feature")
        assert r["ran"] is True
        assert any(f["module_key"] == "nats_core" for f in r["findings"])


def _wiring_result(drift_findings, tamper=True):
    """A wiring result carrying the given call-site findings and nothing else."""
    return {
        "status": "complete",
        "mocked_seam": {"status": "skipped_no_acceptance_files", "findings": []},
        "ctor_arity": {"status": "skipped_no_composition_root", "findings": []},
        "callsite_drift": {"status": "ran", "findings": drift_findings},
        "env_tamper": {
            "status": "ran",
            "findings": (
                [{"pattern": "SYS_MODULES_TAMPER", "file": "y.py", "lineno": 2}]
                if tamper
                else []
            ),
        },
    }


class TestAdvisoryDisposition:
    """Which wiring signals may stop a build, and which only inform one.

    Changed 2026-08-21 on Rich's word. Aperture B of the call-site check —
    newly written calls measured against current signatures — is now
    turn-rejecting. Aperture A, and SYS_MODULES_TAMPER, remain advisory.

    Aperture B was promoted on two measurements: 1,068 tracked non-test files
    across five repositories (67 warnings before the source-reading repairs of
    which only 2 were real; 2 after, both genuine), and 125 real
    signature-changing commits replayed from history (6 findings, all 6 real,
    including a live crash a human found and fixed weeks later).

    Aperture A was held back because it had never been measured at all until
    that same day, and when it was, it turned out to decide WHICH functions
    changed by bare name across the whole repository while deciding whether a
    CALL MATCHES per module. Those disagree: 81% of the call sites it examined
    belonged to a different function of the same name. It found nothing only
    because none of them held a latent bug.
    """

    def test_aperture_b_finding_is_turn_rejecting(self):
        """A newly written call with a wrong argument name stops the turn."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        result = _wiring_result([
            {"pattern": "CALLSITE_DRIFT", "form": "unknown_kwarg",
             "file": "x.py", "lineno": 1, "aperture": "B"}
        ])
        turn_rejecting = FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result)
        assert len(turn_rejecting) == 1 and turn_rejecting[0]["file"] == "x.py", (
            "An aperture-B call-site finding must be turn-rejecting. It means "
            "the build just wrote a call passing an argument name the receiving "
            "function does not accept — a guaranteed crash when that line runs."
        )

    def test_aperture_a_finding_stays_advisory(self):
        """A stale caller elsewhere in the repo informs, it does not block.

        This is the load-bearing half of the promotion. If this test starts
        failing, somebody has widened the gate to aperture A — do not simply
        make it pass. Re-read the measurement first: aperture A's
        changed-function detection matches by bare name across the whole
        repository, so it can point at a function the build never touched.
        """
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        result = _wiring_result([
            {"pattern": "CALLSITE_DRIFT", "form": "unknown_kwarg",
             "file": "stale.py", "lineno": 9, "aperture": "A"}
        ])
        assert FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result) == [], (
            "An aperture-A finding must NOT stop a build. It reports a call "
            "site the build did not write, selected by a matcher that is known "
            "to name the wrong function 81% of the time — so a build could be "
            "stopped over a defect it did not cause and cannot fix."
        )

    def test_mixed_apertures_block_on_b_only(self):
        """B blocks; A rides along as evidence, in the same result."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        result = _wiring_result([
            {"pattern": "CALLSITE_DRIFT", "file": "authored.py", "lineno": 1, "aperture": "B"},
            {"pattern": "CALLSITE_DRIFT", "file": "stale.py", "lineno": 9, "aperture": "A"},
        ])
        turn_rejecting = FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result)
        assert [f["file"] for f in turn_rejecting] == ["authored.py"]

    def test_an_unlabelled_finding_does_not_block(self):
        """No aperture label means we cannot tell which half it came from.

        Absence-of-failure-safe, consistent with the rest of this gate: an
        unreadable signal never stops a build.
        """
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        result = _wiring_result([
            {"pattern": "CALLSITE_DRIFT", "file": "x.py", "lineno": 1}
        ])
        assert FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result) == []

    def test_tamper_stays_advisory(self):
        """SYS_MODULES_TAMPER was not part of this promotion and still informs only."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        result = _wiring_result([])
        assert FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result) == []

    def test_absent_signal_never_blocks(self):
        """A check that did not run cannot stop a build, whatever it left behind."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        result = _wiring_result([
            {"pattern": "CALLSITE_DRIFT", "file": "x.py", "lineno": 1, "aperture": "B"}
        ])
        result["callsite_drift"]["status"] = "parse_degraded"
        assert FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result) == []
