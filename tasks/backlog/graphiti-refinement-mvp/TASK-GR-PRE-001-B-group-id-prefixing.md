---
id: TASK-GR-PRE-001-B
title: Implement group ID prefixing
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- project-namespace
- group-id
- mvp-phase-1
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 3
conductor_workspace: gr-mvp-wave3-namespace
complexity: 4
depends_on:
- TASK-GR-PRE-000-C
autobuild_state:
  current_turn: 2
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-01-30T22:31:36.545851'
  last_updated: '2026-01-30T22:48:26.305902'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-01-30T22:31:36.545851'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-01-30T22:44:09.408105'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement group ID prefixing

## Description

Implement automatic group ID prefixing so that project-specific knowledge is namespaced with the project_id. This enables multiple projects to share a Graphiti instance without knowledge collision.

## Acceptance Criteria

- [ ] Project-specific group IDs are prefixed with `{project_id}__`
- [ ] System-level group IDs remain unprefixed
- [ ] Prefix is applied automatically when adding episodes
- [ ] Search respects project namespace
- [ ] Cross-project search is possible when needed

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

### Files to Modify

- `src/guardkit/integrations/graphiti/client.py` - Add prefixing logic
- `src/guardkit/integrations/graphiti/constants.py` - Define group types

## Test Requirements

- [ ] Unit tests for prefixing logic
- [ ] Unit tests for system vs project scope detection
- [ ] Integration test with multiple projects

## Notes

Must be completed in same wave as TASK-GR-PRE-001-A for coherent namespace support.

## References

- [FEAT-GR-PRE-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-PRE-001-project-namespace-foundation.md)
