---
id: TASK-CEF-002
title: Add CancelledError handling at 5 guard points in invocation chain
status: completed
completed: 2026-03-07T15:30:00Z
updated: 2026-03-07T15:30:00Z
previous_state: in_review
state_transition_reason: "Task completed - all quality gates passed"
completed_location: tasks/completed/TASK-CEF-002/
task_type: implementation
created: 2026-03-07T14:00:00Z
priority: critical
tags: [bug-fix, asyncio, python-3.9-compat, cancelled-error, defense-in-depth]
complexity: 4
parent_review: TASK-REV-C3F8
feature_id: FEAT-CEF1
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Add CancelledError handling at 5 guard points in invocation chain

## Description

Add `CancelledError` handling at all 5 `except Exception` guard points through which a `CancelledError` can escape from the worker thread's event loop to the `gather` results. On Python 3.9+, `CancelledError` is a `BaseException` (not `Exception`), so all existing `except Exception` handlers miss it. This is the defense-in-depth fix that prevents the error from ever reaching the result processing code.

## Requirements

1. Guard Point 1 — `agent_invoker.py:1933` (`_invoke_with_role`): Widen `except Exception` to also catch `asyncio.CancelledError`
2. Guard Point 2 — `agent_invoker.py:1279` (`invoke_player`): Widen `except Exception` to also catch `asyncio.CancelledError`
3. Guard Point 3 — `autobuild.py:3811` (`_invoke_player_safely`): Add `asyncio.CancelledError` to `UNRECOVERABLE_ERRORS` tuple OR add explicit handler before `except Exception`
4. Guard Point 4 — `autobuild.py:3823` (`_invoke_player_safely`): Widen `except Exception` to also catch `asyncio.CancelledError`
5. Guard Point 5 — `feature_orchestrator.py:1894` (`_execute_task`): Widen `except Exception` to also catch `asyncio.CancelledError`, set `final_decision="cancelled"`

## Affected Files

- `guardkit/orchestrator/agent_invoker.py` — lines 1279, 1933
- `guardkit/orchestrator/autobuild.py` — lines 3811, 3823 (and UNRECOVERABLE_ERRORS at line 199)
- `guardkit/orchestrator/feature_orchestrator.py` — line 1894

## Acceptance Criteria

- [ ] AC-1: Guard Point 1 catches `CancelledError` and logs it with `logger.warning`
- [ ] AC-2: Guard Point 2 catches `CancelledError` and returns `AgentInvocationResult(success=False, error="Cancelled: ...")`
- [ ] AC-3: Guard Point 3 catches `CancelledError` — either via UNRECOVERABLE_ERRORS or explicit handler
- [ ] AC-4: Guard Point 4 catches `CancelledError` and returns `AgentInvocationResult(success=False, error="Cancelled: ...")`
- [ ] AC-5: Guard Point 5 catches `CancelledError` and returns `TaskExecutionResult(final_decision="cancelled")`
- [ ] AC-6: All existing `Exception` handling preserved (no behavior change for non-CancelledError exceptions)
- [ ] AC-7: Unit tests verify CancelledError is caught at each guard point
- [ ] AC-8: Logging at each guard point includes the guard point location for diagnostics

## Implementation Hints

### Pattern for each guard point

```python
# Change from:
except Exception as e:
    # ... existing handling ...

# To:
except (Exception, asyncio.CancelledError) as e:
    if isinstance(e, asyncio.CancelledError):
        logger.warning(f"CancelledError caught at {guard_point_name}: {e}")
    # ... existing handling with decision="cancelled" for CancelledError ...
```

### Guard Point 5 — feature_orchestrator.py:1894

```python
except (Exception, asyncio.CancelledError) as e:
    decision = "cancelled" if isinstance(e, asyncio.CancelledError) else "error"
    console.print(f"    [red]✗[/red] {task.id}: {decision.upper()} - {e}")
    return TaskExecutionResult(
        task_id=task.id,
        success=False,
        total_turns=0,
        final_decision=decision,
        error=str(e),
    )
```

### UNRECOVERABLE_ERRORS option (autobuild.py:199)

```python
# Option A: Add to tuple
UNRECOVERABLE_ERRORS = (
    PlanNotFoundError,
    StateValidationError,
    RateLimitExceededError,
    asyncio.CancelledError,  # Python 3.9+: BaseException, not Exception
)

# Option B: Explicit handler before except Exception (preferred — different behavior)
except asyncio.CancelledError as e:
    logger.warning(f"CancelledError in _invoke_player_safely for {task_id}: {e}")
    return AgentInvocationResult(
        task_id=task_id, turn=turn, agent_type="player",
        success=False, report={}, duration_seconds=0.0,
        error=f"Cancelled: {str(e)}",
    )
except UNRECOVERABLE_ERRORS as e:
    # ... existing ...
except Exception as e:
    # ... existing ...
```
