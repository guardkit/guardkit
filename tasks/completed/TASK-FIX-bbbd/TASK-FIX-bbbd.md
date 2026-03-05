---
id: TASK-FIX-bbbd
title: Return episode counts from _add_episodes for accurate seed summary
status: completed
task_type: implementation
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
completed: 2026-03-04T00:00:00Z
priority: medium
tags: [graphiti, seeding, logging, observability]
complexity: 2
parent_review: TASK-REV-49AB
feature_id: FEAT-SQF
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Return episode counts from _add_episodes for accurate seed summary

## Description

The seed orchestrator (`seeding.py:167`) logs `"Seeded {name}"` for every category, even when the circuit breaker silently blocked all episodes (returning None instead of raising). This gives a misleading impression that all categories were successfully seeded.

Fix `_add_episodes()` to return `(created_count, skipped_count)` and update the orchestrator to use these counts in its summary logging.

## Root Cause (from TASK-REV-49AB)

1. `seeding.py:162-170`: `seed_fn(client)` returns normally even when all episodes return None
2. `seed_helpers.py:44-50`: `add_episode()` returns None when circuit breaker blocks, no exception raised
3. `seeding.py:167`: `logger.info(f"  Seeded {name}")` executes unconditionally when no exception occurs
4. Result: category appears "seeded" with 0 actual episodes created

## Changes

### File 1: `guardkit/knowledge/seed_helpers.py`

```python
# BEFORE:
async def _add_episodes(
    client,
    episodes: list,
    group_id: str,
    category_name: str,
    entity_type: str = "generic"
) -> None:
    ...
    for name, body in episodes:
        try:
            await client.add_episode(...)
        except Exception as e:
            logger.warning(f"Failed to seed episode {name}: {e}")

# AFTER:
async def _add_episodes(
    client,
    episodes: list,
    group_id: str,
    category_name: str,
    entity_type: str = "generic"
) -> tuple[int, int]:
    """Returns (created_count, skipped_count)."""
    ...
    created = 0
    skipped = 0
    for name, body in episodes:
        try:
            result = await client.add_episode(...)
            if result is not None:
                created += 1
            else:
                skipped += 1
        except Exception as e:
            logger.warning(f"Failed to seed episode {name}: {e}")
            skipped += 1
    return (created, skipped)
```

### File 2: `guardkit/knowledge/seeding.py` (orchestrator loop)

```python
# BEFORE (lines 162-167):
for name, fn_name in categories:
    try:
        seed_fn = getattr(seeding_module, fn_name)
        await seed_fn(client)
        logger.info(f"  Seeded {name}")

# AFTER:
for name, fn_name in categories:
    try:
        seed_fn = getattr(seeding_module, fn_name)
        result = await seed_fn(client)
        # Log with episode counts if available
        if isinstance(result, tuple) and len(result) == 2:
            created, skipped = result
            if skipped > 0:
                logger.warning(f"  Seeded {name}: {created}/{created + skipped} episodes ({skipped} skipped)")
            else:
                logger.info(f"  Seeded {name}: {created} episodes")
        else:
            logger.info(f"  Seeded {name}")
```

### File 3: Update all `seed_*.py` callers

Each `seed_*.py` module that calls `_add_episodes()` must propagate the return value. Most seed functions currently return None — they should return the tuple from `_add_episodes()`.

**Callers to update** (grep for `_add_episodes`):
- `seed_templates.py:158`
- `seed_rules.py` (if exists)
- `seed_agents.py` (if exists)
- All other `seed_*.py` modules using `_add_episodes`

## Regression Risk

**Low** — signature change from `-> None` to `-> tuple[int, int]`. All callers must be updated. Existing callers that ignore the return value will still work (Python doesn't enforce return type usage), but the orchestrator loop needs to handle both old (None) and new (tuple) returns for backwards compatibility during transition.

## Acceptance Criteria

- [ ] `_add_episodes()` returns `(created_count, skipped_count)` tuple
- [ ] `add_episode()` result is checked for None (circuit breaker skip) vs not-None (success)
- [ ] Orchestrator loop logs accurate episode counts per category
- [ ] Skipped episodes produce a warning-level log (not info)
- [ ] All `seed_*.py` callers of `_add_episodes` propagate the return value
- [ ] Existing tests updated for new return type
- [ ] New test: verify circuit-breaker-blocked episodes are counted as skipped
