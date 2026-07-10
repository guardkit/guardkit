"""Phase 6 Finalize decision — tri-state routing + carve-outs (demotion scope §2, DF-018).

The NORMATIVE, deterministic reference for task-work.md § Phase 6's decision:
whether an IN_REVIEW task auto-completes (Green), pauses (Amber), is blocked (Red),
or is skipped (opt-in off / a carve-out applies). Pure and unit-tested so the
carve-outs and tri-state cannot silently drift — the markdown Phase 6 follows
this algorithm, and :func:`carveout_refusal` is the shared carve-out check the
``guardkit task complete`` CLI enforces at the GREEN action.

The verdicts:

- ``GREEN`` — deterministic audit clean + review clean → auto-complete via
  ``guardkit task complete``; the human is *notified, not gated* (verify-then-
  record banner).
- ``AMBER`` — any non-clean audit / review concern, or ``--pause`` → stay at
  IN_REVIEW with specifics (today's behaviour).
- ``RED``   — BLOCKED.
- ``SKIP``  — Phase 6 does not run: ``--complete`` not passed (opt-in), the task
  did not legitimately reach IN_REVIEW, or a carve-out applies (autobuild /
  operator_handoff).

Carve-outs (scope §2, §3) are HARD — they win over the tri-state so an autobuild
or operator_handoff task can never be auto-finalized here:

- NEVER in ``--autobuild-mode``: feature-build merges BEFORE completion; the
  autobuild lane finalizes via feature-complete calling the shared routine
  post-merge (the guard metric — no completion for an unmerged branch).
- NEVER for ``task_type: operator_handoff``: those tasks never run task-work;
  their completion path is feature-complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

__all__ = [
    "SKIP",
    "GREEN",
    "AMBER",
    "RED",
    "FinalizeDecision",
    "carveout_refusal",
    "decide_finalize",
]

# Verdict constants (string-valued so callers/logs read plainly).
SKIP = "skip"
GREEN = "green"
AMBER = "amber"
RED = "red"

_OPERATOR_HANDOFF = "operator_handoff"


def carveout_refusal(
    *,
    autobuild_mode: bool,
    task_type: Optional[str],
    allow_operator_handoff: bool = False,
) -> Optional[str]:
    """Return a refusal reason if a HARD Phase-6 carve-out forbids finalize, else None.

    Shared by :func:`decide_finalize` (which turns a refusal into a ``SKIP``
    verdict) and by the ``guardkit task complete`` CLI (which refuses the run).
    ``allow_operator_handoff`` is the explicit override the deferred manual /
    feature-complete completion path passes to legitimately complete an
    operator_handoff task via the shared routine.
    """
    if autobuild_mode:
        return (
            "autobuild mode: feature-build merges BEFORE completion; the autobuild "
            "lane finalizes via feature-complete calling the shared routine "
            "post-merge (never auto-complete an unmerged branch)"
        )
    if (task_type or "").strip().lower() == _OPERATOR_HANDOFF and not allow_operator_handoff:
        return (
            "task_type: operator_handoff — those tasks never run task-work; their "
            "completion path is feature-complete (pass allow_operator_handoff for "
            "the deferred manual completion)"
        )
    return None


@dataclass(frozen=True)
class FinalizeDecision:
    """The Phase 6 verdict + a human-readable reason."""

    verdict: str
    reason: str

    @property
    def should_complete(self) -> bool:
        """True only for GREEN — the sole verdict that invokes the shared routine."""
        return self.verdict == GREEN


def decide_finalize(
    *,
    complete_flag: bool,
    pause_flag: bool,
    autobuild_mode: bool,
    task_type: Optional[str],
    reached_in_review: bool,
    audit_clean: bool,
    review_clean: bool,
    blocked: bool = False,
) -> FinalizeDecision:
    """Compute the Phase 6 verdict.

    Order of precedence (demotion scope §2):

    1. reached-IN_REVIEW gate — Phase 6 only runs when Step 6 routed the task to
       IN_REVIEW via Phases 4/4.5/5/5.5 (the only path);
    2. HARD carve-outs (autobuild / operator_handoff) → SKIP;
    3. opt-in — ``--complete`` must be set → else SKIP;
    4. RED (blocked) wins over the pause/green split;
    5. ``--pause`` / ``--no-complete`` → AMBER;
    6. audit clean + review clean → GREEN, otherwise AMBER.
    """
    if not reached_in_review:
        return FinalizeDecision(
            SKIP,
            "task did not reach IN_REVIEW via Phases 4/4.5/5/5.5 — the only path to finalize",
        )

    refusal = carveout_refusal(autobuild_mode=autobuild_mode, task_type=task_type)
    if refusal:
        return FinalizeDecision(SKIP, refusal)

    if not complete_flag:
        return FinalizeDecision(
            SKIP,
            "--complete not passed — Phase 6 is opt-in in rollout phase 2 (the default "
            "flips to auto-complete-on-green later, after the §6 metric window)",
        )

    if blocked:
        return FinalizeDecision(RED, "BLOCKED — red evidence; task is not completable")

    if pause_flag:
        return FinalizeDecision(
            AMBER, "--pause / --no-complete: forced pause at IN_REVIEW"
        )

    if audit_clean and review_clean:
        return FinalizeDecision(
            GREEN,
            "deterministic audit clean + review clean — auto-complete on green "
            "(human notified, not gated)",
        )

    return FinalizeDecision(
        AMBER,
        "non-clean audit or review concerns — pause at IN_REVIEW with specifics",
    )
