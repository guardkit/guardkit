---
id: TASK-FIX-GCW3
title: Auto-initialize AutoBuildContextLoader when enable_context=True
status: completed
task_type: implementation
created: 2026-02-08T16:30:00Z
updated: 2026-02-08T17:00:00Z
completed: 2026-02-08T17:00:00Z
priority: high
parent_review: TASK-REV-8BD8
tags: [autobuild, graphiti, context-retrieval]
complexity: 3
wave: 2
dependencies: [TASK-FIX-GCW1, TASK-FIX-GCW2]
---

# Auto-Initialize AutoBuildContextLoader When enable_context=True

## Description

Instead of requiring callers to construct and pass `AutoBuildContextLoader`, have `AutoBuildOrchestrator.__init__()` auto-create one when `enable_context=True` and no `context_loader` is provided. This eliminates the "last mile" wiring gap identified in TASK-REV-8BD8.

From review TASK-REV-8BD8, Recommendation R5 (this replaces R1 as the primary fix).

## Changes Required

In `AutoBuildOrchestrator.__init__()`, after storing `self._context_loader = context_loader` at line ~552:

```python
# Auto-initialize context_loader if enable_context=True and no loader provided
if self.enable_context and self._context_loader is None:
    try:
        from guardkit.knowledge import get_graphiti, AutoBuildContextLoader
        graphiti = get_graphiti()
        if graphiti and graphiti.enabled:
            self._context_loader = AutoBuildContextLoader(
                graphiti=graphiti, verbose=self.verbose
            )
            logger.info("Auto-initialized context_loader with Graphiti")
        else:
            logger.info("Graphiti not available, context retrieval disabled")
    except ImportError:
        logger.info("Graphiti dependencies not installed, context retrieval disabled")
    except Exception as e:
        logger.info(f"Could not auto-initialize context_loader: {e}")
```

**Note:** `get_graphiti()` is already sync (returns the singleton client or None). No need for `get_graphiti_sync()` wrapper.

## Acceptance Criteria

- [x] When `enable_context=True` and Graphiti is available, `_context_loader` is auto-initialized
- [x] When Graphiti is unavailable, logs INFO and continues without context
- [x] When `context_loader` is explicitly provided, auto-init is skipped (DI takes precedence)
- [x] When `enable_context=False`, no auto-init attempted
- [x] Existing unit tests still pass (they provide mock context_loader via DI)
- [x] New unit tests for auto-init behavior (with/without Graphiti)
- [x] No import errors if graphiti dependencies are not installed

## Files Modified

- `guardkit/orchestrator/autobuild.py` (~15 lines in `__init__`, line 555-570)
- `tests/unit/test_autobuild_context_integration.py` (10 new tests in `TestAutoInitContextLoader`)

## Implementation Notes

- Used `get_graphiti()` (already sync) instead of creating `get_graphiti_sync()`
- Added `graphiti.enabled` check to handle case where singleton exists but is not connected
- Three graceful degradation paths: None/not-enabled, ImportError, generic Exception
- All 27 tests pass (17 existing + 10 new), no regressions
