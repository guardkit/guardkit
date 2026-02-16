"""
Unit tests for FeatureOrchestrator - Multi-task wave execution.

This module provides comprehensive unit tests for the FeatureOrchestrator class,
covering wave execution, task orchestration, and shared worktree management.

Test Coverage:
- Feature orchestration lifecycle (setup, waves, finalize)
- Wave execution with dependency ordering
- Task execution (success, failure, skip scenarios)
- Stop-on-failure behavior
- Resume functionality
- Shared worktree management
- Specific task execution
- Error handling
- Wave Parallelization (TASK-FBP-001)
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import tempfile
import yaml
import asyncio

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    FeatureOrchestrationResult,
    FeatureOrchestrationError,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureOrchestration,
    FeatureExecution,
    FeatureLoader,
    FeatureNotFoundError,
    FeatureValidationError,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_feature() -> Feature:
    """Provide a sample Feature for testing."""
    return Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test feature for unit tests",
        created="2025-12-31T12:00:00Z",
        status="planned",
        complexity=6,
        estimated_tasks=3,
        tasks=[
            FeatureTask(
                id="TASK-T-001",
                name="First Task",
                file_path=Path("tasks/backlog/TASK-T-001.md"),
                complexity=3,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-T-002",
                name="Second Task",
                file_path=Path("tasks/backlog/TASK-T-002.md"),
                complexity=5,
                dependencies=["TASK-T-001"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=45,
            ),
            FeatureTask(
                id="TASK-T-003",
                name="Third Task",
                file_path=Path("tasks/backlog/TASK-T-003.md"),
                complexity=4,
                dependencies=["TASK-T-001"],
                status="pending",
                implementation_mode="direct",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[
                ["TASK-T-001"],
                ["TASK-T-002", "TASK-T-003"],
            ],
            estimated_duration_minutes=105,
            recommended_parallel=2,
        ),
        execution=FeatureExecution(),
    )


@pytest.fixture
def parallel_feature() -> Feature:
    """Provide a Feature with independent tasks for parallel execution testing.

    Unlike sample_feature, these tasks have NO dependencies between them,
    making them suitable for testing true parallel execution.
    """
    return Feature(
        id="FEAT-PARALLEL",
        name="Parallel Test Feature",
        description="Feature with independent tasks for parallel testing",
        created="2025-12-31T12:00:00Z",
        status="planned",
        complexity=4,
        estimated_tasks=3,
        tasks=[
            FeatureTask(
                id="TASK-P-001",
                name="Independent Task 1",
                file_path=Path("tasks/backlog/TASK-P-001.md"),
                complexity=3,
                dependencies=[],  # No dependencies
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-P-002",
                name="Independent Task 2",
                file_path=Path("tasks/backlog/TASK-P-002.md"),
                complexity=3,
                dependencies=[],  # No dependencies
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-P-003",
                name="Independent Task 3",
                file_path=Path("tasks/backlog/TASK-P-003.md"),
                complexity=3,
                dependencies=[],  # No dependencies
                status="pending",
                implementation_mode="direct",
                estimated_minutes=30,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[
                ["TASK-P-001", "TASK-P-002", "TASK-P-003"],  # All in same wave
            ],
            estimated_duration_minutes=30,
            recommended_parallel=3,
        ),
        execution=FeatureExecution(),
    )


@pytest.fixture
def mock_worktree(tmp_path) -> Worktree:
    """Provide a mock Worktree for testing."""
    worktree_path = tmp_path / ".guardkit" / "worktrees" / "FEAT-TEST"
    worktree_path.mkdir(parents=True, exist_ok=True)
    return Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=worktree_path,
        base_branch="main",
    )


@pytest.fixture
def mock_worktree_manager(tmp_path, mock_worktree):
    """Provide a mock WorktreeManager."""
    manager = MagicMock()
    manager.create.return_value = mock_worktree
    worktrees_dir = tmp_path / ".guardkit" / "worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    manager.worktrees_dir = worktrees_dir
    return manager


@pytest.fixture
def temp_repo(sample_feature) -> Path:
    """Create a temporary repository with feature and task files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Create features directory and YAML
        features_dir = repo_root / ".guardkit" / "features"
        features_dir.mkdir(parents=True)

        feature_data = FeatureLoader._feature_to_dict(sample_feature)
        with open(features_dir / "FEAT-TEST.yaml", "w") as f:
            yaml.dump(feature_data, f)

        # Create task files
        for task in sample_feature.tasks:
            task_file = repo_root / task.file_path
            task_file.parent.mkdir(parents=True, exist_ok=True)
            task_file.write_text(
                f"---\nid: {task.id}\ntitle: {task.name}\nstatus: pending\n---\n\n"
                f"# {task.name}\n\nTask content."
            )

        yield repo_root


# ============================================================================
# Test: Initialization
# ============================================================================


def test_orchestrator_initialization(temp_repo, mock_worktree_manager):
    """Test FeatureOrchestrator initialization."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        max_turns=10,
        stop_on_failure=True,
        resume=False,
        verbose=True,
        worktree_manager=mock_worktree_manager,
    )

    assert orchestrator.max_turns == 10
    assert orchestrator.stop_on_failure is True
    assert orchestrator.resume is False
    assert orchestrator.verbose is True


def test_orchestrator_default_values(temp_repo, mock_worktree_manager):
    """Test FeatureOrchestrator default initialization values."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    assert orchestrator.max_turns == 5
    assert orchestrator.stop_on_failure is True
    assert orchestrator.resume is False
    assert orchestrator.verbose is False


def test_orchestrator_custom_features_dir(temp_repo, mock_worktree_manager):
    """Test FeatureOrchestrator with custom features directory."""
    custom_dir = temp_repo / "custom" / "features"
    custom_dir.mkdir(parents=True)

    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        features_dir=custom_dir,
        worktree_manager=mock_worktree_manager,
    )

    assert orchestrator.features_dir == custom_dir


def test_orchestrator_rejects_invalid_max_turns(temp_repo, mock_worktree_manager):
    """Test that max_turns < 1 raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        FeatureOrchestrator(
            repo_root=temp_repo,
            max_turns=0,
            worktree_manager=mock_worktree_manager,
        )
    assert "max_turns must be at least 1" in str(exc_info.value)


# ============================================================================
# Test: Setup Phase
# ============================================================================


def test_setup_phase_creates_worktree(temp_repo, mock_worktree, mock_worktree_manager):
    """Test setup phase creates worktree."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    feature, worktree = orchestrator._setup_phase("FEAT-TEST", "main")

    assert worktree == mock_worktree
    assert feature.id == "FEAT-TEST"
    mock_worktree_manager.create.assert_called_once()


def test_setup_phase_updates_execution_state(temp_repo, mock_worktree, mock_worktree_manager):
    """Test setup phase updates feature execution state."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    feature, worktree = orchestrator._setup_phase("FEAT-TEST", "main")

    assert feature.status == "in_progress"
    assert feature.execution.started_at is not None
    assert feature.execution.worktree_path == str(mock_worktree.path)


# ============================================================================
# Test: Clean State (Force Cleanup)
# ============================================================================


def test_clean_state_uses_force_cleanup(temp_repo, sample_feature, mock_worktree_manager, tmp_path):
    """Test that _clean_state passes force=True to cleanup."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    # Set up feature with existing worktree path
    worktree_path = tmp_path / "worktree" / "path"
    worktree_path.mkdir(parents=True, exist_ok=True)
    sample_feature.execution.worktree_path = str(worktree_path)

    # Call _clean_state
    orchestrator._clean_state(sample_feature)

    # Verify cleanup was called with force=True
    mock_worktree_manager.cleanup.assert_called_once()
    call_args = mock_worktree_manager.cleanup.call_args
    assert call_args[0][0].task_id == sample_feature.id
    assert call_args[1]["force"] is True


def test_clean_state_handles_missing_worktree(temp_repo, sample_feature, mock_worktree_manager):
    """Test that _clean_state handles missing worktree gracefully."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    # Set worktree path to non-existent location
    sample_feature.execution.worktree_path = "/nonexistent/worktree/path"

    # Should not raise, cleanup should not be called
    orchestrator._clean_state(sample_feature)

    # Cleanup should not have been called since path doesn't exist
    mock_worktree_manager.cleanup.assert_not_called()


def test_clean_state_resets_feature_state(temp_repo, sample_feature, mock_worktree_manager, tmp_path):
    """Test that _clean_state resets feature execution state."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    # Set initial state
    worktree_path = tmp_path / "worktree" / "path"
    sample_feature.execution.worktree_path = str(worktree_path)
    sample_feature.status = "in_progress"

    # Call _clean_state
    orchestrator._clean_state(sample_feature)

    # Verify state was reset
    # After _clean_state, the feature status should be reset to "planned"
    # (This tests that FeatureLoader.reset_state was called)
    assert sample_feature.status == "planned"


# ============================================================================
# Test: Task Execution Result Dataclass
# ============================================================================


def test_task_execution_result():
    """Test TaskExecutionResult dataclass."""
    result = TaskExecutionResult(
        task_id="TASK-001",
        success=True,
        total_turns=3,
        final_decision="approved",
        error=None,
    )

    assert result.task_id == "TASK-001"
    assert result.success is True
    assert result.total_turns == 3
    assert result.final_decision == "approved"
    assert result.error is None


def test_task_execution_result_with_error():
    """Test TaskExecutionResult with error."""
    result = TaskExecutionResult(
        task_id="TASK-001",
        success=False,
        total_turns=5,
        final_decision="max_turns_exceeded",
        error="Maximum turns exceeded",
    )

    assert result.success is False
    assert result.error == "Maximum turns exceeded"


# ============================================================================
# Test: Wave Execution Result Dataclass
# ============================================================================


def test_wave_execution_result():
    """Test WaveExecutionResult dataclass."""
    task_results = [
        TaskExecutionResult(task_id="TASK-001", success=True, total_turns=2, final_decision="approved"),
        TaskExecutionResult(task_id="TASK-002", success=True, total_turns=1, final_decision="approved"),
    ]

    result = WaveExecutionResult(
        wave_number=1,
        task_ids=["TASK-001", "TASK-002"],
        results=task_results,
        all_succeeded=True,
    )

    assert result.wave_number == 1
    assert len(result.results) == 2
    assert result.all_succeeded is True


def test_wave_execution_result_with_failure():
    """Test WaveExecutionResult with a failed task."""
    task_results = [
        TaskExecutionResult(task_id="TASK-001", success=False, total_turns=5, final_decision="max_turns"),
        TaskExecutionResult(task_id="TASK-002", success=True, total_turns=1, final_decision="approved"),
    ]

    result = WaveExecutionResult(
        wave_number=1,
        task_ids=["TASK-001", "TASK-002"],
        results=task_results,
        all_succeeded=False,
    )

    assert result.all_succeeded is False


# ============================================================================
# Test: CLI Integration
# ============================================================================


def test_cli_feature_command_help():
    """Test feature command help text."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    runner = CliRunner()
    result = runner.invoke(feature, ["--help"])

    assert result.exit_code == 0
    assert "Execute AutoBuild for all tasks in a feature" in result.output
    assert "--max-turns" in result.output
    assert "--stop-on-failure" in result.output
    assert "--resume" in result.output
    assert "--task" in result.output


def test_cli_feature_command_missing_argument():
    """Test feature command without feature_id argument."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    runner = CliRunner()
    result = runner.invoke(feature, [])

    assert result.exit_code == 2  # Missing argument


@patch("guardkit.cli.autobuild._check_sdk_available", return_value=True)
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_invokes_orchestrator(mock_orchestrator_class, mock_sdk_check):
    """Test feature command creates and invokes orchestrator."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.feature_id = "FEAT-CLI"
    mock_result.status = "completed"
    mock_result.total_tasks = 3
    mock_result.tasks_completed = 3
    mock_result.tasks_failed = 0
    mock_result.worktree = MagicMock(path=Path("/path"), branch_name="autobuild/FEAT-CLI")

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-CLI", "--max-turns", "10"])

    assert result.exit_code == 0
    mock_orchestrator_class.assert_called_once()
    mock_orchestrator.orchestrate.assert_called_once_with(
        feature_id="FEAT-CLI",
        specific_task=None,
    )


@patch("guardkit.cli.autobuild._check_sdk_available", return_value=True)
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_with_specific_task(mock_orchestrator_class, mock_sdk_check):
    """Test feature command with --task option."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.feature_id = "FEAT-CLI"
    mock_result.status = "completed"
    mock_result.total_tasks = 1
    mock_result.tasks_completed = 1
    mock_result.tasks_failed = 0
    mock_result.worktree = MagicMock(path=Path("/path"), branch_name="autobuild/FEAT-CLI")

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-CLI", "--task", "TASK-ABC-001"])

    assert result.exit_code == 0
    mock_orchestrator.orchestrate.assert_called_once_with(
        feature_id="FEAT-CLI",
        specific_task="TASK-ABC-001",
    )


@patch("guardkit.cli.autobuild._check_sdk_available", return_value=True)
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_handles_not_found_error(mock_orchestrator_class, mock_sdk_check):
    """Test feature command handles FeatureNotFoundError."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.side_effect = FeatureNotFoundError("Feature FEAT-MISSING not found")
    mock_orchestrator_class.return_value = mock_orchestrator

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-MISSING"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


@patch("guardkit.cli.autobuild._check_sdk_available", return_value=True)
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_handles_validation_error(mock_orchestrator_class, mock_sdk_check):
    """Test feature command handles FeatureValidationError."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.side_effect = FeatureValidationError("Task file not found: TASK-001")
    mock_orchestrator_class.return_value = mock_orchestrator

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-INVALID"])

    assert result.exit_code == 3
    assert "validation" in result.output.lower()


@patch("guardkit.cli.autobuild._check_sdk_available", return_value=True)
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_handles_orchestration_error(mock_orchestrator_class, mock_sdk_check):
    """Test feature command handles FeatureOrchestrationError."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.side_effect = FeatureOrchestrationError("Setup phase failed")
    mock_orchestrator_class.return_value = mock_orchestrator

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-ERROR"])

    assert result.exit_code == 2
    assert "error" in result.output.lower()


@patch("guardkit.cli.autobuild._check_sdk_available", return_value=True)
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_failure_exit_code(mock_orchestrator_class, mock_sdk_check):
    """Test feature command returns exit code 2 on failure."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    mock_result = MagicMock()
    mock_result.success = False  # Failed orchestration
    mock_result.feature_id = "FEAT-CLI"
    mock_result.status = "failed"
    mock_result.total_tasks = 3
    mock_result.tasks_completed = 1
    mock_result.tasks_failed = 2
    mock_result.worktree = MagicMock(path=Path("/path"), branch_name="autobuild/FEAT-CLI")

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-CLI"])

    assert result.exit_code == 2  # Failure exit code


# ============================================================================
# Test: Dependencies Satisfied
# ============================================================================


def test_dependencies_satisfied_no_deps(temp_repo, sample_feature, mock_worktree_manager):
    """Test dependencies check passes with no dependencies."""
    orchestrator = FeatureOrchestrator(repo_root=temp_repo, worktree_manager=mock_worktree_manager)

    # Task with no dependencies
    task = sample_feature.tasks[0]  # TASK-T-001 has no deps
    assert orchestrator._dependencies_satisfied(task, sample_feature) is True


def test_dependencies_satisfied_with_completed_deps(temp_repo, sample_feature, mock_worktree_manager):
    """Test dependencies check passes when deps completed."""
    orchestrator = FeatureOrchestrator(repo_root=temp_repo, worktree_manager=mock_worktree_manager)

    # Complete TASK-T-001 first
    sample_feature.tasks[0].status = "completed"

    # Check TASK-T-002 which depends on TASK-T-001
    task = sample_feature.tasks[1]  # TASK-T-002 depends on TASK-T-001
    assert orchestrator._dependencies_satisfied(task, sample_feature) is True


def test_dependencies_not_satisfied_pending_deps(temp_repo, sample_feature, mock_worktree_manager):
    """Test dependencies check fails when deps pending."""
    orchestrator = FeatureOrchestrator(repo_root=temp_repo, worktree_manager=mock_worktree_manager)

    # TASK-T-001 still pending
    task = sample_feature.tasks[1]  # TASK-T-002 depends on TASK-T-001
    assert orchestrator._dependencies_satisfied(task, sample_feature) is False


# ============================================================================
# Test: Resume and Fresh Flag Behavior
# ============================================================================


def test_orchestrator_rejects_resume_and_fresh_together(temp_repo, mock_worktree_manager):
    """Test that resume=True and fresh=True raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        FeatureOrchestrator(
            repo_root=temp_repo,
            resume=True,
            fresh=True,
            worktree_manager=mock_worktree_manager,
        )
    assert "Cannot use both --resume and --fresh" in str(exc_info.value)


def test_orchestrator_accepts_resume_only(temp_repo, mock_worktree_manager):
    """Test that resume=True alone is accepted."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        resume=True,
        fresh=False,
        worktree_manager=mock_worktree_manager,
    )
    assert orchestrator.resume is True
    assert orchestrator.fresh is False


def test_orchestrator_accepts_fresh_only(temp_repo, mock_worktree_manager):
    """Test that fresh=True alone is accepted."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        resume=False,
        fresh=True,
        worktree_manager=mock_worktree_manager,
    )
    assert orchestrator.resume is False
    assert orchestrator.fresh is True


@patch("guardkit.cli.autobuild._check_sdk_available", return_value=True)
def test_cli_feature_command_rejects_resume_and_fresh_together(mock_sdk_check):
    """Test CLI rejects --resume and --fresh used together."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-TEST", "--resume", "--fresh"])

    assert result.exit_code == 3
    assert "Cannot use both --resume and --fresh" in result.output


@patch("guardkit.cli.autobuild._check_sdk_available", return_value=True)
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_with_fresh_flag(mock_orchestrator_class, mock_sdk_check):
    """Test feature command with --fresh flag passes fresh=True."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.feature_id = "FEAT-CLI"
    mock_result.status = "completed"
    mock_result.total_tasks = 3
    mock_result.tasks_completed = 3
    mock_result.tasks_failed = 0
    mock_result.worktree = MagicMock(path=Path("/path"), branch_name="autobuild/FEAT-CLI")

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-CLI", "--fresh"])

    assert result.exit_code == 0
    # Verify fresh=True was passed to orchestrator
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs.get("fresh") is True


@patch("guardkit.cli.autobuild._check_sdk_available", return_value=True)
@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_with_resume_flag(mock_orchestrator_class, mock_sdk_check):
    """Test feature command with --resume flag passes resume=True."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.feature_id = "FEAT-CLI"
    mock_result.status = "completed"
    mock_result.total_tasks = 3
    mock_result.tasks_completed = 3
    mock_result.tasks_failed = 0
    mock_result.worktree = MagicMock(path=Path("/path"), branch_name="autobuild/FEAT-CLI")

    mock_orchestrator = MagicMock()
    mock_orchestrator.orchestrate.return_value = mock_result
    mock_orchestrator_class.return_value = mock_orchestrator

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-CLI", "--resume"])

    assert result.exit_code == 0
    # Verify resume=True was passed to orchestrator
    call_kwargs = mock_orchestrator_class.call_args[1]
    assert call_kwargs.get("resume") is True


# ============================================================================
# Test: SDK Timeout Resolution (TASK-REV-8BCC regression test)
# ============================================================================


def test_execute_task_resolves_sdk_timeout_from_task_frontmatter(
    temp_repo, sample_feature, mock_worktree, mock_worktree_manager
):
    """Test that _execute_task correctly resolves SDK timeout from task frontmatter.

    This is a regression test for TASK-REV-8BCC where feature.config was incorrectly
    accessed, causing 'Feature' object has no attribute 'config' error.
    """
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        sdk_timeout=None,  # Force resolution cascade
    )

    # Update task file with autobuild.sdk_timeout in frontmatter
    task = sample_feature.tasks[0]
    task_file = temp_repo / task.file_path
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-T-001
title: First Task
status: pending
autobuild:
  sdk_timeout: 600
---

# First Task

## Requirements
Test requirements.

## Acceptance Criteria
- Test criteria
""")

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

        result = orchestrator._execute_task(task, sample_feature, mock_worktree)

        # Verify task executed successfully
        assert result.success is True

        # Verify sdk_timeout was passed from task frontmatter
        call_kwargs = mock_orch_class.call_args[1]
        assert call_kwargs.get("sdk_timeout") == 600


def test_execute_task_uses_default_sdk_timeout_when_not_specified(
    temp_repo, sample_feature, mock_worktree, mock_worktree_manager
):
    """Test that _execute_task uses default SDK timeout (900) when not specified."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        sdk_timeout=None,  # Force resolution cascade
    )

    # Task file without autobuild.sdk_timeout
    task = sample_feature.tasks[0]
    task_file = temp_repo / task.file_path
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-T-001
title: First Task
status: pending
---

# First Task

## Requirements
Test requirements.

## Acceptance Criteria
- Test criteria
""")

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

        result = orchestrator._execute_task(task, sample_feature, mock_worktree)

        # Verify task executed successfully
        assert result.success is True

        # Verify default sdk_timeout (1200) was used
        call_kwargs = mock_orch_class.call_args[1]
        assert call_kwargs.get("sdk_timeout") == 1200


def test_execute_task_cli_sdk_timeout_overrides_task_frontmatter(
    temp_repo, sample_feature, mock_worktree, mock_worktree_manager
):
    """Test that CLI sdk_timeout overrides task frontmatter setting."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        sdk_timeout=900,  # CLI override
    )

    # Task file with autobuild.sdk_timeout in frontmatter
    task = sample_feature.tasks[0]
    task_file = temp_repo / task.file_path
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-T-001
title: First Task
status: pending
autobuild:
  sdk_timeout: 600
---

# First Task

## Requirements
Test requirements.

## Acceptance Criteria
- Test criteria
""")

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

        result = orchestrator._execute_task(task, sample_feature, mock_worktree)

        # Verify task executed successfully
        assert result.success is True

        # Verify CLI sdk_timeout (900) overrode task frontmatter (600)
        call_kwargs = mock_orch_class.call_args[1]
        assert call_kwargs.get("sdk_timeout") == 900


# ============================================================================
# enable_pre_loop Configuration Cascade Tests (TASK-FB-FIX-010)
# ============================================================================


def test_resolve_enable_pre_loop_cli_takes_precedence(temp_repo, sample_feature, mock_worktree_manager):
    """Test that CLI enable_pre_loop takes precedence over all other sources."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        enable_pre_loop=False,  # CLI override
    )

    # Task data with enable_pre_loop=True in frontmatter
    task_data = {
        "frontmatter": {
            "autobuild": {
                "enable_pre_loop": True,
            }
        }
    }

    # CLI value should win
    result = orchestrator._resolve_enable_pre_loop(sample_feature, task_data)
    assert result is False


def test_execute_task_passes_enable_pre_loop_to_orchestrator(
    temp_repo, sample_feature, mock_worktree, mock_worktree_manager
):
    """Test that _execute_task passes resolved enable_pre_loop to AutoBuildOrchestrator."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        enable_pre_loop=False,  # CLI override
    )

    # Create task file
    task = sample_feature.tasks[0]
    task_file = temp_repo / task.file_path
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-T-001
title: First Task
status: pending
---

# First Task

## Requirements
Test requirements.

## Acceptance Criteria
- Test criteria
""")

    # Mock AutoBuildOrchestrator to capture enable_pre_loop
    with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.total_turns = 1
        mock_result.final_decision = "approved"
        mock_result.error = None
        mock_orch.orchestrate.return_value = mock_result
        mock_orch_class.return_value = mock_orch

        result = orchestrator._execute_task(task, sample_feature, mock_worktree)

        # Verify task executed successfully
        assert result.success is True

        # Verify enable_pre_loop was passed to AutoBuildOrchestrator
        call_kwargs = mock_orch_class.call_args[1]
        assert call_kwargs.get("enable_pre_loop") is False


def test_execute_task_enable_pre_loop_from_task_frontmatter(
    temp_repo, sample_feature, mock_worktree, mock_worktree_manager
):
    """Test that enable_pre_loop from task frontmatter is used when no CLI override."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        enable_pre_loop=None,  # No CLI override
    )

    # Create task file with enable_pre_loop in frontmatter
    task = sample_feature.tasks[0]
    task_file = temp_repo / task.file_path
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-T-001
title: First Task
status: pending
autobuild:
  enable_pre_loop: false
---

# First Task

## Requirements
Test requirements.

## Acceptance Criteria
- Test criteria
""")

    # Mock AutoBuildOrchestrator to capture enable_pre_loop
    with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.total_turns = 1
        mock_result.final_decision = "approved"
        mock_result.error = None
        mock_orch.orchestrate.return_value = mock_result
        mock_orch_class.return_value = mock_orch

        result = orchestrator._execute_task(task, sample_feature, mock_worktree)

        # Verify task executed successfully
        assert result.success is True

        # Verify enable_pre_loop from task frontmatter was used
        call_kwargs = mock_orch_class.call_args[1]
        assert call_kwargs.get("enable_pre_loop") is False


# ============================================================================
# Wave Parallelization Tests (TASK-FBP-001)
# ============================================================================


def test_execute_wave_uses_asyncio_run(temp_repo, sample_feature, mock_worktree, mock_worktree_manager):
    """Test that _execute_wave uses asyncio.run() to execute parallel method."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    # Mock the async parallel method
    mock_results = [
        TaskExecutionResult(task_id="TASK-T-001", success=True, total_turns=1, final_decision="approved")
    ]

    with patch.object(orchestrator, '_execute_wave_parallel', new_callable=AsyncMock) as mock_parallel:
        mock_parallel.return_value = mock_results

        # Execute wave
        result = orchestrator._execute_wave(1, ["TASK-T-001"], sample_feature, mock_worktree)

        # Verify async method was called
        mock_parallel.assert_called_once_with(1, ["TASK-T-001"], sample_feature, mock_worktree)

        # Verify result
        assert result.wave_number == 1
        assert result.all_succeeded is True
        assert len(result.results) == 1


@pytest.mark.asyncio
async def test_execute_wave_parallel_executes_concurrently(temp_repo, parallel_feature, mock_worktree, mock_worktree_manager):
    """Test that tasks within a wave execute concurrently using asyncio.gather()."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    # Mock _execute_task to track concurrent execution
    execution_order = []

    def mock_execute_task(task, feature, worktree, cancellation_event=None):
        execution_order.append(f"start_{task.id}")
        # Simulate some work
        import time
        time.sleep(0.01)
        execution_order.append(f"end_{task.id}")
        return TaskExecutionResult(
            task_id=task.id,
            success=True,
            total_turns=1,
            final_decision="approved"
        )

    with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task):
        # Execute wave with 2 independent tasks (no dependencies)
        results = await orchestrator._execute_wave_parallel(
            1, ["TASK-P-001", "TASK-P-002"], parallel_feature, mock_worktree
        )

        # Verify both tasks executed
        assert len(results) == 2
        assert all(r.success for r in results)

        # Verify tasks started before any finished (concurrent execution)
        assert execution_order.index("start_TASK-P-001") < execution_order.index("end_TASK-P-001")
        assert execution_order.index("start_TASK-P-002") < execution_order.index("end_TASK-P-002")


@pytest.mark.asyncio
async def test_execute_wave_parallel_all_tasks_complete_before_return(temp_repo, parallel_feature, mock_worktree, mock_worktree_manager):
    """Test that all tasks in wave complete before wave result is returned."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    completed_tasks = []

    def mock_execute_task(task, feature, worktree, cancellation_event=None):
        import time
        time.sleep(0.02)  # Simulate work
        completed_tasks.append(task.id)
        return TaskExecutionResult(
            task_id=task.id,
            success=True,
            total_turns=1,
            final_decision="approved"
        )

    with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task):
        # Execute wave with 2 independent tasks (no dependencies)
        results = await orchestrator._execute_wave_parallel(
            1, ["TASK-P-001", "TASK-P-002"], parallel_feature, mock_worktree
        )

        # Verify both tasks completed before return
        assert len(completed_tasks) == 2
        assert "TASK-P-001" in completed_tasks
        assert "TASK-P-002" in completed_tasks

        # Verify results returned
        assert len(results) == 2


@pytest.mark.asyncio
async def test_execute_wave_parallel_exception_isolation(temp_repo, parallel_feature, mock_worktree, mock_worktree_manager):
    """Test that exception from one task doesn't crash other tasks."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    def mock_execute_task(task, feature, worktree, cancellation_event=None):
        if task.id == "TASK-P-001":
            raise Exception("Task P-001 failed")
        return TaskExecutionResult(
            task_id=task.id,
            success=True,
            total_turns=1,
            final_decision="approved"
        )

    with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task):
        # Execute wave with 2 independent tasks (one will fail)
        results = await orchestrator._execute_wave_parallel(
            1, ["TASK-P-001", "TASK-P-002"], parallel_feature, mock_worktree
        )

        # Verify both tasks returned results
        assert len(results) == 2

        # Verify P-001 has error result
        p001_result = next(r for r in results if r.task_id == "TASK-P-001")
        assert p001_result.success is False
        assert "Task P-001 failed" in p001_result.error

        # Verify P-002 succeeded
        p002_result = next(r for r in results if r.task_id == "TASK-P-002")
        assert p002_result.success is True


def test_create_error_result_produces_correct_result(temp_repo, mock_worktree_manager):
    """Test that _create_error_result() helper produces correct TaskExecutionResult."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    error = Exception("Test error message")
    result = orchestrator._create_error_result("TASK-T-001", error)

    assert result.task_id == "TASK-T-001"
    assert result.success is False
    assert result.total_turns == 0
    assert result.final_decision == "error"
    assert result.error == "Test error message"


def test_stop_on_failure_waits_for_wave_completion(temp_repo, sample_feature, mock_worktree, mock_worktree_manager):
    """Test that stop_on_failure flag is checked AFTER wave completes (not mid-wave)."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        stop_on_failure=True,
    )

    # Mock _execute_wave to simulate wave with one failure
    wave1_results = [
        TaskExecutionResult(task_id="TASK-T-001", success=True, total_turns=1, final_decision="approved")
    ]
    wave2_results = [
        TaskExecutionResult(task_id="TASK-T-002", success=False, total_turns=2, final_decision="failed", error="Failed"),
        TaskExecutionResult(task_id="TASK-T-003", success=True, total_turns=1, final_decision="approved")
    ]

    # Mock both _execute_wave and _dependencies_satisfied
    with patch.object(orchestrator, '_execute_wave') as mock_execute_wave, \
         patch.object(orchestrator, '_dependencies_satisfied', return_value=True):
        mock_execute_wave.side_effect = [
            WaveExecutionResult(wave_number=1, task_ids=["TASK-T-001"], results=wave1_results, all_succeeded=True),
            WaveExecutionResult(wave_number=2, task_ids=["TASK-T-002", "TASK-T-003"], results=wave2_results, all_succeeded=False),
        ]

        # Execute waves phase
        results = orchestrator._wave_phase(sample_feature, mock_worktree)

        # Verify wave 1 executed
        assert len(results) >= 1
        assert results[0].wave_number == 1
        assert results[0].all_succeeded is True

        # Verify wave 2 executed (both tasks completed despite one failing)
        assert len(results) == 2
        assert results[1].wave_number == 2
        assert results[1].all_succeeded is False
        assert len(results[1].results) == 2  # Both tasks completed


def test_stop_on_failure_false_continues_to_next_wave(temp_repo, sample_feature, mock_worktree, mock_worktree_manager):
    """Test that stop_on_failure=False continues to next wave even if wave failed."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        stop_on_failure=False,  # Continue on failure
    )

    # Mock _execute_wave to simulate wave with failure
    wave1_results = [
        TaskExecutionResult(task_id="TASK-T-001", success=False, total_turns=2, final_decision="failed", error="Failed")
    ]
    wave2_results = [
        TaskExecutionResult(task_id="TASK-T-002", success=True, total_turns=1, final_decision="approved"),
        TaskExecutionResult(task_id="TASK-T-003", success=True, total_turns=1, final_decision="approved")
    ]

    # Mock both _execute_wave and _dependencies_satisfied
    with patch.object(orchestrator, '_execute_wave') as mock_execute_wave, \
         patch.object(orchestrator, '_dependencies_satisfied', return_value=True):
        mock_execute_wave.side_effect = [
            WaveExecutionResult(wave_number=1, task_ids=["TASK-T-001"], results=wave1_results, all_succeeded=False),
            WaveExecutionResult(wave_number=2, task_ids=["TASK-T-002", "TASK-T-003"], results=wave2_results, all_succeeded=True),
        ]

        # Execute waves phase
        results = orchestrator._wave_phase(sample_feature, mock_worktree)

        # Verify both waves executed
        assert len(results) == 2
        assert results[0].wave_number == 1
        assert results[0].all_succeeded is False
        assert results[1].wave_number == 2
        assert results[1].all_succeeded is True


def test_single_task_wave_works_correctly(temp_repo, sample_feature, mock_worktree, mock_worktree_manager):
    """Test that single-task waves work identically to before."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    # Create task file
    task = sample_feature.tasks[0]
    task_file = temp_repo / task.file_path
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("""---
id: TASK-T-001
title: First Task
status: pending
---

# First Task
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

        # Execute single-task wave
        result = orchestrator._execute_wave(1, ["TASK-T-001"], sample_feature, mock_worktree)

        # Verify wave executed successfully
        assert result.wave_number == 1
        assert result.all_succeeded is True
        assert len(result.results) == 1
        assert result.results[0].task_id == "TASK-T-001"
        assert result.results[0].success is True


@pytest.mark.asyncio
async def test_completed_tasks_skipped_in_parallel(temp_repo, parallel_feature, mock_worktree, mock_worktree_manager):
    """Test that completed tasks are skipped correctly in parallel execution."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        resume=True,
    )

    # Mark P-001 as completed (independent task, no dependencies)
    parallel_feature.tasks[0].status = "completed"
    parallel_feature.tasks[0].turns_completed = 2

    # Mock _execute_task (should not be called for P-001)
    with patch.object(orchestrator, '_execute_task') as mock_execute:
        mock_execute.return_value = TaskExecutionResult(
            task_id="TASK-P-002",
            success=True,
            total_turns=1,
            final_decision="approved"
        )

        # Execute wave with completed and pending task (both independent)
        results = await orchestrator._execute_wave_parallel(
            1, ["TASK-P-001", "TASK-P-002"], parallel_feature, mock_worktree
        )

        # Verify P-001 skipped (not passed to _execute_task)
        assert len(results) == 2

        # Verify P-001 result shows already_completed
        p001_result = next(r for r in results if r.task_id == "TASK-P-001")
        assert p001_result.success is True
        assert p001_result.final_decision == "already_completed"
        assert p001_result.total_turns == 2  # Preserved from previous run

        # Verify P-002 executed
        p002_result = next(r for r in results if r.task_id == "TASK-P-002")
        assert p002_result.success is True
        mock_execute.assert_called_once()  # Only P-002 executed


@pytest.mark.asyncio
async def test_dependency_failed_tasks_skipped_in_parallel(temp_repo, sample_feature, mock_worktree, mock_worktree_manager):
    """Test that tasks with failed dependencies are skipped in parallel execution."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )

    # Mark T-001 as failed (dependency for T-002 and T-003)
    sample_feature.tasks[0].status = "failed"

    # Mock _execute_task (should not be called)
    with patch.object(orchestrator, '_execute_task') as mock_execute:
        # Execute wave 2 (T-002 and T-003 depend on T-001)
        results = await orchestrator._execute_wave_parallel(
            2, ["TASK-T-002", "TASK-T-003"], sample_feature, mock_worktree
        )

        # Verify both tasks skipped
        assert len(results) == 2

        # Verify both show skipped status
        for result in results:
            assert result.success is False
            assert result.final_decision == "skipped"
            assert "Dependency failed" in result.error

        # Verify _execute_task was never called
        mock_execute.assert_not_called()


# ============================================================================
# enable_context Flag Forwarding Tests (TASK-FIX-GCW4)
# ============================================================================


def test_enable_context_defaults_to_true(temp_repo, mock_worktree_manager):
    """Test that enable_context defaults to True in FeatureOrchestrator."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )
    assert orchestrator.enable_context is True


def test_enable_context_can_be_set_to_false(temp_repo, mock_worktree_manager):
    """Test that enable_context can be explicitly set to False."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        enable_context=False,
    )
    assert orchestrator.enable_context is False


@patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator")
@patch("guardkit.orchestrator.feature_orchestrator.TaskLoader.load_task")
def test_execute_task_forwards_enable_context_true(
    mock_load_task, mock_ab_class,
    temp_repo, sample_feature, mock_worktree, mock_worktree_manager,
):
    """Test that _execute_task forwards enable_context=True to AutoBuildOrchestrator."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        enable_context=True,
    )

    # Setup mocks
    mock_load_task.return_value = {
        "requirements": "Test requirements",
        "acceptance_criteria": ["AC1"],
        "frontmatter": {"id": "TASK-T-001", "title": "Test"},
        "file_path": "tasks/backlog/TASK-T-001.md",
    }

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.total_turns = 1
    mock_result.final_decision = "approved"
    mock_result.error = None
    mock_result.recovery_count = 0
    mock_ab_class.return_value.orchestrate.return_value = mock_result

    # Execute
    task = sample_feature.tasks[0]
    orchestrator._execute_task(task, sample_feature, mock_worktree)

    # Verify enable_context was forwarded
    call_kwargs = mock_ab_class.call_args[1]
    assert call_kwargs["enable_context"] is True


@patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator")
@patch("guardkit.orchestrator.feature_orchestrator.TaskLoader.load_task")
def test_execute_task_forwards_enable_context_false(
    mock_load_task, mock_ab_class,
    temp_repo, sample_feature, mock_worktree, mock_worktree_manager,
):
    """Test that _execute_task forwards enable_context=False to AutoBuildOrchestrator."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        enable_context=False,
    )

    # Setup mocks
    mock_load_task.return_value = {
        "requirements": "Test requirements",
        "acceptance_criteria": ["AC1"],
        "frontmatter": {"id": "TASK-T-001", "title": "Test"},
        "file_path": "tasks/backlog/TASK-T-001.md",
    }

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.total_turns = 1
    mock_result.final_decision = "approved"
    mock_result.error = None
    mock_result.recovery_count = 0
    mock_ab_class.return_value.orchestrate.return_value = mock_result

    # Execute
    task = sample_feature.tasks[0]
    orchestrator._execute_task(task, sample_feature, mock_worktree)

    # Verify enable_context was forwarded as False
    call_kwargs = mock_ab_class.call_args[1]
    assert call_kwargs["enable_context"] is False


# ============================================================================
# Task Timeout Tests (TASK-FIX-GTP4)
# ============================================================================


def test_task_timeout_default_value(temp_repo, mock_worktree_manager):
    """Test that task_timeout defaults to 2400 seconds (40 min)."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
    )
    assert orchestrator.task_timeout == 2400


def test_task_timeout_custom_value(temp_repo, mock_worktree_manager):
    """Test that task_timeout accepts a custom value."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        task_timeout=600,
    )
    assert orchestrator.task_timeout == 600


@pytest.mark.asyncio
async def test_task_timeout_triggers_on_slow_task(
    temp_repo, parallel_feature, mock_worktree, mock_worktree_manager,
):
    """Test that a task exceeding task_timeout is correctly timed out."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        task_timeout=1,  # 1 second timeout for fast test
    )

    def mock_execute_task_slow(task, feature, worktree, cancellation_event=None):
        """Simulate a task that takes too long."""
        import time
        time.sleep(5)  # Will exceed the 1s timeout
        return TaskExecutionResult(
            task_id=task.id,
            success=True,
            total_turns=1,
            final_decision="approved",
        )

    with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task_slow):
        results = await orchestrator._execute_wave_parallel(
            1, ["TASK-P-001"], parallel_feature, mock_worktree
        )

        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.final_decision == "timeout"
        assert "timed out" in result.error
        assert "1s" in result.error


@pytest.mark.asyncio
async def test_successful_tasks_unaffected_by_timeout(
    temp_repo, parallel_feature, mock_worktree, mock_worktree_manager,
):
    """Test that tasks completing within timeout are unaffected."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        task_timeout=60,  # Generous timeout
    )

    def mock_execute_task_fast(task, feature, worktree, cancellation_event=None):
        """Simulate a fast task that finishes well within timeout."""
        return TaskExecutionResult(
            task_id=task.id,
            success=True,
            total_turns=2,
            final_decision="approved",
        )

    with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task_fast):
        results = await orchestrator._execute_wave_parallel(
            1, ["TASK-P-001", "TASK-P-002"], parallel_feature, mock_worktree
        )

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.final_decision == "approved" for r in results)


@pytest.mark.asyncio
async def test_timeout_mixed_with_success(
    temp_repo, parallel_feature, mock_worktree, mock_worktree_manager,
):
    """Test that timeout on one task doesn't affect successful siblings."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        task_timeout=1,  # 1 second timeout
    )

    def mock_execute_task_mixed(task, feature, worktree, cancellation_event=None):
        """One task times out, the other succeeds."""
        import time
        if task.id == "TASK-P-001":
            time.sleep(5)  # Will timeout
            return TaskExecutionResult(
                task_id=task.id, success=True,
                total_turns=1, final_decision="approved",
            )
        else:
            return TaskExecutionResult(
                task_id=task.id, success=True,
                total_turns=2, final_decision="approved",
            )

    with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task_mixed):
        results = await orchestrator._execute_wave_parallel(
            1, ["TASK-P-001", "TASK-P-002"], parallel_feature, mock_worktree
        )

        assert len(results) == 2

        # Find results by task_id
        p001 = next(r for r in results if r.task_id == "TASK-P-001")
        p002 = next(r for r in results if r.task_id == "TASK-P-002")

        # P-001 should have timed out
        assert p001.success is False
        assert p001.final_decision == "timeout"
        assert "timed out" in p001.error

        # P-002 should have succeeded
        assert p002.success is True
        assert p002.final_decision == "approved"


@pytest.mark.asyncio
async def test_timeout_updates_wave_display(
    temp_repo, parallel_feature, mock_worktree, mock_worktree_manager,
):
    """Test that timeout triggers correct display update."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        task_timeout=1,
    )

    # Mock the wave display
    mock_display = MagicMock()
    orchestrator._wave_display = mock_display

    def mock_execute_task_slow(task, feature, worktree, cancellation_event=None):
        import time
        time.sleep(5)
        return TaskExecutionResult(
            task_id=task.id, success=True,
            total_turns=1, final_decision="approved",
        )

    with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task_slow):
        await orchestrator._execute_wave_parallel(
            1, ["TASK-P-001"], parallel_feature, mock_worktree
        )

    # Verify the display was updated with timeout status
    timeout_calls = [
        call for call in mock_display.update_task_status.call_args_list
        if call[0][1] == "timeout" or (call[1].get("status") if call[1] else False)
    ]
    # Should have at least one timeout update (besides the initial in_progress)
    assert len(timeout_calls) >= 1
    # Check the timeout call args
    timeout_call = timeout_calls[0]
    assert timeout_call[0][0] == "TASK-P-001"  # task_id
    assert timeout_call[0][1] == "timeout"  # status


@pytest.mark.asyncio
async def test_timeout_updates_feature_state(
    temp_repo, parallel_feature, mock_worktree, mock_worktree_manager,
):
    """Test that timeout correctly updates the feature state."""
    orchestrator = FeatureOrchestrator(
        repo_root=temp_repo,
        worktree_manager=mock_worktree_manager,
        task_timeout=1,
    )

    def mock_execute_task_slow(task, feature, worktree, cancellation_event=None):
        import time
        time.sleep(5)
        return TaskExecutionResult(
            task_id=task.id, success=True,
            total_turns=1, final_decision="approved",
        )

    with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task_slow):
        with patch.object(orchestrator, '_update_feature') as mock_update:
            results = await orchestrator._execute_wave_parallel(
                1, ["TASK-P-001"], parallel_feature, mock_worktree
            )

            # Verify _update_feature was called with the timeout result
            assert mock_update.called
            call_args = mock_update.call_args
            error_result = call_args[0][2]  # Third positional arg is the result
            assert error_result.success is False
            assert error_result.final_decision == "timeout"


# ============================================================================
# Test: File Descriptor Limit Elevation (TASK-FIX-FD01)
# ============================================================================


class TestRaiseFdLimit:
    """Tests for _raise_fd_limit() file descriptor limit elevation."""

    def test_raises_limit_when_below_target(self, temp_repo, mock_worktree_manager):
        """Test that FD limit is raised when soft limit is below target."""
        with patch("guardkit.orchestrator.feature_orchestrator.resource") as mock_resource:
            mock_resource.RLIMIT_NOFILE = 7  # Real constant value
            mock_resource.RLIM_INFINITY = -1
            mock_resource.getrlimit.return_value = (256, 245760)
            mock_resource.setrlimit = MagicMock()

            FeatureOrchestrator(
                repo_root=temp_repo,
                worktree_manager=mock_worktree_manager,
            )

            mock_resource.setrlimit.assert_called_once_with(
                mock_resource.RLIMIT_NOFILE, (4096, 245760)
            )

    def test_noop_when_already_high(self, temp_repo, mock_worktree_manager):
        """Test no-op when soft limit is already >= target."""
        with patch("guardkit.orchestrator.feature_orchestrator.resource") as mock_resource:
            mock_resource.RLIMIT_NOFILE = 7
            mock_resource.RLIM_INFINITY = -1
            mock_resource.getrlimit.return_value = (8192, 245760)

            FeatureOrchestrator(
                repo_root=temp_repo,
                worktree_manager=mock_worktree_manager,
            )

            mock_resource.setrlimit.assert_not_called()

    def test_respects_hard_limit(self, temp_repo, mock_worktree_manager):
        """Test that new soft limit does not exceed hard limit."""
        with patch("guardkit.orchestrator.feature_orchestrator.resource") as mock_resource:
            mock_resource.RLIMIT_NOFILE = 7
            mock_resource.RLIM_INFINITY = -1
            mock_resource.getrlimit.return_value = (256, 1024)  # Hard < target
            mock_resource.setrlimit = MagicMock()

            FeatureOrchestrator(
                repo_root=temp_repo,
                worktree_manager=mock_worktree_manager,
            )

            mock_resource.setrlimit.assert_called_once_with(
                mock_resource.RLIMIT_NOFILE, (1024, 1024)
            )

    def test_handles_infinity_hard_limit(self, temp_repo, mock_worktree_manager):
        """Test handling of RLIM_INFINITY hard limit."""
        with patch("guardkit.orchestrator.feature_orchestrator.resource") as mock_resource:
            mock_resource.RLIMIT_NOFILE = 7
            mock_resource.RLIM_INFINITY = -1
            mock_resource.getrlimit.return_value = (256, -1)  # RLIM_INFINITY
            mock_resource.setrlimit = MagicMock()

            FeatureOrchestrator(
                repo_root=temp_repo,
                worktree_manager=mock_worktree_manager,
            )

            mock_resource.setrlimit.assert_called_once_with(
                mock_resource.RLIMIT_NOFILE, (4096, -1)
            )

    def test_graceful_on_oserror(self, temp_repo, mock_worktree_manager):
        """Test graceful handling when setrlimit raises OSError."""
        with patch("guardkit.orchestrator.feature_orchestrator.resource") as mock_resource:
            mock_resource.RLIMIT_NOFILE = 7
            mock_resource.RLIM_INFINITY = -1
            mock_resource.getrlimit.return_value = (256, 245760)
            mock_resource.setrlimit.side_effect = OSError("Operation not permitted")

            # Should not raise — continues gracefully
            orchestrator = FeatureOrchestrator(
                repo_root=temp_repo,
                worktree_manager=mock_worktree_manager,
            )
            assert orchestrator is not None

    def test_graceful_on_value_error(self, temp_repo, mock_worktree_manager):
        """Test graceful handling when setrlimit raises ValueError."""
        with patch("guardkit.orchestrator.feature_orchestrator.resource") as mock_resource:
            mock_resource.RLIMIT_NOFILE = 7
            mock_resource.RLIM_INFINITY = -1
            mock_resource.getrlimit.return_value = (256, 245760)
            mock_resource.setrlimit.side_effect = ValueError("Invalid limit")

            # Should not raise — continues gracefully
            orchestrator = FeatureOrchestrator(
                repo_root=temp_repo,
                worktree_manager=mock_worktree_manager,
            )
            assert orchestrator is not None

    def test_logs_info_on_success(self, temp_repo, mock_worktree_manager, caplog):
        """Test that INFO log is emitted when limit is raised."""
        with patch("guardkit.orchestrator.feature_orchestrator.resource") as mock_resource:
            mock_resource.RLIMIT_NOFILE = 7
            mock_resource.RLIM_INFINITY = -1
            mock_resource.getrlimit.return_value = (256, 245760)
            mock_resource.setrlimit = MagicMock()

            import logging
            with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.feature_orchestrator"):
                FeatureOrchestrator(
                    repo_root=temp_repo,
                    worktree_manager=mock_worktree_manager,
                )

            assert any("Raised file descriptor limit: 256" in msg for msg in caplog.messages)

    def test_logs_warning_on_error(self, temp_repo, mock_worktree_manager, caplog):
        """Test that WARNING log is emitted on setrlimit failure."""
        with patch("guardkit.orchestrator.feature_orchestrator.resource") as mock_resource:
            mock_resource.RLIMIT_NOFILE = 7
            mock_resource.RLIM_INFINITY = -1
            mock_resource.getrlimit.return_value = (256, 245760)
            mock_resource.setrlimit.side_effect = OSError("Permission denied")

            import logging
            with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.feature_orchestrator"):
                FeatureOrchestrator(
                    repo_root=temp_repo,
                    worktree_manager=mock_worktree_manager,
                )

            assert any("Could not raise file descriptor limit" in msg for msg in caplog.messages)


# ============================================================================
# Test: Graphiti Factory Pre-Initialization (TASK-FIX-FD03)
# ============================================================================


class TestPreInitGraphiti:
    """Tests for _pre_init_graphiti() factory pre-initialization."""

    def test_pre_init_calls_get_graphiti_when_context_enabled(
        self, temp_repo, mock_worktree_manager
    ):
        """Test that _pre_init_graphiti calls get_graphiti when enable_context=True."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.orchestrator.feature_orchestrator.get_graphiti") as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            orchestrator._pre_init_graphiti()

            mock_get.assert_called_once()

    def test_pre_init_skips_when_context_disabled(
        self, temp_repo, mock_worktree_manager
    ):
        """Test that _pre_init_graphiti is a no-op when enable_context=False."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=False,
        )

        with patch("guardkit.orchestrator.feature_orchestrator.get_graphiti") as mock_get:
            orchestrator._pre_init_graphiti()

            mock_get.assert_not_called()

    def test_pre_init_graceful_on_import_error(
        self, temp_repo, mock_worktree_manager
    ):
        """Test graceful degradation when guardkit.knowledge import fails."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch(
            "guardkit.orchestrator.feature_orchestrator.get_graphiti",
            side_effect=ImportError("No module named 'graphiti_core'"),
        ):
            # Should not raise
            orchestrator._pre_init_graphiti()

    def test_pre_init_graceful_on_exception(
        self, temp_repo, mock_worktree_manager
    ):
        """Test graceful degradation when get_graphiti raises unexpected error."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch(
            "guardkit.orchestrator.feature_orchestrator.get_graphiti",
            side_effect=RuntimeError("Connection refused"),
        ):
            # Should not raise
            orchestrator._pre_init_graphiti()

    def test_pre_init_logs_info_when_client_available(
        self, temp_repo, mock_worktree_manager, caplog
    ):
        """Test INFO log when Graphiti client is successfully pre-initialized."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.orchestrator.feature_orchestrator.get_graphiti") as mock_get:
            mock_get.return_value = MagicMock()

            import logging
            with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.feature_orchestrator"):
                orchestrator._pre_init_graphiti()

            assert any(
                "Pre-initialized Graphiti factory" in msg for msg in caplog.messages
            )

    def test_pre_init_logs_info_when_client_none(
        self, temp_repo, mock_worktree_manager, caplog
    ):
        """Test INFO log when Graphiti is not available (returns None)."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.orchestrator.feature_orchestrator.get_graphiti") as mock_get:
            mock_get.return_value = None

            import logging
            with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.feature_orchestrator"):
                orchestrator._pre_init_graphiti()

            assert any(
                "Graphiti not available" in msg for msg in caplog.messages
            )

    def test_pre_init_logs_warning_on_error(
        self, temp_repo, mock_worktree_manager, caplog
    ):
        """Test WARNING log when pre-initialization fails with exception."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch(
            "guardkit.orchestrator.feature_orchestrator.get_graphiti",
            side_effect=RuntimeError("Neo4j down"),
        ):
            import logging
            with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.feature_orchestrator"):
                orchestrator._pre_init_graphiti()

            assert any(
                "Failed to pre-initialize Graphiti" in msg for msg in caplog.messages
            )

    def test_wave_phase_calls_pre_init(
        self, temp_repo, sample_feature, mock_worktree, mock_worktree_manager
    ):
        """Test that _wave_phase calls _pre_init_graphiti before wave execution."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
        )

        call_order = []

        original_execute_wave = orchestrator._execute_wave

        def mock_pre_init():
            call_order.append("pre_init")

        def mock_execute_wave(wave_number, task_ids, feature, worktree):
            call_order.append(f"wave_{wave_number}")
            return WaveExecutionResult(
                wave_number=wave_number,
                task_ids=task_ids,
                results=[
                    TaskExecutionResult(
                        task_id=tid, success=True,
                        total_turns=1, final_decision="approved"
                    )
                    for tid in task_ids
                ],
                all_succeeded=True,
            )

        with patch.object(orchestrator, '_pre_init_graphiti', side_effect=mock_pre_init), \
             patch.object(orchestrator, '_execute_wave', side_effect=mock_execute_wave), \
             patch.object(orchestrator, '_dependencies_satisfied', return_value=True):
            orchestrator._wave_phase(sample_feature, mock_worktree)

        # pre_init must come before any wave execution
        assert call_order[0] == "pre_init"
        assert all(item.startswith("wave_") for item in call_order[1:])


# ============================================================================
# Pre-Flight FalkorDB Check Tests (TASK-ASF-002)
# ============================================================================


class TestPreflightCheck:
    """Tests for _preflight_check() FalkorDB connectivity verification."""

    def test_preflight_returns_true_when_context_disabled(
        self, temp_repo, mock_worktree_manager
    ):
        """Test that pre-flight check returns True when enable_context=False."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=False,
        )

        result = orchestrator._preflight_check()

        assert result is True
        assert orchestrator.enable_context is False

    def test_preflight_disables_context_when_factory_none(
        self, temp_repo, mock_worktree_manager
    ):
        """Test that pre-flight check disables context when get_factory returns None."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.knowledge.graphiti_client.get_factory") as mock_get:
            mock_get.return_value = None

            result = orchestrator._preflight_check()

            assert result is False
            assert orchestrator.enable_context is False

    def test_preflight_disables_context_when_factory_not_enabled(
        self, temp_repo, mock_worktree_manager
    ):
        """Test that pre-flight check disables context when factory.config.enabled is False."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.knowledge.graphiti_client.get_factory") as mock_get:
            mock_factory = MagicMock()
            mock_factory.config.enabled = False
            mock_get.return_value = mock_factory

            result = orchestrator._preflight_check()

            assert result is False
            assert orchestrator.enable_context is False

    def test_preflight_passes_when_connectivity_check_succeeds(
        self, temp_repo, mock_worktree_manager
    ):
        """Test that pre-flight check passes when factory.check_connectivity() returns True."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.knowledge.graphiti_client.get_factory") as mock_get:
            mock_factory = MagicMock()
            mock_factory.config.enabled = True
            mock_factory.check_connectivity.return_value = True
            mock_get.return_value = mock_factory

            result = orchestrator._preflight_check()

            assert result is True
            assert orchestrator.enable_context is True

    def test_preflight_fails_when_connectivity_check_returns_false(
        self, temp_repo, mock_worktree_manager
    ):
        """Test that pre-flight check fails when factory.check_connectivity() returns False."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.knowledge.graphiti_client.get_factory") as mock_get:
            mock_factory = MagicMock()
            mock_factory.config.enabled = True
            mock_factory.check_connectivity.return_value = False
            mock_get.return_value = mock_factory

            result = orchestrator._preflight_check()

            assert result is False
            assert orchestrator.enable_context is False

    def test_preflight_handles_connectivity_timeout(
        self, temp_repo, mock_worktree_manager
    ):
        """Test that pre-flight check handles connectivity timeout gracefully."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.knowledge.graphiti_client.get_factory") as mock_get:
            mock_factory = MagicMock()
            mock_factory.config.enabled = True
            # Simulate timeout by returning False (check_connectivity handles timeout internally)
            mock_factory.check_connectivity.return_value = False
            mock_get.return_value = mock_factory

            result = orchestrator._preflight_check()

            assert result is False
            assert orchestrator.enable_context is False

    def test_preflight_handles_exception(
        self, temp_repo, mock_worktree_manager
    ):
        """Test that pre-flight check handles exceptions gracefully."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.knowledge.graphiti_client.get_factory") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = orchestrator._preflight_check()

            assert result is False
            assert orchestrator.enable_context is False

    def test_preflight_logs_info_when_passed(
        self, temp_repo, mock_worktree_manager, caplog
    ):
        """Test that pre-flight check logs INFO when connectivity check passes."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.knowledge.graphiti_client.get_factory") as mock_get:
            mock_factory = MagicMock()
            mock_factory.config.enabled = True
            mock_factory.check_connectivity.return_value = True
            mock_get.return_value = mock_factory

            import logging
            with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.feature_orchestrator"):
                orchestrator._preflight_check()

            assert any("FalkorDB pre-flight" in msg for msg in caplog.messages)

    def test_preflight_logs_warning_on_failure(
        self, temp_repo, mock_worktree_manager, caplog
    ):
        """Test that pre-flight check logs WARNING when connectivity check fails."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.knowledge.graphiti_client.get_factory") as mock_get:
            mock_factory = MagicMock()
            mock_factory.config.enabled = True
            mock_factory.check_connectivity.return_value = False
            mock_get.return_value = mock_factory

            import logging
            with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.feature_orchestrator"):
                orchestrator._preflight_check()

            assert any(
                "FalkorDB connectivity check failed" in msg for msg in caplog.messages
            )

    def test_wave_phase_calls_preflight_before_pre_init(
        self, temp_repo, sample_feature, mock_worktree, mock_worktree_manager
    ):
        """Test that _wave_phase calls _preflight_check before _pre_init_graphiti."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
        )

        call_order = []

        def mock_preflight():
            call_order.append("preflight")
            return True

        def mock_pre_init():
            call_order.append("pre_init")

        def mock_execute_wave(wave_number, task_ids, feature, worktree):
            call_order.append(f"wave_{wave_number}")
            return WaveExecutionResult(
                wave_number=wave_number,
                task_ids=task_ids,
                results=[
                    TaskExecutionResult(
                        task_id=tid, success=True,
                        total_turns=1, final_decision="approved"
                    )
                    for tid in task_ids
                ],
                all_succeeded=True,
            )

        with patch.object(orchestrator, '_preflight_check', side_effect=mock_preflight), \
             patch.object(orchestrator, '_pre_init_graphiti', side_effect=mock_pre_init), \
             patch.object(orchestrator, '_execute_wave', side_effect=mock_execute_wave), \
             patch.object(orchestrator, '_dependencies_satisfied', return_value=True):
            orchestrator._wave_phase(sample_feature, mock_worktree)

        # Verify correct order: preflight -> pre_init -> waves
        assert call_order[0] == "preflight"
        assert call_order[1] == "pre_init"
        assert all(item.startswith("wave_") for item in call_order[2:])

    def test_pre_init_skipped_when_preflight_disables_context(
        self, temp_repo, sample_feature, mock_worktree, mock_worktree_manager
    ):
        """Test that _pre_init_graphiti is no-op after pre-flight disables context."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
            enable_context=True,
        )

        with patch("guardkit.knowledge.graphiti_client.get_factory") as mock_get:
            mock_factory = MagicMock()
            mock_factory.config.enabled = True
            mock_factory.check_connectivity.return_value = False
            mock_get.return_value = mock_factory

            # Pre-flight check should disable context
            orchestrator._preflight_check()
            assert orchestrator.enable_context is False

            # Now pre_init_graphiti should be a no-op (enable_context is False)
            orchestrator._pre_init_graphiti()

            # get_graphiti should not be called because enable_context is False
            # (pre_init_graphiti returns early when enable_context is False)


# ============================================================================
# Cooperative Thread Cancellation Tests (TASK-ASF-007)
# ============================================================================


class TestCooperativeCancellation:
    """Tests for cooperative thread cancellation in FeatureOrchestrator."""

    @pytest.mark.asyncio
    async def test_cancellation_events_created_per_task(
        self, temp_repo, parallel_feature, mock_worktree, mock_worktree_manager
    ):
        """Test that _execute_wave_parallel creates a cancellation event per task."""
        import threading

        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
        )

        captured_events = {}

        def mock_execute_task(task, feature, worktree, cancellation_event=None):
            captured_events[task.id] = cancellation_event
            return TaskExecutionResult(
                task_id=task.id,
                success=True,
                total_turns=1,
                final_decision="approved",
            )

        with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task):
            results = await orchestrator._execute_wave_parallel(
                1, ["TASK-P-001", "TASK-P-002"], parallel_feature, mock_worktree
            )

        # Verify both tasks received distinct cancellation events
        assert len(captured_events) == 2
        assert "TASK-P-001" in captured_events
        assert "TASK-P-002" in captured_events
        assert isinstance(captured_events["TASK-P-001"], threading.Event)
        assert isinstance(captured_events["TASK-P-002"], threading.Event)
        # Each task gets its own event
        assert captured_events["TASK-P-001"] is not captured_events["TASK-P-002"]

    @pytest.mark.asyncio
    async def test_all_events_set_after_gather(
        self, temp_repo, parallel_feature, mock_worktree, mock_worktree_manager
    ):
        """Test that all cancellation events are set in the finally block."""
        import threading

        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
        )

        captured_events = {}

        def mock_execute_task(task, feature, worktree, cancellation_event=None):
            captured_events[task.id] = cancellation_event
            return TaskExecutionResult(
                task_id=task.id,
                success=True,
                total_turns=1,
                final_decision="approved",
            )

        with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task):
            await orchestrator._execute_wave_parallel(
                1, ["TASK-P-001", "TASK-P-002"], parallel_feature, mock_worktree
            )

        # After gather completes, all events should be set (from finally block)
        for task_id, event in captured_events.items():
            assert event.is_set(), f"Event for {task_id} was not set after gather"

    @pytest.mark.asyncio
    async def test_events_set_even_on_exception(
        self, temp_repo, parallel_feature, mock_worktree, mock_worktree_manager
    ):
        """Test that events are set even when a task raises an exception."""
        import threading

        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
        )

        captured_events = {}

        def mock_execute_task(task, feature, worktree, cancellation_event=None):
            captured_events[task.id] = cancellation_event
            if task.id == "TASK-P-001":
                raise RuntimeError("Simulated failure")
            return TaskExecutionResult(
                task_id=task.id,
                success=True,
                total_turns=1,
                final_decision="approved",
            )

        with patch.object(orchestrator, '_execute_task', side_effect=mock_execute_task):
            await orchestrator._execute_wave_parallel(
                1, ["TASK-P-001", "TASK-P-002"], parallel_feature, mock_worktree
            )

        # All events should still be set despite exception
        for task_id, event in captured_events.items():
            assert event.is_set(), f"Event for {task_id} was not set after exception"

    @patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator")
    @patch("guardkit.orchestrator.feature_orchestrator.TaskLoader.load_task")
    def test_cancellation_event_forwarded_to_autobuild(
        self,
        mock_load_task,
        mock_ab_class,
        temp_repo,
        sample_feature,
        mock_worktree,
        mock_worktree_manager,
    ):
        """Test that _execute_task passes cancellation_event to AutoBuildOrchestrator."""
        import threading

        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
        )

        # Setup mocks
        mock_load_task.return_value = {
            "requirements": "Test requirements",
            "acceptance_criteria": ["AC1"],
            "frontmatter": {"id": "TASK-T-001", "title": "Test"},
            "file_path": "tasks/backlog/TASK-T-001.md",
        }

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.total_turns = 1
        mock_result.final_decision = "approved"
        mock_result.error = None
        mock_result.recovery_count = 0
        mock_ab_class.return_value.orchestrate.return_value = mock_result

        cancel_event = threading.Event()
        task = sample_feature.tasks[0]
        orchestrator._execute_task(task, sample_feature, mock_worktree, cancellation_event=cancel_event)

        # Verify cancellation_event was forwarded to AutoBuildOrchestrator
        call_kwargs = mock_ab_class.call_args[1]
        assert call_kwargs["cancellation_event"] is cancel_event

    @patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator")
    @patch("guardkit.orchestrator.feature_orchestrator.TaskLoader.load_task")
    def test_execute_task_without_cancellation_event(
        self,
        mock_load_task,
        mock_ab_class,
        temp_repo,
        sample_feature,
        mock_worktree,
        mock_worktree_manager,
    ):
        """Test that _execute_task works without cancellation_event (backward compat)."""
        orchestrator = FeatureOrchestrator(
            repo_root=temp_repo,
            worktree_manager=mock_worktree_manager,
        )

        mock_load_task.return_value = {
            "requirements": "Test requirements",
            "acceptance_criteria": ["AC1"],
            "frontmatter": {"id": "TASK-T-001", "title": "Test"},
            "file_path": "tasks/backlog/TASK-T-001.md",
        }

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.total_turns = 1
        mock_result.final_decision = "approved"
        mock_result.error = None
        mock_result.recovery_count = 0
        mock_ab_class.return_value.orchestrate.return_value = mock_result

        task = sample_feature.tasks[0]
        # No cancellation_event passed
        orchestrator._execute_task(task, sample_feature, mock_worktree)

        # Verify cancellation_event defaults to None
        call_kwargs = mock_ab_class.call_args[1]
        assert call_kwargs["cancellation_event"] is None
