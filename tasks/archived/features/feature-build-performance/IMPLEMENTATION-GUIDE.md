# Implementation Guide: Feature Build Performance Quick Wins

## Wave Breakdown

### Wave 1: Core Implementations (Parallel)

Both tasks can be implemented in parallel as they modify different files.

| Task | File | Description |
|------|------|-------------|
| TASK-FBP-001 | `feature_orchestrator.py` | Wave parallelization |
| TASK-FBP-002 | `agent_invoker.py` | Progress heartbeat |

**Conductor Workspace Names**:
- `feature-build-performance-wave1-parallelization`
- `feature-build-performance-wave1-heartbeat`

### Wave 2: Testing (Sequential)

| Task | File | Description |
|------|------|-------------|
| TASK-FBP-003 | `tests/integration/` | Integration tests |

## Technical Approach

### TASK-FBP-001: Wave Parallelization

**Current Code** (`feature_orchestrator.py`):
```python
# Serial execution
for task_id in wave:
    result = await self._execute_task(task_id)
    if not result.success and self.stop_on_failure:
        break
```

**Target Code**:
```python
# Parallel execution
import asyncio

async def _execute_wave(self, wave: List[str]) -> List[OrchestrationResult]:
    """Execute all tasks in a wave concurrently."""
    tasks = [self._execute_task(task_id) for task_id in wave]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed.append(OrchestrationResult(
                task_id=wave[i],
                success=False,
                error=str(result),
                ...
            ))
        else:
            processed.append(result)

    return processed
```

### TASK-FBP-002: Progress Heartbeat

**Location**: `agent_invoker.py`

**Approach**:
```python
async def _invoke_with_heartbeat(self, task_id: str, *args, **kwargs):
    """Invoke SDK with periodic progress logging."""
    async def heartbeat():
        elapsed = 0
        while True:
            await asyncio.sleep(30)
            elapsed += 30
            logger.info(f"[{task_id}] SDK invocation in progress... ({elapsed}s elapsed)")

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        result = await self._invoke_with_role(*args, **kwargs)
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    return result
```

## Risk Mitigation

### Wave Parallelization Risks

| Risk | Mitigation |
|------|------------|
| Task interference in shared worktree | Tasks in same wave have no dependencies by definition |
| Resource contention | SDK subprocesses are independent |
| Error propagation | Wrap in try/except, collect all results |

### Progress Heartbeat Risks

| Risk | Mitigation |
|------|------------|
| Log spam | 30-second interval balances visibility vs noise |
| Task cancellation | Proper cleanup in finally block |

## Testing Strategy

### Unit Tests

1. `test_wave_parallel_execution` - Verify tasks run concurrently
2. `test_wave_error_handling` - Verify errors don't crash other tasks
3. `test_heartbeat_logging` - Verify heartbeat fires at intervals
4. `test_heartbeat_cleanup` - Verify proper cancellation

### Integration Tests

1. `test_feature_build_wave_timing` - Verify wave completes faster than serial
2. `test_feature_build_with_failure` - Verify stop_on_failure works with parallel

## Execution Commands

```bash
# Wave 1 (parallel with Conductor)
conductor spawn feature-build-performance-wave1-parallelization
conductor spawn feature-build-performance-wave1-heartbeat

# Wave 2 (after Wave 1 completes)
/task-work TASK-FBP-003
```
