"""Tests for the acceptance criteria classifier.

Validates classification against real-world criteria from:
- FEAT-2AAA (failing run - TASK-VID-001 through TASK-VID-005)
- FEAT-SKEL-001 (successful run - TASK-SKEL-001 through TASK-SKEL-004)
"""

import pytest

from guardkit.orchestrator.quality_gates.criteria_classifier import (
    ClassifiedCriterion,
    ClassificationResult,
    CriterionType,
    classify_acceptance_criteria,
    classify_criterion,
)


# --- FEAT-2AAA Criteria (Failing Run) ---


class TestTaskVid001Criteria:
    """TASK-VID-001: Add yt-dlp dependency to pyproject.toml.

    This task caused the UNRECOVERABLE_STALL because 2/3 criteria
    are command_execution type, unverifiable via synthetic report.
    """

    def test_file_content_criterion(self):
        """Criterion 1: file content check — should be verifiable."""
        result = classify_criterion(
            "- [ ] `yt-dlp>=2024.1.0` added to `dependencies` list in `pyproject.toml`"
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT
        assert result.confidence >= 0.6

    def test_pip_install_criterion(self):
        """Criterion 2: command execution — was unverifiable."""
        result = classify_criterion(
            '- [ ] `pip install -e ".[dev]"` succeeds without errors'
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION
        assert result.extracted_command is not None
        assert "pip install" in result.extracted_command

    def test_python_import_criterion(self):
        """Criterion 3: command execution — was unverifiable."""
        result = classify_criterion(
            '- [ ] `python -c "import yt_dlp; print(yt_dlp.version.__version__)"` runs successfully'
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION
        assert result.extracted_command is not None
        assert "python" in result.extracted_command

    def test_full_task_classification(self):
        """All 3 criteria classified: expect 1 file_content, 2 command_execution."""
        criteria = [
            "- [ ] `yt-dlp>=2024.1.0` added to `dependencies` list in `pyproject.toml`",
            '- [ ] `pip install -e ".[dev]"` succeeds without errors',
            '- [ ] `python -c "import yt_dlp; print(yt_dlp.version.__version__)"` runs successfully',
        ]
        result = classify_acceptance_criteria(criteria)
        assert len(result.file_content_criteria) == 1
        assert len(result.command_criteria) == 2
        assert len(result.manual_criteria) == 0
        assert result.verifiable_count == 3


class TestTaskVid005Criteria:
    """TASK-VID-005: Add integration tests.

    5/6 criteria were unverifiable (commands + manual).
    """

    def test_pytest_command(self):
        result = classify_criterion(
            "- [ ] `pytest tests/test_video_info.py -v` passes all tests"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION

    def test_coverage_command(self):
        result = classify_criterion(
            "- [ ] `pytest --cov=src --cov-report=term` shows >= 80% coverage"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION


# --- FEAT-SKEL-001 Criteria (Successful Run) ---


class TestSuccessfulRunCriteria:
    """Criteria from the successful FEAT-SKEL-001 run.

    All criteria were file-content verifiable, which is why
    the synthetic report path worked.
    """

    def test_file_exists(self):
        result = classify_criterion(
            "- [ ] `pyproject.toml` exists with correct metadata"
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT

    def test_file_contains(self):
        result = classify_criterion(
            '- [ ] `pyproject.toml` contains `name = "youtube-transcript-mcp"`'
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT

    def test_module_defined(self):
        result = classify_criterion(
            "- [ ] Module `src/server.py` exists with FastMCP server"
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT

    def test_function_defined(self):
        result = classify_criterion(
            "- [ ] Function `ping()` defined in `src/server.py`"
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT


# --- Edge Cases ---


class TestEdgeCases:
    def test_empty_string(self):
        result = classify_acceptance_criteria([""])
        assert result.total_count == 0

    def test_whitespace_only(self):
        result = classify_acceptance_criteria(["   "])
        assert result.total_count == 0

    def test_no_backticks(self):
        """Plain text criterion with no code markers."""
        result = classify_criterion("The API responds with 200 OK")
        # Should default to file_content with low confidence
        assert result.confidence <= 0.5

    def test_manual_visual_check(self):
        result = classify_criterion(
            "- [ ] Visually verify the UI matches the design mockup"
        )
        assert result.criterion_type == CriterionType.MANUAL

    def test_manual_performance_check(self):
        result = classify_criterion(
            "- [ ] Response time stays under 200ms for 95th percentile"
        )
        assert result.criterion_type == CriterionType.MANUAL

    def test_npm_install_command(self):
        result = classify_criterion(
            "- [ ] `npm install` completes without errors"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION
        assert "npm install" in result.extracted_command

    def test_docker_command(self):
        result = classify_criterion(
            "- [ ] `docker build -t myapp .` succeeds"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION

    def test_cargo_test(self):
        result = classify_criterion(
            "- [ ] `cargo test` passes all tests"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION

    def test_checkbox_stripped(self):
        """Markdown checkbox prefix should not affect classification."""
        with_checkbox = classify_criterion("- [x] `pip install` succeeds")
        without_checkbox = classify_criterion("`pip install` succeeds")
        assert with_checkbox.criterion_type == without_checkbox.criterion_type


# --- ClassificationResult Properties ---


class TestClassificationResult:
    def test_mixed_criteria(self):
        criteria = [
            "- [ ] `config.json` exists with correct settings",
            "- [ ] `npm test` passes all tests",
            "- [ ] Visually verify the layout matches mockup",
        ]
        result = classify_acceptance_criteria(criteria)
        assert result.total_count == 3
        assert len(result.file_content_criteria) == 1
        assert len(result.command_criteria) == 1
        assert len(result.manual_criteria) == 1
        assert result.verifiable_count == 2

    def test_empty_input(self):
        result = classify_acceptance_criteria([])
        assert result.total_count == 0
        assert result.verifiable_count == 0
