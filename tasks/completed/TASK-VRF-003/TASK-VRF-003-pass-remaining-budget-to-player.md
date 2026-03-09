---
id: TASK-VRF-003
title: Pass remaining_budget to invoke_player for SDK timeout capping
status: completed
completed: 2026-03-09T00:00:00Z
completed_location: tasks/completed/TASK-VRF-003/
priority: high
complexity: 4
tags: [autobuild, timeout, budget, agent-invoker]
parent_review: TASK-REV-5E1F
feature_id: FEAT-9db9
wave: 2
implementation_mode: task-work
dependencies: []
created: 2026-03-09
---

# Task: Pass remaining_budget to invoke_player

## Description

Add `remaining_budget: Optional[float]` parameter to `invoke_player()` and use `min(calculated_timeout, remaining_budget)` for SDK timeout. This matches the existing Coach behavior in `invoke_coach()` and prevents the Player from starting turns it cannot finish.

## Context

From TASK-REV-5E1F review: `invoke_player()` does NOT accept `remaining_budget`, while `invoke_coach()` does. This asymmetry means Player SDK calls cannot be dynamically shortened as budget depletes, leading to turns that start but cannot complete.

## Changes Required

1. **`guardkit/orchestrator/agent_invoker.py`**:
   - Add `remaining_budget: Optional[float] = None` parameter to `invoke_player()` (line ~1071)
   - In `_calculate_sdk_timeout()` call within invoke_player, pass `remaining_budget` (like invoke_coach does at line ~1351)

2. **`guardkit/orchestrator/autobuild.py`**:
   - Update `_invoke_player_safely()` (line ~3787) to accept and forward `remaining_budget`
   - Update `_execute_turn()` (line ~2020) to pass `remaining_budget` when calling `_invoke_player_safely()`
   - The `remaining_budget` is already available in `_execute_turn()` as a parameter

3. **`guardkit/orchestrator/agent_invoker.py`** `_calculate_sdk_timeout()`:
   - Already has the `remaining_budget` cap logic at lines 3371-3373
   - Just needs invoke_player to pass it through

## Acceptance Criteria

- [x] `invoke_player()` accepts `remaining_budget: Optional[float]` parameter
- [x] SDK timeout is capped to `min(calculated, remaining_budget)` when remaining_budget provided
- [x] `_invoke_player_safely()` forwards remaining_budget
- [x] `_execute_turn()` passes remaining_budget to player invocation
- [x] Existing tests pass
- [x] Coach behavior unchanged (regression check)
