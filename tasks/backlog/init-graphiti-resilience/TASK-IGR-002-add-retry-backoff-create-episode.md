---
id: TASK-IGR-002
title: Add retry with exponential backoff in _create_episode()
status: backlog
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:00:00Z
priority: high
complexity: 4
tags: [graphiti, falkordb, resilience, retry]
parent_review: TASK-REV-21D3
feature_id: FEAT-IGR
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Add retry with exponential backoff in _create_episode()

## Description

Add retry logic with exponential backoff to `GraphitiClient._create_episode()` for transient FalkorDB errors ("Max pending queries exceeded", connection errors). Currently, every episode creation is a single attempt — if it fails, the episode is silently dropped.

## Context

During `guardkit init` with vLLM + FalkorDB, episode 3 of project_overview was permanently lost because FalkorDB returned "Max pending queries exceeded" and there was no retry. The error was transient — episodes 4-8 all succeeded afterwards.

The circuit breaker (threshold=3 consecutive failures) has an additional design issue: it's a one-way latch with no reset/half-open state. Once tripped, the `GraphitiClient` is permanently disabled for the process lifetime.

## Implementation

### Retry in `_create_episode()`

```python
async def _create_episode(self, name, episode_body, group_id, ...):
    if self._circuit_breaker_tripped:
        return None

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await self._graphiti.add_episode(...)
            self._record_success()
            return episode_uuid
        except Exception as e:
            is_transient = "Max pending queries" in str(e) or "Connection" in str(e)
            if is_transient and attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)  # 2s, 4s, 8s
                logger.warning(
                    f"Transient FalkorDB error (attempt {attempt+1}/{max_retries}), "
                    f"retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.warning(f"Episode creation failed: {e}")
                self._record_failure()
                return None
```

### Circuit breaker half-open state

```python
def _record_failure(self) -> None:
    self._consecutive_failures += 1
    if self._consecutive_failures >= self._max_failures:
        self._circuit_breaker_tripped = True
        self._circuit_breaker_tripped_at = time.monotonic()

def _check_circuit_breaker(self) -> bool:
    if not self._circuit_breaker_tripped:
        return False
    elapsed = time.monotonic() - self._circuit_breaker_tripped_at
    if elapsed >= 60.0:
        self._circuit_breaker_tripped = False
        self._consecutive_failures = 0
        logger.info("Circuit breaker reset (half-open)")
        return False
    return True
```

## Acceptance Criteria

- [ ] Transient FalkorDB errors trigger retry with exponential backoff (2s, 4s, 8s)
- [ ] Non-transient errors fail immediately (no retry)
- [ ] Circuit breaker resets after 60s (half-open state)
- [ ] Retry attempts are logged at WARNING level with attempt count
- [ ] Maximum 3 retries before recording failure
- [ ] Existing tests pass
- [ ] New tests for retry and circuit breaker behaviour

## Files to Modify

- `guardkit/knowledge/graphiti_client.py`
- `tests/knowledge/test_graphiti_client.py` (new tests)

## Effort Estimate

~2 hours
