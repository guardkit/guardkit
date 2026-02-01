---
id: TASK-GR-PRE-003-B
title: Implement episode_exists method
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- upsert
- deduplication
- mvp-phase-1
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 4
conductor_workspace: gr-mvp-wave4-init
complexity: 3
depends_on:
- TASK-GR-PRE-003-A
- TASK-GR-PRE-002-A
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-01-31T20:48:08.064301'
  last_updated: '2026-01-31T20:59:07.045441'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-01-31T20:48:08.064301'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement episode_exists method

## Description

Implement a method to check if an episode already exists in Graphiti, enabling duplicate detection and upsert logic.

## Acceptance Criteria

- [ ] episode_exists() checks for existing episode by entity_id
- [ ] Uses source_hash for content-based deduplication
- [ ] Returns existing episode info if found
- [ ] Handles project namespace correctly
- [ ] Performance is acceptable (<100ms for typical case)

## Implementation Notes

### Method Signature

```python
async def episode_exists(
    self,
    entity_id: str,
    group_id: str,
    source_hash: Optional[str] = None
) -> ExistsResult:
    """Check if episode exists.

    Args:
        entity_id: Stable identifier for the episode
        group_id: Group to search in
        source_hash: Optional content hash for exact match

    Returns:
        ExistsResult with exists flag and episode info if found
    """
    pass
```

### Search Strategy

```python
# 1. Search by entity_id in metadata
query = f"entity_id:{entity_id}"
results = await self._search(query, group_id)

# 2. If source_hash provided, verify content match
if source_hash and results:
    for result in results:
        if result.metadata.source_hash == source_hash:
            return ExistsResult(exists=True, episode=result, exact_match=True)
    return ExistsResult(exists=True, episode=results[0], exact_match=False)

return ExistsResult(exists=False)
```

### Files to Modify

- `src/guardkit/integrations/graphiti/client.py` - Add episode_exists

## Test Requirements

- [ ] Unit tests for exists check
- [ ] Unit tests for source_hash matching
- [ ] Integration test with Graphiti

## Notes

Depends on PRE-003-A (research) completing to determine best approach.

## References

- [FEAT-GR-PRE-003 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)
