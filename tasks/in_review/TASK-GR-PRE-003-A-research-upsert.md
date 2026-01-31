---
complexity: 3
conductor_workspace: gr-mvp-wave3-research
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-000-C
feature_id: FEAT-GR-MVP
id: TASK-GR-PRE-003-A
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- research
- upsert
- mvp-phase-1
task_type: documentation
title: Research graphiti-core upsert capabilities
updated: 2026-01-31T21:10:00+00:00
wave: 3
previous_state: in_progress
state_transition_reason: "All acceptance criteria met - documentation complete"
completed_at: 2026-01-31T21:10:00+00:00
---

# Task: Research graphiti-core upsert capabilities

## Description

Research graphiti-core's native capabilities for episode update/upsert operations. This determines the implementation strategy for PRE-003-B and PRE-003-C.

## Acceptance Criteria

- [x] Document graphiti-core's native upsert capabilities
- [x] Identify if temporal versioning (valid_at/invalid_at) can be used
- [x] Document API for invalidating old episodes
- [x] Propose implementation strategy based on findings
- [x] Create ADR for upsert approach

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

- [x] N/A - research task (documentation validated)

## Notes

This is a manual research task, not implementation. Output informs PRE-003-B and PRE-003-C.

## Deliverables

1. **ADR Document**: `docs/adr/ADR-GR-001-upsert-strategy.md`
   - Status: Accepted
   - Decision: Invalidate + Create pattern
   - Implementation details for PRE-003-B and PRE-003-C

2. **Research Document**: `docs/research/graphiti-refinement/RESEARCH-GR-PRE-003-A-upsert-capabilities.md`
   - Complete API reference
   - Temporal versioning analysis
   - Implementation recommendations

## Key Findings Summary

1. **No Native Upsert**: graphiti-core does not provide built-in upsert
2. **Limited Temporal**: valid_at exists but no invalid_at mechanism
3. **Deletion Available**: Neo4j DETACH DELETE can remove episodes
4. **Recommended Strategy**: Invalidate + Create with metadata-based identity matching

## References

- [FEAT-GR-PRE-003 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)
- graphiti-core documentation
- graphiti-core source code
