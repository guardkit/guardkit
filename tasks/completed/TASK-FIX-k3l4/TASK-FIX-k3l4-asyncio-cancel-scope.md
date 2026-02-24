---
id: TASK-FIX-k3l4
title: Suppress asyncio cancel scope noise from SDK generator cleanup
status: completed
task_type: implementation
created: 2026-02-23T00:00:00Z
updated: 2026-02-24T00:00:00Z
completed: 2026-02-24T00:00:00Z
completed_location: tasks/completed/TASK-FIX-k3l4/
priority: low
tags: [autobuild, asyncio, anyio, sdk, noise, agent-invoker]
complexity: 2
parent_review: TASK-REV-ED10
feature_id: FEAT-7a2e
wave: 3
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  total: 402
  passed: 402
  failed: 0
  coverage: null
---

# Task: Suppress asyncio cancel scope noise from SDK generator cleanup

## Problem Statement

At the start of autobuild turns 2, 3, … a pair of non-fatal background asyncio task exceptions
appear in the log:

```
ERROR:asyncio:Task exception was never retrieved
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

These originate from the previous turn's `query()` async generator being closed (Python's
async generator finalizer schedules cleanup as a new asyncio task). AnyIO's cancel scope then
tries to exit in the new task, which it was not entered in — a known upstream AnyIO/SDK issue.

The errors are cosmetic noise that makes logs harder to read and may cause operators to
investigate a non-issue. They are not vLLM-specific and appear on any host with this SDK version.

## Acceptance Criteria

- [x] Check if a newer `claude-agent-sdk` version resolves the cancel scope error; update
      `pyproject.toml` if a fix is available — no upstream fix available; suppression implemented
- [x] If no upstream fix is available: suppress `RuntimeError("Attempted to exit cancel scope in
      a different task than it was entered in")` at the asyncio exception handler level in
      `agent_invoker.py`
- [x] `ProcessError: Command failed with exit code 1` from the subprocess cleanup is also
      suppressed (it is the corollary of the cancel scope error)
- [x] Suppression is targeted: only these specific error messages are suppressed; all other
      asyncio background task errors are still logged
- [x] Existing tests pass; no functional behaviour changes

## Implementation Notes

### Check for upstream fix first

```bash
pip index versions claude-agent-sdk
# or
pip install --upgrade claude-agent-sdk
# Verify the cancel scope error no longer appears in turn 2+ logs
```

### If no upstream fix: targeted suppression in agent_invoker.py

Python's asyncio exception handler can be customised:

```python
import asyncio

_SUPPRESS_PATTERNS = [
    "Attempted to exit cancel scope in a different task",
    "Command failed with exit code 1",  # from SDK subprocess on generator close
]

def _asyncio_exception_handler(loop, context):
    msg = context.get("message", "")
    exc = context.get("exception")
    exc_msg = str(exc) if exc else ""
    if any(p in msg or p in exc_msg for p in _SUPPRESS_PATTERNS):
        return  # suppress known SDK generator cleanup noise
    loop.default_exception_handler(context)

# In AgentInvoker.__init__ or the async runner setup:
loop = asyncio.get_event_loop()
loop.set_exception_handler(_asyncio_exception_handler)
```

Be careful to only install this handler for the autobuild invocation scope (not globally for
the entire process if other components rely on asyncio error reporting).

## Files to Modify

- `pyproject.toml` — update `claude-agent-sdk` version if upstream fix available
- `guardkit/orchestrator/agent_invoker.py` — targeted asyncio exception handler (if needed)
