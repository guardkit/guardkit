---
id: TASK-GR-PRE-001-A
title: Add project_id to GraphitiClient
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- project-namespace
- client
- mvp-phase-1
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 3
conductor_workspace: gr-mvp-wave3-namespace
complexity: 3
depends_on:
- TASK-GR-PRE-000-C
autobuild_state:
  current_turn: 3
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-01-30T22:31:36.548818'
  last_updated: '2026-01-30T22:51:41.985664'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- task-work execution exceeded 900s timeout'
    timestamp: '2026-01-30T22:31:36.548818'
    player_summary: '[RECOVERED via git_only] Original error: SDK timeout after 900s:
      task-work execution exceeded 900s timeout'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-01-30T22:46:39.551979'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-01-30T22:49:42.040245'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
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
