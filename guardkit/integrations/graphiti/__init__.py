"""GuardKit Graphiti integration package.

This package provides integration with Graphiti knowledge graph,
including standardized metadata schemas for episodes and project
namespace management.
"""

from guardkit.integrations.graphiti.metadata import EpisodeMetadata, EntityType
from guardkit.integrations.graphiti.constants import SourceType
from guardkit.integrations.graphiti.exists_result import ExistsResult
from guardkit.integrations.graphiti.project import (
    ProjectInfo,
    ProjectConfig,
    initialize_project,
    get_project_info,
    list_projects,
    project_exists,
    update_project_access_time,
    PROJECT_METADATA_GROUP,
)
from guardkit.integrations.graphiti.episodes import ProjectArchitectureEpisode

__all__ = [
    # Metadata
    "EpisodeMetadata",
    "EntityType",
    "SourceType",
    "ExistsResult",
    # Project management
    "ProjectInfo",
    "ProjectConfig",
    "initialize_project",
    "get_project_info",
    "list_projects",
    "project_exists",
    "update_project_access_time",
    "PROJECT_METADATA_GROUP",
    # Episode schemas
    "ProjectArchitectureEpisode",
]
