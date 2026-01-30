---
id: TASK-GF-36F5
title: Fix Graphiti async event loop issue using single event loop pattern
status: in_review
created: 2026-01-29T14:35:00Z
updated: 2026-01-29T14:35:00Z
priority: high
tags: [graphiti, async, neo4j, refactoring, cli]
complexity: 5
parent_review: TASK-GV-A8F3
related_tasks:
  - TASK-GV-A8F3
  - TASK-GC-72AF
---

# Task: Fix Graphiti async event loop issue using single event loop pattern

## Description

Refactor the Graphiti CLI commands to use a single event loop per command invocation, fixing the "Future attached to a different loop" error that causes all search queries to fail.

**Root Cause** (from TASK-GV-A8F3 review):
- The `_run_async()` helper creates a new event loop via `asyncio.run()` for each call
- graphiti-core's Neo4j driver maintains Futures tied to the initialization loop
- When `search()` runs in a different loop than `initialize()`, Futures fail

## Solution Approach

Replace the current `_run_async()` pattern with a single async function per command:

**Before (broken)**:
```python
@graphiti.command()
def verify(verbose: bool):
    client, settings = _get_client_and_config()
    initialized = _run_async(client.initialize())  # Loop A
    results = _run_async(client.search(...))       # Loop B → FAILS
```

**After (fixed)**:
```python
async def _cmd_verify(verbose: bool):
    client, settings = _get_client_and_config()
    try:
        await client.initialize()    # Same loop
        results = await client.search(...)  # Same loop → WORKS
    finally:
        await client.close()

@graphiti.command()
def verify(verbose: bool):
    asyncio.run(_cmd_verify(verbose))
```

## Acceptance Criteria

- [x] Remove `_run_async()` helper function
- [x] Refactor `seed` command to single async pattern
- [x] Refactor `status` command to single async pattern
- [x] Refactor `verify` command to single async pattern
- [x] Refactor `seed-adrs` command to single async pattern
- [x] Ensure proper resource cleanup with try/finally
- [x] All existing CLI tests pass
- [ ] `guardkit graphiti verify` returns search results (not 0 for all queries)
- [ ] `guardkit graphiti seed --force && guardkit graphiti verify` workflow succeeds

## Files to Modify

- `guardkit/cli/graphiti.py` - Refactor all 4 commands

## Test Plan

1. **Unit tests**: Ensure CLI commands can be invoked (mocked graphiti-core)
2. **Integration test**: With Neo4j running:
   ```bash
   guardkit graphiti seed --force
   guardkit graphiti verify --verbose
   ```
   Expected: Search queries return results, no "different loop" errors

## Review Reference

Full analysis: [.claude/reviews/TASK-GV-A8F3-review-report.md](.claude/reviews/TASK-GV-A8F3-review-report.md)

## Notes

- This fix also ensures seeding works correctly (same async pattern issue)
- graphiti-core documentation recommends single `asyncio.run(main())` pattern
- Resource management (close()) now happens in finally blocks
