"""Unit tests for TASK-FIX-VL01: Path-hardened player report recovery.

Tests that _create_player_report_from_task_work() searches for the agent-written
player report at both the worktree path and the repo root fallback path.

Coverage Target: 100% of Fix 2 recovery block + _resolve_repo_root()
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.paths import TaskArtifactPaths


# ==================== Test Fixtures ====================


@pytest.fixture
def repo_root(tmp_path):
    """Create a temporary repo root directory."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".guardkit" / "autobuild").mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def worktree_in_repo(repo_root):
    """Create a worktree under the repo root's .guardkit/worktrees/ convention."""
    wt = repo_root / ".guardkit" / "worktrees" / "TASK-001"
    wt.mkdir(parents=True, exist_ok=True)
    (wt / ".guardkit" / "autobuild").mkdir(parents=True, exist_ok=True)
    (wt / ".claude" / "task-plans").mkdir(parents=True, exist_ok=True)
    (wt / "docs" / "state").mkdir(parents=True, exist_ok=True)
    return wt


@pytest.fixture
def standalone_worktree(tmp_path):
    """Create a standalone worktree (no .guardkit/worktrees/ convention)."""
    wt = tmp_path / "standalone_worktree"
    wt.mkdir()
    (wt / ".guardkit" / "autobuild").mkdir(parents=True, exist_ok=True)
    (wt / ".claude" / "task-plans").mkdir(parents=True, exist_ok=True)
    (wt / "docs" / "state").mkdir(parents=True, exist_ok=True)
    return wt


def _make_invoker(worktree_path: Path) -> AgentInvoker:
    """Create an AgentInvoker with the given worktree path."""
    return AgentInvoker(
        worktree_path=worktree_path,
        max_turns_per_agent=5,
        sdk_timeout_seconds=30,
    )


def _write_player_report(base_path: Path, task_id: str, turn: int, data: dict):
    """Write a player report JSON file at the expected location."""
    report_path = TaskArtifactPaths.player_report_path(task_id, turn, base_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(data))
    return report_path


def _make_task_work_result(success: bool = True):
    """Create a minimal mock TaskWorkResult."""
    result = Mock()
    result.success = success
    result.output = ""
    return result


# ==================== _resolve_repo_root Tests ====================


class TestResolveRepoRoot:
    """Tests for AgentInvoker._resolve_repo_root()."""

    def test_returns_repo_root_for_worktree_in_guardkit(self, worktree_in_repo, repo_root):
        """When worktree is under .guardkit/worktrees/, returns the repo root."""
        invoker = _make_invoker(worktree_in_repo)
        resolved = invoker._resolve_repo_root()
        assert resolved is not None
        assert resolved == repo_root

    def test_returns_none_for_standalone_worktree(self, standalone_worktree):
        """When worktree is NOT under .guardkit/worktrees/, returns None."""
        invoker = _make_invoker(standalone_worktree)
        resolved = invoker._resolve_repo_root()
        assert resolved is None

    def test_returns_none_when_worktree_is_repo_root(self, repo_root):
        """When worktree_path IS the repo root, returns None (no fallback needed)."""
        invoker = _make_invoker(repo_root)
        resolved = invoker._resolve_repo_root()
        assert resolved is None


# ==================== Player Report Recovery Tests ====================


class TestPlayerReportRecovery:
    """Tests for Fix 2 path-hardened recovery in _create_player_report_from_task_work()."""

    def test_recovery_from_worktree_path(self, standalone_worktree):
        """When player report exists at worktree path, recovery works as before."""
        task_id = "TASK-001"
        turn = 1
        invoker = _make_invoker(standalone_worktree)

        # Write player report at the worktree path (normal case)
        agent_data = {
            "completion_promises": [
                {"promise": "Implemented feature X", "status": "kept"}
            ],
            "requirements_addressed": ["AC-001"],
            "requirements_remaining": [],
        }
        _write_player_report(standalone_worktree, task_id, turn, agent_data)

        # Call the method
        result = _make_task_work_result()
        invoker._create_player_report_from_task_work(task_id, turn, result)

        # Read back the written report
        report_path = TaskArtifactPaths.player_report_path(
            task_id, turn, standalone_worktree
        )
        report = json.loads(report_path.read_text())

        assert len(report["completion_promises"]) == 1
        assert report["completion_promises"][0]["promise"] == "Implemented feature X"
        assert report["requirements_addressed"] == ["AC-001"]

    def test_recovery_from_repo_root_fallback(self, worktree_in_repo, repo_root):
        """When player report exists at repo root (not worktree), fallback recovers it."""
        task_id = "TASK-001"
        turn = 1
        invoker = _make_invoker(worktree_in_repo)

        # Write player report ONLY at the repo root (agent wrote to wrong location)
        agent_data = {
            "completion_promises": [
                {"promise": "Fixed bug Y", "status": "kept"}
            ],
            "requirements_addressed": ["AC-002"],
            "requirements_remaining": ["AC-003"],
        }
        _write_player_report(repo_root, task_id, turn, agent_data)

        # Verify worktree path does NOT have the report
        worktree_report = TaskArtifactPaths.player_report_path(
            task_id, turn, worktree_in_repo
        )
        assert not worktree_report.exists()

        # Call the method
        result = _make_task_work_result()
        invoker._create_player_report_from_task_work(task_id, turn, result)

        # Read back the written report (should be at worktree path now)
        report = json.loads(worktree_report.read_text())

        assert len(report["completion_promises"]) == 1
        assert report["completion_promises"][0]["promise"] == "Fixed bug Y"
        assert report["requirements_addressed"] == ["AC-002"]
        assert report["requirements_remaining"] == ["AC-003"]

    def test_worktree_path_takes_precedence_over_repo_root(
        self, worktree_in_repo, repo_root
    ):
        """When both paths have reports, worktree path report is used."""
        task_id = "TASK-001"
        turn = 1
        invoker = _make_invoker(worktree_in_repo)

        # Write different reports at both locations
        worktree_data = {
            "completion_promises": [
                {"promise": "Worktree version", "status": "kept"}
            ],
            "requirements_addressed": ["AC-WORKTREE"],
            "requirements_remaining": [],
        }
        repo_root_data = {
            "completion_promises": [
                {"promise": "Repo root version", "status": "kept"}
            ],
            "requirements_addressed": ["AC-REPOROOT"],
            "requirements_remaining": [],
        }
        _write_player_report(worktree_in_repo, task_id, turn, worktree_data)
        _write_player_report(repo_root, task_id, turn, repo_root_data)

        # Call the method
        result = _make_task_work_result()
        invoker._create_player_report_from_task_work(task_id, turn, result)

        # Read back — should have worktree version (checked first)
        report_path = TaskArtifactPaths.player_report_path(
            task_id, turn, worktree_in_repo
        )
        report = json.loads(report_path.read_text())

        assert report["completion_promises"][0]["promise"] == "Worktree version"
        assert report["requirements_addressed"] == ["AC-WORKTREE"]

    def test_no_report_at_either_path_proceeds_without_error(
        self, worktree_in_repo, repo_root
    ):
        """When no report exists at either path, recovery is skipped gracefully."""
        task_id = "TASK-001"
        turn = 1
        invoker = _make_invoker(worktree_in_repo)

        # Don't write any player report at either location

        result = _make_task_work_result()
        invoker._create_player_report_from_task_work(task_id, turn, result)

        # Report should be written but without completion_promises from recovery
        report_path = TaskArtifactPaths.player_report_path(
            task_id, turn, worktree_in_repo
        )
        report = json.loads(report_path.read_text())

        # completion_promises may be empty or populated by Fix 5
        # The key assertion: no exception was raised
        assert "task_id" in report

    def test_invalid_json_at_repo_root_is_handled_gracefully(
        self, worktree_in_repo, repo_root
    ):
        """When repo root has invalid JSON, recovery logs debug and continues."""
        task_id = "TASK-001"
        turn = 1
        invoker = _make_invoker(worktree_in_repo)

        # Write invalid JSON at repo root
        report_path = TaskArtifactPaths.player_report_path(
            task_id, turn, repo_root
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("not valid json {{{")

        result = _make_task_work_result()
        invoker._create_player_report_from_task_work(task_id, turn, result)

        # Should proceed without error
        worktree_report = TaskArtifactPaths.player_report_path(
            task_id, turn, worktree_in_repo
        )
        report = json.loads(worktree_report.read_text())
        assert "task_id" in report

    def test_standalone_worktree_has_no_repo_root_fallback(
        self, standalone_worktree
    ):
        """When worktree is standalone (not under .guardkit/worktrees/), no fallback."""
        task_id = "TASK-001"
        turn = 1
        invoker = _make_invoker(standalone_worktree)

        # No report at worktree path
        result = _make_task_work_result()
        invoker._create_player_report_from_task_work(task_id, turn, result)

        # Should proceed without error
        report_path = TaskArtifactPaths.player_report_path(
            task_id, turn, standalone_worktree
        )
        report = json.loads(report_path.read_text())
        assert "task_id" in report
