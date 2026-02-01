---
id: TASK-GR-PRE-001-C
title: Add project initialization logic
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- project-namespace
- initialization
- mvp-phase-1
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 4
conductor_workspace: gr-mvp-wave4-init
complexity: 4
depends_on:
- TASK-GR-PRE-001-A
- TASK-GR-PRE-001-B
autobuild_state:
  current_turn: 2
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-01-31T20:48:08.065262'
  last_updated: '2026-01-31T21:05:47.617482'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- task-work execution exceeded 900s timeout'
    timestamp: '2026-01-31T20:48:08.065262'
    player_summary: '[RECOVERED via git_only] Original error: SDK timeout after 900s:
      task-work execution exceeded 900s timeout'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-01-31T21:03:17.709135'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Add project initialization logic

## Description

Implement project initialization logic that creates the necessary namespace and configuration when a project first connects to Graphiti.

## Acceptance Criteria

- [ ] First use of project_id creates project namespace
- [ ] Project metadata is stored (name, created_at, config)
- [ ] Existing projects are detected and loaded
- [ ] Project list is queryable
- [ ] Graceful handling when Graphiti is unavailable

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

### Files to Modify

- `src/guardkit/integrations/graphiti/client.py` - Add init method
- `src/guardkit/integrations/graphiti/project.py` - New file for project management

## Test Requirements

- [ ] Unit tests for initialization flow
- [ ] Integration test for new project creation
- [ ] Integration test for existing project loading
- [ ] Test graceful degradation when Graphiti unavailable

## Notes

Depends on PRE-001-A and PRE-001-B completing first.

## References

- [FEAT-GR-PRE-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-001-project-namespace-foundation.md)
