---
id: TASK-FIX-d457
title: Fix add_episode return value checking in sync functions
status: completed
completed: 2026-03-04T00:00:00Z
task_type: implementation
created: 2026-03-04T00:00:00Z
priority: high
tags: [graphiti, template-sync, error-handling]
complexity: 2
parent_review: TASK-REV-1F78
feature_id: FEAT-falkordb-timeout-fixes
wave: 2
implementation_mode: direct
dependencies: []
---

# Task: Fix add_episode return value checking in sync functions

## Description

`sync_rule_to_graphiti()` and `sync_agent_to_graphiti()` don't check the return value of `client.add_episode()`. When `add_episode()` returns `None` (failure), the sync functions still log success messages. This produced 5 misleading "Synced rule X" messages during the init run.

## Current Code (template_sync.py:479-487)

```python
await client.add_episode(
    name=f"rule_{template_id}_{rule_name}",
    episode_body=json.dumps(rule_body),
    group_id="rules",
    source="template_sync",
    entity_type="rule"
)
logger.info(f"[Graphiti] Synced rule '{rule_name}'")
return True
```

## Target Code

```python
result = await client.add_episode(
    name=f"rule_{template_id}_{rule_name}",
    episode_body=json.dumps(rule_body),
    group_id="rules",
    source="template_sync",
    entity_type="rule"
)
if result is None:
    logger.warning(f"[Graphiti] Failed to sync rule '{rule_name}' (episode creation returned None)")
    return False
logger.info(f"[Graphiti] Synced rule '{rule_name}'")
return True
```

Apply the same pattern to `sync_agent_to_graphiti()` (line 380-387).

## Files to Modify

- `guardkit/knowledge/template_sync.py` — both sync functions
- `tests/knowledge/test_template_sync.py` — add tests for None return handling

## Acceptance Criteria

- [x] `sync_rule_to_graphiti()` checks add_episode return value
- [x] `sync_agent_to_graphiti()` checks add_episode return value
- [x] Failed syncs log WARNING instead of INFO
- [x] Failed syncs return False
- [x] Sync summary counts reflect actual successes
- [x] Tests pass
