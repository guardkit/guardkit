"""Tests for pre-flight feature validation.

Coverage Target: >=85%
Test Count: 17 tests
"""

import pytest
from pathlib import Path

from guardkit.orchestrator.feature_validator import (
    validate_feature_preflight,
    format_preflight_report,
    PreFlightValidationResult,
    ValidationIssue,
    _extract_frontmatter,
    REQUIRED_FRONTMATTER_FIELDS,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureOrchestration,
)


# ============================================================================
# Helpers
# ============================================================================


def _create_task_file(repo_root: Path, file_path: str, frontmatter: str) -> Path:
    """Create a task markdown file with given frontmatter content."""
    full_path = repo_root / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(f"---\n{frontmatter}\n---\n\n# Task\n")
    return full_path


def _make_feature(tasks: list) -> Feature:
    """Create a minimal Feature with given tasks."""
    return Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test feature for validation",
        tasks=tasks,
        orchestration=FeatureOrchestration(
            parallel_groups=[[t.id for t in tasks]],
        ),
    )


def _make_task(task_id: str, file_path: str) -> FeatureTask:
    """Create a minimal FeatureTask."""
    return FeatureTask(
        id=task_id,
        name=task_id,
        file_path=Path(file_path),
        complexity=5,
    )


# ============================================================================
# Tests: _extract_frontmatter
# ============================================================================


class TestExtractFrontmatter:
    """Tests for YAML frontmatter extraction."""

    def test_extract_valid_frontmatter(self, tmp_path):
        """Valid YAML frontmatter returns parsed dict."""
        task_file = tmp_path / "task.md"
        task_file.write_text("---\nid: TASK-001\ntitle: Test\n---\n# Content\n")
        result = _extract_frontmatter(task_file)
        assert result == {"id": "TASK-001", "title": "Test"}

    def test_extract_no_frontmatter(self, tmp_path):
        """File without frontmatter delimiters returns None."""
        task_file = tmp_path / "task.md"
        task_file.write_text("# No frontmatter here\nJust content.")
        result = _extract_frontmatter(task_file)
        assert result is None

    def test_extract_invalid_yaml(self, tmp_path):
        """Malformed YAML returns None."""
        task_file = tmp_path / "task.md"
        task_file.write_text("---\n: invalid: yaml: [broken\n---\n")
        result = _extract_frontmatter(task_file)
        assert result is None

    def test_extract_no_closing_delimiter(self, tmp_path):
        """Frontmatter without closing --- returns None."""
        task_file = tmp_path / "task.md"
        task_file.write_text("---\nid: TASK-001\ntitle: Test\n")
        result = _extract_frontmatter(task_file)
        assert result is None

    def test_extract_nonexistent_file(self, tmp_path):
        """Non-existent file returns None."""
        result = _extract_frontmatter(tmp_path / "nonexistent.md")
        assert result is None

    def test_extract_non_dict_frontmatter(self, tmp_path):
        """Frontmatter that parses to non-dict (e.g., a string) returns None."""
        task_file = tmp_path / "task.md"
        task_file.write_text("---\njust a string\n---\n")
        result = _extract_frontmatter(task_file)
        assert result is None


# ============================================================================
# Tests: validate_feature_preflight
# ============================================================================


class TestValidateFeaturePreflight:
    """Tests for pre-flight feature validation."""

    def test_valid_feature_passes(self, tmp_path):
        """Feature with all valid canonical task_type and required fields passes."""
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-001.md",
            "id: TASK-001\ntitle: Task One\ntask_type: feature\ncomplexity: 5",
        )
        task = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        feature = _make_feature([task])

        result = validate_feature_preflight(feature, tmp_path)

        assert result.is_valid
        assert not result.has_errors
        assert not result.has_warnings

    def test_invalid_task_type_detected(self, tmp_path):
        """Invalid task_type value produces an error."""
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-001.md",
            "id: TASK-001\ntitle: Task One\ntask_type: foobar\ncomplexity: 5",
        )
        task = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        feature = _make_feature([task])

        result = validate_feature_preflight(feature, tmp_path)

        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].task_id == "TASK-001"
        assert "foobar" in result.errors[0].message
        assert result.errors[0].field == "task_type"

    def test_alias_task_type_produces_warning(self, tmp_path):
        """Alias task_type produces a warning, not an error."""
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-001.md",
            "id: TASK-001\ntitle: Task One\ntask_type: enhancement\ncomplexity: 5",
        )
        task = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        feature = _make_feature([task])

        result = validate_feature_preflight(feature, tmp_path)

        assert result.is_valid  # Aliases don't block execution
        assert not result.has_errors
        assert result.has_warnings
        assert len(result.warnings) == 1
        assert result.warnings[0].task_id == "TASK-001"
        assert "enhancement" in result.warnings[0].message
        assert "feature" in result.warnings[0].suggestion

    def test_missing_required_field_complexity(self, tmp_path):
        """Missing 'complexity' field produces an error."""
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-001.md",
            "id: TASK-001\ntitle: Task One\ntask_type: feature",
        )
        task = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        feature = _make_feature([task])

        result = validate_feature_preflight(feature, tmp_path)

        assert not result.is_valid
        assert any(
            issue.field == "complexity" and "Missing required field" in issue.message
            for issue in result.errors
        )

    def test_missing_required_field_title(self, tmp_path):
        """Missing 'title' field produces an error."""
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-001.md",
            "id: TASK-001\ntask_type: feature\ncomplexity: 5",
        )
        task = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        feature = _make_feature([task])

        result = validate_feature_preflight(feature, tmp_path)

        assert not result.is_valid
        assert any(
            issue.field == "title" for issue in result.errors
        )

    def test_missing_required_field_task_type(self, tmp_path):
        """Missing 'task_type' field produces an error."""
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-001.md",
            "id: TASK-001\ntitle: Task One\ncomplexity: 5",
        )
        task = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        feature = _make_feature([task])

        result = validate_feature_preflight(feature, tmp_path)

        assert not result.is_valid
        assert any(
            issue.field == "task_type" for issue in result.errors
        )

    def test_missing_required_field_id(self, tmp_path):
        """Missing 'id' field produces an error."""
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-001.md",
            "title: Task One\ntask_type: feature\ncomplexity: 5",
        )
        task = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        feature = _make_feature([task])

        result = validate_feature_preflight(feature, tmp_path)

        assert not result.is_valid
        assert any(
            issue.field == "id" for issue in result.errors
        )

    def test_multiple_errors_reported_at_once(self, tmp_path):
        """Multiple tasks with different errors are all collected (batch)."""
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-001.md",
            "id: TASK-001\ntitle: Task One\ntask_type: foobar\ncomplexity: 5",
        )
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-002.md",
            "id: TASK-002\ntitle: Task Two\ntask_type: feature",
        )
        task1 = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        task2 = _make_task("TASK-002", "tasks/backlog/TASK-002.md")
        feature = _make_feature([task1, task2])

        result = validate_feature_preflight(feature, tmp_path)

        assert not result.is_valid
        task_ids_with_errors = {issue.task_id for issue in result.errors}
        assert "TASK-001" in task_ids_with_errors  # invalid task_type
        assert "TASK-002" in task_ids_with_errors  # missing complexity

    def test_missing_file_skipped(self, tmp_path):
        """Task whose file does not exist is skipped (structural validator handles it)."""
        task = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        feature = _make_feature([task])
        # Don't create the file

        result = validate_feature_preflight(feature, tmp_path)

        assert result.is_valid
        assert not result.has_errors
        assert not result.has_warnings

    def test_no_frontmatter_skipped(self, tmp_path):
        """Task file with no frontmatter is skipped gracefully."""
        file_path = tmp_path / "tasks" / "backlog" / "TASK-001.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("# Just a markdown file\nNo frontmatter here.")
        task = _make_task("TASK-001", "tasks/backlog/TASK-001.md")
        feature = _make_feature([task])

        result = validate_feature_preflight(feature, tmp_path)

        assert result.is_valid

    def test_all_canonical_task_types_pass(self, tmp_path):
        """All canonical TaskType enum values pass validation."""
        from guardkit.models.task_types import TaskType

        tasks = []
        for i, task_type in enumerate(TaskType):
            task_id = f"TASK-{i:03d}"
            file_path = f"tasks/backlog/{task_id}.md"
            _create_task_file(
                tmp_path,
                file_path,
                f"id: {task_id}\ntitle: Task {i}\ntask_type: {task_type.value}\ncomplexity: 5",
            )
            tasks.append(_make_task(task_id, file_path))

        feature = _make_feature(tasks)
        result = validate_feature_preflight(feature, tmp_path)

        assert result.is_valid
        assert not result.has_warnings


# ============================================================================
# Tests: format_preflight_report
# ============================================================================


class TestFormatPreflightReport:
    """Tests for report formatting."""

    def test_format_errors(self):
        """Error report includes task count, details, and fix message."""
        result = PreFlightValidationResult(
            errors=[
                ValidationIssue(
                    task_id="TASK-001",
                    field="task_type",
                    severity="error",
                    message="Invalid task_type 'bogus'",
                    suggestion="Valid values: scaffolding, feature",
                ),
            ],
        )

        report = format_preflight_report(result)

        assert "PRE-FLIGHT VALIDATION FAILED" in report
        assert "1 task(s) have invalid frontmatter" in report
        assert "TASK-001" in report
        assert "Invalid task_type 'bogus'" in report
        assert "Fix these issues and retry" in report

    def test_format_warnings(self):
        """Warning report includes alias suggestion and note."""
        result = PreFlightValidationResult(
            warnings=[
                ValidationIssue(
                    task_id="TASK-002",
                    field="task_type",
                    severity="warning",
                    message="task_type 'enhancement' is a legacy alias",
                    suggestion="Change to 'feature' (canonical value)",
                ),
            ],
        )

        report = format_preflight_report(result)

        assert "PRE-FLIGHT VALIDATION WARNINGS" in report
        assert "1 task(s) use legacy aliases" in report
        assert "TASK-002" in report
        assert "enhancement" in report
        assert "Suggestion: Change to 'feature'" in report
        assert "Alias will work at runtime" in report

    def test_format_mixed_errors_and_warnings(self):
        """Report with both errors and warnings includes both sections."""
        result = PreFlightValidationResult(
            errors=[
                ValidationIssue(
                    task_id="TASK-001",
                    field="complexity",
                    severity="error",
                    message="Missing required field 'complexity'",
                ),
            ],
            warnings=[
                ValidationIssue(
                    task_id="TASK-002",
                    field="task_type",
                    severity="warning",
                    message="task_type 'enhancement' is a legacy alias",
                    suggestion="Change to 'feature' (canonical value)",
                ),
            ],
        )

        report = format_preflight_report(result)

        assert "PRE-FLIGHT VALIDATION FAILED" in report
        assert "PRE-FLIGHT VALIDATION WARNINGS" in report

    def test_format_empty_result(self):
        """Empty result (no errors, no warnings) produces empty string."""
        result = PreFlightValidationResult()
        report = format_preflight_report(result)
        assert report == ""

    def test_format_multiple_errors_different_tasks(self):
        """Multiple errors from different tasks are counted correctly."""
        result = PreFlightValidationResult(
            errors=[
                ValidationIssue(
                    task_id="TASK-001",
                    field="task_type",
                    severity="error",
                    message="Invalid task_type 'xyz'",
                ),
                ValidationIssue(
                    task_id="TASK-002",
                    field="complexity",
                    severity="error",
                    message="Missing required field 'complexity'",
                ),
            ],
        )

        report = format_preflight_report(result)

        assert "2 task(s) have invalid frontmatter" in report
        assert "TASK-001" in report
        assert "TASK-002" in report
