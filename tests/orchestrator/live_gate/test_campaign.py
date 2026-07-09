"""Campaign loop: F9 ledger + confound disambiguation + guardrails (WS2 B4).

Includes the GATE: replay of the study-tutor five-attempt live-acceptance
campaign (``study-tutor/docs/runbooks/RESULTS-study-tutor-p2-live-acceptance-
2026-07-05.md``) — the runner must reproduce the SAME attributions, including
the GPU-confound reclassification as an environment revision.
"""

from __future__ import annotations

import pytest

from guardkit.orchestrator.live_gate.campaign import (
    AttemptInput,
    CampaignInputError,
    ProbeBeforeRerunRequired,
    RevisionInput,
    finalize_envelope,
    run_campaign,
    write_campaign,
)
from guardkit.orchestrator.live_gate.disposition import make_disposition
from guardkit.orchestrator.live_gate.verdict import assemble_run_verdict
from guardkit.qa.formats import validate_instance
from guardkit.qa.formats.attempts_ledger import DeploymentState, HarnessSetting, Probe
from guardkit.qa.formats.disposition_record import FailureDisposition


def _disp(failure_id, attribution, disposition, **kw) -> FailureDisposition:
    return make_disposition(failure_id, failure_id, attribution, disposition, **kw)


def _reds_of(record, prefix):
    return [f for f in record.failures if f.failure_id.startswith(prefix)]


# ---------------------------------------------------------------------------
# THE GATE — study-tutor five-attempt replay
# ---------------------------------------------------------------------------


def _study_tutor_campaign():
    """The five attempts from RESULTS-study-tutor-p2-live-acceptance-2026-07-05."""
    a1 = AttemptInput(
        n=1,
        date="2026-07-05",
        deployment_state=DeploymentState(
            repo_shas={"study-tutor": "369973d"}, backend_config="sync Coach, mis-wired serializers"
        ),
        harness_settings=[HarnessSetting(param="turn_deadline_s", status="contract", value="120")],
        result="22/35",
        passed=False,
        # 13 failures triaged (binding doc as arbiter) to two backend wire bugs,
        # fixed GB10-side (208ebf1).
        failures=[
            _disp("a1:timestamp_vs_ts", "backend", "defect_fixed", fix_ref="208ebf1"),
            _disp("a1:turn_count_rowcount", "backend", "defect_fixed", fix_ref="208ebf1"),
        ],
    )
    a2 = AttemptInput(
        n=2,
        date="2026-07-05",
        deployment_state=DeploymentState(backend_config="sync Coach, wire fixed"),
        harness_settings=[HarnessSetting(param="turn_deadline_s", status="contract", value="120")],
        result="35/35",
        passed=True,
    )
    # Attempt 3: async Coach, 34/35 — one deadline spike, PROVISIONALLY backend
    # latency; the confound is identified at attempt 4.
    a3 = AttemptInput(
        n=3,
        date="2026-07-05",
        deployment_state=DeploymentState(backend_config="async Coach (ADR-ARCH-026)"),
        harness_settings=[HarnessSetting(param="turn_deadline_s", status="contract", value="35")],
        result="34/35",
        passed=False,
        failures=[_disp("a3:deadline_spike", "backend", "accommodation_documented")],
    )
    # Attempt 4: async Coach + concurrent LPA extraction, 32/35. Confound
    # identified (llama-swap eviction by LPA's docling/VLM models); async Coach
    # exonerated. Reclassifies attempt 3's spike -> environment (the revision),
    # and its own reds are environment. The 60s deadline is a LOUD accommodation.
    a4 = AttemptInput(
        n=4,
        date="2026-07-05",
        deployment_state=DeploymentState(
            backend_config="async Coach + concurrent LPA extraction"
        ),
        harness_settings=[
            HarnessSetting(
                param="turn_deadline_s",
                status="accommodation",
                value="60",
                vs_contract_value="35",
                reason="concurrent LPA workload contended the GB10 GPU; loosened to isolate the confound",
                documented_where="RESULTS-study-tutor-p2-live-acceptance-2026-07-05.md attempt 4",
            )
        ],
        result="32/35",
        passed=False,
        failures=[
            _disp("a4:evict_1", "environment", "accommodation_documented"),
            _disp("a4:evict_2", "environment", "accommodation_documented"),
            _disp("a4:evict_3", "environment", "accommodation_documented"),
        ],
        revises=[
            RevisionInput(
                target_failure_id="a3:deadline_spike",
                corrected_to="environment",
                evidence="confound identified by Rich: llama-swap eviction by LPA's docling/VLM models; async Coach exonerated",
                date="2026-07-05",
            )
        ],
    )
    # Attempt 5: async Coach, quiet GPU, 35/35 — the controlled rerun confirming
    # the environment attribution. warm-up performed (cold-load ~22s), probe run
    # first (quiet-GPU check).
    a5 = AttemptInput(
        n=5,
        date="2026-07-05",
        deployment_state=DeploymentState(backend_config="async Coach, quiet GPU"),
        harness_settings=[HarnessSetting(param="turn_deadline_s", status="contract", value="60")],
        warm_up_performed=True,
        result="35/35",
        passed=True,
        is_rerun=True,
        probes_run_first=[
            Probe(probe_cmd="nvidia-smi", finding="GPU quiet — no LPA docling/VLM tenants")
        ],
    )
    return [a1, a2, a3, a4, a5]


class TestStudyTutorReplayGate:
    def test_final_verdict_is_pass(self):
        result = run_campaign(
            "study-tutor-p2-wave-7", "FEAT-APP-001", "gb10", _study_tutor_campaign()
        )
        assert result.verdict == "pass"
        assert len(result.ledger.attempts) == 5

    def test_attempt1_wire_bugs_attributed_backend_defect_fixed(self):
        result = run_campaign(
            "study-tutor-p2-wave-7", "FEAT-APP-001", "gb10", _study_tutor_campaign()
        )
        a1_reds = _reds_of(result.dispositions, "a1:")
        assert len(a1_reds) == 2
        assert all(f.attribution == "backend" for f in a1_reds)
        assert all(f.disposition == "defect_fixed" for f in a1_reds)
        assert all(f.fix_ref == "208ebf1" for f in a1_reds)

    def test_gpu_confound_reclassified_as_environment_revision(self):
        # THE gate's named requirement: the deadline spike (attempt 3) is
        # revised backend -> environment when the GPU confound is disambiguated.
        result = run_campaign(
            "study-tutor-p2-wave-7", "FEAT-APP-001", "gb10", _study_tutor_campaign()
        )
        spike = next(f for f in result.dispositions.failures if f.failure_id == "a3:deadline_spike")
        assert spike.attribution == "environment"
        assert len(spike.revisions) == 1
        rev = spike.revisions[0]
        assert rev.prior_attribution == "backend"
        assert rev.corrected_to == "environment"
        assert "llama-swap eviction" in rev.evidence

    def test_eviction_reds_are_environment_and_do_not_count(self):
        result = run_campaign(
            "study-tutor-p2-wave-7", "FEAT-APP-001", "gb10", _study_tutor_campaign()
        )
        a4_reds = _reds_of(result.dispositions, "a4:")
        assert len(a4_reds) == 3
        assert all(f.attribution == "environment" for f in a4_reds)
        # environment reds never count against the feature (DF-017) and are
        # routed auto_rerun (after fix), not route_and_notify.
        for f in a4_reds:
            assert result.routing[f.failure_id] == "auto_rerun"
        assert result.routing["a3:deadline_spike"] == "auto_rerun"  # post-revision
        # backend (attempt-1) reds ARE route_and_notify
        assert result.routing["a1:timestamp_vs_ts"] == "route_and_notify"

    def test_async_coach_exonerated_attempt3_isolated_verdict(self):
        # If attempt 3 were assembled in isolation post-revision, it is an
        # environment_fail — NOT a feature fail (the async Coach is exonerated).
        result = run_campaign(
            "study-tutor-p2-wave-7", "FEAT-APP-001", "gb10", _study_tutor_campaign()
        )
        from guardkit.orchestrator.live_gate.disposition import Red

        spike_red = Red(failure_id="a3:deadline_spike", assertion="a3:deadline_spike", kind="assertion")
        assert assemble_run_verdict([spike_red], result.dispositions) == "environment_fail"

    def test_loud_accommodation_recorded_in_ledger(self):
        result = run_campaign(
            "study-tutor-p2-wave-7", "FEAT-APP-001", "gb10", _study_tutor_campaign()
        )
        a4 = next(a for a in result.ledger.attempts if a.n == 4)
        accommodations = [h for h in a4.harness_settings if h.status == "accommodation"]
        assert len(accommodations) == 1
        acc = accommodations[0]
        assert acc.reason and acc.documented_where  # loud, named — guaranteed by schema

    def test_ledger_and_record_validate_against_schema(self, tmp_path):
        result = run_campaign(
            "study-tutor-p2-wave-7", "FEAT-APP-001", "gb10", _study_tutor_campaign()
        )
        refs = write_campaign(result, tmp_path, run_id="FEAT-APP-001-gb10-run")
        # both files exist under qa/ and validate against their own schemas
        assert validate_instance("attempts-ledger", tmp_path / refs.attempts_ledger_ref)
        assert validate_instance("disposition-record", tmp_path / refs.dispositions_ref)

    def test_probe_run_first_recorded_for_rerun(self):
        result = run_campaign(
            "study-tutor-p2-wave-7", "FEAT-APP-001", "gb10", _study_tutor_campaign()
        )
        a5 = next(a for a in result.ledger.attempts if a.n == 5)
        assert a5.warm_up_performed is True
        assert len(a5.probes_run_first) == 1
        assert "nvidia-smi" in a5.probes_run_first[0].probe_cmd


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------


class TestGuardrails:
    def test_expensive_rerun_without_probe_raises(self):
        att = AttemptInput(
            n=1,
            date="2026-07-05",
            deployment_state=DeploymentState(),
            result="fail",
            passed=False,
            expensive=True,
            is_rerun=True,
            probes_run_first=[],  # the violation
            failures=[_disp("f1", "environment", "accommodation_documented")],
        )
        with pytest.raises(ProbeBeforeRerunRequired):
            run_campaign("c", "FEAT-X", "gb10", [att])

    def test_expensive_rerun_with_probe_is_allowed(self):
        att = AttemptInput(
            n=1,
            date="2026-07-05",
            deployment_state=DeploymentState(),
            result="35/35",
            passed=True,
            expensive=True,
            is_rerun=True,
            probes_run_first=[Probe(probe_cmd="nvidia-smi", finding="quiet")],
        )
        result = run_campaign("c", "FEAT-X", "gb10", [att])
        assert result.verdict == "pass"

    def test_silent_accommodation_is_unconstructable(self):
        # The guardrail is structural: an accommodation without reason/where
        # cannot be built (the code path does not exist).
        with pytest.raises(ValueError):
            HarnessSetting(param="turn_deadline_s", status="accommodation", value="60")

    def test_dangling_revision_target_raises(self):
        att = AttemptInput(
            n=1,
            date="2026-07-05",
            deployment_state=DeploymentState(),
            result="fail",
            passed=False,
            revises=[
                RevisionInput(
                    target_failure_id="nope", corrected_to="environment", evidence="x", date="2026-07-05"
                )
            ],
        )
        with pytest.raises(CampaignInputError):
            run_campaign("c", "FEAT-X", "gb10", [att])

    def test_non_ascending_attempts_raises(self):
        a2 = AttemptInput(n=2, date="2026-07-05", deployment_state=DeploymentState(), result="x", passed=True)
        a1 = AttemptInput(n=1, date="2026-07-05", deployment_state=DeploymentState(), result="x", passed=True)
        with pytest.raises(CampaignInputError):
            run_campaign("c", "FEAT-X", "gb10", [a2, a1])

    def test_empty_attempts_raises(self):
        with pytest.raises(CampaignInputError):
            run_campaign("c", "FEAT-X", "gb10", [])

    def test_terminal_undispositioned_red_would_raise(self):
        # A terminal attempt that reports failures it never binned cannot yield a
        # verdict (DF-017 §2.1). Model by an attempt claiming failed but the
        # terminal has reds with no disposition is impossible via AttemptInput
        # (failures ARE the bins) — so assert closure via a terminal with reds
        # whose record is consistent, and confirm a genuine unbinned terminal via
        # assemble_run_verdict directly.
        from guardkit.orchestrator.live_gate.disposition import Red, UndispositionedRedError

        red = Red(failure_id="x", assertion="x", kind="assertion")
        with pytest.raises(UndispositionedRedError):
            assemble_run_verdict([red], None)


# ---------------------------------------------------------------------------
# finalize_envelope
# ---------------------------------------------------------------------------


class TestFinalizeEnvelope:
    def test_stamps_verdict_and_refs(self):
        from datetime import datetime, timezone

        from guardkit.qa.formats.gate_registry import PreflightResult, ResultsEnvelope

        stamp = datetime(2026, 7, 8, tzinfo=timezone.utc).isoformat()
        env = ResultsEnvelope(
            format_version=ResultsEnvelope.CURRENT_FORMAT_VERSION,
            run_id="FEAT-X-gb10-run",
            feature_id="FEAT-X",
            target_env="gb10",
            started=stamp,
            finished=stamp,
            preflight=PreflightResult(checks=[], instrument_ok=True),
            gates=[],
            verdict="pass",
        )
        att = AttemptInput(n=1, date="2026-07-08", deployment_state=DeploymentState(), result="35/35", passed=True)
        result = run_campaign("FEAT-X", "FEAT-X", "gb10", [att])
        from guardkit.orchestrator.live_gate.campaign import CampaignRefs

        refs = CampaignRefs(dispositions_ref="qa/dispositions-x.yaml", attempts_ledger_ref="qa/attempts-FEAT-X.yaml")
        out = finalize_envelope(env, result, refs)
        assert out.verdict == "pass"
        assert out.dispositions_ref == "qa/dispositions-x.yaml"
        assert out.attempts_ledger_ref == "qa/attempts-FEAT-X.yaml"
