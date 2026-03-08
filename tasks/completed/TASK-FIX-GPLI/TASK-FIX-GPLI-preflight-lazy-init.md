---
id: TASK-FIX-GPLI
title: Fix _preflight_check() to trigger Graphiti lazy initialization
status: completed
task_type: implementation
priority: critical
tags: [graphiti, autobuild, bug-fix, preflight]
complexity: 2
parent_review: TASK-REV-1509
feature_id: FEAT-VR3
wave: 1
implementation_mode: task-work
created: 2026-03-07T14:30:00Z
updated: 2026-03-07T14:30:00Z
completed: 2026-03-07T15:00:00Z
completed_location: tasks/completed/TASK-FIX-GPLI/
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-07T15:00:00Z
  tests_passed: 13
  tests_failed: 0
organized_files:
  - TASK-FIX-GPLI-preflight-lazy-init.md
  - completion-report.md
---

# Task: Fix _preflight_check() to Trigger Graphiti Lazy Initialization

## Problem

`FeatureOrchestrator._preflight_check()` at `feature_orchestrator.py:1195` calls `get_factory()` which is explicitly **non-lazy** — it returns the module-level `_factory` variable directly without triggering initialization. At preflight time, `_factory` is always `None` because no code path has called `init_graphiti()` or `get_graphiti()` yet.

The method that WOULD trigger lazy init (`_pre_init_graphiti()` via `get_graphiti()`) runs immediately after preflight in `_wave_phase()`, but by then preflight has already set `self.enable_context = False`, making pre-init a no-op.

This means **Graphiti context is silently disabled for every autobuild run**, even when FalkorDB is running and correctly configured.

## Root Cause

Call-order defect in `_wave_phase()` (lines 1285-1293):

```python
# Step 1: Calls get_factory() — non-lazy, returns None
self._preflight_check()        # → disables context

# Step 2: Calls get_graphiti() — lazy, WOULD init factory
self._pre_init_graphiti()      # → skipped (enable_context already False)
```

`get_factory()` docstring explicitly states: "Does NOT trigger lazy initialization — use get_graphiti() for that."

## Fix

In `_preflight_check()`, if `get_factory()` returns None, trigger lazy init via `get_graphiti()` before concluding the factory is unavailable.

### Exact Change

File: `guardkit/orchestrator/feature_orchestrator.py`, method `_preflight_check()`, around line 1194-1196:

**Before:**
```python
from guardkit.knowledge.graphiti_client import get_factory
factory = get_factory()
if factory is None or not factory.config.enabled:
```

**After:**
```python
from guardkit.knowledge.graphiti_client import get_factory, get_graphiti
factory = get_factory()
if factory is None:
    # Trigger lazy initialization — loads config from
    # .guardkit/graphiti.yaml, creates GraphitiClientFactory.
    # This is synchronous and does NOT create asyncio objects
    # (GLF-003: thread clients have pending_init=True).
    get_graphiti()
    factory = get_factory()
if factory is None or not factory.config.enabled:
```

### Why This Is Safe

- `get_graphiti()` → `_try_lazy_init()` is synchronous
- `_try_lazy_init()` creates `GraphitiClientFactory(config)` and calls `factory.get_thread_client()`
- Per GLF-003, `get_thread_client()` returns an uninitialized client (`pending_init=True`) — no temporary event loop, no `asyncio.Lock` creation
- The TCP connectivity check in `check_connectivity()` uses raw sockets, not asyncio
- No regression risk for the GLF-003/GLF-005 Lock contamination fixes

## Acceptance Criteria

- [x] AC-001: `_preflight_check()` calls `get_graphiti()` when `get_factory()` returns None
- [x] AC-002: After lazy init, `get_factory()` returns a valid `GraphitiClientFactory`
- [x] AC-003: Factory config loads from project's `.guardkit/graphiti.yaml` (falkordb_host=whitestocks)
- [x] AC-004: When FalkorDB is reachable, log shows "FalkorDB pre-flight TCP check passed"
- [x] AC-005: When FalkorDB is unreachable, graceful degradation still works (context disabled, no crash)
- [x] AC-006: No asyncio Lock contamination — verify no "Lock bound to different event loop" errors
- [x] AC-007: Existing unit tests for `_preflight_check()` still pass
- [x] AC-008: New unit test: mock `get_factory()` returning None, verify `get_graphiti()` called

## Test Plan

1. **Unit**: Mock `get_factory()` → None, verify `get_graphiti()` is called, then `get_factory()` retried
2. **Unit**: Mock `get_factory()` → valid factory, verify `get_graphiti()` NOT called (no redundant init)
3. **Unit**: After lazy init, verify factory.config has correct falkordb_host from config file
4. **Unit**: Verify graceful degradation when lazy init fails (import error, config missing)
5. **Integration**: Run autobuild with FalkorDB on whitestocks, verify "pre-flight TCP check passed"
6. **Regression**: Verify no Lock contamination in E2E run (GLF-003/005 concern)

## References

- Review report: `.claude/reviews/TASK-REV-1509-review-report.md` (Objective 2, revised)
- Bug location: `guardkit/orchestrator/feature_orchestrator.py:1194-1196`
- `get_factory()`: `guardkit/knowledge/graphiti_client.py:2173-2182`
- `get_graphiti()`: `guardkit/knowledge/graphiti_client.py:2146-2170`
- `_try_lazy_init()`: `guardkit/knowledge/graphiti_client.py:2089-2143`
- GLF-003 (deferred init): `tasks/completed/TASK-GLF-003/TASK-GLF-003.md`
- GLF-005 (lightweight ping): `tasks/completed/TASK-GLF-005/TASK-GLF-005-lightweight-health-check.md`
