"""
Comprehensive Test Suite for FeatureCompleteOrchestrator Parallel Task Completion.

This module tests the parallel task completion logic implementation for TASK-FC-002,
including async execution, error isolation, file organization, and edge cases.

Coverage Target: >=80% line, >=75% branch
Test Count: 25+ tests
Stack: Python (pytest, pytest-asyncio)
"""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Future imports - these will be available when TASK-FC-002 is implemented
try:
    from guardkit.orchestrator.feature_complete import (
        FeatureCompleteOrchestrator,
        FeatureCompleteResult,
        TaskCompleteResult,
        FeatureCompleteError,
    )
except ImportError:
    # Temporary stubs for development
    class TaskCompleteResult:
        def __init__(self, task_id, success, error=None):
            self.task_id = task_id
            self.success = success
            self.error = error

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureNotFoundError,
    FeatureOrchestration,
    FeatureTask,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repo_root(tmp_path):
    """Create mock repository structure with all required directories."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create task state directories
    for state_dir in ["backlog", "in_progress", "in_review", "blocked"]:
        (repo_root / "tasks" / state_dir).mkdir(parents=True)

    # Create completed directory with date structure
    date_str = datetime.now().strftime("%Y-%m-%d")
    (repo_root / "tasks" / "completed" / date_str).mkdir(parents=True)

    # Create features directory
    (repo_root / ".guardkit" / "features").mkdir(parents=True)

    return repo_root


@pytest.fixture
def sample_feature(tmp_path):
    """Create sample feature with three tasks in different states."""
    return Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test feature for parallel completion",
        status="in_progress",
        created=datetime.now().isoformat(),
        complexity=5,
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
def mixed_status_feature(tmp_path):
    """Create feature with mixed task statuses (completed + pending)."""
    return Feature(
        id="FEAT-MIXED",
        name="Mixed Status Feature",
        description="Feature with mixed task statuses",
        status="in_progress",
        created=datetime.now().isoformat(),
        complexity=5,
        estimated_tasks=4,
        tasks=[
            FeatureTask(
                id="TASK-101",
                name="Already Completed",
                file_path=tmp_path / "TASK-101.md",
                complexity=3,
                status="completed",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-102",
                name="In Review",
                file_path=tmp_path / "TASK-102.md",
                complexity=3,
                status="in_review",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-103",
                name="In Progress",
                file_path=tmp_path / "TASK-103.md",
                complexity=3,
                status="in_progress",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-104",
                name="Blocked",
                file_path=tmp_path / "TASK-104.md",
                complexity=3,
                status="blocked",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        execution=FeatureExecution(),
        orchestration=FeatureOrchestration(
            parallel_groups=[
                ["TASK-101", "TASK-102"],
                ["TASK-103", "TASK-104"],
            ],
            estimated_duration_minutes=120,
            recommended_parallel=2,
        ),
    )


@pytest.fixture
def orchestrator(mock_repo_root):
    """Create orchestrator instance for testing."""
    return FeatureCompleteOrchestrator(
        repo_root=mock_repo_root,
        verbose=False,
    )


# ============================================================================
# Test Helper Functions
# ============================================================================


def create_task_file(repo_root: Path, task_id: str, status: str = "in_review") -> Path:
    """Create a mock task file in appropriate directory."""
    task_file = repo_root / "tasks" / status / f"{task_id}.md"
    task_file.write_text(f"# {task_id}\n\nTask content\n")
    return task_file


# ============================================================================
# Test Parallel Execution - Core Functionality
# ============================================================================


@pytest.mark.asyncio
async def test_complete_tasks_parallel_success(orchestrator, sample_feature, mock_repo_root):
    """Test successful parallel completion of all tasks."""
    # Create task files
    for task in sample_feature.tasks:
        create_task_file(mock_repo_root, task.id, "in_review")

    # Skip if method not implemented yet
    if not hasattr(orchestrator, "_complete_tasks_parallel"):
        pytest.skip("_complete_tasks_parallel not implemented yet (TASK-FC-002)")

    # Mock _complete_single_task to return success
    with patch.object(
        orchestrator,
        "_complete_single_task",
        return_value=TaskCompleteResult(task_id="TASK-001", success=True, error=None),
    ):
        results = await orchestrator._complete_tasks_parallel(sample_feature)

    # Verify all tasks completed successfully
    assert len(results) == 3
    assert all(r.success for r in results), "All tasks should complete successfully"
    assert all(r.error is None for r in results), "No tasks should have errors"


@pytest.mark.asyncio
async def test_complete_tasks_parallel_with_failures(orchestrator, sample_feature):
    """Test parallel completion handles individual task failures gracefully."""
    if not hasattr(orchestrator, "_complete_tasks_parallel"):
        pytest.skip("_complete_tasks_parallel not implemented yet (TASK-FC-002)")

    # Mock _complete_single_task to simulate one failure
    def mock_complete(task, feature):
        if task.id == "TASK-002":
            return TaskCompleteResult(
                task_id=task.id,
                success=False,
                error="Task file not found",
            )
        return TaskCompleteResult(task_id=task.id, success=True, error=None)

    with patch.object(orchestrator, "_complete_single_task", side_effect=mock_complete):
        results = await orchestrator._complete_tasks_parallel(sample_feature)

    # Verify results
    assert len(results) == 3
    success_count = sum(1 for r in results if r.success)
    failed_count = sum(1 for r in results if not r.success)

    assert success_count == 2, "Two tasks should succeed"
    assert failed_count == 1, "One task should fail"

    # Verify failed task has error message
    failed_result = next(r for r in results if not r.success)
    assert failed_result.task_id == "TASK-002"
    assert "not found" in failed_result.error.lower()


@pytest.mark.asyncio
async def test_complete_tasks_parallel_exception_handling(orchestrator, sample_feature):
    """Test parallel completion catches exceptions and converts to results."""
    if not hasattr(orchestrator, "_complete_tasks_parallel"):
        pytest.skip("_complete_tasks_parallel not implemented yet (TASK-FC-002)")

    # Mock _complete_single_task to raise exception
    def mock_complete(task, feature):
        if task.id == "TASK-002":
            raise RuntimeError("Unexpected database error")
        return TaskCompleteResult(task_id=task.id, success=True, error=None)

    with patch.object(orchestrator, "_complete_single_task", side_effect=mock_complete):
        results = await orchestrator._complete_tasks_parallel(sample_feature)

    # Verify exception was caught and converted to failed result
    assert len(results) == 3
    failed_result = next((r for r in results if r.task_id == "TASK-002"), None)
    assert failed_result is not None, "Failed task should have a result"
    assert not failed_result.success, "Task with exception should be marked as failed"
    assert "error" in failed_result.error.lower() or "unexpected" in failed_result.error.lower()


@pytest.mark.asyncio
async def test_complete_tasks_parallel_truly_parallel(orchestrator, sample_feature, monkeypatch):
    """Test tasks execute in parallel, not sequentially."""
    if not hasattr(orchestrator, "_complete_tasks_parallel"):
        pytest.skip("_complete_tasks_parallel not implemented yet (TASK-FC-002)")

    execution_order = []
    execution_lock = asyncio.Lock()

    async def mock_complete_with_delay(task, feature):
        """Simulate task with varying completion time."""
        await asyncio.sleep(0.01 * int(task.id.split("-")[1]))  # Varying delays
        async with execution_lock:
            execution_order.append(task.id)
        return TaskCompleteResult(task_id=task.id, success=True, error=None)

    # Use asyncio.to_thread wrapper for compatibility
    async def wrapped_complete(task, feature):
        return await mock_complete_with_delay(task, feature)

    with patch.object(orchestrator, "_complete_single_task", side_effect=wrapped_complete):
        start_time = asyncio.get_event_loop().time()
        await orchestrator._complete_tasks_parallel(sample_feature)
        elapsed_time = asyncio.get_event_loop().time() - start_time

    # If truly parallel, should complete in ~0.03s (longest task)
    # If sequential, would take 0.01 + 0.02 + 0.03 = 0.06s
    assert elapsed_time < 0.05, "Tasks should execute in parallel, not sequentially"


# ============================================================================
# Test Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_complete_tasks_already_completed(orchestrator, mixed_status_feature):
    """Test skips tasks that are already completed."""
    if not hasattr(orchestrator, "_complete_tasks_parallel"):
        pytest.skip("_complete_tasks_parallel not implemented yet (TASK-FC-002)")

    results = await orchestrator._complete_tasks_parallel(mixed_status_feature)

    # Should only process non-completed tasks (3 out of 4)
    assert len(results) <= 3, "Should skip already completed task"

    # Verify completed task was not processed
    task_ids = [r.task_id for r in results]
    assert "TASK-101" not in task_ids, "Already completed task should be skipped"


@pytest.mark.asyncio
async def test_complete_tasks_empty_feature(orchestrator):
    """Test handles empty feature gracefully."""
    if not hasattr(orchestrator, "_complete_tasks_parallel"):
        pytest.skip("_complete_tasks_parallel not implemented yet (TASK-FC-002)")

    empty_feature = Feature(
        id="FEAT-EMPTY",
        name="Empty Feature",
        description="No tasks",
        status="in_progress",
        created=datetime.now().isoformat(),
        complexity=1,
        estimated_tasks=0,
        tasks=[],
        execution=FeatureExecution(),
        orchestration=FeatureOrchestration(
            parallel_groups=[],
            estimated_duration_minutes=0,
            recommended_parallel=0,
        ),
    )

    results = await orchestrator._complete_tasks_parallel(empty_feature)

    assert len(results) == 0, "Empty feature should return empty results"


@pytest.mark.asyncio
async def test_complete_tasks_all_completed(orchestrator, tmp_path):
    """Test handles feature where all tasks are already completed."""
    if not hasattr(orchestrator, "_complete_tasks_parallel"):
        pytest.skip("_complete_tasks_parallel not implemented yet (TASK-FC-002)")

    all_completed_feature = Feature(
        id="FEAT-DONE",
        name="All Completed Feature",
        description="All tasks completed",
        status="completed",
        created=datetime.now().isoformat(),
        complexity=3,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-201",
                name="Completed Task 1",
                file_path=tmp_path / "TASK-201.md",
                complexity=3,
                status="completed",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-202",
                name="Completed Task 2",
                file_path=tmp_path / "TASK-202.md",
                complexity=3,
                status="completed",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        execution=FeatureExecution(),
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-201", "TASK-202"]],
            estimated_duration_minutes=60,
            recommended_parallel=2,
        ),
    )

    results = await orchestrator._complete_tasks_parallel(all_completed_feature)

    # Should return empty or skip all
    assert len(results) == 0 or all(
        r.success for r in results
    ), "All completed tasks should be skipped or succeed"


# ============================================================================
# Test Single Task Completion
# ============================================================================


def test_complete_single_task_success(orchestrator, sample_feature, mock_repo_root):
    """Test successful single task completion with file movement."""
    if not hasattr(orchestrator, "_complete_single_task"):
        pytest.skip("_complete_single_task not implemented yet (TASK-FC-002)")

    task = sample_feature.tasks[0]
    task_file = create_task_file(mock_repo_root, task.id, "in_review")

    result = orchestrator._complete_single_task(task, sample_feature)

    # Verify result
    assert result.success, "Task completion should succeed"
    assert result.error is None, "No error should be present"
    assert result.task_id == task.id

    # Verify file moved to correct location
    date_str = datetime.now().strftime("%Y-%m-%d")
    feature_slug = "feat-test"
    target_file = (
        mock_repo_root
        / "tasks"
        / "completed"
        / date_str
        / feature_slug
        / f"{task.id}.md"
    )

    assert target_file.exists(), f"Task file should be moved to {target_file}"
    assert not task_file.exists(), "Original task file should be removed"


def test_complete_single_task_file_not_found(orchestrator, sample_feature):
    """Test handles missing task file gracefully."""
    if not hasattr(orchestrator, "_complete_single_task"):
        pytest.skip("_complete_single_task not implemented yet (TASK-FC-002)")

    task = sample_feature.tasks[0]

    result = orchestrator._complete_single_task(task, sample_feature)

    # Should return failure result
    assert not result.success, "Task completion should fail for missing file"
    assert result.error is not None, "Error message should be present"
    assert "not found" in result.error.lower()


def test_complete_single_task_move_error(orchestrator, sample_feature, mock_repo_root):
    """Test handles file move errors gracefully."""
    if not hasattr(orchestrator, "_complete_single_task"):
        pytest.skip("_complete_single_task not implemented yet (TASK-FC-002)")

    task = sample_feature.tasks[0]
    create_task_file(mock_repo_root, task.id, "in_review")

    # Mock shutil.move to raise exception
    with patch("shutil.move", side_effect=PermissionError("Permission denied")):
        result = orchestrator._complete_single_task(task, sample_feature)

    # Should return failure result
    assert not result.success, "Task completion should fail on move error"
    assert "permission" in result.error.lower() or "denied" in result.error.lower()


# ============================================================================
# Test Feature Slug Extraction
# ============================================================================


def test_extract_feature_slug_simple(orchestrator):
    """Test extracts slug from simple feature ID."""
    if not hasattr(orchestrator, "_extract_feature_slug"):
        pytest.skip("_extract_feature_slug not implemented yet (TASK-FC-002)")

    slug = orchestrator._extract_feature_slug("FEAT-A1B2")
    assert slug == "feat-a1b2", "Should convert to lowercase kebab-case"


def test_extract_feature_slug_with_prefix(orchestrator):
    """Test extracts slug from feature ID with prefix."""
    if not hasattr(orchestrator, "_extract_feature_slug"):
        pytest.skip("_extract_feature_slug not implemented yet (TASK-FC-002)")

    slug = orchestrator._extract_feature_slug("FEAT-AUTH-001")
    assert slug == "feat-auth-001", "Should preserve prefix in lowercase"


def test_extract_feature_slug_already_lowercase(orchestrator):
    """Test handles already lowercase feature IDs."""
    if not hasattr(orchestrator, "_extract_feature_slug"):
        pytest.skip("_extract_feature_slug not implemented yet (TASK-FC-002)")

    slug = orchestrator._extract_feature_slug("feat-test")
    assert slug == "feat-test", "Should handle lowercase input"


# ============================================================================
# Test Task File Discovery
# ============================================================================


def test_find_task_file_in_review(orchestrator, mock_repo_root):
    """Test finds task file in in_review directory."""
    if not hasattr(orchestrator, "_find_task_file"):
        pytest.skip("_find_task_file not implemented yet (TASK-FC-002)")

    task_file = create_task_file(mock_repo_root, "TASK-001", "in_review")

    found = orchestrator._find_task_file("TASK-001")

    assert found == task_file, "Should find task in in_review directory"


def test_find_task_file_in_progress(orchestrator, mock_repo_root):
    """Test finds task file in in_progress directory."""
    if not hasattr(orchestrator, "_find_task_file"):
        pytest.skip("_find_task_file not implemented yet (TASK-FC-002)")

    task_file = create_task_file(mock_repo_root, "TASK-002", "in_progress")

    found = orchestrator._find_task_file("TASK-002")

    assert found == task_file, "Should find task in in_progress directory"


def test_find_task_file_in_backlog(orchestrator, mock_repo_root):
    """Test finds task file in backlog directory."""
    if not hasattr(orchestrator, "_find_task_file"):
        pytest.skip("_find_task_file not implemented yet (TASK-FC-002)")

    task_file = create_task_file(mock_repo_root, "TASK-003", "backlog")

    found = orchestrator._find_task_file("TASK-003")

    assert found == task_file, "Should find task in backlog directory"


def test_find_task_file_in_subdirectory(orchestrator, mock_repo_root):
    """Test finds task file in feature subdirectory."""
    if not hasattr(orchestrator, "_find_task_file"):
        pytest.skip("_find_task_file not implemented yet (TASK-FC-002)")

    # Create feature subdirectory
    feature_dir = mock_repo_root / "tasks" / "backlog" / "feature-auth"
    feature_dir.mkdir(parents=True)
    task_file = feature_dir / "TASK-AUTH-001.md"
    task_file.write_text("# Auth Task")

    found = orchestrator._find_task_file("TASK-AUTH-001")

    assert found == task_file, "Should find task in feature subdirectory"


def test_find_task_file_not_found(orchestrator):
    """Test returns None when task file not found."""
    if not hasattr(orchestrator, "_find_task_file"):
        pytest.skip("_find_task_file not implemented yet (TASK-FC-002)")

    found = orchestrator._find_task_file("TASK-NONEXISTENT")

    assert found is None, "Should return None for non-existent task"


# ============================================================================
# Test Integration with Complete Workflow
# ============================================================================


def test_completion_phase_calls_parallel_completion(orchestrator, sample_feature):
    """Test _completion_phase integrates with _complete_tasks_parallel."""
    if not hasattr(orchestrator, "_completion_phase"):
        pytest.skip("_completion_phase not implemented yet (TASK-FC-002)")

    # Mock _complete_tasks_parallel
    with patch.object(
        orchestrator,
        "_complete_tasks_parallel",
        new_callable=AsyncMock,
        return_value=[
            TaskCompleteResult(task_id="TASK-001", success=True, error=None),
            TaskCompleteResult(task_id="TASK-002", success=True, error=None),
            TaskCompleteResult(task_id="TASK-003", success=True, error=None),
        ],
    ) as mock_parallel:
        orchestrator._completion_phase(sample_feature)

        # Verify parallel completion was called
        mock_parallel.assert_called_once_with(sample_feature)


def test_completion_phase_handles_partial_failure(orchestrator, sample_feature):
    """Test _completion_phase handles partial failures correctly."""
    if not hasattr(orchestrator, "_completion_phase"):
        pytest.skip("_completion_phase not implemented yet (TASK-FC-002)")

    # Mock _complete_tasks_parallel with mixed results
    with patch.object(
        orchestrator,
        "_complete_tasks_parallel",
        new_callable=AsyncMock,
        return_value=[
            TaskCompleteResult(task_id="TASK-001", success=True, error=None),
            TaskCompleteResult(
                task_id="TASK-002", success=False, error="File not found"
            ),
            TaskCompleteResult(task_id="TASK-003", success=True, error=None),
        ],
    ):
        # Should not raise exception - handles failures gracefully
        orchestrator._completion_phase(sample_feature)


# ============================================================================
# Test Performance
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_completion_performance(orchestrator, mock_repo_root):
    """Test parallel completion is significantly faster than sequential."""
    if not hasattr(orchestrator, "_complete_tasks_parallel"):
        pytest.skip("_complete_tasks_parallel not implemented yet (TASK-FC-002)")

    # Create feature with many tasks
    large_feature = Feature(
        id="FEAT-PERF",
        name="Performance Test Feature",
        description="Feature with many tasks",
        status="in_progress",
        created=datetime.now().isoformat(),
        complexity=8,
        estimated_tasks=10,
        tasks=[
            FeatureTask(
                id=f"TASK-{i:03d}",
                name=f"Task {i}",
                file_path=mock_repo_root / f"TASK-{i:03d}.md",
                complexity=3,
                status="in_review",
                dependencies=[],
                implementation_mode="task-work",
                estimated_minutes=30,
            )
            for i in range(10)
        ],
        execution=FeatureExecution(),
        orchestration=FeatureOrchestration(
            parallel_groups=[[f"TASK-{i:03d}" for i in range(10)]],
            estimated_duration_minutes=300,
            recommended_parallel=10,
        ),
    )

    # Mock with small delay to simulate work
    async def mock_complete_with_delay(task, feature):
        await asyncio.sleep(0.01)
        return TaskCompleteResult(task_id=task.id, success=True, error=None)

    with patch.object(
        orchestrator, "_complete_single_task", side_effect=mock_complete_with_delay
    ):
        start_time = asyncio.get_event_loop().time()
        await orchestrator._complete_tasks_parallel(large_feature)
        elapsed_time = asyncio.get_event_loop().time() - start_time

    # Parallel: ~0.01s (all tasks at once)
    # Sequential: ~0.10s (10 tasks × 0.01s each)
    assert (
        elapsed_time < 0.05
    ), f"Parallel execution took {elapsed_time}s, should be < 0.05s"


# ============================================================================
# Test Integration (Setup → Complete → Finalize)
# ============================================================================


def test_complete_feature_integration(orchestrator, sample_feature, mock_repo_root, tmp_path):
    """Test complete_feature integration flow."""
    # Setup feature YAML file
    feature_yaml = mock_repo_root / ".guardkit" / "features" / "FEAT-TEST.yaml"
    feature_yaml.parent.mkdir(parents=True, exist_ok=True)

    # Create minimal YAML content
    yaml_content = f"""id: {sample_feature.id}
name: {sample_feature.name}
description: {sample_feature.description}
status: {sample_feature.status}
created: {sample_feature.created}
complexity: {sample_feature.complexity}
estimated_tasks: {sample_feature.estimated_tasks}
tasks:
  - id: TASK-001
    name: Task One
    file_path: tasks/in_review/TASK-001.md
    complexity: 3
    status: in_review
    dependencies: []
    implementation_mode: task-work
    estimated_minutes: 30
  - id: TASK-002
    name: Task Two
    file_path: tasks/in_review/TASK-002.md
    complexity: 3
    status: in_review
    dependencies: []
    implementation_mode: task-work
    estimated_minutes: 30
  - id: TASK-003
    name: Task Three
    file_path: tasks/in_review/TASK-003.md
    complexity: 3
    status: in_review
    dependencies: []
    implementation_mode: task-work
    estimated_minutes: 30
"""
    feature_yaml.write_text(yaml_content)

    # Create mock task files
    for i in range(1, 4):
        task_dir = mock_repo_root / "tasks" / "in_review"
        task_dir.mkdir(parents=True, exist_ok=True)
        task_file = task_dir / f"TASK-00{i}.md"
        task_file.write_text(f"# TASK-00{i}\n\nTask content")

    # Execute complete_feature
    result = orchestrator.complete_feature(sample_feature.id)

    # Verify result
    assert result.feature_id == sample_feature.id
    assert result.total_tasks == 3
    assert result.completed_count == 3
    assert result.failed_count == 0
    assert result.skipped_count == 0


def test_complete_feature_with_partial_failure(orchestrator, sample_feature, mock_repo_root):
    """Test complete_feature handles partial failures."""
    # Setup feature YAML
    feature_yaml = mock_repo_root / ".guardkit" / "features" / f"{sample_feature.id}.yaml"
    feature_yaml.parent.mkdir(parents=True, exist_ok=True)

    yaml_content = f"""id: {sample_feature.id}
name: {sample_feature.name}
description: {sample_feature.description}
status: {sample_feature.status}
created: {sample_feature.created}
complexity: {sample_feature.complexity}
estimated_tasks: {sample_feature.estimated_tasks}
tasks:
  - id: TASK-001
    name: Task One
    file_path: tasks/in_review/TASK-001.md
    complexity: 3
    status: in_review
    dependencies: []
    implementation_mode: task-work
    estimated_minutes: 30
  - id: TASK-002
    name: Task Two
    file_path: tasks/in_review/TASK-002.md
    complexity: 3
    status: in_review
    dependencies: []
    implementation_mode: task-work
    estimated_minutes: 30
"""
    feature_yaml.write_text(yaml_content)

    # Create only one task file (TASK-001), TASK-002 will fail
    task_dir = mock_repo_root / "tasks" / "in_review"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "TASK-001.md").write_text("# TASK-001\n\nContent")

    # Execute
    result = orchestrator.complete_feature(sample_feature.id)

    # Verify partial completion
    assert result.completed_count == 1  # TASK-001 succeeded
    assert result.failed_count == 1  # TASK-002 failed (file not found)
