---
complexity: 6
dependencies:
- TASK-GR6-001
estimate_hours: 4
feature_id: FEAT-0F4A
id: TASK-GR6-002
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: feature
title: Implement DynamicBudgetCalculator
wave: 3
---

# Implement DynamicBudgetCalculator

## Description

Create the `DynamicBudgetCalculator` class that calculates context budget and allocation based on task characteristics, including AutoBuild-specific allocations.

## Acceptance Criteria

- [x] `calculate(characteristics)` returns `ContextBudget`
- [x] Base budget by complexity: 2000 (simple), 4000 (medium), 6000 (complex)
- [x] Adjustments for novelty (+30%), refinement (+20%), AutoBuild (+15-25%)
- [x] DEFAULT_ALLOCATION for standard tasks
- [x] AUTOBUILD_ALLOCATION with role_constraints, quality_gate_configs, turn_states

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