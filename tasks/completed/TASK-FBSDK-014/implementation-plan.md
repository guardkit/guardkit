# Implementation Plan: TASK-FBSDK-014

## Task
Generate implementation plans during /feature-plan [I]mplement flow

## Overview
When `/feature-plan` creates subtasks via the [I]mplement decision, generate implementation plan files alongside task markdown files. This leverages the "hot" AI context from the review analysis to create plans efficiently, saving 60-90 minutes per task that would otherwise be spent re-analyzing.

## Files to Create/Modify

| File | Change | LOC |
|------|--------|-----|
| `installer/core/lib/implement_orchestrator.py` | Add `generate_implementation_plans()` method | +80 |

## Implementation Approach

1. Add `generate_implementation_plans()` method to `ImplementOrchestrator` class
   - Iterate through `self.subtasks`
   - For each subtask, generate a minimal plan markdown with:
     - Task title and overview
     - Files to create/modify (from subtask data)
     - Implementation approach (numbered steps)
     - Dependencies (from subtask depends_on)
     - Test strategy
     - Estimated effort (LOC, duration, complexity)
   - Write to `.claude/task-plans/{task_id}-implementation-plan.md`
   - Ensure `.claude/task-plans/` directory exists

2. Call the new method from `handle_implement_option()` after step 8 (generate_subtask_files)

3. Add progress output showing plan generation status

## Dependencies
- TASK-FBSDK-013: Stub plan creation (provides fallback if this fails)
- No blocking dependencies

## Test Strategy
1. Manual: Run `/feature-plan "test feature"` and select [I]mplement
2. Verify plan files created at `.claude/task-plans/TASK-*-implementation-plan.md`
3. Verify plan content meets minimum requirements (>50 chars, proper structure)
4. Run `feature-build` on a subtask
5. Verify Player uses `--implement-only` from turn 1
6. Verify no "stub creation" fallback triggered (FBSDK-013 code path not executed)

## Estimated Effort
- LOC: ~80
- Duration: 1-2 hours
- Complexity: 5/10
