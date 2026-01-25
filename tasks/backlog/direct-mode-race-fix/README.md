# Feature: Direct Mode Race Condition Fix

**Parent Review**: TASK-REV-3EC5
**Feature ID**: FEAT-DMRF
**Created**: 2026-01-25

## Problem Statement

The direct mode invocation path (`_invoke_player_direct`) in the AutoBuild orchestrator has a race condition where the Player report file is written but not immediately visible to the orchestrator due to filesystem buffering.

**Evidence**: In FEAT-F392 first attempt, line 83 of the session log shows "Wrote direct mode player report" immediately followed by line 84 "Player report missing". State recovery at line 90 then successfully loads the same file.

## Solution Approach

1. **P0**: Add retry/delay mechanism to `_invoke_player_direct` for report file detection
2. **P1**: Improve state recovery to trust Player report when it loads successfully
3. **P1**: Always run git detection as verification (not just as fallback)

## Subtasks

| ID | Name | Mode | Wave | Complexity |
|----|------|------|------|------------|
| TASK-DMRF-001 | Add retry mechanism to direct mode report loading | task-work | 1 | 3 |
| TASK-DMRF-002 | Improve state recovery has_work logic | task-work | 1 | 2 |
| TASK-DMRF-003 | Add git detection as verification step | task-work | 2 | 2 |

## Execution Strategy

**Wave 1** (parallel):
- TASK-DMRF-001: Retry mechanism
- TASK-DMRF-002: State recovery fix

**Wave 2** (sequential, depends on Wave 1):
- TASK-DMRF-003: Git verification

## Success Criteria

1. Direct mode tasks complete without false "report not found" errors
2. State recovery correctly identifies work when Player report exists
3. Git changes are always captured in Player reports
