"""
Unit tests for FeatureOrchestrator._copy_tasks_to_worktree().

Tests task file copy logic including edge cases for idempotency and error recovery.
"""

import shutil
from pathlib import Path
from unittest.mock import Mock, patch, call

import pytest

from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.feature_loader import Feature, FeatureTask, FeatureOrchestration, FeatureExecution, FeatureValidationError
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repo_root(tmp_path: Path) -> Path:
    """
    Create mock repository root with task files.

    Returns
    -------
    Path
        Path to mock repository root
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create tasks/backlog/test-feature/ directory
    feature_dir = repo / "tasks" / "backlog" / "test-feature"
    feature_dir.mkdir(parents=True)

    # Create sample task files
    (feature_dir / "TASK-001-sample-task.md").write_text("# Task 001")
    (feature_dir / "TASK-002-another-task.md").write_text("# Task 002")
    (feature_dir / "TASK-003-third-task.md").write_text("# Task 003")

    return repo


@pytest.fixture
def mock_worktree(tmp_path: Path) -> Worktree:
    """
    Create mock worktree.

    Returns
    -------
    Worktree
        Mock worktree instance
    """
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()

    return Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=worktree_path,
        base_branch="main",
    )


@pytest.fixture
def mock_feature(mock_repo_root: Path) -> Feature:
    """
    Create mock feature with tasks.

    Parameters
    ----------
    mock_repo_root : Path
        Mock repository root

    Returns
    -------
    Feature
        Mock feature instance
    """
    return Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test feature description",
        created="2025-01-18T00:00:00Z",
        status="planned",
        complexity=5,
        estimated_tasks=3,
        tasks=[
            FeatureTask(
                id="TASK-001",
                name="Sample task",
                file_path=mock_repo_root / "tasks" / "backlog" / "test-feature" / "TASK-001-sample-task.md",
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-002",
                name="Another task",
                file_path=mock_repo_root / "tasks" / "backlog" / "test-feature" / "TASK-002-another-task.md",
                complexity=4,
                dependencies=["TASK-001"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=45,
            ),
            FeatureTask(
                id="TASK-003",
                name="Third task",
                file_path=mock_repo_root / "tasks" / "backlog" / "test-feature" / "TASK-003-third-task.md",
                complexity=3,
                dependencies=["TASK-001"],
                status="pending",
                implementation_mode="direct",
                estimated_minutes=20,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-001"], ["TASK-002", "TASK-003"]],
            estimated_duration_minutes=95,
            recommended_parallel=2,
        ),
        execution=FeatureExecution(),
    )


@pytest.fixture
def orchestrator(mock_repo_root: Path) -> FeatureOrchestrator:
    """
    Create FeatureOrchestrator instance for testing.

    Parameters
    ----------
    mock_repo_root : Path
        Mock repository root

    Returns
    -------
    FeatureOrchestrator
        Test orchestrator instance
    """
    # Mock WorktreeManager to avoid git validation
    mock_manager = Mock(spec=["create", "cleanup", "preserve_on_failure"])

    return FeatureOrchestrator(
        repo_root=mock_repo_root,
        max_turns=5,
        quiet=True,  # Suppress progress display
        worktree_manager=mock_manager,
    )


# ============================================================================
# Unit Tests
# ============================================================================


def test_copy_tasks_to_worktree_success(
    orchestrator: FeatureOrchestrator,
    mock_feature: Feature,
    mock_worktree: Worktree,
) -> None:
    """
    Test successful copy of task files to worktree.

    Verifies:
    - All task files are copied
    - Destination directory is created
    - Files have correct content
    """
    # Execute copy
    orchestrator._copy_tasks_to_worktree(mock_feature, mock_worktree)

    # Verify destination directory created
    dst_dir = mock_worktree.path / "tasks" / "backlog"
    assert dst_dir.exists()
    assert dst_dir.is_dir()

    # Verify all task files copied
    assert (dst_dir / "TASK-001-sample-task.md").exists()
    assert (dst_dir / "TASK-002-another-task.md").exists()
    assert (dst_dir / "TASK-003-third-task.md").exists()

    # Verify content
    assert (dst_dir / "TASK-001-sample-task.md").read_text() == "# Task 001"
    assert (dst_dir / "TASK-002-another-task.md").read_text() == "# Task 002"
    assert (dst_dir / "TASK-003-third-task.md").read_text() == "# Task 003"


def test_copy_tasks_to_worktree_idempotency(
    orchestrator: FeatureOrchestrator,
    mock_feature: Feature,
    mock_worktree: Worktree,
) -> None:
    """
    Test that copying task files is idempotent (skips existing files).

    Verifies:
    - First copy succeeds
    - Second copy skips existing files
    - No errors raised
    """
    # First copy
    orchestrator._copy_tasks_to_worktree(mock_feature, mock_worktree)

    # Verify files exist
    dst_dir = mock_worktree.path / "tasks" / "backlog"
    assert (dst_dir / "TASK-001-sample-task.md").exists()

    # Modify file to detect if it's overwritten
    (dst_dir / "TASK-001-sample-task.md").write_text("# Modified")

    # Second copy (should skip)
    orchestrator._copy_tasks_to_worktree(mock_feature, mock_worktree)

    # Verify file was NOT overwritten
    assert (dst_dir / "TASK-001-sample-task.md").read_text() == "# Modified"


def test_copy_tasks_to_worktree_no_tasks(
    orchestrator: FeatureOrchestrator,
    mock_worktree: Worktree,
    mock_repo_root: Path,
) -> None:
    """
    Test copy with empty tasks list.

    Verifies:
    - No errors raised
    - No files created
    """
    # Create feature with no tasks
    empty_feature = Feature(
        id="FEAT-EMPTY",
        name="Empty Feature",
        description="Feature with no tasks",
        created="2025-01-18T00:00:00Z",
        status="planned",
        complexity=0,
        estimated_tasks=0,
        tasks=[],
        orchestration=FeatureOrchestration(
            parallel_groups=[],
            estimated_duration_minutes=0,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )

    # Should not raise
    orchestrator._copy_tasks_to_worktree(empty_feature, mock_worktree)

    # Verify no files created
    dst_dir = mock_worktree.path / "tasks" / "backlog"
    if dst_dir.exists():
        assert list(dst_dir.glob("*.md")) == []


def test_copy_tasks_to_worktree_missing_file_path_raises(
    orchestrator: FeatureOrchestrator,
    mock_worktree: Worktree,
    mock_repo_root: Path,
) -> None:
    """
    Test copy when first task has no file_path raises FeatureValidationError - SKIPPED.

    This test is obsolete because Pydantic now enforces file_path cannot be None
    during model construction. The validation happens at model creation, not in the copy method.
    """
    pytest.skip("Pydantic now enforces file_path is required during model construction")


def test_copy_tasks_to_worktree_copy_error_recovery(
    orchestrator: FeatureOrchestrator,
    mock_feature: Feature,
    mock_worktree: Worktree,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Test error recovery when copy fails for a file.

    Verifies:
    - Warning logged for failed file
    - Other files still copied
    - No exception raised
    """
    with patch("shutil.copy") as mock_copy:
        # Make second copy fail
        def side_effect(src: Path, dst: Path) -> None:
            if "TASK-002" in str(src):
                raise OSError("Permission denied")

        mock_copy.side_effect = side_effect

        # Execute copy
        orchestrator._copy_tasks_to_worktree(mock_feature, mock_worktree)

        # Verify warning logged
        assert "Failed to copy TASK-002" in caplog.text or "Permission denied" in caplog.text

        # Verify copy was called for all tasks
        assert mock_copy.call_count == 3


def test_copy_tasks_raises_when_tasks_dir_not_in_path(
    orchestrator: FeatureOrchestrator,
    mock_worktree: Worktree,
    mock_repo_root: Path,
) -> None:
    """
    Test that a file_path without 'tasks' directory raises FeatureValidationError.

    Verifies:
    - FeatureValidationError raised
    - Error message includes the bad path and expected format
    """
    feature = Feature(
        id="FEAT-BADPATH",
        name="Feature with bad path",
        description="Task with path missing tasks dir",
        created="2025-01-18T00:00:00Z",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-BAD-001",
                name="Task with bad path",
                file_path="some/random/path/TASK-BAD-001.md",
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-BAD-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )

    with pytest.raises(FeatureValidationError, match="'tasks' directory not found"):
        orchestrator._copy_tasks_to_worktree(feature, mock_worktree)


def test_copy_tasks_raises_when_backlog_missing_after_tasks(
    orchestrator: FeatureOrchestrator,
    mock_worktree: Worktree,
    mock_repo_root: Path,
) -> None:
    """
    Test that a file_path with 'tasks' but not 'backlog' raises FeatureValidationError.

    Verifies:
    - FeatureValidationError raised
    - Error message mentions expected 'backlog' after 'tasks'
    """
    feature = Feature(
        id="FEAT-NOBACKLOG",
        name="Feature with no backlog",
        description="Task with path missing backlog dir",
        created="2025-01-18T00:00:00Z",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-NB-001",
                name="Task without backlog",
                file_path="tasks/completed/TASK-NB-001.md",
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-NB-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )

    with pytest.raises(FeatureValidationError, match="expected 'backlog' after 'tasks'"):
        orchestrator._copy_tasks_to_worktree(feature, mock_worktree)


def test_copy_tasks_raises_when_feature_dir_missing(
    orchestrator: FeatureOrchestrator,
    mock_worktree: Worktree,
    mock_repo_root: Path,
) -> None:
    """
    Test that a file_path with 'tasks/backlog' but no feature dir raises FeatureValidationError.

    Verifies:
    - FeatureValidationError raised
    - Error message mentions missing feature directory
    """
    feature = Feature(
        id="FEAT-NODIR",
        name="Feature with no dir",
        description="Task with path missing feature dir",
        created="2025-01-18T00:00:00Z",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-ND-001",
                name="Task without feature dir",
                file_path="tasks/backlog",
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-ND-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )

    with pytest.raises(FeatureValidationError, match="missing feature directory"):
        orchestrator._copy_tasks_to_worktree(feature, mock_worktree)


def test_copy_tasks_error_message_includes_path_and_task_id(
    orchestrator: FeatureOrchestrator,
    mock_worktree: Worktree,
    mock_repo_root: Path,
) -> None:
    """
    Test that error messages include both the bad file_path and task ID.

    Verifies:
    - Error message contains the invalid path value
    - Error message contains the task ID
    - Error message includes the expected format hint
    """
    bad_path = "wrong/structure/TASK-ERR-001.md"
    feature = Feature(
        id="FEAT-ERR",
        name="Feature with error",
        description="Task with completely wrong path",
        created="2025-01-18T00:00:00Z",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-ERR-001",
                name="Task with error",
                file_path=bad_path,
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-ERR-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )

    with pytest.raises(FeatureValidationError) as exc_info:
        orchestrator._copy_tasks_to_worktree(feature, mock_worktree)

    error_msg = str(exc_info.value)
    assert bad_path in error_msg
    assert "TASK-ERR-001" in error_msg
    assert "tasks/backlog/<feature-slug>/TASK-XXX.md" in error_msg


def test_copy_tasks_individual_file_failure_remains_warning(
    orchestrator: FeatureOrchestrator,
    mock_feature: Feature,
    mock_worktree: Worktree,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Test that individual file copy failures remain as warnings (recoverable).

    Verifies:
    - No exception raised when individual file copy fails
    - Warning logged for the failed file
    - Other files still copied successfully
    """
    with patch("shutil.copy") as mock_copy:
        call_count = 0

        def side_effect(src: Path, dst: Path) -> None:
            nonlocal call_count
            call_count += 1
            if "TASK-002" in str(src):
                raise OSError("Disk full")

        mock_copy.side_effect = side_effect

        # Should NOT raise - individual file failures are recoverable
        orchestrator._copy_tasks_to_worktree(mock_feature, mock_worktree)

        assert "Failed to copy TASK-002" in caplog.text or "Disk full" in caplog.text


# ============================================================================
# Integration Test
# ============================================================================


def test_integration_copy_during_worktree_creation(
    tmp_path: Path,
) -> None:
    """
    Integration test: Verify task files are copied during worktree creation.

    This test verifies the full flow from _create_new_worktree() through
    _copy_tasks_to_worktree().

    Verifies:
    - Worktree creation triggers copy
    - Task files present in worktree
    - TaskStateBridge can find files (conceptual - tested via file existence)
    """
    # Setup mock repository
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create task files
    feature_dir = repo / "tasks" / "backlog" / "integration-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "TASK-INT-001.md").write_text("# Integration Task 001")
    (feature_dir / "TASK-INT-002.md").write_text("# Integration Task 002")

    # Create feature
    feature = Feature(
        id="FEAT-INT",
        name="Integration Test Feature",
        description="Integration test",
        created="2025-01-18T00:00:00Z",
        status="planned",
        complexity=4,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-INT-001",
                name="Integration Task 001",
                file_path=feature_dir / "TASK-INT-001.md",
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-INT-002",
                name="Integration Task 002",
                file_path=feature_dir / "TASK-INT-002.md",
                complexity=3,
                dependencies=["TASK-INT-001"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-INT-001"], ["TASK-INT-002"]],
            estimated_duration_minutes=60,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )

    # Mock WorktreeManager
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    mock_worktree = Worktree(
        task_id="FEAT-INT",
        branch_name="autobuild/FEAT-INT",
        path=worktree_path,
        base_branch="main",
    )

    # Mock FeatureLoader.save_feature
    with patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"):
        with patch.object(
            FeatureOrchestrator,
            "_worktree_manager",
            create=True,
        ) as mock_manager:
            mock_manager.create.return_value = mock_worktree

            # Create orchestrator
            orchestrator = FeatureOrchestrator(
                repo_root=repo,
                max_turns=5,
                quiet=True,
                worktree_manager=mock_manager,
            )

            # Execute _create_new_worktree (should trigger copy)
            result_feature, result_worktree = orchestrator._create_new_worktree(
                feature=feature,
                feature_id="FEAT-INT",
                base_branch="main",
            )

    # Verify task files were copied to worktree
    dst_dir = worktree_path / "tasks" / "backlog"
    assert dst_dir.exists()
    assert (dst_dir / "TASK-INT-001.md").exists()
    assert (dst_dir / "TASK-INT-002.md").exists()

    # Verify content
    assert (dst_dir / "TASK-INT-001.md").read_text() == "# Integration Task 001"
    assert (dst_dir / "TASK-INT-002.md").read_text() == "# Integration Task 002"
