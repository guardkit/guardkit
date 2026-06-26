"""GuardKit memory CLI commands.

Commands:
- memory harvest: Harvest documentation episodes and publish to NATS
- memory harvest --dry-run: Preview harvest without NATS connection

Example:
    $ guardkit memory harvest
    $ guardkit memory harvest --dry-run
    $ guardkit memory harvest --docs-root /path/to/docs
    $ guardkit memory harvest --env-file /path/to/.env
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from guardkit.memory.harvest_walker import walk_harvest_dirs
from guardkit.memory.harvest_publisher import publish_episodes

console = Console()
logger = logging.getLogger(__name__)


def _find_repo_root(start_path: Path | None = None) -> Path:
    """Find repository root by looking for .git directory.

    Args:
        start_path: Starting directory (defaults to cwd).

    Returns:
        Path to repository root.

    Raises:
        FileNotFoundError: If no git repository found.
    """
    current = start_path or Path.cwd()

    # Traverse up looking for .git
    for _ in range(10):  # Max 10 levels up
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    raise FileNotFoundError(
        "Could not find repository root (no .git directory found). "
        "Run this command from within a git repository."
    )


def _format_oversized_report(skipped: list[tuple[str, int]]) -> str:
    """Format oversized docs skip report as a Rich table.

    Args:
        skipped: List of (path, size) tuples.

    Returns:
        Formatted string representation of the table.
    """
    if not skipped:
        return ""

    table = Table(title="Oversized Documents Skipped", show_header=True)
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right", style="yellow")

    for path, size in skipped:
        # Format size as KB
        size_kb = size / 1024
        table.add_row(path, f"{size_kb:.1f} KB")

    return table


def _format_counts_table(counts: dict[str, int]) -> Table:
    """Format episode type counts as a Rich table.

    Args:
        counts: Dictionary mapping episode_type to count.

    Returns:
        Rich Table instance.
    """
    table = Table(title="Episodes by Type", show_header=True)
    table.add_column("Episode Type", style="cyan")
    table.add_column("Count", justify="right", style="green")

    # Sort by episode type for consistent output
    for episode_type in sorted(counts.keys()):
        count = counts[episode_type]
        table.add_row(episode_type, str(count))

    return table


# ============================================================================
# Memory Command Group
# ============================================================================


@click.group()
def memory():
    """Memory and knowledge graph commands.

    Commands for harvesting documentation episodes and publishing
    to NATS for downstream knowledge processing.
    """
    pass


# ============================================================================
# Harvest Command
# ============================================================================


@memory.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview harvest without connecting to NATS (reports counts only)",
)
@click.option(
    "--docs-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Repository root containing docs/ directory (default: auto-detect)",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to .env file for NATS credentials (optional)",
)
def harvest(dry_run: bool, docs_root: Path | None, env_file: Path | None):
    """Harvest documentation episodes and publish to NATS.

    Walks the curated harvest directories (docs/features/, docs/guides/, etc.),
    builds MemoryEpisodeV1 episodes for each markdown file, and publishes them
    to NATS for downstream knowledge processing.

    With --dry-run, only the walker runs - prints counts and oversized skip
    report without connecting to NATS. No GUARDKIT_NATS_PASSWORD is required.

    Without --dry-run, runs walker then publisher. Requires GUARDKIT_NATS_PASSWORD
    environment variable or --env-file.

    Examples:
        # Dry run (no NATS connection)
        guardkit memory harvest --dry-run

        # Full harvest with NATS publish
        guardkit memory harvest

        # Use custom env file for credentials
        guardkit memory harvest --env-file /path/to/.env
    """
    # Load env file if provided (before any NATS password read)
    if env_file:
        load_dotenv(env_file)
        logger.info("Loaded environment from %s", env_file)

    # Find repo root
    try:
        if docs_root is None:
            docs_root = _find_repo_root()
            logger.info("Auto-detected repo root: %s", docs_root)
        else:
            logger.info("Using provided docs root: %s", docs_root)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # === Walker Phase ===
    console.print("\n[bold cyan]Walking harvest directories...[/bold cyan]\n")

    try:
        harvest_result = walk_harvest_dirs(docs_root)
    except Exception as e:
        console.print(f"[red]Walker error:[/red] {e}")
        logger.exception("Walker failed")
        sys.exit(1)

    # Print walker summary
    console.print(f"[green]✓[/green] Harvested {len(harvest_result.episodes)} episodes")

    if harvest_result.skipped_empty > 0:
        console.print(
            f"[yellow]⚠[/yellow] Skipped {harvest_result.skipped_empty} empty documents"
        )

    if harvest_result.skipped_oversized:
        console.print(
            f"[yellow]⚠[/yellow] Skipped {len(harvest_result.skipped_oversized)} "
            f"oversized documents (>900KB)"
        )
        # Print oversized table
        table = _format_oversized_report(harvest_result.skipped_oversized)
        if table:
            console.print(table)

    # Print counts per type
    if harvest_result.counts_per_type:
        console.print()
        counts_table = _format_counts_table(harvest_result.counts_per_type)
        console.print(counts_table)

    # === Dry Run Exit ===
    if dry_run:
        console.print("\n[bold green]Dry run complete[/bold green] (no NATS publish)\n")
        sys.exit(0)

    # === Publisher Phase ===
    console.print("\n[bold cyan]Publishing episodes to NATS...[/bold cyan]\n")

    # Check for NATS password (publisher will raise ValueError if missing)
    try:
        # Run publisher (async)
        publish_summary = asyncio.run(
            publish_episodes(harvest_result.episodes, client=None)
        )
    except ValueError as e:
        # Catch missing/blank GUARDKIT_NATS_PASSWORD
        console.print(f"[red]Error:[/red] {e}")
        console.print(
            "\n[yellow]Tip:[/yellow] Set GUARDKIT_NATS_PASSWORD in your environment "
            "or use --env-file"
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Publisher error:[/red] {e}")
        logger.exception("Publisher failed")
        sys.exit(1)

    # Print publisher summary
    console.print(f"[green]✓[/green] Published {publish_summary.published} episodes")

    if publish_summary.skipped_oversized > 0:
        console.print(
            f"[yellow]⚠[/yellow] Skipped {publish_summary.skipped_oversized} "
            f"oversized episodes during publish"
        )

    # Print published counts per type
    if publish_summary.counts_per_type:
        console.print()
        pub_counts_table = _format_counts_table(publish_summary.counts_per_type)
        console.print(pub_counts_table)

    console.print("\n[bold green]Harvest complete[/bold green]\n")

    # Exit 0 on success (including when oversized docs were skipped)
    sys.exit(0)
