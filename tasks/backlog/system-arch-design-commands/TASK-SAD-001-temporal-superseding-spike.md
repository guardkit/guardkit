---
id: TASK-SAD-001
title: "Temporal superseding spike \u2014 verify Graphiti upsert behaviour"
task_type: feature
parent_review: TASK-REV-AEE1
feature_id: FEAT-SAD
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-E4F5
  base_branch: main
  started_at: '2026-03-01T17:38:40.215022'
  last_updated: '2026-03-01T17:43:50.626223'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-03-01T17:38:40.215022'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
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
