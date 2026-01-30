---
id: TASK-GR5-007
title: Add turn state capture to feature-build
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: task-work
complexity: 5
estimate_hours: 2
dependencies:
  - TASK-GR5-006
---

# Add turn state capture to feature-build

## Description

Integrate turn state capture into the feature-build workflow to enable cross-turn learning.

## Acceptance Criteria

- [ ] `capture_turn_state()` called at end of each Player turn
- [ ] Captures player decision, coach decision, feedback
- [ ] Tracks blockers, progress, files modified
- [ ] Saves to `turn_states` group in Graphiti
- [ ] Episode name: `turn_{feature_id}_{task_id}_turn{N}`

## Technical Details

**Integration Point**: End of Player turn, before Coach validation

**Capture Data**:
- From PlayerResult: action_summary, blockers, progress_summary, files_modified, mode
- From CoachResult: decision, feedback_summary, criteria_status

**Reference**: See FEAT-GR-005 Integration with Feature-Build section.
