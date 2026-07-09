"""F9 · campaign loop — attempts ledger + confound disambiguation (WS2 session B4).

A *campaign* is a sequence of acceptance attempts against one live target
(scope-design §3 step 7 / ST-08). This module turns an ordered list of attempt
inputs into the F9 :class:`AttemptsLedger`, the accumulated F8
:class:`DispositionRecord` (with ST-09 revisions applied), and the campaign's
final verdict — the attribution-aware verdict of the **terminal** attempt (the
acceptance run). Intermediate attempts' reds are ledgered and binned but do not
by themselves decide the campaign verdict.

Deterministic: no clock, no model calls; dates are caller-supplied. The engine
is the offline core the study-tutor five-attempt replay drives.

Structural guardrails (WS2 build-plan §B4), each enforced here or in the schema:

- **Accommodations are loud, named entries** — enforced by
  :class:`~guardkit.qa.formats.attempts_ledger.HarnessSetting` (an accommodation
  without ``reason``/``documented_where`` cannot be constructed). Product
  deadlines are read-only to the harness: there is no field or code path that
  stretches a product deadline — an attempt records only the *harness* settings
  it used, and any deviation is a named accommodation.
- **Probe-before-rerun is a checked field** — :func:`run_campaign` refuses an
  *expensive* rerun whose ``probes_run_first`` is empty
  (:class:`ProbeBeforeRerunRequired`).
- **Undispositioned red = unclosed run** — the terminal attempt's reds must all
  be binned (DF-017 §2.1), else :func:`run_campaign` raises.
- **Automated re-runs only for instrument/environment** — :attr:`CampaignResult.routing`
  reports ``route_and_notify`` for every counts-class red and ``auto_rerun`` only
  for instrument/environment (DF-017 §2.4). The engine never *initiates* a rerun
  itself; it records what each red is eligible for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import yaml

from guardkit.qa.formats.attempts_ledger import (
    Attempt,
    AttemptsLedger,
    DeploymentState,
    HarnessSetting,
    Probe,
)
from guardkit.qa.formats.disposition_record import (
    Attribution,
    DispositionRecord,
    FailureDisposition,
)
from guardkit.qa.formats.gate_registry import ResultsEnvelope

from guardkit.orchestrator.live_gate.disposition import (
    Red,
    Routing,
    build_disposition_record,
    revise_attribution,
    routing_for,
)
from guardkit.orchestrator.live_gate.errors import LiveGateError
from guardkit.orchestrator.live_gate.verdict import Verdict, assemble_run_verdict


class ProbeBeforeRerunRequired(LiveGateError):
    """An expensive rerun was recorded with no probe run first (ST-08).

    Probe-before-rerun is a checked field on expensive suites: re-running a
    costly suite without first probing what changed burns the budget and hides
    the confound. The message names the attempt.
    """


class CampaignInputError(LiveGateError):
    """The campaign input is internally inconsistent (bad ordering, dangling
    revision target, etc.)."""


@dataclass(frozen=True)
class RevisionInput:
    """A same-day ST-09 correction of an EARLIER attempt's red (confound resolved)."""

    target_failure_id: str
    corrected_to: Attribution
    evidence: str
    date: str


@dataclass(frozen=True)
class AttemptInput:
    """One attempt's inputs — what a live driver hands the ledger after the run.

    ``failures`` are this attempt's reds, already binned against the arbiter
    (F8). ``revises`` corrects the attribution of an EARLIER attempt's red once a
    controlled rerun disambiguates a confound (the GPU-eviction case).
    """

    n: int
    date: str
    deployment_state: DeploymentState
    result: str
    passed: bool
    harness_settings: Sequence[HarnessSetting] = ()
    warm_up_performed: bool = False
    failures: Sequence[FailureDisposition] = ()
    probes_run_first: Sequence[Probe] = ()
    expensive: bool = False
    is_rerun: bool = False
    revises: Sequence[RevisionInput] = ()


@dataclass(frozen=True)
class CampaignResult:
    """The campaign's three products + its final verdict."""

    ledger: AttemptsLedger
    dispositions: DispositionRecord
    verdict: Verdict
    #: failure_id -> routing (counts => route_and_notify; instrument/env => auto_rerun).
    routing: Dict[str, Routing] = field(default_factory=dict)


@dataclass(frozen=True)
class CampaignRefs:
    """Repo-relative refs to the written F8/F9 files."""

    dispositions_ref: str
    attempts_ledger_ref: str


def _reds_of(failures: Sequence[FailureDisposition]) -> List[Red]:
    """Reds for a single attempt, from its binned failures (for verdict assembly)."""
    return [
        Red(
            failure_id=f.failure_id,
            assertion=f.assertion,
            kind="assertion",
            observed=f.observed,
            expected=f.expected,
            evidence_ref=f.evidence_ref,
        )
        for f in failures
    ]


def run_campaign(
    campaign: str,
    feature_id: str,
    target_env: str,
    attempts: Sequence[AttemptInput],
) -> CampaignResult:
    """Fold an ordered attempt sequence into the F9 ledger + F8 record + verdict.

    Raises:
        CampaignInputError: empty ``attempts``, non-ascending ``n``, or a
            revision targeting a red not yet seen.
        ProbeBeforeRerunRequired: an expensive rerun with no probes run first.
        UndispositionedRedError: the terminal attempt has an unbinned red.
    """
    if not attempts:
        raise CampaignInputError("run_campaign: attempts is empty — a campaign has ≥1 attempt")

    ordered = list(attempts)
    if [a.n for a in ordered] != sorted(a.n for a in ordered):
        raise CampaignInputError(
            f"attempts must be in ascending n order, got {[a.n for a in ordered]!r}"
        )

    # Accumulated F8 failures, keyed by failure_id, INSERTION-ORDER preserved so
    # the record reads in the order reds were first seen.
    accumulated: Dict[str, FailureDisposition] = {}
    ledger_attempts: List[Attempt] = []

    for att in ordered:
        # Guardrail: probe-before-rerun on expensive suites.
        if att.expensive and att.is_rerun and not att.probes_run_first:
            raise ProbeBeforeRerunRequired(
                f"attempt {att.n} is an expensive rerun but ran no probe first "
                f"(ST-08 probe-before-rerun is a checked field on expensive suites)."
            )

        # Apply this attempt's ST-09 revisions to EARLIER binned reds first — a
        # controlled rerun that disambiguates a confound corrects the prior
        # attribution (e.g. backend-latency -> environment for the GPU eviction).
        for rev in att.revises:
            target = accumulated.get(rev.target_failure_id)
            if target is None:
                raise CampaignInputError(
                    f"attempt {att.n} revises unknown failure_id "
                    f"{rev.target_failure_id!r} — no earlier attempt binned it."
                )
            accumulated[rev.target_failure_id] = revise_attribution(
                target,
                corrected_to=rev.corrected_to,
                evidence=rev.evidence,
                date=rev.date,
            )

        # Fold in this attempt's own reds (upsert — a re-observed red keeps its
        # latest binning).
        for failure in att.failures:
            accumulated[failure.failure_id] = failure

        ledger_attempts.append(
            Attempt(
                n=att.n,
                date=att.date,
                deployment_state=att.deployment_state,
                harness_settings=list(att.harness_settings),
                warm_up_performed=att.warm_up_performed,
                result=att.result,
                passed=att.passed,
                failure_disposition_refs=[f.failure_id for f in att.failures],
                probes_run_first=list(att.probes_run_first),
            )
        )

    ledger = AttemptsLedger(
        format_version=AttemptsLedger.CURRENT_FORMAT_VERSION,
        campaign=campaign,
        feature_id=feature_id,
        target_env=target_env,
        attempts=ledger_attempts,
    )
    record = build_disposition_record(campaign, accumulated.values())

    # Campaign verdict = the terminal (acceptance) attempt's attribution-aware
    # verdict. This also enforces DF-017 §2.1 closure on the terminal attempt.
    terminal = ordered[-1]
    terminal_reds = _reds_of(terminal.failures)
    verdict = assemble_run_verdict(terminal_reds, record)

    routing = {f.failure_id: routing_for(f.attribution) for f in record.failures}

    return CampaignResult(ledger=ledger, dispositions=record, verdict=verdict, routing=routing)


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def write_campaign(result: CampaignResult, repo_root: Path, *, run_id: str) -> CampaignRefs:
    """Write the F8 record + F9 ledger under ``qa/`` and return repo-relative refs.

    - dispositions: ``qa/dispositions-<run_id>.yaml``
    - attempts:     ``qa/attempts-<campaign>.yaml``
    """
    qa_dir = repo_root / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    disp_path = qa_dir / f"dispositions-{run_id}.yaml"
    disp_path.write_text(
        yaml.safe_dump(result.dispositions.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    ledger_path = qa_dir / f"attempts-{result.ledger.campaign}.yaml"
    ledger_path.write_text(
        yaml.safe_dump(result.ledger.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    return CampaignRefs(
        dispositions_ref=_rel(disp_path, repo_root),
        attempts_ledger_ref=_rel(ledger_path, repo_root),
    )


def finalize_envelope(
    envelope: ResultsEnvelope,
    result: CampaignResult,
    refs: CampaignRefs,
) -> ResultsEnvelope:
    """Stamp a B3 envelope with the campaign verdict + F8/F9 refs.

    The terminal run's envelope carries the campaign's final verdict and points
    at the two records that justify it — filling the ``dispositions_ref`` /
    ``attempts_ledger_ref`` B3 deliberately left null.
    """
    return envelope.model_copy(
        update={
            "verdict": result.verdict,
            "dispositions_ref": refs.dispositions_ref,
            "attempts_ledger_ref": refs.attempts_ledger_ref,
        }
    )


def single_run_campaign(
    envelope: ResultsEnvelope,
    *,
    date: str,
    deployment_state: Optional[DeploymentState] = None,
    harness_settings: Sequence[HarnessSetting] = (),
    warm_up_performed: bool = False,
    dispositions: Sequence[FailureDisposition] = (),
) -> CampaignResult:
    """Build a one-attempt campaign from a single B3 run (the CLI ``--campaign`` v1).

    v1 has no live multi-attempt driver, so ``--campaign`` records the single run
    as attempt 1. Any reds in the envelope must be binned in ``dispositions``
    (unattended runs are green or pre-flight short-circuits — a run with unbinned
    reds raises, honestly UNCLOSED, never a silent green).

    Raises:
        UndispositionedRedError: the envelope has a red not covered by
            ``dispositions`` (DF-017 §2.1 — enforced against the envelope's OWN
            reds, not merely the supplied bins).
    """
    from guardkit.orchestrator.live_gate.disposition import assert_run_closed, iter_reds
    from guardkit.orchestrator.live_gate.verdict import enrich_envelope

    reds = iter_reds(envelope.gates, envelope.sweep)
    # Enforce closure against the envelope's real reds up front: an empty
    # ``dispositions`` for a run that HAS reds must raise, not silently pass.
    record = build_disposition_record(envelope.feature_id, dispositions)
    assert_run_closed(reds, record)

    attempt = AttemptInput(
        n=1,
        date=date,
        deployment_state=deployment_state or DeploymentState(),
        result=envelope.verdict,
        passed=envelope.verdict == "pass",
        harness_settings=harness_settings,
        warm_up_performed=warm_up_performed,
        failures=list(dispositions),
        # A single run is not a rerun; expensive-suite probe gating does not apply.
    )
    result = run_campaign(
        campaign=envelope.feature_id,
        feature_id=envelope.feature_id,
        target_env=envelope.target_env,
        attempts=[attempt],
    )
    # Preserve a pre-flight short-circuit verdict (environment_fail/instrument_fail
    # with no reds): enrich_envelope leaves a no-red envelope's verdict untouched,
    # so a single unattended run never gets flipped to a bare "pass".
    preserved = enrich_envelope(envelope, record).verdict
    from dataclasses import replace as _replace

    return _replace(result, verdict=preserved)
