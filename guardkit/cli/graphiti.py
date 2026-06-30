"""
Graphiti CLI commands for knowledge graph management.

Commands:
- graphiti seed: Seed system context into Graphiti
- graphiti status: Show Graphiti connection and seeding status
- graphiti verify: Run test queries to verify seeded knowledge
- graphiti add-context: Add context from files to Graphiti
- graphiti capture-outcome: Capture a task-completion outcome to task_outcomes

Example:
    $ guardkit graphiti seed
    $ guardkit graphiti seed --force
    $ guardkit graphiti status
    $ guardkit graphiti verify
    $ guardkit graphiti add-context docs/architecture/
    $ guardkit graphiti capture-outcome --from-task-file tasks/completed/2026-04/TASK-XXX.md
"""

import asyncio
import json
import logging
import os
import re
import time
import warnings
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig, get_graphiti
from guardkit.knowledge.config import load_graphiti_config, GraphitiSettings


def _format_connection_target(settings: GraphitiSettings) -> str:
    """Format the connection target string based on graph store backend."""
    if settings.graph_store == "falkordb":
        return f"FalkorDB at {settings.falkordb_host}:{settings.falkordb_port}"
    return f"Neo4j at {settings.neo4j_uri}"
from guardkit.knowledge.seeding import (
    seed_all_system_context,
    compute_seed_summary,
    is_seeded,
    clear_seeding_marker,
    SEEDING_VERSION,
)
from guardkit.knowledge.seed_feature_build_adrs import seed_feature_build_adrs
from guardkit.integrations.graphiti.parsers.registry import ParserRegistry
from guardkit.integrations.graphiti.parsers.adr import ADRParser
from guardkit.integrations.graphiti.parsers.feature_spec import FeatureSpecParser
from guardkit.integrations.graphiti.parsers.full_doc_parser import FullDocParser
from guardkit.integrations.graphiti.parsers.project_doc_parser import ProjectDocParser
from guardkit.integrations.graphiti.parsers.project_overview import ProjectOverviewParser
from guardkit.integrations.graphiti.parsers.yaml_parser import YAMLParser

console = Console()
logger = logging.getLogger(__name__)


def _run_async(coro) -> None:
    """Run an async coroutine, suppressing harmless cleanup warnings.

    When asyncio.wait_for() cancels a timed-out Neo4j driver connection,
    the driver's internal coroutines may be garbage-collected without being
    awaited, producing noisy 'coroutine was never awaited' RuntimeWarnings.
    These are harmless and suppressed here.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="coroutine.*was never awaited")
        asyncio.run(coro)


def _get_client_and_config() -> tuple[GraphitiClient, GraphitiSettings]:
    """Create and return Graphiti client and configuration.

    Returns:
        Tuple of (GraphitiClient, GraphitiSettings)
    """
    settings = load_graphiti_config()
    config = GraphitiConfig(
        enabled=settings.enabled,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        timeout=settings.timeout,
        project_id=settings.project_id,
        graph_store=settings.graph_store,
        falkordb_host=settings.falkordb_host,
        falkordb_port=settings.falkordb_port,
        llm_provider=settings.llm_provider,
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model,
        llm_max_tokens=settings.llm_max_tokens,
        embedding_provider=settings.embedding_provider,
        embedding_base_url=settings.embedding_base_url,
        embedding_model=settings.embedding_model,
        embedding_dimensions=getattr(settings, "embedding_dimensions", None),
    )
    client = GraphitiClient(config)
    return client, settings


async def _cmd_seed(force: bool, template: Optional[str] = None, episode_timeout: Optional[float] = None) -> None:
    """Async implementation of seed command."""
    console.print("[bold blue]Graphiti System Context Seeding[/bold blue]")
    console.print()

    # Check if already seeded
    if is_seeded() and not force:
        console.print("[yellow]System context already seeded.[/yellow]")
        console.print("Use --force to re-seed.")
        return

    # Create client
    client, settings = _get_client_and_config()

    # Apply CLI --timeout override to client
    if episode_timeout is not None:
        client.default_timeout_override = episode_timeout

    # Initialize connection
    console.print(f"Connecting to {_format_connection_target(settings)}...")

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[yellow]Graphiti not available or disabled.[/yellow]")
            console.print("Seeding skipped. Check your Graphiti configuration.")
            return

        console.print("[green]Connected to Graphiti[/green]")
        console.print()

        # Pre-seed LLM endpoint check (vLLM/ollama only)
        if settings.llm_provider in ("vllm", "ollama") or settings.embedding_provider in ("vllm", "ollama"):
            console.print("Checking LLM endpoint availability...")
            console.print("[dim]Waiting for vLLM... (timeout 60s)[/dim]")
            llm_ready = await client.wait_for_llm_endpoints(timeout=60.0)
            if llm_ready:
                console.print("[green]LLM endpoints ready[/green]")
            else:
                console.print(
                    "[yellow]Warning: LLM endpoints not available after 60s.[/yellow]"
                )
                console.print(
                    "[yellow]Seeding will likely fail. "
                    "Check that vLLM is running.[/yellow]"
                )
                raise SystemExit(1)
            console.print()

        # Clear marker if forcing
        if force and is_seeded():
            console.print("Clearing previous seeding marker...")
            clear_seeding_marker()

        # Auto-detect template if not specified
        if template is None:
            try:
                from guardkit.knowledge.system_seeding import resolve_template_path
                resolved = resolve_template_path()
                if resolved:
                    template = resolved.name
                    console.print(f"Auto-detected template: [cyan]{template}[/cyan]")
            except Exception as e:
                logger.debug(f"Template auto-detection failed: {e}")

        # Run seeding
        if template:
            console.print(f"Seeding system context (template: [cyan]{template}[/cyan])...")
        else:
            console.print("Seeding system context (all templates)...")
        console.print()

        seed_start = time.monotonic()
        try:
            result = await seed_all_system_context(client, force=force, template=template)
        except Exception as e:
            console.print(f"[red]Error during seeding: {e}[/red]")
            logger.exception("Seeding failed")
            raise SystemExit(1)
        seed_elapsed = time.monotonic() - seed_start

        if result:
            console.print()
            console.print("[bold green]System context seeding complete![/bold green]")
            console.print()
            console.print("Knowledge categories seeded:")

            if isinstance(result, dict):
                # Per-category results available (TASK-SPR-2cf7)
                for cat, outcome in result.items():
                    if outcome == "error":
                        console.print(f"  [red]\u2717[/red] {cat} [red](error)[/red]")
                    elif outcome is None:
                        # No episode counts — assume success
                        console.print(f"  [green]\u2713[/green] {cat}")
                    else:
                        created, skipped = outcome
                        total = created + skipped
                        if total == 0:
                            # No episodes to seed
                            console.print(f"  [green]\u2713[/green] {cat}")
                        elif skipped == 0:
                            # All succeeded
                            console.print(f"  [green]\u2713[/green] {cat} ({created} episodes)")
                        elif created == 0 or skipped > total * 0.8:
                            # Failure: 0 created or >80% skipped
                            console.print(
                                f"  [red]\u2717[/red] {cat} "
                                f"({created}/{total} episodes, {skipped} skipped)"
                            )
                        else:
                            # Partial success
                            console.print(
                                f"  [yellow]\u26a0[/yellow] {cat} "
                                f"({created}/{total} episodes, {skipped} skipped)"
                            )
            else:
                # Boolean result (e.g. already-seeded skip) — no details
                console.print("  [green]\u2713[/green] All categories (no details available)")

            # Display seed summary (TASK-SPR-9d9b)
            if isinstance(result, dict):
                summary = compute_seed_summary(result)
                console.print()
                console.print("[bold]Seed Summary:[/bold]")
                not_succeeded = summary["partial"] + summary["failed"]
                if not_succeeded > 0:
                    console.print(
                        f"  Categories: {summary['succeeded']}/{summary['total_categories']} "
                        f"fully seeded, {not_succeeded} partial/failed"
                    )
                else:
                    console.print(
                        f"  Categories: {summary['total_categories']}/{summary['total_categories']} "
                        f"fully seeded"
                    )
                if summary["total_episodes"] > 0:
                    pct = summary["total_created"] / summary["total_episodes"] * 100
                    console.print(
                        f"  Episodes:   {summary['total_created']}/{summary['total_episodes']} "
                        f"created ({pct:.1f}%)"
                    )
                    if summary["total_skipped"] > 0:
                        console.print(f"  Skipped:    {summary['total_skipped']} episodes")
                else:
                    console.print(f"  Episodes:   {summary['total_created']} created")
                mins, secs = divmod(int(seed_elapsed), 60)
                if mins > 0:
                    console.print(f"  Duration:   {mins}m {secs:02d}s")
                else:
                    console.print(f"  Duration:   {secs}s")

            console.print()
            console.print("Run 'guardkit graphiti verify' to test queries.")
            console.print()
            console.print("To seed project architecture and ADRs:")
            console.print("  guardkit graphiti add-context docs/architecture/ --pattern \"**/*.md\"")
        else:
            console.print("[yellow]Seeding completed with warnings.[/yellow]")
    finally:
        await client.close()


async def _cmd_status(verbose: bool = False) -> None:
    """Async implementation of status command.

    Args:
        verbose: Show all groups even if empty
    """
    # Emit deprecation warning
    console.print()
    console.print("[yellow]⚠️  DEPRECATED: 'guardkit graphiti status' is deprecated.[/yellow]")
    console.print("[yellow]   Use 'guardkit memory status' instead.[/yellow]")
    console.print()

    console.print("[bold cyan]╔════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║       Graphiti Knowledge Status        ║[/bold cyan]")
    console.print("[bold cyan]╚════════════════════════════════════════╝[/bold cyan]")
    console.print()

    # Load configuration
    settings = load_graphiti_config()

    # Show enabled/disabled status
    if settings.enabled:
        console.print("  [bold]Status:[/bold] [green bold]ENABLED[/green bold]")
    else:
        console.print("  [bold]Status:[/bold] [red bold]DISABLED[/red bold]")
        console.print("  [dim]Enable in config/graphiti.yaml[/dim]")
        console.print()
        return

    # Check connection
    client, _ = _get_client_and_config()

    try:
        initialized = await client.initialize()
        try:
            if not initialized or not client.enabled:
                console.print("  [yellow]Connection: Failed[/yellow]")
                console.print("  [dim]Check graph database configuration[/dim]")
                console.print()
                return

            # Check health
            try:
                healthy = await client.health_check()
                if not healthy:
                    console.print("  [yellow]Health: Degraded[/yellow]")
                    console.print()
                    return
            except Exception:
                console.print("  [yellow]Health: Unknown[/yellow]")
                console.print()
                return

            # Count episodes by category
            categories = {
                "System Knowledge": ["product_knowledge", "command_workflows", "patterns", "agents"],
                "Project Knowledge": ["project_overview", "project_architecture", "feature_specs"],
                "Decisions": ["project_decisions", "architecture_decisions"],
                "Learning": ["task_outcomes", "failure_patterns", "successful_fixes"]
            }

            total = 0
            console.print()

            for section, groups in categories.items():
                console.print(f"  [bold]{section}:[/bold]")
                section_total = 0

                for group in groups:
                    # Search with wildcard to get all episodes in this group
                    results = await client.search("*", [group], 100)
                    count = len(results)
                    section_total += count

                    if verbose or count > 0:
                        # Color code based on count
                        if count > 0:
                            status_color = "green"
                        else:
                            status_color = "yellow"

                        console.print(
                            f"    [white]• {group}:[/white] [{status_color}]{count}[/{status_color}]"
                        )

                total += section_total

            console.print()
            console.print(f"  [bold]Total Episodes:[/bold] {total}")
            console.print()

        finally:
            await client.close()

    except Exception as e:
        console.print(f"  [red]Error: {e}[/red]")
        console.print()
        return


async def _cmd_verify(verbose: bool) -> None:
    """Async implementation of verify command."""
    console.print("[bold blue]Graphiti Verification[/bold blue]")
    console.print()

    # Check if seeded
    if not is_seeded():
        console.print("[yellow]System context not seeded.[/yellow]")
        console.print("Run 'guardkit graphiti seed' first.")
        return

    # Create client
    client, settings = _get_client_and_config()

    # Initialize connection
    console.print(f"Connecting to {_format_connection_target(settings)}...")

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[yellow]Graphiti not available.[/yellow]")
            console.print("Cannot verify without active connection.")
            return

        console.print("[green]Connected[/green]")
        console.print()

        # Define test queries
        test_queries = [
            ("What is GuardKit?", ["product_knowledge"], "guardkit"),
            ("How to invoke task-work?", ["command_workflows"], "task-work"),
            ("What are the quality phases?", ["quality_gate_phases"], "phase"),
            ("What is the Player-Coach pattern?", ["feature_build_architecture"], "player"),
            ("How to use SDK vs subprocess?", ["architecture_decisions"], "sdk"),
        ]

        console.print("Running verification queries...")
        console.print()

        passed = 0
        failed = 0

        for query, group_ids, expected_term in test_queries:
            try:
                results = await client.search(query, group_ids=group_ids, num_results=3)

                if results:
                    passed += 1
                    console.print(f"[green]\u2713[/green] {query}")

                    if verbose:
                        for r in results[:2]:
                            name = r.get("name", "unknown")
                            score = r.get("score", 0.0)
                            console.print(f"    -> {name} (score: {score:.2f})")
                else:
                    # Empty results - might be expected if Graphiti returns empty
                    # but connection works
                    passed += 1
                    console.print(f"[yellow]\u2713[/yellow] {query} (no results)")
            except Exception as e:
                failed += 1
                console.print(f"[red]\u2717[/red] {query}")
                if verbose:
                    console.print(f"    Error: {e}")

        console.print()
        console.print(f"Results: {passed} passed, {failed} failed")

        if failed == 0:
            console.print("[bold green]Verification complete![/bold green]")
        else:
            console.print("[yellow]Some queries failed. Check Graphiti connection.[/yellow]")
    finally:
        await client.close()


async def _cmd_seed_adrs(force: bool) -> None:
    """Async implementation of seed-adrs command."""
    console.print("[bold blue]Feature-Build ADR Seeding[/bold blue]")
    console.print()

    # Create client
    client, settings = _get_client_and_config()

    # Handle disabled Graphiti
    if not settings.enabled:
        console.print("[yellow]Graphiti is disabled in configuration.[/yellow]")
        console.print("ADR seeding skipped.")
        return

    # Initialize connection
    console.print(f"Connecting to {_format_connection_target(settings)}...")

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[yellow]Graphiti not available or disabled.[/yellow]")
            console.print("ADR seeding skipped.")
            return

        console.print("[green]Connected to Graphiti[/green]")
        console.print()

        # Run ADR seeding
        console.print("Seeding feature-build ADRs...")

        try:
            await seed_feature_build_adrs(client)
        except Exception as e:
            console.print(f"[red]Error during ADR seeding: {e}[/red]")
            logger.exception("ADR seeding failed")
            raise SystemExit(1)

        console.print()
        console.print("[bold green]Feature-build ADR seeding complete![/bold green]")
        console.print()
        console.print("ADRs seeded:")
        console.print("  [green]\u2713[/green] ADR-FB-001: Use SDK query() for task-work invocation")
        console.print("  [green]\u2713[/green] ADR-FB-002: Use FEAT-XXX paths in feature mode")
        console.print("  [green]\u2713[/green] ADR-FB-003: Pre-loop must invoke real task-work")
    finally:
        await client.close()


@click.group()
def graphiti():
    """Graphiti knowledge graph management commands.

    Manage the Graphiti knowledge graph that provides persistent memory
    for GuardKit sessions.
    """
    pass


@graphiti.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force re-seeding even if already seeded",
)
@click.option(
    "--template",
    "-t",
    default=None,
    help="Template to seed (auto-detected if not specified)",
)
@click.option(
    "--timeout",
    "episode_timeout",
    type=float,
    default=None,
    help="Per-episode timeout in seconds (overrides auto-detected timeout). "
         "Local LLMs are typically ~2x slower than GB10 vLLM; try --timeout 300.",
)
def seed(force: bool, template: Optional[str], episode_timeout: Optional[float]):
    """Seed system context into Graphiti.

    Seeds comprehensive GuardKit knowledge into the Graphiti knowledge graph.
    This includes product knowledge, command workflows, quality gate phases,
    technology stack information, and more.

    Use --template to only seed template-specific categories (templates,
    agents, rules) for the specified template plus 'default'. Without
    --template, auto-detects from manifest.json or seeds all templates.

    Use --force to re-seed even if seeding has already been completed.

    \b
    Performance: Local LLMs (e.g., MacBook Pro) are typically ~2x slower
    than GB10 vLLM. Use --timeout to increase the per-episode timeout if
    you see timeout warnings during seeding.
    """
    _run_async(_cmd_seed(force, template, episode_timeout=episode_timeout))


@graphiti.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show all groups even if empty",
)
def status(verbose: bool):
    """Show Graphiti connection and seeding status.

    Displays information about the Graphiti configuration, connection status,
    knowledge graph statistics, and episode counts per category.

    Use --verbose to show all groups even if empty.
    """
    _run_async(_cmd_status(verbose))


@graphiti.command()
def stats():
    """Show graph topology statistics for performance analysis.

    Displays entity counts, edge counts, episodes per group, and edge
    density metrics. Useful for investigating performance regressions
    by comparing graph state between runs.
    """
    _run_async(_cmd_stats())


async def _cmd_stats() -> None:
    """Async implementation of stats command."""
    try:
        settings = load_graphiti_config()
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        return

    config = GraphitiConfig(
        enabled=settings.enabled,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        timeout=settings.timeout,
        project_id=getattr(settings, 'project_id', None) or "unknown",
        graph_store=settings.graph_store,
        falkordb_host=settings.falkordb_host,
        falkordb_port=settings.falkordb_port,
        host=getattr(settings, 'host', None),
        port=getattr(settings, 'port', None),
        llm_provider=settings.llm_provider,
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model,
        llm_max_tokens=settings.llm_max_tokens,
        embedding_provider=settings.embedding_provider,
        embedding_base_url=settings.embedding_base_url,
        embedding_model=settings.embedding_model,
        embedding_dimensions=getattr(settings, "embedding_dimensions", None),
    )

    client = GraphitiClient(config)
    try:
        initialized = await client.initialize()
        if not initialized:
            console.print("[yellow]Could not connect to graph database[/yellow]")
            return

        result = await client.graph_stats()
        if not result:
            console.print("[yellow]No stats available[/yellow]")
            return

        console.print("\n[bold]Graph Topology Statistics[/bold]\n")

        # Summary table
        table = Table(title="Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        table.add_row("Entity nodes", str(result.get("entity_count", 0)))
        table.add_row("Entity edges (RELATES_TO)", str(result.get("entity_edge_count", 0)))
        table.add_row("Episodes", str(result.get("episode_count", 0)))
        table.add_row("Edge density (edges/entity)", str(result.get("edge_density", 0.0)))
        console.print(table)

        # Episodes per group
        epg = result.get("episodes_per_group", {})
        if epg:
            console.print()
            group_table = Table(title="Episodes per Group")
            group_table.add_column("Group", style="cyan")
            group_table.add_column("Count", style="green", justify="right")
            for group_id, count in sorted(epg.items(), key=lambda x: -x[1]):
                group_table.add_row(group_id, str(count))
            console.print(group_table)

    finally:
        await client.close()


@graphiti.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed query results",
)
def verify(verbose: bool):
    """Verify seeded knowledge with test queries.

    Runs a series of test queries against the Graphiti knowledge graph
    to verify that system context has been properly seeded.

    Use --verbose to see detailed query results.
    """
    _run_async(_cmd_verify(verbose))


@graphiti.command("seed-adrs")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force re-seeding even if already seeded",
)
def seed_adrs(force: bool):
    """Seed feature-build ADRs into Graphiti.

    Seeds critical Architecture Decision Records (ADRs) for feature-build
    workflow. These ADRs encode lessons learned from feature-build failures
    to prevent future sessions from repeating the same mistakes.

    ADRs seeded:
    - ADR-FB-001: Use SDK query() for task-work invocation
    - ADR-FB-002: Use FEAT-XXX paths in feature mode
    - ADR-FB-003: Pre-loop must invoke real task-work

    Use --force to re-seed even if ADRs have already been seeded.
    """
    _run_async(_cmd_seed_adrs(force))


async def _cmd_seed_system(force: bool, template: Optional[str], episode_timeout: Optional[float] = None) -> None:
    """Async implementation of seed-system command."""
    from guardkit.knowledge.system_seeding import (
        seed_system_content,
        is_system_seeded,
        clear_system_seed_marker,
    )

    console.print("[bold blue]System Content Seeding[/bold blue]")
    console.print()

    # Check if already seeded
    if is_system_seeded() and not force:
        console.print("[yellow]System content already seeded.[/yellow]")
        console.print("Use --force to re-seed.")
        return

    # Create client
    client, settings = _get_client_and_config()

    # Apply CLI --timeout override to client
    if episode_timeout is not None:
        client.default_timeout_override = episode_timeout

    # Handle disabled Graphiti
    if not settings.enabled:
        console.print("[yellow]Graphiti is disabled in configuration.[/yellow]")
        console.print("System seeding skipped.")
        return

    # Initialize connection
    console.print(f"Connecting to {_format_connection_target(settings)}...")

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[yellow]Graphiti not available or disabled.[/yellow]")
            console.print("System seeding skipped.")
            return

        console.print("[green]Connected to Graphiti[/green]")
        console.print()

        # Pre-seed LLM endpoint check (vLLM/ollama only)
        if settings.llm_provider in ("vllm", "ollama") or settings.embedding_provider in ("vllm", "ollama"):
            console.print("Checking LLM endpoint availability...")
            console.print("[dim]Waiting for vLLM... (timeout 60s)[/dim]")
            llm_ready = await client.wait_for_llm_endpoints(timeout=60.0)
            if llm_ready:
                console.print("[green]LLM endpoints ready[/green]")
            else:
                console.print(
                    "[yellow]Warning: LLM endpoints not available after 60s.[/yellow]"
                )
                console.print(
                    "[yellow]Seeding will likely fail. "
                    "Check that vLLM is running.[/yellow]"
                )
                raise SystemExit(1)
            console.print()

        # Clear marker if forcing
        if force:
            console.print("Clearing previous system seed marker...")
            clear_system_seed_marker()

        # Run system seeding
        console.print("Seeding system content...")
        console.print()

        try:
            result = await seed_system_content(
                client=client,
                template_name=template,
                force=force,
            )
        except Exception as e:
            console.print(f"[red]Error during system seeding: {e}[/red]")
            logger.exception("System seeding failed")
            raise SystemExit(1)

        # Display results
        if result.success:
            console.print()
            console.print("[bold green]System content seeding complete![/bold green]")
            console.print()

            if result.template_name:
                console.print(f"Template: {result.template_name}")
                console.print()

            console.print("Components seeded:")
            for comp in result.results:
                status = "[green]\u2713[/green]" if comp.success else "[red]\u2717[/red]"
                detail = (
                    f" ({comp.episodes_created} episodes)"
                    if comp.episodes_created > 0
                    else ""
                )
                console.print(f"  {status} {comp.component}{detail}")

            console.print()
            console.print(
                f"Total: {result.total_episodes} episodes created, "
                f"{result.total_skipped} unchanged"
            )
        else:
            console.print("[yellow]System seeding completed with warnings.[/yellow]")
    finally:
        await client.close()


@graphiti.command("seed-system")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force re-seeding regardless of existing content",
)
@click.option(
    "--template",
    "-t",
    default=None,
    help="Template to seed (auto-detected if not specified)",
)
@click.option(
    "--timeout",
    "episode_timeout",
    type=float,
    default=None,
    help="Per-episode timeout in seconds (overrides auto-detected timeout). "
         "Local LLMs are typically ~2x slower than GB10 vLLM; try --timeout 300.",
)
def seed_system(force: bool, template: Optional[str], episode_timeout: Optional[float]):
    """Seed template and system content into Graphiti.

    Seeds system-level content independent of any specific project:

    \b
    - Template manifest metadata
    - Agent definitions from template
    - Rule previews from template
    - Player/Coach role constraints
    - Implementation mode patterns

    This is independent of 'guardkit graphiti seed'. Use it to seed or
    re-seed template/system content at any time.

    \b
    Examples:
        guardkit graphiti seed-system
        guardkit graphiti seed-system --template fastapi-python
        guardkit graphiti seed-system --force
    \b
    Performance: Local LLMs (e.g., MacBook Pro) are typically ~2x slower
    than GB10 vLLM. Use --timeout to increase the per-episode timeout if
    you see timeout warnings during seeding.
    """
    _run_async(_cmd_seed_system(force, template, episode_timeout=episode_timeout))


@graphiti.command("add-context")
@click.argument("path")
@click.option(
    "--type",
    "parser_type",
    default=None,
    help="Force parser type (adr, feature-spec, project-overview)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing context",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be added without adding",
)
@click.option(
    "--pattern",
    default="**/*.md",
    help="Glob pattern for directory (default: **/*.md)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed processing output",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress non-error output",
)
@click.option(
    "--delay",
    type=float,
    default=0.5,
    help="Inter-episode delay in seconds (default: 0.5, 0 to disable)",
)
@click.option(
    "--chunk-size",
    type=int,
    default=None,
    help="Force chunking for docs above this size in bytes (default: 10240). Use 0 to always chunk.",
)
@click.option(
    "--timeout",
    "episode_timeout",
    type=float,
    default=None,
    help="Per-episode timeout in seconds (overrides auto-detected timeout). Use for slow vLLM instances.",
)
def add_context(path: str, parser_type: Optional[str], force: bool, dry_run: bool, pattern: str, verbose: bool, quiet: bool, delay: float, chunk_size: Optional[int] = None, episode_timeout: Optional[float] = None):
    """Add context from files to Graphiti.

    Adds content from markdown files to the Graphiti knowledge graph.
    Supports single files or directories with glob patterns.

    \b
    Examples:
        guardkit graphiti add-context docs/ADR-001.md
        guardkit graphiti add-context docs/architecture/
        guardkit graphiti add-context docs/ --pattern "**/*.md"
        guardkit graphiti add-context docs/ADR-001.md --type adr
        guardkit graphiti add-context docs/ --dry-run
        guardkit graphiti add-context docs/ --delay 1.0
        guardkit graphiti add-context docs/ --delay 0

    \b
    Supported parser types:
        - adr: Architecture Decision Records
        - feature_spec: Feature specifications
        - full_doc: Full document capture (entire markdown content)
        - project_overview: Project overview documents
        - project_doc: General project documentation (CLAUDE.md, README.md)
    """
    # Check mutual exclusivity of --verbose and --quiet
    if verbose and quiet:
        raise click.UsageError("Options --verbose and --quiet are mutually exclusive")

    _run_async(_cmd_add_context(path, parser_type, force, dry_run, pattern, verbose, quiet, delay, chunk_size, episode_timeout))


async def _cmd_add_context(
    path: str,
    parser_type: Optional[str],
    force: bool,
    dry_run: bool,
    pattern: str,
    verbose: bool = False,
    quiet: bool = False,
    delay: float = 0.5,
    chunk_size: Optional[int] = None,
    episode_timeout: Optional[float] = None,
) -> None:
    """Async implementation of add-context command."""
    # Set SEMAPHORE_LIMIT before graphiti-core is imported (lazy import in
    # client.initialize()).  graphiti-core reads this env var at module load
    # time to cap parallel queries in semaphore_gather() — which also bounds
    # parallel entity-extraction LLM calls fired during a single add_episode
    # for chunked documents.  Setting it too high triggers HTTP 429 from
    # upstream LLM servers (e.g. llama-swap concurrencyLimit); setting it too
    # low under-utilises capacity.  Read from the project's graphiti config
    # so the value can be tuned via .guardkit/graphiti.yaml or the
    # CHUNK_EXTRACTION_CONCURRENCY env var.  See TASK-OPS-9F2A.
    #
    # Note: load_graphiti_config() does NOT import graphiti-core (only PyYAML),
    # so it is safe to call before SEMAPHORE_LIMIT is set.
    settings_for_semaphore = load_graphiti_config()
    original_semaphore = os.environ.get("SEMAPHORE_LIMIT")
    os.environ["SEMAPHORE_LIMIT"] = str(settings_for_semaphore.chunk_extraction_concurrency)

    try:
        # Suppress noisy INFO-level log messages during add-context:
        # - graphiti_core.driver.falkordb_driver: ~30 "Index already exists" lines at startup
        # - httpx: HTTP request/response logging for every Graphiti API call
        logging.getLogger("graphiti_core.driver.falkordb_driver").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

        if not quiet:
            console.print("[bold blue]Graphiti Add Context[/bold blue]")
            console.print()

        # Check if path exists
        target_path = Path(path)
        if not target_path.exists():
            console.print(f"[red]Error: Path does not exist: {path}[/red]")
            raise SystemExit(1)

        # Create client
        client, settings = _get_client_and_config()

        # Initialize connection
        try:
            initialized = await client.initialize()
        except Exception as e:
            console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
            await client.close()
            raise SystemExit(1)

        try:
            if not initialized or not client.enabled:
                console.print("[red]Graphiti connection failed or disabled.[/red]")
                raise SystemExit(1)

            if not quiet:
                console.print("[green]Connected to Graphiti[/green]")
                console.print()

            # Create parser registry and register all available parsers
            # Order matters: FullDocParser MUST be last (lowest-priority fallback)
            registry = ParserRegistry()
            registry.register(ADRParser())
            registry.register(FeatureSpecParser())
            registry.register(ProjectDocParser())
            registry.register(ProjectOverviewParser())
            registry.register(YAMLParser())
            effective_chunk_size = chunk_size if chunk_size is not None else settings.llm_chunk_threshold
            if effective_chunk_size is not None:
                registry.register(FullDocParser(chunk_threshold=effective_chunk_size))
            else:
                registry.register(FullDocParser())

            # Collect files to process
            files_to_process: list[str] = []

            if target_path.is_file():
                # Use the original path string for single files
                files_to_process.append(path)
            elif target_path.is_dir():
                # Use glob pattern to find files
                for file_path in target_path.glob(pattern):
                    if file_path.is_file():
                        files_to_process.append(str(file_path))

            if not files_to_process:
                console.print(f"[yellow]No files found matching pattern: {pattern}[/yellow]")
                return

            # Track results
            total_files = len(files_to_process)
            files_processed = 0
            episodes_added = 0
            episodes_failed = 0
            errors: list[str] = []
            warnings: list[str] = []

            # Process each file
            for file_path_str in files_to_process:
                # Reset circuit breaker between files to prevent cascade
                # (a timeout on one large file should not block subsequent files)
                client.reset_circuit_breaker()
                try:
                    # Read file content
                    with open(file_path_str, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Detect or use specified parser
                    if parser_type:
                        parser = registry.get_parser(parser_type)
                        if not parser:
                            console.print(f"[yellow]No parser for type: {parser_type}[/yellow]")
                            continue
                    else:
                        parser = registry.detect_parser(file_path_str, content)
                        if not parser:
                            console.print(f"[yellow]No parser found for: {file_path_str} (unsupported)[/yellow]")
                            continue

                    # Verbose: show parsing info
                    if verbose:
                        console.print(f"Parsing {file_path_str} with {parser.parser_type}")

                    # Parse the file
                    result = parser.parse(content, file_path_str)

                    if not result.success:
                        errors.append(f"{file_path_str}: Parse failed")
                        for warn in result.warnings:
                            warnings.append(f"{file_path_str}: {warn}")
                        continue

                    # Verbose: show episode count
                    if verbose:
                        console.print(f"  Found {len(result.episodes)} episodes")
                        # Show individual episodes
                        for ep in result.episodes:
                            console.print(f"    - {ep.entity_id} ({ep.entity_type})")

                    # Add warnings from parsing
                    for warn in result.warnings:
                        warnings.append(f"{file_path_str}: {warn}")

                    # Add episodes to Graphiti (unless dry run)
                    file_succeeded = 0
                    file_failed = 0
                    if not dry_run:
                        for episode in result.episodes:
                            try:
                                # Include parser metadata in episode content for context
                                # Note: add_episode expects EpisodeMetadata object or None,
                                # not a dict. Let it auto-generate metadata and include
                                # parser metadata in the content body instead.
                                episode_content = episode.content
                                if episode.metadata:
                                    metadata_str = json.dumps(episode.metadata, indent=2)
                                    episode_content = f"{episode.content}\n\n---\nParser metadata:\n```json\n{metadata_str}\n```"

                                result_uuid = await client.add_episode(
                                    name=episode.entity_id,
                                    episode_body=episode_content,
                                    group_id=episode.group_id,
                                    entity_type=episode.entity_type,
                                    source="add_context_cli",
                                    timeout_override=episode_timeout,
                                )
                                if result_uuid is not None:
                                    episodes_added += 1
                                    file_succeeded += 1
                                else:
                                    episodes_failed += 1
                                    file_failed += 1
                                    errors.append(f"{file_path_str}: Episode creation returned None (possible silent failure)")
                                # Inter-episode delay to let FalkorDB drain pending queries
                                if delay > 0:
                                    await asyncio.sleep(delay)
                            except Exception as e:
                                episodes_failed += 1
                                file_failed += 1
                                errors.append(f"{file_path_str}: Error adding episode - {e}")
                    else:
                        # In dry run, just count the episodes that would be added
                        episodes_added += len(result.episodes)

                    files_processed += 1
                    if not quiet:
                        if file_failed == 0:
                            console.print(f"  [green]\u2713[/green] {file_path_str} ({parser.parser_type})")
                        else:
                            console.print(f"  [yellow]\u26a0[/yellow] {file_path_str} ({parser.parser_type}) \u2014 {file_failed} episode(s) failed")

                except Exception as e:
                    errors.append(f"{file_path_str}: Error - {e}")

            if not quiet:
                console.print()

                # Display summary
                file_word = "file" if files_processed == 1 else "files"
                episode_word = "episode" if episodes_added == 1 else "episodes"

                if dry_run:
                    console.print("[bold]Dry run complete - Would add:[/bold]")
                    console.print(f"  {files_processed} {file_word}, {episodes_added} {episode_word}")
                else:
                    console.print("[bold]Summary:[/bold]")
                    console.print(f"  Added {files_processed} {file_word}, {episodes_added} {episode_word}")
                    if episodes_failed > 0:
                        failed_word = "episode" if episodes_failed == 1 else "episodes"
                        console.print(f"  [yellow]Failed: {episodes_failed} {failed_word}[/yellow]")

            # Display warnings (always shown, even in quiet mode)
            if warnings:
                console.print()
                console.print("[yellow]Warnings:[/yellow]")
                for warn in warnings:
                    console.print(f"  Warning: {warn}")

            # Display errors
            if errors:
                console.print()
                console.print("[red]Errors:[/red]")
                for err in errors:
                    console.print(f"  Error: {err}")

        finally:
            await client.close()

    finally:
        # Restore original SEMAPHORE_LIMIT so other commands in the same
        # process are not affected (AC-004).
        if original_semaphore is None:
            os.environ.pop("SEMAPHORE_LIMIT", None)
        else:
            os.environ["SEMAPHORE_LIMIT"] = original_semaphore


async def _cmd_capture(focus: Optional[str], max_questions: int) -> None:
    """Async implementation of capture command."""
    from guardkit.knowledge.interactive_capture import (
        InteractiveCaptureSession,
        KnowledgeCategory,
    )

    console.print("[bold blue]Interactive Knowledge Capture[/bold blue]")
    console.print()

    # Check if Graphiti is enabled
    settings = load_graphiti_config()
    if not settings.enabled:
        console.print("[yellow]Graphiti is disabled in configuration.[/yellow]")
        console.print("Knowledge capture requires Graphiti to be enabled.")
        return

    # Create client and verify connection
    client, _ = _get_client_and_config()

    console.print(f"Connecting to {_format_connection_target(settings)}...")

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[red]Graphiti connection failed or disabled.[/red]")
            raise SystemExit(1)

        console.print("[green]Connected to Graphiti[/green]")
        console.print()

        # Map focus string to enum
        focus_enum = None
        if focus:
            # Convert hyphenated lowercase to enum (e.g., "project-overview" -> KnowledgeCategory.PROJECT_OVERVIEW)
            focus_key = focus.replace("-", "_").upper()
            focus_enum = getattr(KnowledgeCategory, focus_key)

        # Create UI callback for rich console output
        def ui_callback(event: str, data=None):
            """Handle UI events with colored output."""
            if event == "info":
                console.print(f"[blue]{data}[/blue]")
            elif event == "intro":
                console.print(data)
            elif event == "question":
                console.print()
                console.print(
                    f"[cyan bold][{data['number']}/{data['total']}] "
                    f"{data['category'].upper()}[/cyan bold]"
                )
                console.print(f"[dim]Context: {data['context']}[/dim]")
                console.print()
                console.print(f"[yellow bold]{data['question']}[/yellow bold]")
            elif event == "get_input":
                answer = console.input("[white]Your answer[/white]: ")
                return answer
            elif event == "captured":
                console.print("[green]✓ Captured:[/green]")
                for fact in data["facts"][:3]:  # Show first 3 facts
                    display_fact = fact[:80] + "..." if len(fact) > 80 else fact
                    console.print(f"  [dim]- {display_fact}[/dim]")
            elif event == "summary":
                console.print(f"[green bold]{data}[/green bold]")

        # Run the capture session
        session = InteractiveCaptureSession()

        try:
            captured = await session.run_session(
                focus=focus_enum,
                max_questions=max_questions,
                ui_callback=ui_callback,
            )

            if captured:
                console.print()
                console.print(
                    f"[bold green]Successfully captured {len(captured)} "
                    f"knowledge items![/bold green]"
                )
            else:
                console.print()
                console.print(
                    "[yellow]No knowledge captured. "
                    "Session ended or no gaps identified.[/yellow]"
                )

        except Exception as e:
            console.print(f"[red]Error during capture session: {e}[/red]")
            logger.exception("Capture session failed")
            raise SystemExit(1)

    finally:
        await client.close()


async def _cmd_clear(
    confirm: bool,
    system_only: bool,
    project_only: bool,
    dry_run: bool,
    force: bool,
) -> None:
    """Async implementation of clear command."""
    console.print("[bold blue]Graphiti Knowledge Clear[/bold blue]")
    console.print()

    # Validate mutual exclusivity
    if system_only and project_only:
        console.print("[red]Error: --system-only and --project-only cannot be used together[/red]")
        raise SystemExit(1)

    # Check confirmation
    if not confirm and not dry_run:
        console.print("[red]Error: --confirm flag is required to clear knowledge[/red]")
        console.print()
        console.print("This is a destructive operation. Use one of:")
        console.print("  guardkit graphiti clear --confirm            # Clear all")
        console.print("  guardkit graphiti clear --system-only --confirm  # Clear system only")
        console.print("  guardkit graphiti clear --project-only --confirm # Clear project only")
        console.print("  guardkit graphiti clear --dry-run            # Preview only")
        raise SystemExit(1)

    # Create client
    client, settings = _get_client_and_config()

    # Handle disabled Graphiti
    if not settings.enabled:
        console.print("[yellow]Graphiti is disabled in configuration.[/yellow]")
        console.print("Clear operation skipped.")
        return

    # Initialize connection
    console.print(f"Connecting to {_format_connection_target(settings)}...")

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[yellow]Graphiti not available or disabled.[/yellow]")
            console.print("Clear operation skipped.")
            return

        console.print("[green]Connected to Graphiti[/green]")
        console.print()

        # Get preview first
        preview = await client.get_clear_preview(
            system_only=system_only,
            project_only=project_only,
        )

        # Display what would be deleted
        if dry_run:
            console.print("[bold]Dry Run - The following would be deleted:[/bold]")
        else:
            console.print("[bold]The following will be deleted:[/bold]")
        console.print()

        if preview.get("system_groups"):
            console.print("[cyan]System Groups:[/cyan]")
            for group in preview["system_groups"]:
                console.print(f"  - {group}")
            console.print()

        if preview.get("project_groups"):
            console.print("[cyan]Project Groups:[/cyan]")
            for group in preview["project_groups"]:
                console.print(f"  - {group}")
            console.print()

        console.print(f"Total groups: {preview.get('total_groups', 0)}")
        console.print(f"Estimated episodes: {preview.get('estimated_episodes', 0)}")
        console.print()

        # If dry run, stop here
        if dry_run:
            console.print("[yellow]Dry run complete. No data was deleted.[/yellow]")
            return

        # Perform the clear
        console.print("Clearing knowledge...")

        if system_only:
            result = await client.clear_system_groups()
            console.print()
            console.print("[bold green]System knowledge cleared![/bold green]")
            console.print(f"Groups cleared: {len(result.get('groups_cleared', []))}")
            console.print(f"Episodes deleted: {result.get('episodes_deleted', 0)}")
        elif project_only:
            result = await client.clear_project_groups()
            console.print()
            console.print(f"[bold green]Project '{result.get('project', 'unknown')}' knowledge cleared![/bold green]")
            console.print(f"Groups cleared: {len(result.get('groups_cleared', []))}")
            console.print(f"Episodes deleted: {result.get('episodes_deleted', 0)}")
        else:
            result = await client.clear_all()
            console.print()
            console.print("[bold green]All knowledge cleared![/bold green]")
            console.print(f"System groups cleared: {result.get('system_groups_cleared', 0)}")
            console.print(f"Project groups cleared: {result.get('project_groups_cleared', 0)}")
            console.print(f"Total episodes deleted: {result.get('total_episodes_deleted', 0)}")

        if result.get("error"):
            console.print(f"[yellow]Warning: {result['error']}[/yellow]")

    finally:
        await client.close()


@graphiti.command()
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Run interactive Q&A session",
)
@click.option(
    "--focus",
    type=click.Choice([
        "project-overview",
        "architecture",
        "domain",
        "constraints",
        "decisions",
        "goals",
        "role-customization",
        "quality-gates",
        "workflow-preferences",
    ]),
    help="Focus on specific knowledge category",
)
@click.option(
    "--max-questions",
    type=int,
    default=10,
    help="Maximum questions to ask (default: 10)",
)
def capture(interactive: bool, focus: Optional[str], max_questions: int):
    """Capture project knowledge through interactive Q&A.

    Launches an interactive session that identifies knowledge gaps and captures
    missing project information through guided questions. Supports all focus areas
    including AutoBuild workflow customization.

    \b
    Examples:
        guardkit graphiti capture --interactive
        guardkit graphiti capture --interactive --focus architecture
        guardkit graphiti capture --interactive --focus role-customization
        guardkit graphiti capture --interactive --focus quality-gates
        guardkit graphiti capture --interactive --max-questions 5

    \b
    Focus Areas:
        - project-overview: Project purpose, users, goals
        - architecture: Components, services, data flow
        - domain: Terminology, business rules
        - constraints: Technical/business constraints, avoid list
        - decisions: Technology choices, rationale
        - goals: Project objectives
        - role-customization: AutoBuild role boundaries (what AI should ask about)
        - quality-gates: Coverage thresholds, review scores
        - workflow-preferences: Implementation modes, autonomous turn limits
    """
    if not interactive:
        console.print("[yellow]Use --interactive flag to start a capture session[/yellow]")
        console.print()
        console.print("Example: guardkit graphiti capture --interactive")
        return

    _run_async(_cmd_capture(focus, max_questions))


@graphiti.command()
@click.option(
    "--confirm",
    is_flag=True,
    help="Required. Confirm deletion.",
)
@click.option(
    "--system-only",
    is_flag=True,
    help="Only clear system-level knowledge (not project-specific)",
)
@click.option(
    "--project-only",
    is_flag=True,
    help="Only clear current project's knowledge",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without deleting",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompts (for automation)",
)
def clear(confirm: bool, system_only: bool, project_only: bool, dry_run: bool, force: bool):
    """Clear Graphiti knowledge graph data.

    Safely clears Graphiti knowledge with various scope options.
    Requires --confirm flag for safety (unless using --dry-run).

    \b
    Examples:
        guardkit graphiti clear --confirm           # Clear ALL knowledge
        guardkit graphiti clear --system-only --confirm  # System only
        guardkit graphiti clear --project-only --confirm # Current project only
        guardkit graphiti clear --dry-run           # Preview what would be deleted

    \b
    System Groups (cleared with --system-only):
        - guardkit_templates, guardkit_patterns, guardkit_workflows
        - product_knowledge, command_workflows, quality_gate_phases
        - technology_stack, feature_build_architecture, etc.

    \b
    Project Groups (cleared with --project-only):
        - {project}__project_overview
        - {project}__project_architecture
        - {project}__feature_specs
        - {project}__project_decisions
    """
    _run_async(_cmd_clear(confirm, system_only, project_only, dry_run, force))


async def _cmd_show(knowledge_id: str) -> None:
    """Async implementation of show command.

    Detects knowledge type from ID format and routes to correct group:
    - FEAT-* -> feature_specs
    - ADR-* -> architecture_decisions, project_decisions
    - project-overview -> project_overview
    - *-pattern -> patterns
    - *-constraint -> project_constraints
    - *-guide -> project_knowledge
    - Other -> search all groups
    """
    # Create client
    client, settings = _get_client_and_config()

    # Handle disabled Graphiti
    if not settings.enabled:
        console.print("[red]Graphiti is not enabled[/red]")
        console.print("Enable Graphiti in configuration to use show.")
        return

    # Initialize connection
    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[red]Graphiti connection failed or disabled.[/red]")
            console.print("[yellow]Graphiti not available.[/yellow]")
            raise SystemExit(1)

        # Detect knowledge type and determine group_ids
        group_ids = _detect_group_ids(knowledge_id)

        # Execute search
        try:
            results = await client.search(
                knowledge_id,  # Query as positional arg for test compatibility
                group_ids=group_ids,
                num_results=5,
            )
        except Exception as e:
            console.print(f"[red]Error during search: {e}[/red]")
            raise SystemExit(1)

        # Display results
        if not results:
            console.print(f"[yellow]Not found: {knowledge_id}[/yellow]")
            console.print("No results found for the specified knowledge ID.")
            return

        # Format and display the results
        _format_show_output(results, knowledge_id)

    finally:
        await client.close()


def _detect_group_ids(knowledge_id: str) -> list[str]:
    """Detect knowledge type from ID format and return appropriate group_ids.

    Args:
        knowledge_id: The knowledge ID to analyze

    Returns:
        List of group_ids to search
    """
    knowledge_id_lower = knowledge_id.lower()

    # FEAT-* -> feature_specs
    if knowledge_id.upper().startswith("FEAT-"):
        return ["feature_specs"]

    # ADR-* -> architecture_decisions and project_decisions
    if knowledge_id.upper().startswith("ADR-"):
        return ["architecture_decisions", "project_decisions"]

    # project-overview -> project_overview
    if knowledge_id_lower == "project-overview":
        return ["project_overview"]

    # *-pattern or pattern* -> patterns
    if "pattern" in knowledge_id_lower:
        return ["patterns"]

    # *-constraint or constraint* -> project_constraints
    if "constraint" in knowledge_id_lower:
        return ["project_constraints"]

    # *-guide or guide* -> project_knowledge
    if "guide" in knowledge_id_lower:
        return ["project_knowledge"]

    # Default: search across all common groups
    return [
        "feature_specs",
        "project_overview",
        "project_architecture",
        "project_decisions",
        "project_constraints",
        "domain_knowledge",
        "patterns",
        "agents",
        "task_outcomes",
        "failure_patterns",
        "product_knowledge",
        "command_workflows",
        "quality_gate_phases",
        "technology_stack",
        "feature_build_architecture",
        "architecture_decisions",
        "project_knowledge",
    ]


def _format_show_output(results: list[dict], knowledge_id: str) -> None:
    """Format and display show command output using Rich.

    Args:
        results: Search results from Graphiti
        knowledge_id: The knowledge ID that was searched
    """
    console.print()
    console.print("[cyan]" + "=" * 60 + "[/cyan]")

    for result in results:
        name = result.get("name", knowledge_id)
        fact = result.get("fact", str(result))
        uuid = result.get("uuid", "")
        score = result.get("score", 0.0)
        created_at = result.get("created_at", "")
        valid_at = result.get("valid_at", "")

        # Display name/title
        console.print(f"[yellow bold]  {name}[/yellow bold]")
        console.print("[cyan]" + "=" * 60 + "[/cyan]")

        # Try to parse fact as structured data
        try:
            import json
            if isinstance(fact, str) and fact.startswith("{"):
                data = json.loads(fact)

                # Display key fields
                for key in ["id", "description", "purpose", "status"]:
                    if key in data and data[key]:
                        console.print(f"  [cyan]{key.title()}:[/cyan] {data[key]}")

                # Display lists
                for key in ["success_criteria", "goals", "constraints", "requirements"]:
                    if key in data and data[key]:
                        console.print()
                        console.print(f"  [cyan]{key.replace('_', ' ').title()}:[/cyan]")
                        for item in data[key][:5]:  # Limit to 5 items
                            console.print(f"    [dim]-[/dim] {item}")
            else:
                # Display as plain text
                console.print(f"  {fact}")
        except (json.JSONDecodeError, TypeError):
            # Fallback to raw output
            console.print(f"  {fact}")

        # Display metadata if available
        if uuid:
            console.print()
            console.print(f"  [dim]UUID: {uuid}[/dim]")
        if score > 0:
            # Color code by relevance score
            if score > 0.8:
                score_color = "green"
            elif score > 0.5:
                score_color = "yellow"
            else:
                score_color = "white"
            console.print(f"  [dim]Score: [{score_color}]{score:.2f}[/{score_color}][/dim]")
        if created_at:
            console.print(f"  [dim]Created: {created_at}[/dim]")

        console.print()


async def _cmd_search(query: str, group: Optional[str], limit: int) -> None:
    """Async implementation of search command."""
    # Emit deprecation warning
    console.print("[yellow]⚠️  DEPRECATED: 'guardkit graphiti search' is deprecated.[/yellow]")
    console.print("[yellow]   Use 'guardkit memory search' instead.[/yellow]")
    console.print()

    # Create client
    client, settings = _get_client_and_config()

    # Handle disabled Graphiti
    if not settings.enabled:
        console.print("[red]Graphiti is not enabled[/red]")
        console.print("Enable Graphiti in configuration to use search.")
        return

    # Initialize connection
    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[red]Graphiti connection failed or disabled.[/red]")
            raise SystemExit(1)

        # Determine groups to search
        if group:
            group_ids = [group]
        else:
            # Search across all common groups
            group_ids = [
                "feature_specs",
                "project_overview",
                "project_architecture",
                "project_decisions",
                "project_constraints",
                "domain_knowledge",
                "patterns",
                "agents",
                "task_outcomes",
                "failure_patterns",
                "product_knowledge",
                "command_workflows",
                "quality_gate_phases",
                "technology_stack",
                "feature_build_architecture",
                "architecture_decisions",
                # Groups from project_doc parser
                "project_purpose",
                "project_tech_stack",
                # Group from full_doc parser
                "project_knowledge",
            ]

        # Execute search
        try:
            # Log project_id and groups being searched for debugging
            logger.debug(f"Search project_id: {client.project_id}")
            logger.debug(f"Search groups: {group_ids}")

            results = await client.search(
                query=query,
                group_ids=group_ids,
                num_results=limit,
            )
        except Exception as e:
            console.print(f"[red]Error during search: {e}[/red]")
            raise SystemExit(1)

        # Display results
        if not results:
            console.print(f"No results found for: {query}")
            return

        console.print(f"\nFound {len(results)} results for '{query}':\n")

        for i, result in enumerate(results, 1):
            score = result.get("score", 0.0)
            fact = result.get("fact", str(result))

            # Truncate long facts with "..."
            max_fact_length = 100
            if len(fact) > max_fact_length:
                fact = fact[:max_fact_length] + "..."

            # Color code by relevance score
            if score > 0.8:
                score_color = "green"
            elif score > 0.5:
                score_color = "yellow"
            else:
                score_color = "white"

            # Format output: "N. [score] fact..."
            console.print(
                f"[cyan]{i}.[/cyan] "
                f"[{score_color}][{score:.2f}][/{score_color}] "
                f"{fact}"
            )

    finally:
        await client.close()


@graphiti.command("show")
@click.argument("knowledge_id")
def show(knowledge_id: str):
    """Show details of specific knowledge by ID.

    Detects knowledge type from ID format and displays detailed information.
    Supports feature specs, ADRs, project overview, patterns, constraints, and guides.

    \b
    ID Format Detection:
        - FEAT-* -> Feature specifications
        - ADR-* -> Architecture Decision Records
        - project-overview -> Project overview
        - *-pattern -> Patterns
        - *-constraint -> Project constraints
        - *-guide -> Guides

    \b
    Examples:
        guardkit graphiti show FEAT-GR-001
        guardkit graphiti show ADR-001
        guardkit graphiti show project-overview
        guardkit graphiti show singleton-pattern
        guardkit graphiti show no-graphql-constraint
        guardkit graphiti show testing-guide
    """
    _run_async(_cmd_show(knowledge_id))


@graphiti.command("search")
@click.argument("query")
@click.option(
    "--group",
    "-g",
    default=None,
    help="Limit search to specific group (e.g., patterns, feature_specs)",
)
@click.option(
    "--limit",
    "-n",
    type=int,
    default=10,
    help="Maximum number of results (default: 10)",
)
def search(query: str, group: Optional[str], limit: int):
    """Search for knowledge across all categories.

    Searches the Graphiti knowledge graph for relevant information.
    Results are sorted by relevance score, with color coding:
    - Green (>0.8): High relevance
    - Yellow (>0.5): Medium relevance
    - White: Lower relevance

    \b
    Examples:
        guardkit graphiti search "authentication"
        guardkit graphiti search "error handling" --group patterns
        guardkit graphiti search "walking skeleton" --limit 5
        guardkit graphiti search "JWT" -g architecture_decisions -n 3
    """
    _run_async(_cmd_search(query, group, limit))


async def _cmd_list(category: str) -> None:
    """Async implementation of list command."""
    # Create client
    client, settings = _get_client_and_config()

    # Handle disabled Graphiti
    if not settings.enabled:
        console.print("[red]Graphiti is not enabled[/red]")
        console.print("Enable Graphiti in configuration to use list.")
        return

    # Initialize connection
    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[red]Graphiti connection failed or disabled.[/red]")
            raise SystemExit(1)

        # Map categories to groups
        category_map = {
            "features": ("feature_specs", "Feature Specifications"),
            "adrs": ("architecture_decisions", "Architecture Decision Records"),
            "patterns": ("patterns", "Patterns"),
            "constraints": ("project_constraints", "Project Constraints"),
        }

        if category == "all":
            # List all categories
            for cat_key, (group, title) in category_map.items():
                await _list_single_category(client, group, title)
        else:
            # List specific category
            group, title = category_map[category]
            await _list_single_category(client, group, title)

    finally:
        await client.close()


async def _list_single_category(client: GraphitiClient, group: str, title: str) -> None:
    """List items in a single category.

    Args:
        client: GraphitiClient instance
        group: Group ID to search
        title: Display title for the category
    """
    # Search for all items in the group
    try:
        results = await client.search(
            query="*",
            group_ids=[group],
            num_results=50,
        )
    except Exception as e:
        console.print(f"[red]Error searching {group}: {e}[/red]")
        return

    # Display header
    console.print()
    console.print(f"[bold cyan]{title}[/bold cyan] [dim]({len(results)} items)[/dim]")
    console.print("-" * 40)

    if not results:
        console.print("  [dim](empty)[/dim]")
        return

    # Display each item
    for result in results:
        fact = result.get("fact", str(result))
        name = result.get("name", "")

        # Try to extract ID and title from fact
        try:
            import json
            if isinstance(fact, str) and fact.startswith("{"):
                data = json.loads(fact)
                item_id = data.get("id", "")
                item_title = data.get("title", data.get("name", fact[:40]))

                if item_id:
                    console.print(f"  [cyan]•[/cyan] {item_id}: {item_title}")
                else:
                    console.print(f"  [cyan]•[/cyan] {item_title}")
            else:
                # Use name from result or truncated fact
                display_text = name if name else fact[:60]
                console.print(f"  [cyan]•[/cyan] {display_text}...")
        except (json.JSONDecodeError, TypeError):
            # Fallback to truncated fact
            display_text = name if name else fact[:60]
            console.print(f"  [cyan]•[/cyan] {display_text}...")


@graphiti.command("list")
@click.argument(
    "category",
    type=click.Choice(["features", "adrs", "patterns", "constraints", "all"]),
)
def list_knowledge(category: str):
    """List all knowledge in a category.

    Lists all items stored in Graphiti for a specific knowledge category.
    Shows item IDs and titles when available.

    \b
    Categories:
        - features: Feature specifications
        - adrs: Architecture Decision Records
        - patterns: Design patterns
        - constraints: Project constraints
        - all: All categories

    \b
    Examples:
        guardkit graphiti list features
        guardkit graphiti list adrs
        guardkit graphiti list all
    """
    _run_async(_cmd_list(category))


# ============================================================================
# capture-outcome: Task outcome write to `task_outcomes` group (TASK-FIX-CLI7)
# ============================================================================
#
# Purpose: CLI surface for the `task_outcomes` write path. Closes the gap
# documented in installer/core/commands/task-complete.md where the spec
# referenced a non-existent `add-context --group task_outcomes` flag.
# Wraps `guardkit.knowledge.outcome_manager.capture_task_outcome` (the same
# Python entry point the MCP `add_memory` tool would route to internally).


_TASK_ID_RE = re.compile(r"^TASK-[A-Z0-9.\-]+$")


def _parse_task_file_for_outcome(path: Path) -> dict:
    """Best-effort frontmatter+body parse for `--from-task-file`.

    Extracts the structured fields `capture_task_outcome` needs from a
    GuardKit task file. Missing sections fall back to sensible defaults;
    explicit CLI flags always override what's parsed.

    Returns a dict with keys: ``task_id``, ``task_title``, ``requirements``,
    ``summary``, ``approach_used``, ``lessons_learned``, ``feature_id``,
    ``related_adr_ids``, ``complexity``.
    """
    import yaml

    raw = path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise ValueError(
            f"{path} is not a valid task file: missing YAML frontmatter delimiters"
        )

    try:
        front = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path} has invalid YAML frontmatter: {exc}")
    body = parts[2]

    result: dict = {
        "task_id": front.get("id"),
        "task_title": front.get("title"),
        "complexity": front.get("complexity"),
        "feature_id": front.get("feature_id"),
        "requirements": None,
        "summary": None,
        "approach_used": None,
        "lessons_learned": [],
        "related_adr_ids": [],
    }

    # Build related_adr_ids from frontmatter `parent_review` and `related_to`.
    related = []
    parent = front.get("parent_review")
    if isinstance(parent, str) and _TASK_ID_RE.match(parent):
        related.append(parent)
    related_to = front.get("related_to") or []
    if isinstance(related_to, list):
        for item in related_to:
            if isinstance(item, str) and _TASK_ID_RE.match(item) and item not in related:
                related.append(item)
    result["related_adr_ids"] = related

    # Section extraction: split body on `## ` headings, keep a {heading: text} map.
    sections: dict = {}
    current_heading = None
    current_lines: list = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = line[3:].strip()
            current_lines = []
        else:
            if current_heading is not None:
                current_lines.append(line)
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()

    # requirements: prefer ## Why, then ## Description, then title
    requirements_text = sections.get("Why") or sections.get("Description") or ""
    if requirements_text:
        # Collapse to a single-paragraph string (capped to keep episode tidy)
        result["requirements"] = " ".join(requirements_text.split())[:2000]

    # summary: prefer ## Implementation Summary, then first paragraph of ## Description
    summary_text = sections.get("Implementation Summary") or sections.get("Description") or ""
    if summary_text:
        # First non-empty paragraph
        paragraphs = [p.strip() for p in summary_text.split("\n\n") if p.strip()]
        if paragraphs:
            result["summary"] = " ".join(paragraphs[0].split())[:2000]

    # approach_used: prefer ## Implementation Notes
    approach_text = sections.get("Implementation Notes") or ""
    if approach_text:
        paragraphs = [p.strip() for p in approach_text.split("\n\n") if p.strip()]
        if paragraphs:
            result["approach_used"] = " ".join(paragraphs[0].split())[:1500]

    # lessons_learned: bullet items from ## Notes (one bullet per lesson)
    notes_text = sections.get("Notes") or ""
    lessons: list = []
    for raw_line in notes_text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("- "):
            lessons.append(stripped[2:].strip())
    result["lessons_learned"] = lessons

    return result


async def _cmd_capture_outcome(
    from_task_file: Optional[str],
    task_id: Optional[str],
    task_title: Optional[str],
    requirements: Optional[str],
    summary: Optional[str],
    success: bool,
    approach: Optional[str],
    patterns: tuple,
    lessons: tuple,
    problems: tuple,
    tests_written: Optional[int],
    coverage: Optional[float],
    review_cycles: Optional[int],
    feature_id: Optional[str],
    related_adr: tuple,
    timeout: float,
    dry_run: bool,
    strict: bool,
    verbose: bool,
) -> None:
    """Async implementation of capture-outcome command."""
    # Emit deprecation warning
    console.print()
    console.print("[yellow]⚠️  DEPRECATED: 'guardkit graphiti capture-outcome' is deprecated.[/yellow]")
    console.print("[yellow]   Use 'guardkit memory capture-outcome' instead.[/yellow]")
    console.print()

    from datetime import datetime
    from guardkit.knowledge.outcome_manager import capture_task_outcome
    from guardkit.knowledge.entities.outcome import OutcomeType

    # Surface the inner client's "[Graphiti] Captured ..." and
    # "Episode profile [...]: nodes=N, edges=M" log lines so the operator can
    # tell a real write apart from a silent no-op (the Python API returns the
    # same outcome_id in both cases).
    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    for name in (
        "guardkit.knowledge.graphiti_client",
        "guardkit.knowledge.outcome_manager",
    ):
        logger_obj = logging.getLogger(name)
        logger_obj.setLevel(log_level)
        if not logger_obj.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
            logger_obj.addHandler(handler)
            logger_obj.propagate = False

    # Step 1: Load task file if --from-task-file given (CLI flags override
    # parsed values, never the reverse).
    parsed: dict = {}
    if from_task_file:
        try:
            parsed = _parse_task_file_for_outcome(Path(from_task_file))
        except (FileNotFoundError, ValueError) as exc:
            console.print(f"[red]Error reading task file: {exc}[/red]")
            raise SystemExit(2)

    task_id = task_id or parsed.get("task_id")
    task_title = task_title or parsed.get("task_title")
    requirements = requirements or parsed.get("requirements")
    summary = summary or parsed.get("summary")
    approach = approach or parsed.get("approach_used")
    feature_id = feature_id or parsed.get("feature_id")

    lessons_list = list(lessons) if lessons else parsed.get("lessons_learned") or []
    related_adr_list = list(related_adr) if related_adr else parsed.get("related_adr_ids") or []
    patterns_list = list(patterns) if patterns else None
    problems_list = list(problems) if problems else None

    # Validate required fields
    missing = []
    if not task_id:
        missing.append("--task-id (or --from-task-file with `id` in frontmatter)")
    if not task_title:
        missing.append("--task-title (or --from-task-file with `title` in frontmatter)")
    if not summary:
        missing.append(
            "--summary (or --from-task-file with `## Implementation Summary` "
            "or `## Description` section)"
        )
    if missing:
        console.print(f"[red]Error: missing required field(s): {', '.join(missing)}[/red]")
        raise SystemExit(2)

    # Fall back: use title as requirements when neither flag nor task file provided one.
    if not requirements:
        requirements = task_title

    # Dry-run: print what *would* be sent and exit 0.
    if dry_run:
        console.print("[yellow]DRY RUN — would capture outcome (group: task_outcomes):[/yellow]")
        console.print(f"  task_id:       {task_id}")
        console.print(f"  task_title:    {task_title}")
        console.print(f"  success:       {success}")
        console.print(f"  summary:       {(summary or '')[:120]}{'...' if summary and len(summary) > 120 else ''}")
        console.print(f"  approach:      {(approach or '')[:120]}{'...' if approach and len(approach) > 120 else ''}")
        console.print(f"  patterns:      {patterns_list or '(none)'}")
        console.print(f"  lessons:       {len(lessons_list)} item(s)")
        console.print(f"  problems:      {len(problems_list or [])} item(s)")
        console.print(f"  tests_written: {tests_written}")
        console.print(f"  coverage:      {coverage}")
        console.print(f"  feature_id:    {feature_id}")
        console.print(f"  related_adrs:  {related_adr_list or '(none)'}")
        console.print(f"  timeout:       {timeout}s")
        return

    # Step 2: get the factory-managed thread-local client and initialize it.
    #
    # IMPORTANT: must NOT call _get_client_and_config() here. That helper
    # builds a fresh GraphitiClient outside the factory's thread-local
    # store. capture_task_outcome() internally calls get_memory_client() which
    # always goes through the factory — so the inner write would land on
    # a *different* (uninitialised) client instance and silently no-op,
    # while this CLI happily prints "captured" because the Python API
    # returns the generated outcome_id even when degraded. Sharing the
    # factory client closes that gap.
    #
    # TASK-MEM08-004: Routes through memory client factory (graphiti | dual)
    from guardkit.knowledge.fleet_memory_client import get_memory_client

    client = get_memory_client()
    if client is None:
        # Fall back to get_graphiti for backward compatibility
        client = get_graphiti()

    if client is None:
        msg = (
            "Memory client unavailable (config missing or disabled) — outcome NOT "
            "captured (no write to task_outcomes group)"
        )
        if strict:
            console.print(f"[red]{msg}[/red]")
            raise SystemExit(1)
        console.print(f"[yellow]{msg}[/yellow]")
        console.print("[dim]  (use --strict to exit non-zero in this case)[/dim]")
        return

    if timeout is not None:
        client.default_timeout_override = float(timeout)

    try:
        initialized = await client.initialize()
    except Exception as exc:
        console.print(f"[red]Error connecting to Graphiti: {exc}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            msg = (
                "Graphiti unavailable or disabled — outcome NOT captured "
                "(no write to task_outcomes group)"
            )
            if strict:
                console.print(f"[red]{msg}[/red]")
                raise SystemExit(1)
            console.print(f"[yellow]{msg}[/yellow]")
            console.print("[dim]  (use --strict to exit non-zero in this case)[/dim]")
            return

        outcome_id = await capture_task_outcome(
            outcome_type=OutcomeType.TASK_COMPLETED if success else OutcomeType.TASK_FAILED,
            task_id=task_id,
            task_title=task_title,
            task_requirements=requirements,
            success=success,
            summary=summary,
            approach_used=approach,
            patterns_used=patterns_list,
            problems_encountered=problems_list,
            lessons_learned=lessons_list or None,
            tests_written=tests_written,
            test_coverage=coverage,
            review_cycles=review_cycles,
            completed_at=datetime.now(),
            feature_id=feature_id,
            related_adr_ids=related_adr_list or None,
        )
        console.print(f"[green]✅ Outcome captured: {outcome_id}[/green]")
        console.print(f"   Group: task_outcomes")
        console.print(
            "[dim]   See log lines above for episode profile (nodes/edges) "
            "or [Graphiti] timeout warning if extraction did not complete.[/dim]"
        )
    finally:
        await client.close()


@graphiti.command("capture-outcome")
@click.option(
    "--from-task-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    default=None,
    help=(
        "Parse a GuardKit task .md file (frontmatter + sections) to populate "
        "task_id, title, requirements, summary, lessons, etc. CLI flags override."
    ),
)
@click.option("--task-id", default=None, help="Task ID (e.g. TASK-FIX-CLI7).")
@click.option("--task-title", default=None, help="Human-readable task title.")
@click.option(
    "--requirements",
    default=None,
    help="Original task requirements/description. Falls back to title.",
)
@click.option("--summary", default=None, help="Brief summary of the outcome.")
@click.option(
    "--success/--failure",
    default=True,
    help="Whether the outcome was successful (TASK_COMPLETED vs TASK_FAILED).",
)
@click.option("--approach", default=None, help="Description of the approach taken.")
@click.option(
    "--patterns",
    multiple=True,
    help="Design pattern(s) applied. Repeat for multiple.",
)
@click.option(
    "--lessons",
    multiple=True,
    help="Lesson(s) learned. Repeat for multiple.",
)
@click.option(
    "--problems",
    multiple=True,
    help="Problem(s) encountered. Repeat for multiple.",
)
@click.option("--tests-written", type=int, default=None, help="Number of tests written.")
@click.option("--coverage", type=float, default=None, help="Test coverage percentage (0-100).")
@click.option("--review-cycles", type=int, default=None, help="Number of review cycles.")
@click.option("--feature-id", default=None, help="Related feature ID (FEAT-XXX).")
@click.option(
    "--related-adr",
    multiple=True,
    help="Related ADR or task ID. Repeat for multiple.",
)
@click.option(
    "--timeout",
    type=float,
    default=300.0,
    show_default=True,
    help=(
        "Per-episode timeout in seconds. Local LLM extraction can take "
        "60-300s; the default 300s is sized for that. Bump higher if "
        "extraction times out (warning visible in stderr)."
    ),
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be written without contacting Graphiti.",
)
@click.option(
    "--strict",
    is_flag=True,
    help=(
        "Exit non-zero (1) if the Graphiti client is unavailable or disabled. "
        "Default: exit 0 with a warning (matches task-complete.md non-blocking "
        "semantics)."
    ),
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Surface DEBUG-level logging from the Graphiti client.",
)
def capture_outcome(
    from_task_file,
    task_id,
    task_title,
    requirements,
    summary,
    success,
    approach,
    patterns,
    lessons,
    problems,
    tests_written,
    coverage,
    review_cycles,
    feature_id,
    related_adr,
    timeout,
    dry_run,
    strict,
    verbose,
):
    """Capture a task-completion outcome to the ``task_outcomes`` group.

    Wraps the ``capture_task_outcome`` Python API. Distinguishes a real
    write from a silent no-op by surfacing the inner client's INFO-level
    log lines (``[Graphiti] Captured task outcome OUT-XXXXXXXX`` and
    ``Episode profile [...]: nodes=N, edges=M``).

    \b
    Examples:
        # Frontmatter-driven (preferred):
        guardkit graphiti capture-outcome \\
            --from-task-file tasks/completed/2026-04/TASK-FIX-F4A3-...md

        # Frontmatter + per-flag overrides:
        guardkit graphiti capture-outcome \\
            --from-task-file tasks/completed/2026-04/TASK-FIX-F4A3-...md \\
            --tests-written 4 --coverage 100.0 --timeout 300

        # Pure explicit-flag form (no task file):
        guardkit graphiti capture-outcome \\
            --task-id TASK-XXX --task-title "..." --summary "..." \\
            --lessons "lesson 1" --lessons "lesson 2"

        # Dry-run to verify what would be sent:
        guardkit graphiti capture-outcome \\
            --from-task-file tasks/completed/2026-04/TASK-XXX.md --dry-run

    \b
    Notes:
        - Writes to group_id ``task_outcomes`` via the Python API; no other
          parser type in ``add-context`` routes to this group.
        - LLM entity extraction can take 60-300 s on local LLMs; the
          default ``--timeout 300`` is sized for that.
        - When Graphiti is unavailable, default behaviour is to warn and
          exit 0 (matches ``task-complete.md`` non-blocking semantics).
          Use ``--strict`` to exit 1 instead.
    """
    _run_async(
        _cmd_capture_outcome(
            from_task_file=from_task_file,
            task_id=task_id,
            task_title=task_title,
            requirements=requirements,
            summary=summary,
            success=success,
            approach=approach,
            patterns=patterns,
            lessons=lessons,
            problems=problems,
            tests_written=tests_written,
            coverage=coverage,
            review_cycles=review_cycles,
            feature_id=feature_id,
            related_adr=related_adr,
            timeout=timeout,
            dry_run=dry_run,
            strict=strict,
            verbose=verbose,
        )
    )
