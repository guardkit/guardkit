---
complexity: 4
dependencies:
- TASK-GR6-003
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR6-007
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: design_approved
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