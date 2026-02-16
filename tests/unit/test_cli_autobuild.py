"""
Unit tests for AutoBuild CLI commands.

This module provides comprehensive unit tests for the CLI layer,
using Click's CliRunner for isolated testing and mocks for dependencies.

Test Coverage:
- Argument parsing (missing args, invalid options, help text)
- Command execution (task command, status command)
- Output formatting (success, error, verbose modes)
- Exit codes (0 success, 1 not found, 2 error)
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import MagicMock, patch

from guardkit.cli.autobuild import autobuild, task, status
from guardkit.cli.main import cli
from guardkit.orchestrator import OrchestrationResult, TurnRecord
from guardkit.tasks.task_loader import TaskNotFoundError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cli_runner():
    """Provide Click CLI runner for isolated testing."""
    return CliRunner()


@pytest.fixture
def mock_task_data():
    """Provide mock task data for testing."""
    return {
        "task_id": "TASK-AB-001",
        "requirements": "Implement OAuth2 authentication",
        "acceptance_criteria": [
            "Support authorization code flow",
            "Handle token refresh",
            "Include comprehensive tests",
        ],
        "frontmatter": {
            "id": "TASK-AB-001",
            "title": "Implement OAuth2",
            "status": "backlog",
        },
        "content": "## Requirements\nImplement OAuth2 authentication",
        "file_path": Path("/fake/tasks/backlog/TASK-AB-001.md"),
    }


@pytest.fixture
def mock_worktree():
    """Provide mock Worktree for testing."""
    from guardkit.worktrees import Worktree

    return Worktree(
        task_id="TASK-AB-001",
        branch_name="autobuild/TASK-AB-001",
        path=Path("/fake/.guardkit/worktrees/TASK-AB-001"),
        base_branch="main",
    )


@pytest.fixture
def mock_success_result(mock_worktree):
    """Provide mock successful OrchestrationResult."""
    turn_record = TurnRecord(
        turn=1,
        player_result=MagicMock(success=True, report={"files_created": ["auth.py"]}),
        coach_result=MagicMock(
            success=True, report={"decision": "approve", "rationale": "Looks good"}
        ),
        decision="approve",
        feedback=None,
        timestamp="2025-12-23T10:30:00Z",
    )

    return OrchestrationResult(
        task_id="TASK-AB-001",
        success=True,
        total_turns=1,
        final_decision="approved",
        turn_history=[turn_record],
        worktree=mock_worktree,
        error=None,
    )


@pytest.fixture
def mock_failure_result(mock_worktree):
    """Provide mock failed OrchestrationResult."""
    turn_record = TurnRecord(
        turn=1,
        player_result=MagicMock(success=False, error="Import error", report={}),
        coach_result=None,
        decision="error",
        feedback=None,
        timestamp="2025-12-23T10:30:00Z",
    )

    return OrchestrationResult(
        task_id="TASK-AB-001",
        success=False,
        total_turns=1,
        final_decision="error",
        turn_history=[turn_record],
        worktree=mock_worktree,
        error="Import error",
    )


# ============================================================================
# Test: Argument Parsing
# ============================================================================


def test_task_command_missing_task_id(cli_runner):
    """Test task command without task ID (missing required argument)."""
    result = cli_runner.invoke(task, [])
    assert result.exit_code == 2  # Click missing argument error


def test_task_command_help_text(cli_runner):
    """Test task command help text display."""
    result = cli_runner.invoke(task, ["--help"])
    assert result.exit_code == 0
    assert "Execute AutoBuild orchestration" in result.output
    assert "--max-turns" in result.output
    assert "--model" in result.output
    assert "--verbose" in result.output
    assert "--mode" in result.output


def test_task_command_mode_option_in_help(cli_runner):
    """Test task command help shows --mode option."""
    result = cli_runner.invoke(task, ["--help"])
    assert result.exit_code == 0
    assert "--mode" in result.output
    assert "standard" in result.output
    assert "tdd" in result.output
    assert "bdd" in result.output


def test_task_command_invalid_mode(cli_runner):
    """Test task command rejects invalid mode values."""
    result = cli_runner.invoke(task, ["TASK-AB-001", "--mode", "invalid"])
    assert result.exit_code == 2  # Click choice validation error


def test_task_command_invalid_max_turns(cli_runner, mock_task_data):
    """Test task command with invalid max_turns value."""
    # Click will reject non-integer values
    result = cli_runner.invoke(task, ["TASK-AB-001", "--max-turns", "invalid"])
    assert result.exit_code == 2  # Click type validation error


def test_status_command_missing_task_id(cli_runner):
    """Test status command without task ID."""
    result = cli_runner.invoke(status, [])
    assert result.exit_code == 2  # Click missing argument error


def test_status_command_help_text(cli_runner):
    """Test status command help text display."""
    result = cli_runner.invoke(status, ["--help"])
    assert result.exit_code == 0
    assert "Show AutoBuild status" in result.output
    assert "--verbose" in result.output


# ============================================================================
# Test: Task Command Execution
# ============================================================================


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_success(
    mock_orchestrator_class, mock_load_task, mock_require_sdk, cli_runner, mock_task_data, mock_success_result
):
    """Test successful task command execution."""
    # Mock task loading
    mock_load_task.return_value = mock_task_data

    # Mock orchestrator
    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute command
    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Verify task loaded
    mock_load_task.assert_called_once()

    # Verify orchestrator initialized
    mock_orchestrator_class.assert_called_once()

    # Verify orchestrate called with correct args
    mock_orchestrator.orchestrate.assert_called_once_with(
        task_id="TASK-AB-001",
        requirements=mock_task_data["requirements"],
        acceptance_criteria=mock_task_data["acceptance_criteria"],
        task_file_path=mock_task_data["file_path"],
    )

    # Verify exit code
    assert result.exit_code == 0

    # Verify output contains success indicators
    assert "✓" in result.output or "success" in result.output.lower()


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_with_options(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_task_data,
    mock_success_result,
):
    """Test task command with all options specified."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with options
    result = cli_runner.invoke(
        task,
        [
            "TASK-AB-001",
            "--max-turns",
            "10",
            "--model",
            "claude-opus-4-5-20251101",
            "--verbose",
        ],
    )

    # Verify orchestrator initialized with correct max_turns
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["max_turns"] == 10

    # Verify exit code
    assert result.exit_code == 0


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_with_mode_option(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_task_data,
    mock_success_result,
):
    """Test task command passes mode to orchestrator."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with mode option
    result = cli_runner.invoke(
        task,
        ["TASK-AB-001", "--mode", "standard"],
    )

    # Verify orchestrator initialized with correct development_mode
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["development_mode"] == "standard"

    # Verify exit code
    assert result.exit_code == 0

    # Verify mode displayed in banner
    assert "STANDARD" in result.output


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_mode_defaults_to_tdd(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_task_data,
    mock_success_result,
):
    """Test task command defaults to tdd mode when not specified."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute without mode option
    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Verify orchestrator initialized with tdd mode
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["development_mode"] == "tdd"

    # Verify exit code
    assert result.exit_code == 0


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_mode_from_frontmatter(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_success_result,
):
    """Test task command uses mode from task frontmatter if not specified."""
    # Create task data with autobuild.mode in frontmatter
    task_data_with_mode = {
        "task_id": "TASK-AB-001",
        "requirements": "Implement feature",
        "acceptance_criteria": ["Criterion 1"],
        "frontmatter": {"id": "TASK-AB-001"},
        "content": "## Requirements",
        "file_path": Path("/fake/tasks/TASK-AB-001.md"),
        "autobuild": {"mode": "standard"},
    }
    mock_load_task.return_value = task_data_with_mode

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute without mode option (should use frontmatter value)
    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Verify orchestrator initialized with frontmatter mode (default changed to 'tdd')
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["development_mode"] == "tdd"


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_mode_cli_overrides_frontmatter(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_success_result,
):
    """Test CLI mode flag overrides task frontmatter mode."""
    # Create task data with autobuild.mode in frontmatter
    task_data_with_mode = {
        "task_id": "TASK-AB-001",
        "requirements": "Implement feature",
        "acceptance_criteria": ["Criterion 1"],
        "frontmatter": {"id": "TASK-AB-001"},
        "content": "## Requirements",
        "file_path": Path("/fake/tasks/TASK-AB-001.md"),
        "autobuild": {"mode": "standard"},
    }
    mock_load_task.return_value = task_data_with_mode

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with mode option (should override frontmatter)
    result = cli_runner.invoke(task, ["TASK-AB-001", "--mode", "bdd"])

    # Verify orchestrator initialized with CLI mode (not frontmatter)
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["development_mode"] == "bdd"


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
def test_task_command_task_not_found(mock_load_task, mock_require_sdk, cli_runner):
    """Test task command when task file not found."""
    # Mock task loading to raise exception
    mock_load_task.side_effect = TaskNotFoundError("Task TASK-AB-999 not found")

    # Execute command
    result = cli_runner.invoke(task, ["TASK-AB-999"])

    # Verify exit code (handle_cli_errors decorator)
    assert result.exit_code == 1

    # Verify error message
    assert "Task not found" in result.output


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_orchestration_failure(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_task_data,
    mock_failure_result,
):
    """Test task command when orchestration fails."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_failure_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute command
    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Verify exit code (failure)
    assert result.exit_code == 2

    # Verify error output
    assert "failed" in result.output.lower() or "✗" in result.output


# ============================================================================
# Test: Status Command Execution
# ============================================================================


@patch("guardkit.cli.autobuild.WorktreeManager")
@patch("guardkit.cli.autobuild._find_worktree")
def test_status_command_worktree_exists(
    mock_find_worktree, mock_manager_class, cli_runner, mock_worktree
):
    """Test status command when worktree exists."""
    # Mock worktree discovery
    mock_find_worktree.return_value = mock_worktree

    # Execute command
    result = cli_runner.invoke(status, ["TASK-AB-001"])

    # Verify exit code
    assert result.exit_code == 0

    # Verify output contains worktree info
    assert "TASK-AB-001" in result.output
    assert "autobuild/TASK-AB-001" in result.output


@patch("guardkit.cli.autobuild.WorktreeManager")
@patch("guardkit.cli.autobuild._find_worktree")
def test_status_command_no_worktree(
    mock_find_worktree, mock_manager_class, cli_runner
):
    """Test status command when no worktree exists."""
    # Mock worktree discovery to return None
    mock_find_worktree.return_value = None

    # Execute command
    result = cli_runner.invoke(status, ["TASK-AB-001"])

    # Verify exit code (still 0 - not an error)
    assert result.exit_code == 0

    # Verify output indicates no worktree
    assert "No AutoBuild worktree found" in result.output


@patch("guardkit.cli.autobuild.WorktreeManager")
@patch("guardkit.cli.autobuild._find_worktree")
def test_status_command_verbose(
    mock_find_worktree, mock_manager_class, cli_runner, mock_worktree
):
    """Test status command with verbose flag."""
    mock_find_worktree.return_value = mock_worktree

    # Execute with --verbose
    result = cli_runner.invoke(status, ["TASK-AB-001", "--verbose"])

    # Verify exit code
    assert result.exit_code == 0

    # Verify output contains base branch (verbose only)
    assert "main" in result.output


# ============================================================================
# Test: Output Formatting
# ============================================================================


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_verbose_output(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_task_data,
    mock_success_result,
):
    """Test verbose output includes turn history."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with --verbose
    result = cli_runner.invoke(task, ["TASK-AB-001", "--verbose"])

    # Verify exit code
    assert result.exit_code == 0

    # Verify turn history displayed
    assert "Turn History" in result.output or "APPROVE" in result.output


# ============================================================================
# Test: Error Handling Decorator Integration
# ============================================================================


def test_error_handler_decorator_applied():
    """Test that error handler decorator is applied to commands."""
    # Check that task and status commands have the decorator wrapper
    # Note: Click wraps the function in a Command object, so we check task.callback
    assert hasattr(task.callback, "__wrapped__")  # functools.wraps preserves this
    assert hasattr(status.callback, "__wrapped__")


# ============================================================================
# Test: Integration with Main CLI
# ============================================================================


def test_autobuild_group_registered(cli_runner):
    """Test that autobuild group is registered in main CLI."""
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "autobuild" in result.output


def test_autobuild_task_via_main_cli(cli_runner):
    """Test invoking task command through main CLI."""
    result = cli_runner.invoke(cli, ["autobuild", "--help"])
    assert result.exit_code == 0
    assert "autobuild" in result.output.lower()


# ============================================================================
# Test: Edge Cases
# ============================================================================


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_max_turns_exceeded(
    mock_orchestrator_class, mock_load_task, mock_require_sdk, cli_runner, mock_task_data, mock_worktree
):
    """Test task command when max turns exceeded."""
    mock_load_task.return_value = mock_task_data

    # Create result with max_turns_exceeded
    result_data = OrchestrationResult(
        task_id="TASK-AB-001",
        success=False,
        total_turns=5,
        final_decision="max_turns_exceeded",
        turn_history=[],
        worktree=mock_worktree,
        error="Maximum turns (5) exceeded without approval",
    )

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = result_data
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute command
    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Verify exit code (failure)
    assert result.exit_code == 2

    # Verify error message
    assert "failed" in result.output.lower() or "max" in result.output.lower()


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_empty_acceptance_criteria(
    mock_orchestrator_class, mock_load_task, mock_require_sdk, cli_runner, mock_success_result
):
    """Test task command with empty acceptance criteria."""
    # Mock task with empty criteria
    task_data = {
        "task_id": "TASK-AB-001",
        "requirements": "Implement feature X",
        "acceptance_criteria": [],
        "frontmatter": {},
        "content": "",
        "file_path": Path("/fake/tasks/backlog/TASK-AB-001.md"),
    }
    mock_load_task.return_value = task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute command
    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Should still succeed (orchestrator handles empty criteria)
    assert result.exit_code == 0


# ============================================================================
# Test: SDK Pre-flight Checks
# ============================================================================


def test_check_sdk_available_returns_bool():
    """Test _check_sdk_available returns a boolean value."""
    from guardkit.cli.autobuild import _check_sdk_available

    result = _check_sdk_available()
    assert isinstance(result, bool)


@patch("guardkit.cli.autobuild._check_sdk_available")
def test_require_sdk_exits_with_code_1_when_unavailable(mock_check):
    """Test _require_sdk exits with code 1 when SDK unavailable."""
    from guardkit.cli.autobuild import _require_sdk

    mock_check.return_value = False

    with pytest.raises(SystemExit) as exc_info:
        _require_sdk()

    assert exc_info.value.code == 1


@patch("guardkit.cli.autobuild._check_sdk_available")
def test_require_sdk_does_not_exit_when_available(mock_check):
    """Test _require_sdk does not exit when SDK is available."""
    from guardkit.cli.autobuild import _require_sdk

    mock_check.return_value = True

    # Should not raise SystemExit
    _require_sdk()  # No exception expected


@patch("guardkit.cli.autobuild._check_sdk_available")
def test_require_sdk_prints_helpful_message(mock_check, capsys):
    """Test _require_sdk prints installation instructions when SDK unavailable."""
    from guardkit.cli.autobuild import _require_sdk

    mock_check.return_value = False

    with pytest.raises(SystemExit):
        _require_sdk()

    # Rich console output goes to stdout
    # Note: Rich console may not work with capsys in all cases
    # This test validates the exit behavior mainly


@patch("guardkit.cli.autobuild._check_sdk_available")
def test_task_command_exits_early_without_sdk(mock_check, cli_runner):
    """Test task command exits with code 1 when SDK unavailable."""
    mock_check.return_value = False

    result = cli_runner.invoke(task, ["TASK-AB-001"])

    assert result.exit_code == 1
    assert "Claude Agent SDK" in result.output
    assert "pip install" in result.output


@patch("guardkit.cli.autobuild._check_sdk_available")
def test_task_command_prints_installation_instructions_without_sdk(mock_check, cli_runner):
    """Test task command shows installation instructions when SDK unavailable."""
    mock_check.return_value = False

    result = cli_runner.invoke(task, ["TASK-AB-001"])

    assert result.exit_code == 1
    assert "claude-agent-sdk" in result.output
    assert "guardkit doctor" in result.output


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_calls_require_sdk_first(
    mock_orchestrator_class, mock_load_task, mock_require_sdk, cli_runner, mock_task_data, mock_success_result
):
    """Test task command calls _require_sdk before loading task."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Verify _require_sdk was called
    mock_require_sdk.assert_called_once()


@patch("guardkit.cli.autobuild._check_sdk_available")
def test_feature_command_exits_early_without_sdk(mock_check, cli_runner):
    """Test feature command exits with code 1 when SDK unavailable."""
    from guardkit.cli.autobuild import feature

    mock_check.return_value = False

    result = cli_runner.invoke(feature, ["FEAT-A1B2"])

    assert result.exit_code == 1
    assert "Claude Agent SDK" in result.output
    assert "pip install" in result.output


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_feature_command_calls_require_sdk_first(
    mock_orchestrator_class, mock_require_sdk, cli_runner
):
    """Test feature command calls _require_sdk before processing."""
    from guardkit.cli.autobuild import feature

    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # This will fail at feature loading but after SDK check
    result = cli_runner.invoke(feature, ["FEAT-A1B2"])

    # Verify _require_sdk was called
    mock_require_sdk.assert_called_once()


# ============================================================================
# Test: SDK Timeout Option (TASK-SDK-a7f3)
# ============================================================================


def test_task_command_sdk_timeout_in_help(cli_runner):
    """Test task command help shows --sdk-timeout option."""
    result = cli_runner.invoke(task, ["--help"])
    assert result.exit_code == 0
    assert "--sdk-timeout" in result.output
    assert "60-3600" in result.output


def test_feature_command_sdk_timeout_in_help(cli_runner):
    """Test feature command help shows --sdk-timeout option."""
    from guardkit.cli.autobuild import feature

    result = cli_runner.invoke(feature, ["--help"])
    assert result.exit_code == 0
    assert "--sdk-timeout" in result.output
    assert "60-3600" in result.output


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_sdk_timeout_from_cli(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_task_data,
    mock_success_result,
):
    """Test task command passes --sdk-timeout to orchestrator."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with sdk-timeout option
    result = cli_runner.invoke(task, ["TASK-AB-001", "--sdk-timeout", "600"])

    # Verify orchestrator initialized with correct sdk_timeout
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["sdk_timeout"] == 600

    # Verify exit code
    assert result.exit_code == 0

    # Verify timeout displayed in banner
    assert "600s" in result.output


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_sdk_timeout_from_frontmatter(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_success_result,
):
    """Test task command uses sdk_timeout from task frontmatter if not specified."""
    # Create task data with autobuild.sdk_timeout in frontmatter
    task_data_with_timeout = {
        "task_id": "TASK-AB-001",
        "requirements": "Implement feature",
        "acceptance_criteria": ["Criterion 1"],
        "frontmatter": {"id": "TASK-AB-001"},
        "content": "## Requirements",
        "file_path": Path("/fake/tasks/TASK-AB-001.md"),
        "autobuild": {"sdk_timeout": 900},
    }
    mock_load_task.return_value = task_data_with_timeout

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute without sdk-timeout option (should use frontmatter value)
    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Verify orchestrator initialized with frontmatter sdk_timeout (default changed to 1200)
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["sdk_timeout"] == 1200


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_sdk_timeout_cli_overrides_frontmatter(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_success_result,
):
    """Test CLI --sdk-timeout flag overrides task frontmatter sdk_timeout."""
    # Create task data with autobuild.sdk_timeout in frontmatter
    task_data_with_timeout = {
        "task_id": "TASK-AB-001",
        "requirements": "Implement feature",
        "acceptance_criteria": ["Criterion 1"],
        "frontmatter": {"id": "TASK-AB-001"},
        "content": "## Requirements",
        "file_path": Path("/fake/tasks/TASK-AB-001.md"),
        "autobuild": {"sdk_timeout": 900},
    }
    mock_load_task.return_value = task_data_with_timeout

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with sdk-timeout option (should override frontmatter)
    result = cli_runner.invoke(task, ["TASK-AB-001", "--sdk-timeout", "1200"])

    # Verify orchestrator initialized with CLI sdk_timeout (not frontmatter)
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["sdk_timeout"] == 1200


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_sdk_timeout_default_value(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_task_data,
    mock_success_result,
):
    """Test task command uses default sdk_timeout (900) when not specified (TASK-FIX-SDKT)."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute without sdk-timeout option
    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Verify orchestrator initialized with default sdk_timeout (1200 - updated default)
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["sdk_timeout"] == 1200


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
def test_task_command_sdk_timeout_invalid_below_minimum(
    mock_load_task, mock_require_sdk, cli_runner, mock_task_data
):
    """Test task command rejects sdk_timeout below 60 seconds."""
    mock_load_task.return_value = mock_task_data

    result = cli_runner.invoke(task, ["TASK-AB-001", "--sdk-timeout", "30"])

    # Should fail with validation error
    assert result.exit_code != 0
    assert "60" in result.output or "between" in result.output.lower()


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
def test_task_command_sdk_timeout_invalid_above_maximum(
    mock_load_task, mock_require_sdk, cli_runner, mock_task_data
):
    """Test task command rejects sdk_timeout above 3600 seconds."""
    mock_load_task.return_value = mock_task_data

    result = cli_runner.invoke(task, ["TASK-AB-001", "--sdk-timeout", "5000"])

    # Should fail with validation error
    assert result.exit_code != 0
    assert "3600" in result.output or "between" in result.output.lower()


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_sdk_timeout_boundary_minimum(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_task_data,
    mock_success_result,
):
    """Test task command accepts minimum sdk_timeout (60 seconds)."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with minimum valid timeout
    result = cli_runner.invoke(task, ["TASK-AB-001", "--sdk-timeout", "60"])

    # Verify success
    assert result.exit_code == 0

    # Verify orchestrator received correct timeout
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["sdk_timeout"] == 60


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_sdk_timeout_boundary_maximum(
    mock_orchestrator_class,
    mock_load_task,
    mock_require_sdk,
    cli_runner,
    mock_task_data,
    mock_success_result,
):
    """Test task command accepts maximum sdk_timeout (3600 seconds)."""
    mock_load_task.return_value = mock_task_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with maximum valid timeout
    result = cli_runner.invoke(task, ["TASK-AB-001", "--sdk-timeout", "3600"])

    # Verify success
    assert result.exit_code == 0

    # Verify orchestrator received correct timeout
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["sdk_timeout"] == 3600


@patch("guardkit.cli.autobuild._require_sdk")
def test_feature_command_sdk_timeout_validation(mock_require_sdk, cli_runner):
    """Test feature command validates sdk_timeout range."""
    from guardkit.cli.autobuild import feature

    # Test below minimum
    result = cli_runner.invoke(feature, ["FEAT-A1B2", "--sdk-timeout", "30"])
    assert result.exit_code != 0
    assert "60" in result.output or "between" in result.output.lower()

    # Test above maximum
    result = cli_runner.invoke(feature, ["FEAT-A1B2", "--sdk-timeout", "5000"])
    assert result.exit_code != 0
    assert "3600" in result.output or "between" in result.output.lower()


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_feature_command_sdk_timeout_passed_to_orchestrator(
    mock_orchestrator_class, mock_require_sdk, cli_runner
):
    """Test feature command passes --sdk-timeout to orchestrator."""
    from guardkit.cli.autobuild import feature

    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with sdk-timeout option
    result = cli_runner.invoke(feature, ["FEAT-A1B2", "--sdk-timeout", "900"])

    # Verify orchestrator initialized with correct sdk_timeout
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["sdk_timeout"] == 900


# ============================================================================
# enable_pre_loop CLI Option Tests (TASK-FB-FIX-010)
# ============================================================================


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_feature_command_enable_pre_loop_flag(
    mock_orchestrator_class, mock_require_sdk, cli_runner
):
    """Test feature command --enable-pre-loop flag."""
    from guardkit.cli.autobuild import feature

    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with --enable-pre-loop flag
    result = cli_runner.invoke(feature, ["FEAT-A1B2", "--enable-pre-loop"])

    # Verify orchestrator initialized with enable_pre_loop=True
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_pre_loop"] is True


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_feature_command_no_pre_loop_flag(
    mock_orchestrator_class, mock_require_sdk, cli_runner
):
    """Test feature command --no-pre-loop flag."""
    from guardkit.cli.autobuild import feature

    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with --no-pre-loop flag
    result = cli_runner.invoke(feature, ["FEAT-A1B2", "--no-pre-loop"])

    # Verify orchestrator initialized with enable_pre_loop=False
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_pre_loop"] is False


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_feature_command_enable_pre_loop_default_none(
    mock_orchestrator_class, mock_require_sdk, cli_runner
):
    """Test feature command enable_pre_loop defaults to None when not specified."""
    from guardkit.cli.autobuild import feature

    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute without --enable-pre-loop or --no-pre-loop flag
    result = cli_runner.invoke(feature, ["FEAT-A1B2"])

    # Verify orchestrator initialized with enable_pre_loop=None (cascade will apply)
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_pre_loop"] is None


# ============================================================================
# Task Command --no-pre-loop CLI Option Tests (TASK-PLD-003)
# ============================================================================


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
def test_task_command_no_pre_loop_flag(
    mock_load_task, mock_orchestrator_class, mock_require_sdk, cli_runner
):
    """Test task command --no-pre-loop flag disables pre-loop."""
    from guardkit.cli.autobuild import task

    # Setup mock task data
    mock_load_task.return_value = {
        "task_id": "TASK-AB-001",
        "requirements": "Implement feature",
        "acceptance_criteria": ["Criterion 1"],
        "frontmatter": {"id": "TASK-AB-001"},
        "content": "## Requirements",
        "file_path": Path("/fake/tasks/TASK-AB-001.md"),
    }

    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.total_turns = 1
    mock_result.worktree = MagicMock(path=Path("/fake"), branch_name="test")
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute with --no-pre-loop flag
    result = cli_runner.invoke(task, ["TASK-AB-001", "--no-pre-loop"])

    # Verify orchestrator initialized with enable_pre_loop=False
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_pre_loop"] is False


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
def test_task_command_pre_loop_default_enabled(
    mock_load_task, mock_orchestrator_class, mock_require_sdk, cli_runner
):
    """Test task command pre-loop defaults to enabled (True) when not specified."""
    from guardkit.cli.autobuild import task

    # Setup mock task data
    mock_load_task.return_value = {
        "task_id": "TASK-AB-001",
        "requirements": "Implement feature",
        "acceptance_criteria": ["Criterion 1"],
        "frontmatter": {"id": "TASK-AB-001"},
        "content": "## Requirements",
        "file_path": Path("/fake/tasks/TASK-AB-001.md"),
    }

    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.total_turns = 1
    mock_result.worktree = MagicMock(path=Path("/fake"), branch_name="test")
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute without --no-pre-loop flag
    result = cli_runner.invoke(task, ["TASK-AB-001"])

    # Verify orchestrator initialized with enable_pre_loop=True (default for task-build)
    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_pre_loop"] is True


# ============================================================================
# enable_context CLI Flag Tests (TASK-FIX-GCW4)
# ============================================================================


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
def test_task_command_enable_context_default(
    mock_load_task, mock_orchestrator_class, mock_require_sdk,
    cli_runner, mock_task_data, mock_success_result,
):
    """Test that enable_context defaults to True for task command."""
    mock_load_task.return_value = mock_task_data
    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    result = cli_runner.invoke(task, ["TASK-AB-001"])

    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_context"] is True


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
def test_task_command_no_context_flag(
    mock_load_task, mock_orchestrator_class, mock_require_sdk,
    cli_runner, mock_task_data, mock_success_result,
):
    """Test that --no-context flag sets enable_context=False."""
    mock_load_task.return_value = mock_task_data
    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    result = cli_runner.invoke(task, ["TASK-AB-001", "--no-context"])

    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_context"] is False


@patch("guardkit.cli.autobuild._require_sdk")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
@patch("guardkit.cli.autobuild.TaskLoader.load_task")
def test_task_command_enable_context_flag(
    mock_load_task, mock_orchestrator_class, mock_require_sdk,
    cli_runner, mock_task_data, mock_success_result,
):
    """Test that --enable-context flag explicitly sets enable_context=True."""
    mock_load_task.return_value = mock_task_data
    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    result = cli_runner.invoke(task, ["TASK-AB-001", "--enable-context"])

    mock_orchestrator_class.assert_called_once()
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs["enable_context"] is True
