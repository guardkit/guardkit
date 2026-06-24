"""
TASK-ABFIX-010 reproducers — keep an absent test signal as UNKNOWN (None)
through every reconciliation/synthesis/serialization layer, not coerced to False.

The originating defect (FEAT-FMDR): a Coach isolated-pytest TIMEOUT (tests_run=0,
an ABSENT signal) was coerced to an explicit test FAILURE; three such turns
tripped the context-pollution guard and killed a converging task. CKPTTESTRED01
fixed the terminal guard; this task carries the absent->None invariant through
the layers upstream of it.

Covers:
- W1: verify_quality_gates honours ``reconciled_absent`` -> tests_passed=None
  (UNKNOWN), all_gates_passed=False (does NOT auto-approve), incl. the
  tests_failed==0 false-GREEN guard.
- W1 regression: a genuine ran-and-failed verdict still -> tests_passed=False;
  the pre-existing TASK-FIX-64EE fall-through is untouched.
- W1: QualityGateStatus tri-state (None appended to required_gates, not skipped).
- W2: CoachValidationResult.to_dict() serialises independent_tests.signal_absent
  and a None quality_gates.tests_passed, so the checkpoint's
  _extract_tests_passed can decouple the absent signal to None.

See .claude/rules/absence-must-survive-every-reconciliation-layer.md

Coverage Target: >=85%
"""
import sys
from pathlib import Path

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.quality_gates import CoachValidator, QualityGateStatus
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidationResult,
    IndependentTestResult,
)


@pytest.fixture
def tmp_worktree(tmp_path):
    wt = tmp_path / "worktrees" / "TASK-ABFIX-010"
    wt.mkdir(parents=True)
    return wt


# ============================================================================
# W1: verify_quality_gates honours reconciled_absent
# ============================================================================


class TestVerifyQualityGatesReconciledAbsent:
    def test_reconciled_absent_yields_tests_passed_none(self, tmp_worktree):
        """T1a: an absent reconciled signal -> tests_passed is None (UNKNOWN)."""
        twr = {
            "quality_gates": {
                "all_passed": None,
                "tests_passing": None,
                "tests_passed": None,
                "reconciled_absent": True,
                "reconciled_from_specialist": True,
            },
            "code_review": {"score": 75},
        }
        status = CoachValidator(str(tmp_worktree)).verify_quality_gates(twr)
        assert status.tests_passed is None
        # UNKNOWN must NOT auto-approve (absence-of-failure: absent != pass).
        assert status.all_gates_passed is False

    def test_reconciled_absent_with_tests_failed_zero_is_not_green(self, tmp_worktree):
        """T1c (false-GREEN guard): reconciled_absent wins over tests_failed==0.

        The absent phase-4 block carries tests_failed=0. Without the
        reconciled_absent short-circuit, verify_quality_gates would resolve
        tests_passed = (0 == 0) = True — a false-green. It must stay None.
        """
        twr = {
            "quality_gates": {
                "all_passed": None,
                "tests_passed": None,
                "tests_failed": 0,  # the trap
                "reconciled_absent": True,
            },
            "code_review": {"score": 75},
        }
        status = CoachValidator(str(tmp_worktree)).verify_quality_gates(twr)
        assert status.tests_passed is None  # NOT True
        assert status.all_gates_passed is False

    def test_genuine_failure_still_false(self, tmp_worktree):
        """T1b regression: a ran-and-failed verdict (no reconciled_absent) -> False."""
        twr = {
            "quality_gates": {
                "all_passed": False,
                "tests_passed": 10,
                "tests_failed": 3,
                "coverage_met": True,
            },
            "code_review": {"score": 75},
        }
        status = CoachValidator(str(tmp_worktree)).verify_quality_gates(twr)
        assert status.tests_passed is False

    def test_no_reconciled_absent_preserves_legacy_fallthrough(self, tmp_worktree):
        """Without reconciled_absent, all_passed=None + tests_failed=0 still -> True.

        The pre-existing TASK-FIX-64EE fall-through must be untouched — the new
        elif fires ONLY on the reconciled_absent marker.
        """
        twr = {
            "quality_gates": {
                "all_passed": None,
                "tests_passed": 0,
                "tests_failed": 0,
            },
            "code_review": {"score": 75},
        }
        status = CoachValidator(str(tmp_worktree)).verify_quality_gates(twr)
        assert status.tests_passed is True


# ============================================================================
# W1: QualityGateStatus tri-state (append None, do NOT skip)
# ============================================================================


class TestQualityGateStatusTriState:
    def test_none_tests_passed_does_not_auto_approve(self):
        """tests_passed=None is APPENDED to required_gates -> all_gates_passed False.

        Skipping None (the rejected reviewer R2) would let the OTHER gates
        approve despite absent tests — a gate-level false-green.
        """
        s = QualityGateStatus(
            tests_passed=None,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        )
        assert s.all_gates_passed is False

    def test_all_true_still_approves(self):
        s = QualityGateStatus(
            tests_passed=True,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        )
        assert s.all_gates_passed is True


# ============================================================================
# W2: serialization decoupling (signal_absent + None tests_passed survive to_dict)
# ============================================================================


class TestToDictSerializesAbsent:
    def test_signal_absent_and_none_tests_passed_serialized(self):
        """T4: to_dict() carries independent_tests.signal_absent and a None
        quality_gates.tests_passed, so the checkpoint's _extract_tests_passed
        can decouple the absent signal to None (it was dead-on-arrival before)."""
        result = CoachValidationResult(
            task_id="TASK-ABFIX-010",
            turn=1,
            decision="feedback",
            quality_gates=QualityGateStatus(
                tests_passed=None,
                coverage_met=True,
                arch_review_passed=True,
                plan_audit_passed=True,
            ),
            independent_tests=IndependentTestResult(
                tests_passed=False,
                test_command="pytest",
                test_output_summary="isolated test execution timed out",
                duration_seconds=60.0,
                signal_absent=True,
            ),
        )
        vr = result.to_dict()["validation_results"]
        assert vr["quality_gates"]["tests_passed"] is None
        assert vr["independent_tests"]["signal_absent"] is True
