"""TASK-ARCH-COACHSPLIT (D-3) — toolless grammar-enforced Coach synthesis.

Covers the GuardKit-orchestrator side of the Coach split:

* the GUARDKIT_COACH_SYNTHESIS gate (``_coach_synthesis_enabled``),
* the packaged GBNF grammar loader + byte-parity with the docs source,
* the ``HarnessAdapter.invoke_synthesis`` default (delegates to a TOOLLESS
  ``invoke(tools=[])``), proving substrate-agnostic toolless dispatch,
* the synthesis variant of ``_build_coach_prompt`` (AC-5: toolless framing +
  absence-of-failure guards preserved; legacy variant unchanged),
* ``invoke_coach`` routing (AC-1: synthesis path dispatches ``_invoke_with_role``
  with ``allowed_tools=[]``, ``synthesis=True``, and the verdict grammar;
  the legacy path keeps the read-only tool set).

The substrate-level toolless+grammar request shape (AC-2/AC-3) is asserted in
guardkitfactory's ``test_langgraph_harness_synthesis.py``; the run-19 falsifier
(AC-4) is the operator's live GB10 run.

Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency,
matching the harness test suite's convention.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    _coach_synthesis_enabled,
)
from guardkit.orchestrator.coach_grammar import load_coach_verdict_grammar
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    HarnessAdapter,
    ResultMessageEvent,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _build_invoker(worktree: Path) -> AgentInvoker:
    """Minimal AgentInvoker for prompt/routing tests (mirrors the
    convention in test_coach_zero_cardinality_guard.py)."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


# ---------------------------------------------------------------------------
# Gate — _coach_synthesis_enabled (GUARDKIT_COACH_SYNTHESIS)
# ---------------------------------------------------------------------------


class TestSynthesisGate:
    def test_default_is_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        assert _coach_synthesis_enabled() is True

    @pytest.mark.parametrize("val", ["0", "false", "False", "NO", "off", " off "])
    def test_disabled_values(
        self, monkeypatch: pytest.MonkeyPatch, val: str
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_SYNTHESIS", val)
        assert _coach_synthesis_enabled() is False

    @pytest.mark.parametrize("val", ["1", "true", "yes", "on", "anything-else"])
    def test_enabled_values(
        self, monkeypatch: pytest.MonkeyPatch, val: str
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_SYNTHESIS", val)
        assert _coach_synthesis_enabled() is True


# ---------------------------------------------------------------------------
# Grammar loader + parity (AC-3)
# ---------------------------------------------------------------------------


class TestGrammarAsset:
    def test_loader_returns_verdict_grammar(self) -> None:
        g = load_coach_verdict_grammar()
        # The grammar must enforce the verdict contract the parser consumes.
        assert "root" in g
        assert "req-task-id" in g
        assert "req-turn" in g
        assert '"approve"' in g and '"feedback"' in g

    def test_strict_variant_loads(self) -> None:
        g = load_coach_verdict_grammar(strict=True)
        assert "root" in g and "code-fence" in g

    def test_packaged_grammar_is_byte_identical_to_docs_source(self) -> None:
        """The packaged copy MUST match the validated docs/research source so
        the probe-validated grammar is exactly what ships."""
        repo_root = Path(__file__).resolve().parents[2]
        docs_primary = (
            repo_root / "docs" / "research" / "dgx-spark" / "grammars"
            / "coach-verdict.gbnf"
        )
        packaged_primary = (
            repo_root / "guardkit" / "orchestrator" / "grammars"
            / "coach-verdict.gbnf"
        )
        assert docs_primary.read_text() == packaged_primary.read_text()


# ---------------------------------------------------------------------------
# HarnessAdapter.invoke_synthesis default — TOOLLESS delegation
# ---------------------------------------------------------------------------


class _RecordingHarness(HarnessAdapter):
    """Minimal concrete harness that only implements invoke(), so the ABC
    default invoke_synthesis() is exercised."""

    def __init__(self) -> None:
        self.invoke_calls: list[dict] = []

    async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
        self.invoke_calls.append(
            {"prompt": prompt, "role": role, "tools": tools}
        )
        yield AssistantMessageEvent(text="ok")
        yield ResultMessageEvent(session_id=None)


class TestAdapterDefaultInvokeSynthesis:
    def test_default_delegates_to_toolless_invoke(self) -> None:
        harness = _RecordingHarness()

        async def _collect() -> list:
            events = []
            async for ev in harness.invoke_synthesis(
                prompt="synthesise",
                role="coach",
                grammar="IGNORED-ON-SDK",
                cwd=Path.cwd(),
                timeout_seconds=30,
            ):
                events.append(ev)
            return events

        events = asyncio.run(_collect())

        # Default delegated to invoke() with an EMPTY tool list (toolless),
        # dropping the grammar — correct for substrates without GBNF support.
        assert len(harness.invoke_calls) == 1
        assert harness.invoke_calls[0]["tools"] == []
        assert harness.invoke_calls[0]["role"] == "coach"
        assert isinstance(events[0], AssistantMessageEvent)
        assert isinstance(events[1], ResultMessageEvent)


# ---------------------------------------------------------------------------
# _build_coach_prompt synthesis variant (AC-5 framing + guards preserved)
# ---------------------------------------------------------------------------


class TestSynthesisPrompt:
    def test_synthesis_prompt_has_toolless_banner_and_responsibilities(
        self, tmp_path: Path
    ) -> None:
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-SYN-001",
            turn=1,
            requirements="do the thing",
            player_report={"files_modified": []},
            synthesis=True,
        )
        assert "TOOLLESS SYNTHESIS" in prompt
        assert "You have NO tools" in prompt
        # AC-5: the synthesis responsibilities must restate the
        # absence-of-failure rule so an absent/zero-cardinality oracle is
        # NOT treated as a pass.
        assert "zero-cardinality oracle is NOT a pass" in prompt
        # It must NOT instruct the model to run tools it does not have.
        assert "Run the tests yourself" not in prompt

    def test_legacy_prompt_unchanged_when_not_synthesis(
        self, tmp_path: Path
    ) -> None:
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-SYN-001",
            turn=1,
            requirements="do the thing",
            player_report={"files_modified": []},
            synthesis=False,
        )
        assert "TOOLLESS SYNTHESIS" not in prompt
        assert "Run the tests yourself" in prompt

    def test_synthesis_prompt_preserves_absence_of_failure_guards(
        self, tmp_path: Path
    ) -> None:
        """AC-5/AC-6: with an evidence bundle the synthesis prompt must STILL
        carry the absence-of-failure guards + honesty section (the synthesis
        variant only changes the responsibilities/banner)."""
        from guardkit.orchestrator.coach_verification import HonestyVerification
        from guardkit.orchestrator.quality_gates.coach_evidence import (
            CoachEvidenceBundle,
        )

        honesty = HonestyVerification(
            verified=True,
            discrepancies=[],
            honesty_score=1.0,
            resolved_paths=[],
        )
        bundle = CoachEvidenceBundle(
            honesty=honesty,
            gathering_status="complete",
            bdd={
                "scenarios_attempted": 0,
                "scenarios_failed": 0,
                "scenarios_passed": 0,
            },
        )
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-SYN-002",
            turn=1,
            requirements="zero cardinality",
            player_report={"files_modified": []},
            evidence_bundle=bundle,
            synthesis=True,
        )
        assert "TOOLLESS SYNTHESIS" in prompt
        # The five absence-of-failure guards survive the synthesis variant.
        assert "ZERO-CARDINALITY BDD GUARD" in prompt
        # AC-6: honesty verification section is rendered from the bundle.
        assert "<honesty_verification>" in prompt
        # The deterministic evidence bundle is rendered.
        assert "<evidence_bundle>" in prompt


# ---------------------------------------------------------------------------
# invoke_coach routing (AC-1)
# ---------------------------------------------------------------------------


def _make_invoker_for_routing(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._verify_player_claims = MagicMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(
            verified=True, honesty_score=1.0, discrepancies=[]
        )
    )
    return invoker


def _make_bundle():
    """A minimal complete CoachEvidenceBundle so invoke_coach takes the
    synthesis path (synthesis is gated on bundle presence)."""
    from guardkit.orchestrator.coach_verification import HonestyVerification
    from guardkit.orchestrator.quality_gates.coach_evidence import (
        CoachEvidenceBundle,
    )

    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
    )


class TestInvokeCoachRouting:
    def test_synthesis_path_dispatches_toolless_with_grammar(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)  # default ON
        invoker = _make_invoker_for_routing(tmp_path)

        # Capture _invoke_with_role kwargs, then short-circuit (raise) so the
        # downstream parser/loader path is irrelevant to this routing test.
        iwr = AsyncMock(side_effect=RuntimeError("stop-after-capture"))
        with patch.object(invoker, "_invoke_with_role", iwr):
            result = asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-RT-001",
                    turn=1,
                    requirements="reqs",
                    player_report={"files_modified": []},
                    evidence_bundle=_make_bundle(),  # synthesis requires a bundle
                )
            )

        # invoke_coach swallows the error into a failure result; we only care
        # that the routing kwargs were correct.
        assert result.success is False
        iwr.assert_awaited_once()
        kwargs = iwr.call_args.kwargs
        assert kwargs["allowed_tools"] == []          # toolless (AC-1)
        assert kwargs["synthesis"] is True            # dispatch invoke_synthesis
        assert kwargs["agent_type"] == "coach"        # preserves model routing
        assert kwargs["grammar"] and "root" in kwargs["grammar"]  # verdict grammar
        assert "TOOLLESS SYNTHESIS" in kwargs["prompt"]

    def test_no_bundle_falls_back_to_legacy_tools(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Synthesis is gated on bundle presence: with synthesis ENABLED but no
        evidence_bundle, invoke_coach must use the legacy tool-using Coach so it
        can investigate in place of the absent deterministic evidence (review
        finding — a toolless 'synthesise over the bundle' prompt with no bundle
        is an absence-of-failure false-green hazard)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)  # default ON
        invoker = _make_invoker_for_routing(tmp_path)

        iwr = AsyncMock(side_effect=RuntimeError("stop-after-capture"))
        with patch.object(invoker, "_invoke_with_role", iwr):
            asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-RT-003",
                    turn=1,
                    requirements="reqs",
                    player_report={"files_modified": []},
                    # no evidence_bundle → legacy tool-using path despite synthesis ON
                )
            )

        kwargs = iwr.call_args.kwargs
        assert kwargs["allowed_tools"] == ["Read", "Bash", "Grep", "Glob"]
        assert kwargs.get("synthesis", False) is False
        assert "TOOLLESS SYNTHESIS" not in kwargs["prompt"]

    def test_legacy_path_keeps_readonly_tools(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_SYNTHESIS", "0")  # disable synthesis
        invoker = _make_invoker_for_routing(tmp_path)

        iwr = AsyncMock(side_effect=RuntimeError("stop-after-capture"))
        with patch.object(invoker, "_invoke_with_role", iwr):
            asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-RT-002",
                    turn=1,
                    requirements="reqs",
                    player_report={"files_modified": []},
                    evidence_bundle=_make_bundle(),  # even with a bundle, gate off → legacy
                )
            )

        kwargs = iwr.call_args.kwargs
        assert kwargs["allowed_tools"] == ["Read", "Bash", "Grep", "Glob"]
        # Legacy path does not pass the synthesis flag (defaults to False).
        assert kwargs.get("synthesis", False) is False
        assert "TOOLLESS SYNTHESIS" not in kwargs["prompt"]
