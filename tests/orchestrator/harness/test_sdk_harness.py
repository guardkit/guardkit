"""Unit tests for :class:`ClaudeSDKHarness` (TASK-HMIG-006 Phase 3a).

Tests the SDK harness adapter in isolation — patches
``claude_agent_sdk.query`` with a fake async generator yielding scripted
SDK message shapes and asserts the harness translates them into the
correct :class:`HarnessEvent` sequence while preserving:

* TASK-FIX-7A03 per-message parse resilience
* TASK-RFX-B20B session_id capture
* TASK-RFX-8332 / TASK-FIX-GEN1 generator hygiene (``aclose`` called)
* TASK-HMIG-006 Design Decision D-4 SDK-exception → AgentInvocationError
  normalisation
* Constructor-arg forwarding for resume_session_id and cleanup-handler

Coverage Target: >=85% line, >=80% branch on
``guardkit.orchestrator.harness.sdk_harness``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

import claude_agent_sdk
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock
from claude_agent_sdk._errors import MessageParseError

from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ClaudeSDKHarness,
    ResultMessageEvent,
)


# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------


class RecordingAsyncGen:
    """Async-iterable test double mimicking ``claude_agent_sdk.query``.

    Accepts an event script of ``("yield", msg)`` / ``("raise", exc)``
    entries. Records every call to ``aclose()`` so tests can assert the
    harness honours the TASK-RFX-8332 generator hygiene contract.
    """

    def __init__(self, events):
        self._events = list(events)
        self.aclose_calls = 0

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

    async def aclose(self):
        self.aclose_calls += 1


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


def _make_harness(**overrides) -> ClaudeSDKHarness:
    """Build a default harness, allowing per-test override of any kwarg."""
    defaults = dict(
        sdk_timeout_seconds=60,
        allowed_tools=["Read", "Write"],
        permission_mode="acceptEdits",
        max_turns=10,
    )
    defaults.update(overrides)
    return ClaudeSDKHarness(**defaults)


async def _drain(harness: ClaudeSDKHarness, cwd: Path):
    """Helper: consume the async generator into a list."""
    events = []
    async for event in harness.invoke(
        prompt="task_id=TASK-TEST-001 prompt",
        role="player",
        tools=[],
        cwd=cwd,
        timeout_seconds=60,
    ):
        events.append(event)
    return events


# ----------------------------------------------------------------------
# Happy-path translation
# ----------------------------------------------------------------------


class TestSingleTurnTranslation:
    """Single-turn: AssistantMessage + ResultMessage → 2 HarnessEvents."""

    @pytest.mark.asyncio
    async def test_yields_assistant_then_result_events(self, tmp_path):
        harness = _make_harness()
        good = _assistant_msg("payload")
        done = _result_msg(session_id="sess-AB1")
        fake_gen = RecordingAsyncGen([
            ("yield", good),
            ("yield", done),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assert len(events) == 2
        assert isinstance(events[0], AssistantMessageEvent)
        assert events[0].text == "payload"
        assert isinstance(events[1], ResultMessageEvent)
        assert events[1].session_id == "sess-AB1"

    @pytest.mark.asyncio
    async def test_assistant_event_raw_carries_original_sdk_message(
        self, tmp_path
    ):
        """Design Decision D-1: AssistantMessageEvent.raw holds the
        SDK-native AssistantMessage so downstream duck-typed consumers
        (_track_tool_use, _extract_partial_from_messages) keep working."""
        harness = _make_harness()
        good = _assistant_msg("verify-raw")
        done = _result_msg()
        fake_gen = RecordingAsyncGen([
            ("yield", good),
            ("yield", done),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assistant_event = events[0]
        assert isinstance(assistant_event, AssistantMessageEvent)
        # event.raw is the original SDK message — same identity, not a copy.
        assert assistant_event.raw is good

    @pytest.mark.asyncio
    async def test_result_event_raw_carries_original_sdk_message(
        self, tmp_path
    ):
        """Phase 3b additive ABC field: ResultMessageEvent.raw holds the
        SDK-native ResultMessage so the orchestrator's cancelled-error
        session_id rescan and _emit_llm_call_event token extraction
        continue to operate on raw SDK shape without migration
        (TASK-HMIG-006 Phase 3a flag resolution)."""
        harness = _make_harness()
        done = _result_msg(session_id="sess-raw-1")
        fake_gen = RecordingAsyncGen([("yield", done)])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assert len(events) == 1
        result_event = events[0]
        assert isinstance(result_event, ResultMessageEvent)
        # event.raw is the original SDK message — same identity, not a copy.
        assert result_event.raw is done

    @pytest.mark.asyncio
    async def test_result_event_session_id_matches_sdk(self, tmp_path):
        """TASK-RFX-B20B preservation: ResultMessageEvent.session_id
        captures ResultMessage.session_id verbatim."""
        harness = _make_harness()
        done = _result_msg(session_id="sess-RFX-B20B-1234567890abcdef")
        fake_gen = RecordingAsyncGen([("yield", done)])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assert len(events) == 1
        assert isinstance(events[0], ResultMessageEvent)
        assert events[0].session_id == "sess-RFX-B20B-1234567890abcdef"
        # And the harness exposes the same value via its property.
        assert harness.session_id == "sess-RFX-B20B-1234567890abcdef"

    @pytest.mark.asyncio
    async def test_supports_resume_property(self):
        harness = _make_harness()
        # Per AC-007 the SDK harness supports resume.
        assert harness.supports_resume is True

    @pytest.mark.asyncio
    async def test_session_id_none_before_invocation(self):
        """Property returns None before any ResultMessage observed."""
        harness = _make_harness()
        assert harness.session_id is None


# ----------------------------------------------------------------------
# Generator hygiene (TASK-RFX-8332 / TASK-FIX-GEN1)
# ----------------------------------------------------------------------


class TestGeneratorHygiene:
    """Verifies the harness honours aclose()/drain contract."""

    @pytest.mark.asyncio
    async def test_aclose_called_when_stream_ends_without_result(
        self, tmp_path
    ):
        """No ResultMessage observed → generator not exhausted in-loop →
        aclose() in finally block must be called."""
        harness = _make_harness()
        # Only AssistantMessage; no ResultMessage to trigger the in-loop
        # drain path. StopAsyncIteration from the empty event list
        # closes the loop and we land in the finally block.
        good = _assistant_msg("no-result")
        fake_gen = RecordingAsyncGen([("yield", good)])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assert len(events) == 1
        assert fake_gen.aclose_calls == 1

    @pytest.mark.asyncio
    async def test_result_message_drains_and_skips_aclose(self, tmp_path):
        """TASK-FIX-GEN1: when ResultMessage observed, harness drains the
        remaining gen body and sets gen=None so the finally block does
        NOT call aclose() (it would be redundant). The drain path
        exhausts the script naturally."""
        harness = _make_harness()
        done = _result_msg()
        # Extra event after the ResultMessage — the drain loop must
        # consume it without yielding it as a HarnessEvent.
        leftover = _assistant_msg("ignored-after-result")
        fake_gen = RecordingAsyncGen([
            ("yield", done),
            ("yield", leftover),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        # Only the ResultMessage surfaces as a HarnessEvent — the
        # leftover was drained but not yielded downstream.
        assert len(events) == 1
        assert isinstance(events[0], ResultMessageEvent)
        # gen was set to None after drain → aclose() in finally skipped.
        assert fake_gen.aclose_calls == 0


# ----------------------------------------------------------------------
# TASK-FIX-7A03 parse resilience
# ----------------------------------------------------------------------


class TestParseResilience:
    """Per-message MessageParseError/ValueError skip + WARN, plus the
    post-stream "all unparseable" raise."""

    @pytest.mark.asyncio
    async def test_message_parse_error_mid_stream_is_skipped(
        self, tmp_path, caplog
    ):
        import logging

        harness = _make_harness()
        good = _assistant_msg("payload-after-parse-error")
        done = _result_msg()
        fake_gen = RecordingAsyncGen([
            ("raise", MessageParseError(
                "Unknown message type: rate_limit_event", {}
            )),
            ("yield", good),
            ("yield", done),
        ])

        with caplog.at_level(
            logging.WARNING,
            logger="guardkit.orchestrator.harness.sdk_harness",
        ):
            with patch.object(
                claude_agent_sdk, "query", return_value=fake_gen
            ):
                events = await _drain(harness, tmp_path)

        # Stream completed; turn surfaced the post-parse-error assistant
        # plus the terminal ResultMessage.
        assert len(events) == 2
        assert isinstance(events[0], AssistantMessageEvent)
        # Skip-and-warn line was emitted.
        skip_lines = [
            r for r in caplog.records
            if "Skipping unparseable SDK message" in r.getMessage()
        ]
        assert len(skip_lines) == 1
        assert "MessageParseError" in skip_lines[0].getMessage()

    @pytest.mark.asyncio
    async def test_value_error_mid_stream_is_skipped(self, tmp_path, caplog):
        """ValueError raised mid-stream is dropped the same way as
        MessageParseError (error_class tracks the concrete name)."""
        import logging

        harness = _make_harness()
        good = _assistant_msg("still-good")
        done = _result_msg()
        fake_gen = RecordingAsyncGen([
            ("raise", ValueError("Unsupported plugin type: weird")),
            ("yield", good),
            ("yield", done),
        ])

        with caplog.at_level(
            logging.WARNING,
            logger="guardkit.orchestrator.harness.sdk_harness",
        ):
            with patch.object(
                claude_agent_sdk, "query", return_value=fake_gen
            ):
                events = await _drain(harness, tmp_path)

        assert len(events) == 2
        skip_lines = [
            r for r in caplog.records
            if "Skipping unparseable SDK message" in r.getMessage()
        ]
        assert len(skip_lines) == 1
        assert "error_class=ValueError" in skip_lines[0].getMessage()

    @pytest.mark.asyncio
    async def test_all_unparseable_raises_with_message_parse_error_class(
        self, tmp_path
    ):
        """Zero parses + only parse errors → AgentInvocationError with
        error_class='MessageParseError' so TASK-FIX-7A02 classifies
        correctly."""
        harness = _make_harness()
        fake_gen = RecordingAsyncGen([
            ("raise", MessageParseError("Unknown: rate_limit_event", {})),
            ("raise", MessageParseError("Unknown: fresh_mystery", {})),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            with pytest.raises(AgentInvocationError) as ei:
                await _drain(harness, tmp_path)

        err = ei.value
        assert err.error_class == "MessageParseError"
        assert "unparseable" in str(err)
        assert "player" in str(err)

    @pytest.mark.asyncio
    async def test_partial_success_logs_summary_warning(
        self, tmp_path, caplog
    ):
        """At least one parsed message + at least one unparseable →
        summary WARN, no raise."""
        import logging

        harness = _make_harness()
        good = _assistant_msg("partial-success")
        fake_gen = RecordingAsyncGen([
            ("yield", good),
            ("raise", MessageParseError("Unknown: rate_limit_event", {})),
        ])

        with caplog.at_level(
            logging.WARNING,
            logger="guardkit.orchestrator.harness.sdk_harness",
        ):
            with patch.object(
                claude_agent_sdk, "query", return_value=fake_gen
            ):
                events = await _drain(harness, tmp_path)

        assert len(events) == 1
        assert any(
            "parsed successfully" in r.getMessage()
            for r in caplog.records
        )


# ----------------------------------------------------------------------
# Design Decision D-4 exception cascade
# ----------------------------------------------------------------------


class TestExceptionTranslation:
    """All SDK-specific exceptions normalise to AgentInvocationError
    *inside* the harness — orchestrator never sees raw SDK types."""

    @pytest.mark.asyncio
    async def test_cli_not_found_error_translates(self, tmp_path):
        from claude_agent_sdk import CLINotFoundError

        harness = _make_harness()

        def boom(**kwargs):
            raise CLINotFoundError("Claude Code not found")

        with patch.object(claude_agent_sdk, "query", side_effect=boom):
            with pytest.raises(AgentInvocationError) as ei:
                await _drain(harness, tmp_path)

        assert "npm install -g @anthropic-ai/claude-code" in str(ei.value)

    @pytest.mark.asyncio
    async def test_process_error_translates_with_exit_code(self, tmp_path):
        from claude_agent_sdk import ProcessError

        harness = _make_harness()

        def boom(**kwargs):
            raise ProcessError("died", exit_code=137, stderr="killed")

        with patch.object(claude_agent_sdk, "query", side_effect=boom):
            with pytest.raises(AgentInvocationError) as ei:
                await _drain(harness, tmp_path)

        assert "exit 137" in str(ei.value)

    @pytest.mark.asyncio
    async def test_cli_json_decode_error_translates(self, tmp_path):
        from claude_agent_sdk import CLIJSONDecodeError

        harness = _make_harness()

        def boom(**kwargs):
            # CLIJSONDecodeError(line, original_error) signature in SDK 0.1+.
            raise CLIJSONDecodeError("bad json", ValueError("not json"))

        with patch.object(claude_agent_sdk, "query", side_effect=boom):
            with pytest.raises(AgentInvocationError) as ei:
                await _drain(harness, tmp_path)

        assert "Failed to parse SDK response" in str(ei.value)

    @pytest.mark.asyncio
    async def test_value_error_outside_stream_translates_with_error_class(
        self, tmp_path
    ):
        """ValueError raised from query() constructor (not mid-stream)
        lands in the harness's typed-ValueError clause and is wrapped
        with error_class=type(e).__name__."""
        harness = _make_harness()

        def boom(**kwargs):
            raise ValueError("some ValueError from query()")

        with patch.object(claude_agent_sdk, "query", side_effect=boom):
            with pytest.raises(AgentInvocationError) as ei:
                await _drain(harness, tmp_path)

        err = ei.value
        assert err.error_class == "ValueError"
        assert "ValueError" in str(err)
        assert "some ValueError from query()" in str(err)

    @pytest.mark.asyncio
    async def test_generic_exception_translates_with_type_name(
        self, tmp_path
    ):
        """Unexpected exception (RuntimeError) hits the blanket clause
        and the surfaced AgentInvocationError carries the original type
        name in both error_class and the message string."""
        harness = _make_harness()

        class _CustomExplosion(RuntimeError):
            pass

        def boom(**kwargs):
            raise _CustomExplosion("kaboom")

        with patch.object(claude_agent_sdk, "query", side_effect=boom):
            with pytest.raises(AgentInvocationError) as ei:
                await _drain(harness, tmp_path)

        err = ei.value
        assert err.error_class == "_CustomExplosion"
        assert "_CustomExplosion" in str(err)
        assert "kaboom" in str(err)


# ----------------------------------------------------------------------
# Constructor-arg plumbing
# ----------------------------------------------------------------------


class TestConstructorPlumbing:
    """Resume session ID + cleanup handler are forwarded correctly."""

    @pytest.mark.asyncio
    async def test_resume_session_id_forwarded_to_options(self, tmp_path):
        """resume_session_id constructor arg → ClaudeAgentOptions(resume=...)
        on the SDK side. Capture options via a query() side-effect."""
        captured: dict = {}

        def capture(**kwargs):
            captured["options"] = kwargs.get("options")
            return RecordingAsyncGen([("yield", _result_msg())])

        harness = _make_harness(resume_session_id="prior-session-abc123")

        with patch.object(claude_agent_sdk, "query", side_effect=capture):
            await _drain(harness, tmp_path)

        opts = captured["options"]
        assert getattr(opts, "resume", None) == "prior-session-abc123"

    @pytest.mark.asyncio
    async def test_no_resume_when_session_id_none(self, tmp_path):
        """When resume_session_id is None, options.resume must not be set
        (falls back to SDK default of fresh session)."""
        captured: dict = {}

        def capture(**kwargs):
            captured["options"] = kwargs.get("options")
            return RecordingAsyncGen([("yield", _result_msg())])

        harness = _make_harness(resume_session_id=None)

        with patch.object(claude_agent_sdk, "query", side_effect=capture):
            await _drain(harness, tmp_path)

        opts = captured["options"]
        # ClaudeAgentOptions defaults resume to None; the harness must
        # not have set it explicitly.
        assert getattr(opts, "resume", None) is None

    @pytest.mark.asyncio
    async def test_cleanup_handler_installer_invoked_with_running_loop(
        self, tmp_path
    ):
        """The cleanup-handler installer is invoked once at the start of
        invoke() with the running event loop (TASK-HMIG-006 D-6)."""
        installer_calls = []

        def installer(loop):
            installer_calls.append(loop)

        harness = _make_harness(cleanup_handler_installer=installer)
        fake_gen = RecordingAsyncGen([("yield", _result_msg())])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            await _drain(harness, tmp_path)

        assert len(installer_calls) == 1
        # The installer was called with an actual asyncio loop instance.
        assert isinstance(installer_calls[0], asyncio.AbstractEventLoop)

    @pytest.mark.asyncio
    async def test_cleanup_handler_skipped_when_none(self, tmp_path):
        """When cleanup_handler_installer is None (the default), no
        attempt to call is made and invoke() still works."""
        harness = _make_harness(cleanup_handler_installer=None)
        fake_gen = RecordingAsyncGen([("yield", _result_msg())])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assert len(events) == 1
        assert isinstance(events[0], ResultMessageEvent)

    @pytest.mark.asyncio
    async def test_model_forwarded_to_options_when_set(self, tmp_path):
        captured: dict = {}

        def capture(**kwargs):
            captured["options"] = kwargs.get("options")
            return RecordingAsyncGen([("yield", _result_msg())])

        harness = _make_harness(model="claude-sonnet-4-5-20250929")

        with patch.object(claude_agent_sdk, "query", side_effect=capture):
            await _drain(harness, tmp_path)

        opts = captured["options"]
        assert getattr(opts, "model", None) == "claude-sonnet-4-5-20250929"

    @pytest.mark.asyncio
    async def test_allowed_tools_forwarded_to_options(self, tmp_path):
        captured: dict = {}

        def capture(**kwargs):
            captured["options"] = kwargs.get("options")
            return RecordingAsyncGen([("yield", _result_msg())])

        harness = _make_harness(allowed_tools=["Read", "Bash"])

        with patch.object(claude_agent_sdk, "query", side_effect=capture):
            await _drain(harness, tmp_path)

        opts = captured["options"]
        assert list(getattr(opts, "allowed_tools", [])) == ["Read", "Bash"]
