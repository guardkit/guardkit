---
id: TASK-FB-PATH1
title: Fix Coach Validator Path for Feature Mode
status: completed
task_type: implementation
created: 2026-01-09T12:00:00Z
completed: 2026-01-09T13:30:00Z
priority: critical
tags: [feature-build, autobuild, coach, path-resolution, bug-fix]
complexity: 4
parent_feature: feature-build-fixes
wave: 1
implementation_mode: task-work
conductor_workspace: feature-build-fixes-wave1-2
related_review: TASK-REV-FB01
completed_location: tasks/completed/TASK-FB-PATH1/
---

# Fix Coach Validator Path for Feature Mode

## Problem

When running in feature mode, the Coach validator constructs the path to `task_work_results.json` using the individual task ID instead of the shared feature worktree path.

**Evidence**:
```
WARNING: Task-work results not found at
/Users/.../feature_build_cli_test/.guardkit/worktrees/TASK-INFRA-001/.guardkit/autobuild/TASK-INFRA-001/task_work_results.json
```

**Expected Path**:
```
/Users/.../feature_build_cli_test/.guardkit/worktrees/FEAT-3DEB/.guardkit/autobuild/TASK-INFRA-001/task_work_results.json
```

## Root Cause

Coach validator constructs path as:
```python
worktrees_dir / task_id / ".guardkit" / "autobuild" / task_id / "task_work_results.json"
```

But in feature mode, the worktree is shared:
```python
worktrees_dir / feature_id / ".guardkit" / "autobuild" / task_id / "task_work_results.json"
```

The `worktree_path` parameter is available but not being used correctly for path construction.

## Requirements

1. Coach validator must use the actual worktree path, not construct it from task ID
2. Path construction must work in both single-task mode and feature (shared worktree) mode
3. Worktree path must be passed through the validation chain

## Acceptance Criteria

- [x] Coach finds `task_work_results.json` at correct path in feature mode
- [x] Coach finds `task_work_results.json` at correct path in single-task mode
- [x] Unit tests verify path construction in both modes
- [x] Integration test confirms validation succeeds when file exists

## Implementation Approach

### Change 1: Pass Worktree Path to Coach Validator

Modify `CoachValidator` to accept and use the actual worktree path:

```python
class CoachValidator:
    def __init__(self, worktree_path: Path, task_id: str, ...):
        self.worktree_path = worktree_path
        self.task_id = task_id

    def _get_task_work_results_path(self) -> Path:
        return self.worktree_path / ".guardkit" / "autobuild" / self.task_id / "task_work_results.json"
```

### Change 2: Update Callers to Pass Worktree Path

Ensure `AutoBuildOrchestrator` passes the worktree path when creating/calling Coach validator.

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Use worktree_path for path construction |
| `guardkit/orchestrator/coach_verification.py` | Pass worktree_path to validator |
| `guardkit/orchestrator/autobuild.py` | Ensure worktree_path flows through |
| `tests/unit/test_coach_validator.py` | Add tests for both modes |

## Technical Details

### Current Path Construction (Wrong)

```python
# Constructs path from task_id, ignoring actual worktree location
results_path = self.worktrees_dir / self.task_id / ".guardkit" / "autobuild" / self.task_id / "task_work_results.json"
```

### Correct Path Construction

```python
# Uses actual worktree path (which may be feature worktree)
results_path = self.worktree_path / ".guardkit" / "autobuild" / self.task_id / "task_work_results.json"
```

### Path Examples

| Mode | Worktree Path | Results Path |
|------|---------------|--------------|
| Single Task | `.guardkit/worktrees/TASK-001` | `.guardkit/worktrees/TASK-001/.guardkit/autobuild/TASK-001/task_work_results.json` |
| Feature Mode | `.guardkit/worktrees/FEAT-ABC` | `.guardkit/worktrees/FEAT-ABC/.guardkit/autobuild/TASK-001/task_work_results.json` |

## Test Plan

1. **Unit Test**: Verify path construction with task worktree
2. **Unit Test**: Verify path construction with feature worktree
3. **Unit Test**: Verify validation succeeds when file at correct path
4. **Integration Test**: Run Coach validation in feature mode, confirm success

## Estimated Effort

1 hour

## Dependencies

None - can be implemented in parallel with TASK-FB-RPT1

## Notes

- This fix is complementary to TASK-FB-RPT1 (Player report writing)
- Both fixes are required for feature-build to work
- Wave 1 tasks can run in parallel as they modify different files
