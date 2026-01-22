"""
Test suite for implement_orchestrator.py

Tests the complete orchestration flow for the enhanced [I]mplement option.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Add installer/core/lib to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'installer', 'core', 'lib'))

from implement_orchestrator import (
    ImplementOrchestrator,
    handle_implement_option_sync
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def sample_review_task():
    """Sample review task dictionary."""
    return {
        "id": "TASK-REV-TEST",
        "title": "Review feature workflow streamlining",
        "status": "review_complete",
        "created": "2025-12-04T10:00:00Z",
        "priority": "high",
        "tags": ["feature-workflow", "architecture-review"]
    }


@pytest.fixture
def sample_review_report(temp_dir):
    """Create sample review report with recommendations."""
    report_path = os.path.join(temp_dir, "TASK-REV-TEST-review-report.md")
    content = """# Review Report: TASK-REV-TEST

## Executive Summary

Feature workflow streamlining review completed.

## Recommendations

### Phase 1 Subtasks (Feature Plan Command + Enhanced [I]mplement)

| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| FW-001 | Create /feature-plan command | Direct | 3 | 0.5d |
| FW-002 | Auto-detect feature slug | Direct | 2 | 0.25d |
| FW-003 | Extract subtasks from review | task-work | 5 | 1d |
| FW-004 | Assign implementation modes | task-work | 4 | 0.5d |
| FW-005 | Detect parallel groups | task-work | 6 | 1d |

## Implementation Plan

All tasks should follow the workflow defined in IMPLEMENTATION-GUIDE.md.
"""
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return report_path


class TestImplementOrchestrator:
    """Test ImplementOrchestrator class."""

    def test_init(self, sample_review_task, sample_review_report):
        """Test orchestrator initialization."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        assert orchestrator.review_task == sample_review_task
        assert orchestrator.review_report_path == sample_review_report
        assert orchestrator.feature_slug is None
        assert orchestrator.subtasks == []

    def test_extract_feature_info(self, sample_review_task, sample_review_report):
        """Test feature slug and name extraction."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        orchestrator.extract_feature_info()

        assert orchestrator.feature_slug == "feature-workflow-streamlining"
        assert orchestrator.feature_name == "feature workflow streamlining"

    def test_parse_subtasks(self, sample_review_task, sample_review_report):
        """Test subtask parsing from review report."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        orchestrator.extract_feature_info()
        orchestrator.parse_subtasks()

        assert len(orchestrator.subtasks) == 5
        assert orchestrator.subtasks[0]["id"] == "TASK-FW-001"
        assert orchestrator.subtasks[0]["title"] == "Create /feature-plan command"
        assert orchestrator.subtasks[0]["implementation_mode"] == "direct"
        assert orchestrator.subtasks[0]["complexity"] == 3

    def test_assign_modes(self, sample_review_task, sample_review_report):
        """Test implementation mode assignment."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        orchestrator.extract_feature_info()
        orchestrator.parse_subtasks()

        # Before assign_modes, check that modes may already be set from table parsing
        initial_modes = [s.get("implementation_mode") for s in orchestrator.subtasks]

        orchestrator.assign_modes()

        # Check modes were assigned or preserved
        for subtask in orchestrator.subtasks:
            assert "implementation_mode" in subtask
            assert subtask["implementation_mode"] in ["task-work", "direct", "manual"]
            # Note: complexity_analyzed and risk_level are internal to the analyzer
            # They may not be present on the final subtask objects if already set from table

    def test_detect_parallelism(self, sample_review_task, sample_review_report):
        """Test parallel group detection."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        orchestrator.extract_feature_info()
        orchestrator.parse_subtasks()
        orchestrator.assign_modes()
        orchestrator.detect_parallelism()

        # Check parallel groups were assigned
        for subtask in orchestrator.subtasks:
            assert "parallel_group" in subtask
            assert isinstance(subtask["parallel_group"], int)
            assert subtask["parallel_group"] >= 1

    def test_assign_workspaces(self, sample_review_task, sample_review_report):
        """Test Conductor workspace name assignment."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        orchestrator.extract_feature_info()
        orchestrator.parse_subtasks()
        orchestrator.assign_modes()
        orchestrator.detect_parallelism()
        orchestrator.assign_workspaces()

        # Check workspace names for tasks in same wave
        wave_groups = {}
        for subtask in orchestrator.subtasks:
            wave = subtask.get("parallel_group")
            if wave not in wave_groups:
                wave_groups[wave] = []
            wave_groups[wave].append(subtask)

        # If wave has multiple tasks, they should have workspace names
        for wave, tasks in wave_groups.items():
            if len(tasks) > 1:
                for task in tasks:
                    assert "conductor_workspace" in task
                    if task["conductor_workspace"]:
                        assert "feature-workflow-streamlining" in task["conductor_workspace"]
                        assert f"wave{wave}" in task["conductor_workspace"]

    def test_slugify(self, sample_review_task, sample_review_report):
        """Test slug generation."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )

        # Test various inputs
        assert orchestrator._slugify("Create /feature-plan command") == "create-feature-plan-command"
        assert orchestrator._slugify("Update session management") == "update-session-management"
        assert orchestrator._slugify("Add CSS variables") == "add-css-variables"
        assert orchestrator._slugify("Test  Multiple   Spaces") == "test-multiple-spaces"

    def test_format_files_list(self, sample_review_task, sample_review_report):
        """Test files list formatting."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )

        # Empty list
        assert "No files specified" in orchestrator._format_files_list([])

        # With files
        files = ["src/file1.py", "src/file2.py"]
        formatted = orchestrator._format_files_list(files)
        assert "- `src/file1.py`" in formatted
        assert "- `src/file2.py`" in formatted

    def test_format_dependencies(self, sample_review_task, sample_review_report):
        """Test dependencies formatting."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )

        # Empty list
        assert "No dependencies" in orchestrator._format_dependencies([])

        # With dependencies
        deps = ["TASK-FW-001", "TASK-FW-002"]
        formatted = orchestrator._format_dependencies(deps)
        assert "- TASK-FW-001" in formatted
        assert "- TASK-FW-002" in formatted

    def test_get_implementation_guidance(self, sample_review_task, sample_review_report):
        """Test implementation guidance retrieval."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )

        task_work_guidance = orchestrator._get_implementation_guidance("task-work")
        assert "/task-work" in task_work_guidance
        assert "quality gates" in task_work_guidance

        direct_guidance = orchestrator._get_implementation_guidance("direct")
        assert "directly" in direct_guidance.lower()

        manual_guidance = orchestrator._get_implementation_guidance("manual")
        assert "manually" in manual_guidance.lower()


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_orchestration_flow(
        self,
        sample_review_task,
        sample_review_report,
        capsys
    ):
        """Test complete orchestration flow."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )

        # Run all steps
        orchestrator.extract_feature_info()
        assert orchestrator.feature_slug is not None

        orchestrator.parse_subtasks()
        assert len(orchestrator.subtasks) > 0

        orchestrator.assign_modes()
        for subtask in orchestrator.subtasks:
            assert "implementation_mode" in subtask

        orchestrator.detect_parallelism()
        for subtask in orchestrator.subtasks:
            assert "parallel_group" in subtask

        orchestrator.assign_workspaces()

        # Test display methods don't crash
        orchestrator.display_detection_summary()
        captured = capsys.readouterr()
        assert "Auto-detected Configuration" in captured.out

        # These would create files, but we're mocking
        orchestrator.subfolder_path = "tasks/backlog/test-feature"
        orchestrator.display_summary()
        captured = capsys.readouterr()
        assert "Feature Implementation Structure Created" in captured.out


class TestImplementationPlanGeneration:
    """Test implementation plan generation."""

    def test_generate_implementation_plans_creates_files(
        self,
        sample_review_task,
        sample_review_report,
        temp_dir
    ):
        """Test that generate_implementation_plans creates plan files."""
        # Change to temp directory so plans are created there
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            orchestrator = ImplementOrchestrator(
                sample_review_task,
                sample_review_report
            )
            orchestrator.extract_feature_info()
            orchestrator.parse_subtasks()
            orchestrator.assign_modes()

            # Generate plans
            orchestrator.generate_implementation_plans()

            # Check plans directory was created
            plans_dir = Path(temp_dir) / ".claude" / "task-plans"
            assert plans_dir.exists()

            # Check a plan file was created for each subtask
            for subtask in orchestrator.subtasks:
                task_id = subtask["id"]
                plan_path = plans_dir / f"{task_id}-implementation-plan.md"
                assert plan_path.exists(), f"Plan not found for {task_id}"

                # Verify plan content is >50 chars (validation requirement)
                content = plan_path.read_text()
                assert len(content) > 50, f"Plan for {task_id} is too short"

        finally:
            os.chdir(original_cwd)

    def test_plan_content_structure(
        self,
        sample_review_task,
        sample_review_report,
        temp_dir
    ):
        """Test that generated plans have proper structure."""
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            orchestrator = ImplementOrchestrator(
                sample_review_task,
                sample_review_report
            )
            orchestrator.extract_feature_info()
            orchestrator.parse_subtasks()
            orchestrator.assign_modes()
            orchestrator.generate_implementation_plans()

            # Check first plan's structure
            plans_dir = Path(temp_dir) / ".claude" / "task-plans"
            first_task_id = orchestrator.subtasks[0]["id"]
            plan_path = plans_dir / f"{first_task_id}-implementation-plan.md"
            content = plan_path.read_text()

            # Check required sections
            assert "# Implementation Plan:" in content
            assert "## Task" in content
            assert "## Overview" in content
            assert "## Files to Create/Modify" in content
            assert "## Implementation Approach" in content
            assert "## Dependencies" in content
            assert "## Test Strategy" in content
            assert "## Estimated Effort" in content
            assert "Complexity:" in content
            assert "LOC:" in content
            assert "Duration:" in content

        finally:
            os.chdir(original_cwd)

    def test_format_plan_files_empty(self, sample_review_task, sample_review_report):
        """Test _format_plan_files with empty list."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        result = orchestrator._format_plan_files([])
        assert "will be determined" in result

    def test_format_plan_files_with_files(self, sample_review_task, sample_review_report):
        """Test _format_plan_files with file list."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        files = ["src/module.py", "tests/test_module.py"]
        result = orchestrator._format_plan_files(files)
        assert "`src/module.py`" in result
        assert "`tests/test_module.py`" in result
        assert "Implementation target" in result

    def test_format_plan_dependencies_empty(self, sample_review_task, sample_review_report):
        """Test _format_plan_dependencies with empty list."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        result = orchestrator._format_plan_dependencies([])
        assert result == "None"

    def test_format_plan_dependencies_with_deps(self, sample_review_task, sample_review_report):
        """Test _format_plan_dependencies with dependencies."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        deps = ["TASK-FW-001", "TASK-FW-002"]
        result = orchestrator._format_plan_dependencies(deps)
        assert "TASK-FW-001" in result
        assert "TASK-FW-002" in result

    def test_generate_implementation_approach_task_work(
        self,
        sample_review_task,
        sample_review_report
    ):
        """Test implementation approach for task-work mode."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        subtask = {
            "title": "Test task",
            "description": "Test description",
            "files": ["src/file.py"],
            "implementation_mode": "task-work"
        }
        result = orchestrator._generate_implementation_approach(subtask)
        assert "Review task requirements" in result
        assert "Write unit tests" in result
        assert "code quality" in result

    def test_generate_implementation_approach_direct(
        self,
        sample_review_task,
        sample_review_report
    ):
        """Test implementation approach for direct mode."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        subtask = {
            "title": "Test task",
            "files": [],
            "implementation_mode": "direct"
        }
        result = orchestrator._generate_implementation_approach(subtask)
        assert "Review task requirements" in result
        assert "Verify changes work" in result

    def test_generate_test_strategy_task_work(
        self,
        sample_review_task,
        sample_review_report
    ):
        """Test test strategy for task-work mode."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        result = orchestrator._generate_test_strategy("task-work", [])
        assert "Unit tests" in result
        assert "80%" in result

    def test_generate_test_strategy_direct(
        self,
        sample_review_task,
        sample_review_report
    ):
        """Test test strategy for direct mode."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        result = orchestrator._generate_test_strategy("direct", [])
        assert "Manual verification" in result

    def test_generate_test_strategy_manual(
        self,
        sample_review_task,
        sample_review_report
    ):
        """Test test strategy for manual mode."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        result = orchestrator._generate_test_strategy("manual", [])
        assert "Manual verification required" in result

    def test_estimate_loc(self, sample_review_task, sample_review_report):
        """Test LOC estimation."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        # Low complexity, few files
        result = orchestrator._estimate_loc(3, 1)
        assert result > 0
        assert result < 100

        # High complexity, many files
        result_high = orchestrator._estimate_loc(8, 5)
        assert result_high > result

    def test_estimate_duration(self, sample_review_task, sample_review_report):
        """Test duration estimation."""
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            sample_review_report
        )
        # Simple task
        result = orchestrator._estimate_duration(2)
        assert "30 minutes" in result or "1 hour" in result

        # Complex task
        result = orchestrator._estimate_duration(8)
        assert "4-8 hours" in result


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_missing_review_report(self, sample_review_task, temp_dir):
        """Test handling of missing review report."""
        non_existent_path = os.path.join(temp_dir, "non-existent.md")
        orchestrator = ImplementOrchestrator(
            sample_review_task,
            non_existent_path
        )
        orchestrator.extract_feature_info()

        with pytest.raises(SystemExit):
            orchestrator.parse_subtasks()

    def test_empty_recommendations(self, sample_review_task, temp_dir):
        """Test handling of review report with no recommendations."""
        report_path = os.path.join(temp_dir, "empty-review.md")
        content = """# Review Report

## Executive Summary

No recommendations.
"""
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)

        orchestrator = ImplementOrchestrator(
            sample_review_task,
            report_path
        )
        orchestrator.extract_feature_info()

        with pytest.raises(SystemExit):
            orchestrator.parse_subtasks()


def test_module_imports():
    """Test that all required modules can be imported."""
    from implement_orchestrator import (
        ImplementOrchestrator,
        handle_implement_option,
        handle_implement_option_sync
    )
    assert ImplementOrchestrator is not None
    assert handle_implement_option is not None
    assert handle_implement_option_sync is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
