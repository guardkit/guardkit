"""
Integration Tests for Parallel Wave Execution in FeatureOrchestrator

Tests the parallel task execution capabilities of FeatureOrchestrator to ensure
that tasks within the same wave execute in parallel, error isolation works correctly,
and stop_on_failure behavior is properly enforced.

Test Coverage:
    - Parallel execution timing verification
    - Error isolation between parallel tasks
    - Stop-on-failure behavior across waves
    - Heartbeat/progress logging during execution

Architecture:
    - Mocks AutoBuildOrchestrator.orchestrate() at public API level
    - Uses real FeatureOrchestrator instance with mocked dependencies
    - Creates realistic feature YAML structures for testing

Run with:
    pytest tests/integration/test_parallel_wave_execution.py -v
    pytest tests/integration/test_parallel_wave_execution.py -v --cov=guardkit/orchestrator

Coverage Target: >=85%
Test Count: 4 tests
"""

import asyncio
import json
import pytest
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

# Import components under test
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    FeatureOrchestrationResult,
    TaskExecutionResult,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureOrchestration,
    FeatureExecution,
    FeatureLoader,
)
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.worktrees import WorktreeManager, Worktree


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_repo_root(tmp_path):
    """
    Create a temporary repository root with required directories.

    Returns:
        Path: Path to temporary repo root
    """
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    # Create features directory
    features_dir = repo_root / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    # Create tasks directory
    tasks_dir = repo_root / "tasks" / "backlog"
    tasks_dir.mkdir(parents=True)

    # Create worktrees directory
    worktrees_dir = repo_root / ".guardkit" / "worktrees"
    worktrees_dir.mkdir(parents=True)

    return repo_root


@pytest.fixture
def mock_worktree_manager(tmp_repo_root):
    """
    Create a mock WorktreeManager that returns a test worktree.

    Returns:
        MagicMock: Mocked WorktreeManager
    """
    manager = MagicMock(spec=WorktreeManager)
    worktree_path = tmp_repo_root / ".guardkit" / "worktrees" / "FEAT-TEST"
    worktree_path.mkdir(parents=True, exist_ok=True)

    # Create a worktree instance to return
    test_worktree = Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=worktree_path,
        base_branch="main",
    )

    manager.create.return_value = test_worktree
    manager.preserve_on_failure.return_value = None

    return manager


def create_test_feature(
    feature_id: str,
    tasks: List[Dict[str, Any]],
    parallel_groups: List[List[str]],
    tmp_repo_root: Path,
) -> Feature:
    """
    Create a Feature instance for testing.

    Parameters
    ----------
    feature_id : str
        Feature identifier
    tasks : List[Dict[str, Any]]
        Task definitions
    parallel_groups : List[List[str]]
        Wave structure
    tmp_repo_root : Path
        Temporary repository root

    Returns
    -------
    Feature
        Constructed Feature instance
    """
    # Create task markdown files
    task_objs = []
    for task_data in tasks:
        task_file = tmp_repo_root / "tasks" / "backlog" / f"{task_data['id']}.md"
        task_file.write_text(
            f"""---
id: {task_data['id']}
title: {task_data.get('name', task_data['id'])}
status: pending
---

# {task_data.get('name', task_data['id'])}

## Description
Test task

## Requirements
- Test requirement

## Acceptance Criteria
- [ ] Test criterion
""",
            encoding='utf-8',
        )

        task_obj = FeatureTask(
            id=task_data["id"],
            name=task_data.get("name", task_data["id"]),
            file_path=task_file,
            complexity=task_data.get("complexity", 5),
            dependencies=task_data.get("dependencies", []),
            status="pending",
            implementation_mode=task_data.get("implementation_mode", "task-work"),
            estimated_minutes=task_data.get("estimated_minutes", 30),
        )
        task_objs.append(task_obj)

    from datetime import datetime

    feature = Feature(
        id=feature_id,
        name=f"Test Feature {feature_id}",
        description="Test feature for parallel wave execution",
        created=datetime.now().isoformat(),
        status="planned",
        complexity=max(t.get("complexity", 5) for t in tasks),
        estimated_tasks=len(tasks),
        tasks=task_objs,
        orchestration=FeatureOrchestration(
            parallel_groups=parallel_groups,
            estimated_duration_minutes=sum(t["estimated_minutes"] for t in tasks),
            recommended_parallel=max(len(group) for group in parallel_groups),
        ),
        execution=FeatureExecution(
            started_at=None,
            completed_at=None,
            current_wave=0,
            completed_waves=[],
            worktree_path=None,
            tasks_completed=0,
            tasks_failed=0,
            total_turns=0,
            last_updated=None,
        ),
    )

    return feature


def create_mock_orchestrate(
    delay: float = 1.0,
    should_fail: bool = False,
    task_id_override: Optional[str] = None,
):
    """
    Create a mock orchestrate function that simulates work with delay.

    Parameters
    ----------
    delay : float
        Simulated work duration in seconds
    should_fail : bool
        Whether to return a failed result
    task_id_override : Optional[str]
        If provided, only fail when task_id matches

    Returns
    -------
    callable
        Mock orchestrate function
    """

    def mock_orchestrate(
        self,
        task_id,
        requirements,
        acceptance_criteria,
        base_branch="main",
        task_file_path=None,
    ):
        time.sleep(delay)  # Simulate work

        # Check if this specific task should fail
        should_fail_this_task = should_fail
        if task_id_override and task_id != task_id_override:
            should_fail_this_task = False

        if should_fail_this_task:
            return OrchestrationResult(
                task_id=task_id,
                success=False,
                total_turns=1,
                final_decision="error",
                turn_history=[],
                worktree=self._existing_worktree or Worktree(
                    task_id=task_id,
                    branch_name=f"autobuild/{task_id}",
                    path=Path(f".guardkit/worktrees/{task_id}"),
                    base_branch=base_branch,
                ),
                error=f"Task {task_id} failed",
            )

        return OrchestrationResult(
            task_id=task_id,
            success=True,
            total_turns=1,
            final_decision="approved",
            turn_history=[],
            worktree=self._existing_worktree or Worktree(
                task_id=task_id,
                branch_name=f"autobuild/{task_id}",
                path=Path(f".guardkit/worktrees/{task_id}"),
                base_branch=base_branch,
            ),
            error=None,
        )

    return mock_orchestrate


# ============================================================================
# TestParallelWaveExecution - Parallel Execution Tests
# ============================================================================


@pytest.mark.integration
class TestParallelWaveExecution:
    """Test that wave executes tasks in parallel."""

    def test_wave_executes_in_parallel(self, tmp_repo_root, mock_worktree_manager):
        """
        Verify wave tasks execute in parallel, not serially.

        Test Flow:
        1. Create feature with 3 tasks in same wave, each takes 1 second
        2. Mock AutoBuildOrchestrator.orchestrate() with 1-second delay
        3. Execute wave
        4. Verify total execution time is ~1s (parallel) not ~3s (serial)
        """
        # Create feature with 3 tasks in same wave
        feature = create_test_feature(
            feature_id="FEAT-PARALLEL",
            tasks=[
                {"id": "TASK-001", "name": "Task 1", "estimated_minutes": 30},
                {"id": "TASK-002", "name": "Task 2", "estimated_minutes": 30},
                {"id": "TASK-003", "name": "Task 3", "estimated_minutes": 30},
            ],
            parallel_groups=[["TASK-001", "TASK-002", "TASK-003"]],
            tmp_repo_root=tmp_repo_root,
        )

        # Save feature YAML
        features_dir = tmp_repo_root / ".guardkit" / "features"
        feature_file = features_dir / f"{feature.id}.yaml"
        FeatureLoader.save_feature(feature, tmp_repo_root)

        # Create orchestrator with mocked worktree manager
        orchestrator = FeatureOrchestrator(
            repo_root=tmp_repo_root,
            worktree_manager=mock_worktree_manager,
            quiet=True,  # Suppress progress display
        )

        # Mock AutoBuildOrchestrator.orchestrate() with 1-second delay
        with patch.object(
            AutoBuildOrchestrator,
            "orchestrate",
            create_mock_orchestrate(delay=1.0, should_fail=False),
        ):
            # Measure execution time
            start_time = time.time()
            result = orchestrator.orchestrate("FEAT-PARALLEL")
            elapsed_time = time.time() - start_time

        # Verify result
        assert result.success is True
        assert result.status == "completed"
        assert result.tasks_completed == 3
        assert result.tasks_failed == 0

        # Verify parallel execution (should be ~1s, not ~3s)
        # Allow tolerance for thread scheduling overhead
        assert (
            elapsed_time < 2.0
        ), f"Expected ~1s (parallel), got {elapsed_time:.2f}s (serial would be ~3s)"
        assert (
            elapsed_time >= 1.0
        ), f"Expected at least 1s work, got {elapsed_time:.2f}s"

    def test_wave_error_isolation(self, tmp_repo_root, mock_worktree_manager):
        """
        Verify error isolation between parallel tasks in same wave.

        Test Flow:
        1. Create 3 tasks in same wave
        2. Task 2 raises exception after 0.5 seconds
        3. Tasks 1 and 3 should complete successfully
        4. Verify error isolation works
        """
        # Create feature with 3 tasks in same wave
        feature = create_test_feature(
            feature_id="FEAT-ERROR-ISOLATION",
            tasks=[
                {"id": "TASK-001", "name": "Task 1", "estimated_minutes": 30},
                {"id": "TASK-002", "name": "Task 2", "estimated_minutes": 30},
                {"id": "TASK-003", "name": "Task 3", "estimated_minutes": 30},
            ],
            parallel_groups=[["TASK-001", "TASK-002", "TASK-003"]],
            tmp_repo_root=tmp_repo_root,
        )

        # Save feature YAML
        FeatureLoader.save_feature(feature, tmp_repo_root)

        # Create orchestrator
        orchestrator = FeatureOrchestrator(
            repo_root=tmp_repo_root,
            worktree_manager=mock_worktree_manager,
            stop_on_failure=False,  # Continue on failure
            quiet=True,
        )

        # Mock AutoBuildOrchestrator.orchestrate() - TASK-002 fails
        with patch.object(
            AutoBuildOrchestrator,
            "orchestrate",
            create_mock_orchestrate(delay=0.5, should_fail=True, task_id_override="TASK-002"),
        ):
            result = orchestrator.orchestrate("FEAT-ERROR-ISOLATION")

        # Verify result
        assert result.success is False  # At least one task failed
        assert result.tasks_completed == 2  # Tasks 1 and 3 completed
        assert result.tasks_failed == 1  # Task 2 failed

        # Verify wave results
        assert len(result.wave_results) == 1
        wave_result = result.wave_results[0]
        assert wave_result.all_succeeded is False

        # Verify individual task results
        task_results_by_id = {r.task_id: r for r in wave_result.results}
        assert task_results_by_id["TASK-001"].success is True
        assert task_results_by_id["TASK-002"].success is False
        assert task_results_by_id["TASK-003"].success is True

    def test_stop_on_failure_behavior(self, tmp_repo_root, mock_worktree_manager):
        """
        Verify stop_on_failure stops after current wave completes.

        Test Flow:
        1. Create 2 waves: wave 1 with 3 tasks (including failure), wave 2 with 2 tasks
        2. Set stop_on_failure=True
        3. Verify wave 1 completes fully before stopping
        4. Verify wave 2 never starts
        """
        # Create feature with 2 waves
        feature = create_test_feature(
            feature_id="FEAT-STOP-ON-FAILURE",
            tasks=[
                # Wave 1 - one task fails
                {"id": "TASK-001", "name": "Task 1", "estimated_minutes": 30},
                {"id": "TASK-002", "name": "Task 2", "estimated_minutes": 30},
                {"id": "TASK-003", "name": "Task 3", "estimated_minutes": 30},
                # Wave 2 - should not execute
                {"id": "TASK-004", "name": "Task 4", "estimated_minutes": 30},
                {"id": "TASK-005", "name": "Task 5", "estimated_minutes": 30},
            ],
            parallel_groups=[
                ["TASK-001", "TASK-002", "TASK-003"],  # Wave 1
                ["TASK-004", "TASK-005"],  # Wave 2 (should not execute)
            ],
            tmp_repo_root=tmp_repo_root,
        )

        # Save feature YAML
        FeatureLoader.save_feature(feature, tmp_repo_root)

        # Create orchestrator with stop_on_failure=True
        orchestrator = FeatureOrchestrator(
            repo_root=tmp_repo_root,
            worktree_manager=mock_worktree_manager,
            stop_on_failure=True,
            quiet=True,
        )

        # Mock AutoBuildOrchestrator.orchestrate() - TASK-002 fails
        with patch.object(
            AutoBuildOrchestrator,
            "orchestrate",
            create_mock_orchestrate(delay=0.5, should_fail=True, task_id_override="TASK-002"),
        ):
            result = orchestrator.orchestrate("FEAT-STOP-ON-FAILURE")

        # Verify result
        assert result.success is False
        assert result.status == "failed"

        # Verify wave 1 completed fully (all 3 tasks executed)
        assert len(result.wave_results) == 1  # Only wave 1 executed
        wave1_result = result.wave_results[0]
        assert wave1_result.wave_number == 1
        assert len(wave1_result.results) == 3  # All 3 tasks in wave 1 executed

        # Verify task execution status
        assert result.tasks_completed == 2  # Tasks 1 and 3 completed
        assert result.tasks_failed == 1  # Task 2 failed

        # Verify wave 2 tasks were never started
        # (If they were, tasks_completed + tasks_failed would be > 3)
        assert result.tasks_completed + result.tasks_failed == 3

    def test_heartbeat_during_execution(
        self, tmp_repo_root, mock_worktree_manager, caplog
    ):
        """
        Verify heartbeat/progress logs appear during task execution.

        Test Flow:
        1. Create 1 task with longer duration (2 seconds)
        2. Verify progress logs appear during execution
        3. Use caplog fixture for log capture
        """
        import logging

        caplog.set_level(logging.INFO)

        # Create feature with 1 task
        feature = create_test_feature(
            feature_id="FEAT-HEARTBEAT",
            tasks=[
                {"id": "TASK-001", "name": "Long Task", "estimated_minutes": 60},
            ],
            parallel_groups=[["TASK-001"]],
            tmp_repo_root=tmp_repo_root,
        )

        # Save feature YAML
        FeatureLoader.save_feature(feature, tmp_repo_root)

        # Create orchestrator (verbose mode for more logs)
        orchestrator = FeatureOrchestrator(
            repo_root=tmp_repo_root,
            worktree_manager=mock_worktree_manager,
            verbose=True,
            quiet=False,  # Enable progress display
        )

        # Mock AutoBuildOrchestrator.orchestrate() with 2-second delay
        with patch.object(
            AutoBuildOrchestrator,
            "orchestrate",
            create_mock_orchestrate(delay=2.0, should_fail=False),
        ):
            result = orchestrator.orchestrate("FEAT-HEARTBEAT")

        # Verify result
        assert result.success is True
        assert result.tasks_completed == 1

        # Verify progress logs appeared
        log_messages = [record.message for record in caplog.records]

        # Check for phase-related log messages (setup, loop, finalize)
        phase_logs = [
            msg
            for msg in log_messages
            if any(
                keyword in msg.lower()
                for keyword in ["phase", "setup", "executing", "complete"]
            )
        ]
        assert len(phase_logs) > 0, "Expected phase-related log messages during execution"

        # Check for task-specific log messages
        task_logs = [msg for msg in log_messages if "TASK-001" in msg]
        assert len(task_logs) > 0, "Expected task-specific log messages during execution"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
