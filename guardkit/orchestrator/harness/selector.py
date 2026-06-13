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

import inspect
import logging
import os
from pathlib import Path
from typing import Any, Callable

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
      tool set (filesystem + ``execute`` + planning + sub-agents). The
      pre-loop design phase (TASK-HMIG-006.4) forwards the full
      ``["Read", "Write", "Edit", "Bash", "Grep", "Glob"]`` set; it is
      dropped here and DeepAgents' built-in surface is used instead.
    * ``permission_mode`` — SDK ``"acceptEdits"`` / ``"bypassPermissions"``
      vocabulary; LangGraph permissions are out of scope until
      TASK-HMIG-002R wires the real backend/permissions plumbing. The
      pre-loop design phase forwards ``"acceptEdits"``; dropped here.
    * ``max_turns`` — SDK option only; the LangGraph turn loop is owned
      by DeepAgents internally. The pre-loop design phase forwards
      ``max_turns=25``; dropped here.
    * ``setting_sources`` — SDK ``ClaudeAgentOptions.setting_sources``
      field controlling which settings layers load (TASK-HMIG-006.4).
      There is no direct DeepAgents analogue, so it is a **no-op** on the
      LangGraph path: the LangGraph harness always loads the default
      DeepAgents context (option (a) of the TASK-HMIG-006.4 design note).
      Project-sources context-injection into ``LangGraphHarness.invoke()``
      is deferred to a separate task if it proves necessary. A truthy
      value emits a debug-level trace mirroring ``resume_session_id``.
    * ``resume_session_id`` — LangGraph does not support session resume
      in the Wave-2 skeleton (``supports_resume`` is ``False``); the
      caller-side AC-007 warning in ``_invoke_with_role`` surfaces this.
    * ``sdk_debug_dir`` — SDK-specific JSONL preservation path; LangGraph
      preservation is a separate concern owned by guardkitfactory.
    * ``cleanup_handler_installer`` — SDK subprocess cleanup hook; the
      LangGraph path has no subprocess to clean up.
    * ``cwd`` — TASK-FIX-002R-CONSUME: worktree path consumed by
      :func:`select_harness` itself to build the LocalShellBackend via
      :func:`guardkitfactory.harness.build_autobuild_backend`. It is not
      a ``LangGraphHarness.__init__`` parameter, so the translator drops
      it.

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

    # TASK-HMIG-006.4 AC-002: the pre-loop design phase forwards
    # setting_sources=["project"]. DeepAgents has no settings-layer
    # analogue, so the kwarg is a documented no-op on the LangGraph path
    # (the LangGraph harness always loads the default DeepAgents context).
    # Emit a debug trace when a value is present so direct select_harness()
    # callers get a signal the setting will not be honoured.
    setting_sources = harness_kwargs.get("setting_sources")
    if setting_sources:
        logger.debug(
            "TASK-HMIG-006.4 AC-002: setting_sources=%s dropped by "
            "_translate_kwargs_for_langgraph (no DeepAgents analogue; "
            "LangGraph path loads default DeepAgents context).",
            setting_sources,
        )

    # TASK-FIX-MODELPLUMB: auto-prefix `openai:` when the caller passes a
    # bare alias (e.g. `qwen36-workhorse`) without a provider prefix.
    # DeepAgents' `init_chat_model` requires a provider-prefixed string
    # when no explicit BaseChatModel instance is supplied. The SDK harness
    # path accepts bare aliases because routing is via ANTHROPIC_BASE_URL,
    # so the CLI --model flag is historically bare. Preserving that CLI
    # shape while making LangGraph happy means the translator owns the
    # prefix. If the caller already supplied a prefix (`openai:...`,
    # `anthropic:...`) or a BaseChatModel instance (non-string), pass
    # through unchanged.
    #
    # TASK-FIX-COACHBUDG01 follow-up (2026-06-06): the original check
    # ``":" not in model`` is too naive. Some model aliases contain ``:``
    # in the name itself — notably ``gemma4:26b``, the COACHBUDG01 Coach
    # candidate. ``gemma4:26b`` would slip through as already-prefixed and
    # reach ``init_chat_model("gemma4:26b")``, which fails with "Unable to
    # infer model provider for model='gemma4:26b'" (see
    # ``autobuild-FEAT-AOF-run-7.md`` line 205). Robust check: identify
    # the first segment via partition; treat as already-prefixed only when
    # the first segment matches a recognised LangChain provider.
    model = harness_kwargs.get("model")
    if isinstance(model, str):
        first_segment, separator, _rest = model.partition(":")
        already_prefixed = bool(separator) and first_segment in _KNOWN_PROVIDER_PREFIXES
        if not already_prefixed:
            prefixed = f"openai:{model}"
            logger.debug(
                "TASK-FIX-MODELPLUMB: auto-prefixed model alias %r -> %r for "
                "LangGraph (DeepAgents init_chat_model requires a provider "
                "prefix; bare name OR first segment %r not in known providers).",
                model,
                prefixed,
                first_segment,
            )
            model = prefixed

    return {"model": model}


# LangChain init_chat_model providers we recognise as "already prefixed".
# Anything else gets auto-prefixed with ``openai:`` for llama-swap routing.
# Conservative list — additions safe, removals require a falsifier test.
_KNOWN_PROVIDER_PREFIXES: frozenset[str] = frozenset({
    "openai",
    "anthropic",
    "azure_openai",
    "google_vertexai",
    "google_genai",
    "bedrock",
    "anthropic_bedrock",
    "cohere",
    "fireworks",
    "together",
    "ollama",
    "deepseek",
    "groq",
    "mistralai",
    "nvidia",
    "xai",
    "perplexity",
    "huggingface",
})


def _factory_accepts_kwarg(factory: Callable[..., Any], name: str) -> bool:
    """Return ``True`` iff ``factory`` can accept the keyword ``name``.

    Introspects ``factory``'s signature: the keyword is accepted when it
    appears as a named parameter OR the signature carries a ``**kwargs``
    catch-all (:class:`inspect.Parameter.VAR_KEYWORD`). When the callable
    cannot be introspected (a C builtin, a degenerate stub), we report
    ``False`` so the caller drops the kwarg rather than risking a
    ``TypeError`` — the conservative, crash-avoiding choice.

    TASK-FIX-BACKENDKWARG Shape 2: this is the compatibility probe the
    LangGraph branch uses before forwarding ``max_tool_result_chars`` to
    the separately-versioned ``guardkitfactory.build_autobuild_backend``.
    """
    try:
        sig = inspect.signature(factory)
    except (TypeError, ValueError):
        return False
    params = sig.parameters
    if name in params:
        return True
    return any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
    )


def _build_backend_with_optional_cap(
    factory: Callable[..., Any],
    worktree: Path,
    max_tool_result_chars: int | None,
) -> Any:
    """Call ``build_autobuild_backend``, forwarding the gather cap defensively.

    TASK-FIX-BACKENDKWARG. The guardkit selector and the installed
    ``guardkitfactory`` are versioned independently (separate packages,
    separate pins). When the selector forwards ``max_tool_result_chars=``
    (added by TASK-PERF-COACHSYNTH) to a *stale* ``guardkitfactory`` whose
    ``build_autobuild_backend`` predates that parameter, the unconditional
    call raised ``TypeError: build_autobuild_backend() got an unexpected
    keyword argument 'max_tool_result_chars'`` — the run-24 crash that
    killed every SDK invocation 25s into the run.

    Shape 2 introspects the installed factory's signature and only forwards
    the kwarg when it is accepted. Crucially, dropping the kwarg is **not
    silent**: when a *real* (non-``None``) cap is requested but the factory
    cannot honour it, we emit a loud ``WARNING`` so the version skew — and
    the consequent silent disabling of the COACHSYNTH gather bound — is
    observable. Letting the truncation silently not-happen is exactly the
    absence-of-failure / silent-degradation trap the project has a rule
    family about (see ``.claude/rules/absence-of-failure-is-not-success.md``).

    A ``None`` cap is the unbounded default, so dropping it disables nothing
    and is *not* warned about (it would be pure noise on the Player and
    synthesis paths, which always pass ``None``).
    """
    if _factory_accepts_kwarg(factory, "max_tool_result_chars"):
        return factory(worktree, max_tool_result_chars=max_tool_result_chars)

    if max_tool_result_chars is not None:
        logger.warning(
            "TASK-FIX-BACKENDKWARG: the installed guardkitfactory's "
            "build_autobuild_backend() does not accept "
            "'max_tool_result_chars'. The requested gather tool-result cap "
            "(%d chars) is being DROPPED and per-tool-result truncation is "
            "DISABLED for this run. This is a guardkit<->guardkitfactory "
            "version skew — upgrade guardkitfactory to a build that includes "
            "TASK-PERF-COACHSYNTH to restore the Coach B-full gather bound. "
            "Proceeding unbounded to avoid the run-24 construction crash.",
            max_tool_result_chars,
        )

    return factory(worktree)


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
        the full signature. The ``cwd`` kwarg is special-cased
        (TASK-FIX-002R-CONSUME): the selector pops it before delegating
        so it does not reach ``ClaudeSDKHarness.__init__`` (which has no
        such parameter); the langgraph branch threads it into
        :func:`guardkitfactory.harness.build_autobuild_backend` so the
        :class:`LangGraphHarness` is constructed with a path-confined
        ``LocalShellBackend``. Required when ``name == "langgraph"``.

    Returns
    -------
    HarnessAdapter
        A freshly constructed harness instance (single-use per
        invocation per TASK-HMIG-006 Design Decision D-6).

    Raises
    ------
    AgentInvocationError
        If the env var names ``"langgraph"`` but guardkitfactory cannot
        be imported, OR if the langgraph branch is selected without a
        ``cwd=`` kwarg, OR if the env var names an unsupported value.
    """
    name = os.environ.get(env_var, "sdk").lower()

    # TASK-FIX-002R-CONSUME: ``cwd`` is consumed by the langgraph branch
    # below to build the LocalShellBackend; ``ClaudeSDKHarness.__init__``
    # has no such parameter (it receives cwd later via
    # :meth:`invoke`). Pop it here so both branches see a stable kwarg
    # bag and callers can pass cwd unconditionally.
    cwd = harness_kwargs.pop("cwd", None)

    # TASK-PERF-COACHSYNTH: gather-bound kwargs. Popped here (like ``cwd``)
    # so neither concrete harness constructor sees them unexpectedly. They
    # are LangGraph-only knobs:
    #   * ``recursion_limit`` — forwarded to ``LangGraphHarness`` to cap the
    #     DeepAgents super-step count (the F20 substrate drops ``max_turns``,
    #     so this is the only hard tool-cycle bound there).
    #   * ``max_tool_result_chars`` — forwarded to ``build_autobuild_backend``
    #     so each gather tool result is truncated before it re-enters context.
    # Both default to ``None`` (unbounded / LangGraph-default) so the Player
    # and synthesis paths are unchanged. On the SDK path they are dropped:
    # the SDK bounds tool cycles via ``max_turns`` (already forwarded) and has
    # no per-tool-result truncation hook.
    recursion_limit = harness_kwargs.pop("recursion_limit", None)
    max_tool_result_chars = harness_kwargs.pop("max_tool_result_chars", None)

    # TASK-FIX-SPECINVOKE01: optional model-activity sink. LangGraph-only —
    # the harness wires it into a LangChain callback so the no-model-activity
    # watchdog (specialist_invocations._run_specialist_with_watchdog) measures
    # real LLM/tool progress rather than this harness's await-then-yield event
    # cadence (which froze the activity clock and false-killed live, model-
    # active specialists at 150 s — FEAT-9DDE run 3). Popped here (like ``cwd``
    # / ``recursion_limit``) so the SDK harness — which already streams events
    # incrementally and needs no callback — never sees it.
    on_model_activity = harness_kwargs.pop("on_model_activity", None)

    if name == "sdk":
        # Lazy import keeps the package importable when claude_agent_sdk
        # is not installed and the user is on the langgraph path.
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        return ClaudeSDKHarness(**harness_kwargs)

    if name == "langgraph":
        # TASK-FIX-002R-CONSUME: import the backend + permissions factories
        # from guardkitfactory.harness alongside LangGraphHarness. They are
        # the consumer-side counterpart to TASK-HMIG-002R (which built the
        # factories in guardkitfactory on 2026-05-20). Without this wiring
        # LangGraphHarness's backend/permissions defaulted to ``None`` and
        # AC-001D could not exercise the falsifier in TASK-REV-HM09 §7.1.
        try:
            from guardkitfactory.harness import (  # type: ignore[import-not-found]
                LangGraphHarness,
                build_autobuild_backend,
                build_autobuild_permissions,
            )
        except ImportError as e:
            raise AgentInvocationError(
                f"GUARDKIT_HARNESS=langgraph but guardkitfactory is not "
                f"importable: {e}. Install with "
                f"`pip install guardkitfactory` "
                f"or `pip install -e ../guardkitfactory` for "
                f"operator-side dev."
            ) from e

        if cwd is None:
            raise AgentInvocationError(
                "select_harness(langgraph) requires a `cwd=` kwarg "
                "naming the worktree path so "
                "guardkitfactory.harness.build_autobuild_backend(cwd) "
                "can build a path-confined LocalShellBackend. Update "
                "the caller (typically "
                "guardkit.orchestrator.agent_invoker._invoke_with_role) "
                "to pass cwd=self.worktree_path."
            )

        translated = _translate_kwargs_for_langgraph(harness_kwargs)
        # TASK-FIX-BACKENDKWARG Shape 2: forward ``max_tool_result_chars``
        # only when the installed guardkitfactory's signature accepts it;
        # drop-with-WARNING on a stale factory instead of crashing (run-24).
        backend = _build_backend_with_optional_cap(
            build_autobuild_backend, Path(cwd), max_tool_result_chars
        )
        # TASK-FIX-SPECINVOKE01: forward ``on_model_activity`` only when the
        # installed guardkitfactory's signature accepts it; drop-with-WARNING
        # on a stale factory instead of crashing (mirrors the
        # ``max_tool_result_chars`` Shape-2 forward at ``_build_backend_with_
        # optional_cap``). The cross-repo seam test
        # ``tests/orchestrator/harness/test_xrepo_contract_seam.py`` fails loud
        # if a real installed factory ever drops the parameter.
        langgraph_kwargs: dict = {
            "model": translated["model"],
            "backend": backend,
            "permissions": build_autobuild_permissions(),
            "recursion_limit": recursion_limit,
        }
        if on_model_activity is not None:
            if "on_model_activity" in inspect.signature(
                LangGraphHarness.__init__
            ).parameters:
                langgraph_kwargs["on_model_activity"] = on_model_activity
            else:
                logger.warning(
                    "select_harness(langgraph): installed guardkitfactory "
                    "LangGraphHarness does not accept on_model_activity; the "
                    "no-model-activity specialist watchdog will fall back to "
                    "the (substrate-blind) event-arrival clock. Upgrade "
                    "guardkitfactory to restore TASK-FIX-SPECINVOKE01."
                )
        return LangGraphHarness(**langgraph_kwargs)

    raise AgentInvocationError(
        f"Unknown GUARDKIT_HARNESS value: {name!r}. "
        f"Expected 'sdk' or 'langgraph'."
    )


__all__ = ["select_harness"]
