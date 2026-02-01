---
id: TASK-GR5-002
title: Implement `search` command
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
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T14:12:26.727937'
  last_updated: '2026-02-01T14:16:10.212442'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T14:12:26.727937'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Implement `search` command

## Description

Implement the `guardkit graphiti search` command to search for knowledge across all categories.

## Acceptance Criteria

- [ ] `search "query"` searches all groups
- [ ] `--group` option limits to specific group
- [ ] `--limit` option controls max results
- [ ] Results show relevance score with color coding
- [ ] Truncates long facts with "..."

## Usage Examples

```bash
guardkit graphiti search "authentication"
guardkit graphiti search "error handling" --group patterns
guardkit graphiti search "walking skeleton" --limit 5
```

**Reference**: See FEAT-GR-005 search output format.
