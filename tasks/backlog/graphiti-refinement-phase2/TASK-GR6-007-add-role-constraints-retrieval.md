---
id: TASK-GR6-007
title: Add role_constraints retrieval and formatting
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
  - TASK-GR6-003
---

# Add role_constraints retrieval and formatting

## Description

Add retrieval and formatting for role_constraints context, addressing TASK-REV-7549 finding on Player-Coach role reversal.

## Acceptance Criteria

- [ ] Queries `role_constraints` group
- [ ] Filters by current_actor (player/coach)
- [ ] Formats must_do, must_not_do, ask_before lists
- [ ] Emoji markers for boundaries (✓/✗/❓)
- [ ] Emphasized in AutoBuild contexts

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
