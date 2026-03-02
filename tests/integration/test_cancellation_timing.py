"""
Integration Tests for Cancellation Timing (TASK-ABFIX-004, TASK-ABFIX-006)

Exercises the integration seam: FeatureOrchestrator → AutoBuild._loop_phase
with cancellation_event and timeout_event to verify:

Scenarios:
    1. Player completes near timeout boundary → Coach invoked with grace period
    2. Cancellation vs timeout distinction in final decision
    3. Timeout event takes priority over cancellation event
    4. Approve decision propagates even when cancellation is set (after Coach grace period)

Coverage Target: >=80%
Test Count: 5 tests

Run with:
    pytest tests/integration/test_cancellation_timing.py -v
"""

import threading
import time
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
    COACH_GRACE_PERIOD_SECONDS,
)
from guardkit.orchestrator.agent_invoker import (
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
    """Create a mock Worktree."""
    wt = Mock(spec=Worktree)
    wt.task_id = "TASK-CANCEL-001"
    wt.path = tmp_path / "worktree"
    wt.path.mkdir(parents=True, exist_ok=True)
    wt.branch_name = "autobuild/TASK-CANCEL-001"
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
    task_id: str = "TASK-CANCEL-001",
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


def _make_coach_result(
    task_id: str = "TASK-CANCEL-001",
    turn: int = 1,
    decision: str = "approve",
) -> AgentInvocationResult:
    """Build a minimal Coach result."""
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


def _create_orchestrator(
    tmp_path,
    mock_invoker,
    mock_progress_display,
    mock_worktree_manager,
    cancellation_event: Optional[threading.Event] = None,
    timeout_event: Optional[threading.Event] = None,
) -> AutoBuildOrchestrator:
    """Helper to create a configured orchestrator."""
    return AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=5,
        agent_invoker=mock_invoker,
        progress_display=mock_progress_display,
        worktree_manager=mock_worktree_manager,
        enable_pre_loop=False,
        enable_checkpoints=False,
        enable_context=False,
        cancellation_event=cancellation_event,
        timeout_event=timeout_event,
    )


# ============================================================================
# Tests: Cancellation vs Timeout Distinction
# ============================================================================


@pytest.mark.integration
class TestCancellationTimingIntegration:
    """Integration tests for cancellation and timeout event handling."""

    def test_timeout_event_returns_timeout_decision(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that when timeout_event is set, the loop exits with
        'timeout' (not 'cancelled') at the start of the next turn.
        """
        mock_invoker = Mock()
        mock_invoker.invoke_player = Mock(return_value=_make_player_result())
        mock_invoker.invoke_coach = Mock()
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        timeout_event = threading.Event()
        timeout_event.set()  # Pre-set: simulates feature-level timeout

        orchestrator = _create_orchestrator(
            tmp_path, mock_invoker, mock_progress_display, mock_worktree_manager,
            timeout_event=timeout_event,
        )

        turn_history, decision = orchestrator._loop_phase(
            task_id="TASK-CANCEL-001",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
            worktree=mock_worktree,
        )

        assert decision == "timeout"
        assert len(turn_history) == 0
        # Neither Player nor Coach should be invoked
        mock_invoker.invoke_player.assert_not_called()
        mock_invoker.invoke_coach.assert_not_called()

    def test_cancellation_event_returns_cancelled_decision(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that when cancellation_event is set (stop_on_failure),
        the loop exits with 'cancelled' at the start of the next turn.
        """
        mock_invoker = Mock()
        mock_invoker.invoke_player = Mock(return_value=_make_player_result())
        mock_invoker.invoke_coach = Mock()
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        cancel_event = threading.Event()
        cancel_event.set()  # Pre-set: simulates stop_on_failure

        orchestrator = _create_orchestrator(
            tmp_path, mock_invoker, mock_progress_display, mock_worktree_manager,
            cancellation_event=cancel_event,
        )

        turn_history, decision = orchestrator._loop_phase(
            task_id="TASK-CANCEL-001",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
            worktree=mock_worktree,
        )

        assert decision == "cancelled"
        assert len(turn_history) == 0
        mock_invoker.invoke_player.assert_not_called()

    def test_timeout_takes_priority_over_cancellation(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that when BOTH timeout_event and cancellation_event are set,
        the loop exits with 'timeout' (timeout has priority per TASK-ABFIX-006).
        """
        mock_invoker = Mock()
        mock_invoker.invoke_player = Mock(return_value=_make_player_result())
        mock_invoker.invoke_coach = Mock()
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        timeout_event = threading.Event()
        cancel_event = threading.Event()
        timeout_event.set()
        cancel_event.set()

        orchestrator = _create_orchestrator(
            tmp_path, mock_invoker, mock_progress_display, mock_worktree_manager,
            cancellation_event=cancel_event,
            timeout_event=timeout_event,
        )

        turn_history, decision = orchestrator._loop_phase(
            task_id="TASK-CANCEL-001",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
            worktree=mock_worktree,
        )

        # Timeout should take priority
        assert decision == "timeout"

    def test_approve_propagates_despite_cancellation_set(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that when Player succeeds, Coach approves during grace period,
        and cancellation is set — the 'approve' decision propagates.

        This tests the critical requirement from TASK-ABFIX-004:
        approval BEFORE post-turn cancellation check.

        The cancel_event must be set DURING player execution (not before the loop)
        so the top-of-loop cancellation check doesn't trigger first. The between-
        Player-and-Coach check then detects it and grants Coach a grace period.
        """
        coach_budgets = []
        cancel_event = threading.Event()

        async def player_sets_cancel(*args, **kwargs):
            """Player succeeds, then cancellation fires (simulating timeout boundary)."""
            cancel_event.set()
            return _make_player_result(success=True)

        async def capturing_coach(*args, **kwargs):
            coach_budgets.append(kwargs.get("remaining_budget"))
            return _make_coach_result(decision="approve")

        mock_invoker = Mock()
        mock_invoker.invoke_player = AsyncMock(side_effect=player_sets_cancel)
        mock_invoker.invoke_coach = AsyncMock(side_effect=capturing_coach)
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        orchestrator = _create_orchestrator(
            tmp_path, mock_invoker, mock_progress_display, mock_worktree_manager,
            cancellation_event=cancel_event,
        )

        # Patch CoachValidator.validate to force SDK fallback (invoke_coach mock)
        with patch.object(CoachValidator, 'validate', side_effect=Exception("force SDK fallback")):
            turn_history, decision = orchestrator._loop_phase(
                task_id="TASK-CANCEL-001",
                requirements="Implement feature",
                acceptance_criteria=["Feature works"],
                worktree=mock_worktree,
            )

        # Approve should propagate (not cancelled)
        assert decision == "approved"
        assert len(turn_history) == 1
        assert turn_history[0].decision == "approve"
        # Coach should have received grace period budget
        assert len(coach_budgets) == 1
        assert coach_budgets[0] == float(COACH_GRACE_PERIOD_SECONDS)

    def test_cancellation_set_mid_turn_with_player_failure_skips_coach(
        self, tmp_path, mock_worktree, mock_progress_display, mock_worktree_manager,
    ):
        """
        Verify that when cancellation is set between Player and Coach,
        and Player FAILED, Coach is skipped (no grace period for failure).

        The loop should then exit with 'cancelled' at the post-turn check.
        """
        cancel_event = threading.Event()

        async def failing_player_sets_cancel(*args, **kwargs):
            """Player fails and cancellation gets set during execution."""
            cancel_event.set()
            return _make_player_result(success=False)

        mock_invoker = Mock()
        mock_invoker.invoke_player = AsyncMock(side_effect=failing_player_sets_cancel)
        mock_invoker.invoke_coach = AsyncMock()
        mock_invoker.sdk_timeout_seconds = DEFAULT_SDK_TIMEOUT
        mock_invoker._sdk_timeout_is_override = False

        orchestrator = _create_orchestrator(
            tmp_path, mock_invoker, mock_progress_display, mock_worktree_manager,
            cancellation_event=cancel_event,
        )

        turn_history, decision = orchestrator._loop_phase(
            task_id="TASK-CANCEL-001",
            requirements="Implement feature",
            acceptance_criteria=["Feature works"],
            worktree=mock_worktree,
        )

        # Coach should NOT have been invoked
        mock_invoker.invoke_coach.assert_not_called()
        # Decision should be "cancelled" (from post-turn check after error return)
        assert decision == "cancelled"


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
