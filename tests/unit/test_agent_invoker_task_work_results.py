"""Unit tests for AgentInvoker task-work results writing functionality.

This module tests the TaskWorkResult writing capabilities of AgentInvoker,
specifically the _write_task_work_results(), _generate_summary(), and
_validate_file_count_constraint() methods that support Coach validation.

Test Coverage:
- File creation with valid parsed results
- Quality gates data structure validation
- Partial results on timeout handling
- File count constraint validation
- CoachValidator integration readiness
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    DOCUMENTATION_LEVEL_MAX_FILES,
)
from guardkit.orchestrator.paths import TaskArtifactPaths


# ==================== Test Fixtures ====================


@pytest.fixture
def temp_worktree(tmp_path):
    """Create a temporary worktree directory structure."""
    worktree = tmp_path / "test_worktree"
    worktree.mkdir()

    # Create required subdirectories
    (worktree / ".guardkit" / "autobuild").mkdir(parents=True, exist_ok=True)
    (worktree / ".claude" / "task-plans").mkdir(parents=True, exist_ok=True)
    (worktree / "docs" / "state").mkdir(parents=True, exist_ok=True)

    return worktree


@pytest.fixture
def agent_invoker(temp_worktree):
    """Create AgentInvoker instance with temporary worktree."""
    return AgentInvoker(
        worktree_path=temp_worktree,
        max_turns_per_agent=5,
        sdk_timeout_seconds=30,
    )


@pytest.fixture
def valid_result_data():
    """Create a valid result data structure from TaskWorkStreamParser.to_result()."""
    return {
        "tests_passed": 15,
        "tests_failed": 0,
        "coverage": 85.5,
        "quality_gates_passed": True,
        "phases": {
            "phase_3": {"detected": True, "completed": True},
            "phase_4": {"detected": True, "completed": True},
            "phase_4.5": {"detected": True, "completed": True},
        },
        "files_modified": ["src/main.py", "src/utils.py"],
        "files_created": ["tests/test_main.py", "tests/test_utils.py"],
    }


@pytest.fixture
def partial_result_data():
    """Create partial result data (e.g., from timeout)."""
    return {
        "tests_passed": 8,
        "tests_failed": 2,
        "coverage": 72.0,
        "quality_gates_passed": False,
        "phases": {
            "phase_3": {"detected": True, "completed": True},
            "phase_4": {"detected": True, "completed": False},
        },
        "files_modified": ["src/main.py"],
        "files_created": [],
    }


# ==================== Tests for _write_task_work_results ====================


class TestWriteTaskWorkResults:
    """Test suite for _write_task_work_results method."""

    def test_creates_file_with_valid_data(self, agent_invoker, valid_result_data):
        """Test that file is created with valid parsed results."""
        task_id = "TASK-001"
        documentation_level = "standard"

        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, documentation_level
        )

        # Verify file exists
        assert result_path.exists()
        assert result_path.is_file()

        # Verify file location matches expected path
        expected_path = (
            agent_invoker.worktree_path
            / ".guardkit"
            / "autobuild"
            / task_id
            / "task_work_results.json"
        )
        assert result_path == expected_path

    def test_file_contains_valid_json(self, agent_invoker, valid_result_data):
        """Test that written file contains valid JSON."""
        task_id = "TASK-002"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        # Read and parse JSON
        content = result_path.read_text()
        parsed = json.loads(content)

        # Verify it's a dictionary (valid JSON)
        assert isinstance(parsed, dict)

    def test_results_structure_contains_required_fields(
        self, agent_invoker, valid_result_data
    ):
        """Test that results JSON contains all required fields."""
        task_id = "TASK-003"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())

        # Verify required top-level fields
        required_fields = {
            "task_id",
            "timestamp",
            "completed",
            "phases",
            "quality_gates",
            "files_modified",
            "files_created",
            "summary",
        }
        assert required_fields.issubset(results.keys())

    def test_task_id_preserved_in_results(self, agent_invoker, valid_result_data):
        """Test that task_id is correctly preserved in results."""
        task_id = "TASK-CUSTOM-ID"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["task_id"] == task_id

    def test_timestamp_is_valid_iso8601(self, agent_invoker, valid_result_data):
        """Test that timestamp is valid ISO 8601 format."""
        task_id = "TASK-004"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        timestamp = results["timestamp"]

        # Should be parseable as ISO 8601
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pytest.fail(f"Timestamp is not valid ISO 8601: {timestamp}")

    def test_completed_true_when_quality_gates_passed(
        self, agent_invoker, valid_result_data
    ):
        """Test that completed=True when quality_gates_passed=True."""
        task_id = "TASK-005"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["completed"] is True

    def test_completed_false_when_tests_failed(
        self, agent_invoker, partial_result_data
    ):
        """Test that completed=False when tests have failures."""
        task_id = "TASK-006"
        result_path = agent_invoker._write_task_work_results(
            task_id, partial_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["completed"] is False

    def test_creates_parent_directories(self, temp_worktree):
        """Test that parent directories are created if missing."""
        # Start with minimal directory structure
        invoker = AgentInvoker(temp_worktree, max_turns_per_agent=5, sdk_timeout_seconds=30)

        task_id = "TASK-007"
        result_data = {"tests_passed": 5, "tests_failed": 0, "quality_gates_passed": True}

        result_path = invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        # Verify parent directory was created
        assert result_path.parent.exists()
        assert result_path.exists()

    def test_deduplicates_file_lists(self, agent_invoker):
        """Test that files_created and files_modified are deduplicated."""
        task_id = "TASK-008"
        result_data = {
            "tests_passed": 5,
            "tests_failed": 0,
            "files_created": ["file1.py", "file1.py", "file2.py"],
            "files_modified": ["file3.py", "file3.py"],
        }

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())

        # Should be deduplicated and sorted
        assert results["files_created"] == ["file1.py", "file2.py"]
        assert results["files_modified"] == ["file3.py"]

    def test_sorts_file_lists(self, agent_invoker):
        """Test that file lists are sorted."""
        task_id = "TASK-009"
        result_data = {
            "tests_passed": 5,
            "tests_failed": 0,
            "files_created": ["zebra.py", "alpha.py", "beta.py"],
            "files_modified": ["z_file.py", "a_file.py"],
        }

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())

        # Should be alphabetically sorted
        assert results["files_created"] == ["alpha.py", "beta.py", "zebra.py"]
        assert results["files_modified"] == ["a_file.py", "z_file.py"]

    def test_handles_missing_optional_fields(self, agent_invoker):
        """Test that missing optional fields are handled gracefully."""
        task_id = "TASK-010"
        minimal_result_data = {}  # Missing most fields

        result_path = agent_invoker._write_task_work_results(
            task_id, minimal_result_data, "standard"
        )

        results = json.loads(result_path.read_text())

        # Should still have required fields
        assert "task_id" in results
        assert "timestamp" in results
        assert "quality_gates" in results
        assert results["files_created"] == []

    def test_safe_defaults_for_test_metrics(self, agent_invoker):
        """Test that test metrics default to 0."""
        task_id = "TASK-011"
        result_data = {}  # No test data

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        gates = results["quality_gates"]

        assert gates["tests_passed"] == 0
        assert gates["tests_failed"] == 0

    def test_writes_valid_json_formatting(self, agent_invoker, valid_result_data):
        """Test that JSON is properly formatted with indentation."""
        task_id = "TASK-012"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        content = result_path.read_text()

        # Should have indentation (2 spaces)
        assert "\n  " in content or content.count("\n") > 1

    def test_uses_taskartifactpaths_for_location(self, agent_invoker, valid_result_data):
        """Test that file is created at location from TaskArtifactPaths."""
        task_id = "TASK-013"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        expected_path = TaskArtifactPaths.task_work_results_path(
            task_id, agent_invoker.worktree_path
        )

        assert result_path == expected_path


# ==================== Tests for Quality Gates Structure ====================


class TestQualityGatesStructure:
    """Test suite for quality gates data structure in results."""

    def test_quality_gates_has_required_fields(self, agent_invoker, valid_result_data):
        """Test that quality_gates has all required fields."""
        task_id = "TASK-014"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        gates = results["quality_gates"]

        required_fields = {
            "tests_passing",
            "tests_passed",
            "tests_failed",
            "coverage",
            "coverage_met",
            "all_passed",
        }
        assert required_fields.issubset(gates.keys())

    def test_tests_passing_true_when_no_failures(self, agent_invoker, valid_result_data):
        """Test that tests_passing is True when tests_failed is 0."""
        task_id = "TASK-015"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["tests_passing"] is True

    def test_tests_passing_false_when_failures(self, agent_invoker, partial_result_data):
        """Test that tests_passing is False when tests_failed > 0."""
        task_id = "TASK-016"
        result_path = agent_invoker._write_task_work_results(
            task_id, partial_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["tests_passing"] is False

    def test_coverage_met_when_above_threshold(self, agent_invoker, valid_result_data):
        """Test that coverage_met is True when coverage >= 80."""
        task_id = "TASK-017"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["coverage_met"] is True

    def test_coverage_met_false_when_below_threshold(self, agent_invoker, partial_result_data):
        """Test that coverage_met is False when coverage < 80."""
        task_id = "TASK-018"
        result_path = agent_invoker._write_task_work_results(
            task_id, partial_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["coverage_met"] is False

    def test_all_passed_matches_input_quality_gates_passed(
        self, agent_invoker, valid_result_data
    ):
        """Test that all_passed reflects quality_gates_passed."""
        task_id = "TASK-019"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["all_passed"] == valid_result_data["quality_gates_passed"]

    def test_coverage_preserved_in_gates(self, agent_invoker, valid_result_data):
        """Test that coverage value is preserved in quality_gates."""
        task_id = "TASK-020"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["coverage"] == 85.5


# ==================== Tests for _generate_summary ====================


class TestGenerateSummary:
    """Test suite for _generate_summary method."""

    def test_summary_with_complete_data(self, agent_invoker, valid_result_data):
        """Test summary generation with all data present."""
        summary = agent_invoker._generate_summary(valid_result_data)

        assert "15 tests passed" in summary
        assert "85.5% coverage" in summary
        assert "all quality gates passed" in summary

    def test_summary_with_failed_tests(self, agent_invoker, partial_result_data):
        """Test summary includes failed tests."""
        summary = agent_invoker._generate_summary(partial_result_data)

        assert "8 tests passed" in summary
        assert "2 tests failed" in summary

    def test_summary_with_failed_gates(self, agent_invoker):
        """Test summary indicates failed gates."""
        result_data = {
            "tests_passed": 5,
            "quality_gates_passed": False,
        }
        summary = agent_invoker._generate_summary(result_data)

        assert "quality gates failed" in summary

    def test_summary_with_minimal_data(self, agent_invoker):
        """Test summary with minimal data available."""
        result_data = {}
        summary = agent_invoker._generate_summary(result_data)

        # Should return default message
        assert "Implementation completed" in summary

    def test_summary_excludes_zero_tests_passed(self, agent_invoker):
        """Test that 0 passed tests are not included in summary."""
        result_data = {"tests_passed": 0, "tests_failed": 5}
        summary = agent_invoker._generate_summary(result_data)

        assert "0 tests passed" not in summary
        assert "5 tests failed" in summary

    def test_summary_excludes_zero_tests_failed(self, agent_invoker):
        """Test that 0 failed tests are not included in summary."""
        result_data = {"tests_passed": 10, "tests_failed": 0}
        summary = agent_invoker._generate_summary(result_data)

        assert "tests failed" not in summary
        assert "10 tests passed" in summary

    def test_summary_parts_joined_with_commas(self, agent_invoker, valid_result_data):
        """Test that summary parts are joined with commas."""
        summary = agent_invoker._generate_summary(valid_result_data)

        # Should have comma separators between parts
        parts = summary.split(", ")
        assert len(parts) > 1


# ==================== Tests for _validate_file_count_constraint ====================


class TestValidateFileCountConstraint:
    """Test suite for _validate_file_count_constraint method."""

    def test_no_error_when_under_limit(self, agent_invoker, caplog):
        """Test that no warning when files are under limit."""
        task_id = "TASK-021"
        files_created = ["file1.py"]  # Under limit of 2

        agent_invoker._validate_file_count_constraint(
            task_id, "minimal", files_created
        )

        # Should not log a warning
        assert "constraint violated" not in caplog.text.lower()

    def test_no_error_when_at_limit(self, agent_invoker, caplog):
        """Test that no warning when files equal limit."""
        task_id = "TASK-022"
        files_created = ["file1.py", "file2.py"]  # Exactly at limit

        agent_invoker._validate_file_count_constraint(
            task_id, "minimal", files_created
        )

        assert "constraint violated" not in caplog.text.lower()

    def test_warning_when_over_limit(self, agent_invoker, caplog):
        """Test that warning is logged when over limit."""
        task_id = "TASK-023"
        files_created = ["file1.py", "file2.py", "file3.py"]  # Over limit

        agent_invoker._validate_file_count_constraint(
            task_id, "minimal", files_created
        )

        # Should log a warning
        assert "constraint violated" in caplog.text.lower()
        assert task_id in caplog.text

    def test_comprehensive_level_has_no_limit(self, agent_invoker, caplog):
        """Test that comprehensive level has no limit."""
        task_id = "TASK-024"
        files_created = [f"file{i}.py" for i in range(100)]

        agent_invoker._validate_file_count_constraint(
            task_id, "comprehensive", files_created
        )

        # Should not log a warning
        assert "constraint violated" not in caplog.text.lower()

    def test_standard_level_limit_is_two(self, agent_invoker, caplog):
        """Test that standard level has limit of 2."""
        task_id = "TASK-025"
        files_created = ["file1.py", "file2.py", "file3.py"]

        agent_invoker._validate_file_count_constraint(
            task_id, "standard", files_created
        )

        assert "constraint violated" in caplog.text.lower()
        assert "3 files" in caplog.text
        assert "max allowed 2" in caplog.text

    def test_warning_includes_file_preview(self, agent_invoker, caplog):
        """Test that warning includes preview of files."""
        task_id = "TASK-026"
        files_created = ["file1.py", "file2.py", "file3.py"]

        agent_invoker._validate_file_count_constraint(
            task_id, "minimal", files_created
        )

        # Should show first 5 files
        assert "file1.py" in caplog.text

    def test_warning_shows_ellipsis_for_many_files(self, agent_invoker, caplog):
        """Test that warning shows ellipsis when more than 5 files."""
        task_id = "TASK-027"
        files_created = [f"file{i}.py" for i in range(10)]

        agent_invoker._validate_file_count_constraint(
            task_id, "minimal", files_created
        )

        assert "..." in caplog.text

    def test_unknown_level_treated_as_no_limit(self, agent_invoker, caplog):
        """Test that unknown documentation level has no limit."""
        task_id = "TASK-028"
        files_created = [f"file{i}.py" for i in range(50)]

        agent_invoker._validate_file_count_constraint(
            task_id, "unknown_level", files_created
        )

        # Should not log a warning
        assert "constraint violated" not in caplog.text.lower()

    def test_documentation_level_constants_correct(self):
        """Test that DOCUMENTATION_LEVEL_MAX_FILES has expected values."""
        assert DOCUMENTATION_LEVEL_MAX_FILES["minimal"] == 2
        assert DOCUMENTATION_LEVEL_MAX_FILES["standard"] == 2
        assert DOCUMENTATION_LEVEL_MAX_FILES["comprehensive"] is None


# ==================== Tests for Timeout/Partial Results ====================


class TestPartialResultsOnTimeout:
    """Test suite for handling partial results on timeout."""

    def test_partial_result_still_creates_file(self, agent_invoker, partial_result_data):
        """Test that file is created even with partial data."""
        task_id = "TASK-029"
        result_path = agent_invoker._write_task_work_results(
            task_id, partial_result_data, "standard"
        )

        assert result_path.exists()
        assert result_path.stat().st_size > 0

    def test_partial_result_marked_incomplete(self, agent_invoker, partial_result_data):
        """Test that partial results are marked as incomplete."""
        task_id = "TASK-030"
        result_path = agent_invoker._write_task_work_results(
            task_id, partial_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["completed"] is False

    def test_partial_result_contains_phases(self, agent_invoker, partial_result_data):
        """Test that partial results include detected phases."""
        task_id = "TASK-031"
        result_path = agent_invoker._write_task_work_results(
            task_id, partial_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert "phase_3" in results["phases"]
        assert "phase_4" in results["phases"]

    def test_partial_result_with_no_files_created(self, agent_invoker):
        """Test handling of partial result with no files created."""
        task_id = "TASK-032"
        result_data = {
            "tests_passed": 3,
            "tests_failed": 0,
            "files_created": [],
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["files_created"] == []
        assert results["files_modified"] == ["src/main.py"]


# ==================== Integration Tests ====================


class TestCoachValidatorIntegration:
    """Test suite for CoachValidator integration readiness."""

    def test_results_can_be_read_and_parsed(self, agent_invoker, valid_result_data):
        """Test that written results can be read and parsed by consumer."""
        task_id = "TASK-033"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        # Simulate Coach reading the file
        with open(result_path, "r") as f:
            coach_results = json.load(f)

        # Verify structure
        assert coach_results["task_id"] == task_id
        assert isinstance(coach_results["quality_gates"], dict)
        assert isinstance(coach_results["files_created"], list)

    def test_results_path_matches_taskartifactpaths_contract(
        self, agent_invoker, valid_result_data
    ):
        """Test that results path matches TaskArtifactPaths contract."""
        task_id = "TASK-034"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        # Verify path matches expected format
        assert ".guardkit" in str(result_path)
        assert "autobuild" in str(result_path)
        assert task_id in str(result_path)
        assert "task_work_results.json" in str(result_path)

    def test_results_include_all_fields_for_coach_decision(
        self, agent_invoker, valid_result_data
    ):
        """Test that results include fields needed for Coach decision making."""
        task_id = "TASK-035"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())

        # Coach needs these for decision
        coach_required_fields = {
            "task_id",
            "completed",
            "quality_gates",
            "summary",
            "files_created",
        }
        assert coach_required_fields.issubset(results.keys())

    def test_quality_gates_all_passed_field_guides_coach_decision(
        self, agent_invoker, valid_result_data
    ):
        """Test that quality_gates.all_passed field guides Coach's decision."""
        task_id = "TASK-036"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())

        # Coach uses this field to decide approval
        assert "all_passed" in results["quality_gates"]
        assert isinstance(results["quality_gates"]["all_passed"], bool)

    def test_summary_text_useful_for_coach_rationale(
        self, agent_invoker, valid_result_data
    ):
        """Test that summary is useful for Coach's decision rationale."""
        task_id = "TASK-037"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        summary = results["summary"]

        # Summary should be meaningful, not empty
        assert len(summary) > 0
        assert summary != ""


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_handles_none_values_in_result_data(self, agent_invoker):
        """Test that None values in result data are handled."""
        task_id = "TASK-038"
        result_data = {
            "tests_passed": None,
            "tests_failed": None,
            "coverage": None,
            "quality_gates_passed": None,
        }

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        gates = results["quality_gates"]

        # Should handle None gracefully
        assert "all_passed" in gates

    def test_handles_empty_file_lists(self, agent_invoker):
        """Test handling of empty file creation and modification lists."""
        task_id = "TASK-039"
        result_data = {
            "tests_passed": 5,
            "files_created": [],
            "files_modified": [],
        }

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert results["files_created"] == []
        assert results["files_modified"] == []

    def test_handles_very_large_file_lists(self, agent_invoker):
        """Test handling of very large file lists."""
        task_id = "TASK-040"
        result_data = {
            "tests_passed": 100,
            "files_created": [f"file_{i}.py" for i in range(500)],
            "files_modified": [f"src_file_{i}.py" for i in range(300)],
        }

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert len(results["files_created"]) == 500
        assert len(results["files_modified"]) == 300

    def test_handles_special_characters_in_file_paths(self, agent_invoker):
        """Test handling of special characters in file paths."""
        task_id = "TASK-041"
        result_data = {
            "tests_passed": 5,
            "files_created": [
                "path/with spaces/file.py",
                "path/with-dashes/file.py",
                "path/with_underscores/file.py",
            ],
        }

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert len(results["files_created"]) == 3

    def test_handles_unicode_in_result_data(self, agent_invoker):
        """Test handling of unicode characters in result data."""
        task_id = "TASK-042"
        result_data = {
            "tests_passed": 5,
            "files_created": ["файл.py", "文件.py", "αρχείο.py"],
        }

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        assert "файл.py" in results["files_created"]

    def test_handles_very_long_coverage_precision(self, agent_invoker):
        """Test handling of coverage with many decimal places."""
        task_id = "TASK-043"
        result_data = {
            "tests_passed": 5,
            "coverage": 85.12345678901234567890,
        }

        result_path = agent_invoker._write_task_work_results(
            task_id, result_data, "standard"
        )

        results = json.loads(result_path.read_text())
        # Should preserve the value
        assert results["quality_gates"]["coverage"] > 85


# ==================== Return Value Tests ====================


class TestReturnValue:
    """Test suite for method return values."""

    def test_write_task_work_results_returns_path(self, agent_invoker, valid_result_data):
        """Test that _write_task_work_results returns the Path to written file."""
        task_id = "TASK-044"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        assert isinstance(result_path, Path)
        assert result_path.exists()

    def test_returned_path_is_absolute(self, agent_invoker, valid_result_data):
        """Test that returned path is absolute."""
        task_id = "TASK-045"
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_result_data, "standard"
        )

        assert result_path.is_absolute()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
