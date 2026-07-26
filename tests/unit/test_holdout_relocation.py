"""
Unit tests for TASK-SBHO-002: Hold-out relocation — coach dossier out of the shared worktree.

Verifies that:
- coach_evidence_turn_{N}.json and coach_turn_{N}.json live in the
  orchestrator-private directory (.guardkit/autobuild-private/), not in the
  shared worktree (.guardkit/autobuild/).
- coach_feedback remains in the worktree and round-trips through
  load_coach_feedback unchanged.
- Legacy-location fallback works and logs.
- Oracle paths are stripped from Player-facing feedback.
- The honest-cap comment is present at both write seams.
"""

import inspect
import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.paths import TaskArtifactPaths, strip_oracle_paths


# ============================================================================
# Coach evidence & verdict private-dir placement
# ============================================================================


class TestPrivateDirPlacement:
    """Coach evidence and verdict must live in the private dir."""

    def test_private_dir_constant_is_correct(self):
        """TASK_PRIVATE_DIR template must resolve to the right path."""
        worktree = Path("/fake/worktree")
        actual = TaskArtifactPaths.task_private_dir("TASK-001", worktree)
        assert actual == Path("/fake/worktree/.guardkit/autobuild-private/TASK-001")

    def test_coach_evidence_path_returns_private_when_present(self, tmp_path: Path):
        """coach_evidence_path returns the private dir path when the file exists there."""
        task_id = "TASK-001"
        turn = 1
        private_dir = TaskArtifactPaths.task_private_dir(task_id, tmp_path)
        private_dir.mkdir(parents=True)
        evidence_file = private_dir / f"coach_evidence_turn_{turn}.json"
        evidence_file.write_text("{}")

        result = TaskArtifactPaths.coach_evidence_path(task_id, turn, tmp_path)
        assert result == evidence_file
        assert "autobuild-private" in str(result)

    def test_coach_evidence_path_falls_back_to_legacy(self, tmp_path: Path):
        """When private file is missing, coach_evidence_path falls back to legacy."""
        task_id = "TASK-001"
        turn = 1
        legacy_dir = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)
        legacy_dir.mkdir(parents=True)
        legacy_file = legacy_dir / f"coach_evidence_turn_{turn}.json"
        legacy_file.write_text("{}")

        with patch("guardkit.orchestrator.paths.logger") as mock_logger:
            result = TaskArtifactPaths.coach_evidence_path(task_id, turn, tmp_path)

        assert result == legacy_file
        assert "autobuild-private" not in str(result)
        mock_logger.debug.assert_called_once()
        assert "falling back to legacy" in str(mock_logger.debug.call_args)

    def test_coach_decision_path_returns_private_when_present(self, tmp_path: Path):
        """coach_decision_path returns the private dir path when the file exists there."""
        task_id = "TASK-001"
        turn = 1
        private_dir = TaskArtifactPaths.task_private_dir(task_id, tmp_path)
        private_dir.mkdir(parents=True)
        decision_file = private_dir / f"coach_turn_{turn}.json"
        decision_file.write_text('{"decision": "approve"}')

        result = TaskArtifactPaths.coach_decision_path(task_id, turn, tmp_path)
        assert result == decision_file
        assert "autobuild-private" in str(result)

    def test_coach_decision_path_falls_back_to_legacy(self, tmp_path: Path):
        """When private file is missing, coach_decision_path falls back to legacy."""
        task_id = "TASK-001"
        turn = 1
        legacy_dir = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)
        legacy_dir.mkdir(parents=True)
        legacy_file = legacy_dir / f"coach_turn_{turn}.json"
        legacy_file.write_text('{"decision": "approve"}')

        with patch("guardkit.orchestrator.paths.logger") as mock_logger:
            result = TaskArtifactPaths.coach_decision_path(task_id, turn, tmp_path)

        assert result == legacy_file
        assert "autobuild-private" not in str(result)
        mock_logger.debug.assert_called_once()
        assert "falling back to legacy" in str(mock_logger.debug.call_args)

    def test_private_artifact_path_points_to_private_dir(self):
        """private_artifact_path always returns a path inside the private dir."""
        worktree = Path("/fake/worktree")
        result = TaskArtifactPaths.private_artifact_path("TASK-001", "coach_evidence_turn_1.json", worktree)
        assert ".guardkit/autobuild-private" in str(result)

    def test_legacy_artifact_path_points_to_worktree(self):
        """legacy_artifact_path always returns a path inside the worktree autobuild dir."""
        worktree = Path("/fake/worktree")
        result = TaskArtifactPaths.legacy_artifact_path("TASK-001", "coach_turn_1.json", worktree)
        assert ".guardkit/autobuild-private" not in str(result)
        assert ".guardkit/autobuild" in str(result)


# ============================================================================
# Coach feedback stays in worktree
# ============================================================================


class TestCoachFeedbackInWorktree:
    """coach_feedback remains in the worktree, not the private dir."""

    def test_coach_feedback_path_is_in_worktree(self):
        """coach_feedback_path returns a path inside the worktree autobuild dir."""
        worktree = Path("/fake/worktree")
        result = TaskArtifactPaths.coach_feedback_path("TASK-001", 1, worktree)
        assert "autobuild-private" not in str(result)
        assert ".guardkit/autobuild/TASK-001" in str(result)


# ============================================================================
# Oracle path stripping
# ============================================================================


class TestOraclePathStripping:
    """Player-facing feedback must not contain oracle file paths."""

    def test_strips_python_file_path(self):
        result = strip_oracle_paths("Check src/tests/test_oracle.py for details")
        assert "test_oracle.py" not in result
        assert "[<oracle-file>]" in result

    def test_strips_path_in_parens(self):
        result = strip_oracle_paths("(oracle: tests/unit/behavioural.py)")
        assert "behavioural.py" not in result
        assert "[<oracle-file>]" in result

    def test_leaves_non_file_text_unchanged(self):
        result = strip_oracle_paths("AC-1 passes, AC-2 fails")
        assert result == "AC-1 passes, AC-2 fails"

    def test_empty_string(self):
        assert strip_oracle_paths("") == ""

    def test_no_file_extensions(self):
        result = strip_oracle_paths("No paths here, just text")
        assert result == "No paths here, just text"

    def test_strips_multiple_paths(self):
        result = strip_oracle_paths(
            "Failed tests/unit/a.py and src/b.py in parallel"
        )
        assert "a.py" not in result
        assert "b.py" not in result
        assert result.count("[<oracle-file>]") == 2


# ============================================================================
# Honest-cap comment presence
# ============================================================================


class TestHonestCapComment:
    """The honest-cap comment must be present at both write seams."""

    def test_autobuild_write_seam_has_honest_cap(self):
        """autobuild.py evidence writer has the honest-cap comment."""
        import guardkit.orchestrator.autobuild as autobuild_mod
        source = inspect.getsource(autobuild_mod)
        assert "relocation removes the casual read" in source

    def test_agent_invoker_write_seam_has_honest_cap(self):
        """agent_invoker.py verdict writer has the honest-cap comment."""
        import guardkit.orchestrator.agent_invoker as invoker_mod
        source = inspect.getsource(invoker_mod)
        assert "relocation removes the casual read" in source
