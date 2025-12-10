"""
Agent Discovery Module for AI-Powered Agent Selection.

This module provides agent discovery functionality that matches task context
to appropriate specialist agents using metadata (stack, phase, capabilities, keywords).
It replaces hardcoded mappings with intelligent discovery, maintaining GuardKit's
AI-first philosophy.

Task Reference: TASK-HAI-005-7A2E
Epic: haiku-agent-implementation

Algorithm Phases:
1. Scan all agent locations (global + template agents)
2. Extract metadata from frontmatter
3. Apply filters (phase, stack, keywords)
4. Sort by relevance and return

Design Principles:
- Graceful degradation: Skip agents without metadata (no errors)
- Opt-in discovery: Only agents WITH phase field are discoverable
- AI-friendly: Keywords enable semantic matching
- Future-proof: Extensible to new stacks/phases
"""

import glob as glob_module
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import frontmatter, fall back to regex parsing if not available
try:
    import frontmatter
    HAS_FRONTMATTER = True
except ImportError:
    HAS_FRONTMATTER = False

logger = logging.getLogger(__name__)

# Priority constants for agent source precedence
# Lower number = higher priority (local overrides global)
PRIORITY_LOCAL = 1     # .claude/agents/ (highest priority)
PRIORITY_USER = 2      # ~/.agentecflow/agents/
PRIORITY_GLOBAL = 3    # installer/core/agents/
PRIORITY_TEMPLATE = 4  # installer/core/templates/*/agents/ (lowest priority)

# Valid values for validation
VALID_STACKS = [
    'python', 'react', 'dotnet', 'typescript', 'javascript',
    'go', 'rust', 'java', 'ruby', 'php', 'cross-stack', 'csharp'
]
VALID_PHASES = ['implementation', 'review', 'testing', 'orchestration']


def _get_agent_locations() -> List[tuple[Path, str, int]]:
    """
    Get all locations where agents may be stored with precedence information.

    Returns:
        List of tuples: (directory_path, source_name, priority)
        Priority: 1=local (highest), 2=user, 3=global, 4=template (lowest)
    """
    locations = []

    # 1. Project-local agents (.claude/agents/) - HIGHEST PRIORITY
    cwd = Path.cwd()
    local_agents = cwd / ".claude" / "agents"
    if local_agents.exists():
        locations.append((local_agents, "local", PRIORITY_LOCAL))
    else:
        logger.debug(".claude/agents/ not found, skipping local agent scan")

    # 2. Global user agents (~/.agentecflow/agents/)
    home = Path.home()
    user_agents = home / ".agentecflow" / "agents"
    if user_agents.exists():
        locations.append((user_agents, "user", PRIORITY_USER))

    # 3. Global installer agents (installer/core/agents/)
    # Find the project root by looking for installer/core/agents
    current = Path(__file__).resolve()
    for parent in current.parents:
        installer_agents = parent / "installer" / "global" / "agents"
        if installer_agents.exists():
            locations.append((installer_agents, "global", PRIORITY_GLOBAL))

            # 4. Template agents from templates/*/agents/ - LOWEST PRIORITY
            templates_path = parent / "installer" / "global" / "templates"
            if templates_path.exists():
                for template_dir in templates_path.iterdir():
                    if template_dir.is_dir():
                        template_agents = template_dir / "agents"
                        if template_agents.exists():
                            template_name = template_dir.name
                            locations.append((template_agents, f"template:{template_name}", PRIORITY_TEMPLATE))
            break

    return locations


def _scan_agent_locations() -> List[tuple[Path, str, int]]:
    """
    Scan all agent locations for markdown files with precedence tracking.

    Returns:
        List of tuples: (agent_path, source_name, priority)
        Duplicates removed based on agent name, keeping highest priority source.
    """
    # Dictionary to track agents by name: name -> (path, source, priority)
    agents_by_name = {}

    locations = _get_agent_locations()

    for item in locations:
        # Handle both tuple format (new) and Path format (old/testing)
        if isinstance(item, tuple):
            location, source, priority = item
        else:
            # Backward compatibility for tests that mock with Path objects
            location = item
            source = "unknown"
            priority = PRIORITY_GLOBAL  # Default priority for legacy format

        try:
            pattern = str(location / "*.md")
            matches = glob_module.glob(pattern)

            for match_path in matches:
                path = Path(match_path)
                # Extract agent name from filename (without .md extension)
                agent_name = path.stem

                # Only add if not already found, or if this source has higher priority
                if agent_name not in agents_by_name:
                    agents_by_name[agent_name] = (path, source, priority)
                elif priority < agents_by_name[agent_name][2]:
                    # Lower priority number = higher precedence
                    old_source = agents_by_name[agent_name][1]
                    logger.debug(
                        f"Agent '{agent_name}' found in {source} (priority {priority}), "
                        f"overriding {old_source} (priority {agents_by_name[agent_name][2]})"
                    )
                    agents_by_name[agent_name] = (path, source, priority)

        except Exception as e:
            logger.warning(f"Failed to scan agent location {location}: {e}")
            continue

    # Return list of (path, source, priority) tuples
    return list(agents_by_name.values())


def _parse_frontmatter_regex(content: str) -> Dict[str, Any]:
    """
    Parse YAML frontmatter using regex (fallback when frontmatter not installed).

    Args:
        content: File content with potential frontmatter

    Returns:
        Dictionary of parsed frontmatter values
    """
    metadata = {}

    # Check for frontmatter delimiters
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return metadata

    frontmatter_text = match.group(1)

    # Parse simple key: value pairs
    for line in frontmatter_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Handle key: value
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()

            # Skip if it's a multi-line value starter
            if not value:
                continue

            # Handle array syntax [item1, item2]
            if value.startswith('[') and value.endswith(']'):
                items = value[1:-1].split(',')
                metadata[key] = [item.strip().strip('"\'') for item in items if item.strip()]
            else:
                # Simple string value
                metadata[key] = value.strip('"\'')

    return metadata


def _extract_metadata(agent_path: Path, source: str = None, priority: int = None) -> Optional[Dict[str, Any]]:
    """
    Extract discovery metadata from agent file.

    Args:
        agent_path: Path to agent markdown file
        source: Source location name (local, user, global, template:name)
        priority: Priority level (1=highest, 4=lowest)

    Returns:
        Dictionary with metadata or None if file can't be read
    """
    try:
        content = agent_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.warning(f"Failed to read agent file {agent_path}: {e}")
        return None

    # Parse frontmatter
    if HAS_FRONTMATTER:
        try:
            parsed = frontmatter.loads(content)
            metadata = dict(parsed.metadata)
        except Exception as e:
            logger.warning(f"Failed to parse frontmatter for {agent_path}: {e}")
            metadata = _parse_frontmatter_regex(content)
    else:
        metadata = _parse_frontmatter_regex(content)

    # Add path and source to metadata
    metadata['path'] = str(agent_path)
    if source is not None:
        metadata['source'] = source
    if priority is not None:
        metadata['source_priority'] = priority

    return metadata


def _matches_criteria(
    metadata: Dict[str, Any],
    phase: str,
    stack: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    min_capability_match: int = 1
) -> bool:
    """
    Check if agent metadata matches the discovery criteria.

    Args:
        metadata: Agent metadata dictionary
        phase: Required phase filter
        stack: Optional stack filter list
        keywords: Optional keyword list for scoring
        min_capability_match: Minimum keyword matches required

    Returns:
        True if agent matches criteria
    """
    # Phase filter (required, strict)
    agent_phase = metadata.get('phase')
    if not agent_phase or not isinstance(agent_phase, str):
        return False
    if agent_phase.lower() != phase.lower():
        return False

    # Stack filter (optional)
    if stack:
        agent_stacks = metadata.get('stack', [])
        if isinstance(agent_stacks, str):
            agent_stacks = [agent_stacks]
        elif not isinstance(agent_stacks, list):
            agent_stacks = []

        # Normalize to lowercase for comparison (only string items)
        agent_stacks_lower = [str(s).lower() for s in agent_stacks if s is not None]
        stack_lower = [str(s).lower() for s in stack if s is not None]

        # Check for 'cross-stack' (matches all)
        if 'cross-stack' not in agent_stacks_lower:
            # Must have at least one matching stack
            if not any(s in agent_stacks_lower for s in stack_lower):
                return False

    # Keyword scoring (optional)
    if keywords:
        agent_keywords = metadata.get('keywords', [])
        if isinstance(agent_keywords, str):
            agent_keywords = [agent_keywords]
        elif not isinstance(agent_keywords, list):
            agent_keywords = []

        # Normalize to lowercase (only string items)
        agent_keywords_lower = [str(k).lower() for k in agent_keywords if k is not None]
        keywords_lower = [str(k).lower() for k in keywords if k is not None]

        # Count matches
        matches = sum(1 for k in keywords_lower if k in agent_keywords_lower)

        # Also check capabilities for keyword matches
        agent_capabilities = metadata.get('capabilities', [])
        if isinstance(agent_capabilities, str):
            agent_capabilities = [agent_capabilities]
        elif not isinstance(agent_capabilities, list):
            agent_capabilities = []

        capabilities_text = ' '.join(str(c) for c in agent_capabilities if c is not None).lower()
        matches += sum(1 for k in keywords_lower if k in capabilities_text)

        if matches < min_capability_match:
            return False

        # Store relevance score for sorting
        metadata['relevance_score'] = matches

    return True


def _calculate_relevance_score(
    metadata: Dict[str, Any],
    stack: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None
) -> int:
    """
    Calculate relevance score for sorting results.

    Args:
        metadata: Agent metadata dictionary
        stack: Stack filter used in query
        keywords: Keywords used in query

    Returns:
        Relevance score (higher is better)
    """
    score = 0

    # If already calculated during matching
    if 'relevance_score' in metadata:
        score = metadata['relevance_score']

    # Bonus for exact stack match
    if stack:
        agent_stacks = metadata.get('stack', [])
        if isinstance(agent_stacks, str):
            agent_stacks = [agent_stacks]
        elif not isinstance(agent_stacks, list):
            agent_stacks = []
        agent_stacks_lower = [str(s).lower() for s in agent_stacks if s is not None]
        stack_lower = [str(s).lower() for s in stack if s is not None]

        for s in stack_lower:
            if s in agent_stacks_lower:
                score += 2

    # Bonus for having more capabilities defined
    capabilities = metadata.get('capabilities', [])
    if capabilities and isinstance(capabilities, list):
        score += min(len(capabilities), 3)  # Cap bonus at 3

    return score


def _sort_by_relevance(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort results by relevance score (highest first).

    Args:
        results: List of agent metadata dictionaries

    Returns:
        Sorted list
    """
    return sorted(
        results,
        key=lambda x: x.get('relevance_score', 0),
        reverse=True
    )


def discover_agents(
    phase: str,
    stack: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    min_capability_match: int = 1
) -> List[Dict[str, Any]]:
    """
    Discover agents matching criteria using metadata.

    This is the main entry point for agent discovery. It implements a 4-phase
    algorithm:
    1. Scan all agent locations
    2. Extract metadata from each agent
    3. Apply filters (phase required, stack optional, keywords optional)
    4. Sort by relevance and return

    Args:
        phase: Required phase filter (implementation, review, testing, orchestration)
        stack: Optional stack filter list (python, react, dotnet, etc.)
        keywords: Optional keyword list for capability matching
        min_capability_match: Minimum number of keyword matches required (default: 1)

    Returns:
        List of matching agents with metadata, sorted by relevance score.
        Each agent dict contains:
        - name: Agent name
        - description: Agent description
        - stack: List of supported stacks
        - phase: Agent's workflow phase
        - capabilities: List of capabilities
        - keywords: List of keywords
        - path: File path to agent
        - relevance_score: Computed relevance score (if keywords provided)

    Example:
        >>> results = discover_agents(phase='implementation', stack=['python'])
        >>> print(results[0]['name'])
        'python-api-specialist'

        >>> results = discover_agents(
        ...     phase='implementation',
        ...     stack=['python'],
        ...     keywords=['fastapi', 'async']
        ... )
        >>> print(results[0]['relevance_score'])
        4
    """
    results = []
    skipped_count = 0

    # Phase 1: Scan all agent locations with precedence tracking
    try:
        agent_tuples = _scan_agent_locations()
        logger.debug(f"Discovery: Found {len(agent_tuples)} unique agent files to scan")
    except Exception as e:
        logger.error(f"Failed to scan agent locations: {e}")
        return []  # Graceful degradation

    # Phase 2 & 3: Extract metadata and apply filters
    for path, source, priority in agent_tuples:
        try:
            metadata = _extract_metadata(path, source, priority)

            if metadata is None:
                skipped_count += 1
                continue

            # Graceful degradation: Skip agents without phase field
            if 'phase' not in metadata:
                skipped_count += 1
                logger.debug(f"Skipping agent without phase metadata: {path}")
                continue

            # Apply filters
            if _matches_criteria(metadata, phase, stack, keywords, min_capability_match):
                # Calculate final relevance score
                metadata['relevance_score'] = _calculate_relevance_score(
                    metadata, stack, keywords
                )
                results.append(metadata)

        except Exception as e:
            logger.warning(f"Skipping agent {path}: {e}")
            skipped_count += 1
            continue

    # Phase 4: Sort by relevance
    results = _sort_by_relevance(results)

    # Log discovery results
    logger.info(
        f"Discovery: phase={phase}, stack={stack}, "
        f"found {len(results)} agents, skipped {skipped_count}"
    )

    # Log selected agent with source information
    if results:
        best_match = results[0]
        agent_name = best_match.get('name', 'unknown')
        agent_source = best_match.get('source', 'unknown')
        logger.info(f"Agent selected: {agent_name} (source: {agent_source})")
        logger.debug(f"All matched agents: {[(r.get('name', 'unknown'), r.get('source', 'unknown')) for r in results]}")
    else:
        logger.info("No matching agent found, using task-manager (fallback)")

    if skipped_count > 0:
        logger.debug(f"Skipped {skipped_count} agents without metadata or with errors")

    return results


def get_agent_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific agent by name.

    Args:
        name: Agent name to find

    Returns:
        Agent metadata dictionary or None if not found
    """
    try:
        agent_tuples = _scan_agent_locations()
    except Exception as e:
        logger.error(f"Failed to scan agent locations: {e}")
        return None

    for path, source, priority in agent_tuples:
        try:
            metadata = _extract_metadata(path, source, priority)
            if metadata and metadata.get('name') == name:
                return metadata
        except Exception:
            continue

    return None


def list_discoverable_agents() -> List[Dict[str, Any]]:
    """
    List all agents that have discovery metadata.

    Returns:
        List of all discoverable agents (those with 'phase' field)
    """
    results = []

    try:
        agent_tuples = _scan_agent_locations()
    except Exception as e:
        logger.error(f"Failed to scan agent locations: {e}")
        return []

    for path, source, priority in agent_tuples:
        try:
            metadata = _extract_metadata(path, source, priority)
            if metadata and 'phase' in metadata:
                results.append(metadata)
        except Exception:
            continue

    return results


def get_agents_by_stack(stack: str) -> List[Dict[str, Any]]:
    """
    Get all agents for a specific stack (any phase).

    Args:
        stack: Stack to filter by (python, react, dotnet, etc.)

    Returns:
        List of agents supporting the given stack
    """
    results = []

    try:
        agent_tuples = _scan_agent_locations()
    except Exception as e:
        logger.error(f"Failed to scan agent locations: {e}")
        return []

    stack_lower = stack.lower()

    for path, source, priority in agent_tuples:
        try:
            metadata = _extract_metadata(path, source, priority)
            if metadata is None:
                continue

            agent_stacks = metadata.get('stack', [])
            if isinstance(agent_stacks, str):
                agent_stacks = [agent_stacks]
            elif not isinstance(agent_stacks, list):
                agent_stacks = []

            agent_stacks_lower = [str(s).lower() for s in agent_stacks if s is not None]

            if stack_lower in agent_stacks_lower or 'cross-stack' in agent_stacks_lower:
                results.append(metadata)

        except Exception:
            continue

    return results


def validate_discovery_metadata(metadata: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate agent discovery metadata against schema.

    Args:
        metadata: Metadata dictionary to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Validate stack
    if 'stack' not in metadata:
        errors.append("Missing required field: stack")
    elif not isinstance(metadata['stack'], list):
        errors.append("Field 'stack' must be an array")
    elif len(metadata['stack']) == 0:
        errors.append("Field 'stack' must have at least 1 item")
    else:
        for stack in metadata['stack']:
            if stack.lower() not in [s.lower() for s in VALID_STACKS]:
                errors.append(f"Invalid stack value: {stack}")

    # Validate phase
    if 'phase' not in metadata:
        errors.append("Missing required field: phase")
    elif metadata['phase'].lower() not in VALID_PHASES:
        errors.append(f"Invalid phase value: {metadata['phase']}")

    # Validate capabilities
    if 'capabilities' not in metadata:
        errors.append("Missing required field: capabilities")
    elif not isinstance(metadata['capabilities'], list):
        errors.append("Field 'capabilities' must be an array")
    elif len(metadata['capabilities']) == 0:
        errors.append("Field 'capabilities' must have at least 1 item")
    elif len(metadata['capabilities']) > 10:
        errors.append("Field 'capabilities' should have at most 10 items")

    # Validate keywords
    if 'keywords' not in metadata:
        errors.append("Missing required field: keywords")
    elif not isinstance(metadata['keywords'], list):
        errors.append("Field 'keywords' must be an array")
    elif len(metadata['keywords']) < 3:
        errors.append("Field 'keywords' must have at least 3 items")
    elif len(metadata['keywords']) > 15:
        errors.append("Field 'keywords' should have at most 15 items")

    return (len(errors) == 0, errors)


def discover_agent_with_source(
    phase: str,
    stack: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None
) -> tuple[str, str]:
    """
    Discover agent and return both name and source.

    This is a convenience wrapper around discover_agents() that returns
    just the agent name and source path for the best match, with fallback
    to task-manager if no match is found.

    Args:
        phase: Required phase filter (implementation, review, testing, orchestration)
        stack: Optional stack filter list (python, react, dotnet, etc.)
        keywords: Optional keyword list for capability matching

    Returns:
        Tuple[agent_name, agent_source] where source is one of:
        - "local" (from .claude/agents/)
        - "user" (from ~/.agentecflow/agents/)
        - "global" (from installer/core/agents/)
        - "template:name" (from installer/core/templates/*/agents/)

    Example:
        >>> agent_name, source = discover_agent_with_source(
        ...     phase='implementation',
        ...     stack=['python'],
        ...     keywords=['fastapi', 'async']
        ... )
        >>> print(f"Selected: {agent_name} from {source}")
        Selected: python-api-specialist from local
    """
    # Discover agents using existing function
    results = discover_agents(phase, stack, keywords)

    # If we have results, return the best match
    if results:
        best_match = results[0]
        agent_name = best_match.get('name', 'task-manager')
        agent_source = best_match.get('source', 'global')
        return (agent_name, agent_source)

    # Fallback to task-manager
    logger.info("No matching agent found, using task-manager (fallback)")
    return ("task-manager", "global")
