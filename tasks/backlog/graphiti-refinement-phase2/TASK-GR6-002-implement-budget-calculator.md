---
id: TASK-GR6-002
title: Implement DynamicBudgetCalculator
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 6
estimate_hours: 4
dependencies:
- TASK-GR6-001
autobuild_state:
  current_turn: 2
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T15:19:38.579448'
  last_updated: '2026-02-01T15:30:36.307185'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T15:19:38.579448'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-02-01T15:28:12.401704'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Implement DynamicBudgetCalculator

## Description

Create the `DynamicBudgetCalculator` class that calculates context budget and allocation based on task characteristics, including AutoBuild-specific allocations.

## Acceptance Criteria

- [ ] `calculate(characteristics)` returns `ContextBudget`
- [ ] Base budget by complexity: 2000 (simple), 4000 (medium), 6000 (complex)
- [ ] Adjustments for novelty (+30%), refinement (+20%), AutoBuild (+15-25%)
- [ ] DEFAULT_ALLOCATION for standard tasks
- [ ] AUTOBUILD_ALLOCATION with role_constraints, quality_gate_configs, turn_states

## Technical Details

**Location**: `guardkit/knowledge/budget_calculator.py`

**Budget Allocation**:
```python
DEFAULT_ALLOCATION = {
    "feature_context": 0.15,
    "similar_outcomes": 0.25,
    "relevant_patterns": 0.20,
    "architecture_context": 0.20,
    "warnings": 0.15,
    "domain_knowledge": 0.05
}

AUTOBUILD_ALLOCATION = {
    "role_constraints": 0.10,
    "quality_gate_configs": 0.10,
    "turn_states": 0.10,
    "implementation_modes": 0.05,
    # ... other reduced allocations
}
```

**Reference**: See FEAT-GR-006 DynamicBudgetCalculator section.
