"""
Output formatting utilities for Graphiti query commands.

This module provides shared formatting utilities for the Graphiti CLI commands
(show and search). It handles structured data display, color coding by relevance,
and text truncation for long content.
"""

import json
from typing import Any, Optional

from rich.console import Console

console = Console()


def _format_detail(result: dict[str, Any], knowledge_type: str = "default") -> None:
    """Format detailed output for a single search result.

    Args:
        result: Search result dictionary from Graphiti
        knowledge_type: Type of knowledge for specialized formatting
                       (e.g., 'feature', 'adr', 'pattern', 'default')
    """
    name = result.get("name", "Unknown")
    fact = result.get("fact", str(result))
    uuid = result.get("uuid", "")
    score = result.get("score", 0.0)
    created_at = result.get("created_at", "")
    valid_at = result.get("valid_at", "")

    # Display name/title
    console.print(f"[yellow bold]  {name}[/yellow bold]")
    console.print("[cyan]" + "=" * 60 + "[/cyan]")

    # Try to parse fact as structured JSON data
    try:
        if isinstance(fact, str) and fact.startswith("{"):
            data = json.loads(fact)
            _display_structured_fact(data, knowledge_type)
        else:
            # Display as plain text
            console.print(f"  {fact}")
    except (json.JSONDecodeError, TypeError):
        # Fallback to raw output
        console.print(f"  {fact}")

    # Display metadata
    _display_metadata(uuid, score, created_at, valid_at)

    console.print()


def _display_structured_fact(data: dict[str, Any], knowledge_type: str) -> None:
    """Display structured fact data with appropriate formatting.

    Args:
        data: Parsed JSON fact data
        knowledge_type: Type of knowledge for specialized formatting
    """
    # Display key fields based on knowledge type
    if knowledge_type == "feature":
        _display_feature_fields(data)
    elif knowledge_type == "adr":
        _display_adr_fields(data)
    elif knowledge_type == "pattern":
        _display_pattern_fields(data)
    else:
        _display_default_fields(data)


def _display_feature_fields(data: dict[str, Any]) -> None:
    """Display fields specific to feature specifications."""
    for key in ["id", "title", "description", "status", "priority"]:
        if key in data and data[key]:
            console.print(f"  [cyan]{key.title()}:[/cyan] {data[key]}")

    # Display lists
    for key in ["success_criteria", "requirements", "dependencies"]:
        if key in data and data[key]:
            console.print()
            console.print(f"  [cyan]{key.replace('_', ' ').title()}:[/cyan]")
            for item in data[key][:5]:  # Limit to 5 items
                truncated = _truncate_text(str(item), 80)
                console.print(f"    [dim]-[/dim] {truncated}")


def _display_adr_fields(data: dict[str, Any]) -> None:
    """Display fields specific to Architecture Decision Records."""
    for key in ["id", "title", "status", "context", "decision"]:
        if key in data and data[key]:
            value = _truncate_text(str(data[key]), 100)
            console.print(f"  [cyan]{key.title()}:[/cyan] {value}")

    # Display consequences
    if "consequences" in data and data["consequences"]:
        console.print()
        console.print(f"  [cyan]Consequences:[/cyan]")
        for item in data["consequences"][:5]:
            truncated = _truncate_text(str(item), 80)
            console.print(f"    [dim]-[/dim] {truncated}")


def _display_pattern_fields(data: dict[str, Any]) -> None:
    """Display fields specific to patterns."""
    for key in ["name", "description", "problem", "solution"]:
        if key in data and data[key]:
            value = _truncate_text(str(data[key]), 100)
            console.print(f"  [cyan]{key.title()}:[/cyan] {value}")

    # Display when to use
    if "when_to_use" in data and data["when_to_use"]:
        console.print()
        console.print(f"  [cyan]When To Use:[/cyan]")
        for item in data["when_to_use"][:5]:
            truncated = _truncate_text(str(item), 80)
            console.print(f"    [dim]-[/dim] {truncated}")


def _display_default_fields(data: dict[str, Any]) -> None:
    """Display fields for generic/default knowledge types."""
    for key in ["id", "description", "purpose", "status"]:
        if key in data and data[key]:
            value = _truncate_text(str(data[key]), 100)
            console.print(f"  [cyan]{key.title()}:[/cyan] {value}")

    # Display common list fields
    for key in ["success_criteria", "goals", "constraints", "requirements"]:
        if key in data and data[key]:
            console.print()
            console.print(f"  [cyan]{key.replace('_', ' ').title()}:[/cyan]")
            for item in data[key][:5]:  # Limit to 5 items
                truncated = _truncate_text(str(item), 80)
                console.print(f"    [dim]-[/dim] {truncated}")


def _display_metadata(
    uuid: str,
    score: float,
    created_at: str,
    valid_at: Optional[str] = None
) -> None:
    """Display metadata for a search result.

    Args:
        uuid: Result UUID
        score: Relevance score (0.0-1.0)
        created_at: Creation timestamp
        valid_at: Validity timestamp (optional)
    """
    if uuid:
        console.print()
        console.print(f"  [dim]UUID: {uuid}[/dim]")

    if score > 0:
        # Color code by relevance score
        score_color = _get_score_color(score)
        console.print(f"  [dim]Score: [{score_color}]{score:.2f}[/{score_color}][/dim]")

    if created_at:
        console.print(f"  [dim]Created: {created_at}[/dim]")

    if valid_at:
        console.print(f"  [dim]Valid At: {valid_at}[/dim]")


def _get_score_color(score: float) -> str:
    """Get color for relevance score display.

    Args:
        score: Relevance score (0.0-1.0)

    Returns:
        Color name for Rich console formatting
        - Green for high relevance (>0.8)
        - Yellow for medium relevance (>0.5)
        - White for low relevance (<=0.5)
    """
    if score > 0.8:
        return "green"
    elif score > 0.5:
        return "yellow"
    else:
        return "white"


def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text to maximum length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated text with "..." if longer than max_length
    """
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def format_search_results(results: list[dict[str, Any]], query: str) -> None:
    """Format and display search results.

    Args:
        results: List of search results from Graphiti
        query: Original search query
    """
    if not results:
        console.print(f"[yellow]No results found for: {query}[/yellow]")
        return

    console.print(f"\n[cyan]Found {len(results)} results for '{query}':[/cyan]\n")

    for i, result in enumerate(results, 1):
        score = result.get("score", 0.0)
        fact = result.get("fact", str(result))

        # Truncate long facts
        fact_display = _truncate_text(fact, 100)

        # Color code by relevance score
        score_color = _get_score_color(score)

        # Format output: "N. [score] fact..."
        console.print(
            f"[cyan]{i}.[/cyan] "
            f"[{score_color}][{score:.2f}][/{score_color}] "
            f"{fact_display}"
        )


def format_show_output(results: list[dict[str, Any]], knowledge_id: str) -> None:
    """Format and display show command output.

    Args:
        results: Search results from Graphiti
        knowledge_id: The knowledge ID that was searched
    """
    if not results:
        console.print(f"[yellow]Not found: {knowledge_id}[/yellow]")
        console.print("No results found for the specified knowledge ID.")
        return

    console.print()
    console.print("[cyan]" + "=" * 60 + "[/cyan]")

    # Detect knowledge type from ID
    knowledge_type = _detect_knowledge_type(knowledge_id)

    for result in results:
        _format_detail(result, knowledge_type)


def _detect_knowledge_type(knowledge_id: str) -> str:
    """Detect knowledge type from ID format.

    Args:
        knowledge_id: Knowledge identifier

    Returns:
        Knowledge type string ('feature', 'adr', 'pattern', or 'default')
    """
    knowledge_id_upper = knowledge_id.upper()
    knowledge_id_lower = knowledge_id.lower()

    if knowledge_id_upper.startswith("FEAT-"):
        return "feature"
    elif knowledge_id_upper.startswith("ADR-"):
        return "adr"
    elif "pattern" in knowledge_id_lower:
        return "pattern"
    else:
        return "default"


# Box-drawing characters for status display
BOX_CHARS = {
    "top_left": "┌",
    "top_right": "┐",
    "bottom_left": "└",
    "bottom_right": "┘",
    "horizontal": "─",
    "vertical": "│",
    "t_down": "┬",
    "t_up": "┴",
    "t_right": "├",
    "t_left": "┤",
    "cross": "┼",
}


def format_status_box(title: str, items: list[tuple[str, str]], width: int = 60) -> None:
    """Format a status box with title and key-value pairs.

    Args:
        title: Box title
        items: List of (key, value) tuples to display
        width: Box width in characters
    """
    # Top border with title
    console.print(
        f"{BOX_CHARS['top_left']}{BOX_CHARS['horizontal'] * 2} "
        f"[bold]{title}[/bold] "
        f"{BOX_CHARS['horizontal'] * (width - len(title) - 6)}"
        f"{BOX_CHARS['top_right']}"
    )

    # Items
    for key, value in items:
        # Truncate value if too long
        max_value_len = width - len(key) - 8
        value_display = _truncate_text(str(value), max_value_len)

        console.print(
            f"{BOX_CHARS['vertical']} [cyan]{key}:[/cyan] {value_display}"
        )

    # Bottom border
    console.print(
        f"{BOX_CHARS['bottom_left']}"
        f"{BOX_CHARS['horizontal'] * (width - 2)}"
        f"{BOX_CHARS['bottom_right']}"
    )
