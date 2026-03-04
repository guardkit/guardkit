---
id: TASK-FIX-72c1
title: Suppress vector embedding logging during template sync
status: completed
task_type: implementation
created: 2026-03-04T00:00:00Z
completed: 2026-03-04T12:00:00Z
priority: medium
tags: [graphiti, logging, ux]
complexity: 2
parent_review: TASK-REV-1F78
feature_id: FEAT-falkordb-timeout-fixes
wave: 2
implementation_mode: direct
dependencies: []
completed_location: tasks/completed/TASK-FIX-72c1/
---

# Task: Suppress vector embedding logging during template sync

## Description

graphiti-core's FalkorDB driver logs full query parameters (including 768-dimensional embedding vectors) at ERROR level when queries fail. During init, this produced 30 vector dumps totalling ~120KB of unreadable noise in the output.

## Fix

Temporarily set the `graphiti_core.driver.falkordb_driver` logger to WARNING level during sync operations. This suppresses ERROR-level query dumps while preserving GuardKit's own retry WARNING messages.

## Implementation

In `template_sync.py:sync_template_to_graphiti()`:

```python
# At start of function, after client validation:
falkordb_logger = logging.getLogger("graphiti_core.driver.falkordb_driver")
original_level = falkordb_logger.level
falkordb_logger.setLevel(logging.WARNING)
try:
    # ... existing sync operations ...
finally:
    falkordb_logger.setLevel(original_level)
```

## Files Modified

- `guardkit/knowledge/template_sync.py` — added logger level management in `sync_template_to_graphiti()`
- `tests/knowledge/test_template_sync.py` — added `TestFalkorDBLoggerSuppression` class (3 tests)

## Acceptance Criteria

- [x] FalkorDB driver ERROR logs suppressed during sync
- [x] GuardKit retry WARNING messages still visible
- [x] Logger level restored after sync (even on error)
- [x] No 768-dim vector arrays in init output

## Test Results

- 56 passed, 2 skipped
- 3 new tests covering logger suppression, restoration after error, and level during sync
