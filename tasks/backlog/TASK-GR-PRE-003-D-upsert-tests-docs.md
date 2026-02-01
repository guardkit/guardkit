---
id: TASK-GR-PRE-003-D
title: Tests and documentation for upsert
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: medium
tags: [graphiti, testing, documentation, mvp-phase-1]
task_type: testing
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: direct
wave: 5
conductor_workspace: gr-mvp-wave5-upsert
complexity: 3
depends_on:
  - TASK-GR-PRE-003-C
---

# Task: Tests and documentation for upsert

## Description

Create comprehensive tests and documentation for the episode upsert logic (PRE-003-A through PRE-003-C).

## Acceptance Criteria

- [ ] Unit tests for episode_exists
- [ ] Unit tests for upsert_episode (all paths)
- [ ] Integration tests for full upsert workflow
- [ ] Documentation for upsert behavior
- [ ] ADR finalized with implementation notes

## Implementation Notes

### Test Files

- `tests/unit/integrations/graphiti/test_episode_exists.py`
- `tests/unit/integrations/graphiti/test_upsert_episode.py`
- `tests/integration/graphiti/test_upsert_integration.py`

### Documentation Files

- `docs/deep-dives/graphiti/episode-upsert.md` - New file
- Update `docs/adr/ADR-GR-001-upsert-strategy.md` with implementation notes

### Test Scenarios

1. Create new episode (not exists)
2. Update existing episode (content changed)
3. Skip update (content unchanged)
4. Handle missing entity_id
5. Handle concurrent updates
6. Verify metadata preservation (created_at)

## Test Requirements

- [ ] 80%+ coverage for upsert code
- [ ] Integration tests pass

## Notes

Final task in Phase 1 (prerequisites complete after this).

## References

- [FEAT-GR-PRE-003 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)
