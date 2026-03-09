"""
Unit Tests for SDK Session Resume (TASK-RFX-B20B)

Tests session_id capture from ResultMessage, resume kwarg passing
via ClaudeAgentOptions, and session_id propagation through all
invoke_player() return paths.

Coverage Target: >=85%
Test Count: 12 tests
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker, AgentInvocationResult


# ============================================================================
# Fixtures
# ============================================================================

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


def _make_result_message(session_id="sess-abc123def456"):
    """Return a mock ResultMessage with session_id attribute."""
    msg = MagicMock()
    msg.session_id = session_id
    msg.num_turns = 3
    type(msg).__name__ = "ResultMessage"
    return msg


# ============================================================================
# 1. set_player_resume_session Tests (3 tests)
# ============================================================================


class TestSetPlayerResumeSession:
    """Tests for the session ID setter method."""

    def test_set_session_id(self, agent_invoker):
        """Setting a session ID stores it for resume."""
        agent_invoker.set_player_resume_session("sess-abc123")
        assert agent_invoker._last_session_id == "sess-abc123"

    def test_clear_session_id(self, agent_invoker):
        """Setting None clears the session ID."""
        agent_invoker.set_player_resume_session("sess-abc123")
        agent_invoker.set_player_resume_session(None)
        assert agent_invoker._last_session_id is None

    def test_initial_session_id_is_none(self, agent_invoker):
        """Session ID starts as None (no resume on first invocation)."""
        assert agent_invoker._last_session_id is None


# ============================================================================
# 2. _invoke_with_role: session_id capture from ResultMessage (3 tests)
# ============================================================================


class TestInvokeWithRoleSessionCapture:
    """Tests for session_id capture inside _invoke_with_role."""

    @pytest.mark.asyncio
    async def test_captures_session_id_from_result_message(self, agent_invoker):
        """ResultMessage.session_id is stored in _last_session_id."""
        result_msg = _make_result_message("sess-captured-id-12345678")

        async def _query_with_result(*args, **kwargs):
            yield result_msg

        sdk_mock = _make_sdk_module_mock()
        sdk_mock.query = _query_with_result
        sdk_mock.ResultMessage = type(result_msg)

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
            await agent_invoker._invoke_with_role(
                prompt="TASK-RFX-B20B: test prompt",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
            )

        assert agent_invoker._last_session_id == "sess-captured-id-12345678"

    @pytest.mark.asyncio
    async def test_resume_kwarg_passed_to_options(self, agent_invoker):
        """When resume_session_id is provided, ClaudeAgentOptions receives resume kwarg."""
        agent_invoker.set_player_resume_session("sess-prior-session")
        result_msg = _make_result_message("sess-new-session")

        captured_options_kwargs = {}

        async def _query_with_result(*args, **kwargs):
            yield result_msg

        sdk_mock = _make_sdk_module_mock()
        sdk_mock.query = _query_with_result
        sdk_mock.ResultMessage = type(result_msg)

        # Capture kwargs passed to ClaudeAgentOptions
        original_init = sdk_mock.ClaudeAgentOptions
        def capture_options(**kwargs):
            captured_options_kwargs.update(kwargs)
            return original_init(**kwargs)
        sdk_mock.ClaudeAgentOptions = capture_options

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
            await agent_invoker._invoke_with_role(
                prompt="TASK-RFX-B20B: test prompt",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
                resume_session_id="sess-prior-session",
            )

        assert captured_options_kwargs.get("resume") == "sess-prior-session"

    @pytest.mark.asyncio
    async def test_no_resume_kwarg_when_session_id_is_none(self, agent_invoker):
        """When resume_session_id is None, resume kwarg is not in options."""
        result_msg = _make_result_message("sess-new-session")

        captured_options_kwargs = {}

        async def _query_with_result(*args, **kwargs):
            yield result_msg

        sdk_mock = _make_sdk_module_mock()
        sdk_mock.query = _query_with_result
        sdk_mock.ResultMessage = type(result_msg)

        original_init = sdk_mock.ClaudeAgentOptions
        def capture_options(**kwargs):
            captured_options_kwargs.update(kwargs)
            return original_init(**kwargs)
        sdk_mock.ClaudeAgentOptions = capture_options

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
            await agent_invoker._invoke_with_role(
                prompt="TASK-RFX-B20B: test prompt",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
                resume_session_id=None,
            )

        assert "resume" not in captured_options_kwargs


# ============================================================================
# 3. _invoke_with_role: session_id scan on CancelledError (1 test)
# ============================================================================


class TestInvokeWithRoleCancelledSessionScan:
    """Test session_id extraction from accumulated messages on CancelledError."""

    @pytest.mark.asyncio
    async def test_captures_session_id_on_cancelled_error(self, agent_invoker):
        """When CancelledError occurs, scan messages for ResultMessage with session_id.

        The CancelledError scan path activates when messages are accumulated
        but the isinstance(message, ResultMessage) check in the loop doesn't
        match (different class identity). The scan uses type(msg).__name__
        to find ResultMessage objects and extract session_id.
        """
        # Create a ResultMessage-like object that WON'T pass isinstance()
        # check in the stream loop (different class identity from SDK mock),
        # but WILL match type(msg).__name__ == "ResultMessage" in the scan.
        ResultMessageClass = type("ResultMessage", (), {})
        partial_msg = ResultMessageClass()
        partial_msg.session_id = "sess-partial-cancel"
        partial_msg.content = []

        async def _query_then_cancel(*args, **kwargs):
            # Yield a message that won't be caught by isinstance(msg, ResultMessage)
            yield partial_msg
            raise asyncio.CancelledError("test cancellation")

        sdk_mock = _make_sdk_module_mock()
        sdk_mock.query = _query_then_cancel
        # SDK's ResultMessage is a different class from our partial_msg,
        # so isinstance check won't match in the stream loop
        sdk_mock.ResultMessage = MagicMock

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
            # _invoke_with_role re-raises CancelledError after extracting data
            with pytest.raises(asyncio.CancelledError):
                await agent_invoker._invoke_with_role(
                    prompt="TASK-RFX-B20B: test prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                )

        assert agent_invoker._last_session_id == "sess-partial-cancel"


# ============================================================================
# 4. invoke_player: session_id propagated in return paths (5 tests)
# ============================================================================


class TestInvokePlayerSessionPropagation:
    """Tests that session_id is propagated in AgentInvocationResult from invoke_player."""

    @pytest.mark.asyncio
    async def test_legacy_success_path_returns_session_id(self, agent_invoker):
        """Legacy direct SDK path returns session_id in AgentInvocationResult."""
        agent_invoker.use_task_work_delegation = False
        agent_invoker._last_session_id = "sess-legacy-success"

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_get_implementation_mode", return_value="task-work"),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(agent_invoker, "_invoke_with_role", new_callable=AsyncMock),
            patch.object(
                agent_invoker,
                "_load_agent_report",
                return_value={"tests_passed": True, "tests_run": 5},
            ),
            patch.object(agent_invoker, "_validate_player_report"),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
            )

        assert result.session_id == "sess-legacy-success"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_cancelled_error_path_returns_session_id(self, agent_invoker):
        """CancelledError path returns session_id in AgentInvocationResult."""
        agent_invoker.use_task_work_delegation = False
        agent_invoker._last_session_id = "sess-cancelled-preserved"

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_get_implementation_mode", return_value="task-work"),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(
                agent_invoker,
                "_invoke_with_role",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError("test"),
            ),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
            )

        assert result.session_id == "sess-cancelled-preserved"
        assert result.success is False
        assert "Cancelled" in result.error

    @pytest.mark.asyncio
    async def test_timeout_error_path_returns_session_id(self, agent_invoker):
        """SDKTimeoutError path returns session_id in AgentInvocationResult."""
        from guardkit.orchestrator.exceptions import SDKTimeoutError

        agent_invoker.use_task_work_delegation = False
        agent_invoker._last_session_id = "sess-timeout-preserved"

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_get_implementation_mode", return_value="task-work"),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(
                agent_invoker,
                "_invoke_with_role",
                new_callable=AsyncMock,
                side_effect=SDKTimeoutError("timeout"),
            ),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
            )

        assert result.session_id == "sess-timeout-preserved"
        assert result.success is False
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_report_not_found_path_returns_session_id(self, agent_invoker):
        """PlayerReportNotFoundError path returns session_id in AgentInvocationResult."""
        from guardkit.orchestrator.exceptions import PlayerReportNotFoundError

        agent_invoker.use_task_work_delegation = False
        agent_invoker._last_session_id = "sess-report-missing"

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_get_implementation_mode", return_value="task-work"),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(agent_invoker, "_invoke_with_role", new_callable=AsyncMock),
            patch.object(
                agent_invoker,
                "_load_agent_report",
                side_effect=PlayerReportNotFoundError("not found"),
            ),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
            )

        assert result.session_id == "sess-report-missing"
        assert result.success is False

    @pytest.mark.asyncio
    async def test_task_work_success_path_returns_session_id(self, agent_invoker):
        """Task-work delegation success path returns session_id from TaskWorkResult."""
        from guardkit.orchestrator.exceptions import TaskWorkResult

        agent_invoker.use_task_work_delegation = True
        tw_result = TaskWorkResult(
            success=True,
            output={"tests_passed": True},
            session_id="sess-taskwork-success",
            sdk_turns_used=10,
            sdk_max_turns=50,
        )

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_get_implementation_mode", return_value="task-work"),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(agent_invoker, "_ensure_design_approved_state"),
            patch.object(
                agent_invoker,
                "_invoke_task_work_implement",
                new_callable=AsyncMock,
                return_value=tw_result,
            ),
            patch.object(agent_invoker, "_create_player_report_from_task_work"),
            patch.object(
                agent_invoker,
                "_load_agent_report",
                return_value={"tests_passed": True},
            ),
            patch.object(agent_invoker, "_validate_player_report"),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
            )

        assert result.session_id == "sess-taskwork-success"
        assert result.success is True


# ============================================================================
# 5. _invoke_player_direct error paths return session_id (2 tests)
# ============================================================================


class TestInvokePlayerDirectErrorPaths:
    """Tests that _invoke_player_direct error paths include session_id."""

    @pytest.mark.asyncio
    async def test_direct_timeout_error_returns_session_id(self, agent_invoker):
        """SDKTimeoutError in _invoke_player_direct returns session_id."""
        from guardkit.orchestrator.exceptions import SDKTimeoutError

        agent_invoker._last_session_id = "sess-direct-timeout"

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_get_implementation_mode", return_value="direct"),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(
                agent_invoker,
                "_invoke_with_role",
                new_callable=AsyncMock,
                side_effect=SDKTimeoutError("timeout in direct mode"),
            ),
            patch.object(agent_invoker, "_write_direct_mode_results"),
            patch.object(agent_invoker, "_write_player_report_for_direct_mode"),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-TEST-DIRECT",
                turn=1,
                requirements="Direct mode test",
            )

        assert result.session_id == "sess-direct-timeout"
        assert result.success is False
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_direct_unexpected_error_returns_session_id(self, agent_invoker):
        """Unexpected Exception in _invoke_player_direct returns session_id."""
        agent_invoker._last_session_id = "sess-direct-error"

        with (
            patch.object(agent_invoker, "_record_baseline"),
            patch.object(agent_invoker, "_calculate_sdk_timeout", return_value=60),
            patch.object(agent_invoker, "_get_implementation_mode", return_value="direct"),
            patch.object(agent_invoker, "_write_turn_context"),
            patch.object(agent_invoker, "_build_player_prompt", return_value="prompt"),
            patch.object(
                agent_invoker,
                "_invoke_with_role",
                new_callable=AsyncMock,
                side_effect=RuntimeError("unexpected failure"),
            ),
            patch.object(agent_invoker, "_write_direct_mode_results"),
            patch.object(agent_invoker, "_write_player_report_for_direct_mode"),
        ):
            result = await agent_invoker.invoke_player(
                task_id="TASK-TEST-DIRECT",
                turn=1,
                requirements="Direct mode test",
            )

        assert result.session_id == "sess-direct-error"
        assert result.success is False
        assert "unexpected" in result.error.lower()
