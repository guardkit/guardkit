---
id: TASK-VOPT-002
title: Add per-SDK-turn timing instrumentation
status: completed
completed: 2026-03-08T00:00:00Z
updated: 2026-03-08T00:00:00Z
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-VOPT-002/
task_type: implementation
priority: medium
tags: [vllm, performance, instrumentation, timing]
complexity: 2
parent_review: TASK-REV-CB30
feature_id: FEAT-VOPT
wave: 1
implementation_mode: task-work
created: 2026-03-08T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Per-SDK-Turn Timing Instrumentation

## Problem

Current logging shows total elapsed time at 30s intervals but doesn't break down the time spent in each phase of an SDK turn. For Run 4 analysis, we need:

1. Time from SDK invocation start to first response
2. Total SDK turn duration
3. Number of SDK turns consumed within a single AutoBuild turn
4. Context loading time (Graphiti)

## Implementation

### File: `guardkit/orchestrator/agent_invoker.py`

Add timing instrumentation around the SDK invocation in `invoke_player()`:

```python
import time

# Before SDK call
turn_start = time.monotonic()

# After SDK call
turn_duration = time.monotonic() - turn_start
sdk_turns_used = result.turn_count  # from SDK response

logger.info(
    "[%s] SDK invocation complete: %.1fs, %d SDK turns (%.1fs/turn avg)",
    task_id, turn_duration, sdk_turns_used,
    turn_duration / max(sdk_turns_used, 1)
)
```

### File: `guardkit/knowledge/autobuild_context_loader.py`

Add timing around context loading:

```python
context_start = time.monotonic()
# ... existing context loading ...
context_duration = time.monotonic() - context_start
logger.info("[Graphiti] Context loaded in %.1fs", context_duration)
```

## Acceptance Criteria

- [x] AC-001: SDK invocation duration logged per AutoBuild turn
- [x] AC-002: SDK turns consumed logged per AutoBuild turn
- [x] AC-003: Average per-SDK-turn time calculated and logged
- [x] AC-004: Graphiti context load time logged
- [x] AC-005: Existing tests pass

## References

- Review: `.claude/reviews/TASK-REV-CB30-vllm-viability-review-report.md` (Objective 1)
