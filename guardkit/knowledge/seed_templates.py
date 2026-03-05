"""
Templates seeding for GuardKit knowledge graph.

Seeds template metadata by reading actual manifest.json files from
installer/core/templates/ for rich, queryable content in the knowledge graph.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


def _get_templates_dir() -> Path:
    """Locate the installer/core/templates/ directory.

    Walks up from this file to find the project root, then resolves the
    templates directory.

    Returns:
        Path to installer/core/templates/ directory.
    """
    # Walk up from guardkit/knowledge/seed_templates.py to project root
    current = Path(__file__).resolve().parent
    while current != current.parent:
        candidate = current / "installer" / "core" / "templates"
        if candidate.is_dir():
            return candidate
        current = current.parent
    # Fallback: relative to cwd
    return Path.cwd() / "installer" / "core" / "templates"


def _discover_templates(templates_dir: Path) -> list[dict[str, Any]]:
    """Discover all template directories and read their manifests.

    Scans the given directory for template subdirectories. For each template:
    - Reads manifest.json if it exists
    - Falls back to directory name as template ID if manifest is missing

    Args:
        templates_dir: Path to the templates root directory.

    Returns:
        List of dicts with template_id and manifest data.
    """
    templates: list[dict[str, Any]] = []

    if not templates_dir.is_dir():
        logger.warning(f"Templates directory not found: {templates_dir}")
        return templates

    for entry in sorted(templates_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        template_info: dict[str, Any] = {"template_id": entry.name}
        manifest_path = entry / "manifest.json"

        if manifest_path.is_file():
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                template_info["manifest"] = manifest_data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    f"Failed to read manifest for template '{entry.name}': {e}"
                )
                template_info["manifest"] = {}
        else:
            logger.debug(
                f"No manifest.json for template '{entry.name}', "
                "using directory name as ID"
            )
            template_info["manifest"] = {}

        templates.append(template_info)

    return templates


def _build_template_episode(template_info: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Build an episode tuple from template discovery data.

    Args:
        template_info: Dict with template_id and optional manifest data.

    Returns:
        Tuple of (episode_name, episode_body_dict).
    """
    template_id = template_info["template_id"]
    manifest = template_info.get("manifest", {})

    episode_name = f"template_{template_id.replace('-', '_')}"

    body: dict[str, Any] = {
        "entity_type": "template",
        "id": template_id,
    }

    if manifest:
        # Use actual manifest content for rich episode data
        body["name"] = manifest.get("display_name", manifest.get("name", template_id))
        body["description"] = manifest.get("description", "")
        body["language"] = manifest.get("language", "")
        body["version"] = manifest.get("version", "")
        body["architecture"] = manifest.get("architecture", "")

        # Include frameworks list
        frameworks = manifest.get("frameworks", [])
        body["frameworks"] = [
            fw.get("name", "") if isinstance(fw, dict) else fw
            for fw in frameworks
        ]

        body["patterns"] = manifest.get("patterns", [])
        body["layers"] = manifest.get("layers", [])
        body["tags"] = manifest.get("tags", [])
        body["category"] = manifest.get("category", "")
        body["complexity"] = manifest.get("complexity", 0)
        body["production_ready"] = manifest.get("production_ready", False)
        body["quality_scores"] = manifest.get("quality_scores", {})
    else:
        # Minimal episode for templates without manifest
        body["name"] = template_id
        body["description"] = f"Template: {template_id} (no manifest.json)"

    return (episode_name, body)


async def seed_templates(client) -> None:
    """Seed template metadata by reading actual manifest.json files.

    Discovers all templates in installer/core/templates/ and creates
    episodes from their manifest.json content for rich semantic search.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    templates_dir = _get_templates_dir()
    discovered = _discover_templates(templates_dir)

    if not discovered:
        logger.warning("No templates discovered for seeding")
        return

    episodes = [_build_template_episode(t) for t in discovered]

    logger.info(f"Seeding {len(episodes)} templates from {templates_dir}")
    return await _add_episodes(client, episodes, "templates", "templates", entity_type="template")
