---
id: TASK-GR6-002
title: Implement DynamicBudgetCalculator
status: backlog
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
