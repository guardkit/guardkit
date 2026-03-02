"""Adaptive concurrency controller for AutoBuild wave execution.

Monitors wave completion events (rate limits, p95 latency) and adjusts
worker count to prevent cascading failures while maximising throughput.

Policy:
    1. Rate limit detected (count > 0) → reduce concurrency by 50%
    2. p95 latency > threshold above baseline → reduce concurrency by 50%
    3. Stability period with no issues → recover +1 worker
    4. Floor: 1 worker; ceiling: initial configured value

Integration:
    Injected into FeatureOrchestrator; consulted after each wave to
    determine the next wave's worker count.

Example:
    >>> from guardkit.orchestrator.instrumentation.concurrency import (
    ...     ConcurrencyController,
    ... )
    >>> ctrl = ConcurrencyController(initial_workers=8)
    >>> ctrl.current_workers
    8
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Literal, Optional

from guardkit.orchestrator.instrumentation.schemas import WaveCompletedEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass
class ConcurrencyDecision:
    """Result of a concurrency adaptation evaluation.

    Attributes:
        action: Whether to maintain, reduce, or increase worker count.
        new_workers: The recommended worker count for the next wave.
        reason: Human-readable explanation for the decision.
    """

    action: Literal["maintain", "reduce", "increase"]
    new_workers: int
    reason: str


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class ConcurrencyController:
    """Adaptive concurrency controller driven by wave completion events.

    Monitors ``WaveCompletedEvent`` signals and produces
    ``ConcurrencyDecision`` objects that tell the orchestrator how many
    workers to allocate for the next wave.

    Args:
        initial_workers: Starting (and maximum) number of concurrent workers.
        p95_threshold_pct: Percentage *above* the baseline p95 latency that
            triggers a reduction.  Default ``100.0`` means 2x the baseline.
        stability_minutes: Minutes of rate-limit-free operation required
            before recovering a worker.
    """

    def __init__(
        self,
        initial_workers: int,
        p95_threshold_pct: float = 100.0,
        stability_minutes: float = 5.0,
    ) -> None:
        self._initial_workers = initial_workers
        self._current_workers = initial_workers
        self._p95_threshold_pct = p95_threshold_pct
        self._stability_minutes = stability_minutes

        # Baseline latency — established from the first wave with p95 data
        self._baseline_p95: Optional[float] = None

        # Timestamp of last rate-limit event (monotonic clock)
        self._last_rate_limit_time: Optional[float] = None

        # Whether a reduction has occurred (needed for recovery eligibility)
        self._reduced = False

    # -- Public API ---------------------------------------------------------

    @property
    def current_workers(self) -> int:
        """Current number of workers the controller recommends."""
        return self._current_workers

    def on_wave_completed(self, event: WaveCompletedEvent) -> ConcurrencyDecision:
        """Process a wave completion event and return a concurrency decision.

        Evaluation order (first matching rule wins):
            1. Rate-limit reduction (``rate_limit_count > 0``)
            2. Latency-based reduction (p95 exceeds threshold above baseline)
            3. Recovery increase (stability window elapsed, below ceiling)
            4. Maintain current level

        Args:
            event: The wave completion event with metrics.

        Returns:
            A ``ConcurrencyDecision`` describing the action to take.
        """
        decision = self._evaluate(event)
        self._apply(decision)
        self._log_decision(event, decision)
        return decision

    # -- Private Evaluation -------------------------------------------------

    def _evaluate(self, event: WaveCompletedEvent) -> ConcurrencyDecision:
        """Core decision logic — pure evaluation, no side-effects."""

        # Rule 1: Rate-limit reduction
        if event.rate_limit_count > 0:
            new = max(1, self._current_workers // 2)
            return ConcurrencyDecision(
                action="reduce" if new < self._current_workers else "maintain",
                new_workers=new,
                reason=(
                    f"Rate limit detected ({event.rate_limit_count} events); "
                    f"reducing workers from {self._current_workers} to {new}"
                    if new < self._current_workers
                    else (
                        f"Rate limit detected ({event.rate_limit_count} events) "
                        f"but already at minimum ({self._current_workers} worker)"
                    )
                ),
            )

        # Rule 2: Latency-based reduction
        if event.p95_task_latency_ms is not None:
            if self._baseline_p95 is None:
                # First wave with latency data → establish baseline
                self._baseline_p95 = event.p95_task_latency_ms
            else:
                threshold = self._baseline_p95 * (
                    1.0 + self._p95_threshold_pct / 100.0
                )
                if event.p95_task_latency_ms > threshold:
                    new = max(1, self._current_workers // 2)
                    return ConcurrencyDecision(
                        action="reduce" if new < self._current_workers else "maintain",
                        new_workers=new,
                        reason=(
                            f"p95 latency {event.p95_task_latency_ms:.0f}ms exceeds "
                            f"threshold {threshold:.0f}ms (baseline {self._baseline_p95:.0f}ms); "
                            f"reducing workers from {self._current_workers} to {new}"
                        ),
                    )

        # Rule 3: Recovery increase
        if self._reduced and self._current_workers < self._initial_workers:
            if self._is_stability_elapsed():
                new = min(self._current_workers + 1, self._initial_workers)
                return ConcurrencyDecision(
                    action="increase",
                    new_workers=new,
                    reason=(
                        f"Stability window elapsed; recovering workers "
                        f"from {self._current_workers} to {new}"
                    ),
                )

        # Rule 4: Maintain
        return ConcurrencyDecision(
            action="maintain",
            new_workers=self._current_workers,
            reason="No adaptation needed; maintaining current concurrency",
        )

    def _apply(self, decision: ConcurrencyDecision) -> None:
        """Apply the decision to internal state."""
        now = time.monotonic()

        if decision.action == "reduce":
            self._current_workers = decision.new_workers
            self._last_rate_limit_time = now
            self._reduced = True
        elif decision.action == "increase":
            self._current_workers = decision.new_workers
            # Reset rate-limit timer on recovery (stability continues)
            if self._current_workers >= self._initial_workers:
                self._reduced = False
        # "maintain" → no state change needed

    def _is_stability_elapsed(self) -> bool:
        """Check whether the stability window has passed since last issue."""
        if self._last_rate_limit_time is None:
            return False
        elapsed_seconds = time.monotonic() - self._last_rate_limit_time
        required_seconds = self._stability_minutes * 60.0
        return elapsed_seconds >= required_seconds

    # -- Logging ------------------------------------------------------------

    @staticmethod
    def _log_decision(
        event: WaveCompletedEvent, decision: ConcurrencyDecision
    ) -> None:
        """Log the concurrency decision for observability."""
        logger.info(
            "Concurrency decision for wave %s: action=%s, workers=%d — %s",
            event.wave_id,
            decision.action,
            decision.new_workers,
            decision.reason,
        )
