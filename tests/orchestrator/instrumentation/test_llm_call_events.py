"""Tests for LLM call event emission from _invoke_with_role.

TDD: Tests covering successful emission, error emission, non-blocking behaviour,
NullEmitter default, multiple calls producing distinct events, and zero regression.

The SDK is lazily imported inside _invoke_with_role() so we inject a mock module
into sys.modules["claude_agent_sdk"] before each test.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent


# ============================================================================
# Helpers
# ============================================================================


def _build_mock_sdk() -> ModuleType:
    """Build a fake claude_agent_sdk module with all required exports."""
    mod = ModuleType("claude_agent_sdk")

    class _ResultMessage:
        """Mock ResultMessage."""

    class _AssistantMessage:
        """Mock AssistantMessage."""

    class _CLINotFoundError(Exception):
        pass

    class _ProcessError(Exception):
        def __init__(self, msg: str = "", exit_code: int = 1, stderr: str = ""):
            super().__init__(msg)
            self.exit_code = exit_code
            self.stderr = stderr

    class _CLIJSONDecodeError(Exception):
        pass

    mod.ResultMessage = _ResultMessage  # type: ignore[attr-defined]
    mod.AssistantMessage = _AssistantMessage  # type: ignore[attr-defined]
    mod.CLINotFoundError = _CLINotFoundError  # type: ignore[attr-defined]
    mod.ProcessError = _ProcessError  # type: ignore[attr-defined]
    mod.CLIJSONDecodeError = _CLIJSONDecodeError  # type: ignore[attr-defined]
    mod.ClaudeAgentOptions = MagicMock  # type: ignore[attr-defined]

    return mod


def _make_result_msg(sdk: ModuleType) -> Any:
    """Create a ResultMessage instance with usage data."""
    msg = sdk.ResultMessage()  # type: ignore[attr-defined]
    usage = MagicMock()
    usage.input_tokens = 1000
    usage.output_tokens = 500
    msg.usage = usage
    return msg


def _make_invoker(
    tmp_path: Path,
    emitter: Optional[Any] = None,
    **kwargs: Any,
) -> Any:
    """Create an AgentInvoker with optional emitter for testing."""
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    worktree = tmp_path / "worktree"
    worktree.mkdir(exist_ok=True)

    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=30,
        sdk_timeout_seconds=60,
        emitter=emitter,
        **kwargs,
    )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _patch_cleanup():
    """Disable SDK cleanup handler in all tests."""
    with patch("guardkit.orchestrator.agent_invoker._install_sdk_cleanup_handler"):
        yield


@pytest.fixture(autouse=True)
def _patch_sdk_utils():
    """Patch check_assistant_message_error to return None."""
    with patch(
        "guardkit.orchestrator.sdk_utils.check_assistant_message_error",
        return_value=None,
    ):
        yield


@pytest.fixture
def mock_sdk():
    """Install mock SDK module into sys.modules for the test duration."""
    sdk = _build_mock_sdk()
    original = sys.modules.get("claude_agent_sdk")
    sys.modules["claude_agent_sdk"] = sdk
    yield sdk
    if original is not None:
        sys.modules["claude_agent_sdk"] = original
    else:
        sys.modules.pop("claude_agent_sdk", None)


# ============================================================================
# Test: Successful emission (AC-001)
# ============================================================================


class TestSuccessfulEmission:
    """llm.call event emitted for every successful SDK invocation."""

    @pytest.mark.asyncio
    async def test_emits_event_on_successful_call(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """AC-001: llm.call event emitted for every successful SDK invocation."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)
        result_msg = _make_result_msg(mock_sdk)

        async def fake_query(**kw: Any):
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 implement feature",
            agent_type="player",
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        assert isinstance(event, LLMCallEvent)
        assert event.status == "ok"
        assert event.error_type is None
        assert event.agent_role == "player"

    @pytest.mark.asyncio
    async def test_coach_role_emits_event(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """Events are emitted for coach invocations too."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)
        result_msg = _make_result_msg(mock_sdk)

        async def fake_query(**kw: Any):
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 review",
            agent_type="coach",
            allowed_tools=["Read"],
            permission_mode="bypassPermissions",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        assert emitter.events[0].agent_role == "coach"


# ============================================================================
# Test: Error emission (AC-002)
# ============================================================================


class TestErrorEmission:
    """llm.call event emitted for failed SDK invocations (timeout, API error)."""

    @pytest.mark.asyncio
    async def test_emits_event_on_timeout(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """AC-002: llm.call event emitted for timeout errors."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        async def fake_query(**kw: Any):
            raise asyncio.TimeoutError("timed out")
            yield  # pragma: no cover

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        from guardkit.orchestrator.exceptions import SDKTimeoutError

        with pytest.raises(SDKTimeoutError):
            await invoker._invoke_with_role(
                prompt="TASK-TEST-001 implement feature",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
            )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        assert event.status == "error"
        assert event.error_type == "timeout"
        assert event.latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_emits_event_on_process_error(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """AC-002: llm.call event emitted for ProcessError."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        async def fake_query(**kw: Any):
            raise mock_sdk.ProcessError("process died", exit_code=1, stderr="crash")  # type: ignore[attr-defined]
            yield  # pragma: no cover

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        from guardkit.orchestrator.exceptions import AgentInvocationError

        with pytest.raises(AgentInvocationError):
            await invoker._invoke_with_role(
                prompt="TASK-TEST-001 implement feature",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
            )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        assert event.status == "error"
        assert event.error_type is not None


# ============================================================================
# Test: Required fields (AC-003)
# ============================================================================


class TestRequiredFields:
    """Event includes all required fields."""

    @pytest.mark.asyncio
    async def test_event_includes_all_required_fields(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """AC-003: Event includes run_id, task_id, agent_role, provider, model,
        tokens, latency, prompt_profile, status."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)
        result_msg = _make_result_msg(mock_sdk)

        async def fake_query(**kw: Any):
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 implement feature",
            agent_type="player",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
            model="claude-sonnet-4-20250514",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]

        assert event.run_id is not None and event.run_id != ""
        assert event.task_id is not None
        assert event.agent_role == "player"
        assert event.provider in ("anthropic", "openai", "local-vllm")
        assert event.model == "claude-sonnet-4-20250514"
        assert event.input_tokens >= 0
        assert event.output_tokens >= 0
        assert event.latency_ms >= 0.0
        assert event.prompt_profile is not None
        assert event.status == "ok"
        assert event.timestamp is not None


# ============================================================================
# Test: Non-blocking emission (AC-004)
# ============================================================================


class TestNonBlockingEmission:
    """Event emission is non-blocking (asyncio.create_task)."""

    @pytest.mark.asyncio
    async def test_emission_does_not_block_caller(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """AC-004: Event emission is non-blocking."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)
        result_msg = _make_result_msg(mock_sdk)

        async def fake_query(**kw: Any):
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 implement feature",
            agent_type="player",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
        )
        # After yielding control, event should be delivered
        await asyncio.sleep(0.05)
        assert len(emitter.events) == 1


# ============================================================================
# Test: Emission failure does not propagate (AC-005)
# ============================================================================


class TestEmissionFailureSafe:
    """Emission failure does not propagate to caller."""

    @pytest.mark.asyncio
    async def test_emission_failure_does_not_propagate(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """AC-005: Emission failure does not propagate to caller."""
        failing_emitter = AsyncMock()
        failing_emitter.emit = AsyncMock(side_effect=RuntimeError("NATS down"))

        invoker = _make_invoker(tmp_path, emitter=failing_emitter)
        result_msg = _make_result_msg(mock_sdk)

        async def fake_query(**kw: Any):
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        # Should NOT raise even though emitter.emit() raises
        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 implement feature",
            agent_type="player",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
        )
        await asyncio.sleep(0.05)
        failing_emitter.emit.assert_called_once()


# ============================================================================
# Test: NullEmitter default (AC-006)
# ============================================================================


class TestNullEmitterDefault:
    """NullEmitter default preserves existing behaviour."""

    def test_default_emitter_is_null_emitter(self, tmp_path: Path) -> None:
        """AC-006: NullEmitter default when emitter not injected."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        worktree = tmp_path / "worktree"
        worktree.mkdir()
        invoker = AgentInvoker(
            worktree_path=worktree,
            max_turns_per_agent=30,
            sdk_timeout_seconds=60,
        )
        assert isinstance(invoker._emitter, NullEmitter)

    @pytest.mark.asyncio
    async def test_no_events_captured_without_injected_emitter(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """AC-006: NullEmitter drops events (no capture)."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        worktree = tmp_path / "worktree"
        worktree.mkdir()
        invoker = AgentInvoker(
            worktree_path=worktree,
            max_turns_per_agent=30,
            sdk_timeout_seconds=60,
        )
        result_msg = _make_result_msg(mock_sdk)

        async def fake_query(**kw: Any):
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 implement feature",
            agent_type="player",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
        )
        await asyncio.sleep(0.05)

        assert isinstance(invoker._emitter, NullEmitter)
        assert len(invoker._emitter.events) == 0


# ============================================================================
# Test: Multiple calls distinct events (AC-007)
# ============================================================================


class TestMultipleCallsDistinctEvents:
    """Multiple calls in same turn produce distinct events."""

    @pytest.mark.asyncio
    async def test_two_calls_produce_two_events(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """AC-007: Multiple calls produce distinct events."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)
        result_msg = _make_result_msg(mock_sdk)

        async def fake_query(**kw: Any):
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 first call",
            agent_type="player",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
        )
        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 second call",
            agent_type="coach",
            allowed_tools=["Read"],
            permission_mode="bypassPermissions",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 2
        assert emitter.events[0].agent_role == "player"
        assert emitter.events[1].agent_role == "coach"
        assert emitter.events[0] is not emitter.events[1]


# ============================================================================
# Test: Latency tracking
# ============================================================================


class TestLatencyTracking:
    """Latency is correctly measured for success and failure paths."""

    @pytest.mark.asyncio
    async def test_latency_is_positive_on_success(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """Successful calls record positive latency."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)
        result_msg = _make_result_msg(mock_sdk)

        async def fake_query(**kw: Any):
            await asyncio.sleep(0.01)
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 implement feature",
            agent_type="player",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        assert emitter.events[0].latency_ms >= 5.0

    @pytest.mark.asyncio
    async def test_latency_is_recorded_on_error(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """Failed calls still record latency."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        async def fake_query(**kw: Any):
            await asyncio.sleep(0.01)
            raise asyncio.TimeoutError("timed out")
            yield  # pragma: no cover

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        from guardkit.orchestrator.exceptions import SDKTimeoutError

        with pytest.raises(SDKTimeoutError):
            await invoker._invoke_with_role(
                prompt="TASK-TEST-001 implement feature",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
            )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        assert emitter.events[0].latency_ms >= 5.0


# ============================================================================
# Test: Prompt profile defaults (AC-009)
# ============================================================================


class TestPromptProfile:
    """Prompt profile field is correctly populated."""

    @pytest.mark.asyncio
    async def test_default_prompt_profile(
        self, tmp_path: Path, mock_sdk: ModuleType,
    ) -> None:
        """Default prompt profile is digest+rules_bundle."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)
        result_msg = _make_result_msg(mock_sdk)

        async def fake_query(**kw: Any):
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        await invoker._invoke_with_role(
            prompt="TASK-TEST-001 implement feature",
            agent_type="player",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        assert emitter.events[0].prompt_profile == "digest+rules_bundle"
