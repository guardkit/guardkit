"""
Content extraction from agent files for guidance generation.

Extracts boundaries, capability summaries, and other key content
from full agent markdown files.
"""

import re
from typing import Optional


def extract_boundaries(agent_content: str) -> str:
    """
    Extract the Boundaries section from agent content.

    Args:
        agent_content: Full agent markdown content

    Returns:
        Boundaries section including ALWAYS/NEVER/ASK subsections,
        or empty string if not found
    """
    # Find the Boundaries section
    boundaries_match = re.search(
        r'## Boundaries\s*\n(.*?)(?=\n## |\Z)',
        agent_content,
        re.DOTALL
    )

    if not boundaries_match:
        return ""

    boundaries = boundaries_match.group(1).strip()

    # Validate that we have all three subsections
    if not all(section in boundaries for section in ["### ALWAYS", "### NEVER", "### ASK"]):
        return ""

    return boundaries


def extract_capability_summary(agent_content: str) -> str:
    """
    Extract a brief capability summary from agent content.

    Tries to extract from the Capabilities section first,
    falls back to the description at the top of the file.

    Args:
        agent_content: Full agent markdown content

    Returns:
        Brief 2-3 sentence summary of agent capabilities
    """
    # Try to extract from Capabilities section
    capabilities_match = re.search(
        r'## Capabilities\s*\n(.*?)(?=\n## |\Z)',
        agent_content,
        re.DOTALL
    )

    if capabilities_match:
        capabilities_text = capabilities_match.group(1).strip()
        # Extract first paragraph or list
        lines = capabilities_text.split('\n')
        summary_lines = []
        for line in lines:
            if line.strip():
                summary_lines.append(line.strip())
                # Stop after ~2-3 sentences or bullet points
                if len(summary_lines) >= 3:
                    break

        if summary_lines:
            return '\n'.join(summary_lines)

    # Fallback: Extract description after first heading
    # Look for content between first # heading and first ## heading
    description_match = re.search(
        r'^# [^\n]+\s*\n(.*?)(?=\n## |\Z)',
        agent_content,
        re.DOTALL | re.MULTILINE
    )

    if description_match:
        description = description_match.group(1).strip()
        # Take first 2-3 sentences
        sentences = re.split(r'[.!?]\s+', description)
        return '. '.join(sentences[:3]) + '.'

    return "Specialized agent for specific development tasks."


def extract_when_to_use(agent_content: str, capabilities: list[str]) -> str:
    """
    Generate "When to Use" bullet points based on agent capabilities.

    Args:
        agent_content: Full agent markdown content
        capabilities: List of capability keywords from metadata

    Returns:
        2-3 bullet points describing when to use this agent
    """
    when_to_use = []

    # Check for Integration with GuardKit section
    integration_match = re.search(
        r'## Integration with GuardKit\s*\n(.*?)(?=\n## |\Z)',
        agent_content,
        re.DOTALL
    )

    if integration_match:
        integration_text = integration_match.group(1)
        # Extract "When invoked" line
        when_invoked_match = re.search(
            r'\*\*When invoked\*\*:\s*([^\n]+)',
            integration_text
        )
        if when_invoked_match:
            when_to_use.append(when_invoked_match.group(1).strip())

    # Generate based on capabilities if we don't have enough
    if len(when_to_use) < 2 and capabilities:
        for cap in capabilities[:2]:
            when_to_use.append(f"Working with {cap.replace('-', ' ')} in your codebase")

    # Default fallback
    if not when_to_use:
        when_to_use = [
            "Implementing features related to this agent's specialty",
            "Need expert guidance in this specific domain"
        ]

    # Format as bullet points
    return '\n'.join(f"- {item}" for item in when_to_use[:3])
