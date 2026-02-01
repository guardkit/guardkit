---
complexity: 5
conductor_workspace: gr-mvp-wave5-upsert
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-003-B
feature_id: FEAT-GR-MVP
id: TASK-GR-PRE-003-C
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- upsert
- mvp-phase-1
task_type: feature
title: Implement upsert_episode logic
updated: 2026-02-01T14:00:00Z
wave: 5
implementation_completed: 2026-02-01T14:00:00Z
test_results:
  passed: 32
  failed: 0
  coverage_estimate: 85-90%
---

# Task: Implement upsert_episode logic

## Description

Implement upsert logic for episodes that handles creating new episodes or updating existing ones based on entity_id. The strategy depends on PRE-003-A research findings.

## Acceptance Criteria

- [x] upsert_episode() creates new episode if not exists
- [x] upsert_episode() updates existing episode if found
- [x] Updates preserve created_at, modify updated_at
- [x] Handles concurrent updates gracefully
- [x] Returns result indicating create/update action
- [x] Backward compatible with add_episode

## Implementation Notes

### Method Signature

```python
async def upsert_episode(
    self,
    content: str,
    group_id: str,
    entity_id: str,
    source: str = "user_added",
    entity_type: str = "generic",
    metadata: Optional[EpisodeMetadata] = None,
    **kwargs
) -> UpsertResult:
    """Create or update an episode.

    Args:
        content: Episode content
        group_id: Group for the episode
        entity_id: Stable identifier for upsert
        source: Source type
        entity_type: Entity type
        metadata: Optional metadata override

    Returns:
        UpsertResult with action (created/updated) and episode info
    """
    pass
```

### Implementation Strategy (based on PRE-003-A)

```python
async def upsert_episode(self, content: str, group_id: str, entity_id: str, ...) -> UpsertResult:
    # 1. Check if exists
    exists_result = await self.episode_exists(entity_id, group_id)

    # 2. Prepare metadata
    source_hash = hashlib.sha256(content.encode()).hexdigest()

    if exists_result.exists:
        # Strategy depends on PRE-003-A findings
        # Option A: Native upsert
        # Option B: Invalidate + create
        # Option C: Delete + create

        if exists_result.exact_match:
            # Content unchanged, skip update
            return UpsertResult(action="skipped", episode=exists_result.episode)

        # Update with new content
        metadata = EpisodeMetadata.create_now(
            source=source,
            entity_type=entity_type,
            entity_id=entity_id,
            source_hash=source_hash,
            created_at=exists_result.episode.metadata.created_at,  # Preserve
        )
        # ... perform update based on strategy
        return UpsertResult(action="updated", episode=new_episode)

    else:
        # Create new
        metadata = EpisodeMetadata.create_now(
            source=source,
            entity_type=entity_type,
            entity_id=entity_id,
            source_hash=source_hash,
        )
        episode = await self.add_episode(content, group_id, metadata=metadata)
        return UpsertResult(action="created", episode=episode)
```

### Files to Modify

- `src/guardkit/integrations/graphiti/client.py` - Add upsert_episode

## Test Requirements

- [x] Unit tests for create path
- [x] Unit tests for update path
- [x] Unit tests for skip path (unchanged content)
- [ ] Integration tests with Graphiti (optional - requires Neo4j)

## Implementation Summary

### Files Created

1. **UpsertResult Dataclass** (`guardkit/integrations/graphiti/upsert_result.py`)
   - Structured result format with `action` field (created/updated/skipped)
   - Factory methods: `created()`, `updated()`, `skipped()`
   - Boolean helpers: `was_created`, `was_updated`, `was_skipped`
   - Tracks `previous_uuid` for update operations

2. **Unit Tests** (`tests/unit/integrations/graphiti/test_upsert_result.py`)
   - 18 tests covering all factory methods and edge cases

3. **Unit Tests** (`tests/unit/knowledge/test_upsert_episode.py`)
   - 14 tests covering create/update/skip paths, timestamp handling, graceful degradation

### Files Modified

1. **GraphitiClient** (`guardkit/knowledge/graphiti_client.py`)
   - Added `upsert_episode()` method (lines 730-879)
   - Uses "invalidate + create" strategy from PRE-003-A research
   - Preserves `created_at` on updates, sets `updated_at`
   - Content deduplication via SHA-256 source_hash

### Test Results

- 32 tests passed (18 UpsertResult + 14 upsert_episode)
- 0 tests failed
- Estimated coverage: 85-90%

## Notes

Most complex prerequisite task. Strategy determined by PRE-003-A research.

## References

- [FEAT-GR-PRE-003 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)