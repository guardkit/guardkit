"""
Unit tests for per-turn timeout budgeting with Coach grace period (TASK-ABFIX-004).

Tests cover:
1. Module-level constants (COACH_GRACE_PERIOD_SECONDS, MIN_TURN_BUDGET_SECONDS)
2. _calculate_sdk_timeout: caps at remaining_budget when provided
3. invoke_coach: uses capped timeout via remaining_budget, restores after
4. _loop_phase: returns "timeout_budget_exhausted" when budget insufficient
5. _loop_phase: proceeds normally when budget is sufficient
6. _execute_turn: Coach grace period granted when Player succeeds + cancellation set
7. _execute_turn: Cancellation honoured when Player failed
8. _loop_phase: "approve" decision propagates before post-turn cancellation check
"""

import importlib
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
    DEFAULT_SDK_TIMEOUT,
    MAX_SDK_TIMEOUT,
)
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    COACH_GRACE_PERIOD_SECONDS,
    MIN_TURN_BUDGET_SECONDS,
    TurnRecord,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def worktree_path(tmp_path):
    """Temporary directory used as worktree."""
    wt = tmp_path / "worktree"
    wt.mkdir()
    return wt


@pytest.fixture
def mock_worktree():
    """Mock Worktree instance."""
    wt = Mock(spec=Worktree)
    wt.task_id = "TASK-AB-001"
    wt.path = Path("/tmp/worktrees/TASK-AB-001")
    wt.branch_name = "autobuild/TASK-AB-001"
    wt.base_branch = "main"
    return wt


@pytest.fixture
def agent_invoker(worktree_path):
    """AgentInvoker with predictable defaults, no real SDK calls."""
    return AgentInvoker(
        worktree_path=worktree_path,
        max_turns_per_agent=30,
        sdk_timeout_seconds=DEFAULT_SDK_TIMEOUT,
    )


def _make_player_result(success: bool, task_id: str = "TASK-AB-001") -> AgentInvocationResult:
    """Helper: build a minimal AgentInvocationResult for Player."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=1,
        agent_type="player",
        success=success,
        report={"files_changed": [], "tests_passed": success},
        duration_seconds=5.0,
        error=None if success else "Player failed",
    )


def _make_coach_result(decision: str = "approve", task_id: str = "TASK-AB-001") -> AgentInvocationResult:
    """Helper: build a minimal AgentInvocationResult for Coach."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=1,
        agent_type="coach",
        success=True,
        report={"decision": decision, "feedback": "Good work"},
        duration_seconds=10.0,
        error=None,
    )


def _make_orchestrator(
    worktree_path: Path,
    mock_worktree: Worktree,
    max_turns: int = 3,
    cancellation_event: Optional[threading.Event] = None,
) -> AutoBuildOrchestrator:
    """Helper: create a minimal AutoBuildOrchestrator for unit testing."""
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)

    # Minimal attribute setup without calling __init__
    orchestrator.max_turns = max_turns
    orchestrator.resume = False
    orchestrator.repo_root = worktree_path
    orchestrator.enable_pre_loop = False
    orchestrator.enable_context = False
    orchestrator.ablation_mode = False
    orchestrator.enable_checkpoints = False
    orchestrator.rollback_on_pollution = False
    orchestrator._cancellation_event = cancellation_event
    orchestrator._timeout_event = None
    orchestrator._task_timeout = None
    orchestrator._loop_start_time = None  # TASK-ABSR-FRSH
    orchestrator._cumulative_source_files = set()
    orchestrator._cumulative_requirements_addressed = set()
    orchestrator.wave_size = 1
    orchestrator._turn_history = []
    orchestrator._feature_id = None
    orchestrator._max_criteria_passed = 0
    orchestrator._agent_invoker = Mock()
    # TASK-OSI-006: skip orchestrator-side Phase 4/5 in unit tests by
    # forcing implementation_mode to "direct" on the Mock invoker.
    orchestrator._agent_invoker._get_implementation_mode.return_value = "direct"
    orchestrator._worktree_manager = Mock()
    orchestrator._checkpoint_manager = None
    orchestrator._last_player_context_status = None
    orchestrator._last_coach_context_status = None
    orchestrator.verbose = False
    orchestrator.perspective_reset_turns = []

    # Progress display - silent mock
    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    progress.console = Mock()
    progress.start_turn = Mock()
    progress.complete_turn = Mock()
    orchestrator._progress_display = progress

    return orchestrator


# ============================================================================
# Tests: Module constants
# ============================================================================


class TestTimeoutBudgetConstants:
    """Verify module-level constants are defined with correct values."""

    def test_coach_grace_period_is_120(self):
        assert COACH_GRACE_PERIOD_SECONDS == 120

    def test_min_turn_budget_is_600(self):
        assert MIN_TURN_BUDGET_SECONDS == 600

    def test_constants_are_positive_integers(self):
        assert isinstance(COACH_GRACE_PERIOD_SECONDS, int)
        assert isinstance(MIN_TURN_BUDGET_SECONDS, int)
        assert COACH_GRACE_PERIOD_SECONDS > 0
        assert MIN_TURN_BUDGET_SECONDS > 0

    def test_grace_period_less_than_min_turn_budget(self):
        """Grace period should be smaller than the min turn budget so that
        we can still grant Coach time even after exhausting the per-turn check."""
        assert COACH_GRACE_PERIOD_SECONDS < MIN_TURN_BUDGET_SECONDS

    def test_min_turn_budget_env_override(self):
        """GUARDKIT_MIN_TURN_BUDGET overrides the 600 s default at module load (TASK-ABSR-MTBC)."""
        import guardkit.orchestrator.autobuild as autobuild_module

        with patch.dict(os.environ, {"GUARDKIT_MIN_TURN_BUDGET": "300"}):
            importlib.reload(autobuild_module)
            try:
                assert autobuild_module.MIN_TURN_BUDGET_SECONDS == 300
            finally:
                # Restore module to default state so other tests see the
                # canonical 600 s value regardless of run order.
                pass

        # patch.dict has now removed the override; reload back to default.
        importlib.reload(autobuild_module)
        assert autobuild_module.MIN_TURN_BUDGET_SECONDS == 600


# ============================================================================
# Tests: AgentInvoker._calculate_sdk_timeout with remaining_budget
# ============================================================================


class TestCalculateSdkTimeoutBudgetCap:
    """_calculate_sdk_timeout should cap at remaining_budget when provided."""

    def test_no_remaining_budget_uncapped(self, agent_invoker, tmp_path):
        """Without remaining_budget, existing behaviour is unchanged."""
        # Bypass task loader (no real task file)
        with patch.object(agent_invoker, "_sdk_timeout_is_override", False):
            with patch("guardkit.orchestrator.agent_invoker.AgentInvoker._calculate_sdk_timeout",
                       wraps=agent_invoker._calculate_sdk_timeout):
                timeout = agent_invoker._calculate_sdk_timeout("TASK-AB-001")
        # Without a real task file the method falls back to defaults
        assert timeout > 0
        assert timeout <= MAX_SDK_TIMEOUT * agent_invoker.timeout_multiplier

    def test_remaining_budget_caps_timeout(self, agent_invoker):
        """When remaining_budget < calculated timeout, result is capped."""
        # Force known calculated timeout via mock task data
        with patch.object(agent_invoker, "_sdk_timeout_is_override", False):
            with patch(
                "guardkit.tasks.task_loader.TaskLoader.load_task",
                return_value={"frontmatter": {"implementation_mode": "direct", "complexity": 1}},
            ):
                # Without cap: base * 1.0 * 1.1 = DEFAULT_SDK_TIMEOUT * 1.1
                uncapped = agent_invoker._calculate_sdk_timeout("TASK-AB-001")
                # With a tight cap
                capped = agent_invoker._calculate_sdk_timeout("TASK-AB-001", remaining_budget=60.0)

        assert capped == 60
        assert capped < uncapped

    def test_remaining_budget_larger_than_calculated_does_not_increase(self, agent_invoker):
        """When remaining_budget > calculated timeout, calculated value is used."""
        with patch.object(agent_invoker, "_sdk_timeout_is_override", False):
            with patch(
                "guardkit.tasks.task_loader.TaskLoader.load_task",
                return_value={"frontmatter": {"implementation_mode": "direct", "complexity": 1}},
            ):
                uncapped = agent_invoker._calculate_sdk_timeout("TASK-AB-001")
                large_budget = agent_invoker._calculate_sdk_timeout(
                    "TASK-AB-001", remaining_budget=float(MAX_SDK_TIMEOUT * 10)
                )

        assert large_budget == uncapped

    def test_cli_override_ignores_remaining_budget(self, agent_invoker):
        """When user supplied an explicit CLI timeout, remaining_budget is ignored."""
        with patch.object(agent_invoker, "_sdk_timeout_is_override", True):
            agent_invoker.sdk_timeout_seconds = 999
            timeout = agent_invoker._calculate_sdk_timeout("TASK-AB-001", remaining_budget=30.0)
        # CLI override takes precedence over remaining_budget cap
        assert timeout == 999

    def test_zero_remaining_budget_returns_zero_or_one(self, agent_invoker):
        """Degenerate case: zero remaining budget produces a non-negative result."""
        with patch.object(agent_invoker, "_sdk_timeout_is_override", False):
            with patch(
                "guardkit.tasks.task_loader.TaskLoader.load_task",
                return_value={"frontmatter": {"implementation_mode": "direct", "complexity": 1}},
            ):
                timeout = agent_invoker._calculate_sdk_timeout("TASK-AB-001", remaining_budget=0.0)
        assert timeout >= 0


# ============================================================================
# Tests: invoke_coach uses remaining_budget and restores timeout
# ============================================================================


class TestInvokeCoachRemainingBudget:
    """invoke_coach should cap sdk_timeout_seconds at remaining_budget and restore it."""

    @pytest.mark.asyncio
    async def test_invoke_coach_caps_timeout_at_remaining_budget(self, agent_invoker):
        """When remaining_budget is provided, Coach SDK timeout is capped."""
        original = agent_invoker.sdk_timeout_seconds

        captured_timeouts: List[int] = []

        async def fake_invoke_with_role(**kwargs):
            captured_timeouts.append(agent_invoker.sdk_timeout_seconds)

        with patch.object(agent_invoker, "_invoke_with_role", side_effect=fake_invoke_with_role):
            with patch.object(agent_invoker, "_verify_player_claims", return_value=MagicMock(
                verified=True, discrepancies=[], honesty_score=1.0
            )):
                with patch.object(agent_invoker, "_build_coach_prompt", return_value="coach prompt"):
                    with patch.object(agent_invoker, "_load_agent_report", return_value={"decision": "approve"}):
                        with patch.object(agent_invoker, "_validate_coach_decision"):
                            await agent_invoker.invoke_coach(
                                task_id="TASK-AB-001",
                                turn=1,
                                requirements="do stuff",
                                player_report={},
                                remaining_budget=120.0,
                            )

        assert len(captured_timeouts) == 1
        assert captured_timeouts[0] == 120
        # Timeout restored after invocation
        assert agent_invoker.sdk_timeout_seconds == original

    @pytest.mark.asyncio
    async def test_invoke_coach_restores_timeout_on_exception(self, agent_invoker):
        """sdk_timeout_seconds is restored even when an exception occurs."""
        original = agent_invoker.sdk_timeout_seconds

        async def raise_error(**kwargs):
            raise RuntimeError("simulated failure")

        with patch.object(agent_invoker, "_invoke_with_role", side_effect=raise_error):
            with patch.object(agent_invoker, "_verify_player_claims", return_value=MagicMock(
                verified=True, discrepancies=[], honesty_score=1.0
            )):
                with patch.object(agent_invoker, "_build_coach_prompt", return_value="prompt"):
                    result = await agent_invoker.invoke_coach(
                        task_id="TASK-AB-001",
                        turn=1,
                        requirements="do stuff",
                        player_report={},
                        remaining_budget=120.0,
                    )

        assert not result.success
        assert agent_invoker.sdk_timeout_seconds == original

    @pytest.mark.asyncio
    async def test_invoke_coach_no_remaining_budget_unchanged_timeout(self, agent_invoker):
        """Without remaining_budget, sdk_timeout_seconds is determined by _calculate_sdk_timeout."""
        original = agent_invoker.sdk_timeout_seconds
        captured: List[int] = []

        async def fake_invoke_with_role(**kwargs):
            captured.append(agent_invoker.sdk_timeout_seconds)

        with patch.object(agent_invoker, "_invoke_with_role", side_effect=fake_invoke_with_role):
            with patch.object(agent_invoker, "_verify_player_claims", return_value=MagicMock(
                verified=True, discrepancies=[], honesty_score=1.0
            )):
                with patch.object(agent_invoker, "_build_coach_prompt", return_value="prompt"):
                    with patch.object(agent_invoker, "_load_agent_report", return_value={"decision": "approve"}):
                        with patch.object(agent_invoker, "_validate_coach_decision"):
                            await agent_invoker.invoke_coach(
                                task_id="TASK-AB-001",
                                turn=1,
                                requirements="do stuff",
                                player_report={},
                                remaining_budget=None,
                            )

        # Restored after call
        assert agent_invoker.sdk_timeout_seconds == original


# ============================================================================
# Tests: _loop_phase budget exhaustion
# ============================================================================


class TestLoopPhaseBudgetExhaustion:
    """_loop_phase should return 'timeout_budget_exhausted' when budget is too low."""

    def test_budget_exhausted_before_first_turn(self, worktree_path, mock_worktree):
        """When remaining budget < MIN_TURN_BUDGET at loop start, exit immediately."""
        orchestrator = _make_orchestrator(worktree_path, mock_worktree)

        # time.monotonic side-effects:
        # - first call: loop_start_time (at loop entry)
        # - second call: elapsed check before turn 1 => return 9999s to simulate exhaustion
        monotonic_values = [0.0, float(MIN_TURN_BUDGET_SECONDS + 100)]

        with patch("guardkit.orchestrator.autobuild.time") as mock_time:
            mock_time.monotonic = Mock(side_effect=monotonic_values)

            turn_history, decision = orchestrator._loop_phase(
                task_id="TASK-AB-001",
                requirements="do stuff",
                acceptance_criteria=["criterion 1"],
                worktree=mock_worktree,
                time_budget_seconds=float(MIN_TURN_BUDGET_SECONDS),  # Exactly MIN
            )

        assert decision == "timeout_budget_exhausted"
        assert turn_history == []

    def test_budget_sufficient_for_first_turn(self, worktree_path, mock_worktree):
        """When remaining budget >= MIN_TURN_BUDGET, the turn is allowed to proceed."""
        orchestrator = _make_orchestrator(worktree_path, mock_worktree, max_turns=1)

        # Player succeeds on first turn and Coach approves
        player_ok = _make_player_result(success=True)
        coach_ok = _make_coach_result(decision="approve")

        with patch.object(orchestrator, "_execute_turn") as mock_execute:
            mock_turn = Mock()
            mock_turn.decision = "approve"
            mock_turn.feedback = None
            mock_turn.is_configuration_error = False
            mock_turn.player_result = Mock(error=None)
            mock_execute.return_value = mock_turn

            with patch.object(orchestrator, "_capture_turn_state"):
                with patch.object(orchestrator, "_record_honesty"):
                    with patch.object(orchestrator, "_display_criteria_progress"):
                        with patch("guardkit.orchestrator.autobuild.time") as mock_time:
                            # First call: loop_start_time=0; second call: elapsed=10 (< budget)
                            mock_time.monotonic = Mock(side_effect=[0.0, 10.0])

                            _, decision = orchestrator._loop_phase(
                                task_id="TASK-AB-001",
                                requirements="do stuff",
                                acceptance_criteria=["criterion 1"],
                                worktree=mock_worktree,
                                time_budget_seconds=float(MIN_TURN_BUDGET_SECONDS * 2),
                            )

        assert decision == "approved"

    def test_no_budget_means_unlimited(self, worktree_path, mock_worktree):
        """When time_budget_seconds is None, no budget check occurs."""
        orchestrator = _make_orchestrator(worktree_path, mock_worktree, max_turns=1)

        with patch.object(orchestrator, "_execute_turn") as mock_execute:
            mock_turn = Mock()
            mock_turn.decision = "approve"
            mock_turn.feedback = None
            mock_turn.is_configuration_error = False
            mock_turn.player_result = Mock(error=None)
            mock_execute.return_value = mock_turn

            with patch.object(orchestrator, "_capture_turn_state"):
                with patch.object(orchestrator, "_record_honesty"):
                    with patch.object(orchestrator, "_display_criteria_progress"):
                        _, decision = orchestrator._loop_phase(
                            task_id="TASK-AB-001",
                            requirements="do stuff",
                            acceptance_criteria=["criterion 1"],
                            worktree=mock_worktree,
                            time_budget_seconds=None,  # No budget
                        )

        assert decision == "approved"

    def test_budget_exhausted_between_turns(self, worktree_path, mock_worktree):
        """After turn 1 completes, budget check fires before turn 2 begins."""
        orchestrator = _make_orchestrator(worktree_path, mock_worktree, max_turns=3)

        call_count = [0]

        def execute_turn_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_turn = Mock()
            mock_turn.decision = "feedback"  # Needs another turn
            mock_turn.feedback = "try harder"
            mock_turn.is_configuration_error = False
            mock_turn.player_result = Mock(error=None)
            return mock_turn

        with patch.object(orchestrator, "_execute_turn", side_effect=execute_turn_side_effect):
            with patch.object(orchestrator, "_capture_turn_state"):
                with patch.object(orchestrator, "_record_honesty"):
                    with patch.object(orchestrator, "_display_criteria_progress"):
                        with patch.object(orchestrator, "_is_feedback_stalled", return_value=False):
                            with patch.object(orchestrator, "_count_criteria_passed", return_value=0):
                                with patch("guardkit.orchestrator.autobuild.time") as mock_time:
                                    # [loop_start, check_before_turn1, check_before_turn2]
                                    # After turn1, elapsed > budget - MIN
                                    budget = float(MIN_TURN_BUDGET_SECONDS * 2)
                                    mock_time.monotonic = Mock(
                                        side_effect=[
                                            0.0,  # loop_start_time
                                            10.0,  # before turn 1: 10s elapsed, budget OK
                                            budget - 100,  # before turn 2: only 100s left → exhausted
                                        ]
                                    )

                                    _, decision = orchestrator._loop_phase(
                                        task_id="TASK-AB-001",
                                        requirements="do stuff",
                                        acceptance_criteria=["criterion 1"],
                                        worktree=mock_worktree,
                                        time_budget_seconds=budget,
                                    )

        assert decision == "timeout_budget_exhausted"
        assert call_count[0] == 1  # Only turn 1 executed


# ============================================================================
# Tests: Coach grace period in _execute_turn
# ============================================================================


class TestCoachGracePeriod:
    """When Player succeeds and cancellation is set, Coach still gets invoked."""

    def test_player_success_cancellation_set_coach_invoked(self, worktree_path, mock_worktree):
        """When Player succeeds and cancellation event is set, Coach receives grace period."""
        cancel_event = threading.Event()
        cancel_event.set()  # Simulate timeout / stop-on-failure

        orchestrator = _make_orchestrator(worktree_path, mock_worktree, cancellation_event=cancel_event)

        player_success = _make_player_result(success=True)
        coach_approve = _make_coach_result(decision="approve")

        coach_budget_used: List[Optional[float]] = []

        def mock_invoke_coach_safely(*args, **kwargs):
            coach_budget_used.append(kwargs.get("remaining_budget"))
            return coach_approve

        with patch.object(orchestrator, "_invoke_player_safely", return_value=player_success):
            with patch.object(orchestrator, "_invoke_coach_safely", side_effect=mock_invoke_coach_safely):
                with patch.object(orchestrator, "_build_player_summary", return_value="ok"):
                    result = orchestrator._execute_turn(
                        turn=1,
                        task_id="TASK-AB-001",
                        requirements="do stuff",
                        worktree=mock_worktree,
                        previous_feedback=None,
                        remaining_budget=50.0,  # Low budget to trigger grace period scenario
                    )

        # Coach was invoked (grace period honoured)
        assert len(coach_budget_used) == 1
        # Coach gets the grace period budget, not the original low remaining_budget
        assert coach_budget_used[0] == float(COACH_GRACE_PERIOD_SECONDS)

    def test_player_failure_cancellation_set_coach_not_invoked(self, worktree_path, mock_worktree):
        """When Player fails and cancellation is set, coach is NOT invoked."""
        cancel_event = threading.Event()
        cancel_event.set()

        orchestrator = _make_orchestrator(worktree_path, mock_worktree, cancellation_event=cancel_event)

        player_fail = _make_player_result(success=False)
        player_fail = AgentInvocationResult(
            task_id="TASK-AB-001",
            turn=1,
            agent_type="player",
            success=False,
            report={"unrecoverable": False},
            duration_seconds=5.0,
            error="Player failed",
        )

        coach_called = [False]

        def mock_invoke_coach(*args, **kwargs):
            coach_called[0] = True
            return _make_coach_result()

        with patch.object(orchestrator, "_invoke_player_safely", return_value=player_fail):
            with patch.object(orchestrator, "_invoke_coach_safely", side_effect=mock_invoke_coach):
                with patch.object(orchestrator, "_attempt_state_recovery", return_value=None):
                    result = orchestrator._execute_turn(
                        turn=1,
                        task_id="TASK-AB-001",
                        requirements="do stuff",
                        worktree=mock_worktree,
                        previous_feedback=None,
                    )

        assert not coach_called[0]
        assert result.decision == "error"

    def test_no_cancellation_passes_remaining_budget_to_coach(self, worktree_path, mock_worktree):
        """Without cancellation, remaining_budget is passed directly to Coach."""
        orchestrator = _make_orchestrator(worktree_path, mock_worktree, cancellation_event=None)

        player_success = _make_player_result(success=True)
        coach_approve = _make_coach_result(decision="approve")

        captured_budget: List[Optional[float]] = []

        def mock_invoke_coach_safely(*args, **kwargs):
            captured_budget.append(kwargs.get("remaining_budget"))
            return coach_approve

        with patch.object(orchestrator, "_invoke_player_safely", return_value=player_success):
            with patch.object(orchestrator, "_invoke_coach_safely", side_effect=mock_invoke_coach_safely):
                with patch.object(orchestrator, "_build_player_summary", return_value="ok"):
                    orchestrator._execute_turn(
                        turn=1,
                        task_id="TASK-AB-001",
                        requirements="do stuff",
                        worktree=mock_worktree,
                        previous_feedback=None,
                        remaining_budget=800.0,
                    )

        assert len(captured_budget) == 1
        assert captured_budget[0] == 800.0  # Original budget passed through

    def test_grace_period_uses_coach_grace_constant(self, worktree_path, mock_worktree):
        """Grace period budget is exactly COACH_GRACE_PERIOD_SECONDS, not arbitrary."""
        cancel_event = threading.Event()
        cancel_event.set()

        orchestrator = _make_orchestrator(worktree_path, mock_worktree, cancellation_event=cancel_event)

        player_success = _make_player_result(success=True)
        coach_approve = _make_coach_result(decision="approve")

        captured: List[Optional[float]] = []

        def mock_coach(*args, **kwargs):
            captured.append(kwargs.get("remaining_budget"))
            return coach_approve

        with patch.object(orchestrator, "_invoke_player_safely", return_value=player_success):
            with patch.object(orchestrator, "_invoke_coach_safely", side_effect=mock_coach):
                with patch.object(orchestrator, "_build_player_summary", return_value="ok"):
                    orchestrator._execute_turn(
                        turn=1,
                        task_id="TASK-AB-001",
                        requirements="do stuff",
                        worktree=mock_worktree,
                        previous_feedback=None,
                        remaining_budget=None,  # No budget provided
                    )

        assert captured[0] == float(COACH_GRACE_PERIOD_SECONDS)


# ============================================================================
# Tests: _loop_phase - approval propagates before post-turn cancellation
# ============================================================================


class TestApprovalBeforeCancellationCheck:
    """'approve' decision from Coach should propagate even if cancellation is set."""

    def test_approve_propagates_when_cancellation_set_after_coach(self, worktree_path, mock_worktree):
        """If Coach approved but cancellation is set, 'approved' is returned."""
        cancel_event = threading.Event()
        # Cancellation is NOT set before the turn; it will be set inside _execute_turn mock
        orchestrator = _make_orchestrator(
            worktree_path, mock_worktree, max_turns=1, cancellation_event=cancel_event
        )

        def execute_turn_side_effect(*args, **kwargs):
            # Simulate cancellation being set DURING the turn (e.g., from parallel task)
            cancel_event.set()
            mock_turn = Mock()
            mock_turn.decision = "approve"
            mock_turn.feedback = None
            mock_turn.is_configuration_error = False
            mock_turn.player_result = Mock(error=None)
            return mock_turn

        with patch.object(orchestrator, "_execute_turn", side_effect=execute_turn_side_effect):
            with patch.object(orchestrator, "_capture_turn_state"):
                with patch.object(orchestrator, "_record_honesty"):
                    with patch.object(orchestrator, "_display_criteria_progress"):
                        _, decision = orchestrator._loop_phase(
                            task_id="TASK-AB-001",
                            requirements="do stuff",
                            acceptance_criteria=["criterion 1"],
                            worktree=mock_worktree,
                            time_budget_seconds=None,
                        )

        assert decision == "approved"

    def test_cancelled_when_coach_gave_feedback_and_cancellation_set(self, worktree_path, mock_worktree):
        """If Coach gave feedback (not approve) and cancellation is set, 'cancelled' is returned."""
        cancel_event = threading.Event()
        orchestrator = _make_orchestrator(
            worktree_path, mock_worktree, max_turns=3, cancellation_event=cancel_event
        )

        def execute_turn_side_effect(*args, **kwargs):
            cancel_event.set()
            mock_turn = Mock()
            mock_turn.decision = "feedback"
            mock_turn.feedback = "need more tests"
            mock_turn.is_configuration_error = False
            mock_turn.player_result = Mock(error=None)
            return mock_turn

        with patch.object(orchestrator, "_execute_turn", side_effect=execute_turn_side_effect):
            with patch.object(orchestrator, "_capture_turn_state"):
                with patch.object(orchestrator, "_record_honesty"):
                    with patch.object(orchestrator, "_display_criteria_progress"):
                        with patch.object(orchestrator, "_is_feedback_stalled", return_value=False):
                            with patch.object(orchestrator, "_count_criteria_passed", return_value=0):
                                _, decision = orchestrator._loop_phase(
                                    task_id="TASK-AB-001",
                                    requirements="do stuff",
                                    acceptance_criteria=["criterion 1"],
                                    worktree=mock_worktree,
                                    time_budget_seconds=None,
                                )

        assert decision == "cancelled"


# ============================================================================
# Tests: Feature orchestrator passes budget to _execute_task
# ============================================================================


class TestFeatureOrchestratorBudgetPropagation:
    """FeatureOrchestrator should pass time_budget_seconds to _execute_task."""

    def test_execute_task_accepts_time_budget_parameter(self, worktree_path, mock_worktree, tmp_path):
        """_execute_task should accept time_budget_seconds without error."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
        from guardkit.orchestrator.feature_loader import FeatureTask

        # Create minimal orchestrator without __init__
        fo = FeatureOrchestrator.__new__(FeatureOrchestrator)
        fo.repo_root = tmp_path
        fo.task_timeout = 2400
        fo.max_turns = 3
        fo.resume = False
        fo.fresh = False
        fo.enable_pre_loop = None
        fo.enable_context = True
        fo.sdk_timeout = None
        fo.timeout_multiplier = 1.0
        fo.stop_on_failure = False
        fo.task_log_interval = 60
        fo._emitter = Mock()
        fo._wave_display = None
        fo._worktree_manager = Mock()
        # __init__ initialises this to None; bypassing __init__ above means
        # we have to set it explicitly so _execute_task can pass it through
        # to AutoBuildOrchestrator (TASK-FIX-7A05).
        fo._bootstrap_venv_python = None

        task = FeatureTask(
            id="TASK-T-001",
            name="Test task",
            file_path=tmp_path / "TASK-T-001.md",
            complexity=3,
            dependencies=[],
            status="pending",
            implementation_mode="task-work",
            estimated_minutes=30,
        )

        mock_orchestrate_result = Mock()
        mock_orchestrate_result.success = True
        mock_orchestrate_result.total_turns = 1
        mock_orchestrate_result.final_decision = "approved"
        mock_orchestrate_result.error = None
        mock_orchestrate_result.recovery_count = 0
        mock_orchestrate_result.turn_history = []
        # Production checks `is not None`; an autospec'd Mock would be truthy
        # and trip the `list(stall_classification.co_fires)` path in
        # _execute_task. Force None for the no-stall case.
        mock_orchestrate_result.stall_classification = None

        with patch("guardkit.orchestrator.feature_orchestrator.TaskLoader.load_task") as mock_load:
            mock_load.return_value = {
                "frontmatter": {"autobuild": {"sdk_timeout": 1200}},
                "requirements": "do stuff",
                "acceptance_criteria": ["criterion 1"],
                "file_path": tmp_path / "TASK-T-001.md",
            }
            with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as MockABO:
                mock_abo_instance = Mock()
                mock_abo_instance.orchestrate.return_value = mock_orchestrate_result
                MockABO.return_value = mock_abo_instance

                from guardkit.orchestrator.feature_loader import Feature

                feature = Mock(spec=Feature)
                feature.id = "FEAT-TEST"

                # Call with time_budget_seconds
                result = fo._execute_task(
                    task=task,
                    feature=feature,
                    worktree=mock_worktree,
                    time_budget_seconds=1800.0,
                )

        assert result.success
        # Verify orchestrate was called with time_budget_seconds
        call_kwargs = mock_abo_instance.orchestrate.call_args
        assert "time_budget_seconds" in call_kwargs.kwargs or (
            len(call_kwargs.args) >= 6  # positional args fallback
        )


# ============================================================================
# Tests: _cap_specialist_timeout (TASK-ABSR-WALL)
# ============================================================================


class TestCapSpecialistTimeout:
    """Cap orchestrator-invoked specialist sdk_timeout at remaining wall.

    The cap mirrors the Player-side cap in
    ``AgentInvoker._calculate_sdk_timeout`` so a single specialist cannot
    consume the entire remaining wall budget when ``self.sdk_timeout``
    exceeds what's left.
    """

    def _orchestrator(
        self, worktree_path, mock_worktree, sdk_timeout: int = 1200
    ) -> AutoBuildOrchestrator:
        orch = _make_orchestrator(worktree_path, mock_worktree)
        orch.sdk_timeout = sdk_timeout
        return orch

    def test_uses_full_when_ample_remaining(
        self, worktree_path, mock_worktree
    ):
        """Ample remaining_budget → returns base sdk_timeout unchanged."""
        orch = self._orchestrator(worktree_path, mock_worktree, sdk_timeout=1200)
        # 2400 remaining - 120 grace = 2280 reserved; min(1200, 2280) = 1200
        assert orch._cap_specialist_timeout(remaining_budget=2400.0) == 1200

    def test_caps_when_low_remaining(
        self, worktree_path, mock_worktree
    ):
        """Low remaining_budget → cap to remaining minus COACH_GRACE_PERIOD."""
        orch = self._orchestrator(worktree_path, mock_worktree, sdk_timeout=1200)
        # 800 remaining - 120 grace = 680 reserved; min(1200, 680) = 680
        assert orch._cap_specialist_timeout(remaining_budget=800.0) == 680

    def test_floor_at_60s(self, worktree_path, mock_worktree):
        """Pathologically-low remaining → floor at 60 s, never zero/negative."""
        orch = self._orchestrator(worktree_path, mock_worktree, sdk_timeout=1200)
        # 100 remaining - 120 grace = -20 reserved; floor 60; min(1200, 60) = 60
        assert orch._cap_specialist_timeout(remaining_budget=100.0) == 60
        # Even at remaining=0 the floor still holds.
        assert orch._cap_specialist_timeout(remaining_budget=0.0) == 60

    def test_no_budget_passes_base(
        self, worktree_path, mock_worktree
    ):
        """remaining_budget=None → return base sdk_timeout (no cap)."""
        orch = self._orchestrator(worktree_path, mock_worktree, sdk_timeout=1200)
        assert orch._cap_specialist_timeout(remaining_budget=None) == 1200

    def test_circuit_breaker_env_var(
        self, worktree_path, mock_worktree, monkeypatch
    ):
        """GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable → return base regardless."""
        orch = self._orchestrator(worktree_path, mock_worktree, sdk_timeout=1200)
        monkeypatch.setenv("GUARDKIT_SPECIALIST_TIMEOUT_CAP", "disable")
        # Without the env var this would be capped to 60.
        assert orch._cap_specialist_timeout(remaining_budget=100.0) == 1200

    def test_falls_back_when_sdk_timeout_unset(
        self, worktree_path, mock_worktree
    ):
        """Defensive: if sdk_timeout is None, treat base as 1200."""
        orch = self._orchestrator(worktree_path, mock_worktree, sdk_timeout=1200)
        orch.sdk_timeout = None  # simulate missing config
        # No budget → base 1200
        assert orch._cap_specialist_timeout(remaining_budget=None) == 1200
        # Ample budget → still base
        assert orch._cap_specialist_timeout(remaining_budget=2400.0) == 1200


# ============================================================================
# Tests: post-Player budget refresh before pre-specialist guard (TASK-ABSR-FRSH)
# ============================================================================


class TestPostPlayerBudgetRefresh:
    """Pre-specialist guard recomputes remaining_budget from loop_start_time.

    The value threaded into ``_execute_turn`` via ``remaining_budget`` is the
    start-of-turn budget. The Player phase can consume substantial wall
    before the pre-specialist guard runs, so the guard re-derives
    ``post_player_remaining`` from ``self._task_timeout - (time.monotonic() -
    self._loop_start_time)`` and uses that for the
    ``MIN_TURN_BUDGET_SECONDS`` comparison (TASK-ABSR-FRSH, R3).
    """

    def test_post_player_budget_refresh_triggers_skip(
        self, worktree_path, mock_worktree
    ):
        """Stale start-of-turn budget passes the guard, post-Player refresh
        catches it: ``specialist_skipped: budget exhausted`` is emitted with
        the recomputed value, not the stale start-of-turn value.

        Setup:
          - ``_task_timeout`` = 2400s (turn budget)
          - ``_loop_start_time`` = 0.0
          - Player phase consumes wall: ``time.monotonic`` returns 1900.0
            when the post-Player guard runs.
          - ``remaining_budget`` (start-of-turn) = 1500.0 — comfortably
            above ``MIN_TURN_BUDGET_SECONDS`` (600), so the OLD code would
            NOT have skipped specialists.
          - post_player_remaining = 2400 - 1900 = 500.0 — below 600, so
            the NEW code MUST skip specialists.

        Asserts:
          AC-002: post-Player computation triggers the skip path.
          AC-003: emitted error message contains the recomputed value
                  ("post_player_remaining=500"), not the stale start-of-turn
                  value (1500).
        """
        orchestrator = _make_orchestrator(worktree_path, mock_worktree)

        # Override the default "direct" mode so the orchestrator-side
        # Phase 4/5 budget guard actually runs.
        orchestrator._agent_invoker._get_implementation_mode.return_value = (
            "task-work"
        )
        orchestrator._agent_invoker._inject_specialist_records_into_task_work_results = (
            Mock()
        )

        orchestrator._task_timeout = 2400
        orchestrator._loop_start_time = 0.0

        stale_remaining_budget = 1500.0  # well above MIN_TURN_BUDGET_SECONDS

        player_success = _make_player_result(success=True)

        captured_blocks: List[Dict[str, Any]] = []

        def fake_merge(path, phase, block):
            captured_blocks.append(
                {"path": path, "phase": phase, "block": block}
            )

        with patch.object(
            orchestrator, "_invoke_player_safely", return_value=player_success
        ), patch.object(
            orchestrator,
            "_invoke_coach_safely",
            return_value=_make_coach_result(),
        ), patch.object(
            orchestrator, "_build_player_summary", return_value="ok"
        ), patch(
            "guardkit.orchestrator.specialist_invocations._merge_specialist_block",
            side_effect=fake_merge,
        ), patch(
            "guardkit.orchestrator.autobuild.time"
        ) as mock_time:
            # Player has consumed 1900s of wall by the time the
            # post-Player guard reads the clock.
            mock_time.monotonic = Mock(return_value=1900.0)

            orchestrator._execute_turn(
                turn=1,
                task_id="TASK-AB-001",
                requirements="do stuff",
                worktree=mock_worktree,
                previous_feedback=None,
                remaining_budget=stale_remaining_budget,
            )

        # AC-002: a phase_4 specialist_skipped block was written.
        skip_blocks = [b for b in captured_blocks if b["phase"] == "phase_4"]
        assert len(skip_blocks) == 1, (
            f"expected one phase_4 skip block, got {captured_blocks!r}"
        )
        block = skip_blocks[0]["block"]
        assert block["status"] == "skipped"

        # AC-003: error references post_player_remaining, not the stale
        # start-of-turn value.
        error = block["error"]
        assert "specialist_skipped: budget exhausted" in error
        assert "post_player_remaining=500" in error, (
            f"expected post_player_remaining=500 in error, got {error!r}"
        )
        # The stale start-of-turn value (1500) MUST NOT appear in the
        # message — that is the bug this fix prevents.
        assert "1500" not in error, (
            f"stale start-of-turn budget leaked into error: {error!r}"
        )

    def test_post_player_budget_passes_when_wall_remaining(
        self, worktree_path, mock_worktree
    ):
        """When Player consumed little wall, the recomputed budget still
        exceeds ``MIN_TURN_BUDGET_SECONDS`` and specialists run normally
        (no skip block written).
        """
        orchestrator = _make_orchestrator(worktree_path, mock_worktree)

        # Force "direct" mode so the orchestrator-side Phase 4/5 block
        # is bypassed entirely after the (passing) budget guard. This
        # keeps the test focused on the guard rather than the
        # specialist invocation machinery.
        orchestrator._agent_invoker._get_implementation_mode.return_value = (
            "direct"
        )

        orchestrator._task_timeout = 2400
        orchestrator._loop_start_time = 0.0

        player_success = _make_player_result(success=True)

        captured_blocks: List[Dict[str, Any]] = []

        def fake_merge(path, phase, block):
            captured_blocks.append(
                {"path": path, "phase": phase, "block": block}
            )

        with patch.object(
            orchestrator, "_invoke_player_safely", return_value=player_success
        ), patch.object(
            orchestrator,
            "_invoke_coach_safely",
            return_value=_make_coach_result(),
        ), patch.object(
            orchestrator, "_build_player_summary", return_value="ok"
        ), patch(
            "guardkit.orchestrator.specialist_invocations._merge_specialist_block",
            side_effect=fake_merge,
        ), patch(
            "guardkit.orchestrator.autobuild.time"
        ) as mock_time:
            # Only 100s of wall consumed — comfortable headroom.
            mock_time.monotonic = Mock(return_value=100.0)

            orchestrator._execute_turn(
                turn=1,
                task_id="TASK-AB-001",
                requirements="do stuff",
                worktree=mock_worktree,
                previous_feedback=None,
                remaining_budget=2300.0,
            )

        # No phase_4 skip block was written — the guard passed.
        skip_blocks = [
            b
            for b in captured_blocks
            if b["phase"] == "phase_4"
            and b["block"].get("status") == "skipped"
            and "budget exhausted" in str(b["block"].get("error", ""))
        ]
        assert skip_blocks == [], (
            f"unexpected budget-exhausted skip block: {skip_blocks!r}"
        )


# ============================================================================
# Tests: TASK-ABSR-FLOR — task_timeout floor in FeatureOrchestrator
# ============================================================================
#
# Implementation choice (AC-003): option (b) — env-var-driven floor read at
# FeatureOrchestrator.__init__ time. Default `GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR`
# is 3000s. The floor is applied BEFORE the timeout multiplier so these tests
# can assert the floored value directly by pinning `timeout_multiplier=1.0`.


class TestTaskTimeoutFloor:
    """Tests for the 3000s task_timeout floor (TASK-ABSR-FLOR AC-003/AC-005)."""

    def test_task_timeout_floor_applied_when_below_3000(self, tmp_path, monkeypatch):
        """task_timeout=2400 should be floored to 3000 (the binding case from run-3 J004-011)."""
        # Pin a clean env so the floor reads its 3000 default.
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR", raising=False)
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        mock_wm = MagicMock()
        mock_wm.worktrees_dir = tmp_path / "worktrees"

        orchestrator = FeatureOrchestrator(
            repo_root=tmp_path,
            task_timeout=2400,
            timeout_multiplier=1.0,  # pin so floored input is the assertion
            worktree_manager=mock_wm,
        )
        assert orchestrator.task_timeout == 3000

    def test_task_timeout_floor_not_applied_when_above_3000(self, tmp_path, monkeypatch):
        """task_timeout=4000 should remain 4000 — floor only raises low values."""
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR", raising=False)
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        mock_wm = MagicMock()
        mock_wm.worktrees_dir = tmp_path / "worktrees"

        orchestrator = FeatureOrchestrator(
            repo_root=tmp_path,
            task_timeout=4000,
            timeout_multiplier=1.0,
            worktree_manager=mock_wm,
        )
        assert orchestrator.task_timeout == 4000


# ============================================================================
# Tests: TASK-ATR-002 — Phase 5 cap input refreshed between specialists
# ============================================================================


class TestSpecialistBudgetRefresh:
    """Phase 5 ``_cap_specialist_timeout`` input is refreshed after Phase 4.

    The original ``remaining_budget`` is the start-of-turn value and does not
    reflect wall consumed by Phase 4 (test-orchestrator). Reusing it for
    Phase 5 (code-reviewer) over-allocates time Phase 5 doesn't actually have
    and lets the post-specialist Coach validation overrun the feature
    ``task_timeout``. The fix subtracts ``phase4_elapsed`` before computing
    the Phase 5 cap (TASK-ATR-002).
    """

    def _stage_orchestrator(self, worktree_path, mock_worktree, sdk_timeout=1200):
        orch = _make_orchestrator(worktree_path, mock_worktree)
        orch._agent_invoker._get_implementation_mode.return_value = "task-work"
        orch._agent_invoker._inject_specialist_records_into_task_work_results = Mock()
        orch._task_timeout = 2400
        orch._loop_start_time = 0.0
        orch.sdk_timeout = sdk_timeout
        return orch

    def _wrap_cap(self, orchestrator):
        """Wrap ``_cap_specialist_timeout`` so each call's input is captured."""
        cap_inputs: List[Optional[float]] = []
        original_cap = orchestrator._cap_specialist_timeout

        def capture_cap(remaining_budget=None):
            cap_inputs.append(remaining_budget)
            return original_cap(remaining_budget=remaining_budget)

        orchestrator._cap_specialist_timeout = capture_cap
        return cap_inputs

    def test_phase5_cap_input_refreshed_after_phase4_wall(
        self, worktree_path, mock_worktree
    ):
        """Phase 4 takes 200s wall → Phase 5 cap input is start - 200s ± 5s."""
        orchestrator = self._stage_orchestrator(worktree_path, mock_worktree)
        cap_inputs = self._wrap_cap(orchestrator)

        from guardkit.orchestrator import specialist_invocations as _si

        async def fake_invoke_test_orchestrator(**kwargs):
            result = Mock()
            result.status = "passed"
            return result

        async def fake_invoke_code_reviewer(**kwargs):
            return Mock()

        # time.monotonic side-effects (in call order):
        #   1) pre-specialist guard: post_player_remaining = 2400 - 0 = 2400 (passes)
        #   2) _phase4_start: 0.0
        #   3) post-Phase-4 elapsed read: 200.0  → elapsed = 200s
        time_seq = [0.0, 0.0, 200.0]

        with patch.object(
            orchestrator,
            "_invoke_player_safely",
            return_value=_make_player_result(success=True),
        ), patch.object(
            orchestrator,
            "_invoke_coach_safely",
            return_value=_make_coach_result(),
        ), patch.object(
            orchestrator, "_build_player_summary", return_value="ok"
        ), patch.object(
            _si, "invoke_test_orchestrator", side_effect=fake_invoke_test_orchestrator
        ), patch.object(
            _si, "invoke_code_reviewer", side_effect=fake_invoke_code_reviewer
        ), patch(
            "guardkit.orchestrator.autobuild.time"
        ) as mock_time:
            mock_time.monotonic = Mock(side_effect=time_seq)

            orchestrator._execute_turn(
                turn=1,
                task_id="TASK-AB-001",
                requirements="do stuff",
                worktree=mock_worktree,
                previous_feedback=None,
                remaining_budget=2000.0,
            )

        # Two cap calls: Phase 4, Phase 5
        assert len(cap_inputs) == 2, f"expected 2 cap calls, got {cap_inputs!r}"
        # Phase 4 uses the start-of-turn budget unchanged
        assert cap_inputs[0] == 2000.0
        # Phase 5 cap input is start_budget - phase4_elapsed (within 5s tolerance)
        phase5_input = cap_inputs[1]
        assert phase5_input is not None
        assert abs(phase5_input - (2000.0 - 200.0)) < 5.0, (
            f"expected Phase 5 cap input ~1800.0, got {phase5_input}"
        )

    def test_phase5_remaining_is_none_when_remaining_budget_is_none(
        self, worktree_path, mock_worktree
    ):
        """remaining_budget=None → Phase 5 also receives None (no double-default)."""
        orchestrator = self._stage_orchestrator(worktree_path, mock_worktree)
        # Disable the post-Player budget guard by clearing _task_timeout so
        # the guard short-circuits to remaining_budget (which is None) and
        # skips the time.monotonic computation. budget_ok is then True
        # (post_player_remaining is None) so Phase 4/5 still run.
        orchestrator._task_timeout = None
        cap_inputs = self._wrap_cap(orchestrator)

        from guardkit.orchestrator import specialist_invocations as _si

        async def fake_invoke_test_orchestrator(**kwargs):
            result = Mock()
            result.status = "passed"
            return result

        async def fake_invoke_code_reviewer(**kwargs):
            return Mock()

        with patch.object(
            orchestrator,
            "_invoke_player_safely",
            return_value=_make_player_result(success=True),
        ), patch.object(
            orchestrator,
            "_invoke_coach_safely",
            return_value=_make_coach_result(),
        ), patch.object(
            orchestrator, "_build_player_summary", return_value="ok"
        ), patch.object(
            _si, "invoke_test_orchestrator", side_effect=fake_invoke_test_orchestrator
        ), patch.object(
            _si, "invoke_code_reviewer", side_effect=fake_invoke_code_reviewer
        ):
            orchestrator._execute_turn(
                turn=1,
                task_id="TASK-AB-001",
                requirements="do stuff",
                worktree=mock_worktree,
                previous_feedback=None,
                remaining_budget=None,
            )

        # Both cap calls receive None — the refresh logic must NOT default
        # to a base wall value when budget is unset.
        assert len(cap_inputs) == 2, f"expected 2 cap calls, got {cap_inputs!r}"
        assert cap_inputs[0] is None
        assert cap_inputs[1] is None

    def test_phase5_remaining_floored_at_zero_when_phase4_overruns(
        self, worktree_path, mock_worktree
    ):
        """Phase 4 elapsed > remaining_budget → Phase 5 sees 0.0 (floored)."""
        orchestrator = self._stage_orchestrator(worktree_path, mock_worktree)
        cap_inputs = self._wrap_cap(orchestrator)

        from guardkit.orchestrator import specialist_invocations as _si

        async def fake_invoke_test_orchestrator(**kwargs):
            result = Mock()
            result.status = "passed"
            return result

        async def fake_invoke_code_reviewer(**kwargs):
            return Mock()

        # Phase 4 burns more wall (1500s) than the start-of-turn budget (1000s).
        # phase5_remaining must floor at 0.0, not go negative.
        time_seq = [0.0, 0.0, 1500.0]

        with patch.object(
            orchestrator,
            "_invoke_player_safely",
            return_value=_make_player_result(success=True),
        ), patch.object(
            orchestrator,
            "_invoke_coach_safely",
            return_value=_make_coach_result(),
        ), patch.object(
            orchestrator, "_build_player_summary", return_value="ok"
        ), patch.object(
            _si, "invoke_test_orchestrator", side_effect=fake_invoke_test_orchestrator
        ), patch.object(
            _si, "invoke_code_reviewer", side_effect=fake_invoke_code_reviewer
        ), patch(
            "guardkit.orchestrator.autobuild.time"
        ) as mock_time:
            mock_time.monotonic = Mock(side_effect=time_seq)

            orchestrator._execute_turn(
                turn=1,
                task_id="TASK-AB-001",
                requirements="do stuff",
                worktree=mock_worktree,
                previous_feedback=None,
                remaining_budget=1000.0,
            )

        assert len(cap_inputs) == 2
        # Phase 5 receives the 0.0 floor, not a negative value.
        assert cap_inputs[1] == 0.0
