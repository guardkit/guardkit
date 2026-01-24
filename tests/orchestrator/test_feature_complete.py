"""Tests for feature completion orchestrator."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from guardkit.orchestrator.feature_complete import (
    FeatureCompleteOrchestrator,
    FeatureCompleteResult,
    FeatureCompleteError,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureNotFoundError,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repo_root(tmp_path):
    """Create a temporary repository root."""
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def mock_feature():
    """Create a mock feature."""
    from guardkit.orchestrator.feature_loader import FeatureExecution, FeatureOrchestration

    task1 = FeatureTask(
        id="TASK-001",
        name="Task 1",
        file_path=Path("tasks/backlog/TASK-001.md"),
        complexity=5,
        dependencies=[],
        status="completed",
        implementation_mode="task-work",
        estimated_minutes=30,
        started_at=None,
        completed_at=None,
        turns_completed=0,
        current_turn=0,
        result=None,
    )

    task2 = FeatureTask(
        id="TASK-002",
        name="Task 2",
        file_path=Path("tasks/backlog/TASK-002.md"),
        complexity=5,
        dependencies=[],
        status="completed",
        implementation_mode="task-work",
        estimated_minutes=30,
        started_at=None,
        completed_at=None,
        turns_completed=0,
        current_turn=0,
        result=None,
    )

    # Create mock execution
    execution = FeatureExecution(
        started_at=None,
        completed_at=None,
        worktree_path=None,
        current_wave=0,
        completed_waves=[],
        tasks_completed=2,
        tasks_failed=0,
        total_turns=0,
        last_updated=None,
    )

    # Create mock orchestration
    orchestration = FeatureOrchestration(
        parallel_groups=[["TASK-001"], ["TASK-002"]],
        estimated_duration_minutes=60,
        recommended_parallel=2,
    )

    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test feature for unit tests",
        created="2025-01-24T10:00:00Z",  # Fixed: use 'created' instead of 'created_at'
        status="in_progress",
        complexity=5,
        estimated_tasks=2,
        tasks=[task1, task2],
        orchestration=orchestration,
        execution=execution,
    )

    return feature


@pytest.fixture
def mock_worktree(tmp_path):
    """Create a mock worktree."""
    worktree_path = tmp_path / ".guardkit" / "worktrees" / "FEAT-TEST"
    worktree_path.mkdir(parents=True, exist_ok=True)

    return Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=worktree_path,
        base_branch="main",
    )


@pytest.fixture
def mock_worktree_manager():
    """Create a mock WorktreeManager."""
    manager = Mock()
    manager.repo_root = Path("/tmp")
    manager.worktrees_dir = Path("/tmp/.guardkit/worktrees")
    return manager


# ============================================================================
# Tests
# ============================================================================


class TestFeatureCompleteOrchestrator:
    """Tests for FeatureCompleteOrchestrator class."""

    def test_initialization(self, mock_repo_root, mock_worktree_manager):
        """Test orchestrator initialization."""
        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            worktree_manager=mock_worktree_manager,
            dry_run=True,
            force=False,
        )

        assert orchestrator.repo_root == mock_repo_root
        assert orchestrator.dry_run is True
        assert orchestrator.force is False
        assert orchestrator.features_dir == mock_repo_root / ".guardkit" / "features"

    def test_initialization_with_custom_features_dir(self, mock_repo_root, mock_worktree_manager):
        """Test orchestrator initialization with custom features directory."""
        custom_dir = mock_repo_root / "custom" / "features"

        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            features_dir=custom_dir,
            worktree_manager=mock_worktree_manager,
        )

        assert orchestrator.features_dir == custom_dir

    @patch("guardkit.orchestrator.feature_complete.FeatureLoader.load_feature")
    def test_validate_phase_success(self, mock_load_feature, mock_repo_root, mock_feature, mock_worktree_manager):
        """Test validation phase with valid feature."""
        mock_load_feature.return_value = mock_feature

        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=False,
        )

        feature, worktree = orchestrator._validate_phase("FEAT-TEST")

        assert feature == mock_feature
        assert worktree is None  # No worktree path in mock feature
        mock_load_feature.assert_called_once()

    @patch("guardkit.orchestrator.feature_complete.FeatureLoader.load_feature")
    def test_validate_phase_already_completed(
        self, mock_load_feature, mock_repo_root, mock_feature, mock_worktree_manager
    ):
        """Test validation phase when feature already completed."""
        mock_feature.status = "completed"
        mock_load_feature.return_value = mock_feature

        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=False,
        )

        with pytest.raises(FeatureCompleteError) as exc_info:
            orchestrator._validate_phase("FEAT-TEST")

        assert "already completed" in str(exc_info.value)

    @patch("guardkit.orchestrator.feature_complete.FeatureLoader.load_feature")
    def test_validate_phase_incomplete_tasks(
        self, mock_load_feature, mock_repo_root, mock_feature, mock_worktree_manager
    ):
        """Test validation phase with incomplete tasks."""
        # Mark one task as incomplete
        mock_feature.tasks[0].status = "in_progress"
        mock_load_feature.return_value = mock_feature

        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=False,
        )

        with pytest.raises(FeatureCompleteError) as exc_info:
            orchestrator._validate_phase("FEAT-TEST")

        assert "incomplete" in str(exc_info.value)

    @patch("guardkit.orchestrator.feature_complete.FeatureLoader.load_feature")
    def test_validate_phase_force_override(
        self, mock_load_feature, mock_repo_root, mock_feature, mock_worktree_manager
    ):
        """Test validation phase with force flag overrides incomplete check."""
        # Mark one task as incomplete
        mock_feature.tasks[0].status = "in_progress"
        mock_load_feature.return_value = mock_feature

        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=True,
        )

        # Should not raise error with force=True
        feature, worktree = orchestrator._validate_phase("FEAT-TEST")
        assert feature == mock_feature

    @patch("guardkit.orchestrator.feature_complete.FeatureLoader.load_feature")
    def test_validate_phase_with_worktree(
        self, mock_load_feature, mock_repo_root, mock_feature, mock_worktree, mock_worktree_manager
    ):
        """Test validation phase finds existing worktree."""
        mock_feature.execution.worktree_path = str(mock_worktree.path)
        mock_load_feature.return_value = mock_feature

        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=False,
        )

        feature, worktree = orchestrator._validate_phase("FEAT-TEST")

        assert feature == mock_feature
        assert worktree is not None
        assert worktree.path == mock_worktree.path

    def test_completion_phase_placeholder(self, mock_feature, mock_worktree_manager):
        """Test completion phase is a placeholder."""
        orchestrator = FeatureCompleteOrchestrator(
            repo_root=Path("/tmp"),
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=False,
        )

        # Should not raise error - just a placeholder
        orchestrator._completion_phase(mock_feature)

    def test_archival_phase_placeholder(self, mock_feature, mock_worktree, mock_worktree_manager):
        """Test archival phase is a placeholder."""
        orchestrator = FeatureCompleteOrchestrator(
            repo_root=Path("/tmp"),
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=False,
        )

        # Should not raise error - just a placeholder
        orchestrator._archival_phase(mock_feature, mock_worktree)

    def test_handoff_phase_placeholder(self, mock_feature, mock_worktree, mock_worktree_manager):
        """Test handoff phase is a placeholder."""
        orchestrator = FeatureCompleteOrchestrator(
            repo_root=Path("/tmp"),
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=False,
        )

        # Should not raise error - just a placeholder
        orchestrator._handoff_phase(mock_feature, mock_worktree)

    @patch("guardkit.orchestrator.feature_complete.FeatureLoader.load_feature")
    def test_complete_success(self, mock_load_feature, mock_repo_root, mock_feature, mock_worktree_manager):
        """Test complete method success path."""
        mock_load_feature.return_value = mock_feature

        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=False,
        )

        result = orchestrator.complete("FEAT-TEST")

        assert result.success is True
        assert result.feature_id == "FEAT-TEST"
        assert result.status == "completed"
        assert result.tasks_completed == 2
        assert result.total_tasks == 2

    @patch("guardkit.orchestrator.feature_complete.FeatureLoader.load_feature")
    def test_complete_feature_not_found(self, mock_load_feature, mock_repo_root, mock_worktree_manager):
        """Test complete method when feature not found."""
        mock_load_feature.side_effect = FeatureNotFoundError("Feature not found")

        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            worktree_manager=mock_worktree_manager,
            dry_run=False,
            force=False,
        )

        with pytest.raises(FeatureNotFoundError):
            orchestrator.complete("FEAT-MISSING")

    @patch("guardkit.orchestrator.feature_complete.FeatureLoader.load_feature")
    def test_complete_dry_run_mode(self, mock_load_feature, mock_repo_root, mock_feature, mock_worktree_manager):
        """Test complete method in dry-run mode."""
        # Mark feature as already completed
        mock_feature.status = "completed"
        mock_load_feature.return_value = mock_feature

        orchestrator = FeatureCompleteOrchestrator(
            repo_root=mock_repo_root,
            worktree_manager=mock_worktree_manager,
            dry_run=True,  # Dry-run mode
            force=False,
        )

        # Should not raise error in dry-run mode
        result = orchestrator.complete("FEAT-TEST")
        assert result.success is True


class TestFeatureCompleteResult:
    """Tests for FeatureCompleteResult dataclass."""

    def test_result_creation(self):
        """Test creating a FeatureCompleteResult."""
        result = FeatureCompleteResult(
            feature_id="FEAT-TEST",
            success=True,
            status="completed",
            tasks_completed=5,
            total_tasks=5,
            worktree_path="/tmp/.guardkit/worktrees/FEAT-TEST",
        )

        assert result.feature_id == "FEAT-TEST"
        assert result.success is True
        assert result.status == "completed"
        assert result.tasks_completed == 5
        assert result.total_tasks == 5
        assert result.worktree_path == "/tmp/.guardkit/worktrees/FEAT-TEST"
        assert result.error is None

    def test_result_creation_with_error(self):
        """Test creating a FeatureCompleteResult with error."""
        result = FeatureCompleteResult(
            feature_id="FEAT-TEST",
            success=False,
            status="failed",
            tasks_completed=2,
            total_tasks=5,
            error="Some tasks failed",
        )

        assert result.success is False
        assert result.status == "failed"
        assert result.error == "Some tasks failed"


class TestFeatureCompleteError:
    """Tests for FeatureCompleteError exception."""

    def test_exception_creation(self):
        """Test creating a FeatureCompleteError."""
        error = FeatureCompleteError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
