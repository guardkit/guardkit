"""
Architecture spec parser for /system-plan command.

Parses structured architecture markdown files (e.g., guardkit-system-spec.md)
into entity instances for Graphiti persistence and markdown generation.

Supports heading patterns:
    ## 1. System Context   -> SystemContextDef
    ### COMP-xxx: Name     -> ComponentDef
    ### XC-xxx: Name       -> CrosscuttingConcernDef
    ### ADR-SP-NNN: Title  -> ArchitectureDecision

Defensive parsing: missing sections produce warnings in parse_warnings, not errors.

Public API:
    parse_architecture_spec: Parse spec file into ArchSpecResult
    ArchSpecResult: Dataclass holding parsed entities and warnings

Example:
    from guardkit.planning.arch_spec_parser import parse_architecture_spec

    result = parse_architecture_spec(Path("docs/architecture/guardkit-system-spec.md"))
    print(f"Components: {len(result.components)}")
    print(f"ADRs: {len(result.decisions)}")
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from guardkit.knowledge.entities.architecture_context import ArchitectureDecision
from guardkit.knowledge.entities.component import ComponentDef
from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
from guardkit.knowledge.entities.system_context import SystemContextDef

logger = logging.getLogger(__name__)


@dataclass
class ArchSpecResult:
    """Result of parsing an architecture spec file."""

    system_context: Optional[SystemContextDef] = None
    components: List[ComponentDef] = field(default_factory=list)
    concerns: List[CrosscuttingConcernDef] = field(default_factory=list)
    decisions: List[ArchitectureDecision] = field(default_factory=list)
    parse_warnings: List[str] = field(default_factory=list)


def _extract_section(content: str, heading_pattern: str) -> str:
    """Extract content between a H2 heading and the next H2 heading.

    Args:
        content: Full markdown text.
        heading_pattern: Regex to match the section heading (H2 level).

    Returns:
        Section body (without heading) or empty string if not found.
    """
    match = re.search(heading_pattern, content, re.MULTILINE | re.IGNORECASE)
    if not match:
        return ""

    start = match.end()
    remaining = content[start:]

    next_h2 = re.search(r"^## ", remaining, re.MULTILINE)
    if next_h2:
        return remaining[: next_h2.start()].strip()
    return remaining.strip()


def _extract_field(text: str, field_name: str) -> str:
    """Extract a field value from ``- **Key**: Value`` pattern.

    Args:
        text: Block of text to search.
        field_name: Bold key name (e.g. "Purpose").

    Returns:
        Value string or empty string.
    """
    pattern = rf"-\s+\*\*{re.escape(field_name)}\*\*:\s*(.+)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return ""


def _extract_field_list(text: str, field_name: str) -> List[str]:
    """Extract a comma-separated list from ``- **Key**: a, b, c`` pattern."""
    raw = _extract_field(text, field_name)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _split_subsections(section_body: str, prefix: str) -> List[tuple]:
    """Split a section into (heading_text, body) tuples by H3 prefix.

    Args:
        section_body: Body text of a ## section.
        prefix: H3 prefix to match (e.g. "COMP-", "XC-", "ADR-SP-").

    Returns:
        List of (heading_text, body_text) tuples.
    """
    pattern = rf"^###\s+({re.escape(prefix)}\S+:\s*.+)$"
    headings = list(re.finditer(pattern, section_body, re.MULTILINE))

    results = []
    for i, m in enumerate(headings):
        heading_text = m.group(1).strip()
        body_start = m.end()
        if i + 1 < len(headings):
            body_end = headings[i + 1].start()
        else:
            body_end = len(section_body)
        body = section_body[body_start:body_end].strip()
        results.append((heading_text, body))
    return results


def _parse_system_context(
    content: str,
    component_names: List[str],
    external_systems: List[str],
) -> Optional[SystemContextDef]:
    """Parse ``## 1. System Context`` into a SystemContextDef.

    Args:
        content: Full spec content.
        component_names: Pre-extracted component names for bounded_contexts.
        external_systems: Pre-extracted external system names.

    Returns:
        SystemContextDef or None if section not found.
    """
    section = _extract_section(content, r"^##\s+\d+\.\s+System Context")
    if not section:
        return None

    identity_match = re.search(
        r"###\s+Identity\s*\n(.*?)(?=^###|\Z)", section, re.DOTALL | re.MULTILINE
    )
    identity_block = identity_match.group(1) if identity_match else section

    name = _extract_field(identity_block, "Name")
    purpose = _extract_field(identity_block, "Purpose")
    methodology = _extract_field(identity_block, "Methodology")

    if not methodology:
        methodology = "layered"
    else:
        # Normalise: take first word, lowercase
        methodology = methodology.split("(")[0].strip().split()[0].lower()

    if not name:
        return None

    return SystemContextDef(
        name=name,
        purpose=purpose,
        bounded_contexts=component_names,
        external_systems=external_systems,
        methodology=methodology,
    )


def _parse_external_systems(content: str) -> List[str]:
    """Extract external system names from the External Systems table."""
    section = _extract_section(content, r"^##\s+\d+\.\s+System Context")
    if not section:
        return []

    ext_match = re.search(
        r"###\s+External Systems\s*\n(.*?)(?=^###|\Z)",
        section,
        re.DOTALL | re.MULTILINE,
    )
    if not ext_match:
        return []

    table_text = ext_match.group(1)
    systems = []
    for line in table_text.split("\n"):
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) >= 2 and cells[0].lower() not in ("system", "**system**"):
            # Strip bold markers
            name = re.sub(r"\*\*", "", cells[0]).strip()
            if name:
                systems.append(name)
    return systems


def _parse_components(content: str) -> List[ComponentDef]:
    """Parse ``## 2. Components`` into ComponentDef list."""
    section = _extract_section(content, r"^##\s+\d+\.\s+Components")
    if not section:
        return []

    subsections = _split_subsections(section, "COMP-")
    components = []
    for heading, body in subsections:
        # heading: "COMP-cli-layer: CLI Layer"
        colon_idx = heading.index(":")
        name = heading[colon_idx + 1 :].strip()

        purpose = _extract_field(body, "Purpose")
        responsibilities_raw = _extract_field(body, "Responsibilities")
        responsibilities = [
            r.strip() for r in responsibilities_raw.split(",") if r.strip()
        ] if responsibilities_raw else []
        dependencies_raw = _extract_field(body, "Dependencies")
        dependencies = [
            d.strip() for d in dependencies_raw.split(",") if d.strip()
        ] if dependencies_raw else []

        # Detect methodology from system context
        methodology = "modular"

        components.append(
            ComponentDef(
                name=name,
                description=purpose,
                responsibilities=responsibilities,
                dependencies=dependencies,
                methodology=methodology,
            )
        )
    return components


def _parse_crosscutting(content: str) -> List[CrosscuttingConcernDef]:
    """Parse ``## 4. Cross-Cutting Concerns`` into CrosscuttingConcernDef list."""
    section = _extract_section(content, r"^##\s+\d+\.\s+Cross-?[Cc]utting Concerns")
    if not section:
        return []

    subsections = _split_subsections(section, "XC-")
    concerns = []
    for heading, body in subsections:
        colon_idx = heading.index(":")
        name = heading[colon_idx + 1 :].strip()

        approach = _extract_field(body, "Approach")
        affected_raw = _extract_field(body, "Affected Components")
        applies_to = [
            a.strip() for a in affected_raw.split(",") if a.strip()
        ] if affected_raw else []
        constraints = _extract_field(body, "Constraints")

        concerns.append(
            CrosscuttingConcernDef(
                name=name,
                description=approach,
                applies_to=applies_to,
                implementation_notes=constraints,
            )
        )
    return concerns


def _parse_decisions(content: str) -> List[ArchitectureDecision]:
    """Parse ``## 5. Architecture Decisions`` into ArchitectureDecision list."""
    section = _extract_section(content, r"^##\s+\d+\.\s+Architecture Decisions")
    if not section:
        return []

    subsections = _split_subsections(section, "ADR-SP-")
    decisions = []
    for heading, body in subsections:
        # heading: "ADR-SP-001: FalkorDB over Neo4j for Knowledge Graph"
        colon_idx = heading.index(":")
        adr_id = heading[:colon_idx].strip()
        title = heading[colon_idx + 1 :].strip()

        # Extract number from ADR-SP-NNN
        num_match = re.search(r"ADR-SP-(\d+)", adr_id)
        number = int(num_match.group(1)) if num_match else 0

        status = _extract_field(body, "Status")
        context = _extract_field(body, "Context")
        decision = _extract_field(body, "Decision")

        # Consequences: "- **Consequences**: +Foo, -Bar, +Baz"
        consequences_raw = _extract_field(body, "Consequences")
        consequences = []
        if consequences_raw:
            consequences = [
                c.strip() for c in re.split(r",\s*(?=[+-])", consequences_raw) if c.strip()
            ]

        # Related components from "Affected Components" or inferred
        related_raw = _extract_field(body, "Related Components")
        related_components = [
            r.strip() for r in related_raw.split(",") if r.strip()
        ] if related_raw else []

        decisions.append(
            ArchitectureDecision(
                number=number,
                title=title,
                status=status.lower() if status else "proposed",
                context=context,
                decision=decision,
                consequences=consequences,
                related_components=related_components,
            )
        )
    return decisions


def parse_architecture_spec(path: Path) -> ArchSpecResult:
    """Parse a structured architecture spec markdown into entity instances.

    Args:
        path: Path to the spec markdown file.

    Returns:
        ArchSpecResult with parsed entities and any parse warnings.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    content = path.read_text()
    warnings: List[str] = []

    # Parse components first (needed for system_context.bounded_contexts)
    components = _parse_components(content)
    if not components:
        warnings.append("No components found (expected ### COMP-xxx: headings)")

    component_names = [c.name for c in components]

    # Parse external systems from system context table
    external_systems = _parse_external_systems(content)

    # Parse system context
    system_context = _parse_system_context(content, component_names, external_systems)
    if system_context is None:
        warnings.append("No system context found (expected ## N. System Context)")

    # Propagate methodology from system context to components
    if system_context is not None:
        for comp in components:
            comp.methodology = system_context.methodology

    # Parse crosscutting concerns
    concerns = _parse_crosscutting(content)
    if not concerns:
        warnings.append(
            "No crosscutting concerns found (expected ### XC-xxx: headings)"
        )

    # Parse architecture decisions
    decisions = _parse_decisions(content)
    if not decisions:
        warnings.append(
            "No architecture decisions found (expected ### ADR-SP-xxx: headings)"
        )

    entity_count = (
        (1 if system_context else 0)
        + len(components)
        + len(concerns)
        + len(decisions)
    )
    logger.info(
        f"[Planning] Parsed architecture spec: {entity_count} entities "
        f"(1 system, {len(components)} components, "
        f"{len(concerns)} concerns, {len(decisions)} ADRs)"
    )

    return ArchSpecResult(
        system_context=system_context,
        components=components,
        concerns=concerns,
        decisions=decisions,
        parse_warnings=warnings,
    )


__all__ = [
    "parse_architecture_spec",
    "ArchSpecResult",
]
