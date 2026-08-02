"""
GuardKit CLI main entry point.

This module provides the main Click application for GuardKit CLI commands.

Example:
    $ python3 -m guardkit.cli.main autobuild task TASK-AB-001
    $ python3 -m guardkit.cli.main autobuild status TASK-AB-001
"""

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console

from guardkit.cli.autobuild import autobuild
from guardkit.cli.dcl import dcl
from guardkit.cli.feature import feature
from guardkit.cli.init import init
from guardkit.cli.memory import memory
from guardkit.cli.qa import qa
from guardkit.cli.review import review
from guardkit.cli.system_plan import system_plan
from guardkit.cli.system_context import context_switch
from guardkit.cli.task import task
from guardkit.cli.task_review import task_review
from guardkit.cli.task_work import task_work
from guardkit.cli.template import template

# Load .env files automatically
# Priority: .env in current directory, then traverse up to find project root
def _load_env_files():
    """Load .env files from current directory and project root."""
    # Try current directory first
    cwd = Path.cwd()
    env_file = cwd / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        return

    # Traverse up to find project root (directory with .claude/ or .guardkit/)
    current = cwd
    for _ in range(10):  # Max 10 levels up
        if (current / ".claude").is_dir() or (current / ".guardkit").is_dir():
            env_file = current / ".env"
            if env_file.exists():
                load_dotenv(env_file)
            return
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

_load_env_files()

console = Console()
logger = logging.getLogger(__name__)


# ============================================================================
# Main CLI Application
# ============================================================================


@click.group()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress non-essential output",
)
@click.pass_context
def cli(ctx, verbose: bool, quiet: bool):
    """
    GuardKit - AI-Assisted Development Workflow System.

    Quality-first task workflow with built-in gates and automated testing.
    """
    # Setup logging based on verbosity
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    elif quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO)

    # Store flags in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


# ============================================================================
# Command Groups
# ============================================================================

# Add AutoBuild command group
cli.add_command(autobuild)

# Add Feature command group
cli.add_command(feature)

# Add Init command
cli.add_command(init)

# Add Memory command group
cli.add_command(memory)

# Add QA command group (tier-1 verification formats, WS2 B1)
cli.add_command(qa)

# Add DCL derivation command group (D2, design §2 — optional dcl spec track)
cli.add_command(dcl)

# Add Review command
cli.add_command(review)

# Add System-Plan command
cli.add_command(system_plan)

# Add System Context navigation command
cli.add_command(context_switch)

# Add Task command group
cli.add_command(task)

# Add the headless review leg (hyphenated house pattern, as system-plan).
# This is the subcommand the pipeline's conductor spawns as `task-review`.
cli.add_command(task_review)

# Add the headless work leg — the fix journey's second stage. The pipeline's
# conductor spawns this as `task-work`; a thin adapter over the existing
# autobuild machinery (delegation, never a second distillation).
cli.add_command(task_work)

# Add Template command group (deterministic render+parse gate, DIM1-F4/PB-8)
cli.add_command(template)


# ============================================================================
# Utility Commands
# ============================================================================


@cli.command()
def version():
    """Show GuardKit version."""
    from guardkit.cli import __version__

    console.print(f"GuardKit CLI version {__version__}")


@cli.command()
@click.option(
    "--connectivity/--no-connectivity",
    default=False,
    help="Test SDK connectivity to Claude API",
)
def doctor(connectivity: bool):
    """Check GuardKit installation and configuration."""
    from guardkit.cli.doctor import run_doctor

    exit_code = run_doctor(connectivity=connectivity)
    sys.exit(exit_code)


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point for CLI."""
    try:
        cli(obj={})
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"CLI error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
