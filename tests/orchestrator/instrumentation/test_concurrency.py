"""Tests for adaptive concurrency controller.

TDD test suite covering all acceptance criteria and boundary conditions
for ConcurrencyController:

- AC-001: Rate limit count > 0 triggers 50% concurrency reduction
- AC-002: p95 latency above threshold triggers concurrency reduction
- AC-003: p95 just below threshold does not trigger reduction
- AC-004: Recovery increases by +1 after stability period
- AC-005: Zero rate limit count triggers no adaptation
- AC-006: Minimum concurrency is 1 worker
- AC-007: Maximum concurrency is original configured value
- AC-008: ConcurrencyController integrates with FeatureOrchestrator
- AC-009: Concurrency decisions logged
- AC-010: Unit tests cover all boundary conditions
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict
from typing import Optional
from unittest.mock import patch

import pytest

from guardkit.orchestrator.instrumentation.concurrency import (
    ConcurrencyController,
    ConcurrencyDecision,
)
from guardkit.orchestrator.instrumentation.schemas import WaveCompletedEvent


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def _make_wave_event(
    *,
    wave_id: str = "wave-1",
    worker_count: int = 4,
    rate_limit_count: int = 0,
    p95_task_latency_ms: Optional[float] = None,
    tasks_completed: int = 3,
    task_failures: int = 0,
    queue_depth_start: int = 10,
    queue_depth_end: int = 7,
) -> WaveCompletedEvent:
    """Helper to create a WaveCompletedEvent with sensible defaults."""
    return WaveCompletedEvent(
        run_id="run-test-001",
        task_id="TASK-TEST-001",
        agent_role="player",
        attempt=1,
        timestamp="2026-03-02T12:00:00Z",
        wave_id=wave_id,
        worker_count=worker_count,
        queue_depth_start=queue_depth_start,
        queue_depth_end=queue_depth_end,
        tasks_completed=tasks_completed,
        task_failures=task_failures,
        rate_limit_count=rate_limit_count,
        p95_task_latency_ms=p95_task_latency_ms,
    )


# ===========================================================================
# ConcurrencyDecision Dataclass Tests
# ===========================================================================


class TestConcurrencyDecision:
    """Tests for the ConcurrencyDecision dataclass."""

    def test_create_maintain_decision(self) -> None:
        decision = ConcurrencyDecision(
            action="maintain", new_workers=4, reason="No issues detected"
        )
        assert decision.action == "maintain"
        assert decision.new_workers == 4
        assert decision.reason == "No issues detected"

    def test_create_reduce_decision(self) -> None:
        decision = ConcurrencyDecision(
            action="reduce", new_workers=2, reason="Rate limits detected"
        )
        assert decision.action == "reduce"
        assert decision.new_workers == 2

    def test_create_increase_decision(self) -> None:
        decision = ConcurrencyDecision(
            action="increase", new_workers=5, reason="Stability achieved"
        )
        assert decision.action == "increase"
        assert decision.new_workers == 5

    def test_asdict_serialization(self) -> None:
        decision = ConcurrencyDecision(
            action="reduce", new_workers=2, reason="Rate limited"
        )
        data = asdict(decision)
        assert data == {
            "action": "reduce",
            "new_workers": 2,
            "reason": "Rate limited",
        }


# ===========================================================================
# AC-001: Rate Limit Triggers 50% Reduction
# ===========================================================================


class TestRateLimitReduction:
    """AC-001: Rate limit count > 0 triggers 50% concurrency reduction."""

    def test_rate_limit_count_1_triggers_reduction(self) -> None:
        """Boundary: count of 1 triggers reduction."""
        ctrl = ConcurrencyController(initial_workers=4)
        event = _make_wave_event(rate_limit_count=1, p95_task_latency_ms=1000.0)
        decision = ctrl.on_wave_completed(event)
        assert decision.action == "reduce"
        assert decision.new_workers == 2  # 4 * 0.5 = 2

    def test_rate_limit_count_many_triggers_reduction(self) -> None:
        """Multiple rate limits still trigger 50% reduction."""
        ctrl = ConcurrencyController(initial_workers=8)
        event = _make_wave_event(rate_limit_count=10, p95_task_latency_ms=1000.0)
        decision = ctrl.on_wave_completed(event)
        assert decision.action == "reduce"
        assert decision.new_workers == 4  # 8 * 0.5 = 4

    def test_rate_limit_reduction_rounds_down(self) -> None:
        """Odd worker counts: 50% reduction rounds down."""
        ctrl = ConcurrencyController(initial_workers=5)
        event = _make_wave_event(rate_limit_count=1, p95_task_latency_ms=1000.0)
        decision = ctrl.on_wave_completed(event)
        assert decision.action == "reduce"
        assert decision.new_workers == 2  # floor(5 * 0.5) = 2

    def test_rate_limit_on_already_reduced_workers(self) -> None:
        """Successive rate limits keep halving."""
        ctrl = ConcurrencyController(initial_workers=8)
        # First reduction: 8 -> 4
        event1 = _make_wave_event(
            wave_id="w1", rate_limit_count=1, p95_task_latency_ms=1000.0
        )
        d1 = ctrl.on_wave_completed(event1)
        assert d1.new_workers == 4

        # Second reduction: 4 -> 2
        event2 = _make_wave_event(
            wave_id="w2",
            worker_count=4,
            rate_limit_count=1,
            p95_task_latency_ms=1000.0,
        )
        d2 = ctrl.on_wave_completed(event2)
        assert d2.new_workers == 2

    def test_rate_limit_reason_includes_count(self) -> None:
        """Decision reason should mention rate limits."""
        ctrl = ConcurrencyController(initial_workers=4)
        event = _make_wave_event(rate_limit_count=3, p95_task_latency_ms=1000.0)
        decision = ctrl.on_wave_completed(event)
        assert "rate" in decision.reason.lower()


# ===========================================================================
# AC-002: p95 Latency Above Threshold Triggers Reduction
# ===========================================================================


class TestLatencyReduction:
    """AC-002: p95 latency above threshold triggers concurrency reduction."""

    def test_latency_above_2x_baseline_triggers_reduction(self) -> None:
        """Default threshold: 2x baseline (100% increase)."""
        ctrl = ConcurrencyController(initial_workers=4)
        # First wave establishes baseline
        baseline_event = _make_wave_event(
            wave_id="w1", p95_task_latency_ms=5000.0
        )
        d1 = ctrl.on_wave_completed(baseline_event)
        assert d1.action == "maintain"

        # Second wave: latency > 2x baseline (10001 > 10000)
        high_latency_event = _make_wave_event(
            wave_id="w2", p95_task_latency_ms=10001.0
        )
        d2 = ctrl.on_wave_completed(high_latency_event)
        assert d2.action == "reduce"
        assert d2.new_workers == 2  # 4 * 0.5 = 2

    def test_custom_threshold_percentage(self) -> None:
        """Custom p95_threshold_pct respected."""
        ctrl = ConcurrencyController(initial_workers=4, p95_threshold_pct=50.0)
        # Baseline: 1000ms, threshold: 1500ms (50% above)
        baseline_event = _make_wave_event(
            wave_id="w1", p95_task_latency_ms=1000.0
        )
        ctrl.on_wave_completed(baseline_event)

        # 1501ms > 1500ms threshold → reduction
        high_event = _make_wave_event(
            wave_id="w2", p95_task_latency_ms=1501.0
        )
        d = ctrl.on_wave_completed(high_event)
        assert d.action == "reduce"

    def test_latency_reduction_reason_mentions_latency(self) -> None:
        """Reason mentions latency."""
        ctrl = ConcurrencyController(initial_workers=4)
        baseline = _make_wave_event(wave_id="w1", p95_task_latency_ms=5000.0)
        ctrl.on_wave_completed(baseline)

        high = _make_wave_event(wave_id="w2", p95_task_latency_ms=10001.0)
        d = ctrl.on_wave_completed(high)
        assert "latency" in d.reason.lower()


# ===========================================================================
# AC-003: p95 Just Below Threshold Does Not Trigger
# ===========================================================================


class TestLatencyBelowThreshold:
    """AC-003: p95 just below threshold does not trigger reduction."""

    def test_latency_exactly_at_threshold_no_reduction(self) -> None:
        """Exactly at threshold (10000ms when baseline 5000ms): no reduction."""
        ctrl = ConcurrencyController(initial_workers=4)
        baseline = _make_wave_event(wave_id="w1", p95_task_latency_ms=5000.0)
        ctrl.on_wave_completed(baseline)

        at_threshold = _make_wave_event(
            wave_id="w2", p95_task_latency_ms=10000.0
        )
        d = ctrl.on_wave_completed(at_threshold)
        assert d.action == "maintain"

    def test_latency_just_below_threshold_no_reduction(self) -> None:
        """9999ms < 10000ms threshold → no reduction."""
        ctrl = ConcurrencyController(initial_workers=4)
        baseline = _make_wave_event(wave_id="w1", p95_task_latency_ms=5000.0)
        ctrl.on_wave_completed(baseline)

        below = _make_wave_event(wave_id="w2", p95_task_latency_ms=9999.0)
        d = ctrl.on_wave_completed(below)
        assert d.action == "maintain"

    def test_no_latency_data_no_reduction(self) -> None:
        """p95_task_latency_ms=None → no latency-based decision."""
        ctrl = ConcurrencyController(initial_workers=4)
        event = _make_wave_event(p95_task_latency_ms=None)
        d = ctrl.on_wave_completed(event)
        assert d.action == "maintain"

    def test_first_wave_establishes_baseline_no_reduction(self) -> None:
        """First wave establishes baseline; cannot trigger latency reduction."""
        ctrl = ConcurrencyController(initial_workers=4)
        event = _make_wave_event(
            wave_id="w1", p95_task_latency_ms=50000.0
        )
        d = ctrl.on_wave_completed(event)
        # First wave: no baseline yet, so maintain
        assert d.action == "maintain"


# ===========================================================================
# AC-004: Recovery Increases by +1 After Stability
# ===========================================================================


class TestRecoveryIncrease:
    """AC-004: Recovery increases by +1 after stability period."""

    def test_recovery_after_stability_window(self) -> None:
        """After 5 min with no rate limits, +1 worker."""
        ctrl = ConcurrencyController(initial_workers=4, stability_minutes=0.0)
        # Force reduce first
        event1 = _make_wave_event(
            wave_id="w1", rate_limit_count=1, p95_task_latency_ms=1000.0
        )
        d1 = ctrl.on_wave_completed(event1)
        assert d1.action == "reduce"
        assert d1.new_workers == 2

        # Now a clean wave after stability window (0 min = immediate)
        event2 = _make_wave_event(
            wave_id="w2", rate_limit_count=0, p95_task_latency_ms=1000.0
        )
        d2 = ctrl.on_wave_completed(event2)
        assert d2.action == "increase"
        assert d2.new_workers == 3  # 2 + 1

    def test_recovery_with_real_stability_window(self) -> None:
        """Stability window not yet elapsed prevents recovery."""
        ctrl = ConcurrencyController(
            initial_workers=4, stability_minutes=10.0
        )
        # Reduce
        event1 = _make_wave_event(
            wave_id="w1", rate_limit_count=1, p95_task_latency_ms=1000.0
        )
        d1 = ctrl.on_wave_completed(event1)
        assert d1.new_workers == 2

        # Immediately after - stability window not elapsed
        event2 = _make_wave_event(
            wave_id="w2", rate_limit_count=0, p95_task_latency_ms=1000.0
        )
        d2 = ctrl.on_wave_completed(event2)
        assert d2.action == "maintain"

    def test_recovery_with_mocked_time(self) -> None:
        """Recovery works when mocking time to pass stability window."""
        ctrl = ConcurrencyController(
            initial_workers=4, stability_minutes=5.0
        )
        # Reduce first
        event1 = _make_wave_event(
            wave_id="w1", rate_limit_count=1, p95_task_latency_ms=1000.0
        )
        ctrl.on_wave_completed(event1)

        # Mock time to be 6 minutes later
        future_time = time.monotonic() + 360.0  # 6 minutes
        with patch("guardkit.orchestrator.instrumentation.concurrency.time.monotonic", return_value=future_time):
            event2 = _make_wave_event(
                wave_id="w2", rate_limit_count=0, p95_task_latency_ms=1000.0
            )
            d = ctrl.on_wave_completed(event2)
        assert d.action == "increase"
        assert d.new_workers == 3  # 2 + 1

    def test_recovery_reason_mentions_stability(self) -> None:
        """Recovery reason mentions stability."""
        ctrl = ConcurrencyController(initial_workers=4, stability_minutes=0.0)
        event1 = _make_wave_event(
            wave_id="w1", rate_limit_count=1, p95_task_latency_ms=1000.0
        )
        ctrl.on_wave_completed(event1)

        event2 = _make_wave_event(
            wave_id="w2", rate_limit_count=0, p95_task_latency_ms=1000.0
        )
        d = ctrl.on_wave_completed(event2)
        assert "stability" in d.reason.lower() or "recover" in d.reason.lower()


# ===========================================================================
# AC-005: Zero Rate Limits → No Adaptation
# ===========================================================================


class TestZeroRateLimits:
    """AC-005: Zero rate limit count triggers no adaptation."""

    def test_zero_rate_limits_maintains_workers(self) -> None:
        """rate_limit_count=0 → maintain."""
        ctrl = ConcurrencyController(initial_workers=4)
        event = _make_wave_event(
            rate_limit_count=0, p95_task_latency_ms=1000.0
        )
        d = ctrl.on_wave_completed(event)
        assert d.action == "maintain"
        assert d.new_workers == 4

    def test_zero_rate_limits_no_reduction(self) -> None:
        """Multiple waves with zero rate limits, all maintain."""
        ctrl = ConcurrencyController(initial_workers=4)
        for i in range(5):
            event = _make_wave_event(
                wave_id=f"w{i}",
                rate_limit_count=0,
                p95_task_latency_ms=1000.0,
            )
            d = ctrl.on_wave_completed(event)
            assert d.action == "maintain"


# ===========================================================================
# AC-006: Minimum Concurrency Is 1 Worker
# ===========================================================================


class TestMinimumConcurrency:
    """AC-006: Minimum concurrency is 1 worker."""

    def test_cannot_reduce_below_1(self) -> None:
        """Successive reductions floor at 1."""
        ctrl = ConcurrencyController(initial_workers=2)
        # First: 2 -> 1
        event1 = _make_wave_event(
            wave_id="w1", rate_limit_count=1, p95_task_latency_ms=1000.0
        )
        d1 = ctrl.on_wave_completed(event1)
        assert d1.new_workers == 1

        # Second: still 1 (cannot go below)
        event2 = _make_wave_event(
            wave_id="w2",
            worker_count=1,
            rate_limit_count=1,
            p95_task_latency_ms=1000.0,
        )
        d2 = ctrl.on_wave_completed(event2)
        assert d2.new_workers == 1

    def test_single_worker_rate_limit_stays_at_1(self) -> None:
        """Starting with 1 worker and rate limit: stays at 1."""
        ctrl = ConcurrencyController(initial_workers=1)
        event = _make_wave_event(
            rate_limit_count=5, p95_task_latency_ms=1000.0
        )
        d = ctrl.on_wave_completed(event)
        assert d.new_workers == 1

    def test_minimum_floor_with_odd_numbers(self) -> None:
        """3 workers: 50% = 1.5 → floor to 1."""
        ctrl = ConcurrencyController(initial_workers=3)
        event = _make_wave_event(
            rate_limit_count=1, p95_task_latency_ms=1000.0
        )
        d = ctrl.on_wave_completed(event)
        assert d.new_workers == 1  # max(1, floor(3*0.5)) = max(1, 1) = 1


# ===========================================================================
# AC-007: Maximum Concurrency Is Original Configured Value
# ===========================================================================


class TestMaximumConcurrency:
    """AC-007: Maximum concurrency is original configured value."""

    def test_cannot_increase_above_initial(self) -> None:
        """Recovery cannot exceed initial_workers."""
        ctrl = ConcurrencyController(initial_workers=4, stability_minutes=0.0)
        # Reduce: 4 -> 2
        event1 = _make_wave_event(
            wave_id="w1", rate_limit_count=1, p95_task_latency_ms=1000.0
        )
        ctrl.on_wave_completed(event1)

        # Recover: 2 -> 3
        event2 = _make_wave_event(
            wave_id="w2", rate_limit_count=0, p95_task_latency_ms=1000.0
        )
        d2 = ctrl.on_wave_completed(event2)
        assert d2.new_workers == 3

        # Recover: 3 -> 4
        event3 = _make_wave_event(
            wave_id="w3", rate_limit_count=0, p95_task_latency_ms=1000.0
        )
        d3 = ctrl.on_wave_completed(event3)
        assert d3.new_workers == 4

        # Cannot go above 4
        event4 = _make_wave_event(
            wave_id="w4", rate_limit_count=0, p95_task_latency_ms=1000.0
        )
        d4 = ctrl.on_wave_completed(event4)
        assert d4.action == "maintain"
        assert d4.new_workers == 4

    def test_current_workers_property(self) -> None:
        """current_workers reflects latest state."""
        ctrl = ConcurrencyController(initial_workers=6)
        assert ctrl.current_workers == 6

        event = _make_wave_event(
            rate_limit_count=1, p95_task_latency_ms=1000.0
        )
        ctrl.on_wave_completed(event)
        assert ctrl.current_workers == 3  # 6 * 0.5 = 3


# ===========================================================================
# AC-008: Integration with FeatureOrchestrator
# ===========================================================================


class TestIntegration:
    """AC-008: ConcurrencyController integrates with FeatureOrchestrator.

    Tests the controller's interface is compatible for injection:
    - Accepts WaveCompletedEvent
    - Returns ConcurrencyDecision
    - Has current_workers property
    """

    def test_accepts_wave_completed_event(self) -> None:
        """Controller processes WaveCompletedEvent correctly."""
        ctrl = ConcurrencyController(initial_workers=4)
        event = _make_wave_event()
        decision = ctrl.on_wave_completed(event)
        assert isinstance(decision, ConcurrencyDecision)

    def test_decision_has_required_fields(self) -> None:
        """Decision has action, new_workers, reason."""
        ctrl = ConcurrencyController(initial_workers=4)
        event = _make_wave_event()
        d = ctrl.on_wave_completed(event)
        assert hasattr(d, "action")
        assert hasattr(d, "new_workers")
        assert hasattr(d, "reason")

    def test_current_workers_is_property(self) -> None:
        """current_workers is accessible as a property."""
        ctrl = ConcurrencyController(initial_workers=4)
        assert isinstance(ctrl.current_workers, int)

    def test_sequential_wave_processing(self) -> None:
        """Controller processes a realistic sequence of waves."""
        ctrl = ConcurrencyController(initial_workers=8, stability_minutes=0.0)

        # Wave 1: establish baseline, no issues
        d1 = ctrl.on_wave_completed(
            _make_wave_event(
                wave_id="w1", rate_limit_count=0, p95_task_latency_ms=2000.0
            )
        )
        assert d1.action == "maintain"
        assert ctrl.current_workers == 8

        # Wave 2: rate limits hit → reduce
        d2 = ctrl.on_wave_completed(
            _make_wave_event(
                wave_id="w2", rate_limit_count=3, p95_task_latency_ms=3000.0
            )
        )
        assert d2.action == "reduce"
        assert ctrl.current_workers == 4

        # Wave 3: clean → recover +1
        d3 = ctrl.on_wave_completed(
            _make_wave_event(
                wave_id="w3", rate_limit_count=0, p95_task_latency_ms=2000.0
            )
        )
        assert d3.action == "increase"
        assert ctrl.current_workers == 5


# ===========================================================================
# AC-009: Concurrency Decisions Logged
# ===========================================================================


class TestDecisionLogging:
    """AC-009: Concurrency decisions are logged."""

    def test_reduction_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Rate limit reduction is logged."""
        ctrl = ConcurrencyController(initial_workers=4)
        with caplog.at_level(logging.INFO):
            event = _make_wave_event(
                rate_limit_count=1, p95_task_latency_ms=1000.0
            )
            ctrl.on_wave_completed(event)
        assert any("reduce" in r.message.lower() for r in caplog.records)

    def test_maintain_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Maintain decision is logged."""
        ctrl = ConcurrencyController(initial_workers=4)
        with caplog.at_level(logging.INFO):
            event = _make_wave_event(
                rate_limit_count=0, p95_task_latency_ms=1000.0
            )
            ctrl.on_wave_completed(event)
        assert any("maintain" in r.message.lower() for r in caplog.records)

    def test_increase_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Recovery increase is logged."""
        ctrl = ConcurrencyController(initial_workers=4, stability_minutes=0.0)
        with caplog.at_level(logging.INFO):
            event1 = _make_wave_event(
                wave_id="w1", rate_limit_count=1, p95_task_latency_ms=1000.0
            )
            ctrl.on_wave_completed(event1)
            event2 = _make_wave_event(
                wave_id="w2", rate_limit_count=0, p95_task_latency_ms=1000.0
            )
            ctrl.on_wave_completed(event2)
        assert any("increase" in r.message.lower() for r in caplog.records)

    def test_log_includes_worker_counts(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Logged messages include worker count info."""
        ctrl = ConcurrencyController(initial_workers=4)
        with caplog.at_level(logging.INFO):
            event = _make_wave_event(
                rate_limit_count=1, p95_task_latency_ms=1000.0
            )
            ctrl.on_wave_completed(event)
        log_text = " ".join(r.message for r in caplog.records)
        # Should mention the new worker count
        assert "2" in log_text


# ===========================================================================
# AC-010: Boundary Condition Tests
# ===========================================================================


class TestBoundaryConditions:
    """AC-010: Unit tests cover all boundary conditions."""

    def test_initial_workers_1(self) -> None:
        """Edge: initial_workers=1."""
        ctrl = ConcurrencyController(initial_workers=1)
        assert ctrl.current_workers == 1

    def test_large_initial_workers(self) -> None:
        """Edge: large initial_workers."""
        ctrl = ConcurrencyController(initial_workers=100)
        event = _make_wave_event(rate_limit_count=1, p95_task_latency_ms=1000.0)
        d = ctrl.on_wave_completed(event)
        assert d.new_workers == 50

    def test_rate_limit_takes_priority_over_latency(self) -> None:
        """When both rate limit AND high latency present, rate limit dominates."""
        ctrl = ConcurrencyController(initial_workers=4)
        # Establish baseline
        baseline = _make_wave_event(wave_id="w1", p95_task_latency_ms=1000.0)
        ctrl.on_wave_completed(baseline)

        # Both rate limit and high latency
        event = _make_wave_event(
            wave_id="w2",
            rate_limit_count=2,
            p95_task_latency_ms=50000.0,  # way above threshold
        )
        d = ctrl.on_wave_completed(event)
        assert d.action == "reduce"
        assert d.new_workers == 2  # 50% reduction applied once, not twice

    def test_p95_threshold_zero_disables_latency_check(self) -> None:
        """p95_threshold_pct=0 means any increase triggers reduction (edge)."""
        ctrl = ConcurrencyController(initial_workers=4, p95_threshold_pct=0.0)
        baseline = _make_wave_event(wave_id="w1", p95_task_latency_ms=1000.0)
        ctrl.on_wave_completed(baseline)

        # Even tiny increase above baseline triggers
        event = _make_wave_event(wave_id="w2", p95_task_latency_ms=1001.0)
        d = ctrl.on_wave_completed(event)
        assert d.action == "reduce"

    def test_consecutive_maintain_decisions(self) -> None:
        """Multiple waves at original capacity: all maintain."""
        ctrl = ConcurrencyController(initial_workers=4)
        for i in range(10):
            event = _make_wave_event(
                wave_id=f"w{i}",
                rate_limit_count=0,
                p95_task_latency_ms=1000.0,
            )
            d = ctrl.on_wave_completed(event)
            assert d.action == "maintain"
            assert ctrl.current_workers == 4

    def test_recovery_then_reduction_cycle(self) -> None:
        """Full cycle: reduce → recover → reduce again."""
        ctrl = ConcurrencyController(initial_workers=4, stability_minutes=0.0)

        # Reduce: 4 -> 2
        d1 = ctrl.on_wave_completed(
            _make_wave_event(
                wave_id="w1", rate_limit_count=1, p95_task_latency_ms=1000.0
            )
        )
        assert d1.new_workers == 2

        # Recover: 2 -> 3
        d2 = ctrl.on_wave_completed(
            _make_wave_event(
                wave_id="w2", rate_limit_count=0, p95_task_latency_ms=1000.0
            )
        )
        assert d2.new_workers == 3

        # Reduce again: 3 -> 1 (floor(3*0.5)=1)
        d3 = ctrl.on_wave_completed(
            _make_wave_event(
                wave_id="w3", rate_limit_count=2, p95_task_latency_ms=1000.0
            )
        )
        assert d3.new_workers == 1
