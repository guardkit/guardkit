---
id: TASK-FIX-FD03
title: Pre-initialize Graphiti factory before parallel task dispatch
status: completed
created: 2026-02-09T22:00:00Z
updated: 2026-02-10T00:00:00Z
priority: medium
tags: [fix, graphiti, factory, race-condition, initialization, parallel]
task_type: implementation
complexity: 2
feature: null
parent_review: TASK-REV-B9E1
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-10T00:00:00Z
  tests_added: 8
  tests_total: 74
---

# Task: Pre-initialize Graphiti Factory Before Parallel Task Dispatch

## Description

Fix BUG-4 from TASK-REV-B9E1: No `init_graphiti()` call exists before parallel task dispatch, causing a race condition where the first task's `AutoBuildOrchestrator.__init__()` triggers lazy initialization while other parallel tasks see `factory=None`.

### Problem (BUG-4: Factory Initialization Race Condition)

`FeatureOrchestrator._execute_task()` creates an `AutoBuildOrchestrator` per task. In `AutoBuildOrchestrator.__init__()` (autobuild.py:595-613), the constructor calls `get_graphiti()` to trigger lazy factory init via `_try_lazy_init()`. However:

1. All Wave 1 tasks start in parallel via `asyncio.to_thread()`
2. Worker threads have no running asyncio event loop (they're plain threads from ThreadPoolExecutor)
3. `_try_lazy_init()` detects this and performs initialization, but there's a race window
4. SP-002 started before the factory was ready → `factory=None` → no Graphiti context
5. SP-001 started after → `factory=available` → Graphiti context loaded

Evidence from logs: SP-002 shows `factory=None`, SP-001 shows `factory=available`.

### Solution

Call `init_graphiti()` in `FeatureOrchestrator` BEFORE dispatching parallel tasks:

```python
# In FeatureOrchestrator._execute_wave_parallel() or __init__()
if self.enable_context:
    try:
        from guardkit.knowledge import init_graphiti
        init_graphiti()
        logger.info("Pre-initialized Graphiti factory for parallel execution")
    except Exception as e:
        logger.warning(f"Failed to pre-initialize Graphiti: {e}")
```

This ensures the global factory is created before any worker threads call `get_factory()`.

## Acceptance Criteria

- [ ] `init_graphiti()` called before `asyncio.to_thread()` dispatches any tasks
- [ ] Call guarded by `self.enable_context` check (skip when Graphiti disabled)
- [ ] Graceful degradation on init failure (log WARNING, continue without context)
- [ ] All parallel workers see `factory=available` (no more `factory=None` in Wave 1)
- [ ] Unit tests: verify init called before dispatch, verify no-op when context disabled, verify error handling
- [ ] No regressions in existing FeatureOrchestrator tests

## Key Files

- `guardkit/orchestrator/feature_orchestrator.py` — `_execute_wave_parallel()` or `__init__()`
- `tests/unit/test_feature_orchestrator.py` — New tests

## Context

- Review: TASK-REV-B9E1 (P2 fix, BUG-4)
- Review report: `.claude/reviews/TASK-REV-B9E1-review-report.md` Section 7b
- `init_graphiti()` exists in `guardkit/knowledge/__init__.py` — it calls `_try_lazy_init()` which creates the `GraphitiClientFactory` singleton
- The factory is module-level (`_factory`) and thread-safe for reads (created once, then only read by workers)

## Dependencies

None — independent of TASK-FIX-FD01 and TASK-FIX-FD02, can be done in parallel.
