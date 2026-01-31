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
        # TODO: Implement in GREEN phase
        raise NotImplementedError("ProjectConfig.to_dict not implemented yet")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        """Create ProjectConfig from dictionary.

        Args:
            data: Dictionary with config fields.

        Returns:
            New ProjectConfig instance.
        """
        # TODO: Implement in GREEN phase
        raise NotImplementedError("ProjectConfig.from_dict not implemented yet")


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
        # TODO: Implement in GREEN phase
        raise NotImplementedError("ProjectInfo.__post_init__ not implemented yet")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with all fields including entity_type marker.
        """
        # TODO: Implement in GREEN phase
        raise NotImplementedError("ProjectInfo.to_dict not implemented yet")

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
        # TODO: Implement in GREEN phase
        raise NotImplementedError("ProjectInfo.from_dict not implemented yet")


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
    # TODO: Implement in GREEN phase
    # 1. Validate project_id
    # 2. Normalize project_id
    # 3. Get GraphitiClient
    # 4. Check if project exists
    # 5. If exists, load and return
    # 6. If new, create metadata episode and return
    # 7. Handle graceful degradation
    raise NotImplementedError("initialize_project not implemented yet")


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
    # TODO: Implement in GREEN phase
    # 1. Normalize project_id
    # 2. Get GraphitiClient
    # 3. Search for project metadata
    # 4. Parse and return ProjectInfo
    # 5. Handle graceful degradation
    raise NotImplementedError("get_project_info not implemented yet")


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
    # TODO: Implement in GREEN phase
    # 1. Get GraphitiClient
    # 2. Search for all project metadata episodes
    # 3. Parse and return list of ProjectInfo
    # 4. Handle graceful degradation
    raise NotImplementedError("list_projects not implemented yet")


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
    # TODO: Implement in GREEN phase
    # 1. Normalize project_id
    # 2. Get GraphitiClient
    # 3. Search for project metadata
    # 4. Return True if found, False otherwise
    # 5. Handle graceful degradation
    raise NotImplementedError("project_exists not implemented yet")


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
    # TODO: Implement in GREEN phase
    # 1. Normalize project_id
    # 2. Get GraphitiClient
    # 3. Check project exists
    # 4. Add update episode with new last_accessed
    # 5. Handle graceful degradation
    raise NotImplementedError("update_project_access_time not implemented yet")
