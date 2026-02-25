---
id: TASK-FIX-ASPF-004
title: Cancel SDK subprocess on feature timeout
status: completed
task_type: implementation
created: 2026-02-24T23:00:00Z
completed: 2026-02-25T00:00:00Z
priority: high
tags: [feature-orchestrator, cancellation, sdk, timeout]
complexity: 5
parent_review: TASK-REV-953F
feature_id: FEAT-ASPF
wave: 2
implementation_mode: task-work
dependencies: [TASK-FIX-ASPF-001]
completed_location: tasks/completed/TASK-FIX-ASPF-004/
organized_files:
  - TASK-FIX-ASPF-004.md
  - completion-report.md
---

# Task: Cancel SDK subprocess on feature timeout

## Description

When a feature-level timeout fires (2400s), the `asyncio.wait_for` only cancels the asyncio wrapper. The underlying OS thread (via `asyncio.to_thread`) and its SDK subprocess continue running. In Run 2, the Player continued for 690s after timeout, wasting GPU resources.

## Current Architecture

1. `feature_orchestrator.py:1277` wraps task in `asyncio.wait_for(..., timeout=task_timeout)`
2. Timeout fires → `asyncio.TimeoutError` raised
3. `feature_orchestrator.py:1295` sets `cancel_event.set()` in finally block
4. `autobuild.py` checks `_cancellation_event.is_set()` at 3 cooperative checkpoints
5. **Gap**: If SDK subprocess is running, thread is blocked and can't check the event

## Required Fix

The `AgentInvoker` needs a `cancel()` method that terminates the current SDK subprocess. Options:

1. **SIGTERM to subprocess**: Find the Claude Code process PID and send SIGTERM
2. **SDK cancellation API**: Check if `claude_agent_sdk` provides a cancellation mechanism
3. **Process group kill**: If the SDK spawns child processes, kill the entire process group

The `feature_orchestrator.py` timeout handler should call this cancel method in addition to setting the cancellation event.

## Acceptance Criteria

1. SDK subprocess terminates within 30s of feature timeout
2. No orphan processes left after cancellation
3. State recovery still works after forced cancellation
4. Existing timeout tests still pass
5. New test: verify subprocess termination on timeout

## Files to Investigate

- `guardkit/orchestrator/feature_orchestrator.py` — timeout handling (~line 1271-1296)
- `guardkit/orchestrator/agent_invoker.py` — `_invoke_with_role()` SDK subprocess management
- Claude Agent SDK source — cancellation API

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` — add `cancel()` method
- `guardkit/orchestrator/feature_orchestrator.py` — call cancel on timeout
- `guardkit/orchestrator/autobuild.py` — expose agent_invoker reference if needed
