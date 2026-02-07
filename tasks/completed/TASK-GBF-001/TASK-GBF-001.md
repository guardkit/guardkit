---
id: TASK-GBF-001
title: Unify episode serialization pattern across entities
status: completed
created: 2026-02-07T12:00:00Z
updated: 2026-02-07T15:30:00Z
completed: 2026-02-07T15:30:00Z
priority: medium
tags: [graphiti, refactoring, consistency]
parent_review: TASK-REV-C632
feature_id: FEAT-GBF
complexity: 4
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-07T15:30:00Z
previous_state: in_review
state_transition_reason: "Task completed - 34 tests passing, all acceptance criteria met"
completed_location: tasks/completed/TASK-GBF-001/
---

# Task: Unify Episode Serialization Pattern

## Description

The review (TASK-REV-C632, Finding 6) identified a dual serialization path for Graphiti episodes:

1. **Entity-level**: Entities define `to_episode_body()` methods that produce dicts with embedded `_metadata` blocks
2. **Client-level**: `GraphitiClient._inject_metadata()` also injects metadata into episode content

This creates subtle inconsistency - some episodes get metadata from the entity, some from the client, and some from both. The two paths could diverge as the codebase evolves.

## Objectives

- [ ] Audit all entity `to_episode_body()` implementations for metadata field consistency
- [ ] Audit all `add_episode()` / `upsert_episode()` call sites for metadata injection patterns
- [ ] Define a single canonical pattern (either entity-level OR client-level, not both)
- [ ] Refactor to use the canonical pattern consistently
- [ ] Ensure all episodes include the standard metadata fields: `entity_id`, `source`, `source_hash`, `entity_type`, `created_at`, `updated_at`

## Scope

### In Scope
- `guardkit/knowledge/entities/*.py` - Entity `to_episode_body()` methods
- `guardkit/knowledge/graphiti_client.py` - `_inject_metadata()` method
- `guardkit/knowledge/seeding.py` - Seeding episode creation
- All `*_manager.py` and `*_operations.py` files that create episodes

### Out of Scope
- CLI layer (no changes needed)
- Context loading layer (reads, doesn't write)

## Acceptance Criteria

1. All episodes use a single, documented serialization pattern
2. No episode is missing any standard metadata field
3. Existing tests continue to pass
4. New test verifying metadata consistency across entity types
