"""AC-004 byte-compat parity tests (TASK-HMIG-006 Phase 4).

Asserts schema-subset parity of the orchestrator-side
``_extract_partial_from_messages`` output across both substrates.
Documented Wave-2 divergences from Design Decision D-7 are asserted
explicitly per
``.claude/rules/absence-of-failure-is-not-success.md`` — pairing a
"divergence-expected" assertion with the parity-expected ones converts
a potential false-green schema check (both substrates return empty
lists, so equality trivially holds) into a positive-evidence test that
fails the build if either substrate silently changes shape.

When TASK-HMIG-006.2 lands (helper-migration completes), the
divergence assertions invert to parity assertions. That inversion is
the verifiable signal the migration is done.

See ``guardkit/orchestrator/harness/README.md`` for the divergence table.

Coverage Target: >=85% (strict intensity)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, List

import pytest

from guardkit.orchestrator.agent_invoker import _extract_partial_from_messages
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    HarnessAdapter,
    HarnessEvent,
    ResultMessageEvent,
    ToolUseEvent,
)


# ============================================================================
# Substrate-shaped fixtures
#
# We build the raw-shape inputs each substrate would deliver:
#   - SDK: AssistantMessage / ResultMessage with .content list of TextBlock /
#     ToolUseBlock children. Duck-typed on type(block).__name__ per the
#     existing orchestrator helpers.
#   - LangGraph: a dict-shaped LangChain result (no .content attribute).
# ============================================================================


# Class names MUST be exactly "TextBlock" and "ToolUseBlock" because the
# orchestrator's _extract_partial_from_messages and _track_tool_use both
# duck-type via type(block).__name__ == "..." rather than isinstance().
# This is intentional resilience — see agent_invoker.py:344-349.


class TextBlock:
    """SDK-shaped TextBlock duck-type. Name matters: type(block).__name__."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.type = "text"


class ToolUseBlock:
    """SDK-shaped ToolUseBlock duck-type. Name matters: type(block).__name__."""

    def __init__(self, name: str, input: dict) -> None:
        self.name = name
        self.input = input
        self.type = "tool_use"


@dataclass
class _FakeSDKAssistantMessage:
    """SDK-shape AssistantMessage with .content list of typed blocks."""

    content: List[Any] = field(default_factory=list)


@dataclass
class _FakeSDKResultMessage:
    """SDK-shape ResultMessage carrying session_id + usage."""

    session_id: str | None = None
    stop_reason: str | None = "end_turn"
    usage: dict | None = None


# ============================================================================
# Harness stubs — yield the same event sequence each substrate would yield
# for a logically-equivalent turn.
# ============================================================================


class _StubSDKHarness(HarnessAdapter):
    """Yields events shaped exactly like ``ClaudeSDKHarness`` would.

    The ``raw`` slot on the assistant event carries the SDK-typed
    AssistantMessage; ``ToolUseEvent`` instances are yielded BEFORE the
    AssistantMessageEvent (TASK-HMIG-006.2 production parity).
    """

    def __init__(self, *, text: str, tool_calls: list[dict], session_id: str | None):
        self._text = text
        self._tool_calls = tool_calls
        self._session_id = session_id

    async def invoke(  # type: ignore[override]
        self, prompt, role, tools, cwd, *, timeout_seconds
    ) -> AsyncIterator[HarnessEvent]:
        # Build the SDK-shape AssistantMessage with TextBlock + ToolUseBlock
        # for the raw slot. The ToolUseEvent yields mirror what
        # ClaudeSDKHarness.invoke does after TASK-HMIG-006.2.
        blocks: List[Any] = [TextBlock(text=self._text)]
        for tc in self._tool_calls:
            blocks.append(
                ToolUseBlock(name=tc["name"], input=tc["input"])
            )
        sdk_msg = _FakeSDKAssistantMessage(content=blocks)

        # TASK-HMIG-006.2: yield ToolUseEvent per tool call before the
        # AssistantMessageEvent (production SDK harness ordering).
        for tc in self._tool_calls:
            yield ToolUseEvent(
                tool_use_id=tc.get("id", ""),
                name=tc["name"],
                input=tc["input"],
            )
        yield AssistantMessageEvent(text=self._text, raw=sdk_msg)

        sdk_result = _FakeSDKResultMessage(session_id=self._session_id)
        yield ResultMessageEvent(
            session_id=self._session_id,
            stop_reason="end_turn",
            usage=None,
            raw=sdk_result,
        )

    @property
    def supports_resume(self) -> bool:
        return True


class _StubLangGraphHarness(HarnessAdapter):
    """Yields events shaped exactly like ``LangGraphHarness`` would.

    The ``raw`` slot on the AssistantMessageEvent carries the LangChain
    dict (no ``.content`` attribute as a list of typed blocks);
    ``ToolUseEvent`` instances are yielded BEFORE the
    AssistantMessageEvent when ``tool_calls`` is non-empty
    (TASK-HMIG-006.2 production parity). The ResultMessageEvent carries
    ``session_id=None`` per AC-007.
    """

    def __init__(self, *, text: str, tool_calls: list[dict] | None = None):
        self._text = text
        self._tool_calls = tool_calls or []

    async def invoke(  # type: ignore[override]
        self, prompt, role, tools, cwd, *, timeout_seconds
    ) -> AsyncIterator[HarnessEvent]:
        # LangChain-shape result dict — no .content list of typed blocks
        langchain_dict = {
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": self._text},
            ],
        }
        # TASK-HMIG-006.2: yield ToolUseEvent per tool call before the
        # AssistantMessageEvent (production LangGraph harness ordering).
        for tc in self._tool_calls:
            yield ToolUseEvent(
                tool_use_id=tc.get("id", ""),
                name=tc["name"],
                input=tc.get("input", tc.get("args", {})),
            )
        yield AssistantMessageEvent(text=self._text, raw=langchain_dict)
        yield ResultMessageEvent(
            session_id=None, stop_reason="end_turn", usage=None
        )

    @property
    def supports_resume(self) -> bool:
        return False


# ============================================================================
# Helpers
# ============================================================================


async def _drive_to_response_messages(harness: HarnessAdapter) -> List[Any]:
    """Run a harness for one turn and collect the typed-events list.

    TASK-HMIG-006.2 migration: ``_extract_partial_from_messages`` now
    consumes a list of :class:`HarnessEvent` values (the orchestrator's
    ``harness_events`` accumulator), not a list of SDK message objects.
    This helper mirrors that accumulation pattern, appending each event
    as it arrives until the terminal ``ResultMessageEvent``. The name
    is preserved (rather than renamed to ``_drive_to_events``) so the
    existing test bodies keep reading; the docstring documents the
    schema change.
    """
    events: List[Any] = []
    async for event in harness.invoke(
        prompt="test prompt",
        role="player",
        tools=[],
        cwd=Path("."),
        timeout_seconds=30,
    ):
        events.append(event)
        if isinstance(event, ResultMessageEvent):
            break
    return events


# ============================================================================
# Schema-subset parity (the byte-compat contract)
# ============================================================================


_EXPECTED_KEYS = {
    "text_block_count",
    "tool_call_count",
    "file_modifications",
    "last_text_blocks",
    "message_count",
}

_EXPECTED_TYPES = {
    "text_block_count": int,
    "tool_call_count": int,
    "file_modifications": list,
    "last_text_blocks": list,
    "message_count": int,
}


class TestSchemaSubsetParity:
    """Top-level keys + types are identical across substrates."""

    @pytest.mark.asyncio
    async def test_text_only_turn_has_identical_schema(self):
        """Both substrates produce the same key set + value types for a
        text-only turn (no tools, no resume). This is the
        parity-expected case."""
        sdk = _StubSDKHarness(text="hello", tool_calls=[], session_id="abc-123")
        lg = _StubLangGraphHarness(text="hello")

        sdk_partial = _extract_partial_from_messages(
            await _drive_to_response_messages(sdk)
        )
        lg_partial = _extract_partial_from_messages(
            await _drive_to_response_messages(lg)
        )

        # Schema parity
        assert set(sdk_partial.keys()) == _EXPECTED_KEYS
        assert set(lg_partial.keys()) == _EXPECTED_KEYS

        # Type parity
        for key, expected_type in _EXPECTED_TYPES.items():
            assert isinstance(sdk_partial[key], expected_type), (
                f"SDK {key} type mismatch: {type(sdk_partial[key]).__name__}"
            )
            assert isinstance(lg_partial[key], expected_type), (
                f"LangGraph {key} type mismatch: {type(lg_partial[key]).__name__}"
            )

    @pytest.mark.asyncio
    async def test_text_only_turn_value_parity(self):
        """For a text-only turn (no tools, no resume), values are
        identical across substrates — this is the strict parity gate."""
        sdk = _StubSDKHarness(text="hello world", tool_calls=[], session_id=None)
        lg = _StubLangGraphHarness(text="hello world")

        sdk_partial = _extract_partial_from_messages(
            await _drive_to_response_messages(sdk)
        )
        lg_partial = _extract_partial_from_messages(
            await _drive_to_response_messages(lg)
        )

        # TASK-HMIG-006.2: text extraction parity is now true parity —
        # both substrates read the joined text off
        # AssistantMessageEvent.text rather than walking raw content.
        assert sdk_partial["text_block_count"] == 1
        assert lg_partial["text_block_count"] == 1, (
            "TASK-HMIG-006.2 regression: LangGraph text extraction "
            "should now match SDK (both consume "
            "AssistantMessageEvent.text). If this assertion fires, the "
            "typed-event dispatch in _extract_partial_from_messages has "
            "drifted back to duck-typing on raw content."
        )

        # Tool extraction parity (both empty — true parity)
        assert sdk_partial["tool_call_count"] == 0
        assert lg_partial["tool_call_count"] == 0
        assert sdk_partial["file_modifications"] == []
        assert lg_partial["file_modifications"] == []


# ============================================================================
# Documented Wave-2 divergences (per D-7) — divergence-expected cases
# ============================================================================


class TestDocumentedDivergences:
    """Per .claude/rules/absence-of-failure-is-not-success.md: each
    Wave-2 documented divergence was asserted explicitly so a silent
    regression (e.g. LangGraph suddenly producing tool_calls=[]) would
    be caught.

    TASK-HMIG-006.2 INVERSION: with the helper migration to typed
    ``HarnessEvent`` dispatch, the tool-use divergence is gone — both
    substrates now report tool_call_count=1 for a turn that carries
    one tool call. The session-id divergence remains documented per
    AC-007 (LangGraph checkpointer is out of scope).
    """

    @pytest.mark.asyncio
    async def test_tool_use_parity_post_migration(self):
        """TASK-HMIG-006.2 inversion (AC-003): SDK and LangGraph both
        populate tool_calls when a tool call is present. The previous
        ``test_tool_use_divergence_documented`` asserted
        ``lg_partial["tool_call_count"] == 0`` and was the verifiable
        signal pending migration; flipping it to ``== 1`` is the AC-003
        success signal.

        The LangGraph stub is also updated to yield ToolUseEvent
        directly (mirrors production LangGraphHarness emitting
        ToolUseEvent from AIMessage.tool_calls per Step 2 of the
        migration). Without that stub update, the test would pass
        ``lg_partial["tool_call_count"] == 0`` for the WRONG reason
        (stub omitted the event, not because dispatch failed).
        """
        sdk = _StubSDKHarness(
            text="modifying file",
            tool_calls=[
                {
                    "name": "Edit",
                    "input": {
                        "file_path": "src/foo.py",
                        "old_string": "x",
                        "new_string": "y",
                    },
                }
            ],
            session_id="uuid-abc",
        )
        lg = _StubLangGraphHarness(
            text="modifying file",
            tool_calls=[
                {
                    "id": "call-001",
                    "name": "Edit",
                    "input": {
                        "file_path": "src/foo.py",
                        "old_string": "x",
                        "new_string": "y",
                    },
                }
            ],
        )

        sdk_partial = _extract_partial_from_messages(
            await _drive_to_response_messages(sdk)
        )
        lg_partial = _extract_partial_from_messages(
            await _drive_to_response_messages(lg)
        )

        # SDK extracts the tool call (unchanged)
        assert sdk_partial["tool_call_count"] == 1, (
            "SDK regression: ToolUseEvent no longer extracted"
        )
        assert sdk_partial["file_modifications"] == ["src/foo.py"], (
            "SDK regression: Edit file_path no longer captured"
        )

        # TASK-HMIG-006.2 (AC-003): LangGraph now matches SDK — both
        # paths report tool_call_count == 1 via ToolUseEvent dispatch.
        assert lg_partial["tool_call_count"] == 1, (
            "TASK-HMIG-006.2 regression: LangGraph tool_call_count "
            "should now match SDK via ToolUseEvent dispatch. If this "
            "fires, the LangGraph harness stopped yielding ToolUseEvent "
            "or _extract_partial_from_messages stopped dispatching on "
            "ToolUseEvent."
        )
        assert lg_partial["file_modifications"] == ["src/foo.py"], (
            "TASK-HMIG-006.2 regression: LangGraph file_modifications "
            "should now match SDK — Edit tool_calls carry file_path in "
            "their args, picked up by the migrated extractor."
        )

    @pytest.mark.asyncio
    async def test_session_id_divergence_documented(self):
        """SDK ResultMessage carries session_id; LangGraph does not
        (supports_resume=False per AC-007). The session_id isn't in
        the partial-extract output — but the harness stream carries
        it via ResultMessageEvent.session_id, which the orchestrator
        captures into self._last_session_id. Assert both substrates
        produce the documented value."""
        sdk_session = "session-uuid-12345"
        sdk = _StubSDKHarness(text="", tool_calls=[], session_id=sdk_session)
        lg = _StubLangGraphHarness(text="")

        # Collect the events themselves (not response_messages) so we
        # can inspect ResultMessageEvent.session_id directly.
        sdk_events: List[HarnessEvent] = []
        async for event in sdk.invoke(
            prompt="", role="player", tools=[], cwd=Path("."), timeout_seconds=30
        ):
            sdk_events.append(event)

        lg_events: List[HarnessEvent] = []
        async for event in lg.invoke(
            prompt="", role="player", tools=[], cwd=Path("."), timeout_seconds=30
        ):
            lg_events.append(event)

        sdk_result = next(e for e in sdk_events if isinstance(e, ResultMessageEvent))
        lg_result = next(e for e in lg_events if isinstance(e, ResultMessageEvent))

        assert sdk_result.session_id == sdk_session, (
            "SDK regression: ResultMessageEvent.session_id no longer "
            "captured from ResultMessage"
        )
        assert lg_result.session_id is None, (
            "LangGraph drift: session_id now populated — has the "
            "LangGraph checkpointer integration landed? If so, INVERT "
            "this assertion and update AC-007 / D-07."
        )

    def test_supports_resume_divergence(self):
        """SDK harness reports supports_resume=True; LangGraph =False
        (per AC-007). Documented Wave-2 behaviour; no follow-up
        scheduled — JSON-on-disk checkpointing is the migration's
        resume mechanism per D-07."""
        sdk = _StubSDKHarness(text="", tool_calls=[], session_id=None)
        lg = _StubLangGraphHarness(text="")

        assert sdk.supports_resume is True
        assert lg.supports_resume is False


# ============================================================================
# Non-empty fixture surface (absence-of-failure-is-not-success)
# ============================================================================


class TestNonEmptyFixtureSurface:
    """Verify the fixture surface itself is non-empty per
    .claude/rules/absence-of-failure-is-not-success.md. Without this
    guard, a future regression that made all SDK extraction paths
    return zero would still pass the parity check trivially. Pin the
    SDK path's positive-evidence values so the test fails loudly if
    the SDK shape changes."""

    @pytest.mark.asyncio
    async def test_sdk_text_extraction_is_non_zero(self):
        """The SDK fixture MUST produce text_block_count > 0 for the
        text-with-tool case, otherwise the parity test above is a
        false-green."""
        sdk = _StubSDKHarness(
            text="non-empty body",
            tool_calls=[
                {"name": "Edit", "input": {"file_path": "f.py"}},
            ],
            session_id="x",
        )
        partial = _extract_partial_from_messages(
            await _drive_to_response_messages(sdk)
        )

        # Positive-evidence assertions (cannot be trivially satisfied
        # by zero-cardinality)
        assert partial["text_block_count"] >= 1, (
            "SDK fixture produced zero text — divergence test is "
            "now a false-green"
        )
        assert partial["tool_call_count"] >= 1, (
            "SDK fixture produced zero tool_calls — divergence test "
            "is now a false-green"
        )
        assert partial["message_count"] >= 2, (
            "SDK fixture should yield AssistantMessage + ResultMessage"
        )
