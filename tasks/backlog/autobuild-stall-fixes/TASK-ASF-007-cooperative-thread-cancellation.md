---
id: TASK-ASF-007
title: Add cooperative thread cancellation to feature orchestrator
task_type: feature
parent_review: TASK-REV-SFT1
feature_id: FEAT-ASF
wave: 4
implementation_mode: task-work
complexity: 6
dependencies:
  - TASK-ASF-005
  - TASK-ASF-006
priority: medium
status: backlog
tags: [autobuild, stall-fix, R6, phase-4, thread-lifecycle]
---

# Task: Add cooperative thread cancellation to feature orchestrator

## Description

The feature orchestrator uses `asyncio.wait_for(asyncio.to_thread(_execute_task), timeout=2400)` to run tasks. When the timeout fires, `asyncio.wait_for` cancels the `asyncio.Future` but cannot terminate the underlying Python thread. The `_loop_phase()` method runs synchronously in the thread with no cancellation check, so it continues consuming API resources.

In the FEAT-AC1A run, TASK-SFT-001's thread ran for 68 minutes after the feature was declared FAILED (Turns 4-8), consuming API credits and interleaving output.

The diagnostic diagrams identified an additional risk (**Q8**): ghost threads from Feature N interfere with Feature N+1 in multi-feature runs, corrupting shared connection pools and making debugging impossible through log interleaving.

**Cancellation checkpoint gap** (new from diagrams): The state machine shows cancellation can fire in any state, but the proposed fix must check for cancellation in both the Player and Coach phases, not just at the top of the turn loop. If cancellation fires while the Coach is mid-validation, state could be inconsistent.

## Root Cause Addressed

- **F5**: Feature orchestrator thread cannot be cancelled (`feature_orchestrator.py:1139`)
- **Q8** (new from diagrams): Ghost thread interference across features

## Implementation

### 1. Threading event in feature orchestrator

```python
# feature_orchestrator.py
import threading

async def _execute_wave_parallel(self, wave_tasks, feature, worktree):
    cancellation_events = {}

    for task in wave_tasks:
        cancel_event = threading.Event()
        cancellation_events[task["id"]] = cancel_event

        tasks_to_execute.append(
            asyncio.wait_for(
                asyncio.to_thread(
                    self._execute_task, task, feature, worktree,
                    cancellation_event=cancel_event
                ),
                timeout=self.task_timeout,
            )
        )

    try:
        parallel_results = await asyncio.gather(
            *tasks_to_execute, return_exceptions=True
        )
    finally:
        # Signal all threads to stop on timeout or exception
        for event in cancellation_events.values():
            event.set()
```

### 2. Cancellation checks in autobuild loop

```python
# autobuild.py — in _loop_phase()
for turn in range(start_turn, self.max_turns + 1):
    # Check at TOP of loop (before Player)
    if self._cancellation_event and self._cancellation_event.is_set():
        logger.info(f"Cancellation requested for {task_id} at turn {turn}")
        self._save_checkpoint(turn, "cancelled")
        return turn_history, "cancelled"

    # ... Player phase ...

    # Check BETWEEN Player and Coach (new from diagram finding)
    if self._cancellation_event and self._cancellation_event.is_set():
        logger.info(f"Cancellation during Player phase for {task_id}")
        self._save_checkpoint(turn, "cancelled_mid_turn")
        return turn_history, "cancelled"

    # ... Coach phase ...
```

### 3. Clean shutdown

When cancellation is detected:
1. Save checkpoint state (current turn, partial results)
2. Do NOT attempt worktree cleanup (leave for feature_complete)
3. Return "cancelled" as the decision for the task
4. Log the cancellation with turn number and elapsed time

## Files to Modify

1. `guardkit/orchestrator/feature_orchestrator.py` — Create `threading.Event` per task, set on timeout/exception (~line 1039)
2. `guardkit/orchestrator/autobuild.py` — Accept `cancellation_event` parameter, check at top of loop AND between Player/Coach (~line 1416)
3. `guardkit/orchestrator/autobuild.py` — Add `_save_checkpoint()` for clean shutdown
4. `guardkit/orchestrator/autobuild.py` — Handle "cancelled" as a valid `_loop_phase()` return value

## Acceptance Criteria

- [ ] `threading.Event` created per task in `_execute_wave_parallel()`
- [ ] Event set when `asyncio.wait_for` timeout fires or feature declares failure
- [ ] `_loop_phase()` checks cancellation at top of turn loop
- [ ] `_loop_phase()` checks cancellation between Player and Coach phases
- [ ] Checkpoint saved on cancellation (turn number, partial state)
- [ ] "cancelled" is a valid return value from `_loop_phase()` and handled by callers
- [ ] Ghost threads stop within one turn after cancellation event is set
- [ ] Tests cover: normal completion, cancellation at loop top, cancellation between phases

## Regression Risk

**Medium** — Touches the `_loop_phase()` main loop (most sensitive code in the system). Key risks:
1. **Early exit path**: Must ensure clean state on cancellation — no half-written files, no open connections
2. **Between-phase check**: If cancellation fires after Player succeeds but before Coach validates, the Player's work is lost. Acceptable trade-off (work can be recovered via git state on next run)
3. **Event propagation**: Must ensure the `threading.Event` is passed through the full call chain without being lost
4. **Parallel task interference**: Setting all events on one task's timeout must not cancel healthy parallel tasks. Only set the specific task's event on its timeout; set all events only on feature-level failure.

## Reference

- Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md` (Finding 5, Recommendation R6)
- Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md` (Diagram 6, Diagram 7 Q8)
