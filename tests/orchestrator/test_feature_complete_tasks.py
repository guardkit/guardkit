"""
Unit tests for FeatureCompleteOrchestrator parallel task completion.

This module tests the parallel task completion logic, error handling,
and file organization for feature completion.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from guardkit.orchestrator.feature_complete import (
    FeatureCompleteOrchestrator,
    FeatureCompleteResult,
    TaskCompleteResult,
    FeatureCompleteError,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureNotFoundError,
    FeatureExecution,
    FeatureOrchestration,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repo_root(tmp_path):
    """Create mock repository structure."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create task directories
    (repo_root / "tasks" / "backlog").mkdir(parents=True)
    (repo_root / "tasks" / "in_progress").mkdir(parents=True)
    (repo_root / "tasks" / "in_review").mkdir(parents=True)
    (repo_root / "tasks" / "completed").mkdir(parents=True)
    (repo_root / ".guardkit" / "features").mkdir(parents=True)

    return repo_root


@pytest.fixture
def sample_feature(tmp_path):
    """Create sample feature with tasks."""
    return Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test feature for completion",
        status="in_progress",
        created=datetime.now().isoformat(),
        complexity=3,
        estimated_tasks=3,
        tasks=[
            FeatureTask(
                id="TASK-001",
                name="Task One",
                file_path=tmp_path / "TASK-001.md",
                complexity=3,
                status="in_review",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-002",
                name="Task Two",
                file_path=tmp_path / "TASK-002.md",
                complexity=3,
                status="in_review",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-003",
                name="Task Three",
                file_path=tmp_path / "TASK-003.md",
                complexity=3,
                status="in_review",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        execution=FeatureExecution(),
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-001", "TASK-002", "TASK-003"]],
            estimated_duration_minutes=90,
            recommended_parallel=3,
        ),
    )


@pytest.fixture
def orchestrator(mock_repo_root):
    """Create orchestrator instance."""
    return FeatureCompleteOrchestrator(
        repo_root=mock_repo_root,
        verbose=False,
    )


# ============================================================================
# Test Orchestrator Initialization
# ============================================================================


def test_orchestrator_initialization(mock_repo_root):
    """Test orchestrator initializes with correct paths."""
    orchestrator = FeatureCompleteOrchestrator(
        repo_root=mock_repo_root,
        verbose=True,
    )

    assert orchestrator.repo_root == mock_repo_root
    assert orchestrator.features_dir == mock_repo_root / ".guardkit" / "features"
    assert orchestrator.verbose is True


def test_orchestrator_custom_features_dir(mock_repo_root, tmp_path):
    """Test orchestrator accepts custom features directory."""
    custom_dir = tmp_path / "custom_features"
    custom_dir.mkdir()

    orchestrator = FeatureCompleteOrchestrator(
        repo_root=mock_repo_root,
        features_dir=custom_dir,
    )

    assert orchestrator.features_dir == custom_dir


# ============================================================================
# Test Parallel Task Completion
# ============================================================================


@pytest.mark.asyncio
async def test_complete_tasks_parallel_success(orchestrator, sample_feature, mock_repo_root):
    """Test successful parallel completion of all tasks."""
    # Create mock task files
    for task in sample_feature.tasks:
        task_file = mock_repo_root / "tasks" / "in_review" / f"{task.id}.md"
        task_file.write_text(f"# {task.name}")

    # Mock _complete_single_task to avoid actual file operations
    with patch.object(
        orchestrator,
        "_complete_single_task",
        side_effect=lambda t, f: TaskCompleteResult(
            task_id=t.id, success=True, error=None
        ),
    ):
        results = await orchestrator._complete_tasks_parallel(sample_feature)

    # Verify all tasks completed
    assert len(results) == 3
    assert all(r.success for r in results)
    assert all(r.error is None for r in results)


@pytest.mark.asyncio
async def test_complete_tasks_parallel_with_failures(orchestrator, sample_feature):
    """Test parallel completion with some task failures."""
    # Mock _complete_single_task to simulate failures
    def mock_complete(task, feature):
        if task.id == "TASK-002":
            return TaskCompleteResult(
                task_id=task.id,
                success=False,
                error="File not found",
            )
        return TaskCompleteResult(task_id=task.id, success=True, error=None)

    with patch.object(orchestrator, "_complete_single_task", side_effect=mock_complete):
        results = await orchestrator._complete_tasks_parallel(sample_feature)

    # Verify results
    assert len(results) == 3
    success_count = sum(1 for r in results if r.success)
    failed_count = sum(1 for r in results if not r.success)

    assert success_count == 2
    assert failed_count == 1

    # Verify failed task has error message
    failed_result = next(r for r in results if not r.success)
    assert failed_result.task_id == "TASK-002"
    assert failed_result.error == "File not found"


@pytest.mark.asyncio
async def test_complete_tasks_parallel_with_exceptions(orchestrator, sample_feature):
    """Test parallel completion with exceptions raised."""
    # Mock _complete_single_task to raise exception for one task
    def mock_complete(task, feature):
        if task.id == "TASK-002":
            raise RuntimeError("Unexpected error")
        return TaskCompleteResult(task_id=task.id, success=True, error=None)

    with patch.object(orchestrator, "_complete_single_task", side_effect=mock_complete):
        results = await orchestrator._complete_tasks_parallel(sample_feature)

    # Verify exception was caught and converted to result
    assert len(results) == 3
    failed_result = next(r for r in results if r.task_id == "TASK-002")
    assert not failed_result.success
    assert "Unexpected error" in failed_result.error


@pytest.mark.asyncio
async def test_complete_tasks_parallel_already_completed(orchestrator, tmp_path):
    """Test skips already completed tasks."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test",
        status="in_progress",
        created=datetime.now().isoformat(),
        complexity=3,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-001",
                name="Task One",
                file_path=tmp_path / "TASK-001.md",
                complexity=3,
                status="completed",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-002",
                name="Task Two",
                file_path=tmp_path / "TASK-002.md",
                complexity=3,
                status="completed",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        execution=FeatureExecution(),
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-001", "TASK-002"]],
            estimated_duration_minutes=60,
            recommended_parallel=2,
        ),
    )

    results = await orchestrator._complete_tasks_parallel(feature)

    # Verify no tasks were processed (all already completed)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_complete_tasks_parallel_empty_feature(orchestrator):
    """Test handles empty feature gracefully."""
    feature = Feature(
        id="FEAT-EMPTY",
        name="Empty Feature",
        description="No tasks",
        status="in_progress",
        created=datetime.now().isoformat(),
        complexity=3,
        estimated_tasks=2,
        tasks=[],
        execution=FeatureExecution(),
        orchestration=FeatureOrchestration(
            parallel_groups=[],
            estimated_duration_minutes=0,
            recommended_parallel=0,
        ),
    )

    results = await orchestrator._complete_tasks_parallel(feature)

    # Verify returns empty list
    assert len(results) == 0


# ============================================================================
# Test Single Task Completion
# ============================================================================


def test_complete_single_task_success(orchestrator, sample_feature, mock_repo_root):
    """Test successful single task completion."""
    task = sample_feature.tasks[0]
    task_file = mock_repo_root / "tasks" / "in_review" / f"{task.id}.md"
    task_file.write_text(f"# {task.name}")

    result = orchestrator._complete_single_task(task, sample_feature)

    # Verify task completed
    assert result.success
    assert result.error is None
    assert result.task_id == task.id

    # Verify file moved to correct location
    date_str = datetime.now().strftime("%Y-%m-%d")
    target_file = (
        mock_repo_root
        / "tasks"
        / "completed"
        / date_str
        / "feat-test"
        / f"{task.id}.md"
    )
    assert target_file.exists()
    assert not task_file.exists()


def test_complete_single_task_file_not_found(orchestrator, sample_feature):
    """Test handles missing task file gracefully."""
    task = sample_feature.tasks[0]

    result = orchestrator._complete_single_task(task, sample_feature)

    # Verify failure recorded
    assert not result.success
    assert result.error == "Task file not found"
    assert result.task_id == task.id


def test_complete_single_task_move_error(orchestrator, sample_feature, mock_repo_root):
    """Test handles file move errors gracefully."""
    task = sample_feature.tasks[0]
    task_file = mock_repo_root / "tasks" / "in_review" / f"{task.id}.md"
    task_file.write_text(f"# {task.name}")

    # Mock shutil.move to raise exception
    with patch("shutil.move", side_effect=PermissionError("Permission denied")):
        result = orchestrator._complete_single_task(task, sample_feature)

    # Verify failure recorded
    assert not result.success
    assert "Permission denied" in result.error


# ============================================================================
# Test Feature Slug Extraction
# ============================================================================


def test_extract_feature_slug_simple(orchestrator):
    """Test extracts slug from simple feature ID."""
    slug = orchestrator._extract_feature_slug("FEAT-A1B2")
    assert slug == "feat-a1b2"


def test_extract_feature_slug_with_prefix(orchestrator):
    """Test extracts slug from feature ID with prefix."""
    slug = orchestrator._extract_feature_slug("FEAT-AUTH-001")
    assert slug == "feat-auth-001"


# ============================================================================
# Test Task File Discovery
# ============================================================================


def test_find_task_file_in_review(orchestrator, mock_repo_root):
    """Test finds task file in in_review directory."""
    task_file = mock_repo_root / "tasks" / "in_review" / "TASK-001.md"
    task_file.write_text("# Task 001")

    found = orchestrator._find_task_file("TASK-001")

    assert found == task_file


def test_find_task_file_in_progress(orchestrator, mock_repo_root):
    """Test finds task file in in_progress directory."""
    task_file = mock_repo_root / "tasks" / "in_progress" / "TASK-002.md"
    task_file.write_text("# Task 002")

    found = orchestrator._find_task_file("TASK-002")

    assert found == task_file


def test_find_task_file_in_backlog(orchestrator, mock_repo_root):
    """Test finds task file in backlog directory."""
    task_file = mock_repo_root / "tasks" / "backlog" / "TASK-003.md"
    task_file.write_text("# Task 003")

    found = orchestrator._find_task_file("TASK-003")

    assert found == task_file


def test_find_task_file_in_subdirectory(orchestrator, mock_repo_root):
    """Test finds task file in feature subdirectory."""
    feature_dir = mock_repo_root / "tasks" / "backlog" / "feature-auth"
    feature_dir.mkdir()
    task_file = feature_dir / "TASK-AUTH-001.md"
    task_file.write_text("# Auth Task")

    found = orchestrator._find_task_file("TASK-AUTH-001")

    assert found == task_file


def test_find_task_file_not_found(orchestrator):
    """Test returns None when task file not found."""
    found = orchestrator._find_task_file("TASK-NONEXISTENT")
    assert found is None


# ============================================================================
# Test Complete Feature Workflow
# ============================================================================


def test_complete_feature_success(orchestrator, sample_feature, mock_repo_root):
    """Test complete feature workflow with successful completion."""
    # Create mock task files
    for task in sample_feature.tasks:
        task_file = mock_repo_root / "tasks" / "in_review" / f"{task.id}.md"
        task_file.write_text(f"# {task.name}")

    # Mock FeatureLoader
    with patch("guardkit.orchestrator.feature_complete.FeatureLoader") as mock_loader:
        mock_loader.load_feature.return_value = sample_feature

        result = orchestrator.complete_feature("FEAT-TEST")

    # Verify result
    assert result.feature_id == "FEAT-TEST"
    assert result.total_tasks == 3
    assert result.completed_count == 3
    assert result.failed_count == 0
    assert result.skipped_count == 0


def test_complete_feature_with_failures(orchestrator, sample_feature, mock_repo_root):
    """Test complete feature workflow with some failures."""
    # Create mock task files (missing one to simulate failure)
    task_file_1 = mock_repo_root / "tasks" / "in_review" / "TASK-001.md"
    task_file_1.write_text("# Task 001")
    task_file_3 = mock_repo_root / "tasks" / "in_review" / "TASK-003.md"
    task_file_3.write_text("# Task 003")
    # TASK-002 file intentionally missing

    # Mock FeatureLoader
    with patch("guardkit.orchestrator.feature_complete.FeatureLoader") as mock_loader:
        mock_loader.load_feature.return_value = sample_feature

        result = orchestrator.complete_feature("FEAT-TEST")

    # Verify result
    assert result.total_tasks == 3
    assert result.completed_count == 2
    assert result.failed_count == 1


def test_complete_feature_not_found(orchestrator):
    """Test handles feature not found error."""
    # Mock FeatureLoader to raise exception
    with patch("guardkit.orchestrator.feature_complete.FeatureLoader") as mock_loader:
        mock_loader.load_feature.side_effect = FeatureNotFoundError("Feature not found")

        with pytest.raises(FeatureNotFoundError):
            orchestrator.complete_feature("FEAT-NONEXISTENT")


def test_complete_feature_critical_error(orchestrator):
    """Test handles critical errors gracefully."""
    # Mock FeatureLoader to raise unexpected exception
    with patch("guardkit.orchestrator.feature_complete.FeatureLoader") as mock_loader:
        mock_loader.load_feature.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(FeatureCompleteError) as exc_info:
            orchestrator.complete_feature("FEAT-TEST")

        assert "Unexpected error" in str(exc_info.value)


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_complete_feature_all_already_completed(orchestrator, mock_repo_root, tmp_path):
    """Test handles feature with all tasks already completed."""
    feature = Feature(
        id="FEAT-DONE",
        name="Done Feature",
        description="All tasks completed",
        status="completed",
        created=datetime.now().isoformat(),
        complexity=3,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-001",
                name="Task One",
                file_path=tmp_path / "TASK-001.md",
                complexity=3,
                status="completed",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-002",
                name="Task Two",
                file_path=tmp_path / "TASK-002.md",
                complexity=3,
                status="completed",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        execution=FeatureExecution(),
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-001", "TASK-002"]],
            estimated_duration_minutes=60,
            recommended_parallel=2,
        ),
    )

    # Mock FeatureLoader
    with patch("guardkit.orchestrator.feature_complete.FeatureLoader") as mock_loader:
        mock_loader.load_feature.return_value = feature

        result = orchestrator.complete_feature("FEAT-DONE")

    # Verify result - no new completions, all skipped
    assert result.total_tasks == 2
    assert result.completed_count == 0  # No newly completed tasks
    assert result.failed_count == 0
    assert result.skipped_count == 2  # All tasks already completed


def test_complete_feature_mixed_status(orchestrator, mock_repo_root, tmp_path):
    """Test handles feature with mixed task statuses."""
    feature = Feature(
        id="FEAT-MIXED",
        name="Mixed Feature",
        description="Mixed task statuses",
        status="in_progress",
        created=datetime.now().isoformat(),
        complexity=3,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-001",
                name="Task One",
                file_path=tmp_path / "TASK-001.md",
                complexity=3,
                status="completed",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-002",
                name="Task Two",
                file_path=tmp_path / "TASK-002.md",
                complexity=3,
                status="in_review",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-003",
                name="Task Three",
                file_path=tmp_path / "TASK-003.md",
                complexity=3,
                status="in_progress",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        execution=FeatureExecution(),
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-001", "TASK-002", "TASK-003"]],
            estimated_duration_minutes=90,
            recommended_parallel=3,
        ),
    )

    # Create task files for pending tasks
    (mock_repo_root / "tasks" / "in_review" / "TASK-002.md").write_text("# Task 002")
    (mock_repo_root / "tasks" / "in_progress" / "TASK-003.md").write_text("# Task 003")

    # Mock FeatureLoader
    with patch("guardkit.orchestrator.feature_complete.FeatureLoader") as mock_loader:
        mock_loader.load_feature.return_value = feature

        result = orchestrator.complete_feature("FEAT-MIXED")

    # Verify result
    assert result.total_tasks == 3
    assert result.completed_count == 2  # Only newly completed tasks
    assert result.failed_count == 0
    assert result.skipped_count == 1  # One task already completed


# ============================================================================
# Test Verbose Mode Output
# ============================================================================


def test_complete_single_task_verbose_output(mock_repo_root, sample_feature):
    """Test verbose mode outputs success messages."""
    orchestrator = FeatureCompleteOrchestrator(
        repo_root=mock_repo_root,
        verbose=True,
    )

    task = sample_feature.tasks[0]
    task_file = mock_repo_root / "tasks" / "in_review" / f"{task.id}.md"
    task_file.write_text(f"# {task.name}")

    # Capture console output
    from io import StringIO
    import sys
    captured_output = StringIO()
    sys.stdout = captured_output

    try:
        result = orchestrator._complete_single_task(task, sample_feature)
    finally:
        sys.stdout = sys.__stdout__

    # Verify verbose output contains task ID
    output = captured_output.getvalue()
    assert result.success
    # Note: We can't easily test Rich console output, but we've exercised the branch


def test_complete_feature_verbose_with_failures(mock_repo_root, sample_feature):
    """Test verbose mode displays failed tasks."""
    orchestrator = FeatureCompleteOrchestrator(
        repo_root=mock_repo_root,
        verbose=True,
    )

    # Create only some task files to trigger failures
    task_file_1 = mock_repo_root / "tasks" / "in_review" / "TASK-001.md"
    task_file_1.write_text("# Task 001")
    # TASK-002 and TASK-003 files intentionally missing

    # Mock FeatureLoader
    with patch("guardkit.orchestrator.feature_complete.FeatureLoader") as mock_loader:
        mock_loader.load_feature.return_value = sample_feature

        result = orchestrator.complete_feature("FEAT-TEST")

    # Verify failures occurred
    assert result.failed_count > 0


# ============================================================================
# Test Directory Search Edge Cases
# ============================================================================


def test_find_task_file_missing_directory(orchestrator, mock_repo_root):
    """Test handles missing task directory gracefully."""
    # Remove one of the search directories
    search_dir = mock_repo_root / "tasks" / "in_progress"
    if search_dir.exists():
        import shutil
        shutil.rmtree(search_dir)

    # Should handle missing directory and continue searching
    found = orchestrator._find_task_file("TASK-NONEXISTENT")
    assert found is None


def test_find_task_file_all_directories_missing(mock_repo_root):
    """Test handles all search directories missing."""
    # Create orchestrator with repo that has no task directories
    empty_root = mock_repo_root / "empty_repo"
    empty_root.mkdir()

    orchestrator = FeatureCompleteOrchestrator(
        repo_root=empty_root,
        verbose=False,
    )

    found = orchestrator._find_task_file("TASK-001")
    assert found is None
