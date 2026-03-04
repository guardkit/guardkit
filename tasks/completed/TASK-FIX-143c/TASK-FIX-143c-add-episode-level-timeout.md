---
id: TASK-FIX-143c
title: Add episode-level timeout to graphiti client
status: completed
updated: 2026-03-04T00:00:00Z
completed: 2026-03-04T00:00:00Z
task_type: implementation
created: 2026-03-04T00:00:00Z
priority: medium
tags: [graphiti, timeout, resilience]
complexity: 3
parent_review: TASK-REV-1F78
feature_id: FEAT-falkordb-timeout-fixes
wave: 2
implementation_mode: task-work
dependencies: [TASK-FIX-1136]
---

# Task: Add episode-level timeout to graphiti client

## Description

Wrap each `add_episode()` call in `asyncio.wait_for()` with a 120-second timeout. This prevents a single episode from blocking indefinitely. Currently, individual episodes can take 153+ seconds with no upper bound.

## Implementation

In `graphiti_client.py:_create_episode()`, wrap the graphiti-core call:

```python
result = await asyncio.wait_for(
    self._graphiti.add_episode(
        name=name,
        episode_body=episode_body,
        source=EpisodeType.text,
        source_description=f"GuardKit knowledge seeding: {name}",
        reference_time=datetime.now(timezone.utc),
        group_id=group_id
    ),
    timeout=120.0  # 2 minutes max per episode
)
```

Also catch `asyncio.TimeoutError` in the retry loop and treat it as a non-retryable failure (retrying a timed-out episode is unlikely to succeed).

## Files to Modify

- `guardkit/knowledge/graphiti_client.py` — add wait_for in _create_episode
- `tests/knowledge/test_graphiti_client.py` — add timeout test

## Acceptance Criteria

- [x] Each add_episode call has 120s timeout
- [x] asyncio.TimeoutError caught and logged
- [x] Timed-out episodes count toward circuit breaker
- [x] Tests pass
