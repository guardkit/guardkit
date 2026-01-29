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
        logger.warning(f"Failed to parse agent frontmatter: {e}")
        return {}
    except Exception as e:
        logger.warning(f"Unexpected error extracting agent metadata: {e}")
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


def _extract_rule_content(content: str) -> str:
    """Extract main content from rule markdown (excluding frontmatter).

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


# ============================================================================
# TEMPLATE SYNC
# ============================================================================

async def sync_template_to_graphiti(template_path: Path) -> bool:
    """Sync template metadata to Graphiti after creation.

    Reads the template manifest.json and syncs:
    - Template metadata (name, language, frameworks, patterns)
    - All agents in the template's agents/ directory
    - All rules in the template's .claude/rules/ directory

    Args:
        template_path: Path to the template directory containing manifest.json

    Returns:
        True if sync successful, False if client disabled or error occurred.

    Example:
        from pathlib import Path
        success = await sync_template_to_graphiti(
            Path("installer/core/templates/fastapi-python")
        )
    """
    # Get Graphiti client
    client = get_graphiti()

    if not client:
        logger.warning("Template sync skipped: Graphiti client not initialized")
        return False

    if not client.enabled:
        logger.debug("Template sync skipped: Graphiti client disabled")
        return False

    # Check manifest exists
    manifest_path = template_path / "manifest.json"
    if not manifest_path.exists():
        logger.warning(f"Template sync failed: manifest.json not found at {manifest_path}")
        return False

    # Load manifest
    try:
        manifest_text = manifest_path.read_text()
        manifest = json.loads(manifest_text)
    except json.JSONDecodeError as e:
        logger.warning(f"Template sync failed: invalid JSON in manifest.json: {e}")
        return False
    except Exception as e:
        logger.warning(f"Template sync failed: could not read manifest.json: {e}")
        return False

    template_id = manifest.get('name', template_path.name)

    # Build template episode
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

    # Sync template to Graphiti
    try:
        await client.add_episode(
            name=f"template_{template_id}",
            episode_body=json.dumps(template_body),
            group_id="templates"
        )
        logger.info(f"Synced template '{template_id}' to Graphiti")
    except Exception as e:
        logger.warning(f"Failed to sync template to Graphiti: {e}")
        return False

    # Sync agents if agents/ directory exists
    agents_dir = template_path / "agents"
    if agents_dir.exists() and agents_dir.is_dir():
        for agent_file in agents_dir.glob("*.md"):
            # Skip extended files (they're supplementary)
            if "-ext.md" in agent_file.name:
                continue
            try:
                await sync_agent_to_graphiti(agent_file, template_id)
            except Exception as e:
                logger.warning(f"Failed to sync agent {agent_file.name}: {e}")

    # Sync rules if .claude/rules/ directory exists
    rules_dir = template_path / ".claude" / "rules"
    if rules_dir.exists() and rules_dir.is_dir():
        for rule_file in rules_dir.rglob("*.md"):
            try:
                await sync_rule_to_graphiti(rule_file, template_id)
            except Exception as e:
                logger.warning(f"Failed to sync rule {rule_file.name}: {e}")

    return True


# ============================================================================
# AGENT SYNC
# ============================================================================

async def sync_agent_to_graphiti(agent_path: Path, template_id: str) -> bool:
    """Sync agent metadata to Graphiti.

    Extracts metadata from agent markdown frontmatter and creates
    an episode in Graphiti for semantic search.

    Args:
        agent_path: Path to the agent markdown file
        template_id: ID of the parent template

    Returns:
        True if sync successful, False if client disabled or error occurred.

    Example:
        success = await sync_agent_to_graphiti(
            Path("installer/core/templates/fastapi-python/agents/fastapi-specialist.md"),
            "fastapi-python"
        )
    """
    # Get Graphiti client
    client = get_graphiti()

    if not client:
        logger.warning("Agent sync skipped: Graphiti client not initialized")
        return False

    if not client.enabled:
        logger.debug("Agent sync skipped: Graphiti client disabled")
        return False

    # Check file exists
    if not agent_path.exists():
        logger.warning(f"Agent sync failed: file not found at {agent_path}")
        return False

    # Read and parse agent content
    try:
        content = agent_path.read_text()
    except Exception as e:
        logger.warning(f"Agent sync failed: could not read {agent_path}: {e}")
        return False

    metadata = extract_agent_metadata(content)

    if not metadata:
        logger.warning(f"Agent sync skipped: no metadata found in {agent_path}")
        return False

    agent_name = metadata.get('name', agent_path.stem)

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
    }

    # Sync agent to Graphiti
    try:
        await client.add_episode(
            name=f"agent_{template_id}_{agent_name}",
            episode_body=json.dumps(agent_body),
            group_id="agents"
        )
        logger.info(f"Synced agent '{agent_name}' to Graphiti")
        return True
    except Exception as e:
        logger.warning(f"Failed to sync agent to Graphiti: {e}")
        return False


# ============================================================================
# RULE SYNC
# ============================================================================

async def sync_rule_to_graphiti(rule_path: Path, template_id: str) -> bool:
    """Sync rule metadata to Graphiti.

    Extracts metadata from rule markdown frontmatter and creates
    an episode in Graphiti for semantic search.

    Args:
        rule_path: Path to the rule markdown file
        template_id: ID of the parent template

    Returns:
        True if sync successful, False if client disabled or error occurred.

    Example:
        success = await sync_rule_to_graphiti(
            Path("installer/core/templates/fastapi-python/.claude/rules/code-style.md"),
            "fastapi-python"
        )
    """
    # Get Graphiti client
    client = get_graphiti()

    if not client:
        logger.warning("Rule sync skipped: Graphiti client not initialized")
        return False

    if not client.enabled:
        logger.debug("Rule sync skipped: Graphiti client disabled")
        return False

    # Check file exists
    if not rule_path.exists():
        logger.warning(f"Rule sync failed: file not found at {rule_path}")
        return False

    # Read and parse rule content
    try:
        content = rule_path.read_text()
    except Exception as e:
        logger.warning(f"Rule sync failed: could not read {rule_path}: {e}")
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

    # Build rule episode
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
        await client.add_episode(
            name=f"rule_{template_id}_{rule_name}",
            episode_body=json.dumps(rule_body),
            group_id="rules"
        )
        logger.info(f"Synced rule '{rule_name}' to Graphiti")
        return True
    except Exception as e:
        logger.warning(f"Failed to sync rule to Graphiti: {e}")
        return False
