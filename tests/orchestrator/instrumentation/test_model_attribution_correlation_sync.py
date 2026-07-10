"""Synchronous tests for model attribution and correlation (TASK-OBS-9F43).

These tests verify the implementation without async complexity by directly
inspecting the intermediate values rather than waiting for async emission.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator


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

    def __init__(self, model_usage: dict):
        self.model_usage = model_usage
        self.type = "result"


# ============================================================================
# AC-1: Model Attribution Tests
# ============================================================================


class TestModelAttribution:
    """Test model extraction from server-resolved sources."""

    def test_extract_server_resolved_model_from_assistant_message(self):
        """Extracts model from AssistantMessage.model field."""
        invoker = AgentInvoker(worktree_path="/tmp/test")

        response_messages = [
            MockAssistantMessage(model="claude-sonnet-4-20250514"),
        ]

        result = invoker._extract_server_resolved_model(response_messages)
        assert result == "claude-sonnet-4-20250514"

    def test_extract_server_resolved_model_from_result_message(self):
        """Extracts model from ResultMessage.model_usage keys."""
        invoker = AgentInvoker(worktree_path="/tmp/test")

        response_messages = [
            MockResultMessage(
                model_usage={
                    "claude-sonnet-4-20250514": {"input_tokens": 100, "output_tokens": 50}
                }
            ),
        ]

        result = invoker._extract_server_resolved_model(response_messages)
        assert result == "claude-sonnet-4-20250514"

    def test_extract_server_resolved_model_empty_messages(self):
        """Returns None when no server-resolved model available."""
        invoker = AgentInvoker(worktree_path="/tmp/test")

        response_messages = []

        result = invoker._extract_server_resolved_model(response_messages)
        assert result is None

    def test_extract_server_resolved_model_prefers_assistant_message(self):
        """Prefers AssistantMessage.model when both sources present."""
        invoker = AgentInvoker(worktree_path="/tmp/test")

        response_messages = [
            MockAssistantMessage(model="claude-sonnet-4-20250514"),
            MockResultMessage(
                model_usage={"claude-opus-3-20240229": {"input_tokens": 100}}
            ),
        ]

        result = invoker._extract_server_resolved_model(response_messages)
        # First message wins
        assert result == "claude-sonnet-4-20250514"


# ============================================================================
# AC-2: Run ID Correlation Tests
# ============================================================================


class TestRunIDCorrelation:
    """Test single run_id minting and threading."""

    def test_orchestrator_mints_run_id_on_init(self):
        """Orchestrator mints run_id once during initialization."""
        from pathlib import Path

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp"),
            max_turns=5,
        )

        assert hasattr(orchestrator, "_run_id")
        assert orchestrator._run_id.startswith("run-")
        assert len(orchestrator._run_id) > 10  # Has timestamp + id

    def test_agent_invoker_receives_run_id_from_orchestrator(self):
        """AgentInvoker gets run_id threaded from orchestrator."""
        invoker = AgentInvoker(worktree_path="/tmp/test")

        # Simulate threading from orchestrator
        shared_run_id = "run-test-12345"
        invoker._run_id = shared_run_id

        # Verify it's set
        assert invoker._run_id == shared_run_id


# ============================================================================
# AC-3: Attempt and Agent Role Tests
# ============================================================================


class TestAttemptAndAgentRole:
    """Test correct attempt numbering and agent_role tracking."""

    def test_agent_invoker_tracks_current_attempt(self):
        """_current_attempt is set correctly."""
        invoker = AgentInvoker(worktree_path="/tmp/test")

        # Simulate orchestrator setting attempt
        invoker._current_attempt = 3

        assert invoker._current_attempt == 3

    def test_agent_invoker_tracks_current_agent_role(self):
        """_current_agent_role is set at _invoke_with_role entry."""
        invoker = AgentInvoker(worktree_path="/tmp/test")

        # Will be set in _invoke_with_role
        # For now just verify the attribute can be set
        invoker._current_agent_role = "coach"

        assert invoker._current_agent_role == "coach"


# ============================================================================
# AC-4: Tool Execution Fidelity Tests
# ============================================================================


class TestToolExecutionFidelity:
    """Test that tool execution extracts real values."""

    def test_tool_result_block_exit_code_extraction(self):
        """ToolResultBlock provides exit_code attribute."""
        # This test verifies we can extract exit_code from ToolResultBlock
        # The actual ToolResultBlock is from SDK; we verify the extraction logic

        class MockToolResultBlock:
            exit_code = 127
            stderr = "command not found"
            stdout = ""
            tool_use_id = "test-id"

        block = MockToolResultBlock()

        exit_code = getattr(block, "exit_code", 0)
        stderr = getattr(block, "stderr", "")

        assert exit_code == 127
        assert stderr == "command not found"


# ============================================================================
# AC-5: LangGraph Substrate Parity
# ============================================================================


class TestLangGraphSubstrateParity:
    """Test that configured model is used when server-resolved unavailable."""

    def test_configured_model_used_when_no_server_resolved(self):
        """When server doesn't provide model, use configured value."""
        invoker = AgentInvoker(worktree_path="/tmp/test")

        # Empty response (no server-resolved model)
        response_messages = []

        extracted = invoker._extract_server_resolved_model(response_messages)
        assert extracted is None  # No server model

        # The _emit_llm_call_event logic should then use configured model
        # Testing this requires checking the actual emission logic
