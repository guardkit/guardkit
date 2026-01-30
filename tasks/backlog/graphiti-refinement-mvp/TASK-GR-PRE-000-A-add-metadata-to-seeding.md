---
id: TASK-GR-PRE-000-A
title: Add metadata block to existing seeding episodes
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, seeding, metadata, mvp-phase-0]
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 1
conductor_workspace: gr-mvp-wave1-metadata
complexity: 4
depends_on: []
---

# Task: Add metadata block to existing seeding episodes

## Description

Update all existing Graphiti seeding functions to include a standardized `_metadata` block in each episode. This is the foundation for all subsequent features as it enables tracking of episode source, version, and update timestamps.

## Acceptance Criteria

- [ ] All seeding functions in `src/guardkit/integrations/graphiti/seeding.py` include `_metadata` block
- [ ] Metadata includes: `source`, `version`, `created_at`, `updated_at`, `source_hash`
- [ ] Existing episodes can be identified by their metadata for upsert operations
- [ ] Tests pass with metadata validation
- [ ] No breaking changes to existing seeding functionality

## Implementation Notes

### Metadata Schema

```python
_metadata = {
    "source": "guardkit_seeding",  # or "user_added", "auto_captured"
    "version": "1.0.0",
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
    "source_hash": None,  # For file-based content
    "entity_id": None,    # For deduplication
}
```

### Files to Modify

- `src/guardkit/integrations/graphiti/seeding.py` - All seeding functions
- `src/guardkit/integrations/graphiti/client.py` - add_episode method

### Integration Points

- This change is backward compatible - existing episodes without metadata continue to work
- New episodes will always have metadata
- Metadata enables future upsert logic (TASK-GR-PRE-003)

## Test Requirements

- [ ] Unit tests for metadata structure validation
- [ ] Integration test verifying metadata is stored in Graphiti
- [ ] Test that existing seeding still works

## Notes

This is the first task in the Graphiti Refinement MVP. It must be completed before any other tasks in this feature.

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)
- [FEAT-GR-PRE-000 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-000-seeding-metadata-update.md)
