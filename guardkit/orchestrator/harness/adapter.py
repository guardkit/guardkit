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
from typing import AsyncIterator, Literal, Union


@dataclass(frozen=True)
class AssistantMessageEvent:
    """Mirrors an ``AssistantMessage`` from the SDK stream.

    Carries the joined text content of an assistant turn. The ``raw`` slot
    holds the original SDK-side object (typed ``object`` here to keep this
    module SDK-free per AC-006); concrete harnesses populate it when the
    raw form is useful downstream, otherwise leave it ``None``.
    """

    text: str
    raw: object | None = None
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
    """

    session_id: str | None
    stop_reason: str | None = None
    usage: dict[str, object] | None = None
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
    ) -> AsyncIterator[HarnessEvent]:
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
        # declared ``AsyncIterator[HarnessEvent]`` return type is honoured
        # at the language level. Required only for static-checker clarity.
        yield  # type: ignore[unreachable]  # pragma: no cover

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


__all__ = [
    "AssistantMessageEvent",
    "ToolUseEvent",
    "ToolResultEvent",
    "ResultMessageEvent",
    "HarnessEvent",
    "HarnessAdapter",
]
