"""
Main guidance file generator.

Orchestrates extraction, pattern generation, and file assembly.
"""

import re
import yaml
from pathlib import Path
from typing import Optional

from .extractor import (
    extract_boundaries,
    extract_capability_summary,
    extract_when_to_use,
)
from .path_patterns import generate_path_patterns
from .validator import validate_guidance_size


def parse_frontmatter(agent_content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from agent content.

    Args:
        agent_content: Full agent markdown content

    Returns:
        Tuple of (metadata dict, content without frontmatter)
    """
    # Check for frontmatter
    if not agent_content.startswith("---"):
        return {}, agent_content

    # Find end of frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', agent_content, re.DOTALL)
    if not match:
        return {}, agent_content

    frontmatter_text = match.group(1)
    content = match.group(2)

    try:
        metadata = yaml.safe_load(frontmatter_text)
        return metadata or {}, content
    except yaml.YAMLError:
        # Return empty metadata if frontmatter is malformed
        return {}, agent_content


def generate_guidance_from_agent(agent_content: str, agent_name: str) -> str:
    """
    Generate a slim guidance file from full agent content.

    Args:
        agent_content: Full agent markdown content
        agent_name: Name of the agent (e.g., 'api-specialist')

    Returns:
        Complete guidance file content (markdown with frontmatter)
    """
    # Parse frontmatter
    metadata, content_without_fm = parse_frontmatter(agent_content)

    # Extract components
    boundaries = extract_boundaries(agent_content)
    capability_summary = extract_capability_summary(agent_content)
    path_patterns = generate_path_patterns(metadata)
    when_to_use = extract_when_to_use(
        agent_content,
        metadata.get("capabilities", [])
    )

    # Extract display name from first heading
    display_name_match = re.search(r'^# (.+)$', agent_content, re.MULTILINE)
    display_name = display_name_match.group(1) if display_name_match else agent_name.replace('-', ' ').title()

    # Build guidance content
    guidance_parts = []

    # Frontmatter
    frontmatter = {
        "agent": agent_name,
    }
    if path_patterns:
        frontmatter["paths"] = path_patterns

    guidance_parts.append("---")
    guidance_parts.append(yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).strip())
    guidance_parts.append("---")
    guidance_parts.append("")

    # Title
    guidance_parts.append(f"# {display_name} - Quick Reference")
    guidance_parts.append("")

    # Capability summary
    guidance_parts.append(capability_summary)
    guidance_parts.append("")

    # Boundaries
    if boundaries:
        guidance_parts.append("## Boundaries")
        guidance_parts.append("")
        guidance_parts.append(boundaries)
        guidance_parts.append("")

    # When to Use
    guidance_parts.append("## When to Use")
    guidance_parts.append("")
    guidance_parts.append(when_to_use)
    guidance_parts.append("")

    # Full Documentation reference
    guidance_parts.append("## Full Documentation")
    guidance_parts.append("")
    guidance_parts.append("For detailed examples and best practices, see:")
    guidance_parts.append(f"- Agent: `agents/{agent_name}.md`")
    guidance_parts.append(f"- Extended: `agents/{agent_name}-ext.md`")

    guidance_content = '\n'.join(guidance_parts)

    # Validate size
    warnings = validate_guidance_size(guidance_content, agent_name)
    if warnings:
        # Log warnings (in practice, would use logging module)
        for warning in warnings:
            print(f"Warning: {warning}")

    return guidance_content


def save_guidance(content: str, output_dir: str, agent_name: str) -> Path:
    """
    Save guidance content to file.

    Args:
        content: Guidance file content
        output_dir: Output directory path (e.g., '.claude/rules/guidance/')
        agent_name: Agent name for filename (e.g., 'api-specialist')

    Returns:
        Path to saved guidance file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Derive guidance filename from agent name
    # Convert 'api-specialist' -> 'api.md' or keep full name
    guidance_name = agent_name.replace("-specialist", "")
    guidance_file = output_path / f"{guidance_name}.md"

    guidance_file.write_text(content, encoding='utf-8')

    return guidance_file
