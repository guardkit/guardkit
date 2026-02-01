---
id: TASK-GR3-002
title: Implement FeaturePlanContext dataclass
status: backlog
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
