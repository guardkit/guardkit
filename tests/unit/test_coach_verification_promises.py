"""Unit tests for CoachVerifier completion-promise file verification.

Tests for AC-001 of TASK-AB-FIX-INVAB1: extending CoachVerifier with
``_verify_completion_promises_files_exist`` so it catches the FEAT-6CC5
class of sophisticated dishonesty (Player keeps files_created honest while
lying in completion_promises[*].implementation_files).

Coverage Target: >=85%
"""

from pathlib import Path

import pytest

from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    Discrepancy,
)


@pytest.fixture
def verifier(tmp_path: Path) -> CoachVerifier:
    return CoachVerifier(tmp_path)


class TestVerifyCompletionPromisesFilesExist:
    """Tests for the new _verify_completion_promises_files_exist method."""

    def test_no_promises_returns_no_discrepancies(self, verifier: CoachVerifier):
        """Empty completion_promises produces no discrepancies."""
        report = {"completion_promises": []}
        assert verifier._verify_completion_promises_files_exist(report) == []

    def test_missing_completion_promises_key_safe(self, verifier: CoachVerifier):
        """Report without completion_promises key produces no discrepancies."""
        report = {"files_created": ["a.py"]}
        assert verifier._verify_completion_promises_files_exist(report) == []

    def test_completion_promises_none_value_safe(self, verifier: CoachVerifier):
        """``completion_promises: None`` (instead of [] ) is treated as empty."""
        report = {"completion_promises": None}
        # Should not raise; defensive against synthetic-report edge cases.
        assert verifier._verify_completion_promises_files_exist(report) == []

    def test_incomplete_promise_not_checked(
        self, verifier: CoachVerifier, tmp_path: Path
    ):
        """Promises with status != 'complete' are not checked."""
        report = {
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "status": "incomplete",
                    "implementation_files": ["src/never_made.py"],
                }
            ]
        }
        assert verifier._verify_completion_promises_files_exist(report) == []

    def test_complete_promise_with_existing_file_no_discrepancy(
        self, verifier: CoachVerifier, tmp_path: Path
    ):
        """Complete promise + existing file = no discrepancy."""
        target = tmp_path / "src" / "exists.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# real")

        report = {
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "status": "complete",
                    "implementation_files": ["src/exists.py"],
                }
            ]
        }
        assert verifier._verify_completion_promises_files_exist(report) == []

    def test_complete_promise_with_missing_file_produces_critical_discrepancy(
        self, verifier: CoachVerifier
    ):
        """Complete promise + missing file = critical discrepancy (FEAT-6CC5 reproducer)."""
        report = {
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "status": "complete",
                    "implementation_files": ["src/repro/missing.py"],
                }
            ]
        }
        discs = verifier._verify_completion_promises_files_exist(report)
        assert len(discs) == 1
        assert discs[0].claim_type == "promise_file_existence"
        assert discs[0].severity == "critical"
        assert "src/repro/missing.py" in discs[0].player_claim
        assert "src/repro/missing.py" in discs[0].actual_value

    def test_implementation_files_none_is_safe(self, verifier: CoachVerifier):
        """``implementation_files: None`` does not raise."""
        report = {
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "status": "complete",
                    "implementation_files": None,
                }
            ]
        }
        assert verifier._verify_completion_promises_files_exist(report) == []

    def test_missing_criterion_id_falls_back_to_question_mark(
        self, verifier: CoachVerifier
    ):
        """Missing criterion_id renders as '?' in player_claim."""
        report = {
            "completion_promises": [
                {
                    "status": "complete",
                    "implementation_files": ["src/missing.py"],
                }
            ]
        }
        discs = verifier._verify_completion_promises_files_exist(report)
        assert len(discs) == 1
        assert "[?]" in discs[0].player_claim

    def test_multiple_complete_promises_each_checked_independently(
        self, verifier: CoachVerifier, tmp_path: Path
    ):
        """Multiple complete promises produce one discrepancy per missing file."""
        (tmp_path / "exists.py").write_text("")

        report = {
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "status": "complete",
                    "implementation_files": ["exists.py"],
                },
                {
                    "criterion_id": "AC-002",
                    "status": "complete",
                    "implementation_files": ["missing-1.py", "missing-2.py"],
                },
            ]
        }
        discs = verifier._verify_completion_promises_files_exist(report)
        assert len(discs) == 2
        # Both discrepancies should reference AC-002 (the failing criterion)
        for d in discs:
            assert "AC-002" in d.player_claim


class TestVerifyPlayerReportWiresCompletionPromises:
    """Tests that verify_player_report() invokes the new check."""

    def test_completion_promise_lie_surfaces_through_verify_player_report(
        self, verifier: CoachVerifier
    ):
        """The new check participates in verify_player_report's discrepancy list."""
        report = {
            "files_created": [],
            "files_modified": [],
            "tests_written": [],
            "tests_run": False,  # avoid running pytest
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "status": "complete",
                    "implementation_files": ["src/missing.py"],
                }
            ],
        }
        result = verifier.verify_player_report(report)
        assert result.verified is False
        assert any(
            d.claim_type == "promise_file_existence" for d in result.discrepancies
        )
        # Honesty score must drop below 1.0 for a critical discrepancy.
        assert result.honesty_score < 1.0

    def test_honest_report_yields_score_one_zero(
        self, verifier: CoachVerifier, tmp_path: Path
    ):
        """An entirely honest report (no claims to verify) yields score 1.0."""
        report = {
            "files_created": [],
            "files_modified": [],
            "tests_written": [],
            "tests_run": False,
            "completion_promises": [],
        }
        result = verifier.verify_player_report(report)
        assert result.verified is True
        assert result.discrepancies == []
        assert result.honesty_score == 1.0

    def test_count_verifiable_claims_includes_promises(
        self, verifier: CoachVerifier
    ):
        """_count_verifiable_claims must count complete promises' implementation_files."""
        report = {
            "completion_promises": [
                {
                    "status": "complete",
                    "implementation_files": ["a.py", "b.py"],
                },
                {
                    "status": "incomplete",
                    "implementation_files": ["c.py"],
                },
                {
                    "status": "complete",
                    "implementation_files": ["d.py"],
                },
            ]
        }
        # Only complete promises' files count: 2 + 1 = 3 (plus min-1 baseline)
        assert verifier._count_verifiable_claims(report) == 3
