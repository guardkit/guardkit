"""Harness adapter package — substrate boundary for autobuild invocations.

See :mod:`guardkit.orchestrator.harness.adapter` for the full cross-repo
contract; this package's public surface is the :class:`HarnessAdapter`
ABC plus the :class:`HarnessEvent` tagged union of stream events, the
concrete :class:`ClaudeSDKHarness` implementation (TASK-HMIG-006), and
the env-var-driven :func:`select_harness` factory (TASK-HMIG-006 OQ-3).

.. important::

   The eager re-export of :class:`ClaudeSDKHarness` below is **only**
   safe because :mod:`guardkit.orchestrator.harness.sdk_harness` defers
   the ``claude_agent_sdk`` import into the body of
   :meth:`ClaudeSDKHarness.invoke`. AC-003 of TASK-HMIG-006 requires
   ``GUARDKIT_HARNESS=langgraph`` callers to be able to construct the
   harness substrate without ``claude-agent-sdk`` installed — and AC-008
   relies on test fixtures that mock ``claude_agent_sdk`` as a
   non-package ``MagicMock``. Both contracts break if a future change
   lifts the SDK import to module scope inside ``sdk_harness.py``. Do
   not move the SDK import out of :meth:`invoke` without a follow-up
   task that also restructures this re-export.
"""

from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    HarnessAdapter,
    HarnessEvent,
    ResultMessageEvent,
    ToolResultEvent,
    ToolUseEvent,
)
from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness
from guardkit.orchestrator.harness.selector import select_harness

__all__ = [
    "HarnessAdapter",
    "HarnessEvent",
    "AssistantMessageEvent",
    "ToolUseEvent",
    "ToolResultEvent",
    "ResultMessageEvent",
    "ClaudeSDKHarness",
    "select_harness",
]
