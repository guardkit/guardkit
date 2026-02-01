---
id: TASK-GR6-007
title: Add role_constraints retrieval and formatting
status: in_review
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
autobuild_state:
  current_turn: 6
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T16:59:40.599976'
  last_updated: '2026-02-01T17:23:00.792709'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T16:59:40.599976'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:06:54.384587'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:08:24.216259'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:13:57.580668'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 5
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:17:03.167242'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 6
    decision: approve
    feedback: null
    timestamp: '2026-02-01T17:20:23.437333'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
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
