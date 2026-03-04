"""
Template and Agent sync module for GuardKit knowledge graph.

Syncs template and agent metadata to Graphiti after `/template-create`
and `/agent-enhance` commands. This enables semantic search over:
- Template capabilities and languages
- Agent capabilities and technologies
- Rule applicability and path patterns

Usage:
    from guardkit.knowledge.template_sync import sync_template_to_graphiti
    from pathlib import Path

    await sync_template_to_graphiti(Path("installer/core/templates/fastapi-python"))

Patterns Used (following seeding.py conventions):
    - Use `get_graphiti()` singleton to get client
    - Use `client.add_episode()` to add entities
    - Use `json.dumps()` for episode_body
    - Group entities with `group_id` parameter
    - Gracefully handle disabled client (check `if not client.enabled: return`)
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

import yaml

from guardkit.knowledge.graphiti_client import get_graphiti

logger = logging.getLogger(__name__)


# ============================================================================
# METADATA EXTRACTION
# ============================================================================

def extract_agent_metadata(content: str) -> Dict[str, Any]:
    """Extract metadata from agent markdown frontmatter.

    Parses YAML frontmatter between --- delimiters at the start of
    markdown content.

    Args:
        content: Full markdown content including frontmatter

    Returns:
        Dictionary of extracted metadata fields.
        Empty dict if no frontmatter found or parsing fails.

    Example:
        content = '''---
        name: test-agent
        capabilities:
          - Code review
        ---
        # Content
        '''
        metadata = extract_agent_metadata(content)
        # {'name': 'test-agent', 'capabilities': ['Code review']}
    """
    if not content or not content.strip().startswith('---'):
        return {}

    try:
        # Find the frontmatter section between --- delimiters
        pattern = r'^---\s*\n(.*?)\n---'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return {}

        frontmatter_text = match.group(1)

        # Parse YAML
        metadata = yaml.safe_load(frontmatter_text)

        if metadata is None:
            return {}

        return metadata if isinstance(metadata, dict) else {}

    except yaml.YAMLError as e:
        logger.warning(f"[Graphiti] Failed to parse agent frontmatter: {e}")
        return {}
    except Exception as e:
        logger.warning(f"[Graphiti] Unexpected error extracting agent metadata: {e}")
        return {}


def _extract_rule_metadata(content: str) -> Dict[str, Any]:
    """Extract metadata from rule markdown frontmatter.

    Similar to agent metadata but focuses on path patterns.

    Args:
        content: Full markdown content including frontmatter

    Returns:
        Dictionary of extracted metadata fields.
        Empty dict if no frontmatter found or parsing fails.
    """
    return extract_agent_metadata(content)


def _extract_body_content(content: str) -> str:
    """Extract main content from markdown (excluding frontmatter).

    Works for both agent and rule files. Returns everything after
    the YAML frontmatter delimiters (---).

    Args:
        content: Full markdown content including frontmatter

    Returns:
        Content after frontmatter, or full content if no frontmatter
    """
    if not content or not content.strip().startswith('---'):
        return content

    # Find end of frontmatter
    pattern = r'^---\s*\n.*?\n---\s*\n?'
    match = re.match(pattern, content, re.DOTALL)

    if match:
        return content[match.end():].strip()

    return content


def _extract_rule_content(content: str) -> str:
    """Extract main content from rule markdown (excluding frontmatter).

    Args:
        content: Full markdown content including frontmatter

    Returns:
        Content after frontmatter, or full content if no frontmatter
    """
    return _extract_body_content(content)


# ============================================================================
# TEMPLATE SYNC
# ============================================================================

async def sync_template_to_graphiti(template_path: Path, client=None) -> bool:
    """Sync template metadata to Graphiti after creation.

    Reads the template manifest.json (if present) and syncs:
    - Template metadata (name, language, frameworks, patterns) — from manifest
    - All agents in the template's agents/ and .claude/agents/ directories
    - All rules in the template's .claude/rules/ directory

    If manifest.json is absent (e.g., the 'default' template), agents and rules
    are still synced using the directory name as the template_id.

    Args:
        template_path: Path to the template directory
        client: Optional pre-connected GraphitiClient. Falls back to
            get_graphiti() when not provided (for non-init callers).

    Returns:
        True if sync successful, False if client disabled or error occurred.

    Example:
        from pathlib import Path
        success = await sync_template_to_graphiti(
            Path("installer/core/templates/fastapi-python")
        )
    """
    # Get Graphiti client — prefer passed client, fall back to singleton
    if client is None:
        client = get_graphiti()

    if not client:
        logger.warning("[Graphiti] Template sync skipped: client unavailable")
        return False

    if not client.enabled:
        logger.debug("[Graphiti] Template sync skipped: client disabled")
        return False

    # Suppress FalkorDB driver ERROR logs during sync — they dump full
    # 768-dimensional embedding vectors on query failure, producing ~120KB
    # of unreadable noise.  GuardKit's own retry WARNINGs remain visible.
    falkordb_logger = logging.getLogger("graphiti_core.driver.falkordb_driver")
    original_level = falkordb_logger.level
    falkordb_logger.setLevel(logging.WARNING)

    try:
        start_time = time.monotonic()
        template_count = 0
        agent_count = 0
        rule_count = 0
        warning_count = 0

        # Load manifest if it exists (no longer required)
        manifest: Optional[Dict[str, Any]] = None
        manifest_path = template_path / "manifest.json"
        if manifest_path.exists():
            try:
                manifest_text = manifest_path.read_text()
                manifest = json.loads(manifest_text)
            except json.JSONDecodeError as e:
                logger.warning(f"[Graphiti] Invalid JSON in manifest.json: {e}")
                warning_count += 1
                manifest = None
            except Exception as e:
                logger.warning(f"[Graphiti] Could not read manifest.json: {e}")
                warning_count += 1
                manifest = None

        # Determine template_id from manifest or directory name
        template_id = template_path.name
        if manifest:
            template_id = manifest.get('name', template_path.name)

        # Sync manifest metadata if available
        if manifest:
            template_body = {
                "entity_type": "template",
                "id": template_id,
                "name": manifest.get('display_name', template_id),
                "description": manifest.get('description', ''),
                "language": manifest.get('language', 'Unknown'),
                "frameworks": [
                    f.get('name') if isinstance(f, dict) else str(f)
                    for f in manifest.get('frameworks', [])
                ],
                "patterns": manifest.get('patterns', []),
                "tags": manifest.get('tags', []),
                "complexity": manifest.get('complexity', 5),
                "production_ready": manifest.get('production_ready', False),
            }

            try:
                await client.add_episode(
                    name=f"template_{template_id}",
                    episode_body=json.dumps(template_body),
                    group_id="templates",
                    source="template_sync",
                    entity_type="template"
                )
                logger.info(f"[Graphiti] Synced template '{template_id}'")
                template_count += 1
            except Exception as e:
                logger.warning(f"[Graphiti] Failed to sync template '{template_id}': {e}")
                warning_count += 1
                return False
        else:
            logger.info(f"[Graphiti] No manifest.json found for '{template_id}', syncing agents and rules only")

        # Sync agents from both agents/ and .claude/agents/ directories
        agent_dirs: List[Path] = []
        top_agents = template_path / "agents"
        dotclaude_agents = template_path / ".claude" / "agents"

        if top_agents.exists() and top_agents.is_dir():
            agent_dirs.append(top_agents)
        if dotclaude_agents.exists() and dotclaude_agents.is_dir():
            agent_dirs.append(dotclaude_agents)

        for agents_dir in agent_dirs:
            for agent_file in agents_dir.glob("*.md"):
                # Skip extended files (they're supplementary)
                if "-ext.md" in agent_file.name:
                    continue
                try:
                    result = await sync_agent_to_graphiti(agent_file, template_id, client=client)
                    if result:
                        agent_count += 1
                except Exception as e:
                    logger.warning(f"[Graphiti] Failed to sync agent {agent_file.name}: {e}")
                    warning_count += 1

        # Sync rules if .claude/rules/ directory exists
        rules_dir = template_path / ".claude" / "rules"
        if rules_dir.exists() and rules_dir.is_dir():
            for rule_file in rules_dir.rglob("*.md"):
                try:
                    result = await sync_rule_to_graphiti(rule_file, template_id, client=client)
                    if result:
                        rule_count += 1
                except Exception as e:
                    logger.warning(f"[Graphiti] Failed to sync rule {rule_file.name}: {e}")
                    warning_count += 1

        elapsed = time.monotonic() - start_time
        summary_parts = []
        if template_count:
            summary_parts.append(f"{template_count} template")
        summary_parts.append(f"{agent_count} agents")
        summary_parts.append(f"{rule_count} rules")
        summary = ", ".join(summary_parts)
        warning_suffix = f", {warning_count} warnings" if warning_count else ""
        logger.info(
            f"[Graphiti] Template sync complete: {summary} synced"
            f" ({elapsed:.1f}s){warning_suffix}"
        )

        return True
    finally:
        falkordb_logger.setLevel(original_level)


# ============================================================================
# AGENT SYNC
# ============================================================================

async def sync_agent_to_graphiti(agent_path: Path, template_id: str, client=None) -> bool:
    """Sync agent metadata to Graphiti.

    Extracts metadata from agent markdown frontmatter and creates
    an episode in Graphiti for semantic search.

    Args:
        agent_path: Path to the agent markdown file
        template_id: ID of the parent template
        client: Optional pre-connected GraphitiClient. Falls back to
            get_graphiti() when not provided.

    Returns:
        True if sync successful, False if client disabled or error occurred.

    Example:
        success = await sync_agent_to_graphiti(
            Path("installer/core/templates/fastapi-python/agents/fastapi-specialist.md"),
            "fastapi-python"
        )
    """
    # Get Graphiti client — prefer passed client, fall back to singleton
    if client is None:
        client = get_graphiti()

    if not client:
        logger.warning("[Graphiti] Agent sync skipped: client unavailable")
        return False

    if not client.enabled:
        logger.debug("[Graphiti] Agent sync skipped: client disabled")
        return False

    # Check file exists
    if not agent_path.exists():
        logger.warning(f"[Graphiti] Agent sync failed: file not found at {agent_path}")
        return False

    # Read and parse agent content
    try:
        content = agent_path.read_text()
    except Exception as e:
        logger.warning(f"[Graphiti] Agent sync failed: could not read {agent_path}: {e}")
        return False

    metadata = extract_agent_metadata(content)

    if not metadata:
        logger.warning(f"[Graphiti] Agent sync skipped: no metadata found in {agent_path}")
        return False

    agent_name = metadata.get('name', agent_path.stem)

    # Extract body content (everything after frontmatter)
    body_text = _extract_body_content(content)

    # Build agent episode
    agent_body = {
        "entity_type": "agent",
        "id": agent_name,
        "name": metadata.get('name', agent_name),
        "description": metadata.get('description', ''),
        "template_id": template_id,
        "capabilities": metadata.get('capabilities', []),
        "technologies": metadata.get('technologies', []),
        "stack": metadata.get('stack', []),
        "phase": metadata.get('phase', ''),
        "priority": metadata.get('priority', 5),
        "collaborates_with": metadata.get('collaborates_with', []),
        "keywords": metadata.get('keywords', []),
        "content_preview": body_text[:500] if body_text else "",
    }

    # Sync agent to Graphiti
    try:
        result = await client.add_episode(
            name=f"agent_{template_id}_{agent_name}",
            episode_body=json.dumps(agent_body),
            group_id="agents",
            source="template_sync",
            entity_type="agent"
        )
        if result is None:
            logger.warning(f"[Graphiti] Failed to sync agent '{agent_name}' (episode creation returned None)")
            return False
        logger.info(f"[Graphiti] Synced agent '{agent_name}'")
        return True
    except Exception as e:
        logger.warning(f"[Graphiti] Failed to sync agent '{agent_name}': {e}")
        return False


# ============================================================================
# RULE SYNC
# ============================================================================

async def sync_rule_to_graphiti(rule_path: Path, template_id: str, client=None) -> bool:
    """Sync rule metadata to Graphiti.

    Extracts metadata from rule markdown frontmatter and creates
    an episode in Graphiti for semantic search.

    Args:
        rule_path: Path to the rule markdown file
        template_id: ID of the parent template
        client: Optional pre-connected GraphitiClient. Falls back to
            get_graphiti() when not provided.

    Returns:
        True if sync successful, False if client disabled or error occurred.

    Example:
        success = await sync_rule_to_graphiti(
            Path("installer/core/templates/fastapi-python/.claude/rules/code-style.md"),
            "fastapi-python"
        )
    """
    # Get Graphiti client — prefer passed client, fall back to singleton
    if client is None:
        client = get_graphiti()

    if not client:
        logger.warning("[Graphiti] Rule sync skipped: client unavailable")
        return False

    if not client.enabled:
        logger.debug("[Graphiti] Rule sync skipped: client disabled")
        return False

    # Check file exists
    if not rule_path.exists():
        logger.warning(f"[Graphiti] Rule sync failed: file not found at {rule_path}")
        return False

    # Read and parse rule content
    try:
        content = rule_path.read_text()
    except Exception as e:
        logger.warning(f"[Graphiti] Rule sync failed: could not read {rule_path}: {e}")
        return False

    metadata = _extract_rule_metadata(content)
    main_content = _extract_rule_content(content)

    rule_name = rule_path.stem

    # Parse path patterns from frontmatter
    paths_raw = metadata.get('paths', '')
    if isinstance(paths_raw, str):
        path_patterns = [p.strip() for p in paths_raw.split(',') if p.strip()]
    elif isinstance(paths_raw, list):
        path_patterns = paths_raw
    else:
        path_patterns = []

    # Extract topics from headings in content
    topics = []
    for line in main_content.split('\n'):
        if line.startswith('# '):
            topics.append(line[2:].strip())
        elif line.startswith('## '):
            topics.append(line[3:].strip())

    # Build rule episode (content_preview only - full content served via .claude/rules/*.md)
    rule_body = {
        "entity_type": "rule",
        "id": f"{template_id}_{rule_name}",
        "name": rule_name,
        "template_id": template_id,
        "path_patterns": path_patterns,
        "topics": topics[:10],  # Limit to first 10 topics
        "content_preview": main_content[:500] if main_content else "",
    }

    # Sync rule to Graphiti
    try:
        result = await client.add_episode(
            name=f"rule_{template_id}_{rule_name}",
            episode_body=json.dumps(rule_body),
            group_id="rules",
            source="template_sync",
            entity_type="rule"
        )
        if result is None:
            logger.warning(f"[Graphiti] Failed to sync rule '{rule_name}' (episode creation returned None)")
            return False
        logger.info(f"[Graphiti] Synced rule '{rule_name}'")
        return True
    except Exception as e:
        logger.warning(f"[Graphiti] Failed to sync rule '{rule_name}': {e}")
        return False
