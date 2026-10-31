"""Unit tests for state detection module.

Tests git-based and test-based detection functions for partial work recovery.

Coverage Target: >=85%
Test Count: 25+ tests
"""

import subprocess
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.state_detection import (
    GitChangesSummary,
    TestResultsSummary,
    detect_git_changes,
    _parse_git_status,
    _parse_diff_stats,
    _get_diff_stats,
    GIT_COMMAND_TIMEOUT_SECONDS,
    DIFF_COMMAND_TIMEOUT_SECONDS,
)
from guardkit.orchestrator.task_work_scope import ScopeUnavailable
from tests.task_scope_fixtures import admitted_task, git


@contextmanager
def _admitted_repo(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "state@example.invalid")
    git(root, "config", "user.name", "State Fixture")
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("value = 1\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture source")
    with admitted_task(root, "TASK-STATE", register=True) as (_, scope):
        yield root, scope


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
        """Unscoped paths refuse attribution instead of looking clean."""
        with pytest.raises(ScopeUnavailable, match="No trusted admitted task scope"):
            detect_git_changes(tmp_path / "nonexistent")

    def test_no_changes_detected(self, tmp_path: Path):
        with _admitted_repo(tmp_path) as (root, scope):
            result = detect_git_changes(root, scope)
        assert result is not None
        assert result.has_changes is False

    def test_modified_files_detected(self, tmp_path: Path):
        with _admitted_repo(tmp_path) as (root, scope):
            (root / "src" / "main.py").write_text("value = 2\n")
            (root / "src" / "utils.py").write_text("helper = 1\n")
            result = detect_git_changes(root, scope)
        assert result.files_modified == ["src/main.py"]
        assert result.files_added == ["src/utils.py"]

    def test_new_files_detected(self, tmp_path: Path):
        with _admitted_repo(tmp_path) as (root, scope):
            (root / "tests").mkdir()
            (root / "src" / "new_file.py").write_text("new = 1\n")
            (root / "tests" / "test_new.py").write_text("def test_new(): pass\n")
            result = detect_git_changes(root, scope)
        assert result.files_added == ["src/new_file.py", "tests/test_new.py"]

    @pytest.mark.parametrize(
        "error",
        [
            RuntimeError("fatal: not a git repository"),
            subprocess.TimeoutExpired(cmd="git", timeout=GIT_COMMAND_TIMEOUT_SECONDS),
            FileNotFoundError("git"),
        ],
        ids=["git-status-fails", "git-status-timeout", "git-not-found"],
    )
    def test_git_inventory_failure_is_not_an_empty_diff(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
    ):
        with _admitted_repo(tmp_path) as (root, scope):
            from guardkit.orchestrator import task_work_scope

            with monkeypatch.context() as scoped_patch:
                scoped_patch.setattr(
                    task_work_scope, "_git", MagicMock(side_effect=error)
                )
                with pytest.raises(type(error)):
                    detect_git_changes(root, scope)


# ============================================================================
# 7. Integration Tests
# ============================================================================


class TestStateDetectionIntegration:
    """Integration tests for state detection."""

    def test_full_detection_workflow(self, tmp_path: Path):
        """Detection reports what git shows; no tests are run (1 November
        2026: the pytest run through CoachVerifier was removed)."""

        with _admitted_repo(tmp_path) as (root, scope):
            (root / "src" / "main.py").write_text("value = 2\n")
            (root / "tests").mkdir()
            (root / "tests" / "test_main.py").write_text("def test_main(): pass\n")
            git_changes = detect_git_changes(root, scope)
        assert git_changes is not None
        assert git_changes.has_changes is True
        assert len(git_changes.files_modified) == 1
        assert len(git_changes.files_added) == 1
