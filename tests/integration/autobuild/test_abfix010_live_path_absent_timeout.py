"""
TASK-ABFIX-010 — LIVE-PATH integration test.

The unit reproducers in ``tests/unit/test_abfix010_absent_reconciliation.py`` call
``verify_quality_gates`` directly — the *legacy* ``CoachValidator.validate()``
entry. The PRIMARY live Coach path is
``gather_evidence() → CoachEvidenceBundle → _merge_evidence_test_signal_into_report
→ _extract_tests_passed → checkpoint → should_rollback`` (the ``validate()`` path
is an explicit non-primary fallback — see ``autobuild.py`` "MUST NOT fall back to
validate()"). This test drives that live chain end-to-end, deterministically, to
prove the absent-Coach-test-timeout false-RED (FEAT-FMDR / TASK-FMDR-001) is
closed on the path the orchestrator actually uses.

The "a Coach-isolated pytest timeout yields ``IndependentTestResult.signal_absent
= True``" leg is taken as given here — it is covered by the run_independent_tests /
runtime-parity / signal-absent-classifier unit tests. This test starts from that
bundle and exercises the REAL merge bridge + REAL ``_extract_tests_passed`` + REAL
checkpoint pollution detector.

See .claude/rules/absence-must-survive-every-reconciliation-layer.md
"""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

_test_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.worktree_checkpoints import WorktreeCheckpointManager
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    IndependentTestResult,
    QualityGateStatus,
)


@pytest.fixture
def orchestrator():
    return AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=5)


@pytest.fixture
def checkpoint_manager(tmp_path):
    git_executor = Mock()
    git_executor.execute.return_value = Mock(returncode=0, stdout="deadbeef\n", stderr="")
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    (worktree_path / ".guardkit" / "autobuild" / "TASK-FMDR-001").mkdir(parents=True)
    return WorktreeCheckpointManager(
        worktree_path=worktree_path,
        task_id="TASK-FMDR-001",
        git_executor=git_executor,
    )


def _absent_timeout_bundle() -> CoachEvidenceBundle:
    """The bundle gather_evidence produces on a Coach-isolated pytest TIMEOUT.

    The exact FMDR-001 shape: the deterministic quality gate (and the Player's
    self-report) say tests passed, but the Coach's own independent run TIMED OUT
    and produced no verdict → signal_absent=True (tests_passed forced False).
    """
    return CoachEvidenceBundle(
        honesty=None,
        quality_gates=QualityGateStatus(
            tests_passed=True,  # gate/Player claim green (the false-green)
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        ),
        independent_tests=IndependentTestResult(
            tests_passed=False,
            test_command="pytest <files> -v --tb=short",
            test_output_summary="Isolated test execution timed out after 60s",
            duration_seconds=60.0,
            signal_absent=True,  # the absent oracle signal
        ),
    )


def _llm_coach_report() -> dict:
    """The live LLM-Coach report shape: NO validation_results block."""
    return {
        "task_id": "TASK-FMDR-001",
        "turn": 1,
        "decision": "feedback",
        "issues": [],
        "criteria_verification": [],
        "rationale": "feedback turn",
    }


def _turn_record_from_report(report: dict) -> Mock:
    tr = Mock()
    tr.coach_result = Mock()
    tr.coach_result.success = True
    tr.coach_result.report = report
    return tr


# ---------------------------------------------------------------------------
# The live-path chain
# ---------------------------------------------------------------------------


def test_merge_bridge_carries_signal_absent_into_report(orchestrator):
    """The REAL merge bridge threads bundle.independent_tests.signal_absent into
    the LLM-Coach report (which otherwise omits validation_results)."""
    report = _llm_coach_report()
    merged = orchestrator._merge_evidence_test_signal_into_report(
        report, _absent_timeout_bundle()
    )
    indep = merged["validation_results"]["independent_tests"]
    assert indep["signal_absent"] is True


def test_live_path_absent_timeout_extracts_as_unknown(orchestrator):
    """End-to-end live leg: a timeout bundle → merge → _extract_tests_passed → None.

    Critically, signal_absent is read BEFORE quality_gates.tests_passed, so the
    deterministic gate's green verdict does NOT override the absent signal
    (absence-of-failure: absent is neither pass nor fail)."""
    merged = orchestrator._merge_evidence_test_signal_into_report(
        _llm_coach_report(), _absent_timeout_bundle()
    )
    signal = orchestrator._extract_tests_passed(_turn_record_from_report(merged))
    assert signal is None  # NOT True (gate green), NOT False (counted failure)


def test_three_live_path_timeouts_do_not_stall(orchestrator, checkpoint_manager):
    """The FMDR-001 reproducer on the LIVE path: three consecutive Coach-isolated
    timeouts must NOT trip the context-pollution guard (no unrecoverable_stall)."""
    for turn in (1, 2, 3):
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(), _absent_timeout_bundle()
        )
        signal = orchestrator._extract_tests_passed(_turn_record_from_report(merged))
        assert signal is None
        checkpoint_manager.create_checkpoint(turn=turn, tests_passed=signal)

    assert checkpoint_manager.should_rollback() is False


def test_live_path_genuine_failure_still_stalls(orchestrator, checkpoint_manager):
    """No-weakening guard on the live path: three GENUINE ran-and-failed turns
    (signal_absent=False, tests_passed=False) still stall — only the absent
    signal is excused, never a real failure."""
    bundle = CoachEvidenceBundle(
        honesty=None,
        quality_gates=QualityGateStatus(
            tests_passed=False,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        ),
        independent_tests=IndependentTestResult(
            tests_passed=False,
            test_command="pytest",
            test_output_summary="2 failed",
            duration_seconds=1.0,
            signal_absent=False,  # ran and FAILED — a real verdict
        ),
    )
    for turn in (1, 2, 3):
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(), bundle
        )
        signal = orchestrator._extract_tests_passed(_turn_record_from_report(merged))
        assert signal is False
        checkpoint_manager.create_checkpoint(turn=turn, tests_passed=signal)

    assert checkpoint_manager.should_rollback() is True
