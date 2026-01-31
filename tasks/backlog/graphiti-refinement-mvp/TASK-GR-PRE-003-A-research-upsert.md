---
id: TASK-GR-PRE-003-A
title: Research graphiti-core upsert capabilities
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-31T15:00:00Z
priority: high
tags:
  - graphiti
  - research
  - upsert
  - mvp-phase-1
task_type: documentation
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 3
conductor_workspace: gr-mvp-wave3-research
complexity: 3
depends_on:
  - TASK-GR-PRE-000-C
---

# Task: Research graphiti-core upsert capabilities

## Description

Research graphiti-core's native capabilities for episode update/upsert operations. This determines the implementation strategy for PRE-003-B and PRE-003-C.

**Note**: Changed from `implementation_mode: manual` to `task-work` per TASK-GR-REV-001 findings. AI can research graphiti-core docs/source and create ADR output.

## Acceptance Criteria

- [ ] Document graphiti-core's native upsert capabilities
- [ ] Identify if temporal versioning (valid_at/invalid_at) can be used
- [ ] Document API for invalidating old episodes
- [ ] Propose implementation strategy based on findings
- [ ] Create ADR for upsert approach

## Research Questions

1. Does graphiti-core support native episode upsert?
2. How does temporal versioning work in graphiti-core?
3. Can we invalidate old episodes and create new ones?
4. What are the performance implications of each approach?
5. How do we handle concurrent updates?

## Implementation Notes

### Research Areas

```python
# Check graphiti-core documentation and source for:
# 1. Episode update methods
graphiti.update_episode(...)

# 2. Temporal versioning
graphiti.add_episode(..., valid_at=..., invalid_at=...)

# 3. Invalidation
graphiti.invalidate_episode(...)

# 4. Deduplication
graphiti.episode_exists(...)
```

### Potential Strategies

1. **Native Upsert** (if supported)
   - Use graphiti-core's built-in upsert
   - Simplest approach

2. **Invalidate + Create**
   - Mark old episode as invalid
   - Create new episode
   - Maintains history

3. **Delete + Create**
   - Delete old episode
   - Create new episode
   - Loses history

### Output

Create ADR document at:
`docs/adr/ADR-GR-001-upsert-strategy.md`

## Test Requirements

- [ ] N/A - research task outputs documentation only

## Notes

Output informs PRE-003-B and PRE-003-C implementation decisions.

## References

- [FEAT-GR-PRE-003 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)
- graphiti-core documentation
- graphiti-core source code
