---
id: TASK-ISF-001
title: Revert parallel sync to sequential in template_sync.py
status: completed
priority: critical
complexity: 2
parent_review: TASK-REV-C043
feature_id: FEAT-ISF
wave: 1
implementation_mode: task-work
tags: [revert, graphiti, init, reliability]
completed: 2026-03-04T00:00:00Z
completed_location: tasks/completed/TASK-ISF-001/
---

# TASK-ISF-001: Revert Parallel Sync to Sequential

## Problem

`_sync_items_parallel()` in `template_sync.py` uses `asyncio.Semaphore` + `asyncio.gather()` to sync agents and rules concurrently. This interacts badly with the circuit breaker: parallel timeouts accumulate failures faster than sequential successes can reset the counter, causing cascade failure (0/12 rules synced in init_project_7 vs 10/12 in init_project_6).

## Solution

Revert the agent and rule sync calls from `_sync_items_parallel()` back to sequential for-loops.

**Keep** the `_sync_items_parallel()` function in the file — it's well-implemented and can be re-enabled when the circuit breaker is made parallel-aware (e.g., per-batch reset).

## Files Changed

- `guardkit/knowledge/template_sync.py` — Lines ~327-352: Replaced parallel `_sync_items_parallel()` calls with sequential for-loops

## Acceptance Criteria

- [x] Agent sync uses sequential for-loop (not `_sync_items_parallel`)
- [x] Rule sync uses sequential for-loop (not `_sync_items_parallel`)
- [x] `_sync_items_parallel()` function remains in file (unused)
- [x] Existing tests in `tests/knowledge/test_template_sync.py` pass (63 passed, 2 skipped)
- [x] No new regressions in agent/rule sync logic

## Completion Notes

Reverted agent and rule sync from `_sync_items_parallel()` (asyncio.gather with semaphore) back to sequential for-loops. The `_sync_items_parallel()` function is preserved at line 149 for future re-enablement when the circuit breaker is made parallel-aware.
