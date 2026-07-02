"""
Tests for guardkit review CLI command.

Verifies (post-FEAT-MEM-09 graphiti-code cutover; knowledge capture removed):
- Review loads the task (exit code 1 if not found)
- Mode / depth options parse and validate
- --enable-context/--no-context flag behavior
- CLI registration in main app

Coverage Target: >=85%
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from guardkit.cli.review import review


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


# ============================================================================
# Test 1: Task Loading
# ============================================================================


class TestTaskLoading:
    """Test that review loads the task and displays context."""

    def test_review_loads_task(self, runner, mock_task_data):
        """review loads the task and exits 0 when found."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ) as mock_load:
            result = runner.invoke(review, ["TASK-REV-001"])
            assert result.exit_code == 0, result.output
            mock_load.assert_called_once()

    def test_review_displays_task_id(self, runner, mock_task_data):
        """review displays the task id in its output."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(review, ["TASK-REV-001"])
            assert result.exit_code == 0, result.output
            assert "TASK-REV-001" in result.output

    def test_review_displays_mode_and_depth(self, runner, mock_task_data):
        """review displays the review mode and depth."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(
                review,
                ["TASK-REV-001", "--mode=security", "--depth=comprehensive"],
            )
            assert result.exit_code == 0, result.output
            assert "security" in result.output
            assert "comprehensive" in result.output

    def test_review_task_not_found_exits_1(self, runner):
        """review exits with code 1 when the task cannot be loaded."""
        from guardkit.tasks.task_loader import TaskNotFoundError

        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            side_effect=TaskNotFoundError("Task TASK-REV-999 not found"),
        ):
            result = runner.invoke(review, ["TASK-REV-999"])
            assert result.exit_code == 1


# ============================================================================
# Test 2: CLI Registration
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


# ============================================================================
# Test 3: Mode and Depth Options
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

    def test_default_mode_is_architectural(self, runner, mock_task_data):
        """Default mode is architectural (shown in output)."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(review, ["TASK-REV-001"])
            assert result.exit_code == 0, result.output
            assert "architectural" in result.output

    def test_default_depth_is_standard(self, runner, mock_task_data):
        """Default depth is standard (shown in output)."""
        with patch(
            "guardkit.cli.review.TaskLoader.load_task",
            return_value=mock_task_data,
        ):
            result = runner.invoke(review, ["TASK-REV-001"])
            assert result.exit_code == 0, result.output
            assert "standard" in result.output


# ============================================================================
# Test 4: Enable Context Flag (TASK-FIX-GCI7)
# ============================================================================


class TestEnableContextFlag:
    """Test --enable-context/--no-context flag for memory context control."""

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

    def test_help_shows_enable_context_flag(self, runner):
        """--help output shows --enable-context/--no-context flag."""
        result = runner.invoke(review, ["--help"])
        assert "--enable-context" in result.output
        assert "--no-context" in result.output
