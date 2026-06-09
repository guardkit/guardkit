"""HarnessAdapter — abstract substrate interface for autobuild Player/Coach invocations.

This module defines the cross-repo boundary between GuardKit's orchestrator
and pluggable execution harnesses (Anthropic claude-agent-sdk today,
LangGraph tomorrow). It ships only the abstract surface — concrete
implementations live elsewhere:

* ``ClaudeSDKHarness`` (legacy, claude-agent-sdk + Anthropic API) will be
  added to ``guardkit.orchestrator.harness`` in TASK-HMIG-006 alongside the
  ``agent_invoker.py`` refactor that consumes this ABC.
* ``LangGraphHarness`` (new, LangGraph-based) lives in the **separate
  ``guardkitfactory`` package** (see TASK-HMIG-001B in that repo) and is
  imported by ``agent_invoker.py`` only after the ``GUARDKIT_HARNESS``
  cutover flag is set to ``"langgraph"`` (default ``"sdk"``).

This module deliberately imports nothing from ``claude_agent_sdk``,
``anthropic``, or ``guardkitfactory`` — keeping it a pure abstract surface
so the harness boundary is the only seam crossed by both implementations.

See FEAT-HMIG (autobuild-harness-migration) review §2.4 for the C4
Code-level diagram and §3.2-§3.5 for the IN/OUT data-flow contract that
the ``HarnessEvent`` taxonomy below mirrors from the current SDK seam.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncGenerator, AsyncIterator, Literal, Union


@dataclass(frozen=True)
class AssistantMessageEvent:
    """Mirrors an ``AssistantMessage`` from the SDK stream.

    Carries the joined text content of an assistant turn. The ``raw`` slot
    holds the original SDK-side object (typed ``object`` here to keep this
    module SDK-free per AC-006); concrete harnesses populate it when the
    raw form is useful downstream, otherwise leave it ``None``.

    ``reasoning_text`` (TASK-FIX-COACHBUDG01, 2026-06-06) carries the joined
    chain-of-thought / thinking-block content from hybrid reasoning models:
    Anthropic ``ThinkingBlock.thinking`` on the SDK side; llama.cpp's
    ``message.reasoning_content`` field (emitted under ``--reasoning auto``)
    on the LangGraph side. Default ``""`` for backwards compatibility — any
    caller constructing the event without thinking blocks (the legacy
    code path before this field landed, or substrates whose models do not
    emit reasoning) gets the same shape as before. ``coach_output_parser``
    falls through to this field when no fenced ``json`` block is found in
    ``text``; see that module's docstring for the "prefer content"
    precedence rule.
    """

    text: str
    raw: object | None = None
    reasoning_text: str = ""
    type: Literal["assistant_message"] = "assistant_message"


@dataclass(frozen=True)
class ToolUseEvent:
    """Mirrors a ``ToolUseBlock`` content block from an assistant turn.

    Fields mirror what ``agent_invoker.py`` reads off ``ToolUseBlock``
    today: the tool name, the input keys/values dict, and the
    ``tool_use_id`` that pairs this call with its eventual
    ``ToolResultEvent``.
    """

    tool_use_id: str
    name: str
    input: dict[str, object] = field(default_factory=dict)
    type: Literal["tool_use"] = "tool_use"


@dataclass(frozen=True)
class ToolResultEvent:
    """Mirrors a tool-result block paired with a prior ``ToolUseEvent``.

    ``content`` is either a string (most common) or a list of structured
    blocks (image, text, etc.) — kept as ``str | list`` to mirror the SDK
    union without pulling in SDK types.
    """

    tool_use_id: str
    content: str | list[object]
    is_error: bool = False
    type: Literal["tool_result"] = "tool_result"


@dataclass(frozen=True)
class ResultMessageEvent:
    """Mirrors a ``ResultMessage`` — the terminal event of a turn.

    ``session_id`` is the SDK's resumption token; concrete harnesses that
    do not support resume should populate it with ``None``. ``stop_reason``
    and ``usage`` mirror the optional SDK fields used by the orchestrator
    for logging and progress display.

    ``raw`` mirrors the channel on :class:`AssistantMessageEvent`: holds
    the original SDK-side ``ResultMessage`` (or harness-specific terminal
    object) when populated, allowing downstream consumers in
    ``agent_invoker.py`` that duck-type on the raw shape
    (``_emit_llm_call_event`` token extraction, cancelled-error
    session_id rescan) to keep operating without migration. Defaults to
    ``None`` so concrete harnesses that have no useful raw form remain
    compatible with the ABC.
    """

    session_id: str | None
    stop_reason: str | None = None
    usage: dict[str, object] | None = None
    raw: object | None = None
    type: Literal["result_message"] = "result_message"


HarnessEvent = Union[
    AssistantMessageEvent,
    ToolUseEvent,
    ToolResultEvent,
    ResultMessageEvent,
]
"""Discriminated union of every event a ``HarnessAdapter.invoke`` may yield.

Downstream consumers dispatch on ``isinstance(event, ResultMessageEvent)``
(mirroring the existing ``agent_invoker.py`` pattern at lines 2599-2613) or
match on the ``type`` literal. New variants must be added here AND to the
consumer dispatch table in ``agent_invoker.py`` — keep the taxonomy tight.
"""


class HarnessAdapter(ABC):
    """Abstract substrate for autobuild Player/Coach invocations.

    Concrete subclasses translate a prompt + role + tool set + working
    directory into an async stream of :class:`HarnessEvent` values. The
    abstraction lets the orchestrator dispatch through either the legacy
    claude-agent-sdk path or the new LangGraph path based on the
    ``GUARDKIT_HARNESS`` env var (see module docstring).

    Subclasses must implement :meth:`invoke`. The :attr:`session_id` and
    :attr:`supports_resume` properties have concrete defaults so trivial
    subclasses (e.g. test fakes) instantiate cleanly without overriding
    them.
    """

    @abstractmethod
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

        :param prompt: The full prompt text to send to the harness.
        :param role: Agent role tag (e.g. ``"player"``, ``"coach"``,
            ``"specialist"``); concrete harnesses use it for logging and
            for picking role-specific config (model, max_turns, etc.).
        :param tools: List of tool specs the harness should expose to the
            agent. Element type is harness-specific (SDK tool schemas vs.
            LangGraph tool objects) — kept untyped at the interface layer.
        :param cwd: Working directory the harness runs the agent in
            (typically a per-task worktree).
        :param timeout_seconds: Per-invocation timeout. Concrete harnesses
            enforce this however they can (SDK option, asyncio timeout,
            LangGraph checkpoint).

        :raises NotImplementedError: When called on the abstract base
            class. Subclasses MUST override.
        """
        raise NotImplementedError
        # Unreachable yield: makes this an async-generator function so the
        # declared ``AsyncGenerator[HarnessEvent, None]`` return type is
        # honoured at the language level. Required only for static-checker
        # clarity. ``AsyncGenerator`` is the precise type for an async-gen
        # function; ``AsyncIterator`` is the broader protocol it satisfies.
        yield  # type: ignore[unreachable]  # pragma: no cover

    async def invoke_synthesis(
        self,
        prompt: str,
        role: str,
        *,
        grammar: str | None,
        cwd: Path,
        timeout_seconds: int,
    ) -> AsyncGenerator[HarnessEvent, None]:
        """Stream events for a single **toolless** verdict-synthesis turn.

        TASK-ARCH-COACHSPLIT (D-3). A dedicated invocation path for the
        AutoBuild Coach's verdict synthesis. Unlike :meth:`invoke`, this
        call MUST NOT expose any tools to the model — the request carries
        no ``tools`` field at the substrate layer. Two failure modes that
        bite the tool-bound Coach on the llama.cpp + Gemma stack vanish on
        the toolless path:

        1. **Grammar enforcement applies.** llama.cpp bypasses (and on the
           current build *hard-rejects* with HTTP 400 "Cannot use custom
           grammar constraints with tools") a GBNF grammar when the request
           carries ``tools``. A toolless request lets the ``grammar``
           constraint take effect, guaranteeing the verdict schema.
        2. **No tool-call parser to crash.** The run-18 ``HTTP 500 Failed
           to parse input`` class is a non-deterministic artefact of the
           tool-call parser re-reading ``<|tool_call|>`` markers. A toolless
           synthesis turn emits none, so the class cannot fire.

        :param prompt: The full synthesis prompt (self-contained — it
            carries the deterministic evidence, the ACs, the Player report,
            and the verdict-schema instructions).
        :param role: Agent role tag (``"coach"`` for the synthesis call —
            preserves per-role model/budget routing).
        :param grammar: A GBNF grammar string that constrains the output to
            the verdict schema, or ``None`` to run unconstrained. Substrates
            that cannot honour a grammar (e.g. the Anthropic SDK, where the
            model reliably emits the verdict without one) MUST ignore it.
        :param cwd: Working directory (unused by a toolless call, accepted
            for parity with :meth:`invoke`).
        :param timeout_seconds: Per-invocation timeout.

        Default implementation delegates to :meth:`invoke` with an empty
        ``tools`` list and drops ``grammar``. This is correct for the
        Anthropic SDK substrate (the SDK request's tool surface is governed
        by the constructor ``allowed_tools`` — which the synthesis call site
        sets to ``[]`` — and Claude reliably emits the verdict without a
        grammar) and for any trivial test fake that only overrides
        :meth:`invoke`. ``LangGraphHarness`` overrides this to invoke the
        bare model with the grammar so llama.cpp honours it (the whole
        point of the split).
        """
        async for event in self.invoke(
            prompt=prompt,
            role=role,
            tools=[],
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        ):
            yield event

    @property
    def session_id(self) -> str | None:
        """SDK/harness session token for resumption, or ``None`` if absent.

        Default ``None`` so harnesses that do not support resume (or have
        not started a session yet) need not override this. Subclasses that
        do support resume override to return the live token.
        """
        return None

    @property
    def supports_resume(self) -> bool:
        """Whether this harness can resume a prior session via session_id.

        Default ``False``. The legacy ``ClaudeSDKHarness`` (TASK-HMIG-006)
        will override to ``True``; ``LangGraphHarness`` (TASK-HMIG-001B in
        guardkitfactory) overrides per its checkpointer capability.
        """
        return False

    async def cancel(self) -> None:
        """Request termination of any in-flight :meth:`invoke` call.

        TASK-FIX-CTOUT01 contract: when the orchestrator's
        ``cancellation_event`` (TASK-ASF-007) fires during a Coach or
        Player invocation, ``AgentInvoker._cancel_monitor`` calls
        ``await harness.cancel()`` to request immediate termination of
        any in-flight ``invoke(...)`` async iteration. Concrete harnesses
        MUST honour this cancellation within
        ``GUARDKIT_HARNESS_CANCEL_DEADLINE`` seconds (default 30),
        even if a mid-call LLM response is pending.

        The default implementation is a no-op. Concrete subclasses
        override:

        * ``ClaudeSDKHarness.cancel()`` closes the active SDK ``query()``
          async generator; OS-level subprocess escalation is owned
          separately by ``AgentInvoker._kill_child_claude_processes``
          (TASK-FIX-ASPF-004).
        * ``LangGraphHarness.cancel()`` cancels the asyncio Task wrapping
          the in-flight ``agent.ainvoke(...)`` call so LangChain's HTTP
          client receives the cancellation signal.

        The no-op default is intentional: pre-CTOUT01 test fakes that
        subclass :class:`HarnessAdapter` without overriding ``cancel``
        continue to work — they were never wired into the cancellation
        path and the no-op preserves that.

        See ``.claude/rules/harness-cancellation-contract.md`` for the
        full four-layer cancellation taxonomy and the conflict-resolution
        rule between this layer and ``LATE_APPROVAL_GRACE_S``.
        """
        return None


__all__ = [
    "AssistantMessageEvent",
    "ToolUseEvent",
    "ToolResultEvent",
    "ResultMessageEvent",
    "HarnessEvent",
    "HarnessAdapter",
]
