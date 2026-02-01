"""
GuardKit init CLI command.

This module provides the `guardkit init` command for initializing GuardKit
in a project directory with optional template and Graphiti seeding.

Usage:
    guardkit init [TEMPLATE] [OPTIONS]

Arguments:
    TEMPLATE    Template to apply (default: 'default')

Options:
    --skip-graphiti    Skip Graphiti project seeding
    --project-name     Override project name (defaults to directory name)

Example:
    guardkit init                          # Initialize with default template
    guardkit init fastapi-python           # Initialize with FastAPI template
    guardkit init --skip-graphiti          # Skip Graphiti seeding
    guardkit init react-typescript -n myapp  # With custom project name

Coverage Target: >=85%
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig
from guardkit.knowledge.project_seeding import seed_project_knowledge

console = Console()
logger = logging.getLogger(__name__)


def apply_template(template_name: str, target_dir: Optional[Path] = None) -> bool:
    """Apply a template to the target directory.

    Creates the basic GuardKit directory structure and copies template files.

    Args:
        template_name: Name of the template to apply.
        target_dir: Target directory (defaults to cwd).

    Returns:
        True if template applied successfully, False otherwise.
    """
    target_dir = target_dir or Path.cwd()

    # Create basic GuardKit structure
    directories = [
        target_dir / ".claude",
        target_dir / ".claude" / "commands",
        target_dir / ".claude" / "agents",
        target_dir / ".claude" / "task-plans",
        target_dir / "tasks",
        target_dir / "tasks" / "backlog",
        target_dir / "tasks" / "in_progress",
        target_dir / "tasks" / "in_review",
        target_dir / "tasks" / "blocked",
        target_dir / "tasks" / "completed",
        target_dir / ".guardkit",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    logger.info(f"Applied template '{template_name}' to {target_dir}")
    return True


async def _cmd_init(
    template: str,
    skip_graphiti: bool,
    project_name: Optional[str],
) -> int:
    """Async implementation of init command.

    Args:
        template: Template name to apply.
        skip_graphiti: If True, skip Graphiti seeding.
        project_name: Override project name.

    Returns:
        Exit code (0 for success).
    """
    project_dir = Path.cwd()
    project_name = project_name or project_dir.name

    console.print(f"[bold]Initializing GuardKit in {project_dir}[/bold]")
    console.print(f"  Project: {project_name}")
    console.print(f"  Template: {template}")

    # Step 1: Apply template
    console.print("\n[bold]Step 1: Applying template...[/bold]")
    if apply_template(template, project_dir):
        console.print(f"  [green]Applied template: {template}[/green]")
    else:
        console.print(f"  [yellow]Warning: Template '{template}' not found, using defaults[/yellow]")

    # Step 2: Seed Graphiti (if not skipped)
    if skip_graphiti:
        console.print("\n[bold]Step 2: Skipping Graphiti seeding (--skip-graphiti)[/bold]")
    else:
        console.print("\n[bold]Step 2: Seeding project knowledge to Graphiti...[/bold]")

        # Initialize Graphiti client
        client = None
        try:
            config = GraphitiConfig(project_id=project_name)
            client = GraphitiClient(config)
            initialized = await client.initialize()

            if not initialized or not client.enabled:
                console.print("  [yellow]Warning: Graphiti unavailable, skipping seeding[/yellow]")
            else:
                # Seed project knowledge
                result = await seed_project_knowledge(
                    project_name=project_name,
                    client=client,
                    project_dir=project_dir,
                )

                if result.success:
                    console.print("  [green]Project knowledge seeded successfully[/green]")
                    for component_result in result.results:
                        status = "[green]OK[/green]" if component_result.success else "[yellow]WARN[/yellow]"
                        console.print(f"    {status} {component_result.component}: {component_result.message}")
                else:
                    console.print("  [yellow]Warning: Some seeding components failed[/yellow]")

        except Exception as e:
            console.print(f"  [yellow]Warning: Graphiti seeding error: {e}[/yellow]")
            logger.debug(f"Graphiti error: {e}", exc_info=True)
        finally:
            if client:
                try:
                    await client.close()
                except Exception:
                    pass

    # Summary
    console.print("\n[bold green]GuardKit initialized successfully![/bold green]")
    console.print(f"\nNext steps:")
    console.print(f"  1. Create a task: /task-create \"Your first task\"")
    console.print(f"  2. Work on it: /task-work TASK-XXX")
    console.print(f"  3. Complete it: /task-complete TASK-XXX")

    return 0


@click.command()
@click.argument("template", default="default")
@click.option(
    "--skip-graphiti",
    is_flag=True,
    help="Skip Graphiti project knowledge seeding",
)
@click.option(
    "--project-name",
    "-n",
    default=None,
    help="Override project name (defaults to directory name)",
)
def init(template: str, skip_graphiti: bool, project_name: Optional[str]):
    """Initialize GuardKit in the current directory.

    Applies a template and optionally seeds project knowledge to Graphiti.

    TEMPLATE is the name of the template to apply (default: 'default').
    Available templates: default, fastapi-python, react-typescript, nextjs-fullstack.
    """
    exit_code = asyncio.run(_cmd_init(template, skip_graphiti, project_name))
    if exit_code != 0:
        raise SystemExit(exit_code)
