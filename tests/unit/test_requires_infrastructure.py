"""
Unit tests for TASK-INFR-6D4F: requires_infrastructure field and propagation.

Tests verify:
1. FeatureTask model parses requires_infrastructure from YAML
2. AutoBuildOrchestrator loads requires_infrastructure from task frontmatter
3. requires_infrastructure is threaded through _loop_phase → _execute_turn → Coach task dict
4. CoachValidator can read requires_infrastructure from the task parameter
5. Precedence: task frontmatter > feature YAML default
6. Graceful handling when field is absent (defaults to empty list)

Coverage Target: >=85%
"""

import pytest
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys

# Add project root to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.feature_loader import FeatureTask, FeatureLoader, Feature
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, OrchestrationResult
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.worktrees import Worktree
from guardkit.tasks.task_loader import TaskLoader, TaskNotFoundError


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree():
    """Create mock Worktree instance."""
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-INFR-001"
    worktree.path = Path("/tmp/worktrees/TASK-INFR-001")
    worktree.branch_name = "autobuild/TASK-INFR-001"
    worktree.base_branch = "main"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Create mock WorktreeManager."""
    manager = Mock()
    manager.create.return_value = mock_worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create mock AgentInvoker."""
    invoker = Mock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock()
    return invoker


@pytest.fixture
def mock_progress_display():
    """Create mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    display.render_blocked_report = Mock()
    display.console = Mock()
    return display


@pytest.fixture
def mock_pre_loop_gates():
    """Create mock PreLoopQualityGates."""
    gates = MagicMock()
    from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

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
def orchestrator_with_mocks(
    mock_worktree_manager,
    mock_agent_invoker,
    mock_progress_display,
    mock_pre_loop_gates,
):
    """Create AutoBuildOrchestrator with all dependencies mocked."""
    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/repo"),
        max_turns=3,
        enable_pre_loop=False,
        enable_checkpoints=False,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
        pre_loop_gates=mock_pre_loop_gates,
    )


# ============================================================================
# 1. FeatureTask Model Tests
# ============================================================================


class TestFeatureTaskRequiresInfrastructure:
    """Test requires_infrastructure field on FeatureTask model."""

    def test_feature_task_has_requires_infrastructure_field(self):
        """Test FeatureTask model accepts requires_infrastructure."""
        task = FeatureTask(
            id="TASK-001",
            file_path=Path("tasks/backlog/TASK-001.md"),
            requires_infrastructure=["postgresql", "redis"],
        )
        assert task.requires_infrastructure == ["postgresql", "redis"]

    def test_feature_task_defaults_to_empty_list(self):
        """Test requires_infrastructure defaults to empty list when not provided."""
        task = FeatureTask(
            id="TASK-002",
            file_path=Path("tasks/backlog/TASK-002.md"),
        )
        assert task.requires_infrastructure == []

    def test_feature_task_parses_from_dict(self):
        """Test FeatureTask parses requires_infrastructure from dict (YAML-like data)."""
        data = {
            "id": "TASK-003",
            "file_path": "tasks/backlog/TASK-003.md",
            "requires_infrastructure": ["postgresql"],
        }
        task = FeatureTask.model_validate(data)
        assert task.requires_infrastructure == ["postgresql"]

    def test_feature_task_empty_list_in_dict(self):
        """Test FeatureTask handles empty requires_infrastructure list."""
        data = {
            "id": "TASK-004",
            "file_path": "tasks/backlog/TASK-004.md",
            "requires_infrastructure": [],
        }
        task = FeatureTask.model_validate(data)
        assert task.requires_infrastructure == []

    def test_feature_task_missing_field_in_dict(self):
        """Test FeatureTask handles missing requires_infrastructure in dict."""
        data = {
            "id": "TASK-005",
            "file_path": "tasks/backlog/TASK-005.md",
        }
        task = FeatureTask.model_validate(data)
        assert task.requires_infrastructure == []

    def test_feature_task_serialization_includes_field(self):
        """Test requires_infrastructure is included in model_dump."""
        task = FeatureTask(
            id="TASK-006",
            file_path=Path("tasks/backlog/TASK-006.md"),
            requires_infrastructure=["redis", "rabbitmq"],
        )
        data = task.model_dump()
        assert data["requires_infrastructure"] == ["redis", "rabbitmq"]

    def test_feature_task_serialization_empty_list(self):
        """Test empty requires_infrastructure is included in model_dump."""
        task = FeatureTask(
            id="TASK-007",
            file_path=Path("tasks/backlog/TASK-007.md"),
        )
        data = task.model_dump()
        assert data["requires_infrastructure"] == []


# ============================================================================
# 2. Feature YAML Parsing Tests
# ============================================================================


class TestFeatureYAMLParsing:
    """Test requires_infrastructure parsed from feature YAML."""

    def test_feature_yaml_with_requires_infrastructure(self, tmp_path):
        """Test loading feature YAML with requires_infrastructure on tasks."""
        features_dir = tmp_path / ".guardkit" / "features"
        features_dir.mkdir(parents=True)

        tasks_dir = tmp_path / "tasks" / "backlog" / "test-feature"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "TASK-001.md").write_text("# Task 1")

        feature_yaml = features_dir / "FEAT-TEST.yaml"
        feature_yaml.write_text("""
id: FEAT-TEST
name: Test Feature
description: Testing requires_infrastructure
tasks:
  - id: TASK-001
    file_path: tasks/backlog/test-feature/TASK-001.md
    requires_infrastructure:
      - postgresql
      - redis
orchestration:
  parallel_groups:
    - [TASK-001]
""")

        feature = FeatureLoader.load_feature(
            "FEAT-TEST", repo_root=tmp_path, features_dir=features_dir
        )
        assert feature.tasks[0].requires_infrastructure == ["postgresql", "redis"]

    def test_feature_yaml_without_requires_infrastructure(self, tmp_path):
        """Test loading feature YAML without requires_infrastructure defaults."""
        features_dir = tmp_path / ".guardkit" / "features"
        features_dir.mkdir(parents=True)

        tasks_dir = tmp_path / "tasks" / "backlog" / "test-feature"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "TASK-002.md").write_text("# Task 2")

        feature_yaml = features_dir / "FEAT-TEST2.yaml"
        feature_yaml.write_text("""
id: FEAT-TEST2
name: Test Feature 2
description: No infrastructure
tasks:
  - id: TASK-002
    file_path: tasks/backlog/test-feature/TASK-002.md
orchestration:
  parallel_groups:
    - [TASK-002]
""")

        feature = FeatureLoader.load_feature(
            "FEAT-TEST2", repo_root=tmp_path, features_dir=features_dir
        )
        assert feature.tasks[0].requires_infrastructure == []


# ============================================================================
# 3. AutoBuild Loading and Threading Tests
# ============================================================================


class TestAutoBuildRequiresInfrastructureLoading:
    """Test requires_infrastructure loading from task frontmatter in autobuild."""

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_requires_infrastructure_loaded_from_frontmatter(
        self,
        mock_task_loader,
        mock_coach_validator,
        orchestrator_with_mocks,
    ):
        """Test orchestrate() loads requires_infrastructure from task frontmatter."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-INFR-001",
            "requirements": "Test requirements",
            "acceptance_criteria": ["AC-001"],
            "frontmatter": {
                "task_type": "feature",
                "requires_infrastructure": ["postgresql", "redis"],
            },
            "content": "Task content",
            "file_path": Path("/tmp/task.md"),
        }

        mock_validator_instance = MagicMock()
        mock_validator_instance.validate.side_effect = Exception("Force SDK fallback")
        mock_coach_validator.return_value = mock_validator_instance

        orchestrator_with_mocks._agent_invoker.invoke_player.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-001",
                turn=1,
                agent_type="player",
                success=True,
                report={"files_modified": [], "files_created": ["f.py"], "tests_written": [], "tests_passed": True},
                duration_seconds=5.0,
                error=None,
            )
        )

        orchestrator_with_mocks._agent_invoker.invoke_coach.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-001",
                turn=1,
                agent_type="coach",
                success=True,
                report={"decision": "approve", "rationale": "OK"},
                duration_seconds=3.0,
                error=None,
            )
        )

        # Spy on _loop_phase
        original_loop_phase = orchestrator_with_mocks._loop_phase
        loop_phase_calls = []

        def spy_loop_phase(*args, **kwargs):
            loop_phase_calls.append(kwargs)
            return original_loop_phase(*args, **kwargs)

        orchestrator_with_mocks._loop_phase = spy_loop_phase

        orchestrator_with_mocks.orchestrate(
            task_id="TASK-INFR-001",
            requirements="Test requirements",
            acceptance_criteria=["AC-001"],
        )

        assert len(loop_phase_calls) == 1
        assert loop_phase_calls[0]["requires_infrastructure"] == ["postgresql", "redis"]

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_missing_requires_infrastructure_defaults_to_none(
        self,
        mock_task_loader,
        mock_coach_validator,
        orchestrator_with_mocks,
    ):
        """Test missing requires_infrastructure defaults to None in _loop_phase."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-INFR-002",
            "requirements": "Test",
            "acceptance_criteria": ["AC-001"],
            "frontmatter": {"task_type": "feature"},
            "content": "Content",
            "file_path": Path("/tmp/task.md"),
        }

        mock_validator_instance = MagicMock()
        mock_validator_instance.validate.side_effect = Exception("Force SDK fallback")
        mock_coach_validator.return_value = mock_validator_instance

        orchestrator_with_mocks._agent_invoker.invoke_player.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-002", turn=1, agent_type="player", success=True,
                report={"files_modified": [], "files_created": ["f.py"], "tests_written": [], "tests_passed": True},
                duration_seconds=5.0, error=None,
            )
        )
        orchestrator_with_mocks._agent_invoker.invoke_coach.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-002", turn=1, agent_type="coach", success=True,
                report={"decision": "approve", "rationale": "OK"},
                duration_seconds=3.0, error=None,
            )
        )

        original_loop_phase = orchestrator_with_mocks._loop_phase
        loop_phase_calls = []

        def spy_loop_phase(*args, **kwargs):
            loop_phase_calls.append(kwargs)
            return original_loop_phase(*args, **kwargs)

        orchestrator_with_mocks._loop_phase = spy_loop_phase

        orchestrator_with_mocks.orchestrate(
            task_id="TASK-INFR-002",
            requirements="Test",
            acceptance_criteria=["AC-001"],
        )

        assert len(loop_phase_calls) == 1
        assert loop_phase_calls[0]["requires_infrastructure"] is None

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_non_list_requires_infrastructure_ignored(
        self,
        mock_task_loader,
        mock_coach_validator,
        orchestrator_with_mocks,
    ):
        """Test non-list requires_infrastructure in frontmatter is ignored."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-INFR-003",
            "requirements": "Test",
            "acceptance_criteria": ["AC-001"],
            "frontmatter": {
                "task_type": "feature",
                "requires_infrastructure": "postgresql",  # string, not list
            },
            "content": "Content",
            "file_path": Path("/tmp/task.md"),
        }

        mock_validator_instance = MagicMock()
        mock_validator_instance.validate.side_effect = Exception("Force SDK fallback")
        mock_coach_validator.return_value = mock_validator_instance

        orchestrator_with_mocks._agent_invoker.invoke_player.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-003", turn=1, agent_type="player", success=True,
                report={"files_modified": [], "files_created": ["f.py"], "tests_written": [], "tests_passed": True},
                duration_seconds=5.0, error=None,
            )
        )
        orchestrator_with_mocks._agent_invoker.invoke_coach.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-003", turn=1, agent_type="coach", success=True,
                report={"decision": "approve", "rationale": "OK"},
                duration_seconds=3.0, error=None,
            )
        )

        original_loop_phase = orchestrator_with_mocks._loop_phase
        loop_phase_calls = []

        def spy_loop_phase(*args, **kwargs):
            loop_phase_calls.append(kwargs)
            return original_loop_phase(*args, **kwargs)

        orchestrator_with_mocks._loop_phase = spy_loop_phase

        orchestrator_with_mocks.orchestrate(
            task_id="TASK-INFR-003",
            requirements="Test",
            acceptance_criteria=["AC-001"],
        )

        assert len(loop_phase_calls) == 1
        # Non-list value should be ignored, resulting in None
        assert loop_phase_calls[0]["requires_infrastructure"] is None


# ============================================================================
# 4. CoachValidator Receives requires_infrastructure
# ============================================================================


class TestCoachValidatorReceivesInfrastructure:
    """Test that CoachValidator receives requires_infrastructure in task dict."""

    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_coach_validator_receives_requires_infrastructure(
        self,
        mock_task_loader,
        orchestrator_with_mocks,
    ):
        """Test _invoke_coach_safely passes requires_infrastructure to CoachValidator."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-INFR-004",
            "requirements": "Test",
            "acceptance_criteria": ["AC-001"],
            "frontmatter": {
                "task_type": "feature",
                "requires_infrastructure": ["postgresql"],
            },
            "content": "Content",
            "file_path": Path("/tmp/task.md"),
        }

        orchestrator_with_mocks._agent_invoker.invoke_player.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-004", turn=1, agent_type="player", success=True,
                report={"files_modified": [], "files_created": ["f.py"], "tests_written": [], "tests_passed": True},
                duration_seconds=5.0, error=None,
            )
        )

        with patch("guardkit.orchestrator.autobuild.CoachValidator") as mock_validator_class:
            mock_validator_instance = MagicMock()
            mock_validator_class.return_value = mock_validator_instance

            from guardkit.orchestrator.quality_gates.coach_validator import CoachValidationResult

            mock_validation_result = MagicMock(spec=CoachValidationResult)
            mock_validation_result.to_dict.return_value = {
                "decision": "approve",
                "rationale": "Approved",
            }
            mock_validator_instance.validate.return_value = mock_validation_result
            mock_validator_instance.save_decision.return_value = None

            orchestrator_with_mocks.orchestrate(
                task_id="TASK-INFR-004",
                requirements="Test",
                acceptance_criteria=["AC-001"],
            )

            mock_validator_instance.validate.assert_called_once()
            call_kwargs = mock_validator_instance.validate.call_args.kwargs
            task_dict = call_kwargs["task"]

            assert "requires_infrastructure" in task_dict
            assert task_dict["requires_infrastructure"] == ["postgresql"]

    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_coach_validator_receives_empty_requires_infrastructure(
        self,
        mock_task_loader,
        orchestrator_with_mocks,
    ):
        """Test CoachValidator receives empty list when field absent from frontmatter."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-INFR-005",
            "requirements": "Test",
            "acceptance_criteria": ["AC-001"],
            "frontmatter": {"task_type": "feature"},
            "content": "Content",
            "file_path": Path("/tmp/task.md"),
        }

        orchestrator_with_mocks._agent_invoker.invoke_player.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-005", turn=1, agent_type="player", success=True,
                report={"files_modified": [], "files_created": ["f.py"], "tests_written": [], "tests_passed": True},
                duration_seconds=5.0, error=None,
            )
        )

        with patch("guardkit.orchestrator.autobuild.CoachValidator") as mock_validator_class:
            mock_validator_instance = MagicMock()
            mock_validator_class.return_value = mock_validator_instance

            from guardkit.orchestrator.quality_gates.coach_validator import CoachValidationResult

            mock_validation_result = MagicMock(spec=CoachValidationResult)
            mock_validation_result.to_dict.return_value = {
                "decision": "approve",
                "rationale": "OK",
            }
            mock_validator_instance.validate.return_value = mock_validation_result
            mock_validator_instance.save_decision.return_value = None

            orchestrator_with_mocks.orchestrate(
                task_id="TASK-INFR-005",
                requirements="Test",
                acceptance_criteria=["AC-001"],
            )

            mock_validator_instance.validate.assert_called_once()
            call_kwargs = mock_validator_instance.validate.call_args.kwargs
            task_dict = call_kwargs["task"]

            assert "requires_infrastructure" in task_dict
            assert task_dict["requires_infrastructure"] == []


# ============================================================================
# 5. Precedence Tests
# ============================================================================


class TestRequiresInfrastructurePrecedence:
    """Test precedence: task frontmatter > feature YAML default."""

    def test_task_frontmatter_value_used_when_present(self):
        """Test that task frontmatter value takes precedence."""
        # When task frontmatter has requires_infrastructure, it should be used
        # The autobuild orchestrator reads directly from task frontmatter
        # Feature YAML value is only used when generating task files

        frontmatter = {"requires_infrastructure": ["postgresql"]}
        ri = frontmatter.get("requires_infrastructure")
        assert isinstance(ri, list)
        assert ri == ["postgresql"]

    def test_empty_list_is_valid_override(self):
        """Test that empty list in frontmatter is a valid override (no infrastructure)."""
        frontmatter = {"requires_infrastructure": []}
        ri = frontmatter.get("requires_infrastructure")
        assert isinstance(ri, list)
        assert ri == []

    def test_absent_field_returns_none(self):
        """Test that absent field returns None (no override, use feature default)."""
        frontmatter = {"task_type": "feature"}
        ri = frontmatter.get("requires_infrastructure")
        assert ri is None


# ============================================================================
# 6. Error Handling Tests
# ============================================================================


class TestRequiresInfrastructureErrorHandling:
    """Test graceful error handling for requires_infrastructure."""

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_task_not_found_continues_with_none(
        self,
        mock_task_loader,
        mock_coach_validator,
        orchestrator_with_mocks,
    ):
        """Test TaskNotFoundError results in requires_infrastructure=None."""
        mock_task_loader.load_task.side_effect = TaskNotFoundError("Not found")

        mock_validator_instance = MagicMock()
        mock_validator_instance.validate.side_effect = Exception("Force SDK fallback")
        mock_coach_validator.return_value = mock_validator_instance

        orchestrator_with_mocks._agent_invoker.invoke_player.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-006", turn=1, agent_type="player", success=True,
                report={"files_modified": [], "files_created": ["f.py"], "tests_written": [], "tests_passed": True},
                duration_seconds=5.0, error=None,
            )
        )
        orchestrator_with_mocks._agent_invoker.invoke_coach.return_value = (
            AgentInvocationResult(
                task_id="TASK-INFR-006", turn=1, agent_type="coach", success=True,
                report={"decision": "approve", "rationale": "OK"},
                duration_seconds=3.0, error=None,
            )
        )

        original_loop_phase = orchestrator_with_mocks._loop_phase
        loop_phase_calls = []

        def spy_loop_phase(*args, **kwargs):
            loop_phase_calls.append(kwargs)
            return original_loop_phase(*args, **kwargs)

        orchestrator_with_mocks._loop_phase = spy_loop_phase

        result = orchestrator_with_mocks.orchestrate(
            task_id="TASK-INFR-006",
            requirements="Test",
            acceptance_criteria=["AC-001"],
        )

        assert result.success is True
        assert len(loop_phase_calls) == 1
        assert loop_phase_calls[0]["requires_infrastructure"] is None
