---
id: TASK-FIX-77b2
title: Parallelise episode seeding within groups using bounded asyncio.gather
status: completed
task_type: implementation
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T13:00:00Z
completed: 2026-03-04T13:00:00Z
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
priority: low
tags: [graphiti, falkordb, init, performance, parallelism]
complexity: 5
parent_review: TASK-REV-BAC1
feature_id: FEAT-init-graphiti-remaining-fixes
test_results:
  status: passed
  total: 132
  passed: 132
  failed: 0
  skipped: 4
  last_run: 2026-03-04T12:30:00Z
---

# Task: Parallelise episode seeding within groups using bounded asyncio.gather

## Description

Currently all episodes seed sequentially. Episodes within the same group (e.g., 12 rules) could be parallelised using `asyncio.gather` with a semaphore to bound concurrency.

## Root Cause (from TASK-REV-BAC1)

Step 2.5 takes ~1,523s (25 min) for 16 items, averaging ~95s each. The items are independent (no ordering dependency between rules), so bounded parallelism could reduce wall-clock time by 60%.

## Approach

1. Add `max_concurrent_episodes` config option (default: 3)
2. In `template_sync.py`, wrap rule syncing in `asyncio.Semaphore`-bounded gather
3. In `template_sync.py`, wrap agent syncing similarly
4. Keep project_overview episodes sequential (they're ordered sections of CLAUDE.md)
5. Keep cross-group ordering sequential (Step 2 before Step 2.5)

```python
async def sync_rules_parallel(rule_files, template_id, client, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def sync_with_semaphore(rule_file):
        async with semaphore:
            return await sync_rule_to_graphiti(rule_file, template_id, client)

    results = await asyncio.gather(
        *[sync_with_semaphore(f) for f in rule_files],
        return_exceptions=True,
    )
    return results
```

## Trade-offs

- **Pro**: Step 2.5 time: ~1,523s → ~600-800s (-50-60%)
- **Con**: Parallel seeding grows graph faster, potentially increasing per-episode times
- **Con**: OpenAI rate limits may be hit with too much parallelism (need bounded concurrency)
- **Con**: Circuit breaker tracking becomes more complex with parallel failures

## Files to Modify

- `guardkit/knowledge/template_sync.py` — rule and agent syncing loops
- `guardkit/knowledge/graphiti_client.py` — circuit breaker may need thread-safe counter

## Expected Impact

- Step 2.5 time: 1,523s → ~600-800s
- Total init time: ~39 min → ~25-30 min
- OpenAI API call pattern changes (burst instead of sequential)

## Acceptance Criteria

- [x] Semaphore-bounded parallel rule syncing (configurable max_concurrent)
- [x] Semaphore-bounded parallel agent syncing
- [x] Project overview episodes remain sequential
- [x] Circuit breaker handles parallel failures correctly
- [x] OpenAI rate limit errors handled gracefully (retry with backoff)
- [x] Existing tests updated and pass
- [x] Integration test: parallel syncing produces same graph as sequential

## Dependencies

- Should be implemented AFTER TASK-FIX-3921 (skip re-seeding) for maximum benefit
- Parallel seeding with upsert is more efficient than parallel seeding with full re-processing
