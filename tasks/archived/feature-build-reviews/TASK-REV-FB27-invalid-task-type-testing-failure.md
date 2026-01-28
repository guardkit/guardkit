---
id: TASK-REV-FB27
title: "Diagnose Invalid task_type 'testing' Causing Feature Build Failure"
status: review_complete
created: 2026-01-23T00:00:00Z
updated: 2026-01-23T00:00:00Z
priority: high
tags: [feature-build, coach-validator, task-types, bug-fix]
task_type: review
complexity: 4
related_tasks:
  - TASK-REV-FB26
review_results:
  findings_count: 5
  recommendations_count: 3
  decision: implement
  implementation_feature: FEAT-TT
  implementation_tasks:
    - TASK-TT-001
    - TASK-TT-002
    - TASK-TT-003
    - TASK-TT-004
    - TASK-TT-005
---

# Task: Diagnose Invalid task_type 'testing' Causing Feature Build Failure

## Context

This task follows TASK-REV-FB26 to diagnose why the feature build (`FEAT-A96D - FastAPI App with Health Endpoint`) failed on the final task (TASK-FHA-005 - "Set up testing infrastructure").

**Feature Build Results:**
- Wave 1: ✓ PASSED (3 tasks - project structure, config, app entry)
- Wave 2: ✓ PASSED (1 task - health module)
- Wave 3: ✗ FAILED (1 task - testing infrastructure)

**Result: 4/5 tasks completed, 1 failed after exhausting 5 turns**

## Root Cause Identified

From the debug logs in `/docs/reviews/feature-build/last_task_failed.md`:

```
ERROR:guardkit.orchestrator.quality_gates.coach_validator:Invalid task_type value: testing
ERROR:guardkit.orchestrator.quality_gates.coach_validator:Failed to resolve task type: Invalid task_type value: testing. Must be one of: scaffolding, feature, infrastructure, documentation
```

**The problem**: TASK-FHA-005 has `task_type: testing` in its frontmatter, but the `TaskType` enum only supports:
- `scaffolding`
- `feature`
- `infrastructure`
- `documentation`

The CoachValidator fails to resolve the task type, returns feedback instead of approval, and the Player keeps retrying without being able to fix the actual issue (which is in the task metadata, not the implementation).

## Technical Analysis

### Failure Loop Pattern

1. Player completes implementation (shows "0 files created, 0 modified, 0 tests")
2. Coach validation starts
3. `_resolve_task_type()` fails due to invalid task_type value
4. Coach returns feedback with the error message
5. Player receives feedback, attempts another turn
6. Loop repeats until max_turns (5) exceeded

The Player cannot fix this because:
- The error is in task frontmatter metadata
- Player is focused on code implementation
- The feedback message doesn't guide the Player to fix frontmatter

### Code Path

1. `CoachValidator._resolve_task_type()` in [coach_validator.py:305-340](guardkit/orchestrator/quality_gates/coach_validator.py#L305-L340)
2. Task type validation at line ~323-337
3. `TaskType` enum in [task_types.py:21-40](guardkit/models/task_types.py#L21-L40)

## Recommendations

### Option 1: Add "testing" to TaskType enum (Recommended)
Add `TESTING = "testing"` to the TaskType enum with an appropriate QualityGateProfile.

Testing tasks should probably have:
- `tests_required: True` (testing infrastructure must be testable)
- `coverage_required: False` (test code coverage less critical)
- `arch_review_required: False` (testing patterns are well-established)
- `plan_audit_required: True` (ensure testing setup is complete)

### Option 2: Map "testing" to "infrastructure"
Add fallback logic in `_resolve_task_type()` to map unknown values to sensible defaults:
- `testing` → `infrastructure` (closest match)
- Unknown → `feature` (conservative default)

### Option 3: Fix task generation to use valid types
Ensure feature planning generates tasks with valid task_type values. The task "Set up testing infrastructure" should perhaps use `task_type: infrastructure` or `task_type: scaffolding`.

## Acceptance Criteria

- [ ] Identify where TASK-FHA-005 got `task_type: testing` (feature planning, manual, etc.)
- [ ] Implement a fix so that testing-related tasks work correctly
- [ ] Verify fix doesn't break existing task_type handling
- [ ] Re-run feature build to confirm TASK-FHA-005 passes
- [ ] Update documentation if new task_type is added

## Files to Review

- `guardkit/models/task_types.py` - TaskType enum and profiles
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Task type resolution
- Feature planning code that generates task files
- The generated task file TASK-FHA-005 in the worktree

## Test Plan

1. Unit test: Verify `_resolve_task_type()` handles "testing" appropriately
2. Integration test: Run feature build with a task that has `task_type: testing`
3. Regression test: Ensure existing valid task_types still work

## Notes

This is very close to a complete victory - 4/5 tasks passed, only the final task failed due to this metadata validation issue rather than any implementation problem.
