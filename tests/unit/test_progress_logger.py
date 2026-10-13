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


# ---------------------------------------------------------------------------
# 13 October 2026, first web fixture proof: every snapshot of a five-turn task
# read files_changed=0, because the local harness hands over its tool events
# only after the run ends and the event counter moves only as they arrive.
# The snapshot now reads the same git measurement the turn record uses.
# ---------------------------------------------------------------------------


def _lines(logger: TaskProgressLogger, kind: str) -> list:
    """The log's lines of one kind, with the timestamp taken off."""
    return [
        line.split("] ", 1)[1]
        for line in logger.log_path.read_text().splitlines()
        if f"] {kind} " in line
    ]


class TestGitMeasuredFilesChanged:
    def test_snapshot_uses_the_git_measurement_when_events_are_buffered(
        self, tmp_repo
    ):
        logger = TaskProgressLogger(
            task_id="TASK-GIT", repo_root=tmp_repo, measure_files_changed=lambda: 2
        )
        logger.log_start("Player invocation")
        # The event counter is still at its starting value of 0.
        logger.log_snapshot(
            elapsed=60.0, phase="Player invocation", files_changed=0
        )
        logger.close()

        assert _lines(logger, "SNAPSHOT") == [
            "SNAPSHOT TASK-GIT: elapsed=60s, phase=Player invocation, "
            "files_changed=2 (git)"
        ]

    def test_with_no_measurement_the_snapshot_is_unchanged(self, tmp_repo):
        """Byte-identical to the line written before the measurement existed
        (passes before and after)."""
        logger = TaskProgressLogger(task_id="TASK-SAME", repo_root=tmp_repo)
        logger.log_start("Player invocation")
        logger.log_snapshot(
            elapsed=60.0, phase="Player invocation", files_changed=3, last_tool="Edit"
        )
        logger.close()

        assert _lines(logger, "SNAPSHOT") == [
            "SNAPSHOT TASK-SAME: elapsed=60s, phase=Player invocation, "
            "files_changed=3, last_tool=Edit"
        ]

    def test_a_measurement_that_cannot_answer_changes_nothing(self, tmp_repo):
        def broken() -> None:
            raise RuntimeError("git unavailable")

        logger = TaskProgressLogger(
            task_id="TASK-SAME", repo_root=tmp_repo, measure_files_changed=lambda: None
        )
        logger.log_start("Player invocation")
        logger.log_snapshot(
            elapsed=60.0, phase="Player invocation", files_changed=3, last_tool="Edit"
        )
        logger.set_files_changed_measure(broken)
        logger.log_snapshot(
            elapsed=60.0, phase="Player invocation", files_changed=3, last_tool="Edit"
        )
        logger.close()

        assert _lines(logger, "SNAPSHOT") == [
            "SNAPSHOT TASK-SAME: elapsed=60s, phase=Player invocation, "
            "files_changed=3, last_tool=Edit"
        ] * 2

    def test_a_turn_with_buffered_events_ends_with_the_git_count(self, tmp_path):
        """Through ``AutoBuildOrchestrator._execute_turn``: a stand-in Player
        writes one file and delivers no tool events until it returns. A
        snapshot taken while it runs (as the heartbeat would, with the event
        counter at 0) and the turn's closing line both carry the git count."""
        import subprocess
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, Mock, patch

        from guardkit.orchestrator.agent_invoker import AgentInvocationResult
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        worktree = tmp_path / "wt"
        worktree.mkdir()
        (worktree / "README.md").write_text("base\n")
        for args in (
            ["init", "--initial-branch=main"],
            ["add", "-A"],
            ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
             "commit", "-m", "base"],
        ):
            subprocess.run(["git", *args], cwd=worktree, check=True,
                           capture_output=True)

        progress = TaskProgressLogger(task_id="TASK-TURN", repo_root=worktree)

        # Every git command the orchestrator runs, and whether it ran while
        # the stand-in Player was working.
        import guardkit.orchestrator.autobuild as autobuild_module

        real_run = subprocess.run
        git_calls = []
        in_player = {"now": False}

        def git_command(cmd):
            """The git sub-command, past the helper's fixed options."""
            index = 1
            while index < len(cmd) and cmd[index].startswith("-"):
                index += 2 if cmd[index] in ("-c", "-C") else 1
            return cmd[index] if index < len(cmd) else None

        def recording_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and cmd and (cmd[0] == "git" or cmd[0].endswith("/git")):
                git_calls.append((in_player["now"], git_command(cmd), kwargs.get("env")))
            return real_run(cmd, *args, **kwargs)

        def player(*args, **kwargs):
            (worktree / "notes.go").write_text("package notes\n")
            in_player["now"] = True
            progress.log_snapshot(
                elapsed=60.0, phase="task-work implementation",
                files_changed=progress._files_changed,
            )
            in_player["now"] = False
            return AgentInvocationResult(
                task_id="TASK-TURN", turn=1, agent_type="player", success=True,
                report={"task_id": "TASK-TURN", "files_modified": [],
                        "files_created": ["notes.go"], "tests_written": []},
                duration_seconds=1.0,
            )

        coach = AgentInvocationResult(
            task_id="TASK-TURN", turn=1, agent_type="coach", success=True,
            report={"decision": "approve", "issues": [], "rationale": "ok"},
            duration_seconds=1.0,
        )
        invoker = Mock()
        invoker.invoke_player = AsyncMock()
        invoker.invoke_coach = AsyncMock()
        invoker._get_implementation_mode.return_value = "direct"
        manager = Mock()
        manager.worktrees_dir = worktree
        orch = AutoBuildOrchestrator(
            repo_root=worktree,
            max_turns=5,
            worktree_manager=manager,
            agent_invoker=invoker,
            progress_display=MagicMock(),
            enable_pre_loop=False,
            enable_checkpoints=False,
            progress_logger=progress,
        )
        with patch.object(orch, "_invoke_player_safely", side_effect=player), \
                patch.object(orch, "_invoke_coach_safely", return_value=coach), \
                patch.object(autobuild_module.subprocess, "run", side_effect=recording_run):
            orch._execute_turn(
                turn=1, task_id="TASK-TURN", requirements="Add notes",
                worktree=SimpleNamespace(path=worktree), previous_feedback=None,
            )
        # Cleared before the Coach phase: later snapshots read the counter.
        progress.log_snapshot(elapsed=120.0, phase="coach", files_changed=0)
        progress.close()

        snapshots = _lines(progress, "SNAPSHOT")
        assert snapshots[0].endswith("files_changed=1 (git)")
        assert snapshots[-1].endswith("files_changed=0")
        assert _lines(progress, "TURN_CHANGES") == [
            "TURN_CHANGES TASK-TURN: turn=1, files_changed=1 (git)"
        ]
        # While the Player works, the snapshot's git commands never take the
        # index lock; the photographs either side of the Player run as before.
        during = [(cmd, env) for now, cmd, env in git_calls if now]
        assert [cmd for cmd, _ in during] == ["status", "diff"]
        assert all(env["GIT_OPTIONAL_LOCKS"] == "0" for _, env in during)
        assert any(
            not now and "GIT_OPTIONAL_LOCKS" not in (env or {}) for now, _, env in git_calls
        )
