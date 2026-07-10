"""
Integration tests for WorktreeManager archival (TASK-OBS-80FE).

These tests verify that WorktreeManager.cleanup() properly archives artifacts
before removing worktrees.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from guardkit.worktrees.archive import ArchiveResult
from guardkit.worktrees.manager import SubprocessExecutor, Worktree, WorktreeManager


class TestWorktreeManagerArchiveIntegration:
    """Test WorktreeManager cleanup with archival."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create temporary repository."""
        repo = tmp_path / "repo"
        repo.mkdir()

        # Initialize as git repo
        subprocess_executor = SubprocessExecutor()
        subprocess_executor.run(
            ["git", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True
        )
        subprocess_executor.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True
        )
        subprocess_executor.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True
        )

        # Create initial commit
        (repo / "README.md").write_text("Test repo")
        subprocess_executor.run(
            ["git", "add", "README.md"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True
        )
        subprocess_executor.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True
        )

        return repo

    @pytest.fixture
    def worktree_with_artifacts(self, temp_repo, tmp_path):
        """Create worktree with sample artifacts."""
        # Create worktree structure
        worktree_path = temp_repo / ".guardkit" / "worktrees" / "TASK-TEST-001"
        worktree_path.mkdir(parents=True)

        # Create artifacts
        autobuild = worktree_path / ".guardkit" / "autobuild" / "TASK-TEST-001"
        autobuild.mkdir(parents=True)

        (autobuild / "player_turn_1.json").write_text('{"turn": 1}')
        (autobuild / "coach_turn_1.json").write_text('{"decision": "approve"}')
        (autobuild / "task_work_results.json").write_text('{"status": "complete"}')

        # Create feature-level baseline.json
        (worktree_path / ".guardkit" / "autobuild" / "baseline.json").write_text(
            '{"baseline": "green"}'
        )

        return worktree_path

    @pytest.fixture
    def mock_executor(self):
        """Create mock command executor."""
        executor = Mock()
        executor.run = Mock(return_value=Mock(returncode=0))
        return executor

    def test_cleanup_archives_before_removal(
        self,
        temp_repo,
        worktree_with_artifacts,
        mock_executor,
        tmp_path,
        caplog
    ):
        """Test that cleanup archives artifacts before worktree removal (AC-1)."""
        caplog.set_level(logging.INFO)

        # Create manager with custom archive root
        archive_root = tmp_path / "archive"
        with patch("guardkit.worktrees.manager.get_archive_root_from_env") as mock_env:
            mock_env.return_value = archive_root

            manager = WorktreeManager(
                repo_root=temp_repo,
                executor=mock_executor
            )

            worktree = Worktree(
                task_id="TASK-TEST-001",
                path=worktree_with_artifacts,
                branch_name="autobuild/TASK-TEST-001",
                base_branch="main"
            )

            # Run cleanup
            manager.cleanup(worktree, force=True)

        # Verify artifacts were archived
        archive_path = archive_root / "TASK-TEST-001"
        assert archive_path.exists()

        # Verify specific expected files (AC-1)
        task_archive = archive_path / "TASK-TEST-001"
        assert (task_archive / "player_turn_1.json").exists()
        assert (task_archive / "coach_turn_1.json").exists()
        assert (task_archive / "task_work_results.json").exists()

        # Verify baseline.json (AC-3)
        assert (archive_path / "baseline.json").exists()

        # Verify git commands were called after archival
        assert mock_executor.run.call_count >= 2  # worktree remove + branch delete

        # Verify logging
        assert "Archived" in caplog.text
        assert "artifact files" in caplog.text

    def test_cleanup_proceeds_on_archive_failure(
        self,
        temp_repo,
        worktree_with_artifacts,
        mock_executor,
        caplog
    ):
        """Test that cleanup proceeds even if archival fails (AC-4)."""
        caplog.set_level(logging.WARNING)

        # Set unwritable archive root
        with patch("guardkit.worktrees.manager.get_archive_root_from_env") as mock_env:
            mock_env.return_value = Path("/nonexistent/readonly/path")

            manager = WorktreeManager(
                repo_root=temp_repo,
                executor=mock_executor
            )

            worktree = Worktree(
                task_id="TASK-TEST-001",
                path=worktree_with_artifacts,
                branch_name="autobuild/TASK-TEST-001",
                base_branch="main"
            )

            # Cleanup should not raise despite archive failure
            manager.cleanup(worktree, force=True)

        # Verify warning was logged (AC-4)
        assert "Failed to archive artifacts" in caplog.text
        assert "Proceeding with cleanup" in caplog.text

        # Verify git commands were still called
        assert mock_executor.run.call_count >= 2

    def test_archive_root_outside_repo(self, temp_repo, tmp_path):
        """Test that archive root is always outside repo (AC-2)."""
        with patch("guardkit.worktrees.manager.get_archive_root_from_env") as mock_env:
            # Try to set archive inside repo (should be rejected)
            inside_repo = temp_repo / "archive"
            mock_env.return_value = inside_repo

            manager = WorktreeManager(repo_root=temp_repo)

            # Archive path should fall back to outside repo
            # (verified by checking archiver's root in cleanup)
            worktree_path = temp_repo / ".guardkit" / "worktrees" / "TASK-TEST"
            worktree_path.mkdir(parents=True)

            # Create autobuild dir
            autobuild = worktree_path / ".guardkit" / "autobuild" / "TASK-TEST"
            autobuild.mkdir(parents=True)
            (autobuild / "test.json").write_text("{}")

            worktree = Worktree(
                task_id="TASK-TEST",
                path=worktree_path,
                branch_name="autobuild/TASK-TEST",
                base_branch="main"
            )

            # Mock git commands
            with patch.object(manager, "_run_git"):
                manager.cleanup(worktree, force=True)

            # Verify archive is NOT inside repo
            # (fallback to ~/.guardkit/archive/<repo-name>)
            expected_archive = Path.home() / ".guardkit" / "archive" / temp_repo.name
            archive_task = expected_archive / "TASK-TEST"
            assert archive_task.exists()

    def test_archive_includes_sdk_debug(
        self,
        temp_repo,
        mock_executor,
        tmp_path
    ):
        """Test that sdk_debug directories are archived."""
        # Create worktree with sdk_debug
        worktree_path = temp_repo / ".guardkit" / "worktrees" / "TASK-DEBUG"
        worktree_path.mkdir(parents=True)

        autobuild = worktree_path / ".guardkit" / "autobuild" / "TASK-DEBUG"
        autobuild.mkdir(parents=True)

        # Create sdk_debug structure
        sdk_debug = autobuild / "sdk_debug" / "turn_1"
        sdk_debug.mkdir(parents=True)
        (sdk_debug / "request.json").write_text('{"request": "data"}')
        (sdk_debug / "response.json").write_text('{"response": "data"}')

        archive_root = tmp_path / "archive"
        with patch("guardkit.worktrees.manager.get_archive_root_from_env") as mock_env:
            mock_env.return_value = archive_root

            manager = WorktreeManager(
                repo_root=temp_repo,
                executor=mock_executor
            )

            worktree = Worktree(
                task_id="TASK-DEBUG",
                path=worktree_path,
                branch_name="autobuild/TASK-DEBUG",
                base_branch="main"
            )

            manager.cleanup(worktree, force=True)

        # Verify sdk_debug was archived
        sdk_archive = archive_root / "TASK-DEBUG" / "TASK-DEBUG" / "sdk_debug" / "turn_1"
        assert sdk_archive.exists()
        assert (sdk_archive / "request.json").exists()
        assert (sdk_archive / "response.json").exists()

    def test_archive_includes_rollback_archive(
        self,
        temp_repo,
        mock_executor,
        tmp_path
    ):
        """Test that _rollback_archive directories are archived."""
        # Create worktree with rollback archive
        worktree_path = temp_repo / ".guardkit" / "worktrees" / "TASK-ROLLBACK"
        worktree_path.mkdir(parents=True)

        autobuild = worktree_path / ".guardkit" / "autobuild" / "TASK-ROLLBACK"
        autobuild.mkdir(parents=True)

        # Create rollback archive
        rollback = autobuild / "_rollback_archive"
        rollback.mkdir()
        (rollback / "checkpoint_1.json").write_text('{"checkpoint": 1}')

        archive_root = tmp_path / "archive"
        with patch("guardkit.worktrees.manager.get_archive_root_from_env") as mock_env:
            mock_env.return_value = archive_root

            manager = WorktreeManager(
                repo_root=temp_repo,
                executor=mock_executor
            )

            worktree = Worktree(
                task_id="TASK-ROLLBACK",
                path=worktree_path,
                branch_name="autobuild/TASK-ROLLBACK",
                base_branch="main"
            )

            manager.cleanup(worktree, force=True)

        # Verify rollback archive was archived
        rollback_archive = (
            archive_root / "TASK-ROLLBACK" / "TASK-ROLLBACK" / "_rollback_archive"
        )
        assert rollback_archive.exists()
        assert (rollback_archive / "checkpoint_1.json").exists()
