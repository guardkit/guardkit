"""
Graphiti CLI commands for knowledge graph management.

Commands:
- graphiti seed: Seed system context into Graphiti
- graphiti status: Show Graphiti connection and seeding status
- graphiti verify: Run test queries to verify seeded knowledge
- graphiti add-context: Add context from files to Graphiti

Example:
    $ guardkit graphiti seed
    $ guardkit graphiti seed --force
    $ guardkit graphiti status
    $ guardkit graphiti verify
    $ guardkit graphiti add-context docs/architecture/
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig
from guardkit.knowledge.config import load_graphiti_config, GraphitiSettings


def _format_connection_target(settings: GraphitiSettings) -> str:
    """Format the connection target string based on graph store backend."""
    if settings.graph_store == "falkordb":
        return f"FalkorDB at {settings.falkordb_host}:{settings.falkordb_port}"
    return f"Neo4j at {settings.neo4j_uri}"
from guardkit.knowledge.seeding import (
    seed_all_system_context,
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
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        timeout=settings.timeout,
        project_id=settings.project_id,
        graph_store=settings.graph_store,
        falkordb_host=settings.falkordb_host,
        falkordb_port=settings.falkordb_port,
    )
    client = GraphitiClient(config)
    return client, settings


async def _cmd_seed(force: bool) -> None:
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

        # Clear marker if forcing
        if force and is_seeded():
            console.print("Clearing previous seeding marker...")
            clear_seeding_marker()

        # Run seeding
        console.print("Seeding system context...")
        console.print()

        try:
            result = await seed_all_system_context(client, force=force)
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
                "project_overview",
                "project_architecture",
                "failed_approaches",
                "quality_gate_configs",
                "pattern_examples",
            ]
            for cat in categories:
                console.print(f"  [green]\u2713[/green] {cat}")
            console.print()
            console.print("Run 'guardkit graphiti verify' to test queries.")
            console.print()
            console.print("To seed project ADRs:")
            console.print("  guardkit graphiti add-context docs/adr/ --type adr")
        else:
            console.print("[yellow]Seeding completed with warnings.[/yellow]")
    finally:
        await client.close()


async def _cmd_status(verbose: bool = False) -> None:
    """Async implementation of status command.

    Args:
        verbose: Show all groups even if empty
    """
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
def seed(force: bool):
    """Seed system context into Graphiti.

    Seeds comprehensive GuardKit knowledge into the Graphiti knowledge graph.
    This includes product knowledge, command workflows, quality gate phases,
    technology stack information, and more.

    Use --force to re-seed even if seeding has already been completed.
    """
    asyncio.run(_cmd_seed(force))


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
    asyncio.run(_cmd_status(verbose))


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
    asyncio.run(_cmd_verify(verbose))


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
    asyncio.run(_cmd_seed_adrs(force))


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
def add_context(path: str, parser_type: Optional[str], force: bool, dry_run: bool, pattern: str, verbose: bool, quiet: bool, delay: float):
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

    asyncio.run(_cmd_add_context(path, parser_type, force, dry_run, pattern, verbose, quiet, delay))


async def _cmd_add_context(
    path: str,
    parser_type: Optional[str],
    force: bool,
    dry_run: bool,
    pattern: str,
    verbose: bool = False,
    quiet: bool = False,
    delay: float = 0.5,
) -> None:
    """Async implementation of add-context command."""
    # Set SEMAPHORE_LIMIT before graphiti-core is imported (lazy import in
    # client.initialize()).  graphiti-core reads this env var at module load
    # time to cap parallel queries in semaphore_gather().  Save the original
    # value so we can restore it after the command finishes.
    original_semaphore = os.environ.get("SEMAPHORE_LIMIT")
    os.environ["SEMAPHORE_LIMIT"] = "5"

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

    asyncio.run(_cmd_capture(focus, max_questions))


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
    asyncio.run(_cmd_clear(confirm, system_only, project_only, dry_run, force))


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
    asyncio.run(_cmd_show(knowledge_id))


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
    asyncio.run(_cmd_search(query, group, limit))


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
    asyncio.run(_cmd_list(category))
