---
id: TASK-FIX-ASPF-007
title: Eliminate double-write of player_turn_N.json in synthetic path
status: completed
task_type: implementation
created: 2026-02-24T23:00:00Z
completed: 2026-02-25T00:00:00Z
priority: low
tags: [agent-invoker, code-cleanup, synthetic-report]
complexity: 1
parent_review: TASK-REV-953F
feature_id: FEAT-ASPF
wave: 1
implementation_mode: direct
dependencies: []
completed_location: tasks/completed/TASK-FIX-ASPF-007/
---

# Task: Eliminate double-write of player_turn_N.json in synthetic path

## Description

In `invoke_player_direct()` at `agent_invoker.py:2657-2711`, when a synthetic report is created:

1. Line ~2690: `_write_player_report_for_direct_mode(task_id, turn, synthetic_report)` — first write
2. Line ~2696: Report is loaded from disk
3. Line ~2711: `_write_player_report_for_direct_mode(task_id, turn, report)` — second write (same data)

The second write is redundant since the report was just written in step 1.

## Fix

Added a `used_synthetic` flag that tracks whether the synthetic report path was taken. When it was, the second call to `_write_player_report_for_direct_mode()` is skipped via `if not used_synthetic` guard.

## Acceptance Criteria

1. [x] `player_turn_N.json` is written exactly once in the synthetic path
2. [x] Coach still reads correct data
3. [x] All existing tests pass (407/407 passed)

## Files Modified

- `guardkit/orchestrator/agent_invoker.py` — `invoke_player_direct()` (lines 2656, 2693, 2713-2715)

## Implementation Details

Three changes to `invoke_player_direct()`:
1. Line 2656: Initialize `used_synthetic = False` before report existence check
2. Line 2693: Set `used_synthetic = True` after synthetic write
3. Lines 2713-2715: Guard second write with `if not used_synthetic`

Non-synthetic path (SDK writes its own report) is unchanged.
