---
id: TASK-GR3-002
title: Implement FeaturePlanContext dataclass
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-003
wave: 1
parallel_group: wave1-gr003
implementation_mode: direct
complexity: 3
estimate_hours: 2
dependencies: []
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T11:46:55.197746'
  last_updated: '2026-02-01T12:43:34.047050'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T11:46:55.197746'
    player_summary: 'Implemented FeaturePlanContext dataclass with all required fields
      including AutoBuild support fields (role_constraints, quality_gate_configs,
      implementation_modes). The to_prompt_context() method implements budget-aware
      formatting with prioritized sections (40% feature spec, 20% architecture, 15%
      related features, 15% patterns, 10% warnings, plus AutoBuild sections). All
      formatting helper methods include proper truncation limits and handle missing
      data gracefully. The implementation follows the '
    player_success: true
    coach_success: true
---

# Implement FeaturePlanContext dataclass

## Description

Create the `FeaturePlanContext` dataclass that holds rich context for feature planning, including AutoBuild support fields for role constraints, quality gates, and implementation modes.

## Acceptance Criteria

- [ ] Dataclass with all fields from specification
- [ ] `to_prompt_context(budget_tokens: int)` method formats for prompt injection
- [ ] AutoBuild fields: `role_constraints`, `quality_gate_configs`, `implementation_modes`
- [ ] Budget-aware formatting that respects token limits
- [ ] Formatting helpers for each section type

## Technical Details

**Location**: `guardkit/knowledge/feature_plan_context.py`

**Fields**:
- `feature_spec: Dict[str, Any]`
- `related_features: List[Dict[str, Any]]`
- `relevant_patterns: List[Dict[str, Any]]`
- `similar_implementations: List[Dict[str, Any]]`
- `project_architecture: Dict[str, Any]`
- `warnings: List[Dict[str, Any]]`
- `role_constraints: List[Dict[str, Any]]` (AutoBuild)
- `quality_gate_configs: List[Dict[str, Any]]` (AutoBuild)
- `implementation_modes: List[Dict[str, Any]]` (AutoBuild)

**Reference**: See FEAT-GR-003-feature-spec-integration.md for formatting details.
