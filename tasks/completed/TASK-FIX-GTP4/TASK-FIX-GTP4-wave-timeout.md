---
id: TASK-FIX-GTP4
title: Add defensive timeout to FeatureOrchestrator wave execution
status: completed
created: 2026-02-09T14:00:00Z
updated: 2026-02-09T17:00:00Z
completed: 2026-02-09T17:00:00Z
priority: high
tags: [fix, feature-orchestrator, timeout, defensive, parallel]
task_type: implementation
complexity: 4
feature: FEAT-C90E
test_results:
  status: passed
  tests_total: 7
  tests_passed: 7
  tests_failed: 0
  coverage: null
  last_run: 2026-02-09T16:30:00Z
---

# Task: Add Defensive Timeout to FeatureOrchestrator Wave Execution

## Description

Add a per-task timeout to `FeatureOrchestrator._execute_wave_parallel()` to prevent any individual task from blocking an entire wave indefinitely. This is a defensive backstop that would have prevented the ~20-minute stall observed in the FEAT-6EDD AutoBuild run.

See: `.claude/reviews/TASK-REV-2AA0-review-report.md` (Fix 3: Task-Level Timeout)

### Current Code (feature_orchestrator.py ~line 1063)

```python
# In _execute_wave_parallel()
tasks_to_execute.append(
    asyncio.to_thread(self._execute_task, task, feature, worktree)
)
parallel_results = await asyncio.gather(*tasks_to_execute, return_exceptions=True)
```

### Problem

If any task hangs (e.g., due to cross-loop Graphiti issues or any other cause), `asyncio.gather()` waits indefinitely. There is no upper bound on how long a single task can run within a wave.

### Fix

Wrap each task in `asyncio.wait_for()` with a configurable timeout:

```python
tasks_to_execute.append(
    asyncio.wait_for(
        asyncio.to_thread(self._execute_task, task, feature, worktree),
        timeout=self.task_timeout  # e.g., 2400s (40 min)
    )
)
```

Handle `asyncio.TimeoutError` in the `return_exceptions=True` results as a task failure.

## Acceptance Criteria

- [x] `task_timeout` parameter added to `FeatureOrchestrator.__init__()` with default of 2400s (40 min)
- [x] `--task-timeout` CLI option added to `guardkit feature` command
- [x] Each task in `_execute_wave_parallel()` wrapped with `asyncio.wait_for()`
- [x] `asyncio.TimeoutError` handled in result processing as a task failure with clear error message
- [x] Timeout value logged at wave start for visibility
- [x] Timed-out tasks reported in progress display with "TIMEOUT" status
- [x] Existing tests pass (pre-existing failures unrelated to this task)
- [x] New test: task timeout triggers after configured duration (use short timeout in test)
- [x] New test: successful tasks unaffected by timeout setting
- [x] New test: timeout error correctly reported as task failure

## Key Files

### Must Modify
- `guardkit/orchestrator/feature_orchestrator.py` — `_execute_wave_parallel()`, `__init__()`
- `guardkit/cli/main.py` — Add `--task-timeout` option to `feature` command

### Must Update Tests
- `tests/unit/test_feature_orchestrator.py` — Wave execution tests

### Reference
- `.claude/reviews/TASK-REV-2AA0-review-report.md` — Fix 3 recommendation
- `guardkit/orchestrator/progress.py` — Progress display (may need TIMEOUT status)

## Context

- Independent of TASK-FIX-GTP1 (factory) — can be done in parallel
- Defensive measure — prevents future hangs regardless of root cause
- The FEAT-6EDD run stalled for ~20 minutes before user killed the process
- Default timeout of 40 minutes is generous enough to not interfere with legitimate long tasks

## Implementation Notes

### Timeout Handling

When a task times out:
1. `asyncio.wait_for()` raises `asyncio.TimeoutError`
2. This is caught by `asyncio.gather(return_exceptions=True)` as an exception result
3. The result processing loop should detect `TimeoutError` and record it as a specific failure type
4. The timed-out thread may still be running — note that `asyncio.wait_for()` cancels the Future but the underlying `to_thread()` cannot be cancelled (thread continues running). The timeout ensures the wave doesn't wait indefinitely, but the thread itself completes naturally.

### Progress Display

Consider adding a "TIMEOUT" status to the progress display (`progress.py`) so the user can see which task timed out and which completed.

## Test Execution Log

[Automatically populated by /task-work]
