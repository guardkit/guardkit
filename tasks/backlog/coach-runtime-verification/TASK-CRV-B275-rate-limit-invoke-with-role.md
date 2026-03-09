---
id: TASK-CRV-B275
title: Add rate limit detection to _invoke_with_role()
status: backlog
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
priority: low
tags: [rate-limit, agent-invoker, reliability]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 3
implementation_mode: direct
complexity: 1
dependencies: []
---

# Task: Add rate limit detection to _invoke_with_role()

## Description

Rate limit detection (`detect_rate_limit()`) exists in `_invoke_task_work_implement()` but is missing from `_invoke_with_role()`. This means Coach invocations won't get structured `RateLimitExceededError` with reset time information.

Apply the same rate limit detection pattern from the task-work path.

## Acceptance Criteria

- [ ] `detect_rate_limit()` called in `_invoke_with_role()` exception handler
- [ ] `RateLimitExceededError` raised with reset_time when rate limit detected
- [ ] Pattern matches existing implementation in `_invoke_task_work_implement()`
- [ ] Existing tests continue to pass

## Implementation Notes

In `agent_invoker.py` `_invoke_with_role()` exception handler (~line 1991):

```python
# Current:
except Exception as e:
    raise AgentInvocationError(f"SDK invocation failed for {agent_type}: {str(e)}") from e

# Proposed:
except Exception as e:
    is_rate_limit, reset_time = detect_rate_limit(str(e))
    if is_rate_limit:
        raise RateLimitExceededError(
            f"API rate limit exceeded. Reset: {reset_time or 'unknown'}"
        ) from e
    raise AgentInvocationError(f"SDK invocation failed for {agent_type}: {str(e)}") from e
```

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` (`_invoke_with_role()` exception handler)
