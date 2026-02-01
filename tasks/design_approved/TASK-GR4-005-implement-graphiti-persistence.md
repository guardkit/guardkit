---
complexity: 4
dependencies:
- TASK-GR4-004
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR4-005
implementation_mode: task-work
parallel_group: wave1-gr004
parent_review: TASK-REV-0CD7
status: design_approved
sub_feature: GR-004
task_type: feature
title: Implement Graphiti persistence
wave: 1
---

# Implement Graphiti persistence

## Description

Implement the persistence layer that saves captured knowledge to Graphiti as episodes.

## Acceptance Criteria

- [ ] `_save_captured_knowledge()` groups facts by category
- [ ] Creates episodes with correct group_ids
- [ ] Maps categories to group_ids (including AutoBuild categories)
- [ ] Includes timestamp and source metadata
- [ ] Handles Graphiti errors gracefully

## Technical Details

**Category to Group ID Mapping**:
- `project_overview` → `project_overview`
- `architecture` → `project_architecture`
- `domain` → `domain_knowledge`
- `constraints` → `project_constraints`
- `decisions` → `project_decisions`
- `role_customization` → `role_constraints` (NEW)
- `quality_gates` → `quality_gate_configs` (NEW)
- `workflow_preferences` → `implementation_modes` (NEW)

**Episode Structure**:
```python
{
    "entity_type": "captured_knowledge",
    "category": category.value,
    "facts": all_facts,
    "qa_pairs": qa_pairs,
    "source": "interactive_capture",
    "captured_at": timestamp
}
```