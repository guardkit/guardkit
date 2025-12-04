"""
Tests for parallel_analyzer module

Tests cover:
- Input validation
- File conflict detection
- Wave assignment algorithm
- Dependency handling
- Workspace name generation
- Edge cases
"""

import sys
from pathlib import Path
import pytest

# Add installer/global/lib to path
lib_path = Path(__file__).parent.parent / "installer" / "global" / "lib"
sys.path.insert(0, str(lib_path))

from parallel_analyzer import (
    detect_parallel_groups,
    generate_workspace_names,
    analyze_file_conflicts,
    _build_file_to_tasks_mapping,
    _build_conflict_graph,
    _validate_subtasks,
    _validate_dependencies,
)


class TestInputValidation:
    """Test input validation and error handling."""

    def test_validate_subtasks_valid_input(self):
        """Valid input should not raise errors."""
        subtasks = [
            {"id": "A", "files": ["f1.py"]},
            {"id": "B", "files": ["f2.py"]},
        ]
        _validate_subtasks(subtasks)  # Should not raise

    def test_validate_subtasks_not_list(self):
        """Non-list input should raise TypeError."""
        with pytest.raises(TypeError, match="must be a list"):
            _validate_subtasks("not a list")

    def test_validate_subtasks_missing_id(self):
        """Task missing 'id' field should raise ValueError."""
        subtasks = [{"files": ["f1.py"]}]
        with pytest.raises(ValueError, match="missing required 'id' field"):
            _validate_subtasks(subtasks)

    def test_validate_subtasks_invalid_files_type(self):
        """Files field must be a list."""
        subtasks = [{"id": "A", "files": "f1.py"}]
        with pytest.raises(TypeError, match="'files' must be a list"):
            _validate_subtasks(subtasks)

    def test_validate_subtasks_invalid_dependencies_type(self):
        """Dependencies field must be a list."""
        subtasks = [{"id": "A", "dependencies": "B"}]
        with pytest.raises(TypeError, match="'dependencies' must be a list"):
            _validate_subtasks(subtasks)

    def test_validate_dependencies_nonexistent(self):
        """Dependencies must reference existing tasks."""
        subtasks = [
            {"id": "A", "dependencies": ["B"]},
            {"id": "C", "dependencies": []},
        ]
        with pytest.raises(ValueError, match="dependency 'B' does not exist"):
            _validate_dependencies(subtasks)

    def test_validate_dependencies_valid(self):
        """Valid dependencies should not raise errors."""
        subtasks = [
            {"id": "A", "dependencies": []},
            {"id": "B", "dependencies": ["A"]},
        ]
        _validate_dependencies(subtasks)  # Should not raise

    def test_empty_list_input(self):
        """Empty list should return empty list."""
        result = detect_parallel_groups([])
        assert result == []


class TestFileToTasksMapping:
    """Test file-to-tasks mapping construction."""

    def test_simple_mapping(self):
        """Basic file-to-tasks mapping."""
        subtasks = [
            {"id": "A", "files": ["f1.py"]},
            {"id": "B", "files": ["f2.py"]},
        ]
        mapping = _build_file_to_tasks_mapping(subtasks)
        assert mapping["f1.py"] == {"A"}
        assert mapping["f2.py"] == {"B"}

    def test_overlapping_files(self):
        """Multiple tasks touching same file."""
        subtasks = [
            {"id": "A", "files": ["f1.py", "f2.py"]},
            {"id": "B", "files": ["f2.py", "f3.py"]},
        ]
        mapping = _build_file_to_tasks_mapping(subtasks)
        assert mapping["f2.py"] == {"A", "B"}

    def test_empty_files_list(self):
        """Tasks with no files should not appear in mapping."""
        subtasks = [
            {"id": "A", "files": []},
            {"id": "B", "files": ["f1.py"]},
        ]
        mapping = _build_file_to_tasks_mapping(subtasks)
        assert "A" not in str(mapping)
        assert mapping["f1.py"] == {"B"}

    def test_filter_invalid_files(self):
        """Invalid file paths should be filtered out."""
        subtasks = [
            {"id": "A", "files": ["f1.py", None, "", 123, "f2.py"]},
        ]
        mapping = _build_file_to_tasks_mapping(subtasks)
        assert mapping == {"f1.py": {"A"}, "f2.py": {"A"}}


class TestConflictGraph:
    """Test conflict graph construction."""

    def test_no_conflicts(self):
        """Tasks with different files have no conflicts."""
        file_to_tasks = {
            "f1.py": {"A"},
            "f2.py": {"B"},
        }
        conflicts = _build_conflict_graph(file_to_tasks)
        assert conflicts == {}

    def test_simple_conflict(self):
        """Two tasks sharing a file conflict."""
        file_to_tasks = {
            "f1.py": {"A", "B"},
        }
        conflicts = _build_conflict_graph(file_to_tasks)
        assert conflicts["A"] == {"B"}
        assert conflicts["B"] == {"A"}

    def test_multiple_conflicts(self):
        """Task conflicting with multiple others."""
        file_to_tasks = {
            "f1.py": {"A", "B"},
            "f2.py": {"B", "C"},
        }
        conflicts = _build_conflict_graph(file_to_tasks)
        assert conflicts["B"] == {"A", "C"}

    def test_three_way_conflict(self):
        """Three tasks sharing same file."""
        file_to_tasks = {
            "f1.py": {"A", "B", "C"},
        }
        conflicts = _build_conflict_graph(file_to_tasks)
        assert conflicts["A"] == {"B", "C"}
        assert conflicts["B"] == {"A", "C"}
        assert conflicts["C"] == {"A", "B"}


class TestWaveAssignment:
    """Test wave assignment algorithm."""

    def test_no_conflicts_all_parallel(self):
        """Tasks with no conflicts should be in Wave 1."""
        subtasks = [
            {"id": "A", "files": ["f1.py"]},
            {"id": "B", "files": ["f2.py"]},
            {"id": "C", "files": ["f3.py"]},
        ]
        result = detect_parallel_groups(subtasks)

        # All should be in Wave 1 (parallel_group=1)
        assert all(t["parallel_group"] == 1 for t in result)

    def test_simple_file_conflict(self):
        """Tasks with file conflict go in different waves."""
        subtasks = [
            {"id": "A", "files": ["f1.py", "f2.py"]},
            {"id": "B", "files": ["f2.py", "f3.py"]},
            {"id": "C", "files": ["f4.py"]},
        ]
        result = detect_parallel_groups(subtasks)

        # A and C should be in Wave 1 (parallel)
        # B should be in Wave 2 (conflicts with A)
        task_by_id = {t["id"]: t for t in result}

        # A has most files, so goes in Wave 1
        assert task_by_id["A"]["parallel_group"] == 1
        # C has no conflicts, so also in Wave 1
        assert task_by_id["C"]["parallel_group"] == 1
        # B conflicts with A, so Wave 2
        assert task_by_id["B"]["parallel_group"] == 2

    def test_chain_dependency(self):
        """Chain of dependencies results in sequential waves."""
        subtasks = [
            {"id": "A", "files": ["f1.py"], "dependencies": []},
            {"id": "B", "files": ["f2.py"], "dependencies": ["A"]},
            {"id": "C", "files": ["f3.py"], "dependencies": ["B"]},
        ]
        result = detect_parallel_groups(subtasks)

        task_by_id = {t["id"]: t for t in result}

        # Each task in separate wave due to dependencies
        # All get wave numbers even though alone in their waves
        assert task_by_id["A"]["parallel_group"] == 1  # Wave 1
        assert task_by_id["B"]["parallel_group"] == 2  # Wave 2
        assert task_by_id["C"]["parallel_group"] == 3  # Wave 3

    def test_diamond_dependency(self):
        """Diamond dependency pattern."""
        subtasks = [
            {"id": "A", "files": ["f1.py"], "dependencies": []},
            {"id": "B", "files": ["f2.py"], "dependencies": ["A"]},
            {"id": "C", "files": ["f3.py"], "dependencies": ["A"]},
            {"id": "D", "files": ["f4.py"], "dependencies": ["B", "C"]},
        ]
        result = detect_parallel_groups(subtasks)

        task_by_id = {t["id"]: t for t in result}

        # A in Wave 1 (alone, but gets wave number)
        assert task_by_id["A"]["parallel_group"] == 1

        # B and C in Wave 2 (parallel, both depend on A)
        assert task_by_id["B"]["parallel_group"] == 2
        assert task_by_id["C"]["parallel_group"] == 2

        # D in Wave 3 (depends on B and C, alone but gets wave number)
        assert task_by_id["D"]["parallel_group"] == 3

    def test_task_sorting_by_file_count(self):
        """Tasks with more files should be assigned first."""
        subtasks = [
            {"id": "A", "files": ["f1.py"]},
            {"id": "B", "files": ["f1.py", "f2.py", "f3.py"]},
            {"id": "C", "files": ["f4.py"]},
        ]
        result = detect_parallel_groups(subtasks)

        task_by_id = {t["id"]: t for t in result}

        # B has most files, should be in Wave 1
        assert task_by_id["B"]["parallel_group"] == 1
        # C has no conflicts, also in Wave 1
        assert task_by_id["C"]["parallel_group"] == 1
        # A conflicts with B, so Wave 2 (alone but gets wave number)
        assert task_by_id["A"]["parallel_group"] == 2

    def test_single_task_wave_gets_number(self):
        """Single-task waves still get wave numbers for ordering."""
        subtasks = [
            {"id": "A", "files": ["f1.py"]},
        ]
        result = detect_parallel_groups(subtasks)

        # Even alone in wave, task gets wave number
        assert result[0]["parallel_group"] == 1

    def test_no_files_tasks(self):
        """Tasks with no files can run in parallel."""
        subtasks = [
            {"id": "A", "files": []},
            {"id": "B", "files": []},
            {"id": "C", "files": []},
        ]
        result = detect_parallel_groups(subtasks)

        # All should be in Wave 1
        assert all(t["parallel_group"] == 1 for t in result)

    def test_immutable_input(self):
        """Original subtasks list should not be mutated."""
        subtasks = [
            {"id": "A", "files": ["f1.py"]},
            {"id": "B", "files": ["f2.py"]},
        ]
        original_copy = [t.copy() for t in subtasks]

        detect_parallel_groups(subtasks)

        # Original should be unchanged
        assert subtasks == original_copy
        assert "parallel_group" not in subtasks[0]


class TestAnalyzeFileConflicts:
    """Test analyze_file_conflicts helper function."""

    def test_no_conflicts(self):
        """Tasks with different files have no conflicts."""
        subtasks = [
            {"id": "A", "files": ["f1.py"]},
            {"id": "B", "files": ["f2.py"]},
        ]
        conflicts = analyze_file_conflicts(subtasks)
        assert conflicts == {}

    def test_simple_conflict(self):
        """Two tasks sharing file."""
        subtasks = [
            {"id": "A", "files": ["f1.py"]},
            {"id": "B", "files": ["f1.py"]},
        ]
        conflicts = analyze_file_conflicts(subtasks)
        assert conflicts["A"] == {"B"}
        assert conflicts["B"] == {"A"}

    def test_complex_conflicts(self):
        """Multiple overlapping conflicts."""
        subtasks = [
            {"id": "A", "files": ["f1.py", "f2.py"]},
            {"id": "B", "files": ["f2.py", "f3.py"]},
            {"id": "C", "files": ["f3.py", "f4.py"]},
            {"id": "D", "files": ["f5.py"]},
        ]
        conflicts = analyze_file_conflicts(subtasks)

        # A conflicts with B
        assert conflicts["A"] == {"B"}
        # B conflicts with A and C
        assert conflicts["B"] == {"A", "C"}
        # C conflicts with B
        assert conflicts["C"] == {"B"}
        # D has no conflicts
        assert "D" not in conflicts

    def test_empty_list(self):
        """Empty list returns empty dict."""
        conflicts = analyze_file_conflicts([])
        assert conflicts == {}


class TestGenerateWorkspaceNames:
    """Test workspace name generation."""

    def test_parallel_tasks_get_names(self):
        """Tasks in multi-task waves get workspace names."""
        subtasks = [
            {"id": "A", "parallel_group": 1},
            {"id": "B", "parallel_group": 1},
            {"id": "C", "parallel_group": 2},
            {"id": "D", "parallel_group": 2},
        ]
        workspaces = generate_workspace_names(subtasks, "auth-feature")

        # Wave 1 has 2 tasks - both get workspaces
        assert workspaces["A"] == "auth-feature-wave1-1"
        assert workspaces["B"] == "auth-feature-wave1-2"
        # Wave 2 has 2 tasks - both get workspaces
        assert workspaces["C"] == "auth-feature-wave2-1"
        assert workspaces["D"] == "auth-feature-wave2-2"

    def test_single_task_waves_no_names(self):
        """Single-task waves don't get workspace names (no parallel execution)."""
        subtasks = [
            {"id": "A", "parallel_group": 1},
            {"id": "B", "parallel_group": 1},
            {"id": "C", "parallel_group": 2},  # Alone in wave 2
        ]
        workspaces = generate_workspace_names(subtasks, "feature")

        # Wave 1 has 2 tasks - both get workspaces
        assert "A" in workspaces
        assert "B" in workspaces
        # Wave 2 has 1 task - no workspace (sequential)
        assert "C" not in workspaces

    def test_feature_slug_in_names(self):
        """Feature slug should be included in workspace names."""
        subtasks = [
            {"id": "A", "parallel_group": 1},
            {"id": "B", "parallel_group": 1},
        ]
        workspaces = generate_workspace_names(subtasks, "my-feature")

        assert all("my-feature" in name for name in workspaces.values())

    def test_empty_list(self):
        """Empty list returns empty dict."""
        workspaces = generate_workspace_names([], "feature")
        assert workspaces == {}


class TestScenarios:
    """Test complete scenarios from task description."""

    def test_scenario_1_no_conflicts(self):
        """Scenario 1: No conflicts - all parallel."""
        subtasks = [
            {"id": "A", "files": ["file1.py"]},
            {"id": "B", "files": ["file2.py"]},
            {"id": "C", "files": ["file3.py"]},
        ]
        result = detect_parallel_groups(subtasks)

        # All in Wave 1 (parallel)
        assert all(t["parallel_group"] == 1 for t in result)

    def test_scenario_2_file_conflict(self):
        """Scenario 2: File conflict between tasks."""
        subtasks = [
            {"id": "A", "files": ["file1.py", "file2.py"]},
            {"id": "B", "files": ["file2.py", "file3.py"]},
            {"id": "C", "files": ["file4.py"]},
        ]
        result = detect_parallel_groups(subtasks)

        task_by_id = {t["id"]: t for t in result}

        # A and C in Wave 1 (parallel)
        assert task_by_id["A"]["parallel_group"] == 1
        assert task_by_id["C"]["parallel_group"] == 1

        # B in Wave 2 (conflicts with A), alone but still gets wave number
        assert task_by_id["B"]["parallel_group"] == 2

    def test_scenario_3_chain_dependency(self):
        """Scenario 3: Chain dependency - sequential."""
        subtasks = [
            {"id": "A", "files": ["file1.py"], "dependencies": []},
            {"id": "B", "files": ["file2.py"], "dependencies": ["A"]},
            {"id": "C", "files": ["file3.py"], "dependencies": ["B"]},
        ]
        result = detect_parallel_groups(subtasks)

        task_by_id = {t["id"]: t for t in result}

        # All in separate waves (chain dependency), each gets wave number
        assert task_by_id["A"]["parallel_group"] == 1
        assert task_by_id["B"]["parallel_group"] == 2
        assert task_by_id["C"]["parallel_group"] == 3


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_large_number_of_tasks(self):
        """Algorithm should handle 100+ tasks efficiently."""
        subtasks = [
            {"id": f"TASK-{i}", "files": [f"file{i}.py"]}
            for i in range(100)
        ]
        result = detect_parallel_groups(subtasks)

        # All should be in Wave 1 (no conflicts)
        assert all(t["parallel_group"] == 1 for t in result)
        assert len(result) == 100

    def test_all_tasks_conflict(self):
        """All tasks touching same file - worst case."""
        subtasks = [
            {"id": f"TASK-{i}", "files": ["shared.py"]}
            for i in range(10)
        ]
        result = detect_parallel_groups(subtasks)

        # Each task should be in separate wave (all conflict)
        groups = [t["parallel_group"] for t in result]
        # Each task gets its own wave number: 1, 2, 3, ..., 10
        assert groups == list(range(1, 11))

    def test_missing_optional_fields(self):
        """Tasks without optional fields should work."""
        subtasks = [
            {"id": "A"},  # No files, no dependencies
            {"id": "B"},
        ]
        result = detect_parallel_groups(subtasks)

        # Both can run in parallel (no conflicts)
        assert all(t["parallel_group"] == 1 for t in result)

    def test_task_with_many_files(self):
        """Task touching many files."""
        subtasks = [
            {"id": "A", "files": [f"file{i}.py" for i in range(50)]},
            {"id": "B", "files": ["other.py"]},
        ]
        result = detect_parallel_groups(subtasks)

        # No conflicts, both in Wave 1
        assert all(t["parallel_group"] == 1 for t in result)

    def test_duplicate_files_in_task(self):
        """Task listing same file multiple times."""
        subtasks = [
            {"id": "A", "files": ["f1.py", "f1.py", "f2.py"]},
            {"id": "B", "files": ["f2.py"]},
        ]
        result = detect_parallel_groups(subtasks)

        task_by_id = {t["id"]: t for t in result}

        # A and B conflict on f2.py
        # A has more files (3, even with duplicate), so in Wave 1
        assert task_by_id["A"]["parallel_group"] == 1
        # B conflicts with A, so in Wave 2
        assert task_by_id["B"]["parallel_group"] == 2


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_mixed_conflicts_and_dependencies(self):
        """Combination of file conflicts and dependencies."""
        subtasks = [
            {"id": "A", "files": ["f1.py"], "dependencies": []},
            {"id": "B", "files": ["f2.py"], "dependencies": ["A"]},
            {"id": "C", "files": ["f2.py"], "dependencies": []},  # Conflicts with B
            {"id": "D", "files": ["f3.py"], "dependencies": ["A"]},
        ]
        result = detect_parallel_groups(subtasks)

        task_by_id = {t["id"]: t for t in result}

        # Wave 1: A and C (both have no deps, don't conflict)
        assert task_by_id["A"]["parallel_group"] == 1
        assert task_by_id["C"]["parallel_group"] == 1

        # Wave 2: B and D (A complete, both depend on A, don't conflict)
        # Note: B conflicts with C but C already completed in Wave 1
        assert task_by_id["B"]["parallel_group"] == 2
        assert task_by_id["D"]["parallel_group"] == 2

    def test_feature_workflow_realistic_example(self):
        """Realistic feature workflow scenario."""
        subtasks = [
            {
                "id": "TASK-FW-001",
                "files": ["lib/feature_detection.py"],
                "dependencies": [],
            },
            {
                "id": "TASK-FW-002",
                "files": ["lib/slug_generator.py"],
                "dependencies": [],
            },
            {
                "id": "TASK-FW-003",
                "files": ["lib/task_splitter.py"],
                "dependencies": ["TASK-FW-001", "TASK-FW-002"],
            },
            {
                "id": "TASK-FW-004",
                "files": ["lib/task_splitter.py"],  # Conflicts with FW-003
                "dependencies": ["TASK-FW-003"],
            },
        ]
        result = detect_parallel_groups(subtasks)

        task_by_id = {t["id"]: t for t in result}

        # Wave 1: FW-001, FW-002 (parallel)
        assert task_by_id["TASK-FW-001"]["parallel_group"] == 1
        assert task_by_id["TASK-FW-002"]["parallel_group"] == 1

        # Wave 2: FW-003 (depends on both FW-001 and FW-002)
        assert task_by_id["TASK-FW-003"]["parallel_group"] == 2

        # Wave 3: FW-004 (depends on FW-003, conflicts with it)
        assert task_by_id["TASK-FW-004"]["parallel_group"] == 3
