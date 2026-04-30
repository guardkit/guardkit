"""Unit tests for Coach source-file contention detection (TASK-FIX-A7B2).

Tightens the parallel_contention conditional approval rule in
``coach_validator.py`` so it distinguishes source-file contention (real
correctness damage — two tasks edited the same source file in the same
wave) from infra contention (transient — partial __init__.py write race,
worktree mutations during isolated test run).

The TASK-ABFIX-005 isolation snapshot cannot defend against source-file
contention because both tasks committed inconsistent state to the
shared branch BEFORE either snapshot was taken — the snapshot captures
the already-corrupted file. Granting conditional approval in that case
masks the corruption and the failure surfaces only at wave-2
verification (the FEAT-70A4 study-tutor failure mode).

This test suite verifies:
- AC-001/AC-002: Coach reads peer wave edits and detects overlap with
  this task's own edits.
- AC-003: When overlap exists, the parallel_contention conditional
  approval branch does NOT fire — Coach returns feedback so the existing
  Player-Coach retry machinery serialises the next attempt.
- AC-004: When overlap is empty, the existing conditional approval path
  is intact (no regression on transient contention).
- AC-005: A synthetic two-task wave where both edited
  ``features/foo/test_foo.py`` produces a non-conditional-approved
  verdict for the failing task.
- AC-006 is verified in the existing ``test_coach_parallel_isolation.py``
  suite, which must continue to pass unchanged.

Coverage Target: >=85%
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    CoachValidationResult,
    IndependentTestResult,
    QualityGateStatus,
    RequirementsValidation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_validator(
    tmp_path: Path,
    *,
    wave_size: int = 2,
    peer_changed_files=None,
    task_id: str = "TASK-PRV-002",
) -> CoachValidator:
    """Create a minimal CoachValidator for source-file contention testing.

    Defaults to wave_size=2 (parallel) since the contention check only
    fires in parallel waves.
    """
    validator = CoachValidator(
        worktree_path=str(tmp_path),
        task_id=task_id,
        test_command="pytest tests/ -v",
        wave_size=wave_size,
        peer_changed_files=peer_changed_files,
    )
    validator._coach_test_execution = "subprocess"
    return validator


def _passing_gates() -> QualityGateStatus:
    return QualityGateStatus(
        tests_passed=True,
        coverage_met=True,
        arch_review_passed=True,
        plan_audit_passed=True,
    )


def _passing_requirements() -> RequirementsValidation:
    return RequirementsValidation(
        criteria_total=1,
        criteria_met=1,
        all_criteria_met=True,
    )


def _failing_test_result(
    output: str = "FAILED tests/test_x.py - AssertionError: assert 1 == 2",
) -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=False,
        test_command="pytest tests/ -v",
        test_output_summary="1 failed",
        duration_seconds=1.5,
        raw_output=output,
    )


def _task_work_results_with_files(
    files_created=None,
    files_modified=None,
) -> dict:
    """Build a passing task_work_results dict with optional file-edit lists."""
    return {
        "tests_passed": True,
        "coverage_pct": 85.0,
        "arch_review_score": 80,
        "plan_audit_violations": 0,
        "test_count": 5,
        "files_created": list(files_created or []),
        "files_modified": list(files_modified or []),
    }


def _run_validate(
    validator: CoachValidator,
    *,
    test_output: str = "FAILED tests/test_x.py - AssertionError: assert 1 == 2",
    task_work_results: dict = None,
) -> CoachValidationResult:
    """Execute validator.validate() with all internals mocked.

    Mocks read_quality_gate_results, verify_quality_gates,
    run_independent_tests, validate_requirements,
    _check_zero_test_anomaly, _check_seam_test_recommendation,
    _validate_consumer_context.
    """
    task = {
        "task_type": "feature",
        "acceptance_criteria": ["implement feature"],
    }
    failing_result = _failing_test_result(output=test_output)
    if task_work_results is None:
        task_work_results = _task_work_results_with_files()

    with patch.object(
        validator, "read_quality_gate_results", return_value=task_work_results
    ), patch.object(
        validator, "verify_quality_gates", return_value=_passing_gates()
    ), patch.object(
        validator, "run_independent_tests", return_value=failing_result
    ), patch.object(
        validator, "validate_requirements", return_value=_passing_requirements()
    ), patch.object(
        validator, "_check_zero_test_anomaly", return_value=[]
    ), patch.object(
        validator, "_check_seam_test_recommendation", return_value=[]
    ), patch.object(
        validator, "_validate_consumer_context", return_value=[]
    ):
        return validator.validate(validator.task_id or "TASK-PRV-002", 1, task)


# ---------------------------------------------------------------------------
# 1. _detect_source_file_contention helper (AC-001, AC-002)
# ---------------------------------------------------------------------------


class TestDetectSourceFileContention:
    """The helper must return overlap mapping when peer edits intersect own edits."""

    def test_no_peer_changed_files_returns_empty(self, tmp_path: Path) -> None:
        """No peer snapshot supplied → empty result, no contention."""
        validator = _make_validator(tmp_path, peer_changed_files=None)
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py"]
        )
        assert validator._detect_source_file_contention(results) == {}

    def test_empty_peer_dict_returns_empty(self, tmp_path: Path) -> None:
        """Peer dict configured but empty → empty result.

        First task to finish in a wave sees an empty peer dict; no contention.
        """
        validator = _make_validator(tmp_path, peer_changed_files={})
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py"]
        )
        assert validator._detect_source_file_contention(results) == {}

    def test_no_own_files_returns_empty(self, tmp_path: Path) -> None:
        """task_work_results has no files → empty result.

        Defensive: with nothing to compare, contention cannot be detected.
        """
        validator = _make_validator(
            tmp_path,
            peer_changed_files={"TASK-PRV-003": ["features/foo/test_foo.py"]},
        )
        results = _task_work_results_with_files()  # no files
        assert validator._detect_source_file_contention(results) == {}

    def test_disjoint_files_returns_empty(self, tmp_path: Path) -> None:
        """Peer edited different files → no contention (AC-004)."""
        validator = _make_validator(
            tmp_path,
            peer_changed_files={"TASK-PRV-003": ["features/bar/test_bar.py"]},
        )
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py"]
        )
        assert validator._detect_source_file_contention(results) == {}

    def test_overlap_returns_peer_and_files(self, tmp_path: Path) -> None:
        """One overlapping file → returns ``{peer_id: frozenset({file})}``."""
        validator = _make_validator(
            tmp_path,
            peer_changed_files={
                "TASK-PRV-003": ["features/foo/test_foo.py", "shared/utils.py"]
            },
        )
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py", "src/svc.py"]
        )
        overlaps = validator._detect_source_file_contention(results)
        assert overlaps == {"TASK-PRV-003": frozenset({"features/foo/test_foo.py"})}

    def test_multiple_peers_only_overlapping_returned(self, tmp_path: Path) -> None:
        """Two peers, only one overlaps → only the overlapping peer is returned."""
        validator = _make_validator(
            tmp_path,
            peer_changed_files={
                "TASK-PRV-003": ["features/foo/test_foo.py"],  # overlaps
                "TASK-PRV-004": ["features/bar/test_bar.py"],  # disjoint
            },
        )
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py"]
        )
        overlaps = validator._detect_source_file_contention(results)
        assert overlaps == {"TASK-PRV-003": frozenset({"features/foo/test_foo.py"})}

    def test_self_excluded_from_peers_at_construction(self, tmp_path: Path) -> None:
        """A peer entry keyed by self.task_id is filtered out at __init__.

        Defensive: callers that pass the full wave dict (including own entry)
        must not see their own files counted as a peer contention.
        """
        validator = _make_validator(
            tmp_path,
            task_id="TASK-PRV-002",
            peer_changed_files={
                "TASK-PRV-002": ["features/foo/test_foo.py"],  # self
                "TASK-PRV-003": ["features/foo/test_foo.py"],  # peer
            },
        )
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py"]
        )
        overlaps = validator._detect_source_file_contention(results)
        assert "TASK-PRV-002" not in overlaps
        assert overlaps == {"TASK-PRV-003": frozenset({"features/foo/test_foo.py"})}

    def test_files_created_also_counted(self, tmp_path: Path) -> None:
        """Overlap detection includes files_created, not just files_modified."""
        validator = _make_validator(
            tmp_path,
            peer_changed_files={"TASK-PRV-003": ["new_module.py"]},
        )
        results = _task_work_results_with_files(files_created=["new_module.py"])
        overlaps = validator._detect_source_file_contention(results)
        assert overlaps == {"TASK-PRV-003": frozenset({"new_module.py"})}


# ---------------------------------------------------------------------------
# 2. validate() — overlap defeats conditional approval (AC-003, AC-005)
# ---------------------------------------------------------------------------


class TestSourceFileContentionVsConditionalApproval:
    """When peer overlap is detected, parallel_contention conditional approval
    must NOT fire — Coach returns feedback so the existing retry machinery
    serialises the next attempt."""

    def test_overlap_in_parallel_contention_returns_feedback(
        self, tmp_path: Path
    ) -> None:
        """AC-005: Two-task wave both editing features/foo/test_foo.py.

        Failing task receives a non-conditional-approved verdict (decision =
        feedback) instead of the TASK-ABFIX-005 conditional approval.
        """
        shared_file = "features/foo/test_foo.py"
        validator = _make_validator(
            tmp_path,
            wave_size=2,
            task_id="TASK-PRV-002",
            peer_changed_files={"TASK-PRV-003": [shared_file]},
        )
        results = _task_work_results_with_files(files_modified=[shared_file])

        result = _run_validate(validator, task_work_results=results)

        assert result.decision == "feedback", (
            f"Expected feedback when source-file contention detected, "
            f"got '{result.decision}': {result.rationale}"
        )

    def test_overlap_feedback_names_overlapping_files(self, tmp_path: Path) -> None:
        """The feedback description names the peer task and overlapping file
        so the Player has actionable guidance on the next turn.
        """
        shared_file = "features/foo/test_foo.py"
        validator = _make_validator(
            tmp_path,
            peer_changed_files={"TASK-PRV-003": [shared_file]},
        )
        results = _task_work_results_with_files(files_modified=[shared_file])

        result = _run_validate(validator, task_work_results=results)

        assert result.decision == "feedback"
        # Feedback issue should mention the overlap (peer id + file)
        joined_descriptions = " ".join(
            issue.get("description", "") for issue in result.issues
        )
        assert "TASK-PRV-003" in joined_descriptions
        assert shared_file in joined_descriptions

    def test_overlap_in_code_failure_parallel_returns_feedback(
        self, tmp_path: Path
    ) -> None:
        """The "code" + parallel branch (TASK-ABFIX-005 recommendation 3b) is
        also gated by overlap detection.

        In a parallel wave, _classify_test_failure typically reclassifies code
        failures as parallel_contention. We verify the gate via wave_size and
        an unmatched failure output, mirroring
        test_code_failure_parallel_wave_gets_conditional_approval but with
        peer overlap.
        """
        shared_file = "shared/glue.py"
        validator = _make_validator(
            tmp_path,
            wave_size=3,
            peer_changed_files={"TASK-PRV-003": [shared_file]},
        )
        results = _task_work_results_with_files(files_modified=[shared_file])

        result = _run_validate(
            validator,
            test_output=(
                "FAILED tests/test_feature.py::test_x - "
                "AssertionError: assert 1 == 2"
            ),
            task_work_results=results,
        )

        assert result.decision == "feedback", (
            f"Expected feedback when source-file contention overlaps a "
            f"parallel code failure, got '{result.decision}': {result.rationale}"
        )


# ---------------------------------------------------------------------------
# 3. validate() — no overlap preserves existing TASK-ABFIX-005 path (AC-004)
# ---------------------------------------------------------------------------


class TestNoOverlapPreservesExistingApproval:
    """When no peer overlap is detected, the TASK-ABFIX-005 conditional approval
    path must remain intact for genuinely-transient parallel contention."""

    def test_no_peer_snapshot_keeps_conditional_approval(
        self, tmp_path: Path
    ) -> None:
        """No peer_changed_files configured (single-task path) → conditional
        approval still fires for parallel_contention. Backward compatibility.
        """
        validator = _make_validator(
            tmp_path,
            wave_size=2,
            peer_changed_files=None,
        )
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py"]
        )

        result = _run_validate(validator, task_work_results=results)

        assert result.decision == "approve", (
            f"Expected approve (TASK-ABFIX-005 conditional approval) when "
            f"no peer snapshot is configured, got '{result.decision}': "
            f"{result.rationale}"
        )

    def test_empty_peer_dict_keeps_conditional_approval(
        self, tmp_path: Path
    ) -> None:
        """First task to finish (peer dict configured but empty) still gets
        conditional approval. The contention is by definition not source-file
        contention because no peer has published any edits yet."""
        validator = _make_validator(tmp_path, peer_changed_files={})
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py"]
        )

        result = _run_validate(validator, task_work_results=results)

        assert result.decision == "approve"

    def test_disjoint_peer_files_keeps_conditional_approval(
        self, tmp_path: Path
    ) -> None:
        """Peer edited different files → no overlap → conditional approval
        path unchanged (AC-004)."""
        validator = _make_validator(
            tmp_path,
            peer_changed_files={"TASK-PRV-003": ["features/bar/test_bar.py"]},
        )
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py"]
        )

        result = _run_validate(validator, task_work_results=results)

        assert result.decision == "approve", (
            f"Expected approve for disjoint peer files (no real contention), "
            f"got '{result.decision}': {result.rationale}"
        )

    def test_serial_wave_with_peer_dict_unaffected(self, tmp_path: Path) -> None:
        """wave_size=1 path: classification falls through to ('code', 'n/a')
        and conditional approval doesn't apply regardless of peer dict.

        Confirms the new check only adds a constraint, not a new approval
        path. Serial code failures still produce feedback."""
        validator = _make_validator(
            tmp_path,
            wave_size=1,
            peer_changed_files={
                "TASK-PRV-003": ["features/foo/test_foo.py"]
            },
        )
        results = _task_work_results_with_files(
            files_modified=["features/foo/test_foo.py"]
        )

        result = _run_validate(validator, task_work_results=results)

        # Serial wave, code failure → feedback (existing behaviour)
        assert result.decision == "feedback"


# ---------------------------------------------------------------------------
# 4. Constructor normalisation
# ---------------------------------------------------------------------------


class TestPeerChangedFilesNormalisation:
    """The constructor must normalise peer_changed_files to ``Dict[str, frozenset]``
    and filter out invalid / self entries."""

    def test_none_yields_empty_dict(self, tmp_path: Path) -> None:
        """peer_changed_files=None → internal dict is empty (no peers known)."""
        validator = _make_validator(tmp_path, peer_changed_files=None)
        assert validator._peer_changed_files == {}

    def test_self_id_filtered(self, tmp_path: Path) -> None:
        """An entry keyed by self.task_id is dropped."""
        validator = _make_validator(
            tmp_path,
            task_id="TASK-PRV-002",
            peer_changed_files={
                "TASK-PRV-002": ["a.py"],
                "TASK-PRV-003": ["b.py"],
            },
        )
        assert "TASK-PRV-002" not in validator._peer_changed_files
        assert validator._peer_changed_files["TASK-PRV-003"] == frozenset({"b.py"})

    def test_empty_peer_files_filtered(self, tmp_path: Path) -> None:
        """Peer entry with no files is dropped (nothing to compare)."""
        validator = _make_validator(
            tmp_path,
            peer_changed_files={
                "TASK-PRV-003": [],
                "TASK-PRV-004": ["c.py"],
            },
        )
        assert "TASK-PRV-003" not in validator._peer_changed_files
        assert validator._peer_changed_files["TASK-PRV-004"] == frozenset({"c.py"})

    def test_iterable_input_accepted(self, tmp_path: Path) -> None:
        """The constructor accepts any iterable (list, set, frozenset) of files.

        Frees callers from materialising a list when a set is more natural.
        """
        validator = _make_validator(
            tmp_path,
            peer_changed_files={"TASK-PRV-003": frozenset({"x.py", "y.py"})},
        )
        assert validator._peer_changed_files["TASK-PRV-003"] == frozenset(
            {"x.py", "y.py"}
        )
