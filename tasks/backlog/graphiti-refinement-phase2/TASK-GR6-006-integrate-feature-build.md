---
id: TASK-GR6-006
title: Integrate with /feature-build
status: backlog
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
