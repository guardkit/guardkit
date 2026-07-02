"""
CLI commands for System Context navigation.

This module provides the context-switch command for multi-project navigation:
- context-switch: Multi-project navigation

The ``system-overview`` and ``impact-analysis`` commands were retired in the
fleet-memory cutover (FEAT-MEM-09): they were pure knowledge-graph readers with
no residual value once graphiti was removed. Project architecture now lives in
``docs/architecture/`` (see ``/system-plan``).

Example:
    $ guardkit context-switch requirekit
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import click
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def _format_context_switch_display(result: Dict[str, Any], mode: str = "switch") -> str:
    """Format context switch result for terminal display."""
    status = result.get("status", "success")

    if status == "error":
        message = result.get("message", "Unknown error")
        project_id = result.get("project_id", "")
        return f"Error: {message}\nProject: {project_id}"

    lines: list = []
    project_id = result.get("project_id", "Unknown")
    project_path = result.get("project_path", "")

    if mode == "list":
        projects = result.get("projects", [])
        if not projects:
            return "No known projects."

        lines.append("=" * 70)
        lines.append("KNOWN PROJECTS")
        lines.append("=" * 70)
        lines.append("")

        for proj in projects:
            pid = proj.get("id", "unknown")
            path = proj.get("path", "")
            last_accessed = proj.get("last_accessed", "never")
            lines.append(f"  {pid}")
            lines.append(f"    Path: {path}")
            lines.append(f"    Last accessed: {last_accessed}")
            lines.append("")

        lines.append("=" * 70)
        lines.append("Switch context: /context-switch <project-name>")
        lines.append("=" * 70)

        return "\n".join(lines)

    if mode == "current":
        lines.append("=" * 70)
        lines.append(f"CURRENT PROJECT: {project_id}")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"PATH: {project_path}")

    else:  # switch mode
        lines.append("=" * 70)
        lines.append(f"SWITCHED TO: {project_id}")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"PROJECT: {project_id}")
        lines.append(f"PATH: {project_path}")

    # Active tasks
    active_tasks = result.get("active_tasks", [])
    if active_tasks:
        lines.append("")
        lines.append(f"ACTIVE TASKS ({len(active_tasks)}):")
        for task in active_tasks[:5]:
            task_id = task.get("id", "")
            title = task.get("title", "")
            task_status = task.get("status", "")
            lines.append(f"  - {task_id}: {title} ({task_status})")
    else:
        lines.append("")
        lines.append("ACTIVE TASKS:")
        lines.append("  No active tasks")

    lines.append("")
    lines.append("=" * 70)
    lines.append("ORIENTATION COMPLETE")
    lines.append("=" * 70)

    return "\n".join(lines)


# ============================================================================
# CLI Commands
# ============================================================================


@click.command("context-switch")
@click.argument("project", required=False)
@click.option(
    "--list",
    "list_projects",
    is_flag=True,
    help="List all known projects without switching",
)
def context_switch(project: Optional[str], list_projects: bool):
    """Switch active project context or show project information.

    Enables navigation between multiple projects managed by GuardKit.
    When switching, displays an orientation summary with active tasks.

    Arguments:
        PROJECT: Project name to switch to (optional)

    Examples:
        guardkit context-switch                  # Show current project
        guardkit context-switch --list          # List all projects
        guardkit context-switch requirekit      # Switch to requirekit
    """
    from guardkit.planning.context_switch import (
        GuardKitConfig,
        execute_context_switch,
    )

    try:
        config = GuardKitConfig()
    except Exception as e:
        logger.debug(f"Error loading config: {e}")
        console.print("No project configuration found.")
        console.print("Run: guardkit init")
        return

    if list_projects:
        # List mode
        projects = config.list_known_projects()
        result = {"status": "success", "projects": projects}
        output = _format_context_switch_display(result, mode="list")
        console.print(output)
        return

    if project is None:
        # Current mode - show active project
        current = config.active_project
        if current is None:
            console.print("No active project. Run: guardkit context-switch <project>")
            return

        # Get context for current project
        try:
            result = asyncio.run(execute_context_switch(
                client=None,
                target_project=current.get("id", ""),
                config=config,
            ))
        except Exception as e:
            logger.debug(f"Error getting current context: {e}")
            result = {
                "status": "success",
                "project_id": current.get("id", "Unknown"),
                "project_path": current.get("path", ""),
                "active_tasks": [],
            }

        output = _format_context_switch_display(result, mode="current")
        console.print(output)
        return

    # Switch mode
    try:
        result = asyncio.run(execute_context_switch(
            client=None,
            target_project=project,
            config=config,
        ))
    except ValueError as e:
        # Project not found
        result = {
            "status": "error",
            "message": str(e),
            "project_id": project,
        }
    except Exception as e:
        logger.debug(f"Error switching context: {e}")
        result = {
            "status": "error",
            "message": f"Error switching context: {e}",
            "project_id": project,
        }

    if result.get("status") == "error":
        console.print(f"[red]Error: {result.get('message')}[/red]")
        console.print()
        console.print("Known projects:")
        for proj in config.list_known_projects():
            console.print(f"  - {proj.get('id', 'unknown')}")
        raise SystemExit(1)

    output = _format_context_switch_display(result, mode="switch")
    console.print(output)
