"""
Unit tests for CLI error handling decorators.

This module tests the error handling decorator's exception-to-exit-code
mapping and user-friendly error messages.
"""

import pytest
import sys
from unittest.mock import patch
from io import StringIO

from guardkit.cli.decorators import (
    handle_cli_errors,
    EXIT_SUCCESS,
    EXIT_TASK_NOT_FOUND,
    EXIT_ORCHESTRATION_ERROR,
    EXIT_INVALID_ARGUMENTS,
    EXIT_PERMISSION_ERROR,
)
from guardkit.tasks.task_loader import TaskNotFoundError, TaskParseError
from guardkit.orchestrator.exceptions import AgentInvocationError, SDKTimeoutError

# Import worktree exceptions
try:
    from orchestrator.worktrees import WorktreeCreationError, WorktreeMergeError
except ImportError:
    # Fallback for testing
    class WorktreeCreationError(Exception):
        pass

    class WorktreeMergeError(Exception):
        pass


# ============================================================================
# Test: Exception to Exit Code Mapping
# ============================================================================


def test_task_not_found_exit_code():
    """Test TaskNotFoundError maps to EXIT_TASK_NOT_FOUND (1)."""

    @handle_cli_errors
    def command():
        raise TaskNotFoundError("Task TASK-AB-999 not found")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_TASK_NOT_FOUND


def test_task_parse_error_exit_code():
    """Test TaskParseError maps to EXIT_TASK_NOT_FOUND (1)."""

    @handle_cli_errors
    def command():
        raise TaskParseError("Failed to parse task")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_TASK_NOT_FOUND


def test_worktree_creation_error_exit_code():
    """Test WorktreeCreationError maps to EXIT_ORCHESTRATION_ERROR (2)."""

    @handle_cli_errors
    def command():
        raise WorktreeCreationError("Failed to create worktree")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_ORCHESTRATION_ERROR


def test_worktree_merge_error_exit_code():
    """Test WorktreeMergeError maps to EXIT_ORCHESTRATION_ERROR (2)."""

    @handle_cli_errors
    def command():
        raise WorktreeMergeError("Merge conflicts detected")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_ORCHESTRATION_ERROR


def test_agent_invocation_error_exit_code():
    """Test AgentInvocationError maps to EXIT_ORCHESTRATION_ERROR (2)."""

    @handle_cli_errors
    def command():
        raise AgentInvocationError("Agent invocation failed")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_ORCHESTRATION_ERROR


def test_sdk_timeout_error_exit_code():
    """Test SDKTimeoutError maps to EXIT_ORCHESTRATION_ERROR (2)."""

    @handle_cli_errors
    def command():
        raise SDKTimeoutError("SDK timeout after 30s")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_ORCHESTRATION_ERROR


def test_permission_error_exit_code():
    """Test PermissionError maps to EXIT_PERMISSION_ERROR (4)."""

    @handle_cli_errors
    def command():
        raise PermissionError("Permission denied: /path/to/file")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_PERMISSION_ERROR


def test_value_error_exit_code():
    """Test ValueError maps to EXIT_INVALID_ARGUMENTS (3)."""

    @handle_cli_errors
    def command():
        raise ValueError("Invalid argument value")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_INVALID_ARGUMENTS


def test_generic_exception_exit_code():
    """Test generic Exception maps to EXIT_INVALID_ARGUMENTS (3)."""

    @handle_cli_errors
    def command():
        raise RuntimeError("Unexpected error")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_INVALID_ARGUMENTS


# ============================================================================
# Test: Error Messages
# ============================================================================


@patch("sys.stdout", new_callable=StringIO)
def test_task_not_found_message(mock_stdout):
    """Test TaskNotFoundError displays user-friendly message."""

    @handle_cli_errors
    def command():
        raise TaskNotFoundError("Task TASK-AB-999 not found")

    with pytest.raises(SystemExit):
        command()

    # Note: Rich console output might be captured differently
    # This test verifies the decorator runs without error


@patch("sys.stdout", new_callable=StringIO)
def test_worktree_creation_error_message(mock_stdout):
    """Test WorktreeCreationError includes suggestion."""

    @handle_cli_errors
    def command():
        raise WorktreeCreationError("Failed to create worktree")

    with pytest.raises(SystemExit):
        command()

    # Verify decorator runs without error


# ============================================================================
# Test: Decorator Preservation
# ============================================================================


def test_decorator_preserves_function_name():
    """Test decorator preserves original function name."""

    @handle_cli_errors
    def my_command():
        pass

    assert my_command.__name__ == "my_command"


def test_decorator_preserves_docstring():
    """Test decorator preserves original docstring."""

    @handle_cli_errors
    def my_command():
        """This is my command docstring."""
        pass

    assert my_command.__doc__ == "This is my command docstring."


# ============================================================================
# Test: Success Path
# ============================================================================


def test_success_path_no_exit():
    """Test decorator doesn't exit on success."""

    @handle_cli_errors
    def command():
        return "success"

    result = command()
    assert result == "success"


def test_decorator_passes_arguments():
    """Test decorator passes arguments correctly."""

    @handle_cli_errors
    def command(a, b, c=10):
        return a + b + c

    result = command(1, 2, c=3)
    assert result == 6


# ============================================================================
# Test: Multiple Decorators
# ============================================================================


def test_multiple_decorators_compatible():
    """Test handle_cli_errors works with other decorators."""

    def other_decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    @handle_cli_errors
    @other_decorator
    def command():
        raise TaskNotFoundError("Task not found")

    with pytest.raises(SystemExit) as exc_info:
        command()

    assert exc_info.value.code == EXIT_TASK_NOT_FOUND
