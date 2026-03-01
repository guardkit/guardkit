"""
Unit tests for state recovery test path scoping (TASK-FIX-8595).

Tests verify that _attempt_state_recovery uses tests_written from the player
report when available, and falls back to task frontmatter test_scope otherwise.

Coverage Target: >=85%
Test Count: 4 tests
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import sys
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree():
    """Create mock Worktree instance."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-FIX-8595"
    worktree.path = Path("/tmp/worktrees/TASK-FIX-8595")
    worktree.branch_name = "autobuild/TASK-FIX-8595"
    worktree.base_branch = "main"
    return worktree


@pytest.fixture
def orchestrator(mock_pre_loop_gates, mock_coach_validator, mock_worktree_manager, mock_progress_display):
    """Create AutoBuildOrchestrator with all dependencies mocked."""
    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/test-repo"),
        max_turns=5,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        pre_loop_gates=mock_pre_loop_gates,
        enable_checkpoints=False,
    )


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Create mock WorktreeManager."""
    manager = Mock()
    manager.create.return_value = mock_worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_progress_display():
    """Create mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    display.console = Mock()
    return display


@pytest.fixture
def mock_coach_validator():
    """Patch CoachValidator to force SDK fallback."""
    with patch(
        "guardkit.orchestrator.autobuild.CoachValidator"
    ) as mock_validator_class:
        mock_instance = MagicMock()
        mock_instance.validate.side_effect = Exception("Force SDK fallback for test")
        mock_validator_class.return_value = mock_instance
        yield mock_validator_class


@pytest.fixture
def mock_pre_loop_gates():
    """Create mock PreLoopQualityGates."""
    from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

    gates = MagicMock()

    async def mock_execute(*args, **kwargs):
        return PreLoopResult(
            plan={"steps": ["Step 1"]},
            plan_path="/tmp/plan.md",
            complexity=5,
            max_turns=5,
            checkpoint_passed=True,
            architectural_score=85,
            clarifications={},
        )

    gates.execute = mock_execute
    return gates


@pytest.fixture
def mock_work_state():
    """Create a mock WorkState that indicates work was found."""
    state = Mock()
    state.has_work = True
    state.detection_method = "git_changes"
    state.total_files_changed = 2
    state.test_count = 3
    state.tests_passed = True
    state.files_changed = ["src/foo.py"]
    state.test_files = ["tests/test_foo.py"]
    return state


# ============================================================================
# Tests: test_paths extraction logic
# ============================================================================


class TestStateRecoveryScopingFromPlayerReport:
    """Tests verifying test_paths are extracted from player report when available."""

    def test_player_report_tests_written_used_as_test_paths(
        self, orchestrator, mock_worktree, mock_work_state
    ):
        """When player_report has tests_written, those paths are passed to capture_state."""
        player_report = {
            "tests_written": [
                "tests/unit/test_foo.py",
                "tests/unit/test_bar.py",
            ]
        }

        captured_test_paths = []

        def fake_capture_state(turn, test_paths=None):
            captured_test_paths.append(test_paths)
            return mock_work_state

        mock_tracker = Mock()
        mock_tracker.capture_state.side_effect = fake_capture_state
        mock_tracker.save_state = Mock()

        with patch(
            "guardkit.orchestrator.autobuild.MultiLayeredStateTracker",
            return_value=mock_tracker,
        ), patch.object(
            orchestrator,
            "_build_synthetic_report",
            return_value={"task_id": "TASK-FIX-8595", "tests_written": []},
        ):
            orchestrator._attempt_state_recovery(
                task_id="TASK-FIX-8595",
                turn=1,
                worktree=mock_worktree,
                original_error="Player failed",
                player_report=player_report,
            )

        assert len(captured_test_paths) == 1
        assert captured_test_paths[0] == [
            "tests/unit/test_foo.py",
            "tests/unit/test_bar.py",
        ]

    def test_player_report_none_falls_back_to_task_frontmatter(
        self, orchestrator, mock_worktree, mock_work_state
    ):
        """When player_report is None, falls back to test_scope from task frontmatter."""
        captured_test_paths = []

        def fake_capture_state(turn, test_paths=None):
            captured_test_paths.append(test_paths)
            return mock_work_state

        mock_tracker = Mock()
        mock_tracker.capture_state.side_effect = fake_capture_state
        mock_tracker.save_state = Mock()

        fake_task_data = {
            "frontmatter": {"test_scope": "tests/unit/test_specific.py"}
        }

        with patch(
            "guardkit.orchestrator.autobuild.MultiLayeredStateTracker",
            return_value=mock_tracker,
        ), patch(
            "guardkit.tasks.task_loader.TaskLoader.load_task",
            return_value=fake_task_data,
        ), patch.object(
            orchestrator,
            "_build_synthetic_report",
            return_value={"task_id": "TASK-FIX-8595", "tests_written": []},
        ):
            orchestrator._attempt_state_recovery(
                task_id="TASK-FIX-8595",
                turn=1,
                worktree=mock_worktree,
                original_error="Player failed",
                player_report=None,
            )

        assert len(captured_test_paths) == 1
        assert captured_test_paths[0] == ["tests/unit/test_specific.py"]

    def test_player_report_without_tests_written_falls_back(
        self, orchestrator, mock_worktree, mock_work_state
    ):
        """When player_report exists but has no tests_written key, falls back to task frontmatter."""
        player_report = {
            "task_id": "TASK-FIX-8595",
            "files_modified": ["src/foo.py"],
            # No tests_written key
        }

        captured_test_paths = []

        def fake_capture_state(turn, test_paths=None):
            captured_test_paths.append(test_paths)
            return mock_work_state

        mock_tracker = Mock()
        mock_tracker.capture_state.side_effect = fake_capture_state
        mock_tracker.save_state = Mock()

        fake_task_data = {
            "frontmatter": {"test_scope": "tests/unit/test_specific.py"}
        }

        with patch(
            "guardkit.orchestrator.autobuild.MultiLayeredStateTracker",
            return_value=mock_tracker,
        ), patch(
            "guardkit.tasks.task_loader.TaskLoader.load_task",
            return_value=fake_task_data,
        ), patch.object(
            orchestrator,
            "_build_synthetic_report",
            return_value={"task_id": "TASK-FIX-8595", "tests_written": []},
        ):
            orchestrator._attempt_state_recovery(
                task_id="TASK-FIX-8595",
                turn=1,
                worktree=mock_worktree,
                original_error="Player failed",
                player_report=player_report,
            )

        assert len(captured_test_paths) == 1
        assert captured_test_paths[0] == ["tests/unit/test_specific.py"]

    def test_player_report_with_empty_tests_written_falls_back(
        self, orchestrator, mock_worktree, mock_work_state
    ):
        """When player_report has empty tests_written list, falls back to task frontmatter."""
        player_report = {
            "task_id": "TASK-FIX-8595",
            "tests_written": [],  # Empty list - should fall back
        }

        captured_test_paths = []

        def fake_capture_state(turn, test_paths=None):
            captured_test_paths.append(test_paths)
            return mock_work_state

        mock_tracker = Mock()
        mock_tracker.capture_state.side_effect = fake_capture_state
        mock_tracker.save_state = Mock()

        fake_task_data = {
            "frontmatter": {"test_scope": "tests/unit/test_specific.py"}
        }

        with patch(
            "guardkit.orchestrator.autobuild.MultiLayeredStateTracker",
            return_value=mock_tracker,
        ), patch(
            "guardkit.tasks.task_loader.TaskLoader.load_task",
            return_value=fake_task_data,
        ), patch.object(
            orchestrator,
            "_build_synthetic_report",
            return_value={"task_id": "TASK-FIX-8595", "tests_written": []},
        ):
            orchestrator._attempt_state_recovery(
                task_id="TASK-FIX-8595",
                turn=1,
                worktree=mock_worktree,
                original_error="Player failed",
                player_report=player_report,
            )

        assert len(captured_test_paths) == 1
        assert captured_test_paths[0] == ["tests/unit/test_specific.py"]


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
