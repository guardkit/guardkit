"""System Overview: Transform Graphiti facts into structured context.

This module assembles architecture facts from Graphiti into structured overviews
suitable for Claude Code injection and display. It provides:

1. Entity type inference from fact name/content patterns
2. Fact parsing into structured sections (components, decisions, concerns)
3. Token-budgeted condensation with priority ordering
4. Multiple format outputs (display, markdown, JSON)
5. Graceful degradation (return defaults on error/no data)

All log messages use [Graphiti] prefix for easy filtering.

Public API:
    get_system_overview: Main entry point for assembling architecture overview
    condense_for_injection: Token-budgeted condensation for Claude Code injection
    format_overview_display: Format overview for display (terminal, markdown, JSON)

Example:
    from guardkit.planning.system_overview import (
        get_system_overview,
        condense_for_injection,
        format_overview_display
    )
    from guardkit.planning.graphiti_arch import SystemPlanGraphiti

    sp = SystemPlanGraphiti(client=client, project_id="my-project")

    # Get structured overview
    overview = await get_system_overview(sp, verbose=False)

    # Condense for injection (max 800 tokens)
    condensed = condense_for_injection(overview, max_tokens=800)

    # Format for display
    display = format_overview_display(overview, section="all", format="display")
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from guardkit.planning.graphiti_arch import SystemPlanGraphiti

logger = logging.getLogger(__name__)


async def get_system_overview(
    sp: "SystemPlanGraphiti",
    verbose: bool = False
) -> Dict[str, Any]:
    """Assemble structured overview from Graphiti architecture facts.

    This is the main entry point for retrieving architecture context.
    It calls sp.get_architecture_summary() to get raw facts, then parses
    them into structured sections based on entity type patterns.

    Args:
        sp: SystemPlanGraphiti instance for Graphiti operations
        verbose: If True, include full fact content in parsed items

    Returns:
        Dict with keys:
            - status: "ok" or "no_context"
            - system: Dict with system context (methodology, name, etc.)
            - components: List of parsed component facts
            - decisions: List of parsed ADR facts
            - concerns: List of parsed crosscutting concern facts

        Returns {"status": "no_context"} when:
            - sp._available is False
            - get_architecture_summary() returns None
            - facts list is empty
            - Exception occurs
    """
    # Check if Graphiti is available
    if not sp._available:
        logger.debug("[Graphiti] SystemPlanGraphiti not available")
        return {"status": "no_context"}

    try:
        # Get raw facts from Graphiti
        summary = await sp.get_architecture_summary()

        # Handle no context cases
        if summary is None:
            logger.debug("[Graphiti] No architecture summary available")
            return {"status": "no_context"}

        facts = summary.get("facts", [])
        if not facts:
            logger.debug("[Graphiti] No architecture facts found")
            return {"status": "no_context"}

        # Group facts by entity type
        system_context = {}
        components = []
        decisions = []
        concerns = []

        for fact in facts:
            entity_type = _extract_entity_type(fact)

            if entity_type == "system_context":
                # Parse system context (should be only one)
                system_context = _parse_system_context_fact(fact, verbose)
            elif entity_type == "component":
                components.append(_parse_component_fact(fact, verbose))
            elif entity_type == "architecture_decision":
                decisions.append(_parse_decision_fact(fact, verbose))
            elif entity_type == "crosscutting_concern":
                concerns.append(_parse_concern_fact(fact, verbose))

        logger.info(f"[Graphiti] Assembled overview: {len(components)} components, "
                   f"{len(decisions)} decisions, {len(concerns)} concerns")

        return {
            "status": "ok",
            "system": system_context,
            "components": components,
            "decisions": decisions,
            "concerns": concerns,
        }

    except Exception as e:
        logger.warning(f"[Graphiti] Failed to get system overview: {e}")
        return {"status": "no_context"}


def _extract_entity_type(fact: Dict[str, Any]) -> str:
    """Infer entity type from fact name and content patterns.

    Patterns recognized (case insensitive):
        - "Component:" prefix → "component"
        - "ADR-" prefix → "architecture_decision"
        - "Crosscutting:" prefix or "cross-cutting" keyword → "crosscutting_concern"
        - "System Context" prefix → "system_context"
        - Unknown → "system_context" (fallback)

    Args:
        fact: Fact dict with 'name' and 'fact' keys

    Returns:
        Entity type string
    """
    name = fact.get("name", "").lower()
    content = fact.get("fact", "").lower()

    # Check name patterns first
    if name.startswith("component:"):
        return "component"
    if name.startswith("adr-"):
        return "architecture_decision"
    if name.startswith("crosscutting:"):
        return "crosscutting_concern"
    if name.startswith("system context"):
        return "system_context"

    # Check content patterns
    if "cross-cutting" in content or content.startswith("crosscutting:"):
        return "crosscutting_concern"

    # Fallback
    return "system_context"


def _parse_system_context_fact(fact: Dict[str, Any], verbose: bool) -> Dict[str, Any]:
    """Parse system context fact into structured dict.

    Args:
        fact: Raw fact dict from Graphiti
        verbose: If True, include full_content field

    Returns:
        Dict with system context details (name, methodology, purpose, etc.)
    """
    name = fact.get("name", "")
    content = fact.get("fact", "")

    # Extract name (remove "System Context: " prefix)
    system_name = name
    if ":" in name:
        system_name = name.split(":", 1)[1].strip()

    result = {
        "name": system_name,
    }

    # Extract methodology (look for "Methodology: XXX" pattern)
    methodology_match = re.search(r"methodology:\s*([^.]+)", content, re.IGNORECASE)
    if methodology_match:
        result["methodology"] = methodology_match.group(1).strip()

    # Extract purpose
    purpose_match = re.search(r"purpose:\s*([^.]+)", content, re.IGNORECASE)
    if purpose_match:
        result["purpose"] = purpose_match.group(1).strip()

    # Extract bounded contexts
    contexts_match = re.search(r"bounded contexts?:\s*([^.]+)", content, re.IGNORECASE)
    if contexts_match:
        result["bounded_contexts"] = contexts_match.group(1).strip()

    if verbose:
        result["full_content"] = content

    return result


def _parse_component_fact(fact: Dict[str, Any], verbose: bool) -> Dict[str, Any]:
    """Parse component fact into structured dict.

    Args:
        fact: Raw fact dict from Graphiti
        verbose: If True, include full_content field

    Returns:
        Dict with component details (name, description, etc.)
    """
    name = fact.get("name", "")
    content = fact.get("fact", "")

    # Extract name (remove "Component: " prefix)
    component_name = name
    if name.startswith("Component:"):
        component_name = name[len("Component:"):].strip()
    elif name.lower().startswith("component:"):
        component_name = name[len("component:"):].strip()

    # Extract description from content
    # Look for text after "Component: {name}" in the fact content
    description = content

    # Try to find where the actual description starts
    # Pattern: "Component: {name} {description}"
    if content.lower().startswith("component:"):
        # Remove the "Component: {name}" part
        # Find the component name in content and skip past it
        remaining = content
        if component_name.lower() in content.lower():
            # Find position after component name
            idx = content.lower().find(component_name.lower())
            if idx >= 0:
                remaining = content[idx + len(component_name):].strip()

        # Clean up description
        description = remaining

    result = {
        "name": component_name,
        "description": description,
    }

    if verbose:
        result["full_content"] = content

    return result


def _parse_decision_fact(fact: Dict[str, Any], verbose: bool) -> Dict[str, Any]:
    """Parse architecture decision fact into structured dict.

    Args:
        fact: Raw fact dict from Graphiti
        verbose: If True, include context and consequences fields

    Returns:
        Dict with ADR details (adr_id, title, status, etc.)
    """
    name = fact.get("name", "")
    content = fact.get("fact", "")

    # Extract ADR ID (e.g., "ADR-SP-001")
    adr_id_match = re.search(r"(ADR-[A-Z]+-\d+)", name, re.IGNORECASE)
    adr_id = adr_id_match.group(1) if adr_id_match else ""

    # Extract title (text after "ADR-XXX-NNN: ")
    title = name
    if ":" in name:
        title = name.split(":", 1)[1].strip()

    # Extract status (accepted/superseded)
    status = "accepted"  # default
    status_match = re.search(r"status:\s*(accepted|superseded)", content, re.IGNORECASE)
    if status_match:
        status = status_match.group(1).lower()

    result = {
        "adr_id": adr_id,
        "title": title,
        "status": status,
    }

    if verbose:
        # Extract context
        context_match = re.search(r"context:\s*([^.]+)", content, re.IGNORECASE)
        if context_match:
            result["context"] = context_match.group(1).strip()

        # Extract consequences
        consequences_match = re.search(r"consequences?:\s*([^.]+)", content, re.IGNORECASE)
        if consequences_match:
            result["consequences"] = consequences_match.group(1).strip()

        result["full_content"] = content

    return result


def _parse_concern_fact(fact: Dict[str, Any], verbose: bool) -> Dict[str, Any]:
    """Parse crosscutting concern fact into structured dict.

    Args:
        fact: Raw fact dict from Graphiti
        verbose: If True, include full_content field

    Returns:
        Dict with concern details (name, description, etc.)
    """
    name = fact.get("name", "")
    content = fact.get("fact", "")

    # Extract name (remove "Crosscutting: " prefix)
    concern_name = name
    if name.startswith("Crosscutting:"):
        concern_name = name[len("Crosscutting:"):].strip()
    elif name.lower().startswith("crosscutting:"):
        concern_name = name[len("crosscutting:"):].strip()

    # Extract description
    description = content

    result = {
        "name": concern_name,
        "description": description,
    }

    if verbose:
        result["full_content"] = content

    return result


def condense_for_injection(overview: Dict[str, Any], max_tokens: int = 800) -> str:
    """Condense overview to token budget for Claude Code injection.

    Priority order (highest to lowest):
        1. System methodology and name
        2. Component names
        3. ADR titles and IDs
        4. Crosscutting concern names
        5. Component descriptions
        6. ADR context/consequences
        7. Concern descriptions

    Args:
        overview: Structured overview from get_system_overview()
        max_tokens: Maximum token budget (estimated using word count * 1.3)

    Returns:
        Token-budgeted string, or empty string if status is "no_context"
    """
    if overview.get("status") != "ok":
        return ""

    # Build content in priority order
    parts = []
    current_tokens = 0

    # Priority 1: System methodology and name
    system = overview.get("system", {})
    if system:
        methodology = system.get("methodology", "")
        name = system.get("name", "")
        if methodology:
            text = f"Methodology: {methodology}"
            tokens = _estimate_tokens(text)
            if current_tokens + tokens <= max_tokens:
                parts.append(text)
                current_tokens += tokens
        if name and current_tokens < max_tokens:
            text = f"System: {name}"
            tokens = _estimate_tokens(text)
            if current_tokens + tokens <= max_tokens:
                parts.append(text)
                current_tokens += tokens

    # Priority 2: Component names
    components = overview.get("components", [])
    if components and current_tokens < max_tokens:
        comp_names = [c["name"] for c in components]
        text = f"Components: {', '.join(comp_names)}"
        tokens = _estimate_tokens(text)
        if current_tokens + tokens <= max_tokens:
            parts.append(text)
            current_tokens += tokens

    # Priority 3: ADR titles
    decisions = overview.get("decisions", [])
    if decisions and current_tokens < max_tokens:
        adr_texts = []
        for d in decisions:
            adr_id = d.get("adr_id", "")
            title = d.get("title", "")
            if adr_id and title:
                adr_texts.append(f"{adr_id}: {title}")
        if adr_texts:
            text = f"Decisions: {'; '.join(adr_texts)}"
            tokens = _estimate_tokens(text)
            if current_tokens + tokens <= max_tokens:
                parts.append(text)
                current_tokens += tokens

    # Priority 4: Crosscutting concern names
    concerns = overview.get("concerns", [])
    if concerns and current_tokens < max_tokens:
        concern_names = [c["name"] for c in concerns]
        text = f"Crosscutting Concerns: {', '.join(concern_names)}"
        tokens = _estimate_tokens(text)
        if current_tokens + tokens <= max_tokens:
            parts.append(text)
            current_tokens += tokens

    # Priority 5: Component descriptions (truncate if needed)
    for comp in components:
        if current_tokens >= max_tokens:
            break
        desc = comp.get("description", "")
        if desc:
            text = f"{comp['name']}: {desc}"
            tokens = _estimate_tokens(text)
            if current_tokens + tokens <= max_tokens:
                parts.append(text)
                current_tokens += tokens

    return "\n".join(parts)


def _estimate_tokens(text: str) -> int:
    """Estimate token count using simple heuristic.

    Uses word count * 1.3 as approximation (common for English text).

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count (0 for empty string)
    """
    if not text:
        return 0

    words = len(text.split())
    return int(words * 1.3)


def format_overview_display(
    overview: Dict[str, Any],
    section: str = "all",
    format: str = "display"
) -> str:
    """Format overview for display in terminal, markdown, or JSON.

    Args:
        overview: Structured overview from get_system_overview()
        section: Section filter - "all", "components", "decisions", "crosscutting"
        format: Output format - "display" (terminal), "markdown", "json"

    Returns:
        Formatted string ready for display
    """
    # Handle no context case
    if overview.get("status") != "ok":
        return "no context available"

    # JSON format
    if format == "json":
        return json.dumps(overview, indent=2)

    # Build sections
    lines = []

    # Markdown format uses ## headers
    header_prefix = "## " if format == "markdown" else ""

    # System context (always shown if present)
    if section in ["all", "system"]:
        system = overview.get("system", {})
        if system:
            lines.append(f"{header_prefix}System Context")
            if format == "markdown":
                lines.append("")

            if "name" in system:
                lines.append(f"Name: {system['name']}")
            if "methodology" in system:
                lines.append(f"Methodology: {system['methodology']}")
            if "purpose" in system:
                lines.append(f"Purpose: {system['purpose']}")

            lines.append("")

    # Components section
    if section in ["all", "components"]:
        components = overview.get("components", [])
        if components:
            lines.append(f"{header_prefix}Components")
            if format == "markdown":
                lines.append("")

            for comp in components:
                lines.append(f"- {comp['name']}")
                if "description" in comp:
                    lines.append(f"  {comp['description']}")

            lines.append("")

    # Decisions section
    if section in ["all", "decisions"]:
        decisions = overview.get("decisions", [])
        if decisions:
            lines.append(f"{header_prefix}Architecture Decisions")
            if format == "markdown":
                lines.append("")

            for dec in decisions:
                adr_id = dec.get("adr_id", "")
                title = dec.get("title", "")
                status = dec.get("status", "")

                lines.append(f"- {adr_id}: {title}")
                if status:
                    lines.append(f"  Status: {status}")

            lines.append("")

    # Crosscutting concerns section
    if section in ["all", "crosscutting"]:
        concerns = overview.get("concerns", [])
        if concerns:
            lines.append(f"{header_prefix}Crosscutting Concerns")
            if format == "markdown":
                lines.append("")

            for concern in concerns:
                lines.append(f"- {concern['name']}")
                if "description" in concern:
                    lines.append(f"  {concern['description']}")

            lines.append("")

    return "\n".join(lines)
