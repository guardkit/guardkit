---
id: TASK-GR-PRE-002-B
title: Create EpisodeMetadata dataclass
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, metadata, dataclass, mvp-phase-1]
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 3
conductor_workspace: gr-mvp-wave3-metadata
complexity: 3
depends_on:
  - TASK-GR-PRE-000-C
---

# Task: Create EpisodeMetadata dataclass

## Description

Implement the EpisodeMetadata dataclass with validation, serialization, and helper methods. This is the concrete implementation of the schema defined in PRE-002-A.

## Acceptance Criteria

- [ ] EpisodeMetadata dataclass implemented
- [ ] Validation for all required fields
- [ ] to_dict() method for Graphiti serialization
- [ ] from_dict() method for deserialization
- [ ] Helper methods for common operations
- [ ] Pydantic model for strict validation

## Implementation Notes

### Implementation Pattern

```python
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime

@dataclass
class EpisodeMetadata:
    """Standard metadata for all Graphiti episodes."""

    source: str
    version: str
    created_at: str
    entity_type: str
    updated_at: Optional[str] = None
    source_hash: Optional[str] = None
    source_path: Optional[str] = None
    project_id: Optional[str] = None
    entity_id: Optional[str] = None
    expires_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate required fields."""
        if not self.source:
            raise ValueError("source is required")
        if not self.version:
            raise ValueError("version is required")
        # Additional validation...

    def to_dict(self) -> dict:
        """Convert to dictionary for Graphiti storage."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "EpisodeMetadata":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def create_now(
        cls,
        source: str,
        entity_type: str,
        **kwargs
    ) -> "EpisodeMetadata":
        """Create with current timestamp."""
        return cls(
            source=source,
            version="1.0.0",
            created_at=datetime.utcnow().isoformat(),
            entity_type=entity_type,
            **kwargs
        )
```

### Files to Create/Modify

- `src/guardkit/integrations/graphiti/metadata.py` - Implementation

## Test Requirements

- [ ] Unit tests for all methods
- [ ] Unit tests for validation
- [ ] Unit tests for serialization round-trip

## Notes

Can run in parallel with PRE-002-A (different aspects of same feature).

## References

- [FEAT-GR-PRE-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-002-episode-metadata-schema.md)
