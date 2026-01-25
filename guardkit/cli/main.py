"""
GuardKit CLI main entry point.

This module provides the main Click application for GuardKit CLI commands.

Example:
    $ python3 -m guardkit.cli.main autobuild task TASK-AB-001
    $ python3 -m guardkit.cli.main autobuild status TASK-AB-001
"""

import logging
import sys

import click
from rich.console import Console

from guardkit.cli.autobuild import autobuild

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
