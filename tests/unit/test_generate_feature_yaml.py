"""
Unit tests for generate_feature_yaml module.

Tests the YAML feature file generation script for AutoBuild integration.
Validates schema compatibility with FeatureLoader.

Coverage Target: >=85%
Test Count: 15+ tests
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add installer lib to path
installer_lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
if installer_lib_path.exists():
    sys.path.insert(0, str(installer_lib_path))

from generate_feature_yaml import (
    TaskSpec,
    FeatureFile,
    parse_task_string,
    build_parallel_groups,
    estimate_duration,
    generate_feature_id,
    build_task_file_path,  # Helper function for path construction
    validate_task_paths,  # Post-creation path validation
    slugify_task_name,  # Re-exported from installer.core.lib.slug_utils
)


# ============================================================================
# 1. TaskSpec Dataclass Tests
# ============================================================================

class TestTaskSpec:
    """Tests for TaskSpec dataclass and serialization."""

    def test_task_spec_has_file_path_field(self):
        """Test that TaskSpec includes file_path field."""
        task = TaskSpec(
            id="TASK-001",
            name="Test Task",
            complexity=5,
            file_path="tasks/backlog/feature-name/TASK-001.md"
        )
        assert task.file_path == "tasks/backlog/feature-name/TASK-001.md"

    def test_task_spec_file_path_defaults_to_empty_string(self):
        """Test that file_path defaults to empty string for backward compatibility."""
        task = TaskSpec(
            id="TASK-001",
            name="Test Task",
            complexity=5
        )
        assert task.file_path == ""

    def test_task_spec_to_dict_includes_file_path(self):
        """Test that to_dict() includes file_path in output."""
        task = TaskSpec(
            id="TASK-001",
            name="Test Task",
            complexity=5,
            file_path="tasks/backlog/oauth2/TASK-001.md"
        )
        result = task.to_dict()

        assert "file_path" in result
        assert result["file_path"] == "tasks/backlog/oauth2/TASK-001.md"

    def test_task_spec_to_dict_contains_all_required_fields(self):
        """Test that to_dict() contains all fields required by FeatureLoader."""
        task = TaskSpec(
            id="TASK-001",
            name="Test Task",
            complexity=5,
            file_path="tasks/backlog/feature-name/TASK-001.md",
            dependencies=["TASK-000"],
            status="pending",
            implementation_mode="task-work",
            estimated_minutes=30
        )
        result = task.to_dict()

        # All fields required by FeatureLoader._parse_task()
        required_fields = [
            "id", "name", "file_path", "complexity", "dependencies",
            "status", "implementation_mode", "estimated_minutes"
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"


# ============================================================================
# 2. File Path Construction Tests
# ============================================================================

class TestSlugifyTaskName:
    """Tests for task name slugification."""

    def test_slugify_basic_name(self):
        """Test slugification of basic task name."""
        assert slugify_task_name("Create auth service") == "create-auth-service"

    def test_slugify_with_special_characters(self):
        """Test slugification handles special characters."""
        assert slugify_task_name("Add OAuth 2.0 Provider") == "add-oauth-2-0-provider"

    def test_slugify_with_punctuation(self):
        """Test slugification removes punctuation."""
        assert slugify_task_name("Fix bug! (urgent)") == "fix-bug-urgent"

    def test_slugify_uppercase(self):
        """Test slugification converts to lowercase."""
        assert slugify_task_name("Create AUTH Service") == "create-auth-service"

    def test_slugify_multiple_spaces(self):
        """Test slugification collapses multiple spaces."""
        assert slugify_task_name("Create   auth   service") == "create-auth-service"

    def test_slugify_leading_trailing_spaces(self):
        """Test slugification trims leading/trailing spaces."""
        assert slugify_task_name("  Create auth service  ") == "create-auth-service"

    def test_slugify_numbers(self):
        """Test slugification preserves numbers."""
        assert slugify_task_name("Phase 1 setup") == "phase-1-setup"


class TestBuildTaskFilePath:
    """Tests for file path construction helper function."""

    def test_build_task_file_path_with_task_name(self):
        """Test file path includes task name slug when provided."""
        path = build_task_file_path(
            task_id="TASK-001",
            feature_slug="oauth2",
            base_path="tasks/backlog",
            task_name="Create auth service"
        )
        assert path == "tasks/backlog/oauth2/TASK-001-create-auth-service.md"

    def test_build_task_file_path_without_task_name(self):
        """Test file path uses just task ID when name not provided."""
        path = build_task_file_path(
            task_id="TASK-001",
            feature_slug="oauth2",
            base_path="tasks/backlog"
        )
        assert path == "tasks/backlog/oauth2/TASK-001.md"

    def test_build_task_file_path_with_custom_base_path(self):
        """Test file path construction with custom base path."""
        path = build_task_file_path(
            task_id="TASK-AUTH-001",
            feature_slug="authentication",
            base_path="tasks/in_progress",
            task_name="Add OAuth provider"
        )
        assert path == "tasks/in_progress/authentication/TASK-AUTH-001-add-oauth-provider.md"

    def test_build_task_file_path_without_feature_slug(self):
        """Test file path construction without feature slug (flat structure)."""
        path = build_task_file_path(
            task_id="TASK-001",
            feature_slug="",
            base_path="tasks/backlog",
            task_name="Create service"
        )
        # Without feature slug, still includes name in filename
        assert path == "tasks/backlog/TASK-001-create-service.md"

    def test_build_task_file_path_default_base_path(self):
        """Test file path uses default base path."""
        path = build_task_file_path(
            task_id="TASK-001",
            feature_slug="my-feature",
            task_name="Setup project"
        )
        assert path == "tasks/backlog/my-feature/TASK-001-setup-project.md"

    def test_build_task_file_path_empty_task_name(self):
        """Test file path with explicitly empty task name."""
        path = build_task_file_path(
            task_id="TASK-001",
            feature_slug="oauth2",
            task_name=""
        )
        assert path == "tasks/backlog/oauth2/TASK-001.md"

    def test_build_task_file_path_no_doubling(self):
        """Regression: base_path already containing feature_slug should not double it."""
        path = build_task_file_path(
            task_id="TASK-001",
            feature_slug="my-feature",
            base_path="tasks/backlog/my-feature",
            task_name="Create service"
        )
        assert path == "tasks/backlog/my-feature/TASK-001-create-service.md"
        assert "my-feature/my-feature" not in path

    def test_build_task_file_path_no_doubling_without_task_name(self):
        """Regression: no doubling even without task name."""
        path = build_task_file_path(
            task_id="TASK-001",
            feature_slug="my-feature",
            base_path="tasks/backlog/my-feature"
        )
        assert path == "tasks/backlog/my-feature/TASK-001.md"
        assert "my-feature/my-feature" not in path

    def test_build_task_file_path_no_doubling_with_trailing_slash(self):
        """Regression: no doubling even with trailing slash on base_path."""
        path = build_task_file_path(
            task_id="TASK-001",
            feature_slug="my-feature",
            base_path="tasks/backlog/my-feature/",
            task_name="Create service"
        )
        assert "my-feature/my-feature" not in path

    def test_build_task_file_path_slug_equals_base_path(self):
        """Edge case: base_path is just the feature_slug itself."""
        path = build_task_file_path(
            task_id="TASK-001",
            feature_slug="my-feature",
            base_path="my-feature",
            task_name="Create service"
        )
        assert path == "my-feature/TASK-001-create-service.md"
        assert "my-feature/my-feature" not in path


# ============================================================================
# 3. Parse Task String Tests
# ============================================================================

class TestParseTaskString:
    """Tests for parsing task string format."""

    def test_parse_task_string_with_feature_slug(self):
        """Test parsing with feature slug includes task name in file path."""
        task = parse_task_string(
            "TASK-001:Create auth service:5:",
            feature_slug="oauth2",
            task_base_path="tasks/backlog"
        )
        assert task.id == "TASK-001"
        assert task.name == "Create auth service"
        assert task.complexity == 5
        # File path now includes slugified task name
        assert task.file_path == "tasks/backlog/oauth2/TASK-001-create-auth-service.md"

    def test_parse_task_string_without_feature_slug(self):
        """Test parsing without feature slug (backward compatible)."""
        task = parse_task_string("TASK-001:Create auth service:5:")
        assert task.id == "TASK-001"
        assert task.name == "Create auth service"
        assert task.complexity == 5
        assert task.file_path == ""  # Empty when no slug provided

    def test_parse_task_string_with_dependencies(self):
        """Test parsing task with dependencies includes name in path."""
        task = parse_task_string(
            "TASK-002:Add OAuth provider:6:TASK-001",
            feature_slug="oauth2",
            task_base_path="tasks/backlog"
        )
        assert task.id == "TASK-002"
        assert task.dependencies == ["TASK-001"]
        # File path now includes slugified task name
        assert task.file_path == "tasks/backlog/oauth2/TASK-002-add-oauth-provider.md"

    def test_parse_task_string_with_multiple_dependencies(self):
        """Test parsing task with multiple dependencies."""
        task = parse_task_string(
            "TASK-003:Add tests:3:TASK-001,TASK-002",
            feature_slug="oauth2",
            task_base_path="tasks/backlog"
        )
        assert task.dependencies == ["TASK-001", "TASK-002"]
        assert task.file_path == "tasks/backlog/oauth2/TASK-003-add-tests.md"

    def test_parse_task_string_sets_implementation_mode_by_complexity(self):
        """Test that implementation_mode is set based on complexity."""
        # Low complexity -> direct
        low = parse_task_string("TASK-001:Simple task:2:", feature_slug="test")
        assert low.implementation_mode == "direct"

        # High complexity -> task-work
        high = parse_task_string("TASK-002:Complex task:5:", feature_slug="test")
        assert high.implementation_mode == "task-work"

    def test_parse_task_string_default_complexity(self):
        """Test default complexity when not provided."""
        task = parse_task_string("TASK-001:Test task::", feature_slug="test")
        assert task.complexity == 5  # Default


# ============================================================================
# 4. Parallel Groups (Wave Detection) Tests
# ============================================================================

class TestBuildParallelGroups:
    """Tests for dependency-based wave grouping."""

    def test_single_task_single_wave(self):
        """Test single task results in single wave."""
        tasks = [
            TaskSpec(id="TASK-001", name="Task 1", complexity=5, file_path="")
        ]
        groups = build_parallel_groups(tasks)
        assert groups == [["TASK-001"]]

    def test_independent_tasks_parallel(self):
        """Test independent tasks can run in parallel."""
        tasks = [
            TaskSpec(id="TASK-001", name="Task 1", complexity=5, file_path=""),
            TaskSpec(id="TASK-002", name="Task 2", complexity=5, file_path=""),
            TaskSpec(id="TASK-003", name="Task 3", complexity=5, file_path=""),
        ]
        groups = build_parallel_groups(tasks)
        assert len(groups) == 1
        assert set(groups[0]) == {"TASK-001", "TASK-002", "TASK-003"}

    def test_sequential_dependency_chain(self):
        """Test sequential dependencies create separate waves."""
        tasks = [
            TaskSpec(id="TASK-001", name="Task 1", complexity=5, file_path="", dependencies=[]),
            TaskSpec(id="TASK-002", name="Task 2", complexity=5, file_path="", dependencies=["TASK-001"]),
            TaskSpec(id="TASK-003", name="Task 3", complexity=5, file_path="", dependencies=["TASK-002"]),
        ]
        groups = build_parallel_groups(tasks)
        assert len(groups) == 3
        assert groups[0] == ["TASK-001"]
        assert groups[1] == ["TASK-002"]
        assert groups[2] == ["TASK-003"]

    def test_mixed_parallel_and_sequential(self):
        """Test mixed parallel and sequential dependencies."""
        tasks = [
            TaskSpec(id="TASK-001", name="Task 1", complexity=5, file_path="", dependencies=[]),
            TaskSpec(id="TASK-002", name="Task 2", complexity=5, file_path="", dependencies=[]),
            TaskSpec(id="TASK-003", name="Task 3", complexity=5, file_path="", dependencies=["TASK-001", "TASK-002"]),
        ]
        groups = build_parallel_groups(tasks)
        assert len(groups) == 2
        assert set(groups[0]) == {"TASK-001", "TASK-002"}
        assert groups[1] == ["TASK-003"]

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are handled gracefully."""
        tasks = [
            TaskSpec(id="TASK-001", name="Task 1", complexity=5, file_path="", dependencies=["TASK-002"]),
            TaskSpec(id="TASK-002", name="Task 2", complexity=5, file_path="", dependencies=["TASK-001"]),
        ]
        # Should not hang or crash - returns remaining tasks
        groups = build_parallel_groups(tasks)
        # All tasks should eventually be in groups
        all_tasks = set()
        for group in groups:
            all_tasks.update(group)
        assert all_tasks == {"TASK-001", "TASK-002"}


# ============================================================================
# 5. Feature File Output Tests
# ============================================================================

class TestFeatureFileOutput:
    """Tests for complete feature file output format."""

    def test_feature_file_orchestration_format(self):
        """Test that orchestration uses parallel_groups list of lists."""
        tasks = [
            TaskSpec(
                id="TASK-001",
                name="Task 1",
                complexity=5,
                file_path="tasks/backlog/test/TASK-001.md",
                dependencies=[]
            ),
            TaskSpec(
                id="TASK-002",
                name="Task 2",
                complexity=5,
                file_path="tasks/backlog/test/TASK-002.md",
                dependencies=["TASK-001"]
            ),
        ]
        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="Test description",
            tasks=tasks,
            parallel_groups=build_parallel_groups(tasks),
            estimated_duration_minutes=60,
            recommended_parallel=2
        )
        result = feature.to_dict()

        assert "orchestration" in result
        assert "parallel_groups" in result["orchestration"]
        assert isinstance(result["orchestration"]["parallel_groups"], list)
        # Each element is a list of task IDs
        for group in result["orchestration"]["parallel_groups"]:
            assert isinstance(group, list)

    def test_feature_file_tasks_include_file_path(self):
        """Test that all tasks in feature output include file_path."""
        tasks = [
            TaskSpec(
                id="TASK-001",
                name="Task 1",
                complexity=5,
                file_path="tasks/backlog/test/TASK-001.md"
            )
        ]
        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="",
            tasks=tasks,
            parallel_groups=[["TASK-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1
        )
        result = feature.to_dict()

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["file_path"] == "tasks/backlog/test/TASK-001.md"

    def test_feature_file_no_task_files_section(self):
        """Test that output does NOT contain task_files section (redundant)."""
        tasks = [
            TaskSpec(
                id="TASK-001",
                name="Task 1",
                complexity=5,
                file_path="tasks/backlog/test/TASK-001.md"
            )
        ]
        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="",
            tasks=tasks,
            parallel_groups=[["TASK-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1
        )
        result = feature.to_dict()

        assert "task_files" not in result

    def test_feature_file_no_execution_groups_section(self):
        """Test that output does NOT contain execution_groups section (use orchestration)."""
        tasks = [
            TaskSpec(
                id="TASK-001",
                name="Task 1",
                complexity=5,
                file_path="tasks/backlog/test/TASK-001.md"
            )
        ]
        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="",
            tasks=tasks,
            parallel_groups=[["TASK-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1
        )
        result = feature.to_dict()

        assert "execution_groups" not in result


# ============================================================================
# 6. Duration Estimation Tests
# ============================================================================

class TestEstimateDuration:
    """Tests for duration estimation from complexity."""

    def test_estimate_duration_low_complexity(self):
        """Test duration estimation for low complexity tasks."""
        duration = estimate_duration(1)
        assert duration == 15  # Base minutes

    def test_estimate_duration_medium_complexity(self):
        """Test duration estimation for medium complexity tasks."""
        duration = estimate_duration(5)
        assert duration > 15  # Should be higher than base

    def test_estimate_duration_high_complexity(self):
        """Test duration estimation for high complexity tasks."""
        duration = estimate_duration(10)
        assert duration > estimate_duration(5)  # Should scale with complexity


# ============================================================================
# 7. Integration Tests (Schema Compatibility)
# ============================================================================

class TestFeatureLoaderSchemaCompatibility:
    """Integration tests for schema compatibility with FeatureLoader."""

    def test_generated_yaml_loadable_by_feature_loader(self, tmp_path):
        """Test that generated YAML can be loaded by FeatureLoader schema."""
        # Create tasks with file_path
        tasks = [
            TaskSpec(
                id="TASK-001",
                name="Create auth service",
                complexity=5,
                file_path="tasks/backlog/oauth2/TASK-001.md",
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=75
            ),
            TaskSpec(
                id="TASK-002",
                name="Add OAuth provider",
                complexity=6,
                file_path="tasks/backlog/oauth2/TASK-002.md",
                dependencies=["TASK-001"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=120
            )
        ]

        feature = FeatureFile(
            id="FEAT-TEST",
            name="OAuth2 Authentication",
            description="Add OAuth2 support",
            tasks=tasks,
            parallel_groups=build_parallel_groups(tasks),
            estimated_duration_minutes=195,
            recommended_parallel=2
        )

        result = feature.to_dict()

        # Validate against FeatureLoader schema expectations
        # 1. Feature-level fields
        assert "id" in result
        assert "name" in result
        assert "tasks" in result
        assert "orchestration" in result

        # 2. Task-level required fields (from FeatureLoader._parse_task)
        for task in result["tasks"]:
            assert "id" in task
            assert "name" in task
            assert "file_path" in task  # REQUIRED by FeatureLoader
            assert "complexity" in task
            assert "dependencies" in task
            assert "status" in task
            assert "implementation_mode" in task
            assert "estimated_minutes" in task

        # 3. Orchestration structure
        assert "parallel_groups" in result["orchestration"]
        assert "estimated_duration_minutes" in result["orchestration"]
        assert "recommended_parallel" in result["orchestration"]


# ============================================================================
# 8. Backward Compatibility Tests
# ============================================================================

class TestBackwardCompatibility:
    """Tests for backward compatibility with existing CLI usage."""

    def test_parse_task_string_backward_compatible(self):
        """Test that parse_task_string works without new parameters."""
        # Old usage (no feature_slug)
        task = parse_task_string("TASK-001:Test task:5:")

        assert task.id == "TASK-001"
        assert task.name == "Test task"
        assert task.complexity == 5
        # file_path should default to empty (backward compatible)
        assert task.file_path == ""

    def test_task_spec_backward_compatible(self):
        """Test that TaskSpec works without file_path parameter."""
        # Old usage (no file_path)
        task = TaskSpec(
            id="TASK-001",
            name="Test task",
            complexity=5
        )

        assert task.file_path == ""  # Default value

        # to_dict still works
        result = task.to_dict()
        assert result["file_path"] == ""


# ============================================================================
# 9. Post-Creation Path Validation Tests
# ============================================================================

class TestValidateTaskPaths:
    """Tests for post-creation path validation."""

    def test_validate_all_paths_exist(self, tmp_path):
        """Test validation passes when all task files exist."""
        # Create task files on disk
        task_dir = tmp_path / "tasks" / "backlog" / "oauth2"
        task_dir.mkdir(parents=True)
        (task_dir / "TASK-001-auth-service.md").write_text("# Task 1")
        (task_dir / "TASK-002-oauth-provider.md").write_text("# Task 2")

        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="",
            tasks=[
                TaskSpec(
                    id="TASK-001", name="Auth service", complexity=5,
                    file_path="tasks/backlog/oauth2/TASK-001-auth-service.md"
                ),
                TaskSpec(
                    id="TASK-002", name="OAuth provider", complexity=6,
                    file_path="tasks/backlog/oauth2/TASK-002-oauth-provider.md"
                ),
            ],
        )

        errors = validate_task_paths(feature, tmp_path)
        assert errors == []

    def test_validate_missing_paths(self, tmp_path):
        """Test validation reports missing task files."""
        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="",
            tasks=[
                TaskSpec(
                    id="TASK-001", name="Auth service", complexity=5,
                    file_path="tasks/backlog/oauth2/TASK-001-auth-service.md"
                ),
            ],
        )

        errors = validate_task_paths(feature, tmp_path)
        assert len(errors) == 1
        assert "TASK-001" in errors[0]
        assert "file not found" in errors[0]

    def test_validate_partial_missing(self, tmp_path):
        """Test validation reports only missing files, not existing ones."""
        task_dir = tmp_path / "tasks" / "backlog" / "oauth2"
        task_dir.mkdir(parents=True)
        (task_dir / "TASK-001-auth-service.md").write_text("# Task 1")

        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="",
            tasks=[
                TaskSpec(
                    id="TASK-001", name="Auth service", complexity=5,
                    file_path="tasks/backlog/oauth2/TASK-001-auth-service.md"
                ),
                TaskSpec(
                    id="TASK-002", name="OAuth provider", complexity=6,
                    file_path="tasks/backlog/oauth2/TASK-002-oauth-provider.md"
                ),
            ],
        )

        errors = validate_task_paths(feature, tmp_path)
        assert len(errors) == 1
        assert "TASK-002" in errors[0]

    def test_validate_empty_file_path_skipped(self, tmp_path):
        """Test that tasks with empty file_path are skipped (no false positive)."""
        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="",
            tasks=[
                TaskSpec(
                    id="TASK-001", name="Auth service", complexity=5,
                    file_path=""
                ),
            ],
        )

        errors = validate_task_paths(feature, tmp_path)
        assert errors == []

    def test_validate_no_tasks(self, tmp_path):
        """Test validation with no tasks returns empty list."""
        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="",
            tasks=[],
        )

        errors = validate_task_paths(feature, tmp_path)
        assert errors == []

    def test_validate_error_message_includes_path(self, tmp_path):
        """Test error message includes the expected file path."""
        feature = FeatureFile(
            id="FEAT-TEST",
            name="Test Feature",
            description="",
            tasks=[
                TaskSpec(
                    id="TASK-XYZ", name="Missing task", complexity=3,
                    file_path="tasks/backlog/my-feature/TASK-XYZ-missing-task.md"
                ),
            ],
        )

        errors = validate_task_paths(feature, tmp_path)
        assert len(errors) == 1
        assert "tasks/backlog/my-feature/TASK-XYZ-missing-task.md" in errors[0]


# ============================================================================
# 10. CLI Validation Tests (TASK-FIX-FP04)
# ============================================================================

class TestFeatureSlugValidation:
    """Tests for --feature-slug validation in main()."""

    def test_missing_feature_slug_exits_with_error(self, tmp_path, capsys):
        """Test that missing --feature-slug exits with clear error when tasks provided."""
        from generate_feature_yaml import main

        sys.argv = [
            "generate_feature_yaml.py",
            "--name", "Test Feature",
            "--task", "TASK-001:Create service:5:",
            "--base-path", str(tmp_path),
        ]

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--feature-slug is required" in captured.err
        assert "Example:" in captured.err

    def test_empty_feature_slug_exits_with_error(self, tmp_path, capsys):
        """Test that explicitly empty --feature-slug is rejected."""
        from generate_feature_yaml import main

        sys.argv = [
            "generate_feature_yaml.py",
            "--name", "Test Feature",
            "--task", "TASK-001:Create service:5:",
            "--feature-slug", "",
            "--base-path", str(tmp_path),
        ]

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--feature-slug is required" in captured.err

    def test_provided_feature_slug_succeeds(self, tmp_path, capsys):
        """Test that providing --feature-slug allows normal execution."""
        from generate_feature_yaml import main

        sys.argv = [
            "generate_feature_yaml.py",
            "--name", "Test Feature",
            "--task", "TASK-001:Create service:5:",
            "--feature-slug", "my-feature",
            "--base-path", str(tmp_path),
            "--quiet",
        ]

        # Should not raise SystemExit
        main()

        # Verify output file was created
        features_dir = tmp_path / ".guardkit" / "features"
        assert features_dir.exists()
        yaml_files = list(features_dir.glob("FEAT-*.yaml"))
        assert len(yaml_files) == 1

    def test_all_generated_tasks_have_non_empty_file_path(self, tmp_path):
        """Test that all tasks in generated YAML have non-empty file_path values."""
        from generate_feature_yaml import main
        import yaml

        sys.argv = [
            "generate_feature_yaml.py",
            "--name", "Test Feature",
            "--task", "TASK-001:Create service:5:",
            "--task", "TASK-002:Add tests:3:TASK-001",
            "--feature-slug", "my-feature",
            "--base-path", str(tmp_path),
            "--quiet",
        ]

        main()

        features_dir = tmp_path / ".guardkit" / "features"
        yaml_files = list(features_dir.glob("FEAT-*.yaml"))
        assert len(yaml_files) == 1

        with open(yaml_files[0]) as f:
            data = yaml.safe_load(f)

        for task in data["tasks"]:
            assert task["file_path"], f"Task {task['id']} has empty file_path"
            assert task["file_path"].startswith("tasks/backlog/my-feature/")
