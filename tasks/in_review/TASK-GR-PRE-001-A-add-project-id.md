---
complexity: 3
conductor_workspace: gr-mvp-wave3-namespace
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-000-C
feature_id: FEAT-GR-MVP
id: TASK-GR-PRE-001-A
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- project-namespace
- client
- mvp-phase-1
task_type: feature
title: Add project_id to GraphitiClient
updated: 2026-01-30 00:00:00+00:00
wave: 3
---

# Task: Add project_id to GraphitiClient

## Description

Extend the GraphitiClient to accept and store a `project_id` that will be used for namespacing all project-specific operations. The project_id is derived from the directory name with optional override.

## Acceptance Criteria

- [x] GraphitiClient accepts optional `project_id` parameter
- [x] Project ID is auto-detected from directory name if not provided
- [x] Project ID can be overridden via `.guardkit/graphiti.yaml`
- [x] Project ID is validated (alphanumeric + hyphens only)
- [x] Project ID is stored and accessible for prefixing operations
- [x] Backward compatible (no project_id = global/system scope)

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

### Files Modified

- `guardkit/knowledge/graphiti_client.py` - Added project_id support with normalize_project_id()
- `guardkit/knowledge/config.py` - Added config loading with GUARDKIT_PROJECT_ID env var support

## Test Requirements

- [x] Unit tests for project ID detection (TestProjectIdAutoDetection - 6 tests)
- [x] Unit tests for project ID validation (TestNormalizeProjectId - 10 tests)
- [x] Unit tests for config file loading (TestGraphitiConfigLoading - 8 tests)
- [x] Integration test with GraphitiClient (TestGraphitiClientProjectId - 12 tests)

## Test Results

**Test File**: `tests/knowledge/test_graphiti_client_project_id.py`
**Total Tests**: 54
**Passed**: 54 (100%)
**Failed**: 0

## Implementation Summary

The implementation was already complete in the worktree. Key components:

1. **normalize_project_id()** function in `graphiti_client.py`:
   - Converts to lowercase
   - Replaces spaces/underscores with hyphens
   - Removes non-alphanumeric characters (except hyphens)
   - Truncates to max 50 characters

2. **GraphitiConfig** dataclass:
   - Added `project_id: Optional[str] = None` field
   - Validation in `__post_init__` for invalid characters and length

3. **GraphitiClient**:
   - `project_id` property with getter/setter
   - `get_project_id(auto_detect=None)` method
   - `get_group_id(group_name, scope=None)` for prefixing
   - Auto-detection via `get_current_project_name()`

4. **GraphitiSettings** dataclass in `config.py`:
   - Added `project_id: Optional[str] = None` field
   - GUARDKIT_PROJECT_ID environment variable support

## Notes

Can run in parallel with TASK-GR-PRE-001-B, PRE-002-A, PRE-002-B, PRE-003-A.

## References

- [FEAT-GR-PRE-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-001-project-namespace-foundation.md)
