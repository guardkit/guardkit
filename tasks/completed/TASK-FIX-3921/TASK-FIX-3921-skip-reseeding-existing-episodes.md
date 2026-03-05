---
id: TASK-FIX-3921
title: Skip re-seeding unchanged episodes when using --copy-graphiti-from
status: completed
task_type: implementation
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
completed: 2026-03-04T00:00:00Z
priority: medium
tags: [graphiti, falkordb, init, performance, upsert]
complexity: 5
parent_review: TASK-REV-BAC1
feature_id: FEAT-init-graphiti-remaining-fixes
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-04T00:00:00Z
  tests_passed: 127
  tests_skipped: 2
---

# Task: Skip re-seeding unchanged episodes when using --copy-graphiti-from

## Description

When `guardkit init` is run with `--copy-graphiti-from`, the FalkorDB graph already contains data from the previous init. Currently, `seed_project_knowledge()` and `sync_template_to_graphiti()` re-seed ALL episodes, forcing graphiti-core to deduplicate against itself — wasting LLM calls and creating the graph-size scaling problem.

Use the existing `upsert_episode()` method (already in GraphitiClient) to skip episodes whose content hasn't changed.

## Root Cause (from TASK-REV-BAC1)

The `--copy-graphiti-from` amplification effect: each init copies cumulative graph data, making the next init start with ~150+ edges. Re-seeding unchanged content forces O(edges × graph_size) deduplication for zero benefit.

## Approach

1. In `project_seeding.py`, replace `client.add_episode()` calls with `client.upsert_episode()`, passing a stable `entity_id` derived from the episode name
2. In `template_sync.py`, do the same for template, agent, and rule syncing
3. `upsert_episode` already handles: check existence → compare content hash → skip if unchanged
4. Add logging: "Skipping unchanged episode: {name}" so user sees the time savings

## Files to Modify

- `guardkit/knowledge/project_seeding.py` — `seed_project_overview()`, `seed_implementation_modes_from_defaults()`, `_seed_role_constraints_wrapper()`
- `guardkit/knowledge/template_sync.py` — `sync_template_to_graphiti()`, `sync_agent_to_graphiti()`, `sync_rule_to_graphiti()`
- `guardkit/knowledge/seed_role_constraints.py` — `seed_role_constraints()`

## Expected Impact

- Re-init with unchanged content: ~39 min → ~5-10 min (most episodes skip)
- Re-init with changed content: only changed episodes re-seed
- Eliminates the --copy-graphiti-from amplification cycle
- Reduces OpenAI API costs by ~80% on re-init

## Acceptance Criteria

- [x] `seed_project_overview()` uses `upsert_episode()` with stable entity_id
- [x] `seed_implementation_modes_from_defaults()` uses `upsert_episode()`
- [x] `seed_role_constraints()` uses `upsert_episode()`
- [x] `sync_template_to_graphiti()` uses `upsert_episode()` for template, agents, rules
- [x] Logging shows "Skipping unchanged" for episodes that already exist
- [x] Fresh init (no --copy-graphiti-from) works unchanged
- [x] Re-init skips unchanged episodes correctly
- [x] Content changes are detected and re-seeded
- [x] Existing tests updated and pass
