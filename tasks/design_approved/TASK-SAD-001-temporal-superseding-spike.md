---
complexity: 4
dependencies: []
feature_id: FEAT-SAD
id: TASK-SAD-001
implementation_mode: task-work
parent_review: TASK-REV-AEE1
status: design_approved
task_type: feature
title: Temporal superseding spike — verify Graphiti upsert behaviour
wave: 1
---

# Task: Temporal superseding spike — verify Graphiti upsert behaviour

## Description

Verify that Graphiti's `upsert_episode()` with stable `entity_id` allows prior versions to remain queryable after an update. This spike determines whether Option A (soft superseding via data-level encoding) is sufficient for `/arch-refine` and `/design-refine`, or whether native graph edge support is needed.

## Acceptance Criteria

- [ ] Write a pytest test that calls `upsert_episode()` twice with the same `entity_id` and different content
- [ ] Verify whether the old content is still retrievable via semantic search
- [ ] Verify whether the old content is retrievable via entity_id metadata search
- [ ] Document findings: does Graphiti preserve old episodes or overwrite them?
- [ ] If overwriting: implement Option A (create new episode with next ADR number, set status=superseded on original)
- [ ] Write a recommendation doc confirming the chosen temporal superseding mechanism
- [ ] Results documented in `docs/architecture/decisions/ADR-ARCH-001-temporal-superseding-mechanism.md`

## Implementation Notes

- Use existing `GraphitiClient` from `guardkit/knowledge/graphiti_client.py`
- Test against local FalkorDB instance (whitestocks:6379)
- The existing upsert strategy (ADR-GR-001) uses "invalidate + create" with SHA-256 source_hash deduplication
- Test should be placed in `tests/knowledge/test_temporal_superseding.py`
- This spike blocks `/arch-refine` and `/design-refine` command spec work