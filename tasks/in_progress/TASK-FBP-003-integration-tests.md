---
id: TASK-FBP-003
title: Add integration tests for parallel wave execution
status: in_progress
created: 2025-01-15T12:00:00Z
updated: 2025-01-15T14:30:00Z
priority: medium
tags: [feature-build, testing, integration-tests]
parent_task: TASK-REV-FB14
implementation_mode: task-work
wave: 2
complexity: 3
depends_on:
  - TASK-FBP-001
  - TASK-FBP-002
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
---

# Task: Add Integration Tests for Parallel Wave Execution

## Description

Create integration tests to verify the parallel wave execution and progress heartbeat implementations work correctly end-to-end.

## Context

After implementing TASK-FBP-001 (wave parallelization) and TASK-FBP-002 (progress heartbeat), we need integration tests to verify:
1. Waves actually execute faster than serial
2. Error handling works correctly across parallel tasks
3. Progress heartbeat fires during real SDK invocations

## Acceptance Criteria

- [ ] Integration test verifies wave timing is faster than serial baseline
- [ ] Integration test verifies error isolation (one task failure doesn't block others)
- [ ] Integration test verifies stop_on_failure behavior with parallel waves
- [ ] Integration test verifies heartbeat logs appear during execution
- [ ] Tests use mock SDK to avoid actual API calls
- [ ] Tests run in CI pipeline

## Implementation Notes

### Target File
`tests/integration/test_parallel_wave_execution.py`

### Test Cases

```python
@pytest.mark.asyncio
async def test_wave_executes_in_parallel():
    """Verify wave tasks run concurrently, not serially."""
    # Create 3 mock tasks that each take 1 second
    # Verify total time is ~1 second, not ~3 seconds
    pass

@pytest.mark.asyncio
async def test_wave_error_isolation():
    """Verify one task failure doesn't prevent others from completing."""
    # Create 3 tasks, middle one fails
    # Verify first and third tasks complete successfully
    pass

@pytest.mark.asyncio
async def test_stop_on_failure_waits_for_wave():
    """Verify stop_on_failure doesn't abort mid-wave."""
    # Create wave with failing task
    # Verify all wave tasks complete before stopping
    pass

@pytest.mark.asyncio
async def test_heartbeat_during_sdk_invocation():
    """Verify heartbeat logs appear during long operations."""
    # Mock SDK invocation that takes 60+ seconds
    # Verify heartbeat messages at 30s intervals
    pass
```

### Mock Strategy

Use `unittest.mock.AsyncMock` to mock SDK invocations:

```python
@pytest.fixture
def mock_sdk():
    with patch('guardkit.orchestrator.agent_invoker.AgentInvoker._invoke_task_work_implement') as mock:
        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(1)  # Simulate SDK call
            return TaskWorkResult(success=True, ...)
        mock.side_effect = slow_invoke
        yield mock
```

## Notes

Task transitioned to in_progress for task-work execution.
