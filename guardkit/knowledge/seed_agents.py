"""
Agents seeding for GuardKit knowledge graph.

Seeds agent content by reading actual .md files from template directories
(both agents/ and .claude/agents/) for rich, queryable content in the
knowledge graph. Skips -ext.md supplementary files.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)

# 10KB threshold for chunking
_CHUNK_THRESHOLD = 10 * 1024


def _get_templates_dir() -> Path:
    """Locate the installer/core/templates/ directory.

    Returns:
        Path to installer/core/templates/ directory.
    """
    current = Path(__file__).resolve().parent
    while current != current.parent:
        candidate = current / "installer" / "core" / "templates"
        if candidate.is_dir():
            return candidate
        current = current.parent
    return Path.cwd() / "installer" / "core" / "templates"


def _discover_agent_files(template_dir: Path) -> list[Path]:
    """Discover agent .md files in a template directory.

    Checks both agents/ and .claude/agents/ directories.
    Skips -ext.md supplementary files.

    Args:
        template_dir: Path to a specific template directory.

    Returns:
        Sorted list of agent .md file paths.
    """
    agent_files: list[Path] = []

    # Check both possible agent directories
    agent_dirs = [
        template_dir / "agents",
        template_dir / ".claude" / "agents",
    ]

    for agents_dir in agent_dirs:
        if not agents_dir.is_dir():
            continue
        for md_file in sorted(agents_dir.glob("*.md")):
            # Skip -ext.md supplementary files
            if md_file.stem.endswith("-ext"):
                continue
            agent_files.append(md_file)

    return agent_files


def _parse_yaml_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown file content.

    Returns:
        Tuple of (frontmatter_dict, body_text).
    """
    if not content.startswith("---"):
        return {}, content

    # Find closing --- delimiter
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return {}, content

    frontmatter_text = content[3:3 + end_match.start()]
    body = content[3 + end_match.end():]

    # Simple YAML parsing for common frontmatter fields
    metadata: dict[str, Any] = {}
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Handle list values in brackets
            if value.startswith("[") and value.endswith("]"):
                items = [
                    item.strip().strip("\"'")
                    for item in value[1:-1].split(",")
                    if item.strip()
                ]
                metadata[key] = items
            elif value.startswith('"') and value.endswith('"'):
                metadata[key] = value[1:-1]
            elif value == "true":
                metadata[key] = True
            elif value == "false":
                metadata[key] = False
            elif value.isdigit():
                metadata[key] = int(value)
            elif value:
                metadata[key] = value

    return metadata, body.strip()


def _read_agent_content(file_path: Path) -> Optional[dict[str, Any]]:
    """Read and parse an agent .md file.

    Args:
        file_path: Path to the agent markdown file.

    Returns:
        Dict with parsed agent data, or None if file cannot be read.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning(f"Cannot read agent file {file_path}: {e}")
        return None

    if not content.strip():
        logger.warning(f"Empty agent file: {file_path}")
        return None

    frontmatter, body = _parse_yaml_frontmatter(content)

    return {
        "frontmatter": frontmatter,
        "body": body,
        "file_path": str(file_path),
        "file_size": len(content.encode("utf-8")),
    }


def _build_agent_episode(
    template_id: str,
    agent_file: Path,
    parsed: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Build an episode tuple from parsed agent data.

    Args:
        template_id: ID of the template this agent belongs to.
        agent_file: Path to the agent file.
        parsed: Dict with frontmatter, body, file_path, file_size.

    Returns:
        Tuple of (episode_name, episode_body_dict).
    """
    agent_name = agent_file.stem
    episode_name = f"agent_{template_id}_{agent_name}".replace("-", "_")

    frontmatter = parsed.get("frontmatter", {})
    body = parsed.get("body", "")

    episode_body: dict[str, Any] = {
        "entity_type": "agent",
        "id": f"{template_id}/{agent_name}",
        "template_id": template_id,
        "name": frontmatter.get("name", agent_name),
        "description": frontmatter.get("description", ""),
        "capabilities": frontmatter.get("capabilities", []),
        "technologies": frontmatter.get("technologies", []),
        "stack": frontmatter.get("stack", []),
        "phase": frontmatter.get("phase", ""),
        "content": body,
    }

    return (episode_name, episode_body)


async def seed_agents(client, template_filter: set[str] | None = None) -> None:
    """Seed agent content by reading actual .md files from templates.

    Discovers agent files across all templates (checking both agents/ and
    .claude/agents/ directories), reads their content including YAML
    frontmatter, and creates episodes with the full body text.

    Skips -ext.md supplementary files. Files under 10KB are single episodes;
    larger files would be chunked (all non-ext agents are currently <10KB).

    Args:
        client: GraphitiClient instance
        template_filter: If provided, only seed agents from templates
            whose ID is in this set (e.g., {"fastapi-python", "default"}).
    """
    if not client or not client.enabled:
        return

    templates_dir = _get_templates_dir()
    if not templates_dir.is_dir():
        logger.warning(f"Templates directory not found: {templates_dir}")
        return

    episodes: list[tuple[str, dict[str, Any]]] = []

    for template_entry in sorted(templates_dir.iterdir()):
        if not template_entry.is_dir() or template_entry.name.startswith("."):
            continue

        template_id = template_entry.name
        if template_filter and template_id not in template_filter:
            continue
        agent_files = _discover_agent_files(template_entry)

        for agent_file in agent_files:
            parsed = _read_agent_content(agent_file)
            if parsed is None:
                continue

            episode = _build_agent_episode(template_id, agent_file, parsed)
            episodes.append(episode)

    if not episodes:
        logger.warning("No agent files discovered for seeding")
        return

    logger.info(f"Seeding {len(episodes)} agents from {templates_dir}")
    return await _add_episodes(client, episodes, "agents", "agents", entity_type="agent")
