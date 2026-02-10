"""Impact Analysis: Assess task impact on architecture and scenarios.

This module queries Graphiti to identify affected components, constraining ADRs,
and at-risk BDD scenarios. It provides:

1. Multi-depth analysis (quick, standard, deep)
2. Risk scoring heuristic (1-5 scale with labels)
3. Task ID vs topic string query building
4. Token-budgeted condensation for coach injection
5. Terminal display formatting with Unicode risk bars
6. Graceful degradation when BDD group missing/empty

All log messages use [Graphiti] prefix for easy filtering.

Public API:
    run_impact_analysis: Main entry point for analyzing task impact
    condense_impact_for_injection: Token-budgeted condensation for coach injection
    format_impact_display: Format impact for terminal display

Example:
    from guardkit.planning.impact_analysis import (
        run_impact_analysis,
        condense_impact_for_injection,
        format_impact_display
    )
    from guardkit.planning.graphiti_arch import SystemPlanGraphiti

    sp = SystemPlanGraphiti(client=client, project_id="my-project")

    # Run impact analysis
    impact = await run_impact_analysis(
        sp=sp,
        client=client,
        task_or_topic="TASK-SC-005",
        depth="standard",
        include_bdd=False,
        include_tasks=False
    )

    # Condense for injection (max 1200 tokens)
    condensed = condense_impact_for_injection(impact, max_tokens=1200)

    # Format for display
    display = format_impact_display(impact, depth="standard")
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from guardkit.planning.graphiti_arch import SystemPlanGraphiti
    from guardkit.knowledge.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)


async def run_impact_analysis(
    sp: "SystemPlanGraphiti",
    client: "GraphitiClient",
    task_or_topic: str,
    depth: str = "standard",
    include_bdd: bool = False,
    include_tasks: bool = False,
) -> Dict[str, Any]:
    """Run impact analysis for task or topic.

    Queries Graphiti groups to identify:
    - Affected components (all depths)
    - Constraining ADRs (standard/deep)
    - At-risk BDD scenarios (deep with include_bdd=True)
    - Related tasks (deep with include_tasks=True)

    Args:
        sp: SystemPlanGraphiti instance
        client: GraphitiClient instance
        task_or_topic: Task ID (TASK-XXX) or topic string
        depth: Analysis depth - "quick", "standard", or "deep"
        include_bdd: Include BDD scenarios (deep mode only)
        include_tasks: Include related tasks (deep mode only)

    Returns:
        Dict with keys:
            - status: "ok" or "no_context"
            - components: List of affected component dicts
            - adrs: List of constraining ADR dicts (standard/deep only)
            - bdd_scenarios: List of scenario dicts (deep with include_bdd only)
            - risk: Risk score dict with score, label, rationale
            - implications: List of implication strings
            - query: The query string used

        Returns {"status": "no_context"} when:
            - sp._available is False
            - client.enabled is False
            - All queries return empty results
            - Exception occurs
    """
    # Check if Graphiti is available
    if not sp._available or not client.enabled:
        logger.debug("[Graphiti] Impact analysis not available")
        return {"status": "no_context"}

    try:
        # Build query from task ID or topic
        query = _build_query(task_or_topic)
        logger.info(f"[Graphiti] Running impact analysis: depth={depth}, query='{query}'")

        result = {
            "status": "ok",
            "query": query,
        }

        # Query project_architecture for affected components (all depths)
        arch_group_id = client.get_group_id("project_architecture")
        component_hits = await client.search(
            query=query,
            group_ids=[arch_group_id],
            num_results=10,
        )
        components = _parse_component_hits(component_hits)
        result["components"] = components

        # Query project_decisions for ADRs (standard/deep only)
        adrs = []
        if depth in ["standard", "deep"]:
            decisions_group_id = client.get_group_id("project_decisions")
            adr_hits = await client.search(
                query=query,
                group_ids=[decisions_group_id],
                num_results=10,
            )
            adrs = _parse_adr_hits(adr_hits)
            result["adrs"] = adrs

        # Query bdd_scenarios group (deep mode with include_bdd=True)
        bdd_scenarios = []
        if depth == "deep" and include_bdd:
            try:
                bdd_group_id = client.get_group_id("bdd_scenarios")
                bdd_hits = await client.search(
                    query=query,
                    group_ids=[bdd_group_id],
                    num_results=10,
                )
                bdd_scenarios = _parse_bdd_hits(bdd_hits)
                if bdd_scenarios:
                    result["bdd_scenarios"] = bdd_scenarios
                else:
                    logger.info("[Graphiti] No BDD scenarios found, skipping BDD impact section")
            except Exception as e:
                logger.info("[Graphiti] No BDD scenarios found, skipping BDD impact section")

        # Calculate risk score
        risk = _calculate_risk(components, adrs, bdd_scenarios)
        result["risk"] = risk

        # Derive implications
        implications = _derive_implications(components, adrs)
        result["implications"] = implications

        # Check if we have any data
        if not components and not adrs and not bdd_scenarios:
            logger.debug("[Graphiti] No impact data found")
            return {"status": "no_context"}

        return result

    except Exception as e:
        logger.warning(f"[Graphiti] Failed to run impact analysis: {e}")
        return {"status": "no_context"}


def _build_query(task_or_topic: str) -> str:
    """Build query string from task ID or topic.

    If input matches TASK-[A-Z0-9-]+ pattern:
        - Searches in tasks/{in_progress,backlog,design_approved}/
        - Extracts title and tags from frontmatter
        - Returns enriched query string

    Otherwise:
        - Returns topic string directly

    Args:
        task_or_topic: Task ID or topic string

    Returns:
        Query string for Graphiti search
    """
    # Check if it's a task ID
    task_pattern = r"^TASK-[A-Z0-9-]+$"
    if not re.match(task_pattern, task_or_topic):
        # Not a task ID, return as-is
        return task_or_topic

    # Try to find and read task file
    task_dirs = [
        "tasks/in_progress",
        "tasks/backlog",
        "tasks/design_approved",
    ]

    for task_dir in task_dirs:
        task_file = Path(task_dir) / f"{task_or_topic}.md"
        if task_file.exists():
            try:
                # Use open() for proper mock compatibility
                with open(task_file, "r") as f:
                    content = f.read()

                # Parse frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]

                        # Extract title
                        title_match = re.search(r"title:\s*(.+)", frontmatter)
                        title = title_match.group(1).strip() if title_match else ""

                        # Extract tags
                        tags_section = re.search(
                            r"tags:\s*\n((?:  -.*\n)*)", frontmatter
                        )
                        tags = []
                        if tags_section:
                            tag_lines = tags_section.group(1).strip().split("\n")
                            tags = [
                                line.strip().replace("- ", "")
                                for line in tag_lines
                                if line.strip().startswith("-")
                            ]

                        # Build enriched query
                        query_parts = []
                        if title:
                            query_parts.append(title)
                        if tags:
                            query_parts.extend(tags)

                        if query_parts:
                            return " ".join(query_parts)

            except Exception as e:
                logger.debug(f"[Graphiti] Failed to read task file {task_file}: {e}")

    # Fallback: use task ID itself
    return task_or_topic


def _calculate_risk(
    components: List[Dict[str, Any]],
    adrs: List[Dict[str, Any]],
    bdd_scenarios: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculate risk score using heuristic.

    Scoring:
        - Base score: 1.0
        - +0.5 per component beyond first (if score > 0.5)
        - +1.0 per ADR with conflict indicator
        - +0.25 per informational ADR
        - +0.3 per at-risk BDD scenario
        - Clamp to 1-5 range
        - Round to nearest int

    Labels:
        - 1: "low"
        - 2: "medium"
        - 3: "medium"
        - 4: "high"
        - 5: "critical"

    Args:
        components: List of component dicts
        adrs: List of ADR dicts
        bdd_scenarios: List of BDD scenario dicts

    Returns:
        Dict with keys: score (int), label (str), rationale (str)
    """
    score = 1.0

    # Add score for components beyond first
    if len(components) > 1:
        score += 0.5 * (len(components) - 1)

    # Add score for ADRs
    for adr in adrs:
        if adr.get("conflict", False):
            score += 1.0
        else:
            score += 0.25

    # Add score for at-risk BDD scenarios
    for scenario in bdd_scenarios:
        if scenario.get("at_risk", False):
            score += 0.3

    # Clamp to 1-5 range
    score = max(1.0, min(5.0, score))

    # Round to nearest int
    score_int = round(score)

    # Assign label
    label_map = {
        1: "low",
        2: "medium",
        3: "medium",
        4: "high",
        5: "critical",
    }
    label = label_map.get(score_int, "medium")

    # Build rationale
    rationale_parts = []
    if components:
        rationale_parts.append(f"{len(components)} component(s) affected")
    if adrs:
        conflict_count = sum(1 for adr in adrs if adr.get("conflict", False))
        if conflict_count > 0:
            rationale_parts.append(f"{conflict_count} conflicting ADR(s)")
        else:
            rationale_parts.append(f"{len(adrs)} constraining ADR(s)")
    if bdd_scenarios:
        at_risk_count = sum(1 for s in bdd_scenarios if s.get("at_risk", False))
        if at_risk_count > 0:
            rationale_parts.append(f"{at_risk_count} at-risk scenario(s)")

    rationale = "; ".join(rationale_parts) if rationale_parts else "Minimal impact"

    return {
        "score": score_int,
        "label": label,
        "rationale": rationale,
    }


def _parse_component_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse Graphiti component search results.

    Extracts:
        - name: Component name (removes "Component:" prefix)
        - description: Component description from fact content
        - relevance_score: Search relevance score

    Args:
        hits: List of Graphiti search result dicts

    Returns:
        List of component dicts
    """
    components = []

    for hit in hits:
        name = hit.get("name", "")
        fact = hit.get("fact", "")
        score = hit.get("score", 0.0)

        # Extract component name (remove "Component:" prefix)
        component_name = name
        if name.startswith("Component:"):
            component_name = name[len("Component:"):].strip()
        elif name.lower().startswith("component:"):
            component_name = name[len("component:"):].strip()

        # Extract description from fact
        description = fact

        # Try to find where actual description starts
        if fact.lower().startswith("component:"):
            # Find component name in fact and skip past it
            if component_name.lower() in fact.lower():
                idx = fact.lower().find(component_name.lower())
                if idx >= 0:
                    remaining = fact[idx + len(component_name):].strip()
                    description = remaining

        components.append({
            "name": component_name,
            "description": description,
            "relevance_score": score,
        })

    return components


def _parse_adr_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse Graphiti ADR search results.

    Extracts:
        - adr_id: ADR ID (pattern: ADR-[A-Z]+-[0-9]+)
        - title: ADR title (text after "ADR-XXX-NNN:")
        - conflict: Boolean indicating conflict keywords

    Conflict keywords:
        - "conflicts with"
        - "violates"
        - "superseded by"

    Args:
        hits: List of Graphiti search result dicts

    Returns:
        List of ADR dicts
    """
    adrs = []

    for hit in hits:
        name = hit.get("name", "")
        fact = hit.get("fact", "")

        # Extract ADR ID
        adr_id_match = re.search(r"(ADR-[A-Z]+-\d+)", name, re.IGNORECASE)
        adr_id = adr_id_match.group(1) if adr_id_match else ""

        # Extract title (text after "ADR-XXX-NNN:")
        title = name
        if ":" in name:
            title = name.split(":", 1)[1].strip()

        # Detect conflict keywords
        conflict_keywords = ["conflicts with", "violates", "superseded by"]
        conflict = any(keyword in fact.lower() for keyword in conflict_keywords)

        adrs.append({
            "adr_id": adr_id,
            "title": title,
            "conflict": conflict,
        })

    return adrs


def _parse_bdd_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse Graphiti BDD scenario search results.

    Extracts:
        - scenario_name: Scenario name
        - file_location: File location from fact
        - at_risk: Boolean indicating at-risk keywords

    At-risk keywords:
        - "at risk"
        - "at-risk"

    Args:
        hits: List of Graphiti search result dicts

    Returns:
        List of BDD scenario dicts
    """
    scenarios = []

    for hit in hits:
        name = hit.get("name", "")
        fact = hit.get("fact", "")

        # Extract scenario name (remove "Scenario:" prefix if present)
        scenario_name = name
        if name.startswith("Scenario:"):
            scenario_name = name[len("Scenario:"):].strip()
        elif name.lower().startswith("scenario:"):
            scenario_name = name[len("scenario:"):].strip()

        # Extract file location from fact (look for "File: path" pattern)
        file_match = re.search(r"File:\s*([^.]+\.feature:\d+)", fact)
        file_location = file_match.group(1).strip() if file_match else ""

        # Detect at-risk keywords
        at_risk = "at risk" in fact.lower() or "at-risk" in fact.lower()

        scenarios.append({
            "scenario_name": scenario_name,
            "file_location": file_location,
            "at_risk": at_risk,
        })

    return scenarios


def _derive_implications(
    component_hits: List[Dict[str, Any]],
    adr_hits: List[Dict[str, Any]],
) -> List[str]:
    """Derive human-readable implications from components and ADRs.

    Generates implications like:
        - "Changes to Order Management may affect dependent components"
        - "ADR-SP-002 has conflicts that must be resolved"

    Args:
        component_hits: List of component dicts
        adr_hits: List of ADR dicts

    Returns:
        List of implication strings
    """
    implications = []

    # Component implications
    for comp in component_hits:
        name = comp.get("name", "")
        implications.append(f"Changes to {name} may affect dependent components")

    # ADR implications
    for adr in adr_hits:
        adr_id = adr.get("adr_id", "")
        title = adr.get("title", "")
        conflict = adr.get("conflict", False)

        if conflict:
            implications.append(f"{adr_id} ({title}) has conflicts that must be resolved")
        else:
            implications.append(f"{adr_id} ({title}) provides constraints to follow")

    return implications


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


def condense_impact_for_injection(
    impact: Dict[str, Any],
    max_tokens: int = 1200,
) -> str:
    """Condense impact analysis to token budget for coach injection.

    Priority order (highest to lowest):
        1. Risk score and label
        2. Affected component names
        3. ADR constraints (conflicts prioritized)
        4. Implications

    Args:
        impact: Impact analysis dict from run_impact_analysis()
        max_tokens: Maximum token budget (estimated using word count * 1.3)

    Returns:
        Token-budgeted string, or empty string if status is "no_context"
    """
    if impact.get("status") != "ok":
        return ""

    # Build content in priority order
    parts = []
    current_tokens = 0

    # Priority 1: Risk score
    risk = impact.get("risk", {})
    if risk:
        score = risk.get("score", 0)
        label = risk.get("label", "")
        rationale = risk.get("rationale", "")
        text = f"Risk: {score}/5 ({label}) - {rationale}"
        tokens = _estimate_tokens(text)
        if current_tokens + tokens <= max_tokens:
            parts.append(text)
            current_tokens += tokens

    # Priority 2: Component names
    components = impact.get("components", [])
    if components and current_tokens < max_tokens:
        comp_names = [c["name"] for c in components]
        text = f"Affected Components: {', '.join(comp_names)}"
        tokens = _estimate_tokens(text)
        if current_tokens + tokens <= max_tokens:
            parts.append(text)
            current_tokens += tokens

    # Priority 3: ADR constraints (conflicts first)
    adrs = impact.get("adrs", [])
    if adrs and current_tokens < max_tokens:
        # Separate conflicts and informational
        conflicts = [adr for adr in adrs if adr.get("conflict", False)]
        informational = [adr for adr in adrs if not adr.get("conflict", False)]

        # Add conflicts first
        for adr in conflicts:
            if current_tokens >= max_tokens:
                break
            adr_id = adr.get("adr_id", "")
            title = adr.get("title", "")
            text = f"CONFLICT: {adr_id} - {title}"
            tokens = _estimate_tokens(text)
            if current_tokens + tokens <= max_tokens:
                parts.append(text)
                current_tokens += tokens

        # Add informational ADRs
        for adr in informational:
            if current_tokens >= max_tokens:
                break
            adr_id = adr.get("adr_id", "")
            title = adr.get("title", "")
            text = f"Constraint: {adr_id} - {title}"
            tokens = _estimate_tokens(text)
            if current_tokens + tokens <= max_tokens:
                parts.append(text)
                current_tokens += tokens

    # Priority 4: Implications (truncate if needed)
    implications = impact.get("implications", [])
    for imp in implications:
        if current_tokens >= max_tokens:
            break
        tokens = _estimate_tokens(imp)
        if current_tokens + tokens <= max_tokens:
            parts.append(f"- {imp}")
            current_tokens += tokens

    return "\n".join(parts)


def format_impact_display(
    impact: Dict[str, Any],
    depth: str = "standard",
) -> str:
    """Format impact analysis for terminal display.

    Sections based on depth:
        - quick: Components only
        - standard: Components + ADRs + implications
        - deep: Components + ADRs + BDD scenarios + implications

    Risk bar uses Unicode blocks to visualize 1-5 scale:
        - 1: [█    ] Low
        - 2: [██   ] Medium-Low
        - 3: [███  ] Medium
        - 4: [████ ] Medium-High
        - 5: [█████] High

    Args:
        impact: Impact analysis dict from run_impact_analysis()
        depth: Display depth - "quick", "standard", or "deep"

    Returns:
        Formatted string ready for terminal display
    """
    if impact.get("status") != "ok":
        return "no impact data"

    lines = []

    # Risk score with visual bar
    risk = impact.get("risk", {})
    if risk:
        score = risk.get("score", 0)
        label = risk.get("label", "")
        rationale = risk.get("rationale", "")

        # Build risk bar
        filled = "█" * score
        empty = " " * (5 - score)
        bar = f"[{filled}{empty}]"

        lines.append(f"Risk: {bar} {score}/5 ({label})")
        lines.append(f"Rationale: {rationale}")
        lines.append("")

    # Components (all depths)
    components = impact.get("components", [])
    if components:
        lines.append("Affected Components:")
        for comp in components:
            name = comp.get("name", "")
            relevance = comp.get("relevance_score", 0.0)
            lines.append(f"  - {name} (relevance: {relevance:.2f})")
        lines.append("")

    # ADRs (standard/deep only)
    if depth in ["standard", "deep"]:
        adrs = impact.get("adrs", [])
        if adrs:
            lines.append("Constraining ADRs:")
            for adr in adrs:
                adr_id = adr.get("adr_id", "")
                title = adr.get("title", "")
                conflict = adr.get("conflict", False)
                conflict_marker = " [CONFLICT]" if conflict else ""
                lines.append(f"  - {adr_id}: {title}{conflict_marker}")
            lines.append("")

    # BDD scenarios (deep only)
    if depth == "deep":
        bdd_scenarios = impact.get("bdd_scenarios", [])
        if bdd_scenarios:
            lines.append("BDD Scenarios:")
            for scenario in bdd_scenarios:
                name = scenario.get("scenario_name", "")
                file_loc = scenario.get("file_location", "")
                at_risk = scenario.get("at_risk", False)
                risk_marker = " [AT RISK]" if at_risk else ""
                lines.append(f"  - {name}{risk_marker}")
                if file_loc:
                    lines.append(f"    Location: {file_loc}")
            lines.append("")

    # Implications (standard/deep only)
    if depth in ["standard", "deep"]:
        implications = impact.get("implications", [])
        if implications:
            lines.append("Implications:")
            for imp in implications:
                lines.append(f"  - {imp}")
            lines.append("")

    return "\n".join(lines)
