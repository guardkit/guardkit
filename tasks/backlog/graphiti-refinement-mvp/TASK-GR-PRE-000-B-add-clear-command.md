---
id: TASK-GR-PRE-000-B
title: Add guardkit graphiti clear command
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- cli
- clear-command
- mvp-phase-0
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 1
conductor_workspace: gr-mvp-wave1-clear
complexity: 3
depends_on: []
autobuild_state:
  current_turn: 6
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-01-30T22:01:13.743910'
  last_updated: '2026-01-30T22:23:19.466076'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-01-30T22:01:13.743910'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-01-30T22:09:18.518203'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-01-30T22:10:49.062309'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-01-30T22:12:07.086991'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 5
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-01-30T22:14:27.978791'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 6
    decision: approve
    feedback: null
    timestamp: '2026-01-30T22:18:21.926059'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Add guardkit graphiti clear command

## Description

Implement a `guardkit graphiti clear` CLI command that safely clears Graphiti knowledge. This is essential for development, testing, and resetting project knowledge during iteration.

## Acceptance Criteria

- [ ] `guardkit graphiti clear --confirm` clears ALL knowledge (project + system)
- [ ] `guardkit graphiti clear --system-only --confirm` clears only system knowledge
- [ ] `guardkit graphiti clear --project-only --confirm` clears only project knowledge
- [ ] Command requires `--confirm` flag (no accidental clearing)
- [ ] Clear shows summary of what will be deleted before proceeding
- [ ] Dry-run mode available with `--dry-run`
- [ ] Clear respects project namespace boundaries

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

- [ ] Unit tests for clear logic with mocked Graphiti
- [ ] Integration test with real Graphiti (in test database)
- [ ] Test that --confirm is required
- [ ] Test dry-run output

## Notes

Parallel with TASK-GR-PRE-000-A (can run in same wave).

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)
