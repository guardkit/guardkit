"""Envelope verdict assembly with attribution (WS2 session B4).

B3's :func:`guardkit.orchestrator.live_gate.runner.derive_verdict` gives a
DETERMINISTIC per-run verdict from raw gate results — a red is ``fail``, full
stop. B4 enriches that verdict with **attribution**: once every red is binned
(F8), a run whose reds are ALL instrument/environment is not a feature failure —
it is ``instrument_fail`` / ``environment_fail``, which per DF-017 never count
against the feature. This module is where ``instrument_fail`` / ``environment_fail``
become first-class *post-attribution* verdicts (B3 only produced them from
pre-flight short-circuits).

The precedence, over a closed run's reds (documented, deterministic):

    counts (app|backend|contract_gap)  -> fail          (a real feature defect wins)
    else any environment               -> environment_fail
    else any instrument                -> instrument_fail
    no reds                            -> pass  (or environment_fail if a
                                                 surface sweep could not run)

``environment`` takes precedence over ``instrument`` when a run's reds are mixed
across only those two classes: a bad environment can masquerade as an instrument
fault, so the broader "not-ready" verdict is the safer report — either way the
feature is not indicted and the run is re-run after the fix (DF-017 §2.4).

:func:`enrich_envelope` snaps onto a B3-emitted envelope: it re-derives the
verdict from the envelope's own reds + the F8 disposition record and sets
``dispositions_ref``. A pre-flight short-circuit envelope (no gates ran) and a
clean pass are passed through untouched — there is nothing to re-attribute.
"""

from __future__ import annotations

from typing import Literal, Optional, Sequence

from guardkit.qa.formats.disposition_record import DispositionRecord
from guardkit.qa.formats.gate_registry import GateResult, ResultsEnvelope, SweepResult

from guardkit.orchestrator.live_gate.disposition import (
    Red,
    assert_run_closed,
    counts_against_feature,
    dispositions_by_id,
    iter_reds,
)

Verdict = Literal["pass", "fail", "instrument_fail", "environment_fail"]


def assemble_run_verdict(
    reds: Sequence[Red],
    record: Optional[DispositionRecord],
    *,
    preflight_classification: Optional[Literal["instrument_fail", "environment_fail"]] = None,
    sweep_unavailable: bool = False,
) -> Verdict:
    """Assemble the attribution-aware verdict for one closed run (pure).

    Enforces DF-017 §2.1 first: an undispositioned red raises
    ``UndispositionedRedError`` — a run with unbinned reds cannot yield a verdict
    at all (never a silent pass).

    Raises:
        UndispositionedRedError: a red has no disposition in ``record``.
    """
    if preflight_classification is not None:
        # A pre-flight short-circuit was never exercised — attribution N/A.
        return preflight_classification

    assert_run_closed(reds, record)

    if not reds:
        return "environment_fail" if sweep_unavailable else "pass"

    by_id = dispositions_by_id(record)
    saw_environment = False
    saw_instrument = False
    for red in reds:
        attribution = by_id[red.failure_id].attribution
        if counts_against_feature(attribution):
            return "fail"  # a real feature defect wins outright
        if attribution == "environment":
            saw_environment = True
        elif attribution == "instrument":
            saw_instrument = True

    if saw_environment:
        return "environment_fail"
    if saw_instrument:
        return "instrument_fail"
    # Unreachable: every attribution is counts | environment | instrument, and
    # a counts red returned above. Defensive: treat as fail (never a silent pass).
    return "fail"


def enrich_envelope(
    envelope: ResultsEnvelope,
    record: Optional[DispositionRecord],
    *,
    dispositions_ref: Optional[str] = None,
) -> ResultsEnvelope:
    """Return a copy of a B3 envelope with an attribution-aware verdict + F8 ref.

    - A pre-flight short-circuit (no gates ran, verdict already
      instrument_fail/environment_fail) is passed through untouched — it was
      never exercised, so there is nothing to attribute.
    - A clean run with no reds is passed through untouched (verdict stays pass /
      environment_fail-from-unavailable-sweep; ``dispositions_ref`` stays None —
      an empty F8 record would be dishonest to reference).
    - A run with reds is re-verdicted through :func:`assemble_run_verdict` (which
      enforces DF-017 §2.1 closure) and gets ``dispositions_ref`` set.

    Raises:
        UndispositionedRedError: the envelope has reds but ``record`` does not
            bin them all.
    """
    reds = iter_reds(envelope.gates, envelope.sweep)
    if not reds:
        # Nothing to re-attribute (pass, or a pre-flight short-circuit). Preserve
        # the B3 verdict and leave dispositions_ref null.
        return envelope

    new_verdict = assemble_run_verdict(reds, record)
    return envelope.model_copy(
        update={
            "verdict": new_verdict,
            "dispositions_ref": dispositions_ref,
        }
    )


def _reds_from_results(
    gate_results: Sequence[GateResult],
    sweep_result: Optional[SweepResult],
) -> list[Red]:
    """Convenience: reds directly from raw results (for callers without an envelope)."""
    return iter_reds(gate_results, sweep_result)
