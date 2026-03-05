"""
Rules seeding for GuardKit knowledge graph.

Seeds rule content by reading actual .md files from template rule directories
(.claude/rules/) for rich, queryable content in the knowledge graph.
Applies content chunking for files over 10KB.
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


def _discover_rule_files(template_dir: Path) -> list[Path]:
    """Discover rule .md files in a template directory.

    Recursively scans .claude/rules/ for all .md files.

    Args:
        template_dir: Path to a specific template directory.

    Returns:
        Sorted list of rule .md file paths.
    """
    rules_dir = template_dir / ".claude" / "rules"
    if not rules_dir.is_dir():
        return []

    return sorted(rules_dir.rglob("*.md"))


def _read_rule_content(file_path: Path) -> Optional[str]:
    """Read a rule .md file.

    Args:
        file_path: Path to the rule markdown file.

    Returns:
        File content as string, or None if unreadable.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        if not content.strip():
            logger.warning(f"Empty rule file: {file_path}")
            return None
        return content
    except OSError as e:
        logger.warning(f"Cannot read rule file {file_path}: {e}")
        return None


def _extract_title(content: str) -> Optional[str]:
    """Extract the first heading from markdown content.

    Args:
        content: Markdown text.

    Returns:
        Title text if found, None otherwise.
    """
    match = re.search(r"^#{1,2}\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _chunk_by_sections(content: str, document_title: str) -> list[dict[str, str]]:
    """Split content into chunks by ## (h2) headers.

    Args:
        content: Markdown content to chunk.
        document_title: Title for the introduction chunk.

    Returns:
        List of dicts with 'title' and 'content' keys.
    """
    header_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(header_pattern.finditer(content))

    if not matches:
        return [{"title": document_title, "content": content}]

    chunks: list[dict[str, str]] = []

    # Content before first h2
    first_header_pos = matches[0].start()
    if first_header_pos > 0:
        intro = content[:first_header_pos].strip()
        if intro:
            chunks.append({"title": f"{document_title} - Introduction", "content": intro})

    for i, match in enumerate(matches):
        section_title = match.group(1).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end].strip()
        chunks.append({
            "title": f"{document_title} - {section_title}",
            "content": section_content,
        })

    return chunks


def _build_rule_episodes(
    template_id: str,
    rule_file: Path,
    content: str,
) -> list[tuple[str, dict[str, Any]]]:
    """Build episode(s) from a rule file, applying chunking if needed.

    Files over 10KB are split by ## headers into multiple episodes.
    Files under 10KB produce a single episode.

    Args:
        template_id: ID of the template this rule belongs to.
        rule_file: Path to the rule file.
        content: File content.

    Returns:
        List of (episode_name, episode_body_dict) tuples.
    """
    # Compute rule ID from relative path within rules dir
    # e.g., .claude/rules/api/routing.md -> api/routing
    rules_dir = None
    for parent in rule_file.parents:
        if parent.name == "rules":
            rules_dir = parent
            break

    if rules_dir:
        relative = rule_file.relative_to(rules_dir)
        rule_id = str(relative.with_suffix(""))
    else:
        rule_id = rule_file.stem

    file_size = len(content.encode("utf-8"))
    title = _extract_title(content) or rule_file.stem

    base_name = f"rule_{template_id}_{rule_id}".replace("-", "_").replace("/", "_")

    if file_size > _CHUNK_THRESHOLD:
        # Chunk large files by ## headers
        chunks = _chunk_by_sections(content, title)
        if len(chunks) > 1:
            logger.debug(
                f"Chunking rule {rule_file.name} ({file_size} bytes) "
                f"into {len(chunks)} episodes"
            )
            episodes = []
            for i, chunk in enumerate(chunks):
                episode_name = f"{base_name}_chunk_{i}"
                body: dict[str, Any] = {
                    "entity_type": "rule",
                    "id": f"{template_id}/{rule_id}_chunk_{i}",
                    "template_id": template_id,
                    "name": chunk["title"],
                    "rule_path": str(rule_file),
                    "content": chunk["content"],
                    "chunk_index": i,
                    "chunk_total": len(chunks),
                }
                episodes.append((episode_name, body))
            return episodes

    # Single episode for the whole file
    body = {
        "entity_type": "rule",
        "id": f"{template_id}/{rule_id}",
        "template_id": template_id,
        "name": title,
        "rule_path": str(rule_file),
        "content": content,
    }
    return [(base_name, body)]


async def seed_rules(client) -> tuple[int, int]:
    """Seed rule content by reading actual .md files from templates.

    Discovers rule files across all templates in .claude/rules/,
    reads their full content, and creates episodes organized by template.
    Files over 10KB are chunked by ## headers for better queryability.

    Rules are batched per-template to reduce circuit breaker exposure.
    Each template's rules are seeded independently so that failures in
    one template don't block others.

    Args:
        client: GraphitiClient instance

    Returns:
        Tuple of (total_created, total_skipped) across all templates.
    """
    if not client or not client.enabled:
        return (0, 0)

    templates_dir = _get_templates_dir()
    if not templates_dir.is_dir():
        logger.warning(f"Templates directory not found: {templates_dir}")
        return (0, 0)

    # Group episodes by template for per-template batching
    episodes_by_template: dict[str, list[tuple[str, dict[str, Any]]]] = {}

    for template_entry in sorted(templates_dir.iterdir()):
        if not template_entry.is_dir() or template_entry.name.startswith("."):
            continue

        template_id = template_entry.name
        rule_files = _discover_rule_files(template_entry)

        for rule_file in rule_files:
            content = _read_rule_content(rule_file)
            if content is None:
                continue

            rule_episodes = _build_rule_episodes(template_id, rule_file, content)
            if rule_episodes:
                episodes_by_template.setdefault(template_id, []).extend(rule_episodes)

    if not episodes_by_template:
        logger.warning("No rule files discovered for seeding")
        return (0, 0)

    total_episodes = sum(len(eps) for eps in episodes_by_template.values())
    logger.info(
        f"Seeding {total_episodes} rule episodes from {len(episodes_by_template)} "
        f"templates in {templates_dir}"
    )

    total_created = 0
    total_skipped = 0

    for template_id, episodes in episodes_by_template.items():
        # Reset circuit breaker between templates so failures in one
        # template don't cascade to others
        if hasattr(client, "reset_circuit_breaker"):
            client.reset_circuit_breaker()

        group_id = f"rules_{template_id}"
        category_name = f"rules/{template_id}"

        created, skipped = await _add_episodes(
            client, episodes, group_id, category_name, entity_type="rule"
        )
        total_created += created
        total_skipped += skipped

        if skipped > 0:
            logger.warning(
                f"  rules/{template_id}: {created}/{created + skipped} episodes "
                f"({skipped} skipped)"
            )
        else:
            logger.info(f"  rules/{template_id}: {created} episodes")

    return (total_created, total_skipped)
