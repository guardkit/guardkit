---
id: TASK-GR5-008
title: Add turn context loading for next turn
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: task-work
complexity: 4
estimate_hours: 1
dependencies:
- TASK-GR5-007
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T14:42:31.506251'
  last_updated: '2026-02-01T14:52:49.630668'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T14:42:31.506251'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Add turn context loading for next turn

## Description

Implement loading of previous turn context at the start of each feature-build turn to enable cross-turn learning.

## Acceptance Criteria

- [ ] `load_turn_context(feature_id, task_id)` returns formatted context
- [ ] Queries last 5 turns from `turn_states` group
- [ ] Formats turn summary: "Turn N: DECISION - progress"
- [ ] Emphasizes last turn feedback if REJECTED
- [ ] Returns "First turn - no previous context" if no history

## Technical Details

**Location**: `guardkit/knowledge/turn_state.py`

**Context Format**:
```
Previous Turn Summary:
  Turn 1: FEEDBACK - Initial implementation incomplete
  Turn 2: REJECTED - Tests failing, coverage at 65%

Last Turn Feedback (MUST ADDRESS):
  "Coverage must be ≥80%. Missing tests for error paths."
```

**Reference**: See FEAT-GR-005 Turn Context Loading section.
