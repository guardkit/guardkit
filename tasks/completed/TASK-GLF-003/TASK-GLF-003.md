---
id: TASK-GLF-003
title: Implement lazy Graphiti client initialization in consumer's loop
task_type: refactor
parent_review: TASK-REV-50E1
feature_id: FEAT-408A
wave: 2
implementation_mode: task-work
complexity: 6
dependencies:
  - TASK-GLF-001
  - TASK-GLF-002
status: completed
completed: 2026-02-16T00:00:00Z
updated: 2026-02-16T00:00:00Z
previous_state: in_review
state_transition_reason: "Task completed via /task-complete"
completed_location: tasks/completed/TASK-GLF-003/
priority: high
tags: [graphiti, falkordb, asyncio, event-loop, lifecycle]
---

# Task: Implement lazy Graphiti client initialization in consumer's loop

## Description

`GraphitiClientFactory.get_thread_client()` creates a temporary event loop for `client.initialize()`, then closes it. The FalkorDB driver's internal `asyncio.Lock` objects remain bound to this dead loop, causing "Lock bound to different event loop" errors when the client is subsequently used on a different loop.

This is the **root cause** of all Lock affinity errors (~26 of ~53 total errors in Run 4).

## Root Cause (from TASK-REV-50E1 Finding 1a)

**File**: `guardkit/knowledge/graphiti_client.py`, lines 1627-1632

```python
loop = asyncio.new_event_loop()
try:
    success = loop.run_until_complete(coro)  # client.initialize() → builds FalkorDB Locks
finally:
    loop.close()  # Loop dies, Locks orphaned
if success:
    self._thread_local.client = client  # Client persists with dead-loop Locks
```

The event loop chain across the system:
1. `get_thread_client()` → loop_B (created, init, CLOSED — Locks bound here)
2. `asyncio.run(wave_N)` → loop_C (created, tasks run on this loop)
3. Worker threads use loop_D — Locks from loop_B fail on loop_D

## Acceptance Criteria

- [x] AC-001: `get_thread_client()` returns client WITHOUT creating a temporary event loop for initialization
- [x] AC-002: Client has an `is_initialized` property that tracks initialization state
- [x] AC-003: Initialization happens lazily within the consumer's active event loop (via `_get_thread_local_loader` or first use)
- [x] AC-004: All FalkorDB Lock objects are created on the loop that will use them
- [ ] AC-005: Zero "Lock bound to different event loop" errors in AutoBuild run (requires E2E validation)
- [ ] AC-006: Zero "Event loop is closed" errors during mid-run operations (requires E2E validation)
- [x] AC-007: Graphiti still works correctly when FalkorDB is available
- [x] AC-008: Graceful degradation when FalkorDB is unavailable (no crash, context disabled)
- [x] AC-009: Tests verify Lock affinity is maintained across loop transitions

## Implementation Approach

### Option A: Lazy init (RECOMMENDED)

```python
# In get_thread_client(): Don't create a loop, return uninitialized client
def get_thread_client(self) -> Optional[GraphitiClient]:
    if hasattr(self._thread_local, 'client') and self._thread_local.client:
        return self._thread_local.client
    client = GraphitiClient(config=self.config)
    client._pending_init = True  # Mark as needing init
    self._thread_local.client = client
    return client

# In consumer code (_get_thread_local_loader):
async def _ensure_initialized(self, client):
    if getattr(client, '_pending_init', False):
        await client.initialize()
        client._pending_init = False
```

### Callers to Update

- `_get_thread_local_loader()` in `autobuild.py` (line 3114) — initialize client within the thread's loop
- `_preflight_check()` in `feature_orchestrator.py` (line 930) — health check must handle uninitialized client

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/knowledge/graphiti_client.py` | Remove temp loop from `get_thread_client()`, add `is_initialized` / `_pending_init` |
| `guardkit/orchestrator/autobuild.py` | Update `_get_thread_local_loader` to await initialization |
| `guardkit/orchestrator/feature_orchestrator.py` | Update `_preflight_check` to handle lazy init |

## Test Scope

`tests/**/test_*graphiti*client*` or `tests/**/test_*graphiti*factory*`

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Lazy init changes timing of FalkorDB connection | Verify first wave tasks still get context correctly |
| Health check needs an initialized client | Add lightweight TCP ping before full init |
| Thread-local storage interaction | Keep existing `threading.local()` pattern, just defer init timing |
