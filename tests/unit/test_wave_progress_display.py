"""
Unit tests for WaveProgressDisplay.

Tests the wave-level progress visualization for feature orchestration.
"""

import re
import pytest
from io import StringIO
from unittest.mock import MagicMock, patch

from rich.console import Console

from guardkit.cli.display import (
    WaveProgressDisplay,
    WaveTaskStatus,
    WaveRecord,
)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text for easier testing."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_console():
    """Create a mock console that captures output."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80)
    return console, output


@pytest.fixture
def display(mock_console):
    """Create a WaveProgressDisplay with mock console."""
    console, _ = mock_console
    return WaveProgressDisplay(total_waves=4, verbose=False, console=console)


@pytest.fixture
def verbose_display(mock_console):
    """Create a verbose WaveProgressDisplay with mock console."""
    console, _ = mock_console
    return WaveProgressDisplay(total_waves=4, verbose=True, console=console)


# ============================================================================
# Initialization Tests
# ============================================================================


class TestWaveProgressDisplayInit:
    """Tests for WaveProgressDisplay initialization."""

    def test_init_valid_waves(self, mock_console):
        """Test initialization with valid wave count."""
        console, _ = mock_console
        display = WaveProgressDisplay(total_waves=5, console=console)

        assert display.total_waves == 5
        assert display.verbose is False
        assert display.current_wave is None
        assert display.task_statuses == {}
        assert display.wave_history == []

    def test_init_with_verbose(self, mock_console):
        """Test initialization with verbose flag."""
        console, _ = mock_console
        display = WaveProgressDisplay(total_waves=3, verbose=True, console=console)

        assert display.verbose is True

    def test_init_single_wave(self, mock_console):
        """Test initialization with single wave."""
        console, _ = mock_console
        display = WaveProgressDisplay(total_waves=1, console=console)

        assert display.total_waves == 1

    def test_init_invalid_zero_waves(self, mock_console):
        """Test initialization with zero waves raises ValueError."""
        console, _ = mock_console

        with pytest.raises(ValueError, match="total_waves must be at least 1"):
            WaveProgressDisplay(total_waves=0, console=console)

    def test_init_invalid_negative_waves(self, mock_console):
        """Test initialization with negative waves raises ValueError."""
        console, _ = mock_console

        with pytest.raises(ValueError, match="total_waves must be at least 1"):
            WaveProgressDisplay(total_waves=-1, console=console)


# ============================================================================
# Wave Lifecycle Tests
# ============================================================================


class TestWaveLifecycle:
    """Tests for wave lifecycle methods."""

    def test_start_wave(self, display, mock_console):
        """Test starting a wave."""
        _, output = mock_console

        display.start_wave(wave_number=1, task_ids=["TASK-001", "TASK-002"])

        # Check state updated
        assert display.current_wave == 1
        assert display.current_wave_tasks == ["TASK-001", "TASK-002"]
        assert "TASK-001" in display.task_statuses
        assert "TASK-002" in display.task_statuses

        # Check output contains wave info
        output_text = strip_ansi(output.getvalue())
        assert "Wave 1/4" in output_text

    def test_start_wave_single_task(self, display, mock_console):
        """Test starting a wave with single task (no parallel indicator)."""
        _, output = mock_console

        display.start_wave(wave_number=2, task_ids=["TASK-003"])

        assert display.current_wave == 2
        assert len(display.current_wave_tasks) == 1

        output_text = strip_ansi(output.getvalue())
        assert "Wave 2/4" in output_text
        assert "TASK-003" in output_text

    def test_start_wave_parallel_tasks(self, display, mock_console):
        """Test starting a wave with parallel tasks shows indicator."""
        _, output = mock_console

        display.start_wave(wave_number=1, task_ids=["TASK-001", "TASK-002", "TASK-003"])

        output_text = strip_ansi(output.getvalue())
        assert "parallel" in output_text.lower()

    def test_complete_wave_success(self, display, mock_console):
        """Test completing a wave successfully."""
        _, output = mock_console

        # Start and complete wave
        display.start_wave(wave_number=1, task_ids=["TASK-001", "TASK-002"])
        display.complete_wave(wave_number=1, passed=2, failed=0)

        # Check wave recorded
        assert len(display.wave_history) == 1
        wave = display.wave_history[0]
        assert wave.wave_number == 1
        assert wave.passed == 2
        assert wave.failed == 0

        # Check output
        output_text = strip_ansi(output.getvalue())
        assert "PASSED" in output_text
        assert "2 passed" in output_text

    def test_complete_wave_with_failures(self, display, mock_console):
        """Test completing a wave with failures."""
        _, output = mock_console

        display.start_wave(wave_number=1, task_ids=["TASK-001", "TASK-002"])
        display.complete_wave(wave_number=1, passed=1, failed=1)

        wave = display.wave_history[0]
        assert wave.passed == 1
        assert wave.failed == 1

        output_text = strip_ansi(output.getvalue())
        assert "FAILED" in output_text
        assert "1 failed" in output_text

    def test_complete_wave_with_skipped(self, display, mock_console):
        """Test completing a wave with skipped tasks."""
        _, output = mock_console

        display.start_wave(wave_number=1, task_ids=["TASK-001", "TASK-002", "TASK-003"])
        display.complete_wave(wave_number=1, passed=1, failed=1, skipped=1)

        output_text = strip_ansi(output.getvalue())
        assert "1 skipped" in output_text


# ============================================================================
# Task Status Tests
# ============================================================================


class TestTaskStatus:
    """Tests for task status updates."""

    def test_update_task_in_progress(self, display, mock_console):
        """Test updating task to in_progress status."""
        _, output = mock_console

        display.start_wave(wave_number=1, task_ids=["TASK-001"])
        display.update_task_status("TASK-001", "in_progress", "Executing: Create pyproject.toml")

        status = display.task_statuses["TASK-001"]
        assert status.status == "in_progress"
        assert "Executing" in status.details

        # Verify output (strip ANSI for comparison)
        output_text = strip_ansi(output.getvalue())
        assert "TASK-001" in output_text

    def test_update_task_success(self, display, mock_console):
        """Test updating task to success status."""
        _, output = mock_console

        display.start_wave(wave_number=1, task_ids=["TASK-001"])
        display.update_task_status(
            "TASK-001", "success", "Completed",
            turns=2, decision="approve"
        )

        status = display.task_statuses["TASK-001"]
        assert status.status == "success"
        assert status.turns == 2
        assert status.decision == "approve"

        output_text = strip_ansi(output.getvalue())
        assert "SUCCESS" in output_text

    def test_update_task_failed(self, display, mock_console):
        """Test updating task to failed status."""
        _, output = mock_console

        display.start_wave(wave_number=1, task_ids=["TASK-001"])
        display.update_task_status(
            "TASK-001", "failed", "Max turns exceeded",
            turns=5, decision="max_turns"
        )

        status = display.task_statuses["TASK-001"]
        assert status.status == "failed"

        output_text = strip_ansi(output.getvalue())
        assert "FAILED" in output_text

    def test_update_task_skipped(self, display, mock_console):
        """Test updating task to skipped status."""
        _, output = mock_console

        display.start_wave(wave_number=1, task_ids=["TASK-001"])
        display.update_task_status("TASK-001", "skipped", "dependency failed")

        status = display.task_statuses["TASK-001"]
        assert status.status == "skipped"

        output_text = strip_ansi(output.getvalue())
        assert "SKIPPED" in output_text

    def test_update_task_not_in_wave(self, display, mock_console):
        """Test updating task not in current wave (no crash)."""
        _, output = mock_console

        display.start_wave(wave_number=1, task_ids=["TASK-001"])
        # Update a task not in the wave - should not crash
        display.update_task_status("TASK-999", "success", "Unknown task")

        # Original task still valid
        assert "TASK-001" in display.task_statuses


# ============================================================================
# Summary Display Tests
# ============================================================================


class TestSummaryDisplay:
    """Tests for summary display methods."""

    def test_render_final_summary_success(self, display, mock_console):
        """Test rendering final summary for successful feature."""
        _, output = mock_console

        # Simulate completed waves
        display.start_wave(1, ["TASK-001", "TASK-002"])
        display.update_task_status("TASK-001", "success", "", turns=1, decision="approve")
        display.update_task_status("TASK-002", "success", "", turns=2, decision="approve")
        display.complete_wave(1, passed=2, failed=0)

        # Render final summary
        display.render_final_summary(
            feature_id="FEAT-TEST",
            feature_name="Test Feature",
            status="completed",
            total_tasks=2,
            tasks_completed=2,
            tasks_failed=0,
            total_turns=3,
            worktree_path="/path/to/worktree",
        )

        output_text = strip_ansi(output.getvalue())
        assert "SUCCESS" in output_text
        assert "FEAT-TEST" in output_text
        assert "Test Feature" in output_text
        assert "2/2 completed" in output_text

    def test_render_final_summary_failure(self, display, mock_console):
        """Test rendering final summary for failed feature."""
        _, output = mock_console

        display.start_wave(1, ["TASK-001"])
        display.update_task_status("TASK-001", "failed", "", turns=5, decision="max_turns")
        display.complete_wave(1, passed=0, failed=1)

        display.render_final_summary(
            feature_id="FEAT-TEST",
            feature_name="Test Feature",
            status="failed",
            total_tasks=1,
            tasks_completed=0,
            tasks_failed=1,
            total_turns=5,
            worktree_path="/path/to/worktree",
        )

        output_text = strip_ansi(output.getvalue())
        assert "FAILED" in output_text
        assert "1 failed" in output_text

    def test_render_final_summary_with_next_steps(self, display, mock_console):
        """Test that final summary includes next steps."""
        _, output = mock_console

        display.render_final_summary(
            feature_id="FEAT-TEST",
            feature_name="Test Feature",
            status="completed",
            total_tasks=1,
            tasks_completed=1,
            tasks_failed=0,
            total_turns=1,
            worktree_path="/path/to/worktree",
        )

        output_text = strip_ansi(output.getvalue())
        assert "Next Steps" in output_text
        assert "git diff" in output_text or "Review" in output_text


# ============================================================================
# Verbose Mode Tests
# ============================================================================


class TestVerboseMode:
    """Tests for verbose mode display."""

    def test_verbose_wave_task_table(self, verbose_display, mock_console):
        """Test that verbose mode shows task table after wave completion."""
        _, output = mock_console

        verbose_display.start_wave(1, ["TASK-001", "TASK-002"])
        verbose_display.update_task_status("TASK-001", "success", "", turns=1, decision="approve")
        verbose_display.update_task_status("TASK-002", "success", "", turns=2, decision="approve")
        verbose_display.complete_wave(1, passed=2, failed=0)

        output_text = strip_ansi(output.getvalue())
        # In verbose mode, should show detailed table
        assert "TASK-001" in output_text
        assert "TASK-002" in output_text

    def test_non_verbose_no_task_table(self, display, mock_console):
        """Test that non-verbose mode doesn't show detailed task table."""
        _, output = mock_console

        display.start_wave(1, ["TASK-001"])
        display.update_task_status("TASK-001", "success", "", turns=1, decision="approve")
        display.complete_wave(1, passed=1, failed=0)

        # Just basic summary, no elaborate table
        output_text = strip_ansi(output.getvalue())
        assert "1 passed" in output_text


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in display."""

    def test_display_error_doesnt_crash(self, mock_console):
        """Test that display errors don't crash the orchestration."""
        console, _ = mock_console
        display = WaveProgressDisplay(total_waves=2, console=console)

        # These operations should not crash even without proper setup
        # The error handling decorator catches exceptions gracefully
        display.complete_wave(1, passed=0, failed=0)  # No start_wave called
        display.update_task_status("TASK-999", "success", "")  # Unknown task

        # No exception raised = test passes

    def test_invalid_wave_number_handled(self, display):
        """Test that invalid wave operations don't crash."""
        # Start wave 1
        display.start_wave(1, ["TASK-001"])

        # Complete wave 2 (which wasn't started) - should not crash
        display.complete_wave(2, passed=0, failed=0)


# ============================================================================
# Data Classes Tests
# ============================================================================


class TestDataClasses:
    """Tests for data classes."""

    def test_wave_task_status_defaults(self):
        """Test WaveTaskStatus default values."""
        status = WaveTaskStatus(task_id="TASK-001")

        assert status.task_id == "TASK-001"
        assert status.status == "pending"
        assert status.details == ""
        assert status.turns == 0
        assert status.decision == ""

    def test_wave_task_status_with_values(self):
        """Test WaveTaskStatus with custom values."""
        status = WaveTaskStatus(
            task_id="TASK-001",
            status="success",
            details="Completed",
            turns=3,
            decision="approve",
        )

        assert status.status == "success"
        assert status.turns == 3
        assert status.decision == "approve"

    def test_wave_record_creation(self):
        """Test WaveRecord creation."""
        record = WaveRecord(
            wave_number=1,
            task_ids=["TASK-001", "TASK-002"],
            passed=2,
            failed=0,
            total_turns=5,
        )

        assert record.wave_number == 1
        assert len(record.task_ids) == 2
        assert record.passed == 2
        assert record.failed == 0
        assert record.total_turns == 5
        assert record.completed_at is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for full wave lifecycle."""

    def test_full_wave_lifecycle(self, display, mock_console):
        """Test complete wave lifecycle from start to finish."""
        _, output = mock_console

        # Wave 1: Two tasks, both succeed
        display.start_wave(1, ["TASK-001", "TASK-002"])
        display.update_task_status("TASK-001", "in_progress", "Executing")
        display.update_task_status("TASK-001", "success", "", turns=1, decision="approve")
        display.update_task_status("TASK-002", "in_progress", "Executing")
        display.update_task_status("TASK-002", "success", "", turns=2, decision="approve")
        display.complete_wave(1, passed=2, failed=0)

        # Wave 2: One task, fails
        display.start_wave(2, ["TASK-003"])
        display.update_task_status("TASK-003", "in_progress", "Executing")
        display.update_task_status("TASK-003", "failed", "", turns=5, decision="max_turns")
        display.complete_wave(2, passed=0, failed=1)

        # Final summary
        display.render_final_summary(
            feature_id="FEAT-001",
            feature_name="Test Feature",
            status="failed",
            total_tasks=3,
            tasks_completed=2,
            tasks_failed=1,
            total_turns=8,
            worktree_path="/path/to/worktree",
        )

        # Verify state
        assert len(display.wave_history) == 2
        assert display.wave_history[0].passed == 2
        assert display.wave_history[1].failed == 1

        # Verify output contains key information
        output_text = strip_ansi(output.getvalue())
        assert "Wave 1/4" in output_text
        assert "Wave 2/4" in output_text
        assert "FAILED" in output_text

    def test_multiple_waves_tracking(self, display):
        """Test that multiple waves are properly tracked."""
        display.start_wave(1, ["TASK-001"])
        display.complete_wave(1, passed=1, failed=0)

        display.start_wave(2, ["TASK-002"])
        display.complete_wave(2, passed=1, failed=0)

        display.start_wave(3, ["TASK-003"])
        display.complete_wave(3, passed=1, failed=0)

        display.start_wave(4, ["TASK-004"])
        display.complete_wave(4, passed=1, failed=0)

        assert len(display.wave_history) == 4
        for i, wave in enumerate(display.wave_history, 1):
            assert wave.wave_number == i
            assert wave.passed == 1
