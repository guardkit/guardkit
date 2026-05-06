"""Regression tests for CoachVerifier ↔ TaskStateBridge identity resolution.

Covers TASK-FIX-1B4A (Layer 1 of the FEAT-FFC3 false-fail fix). The
suppression path: when a Player-reported file is missing on disk but
state_bridge can resolve the task to a current canonical path that does
exist, the discrepancy is swallowed and the resolution is recorded on
``HonestyVerification.resolved_paths``.

Coverage Target: >=85%
Test Count: 5 tests (one per AC-A7 bullet)
"""

from pathlib import Path

import pytest

from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    Discrepancy,
    HonestyVerification,
    ResolvedPath,
)
from guardkit.tasks.state_bridge import TaskStateBridge


TASK_ID = "TASK-FIX-1B4A"


def _make_worktree(tmp_path: Path) -> Path:
    """Build a minimal worktree skeleton with the standard tasks/ layout."""
    (tmp_path / "tasks" / "backlog").mkdir(parents=True)
    (tmp_path / "tasks" / "in_progress").mkdir(parents=True)
    (tmp_path / "tasks" / "design_approved").mkdir(parents=True)
    return tmp_path


def _write_task_file(worktree: Path, state: str, body: str = "# task") -> Path:
    """Write a task markdown file under the given state directory."""
    target_dir = worktree / "tasks" / state
    target_dir.mkdir(parents=True, exist_ok=True)
    task_path = target_dir / f"{TASK_ID}-canonical-path-resolution.md"
    task_path.write_text(body)
    return task_path


class TestStateBridgeMoveDoesNotFalseFailHonesty:
    """AC-A7 #1 — Player report cites pre-move path, resolution suppresses it."""

    def test_state_bridge_move_does_not_false_fail_honesty(self, tmp_path: Path):
        worktree = _make_worktree(tmp_path)
        # state_bridge has already moved the file from backlog → design_approved
        _write_task_file(worktree, "design_approved")
        pre_move_path = "tasks/backlog/" + f"{TASK_ID}-canonical-path-resolution.md"

        bridge = TaskStateBridge(
            TASK_ID, worktree, in_autobuild_context=True
        )
        verifier = CoachVerifier(
            worktree, task_id=TASK_ID, state_bridge=bridge
        )

        report = {
            "files_modified": [pre_move_path],
            "files_created": [],
            "tests_written": [],
        }
        discrepancies = verifier._verify_files_exist(report)

        assert discrepancies == [], (
            "Expected no discrepancy when state_bridge resolves the "
            "pre-move path to the current canonical location."
        )
        assert len(verifier._resolved_paths) == 1
        rp = verifier._resolved_paths[0]
        assert rp.claimed == pre_move_path
        assert rp.task_id == TASK_ID
        assert "design_approved" in rp.resolved_to


class TestGenuineMissingFileStillFailsHonesty:
    """AC-A7 #2 — file truly absent → critical discrepancy still fires."""

    def test_genuine_missing_file_still_fails_honesty(self, tmp_path: Path):
        worktree = _make_worktree(tmp_path)
        # Task file does NOT exist anywhere — canonical_path_for() returns None
        bridge = TaskStateBridge(
            TASK_ID, worktree, in_autobuild_context=True
        )
        verifier = CoachVerifier(
            worktree, task_id=TASK_ID, state_bridge=bridge
        )

        report = {
            "files_modified": ["src/never_written.py"],
            "files_created": [],
            "tests_written": [],
        }
        discrepancies = verifier._verify_files_exist(report)

        assert len(discrepancies) == 1
        d = discrepancies[0]
        assert d.claim_type == "file_existence"
        assert d.severity == "critical"
        assert "src/never_written.py" in d.player_claim
        assert verifier._resolved_paths == []


class TestStateBridgeUnavailableFallsBackToExactMatch:
    """AC-A7 #3 — no bridge wiring → exact-match behaviour preserved."""

    def test_state_bridge_unavailable_falls_back_to_exact_match(
        self, tmp_path: Path
    ):
        worktree = _make_worktree(tmp_path)
        _write_task_file(worktree, "design_approved")
        pre_move_path = "tasks/backlog/" + f"{TASK_ID}-canonical-path-resolution.md"

        # No task_id, no state_bridge — fail-open
        verifier = CoachVerifier(worktree)

        report = {
            "files_modified": [pre_move_path],
            "files_created": [],
            "tests_written": [],
        }
        discrepancies = verifier._verify_files_exist(report)

        assert len(discrepancies) == 1
        assert discrepancies[0].claim_type == "file_existence"
        assert verifier._resolved_paths == []


class TestCanonicalPathForReturnsNoneWhenTaskNotFound:
    """AC-A7 #4 — canonical_path_for() swallows TaskNotFoundError."""

    def test_canonical_path_for_returns_none_when_task_not_found(
        self, tmp_path: Path
    ):
        worktree = _make_worktree(tmp_path)
        # Bridge for a task whose file does not exist anywhere
        bridge = TaskStateBridge(
            "TASK-DOES-NOT-EXIST",
            worktree,
            in_autobuild_context=True,
        )

        result = bridge.canonical_path_for()

        assert result is None, (
            "canonical_path_for() must return None on TaskNotFoundError, "
            "not propagate the exception."
        )


class TestResolutionRecordedOnResolvedPathsField:
    """AC-A7 #5 — successful resolutions surface on HonestyVerification."""

    def test_resolution_recorded_on_resolved_paths_field(self, tmp_path: Path):
        worktree = _make_worktree(tmp_path)
        _write_task_file(worktree, "design_approved")
        pre_move_path = "tasks/backlog/" + f"{TASK_ID}-canonical-path-resolution.md"

        bridge = TaskStateBridge(
            TASK_ID, worktree, in_autobuild_context=True
        )
        verifier = CoachVerifier(
            worktree, task_id=TASK_ID, state_bridge=bridge
        )

        report = {
            "tests_run": False,  # skip pytest path entirely
            "files_modified": [pre_move_path],
            "files_created": [],
            "tests_written": [],
        }
        result = verifier.verify_player_report(report)

        assert isinstance(result, HonestyVerification)
        assert result.verified is True
        assert result.discrepancies == []
        assert len(result.resolved_paths) == 1
        rp = result.resolved_paths[0]
        assert isinstance(rp, ResolvedPath)
        assert rp.claimed == pre_move_path
        assert rp.task_id == TASK_ID
