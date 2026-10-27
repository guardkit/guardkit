"""Tests for pre-flight feature validation.

Coverage Target: >=85%

"""

from pathlib import Path

from guardkit.orchestrator.feature_validator import (
    validate_feature_preflight,
    format_preflight_report,
    PreFlightValidationResult,
    ValidationIssue,
    _extract_frontmatter,
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
    """The frontmatter checks were deleted in the cull (27 October 2026):
    a missing field, an alias and an unknown task_type all pass."""

    def test_frontmatter_is_not_checked(self, tmp_path):
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-001.md",
            "title: Task One\ntask_type: foobar",
        )
        _create_task_file(
            tmp_path,
            "tasks/backlog/TASK-002.md",
            "id: TASK-002\ntask_type: implementation",
        )
        feature = _make_feature([
            _make_task("TASK-001", "tasks/backlog/TASK-001.md"),
            _make_task("TASK-002", "tasks/backlog/TASK-002.md"),
        ])

        result = validate_feature_preflight(feature, tmp_path)

        assert result.is_valid
        assert result.errors == []
        assert result.warnings == []


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
        assert "1 task(s) have advice" in report
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
