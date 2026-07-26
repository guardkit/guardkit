"""
Unit tests for TaskArtifactPaths utility.

Tests centralized path resolution for task artifacts including:
- Implementation plans
- Player/Coach reports
- AutoBuild artifacts
- Directory management

Coverage Target: >=85%
Test Count: 25+ tests
"""

import tempfile
from pathlib import Path

import pytest

from guardkit.orchestrator.paths import TaskArtifactPaths


class TestImplementationPlanPaths:
    """Test implementation plan path methods."""

    def test_implementation_plan_paths_returns_all_locations(self, tmp_path: Path):
        """Test that implementation_plan_paths returns all expected locations."""
        task_id = "TASK-001"
        paths = TaskArtifactPaths.implementation_plan_paths(task_id, tmp_path)

        assert len(paths) == 4
        assert paths[0] == tmp_path / ".claude" / "task-plans" / "TASK-001-implementation-plan.md"
        assert paths[1] == tmp_path / ".claude" / "task-plans" / "TASK-001-implementation-plan.json"
        assert paths[2] == tmp_path / "docs" / "state" / "TASK-001" / "implementation_plan.md"
        assert paths[3] == tmp_path / "docs" / "state" / "TASK-001" / "implementation_plan.json"

    def test_implementation_plan_paths_with_complex_task_id(self, tmp_path: Path):
        """Test paths with complex task ID (prefix + hash)."""
        task_id = "TASK-E01-a3f2"
        paths = TaskArtifactPaths.implementation_plan_paths(task_id, tmp_path)

        assert paths[0] == tmp_path / ".claude" / "task-plans" / "TASK-E01-a3f2-implementation-plan.md"

    def test_find_implementation_plan_returns_none_when_not_found(self, tmp_path: Path):
        """Test find_implementation_plan returns None when no plan exists."""
        result = TaskArtifactPaths.find_implementation_plan("TASK-001", tmp_path)
        assert result is None

    def test_find_implementation_plan_finds_markdown_plan(self, tmp_path: Path):
        """Test find_implementation_plan finds markdown plan first."""
        task_id = "TASK-001"

        # Create markdown plan in .claude/task-plans
        plan_dir = tmp_path / ".claude" / "task-plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / f"{task_id}-implementation-plan.md"
        plan_file.write_text("# Implementation Plan\n\nDetailed implementation steps...")

        result = TaskArtifactPaths.find_implementation_plan(task_id, tmp_path)
        assert result == plan_file

    def test_find_implementation_plan_finds_json_plan(self, tmp_path: Path):
        """Test find_implementation_plan finds JSON plan."""
        task_id = "TASK-001"

        # Create JSON plan in docs/state
        plan_dir = tmp_path / "docs" / "state" / task_id
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "implementation_plan.json"
        plan_file.write_text('{"files": ["src/main.py", "tests/test_main.py"], "phases": ["planning", "implementation"]}')

        result = TaskArtifactPaths.find_implementation_plan(task_id, tmp_path)
        assert result == plan_file

    def test_find_implementation_plan_skips_empty_files(self, tmp_path: Path):
        """Test find_implementation_plan skips files with insufficient content."""
        task_id = "TASK-001"

        # Create empty plan file (below min_content_length threshold)
        plan_dir = tmp_path / ".claude" / "task-plans"
        plan_dir.mkdir(parents=True)
        empty_plan = plan_dir / f"{task_id}-implementation-plan.md"
        empty_plan.write_text("short")  # Too short

        # Create valid plan in secondary location
        docs_dir = tmp_path / "docs" / "state" / task_id
        docs_dir.mkdir(parents=True)
        valid_plan = docs_dir / "implementation_plan.md"
        valid_plan.write_text("# Implementation Plan\n\nThis is a detailed plan with enough content to be considered valid.")

        result = TaskArtifactPaths.find_implementation_plan(task_id, tmp_path)
        assert result == valid_plan

    def test_find_implementation_plan_respects_custom_min_length(self, tmp_path: Path):
        """Test find_implementation_plan respects custom min_content_length."""
        task_id = "TASK-001"

        # Create plan with 30 chars
        plan_dir = tmp_path / ".claude" / "task-plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / f"{task_id}-implementation-plan.md"
        plan_file.write_text("12345678901234567890123456789X")  # 30 chars

        # With default min (50), should not find
        result = TaskArtifactPaths.find_implementation_plan(task_id, tmp_path)
        assert result is None

        # With lower min, should find
        result = TaskArtifactPaths.find_implementation_plan(task_id, tmp_path, min_content_length=30)
        assert result == plan_file

    def test_preferred_plan_path(self, tmp_path: Path):
        """Test preferred_plan_path returns primary location."""
        task_id = "TASK-002"
        result = TaskArtifactPaths.preferred_plan_path(task_id, tmp_path)

        expected = tmp_path / ".claude" / "task-plans" / "TASK-002-implementation-plan.md"
        assert result == expected


class TestAutoBuildArtifactPaths:
    """Test AutoBuild artifact path methods."""

    def test_autobuild_dir(self, tmp_path: Path):
        """Test autobuild_dir returns correct path."""
        task_id = "TASK-001"
        result = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)

        assert result == tmp_path / ".guardkit" / "autobuild" / "TASK-001"

    def test_player_report_path(self, tmp_path: Path):
        """Test player_report_path returns correct path."""
        result = TaskArtifactPaths.player_report_path("TASK-001", 1, tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "player_turn_1.json"

        result = TaskArtifactPaths.player_report_path("TASK-001", 3, tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "player_turn_3.json"

    def test_coach_decision_path(self, tmp_path: Path):
        """Test coach_decision_path returns private dir path (primary) or legacy fallback.

        TASK-SBHO-002: coach_decision_path now prefers the private directory.
        When the file exists in the legacy worktree location, it falls back there.
        """
        # When no files exist anywhere, returns the private dir path (primary)
        result = TaskArtifactPaths.coach_decision_path("TASK-001", 1, tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild-private" / "TASK-001" / "coach_turn_1.json"

        # When legacy file exists, falls back to legacy path
        legacy_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "coach_turn_1.json").touch()
        result = TaskArtifactPaths.coach_decision_path("TASK-001", 1, tmp_path)
        assert result == legacy_dir / "coach_turn_1.json"

        # Private dir takes precedence when both exist
        private_dir = tmp_path / ".guardkit" / "autobuild-private" / "TASK-001"
        private_dir.mkdir(parents=True, exist_ok=True)
        (private_dir / "coach_turn_1.json").touch()
        result = TaskArtifactPaths.coach_decision_path("TASK-001", 1, tmp_path)
        assert result == private_dir / "coach_turn_1.json"

    def test_task_work_results_path(self, tmp_path: Path):
        """Test task_work_results_path returns correct path."""
        result = TaskArtifactPaths.task_work_results_path("TASK-001", tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "task_work_results.json"

    def test_coach_feedback_path(self, tmp_path: Path):
        """Test coach_feedback_path returns correct path."""
        result = TaskArtifactPaths.coach_feedback_path("TASK-001", 1, tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "coach_feedback_1.json"

    def test_verification_context_path(self, tmp_path: Path):
        """Test verification_context_path returns correct path."""
        result = TaskArtifactPaths.verification_context_path("TASK-001", 2, tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "verification_context_2.json"

    def test_agent_report_path_player(self, tmp_path: Path):
        """Test agent_report_path for player."""
        result = TaskArtifactPaths.agent_report_path("TASK-001", "player", 1, tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "player_turn_1.json"

    def test_agent_report_path_coach(self, tmp_path: Path):
        """Test agent_report_path for coach."""
        result = TaskArtifactPaths.agent_report_path("TASK-001", "coach", 2, tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "coach_turn_2.json"


class TestTaskStatePaths:
    """Test task state path methods."""

    def test_task_state_dir(self, tmp_path: Path):
        """Test task_state_dir returns correct path."""
        result = TaskArtifactPaths.task_state_dir("TASK-001", tmp_path)
        assert result == tmp_path / "docs" / "state" / "TASK-001"

    def test_complexity_score_path(self, tmp_path: Path):
        """Test complexity_score_path returns correct path."""
        result = TaskArtifactPaths.complexity_score_path("TASK-001", tmp_path)
        assert result == tmp_path / "docs" / "state" / "TASK-001" / "complexity_score.json"


class TestDirectoryManagement:
    """Test directory creation methods."""

    def test_ensure_task_dirs_creates_all_directories(self, tmp_path: Path):
        """Test ensure_task_dirs creates all required directories."""
        task_id = "TASK-001"

        # Directories shouldn't exist yet
        assert not (tmp_path / ".guardkit" / "autobuild" / task_id).exists()
        assert not (tmp_path / ".claude" / "task-plans").exists()
        assert not (tmp_path / "docs" / "state" / task_id).exists()

        # Create directories
        TaskArtifactPaths.ensure_task_dirs(task_id, tmp_path)

        # All directories should now exist
        assert (tmp_path / ".guardkit" / "autobuild" / task_id).exists()
        assert (tmp_path / ".claude" / "task-plans").exists()
        assert (tmp_path / "docs" / "state" / task_id).exists()

    def test_ensure_task_dirs_idempotent(self, tmp_path: Path):
        """Test ensure_task_dirs is idempotent (can be called multiple times)."""
        task_id = "TASK-001"

        # Call twice - should not raise
        TaskArtifactPaths.ensure_task_dirs(task_id, tmp_path)
        TaskArtifactPaths.ensure_task_dirs(task_id, tmp_path)

        assert (tmp_path / ".guardkit" / "autobuild" / task_id).exists()

    def test_ensure_autobuild_dir_creates_and_returns_path(self, tmp_path: Path):
        """Test ensure_autobuild_dir creates directory and returns path."""
        task_id = "TASK-001"

        result = TaskArtifactPaths.ensure_autobuild_dir(task_id, tmp_path)

        expected = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
        assert result == expected
        assert result.exists()
        assert result.is_dir()

    def test_ensure_plan_dir_creates_and_returns_path(self, tmp_path: Path):
        """Test ensure_plan_dir creates directory and returns path."""
        result = TaskArtifactPaths.ensure_plan_dir(tmp_path)

        expected = tmp_path / ".claude" / "task-plans"
        assert result == expected
        assert result.exists()
        assert result.is_dir()


class TestPathConsistency:
    """Test path consistency across methods."""

    def test_player_report_path_matches_agent_report_path(self, tmp_path: Path):
        """Test player_report_path matches agent_report_path('player')."""
        task_id = "TASK-001"
        turn = 1

        player_path = TaskArtifactPaths.player_report_path(task_id, turn, tmp_path)
        agent_path = TaskArtifactPaths.agent_report_path(task_id, "player", turn, tmp_path)

        assert player_path == agent_path

    def test_coach_decision_path_matches_agent_report_path(self, tmp_path: Path):
        """Test coach_decision_path vs agent_report_path('coach').

        TASK-SBHO-002: coach_decision_path now prefers the private directory,
        while agent_report_path still returns the worktree path. They only
        match when the file exists in the legacy worktree location (fallback).
        """
        task_id = "TASK-001"
        turn = 2

        coach_path = TaskArtifactPaths.coach_decision_path(task_id, turn, tmp_path)
        agent_path = TaskArtifactPaths.agent_report_path(task_id, "coach", turn, tmp_path)

        # Without any files on disk, coach_decision_path returns private dir,
        # agent_report_path returns worktree path — they differ.
        assert coach_path == tmp_path / ".guardkit" / "autobuild-private" / task_id / f"coach_turn_{turn}.json"
        assert agent_path == tmp_path / ".guardkit" / "autobuild" / task_id / f"coach_turn_{turn}.json"
        assert coach_path != agent_path

        # When the legacy file exists, coach_decision_path falls back to it,
        # matching agent_report_path.
        legacy_dir = tmp_path / ".guardkit" / "autobuild" / task_id
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / f"coach_turn_{turn}.json").touch()
        coach_path_fallback = TaskArtifactPaths.coach_decision_path(task_id, turn, tmp_path)
        assert coach_path_fallback == agent_path

    def test_task_work_results_in_autobuild_dir(self, tmp_path: Path):
        """Test task_work_results_path is within autobuild_dir."""
        task_id = "TASK-001"

        autobuild = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)
        results = TaskArtifactPaths.task_work_results_path(task_id, tmp_path)

        assert results.parent == autobuild


class TestClassAttributes:
    """Test class attributes are correctly defined."""

    def test_plan_locations_has_four_entries(self):
        """Test PLAN_LOCATIONS has expected entries."""
        assert len(TaskArtifactPaths.PLAN_LOCATIONS) == 4
        assert all("{task_id}" in loc for loc in TaskArtifactPaths.PLAN_LOCATIONS)

    def test_required_dirs_has_three_entries(self):
        """Test REQUIRED_DIRS has expected entries."""
        assert len(TaskArtifactPaths.REQUIRED_DIRS) == 3

    def test_player_report_template_valid(self):
        """Test PLAYER_REPORT template has required placeholders."""
        assert "{task_id}" in TaskArtifactPaths.PLAYER_REPORT
        assert "{turn}" in TaskArtifactPaths.PLAYER_REPORT

    def test_coach_decision_template_valid(self):
        """Test COACH_DECISION template has required placeholders."""
        assert "{task_id}" in TaskArtifactPaths.COACH_DECISION
        assert "{turn}" in TaskArtifactPaths.COACH_DECISION


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_paths_with_special_characters_in_task_id(self, tmp_path: Path):
        """Test paths work with special characters in task ID."""
        task_id = "TASK-E01-B2C4"

        result = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)
        assert task_id in str(result)

    def test_paths_with_absolute_worktree(self, tmp_path: Path):
        """Test paths work with absolute worktree path."""
        worktree = tmp_path.resolve()
        task_id = "TASK-001"

        result = TaskArtifactPaths.autobuild_dir(task_id, worktree)
        assert result.is_absolute()

    def test_paths_with_relative_worktree(self):
        """Test paths work with relative worktree path."""
        worktree = Path("./relative/path")
        task_id = "TASK-001"

        result = TaskArtifactPaths.autobuild_dir(task_id, worktree)
        assert not result.is_absolute()
        assert str(result).startswith("relative/path")

    def test_find_implementation_plan_handles_io_error(self, tmp_path: Path):
        """Test find_implementation_plan handles IO errors gracefully."""
        task_id = "TASK-001"

        # Create a directory where a file is expected (causes IOError on read)
        plan_dir = tmp_path / ".claude" / "task-plans"
        plan_dir.mkdir(parents=True)
        # Create a directory instead of a file
        fake_plan = plan_dir / f"{task_id}-implementation-plan.md"
        fake_plan.mkdir()

        # Should not raise, just return None
        result = TaskArtifactPaths.find_implementation_plan(task_id, tmp_path)
        assert result is None


class TestCoachEvidencePathLegacyFallback:
    """Test coach_evidence_path with legacy fallback (TASK-SBHO-002)."""

    def test_coach_evidence_path_returns_private_when_no_files_exist(self, tmp_path: Path):
        """When no files exist, returns private dir path (primary)."""
        result = TaskArtifactPaths.coach_evidence_path("TASK-001", 1, tmp_path)
        expected = tmp_path / ".guardkit" / "autobuild-private" / "TASK-001" / "coach_evidence_turn_1.json"
        assert result == expected

    def test_coach_evidence_path_falls_back_to_legacy(self, tmp_path: Path):
        """When only legacy file exists, falls back to legacy path."""
        legacy_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "coach_evidence_turn_1.json").touch()

        result = TaskArtifactPaths.coach_evidence_path("TASK-001", 1, tmp_path)
        assert result == legacy_dir / "coach_evidence_turn_1.json"

    def test_coach_evidence_path_private_takes_precedence(self, tmp_path: Path):
        """When both exist, private dir takes precedence."""
        legacy_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "coach_evidence_turn_1.json").touch()

        private_dir = tmp_path / ".guardkit" / "autobuild-private" / "TASK-001"
        private_dir.mkdir(parents=True, exist_ok=True)
        (private_dir / "coach_evidence_turn_1.json").touch()

        result = TaskArtifactPaths.coach_evidence_path("TASK-001", 1, tmp_path)
        assert result == private_dir / "coach_evidence_turn_1.json"

    def test_coach_evidence_path_multiple_turns(self, tmp_path: Path):
        """Test different turn numbers resolve correctly."""
        result_1 = TaskArtifactPaths.coach_evidence_path("TASK-001", 1, tmp_path)
        result_2 = TaskArtifactPaths.coach_evidence_path("TASK-001", 2, tmp_path)
        result_3 = TaskArtifactPaths.coach_evidence_path("TASK-001", 10, tmp_path)

        assert "coach_evidence_turn_1.json" in str(result_1)
        assert "coach_evidence_turn_2.json" in str(result_2)
        assert "coach_evidence_turn_10.json" in str(result_3)


class TestPrivateArtifactPath:
    """Test private_artifact_path and legacy_artifact_path (TASK-SBHO-002)."""

    def test_private_artifact_path_returns_private_dir(self, tmp_path: Path):
        """Test private_artifact_path returns path in private dir."""
        task_id = "TASK-001"
        artifact = "custom_artifact.json"

        result = TaskArtifactPaths.private_artifact_path(task_id, artifact, tmp_path)
        expected = tmp_path / ".guardkit" / "autobuild-private" / "TASK-001" / "custom_artifact.json"
        assert result == expected

    def test_legacy_artifact_path_returns_worktree_dir(self, tmp_path: Path):
        """Test legacy_artifact_path returns path in worktree dir."""
        task_id = "TASK-001"
        artifact = "legacy_artifact.json"

        result = TaskArtifactPaths.legacy_artifact_path(task_id, artifact, tmp_path)
        expected = tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "legacy_artifact.json"
        assert result == expected

    def test_private_and_legacy_paths_differ(self, tmp_path: Path):
        """Test private and legacy paths point to different directories."""
        task_id = "TASK-001"
        artifact = "coach_turn_1.json"

        private = TaskArtifactPaths.private_artifact_path(task_id, artifact, tmp_path)
        legacy = TaskArtifactPaths.legacy_artifact_path(task_id, artifact, tmp_path)

        assert private.parent != legacy.parent
        assert "autobuild-private" in str(private)
        assert "autobuild" in str(legacy)
        assert "autobuild-private" not in str(legacy)


class TestCoachFeedbackPathUnchanged:
    """Test coach_feedback_path remains in worktree (TASK-SBHO-002)."""

    def test_coach_feedback_path_stays_in_worktree(self, tmp_path: Path):
        """Coach feedback path should remain in worktree, not private dir."""
        result = TaskArtifactPaths.coach_feedback_path("TASK-001", 1, tmp_path)
        assert result == tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "coach_feedback_1.json"
        assert "autobuild-private" not in str(result)
