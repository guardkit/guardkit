"""Tests for real model attribution and joinable correlation identity.

Covers:
- AC-1: Model attribution from server-resolved fields
- AC-2: Joinable run_id across all events
- AC-3: Correct attempt and agent_role tracking
- AC-4: Real exit_code and stderr_tail from ToolResultBlock
- AC-5: LangGraph substrate parity

Tests follow TDD RED-GREEN-REFACTOR pattern.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.instrumentation.schemas import (
    LLMCallEvent,
    TaskCompletedEvent,
    TaskStartedEvent,
    ToolExecEvent,
)


# ============================================================================
# Mock Helpers
# ============================================================================


class MockAssistantMessage:
    """Mock for Claude SDK AssistantMessage with server-resolved model."""

    def __init__(self, model: str, content: str = "test"):
        self.model = model
        self.content = content
        self.type = "assistant"


class MockResultMessage:
    """Mock for ResultMessage with model_usage keyed by model name."""

    def __init__(self, model_usage: Dict[str, Any]):
        self.model_usage = model_usage
        self.type = "result"


class MockToolResultBlock:
    """Mock for ToolResultBlock with exit_code and stderr."""

    def __init__(
        self,
        exit_code: int = 0,
        stdout: str = "",
        stderr: str = "",
        content: str = "",
    ):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.content = content or stdout
        self.type = "tool_result"


class MockEmitter:
    """Mock instrumentation emitter that captures events."""

    def __init__(self):
        self.events: List[Any] = []

    async def emit(self, event: Any) -> None:
        """Capture event for later inspection."""
        self.events.append(event)

    def get_events_by_type(self, event_type: type) -> List[Any]:
        """Filter events by type."""
        return [e for e in self.events if isinstance(e, event_type)]


# ============================================================================
# AC-1: Model Attribution Tests
# ============================================================================


class TestModelAttribution:
    """Test model extraction from server-resolved sources."""

    @pytest.mark.asyncio
    async def test_model_from_assistant_message_no_flag(self):
        """RED: Server-resolved model from AssistantMessage when no --model flag."""
        # This test will fail until we implement model extraction
        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = MockEmitter()

        response_messages = [
            MockAssistantMessage(model="claude-sonnet-4-20250514"),
        ]

        invoker._emit_llm_call_event(
            agent_type="player",
            model=None,  # No flag set
            latency_ms=1000.0,
            response_messages=response_messages,
            status="ok",
            error=None,
            task_id="TASK-TEST",
        )

        # Give the async emit time to complete
        await asyncio.sleep(0.1)

        events = invoker._emitter.get_events_by_type(LLMCallEvent)
        assert len(events) == 1
        # Should extract from response_messages, not fall back to "default"
        assert events[0].model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_model_from_result_message_model_usage(self):
        """RED: Model from ResultMessage.model_usage when available."""
        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = MockEmitter()

        response_messages = [
            MockResultMessage(
                model_usage={
                    "claude-sonnet-4-20250514": {"input_tokens": 100, "output_tokens": 50}
                }
            ),
        ]

        invoker._emit_llm_call_event(
            agent_type="coach",
            model=None,
            latency_ms=1000.0,
            response_messages=response_messages,
            status="ok",
            error=None,
            task_id="TASK-TEST",
        )

        # Emission is fire-and-forget via loop.create_task(); yield so it runs.
        await asyncio.sleep(0.05)

        events = invoker._emitter.get_events_by_type(LLMCallEvent)
        assert len(events) == 1
        assert events[0].model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_model_from_flag_when_set(self):
        """Model from configured flag takes precedence."""
        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = MockEmitter()

        response_messages = [
            MockAssistantMessage(model="claude-sonnet-4-20250514"),
        ]

        invoker._emit_llm_call_event(
            agent_type="player",
            model="custom-model-override",  # Flag set
            latency_ms=1000.0,
            response_messages=response_messages,
            status="ok",
            error=None,
            task_id="TASK-TEST",
        )

        await asyncio.sleep(0.05)

        events = invoker._emitter.get_events_by_type(LLMCallEvent)
        assert len(events) == 1
        # Configured model takes precedence
        assert events[0].model == "custom-model-override"

    @pytest.mark.asyncio
    async def test_model_fallback_to_default_only_when_no_source(self):
        """Default only when neither flag nor server-resolved available."""
        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = MockEmitter()

        response_messages = []  # Empty response

        invoker._emit_llm_call_event(
            agent_type="player",
            model=None,
            latency_ms=1000.0,
            response_messages=response_messages,
            status="ok",
            error=None,
            task_id="TASK-TEST",
        )

        await asyncio.sleep(0.05)

        events = invoker._emitter.get_events_by_type(LLMCallEvent)
        assert len(events) == 1
        # Only falls back to default when no other source
        assert events[0].model == "default"


# ============================================================================
# AC-2: Run ID Correlation Tests
# ============================================================================


class TestRunIDCorrelation:
    """Test single run_id across all event types."""

    @patch("guardkit.orchestrator.autobuild.WorktreeManager")
    def test_lifecycle_events_share_run_id(self, mock_wm):
        """RED: task.started and task.completed share same run_id."""
        # Lifecycle emits (_emit_task_started/_emit_task_completed) use a blocking
        # asyncio.run() internally, so this test stays synchronous (asyncio.run
        # cannot be nested inside a running loop).
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            sdk_timeout=900,
        )
        orchestrator._emitter = MockEmitter()

        # Mint run_id at orchestrator init
        # (This is what we need to implement)
        orchestrator._run_id = "run-test-abc-123"

        # Emit lifecycle events
        orchestrator._emit_task_started("TASK-TEST")

        # Simulate completion (non-empty turn_history: attempt/turn_count are ge=1)
        orchestrator._emit_task_completed(
            "TASK-TEST", turn_history=[Mock(decision="approved")]
        )

        started_events = orchestrator._emitter.get_events_by_type(TaskStartedEvent)
        completed_events = orchestrator._emitter.get_events_by_type(TaskCompletedEvent)

        assert len(started_events) == 1
        assert len(completed_events) == 1

        # Both should share the orchestrator's run_id
        assert started_events[0].run_id == "run-test-abc-123"
        assert completed_events[0].run_id == "run-test-abc-123"

    @patch("guardkit.orchestrator.autobuild.WorktreeManager")
    def test_llm_call_and_lifecycle_share_run_id(self, mock_wm):
        """RED: llm.call events join with task lifecycle by run_id."""
        # Create shared run_id
        shared_run_id = "run-test-xyz-456"

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            sdk_timeout=900,
        )
        orchestrator._emitter = MockEmitter()
        orchestrator._run_id = shared_run_id

        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = orchestrator._emitter
        invoker._run_id = shared_run_id  # Thread from orchestrator

        # Lifecycle emit uses a blocking asyncio.run() — call it from this
        # synchronous context.
        orchestrator._emit_task_started("TASK-TEST")

        # The llm.call emit is fire-and-forget via loop.create_task(), so it
        # needs a running loop: drive it inside asyncio.run() and yield so the
        # scheduled task runs before we inspect the shared emitter.
        async def _emit_llm_and_drain():
            invoker._emit_llm_call_event(
                agent_type="player",
                model="claude-sonnet-4-20250514",
                latency_ms=1000.0,
                response_messages=[],
                status="ok",
                error=None,
                task_id="TASK-TEST",
            )
            await asyncio.sleep(0.05)

        asyncio.run(_emit_llm_and_drain())

        started = orchestrator._emitter.get_events_by_type(TaskStartedEvent)
        llm_calls = orchestrator._emitter.get_events_by_type(LLMCallEvent)

        assert len(started) == 1
        assert len(llm_calls) == 1

        # Can join by run_id
        assert started[0].run_id == llm_calls[0].run_id == shared_run_id


# ============================================================================
# AC-3: Attempt and Agent Role Tests
# ============================================================================


class TestAttemptAndAgentRole:
    """Test correct attempt numbering and agent_role tracking."""

    @pytest.mark.asyncio
    async def test_attempt_increments_across_turns(self):
        """RED: Attempt reflects actual turn number."""
        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = MockEmitter()
        invoker._run_id = "run-test"

        # Turn 1
        invoker._current_attempt = 1
        invoker._emit_llm_call_event(
            agent_type="player",
            model="test-model",
            latency_ms=1000.0,
            response_messages=[],
            status="ok",
            error=None,
            task_id="TASK-TEST",
        )

        # Turn 2
        invoker._current_attempt = 2
        invoker._emit_llm_call_event(
            agent_type="player",
            model="test-model",
            latency_ms=1000.0,
            response_messages=[],
            status="ok",
            error=None,
            task_id="TASK-TEST",
        )

        # Emission is fire-and-forget via loop.create_task(); yield so both run.
        await asyncio.sleep(0.05)

        events = invoker._emitter.get_events_by_type(LLMCallEvent)
        assert len(events) == 2
        assert events[0].attempt == 1
        assert events[1].attempt == 2

    @pytest.mark.asyncio
    async def test_tool_exec_agent_role_from_coach(self):
        """RED: tool.exec during coach turn has agent_role=coach."""
        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = MockEmitter()
        invoker._run_id = "run-test"
        invoker._current_agent_role = "coach"  # Set during coach turn

        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="echo test",
            exit_code=0,
            latency_ms=100.0,
            stdout_tail="test",
            stderr_tail="",
            task_id="TASK-TEST",
        )

        # Emission is fire-and-forget via loop.create_task(); yield so it runs.
        await asyncio.sleep(0.05)

        events = invoker._emitter.get_events_by_type(ToolExecEvent)
        assert len(events) == 1
        assert events[0].agent_role == "coach"


# ============================================================================
# AC-4: Tool Execution Fidelity Tests
# ============================================================================


class TestToolExecutionFidelity:
    """Test real exit_code and stderr_tail extraction."""

    @pytest.mark.asyncio
    async def test_tool_exec_real_exit_code_nonzero(self):
        """RED: Non-zero exit_code from failing Bash call."""
        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = MockEmitter()
        invoker._run_id = "run-test"

        # Simulate tool execution with non-zero exit
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="exit 127",
            exit_code=127,  # Real exit code, not hardcoded 0
            latency_ms=50.0,
            stdout_tail="",
            stderr_tail="command not found",
            task_id="TASK-TEST",
        )

        # Emission is fire-and-forget via loop.create_task(); yield so it runs.
        await asyncio.sleep(0.05)

        events = invoker._emitter.get_events_by_type(ToolExecEvent)
        assert len(events) == 1
        assert events[0].exit_code == 127
        assert "command not found" in events[0].stderr_tail

    @pytest.mark.asyncio
    async def test_tool_exec_stderr_tail_populated(self):
        """RED: stderr_tail contains actual stderr when produced."""
        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = MockEmitter()
        invoker._run_id = "run-test"

        stderr_content = "Error: file not found\nTraceback..."

        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="cat nonexistent.txt",
            exit_code=1,
            latency_ms=20.0,
            stdout_tail="",
            stderr_tail=stderr_content,
            task_id="TASK-TEST",
        )

        await asyncio.sleep(0.05)

        events = invoker._emitter.get_events_by_type(ToolExecEvent)
        assert len(events) == 1
        assert events[0].stderr_tail == stderr_content


# ============================================================================
# AC-5: LangGraph Substrate Parity Tests
# ============================================================================


class TestLangGraphSubstrateParity:
    """Test attribution works on LangGraph harness."""

    @pytest.mark.asyncio
    async def test_langgraph_gets_configured_model_when_no_server_resolved(self):
        """LangGraph uses configured/resolved model name when server field absent."""
        # LangGraph may not expose server-resolved model in same way as SDK
        # Should use the resolved/configured name
        invoker = AgentInvoker(worktree_path="/tmp/test")
        invoker._emitter = MockEmitter()

        # Simulate LangGraph response without server-resolved field
        response_messages = []  # No AssistantMessage with .model

        invoker._emit_llm_call_event(
            agent_type="player",
            model="claude-sonnet-4-20250514",  # Configured model
            latency_ms=1000.0,
            response_messages=response_messages,
            status="ok",
            error=None,
            task_id="TASK-TEST",
        )

        # Emission is fire-and-forget via loop.create_task(); yield so it runs.
        await asyncio.sleep(0.05)

        events = invoker._emitter.get_events_by_type(LLMCallEvent)
        assert len(events) == 1
        # Should use configured model, never silent "default"
        assert events[0].model == "claude-sonnet-4-20250514"
        assert events[0].model != "default"
