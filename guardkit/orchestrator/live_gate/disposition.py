"""F8 · failure-disposition lifecycle (WS2 session B4).

The enforcement point of **DF-017 §2.1**: a run cannot close while any observed
red lacks a disposition. This module is pure logic over the B3 results envelope's
reds and the F8 :class:`DispositionRecord`; ``verdict.py`` and ``campaign.py``
compose it.

Three responsibilities:

1. **Enumerate the reds a run must bin.** :func:`iter_reds` walks the B3 gate
   results + sweep and yields one :class:`Red` per failed assertion and per sweep
   leak, each with a canonical ``failure_id``.

2. **Refuse to close an undispositioned run.** :func:`undispositioned_reds` /
   :func:`assert_run_closed` — the DF-017 §2.1 gate. An unclosed run RAISES; it is
   never silently treated as a pass (the absence-of-failure discipline applied to
   the closing act itself).

3. **Attribution semantics.** :func:`wire_disposition` collapses the five
   attribution classes onto the nats-core ``counts|instrument|environment`` wire
   value; :func:`counts_against_feature` is the DF-017 invariant — only
   ``{app, backend, contract_gap}`` count against the feature; ``instrument`` and
   ``environment`` NEVER do. :func:`routing_for` returns ``route_and_notify`` for
   counts and ``auto_rerun`` for instrument/environment (DF-017 §2.4: automated
   re-runs only for those two classes, after their fix, and ledgered).

4. **ST-09 revisions.** :func:`revise_attribution` appends an
   :class:`AttributionRevision` (prior → corrected) and updates the current
   attribution — a same-day correction, never a silent overwrite. The
   study-tutor GPU-eviction confound (a deadline spike first read as backend
   latency, corrected to ``environment`` by a quiet-GPU controlled rerun) is the
   worked example.

Deterministic: no clock, no model calls. Dates are passed in by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, Optional, Sequence

from guardkit.qa.formats.disposition_record import (
    Attribution,
    AttributionRevision,
    Disposition,
    DispositionRecord,
    FailureDisposition,
)
from guardkit.qa.formats.gate_registry import GateResult, SweepResult

from guardkit.orchestrator.live_gate.errors import LiveGateError

#: The wire-level collapse (backward-edge §7 item 7 / nats-core 0.7.0).
WireDisposition = Literal["counts", "instrument", "environment"]

#: Routing outcome for a red (DF-017 §2): a red that counts against the feature
#: is routed to a fix owner and notified — NEVER silently retried. Only an
#: instrument/environment red is a candidate for an automated rerun after fix.
Routing = Literal["route_and_notify", "auto_rerun"]

#: The three attribution classes that count against the feature (DF-017).
_COUNTS_AGAINST_FEATURE: frozenset[str] = frozenset(("app", "backend", "contract_gap"))


class UndispositionedRedError(LiveGateError):
    """A run was asked to close while one or more reds had no disposition.

    DF-017 §2.1: a red without a disposition is an UNCLOSED run. The message
    names every offending ``failure_id`` so the arbiter knows exactly what to
    bin.
    """


@dataclass(frozen=True)
class Red:
    """One observed red that must be dispositioned before the run can close."""

    failure_id: str
    assertion: str
    kind: Literal["assertion", "sweep_leak"]
    observed: Optional[str] = None
    expected: Optional[str] = None
    evidence_ref: Optional[str] = None


def _assertion_failure_id(gate_id: str, assertion_id: str) -> str:
    return f"{gate_id}:{assertion_id}"


def _sweep_failure_id(leak: str) -> str:
    return f"sweep:{leak}"


def iter_reds(
    gate_results: Sequence[GateResult],
    sweep_result: Optional[SweepResult] = None,
) -> List[Red]:
    """Enumerate every red a run must bin (pure).

    A red is a failed assertion (``status == "fail"``) or a sweep leak. Gate
    exit codes are not a separate red — the executor already appends a synthetic
    ``<gate>::exit`` FAIL assertion when a non-zero exit enumerated no failing
    assertion (absence-of-failure defense), so walking failed assertions covers
    the exit-code case without double-counting.
    """
    reds: List[Red] = []
    for gate in gate_results:
        for assertion in gate.assertions:
            if assertion.status != "fail":
                continue
            reds.append(
                Red(
                    failure_id=_assertion_failure_id(gate.gate_id, assertion.id),
                    assertion=assertion.id,
                    kind="assertion",
                    observed=assertion.observed,
                    expected=assertion.expected,
                    evidence_ref=assertion.evidence_ref,
                )
            )
    if sweep_result is not None:
        for leak in sweep_result.leaks:
            reds.append(
                Red(
                    failure_id=_sweep_failure_id(leak),
                    assertion=leak,
                    kind="sweep_leak",
                )
            )
    return reds


def undispositioned_reds(
    reds: Sequence[Red],
    record: Optional[DispositionRecord],
) -> List[Red]:
    """Return the reds that carry no disposition in ``record`` (pure)."""
    dispositioned = set()
    if record is not None:
        dispositioned = {f.failure_id for f in record.failures}
    return [r for r in reds if r.failure_id not in dispositioned]


def assert_run_closed(
    reds: Sequence[Red],
    record: Optional[DispositionRecord],
) -> None:
    """DF-017 §2.1 gate: raise unless every red is dispositioned.

    Raises:
        UndispositionedRedError: at least one red has no F8 disposition. The run
            is UNCLOSED — never silently a pass.
    """
    missing = undispositioned_reds(reds, record)
    if missing:
        ids = ", ".join(r.failure_id for r in missing)
        raise UndispositionedRedError(
            f"cannot close run: {len(missing)} red(s) have no disposition "
            f"[{ids}]. DF-017 §2.1 — a red without a disposition is an UNCLOSED "
            f"run; bin each against the seam's arbiter before closing."
        )


def wire_disposition(attribution: Attribution) -> WireDisposition:
    """Collapse an attribution class onto the nats-core wire value.

    ``counts ⇐ {app, backend, contract_gap}``; ``instrument ⇐ instrument``;
    ``environment ⇐ environment`` (backward-edge §7 item 7).
    """
    if attribution in _COUNTS_AGAINST_FEATURE:
        return "counts"
    # attribution is 'instrument' or 'environment' here (exhaustive over the enum)
    return attribution  # type: ignore[return-value]


def counts_against_feature(attribution: Attribution) -> bool:
    """DF-017 invariant: only app/backend/contract_gap count against the feature.

    ``instrument`` and ``environment`` NEVER do — they indict the tool or the
    environment, not the system under test.
    """
    return attribution in _COUNTS_AGAINST_FEATURE


def routing_for(attribution: Attribution) -> Routing:
    """DF-017 §2: route-and-notify a counts-class red; only instrument/environment
    reds are eligible for an automated rerun (after their fix, and ledgered).

    Never returns ``auto_rerun`` for a counts-class red — a feature defect is
    routed to a fix owner, never silently retried.
    """
    return "route_and_notify" if counts_against_feature(attribution) else "auto_rerun"


def revise_attribution(
    failure: FailureDisposition,
    *,
    corrected_to: Attribution,
    evidence: str,
    date: str,
) -> FailureDisposition:
    """Return a copy of ``failure`` with an ST-09 revision appended.

    The prior attribution is recorded and the current attribution is updated —
    a same-day correction with evidence, never a silent overwrite. Idempotent in
    spirit: a no-op correction (``corrected_to == current``) still records the
    revision so the audit trail shows it was reconsidered.
    """
    revision = AttributionRevision(
        date=date,
        prior_attribution=failure.attribution,
        corrected_to=corrected_to,
        evidence=evidence,
    )
    return failure.model_copy(
        update={
            "attribution": corrected_to,
            "revisions": [*failure.revisions, revision],
        }
    )


def build_disposition_record(
    run_id: str,
    failures: Iterable[FailureDisposition],
) -> DispositionRecord:
    """Assemble the F8 record for a run from its binned failures."""
    return DispositionRecord(
        format_version=DispositionRecord.CURRENT_FORMAT_VERSION,
        run_id=run_id,
        failures=list(failures),
    )


def dispositions_by_id(record: Optional[DispositionRecord]) -> Dict[str, FailureDisposition]:
    """Index an F8 record's failures by ``failure_id`` (pure)."""
    if record is None:
        return {}
    return {f.failure_id: f for f in record.failures}


def make_disposition(
    failure_id: str,
    assertion: str,
    attribution: Attribution,
    disposition: Disposition,
    *,
    observed: Optional[str] = None,
    expected: Optional[str] = None,
    evidence_ref: Optional[str] = None,
    fix_ref: Optional[str] = None,
    rescope_rationale: Optional[str] = None,
) -> FailureDisposition:
    """Thin constructor for a :class:`FailureDisposition` (keeps callers tidy)."""
    return FailureDisposition(
        failure_id=failure_id,
        assertion=assertion,
        attribution=attribution,
        disposition=disposition,
        observed=observed,
        expected=expected,
        evidence_ref=evidence_ref,
        fix_ref=fix_ref,
        rescope_rationale=rescope_rationale,
    )
