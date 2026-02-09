---
id: TASK-SP-002
title: "Add complexity gating for architecture context"
status: pending
task_type: feature
parent_review: TASK-REV-DBBC
feature_id: FEAT-SP-001
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
tags: [system-plan, complexity, gating]
---

# Task: Add Complexity Gating for Architecture Context

## Description

Implement the complexity gating logic that determines when architecture context should be loaded for tasks. Simple tasks (complexity 1-3) don't need architecture context, while complex tasks (7+) get full context with higher token budgets.

## Acceptance Criteria

- [ ] `ARCHITECTURE_CONTEXT_THRESHOLD = 4` constant defined
- [ ] `ARCH_TOKEN_BUDGETS` dict with low/medium/high/critical tiers
- [ ] `get_arch_token_budget(complexity: int) -> int` function
- [ ] Complexity 1-3 returns 0 tokens (no architecture context)
- [ ] Complexity 4-6 returns 1000 tokens
- [ ] Complexity 7-8 returns 2000 tokens
- [ ] Complexity 9-10 returns 3000 tokens
- [ ] Unit tests for all complexity tiers and boundary values

## Files to Create/Modify

- `guardkit/planning/__init__.py` — New package init
- `guardkit/planning/complexity_gating.py` — Gating logic and constants
- `tests/unit/planning/test_complexity_gating.py` — Unit tests

## Implementation Notes

- Pure functions, no external dependencies
- Follow spec section "Complexity Gating (Key Design Decision #8)"
- Consider edge cases: complexity=0, complexity=11 (should clamp or handle gracefully)
