---
id: TASK-FIX-46F2
title: Add vLLM streaming retry on transient SDK errors
status: completed
completed: 2026-02-27T00:00:00Z
completed_location: tasks/completed/TASK-FIX-46F2/
task_type: implementation
priority: medium
tags: [autobuild, vllm, resilience, agent-invoker, p1]
complexity: 4
parent_review: TASK-REV-5610
feature_id: FEAT-FF93
wave: 2
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-27
organized_files:
  - TASK-FIX-46F2.md
---

# Task: Add vLLM Streaming Retry on Transient SDK Errors

## Description

Add a single retry with exponential backoff when the SDK encounters a transient streaming error (`SDK API error in stream: unknown`). Currently, the error immediately triggers state recovery, producing a synthetic report with `_synthetic: True` and all git-analysis promises set to `incomplete`, which results in 0/N Coach verification and a full re-implementation on the next turn.

A single retry would likely succeed (the error is transient under GPU load) without the expensive state-recovery → re-implementation path.

## Root Cause

In autobuild run 2, TASK-DB-006 Turn 1 hit `SDK API error in stream: unknown` at ~5,430s. This was a transient vLLM SSE stream interruption caused by 3 concurrent tasks competing for a single GPU. The state recovery path captured partial work but the synthetic report produced 0/6, triggering a full 93-turn re-implementation on Turn 2 (~9,210s), which then timed out before Coach could validate.

## Implementation

In the SDK invocation code path in `agent_invoker.py`, wrap the streaming call with retry logic:

```python
MAX_SDK_RETRIES = 1
SDK_RETRY_BACKOFF = 30  # seconds

for attempt in range(MAX_SDK_RETRIES + 1):
    try:
        result = await sdk_stream_call(...)
        break  # Success
    except SDKStreamError as e:
        if attempt < MAX_SDK_RETRIES and "unknown" in str(e):
            logger.warning(
                "[%s] SDK stream error (attempt %d/%d), retrying in %ds: %s",
                task_id, attempt + 1, MAX_SDK_RETRIES + 1, SDK_RETRY_BACKOFF, e,
            )
            await asyncio.sleep(SDK_RETRY_BACKOFF)
        else:
            raise  # Fall through to existing state recovery
```

**Important**: Only retry on transient errors (`unknown`). Do not retry on authentication, rate limit, or model errors. Fall through to existing state recovery on second failure — preserve the current architecture.

## Acceptance Criteria

- [x] Single retry with 30s backoff on `SDK API error in stream: unknown`
- [x] Only retries transient errors (not auth, rate limit, or model errors)
- [x] Falls through to existing state recovery on second failure
- [x] Retry attempt logged at WARNING level with task ID and attempt count
- [x] Existing state recovery path is NOT modified
- [x] Existing tests pass

## Files Modified

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py` | Added `MAX_SDK_STREAM_RETRIES`, `SDK_STREAM_RETRY_BACKOFF` constants; wrapped stream processing in retry loop |
| `tests/unit/test_agent_invoker_streaming_retry.py` | New test file: 10 tests for retry constants, decision logic, and pattern matching |

## Risk Assessment

**Risk**: Low
- Single retry only, with 30s backoff (not aggressive)
- Falls through to existing proven state recovery on failure
- No changes to state recovery, synthetic reports, or Coach validation
- Only triggers on specific transient error pattern
