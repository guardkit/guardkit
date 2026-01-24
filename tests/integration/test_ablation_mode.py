"""
Integration Tests for Ablation Mode

Tests the ablation testing mode (--ablation) that demonstrates the system is
non-functional without Coach feedback, validating the Block research finding
about adversarial cooperation necessity.

Test Coverage:
    - Ablation mode skips Coach validation
    - Ablation mode auto-approves after Player implementation
    - Ablation mode is tracked in metrics
    - Warning banner displays when ablation mode is active

Architecture:
    - Uses mock fixtures and temporary directories
    - Mocks AgentInvoker to avoid actual SDK calls
    - Tests AutoBuildOrchestrator with ablation_mode=True

Run with:
    pytest tests/integration/test_ablation_mode.py -v
    pytest tests/integration/test_ablation_mode.py -v --cov=guardkit/orchestrator

Coverage Target: >=85%
Test Count: 5 tests
"""

import json
import pytest
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

# Import components under test
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
)
from guardkit.worktrees import WorktreeManager, Worktree


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree_with_task(tmp_path):
    """
    Create a mock worktree structure with task file and directories.
    Initializes as a git repository to satisfy WorktreeManager validation.

    Returns:
        Path: Path to worktree root
    """
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Initialize as git repository
    import subprocess
    subprocess.run(["git", "init"], cwd=worktree, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=worktree, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=worktree, check=True, capture_output=True)

    # Create task directories
    backlog_dir = worktree / "tasks" / "backlog"
    backlog_dir.mkdir(parents=True)

    in_progress_dir = worktree / "tasks" / "in_progress"
    in_progress_dir.mkdir(parents=True)

    # Create task file in backlog state
    task_file = backlog_dir / "TASK-ABLATION-001-test-ablation.md"
    task_file.write_text("""---
id: TASK-ABLATION-001
title: Test Ablation Mode Task
status: backlog
created: 2026-01-24T10:00:00Z
priority: medium
complexity: 3
---

# Test Ablation Mode Task

## Description

Simple task for testing ablation mode behavior.

## Requirements

Implement a basic function that adds two numbers.

## Acceptance Criteria

- [ ] Function accepts two integer parameters
- [ ] Function returns sum of parameters
- [ ] Function has unit tests
""")

    # Create initial commit
    subprocess.run(["git", "add", "."], cwd=worktree, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=worktree, check=True, capture_output=True)

    return worktree


@pytest.fixture
def mock_agent_invoker_success():
    """
    Mock AgentInvoker that returns successful Player results.

    Returns:
        MagicMock: Mocked AgentInvoker
    """
    mock_invoker = MagicMock(spec=AgentInvoker)

    # Mock successful Player invocation using AsyncMock with dynamic return value
    async def mock_invoke_player(task_id, turn, requirements, feedback=None, max_turns=5, **kwargs):
        return AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="player",
            success=True,
            report={
                "task_id": task_id,
                "turn": turn,
                "files_modified": ["src/calculator.py"],
                "files_created": ["tests/test_calculator.py"],
                "tests_written": ["test_add_positive", "test_add_negative", "test_add_zero"],  # List of test names
                "tests_run": 3,
                "tests_passed": 3,
                "test_output_summary": "All tests passed",
                "implementation_notes": "Implemented add function",
                "concerns": [],
                "requirements_addressed": ["Function accepts two integers", "Returns sum"],
                "requirements_remaining": [],
            },
            duration_seconds=5.0,
            error=None,
        )

    mock_invoker.invoke_player = mock_invoke_player

    # Coach should never be called in ablation mode
    mock_invoker.invoke_coach = AsyncMock(
        side_effect=AssertionError("Coach should not be invoked in ablation mode")
    )

    return mock_invoker


# ============================================================================
# 1. Ablation Mode Behavior Tests (3 tests)
# ============================================================================


def test_ablation_mode_skips_coach_validation(mock_worktree_with_task, mock_agent_invoker_success):
    """
    Test that ablation mode skips Coach validation entirely.

    Expected behavior:
    - Player runs normally
    - Coach is never invoked
    - Turn auto-approves
    """
    # Create orchestrator with ablation mode enabled
    orchestrator = AutoBuildOrchestrator(
        repo_root=mock_worktree_with_task,
        max_turns=3,
        ablation_mode=True,  # Enable ablation mode
        enable_pre_loop=False,  # Skip pre-loop for this test
        agent_invoker=mock_agent_invoker_success,
    )

    # Execute orchestration
    result = orchestrator.orchestrate(
        task_id="TASK-ABLATION-001",
        requirements="Implement a basic add function",
        acceptance_criteria=[
            "Function accepts two integers",
            "Function returns sum",
            "Function has unit tests",
        ],
    )

    # Verify ablation mode is tracked
    assert result.ablation_mode is True

    # Verify success (auto-approved)
    assert result.success is True
    assert result.final_decision == "approved"

    # Verify exactly one turn (auto-approved immediately)
    assert result.total_turns == 1

    # Verify turn record shows auto-approval with no Coach
    turn = result.turn_history[0]
    assert turn.decision == "approve"
    assert turn.coach_result is None  # Coach was not invoked
    assert turn.player_result is not None  # Player was invoked


def test_ablation_mode_auto_approves_after_player(mock_worktree_with_task, mock_agent_invoker_success):
    """
    Test that ablation mode auto-approves immediately after Player implementation.

    Expected behavior:
    - Player implements
    - No Coach validation
    - Immediate approval (no iterations)
    """
    orchestrator = AutoBuildOrchestrator(
        repo_root=mock_worktree_with_task,
        max_turns=5,  # Allow up to 5 turns
        ablation_mode=True,
        enable_pre_loop=False,
        agent_invoker=mock_agent_invoker_success,
    )

    result = orchestrator.orchestrate(
        task_id="TASK-ABLATION-001",
        requirements="Implement add function",
        acceptance_criteria=["Returns sum of two integers"],
    )

    # Should complete in exactly 1 turn (no iterations needed)
    assert result.total_turns == 1
    assert result.success is True

    # Verify no Coach invocation in turn history
    for turn in result.turn_history:
        assert turn.coach_result is None


def test_ablation_mode_tracking_in_result(mock_worktree_with_task, mock_agent_invoker_success):
    """
    Test that ablation mode status is tracked in OrchestrationResult.

    Expected behavior:
    - result.ablation_mode = True when enabled
    - result.ablation_mode = False when disabled
    """
    # Test with ablation mode enabled
    orchestrator_ablation = AutoBuildOrchestrator(
        repo_root=mock_worktree_with_task,
        max_turns=3,
        ablation_mode=True,
        enable_pre_loop=False,
        agent_invoker=mock_agent_invoker_success,
    )

    result_ablation = orchestrator_ablation.orchestrate(
        task_id="TASK-ABLATION-001",
        requirements="Test task",
        acceptance_criteria=["Criterion 1"],
    )

    assert result_ablation.ablation_mode is True

    # Test with ablation mode disabled (normal mode)
    # Note: We can't test normal mode without mocking Coach as well,
    # so we just verify the field exists and defaults to False
    orchestrator_normal = AutoBuildOrchestrator(
        repo_root=mock_worktree_with_task,
        max_turns=3,
        ablation_mode=False,  # Explicitly disabled
        enable_pre_loop=False,
    )

    # Verify orchestrator has ablation_mode set to False
    assert orchestrator_normal.ablation_mode is False


# ============================================================================
# 2. CLI Integration Tests (2 tests)
# ============================================================================


def test_ablation_flag_passed_to_orchestrator():
    """
    Test that --ablation CLI flag correctly initializes orchestrator.

    This is a unit test for CLI → Orchestrator parameter passing.
    """
    from guardkit.cli.autobuild import task as task_command
    from click.testing import CliRunner

    runner = CliRunner()

    # Mock SDK check to avoid import error
    with patch('guardkit.cli.autobuild._check_sdk_available', return_value=True):
        # Mock the orchestrator to verify ablation_mode parameter
        with patch('guardkit.cli.autobuild.AutoBuildOrchestrator') as mock_orch_class:
            mock_orch_instance = MagicMock()
            mock_orch_instance.orchestrate.return_value = MagicMock(
                success=True,
                total_turns=1,
                final_decision="approved",
                turn_history=[],
                worktree=MagicMock(path="/tmp/test", branch_name="test", base_branch="main", task_id="TASK-001"),
                error=None,
                ablation_mode=True,
            )
            mock_orch_class.return_value = mock_orch_instance

            # Mock TaskLoader to avoid file system access
            with patch('guardkit.cli.autobuild.TaskLoader.load_task') as mock_loader:
                mock_loader.return_value = {
                    "frontmatter": {},
                    "requirements": "Test",
                    "acceptance_criteria": ["Test"],
                    "file_path": Path("/tmp/test.md"),
                }

                # Run command with --ablation flag
                result = runner.invoke(task_command, ['TASK-001', '--ablation'])

                # Verify orchestrator was initialized with ablation_mode=True
                mock_orch_class.assert_called_once()
                call_kwargs = mock_orch_class.call_args[1]
                assert call_kwargs['ablation_mode'] is True


def test_ablation_warning_banner_displayed():
    """
    Test that ablation mode displays warning banner.

    This verifies the warning is shown to users when ablation mode is active.
    """
    from guardkit.cli.autobuild import task as task_command
    from click.testing import CliRunner

    runner = CliRunner()

    # Mock SDK check to avoid import error
    with patch('guardkit.cli.autobuild._check_sdk_available', return_value=True):
        with patch('guardkit.cli.autobuild.AutoBuildOrchestrator') as mock_orch_class:
            mock_orch_instance = MagicMock()
            mock_orch_instance.orchestrate.return_value = MagicMock(
                success=True,
                total_turns=1,
                final_decision="approved",
                turn_history=[],
                worktree=MagicMock(path="/tmp/test", branch_name="test", base_branch="main", task_id="TASK-001"),
                error=None,
                ablation_mode=True,
            )
            mock_orch_class.return_value = mock_orch_instance

            with patch('guardkit.cli.autobuild.TaskLoader.load_task') as mock_loader:
                mock_loader.return_value = {
                    "frontmatter": {},
                    "requirements": "Test",
                    "acceptance_criteria": ["Test"],
                    "file_path": Path("/tmp/test.md"),
                }

                # Run command with --ablation flag
                result = runner.invoke(task_command, ['TASK-001', '--ablation'])

                # Verify warning banner is in output
                assert "ABLATION MODE ACTIVE" in result.output
                assert "Coach feedback is DISABLED" in result.output
                assert "This mode is for testing only" in result.output


# ============================================================================
# Test Summary
# ============================================================================

"""
Test Summary
============

Ablation Mode Behavior Tests (3 tests):
- test_ablation_mode_skips_coach_validation: Verifies Coach is never invoked
- test_ablation_mode_auto_approves_after_player: Verifies immediate approval
- test_ablation_mode_tracking_in_result: Verifies ablation_mode field tracking

CLI Integration Tests (2 tests):
- test_ablation_flag_passed_to_orchestrator: Verifies --ablation flag propagation
- test_ablation_warning_banner_displayed: Verifies warning banner output

Coverage Target: >=85%
Total Tests: 5
"""
