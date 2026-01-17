"""
Integration Tests for Configuration Propagation in AutoBuild

Tests that configuration values (`sdk_timeout` and `enable_pre_loop`) propagate
correctly through the entire chain from CLI to `TaskWorkInterface`.

Test Coverage:
    - sdk_timeout propagation from CLI to TaskWorkInterface
    - sdk_timeout resolution from task frontmatter
    - sdk_timeout default value fallback
    - enable_pre_loop cascade priority (CLI > task > feature > default)
    - Combination scenarios with mixed config sources

Architecture:
    - Uses mock fixtures and temporary directories
    - Mocks SDK calls to avoid actual agent invocations
    - Tests the full propagation chain without executing real tasks

Run with:
    pytest tests/integration/test_config_propagation.py -v
    pytest tests/integration/test_config_propagation.py -v --cov=guardkit/orchestrator

Coverage Target: >=85%
Test Count: 15+ tests
"""

import pytest
import sys
import yaml
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

# Import components under test
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.quality_gates.pre_loop import PreLoopQualityGates
from guardkit.orchestrator.quality_gates.task_work_interface import (
    TaskWorkInterface,
    DesignPhaseResult,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureOrchestration,
    FeatureExecution,
    FeatureLoader,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree(tmp_path) -> Worktree:
    """Create a mock Worktree for testing."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(parents=True)

    # Create required directories
    (worktree_path / "tasks" / "backlog").mkdir(parents=True)
    (worktree_path / "tasks" / "in_progress").mkdir(parents=True)
    (worktree_path / "tasks" / "design_approved").mkdir(parents=True)
    (worktree_path / ".claude" / "task-plans").mkdir(parents=True)
    (worktree_path / ".guardkit" / "autobuild").mkdir(parents=True)

    return Worktree(
        task_id="TASK-TEST-001",
        branch_name="autobuild/TASK-TEST-001",
        path=worktree_path,
        base_branch="main",
    )


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Provide a mock WorktreeManager."""
    manager = MagicMock()
    manager.create.return_value = mock_worktree
    manager.worktrees_dir = mock_worktree.path.parent
    return manager


@pytest.fixture
def sample_feature() -> Feature:
    """Provide a sample Feature for testing config propagation."""
    return Feature(
        id="FEAT-CONFIG",
        name="Config Test Feature",
        description="Feature for testing config propagation",
        created="2025-12-31T12:00:00Z",
        status="planned",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-CFG-001",
                name="First Config Task",
                file_path=Path("tasks/backlog/TASK-CFG-001.md"),
                complexity=4,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-CFG-002",
                name="Second Config Task",
                file_path=Path("tasks/backlog/TASK-CFG-002.md"),
                complexity=5,
                dependencies=["TASK-CFG-001"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=45,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[
                ["TASK-CFG-001"],
                ["TASK-CFG-002"],
            ],
            estimated_duration_minutes=75,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )


@pytest.fixture
def temp_repo_with_feature(tmp_path, sample_feature) -> Path:
    """Create a temporary repository with feature and task files."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create features directory and YAML
    features_dir = repo_root / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    feature_data = FeatureLoader._feature_to_dict(sample_feature)
    with open(features_dir / "FEAT-CONFIG.yaml", "w") as f:
        yaml.dump(feature_data, f)

    # Create task files
    for task in sample_feature.tasks:
        task_file = repo_root / task.file_path
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            f"---\nid: {task.id}\ntitle: {task.name}\nstatus: pending\n---\n\n"
            f"# {task.name}\n\n## Requirements\nTest requirements.\n\n"
            f"## Acceptance Criteria\n- Test criteria\n"
        )

    return repo_root


@pytest.fixture
def mock_design_phase_result(mock_worktree) -> DesignPhaseResult:
    """Create a mock DesignPhaseResult with valid plan."""
    plan_path = mock_worktree.path / ".claude" / "task-plans" / "TASK-TEST-001-implementation-plan.md"
    plan_path.write_text("""# Implementation Plan: TASK-TEST-001

## Overview
Test implementation plan for config propagation tests.

## Steps
1. Step one
2. Step two

## Estimated Complexity: 5/10
""", encoding='utf-8')

    return DesignPhaseResult(
        implementation_plan={
            "overview": "Test implementation",
            "steps": ["Step one", "Step two"],
        },
        plan_path=str(plan_path),
        complexity={"score": 5, "rationale": "Medium complexity"},
        checkpoint_result="approved",
        architectural_review={"score": 80},
        clarifications={},
    )


# ============================================================================
# TestSdkTimeoutPropagation - SDK Timeout Chain Tests
# ============================================================================


@pytest.mark.integration
class TestSdkTimeoutPropagation:
    """Test sdk_timeout propagates through the full chain."""

    def test_cli_sdk_timeout_to_pre_loop_quality_gates(self, mock_worktree):
        """CLI --sdk-timeout reaches PreLoopQualityGates."""
        # Arrange: Create PreLoopQualityGates with sdk_timeout=1200
        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree.path),
            sdk_timeout=1200,
        )

        # Assert: sdk_timeout was stored correctly
        assert gates.sdk_timeout == 1200

    def test_cli_sdk_timeout_to_task_work_interface(self, mock_worktree):
        """CLI --sdk-timeout reaches TaskWorkInterface via PreLoopQualityGates."""
        # Arrange: Create PreLoopQualityGates with sdk_timeout=1200
        # The interface should be created with the same timeout
        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree.path),
            sdk_timeout=1200,
        )

        # Assert: TaskWorkInterface was created with correct timeout
        assert gates._interface.sdk_timeout_seconds == 1200

    def test_task_work_interface_direct_construction(self, mock_worktree):
        """TaskWorkInterface accepts sdk_timeout_seconds parameter."""
        # Arrange & Act
        interface = TaskWorkInterface(
            worktree_path=mock_worktree.path,
            sdk_timeout_seconds=900,
        )

        # Assert
        assert interface.sdk_timeout_seconds == 900

    def test_task_work_interface_default_timeout(self, mock_worktree):
        """TaskWorkInterface uses default 600s when not specified."""
        # Arrange & Act
        interface = TaskWorkInterface(
            worktree_path=mock_worktree.path,
        )

        # Assert
        assert interface.sdk_timeout_seconds == 600

    @pytest.mark.asyncio
    async def test_sdk_timeout_passed_to_execute_design_phase(
        self, mock_worktree, mock_design_phase_result
    ):
        """Verify sdk_timeout is accessible during design phase execution."""
        # Arrange
        mock_interface = MagicMock(spec=TaskWorkInterface)
        mock_interface.sdk_timeout_seconds = 1200
        mock_interface.execute_design_phase = AsyncMock(
            return_value=mock_design_phase_result
        )

        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree.path),
            interface=mock_interface,
            sdk_timeout=1200,
        )

        # Act
        result = await gates.execute(
            task_id="TASK-TEST-001",
            options={"no_questions": True},
        )

        # Assert: Design phase was called
        mock_interface.execute_design_phase.assert_called_once()
        # And the interface has the correct timeout
        assert mock_interface.sdk_timeout_seconds == 1200

    def test_autobuild_orchestrator_passes_sdk_timeout(self, mock_worktree, mock_worktree_manager):
        """AutoBuildOrchestrator passes sdk_timeout to internal components."""
        # Arrange
        orchestrator = AutoBuildOrchestrator(
            repo_root=mock_worktree.path.parent,
            sdk_timeout=1200,
            worktree_manager=mock_worktree_manager,
        )

        # Assert
        assert orchestrator.sdk_timeout == 1200

    def test_feature_orchestrator_passes_sdk_timeout_to_autobuild(
        self, temp_repo_with_feature, sample_feature, mock_worktree, mock_worktree_manager
    ):
        """FeatureOrchestrator passes sdk_timeout to AutoBuildOrchestrator."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            sdk_timeout=1200,
        )

        task = sample_feature.tasks[0]

        # Mock AutoBuildOrchestrator to capture sdk_timeout
        with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as mock_orch_class:
            mock_orch = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.total_turns = 1
            mock_result.final_decision = "approved"
            mock_result.error = None
            mock_orch.orchestrate.return_value = mock_result
            mock_orch_class.return_value = mock_orch

            # Act
            result = orchestrator._execute_task(task, sample_feature, mock_worktree)

            # Assert: AutoBuildOrchestrator was created with sdk_timeout=1200
            call_kwargs = mock_orch_class.call_args[1]
            assert call_kwargs.get("sdk_timeout") == 1200


# ============================================================================
# TestEnablePreLoopCascade - enable_pre_loop Priority Tests
# ============================================================================


@pytest.mark.integration
class TestEnablePreLoopCascade:
    """Test enable_pre_loop configuration cascade priority."""

    def test_cli_flag_highest_priority(
        self, temp_repo_with_feature, sample_feature, mock_worktree_manager
    ):
        """CLI --no-pre-loop overrides all other config."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=False,  # CLI override
        )

        # Feature YAML has enable_pre_loop=True
        sample_feature.autobuild_config = {"enable_pre_loop": True}

        # Task frontmatter has enable_pre_loop=True
        task_data = {
            "frontmatter": {
                "autobuild": {
                    "enable_pre_loop": True,
                }
            }
        }

        # Act
        result = orchestrator._resolve_enable_pre_loop(sample_feature, task_data)

        # Assert: CLI value wins
        assert result is False

    def test_task_frontmatter_overrides_feature(
        self, temp_repo_with_feature, sample_feature, mock_worktree_manager
    ):
        """Task frontmatter overrides feature YAML."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=None,  # No CLI override
        )

        # Feature YAML has enable_pre_loop=True
        sample_feature.autobuild_config = {"enable_pre_loop": True}

        # Task frontmatter has enable_pre_loop=False
        task_data = {
            "frontmatter": {
                "autobuild": {
                    "enable_pre_loop": False,
                }
            }
        }

        # Act
        result = orchestrator._resolve_enable_pre_loop(sample_feature, task_data)

        # Assert: Task frontmatter wins
        assert result is False

    def test_feature_yaml_used_when_no_task_override(
        self, temp_repo_with_feature, sample_feature, mock_worktree_manager
    ):
        """Feature YAML used when task doesn't override."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=None,  # No CLI override
        )

        # Feature YAML has enable_pre_loop=False
        sample_feature.autobuild_config = {"enable_pre_loop": False}

        # Task frontmatter has no enable_pre_loop
        task_data = {
            "frontmatter": {
                "autobuild": {}
            }
        }

        # Act
        result = orchestrator._resolve_enable_pre_loop(sample_feature, task_data)

        # Assert: Feature YAML value used
        assert result is False

    def test_default_true_when_no_config(
        self, temp_repo_with_feature, sample_feature, mock_worktree_manager
    ):
        """Default True used when nothing configured."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=None,  # No CLI override
        )

        # No autobuild_config on feature
        sample_feature.autobuild_config = None

        # No autobuild config in task
        task_data = {
            "frontmatter": {}
        }

        # Act
        result = orchestrator._resolve_enable_pre_loop(sample_feature, task_data)

        # Assert: Default is True
        assert result is True

    def test_empty_autobuild_config_uses_default(
        self, temp_repo_with_feature, sample_feature, mock_worktree_manager
    ):
        """Empty autobuild config falls through to default."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=None,
        )

        # Empty autobuild_config on feature
        sample_feature.autobuild_config = {}

        # Empty autobuild in task
        task_data = {
            "frontmatter": {
                "autobuild": {}
            }
        }

        # Act
        result = orchestrator._resolve_enable_pre_loop(sample_feature, task_data)

        # Assert: Default is True
        assert result is True


# ============================================================================
# TestConfigCombinations - Mixed Configuration Source Tests
# ============================================================================


@pytest.mark.integration
class TestConfigCombinations:
    """Test various config combinations from different sources."""

    def test_both_configs_from_cli(
        self, temp_repo_with_feature, sample_feature, mock_worktree, mock_worktree_manager
    ):
        """Both sdk_timeout and enable_pre_loop from CLI."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            sdk_timeout=1200,
            enable_pre_loop=False,
        )

        task = sample_feature.tasks[0]

        # Mock AutoBuildOrchestrator to capture both values
        with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as mock_orch_class:
            mock_orch = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.total_turns = 1
            mock_result.final_decision = "approved"
            mock_result.error = None
            mock_orch.orchestrate.return_value = mock_result
            mock_orch_class.return_value = mock_orch

            # Act
            result = orchestrator._execute_task(task, sample_feature, mock_worktree)

            # Assert
            call_kwargs = mock_orch_class.call_args[1]
            assert call_kwargs.get("sdk_timeout") == 1200
            assert call_kwargs.get("enable_pre_loop") is False

    def test_sdk_timeout_from_cli_enable_pre_loop_from_feature(
        self, temp_repo_with_feature, sample_feature, mock_worktree, mock_worktree_manager
    ):
        """sdk_timeout from CLI, enable_pre_loop from feature YAML."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            sdk_timeout=1200,  # CLI
            enable_pre_loop=None,  # Fall through to feature
        )

        # Feature has enable_pre_loop=False
        sample_feature.autobuild_config = {"enable_pre_loop": False}

        task = sample_feature.tasks[0]

        # Mock AutoBuildOrchestrator
        with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as mock_orch_class:
            mock_orch = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.total_turns = 1
            mock_result.final_decision = "approved"
            mock_result.error = None
            mock_orch.orchestrate.return_value = mock_result
            mock_orch_class.return_value = mock_orch

            # Act
            result = orchestrator._execute_task(task, sample_feature, mock_worktree)

            # Assert
            call_kwargs = mock_orch_class.call_args[1]
            assert call_kwargs.get("sdk_timeout") == 1200
            assert call_kwargs.get("enable_pre_loop") is False

    def test_sdk_timeout_from_task_frontmatter(
        self, temp_repo_with_feature, sample_feature, mock_worktree, mock_worktree_manager
    ):
        """sdk_timeout from task frontmatter when CLI is None."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            sdk_timeout=None,  # Force cascade
        )

        # Update task file with sdk_timeout in frontmatter
        task = sample_feature.tasks[0]
        task_file = temp_repo_with_feature / task.file_path
        task_file.write_text("""---
id: TASK-CFG-001
title: First Config Task
status: pending
autobuild:
  sdk_timeout: 900
---

# First Config Task

## Requirements
Test requirements.

## Acceptance Criteria
- Test criteria
""")

        # Mock AutoBuildOrchestrator
        with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as mock_orch_class:
            mock_orch = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.total_turns = 1
            mock_result.final_decision = "approved"
            mock_result.error = None
            mock_orch.orchestrate.return_value = mock_result
            mock_orch_class.return_value = mock_orch

            # Act
            result = orchestrator._execute_task(task, sample_feature, mock_worktree)

            # Assert: sdk_timeout from task frontmatter
            call_kwargs = mock_orch_class.call_args[1]
            assert call_kwargs.get("sdk_timeout") == 900

    def test_feature_level_defaults_for_all_tasks(
        self, temp_repo_with_feature, sample_feature, mock_worktree, mock_worktree_manager
    ):
        """Feature YAML provides defaults for all tasks in feature."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            sdk_timeout=None,
            enable_pre_loop=None,
        )

        # Feature has autobuild config
        sample_feature.autobuild_config = {
            "enable_pre_loop": False,
        }

        # Mock AutoBuildOrchestrator
        with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as mock_orch_class:
            mock_orch = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.total_turns = 1
            mock_result.final_decision = "approved"
            mock_result.error = None
            mock_orch.orchestrate.return_value = mock_result
            mock_orch_class.return_value = mock_orch

            # Act: Execute both tasks
            for task in sample_feature.tasks:
                orchestrator._execute_task(task, sample_feature, mock_worktree)

            # Assert: Both tasks got enable_pre_loop=False from feature
            assert mock_orch_class.call_count == 2
            for call in mock_orch_class.call_args_list:
                call_kwargs = call[1]
                assert call_kwargs.get("enable_pre_loop") is False


# ============================================================================
# TestEdgeCases - Edge Case and Error Handling Tests
# ============================================================================


@pytest.mark.integration
class TestEdgeCases:
    """Test edge cases and error handling for config propagation."""

    def test_none_sdk_timeout_uses_default(self, mock_worktree):
        """None sdk_timeout falls through to default 600."""
        # Arrange & Act
        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree.path),
            sdk_timeout=600,  # Default value
        )

        # Assert
        assert gates._interface.sdk_timeout_seconds == 600

    def test_missing_autobuild_section_in_task(
        self, temp_repo_with_feature, sample_feature, mock_worktree_manager
    ):
        """Missing autobuild section in task frontmatter uses default."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=None,
        )

        # No autobuild_config on feature
        sample_feature.autobuild_config = None

        # Task data with no autobuild section at all
        task_data = {
            "frontmatter": {
                "id": "TASK-CFG-001",
                "title": "Test Task",
            }
        }

        # Act
        result = orchestrator._resolve_enable_pre_loop(sample_feature, task_data)

        # Assert: Default True
        assert result is True

    def test_empty_frontmatter_uses_default(
        self, temp_repo_with_feature, sample_feature, mock_worktree_manager
    ):
        """Empty frontmatter dict uses default values."""
        # Arrange
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo_with_feature,
            worktree_manager=mock_worktree_manager,
            enable_pre_loop=None,
        )

        sample_feature.autobuild_config = None

        # Completely empty frontmatter
        task_data = {"frontmatter": {}}

        # Act
        result = orchestrator._resolve_enable_pre_loop(sample_feature, task_data)

        # Assert: Default True
        assert result is True

    def test_pre_loop_quality_gates_stores_sdk_timeout(self, mock_worktree):
        """PreLoopQualityGates stores and exposes sdk_timeout."""
        # Arrange & Act
        gates = PreLoopQualityGates(
            worktree_path=str(mock_worktree.path),
            sdk_timeout=1500,
        )

        # Assert: Value is stored
        assert gates.sdk_timeout == 1500
        # And propagated to interface
        assert gates._interface.sdk_timeout_seconds == 1500


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
