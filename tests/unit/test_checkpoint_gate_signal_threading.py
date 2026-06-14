"""
Regression tests for TASK-AB-CKPTGATE01.

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

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    IndependentTestResult,
    QualityGateStatus,
)
from guardkit.orchestrator.worktree_checkpoints import (
    Checkpoint,
    WorktreeCheckpointManager,
)


# ============================================================================
# Fixtures and builders
# ============================================================================


@pytest.fixture
def orchestrator():
    """AutoBuildOrchestrator for exercising the merge helper + extractor."""
    return AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=5)


@pytest.fixture
def mock_git_executor():
    """Git executor that returns a stable hash for every command."""
    executor = Mock()
    executor.execute.return_value = Mock(returncode=0, stdout="deadbeef\n", stderr="")
    return executor


@pytest.fixture
def checkpoint_manager(tmp_path, mock_git_executor):
    """Checkpoint manager backed by a mock git executor (no evidence repos)."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    (worktree_path / ".guardkit" / "autobuild" / "TASK-CKPTGATE-001").mkdir(
        parents=True
    )
    return WorktreeCheckpointManager(
        worktree_path=worktree_path,
        task_id="TASK-CKPTGATE-001",
        git_executor=mock_git_executor,
    )


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
    gate_tests_passed: bool | None = True,
    indep_tests_passed: bool | None = True,
    indep_signal_absent: bool = False,
    include_gates: bool = True,
    include_independent: bool = True,
) -> CoachEvidenceBundle:
    """Construct a real CoachEvidenceBundle carrying the requested test signal."""
    gates = None
    if include_gates and gate_tests_passed is not None:
        gates = QualityGateStatus(
            tests_passed=gate_tests_passed,
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        )
    independent = None
    if include_independent:
        independent = IndependentTestResult(
            tests_passed=bool(indep_tests_passed) and not indep_signal_absent,
            test_command="pytest -q",
            test_output_summary="5 passed" if indep_tests_passed else "1 failed",
            duration_seconds=1.0,
            signal_absent=indep_signal_absent,
        )
    return CoachEvidenceBundle(
        honesty=Mock(),  # not read by the merge helper
        quality_gates=gates,
        independent_tests=independent,
    )


def _turn_record(report: dict) -> Mock:
    """A successful Coach turn record wrapping the given report."""
    turn_record = Mock()
    turn_record.coach_result = Mock()
    turn_record.coach_result.success = True
    turn_record.coach_result.report = report
    return turn_record


# ============================================================================
# AC-001 / AC-006: passing gate signal threaded → recorded as pass
# ============================================================================


class TestGateSignalThreadedAsPass:
    def test_llm_report_without_validation_results_becomes_pass(self, orchestrator):
        """FEAT-9DDE reproducer: pre-merge the report extracts to UNKNOWN; after
        merging a tests=True bundle it extracts to True (pass)."""
        report = _llm_coach_report()
        # Before the merge: no validation_results → UNKNOWN.
        assert orchestrator._extract_tests_passed(_turn_record(report)) is None

        merged = orchestrator._merge_evidence_test_signal_into_report(
            report, _bundle(gate_tests_passed=True)
        )
        assert (
            merged["validation_results"]["quality_gates"]["tests_passed"] is True
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
# AC-002: threaded pass is a find_last_passing_checkpoint rollback target
# ============================================================================


class TestRollbackTargetRestored:
    def test_threaded_pass_is_rollback_target(
        self, orchestrator, checkpoint_manager
    ):
        """End-to-end: merge tests=True → extract True → checkpoint pass →
        find_last_passing_checkpoint returns it."""
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(), _bundle(gate_tests_passed=True)
        )
        signal = orchestrator._extract_tests_passed(_turn_record(merged))
        assert signal is True

        checkpoint_manager.create_checkpoint(turn=1, tests_passed=signal, test_count=5)
        # A later UNKNOWN turn must not erase the rollback target.
        checkpoint_manager.create_checkpoint(turn=2, tests_passed=None, test_count=0)

        assert checkpoint_manager.find_last_passing_checkpoint() == 1

    def test_without_threading_there_is_no_rollback_target(
        self, orchestrator, checkpoint_manager
    ):
        """Demonstrates the residual gap this task closes: an unmerged
        LLM-Coach pass turn is UNKNOWN and is NOT a rollback target."""
        signal = orchestrator._extract_tests_passed(
            _turn_record(_llm_coach_report())
        )
        assert signal is None
        checkpoint_manager.create_checkpoint(turn=1, tests_passed=signal, test_count=0)
        assert checkpoint_manager.find_last_passing_checkpoint() is None


# ============================================================================
# AC-003: absent independent signal still resolves to UNKNOWN
# ============================================================================


class TestAbsenceOfFailurePreserved:
    def test_absent_independent_overrides_passing_gate(self, orchestrator):
        """signal_absent=True must win over quality_gates.tests_passed=True
        (the regression guard for TASK-FIX-CKPTTESTRED01)."""
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(),
            _bundle(gate_tests_passed=True, indep_signal_absent=True),
        )
        # Both signals are present in the merged report ...
        assert (
            merged["validation_results"]["quality_gates"]["tests_passed"] is True
        )
        assert (
            merged["validation_results"]["independent_tests"]["signal_absent"]
            is True
        )
        # ... but signal_absent is read first → UNKNOWN.
        assert orchestrator._extract_tests_passed(_turn_record(merged)) is None

    def test_absent_independent_with_no_gates_is_unknown(self, orchestrator):
        """An absent independent signal with no quality_gates → UNKNOWN."""
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(),
            _bundle(include_gates=False, indep_signal_absent=True),
        )
        assert orchestrator._extract_tests_passed(_turn_record(merged)) is None


# ============================================================================
# AC-004: genuine ran-and-failed gate stays False and feeds pollution tally
# ============================================================================


class TestGenuineFailurePreserved:
    def test_failed_gate_recorded_as_false(self, orchestrator):
        """tests=False from the bundle is threaded and extracts to False."""
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(decision="feedback"),
            _bundle(gate_tests_passed=False, indep_tests_passed=False),
        )
        assert orchestrator._extract_tests_passed(_turn_record(merged)) is False

    def test_three_threaded_failures_still_stall(
        self, orchestrator, checkpoint_manager
    ):
        """Three genuine ran-and-failed turns still trigger rollback."""
        for turn in (1, 2, 3):
            merged = orchestrator._merge_evidence_test_signal_into_report(
                _llm_coach_report(decision="feedback"),
                _bundle(gate_tests_passed=False, indep_tests_passed=False),
            )
            signal = orchestrator._extract_tests_passed(_turn_record(merged))
            assert signal is False
            checkpoint_manager.create_checkpoint(
                turn=turn, tests_passed=signal, test_count=5
            )
        assert checkpoint_manager.should_rollback() is True


# ============================================================================
# Non-clobbering + no-op guards
# ============================================================================


class TestNonClobberAndNoOp:
    def test_existing_quality_gate_not_overwritten(self, orchestrator):
        """A report already carrying quality_gates.tests_passed=False wins over
        a bundle that says True (non-clobbering)."""
        report = _llm_coach_report()
        report["validation_results"] = {"quality_gates": {"tests_passed": False}}
        merged = orchestrator._merge_evidence_test_signal_into_report(
            report, _bundle(gate_tests_passed=True)
        )
        assert (
            merged["validation_results"]["quality_gates"]["tests_passed"] is False
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
        """A bundle with neither gates nor independent tests is harmless: the
        report still extracts to UNKNOWN."""
        merged = orchestrator._merge_evidence_test_signal_into_report(
            _llm_coach_report(),
            _bundle(include_gates=False, include_independent=False),
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
