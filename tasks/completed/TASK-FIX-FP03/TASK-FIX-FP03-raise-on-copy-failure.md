---
id: TASK-FIX-FP03
title: Raise exception on task copy failure in _copy_tasks_to_worktree
status: completed
created: 2026-02-10T12:00:00Z
updated: 2026-02-10T12:00:00Z
completed: 2026-02-10T13:00:00Z
completed_location: tasks/completed/TASK-FIX-FP03/
priority: medium
tags: [bug-fix, fail-fast, defensive]
task_type: feature
parent_review: TASK-REV-1BE3
feature_id: FEAT-FP-FIX
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
---

# Task: Raise exception on task copy failure in _copy_tasks_to_worktree

## Description

`_copy_tasks_to_worktree()` at `feature_orchestrator.py:670-675` logs a warning when `file_path` parsing fails but does not raise an exception. This allows execution to continue into the Player-Coach loop where every turn fails with the same `TaskNotFoundError`, wasting turns until stall detection terminates the run.

## Changes Required

**File**: `guardkit/orchestrator/feature_orchestrator.py:656-675`

Replace the warning-only returns with `FeatureValidationError` raises for the path-parsing failures:

```python
except ValueError:
    raise FeatureValidationError(
        f"Invalid task file_path '{task_file_path}' in task {first_task.id}. "
        f"Expected format: tasks/backlog/<feature-slug>/TASK-XXX.md. "
        f"Ensure --feature-slug was passed to generate-feature-yaml."
    )
```

Apply the same pattern to the other early-return warning cases at lines 646-649, 662-665, and 667-670.

**Note**: The per-file copy failure warnings at line 719-722 should remain as warnings since individual file failures are recoverable.

## Acceptance Criteria

- [x] Path-parsing failures in `_copy_tasks_to_worktree()` raise `FeatureValidationError`
- [x] Error messages include the bad `file_path` value and the expected format
- [x] Individual file copy failures (line ~719) remain as warnings (recoverable)
- [x] Tests verify that invalid file_path patterns raise exceptions
- [x] Tests verify that valid file_path patterns still work

## Evidence

- Warning path: `guardkit/orchestrator/feature_orchestrator.py:670-675`
- Log line 23: `WARNING:guardkit.orchestrator.feature_orchestrator:Cannot copy tasks: 'tasks' directory not found in path: .`
- After warning, 3 turns wasted before UNRECOVERABLE_STALL

## Completion Summary

**Files modified**: 2
- `guardkit/orchestrator/feature_orchestrator.py` (lines 645-683): Replaced 4 `logger.warning()` + `return` with `raise FeatureValidationError()`. Narrowed `try/except ValueError` to only cover `parts.index("tasks")` since `FeatureValidationError` extends `ValueError`.
- `tests/unit/test_feature_orchestrator_task_copy.py`: Updated 1 existing test, added 5 new tests.

**Tests**: 11/11 passing (5 existing + 6 new/updated)
**Regressions**: None
