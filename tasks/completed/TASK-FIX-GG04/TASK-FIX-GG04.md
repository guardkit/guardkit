---
id: TASK-FIX-GG04
title: "Fix docstring examples showing await on sync get_graphiti()"
status: completed
task_type: implementation
created: 2026-02-08T22:00:00Z
updated: 2026-02-08T22:00:00Z
completed: 2026-02-08T22:05:00Z
completed_location: tasks/completed/TASK-FIX-GG04/
priority: low
parent_review: TASK-REV-DE4F
feature_id: FEAT-GG-001
tags: [graphiti, documentation, cleanup, gap-closure]
complexity: 1
wave: 2
dependencies: []
---

# Fix Docstring Examples Showing await on Sync get_graphiti()

## Description

Two docstring examples still show `graphiti = await get_graphiti()`, which is incorrect since `get_graphiti()` is now a synchronous function (returns directly, no await needed). While these don't cause bugs (docstrings aren't executed), they could mislead developers.

## Changes Required

### File 1: `guardkit/knowledge/task_analyzer.py:188`

```python
# Before (in docstring Example section)
graphiti = await get_graphiti()

# After
graphiti = get_graphiti()
```

### File 2: `guardkit/knowledge/job_context_retriever.py:315`

```python
# Before (in docstring Example section)
graphiti = await get_graphiti()

# After
graphiti = get_graphiti()
```

## Key Files

- `guardkit/knowledge/task_analyzer.py` - Line 188
- `guardkit/knowledge/job_context_retriever.py` - Line 315

## Acceptance Criteria

- [x] Both docstrings updated to show sync `get_graphiti()` call
- [x] No functional changes

## Test Requirements

- None (docstring-only change)
