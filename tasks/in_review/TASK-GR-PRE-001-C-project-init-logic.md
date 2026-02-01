---
complexity: 4
conductor_workspace: gr-mvp-wave4-init
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-001-A
- TASK-GR-PRE-001-B
feature_id: FEAT-GR-MVP
id: TASK-GR-PRE-001-C
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- project-namespace
- initialization
- mvp-phase-1
task_type: feature
title: Add project initialization logic
updated: 2026-01-31 00:00:00+00:00
wave: 4
---

# Task: Add project initialization logic

## Description

Implement project initialization logic that creates the necessary namespace and configuration when a project first connects to Graphiti.

## Acceptance Criteria

- [x] First use of project_id creates project namespace
- [x] Project metadata is stored (name, created_at, config)
- [x] Existing projects are detected and loaded
- [x] Project list is queryable
- [x] Graceful handling when Graphiti is unavailable

## Implementation Notes

### Initialization Flow

```python
async def initialize_project(project_id: str) -> ProjectInfo:
    """Initialize or load project namespace."""
    # 1. Check if project exists
    # 2. Create if new, load if existing
    # 3. Return project info
    pass
```

### Project Metadata Episode

```python
{
    "entity_type": "project_metadata",
    "project_id": "my-project",
    "created_at": "2026-01-30T00:00:00Z",
    "last_accessed": "2026-01-30T00:00:00Z",
    "graphiti_version": "1.0.0",
    "config": {
        # Project-specific config
    }
}
```

### Files Modified

- `guardkit/integrations/graphiti/project.py` - New file for project management
  - `ProjectInfo` dataclass with serialization
  - `ProjectConfig` dataclass for project settings
  - `initialize_project()` - Initialize or load project
  - `get_project_info()` - Get existing project info
  - `list_projects()` - List all projects
  - `project_exists()` - Check if project exists
  - `update_project_access_time()` - Update last accessed timestamp

## Test Requirements

- [x] Unit tests for initialization flow
- [x] Integration test for new project creation
- [x] Integration test for existing project loading
- [x] Test graceful degradation when Graphiti unavailable

## Test Results

**Test File**: `tests/integrations/graphiti/test_project_init.py`
**Total Tests**: 42
**Passed**: 40 (100%)
**Skipped**: 2 (integration tests requiring live Neo4j)
**Failed**: 0

### Test Coverage by Category

1. **ProjectInfo Dataclass Tests** (5 tests) - All pass
   - Creation with required/all fields
   - Serialization to/from dict
   - Default values

2. **ProjectConfig Dataclass Tests** (3 tests) - All pass
   - Default values
   - Custom values
   - Serialization

3. **initialize_project() Tests** (8 tests) - All pass
   - Creates namespace for new project
   - Stores metadata
   - Loads existing project
   - Custom config
   - Normalizes project_id
   - Graceful degradation (disabled, not connected, client None)

4. **get_project_info() Tests** (5 tests) - All pass
   - Returns existing project
   - Returns None for nonexistent
   - Graceful degradation
   - Handles search errors
   - Normalizes project_id

5. **list_projects() Tests** (5 tests) - All pass
   - Returns all projects
   - Returns empty when no projects
   - Graceful degradation
   - Handles search errors
   - Uses correct group

6. **project_exists() Tests** (4 tests) - All pass
   - Returns True for existing
   - Returns False for nonexistent
   - Graceful degradation
   - Normalizes project_id

7. **update_project_access_time() Tests** (3 tests) - All pass
   - Updates last_accessed
   - Returns False for nonexistent
   - Graceful degradation

8. **Edge Cases and Error Handling** (5 tests) - All pass
   - Empty string project_id
   - None project_id
   - Special characters normalization
   - Invalid dict for from_dict
   - Concurrent initialization

9. **Module-Level Constants** (2 tests) - All pass
   - PROJECT_METADATA_GROUP exists
   - Is system group (no prefix)

## Implementation Summary

The implementation provides a complete project initialization system with:

1. **Project Management Functions**:
   - `initialize_project()` - Create or load project namespace
   - `get_project_info()` - Query existing project
   - `list_projects()` - Enumerate all projects
   - `project_exists()` - Check existence
   - `update_project_access_time()` - Track usage

2. **Data Models**:
   - `ProjectInfo` - Complete project metadata
   - `ProjectConfig` - Project-specific settings

3. **Key Features**:
   - Project ID normalization
   - Graceful degradation when Graphiti unavailable
   - System-level metadata group (no project prefix)
   - Full serialization support (to_dict/from_dict)

## Notes

Depends on PRE-001-A and PRE-001-B completing first.

## References

- [FEAT-GR-PRE-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-001-project-namespace-foundation.md)
