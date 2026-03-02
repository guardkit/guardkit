---
id: TASK-ABFIX-004
title: Implement per-turn timeout budgeting with Coach grace period
task_type: feature
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
wave: 2
implementation_mode: task-work
complexity: 6
dependencies: [TASK-ABFIX-001]
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: completed
completed: 2026-03-02T00:00:00Z
completed_location: tasks/completed/TASK-ABFIX-004/
priority: critical
tags: [autobuild, orchestrator, timeout, feature-orchestrator]
---

# Task: Implement per-turn timeout budgeting with Coach grace period

## Description

Redesign the timeout architecture to use per-turn budgeting instead of a single wall-clock `task_timeout`. The current `asyncio.wait_for(timeout=2400s)` in `feature_orchestrator._execute_wave_parallel()` does not account for multi-turn tasks — turn 2 inherits whatever time remains from the 2400s budget, which may be insufficient.

Also add a grace period so that if the Player completes successfully near the timeout boundary, the Coach still gets invoked (Coach typically takes 10-17s).

## Review Reference

From TASK-REV-A17A Finding 1, Recommendations 1a and 1b:
> 1a: Make task_timeout per-turn, not per-wave. Reset the `asyncio.wait_for` deadline after each completed turn. Track cumulative turn time and extend by `remaining_sdk_timeout` when a turn completes.
> 1b: Add a "grace period" after Player completes. If Player returns `success=True` but task_timeout is about to fire, give 120s for Coach to run.

And Finding 7, Recommendation 7a:
> Skip cancellation check if Player succeeded and Coach is fast. If `player_result.success == True`, invoke Coach regardless of cancellation event, with a strict 120s timeout.

## Requirements

1. In `feature_orchestrator._execute_wave_parallel()` (lines 1296-1310):
   - Pass remaining time budget to `_execute_task()` rather than a fixed timeout
   - OR: restructure so each turn gets its own timeout allocation
2. In `autobuild._loop_phase` (lines 1472-1708):
   - Track cumulative elapsed time per turn
   - Before starting a new turn, check if remaining budget >= minimum turn budget (e.g., 600s)
   - If insufficient budget, exit gracefully with `"timeout_budget_exhausted"` instead of waiting for `asyncio.TimeoutError`
3. Add Coach grace period:
   - After Player returns `success=True`, if remaining budget < 120s but > 0, extend by 120s for Coach
   - In `autobuild._loop_phase:1588-1595`, if Player succeeded, skip the cancellation check and invoke Coach with a strict 120s timeout
4. Cap SDK timeout at remaining task budget:
   - In `agent_invoker._calculate_sdk_timeout()` (lines 3039-3111), accept an optional `remaining_budget` parameter
   - Return `min(calculated_timeout, remaining_budget)` when `remaining_budget` is provided

## Files to Modify

- `guardkit/orchestrator/feature_orchestrator.py` — pass time budget, grace period
- `guardkit/orchestrator/autobuild.py` — per-turn budget tracking, graceful exhaustion, Coach grace
- `guardkit/orchestrator/agent_invoker.py` — cap SDK timeout at remaining budget
- `tests/` — test timeout budget calculation, grace period, budget exhaustion

## Acceptance Criteria

- [ ] Multi-turn tasks get fair timeout allocation per turn (not all-from-wave-start)
- [ ] Coach grace period of 120s is granted when Player succeeds near timeout boundary
- [ ] SDK timeout is capped at remaining task budget
- [ ] Budget exhaustion produces a clear, distinct result from raw timeout
- [ ] Cancellation check between Player/Coach is skipped when Player succeeded
- [ ] All existing tests pass
- [ ] New tests cover per-turn budget calculation and edge cases
