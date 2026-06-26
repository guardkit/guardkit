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

# Optional dependency (the `autobuild` extra). Skip cleanly when absent so the
# suite never errors at collection on an environment without the SDK
# (TASK-INFRA-CIGREEN AC-4). CI installs claude-agent-sdk so these run + gate.
pytest.importorskip("claude_agent_sdk")

import claude_agent_sdk
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    UserMessage,
)
from claude_agent_sdk._errors import MessageParseError

from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ClaudeSDKHarness,
    ResultMessageEvent,
    ToolResultEvent,
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


def _assistant_msg_with_thinking(
    text: str = "hello",
    thinking: str = "Reasoning about the task...",
) -> AssistantMessage:
    """Build an AssistantMessage carrying both a TextBlock and ThinkingBlock.

    Anthropic's extended-thinking shape: a single AssistantMessage can hold
    multiple ThinkingBlock + TextBlock entries in ``content``. The harness
    joins all TextBlock.text into ``event.text`` and all ThinkingBlock.thinking
    into ``event.reasoning_text`` (TASK-FIX-COACHBUDG01).
    """
    return AssistantMessage(
        content=[
            ThinkingBlock(thinking=thinking, signature="sig-test"),
            TextBlock(text=text),
        ],
        model="test-model",
    )


def _assistant_msg_thinking_only(
    thinking: str = "Internal monologue, no content emission.",
) -> AssistantMessage:
    """Build an AssistantMessage that has ONLY a ThinkingBlock (no TextBlock).

    Matches the empirical gemma4-coach pattern observed in §9.14: the
    model emits the entire turn into the thinking channel and the content
    channel comes back empty. The harness must surface this as
    ``AssistantMessageEvent(text="", reasoning_text=<thinking>)`` so the
    orchestrator-side parser's reasoning-fallback branch can rescue the
    verdict.
    """
    return AssistantMessage(
        content=[ThinkingBlock(thinking=thinking, signature="sig-test")],
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


def _user_msg_with_tool_result(
    content="45 passed in 0.13s",
    is_error: bool = False,
    tool_use_id: str = "tu-1",
) -> UserMessage:
    """Build a UserMessage carrying a Bash ToolResultBlock.

    Mirrors how the SDK delivers a tool's output back to the model — the
    shape the harness must surface as a ToolResultEvent (TASK-FIX-COACHTRES01).
    ``content`` is ``str`` for the common case; pass a list for the structured
    block form.
    """
    return UserMessage(
        content=[
            ToolResultBlock(
                tool_use_id=tool_use_id,
                content=content,
                is_error=is_error,
            )
        ]
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
# TASK-FIX-COACHBUDG01 — ThinkingBlock extraction → reasoning_text
# ----------------------------------------------------------------------


class TestThinkingBlockExtraction:
    """Anthropic extended-thinking blocks → AssistantMessageEvent.reasoning_text.

    The harness joins ``ThinkingBlock.thinking`` separately from
    ``TextBlock.text`` and populates ``AssistantMessageEvent.reasoning_text``
    so the orchestrator-side ``coach_output_parser`` can apply the
    "prefer content, fall through to reasoning" precedence documented in
    that module's "Hybrid reasoning models" section (TASK-FIX-COACHBUDG01,
    §9.14 of AUTOBUILD-ON-LLAMA-SWAP-findings.md).
    """

    @pytest.mark.asyncio
    async def test_no_thinking_blocks_yields_empty_reasoning_text(self, tmp_path):
        """Backwards-compat: messages without ThinkingBlock get reasoning_text=''.

        Pre-COACHBUDG01 callers / models / SDK versions that never emit
        ``ThinkingBlock`` must observe the legacy event shape, with the
        ``reasoning_text`` default-string sliding in transparently.
        """
        harness = _make_harness()
        good = _assistant_msg("plain text only")
        done = _result_msg()
        fake_gen = RecordingAsyncGen([("yield", good), ("yield", done)])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assistant_event = events[0]
        assert isinstance(assistant_event, AssistantMessageEvent)
        assert assistant_event.text == "plain text only"
        assert assistant_event.reasoning_text == ""

    @pytest.mark.asyncio
    async def test_text_and_thinking_both_extracted_into_separate_fields(
        self, tmp_path
    ):
        """Anthropic mixed shape: ThinkingBlock + TextBlock in one message.

        ``content`` joins all TextBlock; ``reasoning_text`` joins all
        ThinkingBlock; neither contaminates the other.
        """
        harness = _make_harness()
        msg = _assistant_msg_with_thinking(
            text="```json\n{\"task_id\": \"X\", \"turn\": 1, \"decision\": \"approve\"}\n```",
            thinking="Reviewing the diff... acceptance criteria look met.",
        )
        done = _result_msg()
        fake_gen = RecordingAsyncGen([("yield", msg), ("yield", done)])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assistant_event = events[0]
        assert isinstance(assistant_event, AssistantMessageEvent)
        assert "```json" in assistant_event.text  # canonical verdict in content
        assert assistant_event.text.startswith("```json")
        assert assistant_event.reasoning_text == (
            "Reviewing the diff... acceptance criteria look met."
        )

    @pytest.mark.asyncio
    async def test_thinking_only_message_has_empty_text_and_populated_reasoning(
        self, tmp_path
    ):
        """The §9.14 failure mode: model emits only thinking, no content.

        Without TASK-FIX-COACHBUDG01 this would have collapsed to
        ``AssistantMessageEvent(text="")`` and the parser would have
        raised CoachDecisionNotFoundError even though the verdict was
        present in the thinking channel.
        """
        harness = _make_harness()
        msg = _assistant_msg_thinking_only(
            thinking=(
                "Internal monologue: the implementation looks fine.\n"
                "```json\n"
                '{"task_id": "X", "turn": 1, "decision": "approve"}\n'
                "```"
            )
        )
        done = _result_msg()
        fake_gen = RecordingAsyncGen([("yield", msg), ("yield", done)])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assistant_event = events[0]
        assert isinstance(assistant_event, AssistantMessageEvent)
        assert assistant_event.text == ""
        assert "```json" in assistant_event.reasoning_text
        assert "approve" in assistant_event.reasoning_text

    @pytest.mark.asyncio
    async def test_multiple_thinking_blocks_concatenated_in_order(self, tmp_path):
        """An AssistantMessage carrying multiple ThinkingBlocks joins them.

        Mirrors the legacy multi-TextBlock join: parts concatenate without
        a separator (``"".join``) — preserves the SDK's per-block split
        semantics and lets the regex tolerate either form.
        """
        harness = _make_harness()
        msg = AssistantMessage(
            content=[
                ThinkingBlock(thinking="First thought. ", signature="s1"),
                ThinkingBlock(thinking="Second thought.", signature="s2"),
                TextBlock(text="Final answer."),
            ],
            model="test-model",
        )
        done = _result_msg()
        fake_gen = RecordingAsyncGen([("yield", msg), ("yield", done)])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assistant_event = events[0]
        assert assistant_event.text == "Final answer."
        assert assistant_event.reasoning_text == "First thought. Second thought."


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

    @pytest.mark.asyncio
    async def test_setting_sources_defaults_to_project(self, tmp_path):
        """TASK-HMIG-006.4: omitting setting_sources defaults to ["project"].

        Preserves the value the harness previously hardcoded in invoke(),
        so the existing _invoke_with_role caller (which does not pass it)
        keeps the project-only behaviour.
        """
        captured: dict = {}

        def capture(**kwargs):
            captured["options"] = kwargs.get("options")
            return RecordingAsyncGen([("yield", _result_msg())])

        harness = _make_harness()  # no setting_sources override

        with patch.object(claude_agent_sdk, "query", side_effect=capture):
            await _drain(harness, tmp_path)

        opts = captured["options"]
        assert list(getattr(opts, "setting_sources", [])) == ["project"]

    @pytest.mark.asyncio
    async def test_setting_sources_forwarded_to_options(self, tmp_path):
        """TASK-HMIG-006.4: an explicit setting_sources reaches ClaudeAgentOptions."""
        captured: dict = {}

        def capture(**kwargs):
            captured["options"] = kwargs.get("options")
            return RecordingAsyncGen([("yield", _result_msg())])

        harness = _make_harness(setting_sources=["user", "project"])

        with patch.object(claude_agent_sdk, "query", side_effect=capture):
            await _drain(harness, tmp_path)

        opts = captured["options"]
        assert list(getattr(opts, "setting_sources", [])) == ["user", "project"]


# ----------------------------------------------------------------------
# Cooperative cancellation (TASK-FIX-CTOUT01)
# ----------------------------------------------------------------------


class TestCancelSDKHarness:
    """Verifies HarnessAdapter.cancel() closes the active query() generator.

    TASK-FIX-CTOUT01 added an async ``cancel`` method to HarnessAdapter
    so AgentInvoker._cancel_monitor can request termination of an
    in-flight invoke() when the orchestrator's cancellation_event fires.

    Under SDK harness, cancel() calls ``aclose()`` on the active
    ``query()`` generator — propagating CancelledError into the
    async-for loop in invoke(), which the orchestrator already handles
    via its existing asyncio.timeout() + CancelledError cascade.
    """

    @pytest.mark.asyncio
    async def test_cancel_is_noop_when_no_active_invoke(self):
        """A fresh harness with no in-flight invoke has nothing to close."""
        harness = _make_harness()
        # Must not raise; no observable side effect.
        await harness.cancel()
        assert harness._active_gen is None

    @pytest.mark.asyncio
    async def test_cancel_closes_active_generator(self, tmp_path):
        """When invoke() is in-flight, cancel() closes the gen and
        invoke() unblocks via the closed generator."""
        harness = _make_harness()

        # A gen that yields one assistant message then HANGS on the next
        # __anext__ (simulates the SDK awaiting an LLM HTTP response that
        # never arrives). cancel()'s aclose() must unblock this hang.
        class HangingGen:
            def __init__(self) -> None:
                self.aclose_calls = 0
                self._yielded_first = False
                self._closed = asyncio.Event()

            def __aiter__(self):
                return self

            async def __anext__(self):
                if not self._yielded_first:
                    self._yielded_first = True
                    return _assistant_msg("partial")
                # Hang until cancel() calls aclose(), which sets _closed.
                await self._closed.wait()
                raise StopAsyncIteration

            async def aclose(self):
                self.aclose_calls += 1
                self._closed.set()

        fake_gen = HangingGen()

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            invoke_task = asyncio.create_task(_drain(harness, tmp_path))
            # Spin the event loop enough for invoke() to construct the
            # gen, set self._active_gen, consume the first event, and
            # suspend on the hanging __anext__.
            for _ in range(10):
                await asyncio.sleep(0)
            assert harness._active_gen is fake_gen, (
                "invoke() must expose the active gen on the instance "
                "before suspending — cancel() relies on this for "
                "external aclose()."
            )

            await harness.cancel()

            # cancel() closed the gen; the hanging __anext__ unblocks
            # via _closed.set() inside aclose, then raises
            # StopAsyncIteration, and invoke()'s async-for exits cleanly.
            try:
                await asyncio.wait_for(invoke_task, timeout=2.0)
            except asyncio.TimeoutError:
                invoke_task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await invoke_task
                pytest.fail(
                    "invoke() did not terminate within 2s after cancel — "
                    "the generator's aclose() should unblock the async-for."
                )

        # aclose() was called at least once.
        assert fake_gen.aclose_calls >= 1
        # Instance handle cleared.
        assert harness._active_gen is None

    @pytest.mark.asyncio
    async def test_cancel_clears_active_gen_before_aclose(self, tmp_path):
        """Idempotency: a second cancel() call after the first is a no-op
        because self._active_gen was cleared synchronously before the
        first cancel awaited aclose()."""
        harness = _make_harness()
        good = _assistant_msg("payload")
        done = _result_msg(session_id="sess-cancel-2")
        fake_gen = RecordingAsyncGen([
            ("yield", good),
            ("yield", done),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            await _drain(harness, tmp_path)

        # invoke() finished naturally; instance handle cleared by finally.
        assert harness._active_gen is None
        prior_close_count = fake_gen.aclose_calls
        # A late cancel() must not raise and must not re-close.
        await harness.cancel()
        assert fake_gen.aclose_calls == prior_close_count, (
            "cancel() called after invoke() has finished should be a "
            "no-op — instance handle was cleared, so no second aclose."
        )


# ----------------------------------------------------------------------
# TASK-FIX-COACHTRES01: UserMessage/ToolResultBlock → ToolResultEvent
# ----------------------------------------------------------------------


class TestToolResultTranslation:
    """The harness surfaces a Bash tool result (delivered as a UserMessage
    carrying ToolResultBlock content) as a ToolResultEvent.

    Pre-fix the UserMessage was dropped and the Coach independent-test path
    only ever saw the agent's narration (the FEAT-HARV narration-capture
    defect). These tests pin the emission contract the consumer
    (coach_validator._run_tests_via_sdk) depends on to capture real pytest
    stdout.
    """

    @pytest.mark.asyncio
    async def test_tool_result_block_yields_tool_result_event(self, tmp_path):
        harness = _make_harness(allowed_tools=["Bash"])
        # Realistic stream order: assistant (tool use narration) → user
        # (tool result = pytest stdout) → result.
        narrate = _assistant_msg("I'll run the test command.")
        tool_result = _user_msg_with_tool_result(
            content="45 passed in 0.13s", is_error=False, tool_use_id="tu-9"
        )
        done = _result_msg()
        fake_gen = RecordingAsyncGen([
            ("yield", narrate),
            ("yield", tool_result),
            ("yield", done),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        results = [e for e in events if isinstance(e, ToolResultEvent)]
        assert len(results) == 1
        assert results[0].content == "45 passed in 0.13s"
        assert results[0].is_error is False
        assert results[0].tool_use_id == "tu-9"
        # The ToolResultEvent precedes the terminal ResultMessageEvent so the
        # consumer (which breaks on ResultMessageEvent) sees it.
        idx_result = next(
            i for i, e in enumerate(events) if isinstance(e, ToolResultEvent)
        )
        idx_terminal = next(
            i for i, e in enumerate(events) if isinstance(e, ResultMessageEvent)
        )
        assert idx_result < idx_terminal

    @pytest.mark.asyncio
    async def test_tool_result_error_flag_is_preserved(self, tmp_path):
        harness = _make_harness(allowed_tools=["Bash"])
        tool_result = _user_msg_with_tool_result(
            content="pytest: command not found", is_error=True, tool_use_id="t2"
        )
        done = _result_msg()
        fake_gen = RecordingAsyncGen([
            ("yield", tool_result),
            ("yield", done),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        results = [e for e in events if isinstance(e, ToolResultEvent)]
        assert len(results) == 1
        assert results[0].is_error is True
        assert results[0].content == "pytest: command not found"

    @pytest.mark.asyncio
    async def test_tool_result_list_content_passed_through(self, tmp_path):
        """Structured (list) ToolResultBlock content is forwarded verbatim —
        the consumer's _extract_content_text handles the list form."""
        harness = _make_harness(allowed_tools=["Bash"])
        list_content = [{"type": "text", "text": "44 passed, 1 failed"}]
        tool_result = _user_msg_with_tool_result(
            content=list_content, is_error=False, tool_use_id="t3"
        )
        done = _result_msg()
        fake_gen = RecordingAsyncGen([
            ("yield", tool_result),
            ("yield", done),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        results = [e for e in events if isinstance(e, ToolResultEvent)]
        assert len(results) == 1
        assert results[0].content == list_content

    @pytest.mark.asyncio
    async def test_user_message_without_tool_result_yields_nothing(
        self, tmp_path
    ):
        """A UserMessage with no ToolResultBlock content emits no event —
        only ToolResultBlock entries are surfaced."""
        harness = _make_harness(allowed_tools=["Bash"])
        plain_user = UserMessage(content="just text, no tool result")
        done = _result_msg()
        fake_gen = RecordingAsyncGen([
            ("yield", plain_user),
            ("yield", done),
        ])

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            events = await _drain(harness, tmp_path)

        assert not [e for e in events if isinstance(e, ToolResultEvent)]
        assert any(isinstance(e, ResultMessageEvent) for e in events)
