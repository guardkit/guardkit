---
id: TASK-SPR-47f8
title: Add retry with backoff for transient LLM connection errors
status: completed
completed: 2026-03-05T13:00:00Z
task_type: implementation
created: 2026-03-05T12:00:00Z
priority: low
complexity: 3
parent_review: TASK-REV-F404
feature_id: FEAT-SPR
tags: [graphiti, vllm, resilience, retry]
wave: 3
implementation_mode: task-work
dependencies: []
---

# Task: Add retry with backoff for transient LLM connection errors

## Problem

When vLLM is restarting (e.g., after power cut), seed runs fail entirely because connection errors are treated as permanent failures. Three entire seed runs failed in init_project_9 due to this.

### Evidence

```
ERROR:httpx:Connection error: ...
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Connection error
```

All episodes in those runs were skipped (0/N for every category).

## Solution

Add a pre-seed health check that waits for vLLM to be available:

```python
async def _wait_for_llm(self, timeout: float = 60.0) -> bool:
    """Wait for LLM endpoints to be available."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            # Quick health check to chat endpoint
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.chat_url}/health", timeout=5.0)
                if resp.status_code == 200:
                    return True
        except Exception:
            pass
        await asyncio.sleep(5.0)
    return False
```

Also: `_is_transient_error()` already handles connection errors with retry. Verify the retry logic in `_create_episode()` covers connection errors (it currently retries up to 3 times with exponential backoff for transient errors).

## Files to Modify

- `guardkit/knowledge/graphiti_client.py` — Add LLM health check (optional)
- `guardkit/cli/graphiti.py` — Add pre-seed connectivity check

## Acceptance Criteria

- [x] Seed command checks LLM availability before starting
- [x] Clear message if LLM is not available: "Waiting for vLLM... (timeout 60s)"
- [x] Existing retry logic in `_create_episode()` handles connection errors
- [x] No change to circuit breaker behavior (connection errors should still count)
