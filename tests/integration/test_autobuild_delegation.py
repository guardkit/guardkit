"""
Integration Tests for Task-Work Delegation in AutoBuild

Tests complete task-work delegation flow, verifying that AutoBuild correctly
delegates to task-work and that all subagent infrastructure is properly utilized.

Test Coverage:
    - Basic delegation flow (invoke_player calls task-work --implement-only)
    - Feedback file creation and passing for Turn 2+
    - State validation (design_approved requirement)
    - Mode parameter handling (tdd, standard, bdd)
    - Error handling (timeout, failure scenarios)
    - Full flow integration test

Architecture:
    - Uses real file fixtures and temporary directories
    - Mocks subprocess calls to avoid actual task-work execution
    - Tests state transitions via TaskStateBridge
    - Verifies feedback file creation and format

Run with:
    pytest tests/integration/test_autobuild_delegation.py -v
    pytest tests/integration/test_autobuild_delegation.py -v --cov=guardkit/orchestrator
"""

import asyncio
import json
import pytest
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch, MagicMock

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

# Import components under test
from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
)
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
)
from guardkit.orchestrator.exceptions import (
    SDKTimeoutError,
    TaskStateError,
    PlanNotFoundError,
)
from guardkit.tasks.state_bridge import TaskStateBridge


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree(tmp_path):
    """
    Create a mock worktree structure with task file and plan.

    Returns:
        Path: Path to worktree root
    """
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Create task directories
    task_dir = worktree / "tasks" / "design_approved"
    task_dir.mkdir(parents=True)

    # Also create in_progress for state transition tests
    in_progress_dir = worktree / "tasks" / "in_progress"
    in_progress_dir.mkdir(parents=True)

    # Create task file in design_approved state
    task_file = task_dir / "TASK-TEST-001-test-task.md"
    task_file.write_text("""---
id: TASK-TEST-001
title: Test Task
status: design_approved
created: 2025-12-31T10:00:00Z
priority: medium
complexity: 3
---

# Test Task

## Description

Implement feature X for testing task-work delegation.

## Requirements

- Implement feature X
- Add comprehensive tests
- Ensure code quality

## Acceptance Criteria

- [ ] Feature X works correctly
- [ ] All tests pass
- [ ] Coverage >= 80%
""", encoding='utf-8')

    # Create implementation plan
    plan_dir = worktree / ".claude" / "task-plans"
    plan_dir.mkdir(parents=True)
    plan_file = plan_dir / "TASK-TEST-001-implementation-plan.md"
    plan_file.write_text("""# Implementation Plan: TASK-TEST-001

## Overview

This plan covers the implementation of feature X.

## Steps

1. Create feature module
2. Implement core logic
3. Add unit tests
4. Add integration tests
5. Update documentation

## Files to Create

- src/feature.py
- tests/test_feature.py

## Estimated Complexity: 3/10
""", encoding='utf-8')

    # Create .guardkit/autobuild directory for reports
    autobuild_dir = worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"
    autobuild_dir.mkdir(parents=True)

    return worktree


@pytest.fixture
def mock_worktree_backlog(tmp_path):
    """
    Create a mock worktree with task in backlog state (for state validation tests).

    Returns:
        Path: Path to worktree root
    """
    worktree = tmp_path / "worktree_backlog"
    worktree.mkdir()

    # Create task directories
    backlog_dir = worktree / "tasks" / "backlog"
    backlog_dir.mkdir(parents=True)

    # Create task file in backlog state (not design_approved)
    task_file = backlog_dir / "TASK-TEST-002-backlog-task.md"
    task_file.write_text("""---
id: TASK-TEST-002
title: Backlog Task
status: backlog
created: 2025-12-31T10:00:00Z
priority: medium
---

# Backlog Task

## Description

A task in backlog state for testing.
""", encoding='utf-8')

    return worktree


@pytest.fixture
def runner():
    """CLI test runner."""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def mock_coach_validator():
    """
    Patch CoachValidator to force SDK fallback.

    The CoachValidator is tried first in _invoke_coach_safely. By making it
    raise an exception, we force the orchestrator to use the mock_agent_invoker
    which the tests control.
    """
    with patch(
        "guardkit.orchestrator.autobuild.CoachValidator"
    ) as mock_validator_class:
        # Make CoachValidator.validate() raise to force SDK fallback
        mock_instance = MagicMock()
        mock_instance.validate.side_effect = Exception("Force SDK fallback for test")
        mock_validator_class.return_value = mock_instance
        yield mock_validator_class


@pytest.fixture
def mock_task_file(tmp_path):
    """
    Factory to create mock task files with specific states.

    Returns:
        Callable: Factory function to create task files
    """
    def _create(task_id: str, status: str = "design_approved", create_plan: bool = True):
        # Determine correct directory based on status
        if status == "design_approved":
            task_dir = tmp_path / "tasks" / "design_approved"
        elif status == "in_progress":
            task_dir = tmp_path / "tasks" / "in_progress"
        else:
            task_dir = tmp_path / "tasks" / status

        task_dir.mkdir(parents=True, exist_ok=True)
        task_file = task_dir / f"{task_id}.md"
        task_file.write_text(f"""---
id: {task_id}
title: Test Task
status: {status}
---

# {task_id}

## Description

Test task for integration testing.
""", encoding='utf-8')

        # Create implementation plan if requested
        if create_plan:
            plan_dir = tmp_path / ".claude" / "task-plans"
            plan_dir.mkdir(parents=True, exist_ok=True)
            plan_file = plan_dir / f"{task_id}-implementation-plan.md"
            plan_file.write_text(f"""# Implementation Plan: {task_id}

This is a valid implementation plan with enough content.

## Steps
1. Step one
2. Step two
3. Step three
""", encoding='utf-8')

        # Create autobuild directory
        autobuild_dir = tmp_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True, exist_ok=True)

        return task_file

    return _create


# ============================================================================
# TestTaskWorkDelegation - Basic Delegation Flow
# ============================================================================


@pytest.mark.integration
class TestTaskWorkDelegation:
    """Integration tests for task-work delegation in AutoBuild."""

    @pytest.mark.asyncio
    async def test_invoke_player_calls_task_work(self, mock_worktree):
        """Verify invoke_player delegates to task-work --implement-only."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            development_mode="tdd",
            use_task_work_delegation=True,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Configure mock process
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(
                b'{"success": true, "tests_passed": true}',
                b''
            ))
            mock_exec.return_value = mock_proc

            # Create player report file (task-work would create this)
            report_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"
            report_file = report_dir / "player_turn_1.json"
            report_file.write_text(json.dumps({
                "task_id": "TASK-TEST-001",
                "turn": 1,
                "files_modified": [],
                "files_created": ["src/feature.py"],
                "tests_written": ["tests/test_feature.py"],
                "tests_run": True,
                "tests_passed": True,
                "implementation_notes": "Implemented feature X",
                "concerns": [],
                "requirements_addressed": ["Feature X"],
                "requirements_remaining": [],
            }), encoding='utf-8')

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

            # Verify result
            assert result.success is True
            assert result.agent_type == "player"
            assert result.report["tests_passed"] is True

    @pytest.mark.asyncio
    async def test_invoke_player_with_feedback(self, mock_worktree):
        """Verify feedback is written and passed on Turn 2+."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            development_mode="tdd",
            use_task_work_delegation=True,
        )

        feedback = {
            "task_id": "TASK-TEST-001",
            "turn": 1,
            "decision": "feedback",
            "issues": [
                {
                    "type": "missing_requirement",
                    "severity": "critical",
                    "description": "Add error handling",
                    "suggestion": "Implement try-catch blocks",
                },
                {
                    "type": "code_quality",
                    "severity": "minor",
                    "description": "Extract helper function",
                    "suggestion": "Create a utility method",
                }
            ],
            "rationale": "Need improvements before approval",
        }

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(
                b'{"success": true}',
                b''
            ))
            mock_exec.return_value = mock_proc

            # Create player report for turn 2
            report_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"
            report_file = report_dir / "player_turn_2.json"
            report_file.write_text(json.dumps({
                "task_id": "TASK-TEST-001",
                "turn": 2,
                "files_modified": ["src/feature.py"],
                "files_created": [],
                "tests_written": [],
                "tests_run": True,
                "tests_passed": True,
                "implementation_notes": "Added error handling",
                "concerns": [],
                "requirements_addressed": ["Error handling"],
                "requirements_remaining": [],
            }), encoding='utf-8')

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
                / "coach_feedback_for_turn_2.json"
            )
            assert feedback_path.exists()

            # Verify feedback content
            with open(feedback_path) as f:
                written_feedback = json.load(f)
            assert written_feedback["turn"] == 2
            assert written_feedback["feedback_from_turn"] == 1
            assert len(written_feedback["must_fix"]) >= 1
            assert len(written_feedback["should_fix"]) >= 1

    @pytest.mark.asyncio
    async def test_invoke_player_without_delegation(self, mock_worktree):
        """Verify legacy mode (no delegation) uses SDK directly."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            development_mode="tdd",
            use_task_work_delegation=False,  # Disable delegation
        )

        # Mock the SDK invocation
        with patch.object(invoker, "_invoke_with_role") as mock_sdk:
            # Create player report file
            report_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"
            report_file = report_dir / "player_turn_1.json"
            report_file.write_text(json.dumps({
                "task_id": "TASK-TEST-001",
                "turn": 1,
                "files_modified": [],
                "files_created": ["src/feature.py"],
                "tests_written": ["tests/test_feature.py"],
                "tests_run": True,
                "tests_passed": True,
                "implementation_notes": "Implemented via SDK",
                "concerns": [],
                "requirements_addressed": ["Feature X"],
                "requirements_remaining": [],
            }), encoding='utf-8')

            result = await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Implement feature X",
            )

            # Verify SDK was called (not subprocess)
            mock_sdk.assert_called_once()
            call_kwargs = mock_sdk.call_args
            assert call_kwargs[1]["agent_type"] == "player"


# ============================================================================
# TestStateTransitions - State Validation Tests
# ============================================================================


@pytest.mark.integration
class TestStateTransitions:
    """Test state transitions during delegation."""

    def test_state_bridge_finds_task_in_design_approved(self, mock_worktree):
        """Verify TaskStateBridge finds task in design_approved state."""
        bridge = TaskStateBridge("TASK-TEST-001", mock_worktree)

        state = bridge.get_current_state()
        assert state == "design_approved"

    def test_state_bridge_transitions_from_in_progress(self, tmp_path):
        """Verify TaskStateBridge transitions task from in_progress to design_approved."""
        # Create task in in_progress state
        in_progress_dir = tmp_path / "tasks" / "in_progress"
        in_progress_dir.mkdir(parents=True)
        task_file = in_progress_dir / "TASK-TRANS-001.md"
        task_file.write_text("""---
id: TASK-TRANS-001
title: Transition Test
status: in_progress
---

# Test Task
""", encoding='utf-8')

        # Create implementation plan
        plan_dir = tmp_path / ".claude" / "task-plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "TASK-TRANS-001-implementation-plan.md"
        plan_file.write_text("""# Implementation Plan

Valid plan content with sufficient length for validation.

## Steps
1. First step
2. Second step
""", encoding='utf-8')

        # Create design_approved directory
        design_approved_dir = tmp_path / "tasks" / "design_approved"
        design_approved_dir.mkdir(parents=True)

        bridge = TaskStateBridge("TASK-TRANS-001", tmp_path)

        # Initially in in_progress
        assert bridge.get_current_state() == "in_progress"

        # Transition to design_approved
        result = bridge.ensure_design_approved_state()

        assert result is True
        assert bridge.get_current_state() == "design_approved"

        # Verify file was moved
        assert not task_file.exists()
        new_task_file = design_approved_dir / "TASK-TRANS-001.md"
        assert new_task_file.exists()

    def test_state_bridge_raises_on_missing_plan(self, tmp_path):
        """Verify TaskStateBridge raises PlanNotFoundError when plan is missing."""
        # Create task without implementation plan
        task_dir = tmp_path / "tasks" / "in_progress"
        task_dir.mkdir(parents=True)
        task_file = task_dir / "TASK-NO-PLAN-001.md"
        task_file.write_text("""---
id: TASK-NO-PLAN-001
title: No Plan Task
status: in_progress
---

# Test Task
""", encoding='utf-8')

        # Create design_approved directory
        design_approved_dir = tmp_path / "tasks" / "design_approved"
        design_approved_dir.mkdir(parents=True)

        bridge = TaskStateBridge("TASK-NO-PLAN-001", tmp_path)

        with pytest.raises(PlanNotFoundError) as exc_info:
            bridge.ensure_design_approved_state()

        assert "TASK-NO-PLAN-001" in str(exc_info.value)
        assert "implementation plan" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_ensure_design_approved_called_before_delegation(self, mock_worktree):
        """Verify AgentInvoker calls _ensure_design_approved_state before delegation."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            development_mode="tdd",
            use_task_work_delegation=True,
        )

        with patch.object(invoker, "_ensure_design_approved_state") as mock_ensure:
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(return_value=(b'{}', b''))
                mock_exec.return_value = mock_proc

                # Create player report
                report_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"
                report_file = report_dir / "player_turn_1.json"
                report_file.write_text(json.dumps({
                    "task_id": "TASK-TEST-001",
                    "turn": 1,
                    "files_modified": [],
                    "files_created": [],
                    "tests_written": [],
                    "tests_run": True,
                    "tests_passed": True,
                    "implementation_notes": "",
                    "concerns": [],
                    "requirements_addressed": [],
                    "requirements_remaining": [],
                }), encoding='utf-8')

                await invoker.invoke_player(
                    task_id="TASK-TEST-001",
                    turn=1,
                    requirements="Test",
                )

                # Verify _ensure_design_approved_state was called
                mock_ensure.assert_called_once_with("TASK-TEST-001")


# ============================================================================
# TestModeParameter - Development Mode Tests
# ============================================================================


@pytest.mark.integration
class TestModeParameter:
    """Test development mode parameter handling."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", ["tdd", "standard", "bdd"])
    async def test_mode_passed_to_task_work(self, mock_worktree, mode):
        """Verify mode is passed correctly to task-work."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            development_mode=mode,
            use_task_work_delegation=True,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(
                b'{"success": true}',
                b''
            ))
            mock_exec.return_value = mock_proc

            # Create player report
            report_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"
            report_file = report_dir / "player_turn_1.json"
            report_file.write_text(json.dumps({
                "task_id": "TASK-TEST-001",
                "turn": 1,
                "files_modified": [],
                "files_created": [],
                "tests_written": [],
                "tests_run": True,
                "tests_passed": True,
                "implementation_notes": "",
                "concerns": [],
                "requirements_addressed": [],
                "requirements_remaining": [],
            }), encoding='utf-8')

            await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test",
            )

            call_args = mock_exec.call_args[0]
            assert f"--mode={mode}" in call_args

    @pytest.mark.asyncio
    async def test_mode_override_in_invoke_player(self, mock_worktree):
        """Verify mode parameter in invoke_player overrides instance mode."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            development_mode="standard",  # Instance default
            use_task_work_delegation=True,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b'{}', b''))
            mock_exec.return_value = mock_proc

            # Create player report
            report_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"
            report_file = report_dir / "player_turn_1.json"
            report_file.write_text(json.dumps({
                "task_id": "TASK-TEST-001",
                "turn": 1,
                "files_modified": [],
                "files_created": [],
                "tests_written": [],
                "tests_run": True,
                "tests_passed": True,
                "implementation_notes": "",
                "concerns": [],
                "requirements_addressed": [],
                "requirements_remaining": [],
            }), encoding='utf-8')

            await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test",
                mode="bdd",  # Override to bdd
            )

            call_args = mock_exec.call_args[0]
            assert "--mode=bdd" in call_args

    def test_cli_mode_option(self, runner):
        """Test CLI accepts --mode option."""
        from guardkit.cli.autobuild import autobuild

        result = runner.invoke(
            autobuild,
            ["task", "TASK-TEST-001", "--mode", "tdd", "--help"],
        )
        # --help should work without error
        assert result.exit_code == 0


# ============================================================================
# TestErrorHandling - Error Handling Tests
# ============================================================================


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in delegation flow."""

    @pytest.mark.asyncio
    async def test_task_work_timeout_handled(self, mock_worktree):
        """Verify timeout is handled gracefully."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            sdk_timeout_seconds=1,  # Short timeout
            use_task_work_delegation=True,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            # Simulate timeout on communicate
            mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_proc.kill = Mock()
            mock_proc.wait = AsyncMock()
            mock_exec.return_value = mock_proc

            result = await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test",
            )

            assert result.success is False
            assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_task_work_failure_captured(self, mock_worktree):
        """Verify task-work failures are captured."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            use_task_work_delegation=True,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1  # Non-zero exit code
            mock_proc.communicate = AsyncMock(return_value=(
                b'',
                b'Error: Task not found'
            ))
            mock_exec.return_value = mock_proc

            result = await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test",
            )

            assert result.success is False
            assert "Task not found" in result.error

    @pytest.mark.asyncio
    async def test_guardkit_not_found_handled(self, mock_worktree):
        """Verify missing guardkit command is handled gracefully."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            use_task_work_delegation=True,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = FileNotFoundError("guardkit not found")

            result = await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test",
            )

            assert result.success is False
            assert "guardkit" in result.error.lower() or "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_player_report_not_found(self, mock_worktree):
        """Verify missing player report is handled."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            use_task_work_delegation=True,
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b'{}', b''))
            mock_exec.return_value = mock_proc

            # DON'T create the player report file
            # This should cause PlayerReportNotFoundError

            result = await invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test",
            )

            assert result.success is False
            assert "report" in result.error.lower() or "not found" in result.error.lower()


# ============================================================================
# TestFullDelegationFlow - End-to-End Integration
# ============================================================================


@pytest.mark.integration
class TestFullDelegationFlow:
    """End-to-end integration tests for complete AutoBuild with delegation."""

    def test_complete_autobuild_with_delegation_approval(self, tmp_path, mock_coach_validator):
        """Test complete AutoBuild flow with task-work delegation (approval path)."""
        # Setup mock repository
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir, check=True, capture_output=True
        )

        # Create initial commit
        readme = repo_dir / "README.md"
        readme.write_text("# Test Repo", encoding='utf-8')
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir, check=True, capture_output=True
        )

        # Create task file
        task_dir = repo_dir / "tasks" / "design_approved"
        task_dir.mkdir(parents=True)
        task_file = task_dir / "TASK-E2E-001.md"
        task_file.write_text("""---
id: TASK-E2E-001
title: E2E Test Task
status: design_approved
complexity: 3
---

# E2E Test Task

Implement feature for e2e testing.
""", encoding='utf-8')

        # Create implementation plan
        plan_dir = repo_dir / ".claude" / "task-plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "TASK-E2E-001-implementation-plan.md"
        plan_file.write_text("""# Implementation Plan

Valid plan with enough content for validation purposes.

## Steps
1. Create feature
2. Add tests
""", encoding='utf-8')

        # Mock AgentInvoker for predictable behavior
        mock_invoker = Mock()

        # Player succeeds on turn 1
        player_result = AgentInvocationResult(
            task_id="TASK-E2E-001",
            turn=1,
            agent_type="player",
            success=True,
            report={
                "task_id": "TASK-E2E-001",
                "turn": 1,
                "files_modified": [],
                "files_created": ["src/feature.py"],
                "tests_written": ["tests/test_feature.py"],
                "tests_run": True,
                "tests_passed": True,
                "implementation_notes": "Implemented feature",
                "concerns": [],
                "requirements_addressed": ["Feature"],
                "requirements_remaining": [],
            },
            duration_seconds=10.0,
        )

        # Coach approves on turn 1
        coach_result = AgentInvocationResult(
            task_id="TASK-E2E-001",
            turn=1,
            agent_type="coach",
            success=True,
            report={
                "task_id": "TASK-E2E-001",
                "turn": 1,
                "decision": "approve",
                "validation_results": {
                    "requirements_met": ["Feature"],
                    "tests_run": True,
                    "tests_passed": True,
                    "test_command": "pytest",
                    "test_output_summary": "1 test passed",
                    "code_quality": "Good",
                    "edge_cases_covered": [],
                },
                "rationale": "All requirements met",
            },
            duration_seconds=5.0,
        )

        mock_invoker.invoke_player = AsyncMock(return_value=player_result)
        mock_invoker.invoke_coach = AsyncMock(return_value=coach_result)

        # Create orchestrator with mock invoker
        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_dir,
            max_turns=5,
            agent_invoker=mock_invoker,
            enable_pre_loop=False,  # Skip pre-loop for simpler test
        )

        # Execute orchestration
        result = orchestrator.orchestrate(
            task_id="TASK-E2E-001",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
        )

        # Verify result
        assert result.success is True
        assert result.task_id == "TASK-E2E-001"
        assert result.total_turns == 1
        assert result.final_decision == "approved"
        assert result.error is None

        # Verify worktree preserved
        assert result.worktree is not None

    def test_complete_autobuild_with_delegation_feedback(self, tmp_path, mock_coach_validator):
        """Test AutoBuild with task-work delegation (feedback path)."""
        # Setup mock repository
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir, check=True, capture_output=True
        )

        # Create initial commit
        readme = repo_dir / "README.md"
        readme.write_text("# Test Repo", encoding='utf-8')
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir, check=True, capture_output=True
        )

        # Create task file
        task_dir = repo_dir / "tasks" / "design_approved"
        task_dir.mkdir(parents=True)
        task_file = task_dir / "TASK-FEEDBACK-001.md"
        task_file.write_text("""---
id: TASK-FEEDBACK-001
title: Feedback Test Task
status: design_approved
complexity: 5
---

# Feedback Test Task
""", encoding='utf-8')

        # Create implementation plan
        plan_dir = repo_dir / ".claude" / "task-plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "TASK-FEEDBACK-001-implementation-plan.md"
        plan_file.write_text("""# Implementation Plan

Valid plan content.

## Steps
1. Step one
""", encoding='utf-8')

        # Mock AgentInvoker for 2-turn workflow
        mock_invoker = Mock()

        # Turn 1: Player implements, Coach gives feedback
        player_result_1 = AgentInvocationResult(
            task_id="TASK-FEEDBACK-001",
            turn=1,
            agent_type="player",
            success=True,
            report={
                "task_id": "TASK-FEEDBACK-001",
                "turn": 1,
                "files_modified": [],
                "files_created": ["src/feature.py"],
                "tests_written": ["tests/test_feature.py"],
                "tests_run": True,
                "tests_passed": True,
                "implementation_notes": "Initial implementation",
                "concerns": [],
                "requirements_addressed": ["Basic feature"],
                "requirements_remaining": ["Error handling"],
            },
            duration_seconds=10.0,
        )

        coach_result_1 = AgentInvocationResult(
            task_id="TASK-FEEDBACK-001",
            turn=1,
            agent_type="coach",
            success=True,
            report={
                "task_id": "TASK-FEEDBACK-001",
                "turn": 1,
                "decision": "feedback",
                "issues": [
                    {
                        "type": "missing_requirement",
                        "severity": "major",
                        "description": "Missing error handling",
                        "requirement": "Error handling",
                        "suggestion": "Add try-catch blocks",
                    }
                ],
                "rationale": "Need error handling",
            },
            duration_seconds=5.0,
        )

        # Turn 2: Player addresses feedback, Coach approves
        player_result_2 = AgentInvocationResult(
            task_id="TASK-FEEDBACK-001",
            turn=2,
            agent_type="player",
            success=True,
            report={
                "task_id": "TASK-FEEDBACK-001",
                "turn": 2,
                "files_modified": ["src/feature.py"],
                "files_created": [],
                "tests_written": [],
                "tests_run": True,
                "tests_passed": True,
                "implementation_notes": "Added error handling",
                "concerns": [],
                "requirements_addressed": ["Error handling"],
                "requirements_remaining": [],
            },
            duration_seconds=8.0,
        )

        coach_result_2 = AgentInvocationResult(
            task_id="TASK-FEEDBACK-001",
            turn=2,
            agent_type="coach",
            success=True,
            report={
                "task_id": "TASK-FEEDBACK-001",
                "turn": 2,
                "decision": "approve",
                "validation_results": {
                    "requirements_met": ["Basic feature", "Error handling"],
                    "tests_run": True,
                    "tests_passed": True,
                    "test_command": "pytest",
                    "test_output_summary": "All tests passed",
                    "code_quality": "Good",
                    "edge_cases_covered": ["Error cases"],
                },
                "rationale": "All requirements met",
            },
            duration_seconds=5.0,
        )

        mock_invoker.invoke_player = AsyncMock(
            side_effect=[player_result_1, player_result_2]
        )
        mock_invoker.invoke_coach = AsyncMock(
            side_effect=[coach_result_1, coach_result_2]
        )

        # Create orchestrator
        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_dir,
            max_turns=5,
            agent_invoker=mock_invoker,
            enable_pre_loop=False,
        )

        # Execute
        result = orchestrator.orchestrate(
            task_id="TASK-FEEDBACK-001",
            requirements="Implement feature with error handling",
            acceptance_criteria=["Feature works", "Error handling"],
        )

        # Verify
        assert result.success is True
        assert result.total_turns == 2
        assert result.final_decision == "approved"

        # Verify turn history
        assert len(result.turn_history) == 2
        assert result.turn_history[0].decision == "feedback"
        assert result.turn_history[1].decision == "approve"


# ============================================================================
# TestFeedbackFormatting - Feedback File Tests
# ============================================================================


@pytest.mark.integration
class TestFeedbackFormatting:
    """Test feedback file creation and formatting."""

    def test_write_coach_feedback_creates_file(self, mock_worktree):
        """Verify _write_coach_feedback creates properly formatted JSON file."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            use_task_work_delegation=True,
        )

        feedback = {
            "task_id": "TASK-TEST-001",
            "turn": 1,
            "decision": "feedback",
            "issues": [
                {
                    "type": "missing_requirement",
                    "severity": "critical",
                    "description": "Missing authentication",
                    "suggestion": "Add auth middleware",
                }
            ],
            "rationale": "Auth required",
        }

        path = invoker._write_coach_feedback("TASK-TEST-001", 2, feedback)

        assert path.exists()
        with open(path) as f:
            written = json.load(f)

        assert written["turn"] == 2
        assert written["feedback_from_turn"] == 1
        assert len(written["must_fix"]) == 1  # critical severity -> must_fix

    def test_format_feedback_for_prompt(self, mock_worktree):
        """Verify format_feedback_for_prompt creates readable markdown."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            use_task_work_delegation=True,
        )

        feedback = {
            "turn": 2,
            "feedback_from_turn": 1,
            "feedback_summary": "Improvements needed",
            "must_fix": [
                {
                    "issue": "Missing error handling",
                    "location": "src/feature.py:42",
                    "suggestion": "Add try-catch",
                }
            ],
            "should_fix": [
                {
                    "issue": "Code style",
                    "location": "src/feature.py:10",
                    "suggestion": "Use snake_case",
                }
            ],
            "validation_results": {
                "tests_passed": True,
                "test_output_summary": "5 tests passed",
            },
        }

        formatted = invoker.format_feedback_for_prompt(feedback)

        assert "## Coach Feedback from Turn 1" in formatted
        assert "MUST FIX" in formatted
        assert "SHOULD FIX" in formatted
        assert "Missing error handling" in formatted
        assert "Code style" in formatted

    def test_load_coach_feedback(self, mock_worktree):
        """Verify load_coach_feedback reads feedback correctly."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            use_task_work_delegation=True,
        )

        # Create feedback file
        feedback_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"
        feedback_file = feedback_dir / "coach_feedback_for_turn_2.json"
        feedback_file.write_text(json.dumps({
            "turn": 2,
            "feedback_from_turn": 1,
            "feedback_summary": "Test feedback",
            "must_fix": [],
            "should_fix": [],
            "validation_results": {},
            "raw_feedback": "",
        }), encoding='utf-8')

        feedback = invoker.load_coach_feedback("TASK-TEST-001", 2)

        assert feedback is not None
        assert feedback["turn"] == 2
        assert feedback["feedback_summary"] == "Test feedback"

    def test_load_coach_feedback_missing_returns_none(self, mock_worktree):
        """Verify load_coach_feedback returns None for missing file."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            use_task_work_delegation=True,
        )

        feedback = invoker.load_coach_feedback("TASK-NONEXISTENT", 1)

        assert feedback is None


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
