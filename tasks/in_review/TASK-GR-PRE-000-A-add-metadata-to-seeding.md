---
complexity: 4
conductor_workspace: gr-mvp-wave1-metadata
created: 2026-01-30 00:00:00+00:00
depends_on: []
feature_id: FEAT-GR-MVP
id: TASK-GR-PRE-000-A
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- seeding
- metadata
- mvp-phase-0
task_type: feature
title: Add metadata block to existing seeding episodes
updated: 2026-01-30T22:30:00+00:00
wave: 1
implementation:
  completed_at: 2026-01-30T22:30:00+00:00
  mode: tdd
  phases_completed: [3, 4, 4.5, 5]
  test_results:
    total: 48
    passed: 46
    skipped: 2
    failed: 0
  coverage:
    line: 82
    branch: 67
  code_review_score: 97
---

# Task: Add metadata block to existing seeding episodes

## Description

Update all existing Graphiti seeding functions to include a standardized `_metadata` block in each episode. This is the foundation for all subsequent features as it enables tracking of episode source, version, and update timestamps.

## Acceptance Criteria

- [x] All seeding functions in `guardkit/knowledge/seeding.py` include `_metadata` block
- [x] Metadata includes: `source`, `version`, `created_at`, `updated_at`, `source_hash`, `entity_id`
- [x] Existing episodes can be identified by their metadata for upsert operations
- [x] Tests pass with metadata validation
- [x] No breaking changes to existing seeding functionality

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

- [x] Unit tests for metadata structure validation (9 new tests in TestMetadataBlock)
- [x] Integration test verifying metadata is stored in Graphiti (test_all_seeding_functions_include_metadata)
- [x] Test that existing seeding still works (46 tests passed, 0 regressions)

## Notes

This is the first task in the Graphiti Refinement MVP. It must be completed before any other tasks in this feature.

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)
- [FEAT-GR-PRE-000 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-000-seeding-metadata-update.md)