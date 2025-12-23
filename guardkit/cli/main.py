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
def doctor():
    """Check GuardKit installation and configuration."""
    console.print("[bold]GuardKit Doctor[/bold]\n")

    # Check git repository
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
        console.print("[green]✓[/green] Git repository detected")
    except subprocess.CalledProcessError:
        console.print("[red]✗[/red] Not a git repository")
        sys.exit(1)

    # Check Python version
    import sys as _sys

    py_version = f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}"
    if _sys.version_info >= (3, 9):
        console.print(f"[green]✓[/green] Python {py_version}")
    else:
        console.print(
            f"[yellow]⚠[/yellow] Python {py_version} (3.9+ recommended)"
        )

    # Check dependencies
    try:
        import click as _click
        import frontmatter as _fm
        from rich import __version__ as rich_version

        console.print(f"[green]✓[/green] Dependencies installed")
        if console.is_terminal:
            console.print(f"  - click: {_click.__version__}")
            console.print(f"  - rich: {rich_version}")
            console.print(f"  - frontmatter: installed")
    except ImportError as e:
        console.print(f"[red]✗[/red] Missing dependency: {e.name}")
        sys.exit(1)

    # Check worktrees directory
    from pathlib import Path

    worktrees_dir = Path.cwd() / ".guardkit" / "worktrees"
    if worktrees_dir.exists():
        console.print(f"[green]✓[/green] Worktrees directory: {worktrees_dir}")
    else:
        console.print(
            f"[yellow]⚠[/yellow] Worktrees directory not found (will be created on first use)"
        )

    console.print("\n[green]GuardKit installation OK[/green]")


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
