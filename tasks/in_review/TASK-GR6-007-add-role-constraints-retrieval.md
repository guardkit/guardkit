---
completed_at: 2026-02-01 17:45:00+00:00
complexity: 4
dependencies:
- TASK-GR6-003
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR6-007
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: feature
title: Add role_constraints retrieval and formatting
wave: 3
---

# Add role_constraints retrieval and formatting

## Description

Add retrieval and formatting for role_constraints context, addressing TASK-REV-7549 finding on Player-Coach role reversal.

## Acceptance Criteria

- [x] Queries `role_constraints` group
- [x] Filters by current_actor (player/coach)
- [x] Formats must_do, must_not_do, ask_before lists
- [x] Emoji markers for boundaries (✓/✗/❓)
- [x] Emphasized in AutoBuild contexts

## Technical Details

**Group ID**: `role_constraints`

**Output Format**:
```
### Role Constraints
**Player**:
  Must do:
    ✓ Implement code
    ✓ Write tests
  Must NOT do:
    ✗ Validate quality gates
    ✗ Make architectural decisions
  Ask before:
    ❓ Schema changes
    ❓ Auth changes
```

**Reference**: See FEAT-GR-006 role_constraints formatting.

## Implementation Summary

### Files Implemented

1. **`guardkit/knowledge/role_constraint_formatter.py`** (204 lines)
   - `format_role_constraints()`: Formats all role constraints for prompt injection
   - `format_role_constraints_for_actor()`: Filters and formats for specific actor (player/coach)
   - Emoji markers: ✓ (must_do), ✗ (must_not_do), ❓ (ask_before)
   - AutoBuild emphasis with warning markers

2. **`tests/knowledge/test_role_constraint_formatter.py`** (662 lines)
   - 35 tests covering all acceptance criteria
   - Test categories:
     - Basic formatting tests
     - Role-specific formatting
     - Emoji marker tests
     - Section header tests
     - Content preservation tests
     - AutoBuild emphasis tests
     - Actor filtering tests
     - Edge cases and error handling
     - Output format validation
     - Integration tests

### Module Exports

- Added to `guardkit/knowledge/__init__.py`:
  - `format_role_constraints`
  - `format_role_constraints_for_actor`

### Integration Points

1. **JobContextRetriever** (`job_context_retriever.py`)
   - Queries `role_constraints` group (line 417-419)
   - Stores results in `RetrievedContext.role_constraints` field

2. **FeaturePlanContext** (`feature_plan_context.py`)
   - `_format_role_constraints()` method uses same emoji markers
   - Integrated with `to_prompt_context()` for feature planning

### Test Results

```
35 tests passed, 0 failed
Coverage: 94% (guardkit/knowledge/role_constraint_formatter.py)
  - 42 statements, 2 missed (lines 111, 187 - edge case branches)
```

### Output Format Example

```markdown
### 🎭 Role Constraints

⚠️ *Enforce these boundaries - role reversal causes failures*

**Player**:
  Must do:
    ✓ Write code
    ✓ Create tests
  Must NOT do:
    ✗ Approve work
    ✗ Validate quality
  Ask before:
    ❓ Schema changes
    ❓ Auth changes

**Coach**:
  Must do:
    ✓ Validate work
    ✓ Check quality
  Must NOT do:
    ✗ Write code
    ✗ Implement features
```

### References

- TASK-GR6-007: Add role_constraints retrieval and formatting
- FEAT-GR-006: Job-Specific Context Retrieval
- TASK-REV-7549: Player-Coach role reversal finding