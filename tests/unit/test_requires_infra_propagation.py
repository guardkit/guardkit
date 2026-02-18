"""
Unit tests for TASK-BOOT-B032: requires_infrastructure propagation through orchestrate().

Tests verify:
1. orchestrate() accepts requires_infrastructure as an explicit parameter
2. Explicit parameter takes precedence over task frontmatter value
3. Frontmatter fallback works when explicit parameter is None
4. FeatureOrchestrator._execute_task() passes task.requires_infrastructure to orchestrate()
5. Empty list from caller is treated as valid explicit value (not as "absent")
"""

import pytest
from pathlib import Path
from typing import List, Optional
from unittest.mock import Mock, MagicMock, patch, call, AsyncMock

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.feature_loader import FeatureTask
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.worktrees import Worktree
from guardkit.tasks.task_loader import TaskLoader, TaskNotFoundError


# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree():
    worktree = Mock(spec=Worktree)
    worktree.task_id = "TASK-B032-001"
    worktree.path = Path("/tmp/worktrees/TASK-B032-001")
    worktree.branch_name = "autobuild/TASK-B032-001"
    worktree.base_branch = "main"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    manager = Mock()
    manager.create.return_value = mock_worktree
    manager.preserve_on_failure.return_value = None
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker():
    invoker = Mock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock()
    return invoker


@pytest.fixture
def mock_progress_display():
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
    gates = MagicMock()
    from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult

    async def mock_execute(*args, **kwargs):
        return PreLoopResult(
            plan={"steps": ["Step 1"]},
            plan_path="/tmp/plan.md",
            complexity=3,
            max_turns=3,
            checkpoint_passed=True,
            architectural_score=85,
            clarifications={},
        )

    gates.execute = mock_execute
    return gates


@pytest.fixture
def orchestrator(mock_worktree_manager, mock_agent_invoker, mock_progress_display, mock_pre_loop_gates):
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


def _player_result(task_id: str) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=task_id,
        turn=1,
        agent_type="player",
        success=True,
        report={
            "files_modified": [],
            "files_created": ["impl.py"],
            "tests_written": [],
            "tests_passed": True,
        },
        duration_seconds=5.0,
        error=None,
    )


def _coach_approve_result(task_id: str) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=task_id,
        turn=1,
        agent_type="coach",
        success=True,
        report={"decision": "approve", "rationale": "Looks good"},
        duration_seconds=3.0,
        error=None,
    )


# ============================================================================
# 1. orchestrate() accepts the new parameter
# ============================================================================


class TestOrchestrateAcceptsParameter:
    """orchestrate() must accept requires_infrastructure without error."""

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_orchestrate_accepts_explicit_list(
        self, mock_task_loader, mock_coach_validator, orchestrator
    ):
        """orchestrate() should not raise when requires_infrastructure is a list."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-B032-001",
            "requirements": "req",
            "acceptance_criteria": ["AC1"],
            "frontmatter": {},
            "content": "",
            "file_path": Path("/tmp/task.md"),
        }
        mock_validator = MagicMock()
        mock_validator.validate.side_effect = Exception("force sdk fallback")
        mock_coach_validator.return_value = mock_validator
        orchestrator._agent_invoker.invoke_player.return_value = _player_result("TASK-B032-001")
        orchestrator._agent_invoker.invoke_coach.return_value = _coach_approve_result("TASK-B032-001")

        # Must not raise TypeError about unexpected keyword argument
        orchestrator.orchestrate(
            task_id="TASK-B032-001",
            requirements="req",
            acceptance_criteria=["AC1"],
            requires_infrastructure=["postgresql"],
        )

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_orchestrate_accepts_none(
        self, mock_task_loader, mock_coach_validator, orchestrator
    ):
        """orchestrate() should accept requires_infrastructure=None (backward compat)."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-B032-002",
            "requirements": "req",
            "acceptance_criteria": ["AC1"],
            "frontmatter": {},
            "content": "",
            "file_path": Path("/tmp/task.md"),
        }
        mock_validator = MagicMock()
        mock_validator.validate.side_effect = Exception("force sdk fallback")
        mock_coach_validator.return_value = mock_validator
        orchestrator._agent_invoker.invoke_player.return_value = _player_result("TASK-B032-002")
        orchestrator._agent_invoker.invoke_coach.return_value = _coach_approve_result("TASK-B032-002")

        orchestrator.orchestrate(
            task_id="TASK-B032-002",
            requirements="req",
            acceptance_criteria=["AC1"],
            requires_infrastructure=None,
        )


# ============================================================================
# 2. Explicit parameter takes precedence over frontmatter
# ============================================================================


class TestExplicitParameterPrecedence:
    """Explicit requires_infrastructure overrides frontmatter value."""

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_explicit_list_overrides_frontmatter(
        self, mock_task_loader, mock_coach_validator, orchestrator
    ):
        """When caller provides requires_infrastructure, it replaces frontmatter value."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-B032-003",
            "requirements": "req",
            "acceptance_criteria": ["AC1"],
            "frontmatter": {
                "requires_infrastructure": ["redis"],  # frontmatter says redis
            },
            "content": "",
            "file_path": Path("/tmp/task.md"),
        }
        mock_validator = MagicMock()
        mock_validator.validate.side_effect = Exception("force sdk fallback")
        mock_coach_validator.return_value = mock_validator
        orchestrator._agent_invoker.invoke_player.return_value = _player_result("TASK-B032-003")
        orchestrator._agent_invoker.invoke_coach.return_value = _coach_approve_result("TASK-B032-003")

        loop_calls = []
        orig = orchestrator._loop_phase

        def spy(*args, **kwargs):
            loop_calls.append(kwargs)
            return orig(*args, **kwargs)

        orchestrator._loop_phase = spy

        # Caller says postgresql — must win over frontmatter's redis
        orchestrator.orchestrate(
            task_id="TASK-B032-003",
            requirements="req",
            acceptance_criteria=["AC1"],
            requires_infrastructure=["postgresql"],
        )

        assert len(loop_calls) == 1
        assert loop_calls[0]["requires_infrastructure"] == ["postgresql"]

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_explicit_empty_list_overrides_frontmatter(
        self, mock_task_loader, mock_coach_validator, orchestrator
    ):
        """Empty list from caller is a valid explicit value and overrides frontmatter."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-B032-004",
            "requirements": "req",
            "acceptance_criteria": ["AC1"],
            "frontmatter": {
                "requires_infrastructure": ["redis"],
            },
            "content": "",
            "file_path": Path("/tmp/task.md"),
        }
        mock_validator = MagicMock()
        mock_validator.validate.side_effect = Exception("force sdk fallback")
        mock_coach_validator.return_value = mock_validator
        orchestrator._agent_invoker.invoke_player.return_value = _player_result("TASK-B032-004")
        orchestrator._agent_invoker.invoke_coach.return_value = _coach_approve_result("TASK-B032-004")

        loop_calls = []
        orig = orchestrator._loop_phase

        def spy(*args, **kwargs):
            loop_calls.append(kwargs)
            return orig(*args, **kwargs)

        orchestrator._loop_phase = spy

        orchestrator.orchestrate(
            task_id="TASK-B032-004",
            requirements="req",
            acceptance_criteria=["AC1"],
            requires_infrastructure=[],  # empty list is an explicit value
        )

        assert len(loop_calls) == 1
        assert loop_calls[0]["requires_infrastructure"] == []


# ============================================================================
# 3. Frontmatter fallback when parameter is None
# ============================================================================


class TestFrontmatterFallback:
    """When requires_infrastructure=None, frontmatter value is used (single-task mode)."""

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_frontmatter_used_when_parameter_is_none(
        self, mock_task_loader, mock_coach_validator, orchestrator
    ):
        """Frontmatter value flows through to _loop_phase when param is None."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-B032-005",
            "requirements": "req",
            "acceptance_criteria": ["AC1"],
            "frontmatter": {
                "requires_infrastructure": ["postgresql", "redis"],
            },
            "content": "",
            "file_path": Path("/tmp/task.md"),
        }
        mock_validator = MagicMock()
        mock_validator.validate.side_effect = Exception("force sdk fallback")
        mock_coach_validator.return_value = mock_validator
        orchestrator._agent_invoker.invoke_player.return_value = _player_result("TASK-B032-005")
        orchestrator._agent_invoker.invoke_coach.return_value = _coach_approve_result("TASK-B032-005")

        loop_calls = []
        orig = orchestrator._loop_phase

        def spy(*args, **kwargs):
            loop_calls.append(kwargs)
            return orig(*args, **kwargs)

        orchestrator._loop_phase = spy

        orchestrator.orchestrate(
            task_id="TASK-B032-005",
            requirements="req",
            acceptance_criteria=["AC1"],
            # requires_infrastructure not provided → falls back to frontmatter
        )

        assert len(loop_calls) == 1
        assert loop_calls[0]["requires_infrastructure"] == ["postgresql", "redis"]

    @patch("guardkit.orchestrator.autobuild.CoachValidator")
    @patch("guardkit.orchestrator.autobuild.TaskLoader")
    def test_none_passed_when_frontmatter_absent(
        self, mock_task_loader, mock_coach_validator, orchestrator
    ):
        """When both param and frontmatter are absent, None flows to _loop_phase."""
        mock_task_loader.load_task.return_value = {
            "task_id": "TASK-B032-006",
            "requirements": "req",
            "acceptance_criteria": ["AC1"],
            "frontmatter": {},
            "content": "",
            "file_path": Path("/tmp/task.md"),
        }
        mock_validator = MagicMock()
        mock_validator.validate.side_effect = Exception("force sdk fallback")
        mock_coach_validator.return_value = mock_validator
        orchestrator._agent_invoker.invoke_player.return_value = _player_result("TASK-B032-006")
        orchestrator._agent_invoker.invoke_coach.return_value = _coach_approve_result("TASK-B032-006")

        loop_calls = []
        orig = orchestrator._loop_phase

        def spy(*args, **kwargs):
            loop_calls.append(kwargs)
            return orig(*args, **kwargs)

        orchestrator._loop_phase = spy

        orchestrator.orchestrate(
            task_id="TASK-B032-006",
            requirements="req",
            acceptance_criteria=["AC1"],
        )

        assert len(loop_calls) == 1
        assert loop_calls[0]["requires_infrastructure"] is None


# ============================================================================
# 4. FeatureOrchestrator._execute_task() passes task.requires_infrastructure
# ============================================================================


class TestFeatureOrchestratorPropagation:
    """FeatureOrchestrator must pass task.requires_infrastructure to orchestrate()."""

    def test_execute_task_passes_requires_infrastructure(self):
        """_execute_task() passes task.requires_infrastructure to orchestrate()."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
        from guardkit.orchestrator.feature_loader import Feature, FeatureTask

        task = FeatureTask(
            id="TASK-B032-007",
            file_path=Path("tasks/backlog/TASK-B032-007.md"),
            requires_infrastructure=["postgresql", "redis"],
        )

        orchestrate_calls = []

        def capture_orchestrate(**kwargs):
            orchestrate_calls.append(kwargs)
            return Mock(success=True, total_turns=1, final_decision="approved", error=None)

        mock_orchestrator = Mock()
        mock_orchestrator.orchestrate = capture_orchestrate

        with patch(
            "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator",
            return_value=mock_orchestrator,
        ), patch(
            "guardkit.orchestrator.feature_orchestrator.TaskLoader"
        ) as mock_loader:
            mock_loader.load_task.return_value = {
                "task_id": "TASK-B032-007",
                "requirements": "req",
                "acceptance_criteria": ["AC1"],
                "frontmatter": {},
                "content": "",
                "file_path": Path("tasks/backlog/TASK-B032-007.md"),
            }

            feature = Mock(spec=Feature)
            feature.id = "FEAT-B032"
            feature.orchestration = Mock()
            feature.orchestration.max_turns = 3

            worktree = Mock(spec=Worktree)

            fo = FeatureOrchestrator(
                repo_root=Path("/tmp/repo"),
                worktree_manager=Mock(),  # avoid real WorktreeManager git validation
            )
            fo.sdk_timeout = None
            fo.max_turns = 3
            fo.enable_context = False
            fo._resolve_enable_pre_loop = Mock(return_value=False)

            fo._execute_task(task=task, feature=feature, worktree=worktree)

        assert len(orchestrate_calls) == 1
        assert orchestrate_calls[0]["requires_infrastructure"] == ["postgresql", "redis"]

    def test_execute_task_passes_empty_requires_infrastructure(self):
        """_execute_task() passes empty list for tasks with no infrastructure."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
        from guardkit.orchestrator.feature_loader import Feature, FeatureTask

        task = FeatureTask(
            id="TASK-B032-008",
            file_path=Path("tasks/backlog/TASK-B032-008.md"),
            # requires_infrastructure not set → defaults to []
        )

        orchestrate_calls = []

        def capture_orchestrate(**kwargs):
            orchestrate_calls.append(kwargs)
            return Mock(success=True, total_turns=1, final_decision="approved", error=None)

        mock_orchestrator = Mock()
        mock_orchestrator.orchestrate = capture_orchestrate

        with patch(
            "guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator",
            return_value=mock_orchestrator,
        ), patch(
            "guardkit.orchestrator.feature_orchestrator.TaskLoader"
        ) as mock_loader:
            mock_loader.load_task.return_value = {
                "task_id": "TASK-B032-008",
                "requirements": "req",
                "acceptance_criteria": ["AC1"],
                "frontmatter": {},
                "content": "",
                "file_path": Path("tasks/backlog/TASK-B032-008.md"),
            }

            feature = Mock(spec=Feature)
            feature.id = "FEAT-B032"
            feature.orchestration = Mock()
            feature.orchestration.max_turns = 3

            worktree = Mock(spec=Worktree)

            fo = FeatureOrchestrator(
                repo_root=Path("/tmp/repo"),
                worktree_manager=Mock(),  # avoid real WorktreeManager git validation
            )
            fo.sdk_timeout = None
            fo.max_turns = 3
            fo.enable_context = False
            fo._resolve_enable_pre_loop = Mock(return_value=False)

            fo._execute_task(task=task, feature=feature, worktree=worktree)

        assert len(orchestrate_calls) == 1
        assert orchestrate_calls[0]["requires_infrastructure"] == []
