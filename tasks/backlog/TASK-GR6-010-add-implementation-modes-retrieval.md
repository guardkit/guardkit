---
id: TASK-GR6-010
title: Add implementation_modes retrieval
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: direct
complexity: 3
estimate_hours: 1
dependencies:
  - TASK-GR6-003
---

# Add implementation_modes retrieval

## Description

Add retrieval and formatting for implementation_modes context, addressing TASK-REV-7549 finding on direct vs task-work confusion.

## Acceptance Criteria

- [ ] Queries `implementation_modes` group
- [ ] Returns direct and task-work mode guidance
- [ ] Formats invocation method, result location, pitfalls
- [ ] Helps prevent "file not found" errors in worktrees

## Technical Details

**Group ID**: `implementation_modes`

**Output Format**:
```
### Implementation Mode
*Use correct mode to avoid file location errors*

**task-work**:
  Invocation: /task-work TASK-XXX
  Results at: .guardkit/worktrees/TASK-XXX/
  Pitfalls:
    ⚠️ Don't expect files in main repo during execution

**direct**:
  Invocation: Inline changes
  Results at: Current working directory
  Pitfalls:
    ⚠️ No isolation from main repo
```

**Reference**: See FEAT-GR-006 implementation_modes formatting.
