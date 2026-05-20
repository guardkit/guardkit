"""Harness adapter package — substrate boundary for autobuild invocations.

See :mod:`guardkit.orchestrator.harness.adapter` for the full cross-repo
contract; this package's public surface is the :class:`HarnessAdapter`
ABC plus the :class:`HarnessEvent` tagged union of stream events.
"""

from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    HarnessAdapter,
    HarnessEvent,
    ResultMessageEvent,
    ToolResultEvent,
    ToolUseEvent,
)

__all__ = [
    "HarnessAdapter",
    "HarnessEvent",
    "AssistantMessageEvent",
    "ToolUseEvent",
    "ToolResultEvent",
    "ResultMessageEvent",
]
