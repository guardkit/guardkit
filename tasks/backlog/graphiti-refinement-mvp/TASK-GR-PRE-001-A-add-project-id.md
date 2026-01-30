---
id: TASK-GR-PRE-001-A
title: Add project_id to GraphitiClient
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, project-namespace, client, mvp-phase-1]
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 3
conductor_workspace: gr-mvp-wave3-namespace
complexity: 3
depends_on:
  - TASK-GR-PRE-000-C
---

# Task: Add project_id to GraphitiClient

## Description

Extend the GraphitiClient to accept and store a `project_id` that will be used for namespacing all project-specific operations. The project_id is derived from the directory name with optional override.

## Acceptance Criteria

- [ ] GraphitiClient accepts optional `project_id` parameter
- [ ] Project ID is auto-detected from directory name if not provided
- [ ] Project ID can be overridden via `.guardkit/graphiti.yaml`
- [ ] Project ID is validated (alphanumeric + hyphens only)
- [ ] Project ID is stored and accessible for prefixing operations
- [ ] Backward compatible (no project_id = global/system scope)

## Implementation Notes

### Configuration Priority

1. Explicit parameter to GraphitiClient
2. `.guardkit/graphiti.yaml` project_id field
3. Current directory name (slugified)

### Project ID Format

```python
def normalize_project_id(name: str) -> str:
    """Normalize project ID to valid format."""
    # lowercase, replace spaces with hyphens
    # remove non-alphanumeric (except hyphens)
    # max 50 characters
    pass
```

### Config File

```yaml
# .guardkit/graphiti.yaml
project_id: my-project-name  # Optional override
```

### Files to Modify

- `src/guardkit/integrations/graphiti/client.py` - Add project_id support
- `src/guardkit/integrations/graphiti/config.py` - Add config loading

## Test Requirements

- [ ] Unit tests for project ID detection
- [ ] Unit tests for project ID validation
- [ ] Unit tests for config file loading
- [ ] Integration test with GraphitiClient

## Notes

Can run in parallel with TASK-GR-PRE-001-B, PRE-002-A, PRE-002-B, PRE-003-A.

## References

- [FEAT-GR-PRE-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-001-project-namespace-foundation.md)
