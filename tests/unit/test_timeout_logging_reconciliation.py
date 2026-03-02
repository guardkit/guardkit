"""
Unit tests for TASK-ABFIX-006: Timeout vs Cancelled logging reconciliation.

Verifies:
- Feature-level timeout reports as "timeout" (not "cancelled") in AutoBuild
- Cancellation (stop_on_failure) reports as "cancelled" consistently
- Timeout events log which layer fired and remaining budget on the other layer
- feature_orchestrator passes timeout_event to AutoBuildOrchestrator
"""

import threading
import time
import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock

import pytest

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree():
    wt = Mock(spec=Worktree)
    wt.task_id = "TASK-AB-001"
    wt.path = Path("/tmp/worktrees/TASK-AB-001")
    wt.branch_name = "autobuild/TASK-AB-001"
    wt.base_branch = "main"
    return wt


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    mgr = Mock()
    mgr.create.return_value = mock_worktree
    mgr.preserve_on_failure.return_value = None
    mgr.worktrees_dir = Path("/tmp/worktrees")
    return mgr


@pytest.fixture
def mock_progress_display():
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    return display


@pytest.fixture
def orchestrator_base(mock_worktree_manager, mock_progress_display, tmp_path):
    """Create a minimal AutoBuildOrchestrator for testing loop_phase internals."""
    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1200,
    )
    return orch


# ============================================================================
# _loop_phase decision: timeout vs cancelled
# ============================================================================


def test_loop_phase_returns_timeout_when_timeout_event_set(
    mock_worktree_manager, mock_progress_display, tmp_path, mock_worktree
):
    """When timeout_event is pre-set, _loop_phase returns 'timeout' at the first check."""
    timeout_event = threading.Event()
    timeout_event.set()  # Pre-set before loop starts

    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1200,
        timeout_event=timeout_event,
        task_timeout=2400,
    )

    turn_history, decision = orch._loop_phase(
        task_id="TASK-AB-001",
        requirements="Implement feature",
        acceptance_criteria=["criterion 1"],
        worktree=mock_worktree,
    )

    assert decision == "timeout", f"Expected 'timeout', got '{decision}'"


def test_loop_phase_returns_cancelled_when_only_cancel_event_set(
    mock_worktree_manager, mock_progress_display, tmp_path, mock_worktree
):
    """When cancellation_event is set (no timeout_event), _loop_phase returns 'cancelled'."""
    cancel_event = threading.Event()
    cancel_event.set()  # Pre-set before loop starts

    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1200,
        cancellation_event=cancel_event,
        # No timeout_event — should be "cancelled", not "timeout"
    )

    turn_history, decision = orch._loop_phase(
        task_id="TASK-AB-001",
        requirements="Implement feature",
        acceptance_criteria=["criterion 1"],
        worktree=mock_worktree,
    )

    assert decision == "cancelled", f"Expected 'cancelled', got '{decision}'"


def test_timeout_and_cancel_both_set_prefers_timeout(
    mock_worktree_manager, mock_progress_display, tmp_path, mock_worktree
):
    """When both events are set, timeout takes priority (feature timeout fires first)."""
    cancel_event = threading.Event()
    timeout_event = threading.Event()
    cancel_event.set()
    timeout_event.set()

    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1200,
        cancellation_event=cancel_event,
        timeout_event=timeout_event,
        task_timeout=2400,
    )

    turn_history, decision = orch._loop_phase(
        task_id="TASK-AB-001",
        requirements="Implement feature",
        acceptance_criteria=["criterion 1"],
        worktree=mock_worktree,
    )

    assert decision == "timeout", f"Expected 'timeout' when both events set, got '{decision}'"


# ============================================================================
# Logging attribution
# ============================================================================


def test_loop_phase_logs_feature_level_timeout_attribution(
    mock_worktree_manager, mock_progress_display, tmp_path, mock_worktree, caplog
):
    """Feature-level timeout logs 'TIMEOUT (feature-level):' with sdk_timeout budget."""
    timeout_event = threading.Event()
    timeout_event.set()

    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1200,
        timeout_event=timeout_event,
        task_timeout=2400,
    )

    with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.autobuild"):
        orch._loop_phase(
            task_id="TASK-AB-001",
            requirements="Implement feature",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

    log_text = " ".join(caplog.messages)
    assert "TIMEOUT (feature-level)" in log_text, (
        f"Expected 'TIMEOUT (feature-level):' in logs. Got: {caplog.messages}"
    )


def test_loop_phase_logs_cancelled_attribution_for_stop_on_failure(
    mock_worktree_manager, mock_progress_display, tmp_path, mock_worktree, caplog
):
    """stop_on_failure cancellation logs 'CANCELLED:' message."""
    cancel_event = threading.Event()
    cancel_event.set()

    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1200,
        cancellation_event=cancel_event,
    )

    with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.autobuild"):
        orch._loop_phase(
            task_id="TASK-AB-001",
            requirements="Implement feature",
            acceptance_criteria=["criterion 1"],
            worktree=mock_worktree,
        )

    log_text = " ".join(caplog.messages)
    assert "CANCELLED" in log_text, (
        f"Expected 'CANCELLED' in logs. Got: {caplog.messages}"
    )
    # Must NOT say it's a timeout
    assert "TIMEOUT (feature-level)" not in log_text


# ============================================================================
# SDK-level timeout logging
# ============================================================================


def test_loop_phase_logs_sdk_timeout_attribution(
    mock_worktree_manager, mock_progress_display, tmp_path, mock_worktree, caplog
):
    """When a turn records an SDK timeout error, logs 'TIMEOUT (SDK-level):' with remaining budget."""
    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1200,
        task_timeout=2400,
    )

    # Build a fake turn record where player_result has an SDK timeout error
    sdk_timeout_error = f"SDK timeout after {orch.sdk_timeout}s: Agent invocation exceeded timeout"
    fake_player_result = AgentInvocationResult(
        task_id="TASK-AB-001",
        turn=1,
        agent_type="player",
        success=False,
        report={},
        duration_seconds=1200.0,
        error=sdk_timeout_error,
    )
    fake_turn_record = TurnRecord(
        turn=1,
        player_result=fake_player_result,
        coach_result=None,
        decision="error",
        feedback=None,
        timestamp="2025-01-01T00:00:00Z",
    )

    with patch.object(orch, "_execute_turn", return_value=fake_turn_record):
        with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.autobuild"):
            orch._loop_phase(
                task_id="TASK-AB-001",
                requirements="Implement feature",
                acceptance_criteria=["criterion 1"],
                worktree=mock_worktree,
            )

    log_text = " ".join(caplog.messages)
    assert "TIMEOUT (SDK-level)" in log_text, (
        f"Expected 'TIMEOUT (SDK-level)' in logs. Got: {caplog.messages}"
    )


# ============================================================================
# _build_summary_details and _build_error_message for "timeout"
# ============================================================================


def test_build_summary_details_includes_timeout_case(
    mock_worktree_manager, mock_progress_display, tmp_path
):
    """_build_summary_details returns non-empty content for 'timeout' decision."""
    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1200,
        task_timeout=2400,
    )

    result = orch._build_summary_details([], "timeout")
    assert result is not None
    assert len(result) > 0
    # Should mention timeout, not 'cancelled'
    assert "timeout" in result.lower() or "TIMEOUT" in result


def test_build_error_message_timeout_is_distinct_from_cancelled(
    mock_worktree_manager, mock_progress_display, tmp_path
):
    """_build_error_message for 'timeout' should be different from 'cancelled'."""
    orch = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        progress_display=mock_progress_display,
        enable_pre_loop=False,
        enable_context=False,
        sdk_timeout=1200,
        task_timeout=2400,
    )

    timeout_msg = orch._build_error_message("timeout", [])
    cancelled_msg = orch._build_error_message("cancelled", [])

    assert timeout_msg != cancelled_msg, "timeout and cancelled should have different error messages"
    assert timeout_msg  # Non-empty
    assert "timeout" in timeout_msg.lower() or "TIMEOUT" in timeout_msg


# ============================================================================
# feature_orchestrator: timeout_event passed to _execute_task
# ============================================================================


@pytest.mark.asyncio
async def test_feature_orchestrator_passes_timeout_event_to_execute_task(tmp_path):
    """feature_orchestrator creates timeout_event per task and passes it to _execute_task."""
    from guardkit.orchestrator.feature_orchestrator import (
        FeatureOrchestrator,
        FeatureOrchestrationResult,
    )
    from guardkit.orchestrator.feature_loader import (
        Feature, FeatureTask, FeatureOrchestration, FeatureExecution,
    )

    mock_worktree_manager = Mock()
    mock_worktree = Mock(spec=Worktree)
    mock_worktree.path = tmp_path / "worktrees" / "FEAT-TEST"

    orchestrator = FeatureOrchestrator(
        repo_root=tmp_path,
        worktree_manager=mock_worktree_manager,
        task_timeout=1,  # 1s to trigger timeout quickly
    )

    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test",
        created="2025-01-01T00:00:00Z",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-T-001",
                name="Test Task",
                file_path=Path("tasks/backlog/TASK-T-001.md"),
                complexity=2,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            )
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-T-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )

    # Track what timeout_event was passed to _execute_task
    captured_timeout_events = []

    def mock_execute_task_slow(task, feat, worktree, cancellation_event=None, timeout_event=None, time_budget_seconds=None, wave_size=1):
        captured_timeout_events.append(timeout_event)
        time.sleep(5)  # Exceed the 1s task_timeout
        return TaskExecutionResult(
            task_id=task.id,
            success=True,
            total_turns=1,
            final_decision="approved",
        )

    with patch.object(orchestrator, "_execute_task", side_effect=mock_execute_task_slow):
        results = await orchestrator._execute_wave_parallel(
            1, ["TASK-T-001"], feature, mock_worktree
        )

    # Verify a timeout_event was passed to _execute_task
    assert len(captured_timeout_events) == 1
    timeout_event_passed = captured_timeout_events[0]
    assert timeout_event_passed is not None, "_execute_task should receive a timeout_event"
    assert isinstance(timeout_event_passed, threading.Event)

    # After timeout, the timeout_event should be set
    assert timeout_event_passed.is_set(), (
        "timeout_event should be set after asyncio.TimeoutError fires"
    )

    # The TaskExecutionResult should show "timeout"
    assert len(results) == 1
    assert results[0].final_decision == "timeout"


@pytest.mark.asyncio
async def test_feature_orchestrator_timeout_logs_feature_level_attribution(
    tmp_path, caplog
):
    """feature_orchestrator logs 'TIMEOUT (feature-level):' when asyncio.TimeoutError fires."""
    from guardkit.orchestrator.feature_orchestrator import (
        FeatureOrchestrator,
    )
    from guardkit.orchestrator.feature_loader import (
        Feature, FeatureTask, FeatureOrchestration, FeatureExecution,
    )

    mock_worktree_manager = Mock()
    mock_worktree = Mock(spec=Worktree)
    mock_worktree.path = tmp_path / "worktrees" / "FEAT-TEST"

    orchestrator = FeatureOrchestrator(
        repo_root=tmp_path,
        worktree_manager=mock_worktree_manager,
        task_timeout=1,
        sdk_timeout=1200,
    )

    feature = Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test",
        created="2025-01-01T00:00:00Z",
        status="planned",
        complexity=3,
        estimated_tasks=1,
        tasks=[
            FeatureTask(
                id="TASK-T-001",
                name="Test Task",
                file_path=Path("tasks/backlog/TASK-T-001.md"),
                complexity=2,
                dependencies=[],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=30,
            )
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-T-001"]],
            estimated_duration_minutes=30,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )

    def mock_execute_task_slow(task, feat, worktree, cancellation_event=None, timeout_event=None, time_budget_seconds=None, wave_size=1):
        time.sleep(5)
        return TaskExecutionResult(
            task_id=task.id, success=True, total_turns=1, final_decision="approved",
        )

    with patch.object(orchestrator, "_execute_task", side_effect=mock_execute_task_slow):
        with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.feature_orchestrator"):
            await orchestrator._execute_wave_parallel(
                1, ["TASK-T-001"], feature, mock_worktree
            )

    log_text = " ".join(caplog.messages)
    assert "TIMEOUT (feature-level)" in log_text, (
        f"Expected 'TIMEOUT (feature-level)' in feature_orchestrator logs. Got: {caplog.messages}"
    )
