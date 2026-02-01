---
complexity: 4
dependencies:
- TASK-GR3-003
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR3-006
implementation_mode: task-work
parallel_group: wave1-gr003
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-003
task_type: feature
title: Add AutoBuild context queries
wave: 1
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