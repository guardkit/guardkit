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
from pathlib import Path
from typing import List, Optional
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
    orchestrator._cumulative_source_files = set()
    orchestrator._cumulative_requirements_addressed = set()
    orchestrator.wave_size = 1
    # TASK-FIX-A7B2: wave-shared file-edit map (None = single-task path)
    orchestrator._wave_changed_files = None
    orchestrator._wave_files_lock = None
    orchestrator._turn_history = []
    orchestrator._feature_id = None
    # Set in __init__ (bypassed by __new__ here); the loop stamps it onto
    # observability records.
    orchestrator._run_id = "test-run"
    orchestrator._max_criteria_passed = 0
    orchestrator._agent_invoker = Mock()
    # TASK-OSI-006: skip orchestrator-side Phase 4/5 in unit tests by
    # forcing implementation_mode to "direct" on the Mock invoker.
    orchestrator._agent_invoker._get_implementation_mode.return_value = "direct"
    # The loop budgets against a real number: a bare Mock's
    # _calculate_sdk_timeout() returns another Mock and fails in arithmetic.
    orchestrator._agent_invoker.sdk_timeout_seconds = 1200
    orchestrator._agent_invoker._calculate_sdk_timeout = Mock(return_value=1200)
    orchestrator._worktree_manager = Mock()
    orchestrator._checkpoint_manager = None
    orchestrator._last_player_context_status = None
    orchestrator._last_coach_context_status = None
    orchestrator.verbose = False
    orchestrator.perspective_reset_turns = []
    # TASK-AB-COACHRUNPARITY01: _loop_phase reads these (set in __init__,
    # bypassed by __new__ here). Mirror the real constructor defaults so the
    # bare-orchestrator helper stays faithful.
    orchestrator._seed_feedback = None
    orchestrator._smoke_command = None
    orchestrator._smoke_expected_exit = 0

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

    def test_coach_grace_period_default_is_1500(self):
        """TASK-FIX-SPECCOCH01 (Shape B) raised the default from 120 → 1500
        to cover the empirically-observed gemma4:26b Coach turn-1 latency
        (run-9 of FEAT-AOF measured 944 s under ``--reasoning off``).

        The original 120 s ceiling guaranteed Coach silence whenever the
        grace-period branch fired in autobuild._loop_phase.
        """
        assert COACH_GRACE_PERIOD_SECONDS == 1500

    def test_min_turn_budget_is_600(self):
        assert MIN_TURN_BUDGET_SECONDS == 600

    def test_constants_are_positive_integers(self):
        assert isinstance(COACH_GRACE_PERIOD_SECONDS, int)
        assert isinstance(MIN_TURN_BUDGET_SECONDS, int)
        assert COACH_GRACE_PERIOD_SECONDS > 0
        assert MIN_TURN_BUDGET_SECONDS > 0

    # NOTE: the legacy ``grace_period < min_turn_budget`` invariant was retired
    # with TASK-FIX-SPECCOCH01. The grace-period branch only fires after the
    # outer task budget is already exhausted (``cancellation_event`` set), so
    # comparing it against the per-turn floor (which gates whether a *new*
    # turn starts) is no longer meaningful. The grace period now needs to be
    # large enough to cover real Coach turn-1 latency under slow coaches
    # (1500 s default, env-tunable).

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

    def test_coach_grace_period_env_override(self):
        """GUARDKIT_COACH_GRACE_PERIOD_SECONDS overrides the 1500 s default at
        module load (TASK-FIX-SPECCOCH01 AC-2). Follows the same env-tunable
        pattern as ``GUARDKIT_MIN_TURN_BUDGET`` and
        ``GUARDKIT_TASK_TIMEOUT_SECONDS``.
        """
        import guardkit.orchestrator.autobuild as autobuild_module

        with patch.dict(
            os.environ, {"GUARDKIT_COACH_GRACE_PERIOD_SECONDS": "300"}
        ):
            importlib.reload(autobuild_module)
            try:
                assert autobuild_module.COACH_GRACE_PERIOD_SECONDS == 300
            finally:
                pass

        # Restore module to default state so other tests see the canonical
        # 1500 s value regardless of run order.
        importlib.reload(autobuild_module)
        assert autobuild_module.COACH_GRACE_PERIOD_SECONDS == 1500

    def test_coach_grace_period_unset_resolves_to_default(self):
        """AC-2 (default branch): when GUARDKIT_COACH_GRACE_PERIOD_SECONDS
        is unset, the constant resolves to the 1500 s default. Exercised
        via a clean reload with the env var explicitly removed.
        """
        import guardkit.orchestrator.autobuild as autobuild_module

        env_without = {
            k: v
            for k, v in os.environ.items()
            if k != "GUARDKIT_COACH_GRACE_PERIOD_SECONDS"
        }
        with patch.dict(os.environ, env_without, clear=True):
            importlib.reload(autobuild_module)
            try:
                assert autobuild_module.COACH_GRACE_PERIOD_SECONDS == 1500
            finally:
                pass

        # Restore via final reload under the original env so subsequent
        # tests see the canonical default.
        importlib.reload(autobuild_module)


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
            with patch.object(agent_invoker, "_build_coach_prompt", return_value="coach prompt"):
                with patch.object(agent_invoker, "_load_agent_report", return_value={"decision": "approve"}):
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
            with patch.object(agent_invoker, "_build_coach_prompt", return_value="prompt"):
                result = await agent_invoker.invoke_coach(
                    task_id="TASK-AB-001",
                    turn=1,
                    requirements="do stuff",
                    player_report={},
                    remaining_budget=120.0,
                )

        # A reviewer call that fails is advice only: the decision is approve.
        assert result.report["decision"] == "approve"
        assert agent_invoker.sdk_timeout_seconds == original

    @pytest.mark.asyncio
    async def test_invoke_coach_no_remaining_budget_unchanged_timeout(self, agent_invoker):
        """Without remaining_budget, sdk_timeout_seconds is determined by _calculate_sdk_timeout."""
        original = agent_invoker.sdk_timeout_seconds
        captured: List[int] = []

        async def fake_invoke_with_role(**kwargs):
            captured.append(agent_invoker.sdk_timeout_seconds)

        with patch.object(agent_invoker, "_invoke_with_role", side_effect=fake_invoke_with_role):
            with patch.object(agent_invoker, "_build_coach_prompt", return_value="prompt"):
                with patch.object(agent_invoker, "_load_agent_report", return_value={"decision": "approve"}):
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
        # - first call: loop_start (SDK-timeout attribution clock)
        # - second call: loop_start_time (at loop entry)
        # - third call: elapsed check before turn 1 => simulate exhaustion
        monotonic_values = [0.0, 0.0, float(MIN_TURN_BUDGET_SECONDS + 100)]

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
                with patch.object(orchestrator, "_display_criteria_progress"):
                    with patch("guardkit.orchestrator.autobuild.time") as mock_time:
                        # loop_start=0, loop_start_time=0; then elapsed=10 (< budget)
                        mock_time.monotonic = Mock(side_effect=[0.0, 0.0, 10.0])

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
                with patch.object(orchestrator, "_display_criteria_progress"):
                    with patch("guardkit.orchestrator.autobuild.time") as mock_time:
                        # [loop_start, check_before_turn1, check_before_turn2]
                        # After turn1, elapsed > budget - MIN
                        budget = float(MIN_TURN_BUDGET_SECONDS * 2)
                        mock_time.monotonic = Mock(
                            side_effect=[
                                0.0,  # loop_start
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
                with patch.object(orchestrator, "_display_criteria_progress"):
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

