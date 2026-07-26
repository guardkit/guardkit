"""Tests for TASK-SBHO-002: Hold-out relocation — coach dossier out of the shared worktree.

Verifies that coach_evidence and coach_decision files live in the
orchestrator-private directory with backward-compatible legacy fallback,
that coach_feedback stays in the worktree, and that oracle paths are
stripped from Player-facing feedback.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from guardkit.orchestrator.paths import (
    TaskArtifactPaths,
    strip_oracle_paths,
)


# ===========================================================================
# Path resolution tests
# ===========================================================================


class TestTaskPrivateDir:
    """TaskArtifactPaths.task_private_dir — private dir location."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-001"
        result = TaskArtifactPaths.task_private_dir(task_id, tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild-private" / task_id

    def test_creates_no_directory(self, tmp_path: Path) -> None:
        """task_private_dir is read-only — should not create dirs."""
        task_id = "TASK-TEST-002"
        _ = TaskArtifactPaths.task_private_dir(task_id, tmp_path)
        assert not (tmp_path / ".guardkit" / "autobuild-private" / task_id).exists()


class TestCoachEvidencePath:
    """TaskArtifactPaths.coach_evidence_path — private dir with legacy fallback."""

    def test_private_dir_takes_precedence(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-003"
        turn = 1
        private_dir = TaskArtifactPaths.task_private_dir(task_id, tmp_path)
        private_dir.mkdir(parents=True, exist_ok=True)
        private_file = private_dir / f"coach_evidence_turn_{turn}.json"
        private_file.write_text('{"test": true}')

        legacy_dir = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy_dir / f"coach_evidence_turn_{turn}.json"
        legacy_file.write_text('{"test": false}')

        result = TaskArtifactPaths.coach_evidence_path(task_id, turn, tmp_path)
        assert result == private_file

    def test_falls_back_to_legacy_when_private_missing(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-004"
        turn = 1
        legacy_dir = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy_dir / f"coach_evidence_turn_{turn}.json"
        legacy_file.write_text('{"legacy": true}')

        result = TaskArtifactPaths.coach_evidence_path(task_id, turn, tmp_path)
        assert result == legacy_file

    def test_returns_private_path_even_when_neither_exists(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-005"
        turn = 1
        result = TaskArtifactPaths.coach_evidence_path(task_id, turn, tmp_path)
        expected = TaskArtifactPaths.task_private_dir(task_id, tmp_path) / f"coach_evidence_turn_{turn}.json"
        assert result == expected


class TestCoachDecisionPath:
    """TaskArtifactPaths.coach_decision_path — private dir with legacy fallback."""

    def test_private_dir_takes_precedence(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-006"
        turn = 1
        private_dir = TaskArtifactPaths.task_private_dir(task_id, tmp_path)
        private_dir.mkdir(parents=True, exist_ok=True)
        private_file = private_dir / f"coach_turn_{turn}.json"
        private_file.write_text('{"decision": "approve"}')

        legacy_dir = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy_dir / f"coach_turn_{turn}.json"
        legacy_file.write_text('{"decision": "feedback"}')

        result = TaskArtifactPaths.coach_decision_path(task_id, turn, tmp_path)
        assert result == private_file

    def test_falls_back_to_legacy_when_private_missing(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-007"
        turn = 1
        legacy_dir = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy_dir / f"coach_turn_{turn}.json"
        legacy_file.write_text('{"decision": "feedback"}')

        result = TaskArtifactPaths.coach_decision_path(task_id, turn, tmp_path)
        assert result == legacy_file

    def test_returns_private_path_even_when_neither_exists(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-008"
        turn = 1
        result = TaskArtifactPaths.coach_decision_path(task_id, turn, tmp_path)
        expected = TaskArtifactPaths.task_private_dir(task_id, tmp_path) / f"coach_turn_{turn}.json"
        assert result == expected


class TestPrivateArtifactPath:
    """TaskArtifactPaths.private_artifact_path — generic private dir accessor."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-009"
        result = TaskArtifactPaths.private_artifact_path(
            task_id, "some_artifact.json", tmp_path
        )
        assert result == tmp_path / ".guardkit" / "autobuild-private" / task_id / "some_artifact.json"


class TestLegacyArtifactPath:
    """TaskArtifactPaths.legacy_artifact_path — legacy worktree accessor."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-010"
        result = TaskArtifactPaths.legacy_artifact_path(
            task_id, "some_artifact.json", tmp_path
        )
        assert result == tmp_path / ".guardkit" / "autobuild" / task_id / "some_artifact.json"


# ===========================================================================
# Oracle path stripping tests
# ===========================================================================


class TestStripOraclePaths:
    """strip_oracle_paths — removes worktree-relative paths from text."""

    def test_replaces_file_path_in_text(self) -> None:
        text = "Issue found in src/tests/test_oracle.py"
        result = strip_oracle_paths(text)
        assert "src/tests/test_oracle.py" not in result
        assert "<oracle-file>" in result

    def test_replaces_multiple_paths(self) -> None:
        text = "Found issues in tests/unit/foo.py and src/lib/bar.ts"
        result = strip_oracle_paths(text)
        assert "tests/unit/foo.py" not in result
        assert "src/lib/bar.ts" not in result
        assert result.count("<oracle-file>") == 2

    def test_no_paths_unchanged(self) -> None:
        text = "No file paths here, just plain feedback"
        result = strip_oracle_paths(text)
        assert result == text

    def test_replaces_path_in_parentheses(self) -> None:
        text = "(src/tests/test_oracle.py:42)"
        result = strip_oracle_paths(text)
        assert "src/tests/test_oracle.py" not in result
        assert "[<oracle-file>]" in result

    def test_replaces_md_and_txt_extensions(self) -> None:
        text = "See docs/design.md and notes.txt for details"
        result = strip_oracle_paths(text)
        assert "docs/design.md" not in result
        assert "notes.txt" not in result

    def test_js_and_ts_extensions(self) -> None:
        text = "Import from src/index.js and src/utils.ts"
        result = strip_oracle_paths(text)
        assert "src/index.js" not in result
        assert "src/utils.ts" not in result


# ===========================================================================
# Feedback path stays in worktree
# ===========================================================================


class TestCoachFeedbackPath:
    """Coach feedback stays in the worktree (not relocated)."""

    def test_feedback_path_in_worktree(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-011"
        turn = 1
        result = TaskArtifactPaths.coach_feedback_path(task_id, turn, tmp_path)
        assert ".guardkit/autobuild" in str(result)
        assert "autobuild-private" not in str(result)
        assert f"coach_feedback_{turn}.json" in str(result)


# ===========================================================================
# Integration: write to private, read via accessor
# ===========================================================================


class TestWriteReadRoundTrip:
    """End-to-end: write coach evidence to private dir, read via accessor."""

    def test_evidence_round_trip(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-012"
        turn = 1
        private_dir = TaskArtifactPaths.task_private_dir(task_id, tmp_path)
        private_dir.mkdir(parents=True, exist_ok=True)

        # Write evidence to private dir
        evidence_path = TaskArtifactPaths.private_artifact_path(
            task_id, f"coach_evidence_turn_{turn}.json", tmp_path
        )
        evidence_data = {"task_id": task_id, "turn": turn, "gathering_status": "complete"}
        evidence_path.write_text(json.dumps(evidence_data, indent=2))

        # Read via accessor
        read_path = TaskArtifactPaths.coach_evidence_path(task_id, turn, tmp_path)
        assert read_path == evidence_path
        read_data = json.loads(read_path.read_text())
        assert read_data["gathering_status"] == "complete"

    def test_decision_round_trip(self, tmp_path: Path) -> None:
        task_id = "TASK-TEST-013"
        turn = 1
        private_dir = TaskArtifactPaths.task_private_dir(task_id, tmp_path)
        private_dir.mkdir(parents=True, exist_ok=True)

        # Write decision to private dir
        decision_path = TaskArtifactPaths.private_artifact_path(
            task_id, f"coach_turn_{turn}.json", tmp_path
        )
        decision_data = {"decision": "approve", "rationale": "All AC met"}
        decision_path.write_text(json.dumps(decision_data, indent=2))

        # Read via accessor
        read_path = TaskArtifactPaths.coach_decision_path(task_id, turn, tmp_path)
        assert read_path == decision_path
        read_data = json.loads(read_path.read_text())
        assert read_data["decision"] == "approve"


# ===========================================================================
# Honest-cap comment presence
# ===========================================================================


class TestHonestCapComment:
    """Verify the honest-cap comment is present in the source."""

    def test_private_dir_constant_has_honest_cap(self) -> None:
        """The TASK_PRIVATE_DIR constant should carry the honest-cap comment."""
        import inspect
        source = inspect.getsource(TaskArtifactPaths)
        assert "casual read" in source.lower(), \
            "Honest-cap comment about 'casual read' should be present"
        assert "sandbox lane" in source.lower(), \
            "Honest-cap comment about 'sandbox lane' should be present"
