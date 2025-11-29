"""
Agent Markdown Formatter

Formats agent dictionaries to markdown files with YAML frontmatter.

CRITICAL: Uses YAML list syntax for arrays (dash-prefixed lines).
NOT comma-separated, NOT JSON arrays.
"""


def format_agent_markdown(agent: dict) -> str:
    """
    Convert agent dict to markdown with YAML frontmatter.

    Args:
        agent: Dict with keys: name, description, reason, technologies, priority

    Returns:
        Markdown string with YAML frontmatter + body

    Example:
        >>> agent = {
        ...     'name': 'test-specialist',
        ...     'description': 'Test description',
        ...     'reason': 'Test reason',
        ...     'technologies': ['Python', 'pytest'],
        ...     'priority': 8
        ... }
        >>> result = format_agent_markdown(agent)
        >>> print(result[:50])
        ---
        name: test-specialist
        description: Test desc...
    """
    # Handle missing fields gracefully
    name = agent.get('name', 'unknown-agent')
    description = agent.get('description', '')
    reason = agent.get('reason', '')
    technologies = agent.get('technologies', [])
    priority = agent.get('priority', 5)

    # YAML frontmatter with YAML list syntax for technologies
    # CRITICAL: Use "  - {tech}" format (dash-prefixed lines)
    # NOT comma-separated like "technologies: Python, pytest"
    tech_list = '\n'.join(f"  - {tech}" for tech in technologies)

    frontmatter = f"""---
name: {name}
description: {description}
priority: {priority}
technologies:
{tech_list}
---

"""

    # Markdown body
    title = name.replace('-', ' ').title()
    tech_bullets = '\n'.join(f"- {tech}" for tech in technologies)

    body = f"""# {title}

## Purpose

{description}

## Why This Agent Exists

{reason}

## Technologies

{tech_bullets}

## Usage

This agent is automatically invoked during `/task-work` when working on {name.replace('-', ' ')} implementations.
"""

    return frontmatter + body
