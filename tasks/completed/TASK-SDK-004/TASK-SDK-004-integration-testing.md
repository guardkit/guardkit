---
id: TASK-SDK-004
title: Integration testing for SDK delegation
status: completed
task_type: implementation
created: 2026-01-10T11:00:00Z
updated: 2026-01-10T15:00:00Z
completed: 2026-01-10T15:00:00Z
priority: high
tags: [sdk-delegation, integration-testing, feature-build, e2e]
complexity: 5
wave: 3
parent_feature: sdk-delegation-fix
depends_on:
  - TASK-SDK-001
  - TASK-SDK-002
  - TASK-SDK-003
---

# Integration testing for SDK delegation

## Description

Create integration tests that verify the complete SDK delegation flow works end-to-end, from Player invocation through task-work execution to Coach validation of results.

## Test Scenarios

### Scenario 1: Happy Path

```python
@pytest.mark.integration
async def test_sdk_delegation_happy_path():
    """Test complete SDK delegation flow with successful implementation."""
    # Setup
    task_id = "TASK-TEST-001"
    worktree = create_test_worktree(task_id)

    # Execute
    invoker = AgentInvoker(worktree_path=worktree, use_task_work_delegation=True)
    result = await invoker.invoke_player(task_id, mode="tdd")

    # Verify
    assert result.success
    results_file = worktree / ".guardkit" / "autobuild" / task_id / "task_work_results.json"
    assert results_file.exists()

    results = json.loads(results_file.read_text())
    assert results["completed"]
    assert results["quality_gates"]["tests_passing"]
```

### Scenario 2: Coach Validation

```python
@pytest.mark.integration
async def test_coach_can_read_sdk_delegation_results():
    """Test that Coach can read and validate SDK delegation results."""
    # Setup with pre-written results
    task_id = "TASK-TEST-002"
    worktree = create_test_worktree(task_id)
    write_mock_task_work_results(worktree, task_id, passing=True)

    # Execute Coach validation
    coach = CoachValidator(worktree_path=worktree)
    validation = await coach.validate(task_id)

    # Verify
    assert validation.can_read_results
    assert validation.quality_gates_passed
```

### Scenario 3: Timeout Handling

```python
@pytest.mark.integration
async def test_sdk_delegation_timeout():
    """Test timeout handling for slow task-work execution."""
    invoker = AgentInvoker(
        worktree_path=worktree,
        use_task_work_delegation=True,
        sdk_timeout_seconds=5  # Very short for testing
    )

    with pytest.raises(asyncio.TimeoutError):
        await invoker.invoke_player("TASK-SLOW", mode="tdd")
```

### Scenario 4: Stream Parsing

```python
@pytest.mark.integration
async def test_stream_parser_extracts_quality_gates():
    """Test that stream parser correctly extracts quality gate info."""
    # Mock SDK stream with realistic output
    mock_stream = [
        "Phase 3: Implementation starting...",
        "Created: src/feature.py",
        "Phase 4: Running tests...",
        "12 tests passed, 0 tests failed",
        "Coverage: 87.5%",
        "Phase 5: Code review...",
        "Quality gates: PASSED"
    ]

    parser = StreamParser()
    result = {}
    for message in mock_stream:
        result = parser.parse(message, result)

    assert result["tests_passed"] == 12
    assert result["coverage"] == 87.5
    assert result["quality_gates_passed"]
```

## Acceptance Criteria

- [x] Happy path test passes
- [x] Coach validation test passes
- [x] Timeout handling test passes
- [x] Stream parsing test passes
- [x] Tests run in CI/CD (pytest markers)
- [x] No flaky tests
- [x] Cleanup of test worktrees
- [x] Documentation of test fixtures

## Test Infrastructure

```python
# tests/integration/conftest.py

@pytest.fixture
def test_worktree(tmp_path):
    """Create temporary worktree for testing."""
    worktree = tmp_path / "test-worktree"
    worktree.mkdir()
    (worktree / ".guardkit" / "autobuild").mkdir(parents=True)
    yield worktree
    # Cleanup handled by tmp_path fixture

@pytest.fixture
def mock_task_file(test_worktree):
    """Create mock task file in worktree."""
    tasks_dir = test_worktree / "tasks" / "in_progress"
    tasks_dir.mkdir(parents=True)
    # ... create task file
```

## Files to Create

- `tests/integration/test_sdk_delegation.py` - Main integration tests
- `tests/integration/conftest.py` - Test fixtures (if not exists)

## Files to Modify

- `tests/integration/__init__.py` - Ensure package exists

## Verification

```bash
# Run integration tests
pytest tests/integration/test_sdk_delegation.py -v --tb=short

# Run with real SDK (requires API key)
ANTHROPIC_API_KEY=xxx pytest tests/integration/test_sdk_delegation.py -v -m "not mock"
```

## Related

- TASK-SDK-001: SDK query (dependency)
- TASK-SDK-002: Stream parser (dependency)
- TASK-SDK-003: Results writer (dependency)
