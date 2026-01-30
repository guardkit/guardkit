# FEAT-GR-PRE-002: Episode Metadata Schema

> **Purpose**: Standardize episode metadata to enable better querying, filtering, and traceability of knowledge sources.
>
> **Priority**: High (Prerequisite)
> **Estimated Complexity**: 3
> **Dependencies**: None (foundational)
> **Blocks**: FEAT-GR-002, FEAT-GR-006

---

## Problem Statement

Currently, episodes are added with ad-hoc body structures:

```python
# Current approach - inconsistent metadata
await client.add_episode(
    name="some_episode",
    episode_body=json.dumps({
        "entity_type": "pattern",  # Sometimes present
        "name": "...",
        # No standard source tracking
        # No standard versioning
    }),
    group_id="patterns"
)
```

This causes issues:

1. **No traceability** - Can't tell where knowledge came from (seeding? user input? file parse?)
2. **No filtering by type** - Can't easily filter search results by entity type
3. **No versioning** - Can't track when knowledge was updated or superseded
4. **Inconsistent schemas** - Each seeding function uses different field names

---

## Proposed Solution

### 1. Standard Metadata Fields

Define a standard set of metadata fields that ALL episodes should include:

```python
# guardkit/knowledge/episode_metadata.py

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum


class SourceType(str, Enum):
    """How the episode was created."""
    
    SYSTEM_SEEDING = "system_seeding"      # From GuardKit seeding
    FILE_PARSE = "file_parse"              # Parsed from markdown file
    INTERACTIVE = "interactive"            # From user Q&A session
    DISCOVERED = "discovered"              # Discovered from code analysis
    MANUAL = "manual"                      # Manual entry
    IMPORT = "import"                      # Imported from external source


class EntityType(str, Enum):
    """What kind of entity this episode represents."""
    
    # System knowledge types (from seeding.py)
    PRODUCT = "product"
    WORKFLOW = "workflow"
    COMMAND = "command"
    PHASE = "phase"
    ARCHITECTURE = "architecture"
    AGENT = "agent"
    PATTERN = "pattern"
    RULE = "rule"
    TEMPLATE = "template"
    FAILURE = "failure"
    
    # Project knowledge types
    PROJECT_OVERVIEW = "project_overview"
    PROJECT_ARCHITECTURE = "project_architecture"
    FEATURE_SPEC = "feature_spec"
    ADR = "adr"
    CONSTRAINT = "constraint"
    DOMAIN_TERM = "domain_term"
    GUIDE = "guide"
    
    # Learning types
    TASK_OUTCOME = "task_outcome"
    REVIEW_DECISION = "review_decision"
    REFINEMENT = "refinement"


@dataclass
class EpisodeMetadata:
    """Standard metadata for all episodes.
    
    This metadata is included in the episode body alongside
    the entity-specific content.
    """
    
    # Required: Type classification
    entity_type: str  # From EntityType enum or custom string
    
    # Required: Source tracking
    source_type: str  # From SourceType enum
    
    # Optional: Source details
    source_file: Optional[str] = None      # File path if from file
    source_command: Optional[str] = None   # Command that created it
    source_template: Optional[str] = None  # Template ID if template-related
    
    # Optional: Project context
    project_id: Optional[str] = None       # Project namespace
    
    # Optional: Versioning
    version: int = 1                       # Increment on updates
    supersedes: Optional[str] = None       # ID of episode this replaces
    superseded_by: Optional[str] = None    # ID of episode that replaced this
    
    # Optional: Quality/confidence
    confidence: float = 1.0                # 0.0-1.0, lower for discovered knowledge
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EpisodeMetadata':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
```

### 2. Base Episode Schema

Create a base class that combines metadata with entity-specific content:

```python
# guardkit/knowledge/episode_schema.py

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, TypeVar, Generic
from abc import ABC, abstractmethod
import json

from .episode_metadata import EpisodeMetadata, SourceType, EntityType


@dataclass
class BaseEpisode(ABC):
    """Base class for all episode types.
    
    Combines standard metadata with entity-specific content.
    """
    
    # Standard metadata (included in all episodes)
    _metadata: EpisodeMetadata = field(default_factory=EpisodeMetadata)
    
    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Return the entity type for this episode."""
        pass
    
    def to_episode_body(self) -> str:
        """Convert to JSON string for Graphiti storage.
        
        Returns:
            JSON string combining metadata and entity content.
        """
        body = self._get_entity_content()
        body["_metadata"] = self._metadata.to_dict()
        return json.dumps(body)
    
    @abstractmethod
    def _get_entity_content(self) -> Dict[str, Any]:
        """Get entity-specific content as dictionary."""
        pass
    
    @classmethod
    def from_episode_body(cls, body: str) -> 'BaseEpisode':
        """Create from Graphiti episode body.
        
        Args:
            body: JSON string from Graphiti
            
        Returns:
            Reconstructed episode instance
        """
        data = json.loads(body) if isinstance(body, str) else body
        metadata_dict = data.pop("_metadata", {})
        metadata = EpisodeMetadata.from_dict(metadata_dict)
        
        instance = cls._from_content(data)
        instance._metadata = metadata
        return instance
    
    @classmethod
    @abstractmethod
    def _from_content(cls, content: Dict[str, Any]) -> 'BaseEpisode':
        """Create instance from entity content."""
        pass


@dataclass
class FeatureSpecEpisode(BaseEpisode):
    """Episode for feature specifications."""
    
    id: str = ""
    title: str = ""
    description: str = ""
    success_criteria: list = field(default_factory=list)
    technical_requirements: list = field(default_factory=list)
    acceptance_criteria: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    implementation_notes: str = ""
    testing_strategy: str = ""
    priority: str = ""
    estimated_complexity: int = 0
    
    @property
    def entity_type(self) -> str:
        return EntityType.FEATURE_SPEC.value
    
    def _get_entity_content(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "success_criteria": self.success_criteria,
            "technical_requirements": self.technical_requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "dependencies": self.dependencies,
            "implementation_notes": self.implementation_notes,
            "testing_strategy": self.testing_strategy,
            "priority": self.priority,
            "estimated_complexity": self.estimated_complexity
        }
    
    @classmethod
    def _from_content(cls, content: Dict[str, Any]) -> 'FeatureSpecEpisode':
        return cls(
            id=content.get("id", ""),
            title=content.get("title", ""),
            description=content.get("description", ""),
            success_criteria=content.get("success_criteria", []),
            technical_requirements=content.get("technical_requirements", []),
            acceptance_criteria=content.get("acceptance_criteria", []),
            dependencies=content.get("dependencies", []),
            implementation_notes=content.get("implementation_notes", ""),
            testing_strategy=content.get("testing_strategy", ""),
            priority=content.get("priority", ""),
            estimated_complexity=content.get("estimated_complexity", 0)
        )


@dataclass
class ProjectOverviewEpisode(BaseEpisode):
    """Episode for project overview."""
    
    project_name: str = ""
    template_used: str = ""
    purpose: str = ""
    description: str = ""
    goals: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    target_users: list = field(default_factory=list)
    architecture_summary: str = ""
    key_components: list = field(default_factory=list)
    external_dependencies: list = field(default_factory=list)
    domain: str = ""
    domain_terminology: dict = field(default_factory=dict)
    knowledge_completeness: str = "minimal"
    
    @property
    def entity_type(self) -> str:
        return EntityType.PROJECT_OVERVIEW.value
    
    def _get_entity_content(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "project_name": self.project_name,
            "template_used": self.template_used,
            "purpose": self.purpose,
            "description": self.description,
            "goals": self.goals,
            "constraints": self.constraints,
            "target_users": self.target_users,
            "architecture_summary": self.architecture_summary,
            "key_components": self.key_components,
            "external_dependencies": self.external_dependencies,
            "domain": self.domain,
            "domain_terminology": self.domain_terminology,
            "knowledge_completeness": self.knowledge_completeness
        }
    
    @classmethod
    def _from_content(cls, content: Dict[str, Any]) -> 'ProjectOverviewEpisode':
        return cls(
            project_name=content.get("project_name", ""),
            template_used=content.get("template_used", ""),
            purpose=content.get("purpose", ""),
            description=content.get("description", ""),
            goals=content.get("goals", []),
            constraints=content.get("constraints", []),
            target_users=content.get("target_users", []),
            architecture_summary=content.get("architecture_summary", ""),
            key_components=content.get("key_components", []),
            external_dependencies=content.get("external_dependencies", []),
            domain=content.get("domain", ""),
            domain_terminology=content.get("domain_terminology", {}),
            knowledge_completeness=content.get("knowledge_completeness", "minimal")
        )


@dataclass  
class ADREpisode(BaseEpisode):
    """Episode for Architecture Decision Records."""
    
    id: str = ""
    title: str = ""
    status: str = "proposed"  # proposed | accepted | deprecated | superseded
    context: str = ""
    decision: str = ""
    rationale: str = ""
    consequences: list = field(default_factory=list)
    alternatives_considered: list = field(default_factory=list)
    related_adrs: list = field(default_factory=list)
    date: str = ""
    
    @property
    def entity_type(self) -> str:
        return EntityType.ADR.value
    
    def _get_entity_content(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "rationale": self.rationale,
            "consequences": self.consequences,
            "alternatives_considered": self.alternatives_considered,
            "related_adrs": self.related_adrs,
            "date": self.date
        }
    
    @classmethod
    def _from_content(cls, content: Dict[str, Any]) -> 'ADREpisode':
        return cls(
            id=content.get("id", ""),
            title=content.get("title", ""),
            status=content.get("status", "proposed"),
            context=content.get("context", ""),
            decision=content.get("decision", ""),
            rationale=content.get("rationale", ""),
            consequences=content.get("consequences", []),
            alternatives_considered=content.get("alternatives_considered", []),
            related_adrs=content.get("related_adrs", []),
            date=content.get("date", "")
        )
```

### 3. Helper Functions for Creating Episodes

```python
# guardkit/knowledge/episode_helpers.py

from typing import Dict, Any, Optional
from pathlib import Path

from .episode_metadata import EpisodeMetadata, SourceType, EntityType
from .episode_schema import BaseEpisode, FeatureSpecEpisode, ProjectOverviewEpisode, ADREpisode
from .project_namespace import get_project_id


def create_metadata(
    entity_type: str,
    source_type: str,
    source_file: Optional[Path] = None,
    source_command: Optional[str] = None,
    confidence: float = 1.0,
    project_id: Optional[str] = None
) -> EpisodeMetadata:
    """Create episode metadata with standard fields.
    
    Args:
        entity_type: Type of entity (from EntityType enum)
        source_type: How it was created (from SourceType enum)
        source_file: Optional source file path
        source_command: Optional command that created it
        confidence: Confidence score 0.0-1.0
        project_id: Optional project ID (auto-detected if not provided)
        
    Returns:
        EpisodeMetadata instance
    """
    return EpisodeMetadata(
        entity_type=entity_type,
        source_type=source_type,
        source_file=str(source_file) if source_file else None,
        source_command=source_command,
        project_id=project_id or get_project_id(),
        confidence=confidence
    )


def extract_metadata_from_result(result: Dict[str, Any]) -> Optional[EpisodeMetadata]:
    """Extract metadata from a Graphiti search result.
    
    Args:
        result: Search result dictionary
        
    Returns:
        EpisodeMetadata if present, None otherwise
    """
    # Try to get metadata from various possible locations
    body = result.get("body", result)
    
    if isinstance(body, str):
        import json
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return None
    
    if not isinstance(body, dict):
        return None
    
    metadata_dict = body.get("_metadata")
    if metadata_dict:
        return EpisodeMetadata.from_dict(metadata_dict)
    
    # Fallback: try to extract from flat structure
    if "entity_type" in body and "source_type" in body:
        return EpisodeMetadata(
            entity_type=body.get("entity_type", ""),
            source_type=body.get("source_type", SourceType.MANUAL.value)
        )
    
    return None


def filter_results_by_entity_type(
    results: list,
    entity_types: list
) -> list:
    """Filter search results by entity type.
    
    Args:
        results: List of search results
        entity_types: List of entity types to include
        
    Returns:
        Filtered results
    """
    filtered = []
    
    for result in results:
        metadata = extract_metadata_from_result(result)
        if metadata and metadata.entity_type in entity_types:
            filtered.append(result)
        elif not metadata:
            # Include results without metadata (legacy compatibility)
            body = result.get("body", result)
            if isinstance(body, dict):
                if body.get("entity_type") in entity_types:
                    filtered.append(result)
    
    return filtered
```

---

## Success Criteria

1. **All new episodes include metadata** - New seeding uses standard metadata
2. **Metadata extractable from results** - Can get metadata from search results
3. **Filtering by entity type works** - Can filter results by type
4. **Backward compatible** - Old episodes without metadata still work
5. **Source tracking** - Can trace where knowledge came from

---

## Implementation Tasks

| Task ID | Description | Estimate |
|---------|-------------|----------|
| TASK-GR-PRE-002A | Create `episode_metadata.py` with enums and dataclass | 1h |
| TASK-GR-PRE-002B | Create `episode_schema.py` with base class and entity types | 2h |
| TASK-GR-PRE-002C | Create `episode_helpers.py` with utility functions | 1h |
| TASK-GR-PRE-002D | Update seeding.py to use metadata (optional) | 1h |
| TASK-GR-PRE-002E | Add tests | 1.5h |
| TASK-GR-PRE-002F | Update documentation | 0.5h |

**Total Estimate**: 7 hours

---

## Usage Examples

### Creating an Episode with Metadata

```python
from guardkit.knowledge.episode_schema import FeatureSpecEpisode
from guardkit.knowledge.episode_helpers import create_metadata
from guardkit.knowledge.episode_metadata import SourceType

# Create metadata
metadata = create_metadata(
    entity_type="feature_spec",
    source_type=SourceType.FILE_PARSE.value,
    source_file=Path("docs/features/FEAT-SKEL-001.md"),
    confidence=1.0
)

# Create episode
episode = FeatureSpecEpisode(
    id="FEAT-SKEL-001",
    title="Walking Skeleton",
    description="Basic MCP server setup",
    success_criteria=["Ping tool responds", "Docker runs"],
    _metadata=metadata
)

# Convert to Graphiti format
body = episode.to_episode_body()
await client.add_project_episode(
    name="feat_skel_001",
    episode_body=body,
    group_id="feature_specs"
)
```

### Filtering Results by Type

```python
from guardkit.knowledge.episode_helpers import filter_results_by_entity_type

# Search returns mixed results
results = await client.search_project(
    query="authentication requirements",
    group_ids=["feature_specs", "project_decisions"]
)

# Filter to only feature specs
feature_results = filter_results_by_entity_type(
    results,
    entity_types=["feature_spec"]
)
```

---

## Migration Considerations

- **Backward compatible** - Episodes without `_metadata` still work
- **Gradual adoption** - New episodes use metadata, old ones don't need updating
- **Future-proof** - Metadata schema can be extended without breaking changes
