---
id: TASK-FIX-A34C
title: Add recursion depth guard for Graphiti FalkorDB searches
status: completed
created: 2026-03-27T00:00:00Z
updated: 2026-03-27T00:00:00Z
completed: 2026-03-27T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-A34C/
priority: low
tags: [graphiti, falkordb, resilience, autobuild]
parent_review: TASK-REV-CFE0
feature_id: FEAT-CFE0
implementation_mode: task-work
wave: 1
complexity: 3
---

# Task: Add Recursion Depth Guard for Graphiti FalkorDB Searches

## Description

During the FEAT-5AC9 autobuild run (11 tasks, Agent Factories feature), Graphiti search requests failed with "maximum recursion depth exceeded" after 3 consecutive search attempts. The system degraded gracefully (continued without knowledge graph context), but the underlying issue should be investigated and guarded against.

The recursion depth error likely originates in the FalkorDB workaround patches applied at `guardkit/knowledge/falkordb_workaround.py` (edge_fulltext_search, edge_bfs_search patches for O(n) startNode/endNode).

## Acceptance Criteria

- [x] Investigate the recursion depth error path in `falkordb_workaround.py` patches
- [x] Add `sys.setrecursionlimit` guard or iterative alternative if recursion is in our patches
- [x] If recursion is in upstream `graphiti-core` or `falkordb` driver, document the issue and add a try/except guard with logging
- [x] Add a test that triggers the recursion path (if reproducible) or a defensive test for the guard
- [x] Graphiti context loading continues to degrade gracefully when this error occurs (existing behavior preserved)

## Key Files

- `guardkit/knowledge/falkordb_workaround.py` (monkey-patches for FalkorDB compatibility)
- `guardkit/knowledge/graphiti_client.py` (client factory and connection)
- `guardkit/knowledge/autobuild_context_loader.py` (context loading with retry/fallback)

## Evidence

From FEAT-5AC9 run log:
- Graphiti search failed with "maximum recursion depth exceeded"
- System disabled Graphiti after 3 consecutive failures
- Remaining tasks ran without knowledge context (0 categories, 0 tokens)
- Feature still completed 11/11 tasks successfully

## Notes

This is a low-priority resilience improvement. The current graceful degradation is adequate. This task is about understanding the root cause and adding a targeted guard, not a major rework.
