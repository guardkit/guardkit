---
id: TASK-GR3-003
title: Implement FeaturePlanContextBuilder
status: backlog
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
