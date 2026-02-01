---
id: TASK-GR5-001
title: Implement `show` command
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies: []
autobuild_state:
  current_turn: 2
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T14:12:26.733364'
  last_updated: '2026-02-01T14:23:22.666493'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T14:12:26.733364'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-02-01T14:21:23.181007'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Implement `show` command

## Description

Implement the `guardkit graphiti show` command to display details of specific knowledge by type and ID.

## Acceptance Criteria

- [ ] `show feature FEAT-XXX` displays feature spec details
- [ ] `show adr ADR-001` displays ADR details
- [ ] `show project-overview` displays project overview
- [ ] Supports types: feature, adr, project-overview, pattern, constraint, guide
- [ ] Formatted output with colored sections
- [ ] Handles "not found" gracefully

## Usage Examples

```bash
guardkit graphiti show feature FEAT-SKEL-001
guardkit graphiti show adr ADR-001
guardkit graphiti show project-overview
```

**Reference**: See FEAT-GR-005-knowledge-query-command.md for output format.
