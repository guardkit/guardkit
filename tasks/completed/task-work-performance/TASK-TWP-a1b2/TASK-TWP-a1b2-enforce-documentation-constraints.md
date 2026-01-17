---
id: TASK-TWP-a1b2
title: Enforce documentation level constraints in agent invocations
status: completed
created: 2026-01-16T12:00:00Z
updated: 2026-01-16T15:30:00Z
completed: 2026-01-16T15:30:00Z
priority: high
tags:
  - performance
  - agent-invocation
  - documentation-level
complexity: 4
parent_review: TASK-REV-FB15
feature: task-work-performance
wave: 1
implementation_mode: task-work
estimated_minutes: 180
dependencies: []
---

# Enforce Documentation Level Constraints

## Description

The fastapi-specialist agent generated 117KB of documentation (7 files) for a complexity-3 task despite the documentation level being set to `standard` (which should generate max 2 files). This is the **primary root cause** of `/task-work` slowness, consuming 58 of 65 minutes (89%) in the trace.

## Problem Evidence

From `stand_alone_manual_design.md` trace:
```
Documentation Level: STANDARD
   Reason: auto-select (complexity 3/10)
   Files: 2 files
   Estimated: 12-18 minutes
```

But the agent actually generated:
```
Documentation created: 7 comprehensive files (117 KB)
⎿  Done (27 tool uses · 66.3k tokens · 58m 0s)
```

## Root Cause

The agent prompt mentions "CONSTRAINT: Generate ONLY 2 files maximum" but:
1. There's no validation after agent completion
2. Agents can freely create additional files
3. No enforcement mechanism exists

## Objectives

- Add post-invocation validation for file count based on documentation level
- Add explicit file count limits to agent context
- Log warnings when constraints are violated
- Consider failing the phase if constraints significantly exceeded

## Acceptance Criteria

- [x] Post-invocation validation checks files created vs documentation level
- [x] Validation logs warning if files_created > expected_max
- [x] Agent context includes explicit `max_files` parameter
- [x] Tests verify constraint enforcement
- [x] Documentation level `minimal` allows max 2 files
- [x] Documentation level `standard` allows max 2 files
- [x] Documentation level `comprehensive` allows unlimited files

## Technical Approach

### 1. Update Agent Context

```python
# In agent_invoker.py or equivalent
def build_agent_context(task_context, documentation_level):
    max_files = 2 if documentation_level in ['minimal', 'standard'] else None
    return f"""<AGENT_CONTEXT>
documentation_level: {documentation_level}
max_files: {max_files}  # NEW: Explicit constraint
complexity_score: {task_context.complexity}
...
</AGENT_CONTEXT>"""
```

### 2. Add Post-Invocation Validation

```python
def validate_agent_output(agent_result, documentation_level):
    files_created = count_files_created(agent_result)
    max_allowed = 2 if documentation_level in ['minimal', 'standard'] else float('inf')
    
    if files_created > max_allowed:
        logger.warning(
            f"Documentation constraint violated: created {files_created} files "
            f"(max {max_allowed} for {documentation_level} level)"
        )
        # Consider: return validation_failed=True for strict enforcement
    
    return ValidationResult(
        files_created=files_created,
        max_allowed=max_allowed,
        constraint_violated=files_created > max_allowed
    )
```

### 3. Update Agent Prompts

Add stronger language to agent prompts:
```
DOCUMENTATION CONSTRAINTS (MUST FOLLOW):
- Documentation level: {documentation_level}
- Maximum files allowed: {max_files}
- VIOLATION: Creating more than {max_files} files will trigger validation failure
```

## Files to Modify

- `installer/core/commands/task-work.md` - Update agent prompt templates
- `installer/core/agents/fastapi-specialist.md` - Add constraint handling
- `installer/core/agents/*.md` - All specialist agents need constraint awareness
- `guardkit/orchestrator/agent_invoker.py` - Add validation (if Python orchestration exists)

## Test Requirements

- [x] Test that minimal mode creates ≤2 files
- [x] Test that standard mode creates ≤2 files
- [x] Test that comprehensive mode allows >2 files
- [x] Test that validation warning is logged on violation
- [x] Test that agent context includes max_files parameter

## Notes

This is the highest-priority fix from TASK-REV-FB15. The 58-minute Phase 2 execution was primarily caused by excessive file generation, not inherent complexity in the task.

Expected improvement: 60-70% reduction in Phase 2 duration.

## Implementation Summary

### Files Modified

1. **`guardkit/orchestrator/agent_invoker.py`**:
   - Added `DOCUMENTATION_LEVEL_MAX_FILES` constant mapping documentation levels to max file counts
   - Added `_validate_file_count_constraint()` method for post-invocation validation
   - Updated `invoke_player()` signature to accept `documentation_level` parameter
   - Updated `_invoke_task_work_implement()` signature to propagate `documentation_level`
   - Integrated validation into `_write_task_work_results()` call chain

2. **`tests/unit/test_agent_invoker.py`**:
   - Added `TestFileCountConstraintValidation` class with 10 comprehensive tests
   - Fixed `test_invoke_player_uses_delegation` to include new parameter

### Key Implementation Details

- Validation uses warning logging (not blocking) to monitor violations without breaking existing workflows
- `documentation_level` propagates through the complete async call chain: `invoke_player()` → `_invoke_task_work_implement()` → `_write_task_work_results()` → `_validate_file_count_constraint()`
- All 202 existing tests pass after implementation
