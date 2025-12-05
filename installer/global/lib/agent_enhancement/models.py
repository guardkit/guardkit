"""
Agent Enhancement Data Models

Type-safe data structures for agent enhancement and progressive disclosure.

TASK-PD-001: Created for split file architecture support
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, List


class AgentEnhancement(TypedDict, total=False):
    """
    Type-safe enhancement data structure.

    Used to pass enhancement content between parser, applier, and orchestrator.
    All fields are optional to support partial enhancements.

    Attributes:
        sections: List of section names included in enhancement
        frontmatter: YAML metadata (priority, stack, phase, etc.)
        title: Agent name and purpose
        quick_start: 2-3 usage examples (core content)
        boundaries: ALWAYS/NEVER/ASK framework (required)
        capabilities: Bullet list of agent capabilities
        phase_integration: When agent is used in workflow
        detailed_examples: 5-10 comprehensive examples (extended)
        best_practices: Detailed best practice recommendations (extended)
        anti_patterns: Common mistakes to avoid (extended)
        cross_stack: Multi-language examples (extended)
        mcp_integration: Optional MCP server integration (extended)
        troubleshooting: Debug guides and solutions (extended)
        technology_specific: Per-technology guidance (extended)
        loading_instruction: Reference to extended file (generated)
    """
    sections: List[str]
    frontmatter: str
    title: str
    quick_start: str
    boundaries: str
    capabilities: str
    phase_integration: str
    detailed_examples: str
    best_practices: str
    anti_patterns: str
    cross_stack: str
    mcp_integration: str
    troubleshooting: str
    technology_specific: str
    loading_instruction: str


@dataclass
class SplitContent:
    """
    Represents content split between core and extended agent files.

    Used by apply_with_split() to return information about created files
    and section distribution for progressive disclosure.

    Attributes:
        core_path: Path to core agent file (e.g., agent-name.md)
        extended_path: Path to extended file (e.g., agent-name-ext.md) or None
        core_sections: List of section names in core file
        extended_sections: List of section names in extended file

    Example:
        >>> split = SplitContent(
        ...     core_path=Path("fastapi-specialist.md"),
        ...     extended_path=Path("fastapi-specialist-ext.md"),
        ...     core_sections=["frontmatter", "title", "quick_start", "boundaries"],
        ...     extended_sections=["detailed_examples", "best_practices"]
        ... )
    """
    core_path: Path
    extended_path: Path | None
    core_sections: List[str]
    extended_sections: List[str]
