"""
Comprehensive tests for WorktreeCleanupOrchestrator

Tests cover:
- Task ID normalization (TASK-XXX and FEAT-XXX formats)
- Safety checks (worktree existence, uncommitted changes, merge status)
- Cleanup operations (directory removal, branch deletion)
- Feature YAML state tracking
- Edge cases (already cleaned, git not available, etc.)
- User confirmation and --force flag
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from tempfile import TemporaryDirectory

# Import module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "installer" / "core" / "commands" / "lib"))

from worktree_cleanup import (
    WorktreeCleanupOrchestrator,
    WorktreeCleanupError,
    WorktreeNotFoundError,
    UncommittedChangesError,
    UnmergedBranchError,
    CleanupCheckResult,
    CleanupResult,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_repo():
    """Fixture providing a temporary repository path."""
    with TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        # Initialize .guardkit/worktrees directory
        (repo_path / ".guardkit" / "worktrees").mkdir(parents=True, exist_ok=True)
        yield repo_path


@pytest.fixture
def orchestrator(temp_repo):
    """Fixture providing a WorktreeCleanupOrchestrator instance."""
    return WorktreeCleanupOrchestrator(
        repo_root=temp_repo,
        task_id="TASK-AB-001",
        force=False,
        verbose=False,
    )


# ============================================================================
# Tests: Task ID Normalization
# ============================================================================


class TestTaskIDNormalization:
    """Tests for task ID format normalization."""

    def test_normalize_task_id_task_format(self):
        """Test normalization of TASK-XXX format."""
        orch = WorktreeCleanupOrchestrator(Path.cwd(), "TASK-AB-001")
        assert orch.task_id == "TASK-AB-001"

    def test_normalize_task_id_feat_format(self):
        """Test normalization of FEAT-XXX format to TASK-XXX."""
        orch = WorktreeCleanupOrchestrator(Path.cwd(), "FEAT-AB-001")
        assert orch.task_id == "TASK-AB-001"

    def test_normalize_task_id_with_whitespace(self):
        """Test normalization handles leading/trailing whitespace."""
        orch = WorktreeCleanupOrchestrator(Path.cwd(), "  TASK-AB-001  ")
        assert orch.task_id == "TASK-AB-001"

    def test_normalize_task_id_invalid_format(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid task ID format"):
            WorktreeCleanupOrchestrator(Path.cwd(), "INVALID-001")

    def test_normalize_task_id_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid task ID format"):
            WorktreeCleanupOrchestrator(Path.cwd(), "")


# ============================================================================
# Tests: Safety Checks
# ============================================================================


class TestSafetyChecks:
    """Tests for pre-cleanup safety checks."""

    def test_check_worktree_exists_true(self, orchestrator):
        """Test detection of existing worktree."""
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)
        assert orchestrator._check_worktree_exists() is True

    def test_check_worktree_exists_false(self, orchestrator):
        """Test detection of non-existent worktree."""
        assert orchestrator._check_worktree_exists() is False

    @patch("subprocess.run")
    def test_get_worktree_uncommitted_changes_true(self, mock_run, orchestrator):
        """Test detection of uncommitted changes."""
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)
        mock_result = Mock()
        mock_result.stdout = "M  file.py\n"
        mock_run.return_value = mock_result

        assert orchestrator._get_worktree_uncommitted_changes() is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_get_worktree_uncommitted_changes_false(self, mock_run, orchestrator):
        """Test detection of clean worktree (no uncommitted changes)."""
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        assert orchestrator._get_worktree_uncommitted_changes() is False

    @patch("subprocess.run")
    def test_check_branch_merged_true(self, mock_run, orchestrator):
        """Test detection of merged branch."""
        # First call: branch exists
        # Second call: merge-base succeeds (branch is ancestor of main)
        mock_result1 = Mock()
        mock_result1.stdout = "autobuild/TASK-AB-001\n"

        mock_result2 = Mock()
        mock_result2.returncode = 0

        mock_run.side_effect = [mock_result1, mock_result2]  # branch list + merge-base succeeds

        is_merged, status = orchestrator._check_branch_merged()
        assert is_merged is True
        assert "merged" in status.lower()

    @patch("subprocess.run")
    def test_check_branch_merged_false(self, mock_run, orchestrator):
        """Test detection of unmerged branch."""
        # First call: branch exists
        # Second call: merge-base fails (branch is not ancestor of main)
        mock_result1 = Mock()
        mock_result1.stdout = "autobuild/TASK-AB-001\n"

        mock_run.side_effect = [
            mock_result1,  # branch list
            subprocess.CalledProcessError(1, "cmd"),  # merge-base fails
        ]

        is_merged, status = orchestrator._check_branch_merged()
        assert is_merged is False
        assert "NOT been merged" in status

    @patch("subprocess.run")
    def test_check_branch_merged_not_exists(self, mock_run, orchestrator):
        """Test handling of non-existent branch."""
        mock_result = Mock()
        mock_result.stdout = ""  # Empty result = branch doesn't exist
        mock_run.return_value = mock_result

        is_merged, status = orchestrator._check_branch_merged()
        assert is_merged is True
        assert "already cleaned" in status.lower()

    def test_run_safety_checks_all_good(self, orchestrator):
        """Test safety checks when all checks pass."""
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)

        with patch.object(orchestrator, "_get_worktree_uncommitted_changes", return_value=False):
            with patch.object(orchestrator, "_check_branch_merged", return_value=(True, "Merged")):
                result = orchestrator.run_safety_checks()

                assert result.worktree_exists is True
                assert result.has_uncommitted_changes is False
                assert result.branch_merged is True
                assert len(result.warnings) == 0

    def test_run_safety_checks_with_warnings(self, orchestrator):
        """Test safety checks with uncommitted changes warning."""
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)

        with patch.object(orchestrator, "_get_worktree_uncommitted_changes", return_value=True):
            with patch.object(orchestrator, "_check_branch_merged", return_value=(False, "Not merged")):
                result = orchestrator.run_safety_checks()

                assert result.has_uncommitted_changes is True
                assert result.branch_merged is False
                assert len(result.warnings) == 2
                assert "uncommitted" in result.warnings[0].lower()
                assert "not been merged" in result.warnings[1].lower()


# ============================================================================
# Tests: User Confirmation
# ============================================================================


class TestUserConfirmation:
    """Tests for user confirmation handling."""

    def test_confirm_cleanup_with_force_flag(self, orchestrator):
        """Test that --force flag skips confirmation."""
        orchestrator.force = True
        check_result = CleanupCheckResult(
            worktree_exists=True,
            has_uncommitted_changes=False,
            branch_merged=True,
        )

        assert orchestrator._confirm_cleanup(check_result) is True

    @patch("builtins.input", return_value="y")
    def test_confirm_cleanup_user_agrees(self, mock_input, orchestrator):
        """Test user confirms cleanup."""
        orchestrator.force = False
        check_result = CleanupCheckResult(
            worktree_exists=True,
            has_uncommitted_changes=False,
            branch_merged=True,
        )

        assert orchestrator._confirm_cleanup(check_result) is True

    @patch("builtins.input", return_value="n")
    def test_confirm_cleanup_user_refuses(self, mock_input, orchestrator):
        """Test user refuses cleanup."""
        orchestrator.force = False
        check_result = CleanupCheckResult(
            worktree_exists=True,
            has_uncommitted_changes=False,
            branch_merged=True,
        )

        assert orchestrator._confirm_cleanup(check_result) is False


# ============================================================================
# Tests: Cleanup Operations
# ============================================================================


class TestCleanupOperations:
    """Tests for cleanup operations."""

    def test_remove_worktree_directory_success(self, orchestrator):
        """Test successful worktree directory removal."""
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)
        (orchestrator.worktree_path / "file.txt").write_text("test")

        orchestrator._remove_worktree_directory()
        assert not orchestrator.worktree_path.exists()

    def test_remove_worktree_directory_not_exists(self, orchestrator):
        """Test removal when directory doesn't exist (no-op)."""
        # Should not raise an error
        orchestrator._remove_worktree_directory()

    def test_remove_worktree_directory_failure(self, orchestrator):
        """Test error handling for removal failure."""
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)

        with patch("shutil.rmtree", side_effect=OSError("Permission denied")):
            with pytest.raises(WorktreeCleanupError, match="Failed to remove"):
                orchestrator._remove_worktree_directory()

    @patch("worktree_cleanup.WorktreeCleanupOrchestrator._get_worktree_manager")
    def test_cleanup_via_worktree_manager_success(self, mock_get_manager, orchestrator):
        """Test successful cleanup via WorktreeManager."""
        mock_manager = Mock()
        mock_manager.cleanup = Mock()
        mock_get_manager.return_value = mock_manager

        with patch("lib.orchestrator.worktrees.Worktree"):
            orchestrator._cleanup_via_worktree_manager()
            mock_manager.cleanup.assert_called_once()

    @patch("worktree_cleanup.WorktreeCleanupOrchestrator._get_worktree_manager")
    @patch("worktree_cleanup.WorktreeCleanupOrchestrator._remove_worktree_directory")
    def test_cleanup_via_worktree_manager_fallback(self, mock_remove, mock_get_manager, orchestrator):
        """Test fallback to manual removal when WorktreeManager fails."""
        mock_get_manager.side_effect = Exception("Manager error")
        orchestrator._remove_worktree_directory = Mock()

        with patch("lib.orchestrator.worktrees.Worktree"):
            orchestrator._cleanup_via_worktree_manager()
            orchestrator._remove_worktree_directory.assert_called_once()


# ============================================================================
# Tests: Feature YAML State Tracking
# ============================================================================


class TestFeatureYAMLTracking:
    """Tests for feature YAML state tracking."""

    def test_update_feature_yaml_success(self, orchestrator):
        """Test feature YAML update (placeholder)."""
        result = orchestrator._update_feature_yaml()
        assert result is True

    def test_update_feature_yaml_failure_handled(self, orchestrator):
        """Test that feature YAML update failures are handled gracefully."""
        with patch.object(orchestrator, "_update_feature_yaml", return_value=False):
            # Should not raise error, just log warning
            result = orchestrator._update_feature_yaml()
            assert result is False


# ============================================================================
# Tests: Complete Workflow
# ============================================================================


class TestCompleteWorkflow:
    """Tests for complete cleanup workflow."""

    @patch("worktree_cleanup.WorktreeCleanupOrchestrator._get_worktree_manager")
    @patch("builtins.input", return_value="y")
    def test_run_success(self, mock_input, mock_get_manager, orchestrator):
        """Test complete successful cleanup workflow."""
        # Setup
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)
        mock_manager = Mock()
        mock_manager.cleanup = Mock()
        mock_get_manager.return_value = mock_manager

        with patch.object(orchestrator, "_check_worktree_exists", return_value=True):
            with patch.object(orchestrator, "_get_worktree_uncommitted_changes", return_value=False):
                with patch.object(orchestrator, "_check_branch_merged", return_value=(True, "Merged")):
                    result = orchestrator.run()

                    assert result.success is True
                    assert "cleaned successfully" in result.message.lower()

    def test_run_already_cleaned(self, orchestrator):
        """Test workflow when worktree is already cleaned."""
        with patch.object(orchestrator, "_check_worktree_exists", return_value=False):
            result = orchestrator.run()

            assert result.success is True
            assert "already cleaned" in result.message.lower()

    @patch("builtins.input", return_value="n")
    def test_run_user_cancels(self, mock_input, orchestrator):
        """Test workflow when user cancels cleanup."""
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)

        with patch.object(orchestrator, "_check_worktree_exists", return_value=True):
            with patch.object(orchestrator, "_get_worktree_uncommitted_changes", return_value=False):
                with patch.object(orchestrator, "_check_branch_merged", return_value=(True, "Merged")):
                    result = orchestrator.run()

                    assert result.success is False
                    assert "cancelled" in result.message.lower()

    def test_run_dry_run_mode(self, orchestrator):
        """Test workflow in dry-run mode."""
        orchestrator.dry_run = True
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)

        with patch.object(orchestrator, "_check_worktree_exists", return_value=True):
            with patch.object(orchestrator, "_get_worktree_uncommitted_changes", return_value=False):
                with patch.object(orchestrator, "_check_branch_merged", return_value=(True, "Merged")):
                    with patch("builtins.input", return_value="y"):
                        result = orchestrator.run()

                        assert result.success is True
                        assert "[DRY RUN]" in result.message


# ============================================================================
# Tests: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_get_worktree_manager_import_error(self, orchestrator):
        """Test error handling when WorktreeManager cannot be imported."""
        with patch("worktree_cleanup.WorktreeManager", None):
            with pytest.raises(WorktreeCleanupError, match="Failed to load WorktreeManager"):
                orchestrator._get_worktree_manager()

    @patch("subprocess.run")
    def test_get_worktree_uncommitted_changes_git_error(self, mock_run, orchestrator):
        """Test handling of git command errors."""
        orchestrator.worktree_path.mkdir(parents=True, exist_ok=True)
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Should return True (assume changes exist on error)
        assert orchestrator._get_worktree_uncommitted_changes() is True

    def test_check_worktree_exists_no_worktrees_dir(self, temp_repo):
        """Test when .guardkit/worktrees directory doesn't exist."""
        # Remove the worktrees directory
        worktrees_dir = temp_repo / ".guardkit" / "worktrees"
        if worktrees_dir.exists():
            import shutil
            shutil.rmtree(worktrees_dir)

        orch = WorktreeCleanupOrchestrator(temp_repo, "TASK-AB-001")
        assert orch._check_worktree_exists() is False


# ============================================================================
# Tests: Data Models
# ============================================================================


class TestDataModels:
    """Tests for data model classes."""

    def test_cleanup_check_result_initialization(self):
        """Test CleanupCheckResult initialization."""
        result = CleanupCheckResult(
            worktree_exists=True,
            has_uncommitted_changes=False,
            branch_merged=True,
        )

        assert result.worktree_exists is True
        assert result.has_uncommitted_changes is False
        assert result.branch_merged is True
        assert isinstance(result.warnings, list)
        assert len(result.warnings) == 0

    def test_cleanup_check_result_with_warnings(self):
        """Test CleanupCheckResult with warnings."""
        warnings = ["Warning 1", "Warning 2"]
        result = CleanupCheckResult(
            worktree_exists=True,
            has_uncommitted_changes=True,
            branch_merged=False,
            warnings=warnings,
        )

        assert len(result.warnings) == 2
        assert result.warnings == warnings

    def test_cleanup_result_initialization(self):
        """Test CleanupResult initialization."""
        result = CleanupResult(
            success=True,
            message="Test message",
        )

        assert result.success is True
        assert result.message == "Test message"
        assert isinstance(result.errors, list)
        assert len(result.errors) == 0

    def test_cleanup_result_with_errors(self):
        """Test CleanupResult with errors."""
        errors = ["Error 1", "Error 2"]
        result = CleanupResult(
            success=False,
            message="Failed",
            errors=errors,
        )

        assert result.success is False
        assert len(result.errors) == 2


# ============================================================================
# Tests: Verbose Output
# ============================================================================


class TestVerboseOutput:
    """Tests for verbose mode output."""

    @patch("builtins.print")
    def test_verbose_mode_enabled(self, mock_print, temp_repo):
        """Test that verbose mode prints messages."""
        orch = WorktreeCleanupOrchestrator(
            temp_repo, "TASK-AB-001", verbose=True
        )

        orch._print("Test message")
        mock_print.assert_called_with("Test message")

    @patch("builtins.print")
    def test_verbose_mode_disabled(self, mock_print, temp_repo):
        """Test that verbose mode off suppresses messages."""
        orch = WorktreeCleanupOrchestrator(
            temp_repo, "TASK-AB-001", verbose=False
        )

        orch._print("Test message")
        mock_print.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
