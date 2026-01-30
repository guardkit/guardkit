---
complexity: 3
conductor_workspace: gr-mvp-wave1-clear
created: 2026-01-30 00:00:00+00:00
depends_on: []
feature_id: FEAT-GR-MVP
id: TASK-GR-PRE-000-B
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- cli
- clear-command
- mvp-phase-0
task_type: feature
title: Add guardkit graphiti clear command
updated: 2026-01-30T12:00:00+00:00
wave: 1
---

# Task: Add guardkit graphiti clear command

## Description

Implement a `guardkit graphiti clear` CLI command that safely clears Graphiti knowledge. This is essential for development, testing, and resetting project knowledge during iteration.

## Acceptance Criteria

- [x] `guardkit graphiti clear --confirm` clears ALL knowledge (project + system)
- [x] `guardkit graphiti clear --system-only --confirm` clears only system knowledge
- [x] `guardkit graphiti clear --project-only --confirm` clears only project knowledge
- [x] Command requires `--confirm` flag (no accidental clearing)
- [x] Clear shows summary of what will be deleted before proceeding
- [x] Dry-run mode available with `--dry-run`
- [x] Clear respects project namespace boundaries

## Implementation Notes

### CLI Structure

```bash
guardkit graphiti clear [OPTIONS]

Options:
  --confirm         Required. Confirm deletion.
  --system-only     Only clear system-level knowledge (not project-specific)
  --project-only    Only clear current project's knowledge
  --dry-run         Show what would be deleted without deleting
  --force           Skip confirmation prompts (for automation)
```

### Clear Logic

```python
def clear_graphiti(
    confirm: bool,
    system_only: bool = False,
    project_only: bool = False,
    dry_run: bool = False
) -> ClearResult:
    """Clear Graphiti knowledge with safety checks."""
    # 1. Determine what to clear
    # 2. Show summary
    # 3. Execute if confirmed
    pass
```

### Files to Create/Modify

- `src/guardkit/cli/commands/graphiti_clear.py` - New command
- `src/guardkit/integrations/graphiti/client.py` - Add clear methods

### Group IDs to Handle

**System Groups** (cleared with --system-only):
- `guardkit_templates`
- `guardkit_patterns`
- `guardkit_workflows`

**Project Groups** (cleared with --project-only):
- `{project}__project_overview`
- `{project}__project_architecture`
- `{project}__feature_specs`
- `{project}__project_decisions`

## Test Requirements

- [x] Unit tests for clear logic with mocked Graphiti
- [x] Integration test with real Graphiti (in test database)
- [x] Test that --confirm is required
- [x] Test dry-run output

## Notes

Parallel with TASK-GR-PRE-000-A (can run in same wave).

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)