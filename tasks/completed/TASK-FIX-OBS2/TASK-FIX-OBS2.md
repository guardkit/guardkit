---
id: TASK-FIX-OBS2
title: Add per-task progress logs for parallel execution diagnostics
status: completed
created: 2026-03-20T23:30:00Z
updated: 2026-03-20T23:30:00Z
completed: 2026-03-20T23:45:00Z
completed_location: tasks/completed/TASK-FIX-OBS2/
previous_state: in_review
state_transition_reason: "All acceptance criteria met, all tests passing"
priority: high
tags: [autobuild, observability, parallel, timeout, diagnostics, P1]
parent_review: TASK-REV-8BC0
feature_id: FEAT-8BC0
implementation_mode: task-work
wave: 1
complexity: 5
---

# Task: Add Per-Task Progress Logs for Parallel Execution Diagnostics

## Description

When TASK-DC-002 timed out after 2400s in the FEAT-5606 run, there were zero diagnostic logs between start and timeout. This makes root cause analysis impossible for parallel task failures.

The issue arises because parallel tasks run in separate worker threads via `asyncio.to_thread()`, and their logs are interleaved in the main output stream. When one task produces verbose output (like DC-003), the other task's logs may be lost or buried.

## Acceptance Criteria

- [x] Each parallel task writes a dedicated log file at `.guardkit/autobuild/{task_id}/progress.log`
- [x] Progress snapshots are written every 60 seconds during SDK invocation, including: elapsed time, last tool use observed, files changed so far, current phase
- [x] When a task times out via `asyncio.wait_for`, the feature orchestrator captures and logs the worker thread's last known state before cleanup
- [x] Existing console output behaviour is unchanged (progress logs are in addition to, not replacing, console output)
- [x] Add a `--task-log-interval` flag to feature orchestrator (default: 60s)

## Key Files

- `guardkit/orchestrator/feature_orchestrator.py` (parallel execution, timeout handling)
- `guardkit/orchestrator/agent_invoker.py` (heartbeat logging during SDK invocation)
- `guardkit/orchestrator/autobuild.py` (turn execution)

## Notes

This is critical for diagnosing parallel execution failures. Without per-task logs, timed-out tasks are black boxes.
