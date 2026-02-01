---
complexity: 5
dependencies:
- TASK-GR5-006
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR5-007
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-005
task_type: feature
title: Add turn state capture to feature-build
wave: 2
completed_at: 2026-02-01
---

# Add turn state capture to feature-build

## Description

Integrate turn state capture into the feature-build workflow to enable cross-turn learning.

## Acceptance Criteria

- [x] `capture_turn_state()` called at end of each Player turn
- [x] Captures player decision, coach decision, feedback
- [x] Tracks blockers, progress, files modified
- [x] Saves to `turn_states` group in Graphiti
- [x] Episode name: `turn_{feature_id}_{task_id}_turn{N}`

## Technical Details

**Integration Point**: End of Player turn, before Coach validation

**Capture Data**:
- From PlayerResult: action_summary, blockers, progress_summary, files_modified, mode
- From CoachResult: decision, feedback_summary, criteria_status

**Reference**: See FEAT-GR-005 Integration with Feature-Build section.