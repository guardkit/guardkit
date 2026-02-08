---
id: TASK-FIX-GCW2
title: Add INFO-level log when context retrieval is skipped
status: completed
task_type: implementation
created: 2026-02-08T16:30:00Z
updated: 2026-02-08T17:00:00Z
completed: 2026-02-08T17:05:00Z
priority: medium
parent_review: TASK-REV-8BD8
tags: [observability, autobuild, logging]
complexity: 1
wave: 1
completed_location: tasks/completed/TASK-FIX-GCW2/
---

# Add INFO-Level Log When Context Retrieval Is Skipped

## Description

When `enable_context=True` but `_context_loader is None`, the context retrieval guard silently skips with no log output. Operators cannot distinguish "not called at all" from "called but found nothing".

From review TASK-REV-8BD8, Finding 5 and Recommendation R3.

## Changes Required

At `guardkit/orchestrator/autobuild.py:2573` (Player guard), add an `else` branch:
```python
if self.enable_context and self._context_loader is not None:
    # ... existing retrieval code ...
elif self.enable_context:
    logger.info(f"Player context retrieval skipped: context_loader not provided for {task_id}")
```

Same pattern at line ~2724 (Coach guard):
```python
if self.enable_context and self._context_loader is not None:
    # ... existing retrieval code ...
elif self.enable_context:
    logger.info(f"Coach context retrieval skipped: context_loader not provided for {task_id}")
```

## Acceptance Criteria

- [x] INFO log emitted when `enable_context=True` but `_context_loader is None` (Player)
- [x] INFO log emitted when `enable_context=True` but `_context_loader is None` (Coach)
- [x] No log emitted when `enable_context=False`
- [x] Existing tests still pass
- [x] Unit test verifying skip log is emitted

## Files Modified

- `guardkit/orchestrator/autobuild.py` — Added 2 `elif self.enable_context:` branches with INFO logs (lines 2602, 2762)
- `tests/unit/test_autobuild_context_integration.py` — Added `TestContextSkipLogging` class with 3 tests
