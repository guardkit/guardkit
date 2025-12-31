# AutoBuild Testing Guide

This document describes the testing strategy for the AutoBuild orchestration system.

## Overview

AutoBuild uses a three-tier testing strategy:

1. **Unit Tests** - Test individual components in isolation with mocked dependencies
2. **Integration Tests** - Test component interactions with real file fixtures
3. **End-to-End Tests** - Test complete workflows with mocked SDK calls

## Test Organization

```
tests/
├── unit/
│   ├── test_autobuild_orchestrator.py   # Orchestrator logic tests
│   ├── test_agent_invoker.py            # SDK integration tests
│   ├── test_cli_autobuild.py            # CLI command tests
│   └── test_cli_decorators.py           # Error handling tests
├── integration/
│   └── test_autobuild_e2e.py            # End-to-end workflow tests
└── fixtures/
    ├── TEST-SIMPLE.md                    # Simple single-turn task
    └── TEST-ITERATION.md                 # Multi-turn iterative task
```

## Running Tests

### Prerequisites

Install development dependencies:

```bash
pip install -e ".[dev,autobuild]"
```

### Run All Tests

```bash
pytest tests/ -v --cov=guardkit --cov-report=term-missing
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v -m integration

# Async tests only
pytest tests/ -v -k "async"
```

### Coverage Report

```bash
pytest tests/ -v \
    --cov=guardkit.orchestrator \
    --cov=guardkit.cli.autobuild \
    --cov-report=term-missing \
    --cov-report=html
```

## Unit Tests

### AutoBuildOrchestrator (`test_autobuild_orchestrator.py`)

Tests the orchestration logic using mocked dependencies.

**Test Classes:**

- `TestConstructor` - Initialization and dependency injection
- `TestSetupPhase` - Worktree creation and initialization
- `TestLoopPhase` - Player↔Coach adversarial turns
- `TestFinalizePhase` - Worktree preservation and summary
- `TestIntegration` - End-to-end workflows with mocks
- `TestStatePersistence` - State save/resume functionality

**Key Test Patterns:**

```python
# Fixture for mocked orchestrator
@pytest.fixture
def orchestrator_with_mocks(
    mock_worktree_manager,
    mock_agent_invoker,
    mock_progress_display
):
    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/test-repo"),
        max_turns=5,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
    )

# Helper to create test results
def make_player_result(
    task_id: str = "TASK-AB-001",
    turn: int = 1,
    success: bool = True,
    error: Optional[str] = None,
) -> AgentInvocationResult:
    """Create Player AgentInvocationResult for testing."""
    ...

def make_coach_result(
    task_id: str = "TASK-AB-001",
    turn: int = 1,
    decision: str = "approve",  # or "feedback"
    success: bool = True,
) -> AgentInvocationResult:
    """Create Coach AgentInvocationResult for testing."""
    ...
```

### AgentInvoker (`test_agent_invoker.py`)

Tests SDK integration with mocked Claude Agent SDK.

**Test Classes:**

- `TestAgentInvokerInit` - Configuration and initialization
- `TestPlayerInvocation` - Player agent invocation
- `TestCoachInvocation` - Coach agent validation
- `TestPromptBuilding` - Prompt construction
- `TestReportValidation` - JSON report validation
- `TestSDKIntegration` - SDK interaction patterns
- `TestHelperMethods` - Internal helper functions

**Key Test Patterns:**

```python
# Create report files for testing
def create_report_file(
    worktree_path: Path,
    task_id: str,
    turn: int,
    agent_type: str,
    report: Dict[str, Any]
):
    """Helper to create agent report file."""
    autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
    autobuild_dir.mkdir(parents=True, exist_ok=True)
    report_path = autobuild_dir / f"{agent_type}_turn_{turn}.json"
    report_path.write_text(json.dumps(report, indent=2))
    return report_path

# Mock SDK invocation
@pytest.mark.asyncio
async def test_invoke_player_success(agent_invoker, worktree_path, sample_player_report):
    create_report_file(worktree_path, "TASK-001", 1, "player", sample_player_report)

    with patch.object(agent_invoker, "_invoke_with_role", new_callable=AsyncMock):
        result = await agent_invoker.invoke_player(
            task_id="TASK-001",
            turn=1,
            requirements="Implement OAuth2 authentication",
        )

        assert result.success is True
        assert result.report == sample_player_report
```

### CLI Commands (`test_cli_autobuild.py`)

Tests Click command argument parsing and output formatting.

**Test Coverage:**

- Argument parsing (missing args, invalid options, help text)
- Command execution (task command, status command)
- Output formatting (success, error, verbose modes)
- Exit codes (0 success, 1 not found, 2 error)

**Key Test Patterns:**

```python
@pytest.fixture
def cli_runner():
    return CliRunner()

@patch("guardkit.cli.autobuild.TaskLoader.load_task")
@patch("guardkit.cli.autobuild.AutoBuildOrchestrator")
def test_task_command_success(
    mock_orchestrator_class,
    mock_load_task,
    cli_runner,
    mock_task_data,
    mock_success_result
):
    mock_load_task.return_value = mock_task_data
    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_success_result
    mock_orchestrator_class.return_value = mock_orchestrator

    result = cli_runner.invoke(task, ["TASK-AB-001"])

    assert result.exit_code == 0
```

## Integration Tests

### End-to-End Workflows (`test_autobuild_e2e.py`)

Tests complete orchestration workflows with real file fixtures.

**Test Classes:**

- `TestSimpleTaskWorkflow` - Single-turn approval
- `TestIterativeTaskWorkflow` - Multi-turn with feedback
- `TestMaxTurnsExhaustion` - Max turns limit
- `TestErrorHandling` - Player/Coach failures

**Key Test Patterns:**

```python
@pytest.fixture
def test_repo_root(tmp_path):
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir, check=True, capture_output=True
    )

    readme = repo_dir / "README.md"
    readme.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir, check=True, capture_output=True
    )

    return repo_dir

@pytest.mark.integration
def test_simple_task_single_turn_approval(
    test_repo_root,
    simple_task_fixture,
    mock_agent_invoker_simple,
):
    orchestrator = AutoBuildOrchestrator(
        repo_root=test_repo_root,
        max_turns=5,
        agent_invoker=mock_agent_invoker_simple,
    )

    result = orchestrator.orchestrate(
        task_id=simple_task_fixture['task_id'],
        requirements=simple_task_fixture['requirements'],
        acceptance_criteria=simple_task_fixture['acceptance_criteria'],
    )

    assert result.success is True
    assert result.total_turns == 1
    assert result.final_decision == "approved"
```

## Test Fixtures

### Task Fixtures

Located in `tests/fixtures/`:

**TEST-SIMPLE.md** - Simple task for single-turn testing:

```yaml
---
id: TEST-SIMPLE
title: Simple Test Task
status: backlog
complexity: 2
autobuild:
  expected_turns: 1
---

## Description
Create a simple hello world function.

## Acceptance Criteria
- [ ] Function returns greeting
- [ ] Unit tests pass
```

**TEST-ITERATION.md** - Complex task for multi-turn testing:

```yaml
---
id: TEST-ITERATION
title: Iterative Test Task
status: backlog
complexity: 5
autobuild:
  expected_turns: 3
---

## Description
Implement OAuth2 authentication flow.

## Acceptance Criteria
- [ ] Authorization code flow
- [ ] Token refresh handling
- [ ] Security best practices
- [ ] Edge case coverage
```

### Mock Agent Invokers

Pre-configured mocks for different test scenarios:

```python
@pytest.fixture
def mock_agent_invoker_simple():
    """Single-turn approval workflow."""
    invoker = Mock()
    invoker.invoke_player = AsyncMock(return_value=player_result)
    invoker.invoke_coach = AsyncMock(return_value=coach_approval)
    return invoker

@pytest.fixture
def mock_agent_invoker_iteration():
    """Multi-turn feedback workflow."""
    invoker = Mock()
    invoker.invoke_player = AsyncMock(
        side_effect=[player_result_1, player_result_2, player_result_3]
    )
    invoker.invoke_coach = AsyncMock(
        side_effect=[coach_feedback_1, coach_feedback_2, coach_approval]
    )
    return invoker

@pytest.fixture
def mock_agent_invoker_max_turns():
    """Never approves (tests max_turns exhaustion)."""
    invoker = Mock()
    invoker.invoke_player = AsyncMock(return_value=player_result)
    invoker.invoke_coach = AsyncMock(return_value=coach_feedback)  # Always feedback
    return invoker
```

## Coverage Requirements

Target coverage: **≥80%** for AutoBuild components.

**Key metrics:**

| Component | Target | Tracked In |
|-----------|--------|------------|
| `orchestrator/autobuild.py` | ≥80% | `test_autobuild_orchestrator.py` |
| `orchestrator/agent_invoker.py` | ≥80% | `test_agent_invoker.py` |
| `cli/autobuild.py` | ≥80% | `test_cli_autobuild.py` |
| `worktrees/*.py` | ≥75% | Integration tests |

## Async Testing

AutoBuild uses async/await for SDK calls. Tests use pytest-asyncio:

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result.success is True
```

Configure in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Mocking SDK Calls

The Claude Agent SDK is mocked to avoid real API calls:

```python
async def mock_query_gen(*args, **kwargs):
    """Mock SDK query() generator."""
    yield MagicMock(type="assistant")
    yield MagicMock(type="result", subtype="success")

mock_sdk = MagicMock()
mock_sdk.query = mock_query_gen
mock_sdk.ClaudeAgentOptions = MagicMock()

import sys
with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
    # Test code that imports claude_agent_sdk
    ...
```

## Error Scenarios

### SDK Not Installed

```python
async def test_sdk_handles_import_error(agent_invoker):
    with patch.dict(sys.modules, {"claude_agent_sdk": None}):
        with pytest.raises(AgentInvocationError) as exc_info:
            await agent_invoker._invoke_with_role(...)

        assert "Claude Agent SDK not installed" in str(exc_info.value)
```

### SDK Timeout

```python
async def test_sdk_handles_timeout(agent_invoker):
    async def mock_query_timeout(*args, **kwargs):
        await asyncio.sleep(10)  # Simulate long operation
        yield MagicMock()

    agent_invoker.sdk_timeout_seconds = 0.01  # Very short timeout

    with pytest.raises(SDKTimeoutError):
        await agent_invoker._invoke_with_role(...)
```

### Invalid Agent Reports

```python
def test_validate_player_report_missing_field(agent_invoker):
    incomplete_report = {"task_id": "TASK-001", "turn": 1}

    with pytest.raises(PlayerReportInvalidError) as exc_info:
        agent_invoker._validate_player_report(incomplete_report)

    assert "Missing fields" in str(exc_info.value)
```

## CI Integration

Tests run automatically on GitHub Actions:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev,autobuild]"
      - run: pytest tests/ -v --cov=guardkit --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Troubleshooting

### "No module named 'claude_agent_sdk'"

Install the SDK:

```bash
pip install claude-agent-sdk
```

Or mock it in tests:

```python
with patch.dict(sys.modules, {"claude_agent_sdk": MagicMock()}):
    ...
```

### "pytest-asyncio not found"

Install async test support:

```bash
pip install pytest-asyncio
```

### Git Worktree Errors in Tests

Ensure temporary repos have initial commits:

```python
subprocess.run(["git", "init"], cwd=repo_dir, check=True)
subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo_dir, check=True)
```

### Coverage Below Threshold

Check for untested edge cases:

```bash
pytest tests/ --cov=guardkit --cov-report=term-missing | grep MISSING
```

Add tests for uncovered lines.

## Related Documentation

- [AutoBuild Overview](../../CLAUDE.md#autobuild---autonomous-task-implementation)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
