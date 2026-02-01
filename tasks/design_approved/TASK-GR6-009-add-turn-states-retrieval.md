---
complexity: 5
dependencies:
- TASK-GR6-003
- TASK-GR5-007
estimate_hours: 3
feature_id: FEAT-0F4A
id: TASK-GR6-009
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: design_approved
sub_feature: GR-006
task_type: feature
title: Add turn_states retrieval for cross-turn learning
wave: 3
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