---
id: TASK-FIX-23DB
title: Fix feature orchestrator test fixture frontmatter
status: completed
task_type: fix
created: 2026-03-07T00:00:00Z
updated: 2026-03-07T00:00:00Z
completed: 2026-03-07T00:00:00Z
priority: high
tags: [testing, fixtures, pre-flight-validation]
complexity: 2
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-07T00:00:00Z
---

# Task: Fix feature orchestrator test fixture frontmatter

## Description

2 pre-existing test failures in `tests/unit/test_feature_orchestrator.py` caused by missing `task_type` and `complexity` fields in task file frontmatter written by the `temp_repo` fixture.

The pre-flight validator (`guardkit/orchestrator/feature_validator.py`) requires `REQUIRED_FRONTMATTER_FIELDS = ("id", "title", "task_type", "complexity")` in task files, but the `temp_repo` fixture only writes `id`, `title`, and `status`.

## Failing Tests

1. `test_setup_phase_updates_execution_state` - calls `_setup_phase()` which triggers pre-flight validation
2. One other test that exercises the same code path

Both fail with:
```
FeatureValidationError: PRE-FLIGHT VALIDATION FAILED
3 task(s) have invalid frontmatter:
  TASK-T-001: Missing required field 'task_type'
  TASK-T-001: Missing required field 'complexity'
  TASK-T-002: Missing required field 'task_type'
  ...
```

## Root Cause

The `temp_repo` fixture at line 205-207 creates task files with:
```python
f"---\nid: {task.id}\ntitle: {task.name}\nstatus: pending\n---\n"
```

Missing: `task_type` and `complexity` fields.

## Fix

Update the `temp_repo` fixture to include `task_type` and `complexity` in the frontmatter:
```python
task_file.write_text(
    f"---\nid: {task.id}\ntitle: {task.name}\nstatus: pending\n"
    f"task_type: feature\ncomplexity: {task.complexity}\n---\n\n"
    f"# {task.name}\n\nTask content."
)
```

## Acceptance Criteria

- [x] Both failing tests pass
- [x] No other tests regress
- [x] All 98 tests in test_feature_orchestrator.py pass

## Implementation Notes

Simple fixture data fix — complexity 2/10.
