"""Project initialization and management for Graphiti integration.

This module provides project namespace management for GuardKit's
knowledge graph integration. It handles project initialization,
metadata storage, and querying of existing projects.

When Graphiti is unavailable, all operations degrade gracefully
to return local-only data or None/empty values.

Example Usage:
    # Initialize a new or existing project
    project_info = await initialize_project("my-project")

    # Check if a project exists
    exists = await project_exists("my-project")

    # Get project info
    info = await get_project_info("my-project")

    # List all projects
    projects = await list_projects()

Coverage Target: >=85%
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging
import json
import re
import ast

from guardkit.knowledge.graphiti_client import get_graphiti, normalize_project_id

logger = logging.getLogger(__name__)

# Group ID for storing project metadata
# This is a system-level group (not project-prefixed)
PROJECT_METADATA_GROUP = "guardkit_project_metadata"


@dataclass
class ProjectConfig:
    """Configuration options for a project.

    Attributes:
        default_mode: Default development mode (standard, tdd, bdd)
        auto_seed: Whether to automatically seed knowledge on init

    Example:
        config = ProjectConfig(default_mode="tdd", auto_seed=False)
    """

    default_mode: str = "standard"
    auto_seed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with all config fields.
        """
        return {
            "default_mode": self.default_mode,
            "auto_seed": self.auto_seed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        """Create ProjectConfig from dictionary.

        Args:
            data: Dictionary with config fields.

        Returns:
            New ProjectConfig instance.
        """
        return cls(
            default_mode=data.get("default_mode", "standard"),
            auto_seed=data.get("auto_seed", True),
        )


@dataclass
class ProjectInfo:
    """Information about a project in the knowledge graph.

    Required fields:
        project_id: Normalized project identifier
        created_at: Timestamp when project was first initialized

    Optional fields:
        last_accessed: Timestamp of last access
        graphiti_version: Version of Graphiti schema
        config: Project-specific configuration

    Example:
        info = ProjectInfo(
            project_id="my-project",
            created_at=datetime.now(timezone.utc),
            config=ProjectConfig(default_mode="tdd")
        )
    """

    project_id: str
    created_at: datetime
    last_accessed: Optional[datetime] = None
    graphiti_version: str = "1.0.0"
    config: Optional[ProjectConfig] = None

    def __post_init__(self) -> None:
        """Validate and set defaults after initialization."""
        # Ensure config is not None - use defaults if not provided
        if self.config is None:
            self.config = ProjectConfig()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with all fields including entity_type marker.
        """
        result = {
            "entity_type": "project_metadata",
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat(),
            "graphiti_version": self.graphiti_version,
        }

        if self.last_accessed is not None:
            result["last_accessed"] = self.last_accessed.isoformat()

        if self.config is not None:
            result["config"] = self.config.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectInfo":
        """Create ProjectInfo from dictionary.

        Args:
            data: Dictionary with project metadata fields.

        Returns:
            New ProjectInfo instance.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If field values are invalid.
        """
        # Validate required fields
        if "project_id" not in data:
            raise KeyError("project_id is required")

        # Parse created_at - handle various formats
        created_at_str = data.get("created_at")
        if created_at_str:
            # Handle ISO 8601 format with 'Z' suffix
            if isinstance(created_at_str, str):
                if created_at_str.endswith("Z"):
                    created_at_str = created_at_str[:-1] + "+00:00"
                created_at = datetime.fromisoformat(created_at_str)
            else:
                created_at = created_at_str
        else:
            created_at = datetime.now(timezone.utc)

        # Parse last_accessed if present
        last_accessed = None
        last_accessed_str = data.get("last_accessed")
        if last_accessed_str:
            if isinstance(last_accessed_str, str):
                if last_accessed_str.endswith("Z"):
                    last_accessed_str = last_accessed_str[:-1] + "+00:00"
                last_accessed = datetime.fromisoformat(last_accessed_str)
            else:
                last_accessed = last_accessed_str

        # Parse config if present
        config = None
        config_data = data.get("config")
        if config_data:
            config = ProjectConfig.from_dict(config_data)

        return cls(
            project_id=data["project_id"],
            created_at=created_at,
            last_accessed=last_accessed,
            graphiti_version=data.get("graphiti_version", "1.0.0"),
            config=config,
        )


def _normalize_project_id(project_id: str) -> str:
    """Normalize project_id to valid format.

    Rules:
    - Convert to lowercase
    - Replace spaces with hyphens
    - Remove non-alphanumeric characters (except hyphens)
    - Collapse multiple consecutive hyphens

    Args:
        project_id: The project ID to normalize.

    Returns:
        Normalized project ID string.
    """
    if not project_id or not project_id.strip():
        return ""

    # Convert to lowercase
    result = project_id.lower()

    # Replace spaces and underscores with hyphens
    result = result.replace(" ", "-").replace("_", "-")

    # Remove non-alphanumeric characters (except hyphens)
    result = re.sub(r'[^a-z0-9-]', '', result)

    # Collapse multiple consecutive hyphens
    result = re.sub(r'-+', '-', result)

    # Remove leading/trailing hyphens
    result = result.strip('-')

    return result


def _parse_episode_body(episode_body: str) -> Optional[Dict[str, Any]]:
    """Parse episode body to extract project metadata.

    Handles both JSON strings and Python dict representations.

    Args:
        episode_body: The episode body string.

    Returns:
        Parsed dictionary or None if parsing fails.
    """
    if not episode_body:
        return None

    try:
        # Try JSON first
        return json.loads(episode_body)
    except (json.JSONDecodeError, ValueError):
        pass

    try:
        # Try Python literal eval (for dict representations like str(dict))
        parsed = ast.literal_eval(episode_body)
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, SyntaxError):
        pass

    return None


async def initialize_project(
    project_id: str,
    config: Optional[ProjectConfig] = None,
) -> ProjectInfo:
    """Initialize or load a project namespace.

    If the project already exists in Graphiti, loads and returns its info.
    If the project is new, creates the namespace and stores metadata.

    When Graphiti is unavailable, returns a local-only ProjectInfo
    without persisting to the knowledge graph.

    Args:
        project_id: Project identifier (will be normalized)
        config: Optional project configuration (uses defaults if None)

    Returns:
        ProjectInfo for the initialized or loaded project.

    Raises:
        ValueError: If project_id is empty or None.

    Example:
        # Initialize new project
        info = await initialize_project("my-new-project")

        # Initialize with custom config
        config = ProjectConfig(default_mode="tdd")
        info = await initialize_project("tdd-project", config=config)
    """
    # Validate project_id
    if project_id is None:
        raise ValueError("project_id cannot be None")
    if not project_id or not project_id.strip():
        raise ValueError("project_id cannot be empty")

    # Normalize project_id
    normalized_id = _normalize_project_id(project_id)

    # Get Graphiti client
    client = get_graphiti()

    # Graceful degradation: return local-only ProjectInfo if client unavailable
    if client is None or not client.enabled:
        now = datetime.now(timezone.utc)
        return ProjectInfo(
            project_id=normalized_id,
            created_at=now,
            last_accessed=now,
            config=config or ProjectConfig(),
        )

    # Check if project already exists
    try:
        search_results = await client.search(
            query=f"project_metadata {normalized_id}",
            group_ids=[PROJECT_METADATA_GROUP],
            num_results=10,
            scope="system",
        )

        # Look for existing project metadata
        for result in search_results:
            episode_body = result.get("episode_body", "")
            if not episode_body:
                # Try to get from 'fact' field
                episode_body = result.get("fact", "")

            parsed = _parse_episode_body(episode_body)
            if parsed and parsed.get("project_id") == normalized_id:
                # Found existing project - return it
                return ProjectInfo.from_dict(parsed)

    except Exception as e:
        logger.warning(f"Error searching for existing project: {e}")
        # Continue to create new project

    # Create new project
    now = datetime.now(timezone.utc)
    project_info = ProjectInfo(
        project_id=normalized_id,
        created_at=now,
        last_accessed=now,
        config=config or ProjectConfig(),
    )

    # Store in Graphiti
    try:
        episode_body = json.dumps(project_info.to_dict())
        await client.add_episode(
            name=f"project_metadata_{normalized_id}",
            episode_body=episode_body,
            group_id=PROJECT_METADATA_GROUP,
            scope="system",
        )
    except Exception as e:
        logger.warning(f"Error storing project metadata: {e}")
        # Still return the ProjectInfo even if storage fails

    return project_info


async def get_project_info(project_id: str) -> Optional[ProjectInfo]:
    """Get information about an existing project.

    Args:
        project_id: Project identifier (will be normalized)

    Returns:
        ProjectInfo if project exists, None otherwise.
        Returns None when Graphiti is unavailable.

    Example:
        info = await get_project_info("my-project")
        if info:
            print(f"Project created: {info.created_at}")
    """
    # Normalize project_id
    normalized_id = _normalize_project_id(project_id)

    # Get Graphiti client
    client = get_graphiti()

    # Graceful degradation
    if client is None or not client.enabled:
        return None

    try:
        search_results = await client.search(
            query=f"project_metadata {normalized_id}",
            group_ids=[PROJECT_METADATA_GROUP],
            num_results=10,
            scope="system",
        )

        # Look for matching project
        for result in search_results:
            episode_body = result.get("episode_body", "")
            if not episode_body:
                episode_body = result.get("fact", "")

            parsed = _parse_episode_body(episode_body)
            if parsed and parsed.get("project_id") == normalized_id:
                return ProjectInfo.from_dict(parsed)

        return None

    except Exception as e:
        logger.warning(f"Error getting project info: {e}")
        return None


async def list_projects() -> List[ProjectInfo]:
    """List all projects in the knowledge graph.

    Returns:
        List of ProjectInfo for all known projects.
        Returns empty list when Graphiti is unavailable.

    Example:
        projects = await list_projects()
        for p in projects:
            print(f"- {p.project_id} (created: {p.created_at})")
    """
    # Get Graphiti client
    client = get_graphiti()

    # Graceful degradation
    if client is None or not client.enabled:
        return []

    try:
        search_results = await client.search(
            query="project_metadata",
            group_ids=[PROJECT_METADATA_GROUP],
            num_results=100,
            scope="system",
        )

        projects = []
        seen_ids = set()

        for result in search_results:
            episode_body = result.get("episode_body", "")
            if not episode_body:
                episode_body = result.get("fact", "")

            parsed = _parse_episode_body(episode_body)
            if parsed and "project_id" in parsed:
                pid = parsed["project_id"]
                # Avoid duplicates
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    try:
                        projects.append(ProjectInfo.from_dict(parsed))
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Error parsing project {pid}: {e}")

        return projects

    except Exception as e:
        logger.warning(f"Error listing projects: {e}")
        return []


async def project_exists(project_id: str) -> bool:
    """Check if a project exists in the knowledge graph.

    Args:
        project_id: Project identifier (will be normalized)

    Returns:
        True if project exists, False otherwise.
        Returns False when Graphiti is unavailable.

    Example:
        if await project_exists("my-project"):
            info = await get_project_info("my-project")
    """
    # Normalize project_id
    normalized_id = _normalize_project_id(project_id)

    # Get Graphiti client
    client = get_graphiti()

    # Graceful degradation
    if client is None or not client.enabled:
        return False

    try:
        search_results = await client.search(
            query=f"project_metadata {normalized_id}",
            group_ids=[PROJECT_METADATA_GROUP],
            num_results=10,
            scope="system",
        )

        # Check if any result matches
        for result in search_results:
            episode_body = result.get("episode_body", "")
            if not episode_body:
                episode_body = result.get("fact", "")

            parsed = _parse_episode_body(episode_body)
            if parsed and parsed.get("project_id") == normalized_id:
                return True

        return False

    except Exception as e:
        logger.warning(f"Error checking project existence: {e}")
        return False


async def update_project_access_time(project_id: str) -> bool:
    """Update the last_accessed timestamp for a project.

    Args:
        project_id: Project identifier (will be normalized)

    Returns:
        True if update successful, False if project doesn't exist
        or Graphiti is unavailable.

    Example:
        if await update_project_access_time("my-project"):
            print("Access time updated")
    """
    # Normalize project_id
    normalized_id = _normalize_project_id(project_id)

    # Get Graphiti client
    client = get_graphiti()

    # Graceful degradation
    if client is None or not client.enabled:
        return False

    try:
        # First check if project exists
        project_info = await get_project_info(normalized_id)
        if project_info is None:
            return False

        # Update last_accessed
        now = datetime.now(timezone.utc)
        updated_info = ProjectInfo(
            project_id=project_info.project_id,
            created_at=project_info.created_at,
            last_accessed=now,
            graphiti_version=project_info.graphiti_version,
            config=project_info.config,
        )

        # Store updated info
        episode_body = json.dumps(updated_info.to_dict())
        await client.add_episode(
            name=f"project_metadata_{normalized_id}_update",
            episode_body=episode_body,
            group_id=PROJECT_METADATA_GROUP,
            scope="system",
        )

        return True

    except Exception as e:
        logger.warning(f"Error updating project access time: {e}")
        return False
