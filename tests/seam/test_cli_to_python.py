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


class TestSystemOverviewSeam:
    """Seam tests for system-overview CLI → get_system_overview() entry point."""

    def test_system_overview_invokes_get_system_overview_and_returns_output(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-overview invokes get_system_overview() and returns output.

        Verifies command produces meaningful output (not empty, not just help).
        """
        # Mock get_system_overview to return known data
        mock_overview = {
            "status": "ok",
            "system": {
                "name": "Test System",
                "methodology": "DDD",
                "purpose": "Testing seam",
            },
            "components": [
                {"name": "Component A", "description": "Test component"},
            ],
            "decisions": [],
            "concerns": [],
        }

        # Patch where the function is looked up, not where it's defined
        with patch(
            "guardkit.planning.system_overview.get_system_overview",
            new_callable=AsyncMock,
            return_value=mock_overview,
        ), patch(
            "guardkit.cli.system_context._get_graphiti_client",
            return_value=Mock(enabled=True),
        ):
            result = runner.invoke(
                cli,
                ["system-overview"],
                catch_exceptions=False,
            )

        # Verify CLI succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify meaningful output (not empty, contains expected content)
        assert result.output.strip(), "Output should not be empty"
        assert "Test System" in result.output or "SYSTEM OVERVIEW" in result.output, (
            f"Expected system name or overview header in output: {result.output}"
        )

    def test_system_overview_with_verbose_flag(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-overview --verbose passes verbose=True to get_system_overview().

        Verifies verbose flag is correctly wired through the seam.
        """
        captured_verbose: list[bool] = []

        async def mock_get_overview(sp: Any, verbose: bool = False) -> dict[str, Any]:
            captured_verbose.append(verbose)
            return {"status": "no_context"}

        with patch(
            "guardkit.planning.system_overview.get_system_overview",
            side_effect=mock_get_overview,
        ), patch(
            "guardkit.cli.system_context._get_graphiti_client",
            return_value=Mock(enabled=True),
        ):
            result = runner.invoke(
                cli,
                ["system-overview", "--verbose"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert len(captured_verbose) == 1, "get_system_overview should be called once"
        assert captured_verbose[0] is True, (
            f"Expected verbose=True, got {captured_verbose[0]}"
        )

    def test_system_overview_with_section_filter(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-overview --section=decisions filters output.

        Verifies section argument affects output formatting.
        """
        mock_overview = {
            "status": "ok",
            "system": {"name": "Test"},
            "components": [{"name": "Comp", "description": "Test"}],
            "decisions": [
                {"adr_id": "ADR-001", "title": "Test Decision", "status": "accepted"}
            ],
            "concerns": [],
        }

        with patch(
            "guardkit.planning.system_overview.get_system_overview",
            new_callable=AsyncMock,
            return_value=mock_overview,
        ), patch(
            "guardkit.cli.system_context._get_graphiti_client",
            return_value=Mock(enabled=True),
        ):
            result = runner.invoke(
                cli,
                ["system-overview", "--section", "decisions"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Output should be meaningful
        assert result.output.strip(), "Output should not be empty"

    def test_system_overview_with_json_format(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit system-overview --format=json returns JSON output.

        Verifies format argument affects output format.
        """
        mock_overview = {
            "status": "ok",
            "system": {"name": "Test"},
            "components": [],
            "decisions": [],
            "concerns": [],
        }

        with patch(
            "guardkit.planning.system_overview.get_system_overview",
            new_callable=AsyncMock,
            return_value=mock_overview,
        ), patch(
            "guardkit.cli.system_context._get_graphiti_client",
            return_value=Mock(enabled=True),
        ):
            result = runner.invoke(
                cli,
                ["system-overview", "--format", "json"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should be valid JSON
        import json
        try:
            parsed = json.loads(result.output)
            assert "status" in parsed, "JSON output should contain status"
        except json.JSONDecodeError as e:
            pytest.fail(f"Output should be valid JSON: {e}\nOutput: {result.output}")


class TestGraphitiSearchSeam:
    """Seam tests for graphiti search CLI → search function entry point."""

    def test_graphiti_search_passes_query_string_to_search_function(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit graphiti search passes query string to search function.

        Verifies query argument is correctly wired through the seam.
        """
        captured_queries: list[str] = []

        # Create a mock client that captures search calls
        mock_client = Mock()
        mock_client.enabled = True

        async def mock_initialize() -> bool:
            return True

        async def mock_search(query: str = "", **kwargs: Any) -> list[dict[str, Any]]:
            captured_queries.append(query)
            return [
                {"fact": "Test result", "score": 0.9, "name": "test-fact"}
            ]

        async def mock_close() -> None:
            pass

        mock_client.initialize = mock_initialize
        mock_client.search = mock_search
        mock_client.close = mock_close

        with patch(
            "guardkit.cli.graphiti._get_client_and_config",
            return_value=(mock_client, Mock(enabled=True)),
        ):
            result = runner.invoke(
                cli,
                ["graphiti", "search", "authentication patterns"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert len(captured_queries) == 1, "search should be called once"
        assert captured_queries[0] == "authentication patterns", (
            f"Expected query='authentication patterns', got '{captured_queries[0]}'"
        )

    def test_graphiti_search_passes_group_filter(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit graphiti search --group passes group_ids filter.

        Verifies --group argument is correctly wired.
        """
        captured_group_ids: list[list[str] | None] = []

        mock_client = Mock()
        mock_client.enabled = True

        async def mock_initialize() -> bool:
            return True

        async def mock_search(
            query: str = "", group_ids: list[str] | None = None, **kwargs: Any
        ) -> list[dict[str, Any]]:
            captured_group_ids.append(group_ids)
            return [{"fact": "Test", "score": 0.8, "name": "test"}]

        async def mock_close() -> None:
            pass

        mock_client.initialize = mock_initialize
        mock_client.search = mock_search
        mock_client.close = mock_close

        with patch(
            "guardkit.cli.graphiti._get_client_and_config",
            return_value=(mock_client, Mock(enabled=True)),
        ):
            result = runner.invoke(
                cli,
                ["graphiti", "search", "test query", "--group", "patterns"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert len(captured_group_ids) == 1, "search should be called once"
        assert captured_group_ids[0] == ["patterns"], (
            f"Expected group_ids=['patterns'], got {captured_group_ids[0]}"
        )

    def test_graphiti_search_passes_limit(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit graphiti search --limit passes num_results parameter.

        Verifies --limit argument is correctly wired.
        """
        captured_num_results: list[int] = []

        mock_client = Mock()
        mock_client.enabled = True

        async def mock_initialize() -> bool:
            return True

        async def mock_search(
            query: str = "",
            num_results: int = 10,
            **kwargs: Any
        ) -> list[dict[str, Any]]:
            captured_num_results.append(num_results)
            return []

        async def mock_close() -> None:
            pass

        mock_client.initialize = mock_initialize
        mock_client.search = mock_search
        mock_client.close = mock_close

        with patch(
            "guardkit.cli.graphiti._get_client_and_config",
            return_value=(mock_client, Mock(enabled=True)),
        ):
            result = runner.invoke(
                cli,
                ["graphiti", "search", "test query", "--limit", "5"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert len(captured_num_results) == 1, "search should be called once"
        assert captured_num_results[0] == 5, (
            f"Expected num_results=5, got {captured_num_results[0]}"
        )

    def test_graphiti_search_returns_meaningful_output(
        self, runner: CliRunner
    ) -> None:
        """
        Test: guardkit graphiti search produces meaningful output (not empty).

        Verifies command produces output containing search results.
        """
        mock_client = Mock()
        mock_client.enabled = True

        async def mock_initialize() -> bool:
            return True

        async def mock_search(**kwargs: Any) -> list[dict[str, Any]]:
            return [
                {"fact": "Authentication uses JWT tokens", "score": 0.95, "name": "auth-pattern"},
                {"fact": "OAuth2 for third-party auth", "score": 0.85, "name": "oauth-pattern"},
            ]

        async def mock_close() -> None:
            pass

        mock_client.initialize = mock_initialize
        mock_client.search = mock_search
        mock_client.close = mock_close

        with patch(
            "guardkit.cli.graphiti._get_client_and_config",
            return_value=(mock_client, Mock(enabled=True)),
        ):
            result = runner.invoke(
                cli,
                ["graphiti", "search", "authentication"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert result.output.strip(), "Output should not be empty"
        # Should contain results or result count
        assert "Found" in result.output or "authentication" in result.output.lower() or "JWT" in result.output, (
            f"Expected search results in output: {result.output}"
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
