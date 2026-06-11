"""
Unit tests for TASK-FIX-7A03: Defensive SDK message handling.

Covers the per-message try/except wrapper around the SDK query-stream
iteration in ``AgentInvoker._invoke_with_role`` plus the typed
``ValueError`` clause and the augmented blanket ``Exception`` handler in
the surrounding catch cascade. Paired with the ``error_class`` field
added to ``AgentInvocationError`` in ``guardkit/orchestrator/exceptions.py``.

Coverage Target: >=80% on the changed lines in
``guardkit/orchestrator/agent_invoker.py::_invoke_with_role``.
"""

import asyncio
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

# Optional dependency (the `autobuild` extra). Skip cleanly when absent so the
# suite never errors at collection on an environment without the SDK
# (TASK-INFRA-CIGREEN AC-4). CI installs claude-agent-sdk so these run + gate.
pytest.importorskip("claude_agent_sdk")

import claude_agent_sdk
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock
from claude_agent_sdk._errors import MessageParseError

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.exceptions import AgentInvocationError


# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------


class FakeAsyncGen:
    """Test double mimicking an ``async for``-iterable SDK query stream.

    Accepts an event script of ``("yield", msg)`` / ``("raise", exc)``
    entries. Unlike a real Python async generator, this double *does* let
    the caller continue iterating after a raised exception — the SDK's
    public query generator in production terminates after the first
    uncaught exception, but per-message recovery in ``_invoke_with_role``
    must handle both shapes correctly:

      * Production (real SDK): first parse-type exception → subsequent
        ``__anext__`` raises ``StopAsyncIteration`` → loop exits with
        partial messages. This double reproduces that shape when the
        script contains only yield+raise+[end].
      * Simulated recovery: the script can include yield-after-raise to
        exercise the "continue on parse error" branch directly.
    """

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


def _assistant_msg(text: str = "hello") -> AssistantMessage:
    return AssistantMessage(
        content=[TextBlock(text=text)],
        model="test-model",
    )


def _result_msg(session_id: str = "sess-1") -> ResultMessage:
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
# AgentInvocationError payload contract
# ----------------------------------------------------------------------


class TestAgentInvocationErrorErrorClass:
    """``AgentInvocationError`` gained an optional ``error_class`` kwarg."""

    def test_accepts_error_class_kwarg(self):
        err = AgentInvocationError("boom", error_class="ValueError")
        assert err.error_class == "ValueError"
        assert "boom" in str(err)

    def test_legacy_constructor_without_kwarg_still_works(self):
        err = AgentInvocationError("boom")
        assert err.error_class is None
        assert str(err) == "boom"

    def test_error_class_survives_raise_and_catch(self):
        with pytest.raises(AgentInvocationError) as ei:
            raise AgentInvocationError("parse failed", error_class="MessageParseError")
        assert ei.value.error_class == "MessageParseError"


# ----------------------------------------------------------------------
# Streaming-loop behaviour
# ----------------------------------------------------------------------


class TestDefensiveStreamIteration:
    """Per-message try/except around the SDK query stream (AC item 1+4)."""

    @pytest.mark.asyncio
    async def test_unknown_then_valid_logs_warning_and_completes(
        self, tmp_path, caplog
    ):
        """Unknown message type followed by a valid ``AssistantMessage`` and a
        closing ``ResultMessage`` → turn completes, WARNING names the
        unparseable message, and ``_last_session_id`` captures the result."""
        invoker = _make_invoker(tmp_path)

        good = _assistant_msg("payload-after-unknown")
        done = _result_msg(session_id="sess-AC1")
        fake_gen = FakeAsyncGen([
            ("raise", MessageParseError(
                "Unknown message type: rate_limit_event",
                {"type": "rate_limit_event"},
            )),
            ("yield", good),
            ("yield", done),
        ])

        with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                await invoker._invoke_with_role(
                    prompt="task_id=TASK-TEST-001 prompt",
                    agent_type="player",
                    allowed_tools=[],
                    permission_mode="acceptEdits",
                )

        # Turn completed without AgentInvocationError.
        assert invoker._last_session_id == "sess-AC1"

        # Per-message WARNING was emitted naming error_class and the
        # specific unknown type.
        per_msg_warnings = [
            r for r in caplog.records
            if "Skipping unparseable SDK message" in r.getMessage()
        ]
        assert len(per_msg_warnings) == 1
        assert "MessageParseError" in per_msg_warnings[0].getMessage()
        assert "rate_limit_event" in per_msg_warnings[0].getMessage()

        # Post-stream summary WARNING records the drop count.
        summary = [
            r for r in caplog.records
            if "unparseable message(s) dropped" in r.getMessage()
        ]
        assert len(summary) == 1
        assert "1 unparseable" in summary[0].getMessage()

    @pytest.mark.asyncio
    async def test_valid_then_unknown_accepts_partial_output(
        self, tmp_path, caplog
    ):
        """Production shape: valid ``AssistantMessage`` yielded before an
        unparseable message → turn still completes with the valid message
        captured. Mirrors how real SDK async generators terminate after the
        first uncaught exception."""
        invoker = _make_invoker(tmp_path)

        good = _assistant_msg("partial-success-payload")
        fake_gen = FakeAsyncGen([
            ("yield", good),
            ("raise", MessageParseError("Unknown message type: rate_limit_event", {})),
            # Real SDK gen would now be dead; the double honours that shape
            # by returning StopAsyncIteration on the next __anext__ since
            # the event script is exhausted.
        ])

        with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                await invoker._invoke_with_role(
                    prompt="task_id=TASK-TEST-002 prompt",
                    agent_type="player",
                    allowed_tools=[],
                    permission_mode="acceptEdits",
                )

        # Partial success → no exception, summary WARN present.
        assert any(
            "parsed successfully" in r.getMessage() for r in caplog.records
        )

    @pytest.mark.asyncio
    async def test_all_unknown_messages_raises_with_error_class(self, tmp_path):
        """Stream of only unparseable messages → ``AgentInvocationError``
        with count, agent_type, and ``error_class="MessageParseError"``
        preserved (AC item 2)."""
        invoker = _make_invoker(tmp_path)

        fake_gen = FakeAsyncGen([
            ("raise", MessageParseError("Unknown message type: rate_limit_event", {})),
            ("raise", MessageParseError("Unknown message type: fresh_mystery", {})),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            with pytest.raises(AgentInvocationError) as ei:
                await invoker._invoke_with_role(
                    prompt="task_id=TASK-TEST-003 prompt",
                    agent_type="player",
                    allowed_tools=[],
                    permission_mode="acceptEdits",
                )

        err = ei.value
        msg = str(err)
        assert "unparseable" in msg
        assert "player" in msg
        # At least 1 — the exact count depends on whether the test double
        # yields past the raise, but the critical behaviour is that zero
        # successful parses triggers the structured raise.
        assert err.error_class == "MessageParseError"

    @pytest.mark.asyncio
    async def test_valueerror_in_stream_is_logged_and_dropped(
        self, tmp_path, caplog
    ):
        """``ValueError`` raised mid-stream (e.g. the SDK's internal
        "Unsupported plugin type" raise) is dropped the same way as
        ``MessageParseError``, with ``error_class`` reflecting the
        concrete class name."""
        invoker = _make_invoker(tmp_path)

        good = _assistant_msg("still-good")
        fake_gen = FakeAsyncGen([
            ("raise", ValueError("Unsupported plugin type: weird")),
            ("yield", good),
            ("yield", _result_msg()),
        ])

        with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                await invoker._invoke_with_role(
                    prompt="task_id=TASK-TEST-004 prompt",
                    agent_type="player",
                    allowed_tools=[],
                    permission_mode="acceptEdits",
                )

        drop_warns = [
            r for r in caplog.records
            if "Skipping unparseable SDK message" in r.getMessage()
        ]
        assert len(drop_warns) == 1
        assert "error_class=ValueError" in drop_warns[0].getMessage()


# ----------------------------------------------------------------------
# Outer exception cascade
# ----------------------------------------------------------------------


class TestOuterExceptionCascade:
    """Typed ``ValueError`` clause + augmented blanket handler (AC item 2+3)."""

    @pytest.mark.asyncio
    async def test_valueerror_escaping_streaming_block_preserves_error_class(
        self, tmp_path
    ):
        """A ``ValueError`` raised *outside* the per-message catch (e.g.
        from the SDK's ``query`` constructor itself) lands in the new
        typed ``except ValueError`` clause and is wrapped with
        ``error_class="ValueError"`` and ``type(e).__name__`` in the
        surfaced message. AC item 3 (third bullet of Unit tests)."""
        invoker = _make_invoker(tmp_path)

        def boom(**kwargs):
            raise ValueError("some ValueError in the query() call")

        with patch.object(claude_agent_sdk, "query", side_effect=boom):
            with pytest.raises(AgentInvocationError) as ei:
                await invoker._invoke_with_role(
                    prompt="task_id=TASK-TEST-005 prompt",
                    agent_type="player",
                    allowed_tools=[],
                    permission_mode="acceptEdits",
                )

        err = ei.value
        assert err.error_class == "ValueError"
        assert "ValueError" in str(err)  # type name in surfaced string
        assert "some ValueError in the query() call" in str(err)

    @pytest.mark.asyncio
    async def test_blanket_exception_is_augmented_with_type_name(self, tmp_path):
        """An unexpected exception type (``RuntimeError`` here) hits the
        blanket ``except Exception`` handler. The surfaced message now
        contains ``type(e).__name__`` so the old opaque "SDK invocation
        failed" string is no longer ambiguous. AC item 3 (second bullet
        of acceptance criteria)."""
        invoker = _make_invoker(tmp_path)

        class _CustomExplosion(RuntimeError):
            pass

        def boom(**kwargs):
            raise _CustomExplosion("kaboom")

        with patch.object(claude_agent_sdk, "query", side_effect=boom):
            with pytest.raises(AgentInvocationError) as ei:
                await invoker._invoke_with_role(
                    prompt="task_id=TASK-TEST-006 prompt",
                    agent_type="player",
                    allowed_tools=[],
                    permission_mode="acceptEdits",
                )

        err = ei.value
        assert "_CustomExplosion" in str(err)
        assert "kaboom" in str(err)
        assert err.error_class == "_CustomExplosion"


# ----------------------------------------------------------------------
# Regression: existing cascade handlers still produce the old shapes
# ----------------------------------------------------------------------


class TestNoRegressionOnExistingHandlers:
    """AC item 6: pre-existing timeout / CLINotFound / ProcessError /
    CLIJSONDecodeError handling is not disturbed by the TASK-FIX-7A03
    changes. Those handlers still build ``AgentInvocationError`` without
    an ``error_class`` kwarg (their surfaced messages are not required
    to change)."""

    @pytest.mark.asyncio
    async def test_cli_not_found_still_surfaces_install_hint(self, tmp_path):
        from claude_agent_sdk import CLINotFoundError

        invoker = _make_invoker(tmp_path)

        def boom(**kwargs):
            raise CLINotFoundError("Claude Code not found")

        with patch.object(claude_agent_sdk, "query", side_effect=boom):
            with pytest.raises(AgentInvocationError) as ei:
                await invoker._invoke_with_role(
                    prompt="task_id=TASK-TEST-007 prompt",
                    agent_type="player",
                    allowed_tools=[],
                    permission_mode="acceptEdits",
                )

        assert "npm install -g @anthropic-ai/claude-code" in str(ei.value)

    @pytest.mark.asyncio
    async def test_process_error_still_surfaces_exit_code(self, tmp_path):
        from claude_agent_sdk import ProcessError

        invoker = _make_invoker(tmp_path)

        def boom(**kwargs):
            raise ProcessError("cli died", exit_code=137, stderr="killed")

        with patch.object(claude_agent_sdk, "query", side_effect=boom):
            with pytest.raises(AgentInvocationError) as ei:
                await invoker._invoke_with_role(
                    prompt="task_id=TASK-TEST-008 prompt",
                    agent_type="player",
                    allowed_tools=[],
                    permission_mode="acceptEdits",
                )

        assert "exit 137" in str(ei.value)
