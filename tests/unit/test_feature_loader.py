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
    TASK_SCHEMA,
    FEATURE_SCHEMA,
    ORCHESTRATION_SCHEMA,
    _truncate_data,
    _build_schema_error_message,
    _find_similar_ids,
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
    """Test FeatureParseError for missing required fields with schema hints."""
    features_dir = temp_features_dir / ".guardkit" / "features"
    incomplete_file = features_dir / "FEAT-INCOMPLETE.yaml"

    # Write YAML missing required 'id' field
    incomplete_file.write_text(yaml.dump({"name": "Missing ID feature"}))

    with pytest.raises(FeatureParseError) as exc_info:
        FeatureLoader.load_feature("FEAT-INCOMPLETE", repo_root=temp_features_dir)

    error_msg = str(exc_info.value)
    # Verify improved error message format with schema hints
    assert "Missing required field 'id'" in error_msg
    assert "Feature Schema:" in error_msg
    assert "Present fields:" in error_msg
    assert "Fix:" in error_msg


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
# Test: Feature Validation - file_path checks (TASK-FIX-FP02)
# ============================================================================


def test_validate_feature_rejects_directory_file_path(tmp_path):
    """Test validation rejects file_path pointing to a directory (e.g., '.')."""
    feature = Feature(
        id="FEAT-DIR",
        name="Dir Test",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-DIR-001",
                name="Task with dir path",
                file_path=Path("."),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-DIR-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
    )

    errors = FeatureLoader.validate_feature(feature, repo_root=tmp_path)
    assert any("directory, not a file" in e for e in errors)
    assert any("TASK-DIR-001" in e for e in errors)


def test_validate_feature_rejects_subdirectory_file_path(tmp_path):
    """Test validation rejects file_path pointing to an existing subdirectory."""
    # Create a real directory at the path
    (tmp_path / "tasks" / "backlog").mkdir(parents=True)

    feature = Feature(
        id="FEAT-SUBDIR",
        name="Subdir Test",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-SUBDIR-001",
                name="Task with subdir path",
                file_path=Path("tasks/backlog"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-SUBDIR-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
    )

    errors = FeatureLoader.validate_feature(feature, repo_root=tmp_path)
    assert any("directory, not a file" in e for e in errors)


def test_validate_feature_rejects_non_md_file_path(tmp_path):
    """Test validation rejects file_path not ending in .md."""
    # Create the file so it passes exists() check
    (tmp_path / "tasks" / "backlog").mkdir(parents=True)
    (tmp_path / "tasks" / "backlog" / "TASK-TXT-001.txt").write_text("content")

    feature = Feature(
        id="FEAT-TXT",
        name="Txt Test",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-TXT-001",
                name="Task with txt path",
                file_path=Path("tasks/backlog/TASK-TXT-001.txt"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-TXT-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
    )

    errors = FeatureLoader.validate_feature(feature, repo_root=tmp_path)
    assert any("does not end with .md" in e for e in errors)
    assert any("TASK-TXT-001" in e for e in errors)


def test_validate_feature_rejects_file_path_without_tasks_dir(tmp_path):
    """Test validation rejects file_path without 'tasks' in path components."""
    # Create the file so it passes exists() and suffix checks
    (tmp_path / "src").mkdir(parents=True)
    (tmp_path / "src" / "TASK-SRC-001.md").write_text("content")

    feature = Feature(
        id="FEAT-SRC",
        name="Src Test",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-SRC-001",
                name="Task in wrong dir",
                file_path=Path("src/TASK-SRC-001.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-SRC-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
    )

    errors = FeatureLoader.validate_feature(feature, repo_root=tmp_path)
    assert any("does not contain 'tasks' directory" in e for e in errors)
    assert any("TASK-SRC-001" in e for e in errors)


def test_validate_feature_valid_file_paths_still_pass(tmp_path):
    """Test that existing valid file_path values still pass validation."""
    # Create valid task files
    (tmp_path / "tasks" / "backlog").mkdir(parents=True)
    (tmp_path / "tasks" / "backlog" / "TASK-OK-001.md").write_text("# Task")
    (tmp_path / "tasks" / "backlog" / "TASK-OK-002.md").write_text("# Task")

    feature = Feature(
        id="FEAT-OK",
        name="Valid Test",
        description="",
        created="2025-12-31",
        status="planned",
        complexity=3,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-OK-001",
                name="Valid task 1",
                file_path=Path("tasks/backlog/TASK-OK-001.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-OK-002",
                name="Valid task 2",
                file_path=Path("tasks/backlog/TASK-OK-002.md"),
                complexity=3,
                dependencies=["TASK-OK-001"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-OK-001"], ["TASK-OK-002"]],
            estimated_duration_minutes=60,
            recommended_parallel=1,
        ),
    )

    errors = FeatureLoader.validate_feature(feature, repo_root=tmp_path)
    assert errors == []


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


# ============================================================================
# Test: Schema Hint Error Messages (TASK-FP-004)
# ============================================================================


class TestSchemaHintErrorMessages:
    """Test improved error messages with schema hints."""

    def test_truncate_data_short_string(self):
        """Test _truncate_data doesn't truncate short strings."""
        data = {"id": "TASK-001", "name": "Test"}
        result = _truncate_data(data)
        assert "..." not in result
        assert "TASK-001" in result

    def test_truncate_data_long_string(self):
        """Test _truncate_data truncates long strings at 200 chars."""
        data = {"key": "x" * 300}
        result = _truncate_data(data, max_length=200)
        assert result.endswith("...")
        assert len(result) == 203  # 200 chars + "..."

    def test_truncate_data_custom_max_length(self):
        """Test _truncate_data with custom max_length."""
        data = "This is a test string that should be truncated"
        result = _truncate_data(data, max_length=20)
        assert result == "This is a test strin..."
        assert len(result) == 23

    def test_build_schema_error_message_structure(self):
        """Test _build_schema_error_message produces expected structure."""
        msg = _build_schema_error_message(
            missing_field="file_path",
            context="task 'TASK-001'",
            data={"id": "TASK-001", "name": "Test"},
            schema=TASK_SCHEMA,
        )

        assert "Missing required field 'file_path'" in msg
        assert "task 'TASK-001'" in msg
        assert "Task Schema:" in msg
        assert "Present fields:" in msg
        assert "['id', 'name']" in msg
        assert "Fix:" in msg
        assert "/feature-plan" in msg

    def test_build_schema_error_message_empty_data(self):
        """Test _build_schema_error_message handles empty data."""
        msg = _build_schema_error_message(
            missing_field="id",
            context="feature definition",
            data={},
            schema=FEATURE_SCHEMA,
        )

        assert "Missing required field 'id'" in msg
        assert "Present fields: []" in msg

    def test_build_schema_error_message_none_data(self):
        """Test _build_schema_error_message handles None data."""
        msg = _build_schema_error_message(
            missing_field="id",
            context="feature definition",
            data=None,
            schema=FEATURE_SCHEMA,
        )

        assert "Missing required field 'id'" in msg
        assert "Present fields: []" in msg

    def test_parse_error_missing_task_id(self, temp_features_dir, sample_feature_yaml):
        """Test parse error for missing task 'id' shows schema hint."""
        features_dir = temp_features_dir / ".guardkit" / "features"

        # Create feature with task missing 'id'
        bad_task_feature = sample_feature_yaml.copy()
        bad_task_feature["tasks"] = [
            {
                "name": "Task without ID",
                "file_path": "tasks/test.md",
            }
        ]
        bad_file = features_dir / "FEAT-BAD-TASK-ID.yaml"
        with open(bad_file, "w") as f:
            yaml.dump(bad_task_feature, f)

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-BAD-TASK-ID", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Missing required field 'id'" in error_msg
        assert "Task Schema:" in error_msg
        assert "Fix:" in error_msg

    def test_parse_error_missing_file_path(self, temp_features_dir, sample_feature_yaml):
        """Test parse error for missing 'file_path' shows expected schema."""
        features_dir = temp_features_dir / ".guardkit" / "features"

        # Create feature with task missing 'file_path'
        bad_task_feature = sample_feature_yaml.copy()
        bad_task_feature["tasks"] = [
            {
                "id": "TASK-NO-PATH",
                "name": "Task without file_path",
            }
        ]
        bad_file = features_dir / "FEAT-BAD-PATH.yaml"
        with open(bad_file, "w") as f:
            yaml.dump(bad_task_feature, f)

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-BAD-PATH", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Missing required field 'file_path'" in error_msg
        assert "task 'TASK-NO-PATH'" in error_msg
        assert "Task Schema:" in error_msg

    def test_parse_error_missing_feature_id(self, temp_features_dir):
        """Test parse error for missing feature 'id' shows schema."""
        features_dir = temp_features_dir / ".guardkit" / "features"
        incomplete_file = features_dir / "FEAT-NO-ID.yaml"

        # Write YAML missing 'id' field
        incomplete_file.write_text(yaml.dump({"name": "Feature without ID"}))

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-NO-ID", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Missing required field 'id'" in error_msg
        assert "feature definition" in error_msg
        assert "Feature Schema:" in error_msg

    def test_parse_error_missing_feature_name(self, temp_features_dir):
        """Test parse error for missing feature 'name' shows schema."""
        features_dir = temp_features_dir / ".guardkit" / "features"
        incomplete_file = features_dir / "FEAT-NO-NAME.yaml"

        # Write YAML missing 'name' field
        incomplete_file.write_text(yaml.dump({"id": "FEAT-NO-NAME"}))

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-NO-NAME", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Missing required field 'name'" in error_msg
        assert "Feature Schema:" in error_msg

    def test_parse_error_shows_actual_data(self, temp_features_dir):
        """Test parse error includes actual data that caused error."""
        features_dir = temp_features_dir / ".guardkit" / "features"
        bad_file = features_dir / "FEAT-DATA-PREVIEW.yaml"

        # Write YAML with some fields but missing required one
        data = {"description": "A feature", "complexity": 5}
        bad_file.write_text(yaml.dump(data))

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-DATA-PREVIEW", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Data preview:" in error_msg
        assert "description" in error_msg or "complexity" in error_msg

    def test_parse_error_shows_present_fields(self, temp_features_dir):
        """Test parse error shows list of fields that ARE present."""
        features_dir = temp_features_dir / ".guardkit" / "features"
        bad_file = features_dir / "FEAT-FIELDS.yaml"

        # Write YAML with specific fields but missing 'id'
        data = {"name": "Test Feature", "description": "Description"}
        bad_file.write_text(yaml.dump(data))

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-FIELDS", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Present fields:" in error_msg
        assert "name" in error_msg
        assert "description" in error_msg

    def test_error_message_includes_fix_suggestion(self, temp_features_dir):
        """Test error message includes actionable fix suggestions."""
        features_dir = temp_features_dir / ".guardkit" / "features"
        bad_file = features_dir / "FEAT-FIX.yaml"

        # Write YAML missing required field
        bad_file.write_text(yaml.dump({"name": "No ID feature"}))

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-FIX", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Fix:" in error_msg
        assert "/feature-plan" in error_msg

    def test_valid_task_no_error(self, sample_feature_yaml):
        """Regression test: valid task data doesn't raise error."""
        task_data = sample_feature_yaml["tasks"][0]
        task = FeatureLoader._parse_task(task_data)

        assert task.id == "TASK-AUTH-001"
        assert task.file_path == Path("tasks/backlog/TASK-AUTH-001.md")

    def test_schema_constants_exported(self):
        """Test that schema constants are exported and non-empty."""
        assert TASK_SCHEMA
        assert "id" in TASK_SCHEMA
        assert "file_path" in TASK_SCHEMA

        assert FEATURE_SCHEMA
        assert "id" in FEATURE_SCHEMA
        assert "name" in FEATURE_SCHEMA

        assert ORCHESTRATION_SCHEMA
        assert "parallel_groups" in ORCHESTRATION_SCHEMA


# ============================================================================
# Test: Similar ID Suggestions (TASK-1043)
# ============================================================================


class TestFindSimilarIds:
    """Test _find_similar_ids function for typo suggestions in error messages."""

    def test_prefix_match_same_prefix_different_number(self):
        """Test prefix matching: TASK-AUTH-001 matches TASK-AUTH-002, TASK-AUTH-003."""
        target = "TASK-AUTH-001"
        candidates = {"TASK-AUTH-002", "TASK-AUTH-003", "TASK-LOG-001"}
        result = _find_similar_ids(target, candidates)

        # Should suggest both AUTH tasks (prefix match) before LOG
        assert len(result) >= 2
        assert "TASK-AUTH-002" in result
        assert "TASK-AUTH-003" in result

    def test_character_difference_single_char(self):
        """Test character difference: TASK-DOC-001 with candidates TASK-LOG-001."""
        target = "TASK-DOC-001"
        candidates = {"TASK-LOG-001", "TASK-LOG-002"}
        result = _find_similar_ids(target, candidates)

        # TASK-DOC-001 vs TASK-LOG-001 differs by 2 chars (D→L, O→O, C→G)
        # Actually DOC vs LOG: D→L (1), O=O (0), C→G (1) = 2 chars different
        assert "TASK-LOG-001" in result

    def test_no_match_completely_different(self):
        """Test no suggestions for completely different IDs."""
        target = "TASK-XYZ-999"
        candidates = {"TASK-ABC-001", "TASK-DEF-002"}
        result = _find_similar_ids(target, candidates)

        # XYZ-999 vs ABC-001 and DEF-002 are too different
        # No prefix match, no substring match, char diff > 2
        assert result == []

    def test_substring_match_shorter_target(self):
        """Test substring matching: TASK-LOG-01 contains in TASK-LOG-001."""
        target = "TASK-LOG-01"
        candidates = {"TASK-LOG-001", "TASK-LOG-002"}
        result = _find_similar_ids(target, candidates)

        # "task-log-01" is substring of "task-log-001"
        assert "TASK-LOG-001" in result

    def test_substring_match_longer_target(self):
        """Test substring matching: TASK-LOG-0012 contains TASK-LOG-001."""
        target = "TASK-LOG-0012"
        candidates = {"TASK-LOG-001", "TASK-XYZ-999"}
        result = _find_similar_ids(target, candidates)

        # "task-log-001" is substring of "task-log-0012"
        assert "TASK-LOG-001" in result

    def test_empty_candidates_returns_empty(self):
        """Test empty candidates returns empty list."""
        target = "TASK-AUTH-001"
        candidates = set()
        result = _find_similar_ids(target, candidates)

        assert result == []

    def test_target_not_in_candidates_by_design(self):
        """Test that the function is designed for finding similar, not exact matches.

        The use case is when target is an unknown ID not in the valid set.
        If target IS in candidates, it would match (prefix, char diff = 0).
        """
        target = "TASK-AUTH-001"
        candidates = {"TASK-AUTH-001", "TASK-AUTH-002"}
        result = _find_similar_ids(target, candidates)

        # TASK-AUTH-001 matches prefix TASK-AUTH, so it would be suggested
        # This tests the function behavior, not a bug
        assert "TASK-AUTH-001" in result or "TASK-AUTH-002" in result

    def test_max_three_results(self):
        """Test that at most 3 results are returned."""
        target = "TASK-AUTH-001"
        candidates = {
            "TASK-AUTH-002",
            "TASK-AUTH-003",
            "TASK-AUTH-004",
            "TASK-AUTH-005",
            "TASK-AUTH-006",
        }
        result = _find_similar_ids(target, candidates)

        assert len(result) <= 3

    def test_sorted_by_similarity_prefix_first(self):
        """Test results are sorted by similarity (prefix match = priority 0)."""
        target = "TASK-AUTH-001"
        candidates = {"TASK-AUTH-002", "TASK-BUTH-001", "TASK-LOG-001"}
        result = _find_similar_ids(target, candidates)

        # TASK-AUTH-002 has prefix match (priority 0)
        # TASK-BUTH-001 has same length, 1 char diff (priority 1)
        if len(result) >= 2:
            assert result[0] == "TASK-AUTH-002"  # Prefix match first

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        target = "task-auth-001"
        candidates = {"TASK-AUTH-002", "TASK-LOG-001"}
        result = _find_similar_ids(target, candidates)

        # Should match prefix despite case difference
        assert "TASK-AUTH-002" in result

    def test_max_distance_parameter_default(self):
        """Test default max_distance=2 for character difference."""
        target = "TASK-LOG-001"
        candidates = {"TASK-DOG-001", "TASK-XYZ-001"}
        result = _find_similar_ids(target, candidates)

        # LOG vs DOG: L→D (1), O=O (0), G=G (0) = 1 char diff (within default 2)
        assert "TASK-DOG-001" in result

    def test_max_distance_parameter_custom(self):
        """Test custom max_distance=1 for stricter matching."""
        target = "TASK-LOG-001"
        candidates = {"TASK-DOC-001", "TASK-FOG-001"}
        result = _find_similar_ids(target, candidates, max_distance=1)

        # LOG vs DOC: L→D (1), O=O (0), G→C (1) = 2 chars diff (exceeds max_distance=1)
        # LOG vs FOG: L→F (1), O=O (0), G=G (0) = 1 char diff (within max_distance=1)
        assert "TASK-FOG-001" in result
        assert "TASK-DOC-001" not in result

    def test_mixed_match_types(self):
        """Test mixing prefix, character diff, and substring matches."""
        target = "TASK-AUTH-001"
        candidates = {
            "TASK-AUTH-002",   # Prefix match (priority 0)
            "TASK-AUTH",       # Substring (priority 1)
            "TASK-BUTH-001",   # 1 char diff (priority 1)
        }
        result = _find_similar_ids(target, candidates)

        # All should be suggested
        assert len(result) == 3
        # Prefix match should be first
        assert result[0] == "TASK-AUTH-002"

    def test_no_hyphen_in_target(self):
        """Test handling of IDs without standard hyphen format."""
        target = "TASKAUTH001"
        candidates = {"TASK-AUTH-001", "TASK-AUTH-002"}
        result = _find_similar_ids(target, candidates)

        # "taskauth001" is substring of neither, no prefix extraction possible
        # Should still handle gracefully (empty or substring match)
        # Actually "taskauth001" IS a substring... no wait, checking contains:
        # "taskauth001" in "task-auth-001" = False
        # "task-auth-001" in "taskauth001" = False (hyphens prevent substring)
        assert isinstance(result, list)

    def test_special_characters_in_id(self):
        """Test handling of special characters in IDs (edge case)."""
        target = "TASK-FIX_BUG-001"
        candidates = {"TASK-FIX_BUG-002", "TASK-FIX-BUG-001"}
        result = _find_similar_ids(target, candidates)

        # Underscore should work with rsplit on hyphen
        # "task-fix_bug" prefix matches "task-fix_bug-002"
        assert "TASK-FIX_BUG-002" in result

    def test_validation_error_integration(self):
        """Test _find_similar_ids is used correctly in validate_feature."""
        # Create a feature with unknown dependency that's similar to a real task
        feature = Feature(
            id="FEAT-TEST",
            name="Test",
            description="",
            created="2026-01-25",
            status="planned",
            complexity=5,
            estimated_tasks=2,
            tasks=[
                FeatureTask(
                    id="TASK-AUTH-001",
                    name="Task 1",
                    file_path=Path("tasks/t1.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-AUTH-002",
                    name="Task 2",
                    file_path=Path("tasks/t2.md"),
                    complexity=3,
                    dependencies=["TASK-AUTH-01"],  # Typo: missing last digit
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-AUTH-001"], ["TASK-AUTH-002"]],
                estimated_duration_minutes=60,
                recommended_parallel=1,
            ),
        )

        # Create temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            for task in feature.tasks:
                task_file = repo_root / task.file_path
                task_file.parent.mkdir(parents=True, exist_ok=True)
                task_file.write_text(f"# {task.name}\n")

            errors = FeatureLoader.validate_feature(feature, repo_root=repo_root)

            # Should have unknown dependency error with suggestion
            dep_error = [e for e in errors if "unknown dependency" in e.lower()]
            assert len(dep_error) == 1
            assert "TASK-AUTH-01" in dep_error[0]
            assert "Did you mean" in dep_error[0]
            assert "TASK-AUTH-001" in dep_error[0]

    def test_same_length_different_chars_within_threshold(self):
        """Test same length IDs with exactly max_distance differences."""
        target = "TASK-AAA-001"
        candidates = {"TASK-BBB-001", "TASK-ABC-001"}
        result = _find_similar_ids(target, candidates, max_distance=2)

        # AAA vs ABC: A=A (0), A→B (1), A→C (1) = 2 chars diff (exactly at threshold)
        # AAA vs BBB: A→B (1), A→B (1), A→B (1) = 3 chars diff (exceeds threshold)
        assert "TASK-ABC-001" in result
        assert "TASK-BBB-001" not in result

    def test_numeric_suffix_variations(self):
        """Test variations in numeric suffix detection."""
        target = "TASK-LOG-100"
        candidates = {"TASK-LOG-001", "TASK-LOG-101", "TASK-LOG-200"}
        result = _find_similar_ids(target, candidates)

        # All have same prefix "TASK-LOG"
        assert len(result) == 3

    def test_alphabetical_tiebreaker(self):
        """Test that same-similarity matches are sorted alphabetically."""
        target = "TASK-TEST-001"
        candidates = {"TASK-TEST-003", "TASK-TEST-002", "TASK-TEST-004"}
        result = _find_similar_ids(target, candidates)

        # All have prefix match (priority 0), should be sorted alphabetically
        assert result == ["TASK-TEST-002", "TASK-TEST-003", "TASK-TEST-004"]


# ============================================================================
# Test: Schema Parsing Edge Cases (TASK-FP-005)
# ============================================================================


class TestFeatureLoaderParsing:
    """Tests for FeatureLoader schema parsing edge cases."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to feature YAML fixtures directory."""
        return Path(__file__).parent.parent / "fixtures" / "feature_yamls"

    def test_valid_schema_parses_successfully(self, fixtures_dir):
        """Valid feature YAML should parse without errors."""
        feature = FeatureLoader.load_feature(
            "FEAT-VALID",
            features_dir=fixtures_dir,
        )

        assert feature.id == "FEAT-VALID"
        assert feature.name == "Valid Feature for Testing"
        assert len(feature.tasks) == 3
        assert feature.orchestration.parallel_groups == [
            ["TASK-V-001"],
            ["TASK-V-002"],
            ["TASK-V-003"],
        ]

    def test_missing_file_path_raises_parse_error(self, fixtures_dir):
        """Missing file_path field should raise FeatureParseError with helpful message."""
        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature(
                "missing_file_path",
                features_dir=fixtures_dir,
            )

        error_msg = str(exc_info.value)
        assert "Missing required field 'file_path'" in error_msg
        assert "task 'TASK-NO-PATH'" in error_msg
        assert "Task Schema:" in error_msg
        assert "Fix:" in error_msg

    def test_missing_task_id_raises_parse_error(self, fixtures_dir):
        """Missing id field should raise FeatureParseError."""
        # Create a temp file with missing task id
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            bad_file = temp_dir / "FEAT-NO-TASK-ID.yaml"
            bad_file.write_text(yaml.dump({
                "id": "FEAT-NO-TASK-ID",
                "name": "Feature with task missing id",
                "tasks": [
                    {
                        "name": "Task without ID",
                        "file_path": "tasks/test.md",
                    }
                ],
                "orchestration": {"parallel_groups": [[]]},
            }))

            with pytest.raises(FeatureParseError) as exc_info:
                FeatureLoader.load_feature("FEAT-NO-TASK-ID", features_dir=temp_dir)

            error_msg = str(exc_info.value)
            assert "Missing required field 'id'" in error_msg
            assert "Task Schema:" in error_msg

    def test_old_execution_groups_format_uses_empty_orchestration(self, fixtures_dir):
        """Old execution_groups format should result in empty parallel_groups.

        When execution_groups is used instead of orchestration.parallel_groups,
        the parser ignores execution_groups and creates empty orchestration.
        This is schema-compatible behavior (graceful degradation).
        """
        feature = FeatureLoader.load_feature(
            "old_schema_format",
            features_dir=fixtures_dir,
        )

        # execution_groups is ignored, orchestration defaults to empty
        assert feature.orchestration.parallel_groups == []
        # But tasks are still parsed correctly
        assert len(feature.tasks) == 2
        assert feature.tasks[0].id == "TASK-OLD-001"

    def test_old_execution_groups_format_fails_validation(self, fixtures_dir):
        """Old execution_groups format should fail validation (tasks not in orchestration)."""
        feature = FeatureLoader.load_feature(
            "old_schema_format",
            features_dir=fixtures_dir,
        )

        # Validation should catch missing orchestration
        errors = FeatureLoader.validate_feature(feature, repo_root=fixtures_dir.parent.parent)
        assert any("Tasks not in orchestration" in e for e in errors)

    def test_task_files_section_ignored(self, fixtures_dir):
        """Redundant task_files section should be ignored if present."""
        feature = FeatureLoader.load_feature(
            "with_task_files",
            features_dir=fixtures_dir,
        )

        # Feature should parse successfully, ignoring task_files
        assert feature.id == "FEAT-WITH-FILES"
        assert len(feature.tasks) == 1
        # file_path should come from tasks[].file_path, not task_files
        assert feature.tasks[0].file_path == Path("tasks/backlog/TASK-WF-001.md")

    def test_empty_tasks_list_validation_error(self, fixtures_dir):
        """Feature with no tasks should raise validation error (not parse error)."""
        # Empty tasks parses successfully
        feature = FeatureLoader.load_feature(
            "empty_tasks",
            features_dir=fixtures_dir,
        )
        assert feature.id == "FEAT-EMPTY"
        assert len(feature.tasks) == 0

        # But validation catches the issue
        errors = FeatureLoader.validate_feature(feature, repo_root=fixtures_dir.parent.parent)
        assert any("no tasks defined" in e.lower() for e in errors)

    def test_circular_dependencies_detected(self, fixtures_dir):
        """Circular task dependencies should be detected."""
        feature = FeatureLoader.load_feature(
            "circular_deps",
            features_dir=fixtures_dir,
        )

        # Parsing succeeds
        assert len(feature.tasks) == 3

        # Circular dependency detection works
        cycle = FeatureLoader._detect_circular_dependencies(feature)
        assert cycle is not None
        # Cycle should include at least one of the circular tasks
        assert any(task_id in cycle for task_id in ["TASK-CIRC-A", "TASK-CIRC-B", "TASK-CIRC-C"])

    def test_missing_task_file_validation(self, fixtures_dir):
        """Non-existent task files should raise validation error."""
        feature = FeatureLoader.load_feature(
            "FEAT-VALID",
            features_dir=fixtures_dir,
        )

        # Use a repo_root where task files don't exist
        errors = FeatureLoader.validate_feature(feature, repo_root=fixtures_dir)
        assert len(errors) >= 3  # All 3 task files missing
        assert all("Task file not found" in e for e in errors)

    def test_parallel_groups_list_of_lists(self, fixtures_dir):
        """parallel_groups must be list of lists format."""
        feature = FeatureLoader.load_feature(
            "FEAT-VALID",
            features_dir=fixtures_dir,
        )

        # Verify structure is list of lists
        assert isinstance(feature.orchestration.parallel_groups, list)
        for wave in feature.orchestration.parallel_groups:
            assert isinstance(wave, list)
            for task_id in wave:
                assert isinstance(task_id, str)


class TestFeatureLoaderEdgeCases:
    """Edge case tests for FeatureLoader."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to feature YAML fixtures directory."""
        return Path(__file__).parent.parent / "fixtures" / "feature_yamls"

    def test_single_task_feature(self, fixtures_dir):
        """Feature with single task should work."""
        feature = FeatureLoader.load_feature(
            "single_task",
            features_dir=fixtures_dir,
        )

        assert feature.id == "FEAT-SINGLE"
        assert len(feature.tasks) == 1
        assert feature.tasks[0].id == "TASK-SINGLE-001"
        assert feature.orchestration.parallel_groups == [["TASK-SINGLE-001"]]

    def test_all_tasks_parallel(self, fixtures_dir):
        """All tasks in single wave should work."""
        feature = FeatureLoader.load_feature(
            "all_parallel",
            features_dir=fixtures_dir,
        )

        assert feature.id == "FEAT-PARALLEL"
        assert len(feature.tasks) == 4

        # All tasks in single wave
        assert len(feature.orchestration.parallel_groups) == 1
        assert len(feature.orchestration.parallel_groups[0]) == 4

        # All tasks have no dependencies
        for task in feature.tasks:
            assert task.dependencies == []

    def test_complex_dependency_graph(self, fixtures_dir):
        """Complex but valid dependency graph should work (diamond pattern)."""
        feature = FeatureLoader.load_feature(
            "complex_deps",
            features_dir=fixtures_dir,
        )

        assert feature.id == "FEAT-COMPLEX"
        assert len(feature.tasks) == 5

        # Verify dependency structure (diamond pattern)
        task_map = {t.id: t for t in feature.tasks}

        assert task_map["TASK-CX-001"].dependencies == []
        assert task_map["TASK-CX-002"].dependencies == ["TASK-CX-001"]
        assert task_map["TASK-CX-003"].dependencies == ["TASK-CX-001"]
        assert sorted(task_map["TASK-CX-004"].dependencies) == ["TASK-CX-002", "TASK-CX-003"]
        assert task_map["TASK-CX-005"].dependencies == ["TASK-CX-004"]

        # No circular dependencies
        cycle = FeatureLoader._detect_circular_dependencies(feature)
        assert cycle is None

    def test_optional_fields_use_defaults(self, fixtures_dir):
        """Optional fields should use sensible defaults."""
        feature = FeatureLoader.load_feature(
            "minimal_defaults",
            features_dir=fixtures_dir,
        )

        assert feature.id == "FEAT-MINIMAL"
        assert feature.name == "Minimal Feature"

        # Feature-level defaults
        assert feature.description == ""
        assert feature.status == "planned"
        assert feature.complexity == 5  # Default complexity

        # Task-level defaults
        task = feature.tasks[0]
        assert task.id == "TASK-MIN-001"
        assert task.name == "TASK-MIN-001"  # Defaults to id
        assert task.complexity == 5
        assert task.dependencies == []
        assert task.status == "pending"
        assert task.implementation_mode == "task-work"
        assert task.estimated_minutes == 30

        # Orchestration defaults
        assert feature.orchestration.estimated_duration_minutes == 0
        assert feature.orchestration.recommended_parallel == 1

    def test_feature_with_all_task_statuses(self):
        """Feature should accept all valid task statuses."""
        for status in ["pending", "in_progress", "completed", "failed", "skipped"]:
            task_data = {
                "id": f"TASK-STATUS-{status}",
                "file_path": "tasks/test.md",
                "status": status,
            }
            task = FeatureLoader._parse_task(task_data)
            assert task.status == status

    def test_feature_with_all_implementation_modes(self):
        """Feature should accept all valid implementation modes."""
        for mode in ["task-work", "direct", "manual"]:
            task_data = {
                "id": f"TASK-MODE-{mode}",
                "file_path": "tasks/test.md",
                "implementation_mode": mode,
            }
            task = FeatureLoader._parse_task(task_data)
            assert task.implementation_mode == mode

    def test_self_dependency_detected(self):
        """Task depending on itself should be detected as circular."""
        feature = Feature(
            id="FEAT-SELF-DEP",
            name="Self Dependency Test",
            description="",
            created="2026-01-06",
            status="planned",
            complexity=3,
            estimated_tasks=1,
            tasks=[
                FeatureTask(
                    id="TASK-SELF",
                    name="Task depends on itself",
                    file_path=Path("tasks/self.md"),
                    complexity=3,
                    dependencies=["TASK-SELF"],  # Self-dependency
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-SELF"]],
                estimated_duration_minutes=30,
                recommended_parallel=1,
            ),
        )

        cycle = FeatureLoader._detect_circular_dependencies(feature)
        assert cycle is not None
        assert "TASK-SELF" in cycle

    def test_missing_orchestration_uses_defaults(self):
        """Missing orchestration section should use defaults."""
        data = {
            "id": "FEAT-NO-ORCH",
            "name": "Feature without orchestration",
            "tasks": [
                {
                    "id": "TASK-NO-ORCH",
                    "file_path": "tasks/test.md",
                }
            ],
            # No orchestration section
        }

        feature = FeatureLoader._parse_feature(data)

        assert feature.orchestration.parallel_groups == []
        assert feature.orchestration.estimated_duration_minutes == 0
        assert feature.orchestration.recommended_parallel == 1

    def test_unicode_in_feature_name(self):
        """Feature should handle unicode characters in names."""
        data = {
            "id": "FEAT-UNICODE",
            "name": "Feature with Unicode: \u00e9\u00e8\u00ea \u4e2d\u6587 \U0001F680",
            "description": "Test unicode: \u00e4\u00f6\u00fc\u00df",
            "tasks": [
                {
                    "id": "TASK-UNICODE",
                    "name": "Task: \u2705 \u2764\ufe0f",
                    "file_path": "tasks/unicode.md",
                }
            ],
            "orchestration": {
                "parallel_groups": [["TASK-UNICODE"]],
            },
        }

        feature = FeatureLoader._parse_feature(data)

        assert "\u00e9" in feature.name  # e with accent
        assert "\u4e2d\u6587" in feature.name  # Chinese characters
        assert "\U0001F680" in feature.name  # Rocket emoji
        assert "\u2705" in feature.tasks[0].name  # Checkmark

    def test_very_long_dependency_chain(self):
        """Feature with long dependency chain should work without stack overflow."""
        num_tasks = 50
        tasks = []
        for i in range(num_tasks):
            deps = [f"TASK-CHAIN-{i-1:03d}"] if i > 0 else []
            tasks.append(
                FeatureTask(
                    id=f"TASK-CHAIN-{i:03d}",
                    name=f"Task {i}",
                    file_path=Path(f"tasks/chain-{i}.md"),
                    complexity=3,
                    dependencies=deps,
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                )
            )

        feature = Feature(
            id="FEAT-LONG-CHAIN",
            name="Long Dependency Chain",
            description="",
            created="2026-01-06",
            status="planned",
            complexity=8,
            estimated_tasks=num_tasks,
            tasks=tasks,
            orchestration=FeatureOrchestration(
                parallel_groups=[[f"TASK-CHAIN-{i:03d}"] for i in range(num_tasks)],
                estimated_duration_minutes=num_tasks * 30,
                recommended_parallel=1,
            ),
        )

        # Should not raise RecursionError
        cycle = FeatureLoader._detect_circular_dependencies(feature)
        assert cycle is None  # Linear chain has no cycles


# ============================================================================
# Test: Intra-Wave Dependency Validation (TASK-VAL-WAVE-001)
# ============================================================================


class TestIntraWaveDependencyValidation:
    """Tests for validate_parallel_groups() - detecting tasks depending on others in same wave."""

    def test_validate_parallel_groups_valid_configuration(self):
        """All tasks correctly distributed across waves, no intra-wave dependencies."""
        feature = Feature(
            id="FEAT-VALID-WAVES",
            name="Valid Wave Configuration",
            description="Tasks properly sequenced across waves",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=4,
            tasks=[
                FeatureTask(
                    id="TASK-W-001",
                    name="Foundation task",
                    file_path=Path("tasks/w1.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-W-002",
                    name="Second wave task A",
                    file_path=Path("tasks/w2a.md"),
                    complexity=3,
                    dependencies=["TASK-W-001"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-W-003",
                    name="Second wave task B",
                    file_path=Path("tasks/w2b.md"),
                    complexity=3,
                    dependencies=["TASK-W-001"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-W-004",
                    name="Final task",
                    file_path=Path("tasks/w3.md"),
                    complexity=3,
                    dependencies=["TASK-W-002", "TASK-W-003"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-W-001"],           # Wave 1
                    ["TASK-W-002", "TASK-W-003"],  # Wave 2 (parallel)
                    ["TASK-W-004"],           # Wave 3
                ],
                estimated_duration_minutes=90,
                recommended_parallel=2,
            ),
        )

        errors = FeatureLoader.validate_parallel_groups(feature)
        assert errors == []

    def test_validate_parallel_groups_single_conflict(self):
        """One task depends on another in same wave."""
        feature = Feature(
            id="FEAT-SINGLE-CONFLICT",
            name="Single Intra-Wave Conflict",
            description="Task B depends on Task A but both in Wave 1",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=2,
            tasks=[
                FeatureTask(
                    id="TASK-SC-001",
                    name="Task A",
                    file_path=Path("tasks/a.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-SC-002",
                    name="Task B depends on A",
                    file_path=Path("tasks/b.md"),
                    complexity=3,
                    dependencies=["TASK-SC-001"],  # Depends on task in same wave
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-SC-001", "TASK-SC-002"],  # Both in same wave - ERROR!
                ],
                estimated_duration_minutes=30,
                recommended_parallel=2,
            ),
        )

        errors = FeatureLoader.validate_parallel_groups(feature)
        assert len(errors) == 1
        assert "Wave 1" in errors[0]
        assert "TASK-SC-002" in errors[0]
        assert "depends on" in errors[0]
        assert "TASK-SC-001" in errors[0]
        assert "same parallel group" in errors[0]
        assert "Move TASK-SC-002 to a later wave" in errors[0]

    def test_validate_parallel_groups_multiple_conflicts_same_wave(self):
        """Multiple dependency conflicts in the same wave."""
        feature = Feature(
            id="FEAT-MULTI-SAME-WAVE",
            name="Multiple Conflicts Same Wave",
            description="Wave 2 has A->B and C->D conflicts",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=5,
            tasks=[
                FeatureTask(
                    id="TASK-MS-001",
                    name="Foundation",
                    file_path=Path("tasks/foundation.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-MS-002",
                    name="Task A",
                    file_path=Path("tasks/a.md"),
                    complexity=3,
                    dependencies=["TASK-MS-001"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-MS-003",
                    name="Task B depends on A",
                    file_path=Path("tasks/b.md"),
                    complexity=3,
                    dependencies=["TASK-MS-002"],  # Depends on MS-002 in same wave
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-MS-004",
                    name="Task C",
                    file_path=Path("tasks/c.md"),
                    complexity=3,
                    dependencies=["TASK-MS-001"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-MS-005",
                    name="Task D depends on C",
                    file_path=Path("tasks/d.md"),
                    complexity=3,
                    dependencies=["TASK-MS-004"],  # Depends on MS-004 in same wave
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-MS-001"],
                    # Wave 2: MS-002, MS-003 conflict AND MS-004, MS-005 conflict
                    ["TASK-MS-002", "TASK-MS-003", "TASK-MS-004", "TASK-MS-005"],
                ],
                estimated_duration_minutes=60,
                recommended_parallel=4,
            ),
        )

        errors = FeatureLoader.validate_parallel_groups(feature)
        assert len(errors) == 2

        # Verify both conflicts are reported
        error_text = " ".join(errors)
        assert "TASK-MS-003" in error_text
        assert "TASK-MS-002" in error_text
        assert "TASK-MS-005" in error_text
        assert "TASK-MS-004" in error_text

        # Both should reference Wave 2
        for error in errors:
            assert "Wave 2" in error

    def test_validate_parallel_groups_conflicts_different_waves(self):
        """Conflicts in multiple different waves."""
        feature = Feature(
            id="FEAT-MULTI-WAVE-CONFLICT",
            name="Conflicts in Different Waves",
            description="Wave 1 and Wave 3 each have conflicts",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=4,
            tasks=[
                FeatureTask(
                    id="TASK-MW-001",
                    name="Task A",
                    file_path=Path("tasks/a.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-MW-002",
                    name="Task B depends on A",
                    file_path=Path("tasks/b.md"),
                    complexity=3,
                    dependencies=["TASK-MW-001"],  # Conflict in Wave 1
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-MW-003",
                    name="Task C",
                    file_path=Path("tasks/c.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-MW-004",
                    name="Task D depends on C",
                    file_path=Path("tasks/d.md"),
                    complexity=3,
                    dependencies=["TASK-MW-003"],  # Conflict in Wave 3
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-MW-001", "TASK-MW-002"],  # Wave 1: conflict
                    [],  # Wave 2: empty (unusual but valid)
                    ["TASK-MW-003", "TASK-MW-004"],  # Wave 3: conflict
                ],
                estimated_duration_minutes=60,
                recommended_parallel=2,
            ),
        )

        errors = FeatureLoader.validate_parallel_groups(feature)
        assert len(errors) == 2

        # Verify Wave 1 error
        wave1_errors = [e for e in errors if "Wave 1" in e]
        assert len(wave1_errors) == 1
        assert "TASK-MW-002" in wave1_errors[0]
        assert "TASK-MW-001" in wave1_errors[0]

        # Verify Wave 3 error
        wave3_errors = [e for e in errors if "Wave 3" in e]
        assert len(wave3_errors) == 1
        assert "TASK-MW-004" in wave3_errors[0]
        assert "TASK-MW-003" in wave3_errors[0]

    def test_validate_parallel_groups_empty_orchestration(self):
        """Empty parallel_groups list (no errors)."""
        feature = Feature(
            id="FEAT-EMPTY-ORCH",
            name="Empty Orchestration",
            description="No parallel groups defined",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=1,
            tasks=[
                FeatureTask(
                    id="TASK-EO-001",
                    name="Solo task",
                    file_path=Path("tasks/solo.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[],  # Empty - no waves defined
                estimated_duration_minutes=30,
                recommended_parallel=1,
            ),
        )

        errors = FeatureLoader.validate_parallel_groups(feature)
        assert errors == []

    def test_validate_parallel_groups_single_task_per_wave(self):
        """Single task per wave (no conflicts possible)."""
        feature = Feature(
            id="FEAT-SEQUENTIAL",
            name="Sequential Execution",
            description="Each wave has exactly one task",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=3,
            tasks=[
                FeatureTask(
                    id="TASK-SEQ-001",
                    name="First",
                    file_path=Path("tasks/first.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-SEQ-002",
                    name="Second",
                    file_path=Path("tasks/second.md"),
                    complexity=3,
                    dependencies=["TASK-SEQ-001"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-SEQ-003",
                    name="Third",
                    file_path=Path("tasks/third.md"),
                    complexity=3,
                    dependencies=["TASK-SEQ-002"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-SEQ-001"],
                    ["TASK-SEQ-002"],
                    ["TASK-SEQ-003"],
                ],
                estimated_duration_minutes=90,
                recommended_parallel=1,
            ),
        )

        errors = FeatureLoader.validate_parallel_groups(feature)
        assert errors == []

    def test_validate_parallel_groups_unknown_task_ignored(self):
        """Task ID in wave that doesn't exist (find_task returns None) - no crash."""
        feature = Feature(
            id="FEAT-UNKNOWN-TASK",
            name="Unknown Task in Wave",
            description="Orchestration references non-existent task",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=1,
            tasks=[
                FeatureTask(
                    id="TASK-UK-001",
                    name="Real task",
                    file_path=Path("tasks/real.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-UK-001", "TASK-NONEXISTENT"],  # TASK-NONEXISTENT doesn't exist
                ],
                estimated_duration_minutes=30,
                recommended_parallel=2,
            ),
        )

        # Should not raise an exception - just skip the unknown task
        errors = FeatureLoader.validate_parallel_groups(feature)
        # No intra-wave dependency errors (unknown task has no dependencies)
        assert errors == []

    def test_validate_feature_includes_wave_errors(self):
        """Integration test: validate_feature() includes intra-wave errors."""
        feature = Feature(
            id="FEAT-INTEGRATION",
            name="Integration Test",
            description="Full validation includes wave errors",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=2,
            tasks=[
                FeatureTask(
                    id="TASK-INT-001",
                    name="Task A",
                    file_path=Path("tasks/a.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-INT-002",
                    name="Task B depends on A",
                    file_path=Path("tasks/b.md"),
                    complexity=3,
                    dependencies=["TASK-INT-001"],  # Same wave dependency
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-INT-001", "TASK-INT-002"],  # Both in same wave
                ],
                estimated_duration_minutes=30,
                recommended_parallel=2,
            ),
        )

        # Create temp files so file existence check passes
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            for task in feature.tasks:
                task_file = repo_root / task.file_path
                task_file.parent.mkdir(parents=True, exist_ok=True)
                task_file.write_text(f"# {task.name}\n")

            errors = FeatureLoader.validate_feature(feature, repo_root=repo_root)

            # Should include the intra-wave dependency error
            wave_errors = [e for e in errors if "same parallel group" in e]
            assert len(wave_errors) == 1
            assert "Wave 1" in wave_errors[0]
            assert "TASK-INT-002" in wave_errors[0]
            assert "TASK-INT-001" in wave_errors[0]

    def test_validate_parallel_groups_multiple_dependencies_one_in_wave(self):
        """Task has multiple dependencies, only one is in same wave."""
        feature = Feature(
            id="FEAT-PARTIAL-DEP",
            name="Partial Dependency Conflict",
            description="Task C depends on A (wave 1) and B (same wave)",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=3,
            tasks=[
                FeatureTask(
                    id="TASK-PD-001",
                    name="Task A (Wave 1)",
                    file_path=Path("tasks/a.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-PD-002",
                    name="Task B (Wave 2)",
                    file_path=Path("tasks/b.md"),
                    complexity=3,
                    dependencies=["TASK-PD-001"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-PD-003",
                    name="Task C depends on A and B",
                    file_path=Path("tasks/c.md"),
                    complexity=3,
                    dependencies=["TASK-PD-001", "TASK-PD-002"],  # B is in same wave
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-PD-001"],
                    ["TASK-PD-002", "TASK-PD-003"],  # C and B in same wave - conflict!
                ],
                estimated_duration_minutes=60,
                recommended_parallel=2,
            ),
        )

        errors = FeatureLoader.validate_parallel_groups(feature)
        assert len(errors) == 1
        assert "TASK-PD-003" in errors[0]
        assert "TASK-PD-002" in errors[0]
        # Dependency on TASK-PD-001 should NOT cause error (different wave)
        assert "TASK-PD-001" not in errors[0]

    def test_validate_parallel_groups_bidirectional_conflict(self):
        """Two tasks in same wave depend on each other (reports both)."""
        feature = Feature(
            id="FEAT-BIDIRECT",
            name="Bidirectional Dependency",
            description="A depends on B, B depends on A, same wave",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=2,
            tasks=[
                FeatureTask(
                    id="TASK-BD-001",
                    name="Task A depends on B",
                    file_path=Path("tasks/a.md"),
                    complexity=3,
                    dependencies=["TASK-BD-002"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-BD-002",
                    name="Task B depends on A",
                    file_path=Path("tasks/b.md"),
                    complexity=3,
                    dependencies=["TASK-BD-001"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-BD-001", "TASK-BD-002"],  # Circular in same wave
                ],
                estimated_duration_minutes=30,
                recommended_parallel=2,
            ),
        )

        errors = FeatureLoader.validate_parallel_groups(feature)
        # Should report both directions
        assert len(errors) == 2

        error_messages = " ".join(errors)
        # A depends on B
        assert "TASK-BD-001" in error_messages
        assert "TASK-BD-002" in error_messages

    def test_validate_parallel_groups_empty_waves_skipped(self):
        """Empty waves in parallel_groups are skipped gracefully."""
        feature = Feature(
            id="FEAT-EMPTY-WAVES",
            name="Feature with Empty Waves",
            description="Some waves have no tasks",
            created="2026-01-31",
            status="planned",
            complexity=5,
            estimated_tasks=2,
            tasks=[
                FeatureTask(
                    id="TASK-EW-001",
                    name="Task in Wave 1",
                    file_path=Path("tasks/w1.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
                FeatureTask(
                    id="TASK-EW-002",
                    name="Task in Wave 3",
                    file_path=Path("tasks/w3.md"),
                    complexity=3,
                    dependencies=["TASK-EW-001"],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=30,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-EW-001"],  # Wave 1
                    [],               # Wave 2 empty
                    ["TASK-EW-002"],  # Wave 3
                ],
                estimated_duration_minutes=60,
                recommended_parallel=1,
            ),
        )

        errors = FeatureLoader.validate_parallel_groups(feature)
        assert errors == []
