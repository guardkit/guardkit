---
id: TASK-GCF-001
title: Fix patterns group ID mismatch in JobContextRetriever
status: completed
updated: 2026-03-08T16:05:00Z
completed: 2026-03-08T16:05:00Z
completed_location: tasks/completed/TASK-GCF-001/
task_type: implementation
priority: high
tags: [graphiti, bugfix, context-loading]
complexity: 2
parent_review: TASK-REV-982B
feature_id: FEAT-GCF
wave: 1
implementation_mode: task-work
dependencies: []
created: 2026-03-08T15:00:00Z
---

# Task: Fix patterns group ID mismatch in JobContextRetriever

## Problem

`job_context_retriever.py` line 583 queries `patterns_{tech_stack}` (e.g., `patterns_python`), but `_group_defs.py` defines `patterns` as a SYSTEM group. Since `patterns_python` is not in either PROJECT or SYSTEM group lists, `is_project_group()` defaults to `True`, causing the query to search for `guardkit__patterns_python` — a namespace that doesn't exist. The seeded data lives under the system group `patterns` (no prefix).

## Requirements

1. Change the group ID query in `job_context_retriever.py` from `f"patterns_{tech_stack}"` to `"patterns"`
2. Ensure the search still works correctly with the `patterns` system group
3. Add a unit test verifying the correct group ID is used

## Files to Modify

- `guardkit/knowledge/job_context_retriever.py` (line ~583)
- `tests/knowledge/test_job_context_retriever.py` (add test)

## Acceptance Criteria

- [x] `patterns` group ID used instead of `patterns_{tech_stack}`
- [x] Unit test confirms correct group ID resolution
- [x] Existing tests pass
