"""
Unit tests for task_review_orchestrator.py

Tests validation, Phase 1 implementation, and skeleton phase execution.
"""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

import sys

# Add installer lib to path
installer_lib_path = Path(__file__).parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
if installer_lib_path.exists():
    sys.path.insert(0, str(installer_lib_path))

from task_review_orchestrator import (
    validate_review_mode,
    validate_review_depth,
    validate_output_format,
    find_task_file,
    load_review_context,
    execute_review_analysis,
    synthesize_recommendations,
    generate_review_report,
    present_decision_checkpoint,
    execute_task_review,
    VALID_REVIEW_MODES,
    VALID_REVIEW_DEPTHS,
    VALID_OUTPUT_FORMATS
)


class TestValidation:
    """Test validation functions."""

    def test_validate_review_mode_valid(self):
        """Test validation accepts valid review modes."""
        for mode in VALID_REVIEW_MODES:
            validate_review_mode(mode)  # Should not raise

    def test_validate_review_mode_invalid(self):
        """Test validation rejects invalid review modes."""
        with pytest.raises(ValueError, match="Invalid review mode"):
            validate_review_mode("invalid-mode")

    def test_validate_review_depth_valid(self):
        """Test validation accepts valid review depths."""
        for depth in VALID_REVIEW_DEPTHS:
            validate_review_depth(depth)  # Should not raise

    def test_validate_review_depth_invalid(self):
        """Test validation rejects invalid review depths."""
        with pytest.raises(ValueError, match="Invalid review depth"):
            validate_review_depth("invalid-depth")

    def test_validate_output_format_valid(self):
        """Test validation accepts valid output formats."""
        for output in VALID_OUTPUT_FORMATS:
            validate_output_format(output)  # Should not raise

    def test_validate_output_format_invalid(self):
        """Test validation rejects invalid output formats."""
        with pytest.raises(ValueError, match="Invalid output format"):
            validate_output_format("invalid-format")


class TestFindTaskFile:
    """Test task file finding functionality."""

    def setup_method(self):
        """Create temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        # Create task state directories
        for state_dir in ["backlog", "in_progress", "in_review", "review_complete"]:
            (self.tasks_dir / state_dir).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_find_task_file_in_backlog(self):
        """Test finding task in backlog directory."""
        task_file = self.tasks_dir / "backlog" / "TASK-001-test-task.md"
        task_file.write_text("---\nid: TASK-001\n---\n")

        result = find_task_file("TASK-001", self.tasks_dir)
        assert result == task_file

    def test_find_task_file_in_progress(self):
        """Test finding task in in_progress directory."""
        task_file = self.tasks_dir / "in_progress" / "TASK-002-another-task.md"
        task_file.write_text("---\nid: TASK-002\n---\n")

        result = find_task_file("TASK-002", self.tasks_dir)
        assert result == task_file

    def test_find_task_file_not_found(self):
        """Test behavior when task not found."""
        result = find_task_file("TASK-999", self.tasks_dir)
        assert result is None


class TestLoadReviewContext:
    """Test Phase 1: Load Review Context."""

    def setup_method(self):
        """Create temporary task structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()
        (self.tasks_dir / "in_progress").mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_load_review_context_basic(self):
        """Test loading basic review context."""
        task_content = """---
id: TASK-001
title: Review authentication architecture
status: in_progress
task_type: review
review_mode: architectural
---

## Description
Review the current authentication architecture for security issues.

## Review Scope
- Authentication controllers
- JWT token handling
- Password hashing

## Acceptance Criteria
- [ ] Security vulnerabilities identified
- [ ] Recommendations provided
"""
        task_file = self.tasks_dir / "in_progress" / "TASK-001-review.md"
        task_file.write_text(task_content)

        context = load_review_context("TASK-001", self.tasks_dir)

        assert context["task_id"] == "TASK-001"
        assert context["title"] == "Review authentication architecture"
        assert "authentication architecture" in context["description"]
        assert "JWT token handling" in context["review_scope"]
        assert context["metadata"]["task_type"] == "review"

    def test_load_review_context_missing_task(self):
        """Test error when task not found."""
        with pytest.raises(FileNotFoundError, match="Task TASK-999 not found"):
            load_review_context("TASK-999", self.tasks_dir)


class TestSkeletonPhases:
    """Test skeleton implementations of Phases 2-5."""

    def test_execute_review_analysis_returns_structure(self):
        """Test Phase 2 skeleton returns expected structure."""
        context = {"task_id": "TASK-001", "title": "Test"}
        result = execute_review_analysis(context, "architectural", "standard")

        assert "findings" in result
        assert "mode" in result
        assert "depth" in result
        assert result["mode"] == "architectural"
        assert result["depth"] == "standard"

    def test_synthesize_recommendations_returns_structure(self):
        """Test Phase 3 skeleton returns expected structure."""
        review_results = {"findings": [], "mode": "architectural"}
        result = synthesize_recommendations(review_results)

        assert "recommendations" in result
        assert "confidence" in result
        assert "decision_options" in result

    def test_generate_review_report_returns_markdown(self):
        """Test Phase 4 skeleton returns markdown report."""
        review_results = {"mode": "architectural", "depth": "standard"}
        recommendations = {"recommendations": []}
        result = generate_review_report(review_results, recommendations, "detailed")

        assert isinstance(result, str)
        assert "# Review Report" in result
        assert "architectural" in result

    def test_present_decision_checkpoint_returns_decision(self):
        """Test Phase 5 skeleton returns decision."""
        report = "# Test Report"
        recommendations = {"recommendations": []}
        result = present_decision_checkpoint(report, recommendations)

        assert isinstance(result, str)
        assert result in ["accept", "revise", "implement", "cancel"]


class TestExecuteTaskReview:
    """Test main orchestrator function."""

    def setup_method(self):
        """Create temporary task structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()
        (self.tasks_dir / "backlog").mkdir()
        (self.tasks_dir / "in_progress").mkdir()
        (self.tasks_dir / "review_complete").mkdir()

        # Create a test task
        task_content = """---
id: TASK-001
title: Review test architecture
status: backlog
created: 2025-01-20T00:00:00Z
updated: 2025-01-20T00:00:00Z
priority: medium
tags: []
---

## Description
Test review task.

## Review Scope
Test scope.
"""
        self.task_file = self.tasks_dir / "backlog" / "TASK-001-test.md"
        self.task_file.write_text(task_content)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_execute_task_review_basic_success(self):
        """Test basic task review execution with defaults."""
        # Change to temp directory for task file discovery
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            result = execute_task_review("TASK-001")

            assert result["status"] == "success"
            assert result["review_mode"] == "architectural"  # default
            assert result["review_depth"] == "standard"  # default
            assert result["task_id"] == "TASK-001"
            assert "report" in result
        finally:
            os.chdir(original_dir)

    def test_execute_task_review_with_custom_params(self):
        """Test task review with custom parameters."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            result = execute_task_review(
                "TASK-001",
                mode="code-quality",
                depth="comprehensive",
                output="summary"
            )

            assert result["status"] == "success"
            assert result["review_mode"] == "code-quality"
            assert result["review_depth"] == "comprehensive"
        finally:
            os.chdir(original_dir)

    def test_execute_task_review_invalid_mode(self):
        """Test error handling for invalid mode."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            result = execute_task_review("TASK-001", mode="invalid-mode")

            assert result["status"] == "error"
            assert "Invalid review mode" in result["error"]
        finally:
            os.chdir(original_dir)

    def test_execute_task_review_task_not_found(self):
        """Test error handling when task not found."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            result = execute_task_review("TASK-999")

            assert result["status"] == "error"
            assert "not found" in result["error"].lower()
        finally:
            os.chdir(original_dir)


class TestEndToEndWorkflow:
    """Test complete review workflow end-to-end."""

    def setup_method(self):
        """Create temporary task structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()
        (self.tasks_dir / "backlog").mkdir()
        (self.tasks_dir / "in_progress").mkdir()
        (self.tasks_dir / "review_complete").mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_full_workflow_execution(self):
        """Test complete workflow from backlog to review_complete."""
        # Create task
        task_content = """---
id: TASK-E2E
title: End-to-end review test
status: backlog
created: 2025-01-20T00:00:00Z
updated: 2025-01-20T00:00:00Z
priority: high
tags: [test]
---

## Description
Full workflow test.

## Review Scope
Complete system.
"""
        task_file = self.tasks_dir / "backlog" / "TASK-E2E-test.md"
        task_file.write_text(task_content)

        # Execute review
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            result = execute_task_review(
                "TASK-E2E",
                mode="architectural",
                depth="standard",
                output="detailed"
            )

            # Verify success
            assert result["status"] == "success"
            assert result["task_id"] == "TASK-E2E"

            # Verify task moved to review_complete
            review_complete_dir = self.tasks_dir / "review_complete"
            review_files = list(review_complete_dir.glob("TASK-E2E*.md"))
            assert len(review_files) == 1

            # Verify metadata updated
            from task_utils import read_task_file
            metadata, _ = read_task_file(review_files[0])
            assert metadata["status"] == "review_complete"
            assert metadata["task_type"] == "review"
            assert metadata["review_mode"] == "architectural"
            assert metadata["review_depth"] == "standard"

        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
