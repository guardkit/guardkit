---
id: TASK-FB-FIX-007
title: Fix Pre-Loop Path Resolution for Worktree Context
status: completed
created: 2026-01-11T17:00:00Z
updated: 2026-01-11T19:30:00Z
completed: 2026-01-11T19:30:00Z
priority: critical
tags: [feature-build, autobuild, pre-loop, path-resolution, bug-fix]
complexity: 3
parent_task: TASK-REV-FB07
implementation_mode: task-work
estimated_effort: 1-2 hours
previous_state: in_review
state_transition_reason: "Task completed - all quality gates passed, 62/62 tests passing"
completed_location: tasks/completed/TASK-FB-FIX-007/
---

# TASK-FB-FIX-007: Fix Pre-Loop Path Resolution for Worktree Context

## Problem Statement

The pre_loop validation fails to find the implementation plan because it checks relative paths against the main repository's working directory instead of resolving them against the worktree where the plan was actually created.

**Current Behavior** (broken):
```python
# pre_loop.py:249-250
plan_file = Path(plan_path)  # "docs/state/TASK-XXX/implementation_plan.md" (relative)
if not plan_file.exists():   # Checks /main/repo/docs/state/... (WRONG!)
    raise QualityGateBlocked(...)
```

**Expected Behavior**:
```python
plan_file = Path(plan_path)
if not plan_file.is_absolute():
    plan_file = self.worktree_path / plan_file  # Resolve to worktree
if not plan_file.exists():  # Checks /main/repo/.guardkit/worktrees/TASK-XXX/docs/state/...
    raise QualityGateBlocked(...)
```

## Root Cause

From TASK-REV-FB07 analysis:

1. SDK invokes `/task-work --design-only` with `cwd=worktree_path`
2. `plan_persistence.py` saves plan using relative path: `docs/state/{task_id}/implementation_plan.md`
3. Plan is created at: `{worktree}/docs/state/TASK-XXX/implementation_plan.md`
4. SDK output parsing extracts the relative path correctly
5. Pre_loop validates with `Path(plan_path).exists()` - relative to main repo CWD
6. **FAILS** because plan exists in worktree, not main repo

## Solution

Modified `_extract_pre_loop_results()` in `pre_loop.py` to:

1. Resolve relative paths against `self.worktree_path`
2. Use `TaskArtifactPaths.find_implementation_plan()` as fallback
3. Ensure returned path is always absolute

## Acceptance Criteria

- [x] Relative plan paths are resolved against worktree directory
- [x] Fallback search uses TaskArtifactPaths for robustness
- [x] Unit test verifies relative path resolution works correctly
- [x] No regression in existing pre_loop tests (62/62 tests pass)
- [x] Feature-build completes successfully with test task (plan found)

## Implementation Summary

### File Modified

`guardkit/orchestrator/quality_gates/pre_loop.py`

### Changes Made

1. **Added import for TaskArtifactPaths** (line 236):
   ```python
   from guardkit.orchestrator.paths import TaskArtifactPaths
   ```

2. **Added relative path resolution** (lines 241-249):
   ```python
   # Resolve relative paths against worktree
   if plan_path:
       plan_file = Path(plan_path)
       if not plan_file.is_absolute():
           plan_file = self.worktree_path / plan_file
           logger.debug(f"Resolved relative plan path to: {plan_file}")
       plan_path = str(plan_file)
   ```

3. **Added fallback search** (lines 251-258):
   ```python
   # Fallback: Search all known locations if SDK path not found or doesn't exist
   if not plan_path or not Path(plan_path).exists():
       found_plan = TaskArtifactPaths.find_implementation_plan(
           task_id, self.worktree_path
       )
       if found_plan:
           plan_path = str(found_plan)
           logger.info(f"Found plan at fallback location: {plan_path}")
   ```

4. **Fixed return statement** (line 299):
   ```python
   plan_path=plan_path,  # Use resolved path, not original result.plan_path
   ```

### Unit Tests Added

`tests/unit/test_pre_loop_delegation.py` - TestRelativePathResolution class (5 tests):

1. `test_resolves_relative_path_against_worktree` - Verifies relative paths become absolute
2. `test_absolute_path_unchanged` - Verifies absolute paths remain unchanged
3. `test_fallback_search_when_resolved_path_not_found` - Verifies fallback to TaskArtifactPaths
4. `test_fallback_search_when_sdk_returns_none` - Verifies fallback when SDK returns None
5. `test_raises_when_no_plan_found_anywhere` - Verifies error when plan not found

## Test Results

```
======================== 62 passed, 1 warning in 1.28s =========================
```

All existing tests continue to pass, plus 5 new tests for the fix.

## Related Tasks

- TASK-REV-FB07: Parent review task (this fix addresses root cause)
- TASK-FB-FIX-001 through TASK-FB-FIX-006: Previous fixes that led to this discovery

## Notes

This is the 7th fix in the feature-build series. Previous fixes addressed:
- SDK configuration (setting_sources)
- Message parsing (ContentBlock extraction)
- SDK invocation (subprocess → SDK)

This fix addresses the final piece: **path resolution context**.

## Completion Summary

- **Duration**: ~2.5 hours (within estimated 1-2 hours)
- **Tests Added**: 5 new tests in TestRelativePathResolution class
- **Tests Passing**: 62/62 (100%)
- **Files Modified**: 1 (guardkit/orchestrator/quality_gates/pre_loop.py)
- **Quality Gates**: All passed
