---
id: TASK-FB-DEL1
title: Enable Task-Work Delegation in AutoBuildOrchestrator
status: completed
task_type: implementation
created: 2026-01-09T22:00:00Z
updated: 2026-01-09T22:30:00Z
completed: 2026-01-09T22:35:00Z
priority: critical
tags: [feature-build, autobuild, delegation, bug-fix, critical-path]
complexity: 2
parent_review: TASK-REV-fb02
implementation_mode: task-work
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria verified"
completed_location: tasks/completed/TASK-FB-DEL1/
organized_files: ["TASK-FB-DEL1.md"]
---

# Enable Task-Work Delegation in AutoBuildOrchestrator

## Problem

The `AutoBuildOrchestrator` creates `AgentInvoker` instances without enabling task-work delegation. This causes the Player agent to use legacy direct SDK invocation, which doesn't create `task_work_results.json`. The Coach validator then fails with "Task-work results not found" on every turn.

**Root Cause**: Missing `use_task_work_delegation=True` parameter in 3 locations.

## Requirements

1. Add `use_task_work_delegation=True` to all `AgentInvoker()` instantiations in `autobuild.py`
2. Ensure delegation is enabled for both new and resumed orchestrations
3. Verify Coach validator can find `task_work_results.json` after fix

## Acceptance Criteria

- [x] `AgentInvoker` created with `use_task_work_delegation=True` at line ~636 (existing worktree path)
- [x] `AgentInvoker` created with `use_task_work_delegation=True` at line ~654 (new worktree path)
- [x] `AgentInvoker` created with `use_task_work_delegation=True` at line ~1878 (resume path)
- [x] Unit test verifies `use_task_work_delegation` is `True` for all paths
- [x] Existing tests continue to pass

## Implementation Summary

**Completed**: 2026-01-09

### Changes Made

1. **guardkit/orchestrator/autobuild.py** - Added `use_task_work_delegation=True` to all 3 `AgentInvoker()` instantiations:
   - Line 640: Existing worktree path
   - Line 659: New worktree creation path
   - Line 1884: Resume orchestration path

2. **tests/unit/test_autobuild_orchestrator.py** - Added `test_setup_phase_initializes_agent_invoker_with_delegation` test that:
   - Patches `AgentInvoker` class to capture constructor arguments
   - Verifies `use_task_work_delegation=True` is passed

### Test Results

- All 41 autobuild orchestrator tests pass
- New delegation test specifically verifies the fix

## Notes

- This is the **critical path fix** for the AutoBuild feature
- Previous fixes (TASK-FB-RPT1, TASK-FB-PATH1) are correct but weren't reached
- After this fix, the full delegation architecture will be active
- Low risk change - only adds a parameter, doesn't change logic

## Related

- Review: TASK-REV-fb02 (parent review)
- Previous fixes: TASK-FB-RPT1, TASK-FB-PATH1, TASK-FB-TIMEOUT1
- Architecture: TASK-REV-0414 (Option D: task-work delegation design)
