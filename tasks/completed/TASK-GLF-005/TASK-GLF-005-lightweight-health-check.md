---
id: TASK-GLF-005
title: Implement lightweight health check without full client initialization
task_type: refactor
parent_review: TASK-REV-50E1
feature_id: FEAT-408A
wave: 3
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-GLF-003
status: completed
completed: 2026-02-16T12:00:00Z
completed_location: tasks/completed/TASK-GLF-005/
priority: low
tags: [graphiti, falkordb, health-check, feature-orchestrator]
updated: 2026-02-16T12:00:00Z
previous_state: in_review
state_transition_reason: "All quality gates passed, code review approved, completion validated"
---

# Task: Implement lightweight health check without full client initialization

## Description

`_preflight_check()` runs a health check on a fully initialized Graphiti client, which creates a temporary event loop and contributes to the loop contamination problem. After TASK-GLF-003 implements lazy initialization, the health check should be updated to use a lightweight connectivity test that doesn't trigger full client initialization.

## Root Cause (from TASK-REV-50E1 Finding 1b)

**File**: `guardkit/orchestrator/feature_orchestrator.py`, lines 930-1001

```python
loop = asyncio.new_event_loop()
try:
    healthy = loop.run_until_complete(
        asyncio.wait_for(client._check_health(), timeout=5.0)
    )
finally:
    loop.close()
```

The `_check_health()` method (graphiti_client.py:465-487) runs `self._graphiti.search("health_check_test")` which requires a fully initialized FalkorDB driver with Lock objects. These Locks then become bound to the health check's temporary loop.

## Acceptance Criteria

- [x] AC-001: Health check uses a lightweight connectivity test (TCP/Redis ping) instead of `_check_health()`
- [x] AC-002: Health check does NOT trigger `build_indices_and_constraints()` or create FalkorDB Lock objects
- [x] AC-003: Health check correctly detects FalkorDB availability (True when up, False when down)
- [x] AC-004: Health check correctly detects FalkorDB unavailability without hanging
- [x] AC-005: Full client initialization is deferred to first wave (per TASK-GLF-003 lazy init)
- [x] AC-006: Test verifies health check works without full client initialization

## Implementation Approach

Split health check into two phases:

```python
# Phase 1 (preflight): Lightweight ping
async def _check_connectivity(self) -> bool:
    """Test FalkorDB connectivity without full driver init."""
    try:
        # Simple Redis PING or TCP connection test
        import redis
        r = redis.Redis(host=self.config.host, port=self.config.port)
        return r.ping()
    except Exception:
        return False

# Phase 2 (first wave): Full initialization via lazy init (TASK-GLF-003)
```

Alternative: If FalkorDB driver supports a lightweight `ping()` method, use that instead of raw Redis.

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/feature_orchestrator.py` | Replace `_check_health()` with lightweight ping in `_preflight_check()` |
| `guardkit/knowledge/graphiti_client.py` | Add `check_connectivity()` method (lightweight, no Lock creation) |

## Test Scope

`tests/**/test_*preflight*` or `tests/**/test_*health_check*`

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Lightweight ping passes but full init fails | FalkorDB init failure handled by lazy init graceful degradation (GLF-003) |
| Redis library not available | Use socket-level TCP check as fallback |
| Health check timing changes | Keep 5s timeout on lightweight check |
