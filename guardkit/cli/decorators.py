"""
CLI error handling decorators.

This module provides decorators for consistent CLI error handling,
implementing the architectural review recommendation #3 (MEDIUM PRIORITY).

Example:
    >>> from guardkit.cli.decorators import handle_cli_errors
    >>>
    >>> @handle_cli_errors
    ... def my_command():
    ...     # Errors automatically mapped to exit codes
    ...     raise FileNotFoundError("Task not found")
"""

import functools
import logging
import sys
from typing import Callable

from rich.console import Console

from guardkit.tasks.task_loader import TaskNotFoundError, TaskParseError
from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    CoachDecisionInvalidError,
    SDKTimeoutError,
)

# Worktree exceptions - import with sys.path fallback
try:
    from orchestrator.worktrees import WorktreeCreationError, WorktreeMergeError
except ImportError:
    # Fallback for testing
    class WorktreeCreationError(Exception):
        pass

    class WorktreeMergeError(Exception):
        pass


console = Console()
logger = logging.getLogger(__name__)


# ============================================================================
# Exit Code Constants
# ============================================================================

EXIT_SUCCESS = 0
EXIT_TASK_NOT_FOUND = 1
EXIT_ORCHESTRATION_ERROR = 2
EXIT_INVALID_ARGUMENTS = 3
EXIT_PERMISSION_ERROR = 4


# ============================================================================
# Error Handler Decorator
# ============================================================================


def handle_cli_errors(func: Callable) -> Callable:
    """
    Decorator for consistent CLI error handling.

    This decorator implements centralized error handling for CLI commands,
    mapping exceptions to appropriate exit codes and user-friendly messages.

    Error Mappings
    --------------
    - TaskNotFoundError → Exit 1 (task file not found)
    - TaskParseError → Exit 1 (task parsing failed)
    - WorktreeCreationError → Exit 2 (worktree setup failed)
    - WorktreeMergeError → Exit 2 (merge failed)
    - AgentInvocationError → Exit 2 (agent invocation failed)
    - SDKTimeoutError → Exit 2 (SDK timeout)
    - PermissionError → Exit 4 (permission denied)
    - Other exceptions → Exit 3 (unexpected error)

    Parameters
    ----------
    func : Callable
        CLI command function to wrap

    Returns
    -------
    Callable
        Wrapped function with error handling

    Examples
    --------
    >>> @handle_cli_errors
    ... def task_command(task_id: str):
    ...     task = TaskLoader.load_task(task_id)
    ...     # ... processing ...
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except TaskNotFoundError as e:
            console.print(f"[red]Task not found: {e}[/red]")
            logger.error(f"Task not found: {e}")
            sys.exit(EXIT_TASK_NOT_FOUND)

        except TaskParseError as e:
            console.print(f"[red]Task parsing failed: {e}[/red]")
            logger.error(f"Task parsing failed: {e}")
            sys.exit(EXIT_TASK_NOT_FOUND)

        except WorktreeCreationError as e:
            console.print(f"[red]Worktree creation failed: {e}[/red]")
            console.print("\n[yellow]Suggestion:[/yellow] Check git repository status")
            logger.error(f"Worktree creation failed: {e}")
            sys.exit(EXIT_ORCHESTRATION_ERROR)

        except WorktreeMergeError as e:
            console.print(f"[red]Worktree merge failed: {e}[/red]")
            console.print(
                "\n[yellow]Suggestion:[/yellow] Resolve conflicts manually or use --preserve"
            )
            logger.error(f"Worktree merge failed: {e}")
            sys.exit(EXIT_ORCHESTRATION_ERROR)

        except AgentInvocationError as e:
            console.print(f"[red]Agent invocation failed: {e}[/red]")
            logger.error(f"Agent invocation failed: {e}")
            sys.exit(EXIT_ORCHESTRATION_ERROR)

        except SDKTimeoutError as e:
            console.print(f"[red]SDK timeout: {e}[/red]")
            console.print("\n[yellow]Suggestion:[/yellow] Retry or check network connectivity")
            logger.error(f"SDK timeout: {e}")
            sys.exit(EXIT_ORCHESTRATION_ERROR)

        except CoachDecisionInvalidError as e:
            console.print(f"[red]Coach decision invalid: {e}[/red]")
            logger.error(f"Coach decision invalid: {e}")
            sys.exit(EXIT_ORCHESTRATION_ERROR)

        except PermissionError as e:
            console.print(f"[red]Permission denied: {e}[/red]")
            console.print("\n[yellow]Suggestion:[/yellow] Check file permissions")
            logger.error(f"Permission denied: {e}")
            sys.exit(EXIT_PERMISSION_ERROR)

        except ValueError as e:
            console.print(f"[red]Invalid argument: {e}[/red]")
            logger.error(f"Invalid argument: {e}")
            sys.exit(EXIT_INVALID_ARGUMENTS)

        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            logger.error(f"Unexpected error: {e}", exc_info=True)
            sys.exit(EXIT_INVALID_ARGUMENTS)

    return wrapper


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "handle_cli_errors",
    "EXIT_SUCCESS",
    "EXIT_TASK_NOT_FOUND",
    "EXIT_ORCHESTRATION_ERROR",
    "EXIT_INVALID_ARGUMENTS",
    "EXIT_PERMISSION_ERROR",
]
