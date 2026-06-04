"""ClaudeSDKHarness — concrete :class:`HarnessAdapter` wrapping claude-agent-sdk.

This module is the SDK-side concrete implementation of the substrate
boundary defined in :mod:`guardkit.orchestrator.harness.adapter`. It
wraps the existing ``claude_agent_sdk.query`` + ``ClaudeAgentOptions``
call surface that lived inline in
``AgentInvoker._invoke_with_role`` (agent_invoker.py:2398-2740)
prior to TASK-HMIG-006, and translates the SDK's message stream
(``AssistantMessage`` / ``ResultMessage``) into the substrate-agnostic
:class:`~guardkit.orchestrator.harness.adapter.HarnessEvent` taxonomy
the orchestrator now consumes.

Behaviour preserved verbatim from the inline implementation:

* TASK-FIX-7A03 message-parse resilience: ``MessageParseError`` and
  ``ValueError`` raised mid-stream are logged and skipped; if every
  message is unparseable the harness raises
  :class:`AgentInvocationError` with ``error_class="MessageParseError"``.
* TASK-RFX-B20B session_id capture: ``ResultMessage.session_id`` is
  captured into :attr:`session_id` so the orchestrator can persist it
  for SDK-session resumption.
* TASK-RFX-8332 / TASK-FIX-GEN1 generator hygiene: the query()
  generator is held by explicit reference, drained on
  ``ResultMessage``, and ``aclose()``-d under a 5-second
  :func:`asyncio.timeout` in the finally block.
* TASK-FIX-7A03 exception cascade: SDK-specific exceptions
  (``CLINotFoundError``, ``ProcessError``, ``CLIJSONDecodeError``)
  and the catch-all ``ValueError`` / generic ``Exception`` cases are
  all translated to :class:`AgentInvocationError` *inside* the harness
  so the orchestrator only deals with substrate-agnostic exceptions
  (TASK-HMIG-006 Design Decision D-4).

Per Design Decision D-1, ``AssistantMessage`` translates into a single
:class:`AssistantMessageEvent` with the joined text content; the
``raw`` slot is populated with the original SDK message so any remaining
duck-typed consumer in ``agent_invoker.py`` (e.g. the
``check_assistant_message_error`` API-error scan, the heartbeat
``ToolUseBlock`` log gated to the specialist path) keeps working
unchanged.

TASK-HMIG-006.2 extension: When an ``AssistantMessage`` carries
``ToolUseBlock`` content blocks, the harness now ALSO yields one
:class:`ToolUseEvent` per block BEFORE the :class:`AssistantMessageEvent`.
This mirrors what the LangGraph harness emits from
``AIMessage.tool_calls`` and lets the migrated
``_track_tool_use`` / ``_extract_partial_from_messages`` consumers
dispatch on a typed event instead of walking ``event.raw.content``. The
order (tool-uses first, then the joined-text assistant event) keeps the
typed-event ordering aligned with the textual order in the source
message — useful when partial-extract output is interleaved.

The :meth:`invoke` ``tools`` and ``timeout_seconds`` parameters are
accepted to satisfy the :class:`HarnessAdapter` ABC contract, but the
SDK harness primarily uses the constructor-supplied ``allowed_tools``
and ``sdk_timeout_seconds`` because the SDK's tool-list lives on
``ClaudeAgentOptions`` and the SDK enforces its own timeout via
``asyncio.timeout`` in the orchestrator. Concrete agreement on which
copy wins is documented in the orchestrator (TASK-HMIG-006 Phase 3b
caller).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, List, Optional

from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    HarnessAdapter,
    HarnessEvent,
    ResultMessageEvent,
    ToolUseEvent,
)

logger = logging.getLogger(__name__)


class ClaudeSDKHarness(HarnessAdapter):
    """:class:`HarnessAdapter` wrapping ``claude_agent_sdk.query``.

    Single-use per invocation per TASK-HMIG-006 Design Decision D-6:
    callers construct a fresh instance for each :meth:`invoke` call.
    The :attr:`session_id` attribute is therefore the session of the
    most recently completed invocation on *this* instance.

    Parameters
    ----------
    sdk_timeout_seconds:
        SDK-side timeout; constructor copy is used when the
        :meth:`invoke` ``timeout_seconds`` argument cannot be deferred to.
    allowed_tools:
        List of tool names exposed to the SDK via
        ``ClaudeAgentOptions.allowed_tools``.
    permission_mode:
        One of ``"acceptEdits"`` / ``"bypassPermissions"`` matching the
        SDK's enum string.
    max_turns:
        Maximum SDK internal turns; passed through to
        ``ClaudeAgentOptions.max_turns``.
    setting_sources:
        SDK ``ClaudeAgentOptions.setting_sources`` value controlling which
        settings layers the agent loads (e.g. ``["project"]`` for
        project-only context, ``["user", "project"]`` for both). Defaults
        to ``["project"]`` so existing callers that do not pass it (the
        ``_invoke_with_role`` player/coach path) keep the project-only
        behaviour the harness previously hardcoded. The pre-loop design
        phase (TASK-HMIG-006.4) passes it explicitly.
    model:
        Optional model override (e.g. ``"claude-sonnet-4-5-20250929"``).
        When ``None`` the SDK picks its default.
    resume_session_id:
        Optional prior session ID for SDK-side resumption (TASK-RFX-B20B).
        When ``None`` a fresh session is started.
    sdk_debug_dir:
        Optional path the harness can use to preserve raw SDK events for
        debugging. Currently accepted for forward-compat; the
        orchestrator owns sdk_debug instrumentation in Phase 3a.
    cleanup_handler_installer:
        Optional callable invoked with the running asyncio loop before
        the query loop starts. Lets the orchestrator inject its
        existing ``_install_sdk_cleanup_handler`` without the harness
        depending on it directly (TASK-HMIG-006 Design Decision D-6).
    """

    def __init__(
        self,
        *,
        sdk_timeout_seconds: int,
        allowed_tools: List[str],
        permission_mode: str,
        max_turns: int,
        model: Optional[str] = None,
        resume_session_id: Optional[str] = None,
        sdk_debug_dir: Optional[Path] = None,
        cleanup_handler_installer: Optional[
            Callable[[asyncio.AbstractEventLoop], None]
        ] = None,
        setting_sources: Optional[List[str]] = None,
    ) -> None:
        self._sdk_timeout_seconds = sdk_timeout_seconds
        self._allowed_tools = list(allowed_tools)
        self._permission_mode = permission_mode
        self._max_turns = max_turns
        self._model = model
        # Default to project-only context — preserves the value the
        # harness previously hardcoded in invoke() (TASK-HMIG-006.4).
        self._setting_sources = (
            list(setting_sources) if setting_sources is not None else ["project"]
        )
        self._resume_session_id = resume_session_id
        self._sdk_debug_dir = sdk_debug_dir
        self._cleanup_handler_installer = cleanup_handler_installer
        self._session_id: Optional[str] = None

    @property
    def session_id(self) -> Optional[str]:
        """Session ID captured from the most recent ``ResultMessage``.

        ``None`` until :meth:`invoke` runs and observes a terminal
        ``ResultMessage`` with a non-None ``session_id`` (TASK-RFX-B20B).
        """
        return self._session_id

    @property
    def supports_resume(self) -> bool:
        """SDK harness supports session resumption (TASK-HMIG-006 AC-007).

        Matches the SDK's ``ClaudeAgentOptions.resume`` field semantics:
        a non-None ``resume_session_id`` constructor argument is wired
        into the SDK options when present.
        """
        return True

    async def invoke(
        self,
        prompt: str,
        role: str,
        tools: list,
        cwd: Path,
        *,
        timeout_seconds: int,
    ) -> AsyncGenerator[HarnessEvent, None]:
        """Stream :class:`HarnessEvent` values for a single agent turn.

        Translates the SDK's message stream into the substrate-agnostic
        HarnessEvent taxonomy. The ``tools`` and ``timeout_seconds``
        arguments are accepted for interface compliance with
        :class:`HarnessAdapter` but the SDK path uses the constructor
        copies (``self._allowed_tools`` / ``self._sdk_timeout_seconds``)
        because the SDK's tool-list lives on ``ClaudeAgentOptions`` and
        the orchestrator wraps with its own ``asyncio.timeout``.

        Raises
        ------
        AgentInvocationError
            For any SDK-specific failure mode. Per TASK-HMIG-006
            Design Decision D-4, all SDK exceptions are normalised
            *inside* the harness so the orchestrator's catch cascade
            is substrate-agnostic.
        """
        # Lazy import block — mirrors agent_invoker.py:2398-2438 exactly.
        # Imports here (not at module load) so test fixtures that mock
        # claude_agent_sdk as a non-package MagicMock do not choke on
        # unrelated tests. The ImportError diagnostic is preserved
        # verbatim for cross-environment parity.
        try:
            from claude_agent_sdk import (
                query,
                ClaudeAgentOptions,
                CLINotFoundError,
                ProcessError,
                CLIJSONDecodeError,
                AssistantMessage,
                ResultMessage,
            )
        except ImportError as e:
            diagnosis = (
                f"Claude Agent SDK import failed.\n"
                f"  Error: {e}\n"
                f"  Python: {sys.executable}\n"
                f"  sys.path (first 3): {sys.path[:3]}\n\n"
                f"To fix:\n"
                f"  pip install claude-agent-sdk\n"
                f"  # OR for full autobuild support:\n"
                f"  pip install guardkit-py[autobuild]"
            )
            raise AgentInvocationError(diagnosis) from e

        # TASK-FIX-7A03: MessageParseError sentinel fallback. Tests that
        # mock claude_agent_sdk as a non-package MagicMock cannot resolve
        # the _errors submodule import — the sentinel keeps the typed
        # except clause well-formed in those test environments.
        try:
            from claude_agent_sdk._errors import MessageParseError
        except ImportError:
            class MessageParseError(Exception):  # type: ignore[no-redef]
                """Sentinel when SDK does not expose _errors submodule."""
                pass

        # TASK-HMIG-006 D-6: cleanup handler installed inside invoke()
        # because the SDK subprocess lifetime is per-invocation, not
        # per-harness-instance.
        if self._cleanup_handler_installer is not None:
            self._cleanup_handler_installer(asyncio.get_running_loop())

        # Build ClaudeAgentOptions mirroring agent_invoker.py:2448-2466.
        options_kwargs: dict[str, Any] = dict(
            cwd=str(cwd),
            allowed_tools=self._allowed_tools,
            permission_mode=self._permission_mode,
            max_turns=self._max_turns,
            setting_sources=self._setting_sources,
        )
        if self._model is not None:
            options_kwargs["model"] = self._model
        if self._resume_session_id is not None:
            options_kwargs["resume"] = self._resume_session_id
            logger.info(
                f"Resuming SDK session: {self._resume_session_id[:16]}..."
            )

        # Translate any SDK construction failure into AgentInvocationError
        # before the query loop starts so the orchestrator never sees an
        # SDK-specific exception type (D-4).
        try:
            options = ClaudeAgentOptions(**options_kwargs)
        except ValueError as e:
            raise AgentInvocationError(
                f"SDK value error for role {role} ({type(e).__name__}): {e}",
                error_class=type(e).__name__,
            ) from e

        # TASK-RFX-8332: hold explicit reference to query() generator so
        # we can call aclose() in the finally block, preventing GC from
        # scheduling athrow(GeneratorExit) on the wrong asyncio Task.
        gen: Any = None
        response_messages: List[Any] = []
        unparseable_count = 0
        try:
            try:
                gen = query(prompt=prompt, options=options)
                gen_iter = gen.__aiter__()
                while True:
                    try:
                        message = await gen_iter.__anext__()
                    except StopAsyncIteration:
                        break
                    except (MessageParseError, ValueError) as parse_err:
                        # TASK-FIX-7A03: per-message skip + WARN. Production
                        # SDK gens terminate after the first uncaught raise;
                        # the next __anext__ call observes StopAsyncIteration
                        # and the loop exits cleanly with whatever parsed.
                        unparseable_count += 1
                        logger.warning(
                            f"TASK-FIX-7A03: Skipping unparseable SDK "
                            f"message in {role} stream "
                            f"(error_class={type(parse_err).__name__}): "
                            f"{parse_err}"
                        )
                        continue

                    response_messages.append(message)

                    if isinstance(message, AssistantMessage):
                        # TASK-HMIG-006.2: emit one ToolUseEvent per
                        # ToolUseBlock BEFORE the AssistantMessageEvent so
                        # the migrated _track_tool_use /
                        # _extract_partial_from_messages consumers can
                        # dispatch on typed events instead of walking
                        # event.raw.content. ToolUseBlock is duck-typed by
                        # class name to avoid an SDK import (matches the
                        # heartbeat scan at agent_invoker.py:2930-2945).
                        for block in getattr(message, "content", None) or []:
                            if type(block).__name__ != "ToolUseBlock":
                                continue
                            tool_input = getattr(block, "input", {}) or {}
                            if not isinstance(tool_input, dict):
                                tool_input = {}
                            yield ToolUseEvent(
                                tool_use_id=getattr(block, "id", "") or "",
                                name=getattr(block, "name", "") or "",
                                input=tool_input,
                            )
                        text = _extract_assistant_text(message)
                        yield AssistantMessageEvent(text=text, raw=message)
                    elif isinstance(message, ResultMessage):
                        # TASK-RFX-B20B: capture session_id for resumption.
                        self._session_id = getattr(
                            message, "session_id", None
                        )
                        # TASK-FIX-GEN1: drain remaining messages so the
                        # generator exhausts naturally; prevents aclose()
                        # in the finally block from triggering AnyIO
                        # cancel-scope CancelledError.
                        try:
                            async for _ in gen:
                                pass
                        except Exception:
                            pass  # safe to ignore during drain
                        gen = None  # exhausted; skip aclose() in finally

                        # TASK-FIX-7A03 post-stream resilience bookkeeping
                        # runs BEFORE the terminal yield so the WARN line
                        # (or the structured raise) is emitted even when
                        # the caller exits the async-for after consuming
                        # the ResultMessageEvent. (When the caller breaks
                        # out of `async for`, Python schedules aclose()
                        # which throws GeneratorExit at the next resume —
                        # code after the terminal yield does NOT run.)
                        if unparseable_count > 0:
                            if not response_messages:
                                raise AgentInvocationError(
                                    f"{unparseable_count} messages unparseable "
                                    f"in {role} stream "
                                    f"(no valid messages received)",
                                    error_class="MessageParseError",
                                )
                            logger.warning(
                                f"TASK-FIX-7A03: {role} stream completed with "
                                f"{unparseable_count} unparseable message(s) "
                                f"dropped; {len(response_messages)} message(s) "
                                f"parsed successfully"
                            )

                        yield ResultMessageEvent(
                            session_id=self._session_id,
                            stop_reason=getattr(message, "stop_reason", None),
                            usage=getattr(message, "usage", None),
                            raw=message,
                        )
                        break
                    # Other (non-Assistant, non-Result) messages are
                    # appended to response_messages for the post-stream
                    # bookkeeping but yield no HarnessEvent — they were
                    # never surfaced as events in the pre-refactor path
                    # either (the inline loop only dispatched
                    # `isinstance(message, ResultMessage)`).

                # TASK-FIX-7A03 post-stream resilience bookkeeping for
                # streams that ended without a ResultMessage (production
                # SDK terminates the async-gen after the first uncaught
                # raise → StopAsyncIteration on the next __anext__). The
                # ResultMessage branch runs its own bookkeeping above
                # before yielding (so the WARN survives GeneratorExit
                # from caller-side break).
                if unparseable_count > 0:
                    if not response_messages:
                        raise AgentInvocationError(
                            f"{unparseable_count} messages unparseable "
                            f"in {role} stream "
                            f"(no valid messages received)",
                            error_class="MessageParseError",
                        )
                    logger.warning(
                        f"TASK-FIX-7A03: {role} stream completed with "
                        f"{unparseable_count} unparseable message(s) "
                        f"dropped; {len(response_messages)} message(s) "
                        f"parsed successfully"
                    )
            except AgentInvocationError:
                # Already-structured — pass through untouched so the
                # error_class (e.g. "MessageParseError") survives the
                # outer wrapping below.
                raise
            except (asyncio.TimeoutError, asyncio.CancelledError):
                # Timeout / cancellation belong to the orchestrator's
                # outer asyncio.timeout(...) + asyncio.CancelledError
                # cascade — the orchestrator translates TimeoutError to
                # SDKTimeoutError and runs partial-extract on
                # CancelledError. The harness must not swallow either
                # into AgentInvocationError or the orchestrator-side
                # semantics break (test_llm_call_events.py expects
                # SDKTimeoutError, not AgentInvocationError).
                raise
            except CLINotFoundError as e:
                raise AgentInvocationError(
                    "Claude Code CLI not installed. "
                    "Run: npm install -g @anthropic-ai/claude-code"
                ) from e
            except ProcessError as e:
                raise AgentInvocationError(
                    f"SDK process failed (exit {e.exit_code}): {e.stderr}"
                ) from e
            except CLIJSONDecodeError as e:
                raise AgentInvocationError(
                    f"Failed to parse SDK response: {e}"
                ) from e
            except ValueError as e:
                # D-4 architectural tightening: ValueError raised outside
                # the per-message skip clause (e.g. from query() itself)
                # is normalised here so the orchestrator never sees raw
                # ValueError from the harness boundary.
                raise AgentInvocationError(
                    f"SDK value error for role {role} "
                    f"({type(e).__name__}): {e}",
                    error_class=type(e).__name__,
                ) from e
            except Exception as e:
                raise AgentInvocationError(
                    f"SDK invocation failed for role {role} "
                    f"({type(e).__name__}): {str(e)}",
                    error_class=type(e).__name__,
                ) from e
        finally:
            # TASK-RFX-8332: explicitly close the query() async generator
            # to prevent GC finalization from scheduling
            # athrow(GeneratorExit) on a wrong asyncio Task.
            if gen is not None:
                with suppress(Exception):
                    try:
                        async with asyncio.timeout(5):
                            await gen.aclose()
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        pass


def _extract_assistant_text(message: Any) -> str:
    """Join all ``TextBlock.text`` fields in an ``AssistantMessage``.

    Mirrors the existing inline shape: only ``TextBlock`` content blocks
    contribute to the joined text. ``ToolUseBlock`` blocks are NOT
    joined into the text — they are accessible via the raw SDK message
    on :class:`AssistantMessageEvent.raw` per Design Decision D-1.

    Duck-typed on ``type(block).__name__`` to match the rest of the
    orchestrator's lenient inspection — keeps the harness importable
    even when test fixtures supply MagicMock-shaped blocks.
    """
    content = getattr(message, "content", None) or []
    parts: List[str] = []
    for block in content:
        if type(block).__name__ != "TextBlock":
            continue
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)


__all__ = ["ClaudeSDKHarness"]
