---
id: TASK-CR-004
title: Trim graphiti-knowledge.md content
status: in_review
created: 2026-02-05 14:00:00+00:00
updated: 2026-02-05 14:00:00+00:00
priority: medium
tags:
- context-optimization
- token-reduction
parent_review: TASK-REV-5F19
feature_id: FEAT-CR01
implementation_mode: task-work
wave: 1
complexity: 3
task_type: refactor
depends_on:
- TASK-CR-003
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CR01
  base_branch: main
  started_at: '2026-02-05T17:27:40.761486'
  last_updated: '2026-02-05T17:34:41.501691'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-05T17:27:40.761486'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Trim graphiti-knowledge.md Content

## Description

Reduce graphiti-knowledge.md from ~377 lines (~1,508 tokens) to ~85 lines (~340 tokens) by removing verbose examples, session flow diagrams, and implementation details that can be retrieved from Graphiti itself or docs.

## Acceptance Criteria

- [ ] File reduced to ~85 lines
- [ ] Retained: Interactive Capture overview (condensed), Focus Categories table, Knowledge Query Commands (syntax only)
- [ ] Removed/migrated: AutoBuild Customization examples, Session Flow diagram, Turn State Tracking detail, Turn State Schema, Job-Specific Context Retrieval, Budget Allocation tables, Troubleshooting
- [ ] All guardkit graphiti commands still documented with syntax

## Implementation Notes

Keep: command syntax reference and focus categories table.
Remove: verbose examples, implementation internals, troubleshooting (move to docs/).

Estimated savings: ~1,168 tokens
