---
id: TASK-GR-PRE-002-A
title: Define standard metadata fields
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, metadata, schema, mvp-phase-1]
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

# Task: Define standard metadata fields

## Description

Define the standard metadata fields that will be included in all Graphiti episodes. This creates a consistent schema for tracking episode provenance, versioning, and lifecycle.

## Acceptance Criteria

- [ ] Standard metadata schema defined in code
- [ ] Schema is documented with field descriptions
- [ ] Schema is versioned for future migrations
- [ ] Validation rules defined for each field
- [ ] Schema supports all planned episode types

## Implementation Notes

### Standard Metadata Fields

```python
@dataclass
class EpisodeMetadata:
    """Standard metadata for all Graphiti episodes."""

    # Required fields
    source: str               # "guardkit_seeding" | "user_added" | "auto_captured"
    version: str              # Schema version "1.0.0"
    created_at: str           # ISO 8601 timestamp
    entity_type: str          # Episode type identifier

    # Optional fields
    updated_at: str | None    # ISO 8601 timestamp
    source_hash: str | None   # SHA-256 of source content (for deduplication)
    source_path: str | None   # File path if from file
    project_id: str | None    # Project namespace
    entity_id: str | None     # Stable ID for upsert
    expires_at: str | None    # Optional expiration
    tags: list[str] | None    # Searchable tags
```

### Entity Types

- `project_overview`
- `project_architecture`
- `feature_spec`
- `decision_record`
- `role_constraints`
- `quality_gate_config`
- `implementation_mode`
- `domain_term`
- `constraint`

### Files to Create

- `src/guardkit/integrations/graphiti/metadata.py` - Schema definition
- `src/guardkit/integrations/graphiti/constants.py` - Entity types

## Test Requirements

- [ ] Unit tests for metadata validation
- [ ] Unit tests for serialization/deserialization
- [ ] Test all entity types

## Notes

Can run in parallel with PRE-001-A/B and PRE-003-A.

## References

- [FEAT-GR-PRE-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-002-episode-metadata-schema.md)
