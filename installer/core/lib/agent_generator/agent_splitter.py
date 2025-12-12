"""
Agent Content Splitter

Implements progressive disclosure pattern for agent files by splitting them into:
- Core file (*.md): Essential content, ~6-10KB
- Extended file (*-ext.md): Detailed reference, ~15-25KB

This reduces context window usage by ~55-60% for typical tasks while keeping
comprehensive documentation available on-demand.
"""

import re
from typing import Tuple, List


# Section markers that define core vs extended content
CORE_SECTIONS = [
    "## Overview",
    "## Purpose",
    "## Boundaries",
    "## Quick Start",
    "## Capabilities",
    "## Phase Integration",
    "## Loading Extended Content"
]

EXTENDED_SECTIONS = [
    "## Detailed Examples",
    "## Best Practices",
    "## Anti-Patterns",
    "## Technology-Specific Guidance",
    "## Troubleshooting"
]

# Size targets (in bytes)
CORE_SIZE_TARGET = (6 * 1024, 10 * 1024)  # 6-10KB
CORE_SIZE_WARNING = 15 * 1024  # 15KB
EXTENDED_SIZE_TARGET = (15 * 1024, 25 * 1024)  # 15-25KB
EXTENDED_SIZE_WARNING = 30 * 1024  # 30KB


def split_agent_content(agent_content: str) -> Tuple[str, str]:
    """
    Split agent content into core and extended parts.

    Args:
        agent_content: Full agent markdown content

    Returns:
        tuple[str, str]: (core_content, extended_content)

    Raises:
        ValueError: If agent_content is empty

    Core content (~6-10KB):
        - Frontmatter
        - Overview/Purpose
        - Boundaries (ALWAYS/NEVER/ASK)
        - Quick Start (first 5-10 examples)
        - Capabilities summary
        - Phase integration
        - Loading instructions for extended content

    Extended content (~15-25KB):
        - Detailed code examples (beyond first 10)
        - Best practices with full explanations
        - Anti-patterns with code samples
        - Technology-specific guidance
        - Troubleshooting scenarios
    """
    if not agent_content or not agent_content.strip():
        raise ValueError("Agent content cannot be empty")

    # Parse agent content into sections
    sections = _parse_sections(agent_content)

    # Extract frontmatter
    frontmatter = _extract_frontmatter(agent_content)

    # Get agent name for cross-references
    agent_name = _extract_agent_name(frontmatter)

    # Separate sections into core and extended
    core_sections = []
    extended_sections = []

    for section_name, section_content in sections.items():
        if any(core_marker in section_name for core_marker in CORE_SECTIONS):
            core_sections.append((section_name, section_content))
        elif any(ext_marker in section_name for ext_marker in EXTENDED_SECTIONS):
            extended_sections.append((section_name, section_content))
        else:
            # Default: put in core if it's early in the file, extended otherwise
            if section_name.startswith("# "):  # Title section
                core_sections.append((section_name, section_content))
            else:
                # Check if it's before "Detailed Examples"
                content_pos = agent_content.find(section_content)
                detailed_pos = agent_content.find("## Detailed Examples")
                if detailed_pos == -1 or content_pos < detailed_pos:
                    core_sections.append((section_name, section_content))
                else:
                    extended_sections.append((section_name, section_content))

    # Build core content
    core_content = frontmatter + "\n\n"
    for section_name, section_content in core_sections:
        core_content += section_content + "\n\n"

    # Add loading instructions if not already present
    if "## Loading Extended Content" not in core_content:
        core_content += f"## Loading Extended Content\n\nFor detailed examples and best practices, see `{agent_name}-ext.md`.\n\n"

    # Build extended content with reference to core
    # Only create extended content if there are extended sections
    if extended_sections:
        extended_content = f"# {agent_name} - Extended Reference\n\n"
        extended_content += f"This file contains detailed examples and best practices for the {agent_name} agent.\n\n"
        extended_content += f"For core capabilities and quick start, see the main agent file `{agent_name}.md`.\n\n"

        for section_name, section_content in extended_sections:
            extended_content += section_content + "\n\n"
    else:
        # Minimal agent: just a header and reference back
        extended_content = f"# {agent_name} - Extended Reference\n\n"
        extended_content += f"See the main agent file `{agent_name}.md` for all content.\n"

    return core_content.strip(), extended_content.strip()


def validate_split_sizes(core: str, extended: str) -> List[str]:
    """
    Validate split file sizes against targets.

    Args:
        core: Core file content
        extended: Extended file content

    Returns:
        List of warnings (empty if all pass)

    Targets:
        Core: 6-10KB (warning at 15KB)
        Extended: 15-25KB (warning at 30KB)
    """
    warnings = []

    core_size = len(core.encode('utf-8'))
    extended_size = len(extended.encode('utf-8'))

    # Check core size
    if core_size > CORE_SIZE_WARNING:
        warnings.append(
            f"Core file size ({core_size / 1024:.1f}KB) exceeds warning threshold "
            f"({CORE_SIZE_WARNING / 1024:.0f}KB). Target: {CORE_SIZE_TARGET[0] / 1024:.0f}-"
            f"{CORE_SIZE_TARGET[1] / 1024:.0f}KB"
        )

    # Check extended size
    if extended_size > EXTENDED_SIZE_WARNING:
        warnings.append(
            f"Extended file size ({extended_size / 1024:.1f}KB) exceeds warning threshold "
            f"({EXTENDED_SIZE_WARNING / 1024:.0f}KB). Target: {EXTENDED_SIZE_TARGET[0] / 1024:.0f}-"
            f"{EXTENDED_SIZE_TARGET[1] / 1024:.0f}KB"
        )

    return warnings


def _parse_sections(content: str) -> dict:
    """
    Parse agent content into sections.

    Args:
        content: Agent markdown content

    Returns:
        dict: {section_name: section_content}
    """
    sections = {}
    current_section = None
    current_content = []

    lines = content.split('\n')
    in_frontmatter = False
    frontmatter_closed = False

    for line in lines:
        # Skip frontmatter (handled separately)
        if line.strip() == '---':
            if not in_frontmatter and not frontmatter_closed:
                in_frontmatter = True
                continue
            elif in_frontmatter:
                frontmatter_closed = True
                in_frontmatter = False
                continue

        if in_frontmatter:
            continue

        # Check for section headers (# or ##)
        if re.match(r'^#{1,2}\s+', line):
            # Save previous section
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()

            # Start new section
            current_section = line
            current_content = [line]
        elif current_section:
            current_content.append(line)

    # Save last section
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections


def _extract_frontmatter(content: str) -> str:
    """
    Extract frontmatter from agent content.

    Args:
        content: Agent markdown content

    Returns:
        str: Frontmatter with delimiters
    """
    lines = content.split('\n')
    frontmatter_lines = []
    in_frontmatter = False
    frontmatter_started = False

    for line in lines:
        if line.strip() == '---':
            if not frontmatter_started:
                frontmatter_started = True
                in_frontmatter = True
                frontmatter_lines.append(line)
            elif in_frontmatter:
                frontmatter_lines.append(line)
                break
        elif in_frontmatter:
            frontmatter_lines.append(line)

    return '\n'.join(frontmatter_lines) if frontmatter_lines else '---\n---'


def _extract_agent_name(frontmatter: str) -> str:
    """
    Extract agent name from frontmatter.

    Args:
        frontmatter: Agent frontmatter content

    Returns:
        str: Agent name (defaults to "agent" if not found)
    """
    # Look for name field in frontmatter
    match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
    if match:
        return match.group(1).strip()

    return "agent"
