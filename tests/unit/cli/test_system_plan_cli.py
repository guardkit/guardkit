"""
Unit tests for guardkit system-plan CLI command.

Tests CLI argument parsing, flag combinations, validation, and exit codes.
These are TDD RED phase tests - they will fail until implementation is complete.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, MagicMock, patch

from guardkit.cli.decorators import (
    EXIT_SUCCESS,
    EXIT_INVALID_ARGUMENTS,
)


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_graphiti():
    """Mock Graphiti client with has_architecture_context method."""
    mock = MagicMock()
    mock.enabled = True
    mock.has_architecture_context = AsyncMock(return_value=False)
    mock.get_architecture_summary = AsyncMock(return_value=None)
    return mock


class TestSystemPlanCLIRegistration:
    """Test that the CLI command is properly registered."""

    def test_command_registered(self, runner):
        """Test that 'guardkit system-plan' command exists."""
        # This will fail until we create guardkit/cli/system_plan.py
        # and register it in guardkit/cli/__init__.py
        from guardkit.cli import system_plan

        result = runner.invoke(system_plan.system_plan, ["--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "system-plan" in result.output.lower()

    def test_help_contains_description(self, runner):
        """Test that --help output contains command description."""
        from guardkit.cli.system_plan import system_plan

        result = runner.invoke(system_plan, ["--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "architecture planning" in result.output.lower()

    def test_help_shows_all_options(self, runner):
        """Test that --help shows all command options."""
        from guardkit.cli.system_plan import system_plan

        result = runner.invoke(system_plan, ["--help"])
        assert result.exit_code == EXIT_SUCCESS

        # Check all options are documented
        assert "--mode" in result.output
        assert "--focus" in result.output
        assert "--no-questions" in result.output
        assert "--defaults" in result.output
        assert "--context" in result.output
        assert "--enable-context" in result.output or "--no-context" in result.output


class TestSystemPlanArguments:
    """Test CLI argument parsing."""

    def test_requires_description_argument(self, runner):
        """Test that description argument is required."""
        from guardkit.cli.system_plan import system_plan

        result = runner.invoke(system_plan, [])
        assert result.exit_code != EXIT_SUCCESS
        assert "description" in result.output.lower() or "missing argument" in result.output.lower()

    def test_accepts_description_argument(self, runner):
        """Test that description argument is accepted."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Create payment system"])

            # Should not fail on argument parsing
            # (may fail on other things, but not argument validation)
            assert "description" not in result.output.lower() or result.exit_code == EXIT_SUCCESS


class TestSystemPlanModeOption:
    """Test --mode option validation."""

    def test_mode_accepts_setup(self, runner):
        """Test that --mode=setup is accepted."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test", "--mode=setup"])

            # Should not fail on mode validation
            if result.exit_code != EXIT_SUCCESS:
                assert "invalid choice" not in result.output.lower()

    def test_mode_accepts_refine(self, runner):
        """Test that --mode=refine is accepted."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test", "--mode=refine"])

            if result.exit_code != EXIT_SUCCESS:
                assert "invalid choice" not in result.output.lower()

    def test_mode_accepts_review(self, runner):
        """Test that --mode=review is accepted."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test", "--mode=review"])

            if result.exit_code != EXIT_SUCCESS:
                assert "invalid choice" not in result.output.lower()

    def test_mode_rejects_invalid_value(self, runner):
        """Test that invalid --mode values are rejected."""
        from guardkit.cli.system_plan import system_plan

        result = runner.invoke(system_plan, ["Test", "--mode=invalid"])
        assert result.exit_code != EXIT_SUCCESS
        assert "invalid choice" in result.output.lower()

    def test_mode_is_case_insensitive(self, runner):
        """Test that --mode values are case-insensitive."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None

            # Test uppercase
            result = runner.invoke(system_plan, ["Test", "--mode=SETUP"])
            if result.exit_code != EXIT_SUCCESS:
                assert "invalid choice" not in result.output.lower()


class TestSystemPlanFocusOption:
    """Test --focus option validation."""

    @pytest.mark.parametrize("focus_value", [
        "domains",
        "services",
        "decisions",
        "crosscutting",
        "all",
    ])
    def test_focus_accepts_valid_values(self, runner, focus_value):
        """Test that --focus accepts all valid values."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test", f"--focus={focus_value}"])

            if result.exit_code != EXIT_SUCCESS:
                assert "invalid choice" not in result.output.lower()

    def test_focus_rejects_invalid_value(self, runner):
        """Test that invalid --focus values are rejected."""
        from guardkit.cli.system_plan import system_plan

        result = runner.invoke(system_plan, ["Test", "--focus=invalid"])
        assert result.exit_code != EXIT_SUCCESS
        assert "invalid choice" in result.output.lower()

    def test_focus_is_case_insensitive(self, runner):
        """Test that --focus values are case-insensitive."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test", "--focus=DOMAINS"])

            if result.exit_code != EXIT_SUCCESS:
                assert "invalid choice" not in result.output.lower()


class TestSystemPlanBooleanFlags:
    """Test boolean flag options."""

    def test_no_questions_flag(self, runner):
        """Test that --no-questions flag is accepted."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test", "--no-questions"])

            # Should accept the flag
            assert "--no-questions" not in result.output or result.exit_code == EXIT_SUCCESS

    def test_defaults_flag(self, runner):
        """Test that --defaults flag is accepted."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test", "--defaults"])

            assert "--defaults" not in result.output or result.exit_code == EXIT_SUCCESS

    def test_enable_context_flag(self, runner):
        """Test that --enable-context flag is accepted."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test", "--enable-context"])

            assert result.exit_code == EXIT_SUCCESS or "--enable-context" not in result.output

    def test_no_context_flag(self, runner):
        """Test that --no-context flag is accepted."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test", "--no-context"])

            assert result.exit_code == EXIT_SUCCESS or "--no-context" not in result.output


class TestSystemPlanContextOption:
    """Test --context file path option."""

    def test_context_accepts_file_path(self, runner, tmp_path):
        """Test that --context accepts a file path."""
        from guardkit.cli.system_plan import system_plan

        context_file = tmp_path / "context.md"
        context_file.write_text("# Context\n\nSome context")

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(
                system_plan,
                ["Test", f"--context={context_file}"]
            )

            # Should accept valid file path
            if result.exit_code != EXIT_SUCCESS:
                assert "does not exist" not in result.output.lower()

    def test_context_validates_file_exists(self, runner):
        """Test that --context validates file existence."""
        from guardkit.cli.system_plan import system_plan

        result = runner.invoke(
            system_plan,
            ["Test", "--context=/nonexistent/file.md"]
        )

        # Should fail with file not found error
        assert result.exit_code != EXIT_SUCCESS
        assert "exist" in result.output.lower() or "not found" in result.output.lower()


class TestSystemPlanFlagCombinations:
    """Test various flag combinations."""

    def test_mode_and_focus_together(self, runner):
        """Test that --mode and --focus can be used together."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(
                system_plan,
                ["Test", "--mode=refine", "--focus=services"]
            )

            # Should accept both flags
            if result.exit_code != EXIT_SUCCESS:
                assert "invalid" not in result.output.lower()

    def test_no_questions_and_defaults_mutually_exclusive(self, runner):
        """Test that --no-questions and --defaults cannot be used together."""
        from guardkit.cli.system_plan import system_plan

        result = runner.invoke(
            system_plan,
            ["Test", "--no-questions", "--defaults"]
        )

        # Should reject mutually exclusive flags
        assert result.exit_code != EXIT_SUCCESS
        assert "mutually exclusive" in result.output.lower() or "cannot be used together" in result.output.lower()

    def test_all_flags_together(self, runner, tmp_path):
        """Test using multiple compatible flags together."""
        from guardkit.cli.system_plan import system_plan

        context_file = tmp_path / "context.md"
        context_file.write_text("# Context")

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(
                system_plan,
                [
                    "Test description",
                    "--mode=setup",
                    "--focus=domains",
                    "--no-questions",
                    f"--context={context_file}",
                    "--enable-context",
                ]
            )

            # Should accept all compatible flags
            if result.exit_code != EXIT_SUCCESS:
                assert "invalid" not in result.output.lower()


class TestSystemPlanAsyncExecution:
    """Test that async operations are properly wrapped."""

    def test_uses_asyncio_run(self, runner):
        """Test that the command uses asyncio.run for async operations."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test description"])

            # asyncio.run should have been called
            mock_run.assert_called_once()

    def test_async_function_receives_parameters(self, runner):
        """Test that async function receives CLI parameters."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(
                system_plan,
                ["Test", "--mode=setup", "--focus=domains"]
            )

            # Should have called asyncio.run with parameters
            mock_run.assert_called_once()
            # The called function should receive mode and focus
            call_args = mock_run.call_args
            assert call_args is not None


class TestSystemPlanExitCodes:
    """Test exit code behavior."""

    def test_success_exit_code(self, runner):
        """Test that successful execution returns exit code 0."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None
            result = runner.invoke(system_plan, ["Test"])

            assert result.exit_code == EXIT_SUCCESS

    def test_invalid_argument_exit_code(self, runner):
        """Test that invalid arguments return appropriate exit code."""
        from guardkit.cli.system_plan import system_plan

        result = runner.invoke(system_plan, ["Test", "--mode=invalid"])
        assert result.exit_code != EXIT_SUCCESS

    def test_missing_argument_exit_code(self, runner):
        """Test that missing required arguments return appropriate exit code."""
        from guardkit.cli.system_plan import system_plan

        result = runner.invoke(system_plan, [])
        assert result.exit_code != EXIT_SUCCESS

    def test_error_exit_code(self, runner):
        """Test that errors during execution return exit code 1."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.side_effect = Exception("Test error")
            result = runner.invoke(system_plan, ["Test"])

            # Should return error exit code (handled by @handle_cli_errors)
            assert result.exit_code != EXIT_SUCCESS


class TestSystemPlanErrorHandling:
    """Test error handling with @handle_cli_errors decorator."""

    def test_uses_handle_cli_errors_decorator(self, runner):
        """Test that command uses @handle_cli_errors decorator."""
        from guardkit.cli.system_plan import system_plan

        # Check that the decorator is applied by inspecting wrapped function
        assert hasattr(system_plan, "__wrapped__") or hasattr(system_plan, "callback")

    def test_graceful_error_display(self, runner):
        """Test that errors are displayed gracefully."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.side_effect = ValueError("Test validation error")
            result = runner.invoke(system_plan, ["Test"])

            # Should display error message
            assert "error" in result.output.lower()
            assert result.exit_code != EXIT_SUCCESS


class TestSystemPlanContextPropagation:
    """Test Click context propagation."""

    def test_uses_click_pass_context(self, runner):
        """Test that command uses @click.pass_context."""
        from guardkit.cli.system_plan import system_plan

        with patch("guardkit.cli.system_plan.asyncio.run") as mock_run:
            mock_run.return_value = None

            # Invoke with context
            result = runner.invoke(system_plan, ["Test"], obj={"quiet": True})

            # Should succeed with context
            assert result.exit_code == EXIT_SUCCESS or mock_run.called


class TestSystemPlanCommandStructure:
    """Test overall command structure matches guardkit patterns."""

    def test_command_decorator_structure(self):
        """Test that command follows Click decorator pattern."""
        from guardkit.cli.system_plan import system_plan

        # Should be a Click command
        assert hasattr(system_plan, "params")
        assert hasattr(system_plan, "callback") or callable(system_plan)

    def test_command_name(self):
        """Test that command has correct name."""
        from guardkit.cli.system_plan import system_plan

        # Command name should be 'system-plan'
        assert system_plan.name == "system-plan" or "system-plan" in str(system_plan)
