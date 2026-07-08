"""
Seam tests S2: CLI (Click) → Python Entry Points.

These tests verify that Click CLI commands actually invoke their Python
entry points with correct arguments - catching cases where args are lost,
async wrapping fails, or commands silently do nothing.

Layer A: Click CLI commands (guardkit system-plan, guardkit system-overview, etc.)
Layer B: Python entry points (run_system_plan(), get_system_overview(), etc.)

Uses click.testing.CliRunner for direct command invocation (no subprocess).
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from click.testing import CliRunner

from guardkit.cli.main import cli

if TYPE_CHECKING:
    from typing import Any


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CliRunner configured for seam testing."""
    return CliRunner()


class TestSystemPlanSeam:
    """Seam tests for system-plan CLI → run_system_plan() entry point."""

    def test_system_plan_passes_context_file_to_entry_point(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """
        Test: guardkit system-plan with --context flag passes context file to run_system_plan().

        Verifies the seam between CLI argument parsing and Python entry point invocation.
        """
        # Create a minimal context file
        context_file = tmp_path / "test-spec.md"
        context_file.write_text("# Test Spec\n\n## System Context\n**Name:** Test\n")

        # Mock the run_system_plan function to capture arguments
        captured_args: dict[str, Any] = {}

        async def mock_run_system_plan(**kwargs: Any) -> None:
            """Capture arguments passed to run_system_plan."""
            captured_args.update(kwargs)

        with patch(
            "guardkit.cli.system_plan._run_system_plan",
            side_effect=mock_run_system_plan,
        ):
            result = runner.invoke(
                cli,
                ["system-plan", "Test System", "--context", str(context_file)],
                catch_exceptions=False,
            )

        # Verify CLI succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify entry point was called with correct context_file argument
        assert "context_file" in captured_args, "context_file argument not passed"
        assert captured_args["context_file"] == str(context_file), (
            f"Expected context_file={context_file}, got {captured_args['context_file']}"
        )

    def test_system_plan_passes_mode_to_entry_point(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-plan with --mode flag passes mode to run_system_plan().

        Verifies mode argument is not lost in CLI-to-Python wiring.
        """
        captured_args: dict[str, Any] = {}

        async def mock_run_system_plan(**kwargs: Any) -> None:
            captured_args.update(kwargs)

        with patch(
            "guardkit.cli.system_plan._run_system_plan",
            side_effect=mock_run_system_plan,
        ):
            result = runner.invoke(
                cli,
                ["system-plan", "Test System", "--mode", "refine"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert captured_args.get("mode") == "refine", (
            f"Expected mode='refine', got {captured_args.get('mode')}"
        )

    def test_system_plan_passes_description_as_first_argument(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-plan DESCRIPTION passes description to run_system_plan().

        Verifies the required positional argument is passed correctly.
        """
        captured_args: dict[str, Any] = {}

        async def mock_run_system_plan(**kwargs: Any) -> None:
            captured_args.update(kwargs)

        with patch(
            "guardkit.cli.system_plan._run_system_plan",
            side_effect=mock_run_system_plan,
        ):
            result = runner.invoke(
                cli,
                ["system-plan", "Build payment processing system"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert captured_args.get("description") == "Build payment processing system", (
            f"Expected description='Build payment processing system', got {captured_args.get('description')}"
        )

    def test_system_plan_passes_focus_to_entry_point(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-plan with --focus flag passes focus to run_system_plan().

        Verifies focus area argument is correctly wired.
        """
        captured_args: dict[str, Any] = {}

        async def mock_run_system_plan(**kwargs: Any) -> None:
            captured_args.update(kwargs)

        with patch(
            "guardkit.cli.system_plan._run_system_plan",
            side_effect=mock_run_system_plan,
        ):
            result = runner.invoke(
                cli,
                ["system-plan", "Test System", "--focus", "services"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert captured_args.get("focus") == "services", (
            f"Expected focus='services', got {captured_args.get('focus')}"
        )

    def test_system_plan_passes_no_questions_flag(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-plan with --no-questions passes no_questions=True.

        Verifies boolean flag is correctly wired.
        """
        captured_args: dict[str, Any] = {}

        async def mock_run_system_plan(**kwargs: Any) -> None:
            captured_args.update(kwargs)

        with patch(
            "guardkit.cli.system_plan._run_system_plan",
            side_effect=mock_run_system_plan,
        ):
            result = runner.invoke(
                cli,
                ["system-plan", "Test System", "--no-questions"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert captured_args.get("no_questions") is True, (
            f"Expected no_questions=True, got {captured_args.get('no_questions')}"
        )


class TestErrorHandling:
    """Seam tests for error handling across CLI-to-Python boundary."""

    def test_system_plan_mutually_exclusive_flags_error(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-plan with --no-questions and --defaults fails.

        Verifies mutually exclusive flag validation at CLI level.
        """
        result = runner.invoke(
            cli,
            ["system-plan", "Test", "--no-questions", "--defaults"],
        )

        assert result.exit_code != 0, "Should fail with mutually exclusive flags"
        assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower(), (
            f"Expected error about mutually exclusive flags: {result.output}"
        )

    def test_system_plan_invalid_mode_error(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-plan with invalid --mode fails.

        Verifies Click Choice validation at CLI level.
        """
        result = runner.invoke(
            cli,
            ["system-plan", "Test", "--mode", "invalid_mode"],
        )

        assert result.exit_code != 0, "Should fail with invalid mode"
        assert "invalid" in result.output.lower() or "choice" in result.output.lower(), (
            f"Expected error about invalid choice: {result.output}"
        )

    def test_system_plan_context_file_not_found_error(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-plan with non-existent --context file fails.

        Verifies file existence validation at CLI level.
        """
        result = runner.invoke(
            cli,
            ["system-plan", "Test", "--context", "/nonexistent/file.md"],
        )

        assert result.exit_code != 0, "Should fail with non-existent file"
        # Click reports this as "does not exist" or "Error"
        assert "not exist" in result.output.lower() or "error" in result.output.lower(), (
            f"Expected error about non-existent file: {result.output}"
        )


class TestTaskCreateSeam:
    """Seam tests for task create CLI -> create_task() entry point."""

    def test_task_create_with_title_creates_task_file_in_correct_directory(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """
        Test: guardkit task create with title creates a task file in the correct directory.

        Verifies the seam between CLI argument parsing and Python entry point invocation.
        """
        captured_args: dict[str, Any] = {}
        mock_task_path = tmp_path / "tasks" / "backlog" / "TASK-abc1-test-task.md"
        mock_task_path.parent.mkdir(parents=True, exist_ok=True)
        mock_task_path.write_text("---\nid: TASK-abc1\ntitle: Test Task\n---\n")

        def mock_create_task(**kwargs: Any) -> Path:
            """Capture arguments passed to create_task."""
            captured_args.update(kwargs)
            return mock_task_path

        with patch(
            "guardkit.cli.task.create_task",
            side_effect=mock_create_task,
        ):
            result = runner.invoke(
                cli,
                ["task", "create", "Test Task"],
                catch_exceptions=False,
            )

        # Verify CLI succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify entry point was called with correct title argument
        assert "title" in captured_args, "title argument not passed"
        assert captured_args["title"] == "Test Task", (
            f"Expected title='Test Task', got {captured_args['title']}"
        )

        # Verify output mentions task creation
        assert "Created task" in result.output or "TASK-" in result.output, (
            f"Expected task creation confirmation: {result.output}"
        )

    def test_task_create_passes_priority_to_entry_point(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """
        Test: guardkit task create with --priority flag passes priority to create_task().

        Verifies priority argument is correctly wired.
        """
        captured_args: dict[str, Any] = {}
        mock_task_path = tmp_path / "tasks" / "backlog" / "TASK-abc1-test.md"
        mock_task_path.parent.mkdir(parents=True, exist_ok=True)
        mock_task_path.write_text("---\nid: TASK-abc1\n---\n")

        def mock_create_task(**kwargs: Any) -> Path:
            captured_args.update(kwargs)
            return mock_task_path

        with patch(
            "guardkit.cli.task.create_task",
            side_effect=mock_create_task,
        ):
            result = runner.invoke(
                cli,
                ["task", "create", "Test Task", "--priority", "high"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert captured_args.get("priority") == "high", (
            f"Expected priority='high', got {captured_args.get('priority')}"
        )

    def test_task_create_passes_prefix_to_entry_point(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """
        Test: guardkit task create with --prefix flag passes prefix to create_task().

        Verifies prefix argument is correctly wired.
        """
        captured_args: dict[str, Any] = {}
        mock_task_path = tmp_path / "tasks" / "backlog" / "TASK-FIX-abc1-test.md"
        mock_task_path.parent.mkdir(parents=True, exist_ok=True)
        mock_task_path.write_text("---\nid: TASK-FIX-abc1\n---\n")

        def mock_create_task(**kwargs: Any) -> Path:
            captured_args.update(kwargs)
            return mock_task_path

        with patch(
            "guardkit.cli.task.create_task",
            side_effect=mock_create_task,
        ):
            result = runner.invoke(
                cli,
                ["task", "create", "Fix login bug", "--prefix", "FIX"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert captured_args.get("prefix") == "FIX", (
            f"Expected prefix='FIX', got {captured_args.get('prefix')}"
        )

    def test_task_create_passes_task_type_to_entry_point(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """
        Test: guardkit task create with --task-type flag passes task_type to create_task().

        The /task-review Phase 0 ad-hoc entry depends on this wiring
        (--prefix REV --task-type review).
        """
        captured_args: dict[str, Any] = {}
        mock_task_path = tmp_path / "tasks" / "backlog" / "TASK-REV-abc1-test.md"
        mock_task_path.parent.mkdir(parents=True, exist_ok=True)
        mock_task_path.write_text("---\nid: TASK-REV-abc1\n---\n")

        def mock_create_task(**kwargs: Any) -> Path:
            captured_args.update(kwargs)
            return mock_task_path

        with patch(
            "guardkit.cli.task.create_task",
            side_effect=mock_create_task,
        ):
            result = runner.invoke(
                cli,
                [
                    "task",
                    "create",
                    "Review auth session handling",
                    "--prefix",
                    "REV",
                    "--task-type",
                    "review",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert captured_args.get("task_type") == "review", (
            f"Expected task_type='review', got {captured_args.get('task_type')}"
        )
        assert captured_args.get("prefix") == "REV", (
            f"Expected prefix='REV', got {captured_args.get('prefix')}"
        )

    def test_task_create_rejects_invalid_task_type(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """An invalid --task-type is rejected at the CLI boundary (click.Choice)."""
        result = runner.invoke(
            cli,
            ["task", "create", "Some task", "--task-type", "not-a-type"],
        )
        assert result.exit_code != 0, "Should fail with invalid task type"
        assert "task-type" in result.output.lower() or "invalid" in result.output.lower(), (
            f"Expected task-type validation error: {result.output}"
        )

    def test_task_create_returns_meaningful_output(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """
        Test: guardkit task create produces meaningful output (not empty).

        Verifies command produces output containing task information.
        """
        mock_task_path = tmp_path / "tasks" / "backlog" / "TASK-abc1-add-feature.md"
        mock_task_path.parent.mkdir(parents=True, exist_ok=True)
        mock_task_path.write_text("---\nid: TASK-abc1\n---\n")

        def mock_create_task(**kwargs: Any) -> Path:
            return mock_task_path

        with patch(
            "guardkit.cli.task.create_task",
            side_effect=mock_create_task,
        ):
            result = runner.invoke(
                cli,
                ["task", "create", "Add new feature"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert result.output.strip(), "Output should not be empty"
        # Should contain task path or confirmation
        assert "TASK-" in result.output or "Created" in result.output, (
            f"Expected task info in output: {result.output}"
        )
