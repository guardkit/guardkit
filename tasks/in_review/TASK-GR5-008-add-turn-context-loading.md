---
complexity: 4
dependencies:
- TASK-GR5-007
estimate_hours: 1
feature_id: FEAT-0F4A
id: TASK-GR5-008
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-005
task_type: feature
title: Add turn context loading for next turn
wave: 2
---

# Add turn context loading for next turn

## Description

Implement loading of previous turn context at the start of each feature-build turn to enable cross-turn learning.

## Acceptance Criteria

- [x] `load_turn_context(feature_id, task_id)` returns formatted context
- [x] Queries last 5 turns from `turn_states` group
- [x] Formats turn summary: "Turn N: DECISION - progress"
- [x] Emphasizes last turn feedback if REJECTED
- [x] Returns "First turn - no previous context" if no history

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