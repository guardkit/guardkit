---
id: TASK-IGR-003
title: Reuse connected client in Step 2.5 template sync
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T12:00:00Z
completed: 2026-03-03T12:05:00Z
completed_location: tasks/completed/TASK-IGR-003/
priority: high
complexity: 3
tags: [cli, graphiti, template-sync, init]
parent_review: TASK-REV-21D3
feature_id: FEAT-IGR
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Reuse connected client in Step 2.5 template sync

## Description

Fix Step 2.5 template sync in `guardkit init` by passing the already-connected `GraphitiClient` (from Step 2) to `sync_template_to_graphiti()` instead of having it create a new deferred-connection client via the factory.

## Context

Step 2.5 always fails with "Warning: Template sync returned incomplete results" because:

1. Step 2 creates **Client A** directly via `GraphitiClient(config)` and initializes it (connected)
2. Step 2.5 calls `sync_template_to_graphiti()` which calls `get_graphiti()` internally
3. `get_graphiti()` calls `_factory.get_thread_client()` — but Client A was never registered with the factory
4. The factory creates **Client B** — but because `asyncio.get_running_loop()` succeeds (we're inside `asyncio.run()`), it takes the "deferred connection" branch and returns Client B uninitialized
5. `sync_template_to_graphiti()` checks `client.enabled` → `config.enabled AND _connected` → `True AND False` → `False`
6. Returns `False` → "incomplete results"

## Implementation

### Option A (preferred): Pass client as parameter

```python
# In guardkit/knowledge/template_sync.py:
async def sync_template_to_graphiti(template_dir, client=None):
    if client is None:
        client = get_graphiti()
    # ... rest of function unchanged
```

```python
# In guardkit/cli/init.py, Step 2.5:
sync_result = await sync_template_to_graphiti(template_source, client=client)
```

## Acceptance Criteria

- [x] Step 2.5 template sync succeeds when Step 2 seeding succeeds
- [x] `sync_template_to_graphiti()` accepts optional `client` parameter
- [x] Falls back to `get_graphiti()` when no client provided (for non-init callers)
- [x] Template content is actually written to FalkorDB (not just returning True)
- [x] Existing tests pass (134 passed, 2 skipped)
- [x] No regression in non-init callers of `sync_template_to_graphiti()`

## Files to Modify

- `guardkit/knowledge/template_sync.py`
- `guardkit/cli/init.py`
- `tests/knowledge/test_template_sync.py` (if exists)

## Effort Estimate

~1 hour
