---
id: TASK-GR6-009
title: Add turn_states retrieval for cross-turn learning
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies:
- TASK-GR6-003
- TASK-GR5-007
autobuild_state:
  current_turn: 5
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T16:59:40.599458'
  last_updated: '2026-02-01T17:22:04.493233'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T16:59:40.599458'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:08:12.865517'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:10:24.097095'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:15:59.421317'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 5
    decision: approve
    feedback: null
    timestamp: '2026-02-01T17:17:39.522521'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Add turn_states retrieval for cross-turn learning

## Description

Add retrieval and formatting for turn_states context to enable cross-turn learning in feature-build workflows. This is the key feature addressing TASK-REV-7549 finding.

## Acceptance Criteria

- [ ] Queries `turn_states` group for feature_id + task_id
- [ ] Returns last 5 turns sorted by turn_number
- [ ] Formats turn summary with decision and progress
- [ ] Emphasizes REJECTED feedback (must address)
- [ ] Increased allocation for later turns (15-20%)

## Technical Details

**Group ID**: `turn_states`

**Query**: `turn {feature_id} {task_id}`

**Output Format**:
```
### Previous Turn Context
*Learn from previous turns - don't repeat mistakes*

**Turn 1**: FEEDBACK
  Progress: Initial implementation incomplete

**Turn 2**: REJECTED
  Progress: Tests failing, coverage at 65%
  ⚠️ Feedback: "Coverage must be ≥80%. Missing tests for error paths."
```

**Reference**: See FEAT-GR-006 turn_states retrieval section.
