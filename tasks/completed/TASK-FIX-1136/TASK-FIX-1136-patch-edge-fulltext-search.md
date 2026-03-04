---
id: TASK-FIX-1136
title: Patch edge_fulltext_search O(n×m) query pattern
status: completed
updated: 2026-03-04T00:00:00Z
completed: 2026-03-04T00:00:00Z
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
task_type: implementation
created: 2026-03-04T00:00:00Z
priority: critical
tags: [graphiti, falkordb, performance, workaround, upstream-bug]
complexity: 6
parent_review: TASK-REV-1F78
feature_id: FEAT-falkordb-timeout-fixes
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Patch edge_fulltext_search O(n×m) query pattern

## Description

Add a third monkey-patch to `guardkit/knowledge/falkordb_workaround.py` that fixes the O(n×m) query pattern in graphiti-core's `edge_fulltext_search` method. This is the primary root cause of the 64 query timeouts during `guardkit init`.

## Root Cause (from TASK-REV-1F78)

graphiti-core's edge fulltext search uses:
```cypher
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
  YIELD relationship AS rel, score
  MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)  -- O(n×m) re-MATCH
```

The re-MATCH scans ALL edges for each fulltext result. With 1500 fulltext results and 5000 edges, this produces 7.5M comparisons, taking 26-118 seconds instead of 2ms.

Upstream issue: https://github.com/getzep/graphiti/issues/1272

## Fix

Replace the re-MATCH with direct endpoint access:
```cypher
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
  YIELD relationship AS e, score
  WITH e, score, startNode(e) AS n, endNode(e) AS m  -- O(n) direct access
```

## Implementation Approach

1. Locate the `edge_fulltext_search` method in graphiti-core's FalkorDB driver (site-packages)
2. Add `apply_edge_fulltext_workaround()` to `falkordb_workaround.py` following the existing pattern
3. Monkey-patch the method to use `startNode(e)/endNode(e)` instead of re-MATCH
4. Also check and patch `edge_bfs_search` which has the same pattern per #1272
5. Call the new workaround from `apply_falkordb_workaround()`
6. Add `remove_edge_fulltext_workaround()` for testing
7. Add `is_edge_fulltext_workaround_applied()` for inspection

## Files to Modify

- `guardkit/knowledge/falkordb_workaround.py` — add workaround 3
- `tests/knowledge/test_falkordb_workaround.py` — add tests

## Acceptance Criteria

- [x] `edge_fulltext_search` monkey-patch applied at startup
- [x] `edge_bfs_search` monkey-patch applied if same pattern exists
- [x] Workaround is idempotent (safe to call multiple times)
- [x] Workaround checks upstream source before patching (skip if already fixed)
- [x] Remove function provided for testing
- [x] Unit tests pass (40/40)
- [ ] Manual verification: `guardkit init fastapi-python` completes Step 2.5 without timeouts

## Expected Impact

Edge fulltext queries: 26-118s → ~3ms per query. Eliminates root cause of 64 timeouts.
