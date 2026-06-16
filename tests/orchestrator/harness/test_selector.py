"""Unit tests for :func:`select_harness` and the LangGraph kwarg translator.

Tests TASK-HMIG-006 Phase 3c:

* Env-var dispatch (default ``"sdk"``, explicit ``"sdk"`` /
  ``"langgraph"`` / unsupported value).
* Lazy-import semantics for the langgraph branch — the SDK default path
  must not attempt to import guardkitfactory.
* :func:`_translate_kwargs_for_langgraph` correctly drops every SDK-only
  kwarg and forwards ``model``.

Each test uses the ``env_var=`` parameter of :func:`select_harness` to
avoid cross-test contamination from process-wide
``GUARDKIT_HARNESS`` state.

Coverage Target: >=85% line, >=80% branch on
``guardkit.orchestrator.harness.selector``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness import selector as selector_module
from guardkit.orchestrator.harness.selector import (
    _build_backend_with_optional_cap,
    _factory_accepts_kwarg,
    _translate_kwargs_for_langgraph,
    select_harness,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


_TEST_ENV_VAR = "GUARDKIT_HARNESS_TEST_ONLY"


def _sdk_kwargs(**overrides: Any) -> dict[str, Any]:
    """Build the canonical SDK-shaped kwarg bag the orchestrator forwards.

    Mirrors the call site in
    ``agent_invoker._invoke_with_role`` (lines 2489-2501): every kwarg
    the orchestrator passes is included so the translator and the SDK
    branch both see the realistic shape.
    """
    base: dict[str, Any] = {
        "sdk_timeout_seconds": 60,
        "allowed_tools": ["Read", "Write"],
        "permission_mode": "acceptEdits",
        "max_turns": 30,
        "model": "claude-sonnet-4-5",
        "resume_session_id": None,
        "sdk_debug_dir": None,
        "cleanup_handler_installer": lambda: None,
    }
    base.update(overrides)
    return base


# ----------------------------------------------------------------------
# Translator tests
# ----------------------------------------------------------------------


class TestTranslateKwargsForLangGraph:
    """Unit tests for :func:`_translate_kwargs_for_langgraph`."""

    def test_drops_all_sdk_only_kwargs(self) -> None:
        """Every SDK-only kwarg must be filtered out."""
        translated = _translate_kwargs_for_langgraph(_sdk_kwargs())

        assert "sdk_timeout_seconds" not in translated
        assert "allowed_tools" not in translated
        assert "permission_mode" not in translated
        assert "max_turns" not in translated
        assert "resume_session_id" not in translated
        assert "sdk_debug_dir" not in translated
        assert "cleanup_handler_installer" not in translated

    def test_keeps_model_kwarg(self) -> None:
        """``model`` must survive translation."""
        translated = _translate_kwargs_for_langgraph(
            _sdk_kwargs(model="openai:gpt-4o-mini")
        )

        assert translated == {"model": "openai:gpt-4o-mini"}

    def test_bare_alias_auto_prefixed_with_openai(self) -> None:
        """``qwen36-workhorse`` → ``openai:qwen36-workhorse``.

        TASK-FIX-MODELPLUMB: bare aliases without a provider prefix need
        ``openai:`` for DeepAgents' ``init_chat_model`` to route via the
        OpenAI provider (llama-swap speaks the OpenAI API).
        """
        translated = _translate_kwargs_for_langgraph(
            _sdk_kwargs(model="qwen36-workhorse")
        )

        assert translated == {"model": "openai:qwen36-workhorse"}

    def test_model_alias_with_colon_in_name_auto_prefixed(self) -> None:
        """``gemma4:26b`` (colon-in-name) → ``openai:gemma4:26b``.

        TASK-FIX-COACHBUDG01 follow-up (run-7 line 205): the original
        ``":" not in model`` check was too naive — it treated any colon
        as a provider prefix. ``gemma4:26b`` slipped through unchanged
        and ``init_chat_model("gemma4:26b")`` failed with "Unable to
        infer model provider". Fixed by checking the first segment
        against a known-providers set.
        """
        translated = _translate_kwargs_for_langgraph(
            _sdk_kwargs(model="gemma4:26b")
        )

        assert translated == {"model": "openai:gemma4:26b"}

    def test_already_prefixed_model_unchanged(self) -> None:
        """``anthropic:claude-sonnet-4-5`` already carries a known provider
        prefix — translator must NOT prepend ``openai:`` on top.
        """
        translated = _translate_kwargs_for_langgraph(
            _sdk_kwargs(model="anthropic:claude-sonnet-4-5")
        )

        assert translated == {"model": "anthropic:claude-sonnet-4-5"}

    def test_openai_prefixed_colon_in_name_unchanged(self) -> None:
        """``openai:gemma4:26b`` is the canonical post-prefix form — translator
        must not re-prefix or strip the colon-in-name segment.
        """
        translated = _translate_kwargs_for_langgraph(
            _sdk_kwargs(model="openai:gemma4:26b")
        )

        assert translated == {"model": "openai:gemma4:26b"}

    def test_missing_model_yields_none(self) -> None:
        """If the caller omits ``model``, translator returns ``{"model": None}``."""
        translated = _translate_kwargs_for_langgraph({})

        assert translated == {"model": None}

    def test_extra_unknown_kwarg_is_dropped(self) -> None:
        """Future-proof: any unrecognised key falls out at the boundary."""
        translated = _translate_kwargs_for_langgraph(
            _sdk_kwargs(some_future_kwarg="future-value")
        )

        assert "some_future_kwarg" not in translated
        assert set(translated.keys()) == {"model"}

    def test_resume_session_id_is_dropped_even_when_truthy(self) -> None:
        """Explicit non-None ``resume_session_id`` must still be dropped."""
        translated = _translate_kwargs_for_langgraph(
            _sdk_kwargs(resume_session_id="sess-abc123")
        )

        assert "resume_session_id" not in translated

    def test_drops_setting_sources(self) -> None:
        """TASK-HMIG-006.4 AC-002: pre-loop ``setting_sources`` is dropped.

        DeepAgents has no settings-layer analogue, so the kwarg is a no-op
        on the LangGraph path — ``model`` is the only surviving key.
        """
        translated = _translate_kwargs_for_langgraph(
            _sdk_kwargs(setting_sources=["project"])
        )

        assert "setting_sources" not in translated
        assert set(translated.keys()) == {"model"}

    def test_pre_loop_kwarg_bag_reduces_to_model(self) -> None:
        """The full pre-loop kwarg bag (TASK-HMIG-006.4) reduces to ``model``."""
        pre_loop_bag = {
            "sdk_timeout_seconds": 1200,
            "allowed_tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            "permission_mode": "acceptEdits",
            "max_turns": 25,
            "setting_sources": ["project"],
        }

        translated = _translate_kwargs_for_langgraph(pre_loop_bag)

        assert translated == {"model": None}


# ----------------------------------------------------------------------
# Dispatch tests
# ----------------------------------------------------------------------


class TestSelectHarnessDispatch:
    """Env-var-driven dispatch behaviour for :func:`select_harness`."""

    def test_default_returns_langgraph_harness(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        """Default (env-var unset) → LangGraphHarness.

        TASK-HMIG-011 cutover (2026-06-16): the default flipped ``"sdk"`` ->
        ``"langgraph"``. The SDK path is now an opt-in fallback (see
        ``test_explicit_sdk_returns_claude_sdk_harness``).
        """
        monkeypatch.delenv(_TEST_ENV_VAR, raising=False)

        from guardkitfactory.harness import LangGraphHarness

        harness = select_harness(
            env_var=_TEST_ENV_VAR, model=MagicMock(), cwd=tmp_path
        )

        assert isinstance(harness, LangGraphHarness)

    def test_sdk_fallback_does_not_import_guardkitfactory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit SDK fallback must NOT touch guardkitfactory — AC-003 lazy-import.

        TASK-HMIG-011 cutover (2026-06-16): the lazy-import invariant moved
        from the (former ``"sdk"``) default to the explicit ``GUARDKIT_HARNESS=sdk``
        fallback. The default path now intentionally imports guardkitfactory
        (it routes to LangGraph).
        """
        monkeypatch.setenv(_TEST_ENV_VAR, "sdk")

        original = sys.modules.get("guardkitfactory")
        original_harness = sys.modules.get("guardkitfactory.harness")

        # If guardkitfactory.harness is already cached from a previous test we
        # can't observe a fresh import, so we test the next-best invariant:
        # the explicit SDK path returns the SDK harness without consulting the
        # langgraph branch (which would raise without a cwd= kwarg).
        try:
            harness = select_harness(env_var=_TEST_ENV_VAR, **_sdk_kwargs())
            from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

            assert isinstance(harness, ClaudeSDKHarness)
        finally:
            if original is None:
                sys.modules.pop("guardkitfactory", None)
            if original_harness is None:
                sys.modules.pop("guardkitfactory.harness", None)

    def test_explicit_sdk_returns_claude_sdk_harness(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``GUARDKIT_HARNESS=sdk`` → ClaudeSDKHarness."""
        monkeypatch.setenv(_TEST_ENV_VAR, "sdk")

        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        harness = select_harness(env_var=_TEST_ENV_VAR, **_sdk_kwargs())

        assert isinstance(harness, ClaudeSDKHarness)

    def test_explicit_sdk_case_insensitive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``GUARDKIT_HARNESS=SDK`` (uppercase) still routes to SDK."""
        monkeypatch.setenv(_TEST_ENV_VAR, "SDK")

        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        harness = select_harness(env_var=_TEST_ENV_VAR, **_sdk_kwargs())

        assert isinstance(harness, ClaudeSDKHarness)

    def test_langgraph_returns_langgraph_harness(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """``GUARDKIT_HARNESS=langgraph`` → :class:`LangGraphHarness`."""
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        from guardkitfactory.harness import LangGraphHarness

        # Build a minimal stub model so LangGraphHarness construction
        # succeeds. The harness does not invoke .invoke() during
        # selection — it only stores the model attribute — so any
        # non-None object is fine here.
        stub_model = MagicMock()

        # TASK-FIX-002R-CONSUME: langgraph branch requires a worktree
        # cwd to construct the LocalShellBackend.
        harness = select_harness(
            env_var=_TEST_ENV_VAR, model=stub_model, cwd=tmp_path
        )

        assert isinstance(harness, LangGraphHarness)
        assert harness.model is stub_model

    def test_langgraph_forwards_on_model_activity(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """TASK-FIX-SPECINVOKE01: ``on_model_activity`` reaches LangGraphHarness.

        The orchestrator threads ``AgentInvoker._bump_activity`` here so the
        no-model-activity specialist watchdog measures real model progress
        through the harness's await-then-yield event cadence.
        """
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        from guardkitfactory.harness import LangGraphHarness

        sentinel = lambda: None  # noqa: E731 — minimal callable sink

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            model=MagicMock(),
            cwd=tmp_path,
            on_model_activity=sentinel,
        )

        assert isinstance(harness, LangGraphHarness)
        assert harness.on_model_activity is sentinel

    def test_sdk_pops_on_model_activity(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TASK-FIX-SPECINVOKE01: the SDK harness never sees ``on_model_activity``.

        It already streams events incrementally, so the kwarg is LangGraph-only
        and must be popped before ``ClaudeSDKHarness(**harness_kwargs)`` (which
        has no such parameter) — otherwise selection raises ``TypeError``.
        """
        monkeypatch.setenv(_TEST_ENV_VAR, "sdk")

        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            on_model_activity=lambda: None,
            **_sdk_kwargs(),
        )

        assert isinstance(harness, ClaudeSDKHarness)
        assert not hasattr(harness, "on_model_activity")

    def test_langgraph_when_guardkitfactory_unimportable_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ImportError on guardkitfactory.harness → AgentInvocationError with hint."""
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        # Force the import to fail by mapping the module to None in
        # sys.modules (Python interprets this as "explicitly unimportable").
        monkeypatch.setitem(sys.modules, "guardkitfactory.harness", None)

        with pytest.raises(AgentInvocationError) as exc_info:
            select_harness(env_var=_TEST_ENV_VAR, model=MagicMock())

        msg = str(exc_info.value)
        assert "guardkitfactory" in msg
        # Install-hint diagnostic must be surfaced verbatim per OQ-3.
        assert "pip install guardkitfactory" in msg

    def test_unknown_value_raises_naming_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unsupported env-var value names itself in the error message."""
        monkeypatch.setenv(_TEST_ENV_VAR, "totally_invalid_harness")

        with pytest.raises(AgentInvocationError) as exc_info:
            select_harness(env_var=_TEST_ENV_VAR, **_sdk_kwargs())

        msg = str(exc_info.value)
        assert "totally_invalid_harness" in msg
        assert "sdk" in msg
        assert "langgraph" in msg

    def test_langgraph_translates_kwargs_so_no_typeerror(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """SDK-shaped kwarg bag must reach LangGraphHarness without TypeError.

        Regression for the bare ``LangGraphHarness(**harness_kwargs)``
        bug — every SDK-only kwarg would have raised
        ``TypeError: __init__() got an unexpected keyword argument ...``.
        """
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        from guardkitfactory.harness import LangGraphHarness

        # Pass the full orchestrator-side bag (every SDK kwarg present)
        # plus the TASK-FIX-002R-CONSUME ``cwd`` kwarg.
        harness = select_harness(
            env_var=_TEST_ENV_VAR, cwd=tmp_path, **_sdk_kwargs()
        )

        assert isinstance(harness, LangGraphHarness)

    def test_langgraph_accepts_setting_sources_without_typeerror(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """TASK-HMIG-006.4 AC-002: pre-loop ``setting_sources`` must not break langgraph.

        The pre-loop design phase forwards ``setting_sources=["project"]``.
        The translator drops it, so ``LangGraphHarness(**translated)`` must
        not raise ``TypeError`` on the new kwarg.
        """
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        from guardkitfactory.harness import LangGraphHarness

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            cwd=tmp_path,
            **_sdk_kwargs(setting_sources=["project"]),
        )

        assert isinstance(harness, LangGraphHarness)

    # ------------------------------------------------------------------
    # TASK-FIX-002R-CONSUME regression tests
    # ------------------------------------------------------------------

    def test_langgraph_wires_backend_and_permissions(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """AC-005: langgraph branch wires factory-built backend + permissions.

        Confirms the falsifier from TASK-REV-HM09 §7.1 Wave 1: the
        ``LangGraphHarness`` returned by ``select_harness(langgraph,
        cwd=...)`` has non-None ``.backend`` and non-None ``.permissions``,
        both of types from :mod:`guardkitfactory.harness`. Before
        TASK-FIX-002R-CONSUME, both attributes defaulted to ``None``
        because the selector built ``LangGraphHarness(model=...)`` only.
        """
        # guardkitfactory pins requires-python >= 3.11; guardkit may
        # run its unit suite on 3.10. Skip rather than fail when the
        # cross-repo dependency is not importable.
        pytest.importorskip("guardkitfactory.harness")

        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        from guardkitfactory.harness import LangGraphHarness
        from guardkitfactory.harness.backend_config import LocalShellBackend
        from guardkitfactory.harness.permissions import FilesystemPermission
        from deepagents.backends.composite import CompositeBackend

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            model=MagicMock(),
            cwd=tmp_path,
        )

        assert isinstance(harness, LangGraphHarness)
        assert harness.backend is not None
        # TASK-HMIG-002R-SUMM-ROOT wraps the LocalShellBackend in a
        # CompositeBackend (to carry artifacts_root for summarisation
        # re-rooting). TASK-FIX-WTESCAPE01 then interposed a
        # PathConfinedBackend as the composite ``default`` (write/edit
        # confinement to the worktree); the LocalShellBackend sits one
        # level down at ``default._inner`` and every non-write attribute
        # delegates through.
        assert isinstance(harness.backend, CompositeBackend)
        assert isinstance(harness.backend.default._inner, LocalShellBackend)
        assert harness.backend.default.cwd == tmp_path.resolve()
        # The permissions factory is wired (returns a list). Note: under
        # TASK-HMIG-002R-NOPERMS the deny-rule list is intentionally EMPTY
        # (filesystem confinement moved to virtual_mode/operator-trust, see
        # backend_config module docstring), so we no longer assert non-empty
        # — only that the list is wired and every element (if any) is a
        # FilesystemPermission. (Test updated under TASK-PERF-COACHSYNTH.)
        assert harness.permissions is not None
        assert isinstance(harness.permissions, list)
        assert all(
            isinstance(p, FilesystemPermission) for p in harness.permissions
        )

    def test_langgraph_missing_cwd_raises_with_actionable_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-002 boundary: langgraph without ``cwd=`` raises a diagnostic.

        The error message must name the caller (``_invoke_with_role``)
        and the kwarg (``cwd``) so operators can act on it without
        spelunking through the selector. Requires guardkitfactory to be
        importable so the cwd-missing branch is the one that fires (not
        the import-error branch).
        """
        pytest.importorskip("guardkitfactory.harness")

        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        with pytest.raises(AgentInvocationError) as exc_info:
            # No cwd= kwarg.
            select_harness(env_var=_TEST_ENV_VAR, model=MagicMock())

        msg = str(exc_info.value)
        assert "cwd" in msg
        assert "build_autobuild_backend" in msg
        assert "_invoke_with_role" in msg

    def test_sdk_path_ignores_cwd_kwarg(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """AC-003: SDK harness must accept and ignore the ``cwd=`` kwarg.

        ``ClaudeSDKHarness.__init__`` has no ``cwd`` parameter (it takes
        cwd later via :meth:`invoke`). The selector pops the kwarg before
        delegating so callers can pass ``cwd`` unconditionally without a
        ``TypeError``.
        """
        monkeypatch.setenv(_TEST_ENV_VAR, "sdk")

        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        harness = select_harness(
            env_var=_TEST_ENV_VAR, cwd=tmp_path, **_sdk_kwargs()
        )

        assert isinstance(harness, ClaudeSDKHarness)

    # ------------------------------------------------------------------
    # TASK-PERF-COACHSYNTH: gather-bound kwargs (recursion_limit,
    # max_tool_result_chars). LangGraph-only; dropped on the SDK path.
    # ------------------------------------------------------------------

    def test_langgraph_forwards_recursion_limit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        """The gather's recursion ceiling must reach the LangGraphHarness —

        it is the ONLY hard tool-cycle bound on that substrate (max_turns is
        dropped). Without it the gather can balloon past the model window (F20).
        """
        pytest.importorskip("guardkitfactory.harness")
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            model=MagicMock(),
            cwd=tmp_path,
            recursion_limit=7,
        )
        assert harness.recursion_limit == 7

    def test_langgraph_forwards_tool_result_cap(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        """A non-None max_tool_result_chars wraps the backend in a

        TruncatingBackend so single tool results cannot blow the window.
        """
        pytest.importorskip("guardkitfactory.harness")
        from guardkitfactory.harness.backend_config import TruncatingBackend

        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            model=MagicMock(),
            cwd=tmp_path,
            max_tool_result_chars=4096,
        )
        assert isinstance(harness.backend.default, TruncatingBackend)

    def test_langgraph_default_no_bounds(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        """Player/synthesis paths (no gather kwargs) are unchanged: LangGraph

        default recursion (None) and an unwrapped backend.
        """
        pytest.importorskip("guardkitfactory.harness")
        from guardkitfactory.harness.backend_config import TruncatingBackend

        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        harness = select_harness(
            env_var=_TEST_ENV_VAR, model=MagicMock(), cwd=tmp_path
        )
        assert harness.recursion_limit is None
        assert not isinstance(harness.backend.default, TruncatingBackend)

    def test_sdk_path_drops_gather_bounds(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        """The SDK harness has no recursion_limit / tool-result-cap params;

        the selector must pop them so callers can pass them unconditionally
        without a TypeError (the SDK bounds cycles via max_turns instead).
        """
        monkeypatch.setenv(_TEST_ENV_VAR, "sdk")
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            cwd=tmp_path,
            recursion_limit=5,
            max_tool_result_chars=1234,
            **_sdk_kwargs(),
        )
        assert isinstance(harness, ClaudeSDKHarness)

    def test_sdk_path_threads_setting_sources(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TASK-HMIG-006.4: the SDK harness records the forwarded ``setting_sources``."""
        monkeypatch.setenv(_TEST_ENV_VAR, "sdk")

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            **_sdk_kwargs(setting_sources=["project"]),
        )

        # ClaudeSDKHarness stores the value for use in invoke()'s
        # ClaudeAgentOptions construction.
        assert harness._setting_sources == ["project"]


# ----------------------------------------------------------------------
# TASK-FIX-BACKENDKWARG: selector <-> guardkitfactory signature compat
# ----------------------------------------------------------------------
#
# These tests exercise Shape 2 — the selector's defensive introspection of
# ``build_autobuild_backend``'s signature before forwarding
# ``max_tool_result_chars``. They inject a *fake* ``guardkitfactory.harness``
# into ``sys.modules`` so the selector's lazy ``from guardkitfactory.harness
# import (...)`` resolves to controllable stubs. This means the tests run
# WITHOUT the real guardkitfactory installed (it is not a guardkit unit-suite
# dependency) and let us pin both signature shapes: the stale "old" factory
# that crashed run-24 and the current "new" factory that honours the cap.


def _install_fake_guardkitfactory(
    monkeypatch: pytest.MonkeyPatch,
    build_autobuild_backend: Any,
) -> dict[str, Any]:
    """Inject a stub ``guardkitfactory.harness`` module into ``sys.modules``.

    ``build_autobuild_backend`` is the caller-supplied stub whose *signature*
    is under test (old vs new). Returns a dict that captures the constructed
    stub harness under key ``"harness"`` for assertions.
    """
    captured: dict[str, Any] = {}

    class _StubLangGraphHarness:
        def __init__(
            self,
            *,
            model: Any,
            backend: Any,
            permissions: Any,
            recursion_limit: Any = None,
        ) -> None:
            self.model = model
            self.backend = backend
            self.permissions = permissions
            self.recursion_limit = recursion_limit
            captured["harness"] = self

    def _build_autobuild_permissions() -> list[Any]:
        return []

    fake = ModuleType("guardkitfactory.harness")
    fake.LangGraphHarness = _StubLangGraphHarness  # type: ignore[attr-defined]
    fake.build_autobuild_backend = build_autobuild_backend  # type: ignore[attr-defined]
    fake.build_autobuild_permissions = (  # type: ignore[attr-defined]
        _build_autobuild_permissions
    )

    # Seed the parent package defensively so the import machinery never tries
    # to locate the real (uninstalled) distribution. The leaf lookup
    # short-circuits on the cached child, but a present parent is harmless.
    if "guardkitfactory" not in sys.modules:
        monkeypatch.setitem(
            sys.modules, "guardkitfactory", ModuleType("guardkitfactory")
        )
    monkeypatch.setitem(sys.modules, "guardkitfactory.harness", fake)
    return captured


def _old_factory_no_cap(worktree: Any) -> Any:
    """Stale ``build_autobuild_backend`` — the pre-COACHSYNTH signature that
    crashed run-24 (no ``max_tool_result_chars`` parameter)."""
    return MagicMock(name="composite-backend", _worktree=worktree)


class TestFactoryAcceptsKwarg:
    """Unit tests for the :func:`_factory_accepts_kwarg` signature probe."""

    def test_named_keyword_param_is_accepted(self) -> None:
        def factory(worktree: Any, *, max_tool_result_chars: int | None = None) -> None:
            ...

        assert _factory_accepts_kwarg(factory, "max_tool_result_chars") is True

    def test_missing_param_is_rejected(self) -> None:
        def factory(worktree: Any) -> None:
            ...

        assert _factory_accepts_kwarg(factory, "max_tool_result_chars") is False

    def test_var_keyword_catch_all_is_accepted(self) -> None:
        def factory(worktree: Any, **kwargs: Any) -> None:
            ...

        assert _factory_accepts_kwarg(factory, "max_tool_result_chars") is True

    def test_uninspectable_factory_is_conservatively_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ``inspect.signature`` raises (C builtins, degenerate stubs),
        the probe reports ``False`` so the caller drops the kwarg rather than
        risk a ``TypeError`` — the crash-avoiding choice."""

        def _boom(_factory: Any) -> None:
            raise ValueError("no signature available")

        monkeypatch.setattr(selector_module.inspect, "signature", _boom)

        assert (
            _factory_accepts_kwarg(lambda w: None, "max_tool_result_chars")
            is False
        )


class TestBuildBackendWithOptionalCap:
    """Direct unit tests for :func:`_build_backend_with_optional_cap`."""

    def test_supported_factory_receives_cap(self) -> None:
        received: dict[str, Any] = {}

        def new_factory(
            worktree: Any, *, max_tool_result_chars: int | None = None
        ) -> str:
            received["worktree"] = worktree
            received["cap"] = max_tool_result_chars
            return "backend"

        result = _build_backend_with_optional_cap(
            new_factory, Path("/tmp/wt"), 4096
        )

        assert result == "backend"
        assert received["cap"] == 4096
        assert received["worktree"] == Path("/tmp/wt")

    def test_stale_factory_drops_cap_and_warns(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.WARNING, logger="guardkit.orchestrator.harness.selector"
        ):
            result = _build_backend_with_optional_cap(
                _old_factory_no_cap, Path("/tmp/wt"), 4096
            )

        assert result is not None  # no TypeError
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        msg = warnings[0].getMessage()
        assert "max_tool_result_chars" in msg
        assert "BACKENDKWARG" in msg
        assert "4096" in msg

    def test_stale_factory_none_cap_is_silent(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A ``None`` cap disables nothing, so dropping it must NOT warn."""
        with caplog.at_level(
            logging.WARNING, logger="guardkit.orchestrator.harness.selector"
        ):
            result = _build_backend_with_optional_cap(
                _old_factory_no_cap, Path("/tmp/wt"), None
            )

        assert result is not None
        assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


class TestSelectHarnessBackendKwargCompat:
    """End-to-end :func:`select_harness` Shape-2 behaviour (AC-2..AC-5)."""

    def test_stale_factory_drops_cap_with_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """AC-2: a stale guardkitfactory (no ``max_tool_result_chars`` param)
        must construct the harness WITHOUT crashing, dropping the kwarg and
        emitting a loud WARNING (not silently)."""
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        received: dict[str, Any] = {}

        def old_factory(worktree: Any) -> Any:
            received["worktree"] = worktree
            return MagicMock(name="composite-backend")

        _install_fake_guardkitfactory(monkeypatch, old_factory)

        with caplog.at_level(
            logging.WARNING, logger="guardkit.orchestrator.harness.selector"
        ):
            harness = select_harness(
                env_var=_TEST_ENV_VAR,
                model=MagicMock(),
                cwd=tmp_path,
                max_tool_result_chars=4096,
            )

        assert harness is not None
        # Factory was called WITHOUT the unsupported kwarg.
        assert received["worktree"] == Path(tmp_path)
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("max_tool_result_chars" in r.getMessage() for r in warnings)
        assert any("BACKENDKWARG" in r.getMessage() for r in warnings)

    def test_run24_reproducer_no_typeerror(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        """AC-3 (run-24 regression reproducer).

        Pre-fix, ``select_harness`` called
        ``build_autobuild_backend(Path(cwd), max_tool_result_chars=...)``
        unconditionally. Against a stale factory that signature raises
        ``TypeError: ... unexpected keyword argument 'max_tool_result_chars'``
        — the crash that killed every SDK invocation 25s into run-24. Shape 2
        must make this construction succeed.
        """
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")
        _install_fake_guardkitfactory(monkeypatch, _old_factory_no_cap)

        # Sanity: the stale factory genuinely rejects the kwarg, proving this
        # test exercises the real incompatibility (the exact call shape the
        # pre-Shape-2 selector made unconditionally → the run-24 TypeError).
        with pytest.raises(TypeError):
            _old_factory_no_cap(tmp_path, max_tool_result_chars=4096)  # type: ignore[call-arg]

        # Yet select_harness must now construct the harness without raising.
        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            model=MagicMock(),
            cwd=tmp_path,
            max_tool_result_chars=4096,
        )
        assert harness is not None

    def test_current_factory_receives_cap_and_no_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """AC-4 / AC-5: a current guardkitfactory whose signature accepts the
        cap must RECEIVE ``max_tool_result_chars`` (the COACHSYNTH Lever-2
        truncation stays active, not silently disabled) and emit NO warning.
        """
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        received: dict[str, Any] = {}

        def new_factory(
            worktree: Any, *, max_tool_result_chars: int | None = None
        ) -> Any:
            received["worktree"] = worktree
            received["cap"] = max_tool_result_chars
            return MagicMock(name="composite-backend")

        _install_fake_guardkitfactory(monkeypatch, new_factory)

        with caplog.at_level(
            logging.WARNING, logger="guardkit.orchestrator.harness.selector"
        ):
            harness = select_harness(
                env_var=_TEST_ENV_VAR,
                model=MagicMock(),
                cwd=tmp_path,
                max_tool_result_chars=4096,
            )

        assert harness is not None
        assert received["cap"] == 4096  # forwarded → truncation active
        assert [
            r for r in caplog.records if r.levelno == logging.WARNING
        ] == []

    def test_current_factory_none_cap_forwarded_without_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Player/synthesis default (``None`` cap) on a current factory: the
        ``None`` is forwarded explicitly and nothing is warned about."""
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        received: dict[str, Any] = {}

        def new_factory(
            worktree: Any, *, max_tool_result_chars: int | None = None
        ) -> Any:
            received["cap"] = max_tool_result_chars
            return MagicMock(name="composite-backend")

        _install_fake_guardkitfactory(monkeypatch, new_factory)

        with caplog.at_level(
            logging.WARNING, logger="guardkit.orchestrator.harness.selector"
        ):
            harness = select_harness(
                env_var=_TEST_ENV_VAR,
                model=MagicMock(),
                cwd=tmp_path,
            )

        assert harness is not None
        assert received["cap"] is None
        assert [
            r for r in caplog.records if r.levelno == logging.WARNING
        ] == []
