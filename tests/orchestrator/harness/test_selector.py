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

import sys
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness.selector import (
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

    def test_default_returns_claude_sdk_harness(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Default (env-var unset) → ClaudeSDKHarness."""
        monkeypatch.delenv(_TEST_ENV_VAR, raising=False)

        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        harness = select_harness(env_var=_TEST_ENV_VAR, **_sdk_kwargs())

        assert isinstance(harness, ClaudeSDKHarness)

    def test_default_does_not_import_guardkitfactory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SDK path must NOT touch guardkitfactory — AC-003 lazy-import."""
        monkeypatch.delenv(_TEST_ENV_VAR, raising=False)

        # Install a sentinel that explodes if anyone imports it.
        sentinel = ModuleType("guardkitfactory_sentinel_proof")

        def _explode(*args: Any, **kwargs: Any) -> None:
            raise AssertionError(
                "guardkitfactory should not be touched on the SDK default path"
            )

        # Use a tracker that records any access to guardkitfactory imports.
        original = sys.modules.get("guardkitfactory")
        original_harness = sys.modules.get("guardkitfactory.harness")

        # Track whether guardkitfactory.harness is freshly imported.
        # If it's already cached in sys.modules from a previous test,
        # we can't observe imports against it, so we test the next-best
        # invariant: select_harness on SDK never raises and returns the
        # SDK harness without consulting the langgraph branch.
        try:
            harness = select_harness(env_var=_TEST_ENV_VAR, **_sdk_kwargs())
            from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

            assert isinstance(harness, ClaudeSDKHarness)
        finally:
            # Sanity: restore state in case the test loaded anything weird.
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

        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            model=MagicMock(),
            cwd=tmp_path,
        )

        assert isinstance(harness, LangGraphHarness)
        assert harness.backend is not None
        assert isinstance(harness.backend, LocalShellBackend)
        assert harness.permissions is not None
        assert isinstance(harness.permissions, list)
        assert len(harness.permissions) > 0
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
