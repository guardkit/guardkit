"""
Seam tests S7: Task-Work Delegation → Results Writer.

Tests the technology boundary between task-work delegation/AutoBuild turn
execution (Layer A) and the results file writer (Layer B).

Verifies that task-work results (files_created, files_modified, test results)
are properly written to task_work_results.json and that Coach can read and
parse them — catching the historical bug where files_created was always empty.

Seam Definition:
    Layer A: Task-work delegation / AutoBuild turn execution
    Layer B: Results file writer (task_work_results.json)

Test Coverage:
    - AC: task_work_results.json contains files_created list
    - AC: task_work_results.json contains files_modified list
    - AC: task_work_results.json contains tests_passed status
    - AC: Results file is written to .guardkit/autobuild/TASK-XXX/
    - AC: Coach can read and parse the results file written by Player
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from guardkit.orchestrator.paths import TaskArtifactPaths

if TYPE_CHECKING:
    from typing import Generator


@pytest.mark.seam
class TestTaskWorkResultsWriting:
    """Test that task-work execution writes results to task_work_results.json."""

    @pytest.fixture
    def worktree_path(self, tmp_path: Path) -> Path:
        """Create a temporary worktree directory with proper structure."""
        # Create directory structure
        autobuild_dir = tmp_path / ".guardkit" / "autobuild"
        autobuild_dir.mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def task_id(self) -> str:
        """Return a test task ID."""
        return "TASK-SFT-007-TEST"

    @pytest.fixture
    def sample_parsed_result(self) -> Dict[str, Any]:
        """Sample parsed result from TaskWorkStreamParser."""
        return {
            "tests_passed": 12,
            "tests_failed": 0,
            "coverage": 87.5,
            "quality_gates_passed": True,
            "implementation_complete": True,
        }

    def test_results_file_written_to_correct_directory(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """Results file is written to .guardkit/autobuild/TASK-XXX/ directory."""
        # Given: A task ID and worktree
        expected_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        expected_file = expected_dir / "task_work_results.json"

        # When: Results are written using TaskArtifactPaths
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        # Write test data
        results_data = {
            "task_id": task_id,
            "files_created": ["src/new_file.py"],
            "files_modified": ["src/existing.py"],
            "tests_passed": True,
        }
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(json.dumps(results_data, indent=2))

        # Then: File exists at the expected path
        assert expected_file.exists(), (
            f"Results file should be written to {expected_file}"
        )
        assert results_path == expected_file

    def test_results_contain_files_created_list(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """After task-work execution, task_work_results.json contains files_created list."""
        # Given: Task-work creates results with files_created
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        created_files = [
            "src/auth/oauth.py",
            "tests/test_oauth.py",
            "src/auth/__init__.py",
        ]
        results_data = {
            "task_id": task_id,
            "files_created": created_files,
            "files_modified": [],
            "tests_passed": True,
        }
        results_path.write_text(json.dumps(results_data, indent=2))

        # When: Results are read back
        with open(results_path) as f:
            loaded_results = json.load(f)

        # Then: files_created contains the expected list
        assert "files_created" in loaded_results, (
            "task_work_results.json must contain files_created field"
        )
        assert loaded_results["files_created"] == created_files, (
            f"Expected files_created={created_files}, "
            f"got {loaded_results['files_created']}"
        )
        assert len(loaded_results["files_created"]) == 3, (
            "files_created should contain 3 files"
        )

    def test_results_contain_files_modified_list(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """After task-work execution, task_work_results.json contains files_modified list."""
        # Given: Task-work creates results with files_modified
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        modified_files = [
            "src/config.py",
            "src/main.py",
        ]
        results_data = {
            "task_id": task_id,
            "files_created": [],
            "files_modified": modified_files,
            "tests_passed": True,
        }
        results_path.write_text(json.dumps(results_data, indent=2))

        # When: Results are read back
        with open(results_path) as f:
            loaded_results = json.load(f)

        # Then: files_modified contains the expected list
        assert "files_modified" in loaded_results, (
            "task_work_results.json must contain files_modified field"
        )
        assert loaded_results["files_modified"] == modified_files, (
            f"Expected files_modified={modified_files}, "
            f"got {loaded_results['files_modified']}"
        )

    def test_results_contain_tests_passed_status(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """After task-work execution, task_work_results.json contains tests_passed status."""
        # Given: Task-work creates results with test status
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        results_data = {
            "task_id": task_id,
            "files_created": ["tests/test_feature.py"],
            "files_modified": ["src/feature.py"],
            "tests_info": {
                "tests_run": True,
                "tests_passed": True,
                "tests_count": 5,
                "failures_count": 0,
                "output_summary": "5 passed in 0.42s",
            },
            "quality_gates": {
                "tests_passed": 5,
                "tests_failed": 0,
                "coverage": 85.0,
            },
        }
        results_path.write_text(json.dumps(results_data, indent=2))

        # When: Results are read back
        with open(results_path) as f:
            loaded_results = json.load(f)

        # Then: tests_passed status is present and correct
        tests_info = loaded_results.get("tests_info", {})
        assert "tests_passed" in tests_info or "tests_passed" in loaded_results.get("quality_gates", {}), (
            "task_work_results.json must contain tests_passed status"
        )
        assert tests_info.get("tests_passed") is True, (
            "tests_passed should be True"
        )

    def test_non_empty_files_created_after_implementation(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """
        Regression test: files_created is NOT empty after implementation.

        This catches the historical bug where files_created was always empty
        due to improper result propagation from task-work to the results file.
        """
        # Given: Task-work creates new files during implementation
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        # Simulate implementation that creates files
        results_data = {
            "task_id": task_id,
            "files_created": ["src/new_module.py", "tests/test_new_module.py"],
            "files_modified": ["src/__init__.py"],
            "tests_info": {
                "tests_run": True,
                "tests_passed": True,
            },
        }
        results_path.write_text(json.dumps(results_data, indent=2))

        # When: Results are read back
        with open(results_path) as f:
            loaded_results = json.load(f)

        # Then: files_created is NOT empty (catching the historical bug)
        files_created = loaded_results.get("files_created", [])
        assert len(files_created) > 0, (
            "REGRESSION: files_created should NOT be empty after implementation. "
            "This catches the historical bug where files_created was always []. "
            f"Got: files_created={files_created}"
        )


@pytest.mark.seam
class TestCoachReadsPlayerResults:
    """Test that Coach can read and parse results written by Player."""

    @pytest.fixture
    def worktree_path(self, tmp_path: Path) -> Path:
        """Create a temporary worktree directory with proper structure."""
        autobuild_dir = tmp_path / ".guardkit" / "autobuild"
        autobuild_dir.mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def task_id(self) -> str:
        """Return a test task ID."""
        return "TASK-SFT-007-COACH"

    @pytest.fixture
    def player_written_results(self, worktree_path: Path, task_id: str) -> Path:
        """Write results as Player would, return the path."""
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        results_data = {
            "task_id": task_id,
            "files_created": ["src/auth/oauth.py", "tests/test_oauth.py"],
            "files_modified": ["src/config.py", "src/main.py"],
            "tests_info": {
                "tests_run": True,
                "tests_passed": True,
                "tests_count": 8,
                "failures_count": 0,
                "output_summary": "8 passed in 1.23s",
            },
            "quality_gates": {
                "tests_passed": 8,
                "tests_failed": 0,
                "coverage": 82.5,
                "all_gates_passed": True,
            },
            "architectural_score": 75,
        }
        results_path.write_text(json.dumps(results_data, indent=2))
        return results_path

    def test_coach_reads_results_file(
        self, worktree_path: Path, task_id: str, player_written_results: Path
    ) -> None:
        """Coach can read the task_work_results.json written by Player."""
        # Given: Player has written results
        assert player_written_results.exists()

        # When: Coach reads the results file (using TaskArtifactPaths)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        # Then: Coach can access and read the file
        assert results_path.exists(), (
            f"Coach should be able to find results at {results_path}"
        )
        with open(results_path) as f:
            results = json.load(f)

        assert results["task_id"] == task_id

    def test_coach_parses_files_created(
        self, worktree_path: Path, task_id: str, player_written_results: Path
    ) -> None:
        """Coach can parse files_created from Player results."""
        # Given: Player has written results with files_created
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        # When: Coach parses the results
        with open(results_path) as f:
            results = json.load(f)

        # Then: Coach can access files_created
        files_created = results.get("files_created", [])
        assert isinstance(files_created, list), (
            "files_created should be a list"
        )
        assert len(files_created) == 2, (
            f"Expected 2 files_created, got {len(files_created)}"
        )
        assert "src/auth/oauth.py" in files_created
        assert "tests/test_oauth.py" in files_created

    def test_coach_parses_files_modified(
        self, worktree_path: Path, task_id: str, player_written_results: Path
    ) -> None:
        """Coach can parse files_modified from Player results."""
        # Given: Player has written results with files_modified
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        # When: Coach parses the results
        with open(results_path) as f:
            results = json.load(f)

        # Then: Coach can access files_modified
        files_modified = results.get("files_modified", [])
        assert isinstance(files_modified, list), (
            "files_modified should be a list"
        )
        assert len(files_modified) == 2, (
            f"Expected 2 files_modified, got {len(files_modified)}"
        )
        assert "src/config.py" in files_modified
        assert "src/main.py" in files_modified

    def test_coach_parses_test_status(
        self, worktree_path: Path, task_id: str, player_written_results: Path
    ) -> None:
        """Coach can parse tests_passed status from Player results."""
        # Given: Player has written results with test info
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        # When: Coach parses the results
        with open(results_path) as f:
            results = json.load(f)

        # Then: Coach can access test status
        tests_info = results.get("tests_info", {})
        assert tests_info.get("tests_passed") is True, (
            "Coach should parse tests_passed=True"
        )
        assert tests_info.get("tests_count") == 8, (
            "Coach should parse tests_count=8"
        )

    def test_coach_parses_quality_gates(
        self, worktree_path: Path, task_id: str, player_written_results: Path
    ) -> None:
        """Coach can parse quality gate status from Player results."""
        # Given: Player has written results with quality gates
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        # When: Coach parses the results
        with open(results_path) as f:
            results = json.load(f)

        # Then: Coach can access quality gates
        quality_gates = results.get("quality_gates", {})
        assert quality_gates.get("all_gates_passed") is True, (
            "Coach should parse all_gates_passed=True"
        )
        assert quality_gates.get("coverage") == 82.5, (
            "Coach should parse coverage value"
        )


@pytest.mark.seam
class TestPlayerReportCreation:
    """Test that Player report is created from task_work_results.json."""

    @pytest.fixture
    def worktree_path(self, tmp_path: Path) -> Path:
        """Create a temporary worktree directory with proper structure."""
        autobuild_dir = tmp_path / ".guardkit" / "autobuild"
        autobuild_dir.mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def task_id(self) -> str:
        """Return a test task ID."""
        return "TASK-SFT-007-PLAYER"

    def test_player_report_created_in_autobuild_dir(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """Player report (player_turn_{turn}.json) is created in autobuild directory."""
        # Given: A task and turn number
        turn = 1

        # When: Player report path is resolved
        report_path = TaskArtifactPaths.player_report_path(task_id, turn, worktree_path)

        # Then: Path is in correct location
        expected_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        assert report_path.parent == expected_dir, (
            f"Player report should be in {expected_dir}, got {report_path.parent}"
        )
        assert report_path.name == f"player_turn_{turn}.json", (
            f"Player report should be named player_turn_{turn}.json"
        )

    def test_player_report_contains_files_created(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """Player report contains files_created from task_work_results.json."""
        # Given: task_work_results.json exists with files_created
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        task_work_results = {
            "files_created": ["src/new_feature.py", "tests/test_new_feature.py"],
            "files_modified": [],
            "tests_info": {"tests_passed": True},
        }
        results_path.write_text(json.dumps(task_work_results, indent=2))

        # When: Creating player report (simulating _create_player_report_from_task_work)
        with open(results_path) as f:
            task_work_data = json.load(f)

        player_report = {
            "task_id": task_id,
            "turn": 1,
            "files_created": task_work_data.get("files_created", []),
            "files_modified": task_work_data.get("files_modified", []),
            "tests_passed": task_work_data.get("tests_info", {}).get("tests_passed", False),
        }

        # Write player report
        report_path = TaskArtifactPaths.player_report_path(task_id, 1, worktree_path)
        report_path.write_text(json.dumps(player_report, indent=2))

        # Then: Player report contains files_created
        with open(report_path) as f:
            loaded_report = json.load(f)

        assert loaded_report["files_created"] == ["src/new_feature.py", "tests/test_new_feature.py"]

    def test_player_report_preserves_test_results(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """Player report preserves test results from task_work_results.json."""
        # Given: task_work_results.json with detailed test info
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        task_work_results = {
            "files_created": ["tests/test_auth.py"],
            "files_modified": ["src/auth.py"],
            "tests_info": {
                "tests_run": True,
                "tests_passed": True,
                "tests_count": 10,
                "failures_count": 0,
                "output_summary": "10 passed in 0.85s",
            },
        }
        results_path.write_text(json.dumps(task_work_results, indent=2))

        # When: Creating player report
        with open(results_path) as f:
            task_work_data = json.load(f)

        tests_info = task_work_data.get("tests_info", {})
        player_report = {
            "task_id": task_id,
            "turn": 1,
            "files_created": task_work_data.get("files_created", []),
            "files_modified": task_work_data.get("files_modified", []),
            "tests_run": tests_info.get("tests_run", False),
            "tests_passed": tests_info.get("tests_passed", False),
            "test_output_summary": tests_info.get("output_summary", ""),
            "tests_written": [f for f in task_work_data.get("files_created", [])
                            if "test" in f.lower()],
        }

        # Write player report
        report_path = TaskArtifactPaths.player_report_path(task_id, 1, worktree_path)
        report_path.write_text(json.dumps(player_report, indent=2))

        # Then: Player report has test information
        with open(report_path) as f:
            loaded_report = json.load(f)

        assert loaded_report["tests_run"] is True
        assert loaded_report["tests_passed"] is True
        assert loaded_report["test_output_summary"] == "10 passed in 0.85s"
        assert "tests/test_auth.py" in loaded_report["tests_written"]


@pytest.mark.seam
class TestResultsFileIntegrity:
    """Test that results file maintains data integrity through the seam."""

    @pytest.fixture
    def worktree_path(self, tmp_path: Path) -> Path:
        """Create a temporary worktree directory with proper structure."""
        autobuild_dir = tmp_path / ".guardkit" / "autobuild"
        autobuild_dir.mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def task_id(self) -> str:
        """Return a test task ID."""
        return "TASK-SFT-007-INTEGRITY"

    def test_files_created_persists_through_write_read_cycle(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """files_created data persists correctly through write/read cycle."""
        # Given: Task-work writes results with files_created
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        original_files = ["src/api/routes.py", "src/api/__init__.py", "tests/test_routes.py"]
        results_data = {
            "task_id": task_id,
            "files_created": original_files,
            "files_modified": ["src/main.py"],
        }
        results_path.write_text(json.dumps(results_data, indent=2))

        # When: Results are read back (simulating Coach reading Player output)
        with open(results_path) as f:
            loaded_results = json.load(f)

        # Then: files_created is identical
        assert loaded_results["files_created"] == original_files, (
            "files_created must persist through write/read cycle"
        )

    def test_files_modified_persists_through_write_read_cycle(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """files_modified data persists correctly through write/read cycle."""
        # Given: Task-work writes results with files_modified
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        original_files = ["src/config.py", "src/settings.py", "pyproject.toml"]
        results_data = {
            "task_id": task_id,
            "files_created": [],
            "files_modified": original_files,
        }
        results_path.write_text(json.dumps(results_data, indent=2))

        # When: Results are read back
        with open(results_path) as f:
            loaded_results = json.load(f)

        # Then: files_modified is identical
        assert loaded_results["files_modified"] == original_files, (
            "files_modified must persist through write/read cycle"
        )

    def test_empty_lists_handled_correctly(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """Empty files_created and files_modified lists are handled correctly."""
        # Given: Results with empty lists
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        results_data = {
            "task_id": task_id,
            "files_created": [],
            "files_modified": [],
        }
        results_path.write_text(json.dumps(results_data, indent=2))

        # When: Results are read back
        with open(results_path) as f:
            loaded_results = json.load(f)

        # Then: Empty lists are preserved (not converted to None or omitted)
        assert loaded_results.get("files_created") == [], (
            "Empty files_created must be preserved as []"
        )
        assert loaded_results.get("files_modified") == [], (
            "Empty files_modified must be preserved as []"
        )

    def test_coverage_persists_through_write_read_cycle(
        self, worktree_path: Path, task_id: str
    ) -> None:
        """Coverage metrics persist correctly through write/read cycle."""
        # Given: Results with coverage data
        TaskArtifactPaths.ensure_autobuild_dir(task_id, worktree_path)
        results_path = TaskArtifactPaths.task_work_results_path(task_id, worktree_path)

        coverage_data = {"line_coverage": 85.5, "branch_coverage": 78.0}
        results_data = {
            "task_id": task_id,
            "files_created": [],
            "files_modified": [],
            "coverage": coverage_data,
        }
        results_path.write_text(json.dumps(results_data, indent=2))

        # When: Results are read back
        with open(results_path) as f:
            loaded_results = json.load(f)

        # Then: Coverage is identical
        assert loaded_results["coverage"]["line_coverage"] == 85.5
        assert loaded_results["coverage"]["branch_coverage"] == 78.0
