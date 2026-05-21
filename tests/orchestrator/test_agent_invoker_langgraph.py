"""End-to-end tests for the LangGraph dispatch path through :class:`AgentInvoker`.

Tests TASK-HMIG-006 Phase 3c AC-007 / AC-009:

* AC-003 lazy-import: the SDK default path does NOT touch guardkitfactory.
* Selector dispatch routes to :class:`LangGraphHarness` on
  ``GUARDKIT_HARNESS=langgraph``.
* AC-007 graceful-resume: when a caller offers ``resume_session_id`` and
  the resolved harness does not ``supports_resume``, the orchestrator
  logs the AC-007 warning and proceeds without raising.
* :class:`LangGraphHarnessError` raises when the wrapped LangChain model
  fails — directly through the harness, not via the orchestrator.
* Token-extraction graceful degradation: feeding the LangGraph response
  shape through ``_emit_llm_call_event`` does not raise, and the emitted
  ``LLMCallEvent`` carries ``(0, 0)`` tokens (default fallback) when no
  SDK ``usage`` attribute is present.
* End-to-end single-turn through the LangGraph path completes without
  exception.

The stub model uses
``langchain_core.language_models.fake_chat_models.FakeMessagesListChatModel``
(verified to be importable in this venv) so no LLM endpoint is hit.

Coverage focus: ``select_harness`` langgraph branch, AC-007 warning
emission in ``_invoke_with_role``, and graceful interaction between the
LangGraph event taxonomy and the duck-typed orchestrator instrumentation.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

# Stub-model import — verified working path in this venv (Python 3.14).
# The 'fake' submodule does not export FakeMessagesListChatModel here,
# only 'fake_chat_models' does. Keep this import inside the test module
# (not a shared fixture file) so future migrations notice immediately.
from langchain_core.language_models.fake_chat_models import (
    FakeMessagesListChatModel,
)
from langchain_core.messages import AIMessage

from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


_TEST_ENV_VAR = "GUARDKIT_HARNESS_TEST_ONLY_LG"


def _make_invoker(
    tmp_path: Path,
    emitter: Optional[Any] = None,
    **kwargs: Any,
) -> Any:
    """Construct an :class:`AgentInvoker` with mocked-out dependencies.

    Mirrors the ``_make_invoker`` helper in
    ``tests/orchestrator/instrumentation/test_llm_call_events.py``.
    """
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


def _make_stub_model(response_text: str = "hello from langgraph") -> Any:
    """Construct a stub LangChain chat model that emits a fixed AI response."""
    return FakeMessagesListChatModel(responses=[AIMessage(content=response_text)])


def _make_stub_langgraph_harness(response_text: str = "stub langgraph response"):
    """Build a :class:`LangGraphHarness` subclass with a faked ``invoke`` method.

    The real :class:`LangGraphHarness.invoke` calls
    :func:`deepagents.create_deep_agent`, which expects real tool objects
    and a fully-configured chat model. Building that fixture here would
    bleed deepagents internals into a guardkit-side test (and pull in
    network/model dependencies). Instead we subclass
    :class:`LangGraphHarness` and override :meth:`invoke` to emit the
    *same* event sequence the real implementation produces (one
    :class:`AssistantMessageEvent` carrying a langchain-style dict, then
    one terminal :class:`ResultMessageEvent` with ``session_id=None``).

    This preserves the orchestrator-side boundary under test:

    * ``isinstance(harness, LangGraphHarness)`` — selector dispatch works.
    * ``harness.supports_resume is False`` — AC-007 warning fires.
    * The event taxonomy the orchestrator consumes is byte-for-byte
      identical to what the real harness yields (per TASK-HMIG-001B).
    """
    from guardkitfactory.harness import LangGraphHarness

    class _StubLangGraphHarness(LangGraphHarness):
        """Subclass that fakes ``invoke`` without touching deepagents."""

        async def invoke(  # type: ignore[override]
            self,
            prompt: str,
            role: str,
            tools: list,
            cwd: Path,
            *,
            timeout_seconds: int,
        ):
            # Mirror the real harness output shape: a dict-like 'raw'
            # carrying a langchain-style {"messages": [AIMessage]} on
            # the AssistantMessageEvent, no raw on the terminal event.
            fake_result = {
                "messages": [AIMessage(content=response_text)],
            }
            yield AssistantMessageEvent(text=response_text, raw=fake_result)
            yield ResultMessageEvent(
                session_id=None,
                stop_reason="end_turn",
                usage=None,
            )

    return _StubLangGraphHarness(model=_make_stub_model(response_text))


def _build_mock_sdk() -> ModuleType:
    """Build a fake claude_agent_sdk module for the AC-003 lazy-import test.

    Mirrors the SDK-shaped module that
    ``test_llm_call_events.py:_build_mock_sdk`` constructs so the SDK
    default path can run end-to-end without touching guardkitfactory.
    """
    mod = ModuleType("claude_agent_sdk")

    class _ResultMessage:
        pass

    class _AssistantMessage:
        pass

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


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_cleanup():
    """Disable SDK cleanup handler installation across all tests."""
    with patch("guardkit.orchestrator.agent_invoker._install_sdk_cleanup_handler"):
        yield


@pytest.fixture(autouse=True)
def _patch_sdk_utils():
    """Force ``check_assistant_message_error`` to a no-op so duck-typed
    LangGraph dicts do not surprise the orchestrator on the LangGraph path."""
    with patch(
        "guardkit.orchestrator.sdk_utils.check_assistant_message_error",
        return_value=None,
    ):
        yield


@pytest.fixture
def mock_sdk():
    """Install mock SDK module into sys.modules for the SDK-path tests.

    Mirrors the fixture in
    ``tests/orchestrator/instrumentation/test_llm_call_events.py``.
    """
    sdk = _build_mock_sdk()
    original = sys.modules.get("claude_agent_sdk")
    sys.modules["claude_agent_sdk"] = sdk
    yield sdk
    if original is not None:
        sys.modules["claude_agent_sdk"] = original
    else:
        sys.modules.pop("claude_agent_sdk", None)


# ----------------------------------------------------------------------
# AC-003: lazy-import — SDK default path must not touch guardkitfactory
# ----------------------------------------------------------------------


class TestLazyImportWhenSdkDefault:
    """AC-003: SDK path imports nothing from guardkitfactory."""

    @pytest.mark.asyncio
    async def test_sdk_path_does_not_construct_langgraph_harness(
        self,
        tmp_path: Path,
        mock_sdk: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SDK turn must not construct :class:`LangGraphHarness`.

        Patches ``guardkitfactory.harness.LangGraphHarness`` with a
        sentinel that explodes if anyone constructs it, then runs a
        full SDK invocation. If the lazy import is honoured, the
        sentinel is never touched.
        """
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        # Default env var (unset) → SDK path.
        monkeypatch.delenv("GUARDKIT_HARNESS", raising=False)

        # Sentinel: construction raises so the assertion in the SDK
        # default path is unmistakable.
        construction_calls: list[Any] = []

        class ExplodingLangGraphHarness:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                construction_calls.append((args, kwargs))
                raise AssertionError(
                    "LangGraphHarness must not be constructed on the SDK default path"
                )

        # Install a stand-in guardkitfactory.harness module so that any
        # accidental import would resolve to our exploding class — but
        # the real assertion is that this path is never reached.
        stub_mod = ModuleType("guardkitfactory.harness")
        stub_mod.LangGraphHarness = ExplodingLangGraphHarness  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "guardkitfactory.harness", stub_mod)

        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)

        # Build SDK-path fake: query() returns a single ResultMessage.
        result_msg = mock_sdk.ResultMessage()  # type: ignore[attr-defined]
        usage = MagicMock()
        usage.input_tokens = 100
        usage.output_tokens = 50
        result_msg.usage = usage

        async def fake_query(**kw: Any):
            yield result_msg

        mock_sdk.query = fake_query  # type: ignore[attr-defined]

        await invoker._invoke_with_role(
            prompt="TASK-TEST-LG-001 SDK default path",
            agent_type="player",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
        )
        await asyncio.sleep(0.05)

        # AC-003: LangGraphHarness must never have been constructed.
        assert construction_calls == []

    def test_sdk_path_returns_claude_sdk_harness(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Direct check that ``select_harness`` on the SDK default path
        returns :class:`ClaudeSDKHarness`, not :class:`LangGraphHarness`."""
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness
        from guardkit.orchestrator.harness.selector import select_harness

        monkeypatch.delenv(_TEST_ENV_VAR, raising=False)

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            sdk_timeout_seconds=60,
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
            max_turns=30,
            model=None,
            resume_session_id=None,
            sdk_debug_dir=None,
            cleanup_handler_installer=lambda: None,
        )

        assert isinstance(harness, ClaudeSDKHarness)


# ----------------------------------------------------------------------
# Selector dispatch — env var routing to LangGraphHarness
# ----------------------------------------------------------------------


class TestSelectorRoutesToLangGraphHarness:
    """``GUARDKIT_HARNESS=langgraph`` dispatches to LangGraphHarness."""

    def test_env_var_routes_to_langgraph(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end env-var routing returns a LangGraphHarness."""
        from guardkit.orchestrator.harness.selector import select_harness
        from guardkitfactory.harness import LangGraphHarness

        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        stub_model = _make_stub_model()
        harness = select_harness(env_var=_TEST_ENV_VAR, model=stub_model)

        assert isinstance(harness, LangGraphHarness)
        # Not a ClaudeSDKHarness — verify exclusivity.
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        assert not isinstance(harness, ClaudeSDKHarness)


# ----------------------------------------------------------------------
# AC-007 supports_resume == False — orchestrator warning fires
# ----------------------------------------------------------------------


class TestResumeWarningWhenLangGraphSelected:
    """AC-007: orchestrator emits warning when resume offered to LangGraph."""

    @pytest.mark.asyncio
    async def test_warning_fires_when_resume_offered_to_langgraph(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When ``resume_session_id`` is offered to a harness that does
        not support resume, ``_invoke_with_role`` logs the AC-007
        warning and proceeds — the resume intent is announced, not
        silently swallowed.
        """
        invoker = _make_invoker(tmp_path, emitter=NullEmitter(capture=True))

        # Pre-built LangGraphHarness with a faked invoke() so this test
        # is hermetic (no deepagents construction, no network).
        prebuilt = _make_stub_langgraph_harness()

        # Patch the orchestrator's reference to select_harness so the
        # construction step returns our pre-built langgraph harness.
        with patch(
            "guardkit.orchestrator.agent_invoker.select_harness",
            return_value=prebuilt,
        ):
            with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
                await invoker._invoke_with_role(
                    prompt="TASK-TEST-LG-AC007 resume offered to langgraph",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                    resume_session_id="prior-session-uuid-1234-5678",
                )
                await asyncio.sleep(0.05)

        # AC-007: the warning string must surface the resume intent and
        # name the harness type so operators see why the resume was
        # dropped.
        warning_records = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "AC-007" in r.getMessage()
        ]
        assert len(warning_records) == 1
        msg = warning_records[0].getMessage()
        assert "resume_session_id" in msg
        assert "does not support_resume" in msg
        # The stub subclass name shows up in the warning; the real
        # production-path name is LangGraphHarness but here we just
        # assert the harness type was named somewhere in the message.
        assert "LangGraphHarness" in msg
        # Confirm only the truncated session-id prefix (16 chars) is logged.
        # "prior-session-uuid-1234-5678" → [:16] = "prior-session-uu"
        assert "prior-session-uu" in msg
        # Confirm the FULL UUID is not leaked in plaintext.
        assert "prior-session-uuid-1234-5678" not in msg

    @pytest.mark.asyncio
    async def test_no_warning_when_resume_is_none(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Caller does NOT supply a resume_session_id → no warning."""
        invoker = _make_invoker(tmp_path, emitter=NullEmitter(capture=True))
        prebuilt = _make_stub_langgraph_harness()

        with patch(
            "guardkit.orchestrator.agent_invoker.select_harness",
            return_value=prebuilt,
        ):
            with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
                await invoker._invoke_with_role(
                    prompt="TASK-TEST-LG-AC007 fresh session",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                    resume_session_id=None,
                )
                await asyncio.sleep(0.05)

        ac007_warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "AC-007" in r.getMessage()
        ]
        assert ac007_warnings == []


# ----------------------------------------------------------------------
# LangGraphHarnessError raised when stub model fails
# ----------------------------------------------------------------------


class TestLangGraphHarnessErrorOnFailure:
    """:class:`LangGraphHarnessError` wraps wrapped-stack failures."""

    @pytest.mark.asyncio
    async def test_raises_when_model_construction_or_invoke_fails(
        self,
        tmp_path: Path,
    ) -> None:
        """A model that crashes on ``ainvoke`` surfaces as :class:`LangGraphHarnessError`.

        Drives the harness directly (not via the orchestrator) so the
        assertion is on the harness's own exception-wrapping contract.
        """
        from guardkitfactory.harness import (
            LangGraphHarness,
            LangGraphHarnessError,
        )

        class RaisingModel:
            """Stub model with no LangChain ChatModel interface — guaranteed
            to break either at :func:`create_deep_agent` construction or
            at :meth:`ainvoke`. Either failure path must wrap into
            :class:`LangGraphHarnessError`."""

            def __init__(self) -> None:
                self.boom_message = "stub-model-failed-intentionally"

            def invoke(self, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError(self.boom_message)

            async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError(self.boom_message)

        harness = LangGraphHarness(model=RaisingModel())

        with pytest.raises(LangGraphHarnessError) as exc_info:
            async for _ in harness.invoke(
                prompt="raise me",
                role="player",
                tools=[],
                cwd=tmp_path,
                timeout_seconds=10,
            ):
                pass

        msg = str(exc_info.value)
        # The wrapper must name the role so failures stay attributable.
        assert "role=" in msg
        assert "player" in msg


# ----------------------------------------------------------------------
# Token-extraction graceful degradation
# ----------------------------------------------------------------------


class TestTokenExtractionGracefulDegradation:
    """Token extraction does not raise on LangGraph-shaped messages."""

    @pytest.mark.asyncio
    async def test_emit_llm_call_event_handles_langgraph_messages(
        self,
        tmp_path: Path,
    ) -> None:
        """Running through the LangGraph path emits an LLMCallEvent with
        ``(0, 0)`` tokens — the duck-typed ``extract_token_usage`` returns
        the fallback when no message has a ``usage`` attribute."""
        emitter = NullEmitter(capture=True)
        invoker = _make_invoker(tmp_path, emitter=emitter)
        prebuilt = _make_stub_langgraph_harness("token-test response")

        with patch(
            "guardkit.orchestrator.agent_invoker.select_harness",
            return_value=prebuilt,
        ):
            await invoker._invoke_with_role(
                prompt="TASK-TEST-LG-TOK token extraction",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
            )
            await asyncio.sleep(0.05)

        # Exactly one LLMCallEvent must have been emitted and it must
        # carry the graceful-fallback token counts. The orchestrator
        # MUST NOT crash even though the messages aren't SDK-shaped.
        events = [e for e in emitter.events if isinstance(e, LLMCallEvent)]
        assert len(events) == 1
        event = events[0]
        assert event.status == "ok"
        # extract_token_usage returns (0, 0) when nothing carries
        # `.usage` — that's the graceful degradation contract.
        assert event.input_tokens == 0
        assert event.output_tokens == 0


# ----------------------------------------------------------------------
# End-to-end single-turn through LangGraph
# ----------------------------------------------------------------------


class TestEndToEndSingleTurn:
    """A complete LangGraph turn through ``_invoke_with_role`` succeeds."""

    @pytest.mark.asyncio
    async def test_end_to_end_invoke(
        self,
        tmp_path: Path,
    ) -> None:
        """Invoker call completes without exception; ``_last_session_id`` stays None."""
        invoker = _make_invoker(tmp_path, emitter=NullEmitter(capture=True))
        prebuilt = _make_stub_langgraph_harness("end-to-end response text")

        with patch(
            "guardkit.orchestrator.agent_invoker.select_harness",
            return_value=prebuilt,
        ):
            await invoker._invoke_with_role(
                prompt="TASK-TEST-LG-E2E end-to-end single turn",
                agent_type="player",
                allowed_tools=["Read", "Write"],
                permission_mode="acceptEdits",
            )
            await asyncio.sleep(0.05)

        # LangGraphHarness reports session_id=None → orchestrator's
        # _last_session_id must mirror that.
        assert invoker._last_session_id is None
