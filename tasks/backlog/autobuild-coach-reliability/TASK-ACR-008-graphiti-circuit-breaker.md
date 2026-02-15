---
id: TASK-ACR-008
title: "Add Graphiti connection health check and circuit breaker"
status: backlog
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T10:00:00Z
priority: high
task_type: feature
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 3
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-ACR-006
  - TASK-ACR-007
tags: [autobuild, graphiti, circuit-breaker, resilience, f3-fix]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add Graphiti connection health check and circuit breaker

## Description

Implement a circuit breaker pattern in the GraphitiClient to prevent 43+ connection retry failures when FalkorDB connections degrade. After N consecutive failures, disable the client for the remainder of the run.

## Files to Modify

- `guardkit/knowledge/graphiti_client.py` — add health check method, circuit breaker state, `is_healthy` property

## Acceptance Criteria

- [ ] AC-001: Lightweight health check before each Graphiti operation (e.g., `RETURN 1` Cypher query)
- [ ] AC-002: Track consecutive failures per client instance
- [ ] AC-003: After 3 consecutive failures, trip the circuit breaker
- [ ] AC-004: When tripped, log clearly: "Graphiti disabled after N consecutive failures -- continuing without knowledge graph context"
- [ ] AC-005: Expose `is_healthy` property for callers to check before attempting operations
- [ ] AC-006: Successful operations reset the failure counter
- [ ] AC-007: All existing Graphiti operations (search, add_episode, etc.) respect circuit breaker state
- [ ] AC-008: Unit tests verify: healthy -> degraded -> tripped -> operations return empty, reset after recovery

## Implementation Notes

```python
class GraphitiClient:
    def __init__(self, config):
        self._consecutive_failures = 0
        self._circuit_breaker_tripped = False
        self._max_failures = 3

    @property
    def is_healthy(self) -> bool:
        return self.enabled and not self._circuit_breaker_tripped

    async def _health_check(self) -> bool:
        try:
            # Lightweight check
            await self._driver.execute_query("RETURN 1")
            self._consecutive_failures = 0
            return True
        except Exception:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_failures:
                self._circuit_breaker_tripped = True
                logger.warning("Graphiti disabled after %d consecutive failures", self._consecutive_failures)
            return False
```
