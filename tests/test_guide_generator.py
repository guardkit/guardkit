"""
Tests for guide_generator.py

Comprehensive test suite achieving ≥90% coverage for implementation guide generation.
"""

import sys
from pathlib import Path
import pytest
from io import StringIO

# Add installer/core/lib to path
lib_path = Path(__file__).parent.parent / "installer" / "core" / "lib"
sys.path.insert(0, str(lib_path))

from guide_generator import (
    generate_guide_content,
    write_guide_to_file,
    SubtaskData,
    _normalize_subtask,
    _format_method,
    _generate_default_rationale,
    _group_tasks_by_wave,
    _calculate_wave_duration,
    _is_parallel,
    _generate_overview,
    _generate_method_legend,
    _generate_conductor_section,
    _generate_task_detail,
    _generate_wave_section,
    _generate_task_matrix,
    _generate_method_breakdown,
    _generate_execution_order,
)


class TestSubtaskNormalization:
    """Test subtask normalization with defaults."""

    def test_normalize_minimal_task(self):
        """Normalize task with only required fields."""
        task = {"id": "TASK-A", "title": "Test Task"}
        normalized = _normalize_subtask(task)

        assert normalized.id == "TASK-A"
        assert normalized.title == "Test Task"
        assert normalized.implementation_method == "task-work"
        assert normalized.complexity == 5
        assert normalized.estimated_effort_days == 1.0
        assert normalized.parallel_group == 1

    def test_normalize_full_task(self):
        """Normalize task with all fields provided."""
        task = {
            "id": "TASK-B",
            "title": "Full Task",
            "implementation_method": "direct",
            "complexity": 7,
            "estimated_effort_days": 2.5,
            "parallel_group": 2,
            "conductor_workspace": "feature-wave2-1",
            "dependencies": ["TASK-A"],
            "rationale": "Custom rationale",
            "execution_command": "custom command",
        }
        normalized = _normalize_subtask(task)

        assert normalized.id == "TASK-B"
        assert normalized.implementation_method == "direct"
        assert normalized.complexity == 7
        assert normalized.estimated_effort_days == 2.5
        assert normalized.parallel_group == 2
        assert normalized.conductor_workspace == "feature-wave2-1"
        assert normalized.dependencies == ["TASK-A"]
        assert normalized.rationale == "Custom rationale"

    def test_normalize_partial_task(self):
        """Normalize task with some fields provided, others defaulted."""
        task = {
            "id": "TASK-C",
            "title": "Partial",
            "complexity": 8,
            "parallel_group": 3,
        }
        normalized = _normalize_subtask(task)

        assert normalized.id == "TASK-C"
        assert normalized.complexity == 8
        assert normalized.parallel_group == 3
        assert normalized.implementation_method == "task-work"  # Default
        assert normalized.estimated_effort_days == 1.0  # Default


class TestMethodFormatting:
    """Test method name formatting."""

    def test_format_task_work(self):
        """Format task-work method."""
        assert _format_method("task-work") == "/task-work"

    def test_format_direct(self):
        """Format direct method."""
        assert _format_method("direct") == "Direct Claude Code"

    def test_format_manual(self):
        """Format manual method."""
        assert _format_method("manual") == "Manual"

    def test_format_unknown_method(self):
        """Unknown method returns as-is."""
        assert _format_method("custom") == "custom"


class TestRationaleGeneration:
    """Test default rationale generation."""

    def test_rationale_task_work(self):
        """Generate rationale for task-work method."""
        rationale = _generate_default_rationale("task-work")
        assert "quality gates" in rationale.lower()

    def test_rationale_direct(self):
        """Generate rationale for direct method."""
        rationale = _generate_default_rationale("direct")
        assert "straightforward" in rationale.lower()

    def test_rationale_manual(self):
        """Generate rationale for manual method."""
        rationale = _generate_default_rationale("manual")
        assert "script" in rationale.lower()

    def test_rationale_unknown(self):
        """Unknown method returns default rationale."""
        rationale = _generate_default_rationale("unknown")
        assert "standard implementation" in rationale.lower()


class TestWaveGrouping:
    """Test wave grouping logic."""

    def test_group_single_wave(self):
        """Group tasks in single wave."""
        tasks = [
            SubtaskData("A", "Task A", parallel_group=1),
            SubtaskData("B", "Task B", parallel_group=1),
            SubtaskData("C", "Task C", parallel_group=1),
        ]
        waves = _group_tasks_by_wave(tasks)

        assert len(waves) == 1
        assert len(waves[1]) == 3

    def test_group_multiple_waves(self):
        """Group tasks across multiple waves."""
        tasks = [
            SubtaskData("A", "Task A", parallel_group=1),
            SubtaskData("B", "Task B", parallel_group=2),
            SubtaskData("C", "Task C", parallel_group=3),
        ]
        waves = _group_tasks_by_wave(tasks)

        assert len(waves) == 3
        assert len(waves[1]) == 1
        assert len(waves[2]) == 1
        assert len(waves[3]) == 1

    def test_group_mixed_waves(self):
        """Group tasks with mixed wave sizes."""
        tasks = [
            SubtaskData("A", "Task A", parallel_group=1),
            SubtaskData("B", "Task B", parallel_group=2),
            SubtaskData("C", "Task C", parallel_group=2),
            SubtaskData("D", "Task D", parallel_group=3),
        ]
        waves = _group_tasks_by_wave(tasks)

        assert len(waves) == 3
        assert len(waves[1]) == 1
        assert len(waves[2]) == 2
        assert len(waves[3]) == 1

    def test_group_empty_list(self):
        """Group empty task list."""
        waves = _group_tasks_by_wave([])
        assert len(waves) == 0


class TestDurationCalculation:
    """Test wave duration calculation."""

    def test_duration_less_than_day(self):
        """Calculate duration < 1 day (returns hours)."""
        tasks = [SubtaskData("A", "A", estimated_effort_days=0.5)]
        duration = _calculate_wave_duration(tasks)
        assert "4.0 hours" == duration

    def test_duration_multiple_days(self):
        """Calculate duration >= 1 day."""
        tasks = [
            SubtaskData("A", "A", estimated_effort_days=1.5),
            SubtaskData("B", "B", estimated_effort_days=2.0),
        ]
        duration = _calculate_wave_duration(tasks)
        assert "3.5 days" == duration

    def test_duration_single_day(self):
        """Calculate duration exactly 1 day."""
        tasks = [SubtaskData("A", "A", estimated_effort_days=1.0)]
        duration = _calculate_wave_duration(tasks)
        assert "1.0 days" == duration

    def test_duration_zero(self):
        """Calculate duration with zero effort."""
        tasks = [SubtaskData("A", "A", estimated_effort_days=0.0)]
        duration = _calculate_wave_duration(tasks)
        assert "0.0 hours" == duration


class TestParallelDetection:
    """Test parallel task detection."""

    def test_parallel_multiple_tasks(self):
        """Multiple tasks in wave are parallel."""
        tasks = [SubtaskData("A", "A"), SubtaskData("B", "B")]
        assert _is_parallel(tasks) is True

    def test_parallel_single_task(self):
        """Single task in wave is sequential."""
        tasks = [SubtaskData("A", "A")]
        assert _is_parallel(tasks) is False

    def test_parallel_many_tasks(self):
        """Many tasks in wave are parallel."""
        tasks = [SubtaskData(f"TASK-{i}", f"Task {i}") for i in range(10)]
        assert _is_parallel(tasks) is True


class TestSectionGeneration:
    """Test individual section generators."""

    def test_generate_overview(self):
        """Generate overview section."""
        overview = _generate_overview("Test Feature", 10)
        assert "Test Feature" in overview
        assert "10 tasks" in overview
        assert "# Test Feature Implementation Guide" in overview

    def test_generate_method_legend(self):
        """Generate method legend section."""
        legend = _generate_method_legend()
        assert "/task-work" in legend
        assert "Direct" in legend
        assert "Manual" in legend
        assert "Implementation Method Legend" in legend

    def test_generate_conductor_section(self):
        """Generate Conductor section."""
        waves = {
            1: [SubtaskData("A", "A")],
            2: [SubtaskData("B", "B"), SubtaskData("C", "C")],
        }
        section = _generate_conductor_section("my-repo", waves)
        assert "Conductor.build" in section
        assert "my-repo" in section
        assert "Wave 1" in section
        assert "Wave 2" in section

    def test_generate_task_detail(self):
        """Generate task detail section."""
        task = SubtaskData("TASK-A", "My Task", complexity=7, estimated_effort_days=2.5)
        detail = _generate_task_detail(task)
        assert "TASK-A" in detail
        assert "My Task" in detail
        assert "7/10" in detail
        assert "2.5 days" in detail

    def test_generate_task_detail_with_rationale(self):
        """Generate task detail with custom rationale."""
        task = SubtaskData("TASK-B", "Task", rationale="Custom reason")
        detail = _generate_task_detail(task)
        assert "Custom reason" in detail

    def test_generate_wave_section(self):
        """Generate complete wave section."""
        tasks = [SubtaskData("A", "Task A", estimated_effort_days=1.5)]
        section = _generate_wave_section(1, tasks, "feature")
        assert "Wave 1" in section
        assert "1.5 days" in section
        assert "### A: Task A" in section

    def test_generate_task_matrix(self):
        """Generate task matrix table."""
        tasks = [
            SubtaskData("A", "Task A", complexity=5, estimated_effort_days=1.0),
            SubtaskData("B", "Task B", complexity=7, estimated_effort_days=2.5),
        ]
        matrix = _generate_task_matrix(tasks)
        assert "| A |" in matrix
        assert "| B |" in matrix
        assert "5" in matrix
        assert "7" in matrix
        assert "1.0d" in matrix
        assert "2.5d" in matrix

    def test_generate_method_breakdown(self):
        """Generate method breakdown summary."""
        tasks = [
            SubtaskData("A", "A", implementation_method="task-work", estimated_effort_days=2.0),
            SubtaskData("B", "B", implementation_method="direct", estimated_effort_days=0.5),
            SubtaskData("C", "C", implementation_method="task-work", estimated_effort_days=1.5),
        ]
        breakdown = _generate_method_breakdown(tasks)
        assert "/task-work" in breakdown
        assert "Direct Claude Code" in breakdown
        assert "2 tasks" in breakdown
        assert "1 tasks" in breakdown

    def test_generate_execution_order(self):
        """Generate execution order section."""
        waves = {
            1: [SubtaskData("A", "A")],
            2: [SubtaskData("B", "B"), SubtaskData("C", "C")],
            3: [SubtaskData("D", "D")],
        }
        order = _generate_execution_order(waves)
        assert "Wave 1: A" in order
        assert "Wave 2: B, C (PARALLEL)" in order
        assert "Wave 3: D" in order


class TestGuideGeneration:
    """Test complete guide generation."""

    def test_generate_guide_minimal(self):
        """Generate guide with minimal tasks."""
        subtasks = [
            {"id": "TASK-A", "title": "Foundation", "parallel_group": 1},
            {"id": "TASK-B", "title": "Feature", "parallel_group": 2},
        ]
        content = generate_guide_content("Test Feature", subtasks)

        assert "Test Feature" in content
        assert "TASK-A" in content
        assert "TASK-B" in content
        assert "Implementation Method Legend" in content
        assert "Conductor Parallel Execution" in content

    def test_generate_guide_two_waves(self):
        """Generate guide with 2 waves."""
        subtasks = [
            {"id": "TASK-A", "title": "A", "parallel_group": 1},
            {"id": "TASK-B", "title": "B", "parallel_group": 1},
            {"id": "TASK-C", "title": "C", "parallel_group": 2},
        ]
        content = generate_guide_content("Feature", subtasks)

        assert "Wave 1" in content
        assert "Wave 2" in content
        assert "3 tasks" in content

    def test_generate_guide_four_waves(self):
        """Generate guide with 4 waves."""
        subtasks = [
            {"id": f"TASK-{i}", "title": f"Task {i}", "parallel_group": (i % 4) + 1}
            for i in range(10)
        ]
        content = generate_guide_content("Multi-Wave Feature", subtasks)

        assert "Wave 1" in content
        assert "Wave 2" in content
        assert "Wave 3" in content
        assert "Wave 4" in content
        assert "10 tasks" in content

    def test_generate_guide_single_task(self):
        """Generate guide with single task."""
        subtasks = [{"id": "TASK-ONLY", "title": "Only Task"}]
        content = generate_guide_content("Single Task", subtasks)

        assert "TASK-ONLY" in content
        assert "1 tasks" in content
        assert "Wave 1" in content

    def test_generate_guide_all_parallel(self):
        """Generate guide with all tasks in single wave (parallel)."""
        subtasks = [
            {"id": f"TASK-{i}", "title": f"Task {i}", "parallel_group": 1}
            for i in range(5)
        ]
        content = generate_guide_content("Parallel Feature", subtasks)

        assert "Wave 1" in content
        # Should not have Wave 2
        assert "Wave 2" not in content
        assert "5 tasks" in content

    def test_generate_guide_with_repo_name(self):
        """Generate guide with custom repo name."""
        subtasks = [{"id": "TASK-A", "title": "Task"}]
        content = generate_guide_content("Feature", subtasks, repo_name="custom-repo")

        assert "custom-repo" in content


class TestFileWriting:
    """Test file writing functionality."""

    def test_write_guide_to_file(self, tmp_path):
        """Write guide content to file."""
        content = "# Test Guide\n\nContent here"
        output_path = tmp_path / "test-guide.md"

        write_guide_to_file(content, str(output_path))

        assert output_path.exists()
        assert output_path.read_text() == content

    def test_write_guide_creates_file(self, tmp_path):
        """Write guide creates new file if not exists."""
        output_path = tmp_path / "new-guide.md"
        assert not output_path.exists()

        write_guide_to_file("Content", str(output_path))

        assert output_path.exists()


class TestIntegration:
    """Integration tests with realistic data."""

    def test_progressive_disclosure_pattern(self):
        """Generate guide following progressive-disclosure pattern."""
        subtasks = [
            {"id": "PD-001", "title": "Foundation", "implementation_method": "task-work",
             "complexity": 7, "estimated_effort_days": 2.5, "parallel_group": 1},
            {"id": "PD-002", "title": "Template", "implementation_method": "direct",
             "complexity": 4, "estimated_effort_days": 0.5, "parallel_group": 1},
            {"id": "PD-003", "title": "Generator", "implementation_method": "task-work",
             "complexity": 6, "estimated_effort_days": 2.0, "parallel_group": 2},
            {"id": "PD-004", "title": "Script", "implementation_method": "direct",
             "complexity": 6, "estimated_effort_days": 1.5, "parallel_group": 2},
        ]

        content = generate_guide_content("Progressive Disclosure", subtasks, repo_name="guardkit")

        # Verify all sections present
        assert "Progressive Disclosure Implementation Guide" in content
        assert "4 tasks" in content
        assert "Implementation Method Legend" in content
        assert "Conductor Parallel Execution" in content
        assert "guardkit" in content
        assert "Wave 1" in content
        assert "Wave 2" in content
        assert "PD-001" in content
        assert "PD-004" in content
        assert "Summary: Task Matrix" in content
        assert "Method Breakdown" in content
        assert "Recommended Execution Order" in content

    def test_feature_workflow_pattern(self):
        """Generate guide for feature-workflow tasks."""
        subtasks = [
            {"id": "TASK-FW-003", "title": "Subtask Definitions", "parallel_group": 1,
             "estimated_effort_days": 1.5},
            {"id": "TASK-FW-004", "title": "Mode Selection", "parallel_group": 1,
             "estimated_effort_days": 1.0},
            {"id": "TASK-FW-005", "title": "Parallel Groups", "parallel_group": 2,
             "conductor_workspace": "feature-workflow-wave2-1", "estimated_effort_days": 2.0},
            {"id": "TASK-FW-006", "title": "Guide Generator", "parallel_group": 2,
             "conductor_workspace": "feature-workflow-wave2-2", "estimated_effort_days": 1.5},
        ]

        content = generate_guide_content("Feature Workflow Streamlining", subtasks)

        # Verify wave structure
        assert "Wave 1" in content
        assert "Wave 2" in content
        # Wave 1 has 2 tasks (parallel)
        assert "(PARALLEL)" in content
        # Tasks with conductor_workspace should show **YES** for parallel
        assert "**YES**" in content  # TASK-FW-005 and TASK-FW-006 have workspaces

    def test_end_to_end_generation(self, tmp_path):
        """Complete end-to-end guide generation and file writing."""
        subtasks = [
            {"id": "TASK-1", "title": "Setup", "parallel_group": 1, "estimated_effort_days": 0.5},
            {"id": "TASK-2", "title": "Core", "implementation_method": "task-work",
             "complexity": 8, "estimated_effort_days": 3.0, "parallel_group": 2},
            {"id": "TASK-3", "title": "Testing", "implementation_method": "direct",
             "complexity": 5, "estimated_effort_days": 1.0, "parallel_group": 3},
        ]

        # Generate content
        content = generate_guide_content("End-to-End Feature", subtasks, repo_name="test-repo")

        # Write to file
        output_path = tmp_path / "IMPLEMENTATION-GUIDE.md"
        write_guide_to_file(content, str(output_path))

        # Verify file contents
        written_content = output_path.read_text()
        assert written_content == content
        assert "End-to-End Feature" in written_content
        assert "test-repo" in written_content
        assert "TASK-1" in written_content
        assert "TASK-2" in written_content
        assert "TASK-3" in written_content
