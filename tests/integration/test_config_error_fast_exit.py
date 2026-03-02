"""
Integration Tests for Configuration Error Fast-Exit (TASK-ABFIX-003)

Exercises the integration seam: AutoBuild._loop_phase → CoachValidator.validate →
TurnRecord.is_configuration_error → fast-exit without retry loop.

Scenarios:
    1. Invalid task_type causes immediate exit (not 3-turn stall)
    2. Configuration error propagates through TurnRecord to OrchestrationResult
    3. Normal feedback still enters the feedback loop (regression guard)
    4. Pollution detection is NOT triggered by config errors (tests never ran)

Coverage Target: >=80%
Test Count: 5 tests

Run with:
    pytest tests/integration/test_config_error_fast_exit.py -v
"""

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
    DEFAULT_SDK_TIMEOUT,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    CoachValidationResult,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree(tmp_path):
    """Create a mock Worktree."""
    wt = Mock(spec=Worktree)
    wt.task_id = "TASK-CFG-001"
    wt.path = tmp_path / "worktree"
    wt.path.mkdir(parents=True, exist_ok=True)
    wt.branch_name = "autobuild/TASK-CFG-001"
    wt.base_branch = "main"
    return wt


@pytest.fixture
def mock_progress_display():
    """Mock ProgressDisplay as context manager."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.console = Mock()
    display.console.print = Mock()
    return display


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Mock WorktreeManager."""
    mgr = Mock()
    mgr.create.return_value = mock_worktree
    mgr.preserve_on_failure.return_value = None
    mgr.worktrees_dir = mock_worktree.path.parent
    return mgr


def _make_player_result(
    task_id: str = "TASK-CFG-001",
    turn: int = 1,
    success: bool = True,
) -> AgentInvocationResult:
    """Build a minimal Player result."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=success,
        report={
            "task_id": task_id,
            "turn": turn,
            "files_created": ["src/main.py"],
            "tests_passed": success,
        },
        duration_seconds=5.0,
    )


def _make_config_error_coach_result(
    task_id: str = "TASK-CFG-001",
    turn: int = 1,
    invalid_type: str = "enhancement",
) -> AgentInvocationResult:
    """Build a Coach result that signals a configuration error (invalid task_type)."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "task_id": task_id,
            "turn": turn,
            "decision": "feedback",
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "invalid_task_type",
                    "description": (
                        f"Invalid task_type value: {invalid_type}. "
                        "Must be one of: feature, scaffolding, infrastructure, "
                        "refactor, bugfix, documentation, testing, integration"
                    ),
                }
            ],
            "rationale": f"Invalid task type: {invalid_type}",
            "is_configuration_error": True,
        },
        duration_seconds=2.0,
    )


def _make_normal_feedback_coach_result(
    task_id: str = "TASK-CFG-001",
    turn: int = 1,
) -> AgentInvocationResult:
    """Build a normal feedback Coach result (NOT a config error)."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "task_id": task_id,
            "turn": turn,
            "decision": "feedback",
            "issues": [
                {
                    "severity": "minor",
                    "category": "code_quality",
                    "description": "Add more test coverage",
                }
            ],
            "rationale": "Implementation needs more test coverage",
        },
        duration_seconds=3.0,
    )


def _make_approve_coach_result(
    task_id: str = "TASK-CFG-001",
    turn: int = 1,
) -> AgentInvocationResult:
    """Build an approve Coach result."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "task_id": task_id,
            "turn": turn,
            "decision": "approve",
            "rationale": "All requirements met",
        },
        duration_seconds=3.0,
    )


# ============================================================================
# Tests: Config Error Fast-Exit
# ============================================================================


@pytest.mark.integration
class TestConfigErrorFastExit:
    """Integration tests for configuration error detection and fast-exit."""

    def test_invalid_task_type_causes_immediate_exit(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that when Coach detects an invalid task_type, the loop exits
        after exactly 1 turn with 'configuration_error' decision.

        This prevents the 3-turn stall where Player retries futilely.

        The CoachValidator catches invalid task_type ("enhancement") during
        _resolve_task_type and returns a configuration error result directly,
        without needing the SDK fallback path.
        """
        mock_invoker = Mock()
        mock_invoker.invoke_player = AsyncMock(return_value=_make_player_result())
        mock_invoker.invoke_coach = AsyncMock()  # Fallback, should not be reached
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            max_turns=5,
            agent_invoker=mock_invoker,
            progress_display=mock_progress_display,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=False,
            enable_checkpoints=False,
            enable_context=False,
        )

        turn_history, decision = orchestrator._loop_phase(
            task_id="TASK-CFG-001",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
            worktree=mock_worktree,
            task_type="enhancement",  # Invalid type triggers CoachValidator config error
        )

        # Should exit after exactly 1 turn
        assert decision == "configuration_error"
        assert len(turn_history) == 1
        assert turn_history[0].is_configuration_error is True
        # Player invoked once
        assert mock_invoker.invoke_player.call_count == 1

    def test_config_error_propagates_to_orchestration_result(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that configuration_error propagates through the full
        orchestrate() flow to the OrchestrationResult.
        """
        config_error_report = _make_config_error_coach_result()

        mock_invoker = Mock()
        mock_invoker.invoke_player = AsyncMock(return_value=_make_player_result())
        mock_invoker.invoke_coach = AsyncMock(return_value=config_error_report)
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            max_turns=5,
            agent_invoker=mock_invoker,
            progress_display=mock_progress_display,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=False,
            enable_checkpoints=False,
            enable_context=False,
        )

        # Patch CoachValidator.validate to force SDK fallback (invoke_coach mock)
        with patch.object(CoachValidator, 'validate', side_effect=Exception("force SDK fallback")):
            result = orchestrator.orchestrate(
                task_id="TASK-CFG-001",
                requirements="Implement feature",
                acceptance_criteria=["Feature works"],
            )

        assert result.success is False
        assert result.final_decision == "configuration_error"
        assert result.total_turns == 1
        assert result.error is not None
        assert "configuration" in result.error.lower() or "task_type" in result.error.lower()

    def test_normal_feedback_still_enters_retry_loop(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Regression guard: normal feedback (not config error) should
        still enter the retry loop and not fast-exit.
        """
        mock_invoker = Mock()
        mock_invoker.invoke_player = AsyncMock(return_value=_make_player_result())
        # Turn 1: feedback, Turn 2: approve
        # CoachValidator will fail (no task_work_results.json) and fall back to invoke_coach
        mock_invoker.invoke_coach = AsyncMock(
            side_effect=[
                _make_normal_feedback_coach_result(turn=1),
                _make_approve_coach_result(turn=2),
            ],
        )
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            max_turns=5,
            agent_invoker=mock_invoker,
            progress_display=mock_progress_display,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=False,
            enable_checkpoints=False,
            enable_context=False,
        )

        # Patch CoachValidator.validate to force SDK fallback (invoke_coach mock)
        with patch.object(CoachValidator, 'validate', side_effect=Exception("force SDK fallback")):
            turn_history, decision = orchestrator._loop_phase(
                task_id="TASK-CFG-001",
                requirements="Implement feature",
                acceptance_criteria=["Feature works"],
                worktree=mock_worktree,
            )

        # Should complete after 2 turns (feedback → approve)
        assert decision == "approved"
        assert len(turn_history) == 2
        # No turn should have is_configuration_error set
        for record in turn_history:
            assert record.is_configuration_error is False

    def test_config_error_does_not_create_pollution_checkpoint(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that configuration errors don't create checkpoints
        or trigger pollution detection (since tests were never run).
        """
        mock_invoker = Mock()
        mock_invoker.invoke_player = AsyncMock(return_value=_make_player_result())
        mock_invoker.invoke_coach = AsyncMock()  # Should not be reached (CoachValidator handles it)
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        mock_checkpoint_mgr = Mock()
        mock_checkpoint_mgr.create_checkpoint = Mock()
        mock_checkpoint_mgr.should_rollback = Mock(return_value=False)

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            max_turns=5,
            agent_invoker=mock_invoker,
            progress_display=mock_progress_display,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=False,
            enable_checkpoints=True,
            enable_context=False,
        )
        # Inject mock checkpoint manager
        orchestrator._checkpoint_manager = mock_checkpoint_mgr

        turn_history, decision = orchestrator._loop_phase(
            task_id="TASK-CFG-001",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
            worktree=mock_worktree,
            task_type="enhancement",  # Invalid type triggers CoachValidator config error
        )

        assert decision == "configuration_error"
        # Checkpoint should NOT have been created for config error turn
        mock_checkpoint_mgr.create_checkpoint.assert_not_called()
        # Pollution detection should NOT have been triggered
        mock_checkpoint_mgr.should_rollback.assert_not_called()


# ============================================================================
# Tests: CoachValidator Task Type Resolution Integration
# ============================================================================


@pytest.mark.integration
class TestCoachValidatorTaskTypeIntegration:
    """Test CoachValidator task type resolution with actual validator."""

    def test_invalid_task_type_produces_config_error_result(self, tmp_path):
        """
        Verify that CoachValidator.validate() returns a result with
        is_configuration_error=True when task_type is invalid.

        This tests the CoachValidator directly (not through AutoBuild),
        exercising the real _resolve_task_type → _feedback_result path.
        """
        validator = CoachValidator(
            worktree_path=str(tmp_path),
            task_id="TASK-CFG-001",
            test_command="pytest tests/ -v",
        )

        result = validator.validate(
            task_id="TASK-CFG-001",
            turn=1,
            task={
                "task_type": "enhancement",  # Invalid type
                "acceptance_criteria": ["Feature works"],
            },
        )

        assert result.is_configuration_error is True
        assert result.decision == "feedback"
        # Should have an issue with category "invalid_task_type"
        config_issues = [
            i for i in result.issues
            if i.get("category") == "invalid_task_type"
        ]
        assert len(config_issues) == 1
        assert "enhancement" in config_issues[0]["description"]


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
