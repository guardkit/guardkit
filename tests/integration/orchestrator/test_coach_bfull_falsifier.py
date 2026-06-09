"""TASK-ARCH-COACHBFULL AC-3 — the falsifier (deterministic leg).

The empirical proof that the B-full investigating Coach adds adversarial value
over B-min. Construct a case the deterministic evidence bundle marks **green**
(all gates pass) but where an acceptance criterion is actually **unmet** — the
required behaviour is stubbed in the worktree.

Both legs use the SAME green bundle and the SAME *honest* synthesis Coach (a
fake harness that returns ``feedback`` iff the prompt shows an investigation
finding flagging a FAIL, else ``approve``). The ONLY difference between the legs
is whether the Phase-A gather ran:

* **B-full** (``GUARDKIT_COACH_GATHER=1``): the gather investigates, reports the
  stubbed AC, and the synthesis — seeing the FAIL finding — returns ``feedback``.
* **B-min** (gather OFF): no investigation, so the synthesis sees only the green
  bundle and ``approve``s the same unmet criterion.

That divergence, holding everything else equal, is the proof.

The companion live-substrate leg (one-off ``GUARDKIT_COACH_GATHER=1`` run against
gemma4:31b on the GB10) is captured in
``docs/state/TASK-ARCH-COACHBFULL/ac3-live-confirmation.md`` — it cannot run in
CI (no GPU substrate), so this deterministic leg is the regression guard.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)


# The acceptance criterion that the green bundle cannot see is unmet.
_STUBBED_AC = {"id": "AC-002", "text": "the export button actually exports a file"}
_GATHER_FAIL_FINDING = (
    "AC-001: PASS — handler wired and tested.\n"
    "AC-002: FAIL — src/export.py:12 `def export(): return None` is a stub; "
    "no file is written. IMMEDIATE ACTIONS NEEDED: implement export()."
)


def _make_invoker(worktree: Path) -> AgentInvoker:
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


def _green_bundle():
    """A bundle whose every deterministic gate is green — tests pass, honesty
    clean — yet AC-002 is unmet in the worktree (the bundle cannot tell)."""
    from guardkit.orchestrator.coach_verification import HonestyVerification
    from guardkit.orchestrator.quality_gates.coach_evidence import (
        CoachEvidenceBundle,
    )

    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        tests={"tests_run": 4, "tests_failed": 0, "tests_passed": 4},
    )


def _verdict(task_id: str, decision: str) -> str:
    return (
        "```json\n"
        f'{{"task_id": "{task_id}", "turn": 1, "decision": "{decision}", '
        f'"rationale": "honest coach verdict"}}\n'
        "```"
    )


def _honest_coach(task_id: str):
    """A fake ``_invoke_with_role`` modelling an HONEST Coach.

    Phase A (gather): reports the per-AC checklist that flags AC-002 FAIL.
    Phase B (synthesis): approves UNLESS the prompt carries an investigation
    finding flagging a FAIL — i.e. it only catches the stub when the gather ran.
    """
    calls: list[dict] = []

    async def _iwr(**kwargs):
        calls.append(kwargs)
        if not kwargs.get("synthesis"):
            return (None, [
                AssistantMessageEvent(text=_GATHER_FAIL_FINDING),
                ResultMessageEvent(session_id=None),
            ])
        prompt = kwargs["prompt"]
        caught = (
            "Coach Investigation Findings (Phase A)" in prompt
            and "AC-002: FAIL" in prompt
        )
        decision = "feedback" if caught else "approve"
        return (None, [
            AssistantMessageEvent(text=_verdict(task_id, decision)),
            ResultMessageEvent(session_id=None),
        ])

    return _iwr, calls


def _run(invoker: AgentInvoker, task_id: str):
    return asyncio.run(
        invoker.invoke_coach(
            task_id=task_id,
            turn=1,
            requirements="Implement export; AC-002: export button writes a file.",
            player_report={
                "files_modified": ["src/export.py"],
                "tests_passed": 4,
                "tests_failed": 0,
            },
            evidence_bundle=_green_bundle(),
            acceptance_criteria=[
                {"id": "AC-001", "text": "handler wired"},
                _STUBBED_AC,
            ],
        )
    )


class TestBfullFalsifier:
    def test_bfull_catches_stubbed_ac_that_bmin_approves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The two legs, holding the bundle + honest-Coach logic constant."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)  # synth ON

        # --- Leg 1: B-min (gather OFF) approves the green-but-unmet bundle ---
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        bmin = _make_invoker(tmp_path / "bmin")
        iwr_min, calls_min = _honest_coach("TASK-FALSIFY-MIN")
        bmin._invoke_with_role = iwr_min  # type: ignore[method-assign]
        result_min = _run(bmin, "TASK-FALSIFY-MIN")

        assert result_min.success is True
        assert result_min.report["decision"] == "approve"  # rubber-stamped
        assert len(calls_min) == 1  # no gather ran

        # --- Leg 2: B-full (gather ON) catches the stub, returns feedback ---
        monkeypatch.setenv("GUARDKIT_COACH_GATHER", "1")
        bfull = _make_invoker(tmp_path / "bfull")
        iwr_full, calls_full = _honest_coach("TASK-FALSIFY-FULL")
        bfull._invoke_with_role = iwr_full  # type: ignore[method-assign]
        result_full = _run(bfull, "TASK-FALSIFY-FULL")

        assert result_full.success is True
        assert result_full.report["decision"] == "feedback"  # investigation caught it
        assert len(calls_full) == 2  # gather then synthesis

        # The proof: same bundle, same honest Coach, opposite verdicts —
        # the ONLY difference is whether the Phase-A investigation ran.
        assert result_min.report["decision"] != result_full.report["decision"]
