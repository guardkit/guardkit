"""Unit tests for the coach_verification test runner.

Tests the CoachVerifier class, which runs a worktree's tests under the
worktree's own interpreter (used by state recovery).
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    TestResult,
)


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
    def test_run_tests_default_timeout(self, mock_run: MagicMock, verifier: CoachVerifier):
        """Test that default timeout is 120s."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5 passed",
        )

        verifier._run_tests()

        mock_run.assert_called_once()
        assert mock_run.call_args[1]["timeout"] == 120

    @patch("subprocess.run")
    def test_run_tests_custom_timeout(self, mock_run: MagicMock, verifier: CoachVerifier):
        """Test that custom timeout is passed through to subprocess.run."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5 passed",
        )

        verifier._run_tests(timeout=300)

        mock_run.assert_called_once()
        assert mock_run.call_args[1]["timeout"] == 300

    @patch("subprocess.run")
    def test_run_tests_custom_timeout_fallback_path(self, mock_run: MagicMock, verifier: CoachVerifier):
        """Test that custom timeout is used in the fallback path too."""
        mock_run.side_effect = [
            FileNotFoundError("pytest"),  # Primary path fails
            MagicMock(returncode=0, stdout="5 passed"),  # Fallback succeeds
        ]

        verifier._run_tests(timeout=300)

        # Second call should use the custom timeout
        assert mock_run.call_args_list[1][1]["timeout"] == 300

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


