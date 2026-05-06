"""Unit tests for ``_record_honesty`` consumer guard + producer-side
honesty_verification threading (TASK-FIX-7E3F).

Covers:

- ``TestRecordHonestyConsumerGuard`` (AC-7): the autobuild.py consumer guard
  must early-return on ``None`` payloads, fall back gracefully on a missing
  key, populate ``_honesty_history`` on real payloads, and preserve the
  pre-existing ``not coach_result.success`` short-circuit.

- ``TestCoachValidatorProducerThreading`` (AC-8): the coach_validator.py
  helper signatures must thread ``honesty_verification`` through every
  decision shape so ``to_dict()["honesty_verification"]`` is a populated
  dict and ``_record_honesty`` actually advances ``_honesty_history`` on
  the deterministic-Coach primary path.

These are pure-Python unit tests — no SDK invocations, no live pytest
runs against the host repo.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, TurnRecord
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.coach_verification import (
    Discrepancy,
    HonestyVerification,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidationResult,
    CoachValidator,
    IndependentTestResult,
    QualityGateStatus,
    RequirementsValidation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orchestrator() -> AutoBuildOrchestrator:
    """Construct a minimal AutoBuildOrchestrator for _record_honesty tests.

    Bypasses ``__init__`` so we don't need a git repo or worktree manager —
    the consumer guard only touches ``self._honesty_history``.
    """
    orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orch._honesty_history = []
    return orch


def _make_coach_result(
    report: Dict[str, Any], success: bool = True
) -> AgentInvocationResult:
    """Build a Coach AgentInvocationResult around an arbitrary report dict."""
    return AgentInvocationResult(
        task_id="TASK-FIX-7E3F",
        turn=1,
        agent_type="coach",
        success=success,
        report=report,
        duration_seconds=0.1,
    )


def _make_turn_record(
    report: Dict[str, Any], coach_success: bool = True, turn: int = 1
) -> TurnRecord:
    """Wrap a Coach report in a minimal TurnRecord."""
    coach_result = _make_coach_result(report, success=coach_success)
    return TurnRecord(
        turn=turn,
        player_result=AgentInvocationResult(
            task_id="TASK-FIX-7E3F",
            turn=turn,
            agent_type="player",
            success=True,
            report={},
            duration_seconds=0.0,
        ),
        coach_result=coach_result,
        decision="feedback" if not coach_success else "approve",
        feedback=None,
        timestamp="2026-05-06T18:00:00Z",
    )


# ---------------------------------------------------------------------------
# AC-7: Consumer-side guard
# ---------------------------------------------------------------------------


class TestRecordHonestyConsumerGuard:
    """AC-7: ``_record_honesty`` survives every legitimate report shape."""

    def test_handles_none_payload_without_crash(self):
        """Regression case — key present, value None.

        This is the exact shape that crashed every deterministic-Coach turn
        between b9a45694 and this fix: the producer wrote
        ``{"honesty_verification": None}`` and the consumer used
        ``.get("honesty_verification", {})`` which returns None (because the
        key IS present). ``None.get("honesty_score")`` then raised.
        """
        orch = _make_orchestrator()
        turn_record = _make_turn_record({"honesty_verification": None})

        orch._record_honesty(turn_record)

        # Early-return path: history must not grow.
        assert orch._honesty_history == []

    def test_handles_missing_key_for_legacy_compat(self):
        """Pre-regression shape — key absent entirely.

        Before TASK-AB-FIX-INVAB1 the deterministic Coach never wrote
        ``honesty_verification`` to the report at all. The new guard must
        treat that case identically to ``value is None``: early-return,
        no crash, no history mutation.
        """
        orch = _make_orchestrator()
        turn_record = _make_turn_record({})  # key absent

        orch._record_honesty(turn_record)

        assert orch._honesty_history == []

    def test_records_score_when_payload_populated(self):
        """Happy path — populated dict (post-Layer-C producer)."""
        orch = _make_orchestrator()
        turn_record = _make_turn_record(
            {
                "honesty_verification": {
                    "verified": True,
                    "honesty_score": 0.92,
                    "discrepancy_count": 0,
                }
            }
        )

        orch._record_honesty(turn_record)

        assert orch._honesty_history == [0.92]

    def test_short_circuits_when_coach_failed(self):
        """Pre-existing guard at autobuild.py:4372 must still fire.

        When ``coach_result.success`` is False, the function must early-return
        before touching ``report`` at all — the report may be entirely empty
        in error cases.
        """
        orch = _make_orchestrator()
        # Even a payload that would otherwise score 0.5 must be ignored when
        # the Coach itself failed to invoke.
        turn_record = _make_turn_record(
            {"honesty_verification": {"honesty_score": 0.5}},
            coach_success=False,
        )

        orch._record_honesty(turn_record)

        assert orch._honesty_history == []

    def test_records_score_when_payload_omits_honesty_score(self):
        """Defensive default — ``.get('honesty_score', 1.0)`` still applies."""
        orch = _make_orchestrator()
        turn_record = _make_turn_record(
            {"honesty_verification": {"verified": True, "discrepancy_count": 0}}
        )

        orch._record_honesty(turn_record)

        assert orch._honesty_history == [1.0]

    def test_logs_low_average_after_three_low_turns(self, caplog):
        """Sustained-low warning at autobuild.py:4384 must still fire post-fix."""
        import logging

        orch = _make_orchestrator()
        for score in (0.5, 0.6, 0.5):
            turn_record = _make_turn_record(
                {"honesty_verification": {"honesty_score": score}}
            )
            with caplog.at_level(logging.WARNING):
                orch._record_honesty(turn_record)

        assert any(
            "Player honesty concern" in record.message for record in caplog.records
        ), f"Expected sustained-low warning, got: {[r.message for r in caplog.records]}"


# ---------------------------------------------------------------------------
# AC-8: Producer-side threading on coach_validator helpers
# ---------------------------------------------------------------------------


def _populated_honesty() -> HonestyVerification:
    """Build an HV instance the producer should thread through."""
    return HonestyVerification(
        verified=True,
        discrepancies=[],
        honesty_score=0.95,
        resolved_paths=[],
    )


def _hv_with_discrepancy() -> HonestyVerification:
    """Build an HV instance that names a real discrepancy (for round-trip)."""
    return HonestyVerification(
        verified=False,
        discrepancies=[
            Discrepancy(
                claim_type="file_existence",
                player_claim="src/never_created.py",
                actual_value="not on disk",
                severity="critical",
            )
        ],
        honesty_score=0.4,
        resolved_paths=[],
    )


@pytest.fixture
def validator(tmp_path: Path) -> CoachValidator:
    """A CoachValidator rooted in a throwaway worktree.

    The producer-helper tests don't exercise the full ``validate(...)`` path,
    so the worktree just needs to exist.
    """
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return CoachValidator(str(worktree))


class TestCoachValidatorProducerThreading:
    """AC-8: every helper that builds a CoachValidationResult must thread
    ``honesty_verification`` so ``to_dict()`` round-trips a real dict, not
    a None silently swallowed by the consumer guard."""

    # The seven decision shapes named in the AC-8 spec map to these helpers:
    #   feedback_from_gates        → _feedback_from_gates path
    #   feedback_test_failure      → _feedback_result with category=test_verification
    #   feedback_missing_req       → _feedback_result with category=missing_requirement
    #   feedback_zero_test         → _feedback_result with category=zero-test
    #   feedback_bdd_failed        → _feedback_result with category=bdd_failure
    #   feedback_seam_missing      → _feedback_result with category=seam_tests
    #   approve                    → direct CoachValidationResult constructor
    #
    # AC-8 calls for parametrising over those shapes; the underlying
    # producer wiring is identical (helper accepts kwarg, passes to ctor),
    # so we exercise every helper directly with the threaded payload.

    @pytest.mark.parametrize(
        "shape",
        [
            "feedback_test_failure",
            "feedback_missing_req",
            "feedback_zero_test",
            "feedback_bdd_failed",
            "feedback_seam_missing",
        ],
    )
    def test_feedback_result_threads_honesty_verification(
        self, validator: CoachValidator, shape: str
    ) -> None:
        """``_feedback_result`` must accept and thread the kwarg."""
        hv = _populated_honesty()

        result = validator._feedback_result(
            task_id="TASK-FIX-7E3F",
            turn=1,
            issues=[
                {
                    "severity": "must_fix",
                    "category": shape,
                    "description": f"shape={shape}",
                }
            ],
            rationale=f"driving shape {shape}",
            honesty_verification=hv,
        )

        assert result.honesty_verification is hv

        # to_dict round-trip — this is what _record_honesty consumes.
        round_tripped = result.to_dict()["honesty_verification"]
        assert round_tripped is not None, (
            f"to_dict() lost honesty_verification for shape={shape}"
        )
        assert round_tripped["verified"] is True
        assert round_tripped["honesty_score"] == 0.95
        assert round_tripped["discrepancy_count"] == 0

    def test_feedback_from_gates_threads_honesty_verification(
        self, validator: CoachValidator
    ) -> None:
        """``_feedback_from_gates`` must accept and thread the kwarg."""
        hv = _hv_with_discrepancy()
        gates = QualityGateStatus(
            tests_required=True,
            tests_passed=False,
            coverage_required=True,
            coverage_met=True,
            arch_review_required=False,
            arch_review_passed=True,
            plan_audit_required=False,
            plan_audit_passed=True,
        )
        task_work_results = {
            "quality_gates": {
                "tests_passed": 0,
                "tests_failed": 3,
                "all_passed": False,
            }
        }

        result = validator._feedback_from_gates(
            task_id="TASK-FIX-7E3F",
            turn=1,
            gates=gates,
            task_work_results=task_work_results,
            honesty_verification=hv,
        )

        assert result.honesty_verification is hv
        round_tripped = result.to_dict()["honesty_verification"]
        assert round_tripped == {
            "verified": False,
            "honesty_score": 0.4,
            "discrepancy_count": 1,
            "resolved_paths": [],
        }

    def test_approve_path_constructor_accepts_honesty_verification(self) -> None:
        """The approve-path ``CoachValidationResult(...)`` direct ctor must
        accept ``honesty_verification`` (AC-5). Constructing it directly
        is the cleanest test — the call site at coach_validator.py:1504 is
        exercised by the integration test (AC-9)."""
        hv = _populated_honesty()
        result = CoachValidationResult(
            task_id="TASK-FIX-7E3F",
            turn=1,
            decision="approve",
            quality_gates=None,
            independent_tests=None,
            requirements=None,
            issues=[],
            rationale="approve path",
            honesty_verification=hv,
        )
        assert result.honesty_verification is hv
        assert result.to_dict()["honesty_verification"]["honesty_score"] == 0.95

    def test_pre_verify_honesty_paths_legitimately_None(self) -> None:
        """AC-8: at coach_validator.py:776/805/828 the helpers run BEFORE
        ``_verify_honesty`` has been called, so ``honesty_verification``
        legitimately defaults to None. The consumer guard must still
        handle that without crashing."""
        # Construct a CoachValidationResult that mirrors the
        # invalid-task-type / operator-handoff / missing-results paths.
        result = CoachValidationResult(
            task_id="TASK-FIX-7E3F",
            turn=1,
            decision="feedback",
            quality_gates=None,
            independent_tests=None,
            requirements=None,
            issues=[
                {
                    "severity": "must_fix",
                    "category": "invalid_task_type",
                    "description": "pre-_verify_honesty short-circuit",
                }
            ],
            rationale="pre-honesty short-circuit",
            # honesty_verification omitted → defaults to None (correct here).
        )
        assert result.honesty_verification is None
        assert result.to_dict()["honesty_verification"] is None

        # Now drive the consumer guard with a TurnRecord built from this
        # report. Must NOT crash, must NOT advance history.
        orch = _make_orchestrator()
        turn_record = _make_turn_record(result.to_dict())
        orch._record_honesty(turn_record)
        assert orch._honesty_history == []
