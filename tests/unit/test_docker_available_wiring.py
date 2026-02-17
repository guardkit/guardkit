"""Unit tests for _docker_available wiring in _invoke_coach_safely().

Verifies that the task dict passed to CoachValidator.validate() contains the
correct _docker_available value based on validator._is_docker_available().

Fixes TASK-BOOT-6D85: without this key, task.get("_docker_available", True)
always returns True, so conditional approval (no-docker path) could never fire.
"""

from pathlib import Path
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator


def _make_orchestrator(tmp_path: Path) -> AutoBuildOrchestrator:
    """Create a minimal AutoBuildOrchestrator for testing _invoke_coach_safely."""
    mock_worktree_manager = Mock()
    mock_agent_invoker = Mock()
    mock_progress_display = Mock()

    orchestrator = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        enable_context=False,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
    )
    return orchestrator


def _mock_worktree(tmp_path: Path) -> Mock:
    """Create a minimal mock Worktree."""
    worktree = Mock()
    worktree.path = tmp_path
    return worktree


class TestDockerAvailableWiring:
    """_docker_available must be present in the task dict passed to validate()."""

    def test_docker_available_false_in_task_dict(self, tmp_path):
        """When Docker is unavailable, task dict contains _docker_available=False."""
        orchestrator = _make_orchestrator(tmp_path)
        worktree = _mock_worktree(tmp_path)

        captured_task_dict = {}

        def fake_validate(task_id, turn, task, skip_arch_review=False, context=None):
            captured_task_dict.update(task)
            result = Mock()
            result.to_dict.return_value = {}
            return result

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as MockValidator:
            instance = MockValidator.return_value
            instance._is_docker_available.return_value = False
            instance.validate.side_effect = fake_validate
            instance.save_decision = Mock()

            # Stub _load_coach_config to avoid file I/O
            orchestrator._load_coach_config = Mock(
                return_value={"test_execution": "subprocess"}
            )

            orchestrator._invoke_coach_safely(
                task_id="TASK-BOOT-6D85",
                turn=1,
                requirements="req",
                player_report={},
                worktree=worktree,
            )

        assert "_docker_available" in captured_task_dict, (
            "_docker_available key must be present in task dict"
        )
        assert captured_task_dict["_docker_available"] is False

    def test_docker_available_true_in_task_dict(self, tmp_path):
        """When Docker is available, task dict contains _docker_available=True."""
        orchestrator = _make_orchestrator(tmp_path)
        worktree = _mock_worktree(tmp_path)

        captured_task_dict = {}

        def fake_validate(task_id, turn, task, skip_arch_review=False, context=None):
            captured_task_dict.update(task)
            result = Mock()
            result.to_dict.return_value = {}
            return result

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as MockValidator:
            instance = MockValidator.return_value
            instance._is_docker_available.return_value = True
            instance.validate.side_effect = fake_validate
            instance.save_decision = Mock()

            orchestrator._load_coach_config = Mock(
                return_value={"test_execution": "subprocess"}
            )

            orchestrator._invoke_coach_safely(
                task_id="TASK-BOOT-6D85",
                turn=1,
                requirements="req",
                player_report={},
                worktree=worktree,
            )

        assert "_docker_available" in captured_task_dict
        assert captured_task_dict["_docker_available"] is True

    def test_is_docker_available_called_once(self, tmp_path):
        """_is_docker_available() is called exactly once per Coach invocation."""
        orchestrator = _make_orchestrator(tmp_path)
        worktree = _mock_worktree(tmp_path)

        def fake_validate(task_id, turn, task, skip_arch_review=False, context=None):
            result = Mock()
            result.to_dict.return_value = {}
            return result

        with patch(
            "guardkit.orchestrator.autobuild.CoachValidator"
        ) as MockValidator:
            instance = MockValidator.return_value
            instance._is_docker_available.return_value = False
            instance.validate.side_effect = fake_validate
            instance.save_decision = Mock()

            orchestrator._load_coach_config = Mock(
                return_value={"test_execution": "subprocess"}
            )

            orchestrator._invoke_coach_safely(
                task_id="TASK-BOOT-6D85",
                turn=1,
                requirements="req",
                player_report={},
                worktree=worktree,
            )

        instance._is_docker_available.assert_called_once()
