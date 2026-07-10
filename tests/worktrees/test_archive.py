"""
Tests for run artifact archival (TASK-OBS-80FE).

These tests verify:
- AC-1: Artifacts are archived with specific expected files
- AC-2: Archive root is outside repo working tree
- AC-3: baseline.json is archived at feature level
- AC-4: Archive failure logs WARNING and doesn't block
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from guardkit.worktrees.archive import (
    ArchiveResult,
    RunArtifactArchiver,
    get_archive_root_from_env,
)


class TestArchiveResult:
    """Test ArchiveResult dataclass."""

    def test_success_result(self):
        """Test successful archive result."""
        result = ArchiveResult(
            success=True,
            archive_path=Path("/tmp/archive/FEAT-ABC"),
            files_archived=10
        )

        assert result.success is True
        assert result.archive_path == Path("/tmp/archive/FEAT-ABC")
        assert result.files_archived == 10
        assert result.error is None

    def test_failure_result(self):
        """Test failed archive result."""
        result = ArchiveResult(
            success=False,
            error="Disk full"
        )

        assert result.success is False
        assert result.archive_path is None
        assert result.error == "Disk full"
        assert result.files_archived == 0


class TestGetArchiveRootFromEnv:
    """Test environment variable handling for archive root."""

    def test_env_var_set(self):
        """Test custom archive root from environment."""
        with patch.dict(os.environ, {"GUARDKIT_ARCHIVE_ROOT": "/custom/archive"}):
            result = get_archive_root_from_env()
            assert result == Path("/custom/archive").resolve()

    def test_env_var_not_set(self):
        """Test returns None when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_archive_root_from_env()
            assert result is None


class TestRunArtifactArchiver:
    """Test RunArtifactArchiver class."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repository structure."""
        repo = tmp_path / "repo"
        repo.mkdir()
        return repo

    @pytest.fixture
    def temp_worktree(self, temp_repo):
        """Create a temporary worktree with artifacts."""
        worktree = temp_repo / ".guardkit" / "worktrees" / "FEAT-ABC"
        worktree.mkdir(parents=True)

        # Create autobuild directory structure
        autobuild = worktree / ".guardkit" / "autobuild"
        autobuild.mkdir(parents=True)

        # Create task directory with artifacts
        task_dir = autobuild / "TASK-ABC-001"
        task_dir.mkdir()

        # Create sample artifacts (AC-1: specific expected files)
        (task_dir / "player_turn_1.json").write_text('{"turn": 1}')
        (task_dir / "coach_turn_1.json").write_text('{"decision": "approve"}')
        (task_dir / "task_work_results.json").write_text('{"status": "complete"}')

        # Create sdk_debug directory
        sdk_debug = task_dir / "sdk_debug" / "turn_1"
        sdk_debug.mkdir(parents=True)
        (sdk_debug / "request.json").write_text('{}')

        # Create feature-level baseline.json (AC-3)
        (autobuild / "baseline.json").write_text('{"baseline": "data"}')

        return worktree

    @pytest.fixture
    def archiver(self, temp_repo, tmp_path):
        """Create archiver with custom archive root."""
        archive_root = tmp_path / "archive"
        return RunArtifactArchiver(
            repo_root=temp_repo,
            archive_root=archive_root
        )

    def test_default_archive_root(self, temp_repo):
        """Test default archive root location."""
        archiver = RunArtifactArchiver(repo_root=temp_repo)

        expected_root = Path.home() / ".guardkit" / "archive" / temp_repo.name
        assert archiver.archive_root == expected_root

    def test_custom_archive_root(self, temp_repo, tmp_path):
        """Test custom archive root."""
        custom_root = tmp_path / "custom_archive"
        archiver = RunArtifactArchiver(
            repo_root=temp_repo,
            archive_root=custom_root
        )

        assert archiver.archive_root == custom_root.resolve()

    def test_archive_root_inside_repo_uses_fallback(self, temp_repo):
        """Test that archive root inside repo triggers fallback (AC-2)."""
        # Try to set archive root inside repo
        inside_repo = temp_repo / "archive"
        archiver = RunArtifactArchiver(
            repo_root=temp_repo,
            archive_root=inside_repo
        )

        # Should fall back to default
        expected_root = Path.home() / ".guardkit" / "archive" / temp_repo.name
        assert archiver.archive_root == expected_root

    def test_is_inside_repo(self, temp_repo):
        """Test repository containment check."""
        archiver = RunArtifactArchiver(repo_root=temp_repo)

        # Path inside repo
        inside = temp_repo / "subdir" / "file.txt"
        assert archiver._is_inside_repo(inside) is True

        # Path outside repo
        outside = Path("/tmp/other")
        assert archiver._is_inside_repo(outside) is False

    def test_archive_worktree_artifacts_success(
        self,
        archiver,
        temp_worktree,
        tmp_path
    ):
        """Test successful worktree artifact archival (AC-1)."""
        result = archiver.archive_worktree_artifacts(
            worktree_path=temp_worktree,
            feature_or_task_id="FEAT-ABC"
        )

        assert result.success is True
        assert result.files_archived > 0
        assert result.error is None

        # Verify archive path exists
        archive_path = tmp_path / "archive" / "FEAT-ABC"
        assert archive_path.exists()

        # Verify specific expected files (AC-1)
        task_archive = archive_path / "TASK-ABC-001"
        assert (task_archive / "player_turn_1.json").exists()
        assert (task_archive / "coach_turn_1.json").exists()
        assert (task_archive / "task_work_results.json").exists()
        assert (task_archive / "sdk_debug" / "turn_1" / "request.json").exists()

        # Verify baseline.json at feature level (AC-3)
        assert (archive_path / "baseline.json").exists()

    def test_archive_worktree_artifacts_no_autobuild(self, archiver, temp_repo):
        """Test archival when no autobuild directory exists."""
        worktree = temp_repo / ".guardkit" / "worktrees" / "FEAT-XYZ"
        worktree.mkdir(parents=True)

        result = archiver.archive_worktree_artifacts(
            worktree_path=worktree,
            feature_or_task_id="FEAT-XYZ"
        )

        # Should succeed with 0 files
        assert result.success is True
        assert result.files_archived == 0

    def test_archive_worktree_artifacts_failure(self, archiver, temp_worktree):
        """Test archive failure handling (AC-4)."""
        # Make archive_root unwritable
        archiver.archive_root = Path("/nonexistent/readonly/path")

        result = archiver.archive_worktree_artifacts(
            worktree_path=temp_worktree,
            feature_or_task_id="FEAT-ABC"
        )

        # Should fail gracefully (AC-4)
        assert result.success is False
        assert result.error is not None
        assert "Failed to archive" in result.error

    def test_archive_main_repo_events(self, archiver, temp_repo, tmp_path):
        """Test archival of events.jsonl from main repo."""
        # Create events file in main repo
        autobuild = temp_repo / ".guardkit" / "autobuild" / "FEAT-ABC"
        autobuild.mkdir(parents=True)
        events_file = autobuild / "events.jsonl"
        events_file.write_text('{"event": "test"}\n')

        result = archiver.archive_main_repo_events(
            feature_or_task_id="FEAT-ABC"
        )

        assert result.success is True
        assert result.files_archived == 1

        # Verify archived events file
        archive_path = tmp_path / "archive" / "FEAT-ABC" / "events.jsonl"
        assert archive_path.exists()
        assert archive_path.read_text() == '{"event": "test"}\n'

    def test_archive_main_repo_events_no_file(self, archiver):
        """Test archival when no events file exists."""
        result = archiver.archive_main_repo_events(
            feature_or_task_id="FEAT-ABC"
        )

        # Should succeed with 0 files
        assert result.success is True
        assert result.files_archived == 0

    def test_archive_task_artifacts(self, archiver, temp_worktree, tmp_path):
        """Test incremental task artifact archival."""
        result = archiver.archive_task_artifacts(
            worktree_path=temp_worktree,
            task_id="TASK-ABC-001",
            feature_id="FEAT-ABC"
        )

        assert result.success is True
        assert result.files_archived > 0

        # Verify task artifacts in archive
        archive_path = tmp_path / "archive" / "FEAT-ABC" / "TASK-ABC-001"
        assert archive_path.exists()
        assert (archive_path / "player_turn_1.json").exists()

    def test_archive_task_artifacts_no_feature_id(
        self,
        archiver,
        temp_worktree,
        tmp_path
    ):
        """Test task archival without feature ID."""
        result = archiver.archive_task_artifacts(
            worktree_path=temp_worktree,
            task_id="TASK-ABC-001"
        )

        assert result.success is True

        # Should use task_id as archive root
        archive_path = tmp_path / "archive" / "TASK-ABC-001" / "TASK-ABC-001"
        assert archive_path.exists()

    def test_copy_with_structure_directory(self, archiver, tmp_path):
        """Test directory copying with structure preservation."""
        # Create source directory with nested structure
        src = tmp_path / "source"
        src.mkdir()
        (src / "file1.txt").write_text("content1")
        subdir = src / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content2")

        dest = tmp_path / "dest"

        files_copied = archiver._copy_with_structure(src, dest, "test")

        assert files_copied == 2
        assert dest.exists()
        assert (dest / "file1.txt").read_text() == "content1"
        assert (dest / "subdir" / "file2.txt").read_text() == "content2"

    def test_copy_with_structure_single_file(self, archiver, tmp_path):
        """Test single file copying."""
        src = tmp_path / "source.txt"
        src.write_text("content")

        dest = tmp_path / "dest.txt"

        files_copied = archiver._copy_with_structure(src, dest, "test")

        assert files_copied == 1
        assert dest.read_text() == "content"

    def test_copy_with_structure_nonexistent_source(self, archiver, tmp_path):
        """Test copying from nonexistent source."""
        src = tmp_path / "nonexistent"
        dest = tmp_path / "dest"

        files_copied = archiver._copy_with_structure(src, dest, "test")

        assert files_copied == 0
        assert not dest.exists()
