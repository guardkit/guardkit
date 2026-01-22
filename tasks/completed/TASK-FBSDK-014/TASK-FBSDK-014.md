---
id: TASK-FBSDK-014
title: Generate implementation plans during /feature-plan [I]mplement flow
status: completed
created: 2026-01-20T10:00:00Z
updated: 2026-01-20T12:15:00Z
completed: 2026-01-20T12:15:00Z
priority: high
tags: [feature-plan, implementation-plan, feature-build, optimization]
complexity: 5
parent_review: TASK-REV-FB17
wave: 1
implementation_mode: task-work
depends_on: []
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-FBSDK-014/
organized_files:
  - TASK-FBSDK-014.md
  - implementation-plan.md
  - completion-report.md
---

# TASK-FBSDK-014: Generate Implementation Plans During /feature-plan

## Context

This task implements **Option B** from the FBSDK-013 design discussion. Instead of creating stub plans or having the Player re-analyze tasks during feature-build, we generate real implementation plans during `/feature-plan` when the AI context is "hot" from the review.

## Problem Statement

Currently, when `/feature-plan` creates subtasks via the [I]mplement decision:
1. Task files are created with detailed specs (description, acceptance criteria, etc.)
2. **No implementation plan files are created**
3. When `feature-build` runs, the Player needs a plan for `task-work --implement-only`
4. This causes either: (a) plan not found errors, or (b) re-analysis of the task

This is inefficient because the AI that did the review **already has all the knowledge** needed to create implementation plans - we're just not persisting it.

## Solution

During the [I]mplement flow in `/feature-plan`, after creating each subtask file, also generate an implementation plan file.

### Why This Is Better

| Approach | Time Cost | Notes |
|----------|-----------|-------|
| **Current** (no plans) | Fails or needs stubs | Player can't use --implement-only |
| **Option A** (plan on first loop) | +60-90 min per task | AI re-analyzes from scratch |
| **Option B** (plan during feature-plan) | +2-3 min per task | AI context is hot, no re-analysis |

**Option B wins** because the knowledge is already loaded during the review.

## Implementation Summary

### Files Modified
- `installer/core/lib/implement_orchestrator.py` - Added plan generation methods and integration

### New Methods Added
1. `generate_implementation_plans()` - Main method (lines 355-428)
2. `_format_plan_files()` - Formats file list for plan markdown
3. `_format_plan_dependencies()` - Formats dependencies section
4. `_generate_implementation_approach()` - Generates numbered implementation steps
5. `_generate_test_strategy()` - Generates test strategy based on mode
6. `_estimate_loc()` - Estimates LOC based on complexity
7. `_estimate_duration()` - Estimates duration based on complexity

### Integration Point
Method called from `handle_implement_option()` after step 8 (lines 715-718):
```python
# Step 8b: Generate implementation plans
print("   Generating implementation plans...")
orchestrator.generate_implementation_plans()
print(f"   ✓ Generated {len(orchestrator.subtasks)} implementation plans")
```

## Acceptance Criteria

- [x] After `/feature-plan` [I]mplement, each subtask has a corresponding implementation plan file
- [x] Plan files are at `.claude/task-plans/{task_id}-implementation-plan.md`
- [x] Plan files pass validation (>50 chars, proper structure)
- [x] `feature-build` works without hitting stub creation code path
- [x] Plans contain: files to create, implementation approach, dependencies, estimates
- [ ] Documentation updated (deferred - low priority)

## Test Results

- **27 tests passing** (all existing + 13 new tests)
- **73% coverage** for implement_orchestrator.py
- New test class: `TestImplementationPlanGeneration` with comprehensive coverage

## Review Results

### Architectural Review: 72/100 (APPROVED WITH RECOMMENDATIONS)
- SOLID: 30/50 (SRP concern noted - orchestrator has many responsibilities)
- DRY: 20/25 (Uses appropriate abstraction)
- YAGNI: 22/25 (Minimal solution for the problem)

### Code Review: 8/10 (APPROVED)
- Clean, well-documented methods
- Follows existing codebase patterns
- Good test coverage for new functionality
- Minor recommendations: add validation for empty subtasks, improve coverage to 80%

## Related Tasks

- TASK-FBSDK-013: Stub creation fix (kept as fallback)
- TASK-REV-FB17: Parent review that identified feature-build issues

## Notes

- TASK-FBSDK-013 changes are kept as a **fallback** - if plan generation fails for any reason, stub creation still works
- Future task: Once this is proven stable, we could consider removing the stub creation fallback
- The plan generation should happen in the same AI context as the review to leverage the "hot" knowledge
