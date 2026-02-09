---
autobuild_state:
  base_branch: main
  current_turn: 1
  last_updated: '2026-02-09T12:06:45.309221'
  max_turns: 25
  started_at: '2026-02-09T12:00:33.603202'
  turns:
  - coach_success: true
    decision: approve
    feedback: null
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-02-09T12:00:33.603202'
    turn: 1
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-6EDD
complexity: 3
dependencies: []
feature_id: FEAT-SP-001
id: TASK-SP-002
implementation_mode: task-work
parent_review: TASK-REV-DBBC
status: in_review
tags:
- system-plan
- complexity
- gating
task_type: feature
title: Add complexity gating for architecture context
wave: 1
---

# Task: Add Complexity Gating for Architecture Context

## Description

Implement the complexity gating logic that determines when architecture context should be loaded for tasks. Simple tasks (complexity 1-3) don't need architecture context, while complex tasks (7+) get full context with higher token budgets.

## Acceptance Criteria

- [x] `ARCHITECTURE_CONTEXT_THRESHOLD = 4` constant defined
- [x] `ARCH_TOKEN_BUDGETS` dict with low/medium/high/critical tiers
- [x] `get_arch_token_budget(complexity: int) -> int` function
- [x] Complexity 1-3 returns 0 tokens (no architecture context)
- [x] Complexity 4-6 returns 1000 tokens
- [x] Complexity 7-8 returns 2000 tokens
- [x] Complexity 9-10 returns 3000 tokens
- [x] Unit tests for all complexity tiers and boundary values

## Files to Create/Modify

- `guardkit/planning/__init__.py` — New package init
- `guardkit/planning/complexity_gating.py` — Gating logic and constants
- `tests/unit/planning/test_complexity_gating.py` — Unit tests

## Implementation Notes

- Pure functions, no external dependencies
- Follow spec section "Complexity Gating (Key Design Decision #8)"
- Consider edge cases: complexity=0, complexity=11 (should clamp or handle gracefully)