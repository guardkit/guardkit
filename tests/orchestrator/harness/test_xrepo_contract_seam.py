"""Cross-repo contract smoke-test for the guardkit↔guardkitfactory harness seam.

TASK-INFRA-XREPOCONTRACT (parent TASK-HMIG-010). This module is the **CI
enforcement** for the migrated-contract-boundary meta-rule documented in
``.claude/rules/harness-cancellation-contract.md`` and
``.claude/rules/namespace-hygiene.md``: *every contract boundary that was
migrated across the guardkit↔guardkitfactory repo split needs ALL of its
invocation sites audited plus a CI guard* (run-23 retro recommendation #5).

Why this test exists
--------------------

Cross-repo contract drift between guardkit (the orchestrator) and
guardkitfactory (the LangGraph harness/backend) repeatedly cost a **full
autobuild run to discover**, because the unit tests **mock guardkitfactory**
and never exercise the real call signatures. The recurrences this test
guards against:

* **Run-24** (TASK-FIX-BACKENDKWARG): ``selector.py`` forwarded
  ``max_tool_result_chars`` to ``build_autobuild_backend()``, which did not
  accept it → ``TypeError`` on every SDK invocation, a 25-second crash.
* **The F1/F9/F10/F12/F19 model-threading family** (HMIG): ``model=`` not
  threaded at every call site of the migrated harness boundary.
* **TASK-FIX-CTOUT01** cancel-asymmetry: a new substrate's ``cancel()`` not
  honoured, so the orchestrator's task-level timer could not abort an
  in-flight LangGraph ``agent.ainvoke``.

Unlike the mocked unit tests, this module constructs the **real**
``LangGraphHarness`` + backend through the production ``select_harness``
path and asserts the substrate contract against the **installed**
guardkitfactory. A signature mismatch or a missing substrate method fails
**here, in seconds, in CI** — not after a 25-second runtime crash on a live
autobuild run.

Scope and execution
-------------------

* Marked ``@pytest.mark.seam`` (technology-boundary integration). The CI job
  ``.github/workflows/seam-tests.yml`` checks out the sibling guardkitfactory
  repo, installs both packages, and runs ``pytest -m seam`` as a
  merge-gating job.
* ``pytest.importorskip("guardkitfactory.harness")`` at module load makes the
  whole module **skip cleanly** in a local dev venv that has not installed the
  ``[autobuild]`` extra (no langchain / guardkitfactory stack). This is the
  AC-4 "skippable locally" contract — the seam test is opt-in for the CI job
  that has the real cross-repo stack, never a hard failure for a contributor
  working on an unrelated part of guardkit.
* Fast and dependency-light: construction + ``inspect.signature`` assertions
  only. No live LLM endpoint, no GB10, no ``agent.ainvoke`` call. Target
  runtime <~10s (AC-4).

Related design rules
--------------------

* ``.claude/rules/harness-cancellation-contract.md`` — the four-layer
  cancellation taxonomy; this module codifies its grep signature
  (``rg "async def cancel"``) as the ``cancel``-override assertion in
  :func:`test_substrate_contract_cancel_is_overridden`.
* ``.claude/rules/namespace-hygiene.md`` — the broader "local decision
  touching an externally-defined contract must be audited against that
  contract" meta-rule. The harness boundary is exactly such a contract.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

# AC-4: skip the entire module unless the real cross-repo stack is installed.
# ``guardkitfactory.harness`` pulls in langchain via ``langgraph_harness`` —
# a single importorskip covers both the guardkitfactory package and its
# langchain dependency chain. In a bare guardkit dev venv this skips; in the
# seam-tests CI job (sibling repo checked out + installed) it runs.
guardkitfactory_harness = pytest.importorskip(
    "guardkitfactory.harness",
    reason=(
        "guardkitfactory + langchain stack not installed; this seam test runs "
        "in the seam-tests CI job (pip install -e ../guardkitfactory). Install "
        "the autobuild extra locally to run it: pip install -e ../guardkitfactory"
    ),
)

from guardkit.orchestrator.harness.adapter import (  # noqa: E402
    AssistantMessageEvent,
    HarnessAdapter,
    ResultMessageEvent,
    ToolResultEvent,
    ToolUseEvent,
)
from guardkit.orchestrator.harness.selector import select_harness  # noqa: E402
from guardkit.orchestrator.harness.sdk_harness import (  # noqa: E402
    ClaudeSDKHarness,
)

# The known production substrates. Importing them registers them as
# ``HarnessAdapter`` subclasses so :func:`_concrete_substrates` can also catch
# any *new* substrate added to either repo (future-proofing AC-2).
LangGraphHarness = guardkitfactory_harness.LangGraphHarness
build_autobuild_backend = guardkitfactory_harness.build_autobuild_backend
build_autobuild_permissions = guardkitfactory_harness.build_autobuild_permissions

pytestmark = [pytest.mark.seam, pytest.mark.integration]

# Isolated env-var name so we never perturb the process-wide
# ``GUARDKIT_HARNESS`` (mirrors tests/orchestrator/harness/test_selector.py).
_TEST_ENV_VAR = "GUARDKIT_HARNESS_XREPO_SEAM"

# The HarnessEvent taxonomy every substrate's ``invoke`` / ``invoke_synthesis``
# may yield. Pinned here so a substrate that invents a new event type without
# extending the shared union is caught by the consumer-side dispatch contract.
_HARNESS_EVENT_TYPES = (
    AssistantMessageEvent,
    ToolUseEvent,
    ToolResultEvent,
    ResultMessageEvent,
)


def _real_selector_kwargs(model: Any) -> dict[str, Any]:
    """Return the EXACT kwarg bag the orchestrator forwards to ``select_harness``.

    Mirrors ``guardkit.orchestrator.agent_invoker.AgentInvoker._invoke_with_role``
    at the ``select_harness(...)`` call site (agent_invoker.py:3586-3612). If
    that call site grows or renames a kwarg, this helper must be updated in
    lockstep — keeping the seam test honest about what the live orchestrator
    actually passes.

    The ``cwd`` kwarg is intentionally omitted here so individual tests can
    supply (or withhold) the worktree path; everything else is the real bag.
    """
    return {
        "sdk_timeout_seconds": 600,
        "allowed_tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        "permission_mode": "acceptEdits",
        "max_turns": 25,
        # TASK-PERF-COACHSYNTH gather-bound knobs — the run-24 regression
        # surface. ``max_tool_result_chars`` is forwarded to
        # ``build_autobuild_backend``; ``recursion_limit`` to ``LangGraphHarness``.
        "recursion_limit": 25,
        "max_tool_result_chars": 8000,
        "model": model,
        "resume_session_id": None,
        "sdk_debug_dir": None,
        "cleanup_handler_installer": None,
    }


def _concrete_substrates() -> list[type[HarnessAdapter]]:
    """Collect every concrete (non-abstract) ``HarnessAdapter`` subclass.

    Walks ``HarnessAdapter.__subclasses__()`` recursively. Both production
    substrates are imported at module load (``ClaudeSDKHarness``,
    ``LangGraphHarness``), so a new substrate added to either repo and wired
    into the import graph is automatically covered by the contract assertions
    below — that is the AC-2 future-proofing ("a new substrate missing one
    fails CI").
    """
    seen: dict[type, None] = {}

    def _walk(cls: type) -> None:
        for sub in cls.__subclasses__():
            if sub in seen:
                continue
            seen[sub] = None
            _walk(sub)

    _walk(HarnessAdapter)
    concrete = [
        cls
        for cls in seen
        if not inspect.isabstract(cls)
        # Exclude private test fakes that may be imported into the same
        # process; the contract applies to production substrates.
        and not cls.__name__.startswith("_")
    ]
    return concrete


# ----------------------------------------------------------------------
# AC-1: real end-to-end construction through select_harness
# ----------------------------------------------------------------------


class TestRealConstructionThroughSelector:
    """AC-1: construct the real LangGraph harness + backend via ``select_harness``.

    Exercises the production dispatch path with the exact kwarg bag the
    orchestrator forwards. A kwarg the factory does not accept fails here as a
    ``TypeError`` — reproducing the run-24 TASK-FIX-BACKENDKWARG crash class in
    a fast CI check instead of a 25-second runtime failure.
    """

    def test_langgraph_constructed_end_to_end_with_real_kwargs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The full orchestrator kwarg bag flows through to a real LangGraphHarness."""
        monkeypatch.setenv(_TEST_ENV_VAR, "langgraph")

        # A bare-string model is the production shape (CLI ``--model`` alias).
        # The selector auto-prefixes it; LangGraphHarness stores it without
        # invoking the LLM at construction time, so no endpoint is hit.
        harness = select_harness(
            env_var=_TEST_ENV_VAR,
            cwd=tmp_path,
            **_real_selector_kwargs(model="qwen36-workhorse"),
        )

        assert isinstance(harness, LangGraphHarness)
        # AC-2 sub-claim: model= is threaded through the selector translation.
        assert harness.model is not None
        # The real backend was constructed from the worktree (run-24 surface).
        assert harness.backend is not None
        assert harness.permissions is not None

    def test_max_tool_result_chars_reaches_real_backend_factory(
        self, tmp_path: Path
    ) -> None:
        """AC-1 / run-24: the selector's forwarded kwarg is accepted by the factory.

        Reproduces the TASK-FIX-BACKENDKWARG contract directly against the
        installed ``build_autobuild_backend``: the orchestrator forwards
        ``max_tool_result_chars`` (selector.py:302). If guardkitfactory drops
        that parameter, this call raises ``TypeError`` and CI goes red — the
        exact failure that previously cost a full run to discover.
        """
        backend = build_autobuild_backend(tmp_path, max_tool_result_chars=8000)
        assert backend is not None

    def test_unknown_kwarg_surfaces_as_typeerror(self, tmp_path: Path) -> None:
        """A kwarg the factory does NOT accept fails as TypeError (run-24 class).

        Pins the failure *mode* the seam test relies on: signature drift in the
        cross-repo boundary surfaces as a ``TypeError`` at construction. If a
        future guardkitfactory accepted arbitrary ``**kwargs`` and swallowed
        unknowns, this assertion would fail and flag that the contract guard
        has gone soft.
        """
        with pytest.raises(TypeError):
            build_autobuild_backend(
                tmp_path, this_kwarg_does_not_exist=True  # type: ignore[call-arg]
            )


# ----------------------------------------------------------------------
# AC-2: substrate contract — invoke / invoke_synthesis / cancel + model=
# ----------------------------------------------------------------------


class TestSubstrateContract:
    """AC-2: every concrete HarnessAdapter substrate satisfies the contract.

    Codifies the ``harness-cancellation-contract.md`` grep signature
    (``rg "async def cancel"``) and the model-threading rule as executable
    assertions. A new substrate missing any required method, or relying on the
    no-op ABC ``cancel`` default, fails CI here.
    """

    def test_at_least_both_production_substrates_discovered(self) -> None:
        """Sanity: the discovery walk finds both production substrates."""
        substrates = _concrete_substrates()
        assert ClaudeSDKHarness in substrates
        assert LangGraphHarness in substrates

    @pytest.mark.parametrize(
        "method_name", ["invoke", "invoke_synthesis", "cancel"]
    )
    def test_substrate_implements_required_method(self, method_name: str) -> None:
        """Each substrate exposes invoke / invoke_synthesis / cancel."""
        for substrate in _concrete_substrates():
            method = getattr(substrate, method_name, None)
            assert method is not None and callable(method), (
                f"{substrate.__name__} is missing required substrate method "
                f"{method_name!r} (harness-cancellation-contract.md / "
                f"adapter.HarnessAdapter)."
            )

    @pytest.mark.parametrize("method_name", ["invoke", "invoke_synthesis"])
    def test_invoke_methods_are_async_generators(self, method_name: str) -> None:
        """invoke / invoke_synthesis must be async-generator functions.

        The orchestrator consumes them with ``async for event in harness.invoke(...)``.
        A coroutine that returns a list (rather than yielding) breaks that
        contract silently; ``inspect.isasyncgenfunction`` pins the shape.
        ``invoke_synthesis`` is allowed to be inherited from the ABC default
        (which is itself an async generator delegating to ``invoke``).
        """
        for substrate in _concrete_substrates():
            method = getattr(substrate, method_name)
            assert inspect.isasyncgenfunction(method), (
                f"{substrate.__name__}.{method_name} must be an async generator "
                f"yielding HarnessEvent values (got "
                f"{type(method).__name__}); see adapter.HarnessAdapter."
            )

    def test_cancel_is_overridden_not_abc_noop(self) -> None:
        """AC-2 / CTOUT01: each substrate OVERRIDES cancel (not the no-op default).

        ``HarnessAdapter.cancel`` is a no-op default kept only so legacy test
        fakes instantiate. A *production* substrate that does not override it
        cannot honour the orchestrator's cooperative cancellation
        (``AgentInvoker._cancel_monitor`` → ``await harness.cancel()``), which
        is exactly the TASK-FIX-CTOUT01 defect: the LangGraph substrate's
        in-flight ``agent.ainvoke`` ran to natural completion because nothing
        cancelled it. This is the executable form of the
        ``rg "async def cancel"`` grep signature.
        """
        for substrate in _concrete_substrates():
            assert substrate.cancel is not HarnessAdapter.cancel, (
                f"{substrate.__name__} does not override cancel() — it relies on "
                f"the no-op HarnessAdapter default and cannot honour cooperative "
                f"cancellation. See .claude/rules/harness-cancellation-contract.md."
            )
            assert inspect.iscoroutinefunction(substrate.cancel), (
                f"{substrate.__name__}.cancel must be `async def` (awaited by "
                f"AgentInvoker._cancel_monitor)."
            )

    def test_model_is_threaded_into_constructor(self) -> None:
        """AC-2: every substrate's __init__ accepts a ``model`` parameter.

        The model-threading family of regressions (F1/F9/F10/F12/F19) all
        reduced to ``model=`` not being threaded at a migrated call site. A
        substrate whose constructor cannot accept ``model`` makes the
        orchestrator's ``select_harness(..., model=model)`` forwarding a
        TypeError waiting to happen.
        """
        for substrate in _concrete_substrates():
            params = inspect.signature(substrate.__init__).parameters
            assert "model" in params, (
                f"{substrate.__name__}.__init__ does not accept `model` — the "
                f"orchestrator threads model= through select_harness at every "
                f"invocation site (F1/F9/F10/F12/F19 model-threading family)."
            )


# ----------------------------------------------------------------------
# AC-3: signature pin against the installed guardkitfactory
# ----------------------------------------------------------------------


class TestSignaturePin:
    """AC-3: the orchestrator's required parameters exist on the installed factory.

    ``inspect.signature`` against guardkitfactory's public constructors. A
    guardkit↔guardkitfactory version skew that removes or renames a parameter
    the orchestrator depends on is a red CI build, not a runtime 25-second
    crash.
    """

    def test_build_autobuild_backend_accepts_orchestrator_params(self) -> None:
        """``build_autobuild_backend`` accepts the worktree + max_tool_result_chars."""
        sig = inspect.signature(build_autobuild_backend)
        params = sig.parameters

        # The positional worktree path (selector.py:301-302 passes Path(cwd)).
        positional = [
            name
            for name, p in params.items()
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        assert positional, (
            "build_autobuild_backend lost its positional worktree parameter; "
            "selector.py calls build_autobuild_backend(Path(cwd), ...)."
        )

        # The run-24 keyword (selector.py:302).
        assert "max_tool_result_chars" in params, (
            "build_autobuild_backend dropped `max_tool_result_chars` — this is "
            "the TASK-FIX-BACKENDKWARG run-24 regression. The selector forwards "
            "it at guardkit/orchestrator/harness/selector.py:302."
        )

    def test_build_autobuild_permissions_is_zero_arg(self) -> None:
        """``build_autobuild_permissions()`` takes no required args (selector.py:304)."""
        sig = inspect.signature(build_autobuild_permissions)
        required = [
            name
            for name, p in sig.parameters.items()
            if p.default is inspect.Parameter.empty
            and p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        ]
        assert not required, (
            "build_autobuild_permissions grew a required parameter; the selector "
            "calls it with no arguments at selector.py:304."
        )

    def test_langgraph_harness_init_accepts_orchestrator_params(self) -> None:
        """``LangGraphHarness.__init__`` accepts model / backend / permissions / recursion_limit.

        These are exactly the four arguments the selector constructs it with
        (selector.py:299-306). A renamed or removed parameter here is a version
        skew that would otherwise only surface mid-run.
        """
        params = inspect.signature(LangGraphHarness.__init__).parameters
        for required in ("model", "backend", "permissions", "recursion_limit"):
            assert required in params, (
                f"LangGraphHarness.__init__ dropped/renamed {required!r}; the "
                f"selector constructs it with that kwarg "
                f"(guardkit/orchestrator/harness/selector.py:299-306)."
            )

    def test_invoke_signature_matches_adapter_contract(self) -> None:
        """Each substrate's ``invoke`` keeps the orchestrator-facing parameter names.

        The orchestrator calls ``harness.invoke(prompt=..., role=..., tools=...,
        cwd=..., timeout_seconds=...)``. Pin those names against every concrete
        substrate so a rename on either side of the repo split is caught.
        """
        expected = {"prompt", "role", "tools", "cwd", "timeout_seconds"}
        for substrate in _concrete_substrates():
            params = set(inspect.signature(substrate.invoke).parameters)
            missing = expected - params
            assert not missing, (
                f"{substrate.__name__}.invoke is missing parameter(s) {missing}; "
                f"the orchestrator calls invoke(prompt=, role=, tools=, cwd=, "
                f"timeout_seconds=)."
            )
