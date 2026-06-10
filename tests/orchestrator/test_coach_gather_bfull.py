"""TASK-ARCH-COACHBFULL — the B-full investigating Coach (Phase-A gather).

Covers the GuardKit-orchestrator side of the two-phase Coach:

* the GUARDKIT_COACH_GATHER gate (``_coach_gather_enabled``) — default OFF,
* the Phase-A gather prompt (``_build_coach_gather_prompt``: investigation
  framing, per-AC checklist, NO fenced JSON verdict),
* ``invoke_coach`` routing with gather ON vs OFF (AC-1: a tool-bound gather
  call precedes the toolless synthesis; OFF stays pure B-min),
* strict dominance (AC-2): a Phase-A failure / empty findings degrades to
  B-min and the turn still produces a valid verdict,
* cancellation + budget (AC-5): a CancelledError mid-gather propagates (is NOT
  swallowed); the gather runs under a bounded timeout slice and Phase B keeps
  the full effective timeout,
* criteria threading (AC-4): acceptance_criteria reach the synthesis prompt so
  the verdict can populate criteria_verification (the run-19 empty-array fix).

The bundle-green-but-AC-unmet falsifier (AC-3) lives in
``tests/integration/orchestrator/test_coach_bfull_falsifier.py``.

Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency,
matching ``test_coach_synthesis_split.py``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    _coach_gather_enabled,
)
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    """Minimal AgentInvoker for routing tests (mirrors
    test_coach_synthesis_split.py::_make_invoker_for_routing)."""
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
    """Minimal complete CoachEvidenceBundle so invoke_coach takes the synthesis
    path (synthesis — and therefore the gather — is gated on bundle presence)."""
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


def _verdict_events(task_id: str, turn: int = 1, decision: str = "approve"):
    """A harness event stream carrying a schema-valid fenced JSON verdict."""
    verdict = (
        "Reasoning prose here.\n\n"
        "```json\n"
        f'{{"task_id": "{task_id}", "turn": {turn}, '
        f'"decision": "{decision}", "rationale": "deterministic test verdict"}}\n'
        "```"
    )
    return (None, [
        AssistantMessageEvent(text=verdict),
        ResultMessageEvent(session_id=None),
    ])


def _findings_events(text: str):
    return (None, [
        AssistantMessageEvent(text=text),
        ResultMessageEvent(session_id=None),
    ])


# ---------------------------------------------------------------------------
# Gate — _coach_gather_enabled (GUARDKIT_COACH_GATHER), default OFF
# ---------------------------------------------------------------------------


class TestGatherGate:
    def test_default_is_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        assert _coach_gather_enabled() is False

    @pytest.mark.parametrize("val", ["1", "true", "True", "YES", "on", " on "])
    def test_enabled_values(
        self, monkeypatch: pytest.MonkeyPatch, val: str
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_GATHER", val)
        assert _coach_gather_enabled() is True

    @pytest.mark.parametrize("val", ["0", "false", "no", "off", "anything-else"])
    def test_disabled_values(
        self, monkeypatch: pytest.MonkeyPatch, val: str
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_GATHER", val)
        assert _coach_gather_enabled() is False


# ---------------------------------------------------------------------------
# Phase-A gather prompt (_build_coach_gather_prompt)
# ---------------------------------------------------------------------------


class TestGatherPrompt:
    def test_gather_prompt_is_investigation_not_verdict(
        self, tmp_path: Path
    ) -> None:
        prompt = _make_invoker(tmp_path)._build_coach_gather_prompt(
            task_id="TASK-GA-001",
            turn=1,
            requirements="do the thing",
            player_report={"files_modified": ["src/foo.py"]},
            honesty_verification=None,
            evidence_bundle=_make_bundle(),
            acceptance_criteria=[
                {"id": "AC-001", "text": "feature works"},
                {"id": "AC-002", "text": "edge case handled"},
            ],
        )
        # Framed as investigation, with the read-only tool set.
        assert "INVESTIGATION" in prompt
        assert "Read, Bash, Grep, Glob" in prompt
        # Per-AC checklist is present.
        assert "AC-001" in prompt and "AC-002" in prompt
        # It must NOT instruct the model to emit the fenced JSON verdict —
        # that is Phase B's job.
        assert "THIS IS NOT THE VERDICT" in prompt
        assert "emit a fenced ```json decision block" in prompt
        # Evidence dossier is rendered so the gather knows what's been checked.
        assert "<evidence_bundle>" in prompt


# ---------------------------------------------------------------------------
# invoke_coach routing with gather (AC-1) + OFF stays B-min
# ---------------------------------------------------------------------------


class TestInvokeCoachGatherRouting:
    def test_gather_off_is_pure_bmin_single_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Default (flag unset) ⇒ NO gather call: exactly one synthesis call."""
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)  # default OFF
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)  # synth ON
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            return _verdict_events("TASK-OFF-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        result = asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-OFF-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": []},
                evidence_bundle=_make_bundle(),
            )
        )

        assert result.success is True
        assert len(calls) == 1
        assert calls[0]["synthesis"] is True  # the only call is the synthesis
        assert "Coach Investigation Findings" not in calls[0]["prompt"]

    def test_gather_on_runs_toolbound_then_toolless(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-1: gather ON ⇒ first call is tool-bound (synthesis=False, read-only
        tools), second is toolless+grammar; the gather findings are threaded
        into the synthesis prompt."""
        monkeypatch.setenv("GUARDKIT_COACH_GATHER", "1")
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)  # synth ON
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                # Phase A gather: emit findings text.
                return _findings_events(
                    "AC-002: FAIL — behaviour stubbed at src/foo.py:10"
                )
            return _verdict_events("TASK-ON-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        result = asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-ON-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": ["src/foo.py"]},
                evidence_bundle=_make_bundle(),
            )
        )

        assert result.success is True
        assert len(calls) == 2

        gather, synth = calls[0], calls[1]
        # Phase A — tool-bound investigation.
        assert gather["synthesis"] is False
        assert gather["allowed_tools"] == ["Read", "Bash", "Grep", "Glob"]
        assert gather["agent_type"] == "coach"
        assert "THIS IS NOT THE VERDICT" in gather["prompt"]
        # Phase B — toolless grammar synthesis, now carrying the findings.
        assert synth["synthesis"] is True
        assert synth["allowed_tools"] == []
        assert "Coach Investigation Findings (Phase A)" in synth["prompt"]
        assert "AC-002: FAIL" in synth["prompt"]

    def test_gather_failure_degrades_to_bmin(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-2 strict dominance: a Phase-A exception (e.g. tool-parse 500)
        degrades to B-min — synthesis still runs, a valid verdict emerges, the
        turn is NOT failed, and the synthesis prompt has no findings section."""
        monkeypatch.setenv("GUARDKIT_COACH_GATHER", "1")
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                raise RuntimeError("HTTP 500 Failed to parse input")  # run-18 class
            return _verdict_events("TASK-DEG-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        result = asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-DEG-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": []},
                evidence_bundle=_make_bundle(),
            )
        )

        assert result.success is True  # turn not failed
        assert result.report["decision"] == "approve"
        assert len(calls) == 2  # gather (raised, caught) + synthesis
        assert calls[1]["synthesis"] is True
        assert "Coach Investigation Findings" not in calls[1]["prompt"]

    def test_empty_findings_degrade_to_bmin(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-2/AC-6: an empty gather (whitespace-only findings) degrades to
        B-min — no findings section is injected (absent evidence must not be
        dressed up as positive signal)."""
        monkeypatch.setenv("GUARDKIT_COACH_GATHER", "1")
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                return _findings_events("   \n  \t ")  # whitespace-only
            return _verdict_events("TASK-EMPTY-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        result = asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-EMPTY-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": []},
                evidence_bundle=_make_bundle(),
            )
        )

        assert result.success is True
        assert len(calls) == 2
        assert "Coach Investigation Findings" not in calls[1]["prompt"]

    def test_cancellation_during_gather_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-5: a genuine CancelledError mid-gather is NOT swallowed by the
        degrade-to-B-min handler (it is BaseException, not Exception) — it
        propagates and the synthesis call is never made."""
        monkeypatch.setenv("GUARDKIT_COACH_GATHER", "1")
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                raise asyncio.CancelledError()
            return _verdict_events("TASK-CANC-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-CANC-001",
                    turn=1,
                    requirements="reqs",
                    player_report={"files_modified": []},
                    evidence_bundle=_make_bundle(),
                )
            )

        assert len(calls) == 1  # only the gather; synthesis never reached
        assert calls[0]["synthesis"] is False

    def test_gather_budget_is_bounded_synthesis_keeps_full(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-5: Phase A runs under a bounded slice (≤ 40% of effective, floored
        at 60s); Phase B keeps the full effective timeout. effective=600 ⇒
        gather sees 240, synthesis sees 600."""
        monkeypatch.setenv("GUARDKIT_COACH_GATHER", "1")
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        invoker = _make_invoker(tmp_path)  # _calculate_sdk_timeout → 600

        seen: list[tuple[bool, int]] = []

        async def _iwr(**kwargs):
            seen.append((bool(kwargs.get("synthesis")), invoker.sdk_timeout_seconds))
            if not kwargs.get("synthesis"):
                return _findings_events("AC-001: PASS")
            return _verdict_events("TASK-BUD-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-BUD-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": []},
                evidence_bundle=_make_bundle(),
            )
        )

        assert seen == [(False, 240), (True, 600)]
        # Timeout restored after the turn.
        assert invoker.sdk_timeout_seconds == 600


# ---------------------------------------------------------------------------
# Acceptance-criteria threading into the synthesis prompt (AC-4)
# ---------------------------------------------------------------------------


class TestCriteriaThreading:
    def test_synthesis_prompt_carries_per_ac_checklist_and_example(
        self, tmp_path: Path
    ) -> None:
        """AC-4 root-cause fix: when acceptance_criteria are threaded, the
        synthesis prompt gains the 'verify EACH criterion' section AND the
        criteria_verification example — the absence of which produced run-19's
        empty criteria_verification arrays."""
        prompt = _make_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-AC4-001",
            turn=1,
            requirements="do the thing",
            player_report={"files_modified": []},
            acceptance_criteria=[
                {"id": "AC-001", "text": "feature works"},
                {"id": "AC-002", "text": "edge case handled"},
            ],
            evidence_bundle=_make_bundle(),
            synthesis=True,
        )
        assert "Acceptance Criteria to Verify" in prompt
        assert "AC-001" in prompt and "AC-002" in prompt
        assert "criteria_verification" in prompt
        assert '"criterion_id"' in prompt

    def test_no_criteria_section_when_acs_absent(self, tmp_path: Path) -> None:
        """Back-compat: omitting acceptance_criteria keeps the pre-COACHBFULL
        prompt (no per-criterion section)."""
        prompt = _make_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-AC4-002",
            turn=1,
            requirements="do the thing",
            player_report={"files_modified": []},
            evidence_bundle=_make_bundle(),
            synthesis=True,
        )
        assert "Acceptance Criteria to Verify" not in prompt


# ---------------------------------------------------------------------------
# TASK-PERF-COACHSYNTH — gather is bounded so it cannot overflow the window
# (AC-1 / AC-2 plumbing) + synthesis-prompt findings truncation (AC-4).
# ---------------------------------------------------------------------------


class TestGatherBoundPlumbing:
    """The Phase-A gather call must carry the recursion_limit + tool-result

    truncation bounds (the load-bearing F20 fix), and the toolless synthesis
    call must NOT (so the verdict generation is unconstrained by gather knobs).
    """

    def test_gather_call_carries_bounds_synthesis_does_not(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from guardkit.orchestrator.agent_invoker import (
            _COACH_GATHER_MAX_TOOL_RESULT_CHARS,
            _COACH_GATHER_RECURSION_LIMIT,
        )

        monkeypatch.setenv("GUARDKIT_COACH_GATHER", "1")
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        invoker = _make_invoker(tmp_path)

        calls: list[dict] = []

        async def _iwr(**kwargs):
            calls.append(kwargs)
            if not kwargs.get("synthesis"):
                return _findings_events("AC-001: PASS — verified at src/foo.py:5")
            return _verdict_events("TASK-BND-001")

        invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
        asyncio.run(
            invoker.invoke_coach(
                task_id="TASK-BND-001",
                turn=1,
                requirements="reqs",
                player_report={"files_modified": ["src/foo.py"]},
                evidence_bundle=_make_bundle(),
            )
        )

        assert len(calls) == 2
        gather, synth = calls[0], calls[1]
        # AC-1: gather is bounded — recursion ceiling + per-tool-result cap.
        assert gather["recursion_limit"] == _COACH_GATHER_RECURSION_LIMIT
        assert (
            gather["max_tool_result_chars"]
            == _COACH_GATHER_MAX_TOOL_RESULT_CHARS
        )
        # The bounds must be REAL caps, not disabled.
        assert gather["recursion_limit"] > 0
        assert gather["max_tool_result_chars"] > 0
        # Synthesis (verdict) must not inherit the gather knobs.
        assert synth.get("recursion_limit") is None
        assert synth.get("max_tool_result_chars") is None


# Plumbing coverage note (TASK-PERF-COACHSYNTH): the two remaining hops are
# covered elsewhere — the gather → _invoke_with_role kwargs hop by
# TestGatherBoundPlumbing above, and the select_harness → LangGraphHarness /
# build_autobuild_backend hop by
# tests/orchestrator/harness/test_selector.py::TestSelectHarnessGatherBounds.


class TestGatherFindingsTruncation:
    """AC-4: the Phase-A findings injected into the synthesis prompt are

    capped (with a visible marker) so synthesis-prompt size cannot grow
    unbounded with gather volume (the run-20 latency creep).
    """

    def test_under_limit_passthrough(self) -> None:
        small = "AC-001: PASS\nAC-002: PASS"
        assert AgentInvoker._truncate_gather_findings(small) == small

    def test_over_limit_is_capped_and_marked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            AgentInvoker, "_COACH_GATHER_FINDINGS_LIMIT_CHARS", 100
        )
        big = "F" * 5000
        out = AgentInvoker._truncate_gather_findings(big)
        assert len(out) < len(big)
        assert out.startswith("F" * 100)
        # The marker is load-bearing — the synthesis must not treat the
        # truncated checklist as complete (absence-of-failure-is-not-success).
        assert "truncated" in out
        assert "FAIL/UNSURE" in out

    def test_truncation_applied_in_synthesis_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            AgentInvoker, "_COACH_GATHER_FINDINGS_LIMIT_CHARS", 200
        )
        prompt = _make_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-TRC-001",
            turn=1,
            requirements="reqs",
            player_report={"files_modified": []},
            evidence_bundle=_make_bundle(),
            synthesis=True,
            gather_findings="G" * 8000,
        )
        # The findings section is present but bounded + marked.
        assert "Coach Investigation Findings (Phase A)" in prompt
        assert "truncated for synthesis-prompt budget" in prompt
        # The full 8000-char blob must NOT appear verbatim.
        assert "G" * 8000 not in prompt
