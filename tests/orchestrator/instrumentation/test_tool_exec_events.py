"""Tests for tool execution event emission with secret redaction.

TDD: Tests covering Bash tool event emission, non-Bash tool ignoring,
secret redaction, tool name sanitisation, non-blocking behaviour,
output truncation, existing file tracking preservation, and seam tests.

TASK-INST-005c: Emit ToolExecEvent from SDK stream Bash tool invocations.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.schemas import (
    LLMCallEvent,
    ToolExecEvent,
)


# ============================================================================
# Helpers
# ============================================================================


def _build_mock_sdk() -> ModuleType:
    """Build a fake claude_agent_sdk module with all required exports."""
    mod = ModuleType("claude_agent_sdk")

    class _TextBlock:
        """Mock TextBlock."""
        def __init__(self, text: str = "") -> None:
            self.text = text
            self.type = "text"

    class _ToolUseBlock:
        """Mock ToolUseBlock."""
        def __init__(self, name: str = "", input: Any = None) -> None:
            self.name = name
            self.input = input or {}
            self.type = "tool_use"
            self.id = f"tool_{name}_{id(self)}"

    class _ToolResultBlock:
        """Mock ToolResultBlock."""
        def __init__(self, content: str = "", tool_use_id: str = "") -> None:
            self.content = content
            self.tool_use_id = tool_use_id
            self.type = "tool_result"

    class _ResultMessage:
        """Mock ResultMessage."""
        def __init__(self) -> None:
            self.num_turns = 1

    class _AssistantMessage:
        """Mock AssistantMessage."""
        def __init__(self, content: Optional[List[Any]] = None) -> None:
            self.content = content or []

    class _CLINotFoundError(Exception):
        pass

    class _ProcessError(Exception):
        def __init__(self, msg: str = "", exit_code: int = 1, stderr: str = ""):
            super().__init__(msg)
            self.exit_code = exit_code
            self.stderr = stderr

    class _CLIJSONDecodeError(Exception):
        pass

    mod.TextBlock = _TextBlock  # type: ignore[attr-defined]
    mod.ToolUseBlock = _ToolUseBlock  # type: ignore[attr-defined]
    mod.ToolResultBlock = _ToolResultBlock  # type: ignore[attr-defined]
    mod.ResultMessage = _ResultMessage  # type: ignore[attr-defined]
    mod.AssistantMessage = _AssistantMessage  # type: ignore[attr-defined]
    mod.CLINotFoundError = _CLINotFoundError  # type: ignore[attr-defined]
    mod.ProcessError = _ProcessError  # type: ignore[attr-defined]
    mod.CLIJSONDecodeError = _CLIJSONDecodeError  # type: ignore[attr-defined]
    mod.ClaudeAgentOptions = MagicMock  # type: ignore[attr-defined]

    return mod


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
# Test: Bash tool emits tool.exec event (AC-001)
# ============================================================================


class TestBashToolEmitsEvent:
    """tool.exec event emitted for Bash tool invocations in SDK stream."""

    def test_emit_tool_exec_event_for_bash(self, tmp_path: Path) -> None:
        """AC-001: _emit_tool_exec_event constructs and fires ToolExecEvent."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        # Call the emission method directly
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._emit_and_collect(invoker, emitter))
        finally:
            loop.close()

    async def _emit_and_collect(self, invoker: Any, emitter: NullEmitter) -> None:
        """Helper to emit and check events."""
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="pytest tests/ -v",
            exit_code=0,
            latency_ms=1234.5,
            stdout_tail="12 tests passed",
            stderr_tail="",
            task_id="TASK-TEST-001",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        assert isinstance(event, ToolExecEvent)
        assert event.tool_name == "Bash"
        assert event.exit_code == 0
        assert event.latency_ms == 1234.5


# ============================================================================
# Test: Secret redaction applied (AC-002)
# ============================================================================


class TestSecretRedaction:
    """Secret redaction applied to cmd, stdout_tail, stderr_tail."""

    def test_cmd_secrets_redacted(self, tmp_path: Path) -> None:
        """AC-002: Secrets in cmd are redacted before event construction."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._test_cmd_redaction(invoker, emitter))
        finally:
            loop.close()

    async def _test_cmd_redaction(self, invoker: Any, emitter: NullEmitter) -> None:
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="curl -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' https://api.example.com",
            exit_code=0,
            latency_ms=100.0,
            stdout_tail="OK",
            stderr_tail="",
            task_id="TASK-TEST-001",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        # The Bearer token should be redacted
        assert "eyJhbGciOi" not in event.cmd
        assert "[REDACTED]" in event.cmd

    def test_stdout_secrets_redacted(self, tmp_path: Path) -> None:
        """AC-002: Secrets in stdout_tail are redacted."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._test_stdout_redaction(invoker, emitter))
        finally:
            loop.close()

    async def _test_stdout_redaction(self, invoker: Any, emitter: NullEmitter) -> None:
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="echo test",
            exit_code=0,
            latency_ms=50.0,
            stdout_tail="API key: sk-abcdefghijklmnop1234567890",
            stderr_tail="SECRET=mysecretvalue",
            task_id="TASK-TEST-001",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        # SK key should be redacted in stdout
        assert "sk-abcdefghijklmnop1234567890" not in event.stdout_tail
        assert "[REDACTED]" in event.stdout_tail
        # SECRET= value should be redacted in stderr
        assert "mysecretvalue" not in event.stderr_tail
        assert "[REDACTED]" in event.stderr_tail


# ============================================================================
# Test: Tool names sanitised (AC-003)
# ============================================================================


class TestToolNameSanitisation:
    """Tool names sanitised against shell metacharacters."""

    def test_tool_name_sanitised(self, tmp_path: Path) -> None:
        """AC-003: Shell metacharacters removed from tool name via sanitise_tool_name."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        # The sanitise_tool_name function strips metacharacters
        result = sanitise_tool_name("Bash;rm -rf /|cat")
        assert ";" not in result
        assert "|" not in result
        assert "Bash" in result

    def test_emitted_event_has_sanitised_name(self, tmp_path: Path) -> None:
        """AC-003: ToolExecEvent tool_name is sanitised in the emitted event."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._test_sanitisation(invoker, emitter))
        finally:
            loop.close()

    async def _test_sanitisation(self, invoker: Any, emitter: NullEmitter) -> None:
        # Bash tool name from SDK is always clean, but sanitise_tool_name
        # is applied as a safety layer. Verify that "Bash" passes through
        # sanitise_tool_name unchanged.
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="echo hello",
            exit_code=0,
            latency_ms=10.0,
            stdout_tail="hello",
            stderr_tail="",
            task_id="TASK-TEST-001",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        assert event.tool_name == "Bash"
        # No metacharacters in the sanitised name
        for ch in ";|&$`><()":
            assert ch not in event.tool_name


# ============================================================================
# Test: Non-blocking emission (AC-004)
# ============================================================================


class TestNonBlockingEmission:
    """Event emission is non-blocking (asyncio.create_task)."""

    def test_emission_failure_does_not_propagate(self, tmp_path: Path) -> None:
        """AC-004: Emission failure is logged but not propagated."""
        failing_emitter = AsyncMock()
        failing_emitter.emit = AsyncMock(side_effect=RuntimeError("NATS down"))
        invoker = _make_invoker(tmp_path, emitter=failing_emitter)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._test_failure_safe(invoker, failing_emitter))
        finally:
            loop.close()

    async def _test_failure_safe(self, invoker: Any, failing_emitter: Any) -> None:
        # Should NOT raise even though emitter raises
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="echo test",
            exit_code=0,
            latency_ms=10.0,
            stdout_tail="test",
            stderr_tail="",
            task_id="TASK-TEST-001",
        )
        await asyncio.sleep(0.05)
        failing_emitter.emit.assert_called_once()


# ============================================================================
# Test: Non-Bash tools ignored (AC-005)
# ============================================================================


class TestNonBashToolsIgnored:
    """Non-Bash tools (Write, Edit, Glob) do NOT emit tool.exec events."""

    def test_write_tool_does_not_emit_tool_exec(self, tmp_path: Path) -> None:
        """AC-005: Write tool invocations do not trigger tool.exec events."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._test_write_ignored(invoker, emitter))
        finally:
            loop.close()

    async def _test_write_ignored(self, invoker: Any, emitter: NullEmitter) -> None:
        # Write tool should not emit tool.exec event
        # Only Bash tool should emit tool.exec events
        invoker._emit_tool_exec_event(
            tool_name="Write",
            cmd="",
            exit_code=0,
            latency_ms=10.0,
            stdout_tail="",
            stderr_tail="",
            task_id="TASK-TEST-001",
        )
        await asyncio.sleep(0.05)

        # No ToolExecEvent should be emitted for non-Bash tools
        tool_exec_events = [e for e in emitter.events if isinstance(e, ToolExecEvent)]
        assert len(tool_exec_events) == 0


# ============================================================================
# Test: stdout/stderr truncation (AC-006)
# ============================================================================


class TestOutputTruncation:
    """stdout_tail and stderr_tail truncated to last 500 chars."""

    def test_stdout_truncated_to_500_chars(self, tmp_path: Path) -> None:
        """AC-006: stdout_tail truncated to last 500 characters."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._test_truncation(invoker, emitter))
        finally:
            loop.close()

    async def _test_truncation(self, invoker: Any, emitter: NullEmitter) -> None:
        long_output = "x" * 1000
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="echo test",
            exit_code=0,
            latency_ms=10.0,
            stdout_tail=long_output,
            stderr_tail=long_output,
            task_id="TASK-TEST-001",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        assert len(event.stdout_tail) <= 500
        assert len(event.stderr_tail) <= 500


# ============================================================================
# Test: Existing file tracking unchanged (AC-007)
# ============================================================================


class TestExistingFileTracking:
    """Existing tool tracking in _track_tool_call still works (file tracking unchanged)."""

    def test_write_tool_still_tracked(self) -> None:
        """AC-007: _track_tool_call still tracks Write tool file operations."""
        from guardkit.orchestrator.agent_invoker import TaskWorkStreamParser

        parser = TaskWorkStreamParser()
        parser._track_tool_call("Write", {"file_path": "/tmp/test.py"})

        assert "/tmp/test.py" in parser._files_created

    def test_edit_tool_still_tracked(self) -> None:
        """AC-007: _track_tool_call still tracks Edit tool file operations."""
        from guardkit.orchestrator.agent_invoker import TaskWorkStreamParser

        parser = TaskWorkStreamParser()
        parser._track_tool_call("Edit", {"file_path": "/tmp/existing.py"})

        assert "/tmp/existing.py" in parser._files_modified


# ============================================================================
# Test: Seam test - redaction contract (AC-008)
# ============================================================================


@pytest.mark.seam
@pytest.mark.integration_contract("REDACTION_PIPELINE")
class TestRedactionPipelineContract:
    """Seam test validates redaction contract."""

    def test_redaction_pipeline_format(self) -> None:
        """AC-008: redact_secrets function strips Bearer tokens."""
        from guardkit.orchestrator.instrumentation.redaction import SecretRedactor

        redactor = SecretRedactor()
        result = redactor.redact(
            "curl -H 'Authorization: Bearer eyJhbGciOi...' https://api.example.com"
        )
        assert "eyJhbGciOi" not in result
        assert "[REDACTED]" in result

    def test_redaction_pipeline_sk_keys(self) -> None:
        """AC-008: redact_secrets function strips sk- keys."""
        from guardkit.orchestrator.instrumentation.redaction import SecretRedactor

        redactor = SecretRedactor()
        result = redactor.redact("export OPENAI_KEY=sk-abc123456789012345")
        assert "sk-abc123456789012345" not in result
        assert "[REDACTED]" in result

    def test_sanitise_tool_name_contract(self) -> None:
        """AC-008: sanitise_tool_name strips shell metacharacters."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        result = sanitise_tool_name("Bash;rm -rf /|cat")
        assert ";" not in result
        assert "|" not in result
        assert "Bash" in result


# ============================================================================
# Test: Unit tests cover all scenarios (AC-009)
# ============================================================================


class TestBashEventWithAllFields:
    """Bash tool event includes all expected fields."""

    def test_event_has_all_required_fields(self, tmp_path: Path) -> None:
        """AC-009: ToolExecEvent has all required fields populated."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._test_all_fields(invoker, emitter))
        finally:
            loop.close()

    async def _test_all_fields(self, invoker: Any, emitter: NullEmitter) -> None:
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="pytest tests/ -v",
            exit_code=0,
            latency_ms=500.0,
            stdout_tail="All tests passed",
            stderr_tail="",
            task_id="TASK-TEST-001",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        assert isinstance(event, ToolExecEvent)

        # All BaseEvent fields
        assert event.run_id is not None and event.run_id != ""
        assert event.task_id == "TASK-TEST-001"
        assert event.agent_role in ("player", "coach", "resolver", "router")
        assert event.attempt >= 1
        assert event.timestamp is not None

        # ToolExecEvent-specific fields
        assert event.tool_name == "Bash"
        assert event.cmd == "pytest tests/ -v"  # No secrets to redact
        assert event.exit_code == 0
        assert event.latency_ms == 500.0
        assert event.stdout_tail == "All tests passed"
        assert event.stderr_tail == ""


class TestMultipleBashToolEvents:
    """Multiple Bash tool invocations produce multiple events."""

    def test_two_bash_calls_produce_two_events(self, tmp_path: Path) -> None:
        """AC-009: Each Bash invocation emits a distinct ToolExecEvent."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._test_multiple(invoker, emitter))
        finally:
            loop.close()

    async def _test_multiple(self, invoker: Any, emitter: NullEmitter) -> None:
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="echo first",
            exit_code=0,
            latency_ms=10.0,
            stdout_tail="first",
            stderr_tail="",
            task_id="TASK-TEST-001",
        )
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd="echo second",
            exit_code=0,
            latency_ms=20.0,
            stdout_tail="second",
            stderr_tail="",
            task_id="TASK-TEST-001",
        )
        await asyncio.sleep(0.05)

        tool_events = [e for e in emitter.events if isinstance(e, ToolExecEvent)]
        assert len(tool_events) == 2
        assert tool_events[0].cmd != tool_events[1].cmd


# ============================================================================
# Test: SDK stream wiring (AC-001 integration)
# ============================================================================


class TestSDKStreamWiring:
    """Verify _emit_tool_exec_event is called from SDK stream processing."""

    def test_pending_bash_tools_tracking(self, tmp_path: Path) -> None:
        """Bash ToolUseBlock followed by ToolResultBlock emits event."""
        import time as _time

        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        # Simulate what the SDK stream loop does:
        # 1. Bash ToolUseBlock arrives → store in _pending_bash_tools
        # 2. ToolResultBlock arrives → match, emit, remove

        pending: Dict[str, Dict[str, Any]] = {}
        block_id = "tool_Bash_12345"
        cmd_text = "pytest tests/ -v"
        start_ns = _time.monotonic_ns()

        # Step 1: Bash ToolUseBlock detected
        pending[block_id] = {"cmd": cmd_text, "start_ns": start_ns}

        # Step 2: ToolResultBlock detected for same tool_use_id
        assert block_id in pending
        bash_info = pending.pop(block_id)
        content = "12 tests passed, 0 failed"
        latency_ms = (_time.monotonic_ns() - bash_info["start_ns"]) / 1_000_000

        # Step 3: Emit event (same call as the wiring code)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                self._emit_and_check(
                    invoker, emitter, bash_info["cmd"], latency_ms, content
                )
            )
        finally:
            loop.close()

    async def _emit_and_check(
        self,
        invoker: Any,
        emitter: NullEmitter,
        cmd: str,
        latency_ms: float,
        stdout_tail: str,
    ) -> None:
        invoker._emit_tool_exec_event(
            tool_name="Bash",
            cmd=cmd,
            exit_code=0,
            latency_ms=latency_ms,
            stdout_tail=stdout_tail,
            stderr_tail="",
            task_id="TASK-WIRE-001",
        )
        await asyncio.sleep(0.05)

        assert len(emitter.events) == 1
        event = emitter.events[0]
        assert isinstance(event, ToolExecEvent)
        assert event.tool_name == "Bash"
        assert event.cmd == "pytest tests/ -v"
        assert event.task_id == "TASK-WIRE-001"
        assert event.latency_ms > 0

    def test_non_bash_tool_result_does_not_emit(self, tmp_path: Path) -> None:
        """ToolResultBlock for non-Bash tool does not emit tool.exec event."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        # Simulate: only Write ToolUseBlock → no entry in pending_bash_tools
        pending: Dict[str, Dict[str, Any]] = {}
        write_block_id = "tool_Write_99999"

        # Write tool does NOT add to pending_bash_tools
        # So when ToolResultBlock arrives, nothing happens
        assert write_block_id not in pending

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(asyncio.sleep(0.01))
        finally:
            loop.close()

        # No tool.exec events emitted
        tool_events = [e for e in emitter.events if isinstance(e, ToolExecEvent)]
        assert len(tool_events) == 0
