"""F8 disposition-record + F9 attempts-ledger schema tests (WS2 session B4).

Mirrors the B1 discipline: a well-formed instance validates; a mutated instance
fails LOUDLY with a field-level message (never a silent accept). Also pins the
CLI kind registration (f8/f9 aliases) and the format_version window.
"""

from __future__ import annotations

import textwrap

import pytest

from guardkit.qa.formats import (
    QAFormatError,
    resolve_kind,
    validate_instance,
)

_DISPOSITION_OK = textwrap.dedent(
    """\
    format_version: "1.0"
    run_id: FEAT-APP-001-gb10-run
    failures:
      - failure_id: a1:timestamp_vs_ts
        assertion: a1:timestamp_vs_ts
        attribution: backend
        disposition: defect_fixed
        fix_ref: 208ebf1
      - failure_id: a3:deadline_spike
        assertion: a3:deadline_spike
        attribution: environment
        disposition: accommodation_documented
        revisions:
          - date: "2026-07-05"
            prior_attribution: backend
            corrected_to: environment
            evidence: llama-swap eviction confound identified
    """
)

_ATTEMPTS_OK = textwrap.dedent(
    """\
    format_version: "1.0"
    campaign: study-tutor-p2-wave-7
    feature_id: FEAT-APP-001
    target_env: gb10
    attempts:
      - n: 1
        date: "2026-07-05"
        deployment_state: {backend_config: "sync Coach"}
        harness_settings:
          - {param: turn_deadline_s, status: contract, value: "120"}
        result: "22/35"
        passed: false
        failure_disposition_refs: [a1:timestamp_vs_ts]
      - n: 5
        date: "2026-07-05"
        deployment_state: {backend_config: "async Coach, quiet GPU"}
        warm_up_performed: true
        result: "35/35"
        passed: true
        probes_run_first:
          - {probe_cmd: nvidia-smi, finding: "GPU quiet"}
    """
)


class TestKindRegistration:
    def test_f8_alias_resolves(self):
        assert resolve_kind("f8").FORMAT_KIND == "disposition-record"

    def test_f9_alias_resolves(self):
        assert resolve_kind("f9").FORMAT_KIND == "attempts-ledger"


class TestDispositionRecord:
    def test_valid_instance(self, tmp_path):
        p = tmp_path / "dispositions.yaml"
        p.write_text(_DISPOSITION_OK)
        rec = validate_instance("disposition-record", p)
        assert rec.failures[1].revisions[0].corrected_to == "environment"

    def test_bad_attribution_fails_loudly(self, tmp_path):
        p = tmp_path / "dispositions.yaml"
        p.write_text(_DISPOSITION_OK.replace("attribution: backend", "attribution: gremlin"))
        with pytest.raises(QAFormatError) as exc:
            validate_instance("disposition-record", p)
        assert "attribution" in str(exc.value)

    def test_unknown_key_forbidden(self, tmp_path):
        p = tmp_path / "dispositions.yaml"
        p.write_text(_DISPOSITION_OK + "        surprise: 1\n")
        with pytest.raises(QAFormatError):
            validate_instance("disposition-record", p)


class TestAttemptsLedger:
    def test_valid_instance(self, tmp_path):
        p = tmp_path / "attempts.yaml"
        p.write_text(_ATTEMPTS_OK)
        led = validate_instance("attempts-ledger", p)
        assert len(led.attempts) == 2
        assert led.attempts[0].harness_settings[0].status == "contract"

    def test_silent_accommodation_fails_loudly(self, tmp_path):
        # An accommodation harness setting missing reason/documented_where must
        # fail validation — the loud-named-entry guardrail at schema level.
        bad = _ATTEMPTS_OK.replace(
            "{param: turn_deadline_s, status: contract, value: \"120\"}",
            "{param: turn_deadline_s, status: accommodation, value: \"60\"}",
        )
        p = tmp_path / "attempts.yaml"
        p.write_text(bad)
        with pytest.raises(QAFormatError) as exc:
            validate_instance("attempts-ledger", p)
        assert "accommodation" in str(exc.value)

    def test_empty_attempts_fails(self, tmp_path):
        p = tmp_path / "attempts.yaml"
        p.write_text(
            textwrap.dedent(
                """\
                format_version: "1.0"
                campaign: c
                feature_id: FEAT-X
                target_env: gb10
                attempts: []
                """
            )
        )
        with pytest.raises(QAFormatError):
            validate_instance("attempts-ledger", p)
