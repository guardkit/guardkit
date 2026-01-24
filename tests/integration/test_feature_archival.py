"""
Integration tests for feature archival functionality.

Tests the archival workflow including:
- Feature folder movement from tasks/backlog to tasks/completed/{date}/
- Feature YAML update with archival metadata
- Edge case handling (missing folders, existing destinations)
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock

import pytest
import yaml

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureLoader,
    FeatureOrchestration,
    FeatureTask,
)
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator


@pytest.fixture
def temp_repo() -> Iterator[Path]:
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Create required directories
        (repo_root / "tasks" / "backlog").mkdir(parents=True, exist_ok=True)
        (repo_root / "tasks" / "completed").mkdir(parents=True, exist_ok=True)
        (repo_root / ".guardkit" / "features").mkdir(parents=True, exist_ok=True)

        yield repo_root


@pytest.fixture
def mock_worktree_manager() -> MagicMock:
    """Create a mock worktree manager for testing."""
    return MagicMock()


@pytest.fixture
def sample_feature(temp_repo: Path) -> Feature:
    """Create a sample feature with tasks."""
    task_dir = temp_repo / "tasks" / "backlog" / "dark-mode"
    task_dir.mkdir(parents=True, exist_ok=True)

    # Create task files
    for i in range(1, 3):
        task_file = task_dir / f"TASK-DM-00{i}.md"
        task_file.write_text(f"# Task DM-00{i}\n\nTest task content")

    # Create feature
    feature = Feature(
        id="FEAT-DM-A1B2",
        name="Dark Mode Implementation",
        description="Implement dark mode for the UI",
        created=datetime.now().isoformat(),
        status="completed",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-DM-001",
                name="Add CSS variables",
                file_path=task_dir / "TASK-DM-001.md",
                complexity=3,
                dependencies=[],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=60,
            ),
            FeatureTask(
                id="TASK-DM-002",
                name="Create theme toggle",
                file_path=task_dir / "TASK-DM-002.md",
                complexity=4,
                dependencies=["TASK-DM-001"],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=90,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-DM-001"], ["TASK-DM-002"]],
            estimated_duration_minutes=150,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            tasks_completed=2,
            tasks_failed=0,
        ),
        file_path=temp_repo / ".guardkit" / "features" / "FEAT-DM-A1B2.yaml",
    )

    # Save feature to YAML
    FeatureLoader.save_feature(feature, temp_repo)

    return feature


class TestArchivePhaseBasic:
    """Test basic archive phase functionality."""

    def test_archive_phase_moves_folder(
        self,
        temp_repo: Path,
        sample_feature: Feature,
        mock_worktree_manager: MagicMock,
    ) -> None:
        """Test that archive phase moves feature folder correctly."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            quiet=True,
            worktree_manager=mock_worktree_manager,
        )

        # Verify source exists before archive
        src = temp_repo / "tasks" / "backlog" / "dark-mode"
        assert src.exists(), "Source folder should exist before archival"

        # Run archive phase
        orchestrator._archive_phase(sample_feature)

        # Verify source no longer exists
        assert not src.exists(), "Source folder should be moved after archival"

        # Verify destination exists
        today = datetime.now().strftime("%Y-%m-%d")
        dst = temp_repo / "tasks" / "completed" / today / "dark-mode"
        assert dst.exists(), "Destination folder should exist after archival"

        # Verify task files are in destination
        assert (dst / "TASK-DM-001.md").exists()
        assert (dst / "TASK-DM-002.md").exists()

    def test_archive_phase_updates_feature_yaml(
        self,
        temp_repo: Path,
        sample_feature: Feature,
        mock_worktree_manager: MagicMock,
    ) -> None:
        """Test that archive phase updates feature YAML correctly."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            quiet=True,
            worktree_manager=mock_worktree_manager,
        )

        # Run archive phase
        orchestrator._archive_phase(sample_feature)

        # Reload feature from YAML
        updated_feature = FeatureLoader.load_feature(
            "FEAT-DM-A1B2",
            repo_root=temp_repo,
        )

        # Verify status updated
        assert updated_feature.status == "awaiting_merge"

        # Verify archival metadata
        assert updated_feature.execution.archived_at is not None
        assert updated_feature.execution.archived_to is not None
        assert "dark-mode" in updated_feature.execution.archived_to
        assert "tasks/completed" in updated_feature.execution.archived_to

    def test_archive_phase_sets_completion_counts(
        self,
        temp_repo: Path,
        sample_feature: Feature,
        mock_worktree_manager: MagicMock,
    ) -> None:
        """Test that archive phase sets completion counts correctly."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            quiet=True,
            worktree_manager=mock_worktree_manager,
        )

        # Run archive phase
        orchestrator._archive_phase(sample_feature)

        # Reload feature from YAML
        updated_feature = FeatureLoader.load_feature(
            "FEAT-DM-A1B2",
            repo_root=temp_repo,
        )

        # Verify completion counts
        assert updated_feature.execution.tasks_completed == 2
        assert updated_feature.execution.tasks_failed == 0


class TestArchivePhaseEdgeCases:
    """Test edge cases in archive phase."""

    def test_archive_phase_handles_missing_folder(
        self,
        temp_repo: Path,
        sample_feature: Feature,
        mock_worktree_manager: MagicMock,
    ) -> None:
        """Test that archive phase handles missing folder gracefully."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            quiet=True,
            worktree_manager=mock_worktree_manager,
        )

        # Remove source folder (simulating already archived)
        src = temp_repo / "tasks" / "backlog" / "dark-mode"
        shutil.rmtree(src)

        # Should not raise exception
        orchestrator._archive_phase(sample_feature)

        # Feature should still be updated
        updated_feature = FeatureLoader.load_feature(
            "FEAT-DM-A1B2",
            repo_root=temp_repo,
        )
        assert updated_feature.status == "awaiting_merge"

    def test_archive_phase_creates_nested_directories(
        self,
        temp_repo: Path,
        sample_feature: Feature,
        mock_worktree_manager: MagicMock,
    ) -> None:
        """Test that archive phase creates nested date directories."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            quiet=True,
            worktree_manager=mock_worktree_manager,
        )

        # Remove completed directory to test creation
        completed_dir = temp_repo / "tasks" / "completed"
        shutil.rmtree(completed_dir)

        # Run archive phase
        orchestrator._archive_phase(sample_feature)

        # Verify directories were created
        today = datetime.now().strftime("%Y-%m-%d")
        dst = temp_repo / "tasks" / "completed" / today / "dark-mode"
        assert dst.exists()


class TestDetectFeatureSlug:
    """Test feature slug detection."""

    def test_detect_feature_slug_from_task_path(
        self,
        temp_repo: Path,
        sample_feature: Feature,
        mock_worktree_manager: MagicMock,
    ) -> None:
        """Test slug detection from standard task path."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            quiet=True,
            worktree_manager=mock_worktree_manager,
        )

        slug = orchestrator._detect_feature_slug(sample_feature)

        assert slug == "dark-mode"

    def test_detect_feature_slug_with_complex_path(self, mock_worktree_manager: MagicMock) -> None:
        """Test slug detection with complex task path."""
        # Create a feature with a complex file path
        feature = Feature(
            id="FEAT-TEST",
            name="Test Feature",
            description="Test",
            created=datetime.now().isoformat(),
            status="completed",
            complexity=5,
            estimated_tasks=1,
            tasks=[
                FeatureTask(
                    id="TASK-TEST-001",
                    name="Test Task",
                    file_path=Path(
                        "/some/repo/tasks/backlog/feature-with-dashes/TASK-TEST-001.md"
                    ),
                    complexity=3,
                    dependencies=[],
                    status="completed",
                    implementation_mode="task-work",
                    estimated_minutes=60,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-TEST-001"]],
                estimated_duration_minutes=60,
                recommended_parallel=1,
            ),
        )

        orchestrator = FeatureOrchestrator(
            repo_root=Path("/some/repo"),
            quiet=True,
            worktree_manager=mock_worktree_manager,
        )
        slug = orchestrator._detect_feature_slug(feature)

        assert slug == "feature-with-dashes"

    def test_detect_feature_slug_raises_on_no_tasks(self) -> None:
        """Test that slug detection raises error when no tasks."""
        feature = Feature(
            id="FEAT-EMPTY",
            name="Empty Feature",
            description="No tasks",
            created=datetime.now().isoformat(),
            status="completed",
            complexity=5,
            estimated_tasks=0,
            tasks=[],
            orchestration=FeatureOrchestration(
                parallel_groups=[],
                estimated_duration_minutes=0,
                recommended_parallel=1,
            ),
        )

        orchestrator = FeatureOrchestrator(repo_root=Path.cwd(), quiet=True)

        with pytest.raises(ValueError, match="No tasks in feature"):
            orchestrator._detect_feature_slug(feature)

    def test_detect_feature_slug_raises_on_invalid_path(self, mock_worktree_manager: MagicMock) -> None:
        """Test that slug detection raises error on invalid path."""
        feature = Feature(
            id="FEAT-INVALID",
            name="Invalid Feature",
            description="Invalid path",
            created=datetime.now().isoformat(),
            status="completed",
            complexity=5,
            estimated_tasks=1,
            tasks=[
                FeatureTask(
                    id="TASK-INVALID-001",
                    name="Invalid Task",
                    file_path=Path("/some/invalid/path/TASK-INVALID-001.md"),
                    complexity=3,
                    dependencies=[],
                    status="completed",
                    implementation_mode="task-work",
                    estimated_minutes=60,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-INVALID-001"]],
                estimated_duration_minutes=60,
                recommended_parallel=1,
            ),
        )

        orchestrator = FeatureOrchestrator(
            repo_root=Path("/some/repo"),
            quiet=True,
            worktree_manager=mock_worktree_manager,
        )

        with pytest.raises(ValueError, match="Cannot detect feature slug"):
            orchestrator._detect_feature_slug(feature)


class TestArchivalYAMLPersistence:
    """Test YAML persistence of archival metadata."""

    def test_archival_metadata_persists_in_yaml(
        self,
        temp_repo: Path,
        sample_feature: Feature,
        mock_worktree_manager: MagicMock,
    ) -> None:
        """Test that archival metadata is correctly persisted in YAML."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            quiet=True,
            worktree_manager=mock_worktree_manager,
        )

        # Run archive phase
        orchestrator._archive_phase(sample_feature)

        # Read YAML directly
        yaml_file = temp_repo / ".guardkit" / "features" / "FEAT-DM-A1B2.yaml"
        with open(yaml_file, "r") as f:
            yaml_data = yaml.safe_load(f)

        # Verify archival fields in YAML
        assert yaml_data["status"] == "awaiting_merge"
        assert "archived_at" in yaml_data["execution"]
        assert "archived_to" in yaml_data["execution"]
        assert yaml_data["execution"]["tasks_completed"] == 2
        assert yaml_data["execution"]["tasks_failed"] == 0


class TestArchivalWithMixedTaskStatuses:
    """Test archival with mixed task completion statuses."""

    def test_archive_phase_counts_mixed_statuses(
        self,
        temp_repo: Path,
    ) -> None:
        """Test that archive counts are correct with mixed task statuses."""
        task_dir = temp_repo / "tasks" / "backlog" / "mixed-feature"
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create task files
        for i in range(1, 4):
            task_file = task_dir / f"TASK-MIX-00{i}.md"
            task_file.write_text(f"# Task MIX-00{i}\n\nTest task")

        # Create feature with mixed statuses
        feature = Feature(
            id="FEAT-MIXED",
            name="Mixed Status Feature",
            description="Test mixed statuses",
            created=datetime.now().isoformat(),
            status="failed",
            complexity=6,
            estimated_tasks=3,
            tasks=[
                FeatureTask(
                    id="TASK-MIX-001",
                    name="Task 1",
                    file_path=task_dir / "TASK-MIX-001.md",
                    complexity=3,
                    dependencies=[],
                    status="completed",
                    implementation_mode="task-work",
                    estimated_minutes=60,
                ),
                FeatureTask(
                    id="TASK-MIX-002",
                    name="Task 2",
                    file_path=task_dir / "TASK-MIX-002.md",
                    complexity=3,
                    dependencies=[],
                    status="completed",
                    implementation_mode="task-work",
                    estimated_minutes=60,
                ),
                FeatureTask(
                    id="TASK-MIX-003",
                    name="Task 3",
                    file_path=task_dir / "TASK-MIX-003.md",
                    complexity=3,
                    dependencies=[],
                    status="failed",
                    implementation_mode="task-work",
                    estimated_minutes=60,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-MIX-001"], ["TASK-MIX-002"], ["TASK-MIX-003"]],
                estimated_duration_minutes=180,
                recommended_parallel=1,
            ),
            execution=FeatureExecution(
                started_at=datetime.now().isoformat(),
                tasks_completed=2,
                tasks_failed=1,
            ),
            file_path=temp_repo / ".guardkit" / "features" / "FEAT-MIXED.yaml",
        )

        # Save feature to YAML
        FeatureLoader.save_feature(feature, temp_repo)

        # Run archive phase
        mock_mgr = MagicMock()
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            quiet=True,
            worktree_manager=mock_mgr,
        )
        orchestrator._archive_phase(feature)

        # Reload and verify
        updated_feature = FeatureLoader.load_feature(
            "FEAT-MIXED",
            repo_root=temp_repo,
        )

        assert updated_feature.execution.tasks_completed == 2
        assert updated_feature.execution.tasks_failed == 1
