"""
Unit tests for FeatureLoader - Feature YAML loading and validation.

This module provides comprehensive unit tests for the FeatureLoader class,
covering YAML parsing, validation, and serialization.

Test Coverage:
- Feature YAML loading (success, not found, parse errors)
- Task parsing and validation
- Circular dependency detection
- Feature saving and serialization
- Edge cases (empty features, missing fields)
"""

import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import tempfile
import yaml

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureOrchestration,
    FeatureExecution,
    FeatureLoader,
    FeatureNotFoundError,
    FeatureParseError,
    FeatureValidationError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_feature_yaml() -> Dict[str, Any]:
    """Provide sample feature YAML data."""
    return {
        "id": "FEAT-A1B2",
        "name": "User Authentication",
        "description": "Implement user authentication with OAuth2",
        "created": "2025-12-31T12:00:00Z",
        "status": "planned",
        "complexity": 7,
        "estimated_tasks": 3,
        "tasks": [
            {
                "id": "TASK-AUTH-001",
                "name": "Create login form",
                "file_path": "tasks/backlog/TASK-AUTH-001.md",
                "complexity": 3,
                "dependencies": [],
                "status": "pending",
                "implementation_mode": "task-work",
                "estimated_minutes": 30,
            },
            {
                "id": "TASK-AUTH-002",
                "name": "Implement OAuth2 flow",
                "file_path": "tasks/backlog/TASK-AUTH-002.md",
                "complexity": 6,
                "dependencies": ["TASK-AUTH-001"],
                "status": "pending",
                "implementation_mode": "task-work",
                "estimated_minutes": 60,
            },
            {
                "id": "TASK-AUTH-003",
                "name": "Add token refresh",
                "file_path": "tasks/backlog/TASK-AUTH-003.md",
                "complexity": 4,
                "dependencies": ["TASK-AUTH-002"],
                "status": "pending",
                "implementation_mode": "direct",
                "estimated_minutes": 45,
            },
        ],
        "orchestration": {
            "parallel_groups": [
                ["TASK-AUTH-001"],
                ["TASK-AUTH-002"],
                ["TASK-AUTH-003"],
            ],
            "estimated_duration_minutes": 135,
            "recommended_parallel": 1,
        },
        "execution": {
            "started_at": None,
            "completed_at": None,
            "worktree_path": None,
            "total_turns": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
        },
    }


@pytest.fixture
def temp_features_dir(sample_feature_yaml) -> Path:
    """Create a temporary features directory with sample YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        features_dir = Path(tmpdir) / ".guardkit" / "features"
        features_dir.mkdir(parents=True)

        # Create sample feature file
        feature_file = features_dir / "FEAT-A1B2.yaml"
        with open(feature_file, "w") as f:
            yaml.dump(sample_feature_yaml, f)

        yield Path(tmpdir)


@pytest.fixture
def temp_repo_with_tasks(temp_features_dir, sample_feature_yaml) -> Path:
    """Create temp repo with both feature YAML and task files."""
    # Create task markdown files
    for task in sample_feature_yaml["tasks"]:
        task_file = temp_features_dir / task["file_path"]
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(f"# {task['name']}\n\nTask content here.")

    return temp_features_dir


# ============================================================================
# Test: Feature Loading
# ============================================================================


def test_load_feature_success(temp_features_dir, sample_feature_yaml):
    """Test successful feature loading from YAML."""
    feature = FeatureLoader.load_feature(
        "FEAT-A1B2",
        repo_root=temp_features_dir,
    )

    assert feature.id == "FEAT-A1B2"
    assert feature.name == "User Authentication"
    assert feature.status == "planned"
    assert feature.complexity == 7
    assert len(feature.tasks) == 3


def test_load_feature_not_found(temp_features_dir):
    """Test FeatureNotFoundError when file doesn't exist."""
    with pytest.raises(FeatureNotFoundError) as exc_info:
        FeatureLoader.load_feature("FEAT-NONEXISTENT", repo_root=temp_features_dir)

    assert "Feature file not found" in str(exc_info.value)
    assert "FEAT-NONEXISTENT" in str(exc_info.value)


def test_load_feature_yaml_extension(temp_features_dir, sample_feature_yaml):
    """Test loading feature with .yml extension."""
    features_dir = temp_features_dir / ".guardkit" / "features"

    # Create file with .yml extension
    feature_file = features_dir / "FEAT-YML.yml"
    with open(feature_file, "w") as f:
        yaml.dump({**sample_feature_yaml, "id": "FEAT-YML"}, f)

    feature = FeatureLoader.load_feature("FEAT-YML", repo_root=temp_features_dir)
    assert feature.id == "FEAT-YML"


def test_load_feature_parse_error(temp_features_dir):
    """Test FeatureParseError for invalid YAML."""
    features_dir = temp_features_dir / ".guardkit" / "features"
    invalid_file = features_dir / "FEAT-INVALID.yaml"

    # Write invalid YAML
    invalid_file.write_text("invalid: yaml: content:\n  broken")

    with pytest.raises(FeatureParseError) as exc_info:
        FeatureLoader.load_feature("FEAT-INVALID", repo_root=temp_features_dir)

    assert "Failed to parse feature YAML" in str(exc_info.value)


def test_load_feature_missing_required_field(temp_features_dir):
    """Test FeatureParseError for missing required fields."""
    features_dir = temp_features_dir / ".guardkit" / "features"
    incomplete_file = features_dir / "FEAT-INCOMPLETE.yaml"

    # Write YAML missing required 'id' field
    incomplete_file.write_text(yaml.dump({"name": "Missing ID feature"}))

    with pytest.raises(FeatureParseError) as exc_info:
        FeatureLoader.load_feature("FEAT-INCOMPLETE", repo_root=temp_features_dir)

    assert "Invalid feature structure" in str(exc_info.value)


# ============================================================================
# Test: Task Parsing
# ============================================================================


def test_parse_task_complete(sample_feature_yaml):
    """Test parsing a complete task definition."""
    task_data = sample_feature_yaml["tasks"][0]
    task = FeatureLoader._parse_task(task_data)

    assert task.id == "TASK-AUTH-001"
    assert task.name == "Create login form"
    assert task.file_path == Path("tasks/backlog/TASK-AUTH-001.md")
    assert task.complexity == 3
    assert task.dependencies == []
    assert task.status == "pending"
    assert task.implementation_mode == "task-work"
    assert task.estimated_minutes == 30


def test_parse_task_with_dependencies(sample_feature_yaml):
    """Test parsing task with dependencies."""
    task_data = sample_feature_yaml["tasks"][1]
    task = FeatureLoader._parse_task(task_data)

    assert task.id == "TASK-AUTH-002"
    assert task.dependencies == ["TASK-AUTH-001"]


def test_parse_task_defaults():
    """Test parsing task with defaults applied."""
    minimal_task = {
        "id": "TASK-MIN-001",
        "file_path": "tasks/TASK-MIN-001.md",
    }
    task = FeatureLoader._parse_task(minimal_task)

    assert task.id == "TASK-MIN-001"
    assert task.name == "TASK-MIN-001"  # Defaults to ID
    assert task.complexity == 5  # Default
    assert task.dependencies == []  # Default
    assert task.status == "pending"  # Default
    assert task.implementation_mode == "task-work"  # Default
    assert task.estimated_minutes == 30  # Default


# ============================================================================
# Test: Feature Validation
# ============================================================================


def test_validate_feature_success(temp_repo_with_tasks, sample_feature_yaml):
    """Test successful feature validation."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_repo_with_tasks)
    errors = FeatureLoader.validate_feature(feature, repo_root=temp_repo_with_tasks)

    assert errors == []


def test_validate_feature_no_tasks(temp_features_dir):
    """Test validation error for feature with no tasks."""
    features_dir = temp_features_dir / ".guardkit" / "features"
    empty_feature = features_dir / "FEAT-EMPTY.yaml"

    empty_feature.write_text(
        yaml.dump(
            {
                "id": "FEAT-EMPTY",
                "name": "Empty Feature",
                "tasks": [],
                "orchestration": {"parallel_groups": []},
            }
        )
    )

    feature = FeatureLoader.load_feature("FEAT-EMPTY", repo_root=temp_features_dir)
    errors = FeatureLoader.validate_feature(feature, repo_root=temp_features_dir)

    assert any("no tasks defined" in e.lower() for e in errors)


def test_validate_feature_missing_task_files(temp_features_dir):
    """Test validation error when task files don't exist."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_features_dir)
    errors = FeatureLoader.validate_feature(feature, repo_root=temp_features_dir)

    # All task files are missing
    assert len(errors) >= 3
    assert all("Task file not found" in e for e in errors)


def test_validate_feature_unknown_task_in_orchestration(temp_repo_with_tasks):
    """Test validation error for unknown task in orchestration."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_repo_with_tasks)

    # Add unknown task to orchestration
    feature.orchestration.parallel_groups.append(["TASK-UNKNOWN"])

    errors = FeatureLoader.validate_feature(feature, repo_root=temp_repo_with_tasks)
    assert any("Orchestration references unknown task: TASK-UNKNOWN" in e for e in errors)


def test_validate_feature_task_not_in_orchestration(temp_repo_with_tasks):
    """Test validation error when task missing from orchestration."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_repo_with_tasks)

    # Remove task from orchestration
    feature.orchestration.parallel_groups = [["TASK-AUTH-001"], ["TASK-AUTH-002"]]

    errors = FeatureLoader.validate_feature(feature, repo_root=temp_repo_with_tasks)
    assert any("Tasks not in orchestration" in e for e in errors)
    assert any("TASK-AUTH-003" in e for e in errors)


def test_validate_feature_unknown_dependency(temp_repo_with_tasks):
    """Test validation error for unknown dependency."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_repo_with_tasks)

    # Add unknown dependency
    feature.tasks[0].dependencies = ["TASK-NONEXISTENT"]

    errors = FeatureLoader.validate_feature(feature, repo_root=temp_repo_with_tasks)
    assert any("unknown dependency" in e.lower() for e in errors)


# ============================================================================
# Test: Circular Dependency Detection
# ============================================================================


def test_detect_circular_dependency_simple():
    """Test detection of simple A→B→A cycle."""
    feature = Feature(
        id="FEAT-CYCLE",
        name="Cycle Test",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-A",
                name="Task A",
                file_path=Path("tasks/a.md"),
                complexity=3,
                dependencies=["TASK-B"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-B",
                name="Task B",
                file_path=Path("tasks/b.md"),
                complexity=3,
                dependencies=["TASK-A"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-A", "TASK-B"]],
            estimated_duration_minutes=60,
            recommended_parallel=1,
        ),
    )

    cycle = FeatureLoader._detect_circular_dependencies(feature)
    assert cycle is not None
    assert "TASK-A" in cycle or "TASK-B" in cycle


def test_detect_circular_dependency_transitive():
    """Test detection of A→B→C→A transitive cycle."""
    feature = Feature(
        id="FEAT-TRANS",
        name="Transitive Cycle",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=5,
        estimated_tasks=3,
        tasks=[
            FeatureTask(
                id="TASK-A",
                name="Task A",
                file_path=Path("tasks/a.md"),
                complexity=3,
                dependencies=["TASK-C"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-B",
                name="Task B",
                file_path=Path("tasks/b.md"),
                complexity=3,
                dependencies=["TASK-A"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-C",
                name="Task C",
                file_path=Path("tasks/c.md"),
                complexity=3,
                dependencies=["TASK-B"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-A"], ["TASK-B"], ["TASK-C"]],
            estimated_duration_minutes=90,
            recommended_parallel=1,
        ),
    )

    cycle = FeatureLoader._detect_circular_dependencies(feature)
    assert cycle is not None


def test_no_circular_dependency(sample_feature_yaml):
    """Test that linear dependencies don't trigger cycle detection."""
    feature = FeatureLoader._parse_feature(sample_feature_yaml)
    cycle = FeatureLoader._detect_circular_dependencies(feature)
    assert cycle is None


# ============================================================================
# Test: Feature Saving
# ============================================================================


def test_save_feature_creates_file():
    """Test that save_feature creates YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        features_dir = repo_root / ".guardkit" / "features"

        feature = Feature(
            id="FEAT-NEW",
            name="New Feature",
            description="Test description",
            created="2025-12-31T12:00:00Z",
            status="planned",
            complexity=5,
            estimated_tasks=1,
            tasks=[
                FeatureTask(
                    id="TASK-NEW-001",
                    name="New Task",
                    file_path=Path("tasks/TASK-NEW-001.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                )
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-NEW-001"]],
                estimated_duration_minutes=30,
                recommended_parallel=1,
            ),
        )

        FeatureLoader.save_feature(feature, repo_root=repo_root)

        # Verify file created
        feature_file = features_dir / "FEAT-NEW.yaml"
        assert feature_file.exists()

        # Verify content
        with open(feature_file) as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["id"] == "FEAT-NEW"
        assert saved_data["name"] == "New Feature"


def test_save_feature_preserves_file_path():
    """Test that save_feature uses existing file_path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        features_dir = repo_root / ".guardkit" / "features"
        features_dir.mkdir(parents=True)

        # Create feature with explicit file_path
        feature_file = features_dir / "custom-name.yaml"
        feature = Feature(
            id="FEAT-CUSTOM",
            name="Custom",
            description="",
            created="2025-12-31",
            status="planned",
            complexity=5,
            estimated_tasks=0,
            tasks=[],
            orchestration=FeatureOrchestration(
                parallel_groups=[], estimated_duration_minutes=0, recommended_parallel=1
            ),
            file_path=feature_file,
        )

        FeatureLoader.save_feature(feature, repo_root=repo_root)

        assert feature_file.exists()
        assert not (features_dir / "FEAT-CUSTOM.yaml").exists()


def test_save_and_reload_feature():
    """Test save/reload roundtrip preserves data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        original = Feature(
            id="FEAT-ROUND",
            name="Roundtrip Test",
            description="Testing save/load",
            created="2025-12-31T12:00:00Z",
            status="in_progress",
            complexity=7,
            estimated_tasks=2,
            tasks=[
                FeatureTask(
                    id="TASK-RT-001",
                    name="Task 1",
                    file_path=Path("tasks/t1.md"),
                    complexity=4,
                    dependencies=[],
                    status="completed",
                    implementation_mode="direct",
                    estimated_minutes=20,
                    result={"success": True, "turns": 1},
                ),
                FeatureTask(
                    id="TASK-RT-002",
                    name="Task 2",
                    file_path=Path("tasks/t2.md"),
                    complexity=5,
                    dependencies=["TASK-RT-001"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=40,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-RT-001"], ["TASK-RT-002"]],
                estimated_duration_minutes=60,
                recommended_parallel=2,
            ),
            execution=FeatureExecution(
                started_at="2025-12-31T13:00:00Z",
                completed_at=None,
                worktree_path="/path/to/worktree",
                total_turns=1,
                tasks_completed=1,
                tasks_failed=0,
            ),
        )

        # Save
        FeatureLoader.save_feature(original, repo_root=repo_root)

        # Reload
        reloaded = FeatureLoader.load_feature("FEAT-ROUND", repo_root=repo_root)

        # Verify
        assert reloaded.id == original.id
        assert reloaded.name == original.name
        assert reloaded.status == original.status
        assert len(reloaded.tasks) == len(original.tasks)
        assert reloaded.tasks[0].status == "completed"
        assert reloaded.tasks[0].result == {"success": True, "turns": 1}
        assert reloaded.execution.started_at == original.execution.started_at
        assert reloaded.execution.tasks_completed == 1


# ============================================================================
# Test: Find Task
# ============================================================================


def test_find_task_exists(temp_features_dir):
    """Test finding existing task by ID."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_features_dir)

    task = FeatureLoader.find_task(feature, "TASK-AUTH-002")
    assert task is not None
    assert task.id == "TASK-AUTH-002"
    assert task.name == "Implement OAuth2 flow"


def test_find_task_not_found(temp_features_dir):
    """Test None returned for non-existent task."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_features_dir)

    task = FeatureLoader.find_task(feature, "TASK-NONEXISTENT")
    assert task is None


# ============================================================================
# Test: Data Model Edge Cases
# ============================================================================


def test_feature_task_status_literals():
    """Test FeatureTask accepts valid status literals."""
    for status in ["pending", "in_progress", "completed", "failed", "skipped"]:
        task = FeatureTask(
            id="TASK-TEST",
            name="Test",
            file_path=Path("t.md"),
            complexity=3,
            dependencies=[],
            status=status,
            implementation_mode="task-work",
            estimated_minutes=30,
        )
        assert task.status == status


def test_feature_status_literals():
    """Test Feature accepts valid status literals."""
    for status in ["planned", "in_progress", "completed", "failed", "paused"]:
        feature = Feature(
            id="FEAT-TEST",
            name="Test",
            description="",
            created="2025-12-31",
            status=status,
            complexity=5,
            estimated_tasks=0,
            tasks=[],
            orchestration=FeatureOrchestration(
                parallel_groups=[], estimated_duration_minutes=0, recommended_parallel=1
            ),
        )
        assert feature.status == status


def test_feature_execution_defaults():
    """Test FeatureExecution uses correct defaults."""
    execution = FeatureExecution()

    assert execution.started_at is None
    assert execution.completed_at is None
    assert execution.worktree_path is None
    assert execution.total_turns == 0
    assert execution.tasks_completed == 0
    assert execution.tasks_failed == 0
    assert execution.current_wave == 0
    assert execution.completed_waves == []
    assert execution.last_updated is None


# ============================================================================
# Test: Resume Support - is_incomplete
# ============================================================================


def test_is_incomplete_planned_feature():
    """Test planned feature is not incomplete."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("t1.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-2",
                name="Task 2",
                file_path=Path("t2.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-1", "TASK-2"]],
            estimated_duration_minutes=60,
            recommended_parallel=2,
        ),
    )

    assert FeatureLoader.is_incomplete(feature) is False


def test_is_incomplete_in_progress_feature():
    """Test in_progress feature is incomplete."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        description="",
        created="2025-12-31",
        status="in_progress",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("t1.md"),
                complexity=3,
                dependencies=[],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-2",
                name="Task 2",
                file_path=Path("t2.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-1", "TASK-2"]],
            estimated_duration_minutes=60,
            recommended_parallel=2,
        ),
    )

    assert FeatureLoader.is_incomplete(feature) is True


def test_is_incomplete_paused_feature():
    """Test paused feature is incomplete."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        description="",
        created="2025-12-31",
        status="paused",
        complexity=5,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("t1.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-1"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
    )

    assert FeatureLoader.is_incomplete(feature) is True


def test_is_incomplete_task_in_progress():
    """Test feature with in_progress task is incomplete."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=5,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("t1.md"),
                complexity=3,
                dependencies=[],
                status="in_progress",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-1"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
    )

    assert FeatureLoader.is_incomplete(feature) is True


def test_is_incomplete_partial_completion():
    """Test feature with partial task completion is incomplete."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("t1.md"),
                complexity=3,
                dependencies=[],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-2",
                name="Task 2",
                file_path=Path("t2.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-1", "TASK-2"]],
            estimated_duration_minutes=60,
            recommended_parallel=2,
        ),
        execution=FeatureExecution(started_at="2025-12-31T12:00:00Z"),
    )

    assert FeatureLoader.is_incomplete(feature) is True


def test_is_incomplete_all_completed():
    """Test feature with all tasks completed is not incomplete."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        description="",
        created="2025-12-31",
        status="completed",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("t1.md"),
                complexity=3,
                dependencies=[],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-2",
                name="Task 2",
                file_path=Path("t2.md"),
                complexity=3,
                dependencies=[],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-1", "TASK-2"]],
            estimated_duration_minutes=60,
            recommended_parallel=2,
        ),
        execution=FeatureExecution(
            started_at="2025-12-31T12:00:00Z",
            completed_at="2025-12-31T13:00:00Z",
        ),
    )

    assert FeatureLoader.is_incomplete(feature) is False


# ============================================================================
# Test: Resume Support - get_resume_point
# ============================================================================


def test_get_resume_point_basic():
    """Test getting resume point for incomplete feature."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        description="",
        created="2025-12-31",
        status="in_progress",
        complexity=5,
        estimated_tasks=3,
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("t1.md"),
                complexity=3,
                dependencies=[],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-2",
                name="Task 2",
                file_path=Path("t2.md"),
                complexity=3,
                dependencies=[],
                status="in_progress",
                implementation_mode="task-work",
                estimated_minutes=30,
                current_turn=2,
            ),
            FeatureTask(
                id="TASK-3",
                name="Task 3",
                file_path=Path("t3.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-1"], ["TASK-2"], ["TASK-3"]],
            estimated_duration_minutes=90,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(
            started_at="2025-12-31T12:00:00Z",
            worktree_path="/path/to/worktree",
            current_wave=2,
            completed_waves=[1],
        ),
    )

    resume_point = FeatureLoader.get_resume_point(feature)

    assert resume_point["wave"] == 2
    assert resume_point["task_id"] == "TASK-2"
    assert resume_point["turn"] == 2
    assert resume_point["completed_tasks"] == ["TASK-1"]
    assert resume_point["pending_tasks"] == ["TASK-3"]
    assert resume_point["worktree_path"] == "/path/to/worktree"


def test_get_resume_point_no_in_progress_task():
    """Test resume point when no task is in_progress."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        description="",
        created="2025-12-31",
        status="in_progress",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("t1.md"),
                complexity=3,
                dependencies=[],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-2",
                name="Task 2",
                file_path=Path("t2.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-1"], ["TASK-2"]],
            estimated_duration_minutes=60,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(
            completed_waves=[1],
        ),
    )

    resume_point = FeatureLoader.get_resume_point(feature)

    assert resume_point["wave"] == 2  # Next wave after completed
    assert resume_point["task_id"] is None  # No task in progress
    assert resume_point["turn"] == 0


# ============================================================================
# Test: Resume Support - reset_state
# ============================================================================


def test_reset_state():
    """Test resetting feature state for fresh start."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        description="",
        created="2025-12-31",
        status="in_progress",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("t1.md"),
                complexity=3,
                dependencies=[],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=30,
                turns_completed=2,
                current_turn=0,
                started_at="2025-12-31T12:00:00Z",
                completed_at="2025-12-31T12:30:00Z",
                result={"success": True},
            ),
            FeatureTask(
                id="TASK-2",
                name="Task 2",
                file_path=Path("t2.md"),
                complexity=3,
                dependencies=[],
                status="in_progress",
                implementation_mode="task-work",
                estimated_minutes=30,
                turns_completed=1,
                current_turn=2,
                started_at="2025-12-31T12:30:00Z",
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-1"], ["TASK-2"]],
            estimated_duration_minutes=60,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(
            started_at="2025-12-31T12:00:00Z",
            worktree_path="/path/to/worktree",
            current_wave=2,
            completed_waves=[1],
            total_turns=3,
            tasks_completed=1,
            tasks_failed=0,
        ),
    )

    FeatureLoader.reset_state(feature)

    # Check feature-level reset
    assert feature.status == "planned"
    assert feature.execution.started_at is None
    assert feature.execution.worktree_path is None
    assert feature.execution.current_wave == 0
    assert feature.execution.completed_waves == []
    assert feature.execution.total_turns == 0
    assert feature.execution.tasks_completed == 0

    # Check task-level reset
    for task in feature.tasks:
        assert task.status == "pending"
        assert task.result is None
        assert task.turns_completed == 0
        assert task.current_turn == 0
        assert task.started_at is None
        assert task.completed_at is None


# ============================================================================
# Test: Task State Fields
# ============================================================================


def test_task_state_fields_default():
    """Test FeatureTask state fields have correct defaults."""
    task = FeatureTask(
        id="TASK-TEST",
        name="Test",
        file_path=Path("t.md"),
        complexity=3,
        dependencies=[],
        status="pending",
        implementation_mode="task-work",
        estimated_minutes=30,
    )

    assert task.turns_completed == 0
    assert task.current_turn == 0
    assert task.started_at is None
    assert task.completed_at is None


def test_task_state_fields_persistence():
    """Test task state fields are saved and loaded correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        original = Feature(
            id="FEAT-STATE",
            name="State Test",
            description="",
            created="2025-12-31",
            status="in_progress",
            complexity=5,
            estimated_tasks=1,
            tasks=[
                FeatureTask(
                    id="TASK-1",
                    name="Task 1",
                    file_path=Path("t1.md"),
                    complexity=3,
                    dependencies=[],
                    status="in_progress",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                    turns_completed=2,
                    current_turn=3,
                    started_at="2025-12-31T12:00:00Z",
                    completed_at=None,
                )
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-1"]],
                estimated_duration_minutes=30,
                recommended_parallel=1,
            ),
            execution=FeatureExecution(
                started_at="2025-12-31T12:00:00Z",
                current_wave=1,
                completed_waves=[],
                last_updated="2025-12-31T12:15:00Z",
            ),
        )

        # Save and reload
        FeatureLoader.save_feature(original, repo_root=repo_root)
        reloaded = FeatureLoader.load_feature("FEAT-STATE", repo_root=repo_root)

        # Verify task state fields
        task = reloaded.tasks[0]
        assert task.turns_completed == 2
        assert task.current_turn == 3
        assert task.started_at == "2025-12-31T12:00:00Z"
        assert task.completed_at is None

        # Verify execution state fields
        assert reloaded.execution.current_wave == 1
        assert reloaded.execution.completed_waves == []
        assert reloaded.execution.last_updated == "2025-12-31T12:15:00Z"
