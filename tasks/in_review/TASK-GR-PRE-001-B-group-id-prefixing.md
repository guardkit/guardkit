---
complexity: 4
conductor_workspace: gr-mvp-wave3-namespace
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-000-C
feature_id: FEAT-GR-MVP
id: TASK-GR-PRE-001-B
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- project-namespace
- group-id
- mvp-phase-1
task_type: feature
title: Implement group ID prefixing
updated: 2026-01-30 00:00:00+00:00
wave: 3
---

# Task: Implement group ID prefixing

## Description

Implement automatic group ID prefixing so that project-specific knowledge is namespaced with the project_id. This enables multiple projects to share a Graphiti instance without knowledge collision.

## Acceptance Criteria

- [x] Project-specific group IDs are prefixed with `{project_id}__`
- [x] System-level group IDs remain unprefixed
- [x] Prefix is applied automatically when adding episodes
- [x] Search respects project namespace
- [x] Cross-project search is possible when needed

## Implementation Notes

### Group ID Format

```python
# Project-specific (prefixed)
f"{project_id}__project_overview"     # my-project__project_overview
f"{project_id}__feature_specs"        # my-project__feature_specs

# System-level (no prefix)
"role_constraints"
"quality_gate_configs"
"implementation_modes"
```

### Prefix Logic

```python
def get_group_id(self, group_name: str, scope: str = "project") -> str:
    """Get correctly prefixed group ID."""
    if scope == "system":
        return group_name
    return f"{self.project_id}__{group_name}"
```

### Project Groups (MUST prefix)

- `project_overview`
- `project_architecture`
- `feature_specs`
- `project_decisions`
- `project_constraints`
- `domain_knowledge`

### System Groups (NO prefix)

- `role_constraints`
- `quality_gate_configs`
- `implementation_modes`
- `guardkit_templates`
- `guardkit_patterns`

### Files Modified

- `guardkit/knowledge/graphiti_client.py` - Added prefixing logic with:
  - `get_group_id(group_name, scope)` - Main method for getting prefixed group IDs
  - `is_project_group(group_name)` - Detects if group should be prefixed
  - `_is_already_prefixed(group_id)` - Prevents double-prefixing
  - `_apply_group_prefix(group_id, scope)` - Internal prefix application
  - `PROJECT_GROUP_NAMES` list - Standard project groups
  - `SYSTEM_GROUP_IDS` list - System groups (no prefix)
- `guardkit/integrations/graphiti/constants.py` - SourceType enum already exists

## Test Requirements

- [x] Unit tests for prefixing logic (tests/knowledge/test_graphiti_group_prefixing.py - 35 tests)
- [x] Unit tests for system vs project scope detection (tests/knowledge/test_graphiti_client_project_id.py - 54 tests)
- [x] Integration test with multiple projects (test_full_workflow_with_prefixing, test_cross_project_isolation)

## Notes

Must be completed in same wave as TASK-GR-PRE-001-A for coherent namespace support.

## References

- [FEAT-GR-PRE-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-001-project-namespace-foundation.md)