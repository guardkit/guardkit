"""Unit tests for state tracker module.

Tests WorkState dataclass, StateTracker ABC, and MultiLayeredStateTracker.

Coverage Target: >=85%
Test Count: 30+ tests
"""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.state_detection import (
    GitChangesSummary,
    TestResultsSummary,
)
from guardkit.orchestrator.state_tracker import (
    DetectionMethod,
    MultiLayeredStateTracker,
    StateTracker,
    WorkState,
    _is_test_file,
)


# ============================================================================
# 1. WorkState Dataclass Tests
# ============================================================================


class TestWorkState:
    """Tests for WorkState dataclass."""

    def test_default_values(self):
        """Test default empty values."""
        state = WorkState(turn_number=1)
        assert state.turn_number == 1
        assert state.files_modified == []
        assert state.files_created == []
        assert state.tests_written == []
        assert state.tests_passed is False
        assert state.test_count == 0
        assert state.git_changes is None
        assert state.test_results is None
        assert state.player_report is None
        assert state.detection_method == "git_test_detection"
        assert state.timestamp  # Should have timestamp

    def test_with_files(self):
        """Test with file lists populated."""
        state = WorkState(
            turn_number=2,
            files_modified=["src/main.py", "src/utils.py"],
            files_created=["src/new_file.py"],
            tests_written=["tests/test_main.py"],
            tests_passed=True,
            test_count=10,
        )
        assert state.turn_number == 2
        assert len(state.files_modified) == 2
        assert len(state.files_created) == 1
        assert len(state.tests_written) == 1
        assert state.tests_passed is True
        assert state.test_count == 10

    def test_has_work_true_with_modified(self):
        """Test has_work returns True when files modified."""
        state = WorkState(turn_number=1, files_modified=["a.py"])
        assert state.has_work is True

    def test_has_work_true_with_created(self):
        """Test has_work returns True when files created."""
        state = WorkState(turn_number=1, files_created=["a.py"])
        assert state.has_work is True

    def test_has_work_true_with_tests_written(self):
        """Test has_work returns True when tests written."""
        state = WorkState(turn_number=1, tests_written=["test_a.py"])
        assert state.has_work is True

    def test_has_work_true_with_test_count(self):
        """Test has_work returns True when tests run."""
        state = WorkState(turn_number=1, test_count=5)
        assert state.has_work is True

    def test_has_work_false(self):
        """Test has_work returns False when no work."""
        state = WorkState(turn_number=1)
        assert state.has_work is False

    def test_total_files_changed(self):
        """Test total_files_changed property."""
        state = WorkState(
            turn_number=1,
            files_modified=["a.py", "b.py"],
            files_created=["c.py"],
        )
        assert state.total_files_changed == 3

    def test_total_files_changed_empty(self):
        """Test total_files_changed with empty lists."""
        state = WorkState(turn_number=1)
        assert state.total_files_changed == 0

    def test_to_dict_basic(self):
        """Test to_dict serialization."""
        state = WorkState(
            turn_number=1,
            files_modified=["a.py"],
            files_created=["b.py"],
            tests_written=["test_a.py"],
            tests_passed=True,
            test_count=5,
        )
        result = state.to_dict()

        assert result["turn_number"] == 1
        assert result["files_modified"] == ["a.py"]
        assert result["files_created"] == ["b.py"]
        assert result["tests_written"] == ["test_a.py"]
        assert result["tests_passed"] is True
        assert result["test_count"] == 5
        assert result["detection_method"] == "git_test_detection"
        assert result["git_changes"] is None
        assert result["test_results"] is None
        assert result["player_report_available"] is False

    def test_to_dict_with_git_changes(self):
        """Test to_dict with git changes nested dataclass."""
        git_changes = GitChangesSummary(
            files_modified=["src/main.py"],
            insertions=50,
            deletions=20,
        )
        state = WorkState(
            turn_number=1,
            git_changes=git_changes,
        )
        result = state.to_dict()

        assert result["git_changes"] is not None
        assert result["git_changes"]["files_modified"] == ["src/main.py"]
        assert result["git_changes"]["insertions"] == 50
        assert result["git_changes"]["deletions"] == 20

    def test_to_dict_with_test_results(self):
        """Test to_dict with test results nested dataclass."""
        test_results = TestResultsSummary(
            tests_run=True,
            tests_passed=True,
            test_count=10,
            passed_count=10,
        )
        state = WorkState(
            turn_number=1,
            test_results=test_results,
        )
        result = state.to_dict()

        assert result["test_results"] is not None
        assert result["test_results"]["tests_run"] is True
        assert result["test_results"]["tests_passed"] is True
        assert result["test_results"]["test_count"] == 10

    def test_to_dict_with_player_report(self):
        """Test to_dict excludes full player report but marks availability."""
        state = WorkState(
            turn_number=1,
            player_report={"task_id": "TASK-001", "files_modified": ["a.py"]},
        )
        result = state.to_dict()

        assert result["player_report_available"] is True
        assert "player_report" not in result  # Full report excluded


# ============================================================================
# 2. Detection Method Type Tests
# ============================================================================


class TestDetectionMethod:
    """Tests for DetectionMethod type alias."""

    def test_valid_detection_methods(self):
        """Test all valid detection method values."""
        valid_methods: list[DetectionMethod] = [
            "player_report",
            "git_test_detection",
            "git_only",
            "test_only",
            "comprehensive",
        ]
        for method in valid_methods:
            state = WorkState(turn_number=1, detection_method=method)
            assert state.detection_method == method


# ============================================================================
# 3. _is_test_file Helper Tests
# ============================================================================


class TestIsTestFile:
    """Tests for _is_test_file helper function."""

    def test_test_prefix_python(self):
        """Test Python test file with test_ prefix."""
        assert _is_test_file("test_main.py") is True
        assert _is_test_file("src/test_utils.py") is True

    def test_test_suffix_python(self):
        """Test Python test file with _test suffix."""
        assert _is_test_file("main_test.py") is True
        assert _is_test_file("src/utils_test.py") is True

    def test_test_suffix_typescript(self):
        """Test TypeScript test files."""
        assert _is_test_file("main.test.ts") is True
        assert _is_test_file("component.test.tsx") is True

    def test_test_suffix_javascript(self):
        """Test JavaScript test files."""
        assert _is_test_file("main.test.js") is True
        assert _is_test_file("component.test.jsx") is True

    def test_spec_suffix_ruby(self):
        """Test Ruby spec files."""
        assert _is_test_file("user_spec.rb") is True

    def test_test_suffix_go(self):
        """Test Go test files."""
        assert _is_test_file("main_test.go") is True

    def test_tests_directory(self):
        """Test files in tests/ directory."""
        assert _is_test_file("tests/unit/main.py") is True
        assert _is_test_file("src/tests/integration.py") is True

    def test_test_directory(self):
        """Test files in test/ directory."""
        assert _is_test_file("test/main.py") is True
        assert _is_test_file("src/test/helpers.py") is True

    def test_not_test_file(self):
        """Test non-test files."""
        assert _is_test_file("main.py") is False
        assert _is_test_file("src/utils.py") is False
        assert _is_test_file("component.tsx") is False


# ============================================================================
# 4. StateTracker ABC Tests
# ============================================================================


class TestStateTrackerABC:
    """Tests for StateTracker abstract base class."""

    def test_cannot_instantiate_abc(self):
        """Test that StateTracker cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            StateTracker()  # type: ignore

    def test_subclass_must_implement_capture_state(self):
        """Test that subclass must implement capture_state."""

        class IncompleteTracker(StateTracker):
            pass

        with pytest.raises(TypeError, match="abstract"):
            IncompleteTracker()  # type: ignore


# ============================================================================
# 5. MultiLayeredStateTracker Initialization Tests
# ============================================================================


class TestMultiLayeredStateTrackerInit:
    """Tests for MultiLayeredStateTracker initialization."""

    def test_basic_initialization(self, tmp_path: Path):
        """Test basic initialization."""
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        assert tracker.task_id == "TASK-001"
        assert tracker.worktree_path == tmp_path
        assert tracker.autobuild_dir == tmp_path / ".guardkit" / "autobuild" / "TASK-001"

    def test_path_conversion(self, tmp_path: Path):
        """Test that string paths are converted to Path objects."""
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=str(tmp_path),
        )
        assert isinstance(tracker.worktree_path, Path)


# ============================================================================
# 6. MultiLayeredStateTracker._load_player_report Tests
# ============================================================================


class TestLoadPlayerReport:
    """Tests for _load_player_report method."""

    def test_report_not_found(self, tmp_path: Path):
        """Test when Player report file doesn't exist."""
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        result = tracker._load_player_report(turn=1)
        assert result is None

    def test_valid_report_loaded(self, tmp_path: Path):
        """Test loading a valid Player report."""
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        # Create report file
        report_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
        report_dir.mkdir(parents=True)
        report_path = report_dir / "player_turn_1.json"
        report_data = {
            "task_id": "TASK-001",
            "turn": 1,
            "files_modified": ["src/main.py"],
            "tests_passed": True,
        }
        report_path.write_text(json.dumps(report_data))

        result = tracker._load_player_report(turn=1)

        assert result is not None
        assert result["task_id"] == "TASK-001"
        assert result["files_modified"] == ["src/main.py"]

    def test_invalid_json_report(self, tmp_path: Path):
        """Test handling invalid JSON in report."""
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        # Create invalid report file
        report_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
        report_dir.mkdir(parents=True)
        report_path = report_dir / "player_turn_1.json"
        report_path.write_text("not valid json {{{")

        result = tracker._load_player_report(turn=1)
        assert result is None


# ============================================================================
# 7. MultiLayeredStateTracker.capture_state Tests
# ============================================================================


class TestCaptureState:
    """Tests for capture_state method."""

    @patch("guardkit.orchestrator.state_tracker.detect_git_changes")
    @patch("guardkit.orchestrator.state_tracker.detect_test_results")
    def test_no_state_detected(
        self,
        mock_test_results: MagicMock,
        mock_git_changes: MagicMock,
        tmp_path: Path,
    ):
        """Test when no state is detected."""
        mock_git_changes.return_value = None
        mock_test_results.return_value = None

        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        result = tracker.capture_state(turn=1)

        assert result is None

    @patch("guardkit.orchestrator.state_tracker.detect_git_changes")
    @patch("guardkit.orchestrator.state_tracker.detect_test_results")
    def test_git_only_detection(
        self,
        mock_test_results: MagicMock,
        mock_git_changes: MagicMock,
        tmp_path: Path,
    ):
        """Test state capture with only git changes."""
        mock_git_changes.return_value = GitChangesSummary(
            files_modified=["src/main.py"],
            files_added=["src/new.py"],
            insertions=50,
            deletions=10,
        )
        mock_test_results.return_value = None

        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        result = tracker.capture_state(turn=1)

        assert result is not None
        assert result.detection_method == "git_only"
        assert "src/main.py" in result.files_modified
        assert "src/new.py" in result.files_created

    @patch("guardkit.orchestrator.state_tracker.detect_git_changes")
    @patch("guardkit.orchestrator.state_tracker.detect_test_results")
    def test_test_only_detection(
        self,
        mock_test_results: MagicMock,
        mock_git_changes: MagicMock,
        tmp_path: Path,
    ):
        """Test state capture with only test results."""
        mock_git_changes.return_value = None
        mock_test_results.return_value = TestResultsSummary(
            tests_run=True,
            tests_passed=True,
            test_count=10,
            passed_count=10,
        )

        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        result = tracker.capture_state(turn=1)

        assert result is not None
        assert result.detection_method == "test_only"
        assert result.tests_passed is True
        assert result.test_count == 10

    @patch("guardkit.orchestrator.state_tracker.detect_git_changes")
    @patch("guardkit.orchestrator.state_tracker.detect_test_results")
    def test_git_and_test_detection(
        self,
        mock_test_results: MagicMock,
        mock_git_changes: MagicMock,
        tmp_path: Path,
    ):
        """Test state capture with both git and test results."""
        mock_git_changes.return_value = GitChangesSummary(
            files_modified=["src/main.py"],
            insertions=50,
        )
        mock_test_results.return_value = TestResultsSummary(
            tests_run=True,
            tests_passed=True,
            test_count=5,
        )

        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        result = tracker.capture_state(turn=1)

        assert result is not None
        assert result.detection_method == "git_test_detection"
        assert result.tests_passed is True
        assert "src/main.py" in result.files_modified

    @patch("guardkit.orchestrator.state_tracker.detect_git_changes")
    @patch("guardkit.orchestrator.state_tracker.detect_test_results")
    def test_player_report_takes_priority(
        self,
        mock_test_results: MagicMock,
        mock_git_changes: MagicMock,
        tmp_path: Path,
    ):
        """Test that Player report takes priority over detection."""
        # Create Player report
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        report_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
        report_dir.mkdir(parents=True)
        report_path = report_dir / "player_turn_1.json"
        report_data = {
            "task_id": "TASK-001",
            "turn": 1,
            "files_modified": ["player_file.py"],
            "files_created": ["player_new.py"],
            "tests_written": ["player_test.py"],
            "tests_passed": True,
        }
        report_path.write_text(json.dumps(report_data))

        # Set up mocks for git/test detection
        mock_git_changes.return_value = GitChangesSummary(
            files_modified=["git_file.py"],
        )
        mock_test_results.return_value = TestResultsSummary(
            tests_run=True,
            tests_passed=True,
            test_count=5,
        )

        result = tracker.capture_state(turn=1)

        assert result is not None
        assert result.detection_method == "player_report"
        # Player report data used for files
        assert "player_file.py" in result.files_modified
        assert "player_new.py" in result.files_created
        # But test results still used for verification
        assert result.test_count == 5

    @patch("guardkit.orchestrator.state_tracker.detect_git_changes")
    @patch("guardkit.orchestrator.state_tracker.detect_test_results")
    def test_test_file_identification(
        self,
        mock_test_results: MagicMock,
        mock_git_changes: MagicMock,
        tmp_path: Path,
    ):
        """Test that test files are identified from created/modified."""
        mock_git_changes.return_value = GitChangesSummary(
            files_modified=["src/main.py", "tests/test_main.py"],
            files_added=["tests/test_new.py"],
        )
        mock_test_results.return_value = None

        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        result = tracker.capture_state(turn=1)

        assert result is not None
        assert "tests/test_main.py" in result.tests_written
        assert "tests/test_new.py" in result.tests_written


# ============================================================================
# 8. MultiLayeredStateTracker.save_state Tests
# ============================================================================


class TestSaveState:
    """Tests for save_state method."""

    def test_save_state_creates_directory(self, tmp_path: Path):
        """Test that save_state creates the autobuild directory."""
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        state = WorkState(
            turn_number=1,
            files_modified=["a.py"],
        )

        result_path = tracker.save_state(state)

        assert result_path.exists()
        assert tracker.autobuild_dir.exists()

    def test_save_state_creates_json_file(self, tmp_path: Path):
        """Test that save_state creates proper JSON file."""
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        state = WorkState(
            turn_number=2,
            files_modified=["a.py", "b.py"],
            tests_passed=True,
            test_count=5,
        )

        result_path = tracker.save_state(state)

        # Verify file contents
        saved_data = json.loads(result_path.read_text())
        assert saved_data["turn_number"] == 2
        assert saved_data["files_modified"] == ["a.py", "b.py"]
        assert saved_data["tests_passed"] is True
        assert saved_data["test_count"] == 5

    def test_save_state_path_format(self, tmp_path: Path):
        """Test that save_state uses correct path format."""
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        state = WorkState(turn_number=3)

        result_path = tracker.save_state(state)

        assert result_path.name == "work_state_turn_3.json"
        assert result_path.parent == tracker.autobuild_dir


# ============================================================================
# 9. Integration Tests
# ============================================================================


class TestStateTrackerIntegration:
    """Integration tests for MultiLayeredStateTracker."""

    @patch("guardkit.orchestrator.state_tracker.detect_git_changes")
    @patch("guardkit.orchestrator.state_tracker.detect_test_results")
    def test_full_workflow_with_save(
        self,
        mock_test_results: MagicMock,
        mock_git_changes: MagicMock,
        tmp_path: Path,
    ):
        """Test complete workflow: capture state and save."""
        mock_git_changes.return_value = GitChangesSummary(
            files_modified=["src/auth.py"],
            files_added=["src/oauth.py", "tests/test_oauth.py"],
            insertions=100,
            deletions=10,
        )
        mock_test_results.return_value = TestResultsSummary(
            tests_run=True,
            tests_passed=True,
            test_count=8,
            passed_count=8,
        )

        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )

        # Capture state
        state = tracker.capture_state(turn=1)
        assert state is not None
        assert state.has_work is True
        assert len(state.files_modified) == 1
        assert len(state.files_created) == 2

        # Save state
        saved_path = tracker.save_state(state)
        assert saved_path.exists()

        # Verify saved content is valid JSON
        saved_data = json.loads(saved_path.read_text())
        assert saved_data["turn_number"] == 1
        assert saved_data["detection_method"] == "git_test_detection"

    @patch("guardkit.orchestrator.state_tracker.detect_git_changes")
    @patch("guardkit.orchestrator.state_tracker.detect_test_results")
    def test_player_report_with_verification(
        self,
        mock_test_results: MagicMock,
        mock_git_changes: MagicMock,
        tmp_path: Path,
    ):
        """Test Player report with independent git/test verification."""
        # Create Player report
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        report_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
        report_dir.mkdir(parents=True)
        report_path = report_dir / "player_turn_1.json"
        report_data = {
            "task_id": "TASK-001",
            "turn": 1,
            "files_modified": ["src/main.py"],
            "files_created": ["src/new.py"],
            "tests_written": ["tests/test_main.py"],
            "tests_passed": True,  # Player claims tests passed
        }
        report_path.write_text(json.dumps(report_data))

        # But independent test verification says tests failed
        mock_git_changes.return_value = GitChangesSummary(
            files_modified=["src/main.py"],
        )
        mock_test_results.return_value = TestResultsSummary(
            tests_run=True,
            tests_passed=False,  # Independent verification: tests failed
            test_count=5,
            passed_count=3,
            failed_count=2,
        )

        state = tracker.capture_state(turn=1)

        # Uses Player report detection method
        assert state.detection_method == "player_report"
        # File info from Player report
        assert "src/main.py" in state.files_modified
        # But test status from independent verification
        assert state.tests_passed is False  # Independent verification wins
        assert state.test_count == 5

    @patch("guardkit.orchestrator.state_tracker.detect_git_changes")
    @patch("guardkit.orchestrator.state_tracker.detect_test_results")
    def test_tests_not_run_fallback(
        self,
        mock_test_results: MagicMock,
        mock_git_changes: MagicMock,
        tmp_path: Path,
    ):
        """Test fallback when tests don't run (uses Player report value)."""
        # Create Player report
        tracker = MultiLayeredStateTracker(
            task_id="TASK-001",
            worktree_path=tmp_path,
        )
        report_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
        report_dir.mkdir(parents=True)
        report_path = report_dir / "player_turn_1.json"
        report_data = {
            "task_id": "TASK-001",
            "turn": 1,
            "files_modified": ["src/main.py"],
            "tests_passed": True,  # Player claims tests passed
        }
        report_path.write_text(json.dumps(report_data))

        # Test detection returns no tests run
        mock_git_changes.return_value = None
        mock_test_results.return_value = TestResultsSummary(
            tests_run=False,  # Tests didn't run
            tests_passed=False,
            test_count=0,
        )

        state = tracker.capture_state(turn=1)

        # Falls back to Player report value when tests don't run
        assert state.tests_passed is True  # From Player report
        assert state.test_count == 0  # From test detection
