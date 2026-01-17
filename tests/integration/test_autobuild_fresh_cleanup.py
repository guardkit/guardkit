"""
Integration tests for AutoBuild --fresh flag with force cleanup.

Tests that the --fresh flag successfully cleans up worktrees even when
they contain untracked files or uncommitted changes.

Coverage Target: >=85%
Test Count: 3+ tests
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureOrchestration,
    FeatureExecution,
    FeatureLoader,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_repo_with_feature():
    """Create a temporary repository with a feature."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Create features directory
        features_dir = repo_root / ".guardkit" / "features"
        features_dir.mkdir(parents=True)

        # Create a sample feature
        feature = Feature(
            id="FEAT-FRESH-TEST",
            name="Test Feature for Fresh Cleanup",
            description="Testing fresh flag cleanup behavior",
            created="2025-12-08T10:00:00Z",
            status="planned",
            complexity=2,
            estimated_tasks=1,
            tasks=[
                FeatureTask(
                    id="TASK-FRESH-001",
                    name="Test Task 1",
                    file_path=Path("tasks/backlog/TASK-FRESH-001.md"),
                    complexity=2,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                )
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-FRESH-001"]],
                estimated_duration_minutes=30,
                recommended_parallel=1,
            ),
            execution=FeatureExecution(
                worktree_path=str(repo_root / ".guardkit" / "worktrees" / "FEAT-FRESH-TEST"),
                started_at="2025-12-08T10:00:00Z",
            ),
        )

        # Save feature
        feature_data = FeatureLoader._feature_to_dict(feature)
        with open(features_dir / "FEAT-FRESH-TEST.yaml", "w") as f:
            yaml.dump(feature_data, f)

        # Create task file
        task_file = repo_root / "tasks" / "backlog" / "TASK-FRESH-001.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            "---\nid: TASK-FRESH-001\ntitle: Test Task 1\nstatus: pending\n---\n\n"
            "# Test Task 1\n\nTask content."
        )

        # Create worktree directory with untracked files (simulating incomplete work)
        worktree_dir = repo_root / ".guardkit" / "worktrees" / "FEAT-FRESH-TEST"
        worktree_dir.mkdir(parents=True, exist_ok=True)
        (worktree_dir / "untracked.txt").write_text("This is an untracked file")
        (worktree_dir / ".git").mkdir(exist_ok=True)

        yield repo_root


# ============================================================================
# Tests: Fresh Cleanup Integration
# ============================================================================


def test_fresh_cleanup_removes_worktree_with_untracked_files(temp_repo_with_feature):
    """Test that --fresh cleanup removes worktree with untracked files."""
    worktree_dir = (
        temp_repo_with_feature
        / ".guardkit"
        / "worktrees"
        / "FEAT-FRESH-TEST"
    )
    assert worktree_dir.exists()
    assert (worktree_dir / "untracked.txt").exists()

    # Create mock worktree manager that verifies force=True is used
    mock_manager = MagicMock()
    cleanup_called = False
    force_flag_used = False

    def mock_cleanup(worktree, force=False):
        nonlocal cleanup_called, force_flag_used
        cleanup_called = True
        force_flag_used = force

    mock_manager.cleanup = mock_cleanup
    mock_manager.worktrees_dir = worktree_dir.parent

    # Create orchestrator and clean state
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo_with_feature,
        worktree_manager=mock_manager,
    )

    # Load feature
    feature = FeatureLoader.load_feature("FEAT-FRESH-TEST", temp_repo_with_feature)

    # Clean state (simulating --fresh)
    orchestrator._clean_state(feature)

    # Verify cleanup was called with force=True
    assert cleanup_called is True, "Cleanup should be called"
    assert force_flag_used is True, "Force flag should be True for fresh cleanup"


def test_fresh_cleanup_handles_cleanup_errors_gracefully(temp_repo_with_feature):
    """Test that cleanup errors are handled without crashing."""
    mock_manager = MagicMock()
    mock_manager.cleanup.side_effect = Exception("Simulated cleanup failure")

    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo_with_feature,
        worktree_manager=mock_manager,
    )

    feature = FeatureLoader.load_feature("FEAT-FRESH-TEST", temp_repo_with_feature)

    # Should not raise despite cleanup failure
    orchestrator._clean_state(feature)

    # Verify cleanup was attempted
    mock_manager.cleanup.assert_called_once()


def test_fresh_cleanup_with_missing_worktree_path(temp_repo_with_feature):
    """Test that clean_state handles missing worktree_path gracefully."""
    mock_manager = MagicMock()

    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo_with_feature,
        worktree_manager=mock_manager,
    )

    feature = FeatureLoader.load_feature("FEAT-FRESH-TEST", temp_repo_with_feature)

    # Clear the worktree path
    feature.execution.worktree_path = None

    # Should not raise and cleanup should not be called
    orchestrator._clean_state(feature)

    # Verify cleanup was not called (no worktree_path to clean)
    mock_manager.cleanup.assert_not_called()


def test_fresh_cleanup_force_flag_in_cleanup_call(temp_repo_with_feature):
    """Integration test: Verify force=True is passed in cleanup call."""
    calls = []

    def mock_cleanup(worktree, force=False):
        calls.append({"worktree_id": worktree.task_id, "force": force})

    mock_manager = MagicMock()
    mock_manager.cleanup = mock_cleanup

    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo_with_feature,
        worktree_manager=mock_manager,
    )

    feature = FeatureLoader.load_feature("FEAT-FRESH-TEST", temp_repo_with_feature)

    # Execute clean state
    orchestrator._clean_state(feature)

    # Verify the cleanup call included force=True
    assert len(calls) == 1
    assert calls[0]["worktree_id"] == "FEAT-FRESH-TEST"
    assert calls[0]["force"] is True
