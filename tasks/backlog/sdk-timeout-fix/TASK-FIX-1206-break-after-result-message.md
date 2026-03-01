---
id: TASK-FIX-1206
title: Add break after ResultMessage in all SDK invocation paths
status: backlog
task_type: feature
parent_review: TASK-REV-A327
feature_id: FEAT-E4F5
wave: 1
implementation_mode: task-work
complexity: 2
priority: high
tags: [sdk, timeout, stream, p0, bugfix]
depends_on: []
---

# Task: Add break after ResultMessage in all SDK invocation paths

## Description

Add a `break` statement after receiving a `ResultMessage` from the Claude Agent SDK in all three invocation paths in `agent_invoker.py`. Currently, the `async for` loop continues waiting for the stream to close after `ResultMessage`, which can hang indefinitely if the CLI subprocess doesn't exit cleanly.

This was the primary root cause of TASK-SAD-002 timing out after 2340s despite completing all work in ~480s during FEAT-E4F5 run 1.

## Acceptance Criteria

- [ ] `_invoke_task_work_implement()` (line ~3975): Add `break` after `ResultMessage` logging
- [ ] `_invoke_with_role()` (line ~1753): Import `ResultMessage`, check `isinstance`, and `break`
- [ ] `_invoke_player_direct()` (line ~3050): Add `break` after `ResultMessage` if `ResultMessage` is received
- [ ] All existing tests pass (no regressions)
- [ ] Unit test: Verify that stream processing stops after `ResultMessage` is received

## Implementation Notes

- File: `guardkit/orchestrator/agent_invoker.py`
- `ResultMessage` is the SDK's terminal message — no useful data follows it
- The SDK internally uses `_first_result_event.set()` when result is received (query.py:210-211)
- Both TASK-SAD-001 (turns=27) and TASK-SAD-003 (turns=34) received `ResultMessage` as their final stream event before natural termination — confirming it is always the last message
- The `_invoke_with_role()` path currently does `pass` in the loop and doesn't import `ResultMessage`; it will need the import added
