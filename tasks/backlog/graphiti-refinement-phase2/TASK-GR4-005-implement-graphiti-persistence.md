---
id: TASK-GR4-005
title: Implement Graphiti persistence
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-004
wave: 1
parallel_group: wave1-gr004
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
  - TASK-GR4-004
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
