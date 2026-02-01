---
id: TASK-GR3-003
title: Implement FeaturePlanContextBuilder
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-003
wave: 1
parallel_group: wave1-gr003
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies:
- TASK-GR3-001
- TASK-GR3-002
autobuild_state:
  current_turn: 5
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T12:53:44.896686'
  last_updated: '2026-02-01T13:08:01.916021'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T12:53:44.896686'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T13:02:41.625035'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Tests did not pass during task-work execution

      - Coverage threshold not met'
    timestamp: '2026-02-01T13:03:39.549310'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T13:05:07.052620'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 5
    decision: approve
    feedback: null
    timestamp: '2026-02-01T13:06:19.418894'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Implement FeaturePlanContextBuilder

## Description

Create the `FeaturePlanContextBuilder` class that builds comprehensive context for feature planning by detecting features, seeding specs to Graphiti, and querying for enrichment.

## Acceptance Criteria

- [ ] `build_context(description, context_files, tech_stack)` returns `FeaturePlanContext`
- [ ] Auto-detects feature ID from description
- [ ] Seeds feature spec to Graphiti if found
- [ ] Queries Graphiti for related features, patterns, warnings
- [ ] Queries AutoBuild context: role_constraints, quality_gate_configs, implementation_modes
- [ ] Handles missing Graphiti gracefully (returns empty context)

## Technical Details

**Location**: `guardkit/knowledge/feature_plan_context.py`

**Query Groups**:
- `feature_specs` - Feature specifications
- `patterns_{tech_stack}` - Stack-specific patterns
- `failure_patterns` - Warning context
- `role_constraints` - Player/Coach boundaries (NEW)
- `quality_gate_configs` - Threshold configurations (NEW)
- `implementation_modes` - Direct vs task-work (NEW)

**Reference**: See FEAT-GR-003-feature-spec-integration.md for full implementation.
