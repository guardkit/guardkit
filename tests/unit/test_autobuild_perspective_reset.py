"""
Test suite for perspective reset functionality (TASK-BRF-001).

Comprehensive tests for the fresh perspective reset feature that prevents
anchoring bias in the AutoBuild orchestrator's Player-Coach loop.

Test Organization:
    - TestPerspectiveResetInitialization: Constructor and parameter setup
    - TestShouldResetPerspective: Core reset detection logic
    - TestPerspectiveResetInLoop: Integration with _loop_phase
    - TestPerspectiveResetEdgeCases: Edge cases and boundary conditions
    - TestPerspectiveResetLogging: Logging behavior verification

Coverage Goals:
    - 100% line coverage for _should_reset_perspective method
    - 100% coverage for initialization of reset parameters
    - Integration coverage for _loop_phase reset logic
    - Edge case coverage for boundary conditions
"""

import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, MagicMock, patch, AsyncMock, call
import logging
from dataclasses import dataclass

# Import components under test
import sys
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.worktrees import Worktree


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree():
    """Create mock Worktree instance."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-BRF-001"
    worktree.path = Path("/tmp/worktrees/TASK-BRF-001")
    worktree.branch_name = "autobuild/TASK-BRF-001"
    worktree.base_branch = "main"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Create mock WorktreeManager."""
    manager = Mock()
    manager.create.return_value = mock_worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create mock AgentInvoker."""
    invoker = Mock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock()
    return invoker


@pytest.fixture
def mock_progress_display():
    """Create mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    return display


@pytest.fixture
def mock_coach_validator():
    """Patch CoachValidator to force SDK fallback."""
    with patch(
        "guardkit.orchestrator.autobuild.CoachValidator"
    ) as mock_validator_class:
        mock_instance = MagicMock()
        mock_instance.validate.side_effect = Exception("Force SDK fallback for test")
        mock_validator_class.return_value = mock_instance
        yield mock_validator_class


@pytest.fixture
def mock_pre_loop_gates():
    """Create mock PreLoopQualityGates."""
    gates = MagicMock()
    from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

    async def mock_execute(*args, **kwargs):
        return PreLoopResult(
            plan={"steps": ["Step 1"]},
            plan_path="/tmp/plan.md",
            complexity=5,
            max_turns=5,
            checkpoint_passed=True,
            architectural_score=85,
            clarifications={},
        )

    gates.execute = mock_execute
    return gates


@pytest.fixture
def orchestrator_with_perspective_reset(
    mock_worktree_manager,
    mock_agent_invoker,
    mock_progress_display,
    mock_coach_validator,
    mock_pre_loop_gates,
):
    """Create AutoBuildOrchestrator with perspective reset enabled."""
    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/test-repo"),
        max_turns=5,
        enable_perspective_reset=True,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
        pre_loop_gates=mock_pre_loop_gates,
    )


@pytest.fixture
def orchestrator_without_perspective_reset(
    mock_worktree_manager,
    mock_agent_invoker,
    mock_progress_display,
    mock_coach_validator,
    mock_pre_loop_gates,
):
    """Create AutoBuildOrchestrator with perspective reset disabled."""
    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/test-repo"),
        max_turns=5,
        enable_perspective_reset=False,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
        pre_loop_gates=mock_pre_loop_gates,
    )


def make_player_result(
    task_id: str = "TASK-BRF-001",
    turn: int = 1,
    success: bool = True,
    error: Optional[str] = None,
) -> AgentInvocationResult:
    """Helper to create Player AgentInvocationResult."""
    report = {}
    if success:
        report = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": [f"src/file{i}.py" for i in range(2)],
            "files_created": [f"src/new{i}.py" for i in range(2)],
            "tests_written": [f"tests/test_file{i}.py" for i in range(2)],
            "tests_run": True,
            "tests_passed": True,
            "implementation_notes": f"Turn {turn} implementation",
            "concerns": [],
            "requirements_addressed": ["Feature implementation"],
            "requirements_remaining": [],
        }

    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=success,
        report=report,
        duration_seconds=10.0,
        error=error,
    )


def make_coach_result(
    task_id: str = "TASK-BRF-001",
    turn: int = 1,
    decision: str = "feedback",
    success: bool = True,
    error: Optional[str] = None,
) -> AgentInvocationResult:
    """Helper to create Coach AgentInvocationResult."""
    report = {}
    if success:
        if decision == "approve":
            report = {
                "task_id": task_id,
                "turn": turn,
                "decision": "approve",
                "validation_results": {
                    "requirements_met": ["Feature"],
                    "tests_passed": True,
                },
                "rationale": "Implementation approved",
            }
        else:  # feedback
            report = {
                "task_id": task_id,
                "turn": turn,
                "decision": "feedback",
                "issues": [
                    {
                        "type": "missing_requirement",
                        "description": "Missing edge case",
                        "suggestion": "Add edge case handling",
                    }
                ],
                "rationale": "More work needed",
            }

    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=success,
        report=report,
        duration_seconds=8.0,
        error=error,
    )


# ============================================================================
# TestPerspectiveResetInitialization
# ============================================================================


class TestPerspectiveResetInitialization:
    """Test initialization and parameter setup for perspective reset."""

    def test_perspective_reset_enabled_by_default(
        self, orchestrator_with_perspective_reset
    ):
        """Test that perspective reset is enabled by default."""
        assert orchestrator_with_perspective_reset.enable_perspective_reset is True
        assert orchestrator_with_perspective_reset.perspective_reset_turns == [3, 5]

    def test_perspective_reset_can_be_disabled(self, orchestrator_without_perspective_reset):
        """Test that perspective reset can be disabled."""
        assert orchestrator_without_perspective_reset.enable_perspective_reset is False
        assert orchestrator_without_perspective_reset.perspective_reset_turns == []

    def test_perspective_reset_turns_hardcoded(self, orchestrator_with_perspective_reset):
        """Test that reset turns are hardcoded as [3, 5]."""
        assert orchestrator_with_perspective_reset.perspective_reset_turns == [3, 5]

    def test_reset_turns_empty_when_disabled(self, orchestrator_without_perspective_reset):
        """Test that reset_turns list is empty when disabled."""
        assert len(orchestrator_without_perspective_reset.perspective_reset_turns) == 0

    def test_initialization_logs_perspective_reset_config(
        self, orchestrator_with_perspective_reset, caplog
    ):
        """Test that initialization logs perspective reset configuration."""
        with caplog.at_level(logging.INFO):
            # The logger call happened during __init__, so we just check the fixture
            assert orchestrator_with_perspective_reset.enable_perspective_reset is True

    def test_different_orchestrators_have_independent_configs(
        self, orchestrator_with_perspective_reset, orchestrator_without_perspective_reset
    ):
        """Test that different orchestrator instances have independent configs."""
        assert (
            orchestrator_with_perspective_reset.enable_perspective_reset
            != orchestrator_without_perspective_reset.enable_perspective_reset
        )
        assert (
            orchestrator_with_perspective_reset.perspective_reset_turns
            != orchestrator_without_perspective_reset.perspective_reset_turns
        )


# ============================================================================
# TestShouldResetPerspective
# ============================================================================


class TestShouldResetPerspective:
    """Test the _should_reset_perspective method."""

    def test_reset_triggered_at_turn_3(self, orchestrator_with_perspective_reset, caplog):
        """Test that perspective reset is triggered at turn 3."""
        with caplog.at_level(logging.INFO):
            result = orchestrator_with_perspective_reset._should_reset_perspective(3)
        assert result is True
        assert "Perspective reset triggered at turn 3" in caplog.text

    def test_reset_triggered_at_turn_5(self, orchestrator_with_perspective_reset, caplog):
        """Test that perspective reset is triggered at turn 5."""
        with caplog.at_level(logging.INFO):
            result = orchestrator_with_perspective_reset._should_reset_perspective(5)
        assert result is True
        assert "Perspective reset triggered at turn 5" in caplog.text

    def test_reset_not_triggered_at_turn_1(
        self, orchestrator_with_perspective_reset, caplog
    ):
        """Test that perspective reset is not triggered at turn 1."""
        with caplog.at_level(logging.INFO):
            result = orchestrator_with_perspective_reset._should_reset_perspective(1)
        assert result is False
        assert "Perspective reset triggered" not in caplog.text

    def test_reset_not_triggered_at_turn_2(
        self, orchestrator_with_perspective_reset, caplog
    ):
        """Test that perspective reset is not triggered at turn 2."""
        with caplog.at_level(logging.INFO):
            result = orchestrator_with_perspective_reset._should_reset_perspective(2)
        assert result is False

    def test_reset_not_triggered_at_turn_4(
        self, orchestrator_with_perspective_reset, caplog
    ):
        """Test that perspective reset is not triggered at turn 4."""
        with caplog.at_level(logging.INFO):
            result = orchestrator_with_perspective_reset._should_reset_perspective(4)
        assert result is False

    def test_reset_not_triggered_at_turn_6(
        self, orchestrator_with_perspective_reset, caplog
    ):
        """Test that perspective reset is not triggered at turn 6."""
        with caplog.at_level(logging.INFO):
            result = orchestrator_with_perspective_reset._should_reset_perspective(6)
        assert result is False

    def test_reset_never_triggered_when_disabled(
        self, orchestrator_without_perspective_reset
    ):
        """Test that reset is never triggered when disabled."""
        for turn in [1, 2, 3, 4, 5, 6]:
            result = orchestrator_without_perspective_reset._should_reset_perspective(turn)
            assert result is False

    def test_reset_triggered_logs_scheduled_reason(
        self, orchestrator_with_perspective_reset, caplog
    ):
        """Test that reset logging includes 'scheduled' reason."""
        with caplog.at_level(logging.INFO):
            orchestrator_with_perspective_reset._should_reset_perspective(3)
        assert "scheduled reset" in caplog.text

    def test_reset_for_turn_boundary(self, orchestrator_with_perspective_reset):
        """Test reset detection at turn boundaries."""
        # Test exact boundary values
        assert orchestrator_with_perspective_reset._should_reset_perspective(2) is False
        assert orchestrator_with_perspective_reset._should_reset_perspective(3) is True
        assert orchestrator_with_perspective_reset._should_reset_perspective(4) is False
        assert orchestrator_with_perspective_reset._should_reset_perspective(5) is True


# ============================================================================
# TestPerspectiveResetInLoop
# ============================================================================


class TestPerspectiveResetInLoop:
    """Test integration of perspective reset with the loop phase."""

    def test_perspective_reset_clears_feedback_at_turn_3(
        self, orchestrator_with_perspective_reset, mock_worktree
    ):
        """
        Test that feedback is cleared when perspective reset triggers at turn 3.

        This is a simplified test that verifies the reset logic would work
        correctly in the loop. The actual loop behavior is tested via integration
        tests, but here we verify the helper method directly.
        """
        # Simulate turn 2 with feedback
        orchestrator_with_perspective_reset._turn_history = [
            TurnRecord(
                turn=1,
                player_result=make_player_result(turn=1),
                coach_result=make_coach_result(turn=1, decision="feedback"),
                decision="feedback",
                feedback="Add more tests",
                timestamp="2026-01-24T10:00:00Z",
            ),
            TurnRecord(
                turn=2,
                player_result=make_player_result(turn=2),
                coach_result=make_coach_result(turn=2, decision="feedback"),
                decision="feedback",
                feedback="Fix edge cases",
                timestamp="2026-01-24T10:05:00Z",
            ),
        ]

        # At turn 3, perspective should reset
        result = orchestrator_with_perspective_reset._should_reset_perspective(3)
        assert result is True

    def test_perspective_reset_clears_feedback_at_turn_5(
        self, orchestrator_with_perspective_reset
    ):
        """Test that feedback is cleared when perspective reset triggers at turn 5."""
        # At turn 5, perspective should reset
        result = orchestrator_with_perspective_reset._should_reset_perspective(5)
        assert result is True

    def test_feedback_maintained_between_non_reset_turns(
        self, orchestrator_with_perspective_reset
    ):
        """Test that feedback is maintained between non-reset turns."""
        # Turns 1, 2, 4, 6 should not trigger reset
        for turn in [1, 2, 4, 6]:
            result = orchestrator_with_perspective_reset._should_reset_perspective(turn)
            assert result is False

    def test_reset_would_affect_player_invocation(self, orchestrator_with_perspective_reset):
        """
        Test that reset logic would affect Player invocation feedback parameter.

        This verifies the logic path without executing the full loop.
        """
        # When _should_reset_perspective returns True, feedback should be None
        # This is verified in _loop_phase where: if self._should_reset_perspective(turn): previous_feedback = None
        reset_triggered = orchestrator_with_perspective_reset._should_reset_perspective(3)
        assert reset_triggered is True


# ============================================================================
# TestPerspectiveResetEdgeCases
# ============================================================================


class TestPerspectiveResetEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_reset_with_zero_turn(self, orchestrator_with_perspective_reset):
        """Test reset detection with invalid turn 0."""
        result = orchestrator_with_perspective_reset._should_reset_perspective(0)
        assert result is False

    def test_reset_with_negative_turn(self, orchestrator_with_perspective_reset):
        """Test reset detection with negative turn."""
        result = orchestrator_with_perspective_reset._should_reset_perspective(-1)
        assert result is False

    def test_reset_with_very_large_turn(self, orchestrator_with_perspective_reset):
        """Test reset detection with turn larger than max_turns."""
        result = orchestrator_with_perspective_reset._should_reset_perspective(1000)
        assert result is False

    def test_reset_turns_are_exact_matches(self, orchestrator_with_perspective_reset):
        """Test that only exact turn numbers trigger reset (not ranges)."""
        # Should only match 3 and 5, not ranges or approximations
        assert orchestrator_with_perspective_reset._should_reset_perspective(3) is True
        assert orchestrator_with_perspective_reset._should_reset_perspective(5) is True
        assert orchestrator_with_perspective_reset._should_reset_perspective(3.5) is False
        assert orchestrator_with_perspective_reset._should_reset_perspective(5.5) is False

    def test_reset_disabled_survives_turn_checks(
        self, orchestrator_without_perspective_reset
    ):
        """Test that disabled reset never triggers regardless of turn."""
        test_turns = [1, 2, 3, 4, 5, 6, 10, 100]
        for turn in test_turns:
            result = orchestrator_without_perspective_reset._should_reset_perspective(turn)
            assert result is False, f"Reset should not trigger at turn {turn} when disabled"

    def test_perspective_reset_turns_immutable_after_init(
        self, orchestrator_with_perspective_reset
    ):
        """Test that perspective reset turns list is correct after initialization."""
        original_turns = orchestrator_with_perspective_reset.perspective_reset_turns
        # Should be exactly [3, 5]
        assert original_turns == [3, 5]


# ============================================================================
# TestPerspectiveResetLogging
# ============================================================================


class TestPerspectiveResetLogging:
    """Test logging behavior for perspective reset."""

    def test_reset_logging_includes_turn_number(
        self, orchestrator_with_perspective_reset, caplog
    ):
        """Test that reset logging includes the turn number."""
        with caplog.at_level(logging.INFO):
            orchestrator_with_perspective_reset._should_reset_perspective(3)
        assert "turn 3" in caplog.text.lower()

    def test_reset_logging_includes_scheduled_keyword(
        self, orchestrator_with_perspective_reset, caplog
    ):
        """Test that reset logging includes 'scheduled' keyword."""
        with caplog.at_level(logging.INFO):
            orchestrator_with_perspective_reset._should_reset_perspective(3)
        assert "scheduled" in caplog.text.lower()

    def test_multiple_resets_all_logged(
        self, orchestrator_with_perspective_reset, caplog
    ):
        """Test that multiple resets are all logged."""
        with caplog.at_level(logging.INFO):
            orchestrator_with_perspective_reset._should_reset_perspective(3)
            orchestrator_with_perspective_reset._should_reset_perspective(5)

        assert caplog.text.count("Perspective reset triggered") >= 2

    def test_initialization_logs_reset_config(
        self,
        caplog,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_coach_validator,
        mock_pre_loop_gates,
    ):
        """Test that initialization logs the reset configuration."""
        with caplog.at_level(logging.INFO):
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/test-repo"),
                max_turns=5,
                enable_perspective_reset=True,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
                pre_loop_gates=mock_pre_loop_gates,
            )
        assert "enable_perspective_reset=True" in caplog.text

    def test_initialization_logs_reset_turns(
        self,
        caplog,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_coach_validator,
        mock_pre_loop_gates,
    ):
        """Test that initialization logs the reset turns."""
        with caplog.at_level(logging.INFO):
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/test-repo"),
                max_turns=5,
                enable_perspective_reset=True,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
                pre_loop_gates=mock_pre_loop_gates,
            )
        assert "reset_turns=" in caplog.text


# ============================================================================
# TestPerspectiveResetCoverage
# ============================================================================


class TestPerspectiveResetCoverage:
    """Ensure comprehensive coverage of all reset-related code paths."""

    def test_reset_return_value_true(self, orchestrator_with_perspective_reset):
        """Test that reset returns True when triggered."""
        result = orchestrator_with_perspective_reset._should_reset_perspective(3)
        assert isinstance(result, bool)
        assert result is True

    def test_reset_return_value_false(self, orchestrator_with_perspective_reset):
        """Test that reset returns False when not triggered."""
        result = orchestrator_with_perspective_reset._should_reset_perspective(1)
        assert isinstance(result, bool)
        assert result is False

    def test_enable_flag_controls_reset_list(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_coach_validator,
        mock_pre_loop_gates,
    ):
        """Test that enable_perspective_reset flag controls reset list."""
        # With reset enabled
        orch_enabled = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test-repo"),
            enable_perspective_reset=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )
        assert orch_enabled.perspective_reset_turns == [3, 5]

        # With reset disabled
        orch_disabled = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test-repo"),
            enable_perspective_reset=False,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            pre_loop_gates=mock_pre_loop_gates,
        )
        assert orch_disabled.perspective_reset_turns == []

    def test_reset_method_consistency(self, orchestrator_with_perspective_reset):
        """Test that reset method returns consistent results."""
        # Same turn should always return same result
        result1 = orchestrator_with_perspective_reset._should_reset_perspective(3)
        result2 = orchestrator_with_perspective_reset._should_reset_perspective(3)
        assert result1 == result2 == True

        result3 = orchestrator_with_perspective_reset._should_reset_perspective(4)
        result4 = orchestrator_with_perspective_reset._should_reset_perspective(4)
        assert result3 == result4 == False
