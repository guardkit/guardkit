---
id: TASK-GR5-007
title: Add turn state capture to feature-build
status: in_review
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
autobuild_state:
  current_turn: 4
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T14:23:22.798876'
  last_updated: '2026-02-01T14:42:31.406188'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T14:23:22.798876'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T14:31:14.731324'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T14:32:38.964359'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: approve
    feedback: null
    timestamp: '2026-02-01T14:38:36.088920'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
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
