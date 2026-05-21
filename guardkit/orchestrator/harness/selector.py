"""Env-var-driven :class:`HarnessAdapter` selector.

Resolves the active harness implementation from the ``GUARDKIT_HARNESS``
environment variable (default ``"sdk"``). Lives in a dedicated module
per TASK-HMIG-006 OQ-3 so :mod:`guardkit.orchestrator.harness.__init__`
remains a pure re-exports module that does not import :mod:`os`.

Supported values
----------------

``"sdk"`` (default)
    Constructs a fresh :class:`~guardkit.orchestrator.harness.sdk_harness.ClaudeSDKHarness`
    wrapping the claude-agent-sdk path.

``"langgraph"``
    Lazily imports ``guardkitfactory.harness.LangGraphHarness`` and
    constructs it with the supplied kwargs. The import is deferred so
    callers running on the default SDK path do not need guardkitfactory
    installed. If guardkitfactory cannot be imported, an
    :class:`AgentInvocationError` is raised with a portable install
    diagnostic (TASK-HMIG-006 Phase 3a / risk row "Lazy-import ordering").

Any other value raises :class:`AgentInvocationError` naming the invalid
value so the caller does not silently fall through to the SDK default
when a typo is introduced.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness.adapter import HarnessAdapter

logger = logging.getLogger(__name__)


def _translate_kwargs_for_langgraph(harness_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Map orchestrator-side SDK-shaped kwargs onto :class:`LangGraphHarness`'s signature.

    The orchestrator's ``_invoke_with_role`` builds a single SDK-shaped
    kwarg bag and forwards it through :func:`select_harness`. The Wave-2
    :class:`~guardkitfactory.harness.LangGraphHarness` skeleton (TASK-HMIG-001B)
    accepts only ``model`` / ``backend`` / ``permissions``, so a bare
    ``LangGraphHarness(**harness_kwargs)`` raises ``TypeError`` on every
    SDK-only kwarg.

    This translator drops the SDK-only kwargs silently — they have no
    LangGraph analogue in the Wave-2 skeleton:

    * ``sdk_timeout_seconds`` — SDK option; LangGraph's timeout is owned
      by the orchestrator's ``asyncio.timeout`` wrapper.
    * ``allowed_tools`` — SDK ``ClaudeAgentOptions.allowed_tools`` field;
      the LangGraph path receives its tool surface through the
      ``invoke()`` ``tools`` argument and through DeepAgents' built-in
      tool set (filesystem + ``execute`` + planning + sub-agents).
    * ``permission_mode`` — SDK ``"acceptEdits"`` / ``"bypassPermissions"``
      vocabulary; LangGraph permissions are out of scope until
      TASK-HMIG-002R wires the real backend/permissions plumbing.
    * ``max_turns`` — SDK option only; the LangGraph turn loop is owned
      by DeepAgents internally.
    * ``resume_session_id`` — LangGraph does not support session resume
      in the Wave-2 skeleton (``supports_resume`` is ``False``); the
      caller-side AC-007 warning in ``_invoke_with_role`` surfaces this.
    * ``sdk_debug_dir`` — SDK-specific JSONL preservation path; LangGraph
      preservation is a separate concern owned by guardkitfactory.
    * ``cleanup_handler_installer`` — SDK subprocess cleanup hook; the
      LangGraph path has no subprocess to clean up.

    The keeper list:

    * ``model`` — forwarded as-is. Accepts the same shapes as
      :func:`deepagents.create_deep_agent`'s ``model`` parameter (a
      ``BaseChatModel`` instance or a provider-prefixed string).

    Real backend/permissions wiring is TASK-HMIG-002R; until then,
    :class:`LangGraphHarness` falls back to its built-in DeepAgents
    ``StateBackend`` with no permission restrictions.
    """
    # TASK-HMIG-006 review S-2: emit a debug-level trace whenever a
    # truthy resume_session_id is silently dropped. The orchestrator-side
    # AC-007 warning at agent_invoker.py only fires for callers that go
    # through _invoke_with_role; direct callers of select_harness() get
    # no signal otherwise. Debug-level so we do not bury the
    # orchestrator's warning in production noise.
    resume_session_id = harness_kwargs.get("resume_session_id")
    if resume_session_id:
        logger.debug(
            "TASK-HMIG-006 AC-007: resume_session_id=%s... dropped by "
            "_translate_kwargs_for_langgraph (LangGraph Wave-2 skeleton "
            "does not support resume).",
            resume_session_id[:16],
        )
    return {"model": harness_kwargs.get("model")}


def select_harness(
    env_var: str = "GUARDKIT_HARNESS",
    **harness_kwargs,
) -> HarnessAdapter:
    """Construct the harness named by the ``GUARDKIT_HARNESS`` env var.

    Parameters
    ----------
    env_var:
        Name of the environment variable to consult. Defaults to
        ``"GUARDKIT_HARNESS"`` — exposed as a parameter so tests can
        switch isolated env-var names without monkey-patching the
        process environment.
    **harness_kwargs:
        Keyword arguments forwarded to the constructed harness.
        :class:`~guardkit.orchestrator.harness.sdk_harness.ClaudeSDKHarness`
        accepts ``sdk_timeout_seconds`` / ``allowed_tools`` /
        ``permission_mode`` / ``max_turns`` / etc.; see that class for
        the full signature.

    Returns
    -------
    HarnessAdapter
        A freshly constructed harness instance (single-use per
        invocation per TASK-HMIG-006 Design Decision D-6).

    Raises
    ------
    AgentInvocationError
        If the env var names ``"langgraph"`` but guardkitfactory cannot
        be imported, OR if the env var names an unsupported value.
    """
    name = os.environ.get(env_var, "sdk").lower()

    if name == "sdk":
        # Lazy import keeps the package importable when claude_agent_sdk
        # is not installed and the user is on the langgraph path.
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        return ClaudeSDKHarness(**harness_kwargs)

    if name == "langgraph":
        try:
            from guardkitfactory.harness import LangGraphHarness  # type: ignore[import-not-found]
        except ImportError as e:
            raise AgentInvocationError(
                f"GUARDKIT_HARNESS=langgraph but guardkitfactory is not "
                f"importable: {e}. Install with "
                f"`pip install guardkitfactory` "
                f"or `pip install -e ../guardkitfactory` for "
                f"operator-side dev."
            ) from e
        return LangGraphHarness(**_translate_kwargs_for_langgraph(harness_kwargs))

    raise AgentInvocationError(
        f"Unknown GUARDKIT_HARNESS value: {name!r}. "
        f"Expected 'sdk' or 'langgraph'."
    )


__all__ = ["select_harness"]
