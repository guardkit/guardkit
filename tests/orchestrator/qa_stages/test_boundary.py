"""ST-06 boundary-probe tests, incl. THE B6 GATE (raw-error leak on a fixture seam)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from guardkit.orchestrator.qa_stages import (
    ProbeInput,
    QAStageStubError,
    UnconfiguredProbeTarget,
    default_input_battery,
    load_seam_ids,
    run_boundary_probes,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "qa_stages"

sys.path.insert(0, str(FIXTURES))
from seam_decoder import HARDENED, LEAKY, EnvelopeError  # noqa: E402


# --------------------------------------------------------------------------- #
# THE GATE — a leaky seam produces a raw-escape finding
# --------------------------------------------------------------------------- #
def test_boundary_gate_reproduces_raw_escape():
    """B6 GATE: the leaky decoder leaks raw errors past its sealed EnvelopeError set."""
    result = run_boundary_probes("deploy-envelope", LEAKY)
    assert result.findings  # at least one finding
    assert result.leaks  # at least one RAW-error leak
    leaked_types = {o.exception_type for o in result.leaks}
    # json + missing-key escapes are raw (outside EnvelopeError).
    assert "JSONDecodeError" in leaked_types or "KeyError" in leaked_types
    assert all(o.exception_type != "EnvelopeError" for o in result.leaks)


def test_boundary_gate_reproduces_the_retro_typeerror():
    """The retro's exact escape: a proxy-style nested error string → raw TypeError."""
    # Target the fixture decoder's discriminator ("kind") so we reach the
    # data["error"]["detail"] path where a string 'error' throws TypeError.
    inputs = [ProbeInput("proxy-nested-error", {"kind": "queued", "error": "boom"})]
    result = run_boundary_probes("deploy-envelope", LEAKY, inputs)
    assert len(result.leaks) == 1
    assert result.leaks[0].exception_type == "TypeError"


def test_hardened_seam_reports_clean_posture():
    result = run_boundary_probes("deploy-envelope", HARDENED)
    assert result.findings == []
    assert result.leaks == []
    assert all(o.classification == "handled" for o in result.outcomes)


def test_garbage_accept_is_a_finding():
    class _Permissive:
        sealed_errors = (EnvelopeError,)

        def decode(self, raw):
            return {"ok": True}  # accepts everything, incl. garbage

    result = run_boundary_probes("s", _Permissive())
    # Every garbage input is silently accepted → all findings, classification 'accepted'.
    assert result.findings
    assert all(o.classification == "accepted" for o in result.findings)
    assert result.leaks == []


def test_non_garbage_input_accepted_is_not_a_finding():
    class _Ok:
        sealed_errors = (EnvelopeError,)

        def decode(self, raw):
            return raw

    inputs = [ProbeInput("valid-shape", {"kind": "queued"}, is_garbage=False)]
    result = run_boundary_probes("s", _Ok(), inputs)
    assert result.findings == []
    assert result.outcomes[0].classification == "handled"


# --------------------------------------------------------------------------- #
# Loud unconfigured target (FEAT-DD4F — no silent green)
# --------------------------------------------------------------------------- #
def test_unconfigured_target_raises_loudly():
    with pytest.raises(QAStageStubError, match="not configured"):
        run_boundary_probes("s", UnconfiguredProbeTarget())


def test_default_battery_covers_the_known_escape_classes():
    battery = default_input_battery()
    labels = {p.label for p in battery}
    assert {"proxy-nested-error", "out-of-enum", "empty-bytes", "top-level-list"} <= labels


# --------------------------------------------------------------------------- #
# F6 seam manifest is consumed READ-ONLY
# --------------------------------------------------------------------------- #
def test_load_seam_ids_reads_f6_manifest():
    ids = load_seam_ids(FIXTURES / "seam_manifest.yaml")
    assert ids == ["deploy-envelope"]
