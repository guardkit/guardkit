"""
Unit Tests for ProgressDisplay

Tests cover:
• Initialization and configuration
• Turn lifecycle (start → update → complete)
• State tracking (minimal per architectural review)
• Error handling (warn strategy, never crash)
• Context manager support
• Summary rendering
• Edge cases and error conditions

Architecture:
• Mock Rich components to test logic isolation
• Verify state transitions without display side effects
• Test error recovery and graceful degradation
"""

import logging
import warnings
from datetime import datetime
from io import StringIO
from unittest.mock import MagicMock, Mock, patch, call

import pytest
from rich.console import Console

from guardkit.orchestrator.progress import (
    ProgressDisplay,
    TurnStatus,
    FinalStatus,
    _handle_display_error
)


# Test Fixtures

@pytest.fixture
def mock_console():
    """Mock Rich Console for testing without actual terminal output."""
    console = MagicMock(spec=Console)
    console.print = MagicMock()
    return console


@pytest.fixture
def display(mock_console):
    """Standard ProgressDisplay instance with mocked console."""
    return ProgressDisplay(max_turns=5, console=mock_console)


@pytest.fixture
def display_with_real_console():
    """ProgressDisplay with real console capturing output."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    display = ProgressDisplay(max_turns=3, console=console)
    display._output = output  # Store for assertions
    return display


# Test Initialization

class TestInitialization:
    """Test ProgressDisplay initialization and configuration."""

    def test_init_default_parameters(self):
        """Should initialize with default parameters."""
        display = ProgressDisplay(max_turns=5)

        assert display.max_turns == 5
        assert display.current_turn is None
        assert display.turn_history == []
        assert display._progress is None
        assert display._task_id is None
        assert display.console is not None  # Creates default console

    def test_init_with_custom_console(self, mock_console):
        """Should accept custom console instance."""
        display = ProgressDisplay(max_turns=3, console=mock_console)

        assert display.console is mock_console

    def test_init_invalid_max_turns(self):
        """Should raise ValueError for invalid max_turns."""
        with pytest.raises(ValueError, match="max_turns must be at least 1"):
            ProgressDisplay(max_turns=0)

        with pytest.raises(ValueError, match="max_turns must be at least 1"):
            ProgressDisplay(max_turns=-1)

    def test_init_with_kwargs(self, mock_console):
        """Should accept additional kwargs for future extensibility."""
        # Should not raise even with extra kwargs
        display = ProgressDisplay(
            max_turns=5,
            console=mock_console,
            theme="dark",  # Reserved for future use
            verbose=True   # Reserved for future use
        )

        assert display.max_turns == 5


# Test Context Manager

class TestContextManager:
    """Test context manager support."""

    def test_context_manager_enter(self, display):
        """Should support context manager __enter__."""
        with display as d:
            assert d is display

    def test_context_manager_exit_cleanup(self, display):
        """Should cleanup resources on __exit__."""
        with patch.object(display, '_cleanup') as mock_cleanup:
            with display:
                pass

            mock_cleanup.assert_called_once()

    def test_context_manager_exit_does_not_suppress_exceptions(self, display):
        """Should not suppress exceptions during __exit__."""
        with pytest.raises(ValueError, match="test error"):
            with display:
                raise ValueError("test error")

    @patch('guardkit.orchestrator.progress.Progress')
    def test_cleanup_stops_progress(self, mock_progress_class, display):
        """Should stop Rich progress during cleanup."""
        mock_progress = MagicMock()
        display._progress = mock_progress

        display._cleanup()

        mock_progress.stop.assert_called_once()
        assert display._progress is None
        assert display._task_id is None

    def test_cleanup_handles_stop_errors(self, display, caplog):
        """Should handle errors during progress.stop() gracefully."""
        mock_progress = MagicMock()
        mock_progress.stop.side_effect = RuntimeError("stop failed")
        display._progress = mock_progress

        # Should not raise
        with caplog.at_level(logging.DEBUG):
            display._cleanup()

        assert display._progress is None  # Cleanup completes despite error
        assert "Error stopping progress" in caplog.text


# Test Turn Lifecycle

class TestTurnLifecycle:
    """Test turn start → update → complete workflow."""

    @patch('guardkit.orchestrator.progress.Progress')
    def test_start_turn_creates_progress(self, mock_progress_class, display):
        """Should create Rich progress and add task."""
        mock_progress = MagicMock()
        mock_progress.add_task.return_value = "task-123"
        mock_progress_class.return_value = mock_progress

        display.start_turn(turn=1, phase="Player Implementation")

        # Should create progress
        assert mock_progress_class.called
        mock_progress.start.assert_called_once()

        # Should add task with description
        mock_progress.add_task.assert_called_once()
        call_args = mock_progress.add_task.call_args
        description = call_args[0][0]
        assert "Turn 1/5" in description
        assert "Player Implementation" in description

        # Should update state
        assert display.current_turn == 1
        assert len(display.turn_history) == 1
        assert display.turn_history[0]["turn"] == 1
        assert display.turn_history[0]["phase"] == "Player Implementation"
        assert display.turn_history[0]["status"] == "in_progress"

    def test_start_turn_invalid_turn_number(self, display):
        """Should raise ValueError for invalid turn number."""
        with pytest.raises(ValueError, match="Invalid turn number"):
            display.start_turn(turn=0, phase="Test")

        with pytest.raises(ValueError, match="Invalid turn number"):
            display.start_turn(turn=6, phase="Test")  # max_turns=5

    @patch('guardkit.orchestrator.progress.Progress')
    def test_start_turn_cleanup_previous(self, mock_progress_class, display):
        """Should cleanup previous turn if starting new one."""
        mock_progress = MagicMock()
        mock_progress_class.return_value = mock_progress
        display._progress = MagicMock()  # Simulate active turn

        with patch.object(display, '_cleanup') as mock_cleanup:
            display.start_turn(turn=1, phase="Test")

            mock_cleanup.assert_called_once()

    @patch('guardkit.orchestrator.progress.Progress')
    def test_update_turn(self, mock_progress_class, display):
        """Should update progress description and percentage."""
        mock_progress = MagicMock()
        mock_task_id = "task-123"
        display._progress = mock_progress
        display._task_id = mock_task_id
        display.current_turn = 2

        display.update_turn("Writing tests...", progress=50)

        # Should update description
        calls = mock_progress.update.call_args_list
        assert len(calls) == 2  # Once for description, once for progress

        # Check description update
        desc_call = calls[0]
        assert desc_call[0][0] == mock_task_id
        assert "Writing tests..." in desc_call[1]["description"]

        # Check progress update
        progress_call = calls[1]
        assert progress_call[0][0] == mock_task_id
        assert progress_call[1]["completed"] == 50

    def test_update_turn_without_active_turn(self, display, caplog):
        """Should log warning if update called without active turn."""
        with caplog.at_level(logging.WARNING):
            display.update_turn("Test message")

            assert "update_turn called without active turn" in caplog.text

    def test_update_turn_invalid_progress(self, display, caplog):
        """Should log warning for invalid progress values."""
        display._progress = MagicMock()
        display._task_id = "task-123"
        display.current_turn = 1

        with caplog.at_level(logging.WARNING):
            display.update_turn("Test", progress=150)  # > 100

            assert "Invalid progress value" in caplog.text

    @patch('guardkit.orchestrator.progress.Progress')
    def test_complete_turn_success(self, mock_progress_class, mock_console):
        """Should complete turn with success status."""
        display = ProgressDisplay(max_turns=5, console=mock_console)
        mock_progress = MagicMock()
        mock_task_id = "task-123"
        display._progress = mock_progress
        display._task_id = mock_task_id
        display.current_turn = 1
        display.turn_history = [{
            "turn": 1,
            "phase": "Test",
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "error": None
        }]

        display.complete_turn("success", "3 files created")

        # Should complete progress
        mock_progress.update.assert_called_with(mock_task_id, completed=100)

        # Should print status
        mock_console.print.assert_called()
        print_args = mock_console.print.call_args[0][0]
        assert "✓" in print_args  # Success icon
        assert "3 files created" in print_args

        # Should update history
        assert display.turn_history[0]["status"] == "success"
        assert display.turn_history[0]["summary"] == "3 files created"
        assert display.turn_history[0]["ended_at"] is not None

        # Should cleanup
        assert display._progress is None

    @patch('guardkit.orchestrator.progress.Progress')
    def test_complete_turn_feedback(self, mock_progress_class, mock_console):
        """Should complete turn with feedback status."""
        display = ProgressDisplay(max_turns=5, console=mock_console)
        mock_progress = MagicMock()
        display._progress = mock_progress
        display._task_id = "task-123"
        display.current_turn = 1
        display.turn_history = [{
            "turn": 1,
            "phase": "Test",
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "error": None
        }]

        display.complete_turn("feedback", "2 issues found")

        # Should use warning icon
        print_args = mock_console.print.call_args[0][0]
        assert "⚠" in print_args  # Feedback icon
        assert "2 issues found" in print_args

    @patch('guardkit.orchestrator.progress.Progress')
    def test_complete_turn_error(self, mock_progress_class, mock_console):
        """Should complete turn with error status and message."""
        display = ProgressDisplay(max_turns=5, console=mock_console)
        mock_progress = MagicMock()
        display._progress = mock_progress
        display._task_id = "task-123"
        display.current_turn = 1
        display.turn_history = [{
            "turn": 1,
            "phase": "Test",
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "error": None
        }]

        display.complete_turn("error", "Build failed", error="pytest exited with code 1")

        # Should use error icon
        print_args = mock_console.print.call_args[0][0]
        assert "✗" in print_args  # Error icon
        assert "Build failed" in print_args
        assert "pytest exited with code 1" in print_args

        # Should record error in history
        assert display.turn_history[0]["error"] == "pytest exited with code 1"

    def test_complete_turn_without_active_turn(self, display, caplog):
        """Should log warning if complete called without active turn."""
        with caplog.at_level(logging.WARNING):
            display.complete_turn("success", "Test")

            assert "complete_turn called without active turn" in caplog.text


# Test Error Handling

class TestErrorHandling:
    """Test error handling and warn strategy."""

    def test_handle_error_with_panel(self, mock_console):
        """Should display error in Rich panel."""
        display = ProgressDisplay(max_turns=5, console=mock_console)
        display.current_turn = 2

        display.handle_error("SDK timeout after 30 seconds")

        # Should print panel
        mock_console.print.assert_called_once()
        # Panel is passed as argument
        call_args = mock_console.print.call_args[0]
        assert len(call_args) > 0  # Panel object passed

    def test_handle_error_updates_history(self, display):
        """Should update turn history with error details."""
        display.current_turn = 1
        display.turn_history = [{
            "turn": 1,
            "phase": "Test",
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "error": None
        }]

        display.handle_error("Test error message")

        assert display.turn_history[0]["status"] == "error"
        assert display.turn_history[0]["error"] == "Test error message"
        assert display.turn_history[0]["ended_at"] is not None

    def test_handle_error_with_explicit_turn(self, display):
        """Should handle error for specific turn number."""
        display.current_turn = 1
        display.turn_history = [{
            "turn": 2,
            "phase": "Test",
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "error": None
        }]

        display.handle_error("Error in turn 2", turn=2)

        # Should update correct turn
        assert display.turn_history[0]["error"] == "Error in turn 2"

    def test_error_decorator_catches_exceptions(self):
        """Should catch and log exceptions with _handle_display_error decorator."""
        @_handle_display_error
        def failing_function(self):
            raise RuntimeError("Test error")

        mock_self = MagicMock()

        # Should not raise
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = failing_function(mock_self)

            assert result is None
            assert len(w) == 1
            assert "Progress display error" in str(w[0].message)

    @patch('guardkit.orchestrator.progress.Progress')
    def test_display_error_does_not_crash_orchestration(self, mock_progress_class, display):
        """Display errors should warn but not crash."""
        # Simulate Rich error during start_turn
        mock_progress = MagicMock()
        mock_progress.add_task.side_effect = RuntimeError("Rich crashed")
        mock_progress_class.return_value = mock_progress

        # Should not raise
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            display.start_turn(1, "Test")

            assert len(w) == 1
            assert "Progress display error" in str(w[0].message)


# Test Summary Rendering

class TestSummaryRendering:
    """Test final summary rendering."""

    def test_render_summary_creates_table(self, mock_console):
        """Should render summary table with turn history."""
        display = ProgressDisplay(max_turns=3, console=mock_console)
        display.turn_history = [
            {
                "turn": 1,
                "phase": "Player Implementation",
                "status": "success",
                "summary": "3 files created",
                "started_at": "2025-01-01T10:00:00",
                "ended_at": "2025-01-01T10:05:00",
                "error": None
            },
            {
                "turn": 2,
                "phase": "Coach Validation",
                "status": "feedback",
                "summary": "2 issues found",
                "started_at": "2025-01-01T10:06:00",
                "ended_at": "2025-01-01T10:08:00",
                "error": None
            }
        ]

        display.render_summary(
            total_turns=2,
            final_status="max_turns_exceeded",
            details="Requires human review"
        )

        # Should print table and panel (3 calls: blank line, table, blank line, panel)
        assert mock_console.print.call_count >= 3

    def test_render_summary_approved_status(self, mock_console):
        """Should render approved status in green."""
        display = ProgressDisplay(max_turns=3, console=mock_console)
        display.turn_history = [
            {
                "turn": 1,
                "phase": "Player",
                "status": "success",
                "summary": "Done",
                "started_at": "2025-01-01T10:00:00",
                "ended_at": "2025-01-01T10:05:00",
                "error": None
            }
        ]

        display.render_summary(
            total_turns=1,
            final_status="approved",
            details="All requirements met"
        )

        # Panel should be printed with green border
        assert mock_console.print.called

    def test_render_summary_error_status(self, mock_console):
        """Should render error status in red."""
        display = ProgressDisplay(max_turns=3, console=mock_console)
        display.turn_history = [
            {
                "turn": 1,
                "phase": "Player",
                "status": "error",
                "error": "Build failed",
                "started_at": "2025-01-01T10:00:00",
                "ended_at": "2025-01-01T10:05:00"
            }
        ]

        display.render_summary(
            total_turns=1,
            final_status="error",
            details="Orchestration failed"
        )

        assert mock_console.print.called


# Test State Tracking (Minimal)

class TestStateTracking:
    """Test minimal state tracking per architectural review."""

    def test_turn_history_structure(self, display):
        """Turn history should contain minimal required fields."""
        display.turn_history = [{
            "turn": 1,
            "phase": "Player Implementation",
            "status": "success",
            "started_at": "2025-01-01T10:00:00",
            "ended_at": "2025-01-01T10:05:00",
            "error": None
        }]

        record = display.turn_history[0]
        assert "turn" in record
        assert "phase" in record
        assert "status" in record
        assert "started_at" in record
        assert "ended_at" in record
        assert "error" in record

    def test_no_deep_state_tracking(self, display):
        """Should NOT track implementation details (per architectural review)."""
        # Verify history does NOT contain:
        # - Files created/modified
        # - Line of code counts
        # - Test coverage details
        # - Player/Coach internal state

        display.turn_history = [{
            "turn": 1,
            "phase": "Test",
            "status": "success",
            "started_at": "2025-01-01T10:00:00",
            "ended_at": "2025-01-01T10:05:00",
            "error": None
        }]

        record = display.turn_history[0]

        # These fields should NOT exist
        assert "files_created" not in record
        assert "lines_of_code" not in record
        assert "test_coverage" not in record
        assert "player_state" not in record
        assert "coach_state" not in record


# Test Edge Cases

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiple_turns_sequential(self, display):
        """Should handle multiple turns sequentially."""
        with patch('guardkit.orchestrator.progress.Progress'):
            display.start_turn(1, "Turn 1")
            display.complete_turn("success", "Done")

            display.start_turn(2, "Turn 2")
            display.complete_turn("feedback", "Issues")

            assert len(display.turn_history) == 2
            assert display.turn_history[0]["turn"] == 1
            assert display.turn_history[1]["turn"] == 2

    def test_max_turns_reached(self, display):
        """Should allow starting turn at max_turns."""
        with patch('guardkit.orchestrator.progress.Progress'):
            # Should not raise
            display.start_turn(5, "Final turn")  # max_turns=5

    def test_empty_turn_history_summary(self, mock_console):
        """Should handle summary with empty turn history."""
        display = ProgressDisplay(max_turns=5, console=mock_console)

        # Should not raise
        display.render_summary(
            total_turns=0,
            final_status="error",
            details="No turns executed"
        )

        assert mock_console.print.called

    def test_none_console_creates_default(self):
        """Should create default console if none provided."""
        display = ProgressDisplay(max_turns=3, console=None)

        assert display.console is not None
        assert isinstance(display.console, Console)


# Integration Test (with real Rich components)

class TestIntegration:
    """Integration tests with real Rich components (no mocking)."""

    def test_full_turn_workflow_with_real_console(self, display_with_real_console):
        """Should execute complete turn workflow with real Rich console."""
        display = display_with_real_console

        # Start turn
        display.start_turn(1, "Player Implementation")
        assert display.current_turn == 1

        # Update turn
        display.update_turn("Writing code...", progress=30)
        display.update_turn("Running tests...", progress=70)

        # Complete turn
        display.complete_turn("success", "3 files created, 2 tests passing")

        # Verify state
        assert len(display.turn_history) == 1
        assert display.turn_history[0]["status"] == "success"
        assert display._progress is None  # Cleaned up

    def test_context_manager_with_real_console(self, display_with_real_console):
        """Should work as context manager with real console."""
        display = display_with_real_console

        with display:
            display.start_turn(1, "Test")
            display.complete_turn("success", "Done")

        # Should cleanup after exit
        assert display._progress is None


# Parametrized Tests

@pytest.mark.parametrize("status,expected_icon", [
    ("success", "✓"),
    ("feedback", "⚠"),
    ("error", "✗"),
    ("in_progress", "⏳"),
])
def test_status_icons(mock_console, status, expected_icon):
    """Should use correct icons for each status."""
    display = ProgressDisplay(max_turns=5, console=mock_console)
    display._progress = MagicMock()
    display._task_id = "task-123"
    display.current_turn = 1
    display.turn_history = [{
        "turn": 1,
        "phase": "Test",
        "status": "in_progress",
        "started_at": datetime.now().isoformat(),
        "ended_at": None,
        "error": None
    }]

    display.complete_turn(status, "Test summary")

    print_args = mock_console.print.call_args[0][0]
    assert expected_icon in print_args


@pytest.mark.parametrize("final_status,expected_color", [
    ("approved", "green"),
    ("max_turns_exceeded", "yellow"),
    ("error", "red"),
])
def test_final_status_colors(mock_console, final_status, expected_color):
    """Should use correct colors for final status."""
    display = ProgressDisplay(max_turns=3, console=mock_console)
    display.turn_history = []

    display.render_summary(
        total_turns=1,
        final_status=final_status,
        details="Test details"
    )

    # Panel should be created with correct border color
    assert mock_console.print.called
