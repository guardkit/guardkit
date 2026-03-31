---
id: TASK-REV-2AA0
title: Review system-plan AutoBuild output
status: backlog
created: 2026-02-09T12:00:00Z
updated: 2026-02-09T12:00:00Z
priority: high
tags: [review, autobuild, system-plan, graphiti, coroutine-bug]
task_type: review
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review system-plan AutoBuild Output

## Description

Analyse the AutoBuild output for the system-plan command captured in `docs/reviews/system_understanding/system_plan_1.md`. Two issues require investigation:

### Issue 1: Graphiti Exceptions (Validation - Positive Signal)

Graphiti is being called during the AutoBuild run but throwing exceptions. This is actually a positive signal - it validates that the Graphiti integration work from recent tasks (GCI0-GCI7, GG01-GG03) is correctly wired in. The exceptions need to be categorised:
- Are they connection/configuration errors (expected if Neo4j not running)?
- Are they code errors in the integration points?
- Do they degrade gracefully as designed?

### Issue 2: Potential Stuck/Stalled Execution

The AutoBuild run appears to have stalled - no output change for ~20 minutes. A RuntimeWarning has been observed near the end of the output:

```
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/autobuild.py:2419: RuntimeWarning: coroutine 'capture_turn_state' was never awaited
  logger.warning(f"Error capturing turn state: {e}")
```

This suggests `capture_turn_state` is an async coroutine being called without `await`, which could cause the orchestrator to hang or silently fail. This is in the error handling path, so the original error that triggered the warning may also be relevant.

## Acceptance Criteria

- [ ] Categorise all Graphiti exceptions in the output (connection vs code vs expected)
- [ ] Confirm graceful degradation is working as designed
- [ ] Identify root cause of the `capture_turn_state` coroutine not being awaited
- [ ] Determine if the unawaited coroutine is causing the stall
- [ ] Check `autobuild.py:2419` and surrounding context for the async/await bug
- [ ] Assess whether the stall detection mechanisms (from TASK-AB-SD01) should have caught this
- [ ] Provide fix recommendation for the coroutine issue

## Key Files to Investigate

- `docs/reviews/system_understanding/system_plan_1.md` - AutoBuild output log
- `guardkit/orchestrator/autobuild.py` - Line 2419 and `capture_turn_state` call sites
- `guardkit/knowledge/turn_state_operations.py` - `capture_turn_state` definition
- `guardkit/orchestrator/progress.py` - Progress display (stall detection UI)

## Context

- Related to feature: FEAT-6EDD (system-plan command)
- Graphiti integration tasks: TASK-FIX-GCI0 through GCI7, TASK-FIX-GG01 through GG03
- Stall detection: TASK-AB-SD01, TASK-FIX-CKPT, TASK-FIX-64EE

## Implementation Notes

[Space for review findings]

## Test Execution Log

[Automatically populated by /task-review]
