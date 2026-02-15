"""Unit tests for Coach honesty verification module.

Tests the CoachVerifier class that cross-references Player claims
against actual test results and filesystem state.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    Discrepancy,
    HonestyVerification,
    TestResult,
    format_verification_context,
)


class TestDiscrepancy:
    """Tests for Discrepancy dataclass."""

    def test_discrepancy_creation(self):
        """Test creating a discrepancy."""
        disc = Discrepancy(
            claim_type="test_result",
            player_claim="tests_passed: True",
            actual_value="tests_passed: False",
            severity="critical",
        )
        assert disc.claim_type == "test_result"
        assert disc.player_claim == "tests_passed: True"
        assert disc.actual_value == "tests_passed: False"
        assert disc.severity == "critical"


class TestTestResult:
    """Tests for TestResult dataclass."""

    def test_test_result_creation(self):
        """Test creating a test result."""
        result = TestResult(
            passed=True,
            test_count=5,
            output="5 passed in 0.23s",
        )
        assert result.passed is True
        assert result.test_count == 5
        assert result.output == "5 passed in 0.23s"


class TestHonestyVerification:
    """Tests for HonestyVerification dataclass."""

    def test_default_values(self):
        """Test default values."""
        verification = HonestyVerification(verified=True)
        assert verification.verified is True
        assert verification.discrepancies == []
        assert verification.honesty_score == 1.0

    def test_with_discrepancies(self):
        """Test with discrepancies."""
        disc = Discrepancy(
            claim_type="file_existence",
            player_claim="files_created: ['test.py']",
            actual_value="File does not exist",
            severity="critical",
        )
        verification = HonestyVerification(
            verified=False,
            discrepancies=[disc],
            honesty_score=0.5,
        )
        assert verification.verified is False
        assert len(verification.discrepancies) == 1
        assert verification.honesty_score == 0.5


class TestCoachVerifier:
    """Tests for CoachVerifier class."""

    @pytest.fixture
    def verifier(self, tmp_path: Path) -> CoachVerifier:
        """Create a CoachVerifier instance."""
        return CoachVerifier(tmp_path)

    def test_init(self, tmp_path: Path):
        """Test CoachVerifier initialization."""
        verifier = CoachVerifier(tmp_path)
        assert verifier.worktree_path == tmp_path
        assert verifier._cached_test_result is None

    def test_verify_files_exist_success(self, verifier: CoachVerifier, tmp_path: Path):
        """Test file verification when files exist."""
        # Create test file
        test_file = tmp_path / "src" / "test.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# test")

        report = {
            "files_created": ["src/test.py"],
            "files_modified": [],
        }

        discrepancies = verifier._verify_files_exist(report)
        assert discrepancies == []

    def test_verify_files_exist_missing_file(
        self, verifier: CoachVerifier, tmp_path: Path
    ):
        """Test file verification when file is missing."""
        report = {
            "files_created": ["src/missing.py"],
            "files_modified": [],
        }

        discrepancies = verifier._verify_files_exist(report)
        assert len(discrepancies) == 1
        assert discrepancies[0].claim_type == "file_existence"
        assert discrepancies[0].severity == "critical"
        assert "src/missing.py" in discrepancies[0].player_claim

    def test_verify_files_exist_multiple_lists(
        self, verifier: CoachVerifier, tmp_path: Path
    ):
        """Test file verification across multiple list types."""
        # Create some files
        (tmp_path / "created.py").write_text("")
        (tmp_path / "modified.py").write_text("")

        report = {
            "files_created": ["created.py", "missing_created.py"],
            "files_modified": ["modified.py", "missing_modified.py"],
            "tests_written": ["missing_test.py"],
        }

        discrepancies = verifier._verify_files_exist(report)
        assert len(discrepancies) == 3  # 3 missing files

    def test_extract_test_count_valid(self, verifier: CoachVerifier):
        """Test extracting test count from valid summary."""
        assert verifier._extract_test_count("5 passed in 0.23s") == 5
        assert verifier._extract_test_count("10 passed, 2 failed") == 10
        assert verifier._extract_test_count("1 passed") == 1

    def test_extract_test_count_invalid(self, verifier: CoachVerifier):
        """Test extracting test count from invalid summary."""
        assert verifier._extract_test_count("no tests found") is None
        assert verifier._extract_test_count("") is None
        assert verifier._extract_test_count("tests complete") is None

    def test_parse_pytest_count(self, verifier: CoachVerifier):
        """Test parsing pytest output for test count."""
        assert verifier._parse_pytest_count("5 passed in 0.23s") == 5
        assert verifier._parse_pytest_count("12 passed, 3 failed") == 12
        assert verifier._parse_pytest_count("no tests ran") == 0

    def test_count_verifiable_claims(self, verifier: CoachVerifier):
        """Test counting verifiable claims in report."""
        # Empty report
        assert verifier._count_verifiable_claims({}) == 1  # min 1 to avoid div by zero

        # Report with tests
        report_with_tests = {
            "tests_run": True,
            "files_created": ["a.py", "b.py"],
            "files_modified": ["c.py"],
            "tests_written": ["test_a.py"],
        }
        # 2 (tests_run) + 2 (created) + 1 (modified) + 1 (tests_written) = 6
        assert verifier._count_verifiable_claims(report_with_tests) == 6

    @patch("subprocess.run")
    def test_run_tests_success(self, mock_run: MagicMock, verifier: CoachVerifier):
        """Test running tests successfully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5 passed in 0.23s",
        )

        result = verifier._run_tests()

        assert result.passed is True
        assert result.test_count == 5
        assert "5 passed" in result.output

    @patch("subprocess.run")
    def test_run_tests_failure(self, mock_run: MagicMock, verifier: CoachVerifier):
        """Test running tests with failures."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="3 passed, 2 failed",
        )

        result = verifier._run_tests()

        assert result.passed is False
        assert result.test_count == 3

    @patch("subprocess.run")
    def test_run_tests_caching(self, mock_run: MagicMock, verifier: CoachVerifier):
        """Test that test results are cached."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5 passed",
        )

        # First call
        result1 = verifier._run_tests()
        # Second call
        result2 = verifier._run_tests()

        # Should only run once due to caching
        mock_run.assert_called_once()
        assert result1 is result2

    @patch("subprocess.run")
    def test_run_tests_timeout(self, mock_run: MagicMock, verifier: CoachVerifier):
        """Test handling test timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=120)

        result = verifier._run_tests()

        assert result.passed is False
        assert result.test_count == 0
        assert "timed out" in result.output

    @patch("subprocess.run")
    def test_run_tests_with_scoped_paths(self, mock_run: MagicMock, verifier: CoachVerifier):
        """Test running tests with scoped test paths."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="3 passed",
        )

        result = verifier._run_tests(test_paths=["tests/seam/"])

        # Should pass the test_paths to pytest
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "pytest" in call_args
        assert "--tb=no" in call_args
        assert "-q" in call_args
        assert "tests/seam/" in call_args

        assert result.passed is True
        assert result.test_count == 3

    @patch("subprocess.run")
    def test_run_tests_scoped_paths_no_caching(self, mock_run: MagicMock, verifier: CoachVerifier):
        """Test that scoped test runs bypass cache."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5 passed",
        )

        # First call with scoped path
        result1 = verifier._run_tests(test_paths=["tests/unit/"])
        # Second call with different scoped path
        result2 = verifier._run_tests(test_paths=["tests/integration/"])

        # Should run twice (no caching for scoped runs)
        assert mock_run.call_count == 2

        # Verify different paths were used
        call1_args = mock_run.call_args_list[0][0][0]
        call2_args = mock_run.call_args_list[1][0][0]
        assert "tests/unit/" in call1_args
        assert "tests/integration/" in call2_args

    @patch("subprocess.run")
    def test_verify_test_results_match(
        self, mock_run: MagicMock, verifier: CoachVerifier
    ):
        """Test verification when test results match."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5 passed",
        )

        report = {
            "tests_run": True,
            "tests_passed": True,
        }

        discrepancies = verifier._verify_test_results(report)
        assert discrepancies == []

    @patch("subprocess.run")
    def test_verify_test_results_mismatch(
        self, mock_run: MagicMock, verifier: CoachVerifier
    ):
        """Test verification when test results don't match."""
        mock_run.return_value = MagicMock(
            returncode=1,  # Tests failed
            stdout="3 passed, 2 failed",
        )

        report = {
            "tests_run": True,
            "tests_passed": True,  # Player claims tests passed
        }

        discrepancies = verifier._verify_test_results(report)
        assert len(discrepancies) == 1
        assert discrepancies[0].claim_type == "test_result"
        assert discrepancies[0].severity == "critical"

    def test_verify_test_results_not_run(self, verifier: CoachVerifier):
        """Test verification when tests weren't run."""
        report = {
            "tests_run": False,
        }

        discrepancies = verifier._verify_test_results(report)
        assert discrepancies == []

    @patch("subprocess.run")
    def test_verify_test_count_match(
        self, mock_run: MagicMock, verifier: CoachVerifier
    ):
        """Test test count verification when counts match."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5 passed in 0.23s",
        )

        report = {
            "test_output_summary": "5 passed in 0.23s",
        }

        discrepancies = verifier._verify_test_count(report)
        assert discrepancies == []

    @patch("subprocess.run")
    def test_verify_test_count_mismatch(
        self, mock_run: MagicMock, verifier: CoachVerifier
    ):
        """Test test count verification when counts don't match."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="3 passed in 0.23s",
        )

        report = {
            "test_output_summary": "5 passed in 0.23s",  # Player claims 5
        }

        discrepancies = verifier._verify_test_count(report)
        assert len(discrepancies) == 1
        assert discrepancies[0].claim_type == "test_count"
        assert discrepancies[0].severity == "warning"

    @patch("subprocess.run")
    def test_verify_player_report_all_verified(
        self, mock_run: MagicMock, verifier: CoachVerifier, tmp_path: Path
    ):
        """Test full verification when all claims are valid."""
        # Create claimed files
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5 passed in 0.23s",
        )

        report = {
            "tests_run": True,
            "tests_passed": True,
            "test_output_summary": "5 passed in 0.23s",
            "files_created": ["src/main.py"],
            "tests_written": ["tests/test_main.py"],
        }

        verification = verifier.verify_player_report(report)

        assert verification.verified is True
        assert verification.discrepancies == []
        assert verification.honesty_score == 1.0

    @patch("subprocess.run")
    def test_verify_player_report_with_discrepancies(
        self, mock_run: MagicMock, verifier: CoachVerifier, tmp_path: Path
    ):
        """Test full verification with discrepancies."""
        # Don't create any files (discrepancy)

        mock_run.return_value = MagicMock(
            returncode=1,  # Tests failed (discrepancy)
            stdout="3 passed, 2 failed",
        )

        report = {
            "tests_run": True,
            "tests_passed": True,  # Claims passed but they failed
            "test_output_summary": "5 passed",  # Claims 5 but only 3 passed
            "files_created": ["missing.py"],  # File doesn't exist
        }

        verification = verifier.verify_player_report(report)

        assert verification.verified is False
        assert len(verification.discrepancies) >= 2  # At least test_result and file_existence
        assert verification.honesty_score < 1.0


class TestFormatVerificationContext:
    """Tests for format_verification_context function."""

    def test_format_verified(self):
        """Test formatting when all verified."""
        verification = HonestyVerification(verified=True)
        output = format_verification_context(verification)

        assert "Honesty Score: 1.00" in output
        assert "All claims verified successfully" in output

    def test_format_with_discrepancies(self):
        """Test formatting with discrepancies."""
        discrepancies = [
            Discrepancy(
                claim_type="test_result",
                player_claim="tests_passed: True",
                actual_value="tests_passed: False",
                severity="critical",
            ),
            Discrepancy(
                claim_type="test_count",
                player_claim="5 tests",
                actual_value="3 tests",
                severity="warning",
            ),
        ]
        verification = HonestyVerification(
            verified=False,
            discrepancies=discrepancies,
            honesty_score=0.5,
        )
        output = format_verification_context(verification)

        assert "Honesty Score: 0.50" in output
        assert "DISCREPANCIES FOUND:" in output
        assert "[CRITICAL]" in output
        assert "[WARNING]" in output
        assert "test_result" in output
        assert "test_count" in output
