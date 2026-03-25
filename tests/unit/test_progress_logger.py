"""Tests for TaskProgressLogger (TASK-FIX-OBS2).

Verifies per-task progress logging for parallel execution diagnostics.
"""

import time
from pathlib import Path

import pytest

from guardkit.orchestrator.progress_logger import TaskProgressLogger, DEFAULT_LOG_INTERVAL


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a temporary repo root."""
    return tmp_path


class TestTaskProgressLogger:
    """Tests for TaskProgressLogger."""

    def test_creates_log_directory_and_file(self, tmp_repo):
        """Log directory and file are created on init."""
        logger = TaskProgressLogger(task_id="TASK-001", repo_root=tmp_repo)
        expected_dir = tmp_repo / ".guardkit" / "autobuild" / "TASK-001"
        assert expected_dir.exists()
        assert logger.log_path == expected_dir / "progress.log"
        logger.close()

    def test_log_start_writes_start_entry(self, tmp_repo):
        """log_start writes a START entry to the log file."""
        logger = TaskProgressLogger(task_id="TASK-001", repo_root=tmp_repo)
        logger.log_start("Player invocation turn 1")
        logger.close()

        content = logger.log_path.read_text()
        assert "START TASK-001: Player invocation turn 1" in content

    def test_log_snapshot_writes_snapshot_entry(self, tmp_repo):
        """log_snapshot writes a SNAPSHOT entry with all fields."""
        logger = TaskProgressLogger(task_id="TASK-002", repo_root=tmp_repo)
        logger.log_start("Player invocation")
        logger.log_snapshot(
            elapsed=60.0,
            phase="Player invocation",
            files_changed=3,
            last_tool="Edit",
        )
        logger.close()

        content = logger.log_path.read_text()
        assert "SNAPSHOT TASK-002" in content
        assert "elapsed=60s" in content
        assert "files_changed=3" in content
        assert "last_tool=Edit" in content

    def test_log_timeout_writes_timeout_entry(self, tmp_repo):
        """log_timeout writes a TIMEOUT entry with last state."""
        logger = TaskProgressLogger(task_id="TASK-003", repo_root=tmp_repo)
        logger.log_start("Player invocation")
        logger._current_phase = "Player invocation"
        logger._last_tool = "Bash"
        logger._files_changed = 5
        logger._snapshot_count = 4
        logger.log_timeout(elapsed=2400.0)
        logger.close()

        content = logger.log_path.read_text()
        assert "TIMEOUT TASK-003" in content
        assert "elapsed=2400s" in content
        assert "snapshots=4" in content

    def test_log_timeout_with_custom_state(self, tmp_repo):
        """log_timeout accepts custom last_state string."""
        logger = TaskProgressLogger(task_id="TASK-004", repo_root=tmp_repo)
        logger.log_timeout(elapsed=1200.0, last_state="stuck in test loop")
        logger.close()

        content = logger.log_path.read_text()
        assert "last_state=stuck in test loop" in content

    def test_log_complete_writes_complete_entry(self, tmp_repo):
        """log_complete writes a COMPLETE entry."""
        logger = TaskProgressLogger(task_id="TASK-005", repo_root=tmp_repo)
        logger.log_start("Player invocation")
        logger._snapshot_count = 10
        logger.log_complete(elapsed=600.0, decision="approved")
        logger.close()

        content = logger.log_path.read_text()
        assert "COMPLETE TASK-005" in content
        assert "decision=approved" in content
        assert "snapshots=10" in content

    def test_get_last_state_returns_formatted_state(self, tmp_repo):
        """get_last_state returns human-readable state."""
        logger = TaskProgressLogger(task_id="TASK-006", repo_root=tmp_repo)
        logger._current_phase = "Coach validation"
        logger._last_tool = "Read"
        logger._files_changed = 2
        logger._snapshot_count = 3

        state = logger.get_last_state()
        assert "phase=Coach validation" in state
        assert "last_tool=Read" in state
        assert "files_changed=2" in state
        logger.close()

    def test_get_last_state_no_data(self, tmp_repo):
        """get_last_state returns fallback when no state captured."""
        logger = TaskProgressLogger(task_id="TASK-007", repo_root=tmp_repo)
        state = logger.get_last_state()
        assert "files_changed=0" in state
        assert "snapshots=0" in state
        logger.close()

    def test_default_interval(self, tmp_repo):
        """Default interval is 60 seconds."""
        logger = TaskProgressLogger(task_id="TASK-008", repo_root=tmp_repo)
        assert logger.interval == DEFAULT_LOG_INTERVAL
        assert logger.interval == 60
        logger.close()

    def test_custom_interval(self, tmp_repo):
        """Custom interval is respected."""
        logger = TaskProgressLogger(task_id="TASK-009", repo_root=tmp_repo, interval=30)
        assert logger.interval == 30
        logger.close()

    def test_context_manager(self, tmp_repo):
        """Works as a context manager."""
        with TaskProgressLogger(task_id="TASK-010", repo_root=tmp_repo) as logger:
            logger.log_start("test phase")
            logger.log_snapshot(elapsed=60, phase="test phase")
        # File should be closed after exiting context
        assert logger._file.closed

    def test_multiple_snapshots(self, tmp_repo):
        """Multiple snapshots are all written."""
        logger = TaskProgressLogger(task_id="TASK-011", repo_root=tmp_repo)
        logger.log_start("Player invocation")
        for i in range(1, 4):
            logger.log_snapshot(
                elapsed=60.0 * i,
                phase="Player invocation",
                files_changed=i,
            )
        logger.close()

        content = logger.log_path.read_text()
        assert content.count("SNAPSHOT") == 3
        assert logger._snapshot_count == 3

    def test_appends_to_existing_file(self, tmp_repo):
        """Logger appends to existing log file (e.g., across SDK invocations)."""
        log_dir = tmp_repo / ".guardkit" / "autobuild" / "TASK-012"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "progress.log"
        log_file.write_text("previous content\n")

        logger = TaskProgressLogger(task_id="TASK-012", repo_root=tmp_repo)
        logger.log_start("new phase")
        logger.close()

        content = log_file.read_text()
        assert "previous content" in content
        assert "START TASK-012" in content

    def test_close_is_idempotent(self, tmp_repo):
        """Calling close() multiple times doesn't raise."""
        logger = TaskProgressLogger(task_id="TASK-013", repo_root=tmp_repo)
        logger.close()
        logger.close()  # Should not raise

    def test_write_after_close_is_safe(self, tmp_repo):
        """Writing after close doesn't crash (graceful degradation)."""
        logger = TaskProgressLogger(task_id="TASK-014", repo_root=tmp_repo)
        logger.close()
        # Should not raise
        logger.log_start("late start")
        logger.log_snapshot(elapsed=60, phase="late phase")
