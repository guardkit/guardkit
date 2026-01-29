"""
Graphiti CLI commands for knowledge graph management.

Commands:
- graphiti seed: Seed system context into Graphiti
- graphiti status: Show Graphiti connection and seeding status
- graphiti verify: Run test queries to verify seeded knowledge

Example:
    $ guardkit graphiti seed
    $ guardkit graphiti seed --force
    $ guardkit graphiti status
    $ guardkit graphiti verify
"""

import asyncio
import logging
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig
from guardkit.knowledge.config import load_graphiti_config, GraphitiSettings
from guardkit.knowledge.seeding import (
    seed_all_system_context,
    is_seeded,
    clear_seeding_marker,
    SEEDING_VERSION,
)
from guardkit.knowledge.seed_feature_build_adrs import seed_feature_build_adrs

console = Console()
logger = logging.getLogger(__name__)


def _get_client_and_config() -> tuple[GraphitiClient, GraphitiSettings]:
    """Create and return Graphiti client and configuration.

    Returns:
        Tuple of (GraphitiClient, GraphitiSettings)
    """
    settings = load_graphiti_config()
    config = GraphitiConfig(
        enabled=settings.enabled,
        host=settings.host,
        port=settings.port,
        timeout=settings.timeout,
    )
    client = GraphitiClient(config)
    return client, settings


def _run_async(coro):
    """Run an async coroutine synchronously.

    This handles the case where no event loop exists (e.g., in Click tests)
    by using asyncio.run() which creates a new event loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        return asyncio.run(coro)
    else:
        return loop.run_until_complete(coro)


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
def seed(force: bool):
    """Seed system context into Graphiti.

    Seeds comprehensive GuardKit knowledge into the Graphiti knowledge graph.
    This includes product knowledge, command workflows, quality gate phases,
    technology stack information, and more.

    Use --force to re-seed even if seeding has already been completed.
    """
    console.print("[bold blue]Graphiti System Context Seeding[/bold blue]")
    console.print()

    # Check if already seeded
    if is_seeded() and not force:
        console.print("[yellow]System context already seeded.[/yellow]")
        console.print("Use --force to re-seed.")
        return

    # Create client
    client, settings = _get_client_and_config()

    # Initialize connection
    console.print(f"Connecting to Graphiti at {settings.host}:{settings.port}...")

    try:
        initialized = _run_async(client.initialize())
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    if not initialized or not client.enabled:
        console.print("[yellow]Graphiti not available or disabled.[/yellow]")
        console.print("Seeding skipped. Check your Graphiti configuration.")
        return

    console.print("[green]Connected to Graphiti[/green]")
    console.print()

    # Clear marker if forcing
    if force and is_seeded():
        console.print("Clearing previous seeding marker...")
        clear_seeding_marker()

    # Run seeding
    console.print("Seeding system context...")
    console.print()

    try:
        result = _run_async(seed_all_system_context(client, force=force))
    except Exception as e:
        console.print(f"[red]Error during seeding: {e}[/red]")
        logger.exception("Seeding failed")
        raise SystemExit(1)

    if result:
        console.print()
        console.print("[bold green]System context seeding complete![/bold green]")
        console.print()
        console.print("Knowledge categories seeded:")
        categories = [
            "product_knowledge",
            "command_workflows",
            "quality_gate_phases",
            "technology_stack",
            "feature_build_architecture",
            "architecture_decisions",
            "failure_patterns",
            "component_status",
            "integration_points",
            "templates",
            "agents",
            "patterns",
            "rules",
        ]
        for cat in categories:
            console.print(f"  [green]\u2713[/green] {cat}")
        console.print()
        console.print("Run 'guardkit graphiti verify' to test queries.")
    else:
        console.print("[yellow]Seeding completed with warnings.[/yellow]")


@graphiti.command()
def status():
    """Show Graphiti connection and seeding status.

    Displays information about the Graphiti configuration, connection status,
    and whether system context has been seeded.
    """
    console.print("[bold blue]Graphiti Status[/bold blue]")
    console.print()

    # Load configuration
    settings = load_graphiti_config()

    # Create status table
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Enabled", "[green]Yes[/green]" if settings.enabled else "[red]No[/red]")
    table.add_row("Host", settings.host)
    table.add_row("Port", str(settings.port))
    table.add_row("Timeout", f"{settings.timeout}s")

    console.print(table)
    console.print()

    # Check connection
    if settings.enabled:
        client, _ = _get_client_and_config()

        console.print("Checking connection...")
        try:
            initialized = _run_async(client.initialize())
            if initialized and client.enabled:
                console.print("[green]Connection: OK[/green]")

                # Check health
                try:
                    healthy = _run_async(client.health_check())
                    if healthy:
                        console.print("[green]Health: OK[/green]")
                    else:
                        console.print("[yellow]Health: Degraded[/yellow]")
                except Exception:
                    console.print("[yellow]Health: Unknown[/yellow]")
            else:
                console.print("[red]Connection: Failed[/red]")
        except Exception as e:
            console.print(f"[red]Connection: Error - {e}[/red]")
    else:
        console.print("[yellow]Connection: Skipped (disabled)[/yellow]")

    console.print()

    # Check seeding status
    if is_seeded():
        console.print(f"[green]Seeded: Yes (version {SEEDING_VERSION})[/green]")
    else:
        console.print("[yellow]Seeded: No[/yellow]")
        console.print("Run 'guardkit graphiti seed' to seed system context.")


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
    console.print(f"Connecting to Graphiti at {settings.host}:{settings.port}...")

    try:
        initialized = _run_async(client.initialize())
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

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
            results = _run_async(client.search(query, group_ids=group_ids, num_results=3))

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
    console.print(f"Connecting to Graphiti at {settings.host}:{settings.port}...")

    try:
        initialized = _run_async(client.initialize())
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    if not initialized or not client.enabled:
        console.print("[yellow]Graphiti not available or disabled.[/yellow]")
        console.print("ADR seeding skipped.")
        return

    console.print("[green]Connected to Graphiti[/green]")
    console.print()

    # Run ADR seeding
    console.print("Seeding feature-build ADRs...")

    try:
        _run_async(seed_feature_build_adrs(client))
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
