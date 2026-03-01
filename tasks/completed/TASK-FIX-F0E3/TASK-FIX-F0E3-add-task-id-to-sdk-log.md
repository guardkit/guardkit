---
id: TASK-FIX-F0E3
title: Add task_id to SDK completion log message
status: completed
completed: '2026-03-01T23:00:00Z'
task_type: feature
parent_review: TASK-REV-A327
feature_id: FEAT-E4F5
wave: 3
implementation_mode: direct
complexity: 1
priority: low
tags: [logging, diagnostic, p3]
depends_on: []
---

# Task: Add task_id to SDK completion log message

## Description

Add the `task_id` prefix to the `SDK completed: turns=N` log message in `_invoke_task_work_implement()`. Currently this log line lacks the task identifier, making attribution in parallel execution logs ambiguous (requires timestamp analysis to determine which task produced the message).

## Acceptance Criteria

- [x] Log message format changed from `SDK completed: turns=N` to `[{task_id}] SDK completed: turns=N`
- [x] All existing tests pass

## Implementation Notes

- File: `guardkit/orchestrator/agent_invoker.py`, line 3975
- Current: `logger.info(f"SDK completed: turns={message.num_turns}")`
- Change to: `logger.info(f"[{task_id}] SDK completed: turns={message.num_turns}")`
- The `task_id` variable is already in scope at this line
