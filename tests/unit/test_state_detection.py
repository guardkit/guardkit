"""Unit tests for state detection module.

Tests git-based and test-based detection functions for partial work recovery.

Coverage Target: >=85%
Test Count: 25+ tests
"""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.state_detection import (
    GitChangesSummary,
    TestResultsSummary,
    detect_git_changes,
    detect_test_results,
    _parse_git_status,
    _parse_diff_stats,
    _get_diff_stats,
    GIT_COMMAND_TIMEOUT_SECONDS,
    DIFF_COMMAND_TIMEOUT_SECONDS,
)


# ============================================================================
# 1. GitChangesSummary Dataclass Tests
# ============================================================================


class TestGitChangesSummary:
    """Tests for GitChangesSummary dataclass."""

    def test_default_values(self):
        """Test default empty values."""
        summary = GitChangesSummary()
        assert summary.files_modified == []
        assert summary.files_added == []
        assert summary.files_deleted == []
        assert summary.diff_stats == ""
        assert summary.insertions == 0
        assert summary.deletions == 0
        assert summary.timestamp  # Should have timestamp

    def test_with_files(self):
        """Test with file lists populated."""
        summary = GitChangesSummary(
            files_modified=["src/main.py", "src/utils.py"],
            files_added=["src/new_file.py"],
            files_deleted=["src/old_file.py"],
            insertions=100,
            deletions=50,
        )
        assert len(summary.files_modified) == 2
        assert len(summary.files_added) == 1
        assert len(summary.files_deleted) == 1
        assert summary.insertions == 100
        assert summary.deletions == 50

    def test_total_files_changed(self):
        """Test total_files_changed property."""
        summary = GitChangesSummary(
            files_modified=["a.py", "b.py"],
            files_added=["c.py"],
            files_deleted=["d.py"],
        )
        assert summary.total_files_changed == 4

    def test_total_files_changed_empty(self):
        """Test total_files_changed with empty lists."""
        summary = GitChangesSummary()
        assert summary.total_files_changed == 0

    def test_has_changes_true(self):
        """Test has_changes returns True when changes exist."""
        summary = GitChangesSummary(files_modified=["a.py"])
        assert summary.has_changes is True

    def test_has_changes_false(self):
        """Test has_changes returns False when no changes."""
        summary = GitChangesSummary()
        assert summary.has_changes is False


# ============================================================================
# 2. TestResultsSummary Dataclass Tests
# ============================================================================


class TestTestResultsSummary:
    """Tests for TestResultsSummary dataclass."""

    def test_default_values(self):
        """Test default values."""
        summary = TestResultsSummary()
        assert summary.tests_run is False
        assert summary.tests_passed is False
        assert summary.test_count == 0
        assert summary.passed_count == 0
        assert summary.failed_count == 0
        assert summary.output_summary == ""
        assert summary.error is None

    def test_with_passing_tests(self):
        """Test with passing test results."""
        summary = TestResultsSummary(
            tests_run=True,
            tests_passed=True,
            test_count=10,
            passed_count=10,
            failed_count=0,
            output_summary="10 passed in 0.5s",
        )
        assert summary.tests_run is True
        assert summary.tests_passed is True
        assert summary.test_count == 10
        assert summary.passed_count == 10
        assert summary.failed_count == 0

    def test_with_failing_tests(self):
        """Test with failing test results."""
        summary = TestResultsSummary(
            tests_run=True,
            tests_passed=False,
            test_count=10,
            passed_count=7,
            failed_count=3,
            output_summary="7 passed, 3 failed",
        )
        assert summary.tests_passed is False
        assert summary.passed_count == 7
        assert summary.failed_count == 3

    def test_with_error(self):
        """Test with error message."""
        summary = TestResultsSummary(
            tests_run=False,
            error="pytest not found",
        )
        assert summary.tests_run is False
        assert summary.error == "pytest not found"


# ============================================================================
# 3. Git Status Parsing Tests
# ============================================================================


class TestParseGitStatus:
    """Tests for _parse_git_status function."""

    def test_parse_empty_status(self):
        """Test parsing empty git status output."""
        modified, added, deleted = _parse_git_status("")
        assert modified == []
        assert added == []
        assert deleted == []

    def test_parse_modified_files(self):
        """Test parsing modified files."""
        status_output = " M src/main.py\n M src/utils.py"
        modified, added, deleted = _parse_git_status(status_output)
        assert "src/main.py" in modified
        assert "src/utils.py" in modified
        assert len(added) == 0
        assert len(deleted) == 0

    def test_parse_untracked_files(self):
        """Test parsing untracked/new files."""
        status_output = "?? src/new_file.py\n?? tests/test_new.py"
        modified, added, deleted = _parse_git_status(status_output)
        assert len(modified) == 0
        assert "src/new_file.py" in added
        assert "tests/test_new.py" in added
        assert len(deleted) == 0

    def test_parse_deleted_files(self):
        """Test parsing deleted files."""
        status_output = " D src/removed.py"
        modified, added, deleted = _parse_git_status(status_output)
        assert len(modified) == 0
        assert len(added) == 0
        assert "src/removed.py" in deleted

    def test_parse_added_files(self):
        """Test parsing staged added files."""
        status_output = "A  src/staged_new.py"
        modified, added, deleted = _parse_git_status(status_output)
        assert "src/staged_new.py" in added

    def test_parse_renamed_files(self):
        """Test parsing renamed files."""
        status_output = "R  old_name.py -> new_name.py"
        modified, added, deleted = _parse_git_status(status_output)
        assert "new_name.py" in modified

    def test_parse_mixed_status(self):
        """Test parsing mixed file statuses."""
        status_output = " M src/modified.py\n?? src/new.py\n D src/deleted.py\nA  src/added.py"
        modified, added, deleted = _parse_git_status(status_output)
        assert "src/modified.py" in modified
        assert "src/new.py" in added
        assert "src/added.py" in added
        assert "src/deleted.py" in deleted


# ============================================================================
# 4. Diff Stats Parsing Tests
# ============================================================================


class TestParseDiffStats:
    """Tests for _parse_diff_stats function."""

    def test_parse_empty_diff(self):
        """Test parsing empty diff output."""
        insertions, deletions = _parse_diff_stats("")
        assert insertions == 0
        assert deletions == 0

    def test_parse_insertions_only(self):
        """Test parsing diff with only insertions."""
        diff_output = "1 file changed, 42 insertions(+)"
        insertions, deletions = _parse_diff_stats(diff_output)
        assert insertions == 42
        assert deletions == 0

    def test_parse_deletions_only(self):
        """Test parsing diff with only deletions."""
        diff_output = "1 file changed, 15 deletions(-)"
        insertions, deletions = _parse_diff_stats(diff_output)
        assert insertions == 0
        assert deletions == 15

    def test_parse_both_insertions_deletions(self):
        """Test parsing diff with both insertions and deletions."""
        diff_output = "3 files changed, 100 insertions(+), 50 deletions(-)"
        insertions, deletions = _parse_diff_stats(diff_output)
        assert insertions == 100
        assert deletions == 50

    def test_parse_multiline_output(self):
        """Test parsing multiline diff --stat output."""
        diff_output = """
 src/main.py  | 42 ++++++++++++++++
 src/utils.py | 15 -------
 3 files changed, 42 insertions(+), 15 deletions(-)
"""
        insertions, deletions = _parse_diff_stats(diff_output)
        assert insertions == 42
        assert deletions == 15


# ============================================================================
# 5. detect_git_changes Tests
# ============================================================================


class TestDetectGitChanges:
    """Tests for detect_git_changes function."""

    def test_nonexistent_path(self, tmp_path: Path):
        """Test with non-existent worktree path."""
        result = detect_git_changes(tmp_path / "nonexistent")
        assert result is None

    @patch("subprocess.run")
    def test_no_changes_detected(self, mock_run: MagicMock, tmp_path: Path):
        """Test when no changes in worktree."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",  # Empty status output
            stderr="",
        )

        result = detect_git_changes(tmp_path)
        assert result is None

    @patch("subprocess.run")
    def test_modified_files_detected(self, mock_run: MagicMock, tmp_path: Path):
        """Test detecting modified files."""
        mock_run.side_effect = [
            # git status
            MagicMock(returncode=0, stdout=" M src/main.py\n M src/utils.py", stderr=""),
            # git diff --stat
            MagicMock(returncode=0, stdout="2 files changed, 50 insertions(+), 20 deletions(-)", stderr=""),
        ]

        result = detect_git_changes(tmp_path)

        assert result is not None
        assert "src/main.py" in result.files_modified
        assert "src/utils.py" in result.files_modified
        assert result.insertions == 50
        assert result.deletions == 20

    @patch("subprocess.run")
    def test_new_files_detected(self, mock_run: MagicMock, tmp_path: Path):
        """Test detecting new/untracked files."""
        mock_run.side_effect = [
            # git status
            MagicMock(returncode=0, stdout="?? src/new_file.py\n?? tests/test_new.py", stderr=""),
            # git diff --stat
            MagicMock(returncode=0, stdout="0 files changed", stderr=""),
        ]

        result = detect_git_changes(tmp_path)

        assert result is not None
        assert "src/new_file.py" in result.files_added
        assert "tests/test_new.py" in result.files_added

    @patch("subprocess.run")
    def test_git_status_fails(self, mock_run: MagicMock, tmp_path: Path):
        """Test when git status command fails."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        result = detect_git_changes(tmp_path)
        assert result is None

    @patch("subprocess.run")
    def test_git_status_timeout(self, mock_run: MagicMock, tmp_path: Path):
        """Test handling git status timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="git status", timeout=GIT_COMMAND_TIMEOUT_SECONDS
        )

        result = detect_git_changes(tmp_path)
        assert result is None

    @patch("subprocess.run")
    def test_git_not_found(self, mock_run: MagicMock, tmp_path: Path):
        """Test when git command is not found."""
        mock_run.side_effect = FileNotFoundError("git")

        result = detect_git_changes(tmp_path)
        assert result is None


# ============================================================================
# 6. detect_test_results Tests
# ============================================================================


class TestDetectTestResults:
    """Tests for detect_test_results function."""

    def test_nonexistent_path(self, tmp_path: Path):
        """Test with non-existent worktree path."""
        result = detect_test_results(tmp_path / "nonexistent")
        assert result is None

    @patch("guardkit.orchestrator.coach_verification.CoachVerifier")
    def test_passing_tests_detected(self, mock_verifier_class: MagicMock, tmp_path: Path):
        """Test detecting passing tests."""
        mock_verifier = MagicMock()
        mock_verifier._run_tests.return_value = MagicMock(
            passed=True,
            test_count=10,
            output="10 passed in 0.5s",
        )
        mock_verifier_class.return_value = mock_verifier

        result = detect_test_results(tmp_path, task_id="TASK-001", turn=1)

        assert result is not None
        assert result.tests_run is True
        assert result.tests_passed is True
        assert result.test_count == 10
        assert result.passed_count == 10

    @patch("guardkit.orchestrator.coach_verification.CoachVerifier")
    def test_failing_tests_detected(self, mock_verifier_class: MagicMock, tmp_path: Path):
        """Test detecting failing tests."""
        mock_verifier = MagicMock()
        mock_verifier._run_tests.return_value = MagicMock(
            passed=False,
            test_count=10,
            output="7 passed, 3 failed",
        )
        mock_verifier_class.return_value = mock_verifier

        result = detect_test_results(tmp_path, task_id="TASK-001", turn=1)

        assert result is not None
        assert result.tests_run is True
        assert result.tests_passed is False
        assert result.test_count == 10

    @patch("guardkit.orchestrator.coach_verification.CoachVerifier")
    def test_no_tests_found(self, mock_verifier_class: MagicMock, tmp_path: Path):
        """Test when no tests are found."""
        mock_verifier = MagicMock()
        mock_verifier._run_tests.return_value = MagicMock(
            passed=True,
            test_count=0,
            output="no tests ran",
        )
        mock_verifier_class.return_value = mock_verifier

        result = detect_test_results(tmp_path, task_id="TASK-001", turn=1)

        assert result is not None
        assert result.tests_run is False
        assert result.test_count == 0

    @patch("guardkit.orchestrator.coach_verification.CoachVerifier")
    def test_test_execution_error(self, mock_verifier_class: MagicMock, tmp_path: Path):
        """Test handling test execution error."""
        mock_verifier = MagicMock()
        mock_verifier._run_tests.side_effect = Exception("pytest failed")
        mock_verifier_class.return_value = mock_verifier

        result = detect_test_results(tmp_path, task_id="TASK-001", turn=1)

        assert result is not None
        assert result.tests_run is False
        assert result.error == "pytest failed"

    def test_coach_verifier_import_error(self, tmp_path: Path):
        """Test handling import error for CoachVerifier."""
        # Simulate import error by making the module raise an error
        with patch.dict("sys.modules", {"guardkit.orchestrator.coach_verification": None}):
            result = detect_test_results(tmp_path, task_id="TASK-001", turn=1)

            assert result is not None
            assert result.tests_run is False
            assert result.error is not None
            # Import will fail since module is set to None


# ============================================================================
# 7. Integration Tests
# ============================================================================


class TestStateDetectionIntegration:
    """Integration tests for state detection."""

    @patch("subprocess.run")
    @patch("guardkit.orchestrator.coach_verification.CoachVerifier")
    def test_full_detection_workflow(
        self,
        mock_verifier_class: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ):
        """Test complete detection workflow with git and tests."""
        # Setup git mocks
        mock_run.side_effect = [
            # git status
            MagicMock(
                returncode=0,
                stdout=" M src/main.py\n?? tests/test_main.py",
                stderr="",
            ),
            # git diff --stat
            MagicMock(
                returncode=0,
                stdout="2 files changed, 100 insertions(+), 10 deletions(-)",
                stderr="",
            ),
        ]

        # Setup test mock
        mock_verifier = MagicMock()
        mock_verifier._run_tests.return_value = MagicMock(
            passed=True,
            test_count=5,
            output="5 passed in 0.3s",
        )
        mock_verifier_class.return_value = mock_verifier

        # Run git detection
        git_changes = detect_git_changes(tmp_path)
        assert git_changes is not None
        assert git_changes.has_changes is True
        assert len(git_changes.files_modified) == 1
        assert len(git_changes.files_added) == 1

        # Run test detection
        test_results = detect_test_results(tmp_path)
        assert test_results is not None
        assert test_results.tests_passed is True
        assert test_results.test_count == 5
