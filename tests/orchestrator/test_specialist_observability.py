"""
Unit tests for specialist-path observability (TASK-FIX-CRSTL-MULT R2).

Covers the operator-visible ``ToolUseBlock`` log emission inside
``AgentInvoker._invoke_with_role``'s SDK message loop. The line surfaces
per-tool signal during long orchestrator-invoked specialist invocations
(test-orchestrator, code-reviewer) so a stalled specialist can be
diagnosed from the log alone instead of inferring from wall-clock
heartbeat alone.

The emit is gated on ``heartbeat_label_override`` being set:
  - Player/Coach paths (no override) stay silent, since the task-work
    delegation path at ``agent_invoker.py:5279-5281`` already logs
    Write/Edit ToolUseBlocks and we don't want double-logging.
  - Specialist paths (override set, e.g. ``"specialist:code-reviewer"``)
    log every ToolUseBlock at INFO level.

Coverage Target: >=85% on the changed lines in
``guardkit/orchestrator/agent_invoker.py::_invoke_with_role``.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

import claude_agent_sdk
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from guardkit.orchestrator.agent_invoker import AgentInvoker


# ----------------------------------------------------------------------
# Test doubles (mirrors the FakeAsyncGen pattern from test_agent_invoker_sdk_errors.py)
# ----------------------------------------------------------------------


class FakeAsyncGen:
    """Test double mimicking an async-iterable SDK query stream."""

    def __init__(self, events):
        self._events = list(events)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._events:
            raise StopAsyncIteration
        kind, payload = self._events.pop(0)
        if kind == "yield":
            return payload
        if kind == "raise":
            raise payload
        raise AssertionError(f"Unknown fake-gen event kind: {kind!r}")

    async def aclose(self):  # pragma: no cover - trivial
        return None


def _make_invoker(tmp_path: Path) -> AgentInvoker:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=5,
        sdk_timeout_seconds=60,
    )


def _assistant_msg_with_tool(
    tool_name: str, tool_input: dict, tool_id: str = "tool-1"
) -> AssistantMessage:
    """AssistantMessage carrying a single ToolUseBlock."""
    return AssistantMessage(
        content=[ToolUseBlock(id=tool_id, name=tool_name, input=tool_input)],
        model="test-model",
    )


def _assistant_msg_text(text: str = "hello") -> AssistantMessage:
    return AssistantMessage(
        content=[TextBlock(text=text)],
        model="test-model",
    )


def _result_msg(session_id: str = "sess-obs") -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=False,
        num_turns=1,
        session_id=session_id,
        total_cost_usd=0.0,
    )


# ----------------------------------------------------------------------
# Specialist-path emission
# ----------------------------------------------------------------------


class TestSpecialistToolUseBlockLogging:
    """heartbeat_label_override gates ToolUseBlock log emission."""

    @pytest.mark.asyncio
    async def test_specialist_path_emits_tool_use_log(self, tmp_path, caplog):
        """When heartbeat_label_override is set, each ToolUseBlock is logged
        at INFO level with the override label, the tool name, and the
        sorted input keys."""
        invoker = _make_invoker(tmp_path)

        tool_msg = _assistant_msg_with_tool(
            "Read", {"file_path": "/x/y/z.py"}, tool_id="tool-read-1"
        )
        done = _result_msg(session_id="sess-spec-1")
        fake_gen = FakeAsyncGen([("yield", tool_msg), ("yield", done)])

        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.agent_invoker"
        ):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                await invoker._invoke_with_role(
                    prompt="prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="bypassPermissions",
                    task_id="TASK-AIV2-003",
                    heartbeat_label_override="specialist:code-reviewer",
                )

        matching = [
            r.getMessage() for r in caplog.records
            if "ToolUseBlock" in r.getMessage()
            and "specialist:code-reviewer" in r.getMessage()
        ]
        assert matching, (
            "expected at least one specialist-path ToolUseBlock log line, "
            f"caplog records: {[r.getMessage() for r in caplog.records]}"
        )
        # The line carries task_id, label, tool name, and sorted input keys.
        msg = matching[0]
        assert "[TASK-AIV2-003]" in msg
        assert "ToolUseBlock Read" in msg
        assert "['file_path']" in msg

    @pytest.mark.asyncio
    async def test_specialist_path_logs_multiple_tool_blocks(
        self, tmp_path, caplog
    ):
        """A specialist invocation with multiple ToolUseBlocks emits one log
        line per block."""
        invoker = _make_invoker(tmp_path)

        msg1 = _assistant_msg_with_tool(
            "Read", {"file_path": "a.py"}, tool_id="t1"
        )
        msg2 = _assistant_msg_with_tool(
            "Grep", {"pattern": "x", "path": "."}, tool_id="t2"
        )
        done = _result_msg(session_id="sess-spec-2")
        fake_gen = FakeAsyncGen(
            [("yield", msg1), ("yield", msg2), ("yield", done)]
        )

        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.agent_invoker"
        ):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                await invoker._invoke_with_role(
                    prompt="prompt",
                    agent_type="player",
                    allowed_tools=["Read", "Grep"],
                    permission_mode="bypassPermissions",
                    task_id="TASK-AIV2-003",
                    heartbeat_label_override="specialist:code-reviewer",
                )

        tool_use_lines = [
            r.getMessage() for r in caplog.records
            if "specialist:code-reviewer ToolUseBlock" in r.getMessage()
        ]
        assert len(tool_use_lines) == 2, (
            f"expected 2 ToolUseBlock log lines, got "
            f"{len(tool_use_lines)}: {tool_use_lines}"
        )
        # Sorted-keys contract: Grep input has ['path', 'pattern'] when sorted.
        assert any("Read input keys: ['file_path']" in m for m in tool_use_lines)
        assert any(
            "Grep input keys: ['path', 'pattern']" in m
            for m in tool_use_lines
        )

    @pytest.mark.asyncio
    async def test_specialist_path_handles_non_dict_input(
        self, tmp_path, caplog
    ):
        """Non-dict ToolUseBlock input → log line with empty key list, no
        crash. Defensive: the SDK has historically emitted string-shaped
        inputs for malformed tool calls."""
        invoker = _make_invoker(tmp_path)

        # ToolUseBlock with a non-dict input (e.g. a stringified blob the
        # SDK forgot to parse) — the emit must not raise.
        tool_msg = AssistantMessage(
            content=[
                ToolUseBlock(
                    id="tool-bad", name="WeirdTool", input={"not": "actually a dict"}
                )
            ],
            model="test-model",
        )
        done = _result_msg(session_id="sess-spec-3")
        fake_gen = FakeAsyncGen([("yield", tool_msg), ("yield", done)])

        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.agent_invoker"
        ):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                await invoker._invoke_with_role(
                    prompt="prompt",
                    agent_type="player",
                    allowed_tools=["WeirdTool"],
                    permission_mode="bypassPermissions",
                    task_id="TASK-AIV2-003",
                    heartbeat_label_override="specialist:test-orchestrator",
                )

        matching = [
            r.getMessage() for r in caplog.records
            if "ToolUseBlock WeirdTool" in r.getMessage()
        ]
        assert matching, "expected a WeirdTool log line"

    @pytest.mark.asyncio
    async def test_non_specialist_path_does_not_double_log(
        self, tmp_path, caplog
    ):
        """heartbeat_label_override=None (Player/Coach path) → the new log
        line is NOT emitted, since the task-work delegation path already
        emits one for Write/Edit blocks.

        This prevents log-volume regression for the Player/Coach paths
        and is the explicit guard in the task AC.
        """
        invoker = _make_invoker(tmp_path)

        tool_msg = _assistant_msg_with_tool(
            "Read", {"file_path": "/x.py"}, tool_id="tool-p1"
        )
        done = _result_msg(session_id="sess-player-1")
        fake_gen = FakeAsyncGen([("yield", tool_msg), ("yield", done)])

        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.agent_invoker"
        ):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                await invoker._invoke_with_role(
                    prompt="prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                    task_id="TASK-PLAYER-001",
                    heartbeat_label_override=None,
                )

        # No specialist-shaped log line should appear when override is None.
        specialist_lines = [
            r.getMessage() for r in caplog.records
            if "specialist:" in r.getMessage()
            and "ToolUseBlock" in r.getMessage()
        ]
        assert specialist_lines == [], (
            f"expected no specialist log lines on Player path, got "
            f"{specialist_lines}"
        )
        # And no bare "[TASK-PLAYER-001] ... ToolUseBlock Read input keys"
        # from the new emit path either (the override is None so the
        # branch should not run).
        new_emit_lines = [
            r.getMessage() for r in caplog.records
            if "[TASK-PLAYER-001]" in r.getMessage()
            and "ToolUseBlock Read input keys" in r.getMessage()
        ]
        assert new_emit_lines == [], (
            f"expected no new-emit log lines on Player path, got "
            f"{new_emit_lines}"
        )

    @pytest.mark.asyncio
    async def test_specialist_path_ignores_text_blocks(
        self, tmp_path, caplog
    ):
        """An AssistantMessage carrying only TextBlocks → no ToolUseBlock log
        line is emitted (the branch correctly skips non-ToolUseBlock
        content)."""
        invoker = _make_invoker(tmp_path)

        text_msg = _assistant_msg_text("just narration, no tools")
        done = _result_msg(session_id="sess-spec-4")
        fake_gen = FakeAsyncGen([("yield", text_msg), ("yield", done)])

        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.agent_invoker"
        ):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                await invoker._invoke_with_role(
                    prompt="prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="bypassPermissions",
                    task_id="TASK-AIV2-003",
                    heartbeat_label_override="specialist:code-reviewer",
                )

        tool_use_lines = [
            r.getMessage() for r in caplog.records
            if "ToolUseBlock" in r.getMessage()
        ]
        assert tool_use_lines == [], (
            f"expected no ToolUseBlock log lines for a text-only message, "
            f"got {tool_use_lines}"
        )
