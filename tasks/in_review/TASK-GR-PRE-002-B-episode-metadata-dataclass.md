---
complexity: 3
conductor_workspace: gr-mvp-wave3-metadata
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-000-C
feature_id: FEAT-GR-MVP
id: TASK-GR-PRE-002-B
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- metadata
- dataclass
- mvp-phase-1
task_type: feature
title: Create EpisodeMetadata dataclass
updated: 2026-01-30 00:00:00+00:00
wave: 3
---

# Task: Create EpisodeMetadata dataclass

## Description

Implement the EpisodeMetadata dataclass with validation, serialization, and helper methods. This is the concrete implementation of the schema defined in PRE-002-A.

## Acceptance Criteria

- [x] EpisodeMetadata dataclass implemented
- [x] Validation for all required fields
- [x] to_dict() method for Graphiti serialization
- [x] from_dict() method for deserialization
- [x] Helper methods for common operations
- [x] Pydantic model for strict validation (dataclass validation used instead - simpler, no external deps)

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

- [x] Unit tests for all methods (31 tests passing)
- [x] Unit tests for validation
- [x] Unit tests for serialization round-trip
- [x] 93% line coverage achieved

## Notes

Can run in parallel with PRE-002-A (different aspects of same feature).

## References

- [FEAT-GR-PRE-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-002-episode-metadata-schema.md)

## Implementation Summary

**Files Created:**
- `guardkit/integrations/graphiti/metadata.py` - Main implementation with EpisodeMetadata dataclass and EntityType enum
- `guardkit/integrations/graphiti/constants.py` - SourceType enum
- `guardkit/integrations/graphiti/__init__.py` - Package exports
- `tests/unit/integrations/graphiti/test_episode_metadata.py` - Comprehensive test suite

**Test Results:**
- 31/31 tests passing (100% pass rate)
- 93% line coverage for metadata.py
- 100% coverage for constants.py and __init__.py

**Code Review:** APPROVED - High-quality implementation with comprehensive test coverage