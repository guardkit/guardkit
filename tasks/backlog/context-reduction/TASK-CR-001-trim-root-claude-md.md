---
id: TASK-CR-001
title: Trim root CLAUDE.md to lean version
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
complexity: 5
task_type: refactor
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CR01
  base_branch: main
  started_at: '2026-02-05T17:14:31.105564'
  last_updated: '2026-02-05T17:27:40.714528'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-05T17:14:31.105564'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-02-05T17:23:38.844724'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Trim Root CLAUDE.md to Lean Version

## Description

Reduce root CLAUDE.md from ~996 lines (~3,980 tokens) to ~300 lines (~1,600 tokens) by removing content that duplicates command specs, rules files, or is rarely needed at conversation start.

## Acceptance Criteria

- [ ] Root CLAUDE.md reduced to ~300 lines
- [ ] Retained sections: Core Features, Core Principles, Essential Commands (syntax only), Task Workflow Phases, Quality Gates table, Task States & Transitions, Testing by Stack, Project Structure
- [ ] Removed/condensed sections: /feature-plan verbose example, /feature-build details, /feature-complete details, Review vs Implementation verbose table, Review Modes/Depth/Examples, Installation & Setup, Conductor Integration, Template Philosophy/Quality, Progressive Disclosure, Rules Structure, MCP Integration, Graphiti Knowledge section, Troubleshooting, Known Limitations, When to Use GuardKit
- [ ] All removed content is either already in path-gated rules files or command specs
- [ ] No workflow regressions: /task-work, /feature-build, /feature-plan still function correctly

## Implementation Notes

Key principle: CLAUDE.md should be a **quick reference card**, not comprehensive documentation. Command specs (`installer/core/commands/*.md`) and rules files already contain the detail.

Sections to keep (compress where possible):
- Core Features + Principles (~80 tokens)
- Essential Commands - syntax only, no examples (~200 tokens)
- Task Workflow Phases (~140 tokens)
- Quality Gates table (~120 tokens)
- Task States & Transitions (~160 tokens)
- Project Structure (~80 tokens)
- Testing by Stack (~60 tokens)
- Complexity Evaluation - table only (~80 tokens)
- Design-First Workflow - 1-liner reference (~20 tokens)

Estimated savings: ~2,380 tokens
