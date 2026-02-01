---
id: TASK-GR3-006
title: Add AutoBuild context queries
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-003
wave: 1
parallel_group: wave1-gr003
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
- TASK-GR3-003
autobuild_state:
  current_turn: 2
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T13:09:05.713196'
  last_updated: '2026-02-01T13:21:31.412279'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T13:09:05.713196'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-02-01T13:14:16.800680'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Add AutoBuild context queries

## Description

Add Graphiti queries for AutoBuild-specific context: role_constraints, quality_gate_configs, and implementation_modes. These address critical findings from TASK-REV-1505.

## Acceptance Criteria

- [ ] `_get_role_constraints()` queries `role_constraints` group
- [ ] `_get_quality_gate_configs()` queries `quality_gate_configs` group
- [ ] `_get_implementation_modes()` queries `implementation_modes` group
- [ ] Results included in `FeaturePlanContext`
- [ ] Formatting methods for prompt injection

## Technical Details

**New Group IDs**:
- `role_constraints` - Player/Coach boundaries
- `quality_gate_configs` - Threshold configurations
- `implementation_modes` - Direct vs task-work patterns

**Addresses**: TASK-REV-7549 findings on role reversal, threshold drift

**Reference**: See FEAT-GR-003 AutoBuild Integration section.
