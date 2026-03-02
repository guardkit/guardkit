"""
Integration Tests for Per-Turn Timeout Budget (TASK-ABFIX-004)

Exercises the integration seam: FeatureOrchestrator → AutoBuild → AgentInvoker → Coach
to verify that timeout budgets flow correctly through the system.

Scenarios:
    1. Multi-turn task where turn 1 consumes ~60% of budget; turn 2 receives correct remaining
    2. Coach grace period granted when Player succeeds near timeout boundary
    3. SDK timeout is capped at remaining budget
    4. Budget exhaustion exits gracefully (not via asyncio.TimeoutError)

Coverage Target: >=80%
Test Count: 6 tests

Run with:
    pytest tests/integration/test_timeout_budget.py -v
"""

import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
    COACH_GRACE_PERIOD_SECONDS,
    MIN_TURN_BUDGET_SECONDS,
)
from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
    DEFAULT_SDK_TIMEOUT,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree(tmp_path):
    """Create a mock Worktree for testing."""
    wt = Mock(spec=Worktree)
    wt.task_id = "TASK-BUDGET-001"
    wt.path = tmp_path / "worktree"
    wt.path.mkdir(parents=True, exist_ok=True)
    wt.branch_name = "autobuild/TASK-BUDGET-001"
    wt.base_branch = "main"
    return wt


@pytest.fixture
def mock_progress_display():
    """Mock ProgressDisplay that acts as context manager."""
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
    """Mock WorktreeManager that returns the mock worktree."""
    mgr = Mock()
    mgr.create.return_value = mock_worktree
    mgr.preserve_on_failure.return_value = None
    mgr.worktrees_dir = mock_worktree.path.parent
    return mgr


def _make_player_result(
    task_id: str = "TASK-BUDGET-001",
    turn: int = 1,
    success: bool = True,
) -> AgentInvocationResult:
    """Helper: build a minimal Player result."""
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


def _make_coach_result(
    task_id: str = "TASK-BUDGET-001",
    turn: int = 1,
    decision: str = "approve",
) -> AgentInvocationResult:
    """Helper: build a minimal Coach result."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "task_id": task_id,
            "turn": turn,
            "decision": decision,
            "rationale": "Implementation meets requirements",
        },
        duration_seconds=3.0,
    )


# ============================================================================
# Tests: Per-Turn Budget Tracking Through the Loop
# ============================================================================


@pytest.mark.integration
class TestTimeoutBudgetIntegration:
    """Integration tests for timeout budget flowing through AutoBuild loop."""

    def test_remaining_budget_decreases_across_turns(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that remaining budget is correctly tracked across multiple turns.

        Simulates a multi-turn task where each turn consumes time.
        After turn 1, remaining budget should be reduced by elapsed time.

        Budget flows: _loop_phase → _execute_turn → _invoke_coach_safely → invoke_coach
        (via CoachValidator fallback path), so we capture remaining_budget from Coach.
        """
        coach_budgets = []

        async def slow_player(*args, **kwargs):
            """Simulate Player taking some time."""
            time.sleep(0.3)
            turn = kwargs.get("turn", args[1] if len(args) > 1 else 1)
            task_id = kwargs.get("task_id", args[0] if len(args) > 0 else "TASK-BUDGET-001")
            return _make_player_result(task_id=task_id, turn=turn)

        async def capturing_coach(*args, **kwargs):
            """Capture remaining_budget passed to Coach, return feedback/approve."""
            coach_budgets.append(kwargs.get("remaining_budget"))
            turn = kwargs.get("turn", args[1] if len(args) > 1 else 1)
            task_id = kwargs.get("task_id", args[0] if len(args) > 0 else "TASK-BUDGET-001")
            if turn == 1:
                return _make_coach_result(task_id=task_id, turn=turn, decision="feedback")
            return _make_coach_result(task_id=task_id, turn=turn, decision="approve")

        mock_invoker = Mock()
        mock_invoker.invoke_player = AsyncMock(side_effect=slow_player)
        mock_invoker.invoke_coach = AsyncMock(side_effect=capturing_coach)
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
        # Directly test _loop_phase with a time budget
        # Patch CoachValidator.validate to force SDK fallback (invoke_coach mock)
        with patch.object(CoachValidator, 'validate', side_effect=Exception("force SDK fallback")):
            turn_history, decision = orchestrator._loop_phase(
                task_id="TASK-BUDGET-001",
                requirements="Implement feature",
                acceptance_criteria=["Feature works"],
                worktree=mock_worktree,
                time_budget_seconds=2000.0,
            )

        assert decision == "approved"
        assert len(coach_budgets) == 2
        # Turn 1 coach budget should be close to 2000 (small elapsed)
        assert coach_budgets[0] is not None
        assert coach_budgets[0] > 1990.0
        # Turn 2 coach budget should be less than turn 1 (time elapsed)
        assert coach_budgets[1] is not None
        assert coach_budgets[1] < coach_budgets[0]
        # The difference should reflect the time spent in turn 1
        elapsed_between_turns = coach_budgets[0] - coach_budgets[1]
        assert elapsed_between_turns > 0.2  # At least 0.3s sleep

    def test_budget_exhaustion_exits_gracefully(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that when remaining budget < MIN_TURN_BUDGET_SECONDS,
        the loop exits with 'timeout_budget_exhausted' instead of
        waiting for asyncio.TimeoutError.
        """
        mock_invoker = Mock()
        mock_invoker.invoke_player = Mock(return_value=_make_player_result())
        mock_invoker.invoke_coach = Mock(
            return_value=_make_coach_result(decision="feedback"),
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

        # Give a budget that's just below MIN_TURN_BUDGET_SECONDS
        # so the loop exits before turn 1
        turn_history, decision = orchestrator._loop_phase(
            task_id="TASK-BUDGET-001",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
            worktree=mock_worktree,
            time_budget_seconds=float(MIN_TURN_BUDGET_SECONDS - 1),
        )

        assert decision == "timeout_budget_exhausted"
        assert len(turn_history) == 0
        # Player should never be invoked
        mock_invoker.invoke_player.assert_not_called()

    def test_budget_sufficient_for_first_turn_but_not_second(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that when budget is enough for turn 1 but not turn 2,
        the loop completes turn 1 and then exits gracefully.
        """
        async def slow_player(*args, **kwargs):
            """Simulate Player taking most of the budget."""
            time.sleep(1.0)
            return _make_player_result()

        mock_invoker = Mock()
        mock_invoker.invoke_player = AsyncMock(side_effect=slow_player)
        mock_invoker.invoke_coach = AsyncMock(
            return_value=_make_coach_result(decision="feedback"),
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

        # Budget: enough for 1 turn (MIN + 0.5s) but not for 2
        # Player sleeps 1.0s, so after turn 1 remaining < MIN → budget exhausted
        budget = float(MIN_TURN_BUDGET_SECONDS + 0.5)
        # Patch CoachValidator.validate to force SDK fallback (invoke_coach mock)
        with patch.object(CoachValidator, 'validate', side_effect=Exception("force SDK fallback")):
            turn_history, decision = orchestrator._loop_phase(
                task_id="TASK-BUDGET-001",
                requirements="Implement feature",
                acceptance_criteria=["Feature works"],
                worktree=mock_worktree,
                time_budget_seconds=budget,
            )

        # Should complete turn 1 but exit before turn 2
        assert decision == "timeout_budget_exhausted"
        assert len(turn_history) == 1
        assert mock_invoker.invoke_player.call_count == 1


# ============================================================================
# Tests: Coach Grace Period at Cancellation Boundary
# ============================================================================


@pytest.mark.integration
class TestCoachGracePeriodIntegration:
    """Integration tests for Coach grace period when Player succeeds near timeout."""

    def test_coach_receives_grace_period_when_player_succeeds_at_boundary(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify the end-to-end flow: Player succeeds → cancellation set →
        Coach receives COACH_GRACE_PERIOD_SECONDS as remaining_budget.

        Cancel event is set DURING player execution so it's detected between
        Player and Coach (not at the top-of-loop check).
        """
        coach_budget_received = []
        cancel_event = threading.Event()

        async def player_sets_cancel(*args, **kwargs):
            """Player succeeds, then cancellation fires (simulating timeout boundary)."""
            cancel_event.set()
            return _make_player_result(success=True)

        async def capturing_coach(*args, **kwargs):
            coach_budget_received.append(kwargs.get("remaining_budget"))
            return _make_coach_result(decision="approve")

        mock_invoker = Mock()
        mock_invoker.invoke_player = AsyncMock(side_effect=player_sets_cancel)
        mock_invoker.invoke_coach = AsyncMock(side_effect=capturing_coach)
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
            cancellation_event=cancel_event,
        )

        # Patch CoachValidator.validate to force SDK fallback (invoke_coach mock)
        with patch.object(CoachValidator, 'validate', side_effect=Exception("force SDK fallback")):
            turn_history, decision = orchestrator._loop_phase(
                task_id="TASK-BUDGET-001",
                requirements="Implement feature",
                acceptance_criteria=["Feature works"],
                worktree=mock_worktree,
            )

        # Coach should have been invoked with grace period budget
        assert decision == "approved"
        assert len(coach_budget_received) == 1
        assert coach_budget_received[0] == float(COACH_GRACE_PERIOD_SECONDS)

    def test_coach_skipped_when_player_fails_at_boundary(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that when Player fails AND cancellation is set,
        Coach is NOT invoked (no grace period for failed Player).
        """
        mock_invoker = Mock()
        mock_invoker.invoke_player = Mock(
            return_value=_make_player_result(success=False),
        )
        mock_invoker.invoke_coach = Mock()
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        cancel_event = threading.Event()
        cancel_event.set()

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            max_turns=5,
            agent_invoker=mock_invoker,
            progress_display=mock_progress_display,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=False,
            enable_checkpoints=False,
            enable_context=False,
            cancellation_event=cancel_event,
        )

        turn_history, decision = orchestrator._loop_phase(
            task_id="TASK-BUDGET-001",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
            worktree=mock_worktree,
        )

        # Coach should NOT have been invoked
        mock_invoker.invoke_coach.assert_not_called()
        # Decision should be "cancelled" (post-turn cancellation check)
        assert decision == "cancelled"


# ============================================================================
# Tests: SDK Timeout Capping
# ============================================================================


@pytest.mark.integration
class TestSDKTimeoutCappingIntegration:
    """Integration tests for SDK timeout capped at remaining task budget."""

    def test_sdk_timeout_capped_at_remaining_budget(self, tmp_path):
        """
        Verify that _calculate_sdk_timeout caps the computed timeout
        at the remaining_budget when provided.

        Tests the AgentInvoker component directly to verify the cap.
        """
        invoker = AgentInvoker(
            worktree_path=tmp_path,
            max_turns_per_agent=30,
            sdk_timeout_seconds=DEFAULT_SDK_TIMEOUT,
        )

        # Calculate without budget cap
        uncapped = invoker._calculate_sdk_timeout("TASK-001")
        # Calculate with tight budget
        capped = invoker._calculate_sdk_timeout("TASK-001", remaining_budget=200.0)

        # Capped should be <= 200
        assert capped <= 200
        # Uncapped should be the full calculated timeout
        assert uncapped >= capped


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
