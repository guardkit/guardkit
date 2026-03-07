"""
Unit Tests for CancelledError Guard Points (TASK-CEF-002)

Verifies that asyncio.CancelledError is caught and handled correctly
at each of the 5 guard points in the invocation chain.

Guard Points Tested
-------------------
GP1 - agent_invoker._invoke_with_role      : re-raises after logger.warning
GP2 - agent_invoker.invoke_player          : returns AgentInvocationResult(success=False, error="Cancelled: ...")
GP3 - autobuild._invoke_player_safely      : explicit except before UNRECOVERABLE_ERRORS, returns result with error="Cancelled: ..."
GP5 - feature_orchestrator._execute_task   : returns TaskExecutionResult(final_decision="cancelled")
AC-6 - existing Exception handling preserved: non-CancelledError exceptions still produce original error messages
"""

import asyncio
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker, AgentInvocationResult
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
)


# ============================================================================
# Fixtures
# ============================================================================

# Actual repo root — used for FeatureOrchestrator which needs a real git repo
REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture
def tmp_worktree(tmp_path):
    """Temporary worktree directory for AgentInvoker."""
    wt = tmp_path / "worktree"
    wt.mkdir()
    return wt


@pytest.fixture
def agent_invoker(tmp_worktree):
    """AgentInvoker with minimal configuration for testing."""
    return AgentInvoker(
        worktree_path=tmp_worktree,
        max_turns_per_agent=5,
        sdk_timeout_seconds=60,
    )


@pytest.fixture
def feature_orchestrator():
    """FeatureOrchestrator constructed against the actual git repo root."""
    return FeatureOrchestrator(
        repo_root=REPO_ROOT,
        max_turns=3,
        enable_context=False,
    )


# ============================================================================
# Helpers
# ============================================================================


def _make_sdk_module_mock():
    """Return a minimal mock of the claude_agent_sdk module."""
    sdk = MagicMock()
    sdk.ClaudeAgentOptions = MagicMock(return_value=MagicMock())
    sdk.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
    sdk.ProcessError = type("ProcessError", (Exception,), {})
    sdk.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})
    sdk.AssistantMessage = MagicMock()
    sdk.ResultMessage = MagicMock()
    return sdk


def _make_latency_ctx():
    """Return a synchronous context manager mock for measure_latency."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=MagicMock(ms=0))
    ctx.__exit__ = Mock(return_value=False)
    return ctx


def _make_heartbeat_ctx():
    """Return an async context manager mock for async_heartbeat."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _make_agent_invoker_mock():
    """
    Return a MagicMock for AgentInvoker where invoke_player is an AsyncMock.

    This is required for GP3 tests: _invoke_player_safely calls
    self._agent_invoker.invoke_player(...) to create a coroutine, which is
    then passed to loop.run_until_complete(). The coroutine must be created
    without raising so run_until_complete can intercept execution.
    """
    mock_invoker = MagicMock()
    mock_invoker.invoke_player = AsyncMock(return_value=MagicMock())
    return mock_invoker


# ============================================================================
# GP1 — _invoke_with_role: CancelledError is logged and re-raised
# ============================================================================


class TestGP1InvokeWithRole:
    """Guard Point 1: _invoke_with_role catches CancelledError, logs it, and re-raises."""

    @pytest.mark.asyncio
    async def test_cancelled_error_is_reraised(self, agent_invoker):
        """CancelledError raised inside _invoke_with_role bubbles up to the caller."""

        async def _raising_query(*args, **kwargs):
            raise asyncio.CancelledError("test cancellation")
            yield  # make it an async generator (never reached)

        sdk_mock = _make_sdk_module_mock()
        sdk_mock.query = _raising_query

        with (
            patch.dict("sys.modules", {"claude_agent_sdk": sdk_mock}),
            patch(
                "guardkit.orchestrator.agent_invoker.measure_latency",
                return_value=_make_latency_ctx(),
            ),
            patch(
                "guardkit.orchestrator.agent_invoker.async_heartbeat",
                return_value=_make_heartbeat_ctx(),
            ),
            patch(
                "guardkit.orchestrator.sdk_utils.check_assistant_message_error",
                return_value=None,
            ),
            patch("guardkit.orchestrator.agent_invoker._install_sdk_cleanup_handler"),
            patch.object(agent_invoker, "_emit_llm_call_event"),
        ):
            with pytest.raises(asyncio.CancelledError):
                await agent_invoker._invoke_with_role(
                    prompt="TASK-CEF-002: test prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                )

    @pytest.mark.asyncio
    async def test_cancelled_error_triggers_logger_warning(self, agent_invoker):
        """CancelledError at _invoke_with_role emits a logger.warning mentioning the guard point."""

        async def _raising_query(*args, **kwargs):
            raise asyncio.CancelledError("gp1-cancellation")
            yield

        sdk_mock = _make_sdk_module_mock()
        sdk_mock.query = _raising_query

        with (
            patch.dict("sys.modules", {"claude_agent_sdk": sdk_mock}),
            patch(
                "guardkit.orchestrator.agent_invoker.measure_latency",
                return_value=_make_latency_ctx(),
            ),
            patch(
                "guardkit.orchestrator.agent_invoker.async_heartbeat",
                return_value=_make_heartbeat_ctx(),
            ),
            patch(
                "guardkit.orchestrator.sdk_utils.check_assistant_message_error",
                return_value=None,
            ),
            patch("guardkit.orchestrator.agent_invoker._install_sdk_cleanup_handler"),
            patch.object(agent_invoker, "_emit_llm_call_event"),
            patch("guardkit.orchestrator.agent_invoker.logger") as mock_logger,
        ):
            with pytest.raises(asyncio.CancelledError):
                await agent_invoker._invoke_with_role(
                    prompt="TASK-CEF-002: test prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                )

            warning_calls = mock_logger.warning.call_args_list
            assert any(
                "_invoke_with_role" in str(call) for call in warning_calls
            ), (
                f"Expected logger.warning to mention '_invoke_with_role' but got: "
                f"{warning_calls}"
            )


# ============================================================================
# GP2 — invoke_player: CancelledError returns AgentInvocationResult(success=False)
# ============================================================================


class TestGP2InvokePlayer:
    """Guard Point 2: invoke_player catches CancelledError and returns failure result."""

    @pytest.mark.asyncio
    async def test_cancelled_error_returns_failure_result(self, agent_invoker):
        """CancelledError in invoke_player returns AgentInvocationResult with success=False."""
        agent_invoker.use_task_work_delegation = False

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(
                agent_invoker, "_get_implementation_mode", return_value="standard"
            ),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(
                agent_invoker,
                "_invoke_with_role",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError("player-cancelled"),
            ),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-CEF-002",
                turn=1,
                requirements="test requirements",
            )

        assert isinstance(result, AgentInvocationResult)
        assert result.success is False
        assert result.task_id == "TASK-CEF-002"
        assert result.turn == 1
        assert result.agent_type == "player"

    @pytest.mark.asyncio
    async def test_cancelled_error_message_format(self, agent_invoker):
        """CancelledError in invoke_player sets error to 'Cancelled: ...'."""
        agent_invoker.use_task_work_delegation = False

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(
                agent_invoker, "_get_implementation_mode", return_value="standard"
            ),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(
                agent_invoker,
                "_invoke_with_role",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError("explicit cancellation message"),
            ),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-CEF-002",
                turn=1,
                requirements="test requirements",
            )

        assert result.error is not None
        assert result.error.startswith("Cancelled:"), (
            f"Expected error starting with 'Cancelled:' but got: {result.error!r}"
        )

    @pytest.mark.asyncio
    async def test_cancelled_error_triggers_logger_warning(self, agent_invoker):
        """CancelledError in invoke_player emits a logger.warning mentioning the guard point."""
        agent_invoker.use_task_work_delegation = False

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(
                agent_invoker, "_get_implementation_mode", return_value="standard"
            ),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(
                agent_invoker,
                "_invoke_with_role",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError("gp2-cancellation"),
            ),
            patch("guardkit.orchestrator.agent_invoker.logger") as mock_logger,
        ):
            await agent_invoker.invoke_player(
                task_id="TASK-CEF-002",
                turn=1,
                requirements="test requirements",
            )

            warning_calls = mock_logger.warning.call_args_list
            assert any(
                "invoke_player" in str(call) for call in warning_calls
            ), (
                f"Expected logger.warning to mention 'invoke_player' but got: "
                f"{warning_calls}"
            )

    @pytest.mark.asyncio
    async def test_non_cancelled_exception_produces_unexpected_error_message(
        self, agent_invoker
    ):
        """AC-6: Non-CancelledError exceptions still produce 'Unexpected error: ...' message."""
        agent_invoker.use_task_work_delegation = False

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(
                agent_invoker, "_get_implementation_mode", return_value="standard"
            ),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(
                agent_invoker,
                "_invoke_with_role",
                new_callable=AsyncMock,
                side_effect=RuntimeError("something went wrong"),
            ),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-CEF-002",
                turn=1,
                requirements="test requirements",
            )

        assert result.success is False
        assert result.error is not None
        assert result.error.startswith("Unexpected error:"), (
            f"Expected 'Unexpected error:' prefix but got: {result.error!r}"
        )
        assert "something went wrong" in result.error


# ============================================================================
# GP3 — _invoke_player_safely: CancelledError returns result before UNRECOVERABLE_ERRORS
# ============================================================================


class TestGP3InvokePlayerSafely:
    """Guard Point 3: _invoke_player_safely catches CancelledError explicitly."""

    def _make_autobuild_orchestrator(self, tmp_path):
        """
        Create a minimal AutoBuildOrchestrator with WorktreeManager mocked
        so construction does not touch the file system.

        The _agent_invoker is set to a proper MagicMock with invoke_player
        as an AsyncMock so that calling invoke_player(...) produces a coroutine
        object rather than raising AttributeError. This allows run_until_complete
        to be intercepted cleanly by side_effect.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        with patch("guardkit.orchestrator.autobuild.WorktreeManager"):
            orchestrator = AutoBuildOrchestrator(
                repo_root=tmp_path,
                max_turns=3,
                enable_pre_loop=False,
                enable_context=False,
            )

        # Assign a proper mock so invoke_player(...) returns a coroutine
        orchestrator._agent_invoker = _make_agent_invoker_mock()
        return orchestrator

    def _run_invoke_player_safely(
        self, orchestrator, mock_loop_side_effect
    ):
        """
        Execute _invoke_player_safely with a mocked event loop whose
        run_until_complete raises the given side_effect.

        Patches asyncio.get_event_loop at the autobuild module level so
        the code's `asyncio.get_event_loop()` call uses our mock loop.
        """
        mock_loop = MagicMock()
        mock_loop.run_until_complete.side_effect = mock_loop_side_effect

        with patch("asyncio.get_event_loop", return_value=mock_loop):
            return orchestrator._invoke_player_safely(
                task_id="TASK-CEF-002",
                turn=1,
                requirements="test requirements",
                feedback=None,
            )

    def test_cancelled_error_returns_failure_result(self, tmp_path):
        """CancelledError in _invoke_player_safely returns AgentInvocationResult(success=False)."""
        orchestrator = self._make_autobuild_orchestrator(tmp_path)

        result = self._run_invoke_player_safely(
            orchestrator,
            mock_loop_side_effect=asyncio.CancelledError("safely-cancelled"),
        )

        assert isinstance(result, AgentInvocationResult)
        assert result.success is False
        assert result.task_id == "TASK-CEF-002"
        assert result.turn == 1

    def test_cancelled_error_message_format(self, tmp_path):
        """CancelledError in _invoke_player_safely sets error field to 'Cancelled: ...'."""
        orchestrator = self._make_autobuild_orchestrator(tmp_path)

        result = self._run_invoke_player_safely(
            orchestrator,
            mock_loop_side_effect=asyncio.CancelledError("gp3-msg"),
        )

        assert result.error is not None
        assert result.error.startswith("Cancelled:"), (
            f"Expected error starting with 'Cancelled:' but got: {result.error!r}"
        )

    def test_cancelled_error_triggers_logger_warning(self, tmp_path):
        """CancelledError in _invoke_player_safely emits logger.warning with guard point name."""
        orchestrator = self._make_autobuild_orchestrator(tmp_path)

        mock_loop = MagicMock()
        mock_loop.run_until_complete.side_effect = asyncio.CancelledError("gp3-warning")

        with (
            patch("asyncio.get_event_loop", return_value=mock_loop),
            patch("guardkit.orchestrator.autobuild.logger") as mock_logger,
        ):
            orchestrator._invoke_player_safely(
                task_id="TASK-CEF-002",
                turn=1,
                requirements="test requirements",
                feedback=None,
            )

            warning_calls = mock_logger.warning.call_args_list
            assert any(
                "_invoke_player_safely" in str(call) for call in warning_calls
            ), (
                f"Expected logger.warning to mention '_invoke_player_safely' but got: "
                f"{warning_calls}"
            )

    def test_non_cancelled_exception_produces_recoverable_error(self, tmp_path):
        """AC-6: Non-CancelledError exceptions go through the recoverable-error path."""
        orchestrator = self._make_autobuild_orchestrator(tmp_path)

        result = self._run_invoke_player_safely(
            orchestrator,
            mock_loop_side_effect=ValueError("recoverable-gp3"),
        )

        assert result.success is False
        assert result.error is not None
        # Non-CancelledError must NOT produce "Cancelled:" prefix
        assert not result.error.startswith("Cancelled:"), (
            f"Generic error should NOT start with 'Cancelled:' but got: {result.error!r}"
        )
        assert "recoverable-gp3" in result.error


# ============================================================================
# GP5 — _execute_task: CancelledError returns TaskExecutionResult(final_decision="cancelled")
# ============================================================================


class TestGP5ExecuteTask:
    """Guard Point 5: _execute_task catches CancelledError and returns final_decision='cancelled'."""

    def _make_feature_task(self):
        """Create a minimal FeatureTask."""
        from guardkit.orchestrator.feature_loader import FeatureTask

        return FeatureTask(id="TASK-CEF-002")

    def _make_feature(self):
        """Create a minimal Feature."""
        from guardkit.orchestrator.feature_loader import Feature

        return Feature(id="FEAT-CEF1", name="test feature")

    def _make_worktree(self, tmp_path):
        """Create a minimal Worktree."""
        from guardkit.worktrees.manager import Worktree

        wt_path = tmp_path / "worktree"
        wt_path.mkdir(exist_ok=True)
        return Worktree(
            task_id="TASK-CEF-002",
            branch_name="autobuild/TASK-CEF-002",
            path=wt_path,
            base_branch="main",
        )

    def test_cancelled_error_returns_cancelled_decision(
        self, tmp_path, feature_orchestrator
    ):
        """CancelledError in _execute_task returns TaskExecutionResult with final_decision='cancelled'."""
        task = self._make_feature_task()
        feature = self._make_feature()
        worktree = self._make_worktree(tmp_path)

        # AutoBuildOrchestrator constructor raises CancelledError — simulates cancellation
        # propagating from within the task orchestration.
        with patch(
            "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator",
            side_effect=asyncio.CancelledError("gp5-cancellation"),
        ):
            result = feature_orchestrator._execute_task(
                task=task,
                feature=feature,
                worktree=worktree,
            )

        assert isinstance(result, TaskExecutionResult)
        assert result.task_id == "TASK-CEF-002"
        assert result.final_decision == "cancelled"
        assert result.success is False
        assert result.total_turns == 0

    def test_cancelled_error_triggers_logger_warning(
        self, tmp_path, feature_orchestrator
    ):
        """CancelledError in _execute_task emits logger.warning mentioning the guard point."""
        task = self._make_feature_task()
        feature = self._make_feature()
        worktree = self._make_worktree(tmp_path)

        with (
            patch(
                "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator",
                side_effect=asyncio.CancelledError("gp5-warning"),
            ),
            patch(
                "guardkit.orchestrator.feature_orchestrator.logger"
            ) as mock_logger,
        ):
            feature_orchestrator._execute_task(
                task=task,
                feature=feature,
                worktree=worktree,
            )

            warning_calls = mock_logger.warning.call_args_list
            assert any(
                "_execute_task" in str(call) for call in warning_calls
            ), (
                f"Expected logger.warning to mention '_execute_task' but got: "
                f"{warning_calls}"
            )

    def test_non_cancelled_exception_returns_error_decision(
        self, tmp_path, feature_orchestrator
    ):
        """AC-6: Non-CancelledError exceptions in _execute_task return final_decision='error'."""
        task = self._make_feature_task()
        feature = self._make_feature()
        worktree = self._make_worktree(tmp_path)

        with patch(
            "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator",
            side_effect=RuntimeError("non-cancelled-gp5"),
        ):
            result = feature_orchestrator._execute_task(
                task=task,
                feature=feature,
                worktree=worktree,
            )

        assert isinstance(result, TaskExecutionResult)
        assert result.final_decision == "error"
        assert result.success is False
        assert "non-cancelled-gp5" in (result.error or "")

    def test_cancelled_error_sets_error_field(self, tmp_path, feature_orchestrator):
        """CancelledError in _execute_task populates the error field."""
        task = self._make_feature_task()
        feature = self._make_feature()
        worktree = self._make_worktree(tmp_path)

        with patch(
            "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator",
            side_effect=asyncio.CancelledError("gp5-error-field"),
        ):
            result = feature_orchestrator._execute_task(
                task=task,
                feature=feature,
                worktree=worktree,
            )

        assert result.error is not None
