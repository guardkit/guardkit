"""LPA-06 poller classifier — every branch (WS2 B3 gate: classifier branches).

The B3 definition-of-done names this explicitly: "unit tests for every
classifier branch". The three outputs are progressing / stuck / failed, plus
the terminal-success and deadline-overrun sub-branches and the input-guard
raises.
"""

from __future__ import annotations

import pytest

from guardkit.orchestrator.live_gate.poller import PollSample, classify_operation


def _samples(*specs):
    """specs: (elapsed_s, progress, done, failed) tuples (progress/done/failed optional)."""
    out = []
    for spec in specs:
        elapsed = spec[0]
        progress = spec[1] if len(spec) > 1 else None
        done = spec[2] if len(spec) > 2 else False
        failed = spec[3] if len(spec) > 3 else False
        out.append(PollSample(elapsed_s=elapsed, progress=progress, done=done, failed=failed))
    return out


class TestFailedBranch:
    def test_explicit_failure_anywhere_is_failed(self):
        s = _samples((0, 10), (5, 20, False, True), (10, 30))
        assert classify_operation(s, deadline_s=100, stall_window_s=30) == "failed"

    def test_failure_wins_over_later_done(self):
        # a failure observed, then a done — the witnessed failure stands.
        s = _samples((0, 0, False, True), (5, 100, True, False))
        assert classify_operation(s, deadline_s=100, stall_window_s=30) == "failed"

    def test_deadline_overrun_without_completion_is_failed(self):
        # progress is advancing, but the honest deadline is blown → failed,
        # not stuck (silent overrun is a finding, the deadline is the hard stop).
        s = _samples((0, 0), (60, 50), (120, 90))
        assert classify_operation(s, deadline_s=120, stall_window_s=1000) == "failed"


class TestStuckBranch:
    def test_no_progress_past_stall_window_within_deadline_is_stuck(self):
        s = _samples((0, 42), (10, 42), (30, 42))
        assert classify_operation(s, deadline_s=100, stall_window_s=20) == "stuck"

    def test_progress_none_throughout_and_stalled_is_stuck(self):
        s = _samples((0, None), (10, None), (30, None))
        assert classify_operation(s, deadline_s=100, stall_window_s=20) == "stuck"

    def test_stall_measured_from_last_change_not_start(self):
        # advanced at t=25, then flat to t=50 → stalled span 25 >= window 20.
        s = _samples((0, 1), (25, 2), (50, 2))
        assert classify_operation(s, deadline_s=100, stall_window_s=20) == "stuck"


class TestProgressingBranch:
    def test_advancing_within_window_is_progressing(self):
        s = _samples((0, 0), (10, 25), (20, 60))
        assert classify_operation(s, deadline_s=100, stall_window_s=30) == "progressing"

    def test_terminal_success_is_progressing(self):
        s = _samples((0, 0), (5, 50), (9, 100, True))
        assert classify_operation(s, deadline_s=100, stall_window_s=1) == "progressing"

    def test_done_beats_a_flat_stall(self):
        # unchanged progress but done=True → reached success, not stuck.
        s = _samples((0, 100), (40, 100, True))
        assert classify_operation(s, deadline_s=100, stall_window_s=10) == "progressing"

    def test_single_early_sample_is_progressing(self):
        s = _samples((1, 5))
        assert classify_operation(s, deadline_s=100, stall_window_s=30) == "progressing"


class TestInputGuards:
    def test_empty_samples_raises(self):
        with pytest.raises(ValueError, match="samples is empty"):
            classify_operation([], deadline_s=100, stall_window_s=10)

    def test_nonpositive_deadline_raises(self):
        with pytest.raises(ValueError, match="deadline_s must be positive"):
            classify_operation(_samples((0, 1)), deadline_s=0, stall_window_s=10)

    def test_negative_stall_window_raises(self):
        with pytest.raises(ValueError, match="stall_window_s must be non-negative"):
            classify_operation(_samples((0, 1)), deadline_s=10, stall_window_s=-1)
