"""
Regression tests for TASK-AB-CKPTGATE01.

Since the cull of 27 October 2026 the only test signal threaded is the
project's own test run (``independent_tests``); the quality-gate status, the
requirements rows and the Phase 4 counts the Player reported are gone, and
so is the checkpoint rollback they fed.

Thread the deterministic Coach gate test signal into the LLM-Coach report so a
genuinely-passing turn is recorded as ``pass`` (not ``unknown``).

TASK-FIX-CKPTTESTRED01 closed the checkpoint false-red by making the test
signal tri-state and treating an absent signal as ``UNKNOWN``. It deliberately
left a residual gap: the deterministic ``tests=True`` gate result was not
*threaded* into the LLM-Coach report, so a turn whose tests genuinely passed
was recorded as ``UNKNOWN`` rather than ``pass``. That cost
``find_last_passing_checkpoint`` a valid rollback target — a later real
pollution run could ``unrecoverable_stall`` with no target even though an
earlier turn was clean.

This task threads the authoritative gate signal from the Coach evidence bundle
into the returned ``coach_result.report`` via
``AutoBuildOrchestrator._merge_evidence_test_signal_into_report``, so the
checkpoint layer (``_extract_tests_passed``) reads the same oracle the gate
logged.

Invariants under guard:
- absence-of-failure (.claude/rules/absence-of-failure-is-not-success.md):
  an absent independent signal still resolves to UNKNOWN, never a pass.
- non-clobbering: a report already carrying validation_results is not
  overwritten.
- Coach read-only (feature-build-invariants.md FB-004): the merge is an
  orchestrator-side enrichment, never a Coach write.

Coverage Target: >=85%
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    IndependentTestResult,
)


# ============================================================================
# Fixtures and builders
# ============================================================================


@pytest.fixture
def orchestrator():
    """AutoBuildOrchestrator for exercising the merge helper + extractor."""
    return AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=5)


def _llm_coach_report(decision: str = "approve") -> dict:
    """An LLM-Coach report with NO validation_results (the run-5 shape).

    Mirrors the default LLM Coach verdict:
    {decision, issues, criteria_verification, rationale}.
    """
    return {
        "task_id": "TASK-CKPTGATE-001",
        "turn": 1,
        "decision": decision,
        "issues": [],
        "criteria_verification": [
            {"criterion_id": "AC-001", "result": "verified", "notes": "ok"},
        ],
        "rationale": "Implementation satisfies all acceptance criteria.",
    }


def _bundle(
    *,
    indep_tests_passed: bool | None = True,
    indep_signal_absent: bool = False,
    include_independent: bool = True,
) -> CoachEvidenceBundle:
    """Construct a real CoachEvidenceBundle carrying the requested test run."""
    independent = None
    if include_independent:
        independent = IndependentTestResult(
            tests_passed=bool(indep_tests_passed) and not indep_signal_absent,
            test_command="pytest -q",
            test_output_summary="5 passed" if indep_tests_passed else "1 failed",
            duration_seconds=1.0,
            signal_absent=indep_signal_absent,
        )
    return CoachEvidenceBundle(independent_tests=independent)


def _turn_record(report: dict) -> Mock:
    """A successful Coach turn record wrapping the given report."""
    turn_record = Mock()
    turn_record.coach_result = Mock()
    turn_record.coach_result.success = True
    turn_record.coach_result.report = report
    return turn_record


def _capture_state(orchestrator, report: dict, tmp_path: Path) -> dict:
    record = SimpleNamespace(
        turn=1,
        decision=report.get("decision", "feedback"),
        feedback="fix failures",
        player_result=None,
        coach_result=SimpleNamespace(success=True, report=report),
    )
    orchestrator._capture_turn_state(
        record,
        ["criterion"],
        task_id="TASK-CKPTGATE-001",
        worktree_path=tmp_path,
    )
    state_path = (
        tmp_path / ".guardkit/autobuild/TASK-CKPTGATE-001/turn_state_turn_1.json"
    )
    return json.loads(state_path.read_text())


# ============================================================================
# AC-001 / AC-006: the project's passing test run threaded → recorded as pass
# ============================================================================


class TestGateSignalThreadedAsPass:
    def test_llm_report_without_validation_results_becomes_pass(self, orchestrator):
        """FEAT-9DDE reproducer: pre-merge the report extracts to UNKNOWN; after
        merging a passing test run it extracts to True (pass)."""
        report = _llm_coach_report()
        # Before the merge: no validation_results → UNKNOWN.
        assert orchestrator._extract_tests_passed(_turn_record(report)) is None

        merged = orchestrator._merge_evidence_test_signal_into_report(
            report, _bundle(indep_tests_passed=True)
        )
        assert (
            merged["validation_results"]["independent_tests"]["tests_passed"]
            is True
        )
        assert orchestrator._extract_tests_passed(_turn_record(merged)) is True

    def test_merge_returns_same_report_object(self, orchestrator):
        """The helper mutates and returns the same report object."""
        report = _llm_coach_report()
        merged = orchestrator._merge_evidence_test_signal_into_report(
            report, _bundle()
        )
        assert merged is report


# ============================================================================
# AC-003: absent independent signal still resolves to UNKNOWN
# ============================================================================


class TestAbsenceOfFailurePreserved:
    def test_absent_independent_overrides_a_reported_pass(self, orchestrator):
        """signal_absent=True wins over a quality_gates.tests_passed=True the
        report already carried (the regression guard for
        TASK-FIX-CKPTTESTRED01)."""
        report = _llm_coach_report()
        report["validation_results"] = {"quality_gates": {"tests_passed": True}}
        merged = orchestrator._merge_evidence_test_signal_into_report(
            report, _bundle(indep_signal_absent=True)
        )
        assert (
            merged["validation_results"]["independent_tests"]["signal_absent"]
            is True
        )
        # signal_absent is read first → UNKNOWN.
        assert orchestrator._extract_tests_passed(_turn_record(merged)) is None

    def test_absent_independent_is_unknown(self, orchestrator):
        """An absent independent signal on its own → UNKNOWN."""
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(),
            _bundle(indep_signal_absent=True),
        )
        assert orchestrator._extract_tests_passed(_turn_record(merged)) is None


# ============================================================================
# AC-004: a genuine ran-and-failed run stays False
# ============================================================================


class TestGenuineFailurePreserved:
    def test_failed_run_recorded_as_false(self, orchestrator):
        """A failed test run from the bundle is threaded and extracts to False."""
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(decision="feedback"),
            _bundle(indep_tests_passed=False),
        )
        assert orchestrator._extract_tests_passed(_turn_record(merged)) is False


# ============================================================================
# Non-clobbering + no-op guards
# ============================================================================


class TestNonClobberAndNoOp:
    def test_existing_independent_result_not_overwritten(self, orchestrator):
        """A report already carrying independent_tests.tests_passed=False wins
        over a bundle that says True (non-clobbering)."""
        report = _llm_coach_report()
        report["validation_results"] = {
            "independent_tests": {"tests_passed": False}
        }
        merged = orchestrator._merge_evidence_test_signal_into_report(
            report, _bundle(indep_tests_passed=True)
        )
        assert (
            merged["validation_results"]["independent_tests"]["tests_passed"]
            is False
        )
        assert orchestrator._extract_tests_passed(_turn_record(merged)) is False

    def test_none_bundle_is_noop(self, orchestrator):
        """A None bundle leaves the report untouched (partial-rollout guard)."""
        report = _llm_coach_report()
        merged = orchestrator._merge_evidence_test_signal_into_report(report, None)
        assert merged is report
        assert "validation_results" not in report

    def test_none_report_is_noop(self, orchestrator):
        """A None report returns None without raising."""
        assert (
            orchestrator._merge_evidence_test_signal_into_report(None, _bundle())
            is None
        )

    def test_bundle_without_signals_creates_empty_validation_results(
        self, orchestrator
    ):
        """A bundle with no independent test run is harmless: the report
        still extracts to UNKNOWN."""
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(),
            _bundle(include_independent=False),
        )
        assert orchestrator._extract_tests_passed(_turn_record(merged)) is None

    def test_verdict_fields_are_read_only(self, orchestrator):
        """The merge must not touch decision/issues/criteria_verification
        (Coach read-only invariant; the helper enriches only
        validation_results)."""
        report = _llm_coach_report(decision="approve")
        original_decision = report["decision"]
        original_issues = report["issues"]
        original_criteria = report["criteria_verification"]
        orchestrator._merge_evidence_test_signal_into_report(report, _bundle())
        assert report["decision"] == original_decision
        assert report["issues"] is original_issues
        assert report["criteria_verification"] is original_criteria


class TestEvidenceMetadataThreading:
    def test_count_comes_from_independent_summary(self, orchestrator):
        bundle = _bundle()
        bundle.independent_tests.test_output_summary = "849 passed in 12.3s"
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(),
            bundle,
        )

        assert orchestrator._extract_test_count(_turn_record(merged)) == 849

    def test_absent_signal_never_manufactures_count_from_summary(self, orchestrator):
        bundle = _bundle(indep_signal_absent=True)
        bundle.independent_tests.test_output_summary = "849 passed in 12.3s"
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(),
            bundle,
        )

        assert orchestrator._extract_test_count(_turn_record(merged)) == 0

    def test_green_boolean_without_count_stays_zero(self, orchestrator):
        report = _llm_coach_report()
        report["validation_results"] = {"tests_passed": True}

        assert orchestrator._extract_test_count(_turn_record(report)) == 0

    def test_green_tests_do_not_manufacture_criteria(self, orchestrator):
        report = _llm_coach_report()
        report["criteria_verification"] = []
        merged = orchestrator._merge_evidence_test_signal_into_report(
            report,
            _bundle(),
        )

        assert orchestrator._criteria_verifications_from_report(merged) == []

    def test_existing_metadata_is_not_overwritten(self, orchestrator):
        report = _llm_coach_report()
        report["criteria_verification"] = []
        report["validation_results"] = {
            "tests": {"tests_run": 7},
            "requirements": {
                "criteria_total": 1,
                "criteria_met": 0,
                "criteria_results": [
                    {
                        "criterion_id": "AC-001",
                        "result": "rejected",
                        "status": "rejected",
                    }
                ],
            },
        }

        merged = orchestrator._merge_evidence_test_signal_into_report(
            report,
            _bundle(),
        )

        assert merged["validation_results"]["tests"]["tests_run"] == 7
        assert merged["validation_results"]["requirements"]["criteria_total"] == 1
        assert len(orchestrator._criteria_verifications_from_report(merged)) == 1


class TestPersistedEvidenceMetadata:
    def test_legacy_criteria_survive_turn_state(
        self, orchestrator, tmp_path
    ):
        report = {
            "decision": "feedback",
            "acceptance_criteria_verification": {
                "criteria_results": [
                    {
                        "criterion_id": "AC-001",
                        "status": "verified",
                        "result": "verified",
                    }
                ]
            },
        }

        state = _capture_state(orchestrator, report, tmp_path)

        assert state["acceptance_criteria_status"] == {"AC-001": "verified"}

    def test_failed_actual_counts_survive_turn_state(
        self, orchestrator, tmp_path
    ):
        bundle = _bundle(indep_tests_passed=False)
        bundle.independent_tests.test_output_summary = "8 passed, 2 failed"
        merged = orchestrator._merge_evidence_test_signal_into_report(
            {"decision": "feedback", "criteria_verification": []},
            bundle,
        )

        state = _capture_state(orchestrator, merged, tmp_path)

        assert state["tests_passed"] == 8
        assert state["tests_failed"] == 2

    def test_nested_summary_preserves_mixed_outcomes(self, orchestrator):
        report = {
            "validation_results": {
                "independent_tests": {
                    "signal_absent": False,
                    "test_output_summary": "8 passed, 2 failed",
                }
            }
        }

        assert orchestrator._extract_test_outcome_counts(
            _turn_record(report)
        ) == (8, 2)

    def test_legacy_summary_preserves_mixed_outcomes(self, orchestrator):
        report = {
            "validation_results": {
                "test_output_summary": "8 passed, 2 failed",
            }
        }

        assert orchestrator._extract_test_outcome_counts(
            _turn_record(report)
        ) == (8, 2)

    def test_unparseable_failed_counts_remain_unknown(
        self, orchestrator, tmp_path
    ):
        bundle = _bundle(indep_tests_passed=False)
        bundle.independent_tests.test_output_summary = "unparseable output"
        merged = orchestrator._merge_evidence_test_signal_into_report(
            {"decision": "feedback", "criteria_verification": []},
            bundle,
        )

        state = _capture_state(orchestrator, merged, tmp_path)

        assert state["tests_passed"] is None
        assert state["tests_failed"] is None

    @pytest.mark.parametrize("count", [None, True, False, -1, "848", {}, []])
    def test_invalid_explicit_totals_are_not_counts(self, orchestrator, count):
        report = {"validation_results": {"tests": {"tests_run": count}}}

        assert orchestrator._extract_test_count(_turn_record(report)) == 0

    @pytest.mark.parametrize(
        ("summary", "expected_passed", "expected_failed"),
        [
            ("8 passed, 2 xfailed", 8, 0),
            ("8 passed, 2 skipped", 8, 0),
            ("8 passed, 2 errors", 8, 2),
        ],
    )
    def test_real_run_categories_persist_observed_outcomes(
        self,
        orchestrator,
        tmp_path,
        summary,
        expected_passed,
        expected_failed,
    ):
        bundle = _bundle()
        bundle.independent_tests.test_output_summary = summary
        merged = orchestrator._merge_evidence_test_signal_into_report(
            {"decision": "approve", "criteria_verification": []},
            bundle,
        )

        state = _capture_state(orchestrator, merged, tmp_path)

        assert state["tests_passed"] == expected_passed
        assert state["tests_failed"] == expected_failed

    @pytest.mark.parametrize("verdict", [True, False, None])
    def test_boolean_verdict_without_counts_is_unknown(
        self, orchestrator, verdict
    ):
        report = {
            "validation_results": {
                "tests": {"tests_passed": verdict},
                "quality_gates": {"tests_passed": verdict},
            }
        }

        assert orchestrator._extract_test_outcome_counts(
            _turn_record(report)
        ) == (None, None)

    def test_explicit_integer_outcomes_are_preserved(self, orchestrator):
        report = {
            "validation_results": {
                "tests": {"tests_run": 12, "tests_passed": 7, "tests_failed": 2}
            }
        }

        assert orchestrator._extract_test_outcome_counts(
            _turn_record(report)
        ) == (7, 2)
