"""
CLI commands for System Context Read operations.

This module provides CLI commands for reading system architecture context:
- system-overview: Architecture summary
- impact-analysis: Pre-task validation with risk scoring
- context-switch: Multi-project navigation

Example:
    $ guardkit system-overview
    $ guardkit impact-analysis TASK-042
    $ guardkit context-switch requirekit
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)

# Message constants
NO_CONTEXT_MESSAGE = """
======================================================================
NO ARCHITECTURE CONTEXT
======================================================================

No architecture information found for this project.

NEXT STEPS:
  1. Run /system-plan "project description" to capture architecture
  2. Or create docs manually in docs/architecture/

For quick understanding:
  - Read CLAUDE.md for project conventions
======================================================================
"""

GRAPHITI_UNAVAILABLE_MESSAGE = """
======================================================================
ARCHITECTURE CONTEXT UNAVAILABLE
======================================================================

Cannot query Graphiti for architecture information.

ALTERNATIVES:
  - Read docs/architecture/ARCHITECTURE.md directly
  - Check CLAUDE.md for project conventions

To configure Graphiti:
  pip install guardkit-py[graphiti]
======================================================================
"""


def _format_risk_bar(score: int, max_score: int = 5) -> str:
    """Format risk score as Unicode bar.

    Args:
        score: Risk score (1-5)
        max_score: Maximum score for bar

    Returns:
        Formatted risk bar string, e.g., "[███  ] 3/5"
    """
    filled = min(score, max_score)
    empty = max_score - filled
    bar = "█" * filled + " " * empty
    return f"[{bar}] {score}/{max_score}"


def _format_overview_section(overview: Dict[str, Any], section: str, verbose: bool) -> str:
    """Format a single section of the system overview."""
    lines: List[str] = []

    if section in ["all", "system", "stack"]:
        system = overview.get("system", {})
        if system:
            lines.append("")
            lines.append("SYSTEM CONTEXT:")
            if system.get("name"):
                lines.append(f"  Name: {system['name']}")
            if system.get("purpose"):
                lines.append(f"  Purpose: {system['purpose']}")
            if system.get("methodology"):
                lines.append(f"  Methodology: {system['methodology']}")

    if section in ["all", "components"]:
        components = overview.get("components", [])
        if components:
            lines.append("")
            lines.append(f"COMPONENTS ({len(components)}):")
            for comp in components:
                name = comp.get("name", "Unknown")
                desc = comp.get("description", "")
                lines.append(f"  - {name}: {desc}")
                if verbose and comp.get("full_content"):
                    lines.append(f"    {comp['full_content']}")

    if section in ["all", "decisions"]:
        decisions = overview.get("decisions", [])
        if decisions:
            lines.append("")
            lines.append(f"ARCHITECTURE DECISIONS ({len(decisions)}):")
            for dec in decisions:
                adr_id = dec.get("adr_id", "")
                title = dec.get("title", "")
                status = dec.get("status", "")
                lines.append(f"  - {adr_id}: {title} ({status})")

    if section in ["all", "crosscutting", "concerns"]:
        concerns = overview.get("concerns", [])
        if concerns:
            lines.append("")
            lines.append(f"CROSSCUTTING CONCERNS ({len(concerns)}):")
            for concern in concerns:
                name = concern.get("name", "Unknown")
                desc = concern.get("description", "")
                lines.append(f"  - {name}: {desc}")

    return "\n".join(lines)


def _format_overview_display(overview: Dict[str, Any], section: str = "all", verbose: bool = False) -> str:
    """Format system overview for terminal display."""
    status = overview.get("status", "ok")

    if status == "no_context":
        return NO_CONTEXT_MESSAGE.strip()

    lines: List[str] = []
    system_name = overview.get("system", {}).get("name", "Unknown Project")

    lines.append("=" * 70)
    lines.append(f"SYSTEM OVERVIEW: {system_name}")
    lines.append("=" * 70)

    lines.append(_format_overview_section(overview, section, verbose))

    lines.append("")
    lines.append("=" * 70)
    lines.append("NEXT STEPS:")
    lines.append("  - Impact analysis: /impact-analysis TASK-XXX")
    lines.append("  - Plan feature: /feature-plan \"description\"")
    lines.append("=" * 70)

    return "\n".join(lines)


def _format_impact_display(impact: Dict[str, Any], depth: str = "standard") -> str:
    """Format impact analysis for terminal display."""
    status = impact.get("status", "ok")

    if status == "no_context":
        return "No impact data available - no architecture context found."

    lines: List[str] = []
    query = impact.get("query", "Unknown")

    lines.append("=" * 70)
    lines.append(f"IMPACT ANALYSIS: {query}")
    lines.append("=" * 70)

    # Risk assessment
    risk = impact.get("risk", {})
    score = risk.get("score", 1)
    label = risk.get("label", "unknown")
    rationale = risk.get("rationale", "")

    lines.append("")
    lines.append("RISK ASSESSMENT:")
    lines.append(f"  Score: {score}/5 ({label})")
    lines.append(f"  {_format_risk_bar(score)}")
    if rationale:
        lines.append(f"  Rationale: {rationale}")

    # Affected components
    components = impact.get("components", [])
    if components:
        lines.append("")
        lines.append(f"AFFECTED COMPONENTS ({len(components)}):")
        for comp in components:
            name = comp.get("name", "Unknown")
            desc = comp.get("description", "")
            score_val = comp.get("relevance_score", 0)
            lines.append(f"  - {name} ({score_val:.2f})")
            if desc:
                lines.append(f"    {desc}")

    # ADRs (not in quick mode)
    if depth != "quick":
        adrs = impact.get("adrs", [])
        if adrs:
            lines.append("")
            lines.append(f"CONSTRAINING ADRs ({len(adrs)}):")
            for adr in adrs:
                adr_id = adr.get("adr_id", "")
                title = adr.get("title", "")
                conflict = adr.get("conflict", False)
                conflict_str = " [CONFLICT]" if conflict else ""
                lines.append(f"  - {adr_id}: {title}{conflict_str}")

    # BDD scenarios (deep mode or --include-bdd)
    bdd_scenarios = impact.get("bdd_scenarios", [])
    if bdd_scenarios:
        lines.append("")
        lines.append(f"BDD SCENARIOS AT RISK ({len(bdd_scenarios)}):")
        for scenario in bdd_scenarios:
            name = scenario.get("scenario_name", "Unknown")
            location = scenario.get("file_location", "")
            at_risk = scenario.get("at_risk", False)
            risk_str = "[AT RISK]" if at_risk else ""
            lines.append(f"  - {name} {risk_str}")
            if location:
                lines.append(f"    {location}")

    # Implications
    implications = impact.get("implications", [])
    if implications:
        lines.append("")
        lines.append("IMPLICATIONS:")
        for impl in implications:
            lines.append(f"  - {impl}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


def _format_context_switch_display(result: Dict[str, Any], mode: str = "switch") -> str:
    """Format context switch result for terminal display."""
    status = result.get("status", "success")

    if status == "error":
        message = result.get("message", "Unknown error")
        project_id = result.get("project_id", "")
        return f"Error: {message}\nProject: {project_id}"

    lines: List[str] = []
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

    # Architecture (if available)
    architecture = result.get("architecture", [])
    if architecture:
        lines.append("")
        lines.append("ARCHITECTURE:")
        for item in architecture[:3]:
            fact = item.get("fact", "")
            if fact:
                lines.append(f"  - {fact[:80]}...")
    elif mode == "switch":
        lines.append("")
        lines.append("ARCHITECTURE:")
        lines.append("  [Graphiti unavailable - check docs/architecture/ manually]")

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


@click.command("system-overview")
@click.option(
    "--verbose",
    is_flag=True,
    help="Include extended content and full descriptions",
)
@click.option(
    "--section",
    type=click.Choice(["all", "components", "decisions", "crosscutting", "stack"]),
    default="all",
    help="Filter to a specific section",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["display", "json", "markdown"]),
    default="display",
    help="Output format",
)
def system_overview(verbose: bool, section: str, output_format: str):
    """Display architecture summary of the current project.

    Queries Graphiti for stored architecture context and displays
    a concise summary including components, decisions, and cross-cutting concerns.

    Examples:
        guardkit system-overview
        guardkit system-overview --verbose
        guardkit system-overview --section=decisions
        guardkit system-overview --format=json
    """
    from guardkit.planning.system_overview import get_system_overview

    try:
        overview = get_system_overview(verbose=verbose)
    except Exception as e:
        logger.debug(f"Error getting system overview: {e}")
        overview = {"status": "no_context"}

    if output_format == "json":
        console.print(json.dumps(overview, indent=2))
    else:
        output = _format_overview_display(overview, section=section, verbose=verbose)
        console.print(output)


@click.command("impact-analysis")
@click.argument("task_or_topic")
@click.option(
    "--depth",
    type=click.Choice(["quick", "standard", "deep"]),
    default="standard",
    help="Analysis depth: quick (components only), standard (+ ADRs), deep (+ BDD)",
)
@click.option(
    "--include-bdd",
    is_flag=True,
    help="Include BDD scenario impact (auto-enabled in deep mode)",
)
@click.option(
    "--include-tasks",
    is_flag=True,
    help="Include related task search (auto-enabled in deep mode)",
)
def impact_analysis(
    task_or_topic: str,
    depth: str,
    include_bdd: bool,
    include_tasks: bool,
):
    """Analyze architectural impact of a task or topic.

    Evaluates a proposed change against the project's architecture context,
    identifying affected components, ADR constraints, and risk level.

    Arguments:
        TASK_OR_TOPIC: Either a task ID (e.g., TASK-042) or a topic string

    Examples:
        guardkit impact-analysis TASK-042
        guardkit impact-analysis "add user authentication"
        guardkit impact-analysis TASK-042 --depth=deep
    """
    from guardkit.planning.impact_analysis import run_impact_analysis

    # Deep mode auto-enables BDD and tasks
    if depth == "deep":
        include_bdd = True
        include_tasks = True

    try:
        impact = run_impact_analysis(
            task_or_topic=task_or_topic,
            depth=depth,
            include_bdd=include_bdd,
            include_tasks=include_tasks,
        )
    except Exception as e:
        logger.debug(f"Error running impact analysis: {e}")
        impact = {"status": "no_context"}

    output = _format_impact_display(impact, depth=depth)
    console.print(output)


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
    When switching, displays an orientation summary with active tasks
    and architecture overview.

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
                client=None,  # No Graphiti needed for current view
                target_project=current.get("id", ""),
                config=config,
            ))
        except Exception as e:
            logger.debug(f"Error getting current context: {e}")
            result = {
                "status": "success",
                "project_id": current.get("id", "Unknown"),
                "project_path": current.get("path", ""),
                "architecture": [],
                "active_tasks": [],
            }

        output = _format_context_switch_display(result, mode="current")
        console.print(output)
        return

    # Switch mode
    try:
        result = asyncio.run(execute_context_switch(
            client=None,  # Graphiti client - will use get_graphiti() internally
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
