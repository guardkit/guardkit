---
id: TASK-GR6-006
title: Integrate with /feature-build
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 5
estimate_hours: 2
dependencies:
- TASK-GR6-005
autobuild_state:
  current_turn: 6
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T17:35:59.111540'
  last_updated: '2026-02-01T18:08:09.209655'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:35:59.111540'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:40:57.753464'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:47:23.729128'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:54:03.327510'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 5
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T17:59:27.624796'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 6
    decision: approve
    feedback: null
    timestamp: '2026-02-01T18:03:30.861645'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Integrate with /feature-build

## Description

Integrate the `JobContextRetriever` into the `/feature-build` command with AutoBuild-specific context retrieval.

## Acceptance Criteria

- [ ] Context retrieved for each Player turn
- [ ] AutoBuild context included (role_constraints, quality_gates, turn_states)
- [ ] Refinement attempts get emphasized warnings
- [ ] Coach receives appropriate subset of context
- [ ] `--verbose` flag shows context retrieval details

## Technical Details

**Integration Points**:
- Player turn start: Full context with role_constraints
- Coach turn start: Quality gate configs, turn states

**AutoBuild Characteristics**:
- `is_autobuild: True`
- `current_actor: "player"` or `"coach"`
- `turn_number: N`
- `has_previous_turns: True` (if N > 1)

**Reference**: See FEAT-GR-006 Integration with /feature-build section.
