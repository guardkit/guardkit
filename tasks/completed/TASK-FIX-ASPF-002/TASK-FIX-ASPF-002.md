---
id: TASK-FIX-ASPF-002
title: State recovery must write task_work_results.json to disk
status: completed
task_type: implementation
created: 2026-02-24T23:00:00Z
completed: 2026-02-25T00:00:00Z
priority: critical
tags: [autobuild, state-recovery, coach-validator, criteria-pipeline]
complexity: 3
parent_review: TASK-REV-953F
feature_id: FEAT-ASPF
wave: 1
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-FIX-ASPF-002/
---

# Task: State recovery must write task_work_results.json to disk

## Description

When the Player fails (SDK timeout, error), the autobuild orchestrator runs `_attempt_state_recovery()` which builds a synthetic report in memory. However, this recovered data is **never written to `task_work_results.json` on disk**. The Coach validator reads from disk and finds the stale ERROR-flagged version from the exception handler, causing it to short-circuit without evaluating criteria.

This is the root cause of Run 2 Turn 2 failure in the logging_feature_2 autobuild.

## Root Cause

In `autobuild.py:_execute_turn()`, after state recovery succeeds (~line 1855):

```python
if recovered_player_result:
    player_result = recovered_player_result  # In-memory only!
    # BUG: task_work_results.json still has {"error": "SDK timeout..."}
```

The Coach then reads the stale file at `coach_validator.py:583-586`:

```python
task_work_results = self.read_quality_gate_results(task_id)
if "error" in task_work_results:
    logger.warning(f"Task-work results not found for {task_id}")
    return self._feedback_result(...)  # Short-circuits!
```

## Fix

After `_attempt_state_recovery()` returns a recovered result, write the recovered data to disk using the existing `_write_direct_mode_results()` method.

**Location**: `guardkit/orchestrator/autobuild.py`, `_execute_turn()` method, after the line `player_result = recovered_player_result`

**Expected change** (~3 lines):

```python
if recovered_player_result:
    player_result = recovered_player_result
    # Write recovered data to disk so Coach can read it
    self._agent_invoker._write_direct_mode_results(
        task_id, player_result.report, success=True
    )
```

**Important**: The `_agent_invoker` attribute must be accessible from the AutoBuildOrchestrator. Verify the attribute name and access pattern. If `_agent_invoker` is not directly available, the write may need to go through an existing method or the worktree path must be used to locate the correct output directory.

## Expected Interface

The `_write_direct_mode_results(task_id, report, success)` method in `agent_invoker.py` expects:
- `task_id`: str — the task being processed
- `report`: dict — the player report (synthetic in this case)
- `success`: bool — whether the invocation succeeded

The report dict should contain at minimum: `requirements_addressed`, `_synthetic`, `completion_promises`.

## Acceptance Criteria

1. After state recovery, `task_work_results.json` contains the recovered synthetic data (not the error)
2. The Coach validator can read the recovered data and evaluate criteria
3. The `"error"` key is NOT present in the recovered `task_work_results.json`
4. Existing state recovery tests still pass
5. New test: verify that `task_work_results.json` is updated after state recovery

## Files to Modify

- `guardkit/orchestrator/autobuild.py` — `_execute_turn()` method (~line 1855)

## Files to Test

- `tests/unit/test_autobuild.py` or equivalent — add test for state recovery disk write
