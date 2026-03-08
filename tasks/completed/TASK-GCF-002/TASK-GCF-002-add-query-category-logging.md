---
id: TASK-GCF-002
title: Add logging to _query_category exception handler
status: completed
updated: 2026-03-08T16:05:00Z
completed: 2026-03-08T16:05:00Z
previous_state: in_progress
task_type: implementation
priority: high
tags: [graphiti, observability, context-loading]
complexity: 1
parent_review: TASK-REV-982B
feature_id: FEAT-GCF
wave: 1
implementation_mode: direct
dependencies: []
created: 2026-03-08T15:00:00Z
---

# Task: Add logging to _query_category exception handler

## Problem

`_query_category()` in `job_context_retriever.py` (lines 996-998) has a bare `except Exception` that silently returns `[], 0`. This makes it impossible to diagnose search failures — connection timeouts, query syntax errors, and FalkorDB internal errors are all invisible.

## Requirements

1. Add `logger.warning()` to the exception handler in `_query_category()` that logs the category name and the exception
2. Keep the graceful degradation behaviour (still return `[], 0`)
3. Apply the same fix to `_query_turn_states()` if it has the same pattern

## Files to Modify

- `guardkit/knowledge/job_context_retriever.py` (lines ~996-998 and similar patterns)

## Implementation

```python
except Exception as e:
    logger.warning(
        "[Graphiti] Category '%s' query failed: %s", category, e
    )
    return [], 0
```

## Acceptance Criteria

- [x] `_query_category()` logs warnings on exception with category name and error
- [x] `_query_turn_states()` logs warnings on exception similarly
- [x] Graceful degradation preserved (returns `[], 0`)
- [x] Existing tests pass
