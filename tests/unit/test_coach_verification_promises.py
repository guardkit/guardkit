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


class TestSiblingRelativeClaimResolution:
    """TASK-FIX-XREPOPROM01 — the FEAT-10AC run-1 honesty-collapse reproducer.

    A Player writing a declared sibling evidence repo reported its
    completion-promise ``implementation_files`` (and files_modified claims)
    as SIBLING-RELATIVE unqualified paths. Both Player-authored-claim
    verifiers resolved them against the worktree only, manufacturing
    critical ``promise_file_existence`` + ``claim_audit`` discrepancies for
    work that existed (and was checkpointed) in the sibling — an
    ``evidence-boundary-narrower-than-write-surface`` false-red that
    collapsed the run in 3 turns.
    """

    @pytest.fixture
    def sibling(self, tmp_path: Path):
        from guardkit.orchestrator.evidence_repos import EvidenceRepo

        factory = tmp_path / "guardkitfactory"
        target = factory / "src" / "guardkitfactory" / "wiring"
        target.mkdir(parents=True)
        (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
        return EvidenceRepo(name="guardkitfactory", root=factory)

    @pytest.fixture
    def worktree(self, tmp_path: Path) -> Path:
        wt = tmp_path / "worktree"
        wt.mkdir()
        return wt

    def _promise_report(self, path: str) -> dict:
        return {
            "completion_promises": [
                {
                    "criterion_id": "AC-1",
                    "status": "complete",
                    "implementation_files": [path],
                }
            ]
        }

    def test_unqualified_sibling_promise_resolves_not_critical(
        self, worktree: Path, sibling
    ):
        """A sibling-relative promise path that EXISTS under a declared
        evidence repo is resolved (recorded), never a discrepancy."""
        v = CoachVerifier(worktree, evidence_repos=[sibling])
        report = self._promise_report("src/guardkitfactory/wiring/analyzer.py")
        discs = v._verify_completion_promises_files_exist(report)
        assert discs == []
        assert len(v._resolved_paths) == 1
        assert v._resolved_paths[0].claimed == (
            "src/guardkitfactory/wiring/analyzer.py"
        )

    def test_missing_everywhere_still_critical(self, worktree: Path, sibling):
        """FEAT-6CC5 protection unchanged: a path existing in neither the
        worktree nor any declared repo stays a critical discrepancy."""
        v = CoachVerifier(worktree, evidence_repos=[sibling])
        report = self._promise_report("src/guardkitfactory/wiring/nowhere.py")
        discs = v._verify_completion_promises_files_exist(report)
        assert len(discs) == 1
        assert discs[0].claim_type == "promise_file_existence"
        assert discs[0].severity == "critical"

    def test_no_declared_repos_prior_behaviour_exact(self, worktree: Path):
        """With no evidence repos declared, the worktree-only behaviour is
        exact — the sibling-relative path stays critical."""
        v = CoachVerifier(worktree)
        report = self._promise_report("src/guardkitfactory/wiring/analyzer.py")
        discs = v._verify_completion_promises_files_exist(report)
        assert len(discs) == 1
        assert discs[0].severity == "critical"

    @staticmethod
    def _git_init(path: Path) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t"], cwd=path, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "t"], cwd=path, check=True
        )

    def test_claim_audit_drops_sibling_resolved_unqualified(
        self, worktree: Path, sibling
    ):
        """claim_audit must not audit a worktree-missing, sibling-present
        unqualified claim against the worktree's git status."""
        self._git_init(worktree)
        v = CoachVerifier(worktree, evidence_repos=[sibling])
        report = {
            "files_modified": ["src/guardkitfactory/wiring/analyzer.py"],
        }
        discs = v._verify_claims_were_staged(report)
        assert discs == []

    def test_claim_audit_missing_everywhere_still_fabricated(
        self, worktree: Path, sibling
    ):
        """A claim existing nowhere still classifies as fabricated critical."""
        self._git_init(worktree)
        v = CoachVerifier(worktree, evidence_repos=[sibling])
        report = {"files_modified": ["src/guardkitfactory/wiring/ghost.py"]}
        discs = v._verify_claims_were_staged(report)
        assert len(discs) == 1
        assert discs[0].severity == "critical"

    def test_end_to_end_verify_player_report_resolves(self, worktree: Path, sibling):
        """The full verify_player_report path surfaces the resolution on
        HonestyVerification.resolved_paths and stays verified."""
        self._git_init(worktree)
        v = CoachVerifier(worktree, evidence_repos=[sibling])
        report = self._promise_report("src/guardkitfactory/wiring/analyzer.py")
        result = v.verify_player_report(report)
        assert result.verified is True
        assert [r.claimed for r in result.resolved_paths] == [
            "src/guardkitfactory/wiring/analyzer.py"
        ]
