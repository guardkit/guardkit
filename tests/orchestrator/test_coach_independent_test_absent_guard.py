"""TASK-FIX-COACHFG01 — fail-closed when the Coach's independent-test oracle
is absent (``signal_absent``).

Reproduces and closes the run-19 false-green: the toolless synthesis Coach's
own trust-but-verify pytest run timed out (300s → ``signal_absent=True``) yet
the local model emitted ``approve`` anyway, and the orchestrator accepted it
because guard #6 lived only in the prompt. These tests drive the REAL
``invoke_coach`` synthesis decision path (mocked harness emits the verdict;
``extract_and_write`` → ``_load_agent_report`` → ``_validate_coach_decision``
all run for real against a tmp worktree) and assert the deterministic
post-synthesis guard overrides ``approve``→``feedback`` when, and only when,
the independent-test signal is absent.

Instance of ``.claude/rules/absence-of-failure-is-not-success.md`` — the
"wire the verifier into the *primary* path, not just the LLM" remediation
applied to the TASK-ARCH-COACHSPLIT (D-3) toolless-synthesis decision path.

Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency,
matching the convention in ``test_coach_synthesis_split.py``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    IndependentTestResult,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    """A minimal AgentInvoker able to run the full ``invoke_coach`` synthesis
    path (mirrors ``_make_invoker_for_routing`` in test_coach_synthesis_split,
    but does NOT short-circuit ``_invoke_with_role`` — the downstream
    parser/loader/validator run for real)."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _bundle(independent: Optional[IndependentTestResult]) -> CoachEvidenceBundle:
    """A complete bundle (so ``invoke_coach`` takes the synthesis path) whose
    ``independent_tests`` leg is whatever the test supplies."""
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        independent_tests=independent,
    )


def _approve_events(task_id: str, turn: int) -> list:
    """Harness events carrying a fenced ``approve`` verdict — the run-19 shape:
    a clean approve emitted DESPITE the independent oracle never completing."""
    verdict = {
        "task_id": task_id,
        "turn": turn,
        "decision": "approve",
        "rationale": "All Player-reported gates pass; tests look green.",
        "criteria_verification": [],
    }
    text = "```json\n" + json.dumps(verdict) + "\n```"
    return [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)]


def _run_coach(
    invoker: AgentInvoker,
    *,
    task_id: str,
    turn: int,
    bundle: CoachEvidenceBundle,
):
    """Invoke the Coach with ``_invoke_with_role`` mocked to return the
    approve-verdict harness events. Everything else runs for real."""
    iwr = AsyncMock(return_value=(None, _approve_events(task_id, turn)))
    with patch.object(invoker, "_invoke_with_role", iwr):
        return asyncio.run(
            invoker.invoke_coach(
                task_id=task_id,
                turn=turn,
                requirements="reqs",
                player_report={"files_modified": [], "tests_passed": True},
                evidence_bundle=bundle,
            )
        )


# ---------------------------------------------------------------------------
# AC-4 — reproducer: signal_absent approve is overridden to feedback
# ---------------------------------------------------------------------------


class TestAbsentSignalOverride:
    def test_signal_absent_approve_is_overridden_to_feedback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-4 (run-19 reproducer). An ``approve`` verdict synthesised over a
        bundle whose independent-test oracle TIMED OUT (signal_absent=True,
        tests_passed=False) MUST be returned as ``feedback``. This test fails
        on ``main`` (which returns the false-green ``approve``) and passes
        after the deterministic guard lands."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)  # default ON
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)  # gather OFF
        invoker = _make_invoker(tmp_path)

        independent = IndependentTestResult(
            tests_passed=False,
            test_command="pytest -q",
            test_output_summary="SDK coach test execution timed out after 300s",
            duration_seconds=300.0,
            signal_absent=True,
        )
        result = _run_coach(
            invoker, task_id="TASK-RUN19", turn=1, bundle=_bundle(independent)
        )

        assert result.success is True
        assert result.report["decision"] == "feedback"

    def test_override_rationale_and_category(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-2. The overridden verdict names the cause and quotes
        ``test_output_summary`` verbatim, with ``category: absence_of_failure``."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        summary = "SDK independent tests failed in 300.0s (transport timeout)"
        independent = IndependentTestResult(
            tests_passed=False,
            test_command="pytest -q",
            test_output_summary=summary,
            duration_seconds=300.0,
            signal_absent=True,
        )
        result = _run_coach(
            invoker, task_id="TASK-RUN19", turn=2, bundle=_bundle(independent)
        )

        rationale = result.report["rationale"]
        assert (
            "Independent test verification did not complete (signal absent)"
            in rationale
        )
        assert (
            "cannot independently confirm the Player's reported tests"
            in rationale
        )
        # test_output_summary preserved verbatim so operators see timeout vs error
        assert summary in rationale

        issues = result.report["issues"]
        assert any(i.get("category") == "absence_of_failure" for i in issues)

    def test_override_rewrites_coach_turn_file_on_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The on-disk ``coach_turn_N.json`` must also flip to ``feedback`` —
        Layer-4 late-approval reconciliation
        (``feature_orchestrator._check_late_approval``) reads ``decision``
        straight off disk, so an in-memory-only override would be resurrected
        as ``approve``. See .claude/rules/harness-cancellation-contract.md."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        independent = IndependentTestResult(
            tests_passed=False,
            test_command="pytest -q",
            test_output_summary="timed out after 300s",
            duration_seconds=300.0,
            signal_absent=True,
        )
        _run_coach(
            invoker, task_id="TASK-RUN19", turn=3, bundle=_bundle(independent)
        )

        on_disk = json.loads(
            invoker._get_report_path("TASK-RUN19", 3, "coach").read_text()
        )
        assert on_disk["decision"] == "feedback"


# ---------------------------------------------------------------------------
# AC-5 / AC-6 — no over-reach, no happy-path regression
# ---------------------------------------------------------------------------


class TestGuardDoesNotOverReach:
    def test_genuine_failure_is_not_short_circuited(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-5. Independent tests that RAN and genuinely FAILED
        (tests_passed=False, signal_absent=False) are NOT this guard's case —
        the guard is a no-op and the verdict flows through unchanged (here:
        the synthesised ``approve`` is left for the existing
        conditional-approval / _classify_test_failure path to own)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        independent = IndependentTestResult(
            tests_passed=False,
            test_command="pytest -q",
            test_output_summary="2 failed, 8 passed",
            duration_seconds=12.0,
            signal_absent=False,  # ran and failed — NOT absent
        )
        result = _run_coach(
            invoker, task_id="TASK-FAIL", turn=1, bundle=_bundle(independent)
        )

        assert result.report["decision"] == "approve"

    def test_happy_path_approve_is_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-6. Independent tests that ran and PASSED (tests_passed=True,
        signal_absent=False) with an ``approve`` verdict are returned as
        ``approve`` untouched."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        independent = IndependentTestResult(
            tests_passed=True,
            test_command="pytest -q",
            test_output_summary="10 passed",
            duration_seconds=9.0,
            signal_absent=False,
        )
        result = _run_coach(
            invoker, task_id="TASK-OK", turn=1, bundle=_bundle(independent)
        )

        assert result.report["decision"] == "approve"

    def test_no_independent_tests_leg_leaves_approve(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A bundle with no independent-test leg at all (None) is not this
        guard's case — an ``approve`` is returned untouched (the absent-leg
        situation is owned by the gathering_status guard #5, not guard #6)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker, task_id="TASK-NOIND", turn=1, bundle=_bundle(None)
        )

        assert result.report["decision"] == "approve"
