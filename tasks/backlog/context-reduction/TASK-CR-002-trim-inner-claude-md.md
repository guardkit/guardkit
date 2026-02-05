---
id: TASK-CR-002
title: Trim .claude/CLAUDE.md and remove duplicates
status: in_review
created: 2026-02-05 14:00:00+00:00
updated: 2026-02-05 14:00:00+00:00
priority: high
tags:
- context-optimization
- token-reduction
parent_review: TASK-REV-5F19
feature_id: FEAT-CR01
implementation_mode: task-work
wave: 1
complexity: 2
task_type: refactor
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CR01
  base_branch: main
  started_at: '2026-02-05T17:14:31.105271'
  last_updated: '2026-02-05T17:23:49.797783'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-05T17:14:31.105271'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Trim .claude/CLAUDE.md and Remove Duplicates

## Description

Reduce .claude/CLAUDE.md from ~113 lines (~450 tokens) to ~30 lines (~140 tokens) by removing sections that duplicate the root CLAUDE.md.

## Acceptance Criteria

- [ ] .claude/CLAUDE.md reduced to ~30 lines
- [ ] Retained: Project Context paragraph, Technology Stack Detection
- [ ] Removed: Core Principles (duplicate), Workflow Overview (duplicate), Getting Started (duplicate), Dev Mode Selection (duplicate)
- [ ] Clarifying Questions reference condensed to 1-line pointer

## Implementation Notes

The .claude/CLAUDE.md currently repeats core principles, workflow overview, and development mode selection that are already in root CLAUDE.md. Since both files load, this is pure duplication.

Estimated savings: ~310 tokens
