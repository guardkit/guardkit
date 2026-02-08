"""
Tests for guardkit review CLI command.

Verifies:
- --capture-knowledge / -ck flag parsing
- Flag triggers run_review_capture() after review
- Review findings passed to run_review_capture()
- Capture results displayed (captured count or skipped/failed)
- Flag optional, defaults to False
- Graceful handling when Graphiti unavailable
- CLI registration in main app

Coverage Target: >=85%
"""

import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from click.testing import CliRunner

from guardkit.cli.review import review, _run_capture


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_task_data():
    """Mock TaskLoader.load_task return value."""
    return {
        "task_id": "TASK-REV-001",
        "requirements": "Review authentication architecture",
        "acceptance_criteria": ["Check SOLID compliance"],
        "frontmatter": {
            "title": "Review auth architecture",
            "status": "in_progress",
            "task_type": "review",
        },
        "content": "# Review\nReview authentication architecture.",
        "file_path": Path("tasks/in_progress/TASK-REV-001.md"),
    }


@pytest.fixture
def mock_capture_result_success():
    """Successful capture result."""
    return {
        "capture_executed": True,
        "task_id": "TASK-REV-001",
        "task_context": {"task_id": "TASK-REV-001"},
        "review_mode": "architectural",
        "findings_count": 2,
    }


@pytest.fixture
def mock_capture_result_skipped():
    """Skipped capture result (Graphiti unavailable)."""
    return {
        "capture_executed": False,
        "task_id": "TASK-REV-001",
        "task_context": {"task_id": "TASK-REV-001"},
        "review_mode": "architectural",
        "findings_count": 0,
        "error": "Graphiti not connected",
    }


# ============================================================================
# Test 1: Flag Parsing
# ============================================================================


class TestFlagParsing:
    """Test --capture-knowledge flag is parsed correctly by Click."""

    def test_capture_knowledge_long_flag(self, runner, mock_task_data):
        """--capture-knowledge flag is accepted."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            result = runner.invoke(
                review, ["TASK-REV-001", "--capture-knowledge"]
            )
            assert result.exit_code == 0, result.output
            mock_capture.assert_called_once()

    def test_capture_knowledge_short_flag(self, runner, mock_task_data):
        """-ck short flag is accepted."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            result = runner.invoke(review, ["TASK-REV-001", "-ck"])
            assert result.exit_code == 0, result.output
            mock_capture.assert_called_once()

    def test_capture_knowledge_default_false(self, runner, mock_task_data):
        """Flag defaults to False (no capture triggered)."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            result = runner.invoke(review, ["TASK-REV-001"])
            assert result.exit_code == 0, result.output
            mock_capture.assert_not_called()


# ============================================================================
# Test 2: Capture Triggering
# ============================================================================


class TestCaptureTrigger:
    """Test that capture is triggered with correct arguments."""

    def test_capture_receives_task_context(self, runner, mock_task_data):
        """run_capture receives task_context with task_id and review_mode."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            runner.invoke(review, ["TASK-REV-001", "-ck"])

            call_args = mock_capture.call_args
            task_context = call_args[0][0]
            assert task_context["task_id"] == "TASK-REV-001"
            assert task_context["review_mode"] == "architectural"

    def test_capture_receives_review_findings(self, runner, mock_task_data):
        """run_capture receives review_findings with mode."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            runner.invoke(
                review, ["TASK-REV-001", "--mode=security", "-ck"]
            )

            call_args = mock_capture.call_args
            review_findings = call_args[0][1]
            assert review_findings["mode"] == "security"

    def test_capture_receives_correct_mode(self, runner, mock_task_data):
        """Different --mode values pass through to capture."""
        modes = [
            "architectural",
            "code-quality",
            "decision",
            "technical-debt",
            "security",
        ]
        for mode in modes:
            with patch(
                "guardkit.cli.review.TaskLoader.load_task",
                return_value=mock_task_data,
            ), patch(
                "guardkit.cli.review._run_capture"
            ) as mock_capture:
                runner.invoke(
                    review, ["TASK-REV-001", f"--mode={mode}", "-ck"]
                )

                call_args = mock_capture.call_args
                task_ctx = call_args[0][0]
                findings = call_args[0][1]
                assert task_ctx["review_mode"] == mode
                assert findings["mode"] == mode


# ============================================================================
# Test 3: Capture Result Display
# ============================================================================


class TestCaptureDisplay:
    """Test capture result display output."""

    def test_displays_success_message(
        self, runner, mock_task_data, mock_capture_result_success
    ):
        """Successful capture shows captured count."""
        async def mock_run_review(*args, **kwargs):
            return mock_capture_result_success

        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession"
        ), patch(
            "guardkit.cli.review.asyncio.run",
            return_value=mock_capture_result_success,
        ):
            result = runner.invoke(review, ["TASK-REV-001", "-ck"])
            assert "Knowledge Capture" in result.output
            assert "Captured" in result.output

    def test_displays_skipped_message_on_error(
        self, runner, mock_task_data, mock_capture_result_skipped
    ):
        """Failed capture shows skipped message."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review.asyncio.run",
            return_value=mock_capture_result_skipped,
        ):
            result = runner.invoke(review, ["TASK-REV-001", "-ck"])
            assert "Knowledge Capture" in result.output
            assert "Skipped" in result.output

    def test_displays_skipped_on_exception(self, runner, mock_task_data):
        """Exception during capture shows skipped message."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review.asyncio.run",
            side_effect=Exception("Connection refused"),
        ):
            result = runner.invoke(review, ["TASK-REV-001", "-ck"])
            assert "Knowledge Capture" in result.output
            assert "Skipped" in result.output
            assert "Connection refused" in result.output


# ============================================================================
# Test 4: Graceful Degradation
# ============================================================================


class TestGracefulDegradation:
    """Test graceful handling when Graphiti unavailable."""

    def test_no_crash_on_import_error(self, runner, mock_task_data):
        """Import error for review_knowledge_capture doesn't crash."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review.asyncio.run",
            side_effect=ImportError("No module named 'graphiti_core'"),
        ):
            result = runner.invoke(review, ["TASK-REV-001", "-ck"])
            assert result.exit_code == 0
            assert "Knowledge Capture" in result.output
            assert "Skipped" in result.output

    def test_no_crash_on_runtime_error(self, runner, mock_task_data):
        """Runtime errors during capture don't crash."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review.asyncio.run",
            side_effect=RuntimeError("Event loop closed"),
        ):
            result = runner.invoke(review, ["TASK-REV-001", "-ck"])
            assert result.exit_code == 0
            assert "Skipped" in result.output


# ============================================================================
# Test 5: _run_capture Unit Tests
# ============================================================================


class TestRunCaptureFunction:
    """Test _run_capture helper function directly."""

    def test_calls_run_review_capture(self, mock_capture_result_success):
        """_run_capture calls run_review_capture with correct args."""
        task_ctx = {"task_id": "TASK-001", "review_mode": "architectural"}
        findings = {"mode": "architectural", "findings": []}

        with patch(
            "guardkit.cli.review.asyncio.run",
            return_value=mock_capture_result_success,
        ) as mock_run:
            _run_capture(task_ctx, findings)
            mock_run.assert_called_once()

    def test_handles_exception_gracefully(self):
        """_run_capture catches exceptions without raising."""
        task_ctx = {"task_id": "TASK-001", "review_mode": "architectural"}
        findings = {"mode": "architectural", "findings": []}

        with patch(
            "guardkit.cli.review.asyncio.run",
            side_effect=Exception("Graphiti unavailable"),
        ):
            # Should not raise
            _run_capture(task_ctx, findings)


# ============================================================================
# Test 6: CLI Registration
# ============================================================================


class TestCLIRegistration:
    """Test that review command is registered in main CLI."""

    def test_review_registered_in_cli(self):
        """Review command is accessible from main CLI group."""
        from guardkit.cli.main import cli

        commands = cli.commands if hasattr(cli, "commands") else {}
        assert "review" in commands, (
            f"'review' not found in CLI commands: {list(commands.keys())}"
        )

    def test_review_help_shows_capture_flag(self, runner):
        """--help output shows --capture-knowledge flag."""
        result = runner.invoke(review, ["--help"])
        assert "--capture-knowledge" in result.output
        assert "-ck" in result.output


# ============================================================================
# Test 7: Mode and Depth Options
# ============================================================================


class TestModeAndDepthOptions:
    """Test --mode and --depth options work correctly."""

    def test_invalid_mode_rejected(self, runner, mock_task_data):
        """Invalid --mode value is rejected by Click."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(
                review, ["TASK-REV-001", "--mode=invalid"]
            )
            assert result.exit_code != 0

    def test_invalid_depth_rejected(self, runner, mock_task_data):
        """Invalid --depth value is rejected by Click."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(
                review, ["TASK-REV-001", "--depth=invalid"]
            )
            assert result.exit_code != 0

    def test_depth_passed_to_context(self, runner, mock_task_data):
        """--depth value passes through to task context."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            runner.invoke(
                review,
                ["TASK-REV-001", "--depth=comprehensive", "-ck"],
            )
            call_args = mock_capture.call_args
            task_ctx = call_args[0][0]
            assert task_ctx["depth"] == "comprehensive"

    def test_default_mode_is_architectural(self, runner, mock_task_data):
        """Default mode is architectural."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            runner.invoke(review, ["TASK-REV-001", "-ck"])
            call_args = mock_capture.call_args
            task_ctx = call_args[0][0]
            assert task_ctx["review_mode"] == "architectural"

    def test_default_depth_is_standard(self, runner, mock_task_data):
        """Default depth is standard."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            runner.invoke(review, ["TASK-REV-001", "-ck"])
            call_args = mock_capture.call_args
            task_ctx = call_args[0][0]
            assert task_ctx["depth"] == "standard"


# ============================================================================
# Test 8: Enable Context Flag (TASK-FIX-GCI7)
# ============================================================================


class TestEnableContextFlag:
    """Test --enable-context/--no-context flag for Graphiti context control."""

    def test_enable_context_defaults_to_true(self, runner, mock_task_data):
        """--enable-context defaults to True."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(review, ["TASK-REV-001"])
            assert result.exit_code == 0, result.output
            # No "Disabled" message should appear
            assert "Disabled" not in result.output

    def test_no_context_flag_accepted(self, runner, mock_task_data):
        """--no-context flag is accepted by Click."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(review, ["TASK-REV-001", "--no-context"])
            assert result.exit_code == 0, result.output

    def test_enable_context_flag_accepted(self, runner, mock_task_data):
        """--enable-context flag is accepted by Click."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(
                review, ["TASK-REV-001", "--enable-context"]
            )
            assert result.exit_code == 0, result.output

    def test_no_context_shows_disabled_message(self, runner, mock_task_data):
        """--no-context shows 'Disabled' in output."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(review, ["TASK-REV-001", "--no-context"])
            assert "Disabled" in result.output

    def test_no_context_suppresses_capture_knowledge(
        self, runner, mock_task_data
    ):
        """--no-context suppresses --capture-knowledge (can't write without Graphiti)."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            result = runner.invoke(
                review, ["TASK-REV-001", "--no-context", "-ck"]
            )
            assert result.exit_code == 0, result.output
            # _run_capture should NOT be called when context is disabled
            mock_capture.assert_not_called()

    def test_enable_context_stored_in_task_context(
        self, runner, mock_task_data
    ):
        """enable_context value is stored in task_context for downstream use."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ), patch(
            "guardkit.cli.review._run_capture"
        ) as mock_capture:
            runner.invoke(review, ["TASK-REV-001", "-ck"])
            call_args = mock_capture.call_args
            task_ctx = call_args[0][0]
            assert task_ctx["enable_context"] is True

    def test_no_context_stored_in_task_context(self, runner, mock_task_data):
        """enable_context=False is stored in task_context when --no-context used."""
        # Since --no-context suppresses capture, we need to check via the
        # display output instead
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(review, ["TASK-REV-001", "--no-context"])
            assert result.exit_code == 0
            assert "Disabled" in result.output

    def test_help_shows_enable_context_flag(self, runner):
        """--help output shows --enable-context/--no-context flag."""
        result = runner.invoke(review, ["--help"])
        assert "--enable-context" in result.output
        assert "--no-context" in result.output
