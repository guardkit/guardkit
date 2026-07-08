"""LPA-06 · async-poller progressing/stuck/failed classifier (WS2 session B3).

Scope-design §3 step 4: "watches the same UI the user watches, honest deadline,
mid-flight screenshot, must classify progressing/stuck/failed; a system that can
stall silently is itself a finding."

This module is the *classifier* — the pure, deterministic core. It takes an
ordered series of observations of one watched operation and returns one of the
three LPA-06 classifications. It does NOT drive a browser or take screenshots
(that is the live seam supplied by the gate execution context / walk driver);
keeping the classification pure makes every branch unit-testable offline, which
the B3 gate requires.

Determinism (DF-015 clause 1): no wall-clock reads, no model calls. Every input
that matters — elapsed time, progress signal, done/failed flags, the deadline,
the stall window — is passed in. The caller samples the real operation and hands
the samples here.

Classification (evaluated over the ordered samples):

  failed      an explicit failure was observed, OR the operation overran its
              honest deadline without completing (a silent overrun IS a finding
              — the deadline is the hard stop, not a suggestion).
  stuck       within the deadline, not complete, and the progress signal has
              not advanced for at least ``stall_window_s`` (alive but stalled —
              the LPA-06 "stalls silently" finding, surfaced as a classification
              rather than an infinite wait).
  progressing advancing within the stall window, or reached terminal success
              (``done``) — the only healthy outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Literal, Optional, Sequence

Classification = Literal["progressing", "stuck", "failed"]


@dataclass(frozen=True)
class PollSample:
    """One observation of a watched operation.

    ``elapsed_s`` is seconds since the operation started (monotonic, supplied by
    the caller — the classifier never reads a clock). ``progress`` is any
    comparable progress signal (a percentage, a step index, a status string, a
    row count); equality is all the classifier needs — an unchanged value across
    the stall window is a stall. ``done``/``failed`` are terminal signals.
    """

    elapsed_s: float
    progress: Optional[Any] = None
    done: bool = False
    failed: bool = False


def classify_operation(
    samples: Sequence[PollSample],
    *,
    deadline_s: float,
    stall_window_s: float,
) -> Classification:
    """Classify one watched operation from its ordered observations.

    Args:
        samples: observations in time order (ascending ``elapsed_s``). Must be
            non-empty — classifying an operation nobody observed is not
            meaningful (an unobserved operation is the walk driver's
            "unobserved step = failed step", handled there, not silently
            defaulted here).
        deadline_s: the honest deadline. Reaching it without completing is a
            failure, never merely "stuck".
        stall_window_s: how long the progress signal may stay unchanged (while
            alive and within the deadline) before the operation is "stuck".

    Raises:
        ValueError: empty ``samples``, or a non-positive ``deadline_s`` /
            negative ``stall_window_s`` (a zero/negative deadline or a negative
            window is a caller misconfiguration, not a classification).
    """
    ordered: List[PollSample] = list(samples)
    if not ordered:
        raise ValueError(
            "classify_operation: samples is empty — an operation nobody "
            "observed cannot be classified (provide at least one PollSample)"
        )
    if deadline_s <= 0:
        raise ValueError(f"deadline_s must be positive, got {deadline_s!r}")
    if stall_window_s < 0:
        raise ValueError(f"stall_window_s must be non-negative, got {stall_window_s!r}")

    # 1. Explicit failure anywhere wins — a witnessed failure is a failure.
    if any(s.failed for s in ordered):
        return "failed"

    latest = ordered[-1]

    # 2. Terminal success — reached completion, healthy.
    if latest.done:
        return "progressing"

    # 3. Deadline blown without completing — the hard stop (silent overrun is a
    #    finding, classified failed, not stuck).
    if latest.elapsed_s >= deadline_s:
        return "failed"

    # 4. Alive and within the deadline: has progress advanced recently?
    last_change_elapsed = ordered[0].elapsed_s
    prev_progress = ordered[0].progress
    for sample in ordered[1:]:
        if sample.progress != prev_progress:
            last_change_elapsed = sample.elapsed_s
            prev_progress = sample.progress
    stalled_span = latest.elapsed_s - last_change_elapsed
    if stalled_span >= stall_window_s:
        return "stuck"
    return "progressing"
