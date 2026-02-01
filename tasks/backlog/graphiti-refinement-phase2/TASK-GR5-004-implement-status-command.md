---
id: TASK-GR5-004
title: Implement `status` command
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: direct
complexity: 3
estimate_hours: 1
dependencies:
- TASK-GR5-001
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T14:23:22.799134'
  last_updated: '2026-02-01T14:27:46.047495'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T14:23:22.799134'
    player_summary: "Enhanced the existing `guardkit graphiti status` command to show\
      \ knowledge graph health and statistics. The implementation includes:\n\n1.\
      \ **Enhanced CLI Command**: Updated the `status` command to accept a `--verbose`\
      \ flag that shows all groups even if empty.\n\n2. **Knowledge Graph Statistics**:\
      \ Modified `_cmd_status()` to query Graphiti for episode counts across four\
      \ main categories:\n   - System Knowledge (product_knowledge, command_workflows,\
      \ patterns, agents)\n   - Project Knowledge (project_over"
    player_success: true
    coach_success: true
---

# Implement `status` command

## Description

Implement the `guardkit graphiti status` command to show knowledge graph health and statistics.

## Acceptance Criteria

- [ ] Shows enabled/disabled status
- [ ] Counts episodes per category (System, Project, Decisions, Learning)
- [ ] `--verbose` shows all groups even if empty
- [ ] Total episode count
- [ ] Colored status indicators (green/yellow/red)

## Usage Examples

```bash
guardkit graphiti status
guardkit graphiti status --verbose
```

**Reference**: See FEAT-GR-005 status output format.
