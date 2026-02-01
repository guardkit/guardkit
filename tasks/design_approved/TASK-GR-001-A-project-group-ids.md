---
complexity: 2
conductor_workspace: gr-mvp-wave6-schemas
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-003-D
feature_id: FEAT-GR-MVP
id: TASK-GR-001-A
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: design_approved
tags:
- graphiti
- project-seeding
- config
- mvp-phase-2
task_type: feature
title: Add project-specific group IDs to config
updated: 2026-01-30 00:00:00+00:00
wave: 6
---

# Task: Add project-specific group IDs to config

## Description

Define and implement the standard group IDs for project-specific knowledge in the configuration. These groups organize different types of knowledge within a project namespace.

## Acceptance Criteria

- [ ] Project group IDs defined in constants
- [ ] Groups configurable via .guardkit/graphiti.yaml
- [ ] Default groups created during project init
- [ ] Group descriptions documented

## Implementation Notes

### Project Group IDs

```python
# src/guardkit/integrations/graphiti/constants.py

PROJECT_GROUPS = {
    "project_overview": "High-level project purpose and goals",
    "project_architecture": "System architecture and patterns",
    "feature_specs": "Feature specifications and requirements",
    "project_decisions": "Architecture Decision Records (ADRs)",
    "project_constraints": "Constraints and limitations",
    "domain_knowledge": "Domain terminology and concepts",
}

SYSTEM_GROUPS = {
    "role_constraints": "Player/Coach role boundaries",
    "quality_gate_configs": "Task-type specific quality thresholds",
    "implementation_modes": "Direct vs task-work patterns",
}
```

### Config Schema

```yaml
# .guardkit/graphiti.yaml
project_id: my-project
groups:
  enabled:
    - project_overview
    - project_architecture
    - feature_specs
  disabled:
    - domain_knowledge  # Not needed for this project
```

### Files to Create/Modify

- `src/guardkit/integrations/graphiti/constants.py` - Add group definitions
- `src/guardkit/integrations/graphiti/config.py` - Add group config

## Test Requirements

- [ ] Unit tests for group constants
- [ ] Unit tests for config loading

## Notes

First task in Phase 2 (core functionality).

## References

- [FEAT-GR-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-001-project-knowledge-seeding.md)