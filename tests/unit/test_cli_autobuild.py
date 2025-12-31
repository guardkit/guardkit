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


@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_success(
    mock_orchestrator_class, mock_load_task, cli_runner, mock_task_data, mock_success_result
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


@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_with_options(
    mock_orchestrator_class,
    mock_load_task,
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


@patch("guardkit.cli.autobuild.TaskLoader.load_task")
def test_task_command_task_not_found(mock_load_task, cli_runner):
    """Test task command when task file not found."""
    # Mock task loading to raise exception
    mock_load_task.side_effect = TaskNotFoundError("Task TASK-AB-999 not found")

    # Execute command
    result = cli_runner.invoke(task, ["TASK-AB-999"])

    # Verify exit code (handle_cli_errors decorator)
    assert result.exit_code == 1

    # Verify error message
    assert "Task not found" in result.output


@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_orchestration_failure(
    mock_orchestrator_class,
    mock_load_task,
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


@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_verbose_output(
    mock_orchestrator_class,
    mock_load_task,
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


@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_max_turns_exceeded(
    mock_orchestrator_class, mock_load_task, cli_runner, mock_task_data, mock_worktree
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


@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_empty_acceptance_criteria(
    mock_orchestrator_class, mock_load_task, cli_runner, mock_success_result
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
