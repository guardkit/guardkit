---
complexity: 3
conductor_workspace: gr-mvp-wave3-metadata
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-000-C
feature_id: FEAT-GR-MVP
id: TASK-GR-PRE-002-A
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- metadata
- schema
- mvp-phase-1
task_type: feature
title: Define standard metadata fields
updated: 2026-01-30 00:00:00+00:00
wave: 3
implementation:
  started_at: 2026-01-30T12:00:00Z
  completed_at: 2026-01-30T12:30:00Z
  mode: tdd
  coverage: 93%
  tests_passed: 31
  tests_total: 31
---

# Task: Define standard metadata fields

## Description

Define the standard metadata fields that will be included in all Graphiti episodes. This creates a consistent schema for tracking episode provenance, versioning, and lifecycle.

## Acceptance Criteria

- [x] Standard metadata schema defined in code
- [x] Schema is documented with field descriptions
- [x] Schema is versioned for future migrations
- [x] Validation rules defined for each field
- [x] Schema supports all planned episode types

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

### Files Created

- `guardkit/integrations/graphiti/metadata.py` - EpisodeMetadata dataclass and EntityType enum
- `guardkit/integrations/graphiti/constants.py` - SourceType enum
- `guardkit/integrations/graphiti/__init__.py` - Package exports
- `tests/unit/integrations/graphiti/test_episode_metadata.py` - 31 unit tests

## Test Requirements

- [x] Unit tests for metadata validation
- [x] Unit tests for serialization/deserialization
- [x] Test all entity types

## Implementation Summary

### TDD Workflow Completed

1. **RED Phase**: Created 31 failing tests covering:
   - EpisodeMetadata creation (6 tests)
   - Serialization/deserialization (5 tests)
   - EntityType enum (5 tests)
   - SourceType enum (4 tests)
   - Validation logic (5 tests)
   - Helper methods (4 tests)
   - Edge cases (2 tests)

2. **GREEN Phase**: Implemented:
   - `SourceType(str, Enum)` with 3 values
   - `EntityType(str, Enum)` with 9 values
   - `EpisodeMetadata` dataclass with:
     - 4 required fields
     - 7 optional fields
     - `__post_init__` validation
     - `to_dict()` serialization
     - `from_dict()` deserialization
     - `create_now()` factory method

3. **Quality Gates**:
   - Tests: 31/31 passing (100%)
   - Coverage: 93% (exceeds 80% threshold)
   - Code Review: APPROVED

## Notes

Can run in parallel with PRE-001-A/B and PRE-003-A.

## References

- [FEAT-GR-PRE-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-002-episode-metadata-schema.md)
