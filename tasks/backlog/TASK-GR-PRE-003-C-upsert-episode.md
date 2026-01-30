---
id: TASK-GR-PRE-003-C
title: Implement upsert_episode logic
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, upsert, mvp-phase-1]
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 5
conductor_workspace: gr-mvp-wave5-upsert
complexity: 5
depends_on:
  - TASK-GR-PRE-003-B
---

# Task: Implement upsert_episode logic

## Description

Implement upsert logic for episodes that handles creating new episodes or updating existing ones based on entity_id. The strategy depends on PRE-003-A research findings.

## Acceptance Criteria

- [ ] upsert_episode() creates new episode if not exists
- [ ] upsert_episode() updates existing episode if found
- [ ] Updates preserve created_at, modify updated_at
- [ ] Handles concurrent updates gracefully
- [ ] Returns result indicating create/update action
- [ ] Backward compatible with add_episode

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

- [ ] Unit tests for create path
- [ ] Unit tests for update path
- [ ] Unit tests for skip path (unchanged content)
- [ ] Integration tests with Graphiti

## Notes

Most complex prerequisite task. Strategy determined by PRE-003-A research.

## References

- [FEAT-GR-PRE-003 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)
