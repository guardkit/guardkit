"""
Unit tests for TASK-VPR-003: SDK Turn Ceiling Monitoring.

Tests ceiling detection logic, summary generation, and warning thresholds.

Coverage Target: >=85%
Test Count: 16 tests
"""

import pytest

from guardkit.orchestrator.sdk_ceiling import (
    SdkTurnRecord,
    CeilingSummary,
    CEILING_WARNING_THRESHOLD,
    compute_ceiling_summary,
    detect_ceiling_hit,
)


class TestDetectCeilingHit:
    """Tests for detect_ceiling_hit() function."""

    def test_ceiling_hit_when_turns_equals_max(self):
        """turns_used == max_turns -> ceiling hit."""
        assert detect_ceiling_hit(50, 50) is True

    def test_ceiling_hit_when_turns_exceeds_max(self):
        """turns_used > max_turns -> ceiling hit."""
        assert detect_ceiling_hit(55, 50) is True

    def test_no_ceiling_hit_when_under_max(self):
        """turns_used < max_turns -> no ceiling hit."""
        assert detect_ceiling_hit(30, 50) is False

    def test_no_ceiling_hit_when_turns_none(self):
        """None turns_used -> no ceiling hit."""
        assert detect_ceiling_hit(None, 50) is False

    def test_no_ceiling_hit_when_max_none(self):
        """None max_turns -> no ceiling hit."""
        assert detect_ceiling_hit(50, None) is False

    def test_no_ceiling_hit_when_both_none(self):
        """Both None -> no ceiling hit."""
        assert detect_ceiling_hit(None, None) is False


class TestSdkTurnRecord:
    """Tests for SdkTurnRecord dataclass."""

    def test_ceiling_hit_property_when_at_max(self):
        """ceiling_hit property reflects turns_used >= max_turns."""
        record = SdkTurnRecord(task_id="TASK-001", turns_used=50, max_turns=50)
        assert record.ceiling_hit is True

    def test_no_ceiling_hit_property(self):
        """ceiling_hit is False when under max."""
        record = SdkTurnRecord(task_id="TASK-001", turns_used=30, max_turns=50)
        assert record.ceiling_hit is False

    def test_frozen_dataclass(self):
        """SdkTurnRecord is immutable."""
        record = SdkTurnRecord(task_id="TASK-001", turns_used=50, max_turns=50)
        with pytest.raises(AttributeError):
            record.turns_used = 40


class TestComputeCeilingSummary:
    """Tests for compute_ceiling_summary() function."""

    def test_all_ceiling_hits(self):
        """All invocations hit ceiling -> 100% rate."""
        records = [
            SdkTurnRecord(task_id="TASK-001", turns_used=50, max_turns=50),
            SdkTurnRecord(task_id="TASK-002", turns_used=50, max_turns=50),
            SdkTurnRecord(task_id="TASK-003", turns_used=50, max_turns=50),
        ]
        summary = compute_ceiling_summary(records)
        assert summary.total_invocations == 3
        assert summary.ceiling_hits == 3
        assert summary.ceiling_hit_rate == 100.0
        assert summary.exceeds_warning_threshold is True

    def test_no_ceiling_hits(self):
        """No ceiling hits -> 0% rate."""
        records = [
            SdkTurnRecord(task_id="TASK-001", turns_used=30, max_turns=50),
            SdkTurnRecord(task_id="TASK-002", turns_used=25, max_turns=50),
        ]
        summary = compute_ceiling_summary(records)
        assert summary.total_invocations == 2
        assert summary.ceiling_hits == 0
        assert summary.ceiling_hit_rate == 0.0
        assert summary.exceeds_warning_threshold is False

    def test_mixed_hits(self):
        """Mix of hits and non-hits."""
        records = [
            SdkTurnRecord(task_id="TASK-001", turns_used=50, max_turns=50),  # hit
            SdkTurnRecord(task_id="TASK-002", turns_used=30, max_turns=50),  # no hit
            SdkTurnRecord(task_id="TASK-003", turns_used=50, max_turns=50),  # hit
        ]
        summary = compute_ceiling_summary(records)
        assert summary.ceiling_hits == 2
        assert abs(summary.ceiling_hit_rate - 66.67) < 0.1

    def test_empty_records(self):
        """Empty records -> 0 invocations, 0% rate."""
        summary = compute_ceiling_summary([])
        assert summary.total_invocations == 0
        assert summary.ceiling_hits == 0
        assert summary.ceiling_hit_rate == 0.0
        assert summary.exceeds_warning_threshold is False

    def test_warning_threshold_boundary(self):
        """60% exactly does NOT exceed threshold (> not >=)."""
        records = [
            SdkTurnRecord(task_id=f"TASK-{i}", turns_used=50, max_turns=50)
            for i in range(3)
        ] + [
            SdkTurnRecord(task_id=f"TASK-{i}", turns_used=30, max_turns=50)
            for i in range(3, 5)
        ]
        summary = compute_ceiling_summary(records)
        assert summary.ceiling_hit_rate == 60.0
        assert summary.exceeds_warning_threshold is False  # Exactly 60% does NOT exceed

    def test_above_warning_threshold(self):
        """Above 60% triggers warning."""
        records = [
            SdkTurnRecord(task_id="TASK-001", turns_used=50, max_turns=50),
            SdkTurnRecord(task_id="TASK-002", turns_used=50, max_turns=50),
            SdkTurnRecord(task_id="TASK-003", turns_used=30, max_turns=50),
        ]
        summary = compute_ceiling_summary(records)
        assert abs(summary.ceiling_hit_rate - 66.67) < 0.1
        assert summary.exceeds_warning_threshold is True

    def test_records_preserved_as_tuple(self):
        """Records are stored as a frozen tuple in summary."""
        records = [
            SdkTurnRecord(task_id="TASK-001", turns_used=50, max_turns=50),
        ]
        summary = compute_ceiling_summary(records)
        assert isinstance(summary.records, tuple)
        assert len(summary.records) == 1
        assert summary.records[0].task_id == "TASK-001"


class TestCeilingWarningThreshold:
    """Tests for CEILING_WARNING_THRESHOLD constant."""

    def test_threshold_value(self):
        """Warning threshold is 60%."""
        assert CEILING_WARNING_THRESHOLD == 60.0
