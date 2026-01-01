---
id: TASK-TWD-005
title: Create integration tests for task-work delegation flow
status: backlog
task_type: implementation
created: 2025-12-31T14:00:00Z
priority: medium
tags: [autobuild, testing, integration, quality-assurance]
complexity: 5
parent_feature: autobuild-task-work-delegation
wave: 3
implementation_mode: task-work
conductor_workspace: autobuild-twd-wave3-1
source_review: TASK-REV-RW01
depends_on: [TASK-TWD-001, TASK-TWD-002, TASK-TWD-003, TASK-TWD-004]
---

# Task: Create integration tests for task-work delegation flow

## Description

Create comprehensive integration tests to verify the complete task-work delegation flow works correctly end-to-end. These tests ensure that AutoBuild correctly delegates to task-work and that all subagent infrastructure is properly utilized.

## Test Scenarios

### 1. Basic Delegation Flow

```python
# tests/integration/test_autobuild_delegation.py

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.agent_invoker import AgentInvoker


class TestTaskWorkDelegation:
    """Integration tests for task-work delegation in AutoBuild."""

    @pytest.fixture
    def mock_worktree(self, tmp_path):
        """Create a mock worktree structure."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        # Create task file
        task_dir = worktree / "tasks" / "in_progress"
        task_dir.mkdir(parents=True)
        task_file = task_dir / "TASK-TEST-001.md"
        task_file.write_text("""---
id: TASK-TEST-001
title: Test Task
status: design_approved
---

# Test Task

## Requirements
- Implement feature X
""")
        return worktree

    @pytest.mark.asyncio
    async def test_invoke_player_calls_task_work(self, mock_worktree):
        """Verify invoke_player delegates to task-work --implement-only."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            development_mode="tdd",
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b'{"success": true}', b'')
            mock_exec.return_value = mock_proc

            result = await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Implement feature X",
            )

            # Verify task-work was called with correct args
            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]
            assert "guardkit" in call_args
            assert "task-work" in call_args
            assert "--implement-only" in call_args
            assert "--mode=tdd" in call_args

    @pytest.mark.asyncio
    async def test_invoke_player_with_feedback(self, mock_worktree):
        """Verify feedback is written and passed on Turn 2+."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            development_mode="tdd",
        )

        feedback = {
            "turn": 1,
            "must_fix": ["Add error handling"],
            "should_fix": ["Extract helper"],
        }

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b'{"success": true}', b'')
            mock_exec.return_value = mock_proc

            result = await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=2,
                requirements="Implement feature X",
                feedback=feedback,
            )

            # Verify feedback file was created
            feedback_path = (
                mock_worktree
                / ".guardkit"
                / "autobuild"
                / "TASK-TEST-001"
                / "coach_feedback.json"
            )
            assert feedback_path.exists()

            # Verify --feedback-file was passed
            call_args = mock_exec.call_args[0]
            assert "--feedback-file" in call_args
```

### 2. State Transition Tests

```python
class TestStateTransitions:
    """Test state transitions during delegation."""

    @pytest.mark.asyncio
    async def test_task_requires_design_approved_state(self, mock_worktree):
        """Verify task must be in design_approved state."""
        # Create task in wrong state
        task_file = mock_worktree / "tasks" / "backlog" / "TASK-TEST-002.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text("""---
id: TASK-TEST-002
status: backlog
---
""")

        invoker = AgentInvoker(worktree_path=mock_worktree)

        with pytest.raises(StateError) as exc_info:
            await invoker.invoke_player(
                task_id="TASK-TEST-002",
                turn=1,
                requirements="Test",
            )

        assert "design_approved" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_preloop_sets_design_approved_state(self, mock_worktree):
        """Verify PreLoop sets state correctly before delegation."""
        from guardkit.orchestrator.quality_gates.pre_loop import PreLoopQualityGates

        pre_loop = PreLoopQualityGates(worktree_path=mock_worktree)

        with patch.object(pre_loop, "task_work_interface") as mock_tw:
            mock_tw.execute_design_phase.return_value = MagicMock(
                implementation_plan={"steps": []},
                checkpoint_result="approved",
            )

            await pre_loop.execute(task_id="TASK-TEST-001")

            # Verify task state was set
            # ... state verification logic
```

### 3. Mode Parameter Tests

```python
class TestModeParameter:
    """Test development mode parameter handling."""

    @pytest.mark.parametrize("mode", ["tdd", "standard", "bdd"])
    @pytest.mark.asyncio
    async def test_mode_passed_to_task_work(self, mock_worktree, mode):
        """Verify mode is passed correctly to task-work."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            development_mode=mode,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b'{"success": true}', b'')
            mock_exec.return_value = mock_proc

            await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test",
            )

            call_args = mock_exec.call_args[0]
            assert f"--mode={mode}" in call_args

    def test_cli_mode_option(self, runner):
        """Test CLI accepts --mode option."""
        from guardkit.cli.autobuild import autobuild

        result = runner.invoke(
            autobuild,
            ["task", "TASK-TEST-001", "--mode", "tdd", "--help"],
        )
        assert result.exit_code == 0
```

### 4. Error Handling Tests

```python
class TestErrorHandling:
    """Test error handling in delegation flow."""

    @pytest.mark.asyncio
    async def test_task_work_timeout_handled(self, mock_worktree):
        """Verify timeout is handled gracefully."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            sdk_timeout_seconds=1,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.side_effect = asyncio.TimeoutError()
            mock_exec.return_value = mock_proc

            result = await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test",
            )

            assert not result.success
            assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_task_work_failure_captured(self, mock_worktree):
        """Verify task-work failures are captured."""
        invoker = AgentInvoker(worktree_path=mock_worktree)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate.return_value = (
                b'',
                b'Error: Task not found',
            )
            mock_exec.return_value = mock_proc

            result = await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test",
            )

            assert not result.success
            assert "Task not found" in result.error
```

### 5. Full Flow Integration Test

```python
class TestFullDelegationFlow:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_autobuild_with_delegation(self, mock_worktree):
        """Test complete AutoBuild flow with task-work delegation."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=mock_worktree,
            max_turns=3,
            development_mode="tdd",
        )

        # Mock the subprocess calls
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Player calls succeed
            mock_player = AsyncMock()
            mock_player.returncode = 0
            mock_player.communicate.return_value = (
                b'{"success": true, "tests_passed": true}',
                b'',
            )

            # Coach approves
            mock_coach = AsyncMock()
            mock_coach.returncode = 0
            mock_coach.communicate.return_value = (
                b'{"decision": "approve"}',
                b'',
            )

            mock_exec.side_effect = [mock_player, mock_coach]

            result = await orchestrator.orchestrate(
                task_id="TASK-TEST-001",
                requirements="Implement feature X",
                acceptance_criteria=["Feature works"],
            )

            assert result.success
            assert result.total_turns == 1
```

## Test Fixtures

```python
# tests/conftest.py

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_task_file(tmp_path):
    """Create a mock task file."""
    def _create(task_id, status="design_approved"):
        task_dir = tmp_path / "tasks" / "in_progress"
        task_dir.mkdir(parents=True, exist_ok=True)
        task_file = task_dir / f"{task_id}.md"
        task_file.write_text(f"""---
id: {task_id}
title: Test Task
status: {status}
---

# {task_id}
""")
        return task_file
    return _create
```

## Acceptance Criteria

1. Unit tests for invoke_player delegation
2. Unit tests for feedback file creation and passing
3. Unit tests for state validation
4. Unit tests for mode parameter handling
5. Unit tests for error handling (timeout, failure)
6. Integration test for complete flow
7. All tests pass with pytest
8. Code coverage ≥80% for modified files

## Files to Create

- `tests/integration/test_autobuild_delegation.py` - Main test file
- `tests/conftest.py` - Update with new fixtures (if needed)

## Testing Commands

```bash
# Run all delegation tests
pytest tests/integration/test_autobuild_delegation.py -v

# Run with coverage
pytest tests/integration/test_autobuild_delegation.py -v --cov=guardkit/orchestrator

# Run integration tests only
pytest tests/integration/ -v -m integration
```

## Notes

- Use pytest-asyncio for async test support
- Mock subprocess calls to avoid actual task-work execution in unit tests
- Consider adding smoke test that actually runs task-work (marked as slow)
- Ensure tests work in CI/CD environment
