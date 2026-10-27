"""
GuardKit Task CLI commands.

This module provides CLI commands for task management, including task creation.
These commands provide a CLI interface to Python entry points.

Example:
    $ guardkit task create "Add user authentication"
    $ guardkit task create "Fix login bug" --priority high
    $ guardkit task create "Review auth session handling" --prefix REV --task-type review
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

# Mirrors the "Task Type Values" list in installer/core/commands/task-create.md.
VALID_TASK_TYPES = (
    "feature",
    "scaffolding",
    "infrastructure",
    "integration",
    "documentation",
    "testing",
    "refactor",
    "declarative",
    "review",
)


# ============================================================================
# Python Entry Points (Layer B)
# ============================================================================


def create_task(
    title: str,
    priority: str = "medium",
    prefix: Optional[str] = None,
    repo_root: Optional[Path] = None,
    task_type: str = "feature",
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
    task_type : str
        Task type (see VALID_TASK_TYPES; default "feature"). "review" tasks
        get a review-shaped body with a "Review Scope" section so
        /task-review's Phase 0 ad-hoc entry can run them without editing.

    Returns
    -------
    Path
        Path to created task file

    Raises
    ------
    ValueError
        If title is empty or priority/task_type is invalid
    OSError
        If task directory cannot be created or file cannot be written
    """
    # Validate inputs
    if not title or not title.strip():
        raise ValueError("Task title cannot be empty")

    title = title.strip()
    priority = priority.lower()
    task_type = task_type.lower()

    if priority not in ("high", "medium", "low"):
        raise ValueError(f"Invalid priority: {priority}. Must be high, medium, or low")

    if task_type not in VALID_TASK_TYPES:
        raise ValueError(
            f"Invalid task_type: {task_type}. Must be one of {', '.join(VALID_TASK_TYPES)}"
        )

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
    content = _generate_task_content(task_id, title, priority, task_type)

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



def _generate_task_content(
    task_id: str, title: str, priority: str, task_type: str = "feature"
) -> str:
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
    task_type : str
        Task type; "review" emits a review-shaped body (Review Scope section)

    Returns
    -------
    str
        Task markdown content
    """
    if task_type == "review":
        # Review-shaped body: /task-review's Execution Protocol errors on a
        # missing "Review Scope" section, so the ad-hoc description becomes
        # the scope and the task is runnable the moment it is created.
        return f"""---
id: {task_id}
title: {title}
priority: {priority}
status: backlog
task_type: review
---

# {title}

## Review Scope

{title}

## Objective

Analyze and produce findings/recommendations; this task carries no implementation.

## Acceptance Criteria

- [ ] Review report generated at .claude/reviews/{task_id}-review-report.md
- [ ] Decision checkpoint completed ([A]ccept / [R]evise / [I]mplement / [C]ancel)
"""

    return f"""---
id: {task_id}
title: {title}
priority: {priority}
status: backlog
task_type: {task_type}
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
@click.option(
    "--task-type",
    "task_type",
    type=click.Choice(VALID_TASK_TYPES, case_sensitive=False),
    default="feature",
    help="Task type (default: feature); 'review' emits a review-shaped body",
)
def create(title: str, priority: str, prefix: Optional[str], task_type: str) -> None:
    """
    Create a new task in the backlog.

    TITLE is the task title (required).

    \b
    Examples:
        guardkit task create "Add user authentication"
        guardkit task create "Fix login bug" --priority high
        guardkit task create "Update docs" --prefix DOC
        guardkit task create "Review auth session handling" --prefix REV --task-type review
    """
    try:
        task_path = create_task(
            title=title, priority=priority, prefix=prefix, task_type=task_type
        )
        click.echo(f"Created task: {task_path.name}")
        click.echo(f"Location: {task_path}")
    except ValueError as e:
        raise click.ClickException(str(e))
    except OSError as e:
        raise click.ClickException(f"Failed to create task: {e}")


@task.command()
@click.argument("task_id")
@click.option(
    "--root",
    "root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Repository root (default: current directory / git root).",
)
@click.option(
    "--autobuild-mode",
    "autobuild_mode",
    is_flag=True,
    default=False,
    help="Phase-6 carve-out: REFUSE to complete (autobuild finalizes post-merge "
    "via feature-complete; never complete an unmerged branch).",
)
@click.option(
    "--pause",
    "pause",
    is_flag=True,
    default=False,
    help="Do not complete — report that the task stays at IN_REVIEW (Amber).",
)
@click.option(
    "--no-capture",
    "no_capture",
    is_flag=True,
    default=False,
    help="Skip the fleet-memory capture-outcome write.",
)
@click.option(
    "--no-git-commit",
    "no_git_commit",
    is_flag=True,
    default=False,
    help="Skip the conductor git-state commit.",
)
def complete(
    task_id: str,
    root: "Optional[Path]",
    autobuild_mode: bool,
    pause: bool,
    no_capture: bool,
    no_git_commit: bool,
) -> None:
    """Finalize a task via the shared atomic completion routine.

    TASK_ID is the task id (or a full path to the task file).

    The single completion path behind task-work § Phase 6 (Green) and the
    /task-complete slash wrapper: atomic status-flip + move into
    ``tasks/completed/``, related-file archival, fleet-memory capture-outcome,
    and the conductor git-state commit. Fail-closed through ``qa.enforce_tier1``
    when that flag is on. Location-agnostic: it finds the task in IN_REVIEW (the
    normal task-work terminal) or any other state.

    \b
    Examples:
        guardkit task complete TASK-045
        guardkit task complete TASK-045 --pause        # stay at IN_REVIEW
        guardkit task complete TASK-045 --no-capture
    """
    from installer.core.commands.lib.task_completion_helper import (
        complete_task,
        CompletionRefused,
    )

    if pause:
        click.echo(f"⏸  {task_id} left at IN_REVIEW (--pause). Complete later with: "
                   f"guardkit task complete {task_id}")
        return

    try:
        result = complete_task(
            task_id,
            refuse_autobuild=autobuild_mode,
            capture_outcome=not no_capture,
            commit_git_state=not no_git_commit,
            repo_root=root,
        )
    except CompletionRefused as exc:
        raise click.ClickException(str(exc))
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))

    click.echo(f"✅ Completed {result['task_id']}")
    click.echo(f"   Moved: {result['old_path']} → {result['new_path']} (atomic flip+move)")
    click.echo(f"   Archived: {result['documents_archived']} related file(s)")
    if not no_capture:
        click.echo(f"   fleet-memory capture-outcome: {result['capture_status']}")
    if not no_git_commit:
        click.echo(f"   conductor git-state: {result['git_state_status']}")


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "task",
    "create_task",
    "VALID_TASK_TYPES",
]
