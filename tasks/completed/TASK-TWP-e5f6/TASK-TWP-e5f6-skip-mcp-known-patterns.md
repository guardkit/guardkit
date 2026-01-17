---
id: TASK-TWP-e5f6
title: Skip Design Patterns MCP for tasks with known patterns
status: completed
created: 2026-01-16T12:00:00Z
updated: 2026-01-16T14:50:00Z
completed: 2026-01-16T14:50:00Z
priority: medium
tags:
  - performance
  - mcp
  - design-patterns
complexity: 2
parent_review: TASK-REV-FB15
feature: task-work-performance
wave: 2
implementation_mode: direct
estimated_minutes: 60
actual_minutes: 20
dependencies: []
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-TWP-e5f6/
organized_files:
  - TASK-TWP-e5f6-skip-mcp-known-patterns.md
---

# Skip MCP for Known Patterns

## Description

The design-patterns MCP is invoked for every task during Phase 2.5A, even when the task already specifies a pattern or is too simple to benefit. In the trace, it returned irrelevant React patterns for a Python task.

## Problem Evidence

From `stand_alone_manual_design.md` trace:
```
Query: "Singleton pattern for configuration settings with environment
        variable loading and validation in Python FastAPI application"

Response:
1. **Form Validation Pattern** (React Forms) - 180.0% confidence
2. **useRef and forwardRef Pattern** (React Hooks) - 135.0%
3. **Controlled and Uncontrolled Forms** (React Forms) - 120.0%
```

The MCP returned **React patterns** for a **Python** task, requiring additional calls to find relevant results.

## Root Cause

1. MCP search doesn't effectively filter by programming language
2. All tasks invoke MCP regardless of complexity or existing pattern specification
3. Simple tasks (complexity ≤3) don't benefit from pattern suggestions

## Objectives

- Skip MCP for tasks that already reference known patterns
- Skip MCP for simple tasks (complexity ≤3)
- Skip MCP for bug fixes that don't require new architecture

## Acceptance Criteria

- [x] MCP skipped when task description contains known pattern names
- [x] MCP skipped when complexity ≤3
- [x] MCP skipped when task_type is "bugfix"
- [x] MCP still invoked for complexity ≥4 feature tasks without known patterns
- [x] Log message indicates when MCP is skipped and why

## Implementation Summary

Updated `installer/core/commands/task-work.md` Phase 2.5A to include:

1. **Skip Condition Evaluation Function**: `should_invoke_design_patterns_mcp(task_context)` that checks:
   - Complexity ≤3 → skip (simple task)
   - task_type == "bugfix" → skip (no new architecture needed)
   - Task references known pattern (18 patterns checked) → skip

2. **Known Patterns List** (expanded from original 10 to 18):
   - singleton, repository, factory, strategy, observer
   - adapter, decorator, facade, command, mediator
   - builder, prototype, chain of responsibility, state
   - template method, visitor, memento, iterator

3. **Skip Message Display**:
   ```
   ⏭️  Skipping Pattern Suggestion (Phase 2.5A)
      Reason: {skip_reason}

      Proceeding to Phase 2.5B...
   ```

4. **Workflow**: Conditional execution with clear skip reasons:
   - STEP 1: Evaluate skip conditions
   - STEP 2: Invoke MCP (only if should_invoke == True)

## Files Modified

- `installer/core/commands/task-work.md` - Added conditional skip logic to Phase 2.5A

## Test Results

- All 60 existing task-work interface tests pass
- No regressions detected

## Completion Summary

| Metric | Value |
|--------|-------|
| Estimated Time | 60 minutes |
| Actual Time | ~20 minutes |
| Files Changed | 1 |
| Lines Added | ~75 |
| Tests Passed | 60/60 |
| Acceptance Criteria | 5/5 |

## Notes

This is a low-priority optimization since MCP only takes ~5 seconds. However, it eliminates confusion from irrelevant results and cleans up the execution trace.

The design-patterns MCP has a separate issue with Python support, but fixing that is outside our control (depends on MCP maintainer). This task works around the issue by not invoking MCP when it's unlikely to add value.

Expected improvement: Cleaner execution, no irrelevant pattern suggestions for simple tasks.
