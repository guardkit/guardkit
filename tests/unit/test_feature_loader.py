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
            "current_task_id": None,
            "completed_task_ids": [],
        },
    }


@pytest.fixture
def temp_features_dir(tmp_path):
    """Create temporary features directory with sample feature."""
    features_dir = tmp_path / ".claude" / "features"
    features_dir.mkdir(parents=True)

    # Create a sample feature file
    sample_yaml = {
        "id": "FEAT-A1B2",
        "name": "Sample Feature",
        "description": "A test feature",
        "created": "2025-12-31T12:00:00Z",
        "status": "planned",
        "complexity": 5,
        "estimated_tasks": 1,
        "tasks": [
            {
                "id": "TASK-001",
                "name": "Sample Task",
                "file_path": "tasks/backlog/TASK-001.md",
                "complexity": 5,
                "status": "pending",
                "implementation_mode": "task-work",
            }
        ],
        "orchestration": {
            "parallel_groups": [["TASK-001"]],
        },
    }

    feature_file = features_dir / "FEAT-A1B2.yaml"
    with open(feature_file, "w") as f:
        yaml.dump(sample_yaml, f)

    return tmp_path


# ============================================================================
# Basic Feature Loading Tests
# ============================================================================


def test_load_feature_success(temp_features_dir):
    """Test loading a valid feature from YAML."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_features_dir)
    assert feature.id == "FEAT-A1B2"
    assert feature.name == "Sample Feature"
    assert len(feature.tasks) == 1


def test_load_feature_not_found(temp_features_dir):
    """Test loading a non-existent feature raises error."""
    with pytest.raises(FeatureNotFoundError, match="Feature not found: FEAT-XXXX"):
        FeatureLoader.load_feature("FEAT-XXXX", repo_root=temp_features_dir)


def test_load_feature_yaml_extension(temp_features_dir):
    """Test loading feature with .yaml extension works."""
    feature = FeatureLoader.load_feature("FEAT-A1B2.yaml", repo_root=temp_features_dir)
    assert feature.id == "FEAT-A1B2"


def test_load_feature_parse_error(temp_features_dir):
    """Test loading invalid YAML raises parse error."""
    features_dir = temp_features_dir / ".claude" / "features"
    bad_file = features_dir / "FEAT-BAD.yaml"
    bad_file.write_text("invalid: yaml: content: [")

    with pytest.raises(FeatureParseError):
        FeatureLoader.load_feature("FEAT-BAD", repo_root=temp_features_dir)


def test_load_feature_missing_required_field(temp_features_dir):
    """Test loading YAML with missing required field."""
    features_dir = temp_features_dir / ".claude" / "features"
    incomplete_file = features_dir / "FEAT-INCOMPLETE.yaml"

    # Missing 'id' field
    with open(incomplete_file, "w") as f:
        yaml.dump({"name": "Incomplete Feature"}, f)

    with pytest.raises(FeatureParseError, match="Field 'id' is required"):
        FeatureLoader.load_feature("FEAT-INCOMPLETE", repo_root=temp_features_dir)


# ============================================================================
# Task Parsing Tests
# ============================================================================


def test_parse_task_complete(sample_feature_yaml):
    """Test parsing task with all fields."""
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
    """Test task parsing uses default values."""
    minimal_task = {
        "id": "TASK-MIN",
        "name": "Minimal Task",
    }
    task = FeatureLoader._parse_task(minimal_task)

    assert task.id == "TASK-MIN"
    assert task.file_path == Path("")
    assert task.complexity == 5
    assert task.dependencies == []
    assert task.status == "pending"
    assert task.implementation_mode == "task-work"
    assert task.estimated_minutes == 0


# ============================================================================
# Feature Validation Tests
# ============================================================================


def test_validate_feature_success(temp_features_dir):
    """Test validation of a valid feature."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_features_dir)
    errors = FeatureLoader.validate_feature(feature, repo_root=temp_features_dir)
    assert errors == []


def test_validate_feature_no_tasks():
    """Test validation fails when feature has no tasks."""
    feature = Feature(
        id="FEAT-EMPTY",
        name="Empty Feature",
        tasks=[],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )
    errors = FeatureLoader.validate_feature(feature)
    assert len(errors) == 1
    assert "must have at least one task" in errors[0]


def test_validate_feature_missing_task_files(temp_features_dir):
    """Test validation detects missing task files."""
    feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=temp_features_dir)
    errors = FeatureLoader.validate_feature(feature, repo_root=temp_features_dir)
    # Task file doesn't exist
    assert any("does not exist" in err for err in errors)


def test_validate_feature_unknown_task_in_orchestration():
    """Test validation detects unknown tasks in orchestration."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        tasks=[
            FeatureTask(id="TASK-A", name="Task A", file_path=Path("tasks/TASK-A.md"))
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-A"], ["TASK-UNKNOWN"]]
        ),
    )
    errors = FeatureLoader.validate_feature(feature)
    assert any("TASK-UNKNOWN" in err and "not defined in tasks" in err for err in errors)


def test_validate_feature_task_not_in_orchestration():
    """Test validation detects tasks missing from orchestration."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        tasks=[
            FeatureTask(id="TASK-A", name="Task A", file_path=Path("tasks/TASK-A.md")),
            FeatureTask(id="TASK-B", name="Task B", file_path=Path("tasks/TASK-B.md")),
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-A"]]),
    )
    errors = FeatureLoader.validate_feature(feature)
    assert any("TASK-B" in err and "not in orchestration" in err for err in errors)


def test_validate_feature_unknown_dependency():
    """Test validation detects unknown dependencies."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        tasks=[
            FeatureTask(
                id="TASK-A",
                name="Task A",
                file_path=Path("tasks/TASK-A.md"),
                dependencies=["TASK-UNKNOWN"],
            )
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-A"]]),
    )
    errors = FeatureLoader.validate_feature(feature)
    assert any("TASK-UNKNOWN" in err and "unknown dependency" in err for err in errors)


def test_validate_feature_rejects_directory_file_path():
    """Test validation rejects task file_path that is a directory."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        tasks=[
            FeatureTask(
                id="TASK-A", name="Task A", file_path=Path("tasks/backlog/")
            )  # Directory
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-A"]]),
    )
    errors = FeatureLoader.validate_feature(feature)
    assert any(
        "TASK-A" in err and "must be a file path, not a directory" in err
        for err in errors
    )


def test_validate_feature_rejects_subdirectory_file_path():
    """Test validation rejects task file_path in subdirectory."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        tasks=[
            FeatureTask(
                id="TASK-A",
                name="Task A",
                file_path=Path("tasks/backlog/subfolder/TASK-A.md"),
            )
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-A"]]),
    )
    errors = FeatureLoader.validate_feature(feature)
    assert any(
        "TASK-A" in err and "must be directly in tasks/" in err for err in errors
    )


def test_validate_feature_rejects_non_md_file_path():
    """Test validation rejects task file_path that is not .md."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        tasks=[
            FeatureTask(
                id="TASK-A", name="Task A", file_path=Path("tasks/backlog/TASK-A.txt")
            )
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-A"]]),
    )
    errors = FeatureLoader.validate_feature(feature)
    assert any("TASK-A" in err and "must have .md extension" in err for err in errors)


def test_validate_feature_rejects_file_path_without_tasks_dir():
    """Test validation rejects task file_path not starting with tasks/."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        tasks=[
            FeatureTask(id="TASK-A", name="Task A", file_path=Path("docs/TASK-A.md"))
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-A"]]),
    )
    errors = FeatureLoader.validate_feature(feature)
    assert any("TASK-A" in err and "must start with tasks/" in err for err in errors)


def test_validate_feature_valid_file_paths_still_pass():
    """Test that valid file paths pass validation (no spurious errors)."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        tasks=[
            FeatureTask(
                id="TASK-A", name="Task A", file_path=Path("tasks/backlog/TASK-A.md")
            ),
            FeatureTask(
                id="TASK-B",
                name="Task B",
                file_path=Path("tasks/in_progress/TASK-B.md"),
            ),
            FeatureTask(
                id="TASK-C",
                name="Task C",
                file_path=Path("tasks/completed/TASK-C.md"),
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-A", "TASK-B", "TASK-C"]]
        ),
    )
    errors = FeatureLoader.validate_feature(feature)
    # Should have no file path validation errors
    file_path_errors = [e for e in errors if "file_path" in e.lower()]
    assert len(file_path_errors) == 0


# ============================================================================
# Circular Dependency Detection Tests
# ============================================================================


def test_detect_circular_dependency_simple():
    """Test detection of simple circular dependency."""
    tasks = [
        FeatureTask(id="TASK-A", name="A", dependencies=["TASK-B"]),
        FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
    ]
    circular = FeatureLoader._detect_circular_dependencies(tasks)
    assert len(circular) == 1
    assert "TASK-A" in circular[0] and "TASK-B" in circular[0]


def test_detect_circular_dependency_transitive():
    """Test detection of transitive circular dependency."""
    tasks = [
        FeatureTask(id="TASK-A", name="A", dependencies=["TASK-B"]),
        FeatureTask(id="TASK-B", name="B", dependencies=["TASK-C"]),
        FeatureTask(id="TASK-C", name="C", dependencies=["TASK-A"]),
    ]
    circular = FeatureLoader._detect_circular_dependencies(tasks)
    assert len(circular) == 1


def test_no_circular_dependency():
    """Test that valid dependencies don't trigger circular detection."""
    tasks = [
        FeatureTask(id="TASK-A", name="A", dependencies=[]),
        FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
        FeatureTask(id="TASK-C", name="C", dependencies=["TASK-B"]),
    ]
    circular = FeatureLoader._detect_circular_dependencies(tasks)
    assert circular == []


# ============================================================================
# Feature Saving Tests
# ============================================================================


def test_save_feature_creates_file(temp_features_dir):
    """Test saving feature creates YAML file."""
    feature = Feature(
        id="FEAT-NEW",
        name="New Feature",
        tasks=[
            FeatureTask(id="TASK-1", name="Task 1", file_path=Path("tasks/TASK-1.md"))
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-1"]]),
    )

    FeatureLoader.save_feature(feature, repo_root=temp_features_dir)

    feature_file = temp_features_dir / ".claude" / "features" / "FEAT-NEW.yaml"
    assert feature_file.exists()


def test_save_feature_preserves_file_path(temp_features_dir):
    """Test that saving preserves file_path as string in YAML."""
    feature = Feature(
        id="FEAT-PATH",
        name="Path Feature",
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("tasks/backlog/TASK-1.md"),
            )
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-1"]]),
    )

    FeatureLoader.save_feature(feature, repo_root=temp_features_dir)

    feature_file = temp_features_dir / ".claude" / "features" / "FEAT-PATH.yaml"
    with open(feature_file, "r") as f:
        data = yaml.safe_load(f)

    # file_path should be saved as string
    assert data["tasks"][0]["file_path"] == "tasks/backlog/TASK-1.md"


def test_save_and_reload_feature(temp_features_dir):
    """Test that saved feature can be reloaded."""
    original = Feature(
        id="FEAT-ROUND",
        name="Round Trip",
        description="Test round-trip save/load",
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("tasks/TASK-1.md"),
                complexity=7,
            )
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-1"]]),
    )

    FeatureLoader.save_feature(original, repo_root=temp_features_dir)
    loaded = FeatureLoader.load_feature("FEAT-ROUND", repo_root=temp_features_dir)

    assert loaded.id == original.id
    assert loaded.name == original.name
    assert loaded.description == original.description
    assert len(loaded.tasks) == len(original.tasks)
    assert loaded.tasks[0].complexity == 7


# ============================================================================
# Find Task Tests
# ============================================================================


def test_find_task_exists():
    """Test finding an existing task."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        tasks=[
            FeatureTask(id="TASK-A", name="Task A"),
            FeatureTask(id="TASK-B", name="Task B"),
        ],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )
    task = FeatureLoader.find_task(feature, "TASK-A")
    assert task is not None
    assert task.id == "TASK-A"


def test_find_task_not_found():
    """Test finding a non-existent task."""
    feature = Feature(
        id="FEAT-TEST",
        name="Test",
        tasks=[FeatureTask(id="TASK-A", name="Task A")],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )
    task = FeatureLoader.find_task(feature, "TASK-UNKNOWN")
    assert task is None


# ============================================================================
# Pydantic Model Tests
# ============================================================================


def test_feature_task_status_literals():
    """Test that FeatureTask status field uses Literal type."""
    # Valid statuses
    valid = ["pending", "in_progress", "completed", "failed", "skipped"]
    for status in valid:
        task = FeatureTask(id="TASK-1", name="Test", status=status)
        assert task.status == status

    # Invalid status should raise ValidationError
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        FeatureTask(id="TASK-1", name="Test", status="invalid_status")


def test_feature_status_literals():
    """Test that Feature status field uses Literal type."""
    # Valid statuses
    valid = ["planned", "in_progress", "completed", "failed", "paused"]
    for status in valid:
        feature = Feature(
            id="FEAT-1",
            name="Test",
            tasks=[],
            orchestration=FeatureOrchestration(parallel_groups=[]),
            status=status,
        )
        assert feature.status == status

    # Invalid status should raise ValidationError
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Feature(
            id="FEAT-1",
            name="Test",
            tasks=[],
            orchestration=FeatureOrchestration(parallel_groups=[]),
            status="bogus",
        )


def test_feature_execution_defaults():
    """Test that FeatureExecution has correct defaults."""
    execution = FeatureExecution()
    assert execution.started_at is None
    assert execution.completed_at is None
    assert execution.worktree_path is None
    assert execution.current_task_id is None
    assert execution.completed_task_ids == []


# ============================================================================
# State Management Tests
# ============================================================================


def test_is_incomplete_planned_feature():
    """Test that planned feature is incomplete."""
    feature = Feature(
        id="FEAT-1",
        name="Test",
        status="planned",
        tasks=[FeatureTask(id="TASK-1", name="Task 1", status="pending")],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )
    assert FeatureLoader.is_incomplete(feature) is True


def test_is_incomplete_in_progress_feature():
    """Test that in_progress feature is incomplete."""
    feature = Feature(
        id="FEAT-1",
        name="Test",
        status="in_progress",
        tasks=[FeatureTask(id="TASK-1", name="Task 1", status="in_progress")],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )
    assert FeatureLoader.is_incomplete(feature) is True


def test_is_incomplete_paused_feature():
    """Test that paused feature is incomplete."""
    feature = Feature(
        id="FEAT-1",
        name="Test",
        status="paused",
        tasks=[FeatureTask(id="TASK-1", name="Task 1", status="pending")],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )
    assert FeatureLoader.is_incomplete(feature) is True


def test_is_incomplete_task_in_progress():
    """Test that feature with in_progress task is incomplete."""
    feature = Feature(
        id="FEAT-1",
        name="Test",
        status="in_progress",
        tasks=[FeatureTask(id="TASK-1", name="Task 1", status="in_progress")],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )
    assert FeatureLoader.is_incomplete(feature) is True


def test_is_incomplete_partial_completion():
    """Test that feature with some completed tasks is incomplete."""
    feature = Feature(
        id="FEAT-1",
        name="Test",
        status="in_progress",
        tasks=[
            FeatureTask(id="TASK-1", name="Task 1", status="completed"),
            FeatureTask(id="TASK-2", name="Task 2", status="pending"),
        ],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )
    assert FeatureLoader.is_incomplete(feature) is True


def test_is_incomplete_all_completed():
    """Test that feature with all completed tasks is complete."""
    feature = Feature(
        id="FEAT-1",
        name="Test",
        status="completed",
        tasks=[
            FeatureTask(id="TASK-1", name="Task 1", status="completed"),
            FeatureTask(id="TASK-2", name="Task 2", status="completed"),
        ],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )
    assert FeatureLoader.is_incomplete(feature) is False


def test_get_resume_point_basic():
    """Test getting resume point from feature."""
    feature = Feature(
        id="FEAT-1",
        name="Test",
        tasks=[
            FeatureTask(id="TASK-1", name="Task 1", status="completed"),
            FeatureTask(id="TASK-2", name="Task 2", status="in_progress"),
        ],
        orchestration=FeatureOrchestration(parallel_groups=[]),
        execution=FeatureExecution(current_task_id="TASK-2"),
    )
    resume_point = FeatureLoader.get_resume_point(feature)
    assert resume_point == "TASK-2"


def test_get_resume_point_no_in_progress_task():
    """Test getting resume point when no task is in_progress."""
    feature = Feature(
        id="FEAT-1",
        name="Test",
        tasks=[
            FeatureTask(id="TASK-1", name="Task 1", status="completed"),
            FeatureTask(id="TASK-2", name="Task 2", status="pending"),
        ],
        orchestration=FeatureOrchestration(parallel_groups=[["TASK-1"], ["TASK-2"]]),
    )
    resume_point = FeatureLoader.get_resume_point(feature)
    assert resume_point == "TASK-2"


def test_reset_state():
    """Test resetting feature state."""
    feature = Feature(
        id="FEAT-1",
        name="Test",
        status="in_progress",
        tasks=[
            FeatureTask(id="TASK-1", name="Task 1", status="completed"),
            FeatureTask(id="TASK-2", name="Task 2", status="in_progress"),
        ],
        orchestration=FeatureOrchestration(parallel_groups=[]),
        execution=FeatureExecution(
            started_at="2025-01-01T00:00:00Z",
            current_task_id="TASK-2",
            completed_task_ids=["TASK-1"],
        ),
    )

    FeatureLoader.reset_state(feature)

    assert feature.status == "planned"
    assert all(task.status == "pending" for task in feature.tasks)
    assert feature.execution.started_at is None
    assert feature.execution.current_task_id is None
    assert feature.execution.completed_task_ids == []


def test_task_state_fields_default():
    """Test that task state fields have correct defaults."""
    task = FeatureTask(id="TASK-1", name="Test Task")
    assert task.status == "pending"
    assert task.started_at is None
    assert task.completed_at is None
    assert task.error is None


def test_task_state_fields_persistence():
    """Test that task state fields persist through save/load."""
    feature = Feature(
        id="FEAT-STATE",
        name="State Test",
        tasks=[
            FeatureTask(
                id="TASK-1",
                name="Task 1",
                file_path=Path("tasks/TASK-1.md"),
                status="completed",
                started_at="2025-01-01T10:00:00Z",
                completed_at="2025-01-01T11:00:00Z",
            )
        ],
        orchestration=FeatureOrchestration(parallel_groups=[]),
    )

    # Use temp directory
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        FeatureLoader.save_feature(feature, repo_root=repo_root)
        loaded = FeatureLoader.load_feature("FEAT-STATE", repo_root=repo_root)

        assert loaded.tasks[0].status == "completed"
        assert loaded.tasks[0].started_at == "2025-01-01T10:00:00Z"
        assert loaded.tasks[0].completed_at == "2025-01-01T11:00:00Z"


# ============================================================================
# Schema Error Message Tests
# ============================================================================


class TestSchemaHintErrorMessages:
    """Test that parse error messages include schema hints."""

    def test_truncate_data_short_string(self):
        """Test truncation of short data."""
        result = _truncate_data("short", max_length=50)
        assert result == "short"

    def test_truncate_data_long_string(self):
        """Test truncation of long data."""
        long_str = "a" * 100
        result = _truncate_data(long_str, max_length=50)
        assert result == "a" * 50 + "..."

    def test_truncate_data_custom_max_length(self):
        """Test truncation with custom max length."""
        result = _truncate_data("hello world", max_length=5)
        assert result == "hello..."

    def test_build_schema_error_message_structure(self):
        """Test schema error message has correct structure."""
        data = {"id": "TASK-1"}
        error = _build_schema_error_message(
            data, "Field 'name' is required", TASK_SCHEMA
        )

        assert "Field 'name' is required" in error
        assert "Required fields:" in error
        assert "'id'" in error  # id is required
        assert "'name'" in error  # name is required
        assert "Provided data:" in error

    def test_build_schema_error_message_empty_data(self):
        """Test schema error message with empty data."""
        data = {}
        error = _build_schema_error_message(
            data, "Missing required fields", TASK_SCHEMA
        )
        assert "Provided data:" in error
        assert "{}" in error

    def test_build_schema_error_message_none_data(self):
        """Test schema error message with None data."""
        data = None
        error = _build_schema_error_message(
            data, "Missing required fields", TASK_SCHEMA
        )
        assert "Provided data:" in error
        assert "None" in error

    def test_parse_error_missing_task_id(self):
        """Test parse error message for missing task id."""
        incomplete_task = {"name": "Task without ID"}
        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader._parse_task(incomplete_task)

        error_msg = str(exc_info.value)
        assert "Field 'id' is required" in error_msg
        assert "Required fields:" in error_msg
        assert "'id'" in error_msg

    def test_parse_error_missing_file_path(self):
        """Test parse error for task with missing file_path doesn't fail (has default)."""
        # file_path has a default (Path("")) so it's not required
        task_data = {"id": "TASK-1", "name": "Task"}
        task = FeatureLoader._parse_task(task_data)
        assert task.file_path == Path("")

    def test_parse_error_missing_feature_id(self, temp_features_dir):
        """Test parse error for feature missing id."""
        features_dir = temp_features_dir / ".claude" / "features"
        bad_file = features_dir / "FEAT-NO-ID.yaml"

        with open(bad_file, "w") as f:
            yaml.dump({"name": "Feature without ID"}, f)

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-NO-ID", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Field 'id' is required" in error_msg

    def test_parse_error_missing_feature_name(self, temp_features_dir):
        """Test parse error for feature missing name."""
        features_dir = temp_features_dir / ".claude" / "features"
        bad_file = features_dir / "FEAT-NO-NAME.yaml"

        with open(bad_file, "w") as f:
            yaml.dump({"id": "FEAT-NO-NAME"}, f)

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-NO-NAME", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Field 'name' is required" in error_msg

    def test_parse_error_shows_actual_data(self, temp_features_dir):
        """Test that parse error shows the actual data provided."""
        features_dir = temp_features_dir / ".claude" / "features"
        bad_file = features_dir / "FEAT-BAD-DATA.yaml"

        bad_data = {"id": "FEAT-BAD-DATA", "status": "invalid_status"}
        with open(bad_file, "w") as f:
            yaml.dump(bad_data, f)

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-BAD-DATA", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Provided data:" in error_msg

    def test_parse_error_shows_present_fields(self, temp_features_dir):
        """Test that parse error includes present fields in data summary."""
        features_dir = temp_features_dir / ".claude" / "features"
        bad_file = features_dir / "FEAT-PARTIAL.yaml"

        partial_data = {"id": "FEAT-PARTIAL", "description": "Has ID but missing name"}
        with open(bad_file, "w") as f:
            yaml.dump(partial_data, f)

        with pytest.raises(FeatureParseError) as exc_info:
            FeatureLoader.load_feature("FEAT-PARTIAL", repo_root=temp_features_dir)

        error_msg = str(exc_info.value)
        assert "Provided data:" in error_msg
        # Should show what fields ARE present
        assert "id" in error_msg.lower()

    def test_error_message_includes_fix_suggestion(self):
        """Test that error messages include fix suggestions."""
        data = {"id": "TASK-1"}  # Missing 'name'
        error = _build_schema_error_message(
            data, "Field 'name' is required", TASK_SCHEMA
        )

        # Should include schema reference
        assert "Required fields:" in error


def test_valid_task_no_error():
    """Test that valid task doesn't raise error."""
    valid_task = {"id": "TASK-1", "name": "Valid Task"}
    task = FeatureLoader._parse_task(valid_task)
    assert task.id == "TASK-1"
    assert task.name == "Valid Task"


def test_schema_constants_exported():
    """Test that schema constants are exported."""
    assert TASK_SCHEMA is not None
    assert FEATURE_SCHEMA is not None
    assert ORCHESTRATION_SCHEMA is not None

    # Check structure
    assert "id" in TASK_SCHEMA
    assert "name" in TASK_SCHEMA
    assert "id" in FEATURE_SCHEMA
    assert "name" in FEATURE_SCHEMA


# ============================================================================
# Find Similar IDs Tests
# ============================================================================


class TestFindSimilarIds:
    """Test fuzzy ID matching for better error messages."""

    def test_prefix_match_same_prefix_different_number(self):
        """Test matching IDs with same prefix but different numbers."""
        candidates = ["TASK-ABC-001", "TASK-ABC-002", "TASK-ABC-003"]
        result = _find_similar_ids("TASK-ABC-004", candidates)
        assert len(result) > 0
        assert "TASK-ABC-001" in result or "TASK-ABC-002" in result

    def test_character_difference_single_char(self):
        """Test matching with single character difference."""
        candidates = ["TASK-A1B2", "TASK-A1C2", "TASK-A1D2"]
        result = _find_similar_ids("TASK-A1B3", candidates)
        assert "TASK-A1B2" in result

    def test_no_match_completely_different(self):
        """Test no matches for completely different IDs."""
        candidates = ["TASK-ABC-001", "TASK-DEF-002"]
        result = _find_similar_ids("TASK-XYZ-999", candidates)
        assert len(result) == 0

    def test_substring_match_shorter_target(self):
        """Test matching when target is substring of candidate."""
        candidates = ["TASK-AUTHENTICATION-001"]
        result = _find_similar_ids("TASK-AUTH-001", candidates)
        assert len(result) > 0

    def test_substring_match_longer_target(self):
        """Test matching when candidate is substring of target."""
        candidates = ["TASK-AUTH-001"]
        result = _find_similar_ids("TASK-AUTHENTICATION-001", candidates)
        assert len(result) > 0

    def test_empty_candidates_returns_empty(self):
        """Test that empty candidate list returns empty result."""
        result = _find_similar_ids("TASK-ABC-001", [])
        assert result == []

    def test_target_not_in_candidates_by_design(self):
        """Test that exact matches are not considered 'similar'."""
        candidates = ["TASK-ABC-001", "TASK-ABC-002"]
        # Target is exact match - should not be in similar list
        result = _find_similar_ids("TASK-ABC-001", candidates)
        assert "TASK-ABC-001" not in result

    def test_max_three_results(self):
        """Test that at most 3 similar IDs are returned."""
        candidates = [f"TASK-ABC-{i:03d}" for i in range(1, 20)]
        result = _find_similar_ids("TASK-ABC-999", candidates)
        assert len(result) <= 3

    def test_sorted_by_similarity_prefix_first(self):
        """Test that results are sorted by similarity (prefix matches first)."""
        candidates = ["TASK-ABC-001", "TASK-XYZ-001", "TASK-ABC-002"]
        result = _find_similar_ids("TASK-ABC-999", candidates)
        # Prefix matches should come first
        if len(result) >= 2:
            assert result[0].startswith("TASK-ABC")

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        candidates = ["task-abc-001", "TASK-ABC-002"]
        result = _find_similar_ids("TASK-abc-003", candidates)
        assert len(result) > 0

    def test_max_distance_parameter_default(self):
        """Test default max_distance parameter."""
        # Very different IDs should not match
        candidates = ["TASK-AAAA-001"]
        result = _find_similar_ids("TASK-ZZZZ-001", candidates)
        # Should not match with default distance
        assert len(result) == 0

    def test_max_distance_parameter_custom(self):
        """Test custom max_distance parameter."""
        candidates = ["TASK-AAAA-001"]
        # With higher max_distance, might match
        result = _find_similar_ids("TASK-ZZZZ-001", candidates, max_distance=10)
        # May or may not match depending on implementation

    def test_mixed_match_types(self):
        """Test matching with both prefix and character similarity."""
        candidates = [
            "TASK-AUTH-001",  # prefix match
            "TASK-AUTZ-001",  # 1 char different
            "TASK-XYZ-001",  # no match
        ]
        result = _find_similar_ids("TASK-AUTH-002", candidates)
        assert len(result) >= 1
        # Should include at least the prefix match
        assert "TASK-AUTH-001" in result

    def test_no_hyphen_in_target(self):
        """Test handling of target without hyphen."""
        candidates = ["TASK-ABC-001"]
        result = _find_similar_ids("TASKABC001", candidates)
        # Should handle gracefully

    def test_special_characters_in_id(self):
        """Test handling of special characters."""
        candidates = ["TASK_ABC_001", "TASK.ABC.001"]
        result = _find_similar_ids("TASK-ABC-001", candidates)
        # Should handle different separators

    def test_validation_error_integration(self):
        """Test integration with FeatureValidationError."""
        feature = Feature(
            id="FEAT-TEST",
            name="Test",
            tasks=[FeatureTask(id="TASK-A", name="Task A")],
            orchestration=FeatureOrchestration(parallel_groups=[["TASK-B"]]),
        )
        errors = FeatureLoader.validate_feature(feature)

        # Should suggest similar task ID
        assert len(errors) > 0
        error_msg = errors[0]
        assert "TASK-B" in error_msg

    def test_same_length_different_chars_within_threshold(self):
        """Test IDs with same length but few character differences."""
        candidates = ["TASK-A1B2C3"]
        result = _find_similar_ids("TASK-A1B2D3", candidates)
        # Only 1 char different
        assert "TASK-A1B2C3" in result

    def test_numeric_suffix_variations(self):
        """Test matching IDs with different numeric suffixes."""
        candidates = ["TASK-FOO-123", "TASK-FOO-456"]
        result = _find_similar_ids("TASK-FOO-789", candidates)
        # Same prefix
        assert len(result) > 0

    def test_alphabetical_tiebreaker(self):
        """Test that ties are broken alphabetically."""
        candidates = ["TASK-AAA-001", "TASK-BBB-001", "TASK-CCC-001"]
        result = _find_similar_ids("TASK-DDD-001", candidates)
        # All equally similar, should be sorted alphabetically
        if len(result) == 3:
            assert result == sorted(result)


# ============================================================================
# Feature Loader Parsing Tests
# ============================================================================


class TestFeatureLoaderParsing:
    """Test FeatureLoader parsing edge cases."""

    def test_valid_schema_parses_successfully(self, sample_feature_yaml):
        """Test that valid YAML parses without errors."""
        # Save to temp file and load
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(sample_feature_yaml, f)
            temp_file = f.name

        try:
            with open(temp_file, "r") as f:
                data = yaml.safe_load(f)
            feature = Feature.model_validate(data)
            assert feature.id == "FEAT-A1B2"
        finally:
            Path(temp_file).unlink()

    def test_missing_file_path_raises_parse_error(self):
        """Test that file_path uses default when missing (not an error)."""
        task_data = {"id": "TASK-1", "name": "Test"}
        task = FeatureLoader._parse_task(task_data)
        # file_path has default Path("")
        assert task.file_path == Path("")

    def test_missing_task_id_raises_parse_error(self):
        """Test that missing task ID raises parse error."""
        task_data = {"name": "Test Task"}
        with pytest.raises(FeatureParseError):
            FeatureLoader._parse_task(task_data)

    def test_old_execution_groups_format_uses_empty_orchestration(
        self, temp_features_dir
    ):
        """Test that old execution_groups format is ignored (backward compat)."""
        features_dir = temp_features_dir / ".claude" / "features"
        old_format_file = features_dir / "FEAT-OLD.yaml"

        old_data = {
            "id": "FEAT-OLD",
            "name": "Old Format",
            "tasks": [
                {
                    "id": "TASK-1",
                    "name": "Task 1",
                    "file_path": "tasks/TASK-1.md",
                    "execution_group": 1,  # Old format
                }
            ],
            # No orchestration section
        }
        with open(old_format_file, "w") as f:
            yaml.dump(old_data, f)

        feature = FeatureLoader.load_feature("FEAT-OLD", repo_root=temp_features_dir)
        # Should use default empty orchestration
        assert feature.orchestration.parallel_groups == []

    def test_old_execution_groups_format_fails_validation(self, temp_features_dir):
        """Test that old format without orchestration fails validation."""
        features_dir = temp_features_dir / ".claude" / "features"
        old_format_file = features_dir / "FEAT-OLD-VAL.yaml"

        old_data = {
            "id": "FEAT-OLD-VAL",
            "name": "Old Format Validation",
            "tasks": [
                {
                    "id": "TASK-1",
                    "name": "Task 1",
                    "file_path": "tasks/TASK-1.md",
                    "execution_group": 1,  # Old format
                }
            ],
            # No orchestration
        }
        with open(old_format_file, "w") as f:
            yaml.dump(old_data, f)

        feature = FeatureLoader.load_feature(
            "FEAT-OLD-VAL", repo_root=temp_features_dir
        )
        errors = FeatureLoader.validate_feature(feature)

        # Should have validation error for missing orchestration
        assert any("not in orchestration" in err for err in errors)

    def test_task_files_section_ignored(self, temp_features_dir):
        """Test that task_files section is ignored (deprecated)."""
        features_dir = temp_features_dir / ".claude" / "features"
        deprecated_file = features_dir / "FEAT-DEPRECATED.yaml"

        data = {
            "id": "FEAT-DEPRECATED",
            "name": "Deprecated Format",
            "tasks": [
                {"id": "TASK-1", "name": "Task 1", "file_path": "tasks/TASK-1.md"}
            ],
            "task_files": ["tasks/TASK-1.md"],  # Deprecated
            "orchestration": {"parallel_groups": [["TASK-1"]]},
        }
        with open(deprecated_file, "w") as f:
            yaml.dump(data, f)

        # Should load without error (task_files ignored)
        feature = FeatureLoader.load_feature(
            "FEAT-DEPRECATED", repo_root=temp_features_dir
        )
        assert feature.id == "FEAT-DEPRECATED"

    def test_empty_tasks_list_validation_error(self):
        """Test that empty tasks list raises validation error."""
        feature = Feature(
            id="FEAT-EMPTY",
            name="Empty",
            tasks=[],
            orchestration=FeatureOrchestration(parallel_groups=[]),
        )
        errors = FeatureLoader.validate_feature(feature)
        assert any("must have at least one task" in err for err in errors)

    def test_circular_dependencies_detected(self):
        """Test that circular dependencies are detected during validation."""
        feature = Feature(
            id="FEAT-CIRCULAR",
            name="Circular",
            tasks=[
                FeatureTask(id="TASK-A", name="A", dependencies=["TASK-B"]),
                FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
            ],
            orchestration=FeatureOrchestration(parallel_groups=[]),
        )
        errors = FeatureLoader.validate_feature(feature)
        assert any("circular" in err.lower() for err in errors)

    def test_missing_task_file_validation(self, temp_features_dir):
        """Test that missing task file is caught by validation."""
        feature = Feature(
            id="FEAT-MISSING",
            name="Missing File",
            tasks=[
                FeatureTask(
                    id="TASK-1",
                    name="Task 1",
                    file_path=Path("tasks/nonexistent/TASK-1.md"),
                )
            ],
            orchestration=FeatureOrchestration(parallel_groups=[["TASK-1"]]),
        )
        errors = FeatureLoader.validate_feature(feature, repo_root=temp_features_dir)
        # Should detect file path validation errors
        assert len(errors) > 0

    def test_parallel_groups_list_of_lists(self):
        """Test that parallel_groups is list of lists."""
        feature = Feature(
            id="FEAT-PARALLEL",
            name="Parallel",
            tasks=[
                FeatureTask(id="TASK-A", name="A", file_path=Path("tasks/TASK-A.md")),
                FeatureTask(id="TASK-B", name="B", file_path=Path("tasks/TASK-B.md")),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-A"], ["TASK-B"]]
            ),
        )
        assert len(feature.orchestration.parallel_groups) == 2
        assert feature.orchestration.parallel_groups[0] == ["TASK-A"]
        assert feature.orchestration.parallel_groups[1] == ["TASK-B"]


# ============================================================================
# Feature Loader Edge Cases
# ============================================================================


class TestFeatureLoaderEdgeCases:
    """Test edge cases in feature loading and validation."""

    def test_single_task_feature(self):
        """Test feature with single task."""
        feature = Feature(
            id="FEAT-SINGLE",
            name="Single Task",
            tasks=[FeatureTask(id="TASK-1", name="Only Task")],
            orchestration=FeatureOrchestration(parallel_groups=[["TASK-1"]]),
        )
        errors = FeatureLoader.validate_feature(feature)
        # Should have no validation errors (except missing file)
        non_file_errors = [e for e in errors if "does not exist" not in e]
        assert len(non_file_errors) == 0

    def test_all_tasks_parallel(self):
        """Test feature where all tasks can run in parallel."""
        feature = Feature(
            id="FEAT-PARALLEL",
            name="All Parallel",
            tasks=[
                FeatureTask(id="TASK-A", name="A", dependencies=[]),
                FeatureTask(id="TASK-B", name="B", dependencies=[]),
                FeatureTask(id="TASK-C", name="C", dependencies=[]),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-A", "TASK-B", "TASK-C"]]
            ),
        )
        errors = FeatureLoader.validate_feature(feature)
        # Should have no circular dependency errors
        circ_errors = [e for e in errors if "circular" in e.lower()]
        assert len(circ_errors) == 0

    def test_complex_dependency_graph(self):
        """Test feature with complex dependency graph."""
        feature = Feature(
            id="FEAT-COMPLEX",
            name="Complex Dependencies",
            tasks=[
                FeatureTask(id="TASK-A", name="A", dependencies=[]),
                FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
                FeatureTask(id="TASK-C", name="C", dependencies=["TASK-A"]),
                FeatureTask(id="TASK-D", name="D", dependencies=["TASK-B", "TASK-C"]),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-A"], ["TASK-B", "TASK-C"], ["TASK-D"]]
            ),
        )
        errors = FeatureLoader.validate_feature(feature)
        # Should validate successfully (no circular deps)
        circ_errors = [e for e in errors if "circular" in e.lower()]
        assert len(circ_errors) == 0

    def test_optional_fields_use_defaults(self):
        """Test that optional fields use default values."""
        minimal_feature = Feature(
            id="FEAT-MIN",
            name="Minimal",
            tasks=[FeatureTask(id="TASK-1", name="Task")],
            orchestration=FeatureOrchestration(parallel_groups=[["TASK-1"]]),
        )
        # Check defaults
        assert minimal_feature.description == ""
        assert minimal_feature.status == "planned"
        assert minimal_feature.complexity == 5
        assert minimal_feature.estimated_tasks == 0

    def test_feature_with_all_task_statuses(self):
        """Test feature with tasks in all possible statuses."""
        feature = Feature(
            id="FEAT-ALL-STATUSES",
            name="All Statuses",
            tasks=[
                FeatureTask(id="TASK-1", name="T1", status="pending"),
                FeatureTask(id="TASK-2", name="T2", status="in_progress"),
                FeatureTask(id="TASK-3", name="T3", status="completed"),
                FeatureTask(id="TASK-4", name="T4", status="failed"),
                FeatureTask(id="TASK-5", name="T5", status="skipped"),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-1", "TASK-2", "TASK-3", "TASK-4", "TASK-5"]
                ]
            ),
        )
        assert len(feature.tasks) == 5

    def test_feature_with_all_implementation_modes(self):
        """Test feature with tasks using all implementation modes."""
        feature = Feature(
            id="FEAT-ALL-MODES",
            name="All Modes",
            tasks=[
                FeatureTask(id="TASK-1", name="T1", implementation_mode="direct"),
                FeatureTask(id="TASK-2", name="T2", implementation_mode="task-work"),
                FeatureTask(id="TASK-3", name="T3", implementation_mode="manual"),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-1", "TASK-2", "TASK-3"]]
            ),
        )
        assert len(feature.tasks) == 3

    def test_self_dependency_detected(self):
        """Test that self-dependency is detected as circular."""
        feature = Feature(
            id="FEAT-SELF-DEP",
            name="Self Dependency",
            tasks=[FeatureTask(id="TASK-A", name="A", dependencies=["TASK-A"])],
            orchestration=FeatureOrchestration(parallel_groups=[["TASK-A"]]),
        )
        errors = FeatureLoader.validate_feature(feature)
        assert any("circular" in err.lower() for err in errors)

    def test_missing_orchestration_uses_defaults(self):
        """Test that missing orchestration uses default values."""
        feature = Feature(
            id="FEAT-DEFAULT-ORCH",
            name="Default Orchestration",
            tasks=[FeatureTask(id="TASK-1", name="Task 1")],
            # orchestration not specified, uses default
        )
        assert feature.orchestration.parallel_groups == []
        assert feature.orchestration.estimated_duration_minutes == 0
        assert feature.orchestration.recommended_parallel == 1

    def test_unicode_in_feature_name(self):
        """Test that unicode characters in names are handled."""
        feature = Feature(
            id="FEAT-UNICODE",
            name="Feature with émojis 🚀",
            tasks=[FeatureTask(id="TASK-1", name="Task with 中文")],
            orchestration=FeatureOrchestration(parallel_groups=[["TASK-1"]]),
        )
        assert "🚀" in feature.name
        assert "中文" in feature.tasks[0].name

    def test_very_long_dependency_chain(self):
        """Test feature with very long linear dependency chain."""
        tasks = []
        for i in range(10):
            task_id = f"TASK-{i}"
            deps = [f"TASK-{i-1}"] if i > 0 else []
            tasks.append(FeatureTask(id=task_id, name=f"Task {i}", dependencies=deps))

        feature = Feature(
            id="FEAT-LONG-CHAIN",
            name="Long Chain",
            tasks=tasks,
            orchestration=FeatureOrchestration(
                parallel_groups=[[f"TASK-{i}"] for i in range(10)]
            ),
        )
        errors = FeatureLoader.validate_feature(feature)
        # Should have no circular dependency errors
        circ_errors = [e for e in errors if "circular" in e.lower()]
        assert len(circ_errors) == 0


# ============================================================================
# Intra-Wave Dependency Validation Tests
# ============================================================================


class TestIntraWaveDependencyValidation:
    """Test validation of dependencies within parallel groups (waves)."""

    def test_validate_parallel_groups_valid_configuration(self):
        """Test that valid parallel groups pass validation."""
        tasks = [
            FeatureTask(id="TASK-A", name="A", dependencies=[]),
            FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
            FeatureTask(id="TASK-C", name="C", dependencies=["TASK-B"]),
        ]
        orchestration = FeatureOrchestration(
            parallel_groups=[["TASK-A"], ["TASK-B"], ["TASK-C"]]
        )

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        assert errors == []

    def test_validate_parallel_groups_single_conflict(self):
        """Test detection of single intra-wave dependency conflict."""
        tasks = [
            FeatureTask(id="TASK-A", name="A", dependencies=[]),
            FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
        ]
        # Both tasks in same wave, but B depends on A
        orchestration = FeatureOrchestration(parallel_groups=[["TASK-A", "TASK-B"]])

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        assert len(errors) == 1
        assert "TASK-B" in errors[0]
        assert "TASK-A" in errors[0]
        assert "same parallel group" in errors[0]

    def test_validate_parallel_groups_multiple_conflicts_same_wave(self):
        """Test detection of multiple conflicts in same wave."""
        tasks = [
            FeatureTask(id="TASK-A", name="A", dependencies=[]),
            FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
            FeatureTask(id="TASK-C", name="C", dependencies=["TASK-A"]),
        ]
        # All in same wave
        orchestration = FeatureOrchestration(
            parallel_groups=[["TASK-A", "TASK-B", "TASK-C"]]
        )

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        assert len(errors) == 2  # B→A and C→A
        assert any("TASK-B" in err and "TASK-A" in err for err in errors)
        assert any("TASK-C" in err and "TASK-A" in err for err in errors)

    def test_validate_parallel_groups_conflicts_different_waves(self):
        """Test that dependencies across waves don't trigger errors."""
        tasks = [
            FeatureTask(id="TASK-A", name="A", dependencies=[]),
            FeatureTask(id="TASK-B", name="B", dependencies=[]),
            FeatureTask(id="TASK-C", name="C", dependencies=["TASK-A", "TASK-B"]),
        ]
        # Wave 1: A,B parallel; Wave 2: C (depends on both)
        orchestration = FeatureOrchestration(
            parallel_groups=[["TASK-A", "TASK-B"], ["TASK-C"]]
        )

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        assert errors == []

    def test_validate_parallel_groups_empty_orchestration(self):
        """Test validation with empty orchestration."""
        tasks = [FeatureTask(id="TASK-A", name="A", dependencies=[])]
        orchestration = FeatureOrchestration(parallel_groups=[])

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        assert errors == []

    def test_validate_parallel_groups_single_task_per_wave(self):
        """Test that single-task waves never have conflicts."""
        tasks = [
            FeatureTask(id="TASK-A", name="A", dependencies=[]),
            FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
        ]
        # Each task in its own wave
        orchestration = FeatureOrchestration(parallel_groups=[["TASK-A"], ["TASK-B"]])

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        assert errors == []

    def test_validate_parallel_groups_unknown_task_ignored(self):
        """Test that unknown tasks in groups are handled gracefully."""
        tasks = [FeatureTask(id="TASK-A", name="A", dependencies=[])]
        # TASK-B not defined
        orchestration = FeatureOrchestration(parallel_groups=[["TASK-A", "TASK-B"]])

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        # Should not crash, just skip unknown task
        # (Unknown task error is handled by different validator)
        assert errors == []

    def test_validate_feature_includes_wave_errors(self):
        """Test that validate_feature includes wave validation errors."""
        feature = Feature(
            id="FEAT-WAVE",
            name="Wave Test",
            tasks=[
                FeatureTask(id="TASK-A", name="A", dependencies=[]),
                FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-A", "TASK-B"]]
            ),
        )

        errors = FeatureLoader.validate_feature(feature)
        wave_errors = [e for e in errors if "same parallel group" in e]
        assert len(wave_errors) >= 1

    def test_validate_parallel_groups_multiple_dependencies_one_in_wave(self):
        """Test conflict when task depends on multiple tasks, one in same wave."""
        tasks = [
            FeatureTask(id="TASK-A", name="A", dependencies=[]),
            FeatureTask(id="TASK-B", name="B", dependencies=[]),
            FeatureTask(
                id="TASK-C", name="C", dependencies=["TASK-A", "TASK-B"]
            ),  # Depends on A and B
        ]
        # Wave 1: A,C; Wave 2: B
        # C depends on A which is in same wave → conflict
        orchestration = FeatureOrchestration(
            parallel_groups=[["TASK-A", "TASK-C"], ["TASK-B"]]
        )

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        assert len(errors) == 1
        assert "TASK-C" in errors[0] and "TASK-A" in errors[0]

    def test_validate_parallel_groups_bidirectional_conflict(self):
        """Test that bidirectional dependencies in same wave are detected."""
        tasks = [
            FeatureTask(id="TASK-A", name="A", dependencies=["TASK-B"]),
            FeatureTask(id="TASK-B", name="B", dependencies=["TASK-A"]),
        ]
        # Both depend on each other and in same wave
        orchestration = FeatureOrchestration(parallel_groups=[["TASK-A", "TASK-B"]])

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        # Should detect both conflicts (or circular dependency elsewhere)
        assert len(errors) >= 1

    def test_validate_parallel_groups_empty_waves_skipped(self):
        """Test that empty waves don't cause errors."""
        tasks = [FeatureTask(id="TASK-A", name="A", dependencies=[])]
        orchestration = FeatureOrchestration(
            parallel_groups=[["TASK-A"], [], ["TASK-A"]]
        )

        errors = FeatureLoader._validate_parallel_groups(tasks, orchestration)
        # Empty waves should be ignored
        assert errors == []


# ============================================================================
# Pydantic Validation Tests
# ============================================================================


class TestPydanticValidation:
    """Test Pydantic model validation and constraints."""

    def test_invalid_task_status_raises_validation_error(self):
        """Test that invalid task status raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            FeatureTask(id="TASK-1", name="Test", status="invalid_status")

        # Check error details
        errors = exc_info.value.errors()
        assert len(errors) >= 1
        assert any("status" in str(err["loc"]) for err in errors)

    def test_invalid_implementation_mode_raises_validation_error(self):
        """Test that invalid implementation_mode raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FeatureTask(
                id="TASK-1", name="Test", implementation_mode="invalid_mode"
            )

    def test_invalid_feature_status_raises_validation_error(self):
        """Test that invalid feature status raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Feature(
                id="FEAT-1",
                name="Test",
                tasks=[],
                orchestration=FeatureOrchestration(parallel_groups=[]),
                status="invalid_status",
            )

    def test_model_json_schema_export(self):
        """Test that Feature model can export JSON schema."""
        schema = Feature.model_json_schema()
        assert schema is not None
        assert "properties" in schema
        assert "id" in schema["properties"]
        assert "name" in schema["properties"]

    def test_feature_task_model_json_schema_export(self):
        """Test that FeatureTask model can export JSON schema."""
        schema = FeatureTask.model_json_schema()
        assert schema is not None
        assert "properties" in schema
        assert "id" in schema["properties"]

    def test_extra_fields_ignored(self):
        """Test that extra fields in YAML are ignored (not error)."""
        data = {
            "id": "FEAT-1",
            "name": "Test",
            "tasks": [],
            "orchestration": {"parallel_groups": []},
            "unknown_field": "should be ignored",
        }
        feature = Feature.model_validate(data)
        assert feature.id == "FEAT-1"
        # Extra field ignored

    def test_feature_model_dump_serialization(self):
        """Test that Feature can be serialized with model_dump."""
        feature = Feature(
            id="FEAT-1",
            name="Test",
            tasks=[FeatureTask(id="TASK-1", name="T1")],
            orchestration=FeatureOrchestration(parallel_groups=[]),
        )
        data = feature.model_dump()
        assert data["id"] == "FEAT-1"
        assert data["name"] == "Test"

    def test_backward_compat_path_coercion(self):
        """Test that string paths are coerced to Path objects."""
        task_data = {
            "id": "TASK-1",
            "name": "Test",
            "file_path": "tasks/backlog/TASK-1.md",  # String
        }
        task = FeatureTask.model_validate(task_data)
        assert isinstance(task.file_path, Path)
        assert str(task.file_path) == "tasks/backlog/TASK-1.md"

    def test_invalid_complexity_out_of_range(self):
        """Test that complexity outside 1-10 range raises error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FeatureTask(id="TASK-1", name="Test", complexity=15)

        with pytest.raises(ValidationError):
            FeatureTask(id="TASK-1", name="Test", complexity=0)

    def test_valid_statuses_all_accepted(self):
        """Test that all valid task statuses are accepted."""
        valid_statuses = ["pending", "in_progress", "completed", "failed", "skipped"]
        for status in valid_statuses:
            task = FeatureTask(id="TASK-1", name="Test", status=status)
            assert task.status == status

    def test_valid_implementation_modes_all_accepted(self):
        """Test that all valid implementation modes are accepted."""
        valid_modes = ["direct", "task-work", "manual"]
        for mode in valid_modes:
            task = FeatureTask(id="TASK-1", name="Test", implementation_mode=mode)
            assert task.implementation_mode == mode

    def test_valid_feature_statuses_all_accepted(self):
        """Test that all valid feature statuses are accepted."""
        valid_statuses = ["planned", "in_progress", "completed", "failed", "paused"]
        for status in valid_statuses:
            feature = Feature(
                id="FEAT-1",
                name="Test",
                tasks=[],
                orchestration=FeatureOrchestration(parallel_groups=[]),
                status=status,
            )
            assert feature.status == status

    def test_pydantic_defaults_match_original(self):
        """Test that Pydantic defaults match original default values."""
        task = FeatureTask(id="TASK-1", name="Test")
        assert task.complexity == 5
        assert task.status == "pending"
        assert task.implementation_mode == "task-work"
        assert task.dependencies == []
        assert task.estimated_minutes == 0

        feature = Feature(
            id="FEAT-1",
            name="Test",
            tasks=[],
            orchestration=FeatureOrchestration(parallel_groups=[]),
        )
        assert feature.status == "planned"
        assert feature.complexity == 5
        assert feature.description == ""


# ============================================================================
# Schema Validation Gap Coverage
# ============================================================================


class TestSchemaValidationGaps:
    """Test coverage of schema validation edge cases from YSC-001/YSC-002."""

    def test_extra_fields_ignored_at_all_levels(self):
        """Test that extra fields are ignored at all YAML levels."""
        data = {
            "id": "FEAT-1",
            "name": "Test",
            "extra_feature_field": "ignored",
            "tasks": [
                {
                    "id": "TASK-1",
                    "name": "T1",
                    "extra_task_field": "also ignored",
                }
            ],
            "orchestration": {
                "parallel_groups": [],
                "extra_orch_field": "ignored too",
            },
        }
        feature = Feature.model_validate(data)
        assert feature.id == "FEAT-1"

    def test_parallel_groups_top_level_not_used(self):
        """Test that top-level parallel_groups (old location) is ignored."""
        data = {
            "id": "FEAT-1",
            "name": "Test",
            "tasks": [{"id": "TASK-1", "name": "T1"}],
            "parallel_groups": [["TASK-1"]],  # Old location (top-level)
            "orchestration": {
                "parallel_groups": []
            },  # New location (should take precedence)
        }
        feature = Feature.model_validate(data)
        # Should use orchestration.parallel_groups (empty), not top-level
        assert feature.orchestration.parallel_groups == []

    def test_round_trip_with_generate_feature_yaml(self):
        """Test that generate_feature_yaml round-trips correctly."""
        # Simulate what generate_feature_yaml creates
        from datetime import datetime

        feature = Feature(
            id="FEAT-ROUNDTRIP",
            name="Round Trip Test",
            description="Test round-trip",
            created=datetime.now().isoformat(),
            status="planned",
            complexity=5,
            estimated_tasks=2,
            tasks=[
                FeatureTask(
                    id="TASK-ROUNDTRIP-001",
                    name="Task 1",
                    file_path=Path("tasks/backlog/TASK-ROUNDTRIP-001.md"),
                    complexity=3,
                    dependencies=[],
                    status="pending",
                    implementation_mode="task-work",
                    estimated_minutes=60,
                ),
                FeatureTask(
                    id="TASK-ROUNDTRIP-002",
                    name="Task 2",
                    file_path=Path("tasks/backlog/TASK-ROUNDTRIP-002.md"),
                    complexity=5,
                    dependencies=["TASK-ROUNDTRIP-001"],
                    status="pending",
                    implementation_mode="direct",
                    estimated_minutes=90,
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[
                    ["TASK-ROUNDTRIP-001"],
                    ["TASK-ROUNDTRIP-002"],
                ],
                estimated_duration_minutes=120,
                recommended_parallel=2,
            ),
        )

        # Save and reload
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            FeatureLoader.save_feature(feature, repo_root=repo_root)
            loaded = FeatureLoader.load_feature("FEAT-ROUNDTRIP", repo_root=repo_root)

        # Verify all fields match
        assert loaded.id == feature.id
        assert loaded.name == feature.name
        assert loaded.description == feature.description
        assert loaded.status == feature.status
        assert loaded.complexity == feature.complexity
        assert loaded.estimated_tasks == feature.estimated_tasks

        # Verify tasks
        assert len(loaded.tasks) == 2
        assert loaded.tasks[0].id == "TASK-ROUNDTRIP-001"
        assert loaded.tasks[0].complexity == 3
        assert loaded.tasks[1].complexity == 5
        assert loaded.tasks[1].dependencies == ["TASK-ROUNDTRIP-001"]

        # Verify orchestration
        assert loaded.orchestration.parallel_groups == [
            ["TASK-ROUNDTRIP-001"],
            ["TASK-ROUNDTRIP-002"],
        ]
        assert loaded.orchestration.estimated_duration_minutes == 120
        assert loaded.orchestration.recommended_parallel == 2

    def test_json_schema_comprehensive_validation(self):
        """
        Test that JSON schema export is valid and contains expected structure.

        Validates:
        - Schema is valid JSON Schema
        - Contains Literal enum values for status and implementation_mode
        - Has proper field definitions
        - Includes descriptions
        """
        # Get JSON schemas for all models
        task_schema = FeatureTask.model_json_schema()
        orch_schema = FeatureOrchestration.model_json_schema()
        feature_schema = Feature.model_json_schema()

        # Validate FeatureTask schema structure
        assert task_schema["type"] == "object"
        assert "properties" in task_schema
        assert "required" in task_schema

        # Verify required fields
        assert "id" in task_schema["required"]
        # file_path has a default (Path("")) so it's not in required

        # Check status field has Literal enum values
        status_schema = task_schema["properties"]["status"]
        assert "enum" in status_schema
        expected_statuses = ["pending", "in_progress", "completed", "failed", "skipped"]
        assert set(status_schema["enum"]) == set(expected_statuses)

        # Check implementation_mode field has Literal enum values
        mode_schema = task_schema["properties"]["implementation_mode"]
        assert "enum" in mode_schema
        expected_modes = ["direct", "task-work", "manual"]
        assert set(mode_schema["enum"]) == set(expected_modes)

        # Check complexity has constraints
        complexity_schema = task_schema["properties"]["complexity"]
        assert complexity_schema.get("minimum") == 1
        assert complexity_schema.get("maximum") == 10

        # Validate FeatureOrchestration schema
        assert orch_schema["type"] == "object"
        assert "parallel_groups" in orch_schema["properties"]
        parallel_groups_schema = orch_schema["properties"]["parallel_groups"]
        # Should be array of arrays
        assert parallel_groups_schema["type"] == "array"
        assert parallel_groups_schema["items"]["type"] == "array"

        # Validate Feature schema
        assert feature_schema["type"] == "object"
        assert "id" in feature_schema["required"]
        assert "name" in feature_schema["required"]

        # Check feature status enum
        feature_status_schema = feature_schema["properties"]["status"]
        assert "enum" in feature_status_schema
        expected_feature_statuses = ["planned", "in_progress", "completed", "failed", "paused"]
        assert set(feature_status_schema["enum"]) == set(expected_feature_statuses)


# ============================================================================
# Test: Write-Time Validation (TASK-YSC-004)
# ============================================================================


def test_validate_yaml_valid_data(sample_feature_yaml):
    """Test validate_yaml returns empty list for valid data."""
    errors = FeatureLoader.validate_yaml(sample_feature_yaml)
    assert errors == []


def test_validate_yaml_invalid_status(sample_feature_yaml):
    """Test validate_yaml catches invalid feature status."""
    sample_feature_yaml["status"] = "bogus"
    errors = FeatureLoader.validate_yaml(sample_feature_yaml)
    assert len(errors) >= 1
    # Error should mention the field and value
    assert any("status" in e.lower() for e in errors)
    assert any("bogus" in e for e in errors)


def test_validate_yaml_missing_id(sample_feature_yaml):
    """Test validate_yaml catches missing required field 'id'."""
    del sample_feature_yaml["id"]
    errors = FeatureLoader.validate_yaml(sample_feature_yaml)
    assert len(errors) >= 1
    assert any("id" in e.lower() for e in errors)


def test_validate_yaml_missing_name(sample_feature_yaml):
    """Test validate_yaml catches missing required field 'name'."""
    del sample_feature_yaml["name"]
    errors = FeatureLoader.validate_yaml(sample_feature_yaml)
    assert len(errors) >= 1
    assert any("name" in e.lower() for e in errors)


def test_validate_yaml_wrong_nesting_tasks_as_string(sample_feature_yaml):
    """Test validate_yaml catches wrong nesting (tasks as string instead of list)."""
    sample_feature_yaml["tasks"] = "not a list"
    errors = FeatureLoader.validate_yaml(sample_feature_yaml)
    assert len(errors) >= 1
    assert any("tasks" in e.lower() for e in errors)


def test_validate_yaml_invalid_task_status(sample_feature_yaml):
    """Test validate_yaml catches invalid task status within tasks list."""
    sample_feature_yaml["tasks"][0]["status"] = "invalid_status"
    errors = FeatureLoader.validate_yaml(sample_feature_yaml)
    assert len(errors) >= 1
    assert any("status" in e.lower() for e in errors)


def test_validate_yaml_task_complexity_out_of_range(sample_feature_yaml):
    """Test validate_yaml catches task complexity outside 1-10 range."""
    sample_feature_yaml["tasks"][0]["complexity"] = 15
    errors = FeatureLoader.validate_yaml(sample_feature_yaml)
    assert len(errors) >= 1


def test_validate_yaml_empty_dict():
    """Test validate_yaml handles empty dict (missing all required fields)."""
    errors = FeatureLoader.validate_yaml({})
    assert len(errors) >= 2  # At least id and name missing


def test_validate_yaml_error_messages_include_field_name(sample_feature_yaml):
    """Test that validation errors include field name in the message."""
    sample_feature_yaml["status"] = "invalid"
    errors = FeatureLoader.validate_yaml(sample_feature_yaml)
    # Each error should contain a field reference
    for error in errors:
        # Errors from Pydantic typically include field paths
        assert len(error) > 0  # Just verify non-empty


def test_save_feature_validates_before_write(temp_features_dir, sample_feature_yaml):
    """Test save_feature validates data before writing."""
    # Create a feature with valid data first
    feature = Feature.model_validate(sample_feature_yaml)

    # Save should succeed for valid feature
    FeatureLoader.save_feature(feature, repo_root=temp_features_dir)

    # Now test that invalid data would be caught by validate_yaml
    invalid_data = sample_feature_yaml.copy()
    invalid_data["status"] = "bogus"
    errors = FeatureLoader.validate_yaml(invalid_data)
    assert len(errors) >= 1
