---
id: TASK-GR3-006
title: Add AutoBuild context queries
status: backlog
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
