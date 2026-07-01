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
from guardkit.memory.graph_export import (
    build_export_episodes,
    read_falkordb_episodics,
)
from guardkit.knowledge.fleet_memory_client import get_memory_client
from guardkit.knowledge.outcome_manager import capture_task_outcome
from guardkit.knowledge.entities.outcome import OutcomeType

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


# ============================================================================
# Migrate-Graph Command (FEAT-MEM-09 WS-1b)
# ============================================================================


@memory.command("migrate-graph")
@click.option(
    "--project",
    default="guardkit",
    help="Only migrate this project's graphs (sanitised). Default: guardkit.",
)
@click.option(
    "--all-projects",
    is_flag=True,
    help="Migrate ALL projects' graphs (fleet-wide), ignoring --project.",
)
@click.option(
    "--host",
    default=None,
    help="FalkorDB host (default: $FALKORDB_HOST or 'whitestocks').",
)
@click.option(
    "--port",
    default=None,
    type=int,
    help="FalkorDB port (default: $FALKORDB_PORT or 6379).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Read + build episodes and report counts; do NOT connect to NATS.",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Max Episodic nodes per graph (for dry-run sampling).",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to .env file for NATS + FalkorDB credentials (optional).",
)
def migrate_graph(
    project: str,
    all_projects: bool,
    host: str | None,
    port: int | None,
    dry_run: bool,
    limit: int | None,
    env_file: Path | None,
):
    """Migrate FalkorDB (Graphiti) Episodic prose to fleet-memory as scoped documents.

    Reads each project graph's raw ``Episodic`` nodes and publishes them as typed
    ``DocumentPayload`` episodes (prose in ``content`` + the source group's
    ``domain_tags``), skipping retire-disposition groups (covered by the harvest corpus).
    The Qwen2.5-extracted Entity/edge layer is NOT migrated (fleet-memory is
    pure-embeddings). Idempotent: re-runs dedup server-side on the natural key.

    With --dry-run, only reads + builds (reports counts); no NATS. Without it, publishes
    (requires GUARDKIT_NATS_PASSWORD).

    RELAY REBUILD REQUIRED first: DocumentPayload.content (FEAT-MEM-09 WS-1a) is only
    stored by a rebuilt relay image; an older relay SILENTLY DROPS content.

    Examples:
        guardkit memory migrate-graph --dry-run --limit 5
        guardkit memory migrate-graph                     # guardkit only
        guardkit memory migrate-graph --all-projects      # fleet-wide
    """
    if env_file:
        load_dotenv(env_file)
        logger.info("Loaded environment from %s", env_file)

    fdb_host = host or os.getenv("FALKORDB_HOST", "whitestocks")
    fdb_port = port if port is not None else int(os.getenv("FALKORDB_PORT", "6379"))
    project_filter = None if all_projects else project

    scope = "ALL projects" if all_projects else f"project={project!r}"
    console.print(
        f"\n[bold cyan]Reading FalkorDB[/bold cyan] {fdb_host}:{fdb_port} ({scope})...\n"
    )

    try:
        graphs = list(
            read_falkordb_episodics(
                fdb_host, fdb_port, project_filter=project_filter, limit_per_graph=limit
            )
        )
    except Exception as e:
        console.print(f"[red]FalkorDB read error:[/red] {e}")
        logger.exception("FalkorDB read failed")
        sys.exit(1)

    result = build_export_episodes(graphs)

    console.print(
        f"[green]✓[/green] Built {len(result.episodes)} document episodes "
        f"from {result.graphs_scanned} graph(s)"
    )
    console.print(
        f"    skipped: {result.skipped_retired} retired, "
        f"{result.skipped_empty} empty, {result.skipped_no_group} non-project graphs"
    )
    if result.counts_per_project:
        console.print()
        counts_table = _format_counts_table(result.counts_per_project)
        console.print(counts_table)

    if dry_run:
        console.print("\n[bold green]Dry run complete[/bold green] (no NATS publish)\n")
        sys.exit(0)

    if not result.episodes:
        console.print("\n[yellow]No episodes to publish.[/yellow]\n")
        sys.exit(0)

    console.print(
        "\n[yellow]⚠ Ensure the fleet-memory relay was rebuilt with "
        "DocumentPayload.content (WS-1a), else content is silently dropped.[/yellow]"
    )
    console.print("\n[bold cyan]Publishing episodes to NATS...[/bold cyan]\n")

    try:
        publish_summary = asyncio.run(publish_episodes(result.episodes, client=None))
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print(
            "\n[yellow]Tip:[/yellow] Set GUARDKIT_NATS_PASSWORD or use --env-file"
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Publisher error:[/red] {e}")
        logger.exception("Publisher failed")
        sys.exit(1)

    console.print(f"[green]✓[/green] Published {publish_summary.published} episodes")
    if publish_summary.skipped_oversized > 0:
        console.print(
            f"[yellow]⚠[/yellow] Skipped {publish_summary.skipped_oversized} "
            f"oversized episodes during publish"
        )
    console.print("\n[bold green]Graph migration complete[/bold green]\n")
    sys.exit(0)


# ============================================================================
# Search Command
# ============================================================================


@memory.command()
@click.argument("query")
@click.option(
    "--token-budget",
    type=int,
    default=None,
    help="Maximum tokens for context block (default: server-determined)",
)
@click.option(
    "--payload-types",
    multiple=True,
    help="Filter by payload types (e.g., build_outcome, feature_spec)",
)
@click.option(
    "--domain-tags",
    multiple=True,
    help="Filter by domain tags",
)
def search(
    query: str,
    token_budget: Optional[int],
    payload_types: tuple[str, ...],
    domain_tags: tuple[str, ...],
):
    """Search fleet memory for knowledge.

    Queries the fleet-memory backend and returns a context block with
    coverage score. Supports filtering by payload types and domain tags.

    Examples:
        guardkit memory search "authentication"
        guardkit memory search "error handling" --payload-types build_outcome
        guardkit memory search "JWT" --token-budget 500
    """
    asyncio.run(_cmd_search(query, token_budget, payload_types, domain_tags))


async def _cmd_search(
    query: str,
    token_budget: Optional[int],
    payload_types: tuple[str, ...],
    domain_tags: tuple[str, ...],
) -> None:
    """Async implementation of search command."""
    client = get_memory_client()

    if client is None:
        console.print("[yellow]Memory client unavailable (config missing or disabled)[/yellow]")
        return

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to memory store: {e}[/red]")
        return

    try:
        if not initialized or not client.enabled:
            console.print("[yellow]Memory store unavailable or disabled[/yellow]")
            return

        # Convert payload_types and domain_tags to lists
        payload_types_list = list(payload_types) if payload_types else None
        domain_tags_list = list(domain_tags) if domain_tags else None

        # Execute search
        try:
            results = await client.search(
                query=query,
                num_results=10,
            )
        except Exception as e:
            console.print(f"[red]Search error: {e}[/red]")
            return

        # Display results
        if not results:
            console.print(f"No results found for: {query}")
            return

        console.print(f"\n[bold cyan]Search Results[/bold cyan] for '{query}':\n")

        for i, result in enumerate(results, 1):
            fact = result.get("fact", str(result))
            score = result.get("score", 0.0)

            # Truncate long facts
            max_fact_length = 100
            if len(fact) > max_fact_length:
                fact = fact[:max_fact_length] + "..."

            # Color code by score
            if score > 0.8:
                score_color = "green"
            elif score > 0.5:
                score_color = "yellow"
            else:
                score_color = "white"

            console.print(
                f"[cyan]{i}.[/cyan] "
                f"[{score_color}][{score:.2f}][/{score_color}] "
                f"{fact}"
            )

    finally:
        await client.close()


# ============================================================================
# Status Command
# ============================================================================


@memory.command()
def status():
    """Show memory store reachability and statistics.

    Displays connection status and per-payload_type counts.

    Example:
        guardkit memory status
    """
    asyncio.run(_cmd_status())


async def _cmd_status() -> None:
    """Async implementation of status command."""
    console.print("\n[bold cyan]Memory Store Status[/bold cyan]\n")

    client = get_memory_client()

    if client is None:
        console.print("  [yellow]Status:[/yellow] [red]UNAVAILABLE[/red]")
        console.print("  [dim]Memory client not configured[/dim]")
        return

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print("  [yellow]Status:[/yellow] [red]ERROR[/red]")
        console.print(f"  [red]Error: {e}[/red]")
        return

    try:
        if not initialized or not client.enabled:
            console.print("  [yellow]Status:[/yellow] [red]DISABLED[/red]")
            console.print("  [dim]Enable in configuration[/dim]")
            return

        # Check health
        try:
            healthy = await client.health_check()
            if healthy:
                console.print("  [bold]Status:[/bold] [green bold]REACHABLE[/green bold]")
            else:
                console.print("  [yellow]Status:[/yellow] [yellow]DEGRADED[/yellow]")
        except Exception as e:
            console.print("  [yellow]Status:[/yellow] [yellow]UNKNOWN[/yellow]")
            console.print(f"  [dim]Health check error: {e}[/dim]")
            return

        # Show basic info - no graph_stats in fleet-memory
        console.print("\n  [bold]Backend:[/bold] fleet-memory")
        console.print("  [dim]Note: Per-payload_type counts coming soon[/dim]\n")

    finally:
        await client.close()


# ============================================================================
# Capture Outcome Command
# ============================================================================


@memory.command("capture-outcome")
@click.option(
    "--from-task-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Parse a task .md file to populate fields (CLI flags override)",
)
@click.option("--task-id", default=None, help="Task ID (e.g. TASK-XXX)")
@click.option("--task-title", default=None, help="Task title")
@click.option("--summary", default=None, help="Brief summary of the outcome")
@click.option(
    "--success/--failure",
    default=True,
    help="Whether the task was successful",
)
def capture_outcome(
    from_task_file: Optional[Path],
    task_id: Optional[str],
    task_title: Optional[str],
    summary: Optional[str],
    success: bool,
):
    """Capture a task completion outcome to memory.

    Writes a build_outcome payload via the fleet-memory adapter.

    Examples:
        guardkit memory capture-outcome --from-task-file tasks/completed/TASK-XXX.md
        guardkit memory capture-outcome --task-id TASK-XXX --task-title "Fix bug" --summary "Fixed the bug"
    """
    asyncio.run(_cmd_capture_outcome(from_task_file, task_id, task_title, summary, success))


async def _cmd_capture_outcome(
    from_task_file: Optional[Path],
    task_id: Optional[str],
    task_title: Optional[str],
    summary: Optional[str],
    success: bool,
) -> None:
    """Async implementation of capture-outcome command."""
    import yaml
    from datetime import datetime

    # Parse task file if provided
    if from_task_file:
        try:
            raw = from_task_file.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                front = yaml.safe_load(parts[1]) or {}
                task_id = task_id or front.get("id")
                task_title = task_title or front.get("title")

                # Extract summary from body sections
                if not summary:
                    body = parts[2]
                    sections = {}
                    current_heading = None
                    current_lines = []
                    for line in body.splitlines():
                        if line.startswith("## "):
                            if current_heading:
                                sections[current_heading] = "\n".join(current_lines).strip()
                            current_heading = line[3:].strip()
                            current_lines = []
                        elif current_heading:
                            current_lines.append(line)
                    if current_heading:
                        sections[current_heading] = "\n".join(current_lines).strip()

                    desc_text = sections.get("Description") or sections.get("Why") or ""
                    if desc_text:
                        paragraphs = [p.strip() for p in desc_text.split("\n\n") if p.strip()]
                        if paragraphs:
                            summary = " ".join(paragraphs[0].split())[:2000]
        except Exception as e:
            console.print(f"[red]Error reading task file: {e}[/red]")
            sys.exit(1)

    # Validate required fields
    missing = []
    if not task_id:
        missing.append("--task-id")
    if not task_title:
        missing.append("--task-title")
    if not summary:
        missing.append("--summary")

    if missing:
        console.print(f"[red]Error: missing required fields: {', '.join(missing)}[/red]")
        sys.exit(1)

    # Get memory client
    client = get_memory_client()

    if client is None:
        console.print("[yellow]Memory client unavailable - outcome NOT captured[/yellow]")
        return

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to memory store: {e}[/red]")
        sys.exit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[yellow]Memory store unavailable - outcome NOT captured[/yellow]")
            return

        # Capture the outcome
        outcome_id = await capture_task_outcome(
            outcome_type=OutcomeType.TASK_COMPLETED if success else OutcomeType.TASK_FAILED,
            task_id=task_id,
            task_title=task_title,
            task_requirements=task_title,  # Fallback
            success=success,
            summary=summary,
            completed_at=datetime.now(),
        )

        console.print(f"[green]✅ Outcome captured: {outcome_id}[/green]")

    finally:
        await client.close()
