---
id: TASK-GR-PRE-002-C
title: Update add_episode to include metadata
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, metadata, client, mvp-phase-1]
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 4
conductor_workspace: gr-mvp-wave4-episode
complexity: 3
depends_on:
  - TASK-GR-PRE-002-A
  - TASK-GR-PRE-002-B
---

# Task: Update add_episode to include metadata

## Description

Modify the GraphitiClient.add_episode() method to automatically include standardized metadata in every episode added to Graphiti.

## Acceptance Criteria

- [ ] add_episode() accepts optional EpisodeMetadata parameter
- [ ] Metadata is auto-generated if not provided
- [ ] Metadata is merged into episode content correctly
- [ ] Existing callers continue to work (backward compatible)
- [ ] Metadata is stored in `_metadata` key of episode

## Implementation Notes

### Updated Method Signature

```python
async def add_episode(
    self,
    content: str,
    group_id: str,
    source: str = "user_added",
    entity_type: str = "generic",
    metadata: Optional[EpisodeMetadata] = None,
    **kwargs
) -> AddEpisodeResult:
    """Add episode with automatic metadata."""

    # Generate metadata if not provided
    if metadata is None:
        metadata = EpisodeMetadata.create_now(
            source=source,
            entity_type=entity_type,
            project_id=self.project_id,
        )

    # Inject metadata into content
    episode_content = self._inject_metadata(content, metadata)

    # Call Graphiti
    return await self._graphiti.add_episode(
        episode_content,
        group_id=self.get_group_id(group_id),
        **kwargs
    )
```

### Metadata Injection

```python
def _inject_metadata(self, content: str, metadata: EpisodeMetadata) -> str:
    """Inject metadata block into episode content."""
    metadata_block = f"\n\n_metadata: {json.dumps(metadata.to_dict())}"
    return content + metadata_block
```

### Files to Modify

- `src/guardkit/integrations/graphiti/client.py` - Update add_episode

## Test Requirements

- [ ] Unit tests for metadata injection
- [ ] Unit tests for auto-generation
- [ ] Integration test with Graphiti

## Notes

Depends on PRE-002-A and PRE-002-B completing first.

## References

- [FEAT-GR-PRE-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-002-episode-metadata-schema.md)
