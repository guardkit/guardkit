"""EpisodeMetadata dataclass for Graphiti episode standardization.

Provides a structured metadata format for all Graphiti episodes,
ensuring consistent tracking of source, versioning, and entity information.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from enum import Enum


class EntityType(str, Enum):
    """Entity types for Graphiti episodes.

    Defines the types of entities that can be represented in the knowledge graph.

    Values:
        PROJECT_OVERVIEW: High-level project information
        PROJECT_ARCHITECTURE: Architectural decisions and structure
        FEATURE_SPEC: Feature specifications and requirements
        DECISION_RECORD: Architectural decision records (ADRs)
        ROLE_CONSTRAINTS: Role-based access and constraints
        QUALITY_GATE_CONFIG: Quality gate configurations
        IMPLEMENTATION_MODE: Implementation mode settings (TDD, standard, BDD)
        DOMAIN_TERM: Domain-specific terminology and definitions
        CONSTRAINT: System or business constraints
    """
    PROJECT_OVERVIEW = "project_overview"
    PROJECT_ARCHITECTURE = "project_architecture"
    FEATURE_SPEC = "feature_spec"
    DECISION_RECORD = "decision_record"
    ROLE_CONSTRAINTS = "role_constraints"
    QUALITY_GATE_CONFIG = "quality_gate_config"
    IMPLEMENTATION_MODE = "implementation_mode"
    DOMAIN_TERM = "domain_term"
    CONSTRAINT = "constraint"


@dataclass
class EpisodeMetadata:
    """Standard metadata for all Graphiti episodes.

    Required fields:
        source: How the episode was created (guardkit_seeding, user_added, auto_captured)
        version: Schema version in semantic versioning format (e.g., "1.0.0")
        created_at: ISO 8601 timestamp when episode was created
        entity_type: Type of entity this episode represents

    Optional fields:
        updated_at: ISO 8601 timestamp when episode was last updated
        source_hash: SHA-256 hash of source content for deduplication
        source_path: File path if episode was created from a file
        project_id: Project namespace for filtering
        entity_id: Stable ID for upsert operations
        expires_at: Optional expiration timestamp
        tags: Searchable tags for filtering
    """

    # Required fields
    source: str  # SourceType value
    version: str  # Semantic version string
    created_at: str  # ISO 8601 timestamp
    entity_type: str  # EntityType value

    # Optional fields
    updated_at: Optional[str] = None
    source_hash: Optional[str] = None
    source_path: Optional[str] = None
    project_id: Optional[str] = None
    entity_id: Optional[str] = None
    expires_at: Optional[str] = None
    tags: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Validate and normalize fields after initialization."""
        # Handle enum values - convert to string
        if hasattr(self.source, 'value'):
            self.source = self.source.value
        if hasattr(self.entity_type, 'value'):
            self.entity_type = self.entity_type.value

        # Validate required fields are not empty
        if not self.source:
            raise ValueError("source is required and cannot be empty")
        if not self.version:
            raise ValueError("version is required and cannot be empty")
        if not self.created_at:
            raise ValueError("created_at is required and cannot be empty")
        if not self.entity_type:
            raise ValueError("entity_type is required and cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all non-None fields.
        """
        result = {
            "source": self.source,
            "version": self.version,
            "created_at": self.created_at,
            "entity_type": self.entity_type,
        }

        # Add optional fields only if they have values
        if self.updated_at is not None:
            result["updated_at"] = self.updated_at
        if self.source_hash is not None:
            result["source_hash"] = self.source_hash
        if self.source_path is not None:
            result["source_path"] = self.source_path
        if self.project_id is not None:
            result["project_id"] = self.project_id
        if self.entity_id is not None:
            result["entity_id"] = self.entity_id
        if self.expires_at is not None:
            result["expires_at"] = self.expires_at
        if self.tags is not None:
            result["tags"] = self.tags

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpisodeMetadata":
        """Create EpisodeMetadata from dictionary.

        Args:
            data: Dictionary with metadata fields.

        Returns:
            New EpisodeMetadata instance.
        """
        return cls(
            source=data["source"],
            version=data["version"],
            created_at=data["created_at"],
            entity_type=data["entity_type"],
            updated_at=data.get("updated_at"),
            source_hash=data.get("source_hash"),
            source_path=data.get("source_path"),
            project_id=data.get("project_id"),
            entity_id=data.get("entity_id"),
            expires_at=data.get("expires_at"),
            tags=data.get("tags"),
        )

    @classmethod
    def create_now(
        cls,
        source: Union[str, "SourceType"],
        entity_type: Union[str, EntityType],
        version: str = "1.0.0",
        **kwargs
    ) -> "EpisodeMetadata":
        """Create metadata with current UTC timestamp.

        Args:
            source: Source type for the episode.
            entity_type: Type of entity.
            version: Schema version (default "1.0.0").
            **kwargs: Additional optional fields.

        Returns:
            New EpisodeMetadata with current timestamp.
        """
        # Use isoformat with microseconds, then replace +00:00 with Z for ISO 8601
        now = datetime.now(timezone.utc)
        created_at = now.isoformat().replace('+00:00', 'Z')

        return cls(
            source=source,
            version=version,
            created_at=created_at,
            entity_type=entity_type,
            **kwargs
        )


# Import SourceType for forward reference annotation
# This is done at module level to avoid circular imports
try:
    from guardkit.integrations.graphiti.constants import SourceType as _SourceType
except ImportError:
    pass
