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
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import yaml

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
def mock_worktree() -> Worktree:
    """Provide a mock Worktree for testing."""
    return Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=Path("/fake/.guardkit/worktrees/FEAT-TEST"),
        base_branch="main",
    )


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Provide a mock WorktreeManager."""
    manager = MagicMock()
    manager.create.return_value = mock_worktree
    manager.worktrees_dir = Path("/fake/.guardkit/worktrees")
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


@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_invokes_orchestrator(mock_orchestrator_class):
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


@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_with_specific_task(mock_orchestrator_class):
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


@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_handles_not_found_error(mock_orchestrator_class):
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


@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_handles_validation_error(mock_orchestrator_class):
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


@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_handles_orchestration_error(mock_orchestrator_class):
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


@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_failure_exit_code(mock_orchestrator_class):
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


def test_cli_feature_command_rejects_resume_and_fresh_together():
    """Test CLI rejects --resume and --fresh used together."""
    from click.testing import CliRunner
    from guardkit.cli.autobuild import feature

    runner = CliRunner()
    result = runner.invoke(feature, ["FEAT-TEST", "--resume", "--fresh"])

    assert result.exit_code == 3
    assert "Cannot use both --resume and --fresh" in result.output


@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_with_fresh_flag(mock_orchestrator_class):
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


@patch("guardkit.cli.autobuild.FeatureOrchestrator")
def test_cli_feature_command_with_resume_flag(mock_orchestrator_class):
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
