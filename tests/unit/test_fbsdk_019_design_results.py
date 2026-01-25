"""Unit tests for TASK-FBSDK-019: Design results persistence and merge logic.

This module tests the design results functionality added in TASK-FBSDK-019:
- TaskArtifactPaths.design_results_path() for path resolution
- AgentInvoker._read_json_artifact() for JSON reading with error handling
- AgentInvoker._write_design_results() for persisting Phase 2.5B results
- AgentInvoker._read_design_results() for loading design results
- AgentInvoker._write_task_work_results() merge logic for implement-only mode

Test Coverage:
- Path resolution for design_results.json
- Design results file creation and schema
- Reading design results (success and error cases)
- Merging design results into task_work_results.json
- Edge cases: missing files, invalid JSON, pre-loop disabled

Coverage Target: >=80%
Test Count: 15+ tests
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
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
def valid_design_data():
    """Create valid design phase results data."""
    return {
        "architectural_review": {
            "score": 75,
            "solid_score": 8,
            "dry_score": 9,
            "yagni_score": 8,
        },
        "complexity_score": 5,
    }


@pytest.fixture
def valid_task_work_data():
    """Create valid task-work results data for merging."""
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


# ==================== Tests for TaskArtifactPaths.design_results_path ====================


class TestDesignResultsPath:
    """Test suite for design_results_path method."""

    def test_design_results_path_returns_correct_path(self, tmp_path):
        """Test design_results_path returns correct path format."""
        task_id = "TASK-001"
        result = TaskArtifactPaths.design_results_path(task_id, tmp_path)

        expected = tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "design_results.json"
        assert result == expected

    def test_design_results_path_with_complex_task_id(self, tmp_path):
        """Test design_results_path with prefix-based task ID."""
        task_id = "TASK-E01-a3f2"
        result = TaskArtifactPaths.design_results_path(task_id, tmp_path)

        expected = tmp_path / ".guardkit" / "autobuild" / "TASK-E01-a3f2" / "design_results.json"
        assert result == expected

    def test_design_results_path_in_autobuild_dir(self, tmp_path):
        """Test design_results_path is within autobuild directory."""
        task_id = "TASK-001"
        design_path = TaskArtifactPaths.design_results_path(task_id, tmp_path)
        autobuild_dir = TaskArtifactPaths.autobuild_dir(task_id, tmp_path)

        assert design_path.parent == autobuild_dir


# ==================== Tests for AgentInvoker._read_json_artifact ====================


class TestReadJsonArtifact:
    """Test suite for _read_json_artifact helper method."""

    def test_read_json_artifact_returns_dict_for_valid_file(self, agent_invoker, temp_worktree):
        """Test _read_json_artifact returns parsed dict for valid JSON file."""
        # Create valid JSON artifact
        artifact_path = temp_worktree / "test_artifact.json"
        test_data = {"key": "value", "number": 42}
        artifact_path.write_text(json.dumps(test_data))

        result = agent_invoker._read_json_artifact(artifact_path)

        assert result == test_data
        assert result["key"] == "value"
        assert result["number"] == 42

    def test_read_json_artifact_returns_none_for_missing_file(self, agent_invoker, temp_worktree):
        """Test _read_json_artifact returns None when file doesn't exist."""
        artifact_path = temp_worktree / "nonexistent.json"

        result = agent_invoker._read_json_artifact(artifact_path)

        assert result is None

    def test_read_json_artifact_returns_none_for_invalid_json(self, agent_invoker, temp_worktree):
        """Test _read_json_artifact returns None for invalid JSON."""
        artifact_path = temp_worktree / "invalid.json"
        artifact_path.write_text("{invalid json content")

        result = agent_invoker._read_json_artifact(artifact_path)

        assert result is None

    def test_read_json_artifact_handles_io_error(self, agent_invoker, temp_worktree):
        """Test _read_json_artifact handles IO errors gracefully."""
        # Create a directory instead of file (causes IO error on read)
        artifact_path = temp_worktree / "dir_not_file.json"
        artifact_path.mkdir()

        result = agent_invoker._read_json_artifact(artifact_path)

        assert result is None


# ==================== Tests for AgentInvoker._write_design_results ====================


class TestWriteDesignResults:
    """Test suite for _write_design_results method."""

    def test_write_design_results_creates_file(self, agent_invoker, valid_design_data):
        """Test _write_design_results creates design_results.json file."""
        task_id = "TASK-001"

        result_path = agent_invoker._write_design_results(task_id, valid_design_data)

        assert result_path.exists()
        assert result_path.name == "design_results.json"

    def test_write_design_results_has_correct_schema(self, agent_invoker, valid_design_data):
        """Test _write_design_results creates file with correct schema."""
        task_id = "TASK-001"

        result_path = agent_invoker._write_design_results(task_id, valid_design_data)

        # Read and verify content
        content = json.loads(result_path.read_text())
        assert "architectural_review" in content
        assert "complexity_score" in content
        assert content["architectural_review"]["score"] == 75
        assert content["complexity_score"] == 5

    def test_write_design_results_extracts_relevant_fields(self, agent_invoker):
        """Test _write_design_results extracts only architectural_review and complexity_score."""
        task_id = "TASK-001"
        full_result_data = {
            "architectural_review": {"score": 80},
            "complexity_score": 7,
            "tests_passed": 10,  # Should NOT be included
            "coverage": 90.0,  # Should NOT be included
        }

        result_path = agent_invoker._write_design_results(task_id, full_result_data)

        content = json.loads(result_path.read_text())
        assert "architectural_review" in content
        assert "complexity_score" in content
        assert "tests_passed" not in content
        assert "coverage" not in content

    def test_write_design_results_is_idempotent(self, agent_invoker, valid_design_data):
        """Test _write_design_results overwrites existing file (idempotent)."""
        task_id = "TASK-001"

        # Write first time
        first_path = agent_invoker._write_design_results(task_id, valid_design_data)
        first_content = first_path.read_text()

        # Write second time with different data
        updated_data = {
            "architectural_review": {"score": 90},
            "complexity_score": 8,
        }
        second_path = agent_invoker._write_design_results(task_id, updated_data)

        # Should be same path, different content
        assert first_path == second_path
        second_content = second_path.read_text()
        assert first_content != second_content

        # Verify updated content
        content = json.loads(second_content)
        assert content["architectural_review"]["score"] == 90

    def test_write_design_results_creates_autobuild_dir(self, agent_invoker):
        """Test _write_design_results creates autobuild directory if missing."""
        task_id = "TASK-NEW"
        design_data = {
            "architectural_review": {"score": 75},
            "complexity_score": 5,
        }

        # Autobuild dir shouldn't exist yet
        autobuild_dir = TaskArtifactPaths.autobuild_dir(task_id, agent_invoker.worktree_path)
        assert not autobuild_dir.exists()

        # Write design results
        result_path = agent_invoker._write_design_results(task_id, design_data)

        # Directory should now exist
        assert autobuild_dir.exists()
        assert result_path.parent == autobuild_dir


# ==================== Tests for AgentInvoker._read_design_results ====================


class TestReadDesignResults:
    """Test suite for _read_design_results method."""

    def test_read_design_results_returns_data_when_file_exists(self, agent_invoker, valid_design_data):
        """Test _read_design_results returns data when file exists."""
        task_id = "TASK-001"

        # Write design results first
        agent_invoker._write_design_results(task_id, valid_design_data)

        # Read back
        result = agent_invoker._read_design_results(task_id)

        assert result is not None
        assert result["architectural_review"]["score"] == 75
        assert result["complexity_score"] == 5

    def test_read_design_results_returns_none_when_file_missing(self, agent_invoker):
        """Test _read_design_results returns None when pre-loop disabled (no file)."""
        task_id = "TASK-NO-DESIGN"

        result = agent_invoker._read_design_results(task_id)

        assert result is None

    def test_read_design_results_returns_none_for_invalid_json(self, agent_invoker):
        """Test _read_design_results returns None when file has invalid JSON."""
        task_id = "TASK-001"

        # Create autobuild dir and write invalid JSON
        autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, agent_invoker.worktree_path)
        design_file = autobuild_dir / "design_results.json"
        design_file.write_text("{invalid json")

        result = agent_invoker._read_design_results(task_id)

        assert result is None


# ==================== Tests for _write_task_work_results Merge Logic ====================


class TestTaskWorkResultsMerge:
    """Test suite for design results merge logic in _write_task_work_results."""

    @patch.object(AgentInvoker, "_generate_summary")
    @patch.object(AgentInvoker, "_validate_file_count_constraint")
    def test_write_task_work_results_merges_design_results(
        self,
        mock_validate,
        mock_summary,
        agent_invoker,
        valid_task_work_data,
        valid_design_data,
    ):
        """Test _write_task_work_results merges design results when available."""
        task_id = "TASK-001"
        mock_summary.return_value = "Implementation completed successfully"

        # Write design results first (simulate pre-loop)
        agent_invoker._write_design_results(task_id, valid_design_data)

        # Write task-work results (implement-only mode)
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_task_work_data, documentation_level="standard"
        )

        # Read merged results
        content = json.loads(result_path.read_text())

        # Verify design results were merged
        assert "architectural_review" in content
        assert content["architectural_review"]["score"] == 75
        assert content["complexity_score"] == 5

        # Verify task-work results still present (in quality_gates structure)
        assert "quality_gates" in content
        assert content["quality_gates"]["tests_passed"] == 15
        assert content["quality_gates"]["all_passed"] is True

    @patch.object(AgentInvoker, "_generate_summary")
    @patch.object(AgentInvoker, "_validate_file_count_constraint")
    def test_write_task_work_results_works_without_design_results(
        self,
        mock_validate,
        mock_summary,
        agent_invoker,
        valid_task_work_data,
    ):
        """Test _write_task_work_results works when pre-loop disabled (no design file)."""
        task_id = "TASK-NO-PRELOOP"
        mock_summary.return_value = "Implementation completed successfully"

        # Write task-work results WITHOUT pre-loop design results
        result_path = agent_invoker._write_task_work_results(
            task_id, valid_task_work_data, documentation_level="standard"
        )

        # Read results
        content = json.loads(result_path.read_text())

        # Should still work, just without architectural_review from design phase
        assert "quality_gates" in content
        assert content["quality_gates"]["tests_passed"] == 15
        # architectural_review may be absent or have default values from task_work_data

    @patch.object(AgentInvoker, "_generate_summary")
    @patch.object(AgentInvoker, "_validate_file_count_constraint")
    def test_write_task_work_results_design_merge_overwrites(
        self,
        mock_validate,
        mock_summary,
        agent_invoker,
        valid_design_data,
    ):
        """Test design results overwrite task-work architectural_review if both present."""
        task_id = "TASK-001"
        mock_summary.return_value = "Implementation completed successfully"

        # Task-work data with different architectural_review (should be overwritten)
        task_work_data = {
            "tests_passed": 15,
            "tests_failed": 0,
            "architectural_review": {"score": 50},  # Lower score from task-work
            "complexity_score": 3,  # Different complexity
        }

        # Write design results (higher score from pre-loop)
        agent_invoker._write_design_results(task_id, valid_design_data)

        # Write task-work results
        result_path = agent_invoker._write_task_work_results(
            task_id, task_work_data, documentation_level="standard"
        )

        # Read merged results
        content = json.loads(result_path.read_text())

        # Design results should overwrite task-work results
        assert content["architectural_review"]["score"] == 75  # From design_results
        assert content["complexity_score"] == 5  # From design_results


# ==================== Tests for Edge Cases ====================


class TestEdgeCases:
    """Test suite for edge cases and error scenarios."""

    def test_design_results_path_constant_exists(self):
        """Test DESIGN_RESULTS constant is defined in TaskArtifactPaths."""
        assert hasattr(TaskArtifactPaths, "DESIGN_RESULTS")
        assert "{task_id}" in TaskArtifactPaths.DESIGN_RESULTS

    def test_write_design_results_handles_missing_fields(self, agent_invoker):
        """Test _write_design_results handles missing architectural_review or complexity_score."""
        task_id = "TASK-PARTIAL"

        # Data with missing architectural_review
        partial_data = {
            "complexity_score": 5,
            # architectural_review is missing
        }

        result_path = agent_invoker._write_design_results(task_id, partial_data)
        content = json.loads(result_path.read_text())

        # Should still create file with empty architectural_review
        assert "architectural_review" in content
        assert content["architectural_review"] == {}
        assert content["complexity_score"] == 5

    def test_write_design_results_handles_empty_result_data(self, agent_invoker):
        """Test _write_design_results handles empty result_data dict."""
        task_id = "TASK-EMPTY"

        result_path = agent_invoker._write_design_results(task_id, {})
        content = json.loads(result_path.read_text())

        # Should create minimal valid file
        assert "architectural_review" in content
        assert "complexity_score" in content
        assert content["architectural_review"] == {}
        assert content["complexity_score"] is None
