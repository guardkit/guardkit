"""
GuardKit Task CLI commands.

This module provides CLI commands for task management, including task creation.
These commands provide a CLI interface to Python entry points.

Example:
    $ guardkit task create "Add user authentication"
    $ guardkit task create "Fix login bug" --priority high
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import click

from installer.core.lib.slug_utils import slugify_task_name

if TYPE_CHECKING:
    from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Python Entry Points (Layer B)
# ============================================================================


def create_task(
    title: str,
    priority: str = "medium",
    prefix: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> Path:
    """
    Create a task file in the backlog directory.

    This is the Python entry point that the CLI command invokes.
    It creates a task markdown file with YAML frontmatter.

    Parameters
    ----------
    title : str
        Task title
    priority : str
        Task priority (high, medium, low)
    prefix : str, optional
        Optional prefix for task ID (e.g., "FIX", "DOC")
    repo_root : Path, optional
        Repository root (defaults to current directory)

    Returns
    -------
    Path
        Path to created task file

    Raises
    ------
    ValueError
        If title is empty or priority is invalid
    OSError
        If task directory cannot be created or file cannot be written
    """
    # Validate inputs
    if not title or not title.strip():
        raise ValueError("Task title cannot be empty")

    title = title.strip()
    priority = priority.lower()

    if priority not in ("high", "medium", "low"):
        raise ValueError(f"Invalid priority: {priority}. Must be high, medium, or low")

    # Determine repo root
    if repo_root is None:
        repo_root = Path.cwd()

    # Generate hash-based task ID
    task_id = _generate_task_id(title, prefix)

    # Create backlog directory if needed
    backlog_dir = repo_root / "tasks" / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    slug = slugify_task_name(title)
    filename = f"{task_id}-{slug}.md"
    task_path = backlog_dir / filename

    # Generate task content
    content = _generate_task_content(task_id, title, priority)

    # Write task file
    task_path.write_text(content, encoding="utf-8")
    logger.info(f"Created task {task_id} at {task_path}")

    return task_path


def _generate_task_id(title: str, prefix: Optional[str] = None) -> str:
    """
    Generate hash-based task ID.

    Uses first 4 characters of SHA256 hash of title + timestamp
    to ensure uniqueness.

    Parameters
    ----------
    title : str
        Task title
    prefix : str, optional
        Optional prefix (e.g., "FIX", "DOC")

    Returns
    -------
    str
        Task ID in format TASK-{hash} or TASK-{prefix}-{hash}
    """
    # Include timestamp to ensure uniqueness for same title
    timestamp = datetime.now(timezone.utc).isoformat()
    hash_input = f"{title}:{timestamp}"
    hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:4]

    if prefix:
        return f"TASK-{prefix.upper()}-{hash_value}"
    return f"TASK-{hash_value}"



def _generate_task_content(task_id: str, title: str, priority: str) -> str:
    """
    Generate task markdown content with frontmatter.

    Parameters
    ----------
    task_id : str
        Task identifier
    title : str
        Task title
    priority : str
        Task priority

    Returns
    -------
    str
        Task markdown content
    """
    return f"""---
id: {task_id}
title: {title}
priority: {priority}
status: backlog
task_type: feature
---

# {title}

## Objective

[Describe what this task should accomplish]

## Acceptance Criteria

- [ ] [First criterion]
- [ ] [Second criterion]

## Implementation Notes

[Add any relevant notes for implementation]
"""


# ============================================================================
# CLI Commands (Layer A)
# ============================================================================


@click.group()
def task():
    """Task management commands."""
    pass


@task.command()
@click.argument("title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["high", "medium", "low"], case_sensitive=False),
    default="medium",
    help="Task priority (default: medium)",
)
@click.option(
    "--prefix",
    type=str,
    default=None,
    help="Task ID prefix (e.g., FIX, DOC)",
)
def create(title: str, priority: str, prefix: Optional[str]) -> None:
    """
    Create a new task in the backlog.

    TITLE is the task title (required).

    \b
    Examples:
        guardkit task create "Add user authentication"
        guardkit task create "Fix login bug" --priority high
        guardkit task create "Update docs" --prefix DOC
    """
    try:
        task_path = create_task(title=title, priority=priority, prefix=prefix)
        click.echo(f"Created task: {task_path.name}")
        click.echo(f"Location: {task_path}")
    except ValueError as e:
        raise click.ClickException(str(e))
    except OSError as e:
        raise click.ClickException(f"Failed to create task: {e}")


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "task",
    "create_task",
]
