"""Integration: a failing smoke gate stops the feature build (TASK-SMK-F703A).

Exercises the ``_wave_phase`` hook end-to-end with ``_execute_wave`` stubbed
so the test is fast and deterministic. A feature with a failing smoke command
after wave 1 must not start wave 2, must preserve the worktree, and must
surface the smoke failure in the final summary.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.smoke_gates import SmokeGateResult
from guardkit.worktrees import Worktree


def _make_orchestrator(tmp_path: Path) -> FeatureOrchestrator:
    return FeatureOrchestrator(
        repo_root=tmp_path,
        max_turns=1,
        worktree_manager=MagicMock(),
        quiet=True,
    )


def _make_worktree(path: Path) -> Worktree:
    return Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=path,
        base_branch="main",
    )


def _make_feature(
    task_ids_per_wave: List[List[str]],
    smoke: SmokeGates,
):
    """Minimal feature MagicMock with an explicit ``smoke_gates`` object."""
    feature = MagicMock()
    feature.id = "FEAT-TEST"
    feature.name = "Test Feature"
    feature.status = "in_progress"
    feature.smoke_gates = smoke  # explicit: MagicMock would else match anything

    tasks = []
    for wave_task_ids in task_ids_per_wave:
        for tid in wave_task_ids:
            task = MagicMock()
            task.id = tid
            task.dependencies = []
            task.status = "pending"
            tasks.append(task)
    feature.tasks = tasks
    feature.orchestration.parallel_groups = task_ids_per_wave
    feature.execution.current_wave = 0
    feature.execution.completed_waves = []

    task_map = {t.id: t for t in tasks}
    return feature, task_map


def _succeeding_wave(wave_number: int, task_ids: List[str]) -> WaveExecutionResult:
    return WaveExecutionResult(
        wave_number=wave_number,
        task_ids=task_ids,
        results=[
            TaskExecutionResult(
                task_id=tid, success=True, total_turns=1, final_decision="approved"
            )
            for tid in task_ids
        ],
        all_succeeded=True,
    )


def _smoke(passed: bool, *, gate_not_wired: bool = False) -> SmokeGateResult:
    return SmokeGateResult(
        passed=passed,
        exit_code=0 if passed else (5 if gate_not_wired else 1),
        stdout="",
        stderr="" if passed else "ModuleNotFoundError: No module named 'installer'",
        timed_out=False,
        command="python3 mod.py",
        timeout=5,
        after_wave=1,
        gate_not_wired=gate_not_wired,
    )


def _common_patches(orchestrator):
    """The side-effecting deps every wave-phase test must stub."""
    return (
        patch.object(orchestrator, "_preflight_check"),
        patch.object(orchestrator, "_pre_init_graphiti"),
        patch.object(orchestrator, "_bootstrap_environment"),
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
            side_effect=lambda f, tid: f,  # any non-None task is fine here
        ),
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature",
        ),
    )


# ============================================================================
# TASK-AB-COACHRUNPARITY01 (arm a): bounded smoke-feedback-retry
# ============================================================================


def test_smoke_failure_retries_then_passes(tmp_path: Path) -> None:
    """Smoke fails once, then passes after a feedback re-run; wave 2 starts.

    The wave is re-entered with the smoke stderr fed back to the Player as
    turn-1 seed_feedback. After the retry passes the gate, the feature
    continues to wave 2.
    """
    orchestrator = _make_orchestrator(tmp_path)
    orchestrator._smoke_gate_max_retries = 1
    worktree = _make_worktree(tmp_path)
    smoke = SmokeGates(after_wave=1, command="python3 mod.py", expected_exit=0, timeout=5)
    feature, task_map = _make_feature([["TASK-001"], ["TASK-002"]], smoke=smoke)

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        mock_mark = stack.enter_context(
            patch.object(orchestrator, "_mark_wave_completed")
        )
        mock_execute_wave = stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[
                _succeeding_wave(1, ["TASK-001"]),        # attempt 0
                _succeeding_wave(1, ["TASK-001"]),        # retry attempt 1
                _succeeding_wave(2, ["TASK-002"]),        # wave 2
            ],
        ))
        mock_run_smoke = stack.enter_context(patch(
            "guardkit.orchestrator.feature_orchestrator.run_smoke_gate",
            side_effect=[_smoke(passed=False), _smoke(passed=True)],
        ))
        results = orchestrator._wave_phase(feature, worktree)

    # wave1, wave1-retry, wave2 -> 3 _execute_wave calls
    assert mock_execute_wave.call_count == 3
    # smoke fired after wave1 (fail) and after the retry (pass) = 2; wave 2
    # does not fire (after_wave=1).
    assert mock_run_smoke.call_count == 2
    # The retry _execute_wave call carried the smoke feedback as seed_feedback.
    retry_call = mock_execute_wave.call_args_list[1]
    assert retry_call.kwargs.get("seed_feedback")
    assert "RUNTIME-PARITY" in retry_call.kwargs["seed_feedback"]
    assert retry_call.kwargs.get("attempt") == 1
    # Wave 2 ran (replace-not-append: exactly 2 wave results).
    assert len(results) == 2
    assert [r.wave_number for r in results] == [1, 2]
    # Wave 1 marked completed only after smoke passed; wave 2 too.
    assert mock_mark.call_count == 2


def test_smoke_retries_exhausted_terminates(tmp_path: Path) -> None:
    """Smoke fails on the first run and the retry; the feature terminates."""
    orchestrator = _make_orchestrator(tmp_path)
    orchestrator._smoke_gate_max_retries = 1
    worktree = _make_worktree(tmp_path)
    smoke = SmokeGates(after_wave=1, command="python3 mod.py", expected_exit=0, timeout=5)
    feature, _ = _make_feature([["TASK-001"], ["TASK-002"]], smoke=smoke)

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        mock_mark = stack.enter_context(
            patch.object(orchestrator, "_mark_wave_completed")
        )
        mock_execute_wave = stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[
                _succeeding_wave(1, ["TASK-001"]),  # attempt 0
                _succeeding_wave(1, ["TASK-001"]),  # retry attempt 1
            ],
        ))
        mock_run_smoke = stack.enter_context(patch(
            "guardkit.orchestrator.feature_orchestrator.run_smoke_gate",
            side_effect=[_smoke(passed=False), _smoke(passed=False)],
        ))
        results = orchestrator._wave_phase(feature, worktree)

    assert mock_execute_wave.call_count == 2   # wave1 + one retry, then stop
    assert mock_run_smoke.call_count == 2
    assert len(results) == 1                   # wave 2 never started
    assert results[0].wave_number == 1
    # Smoke-blocked wave is never marked completed (C1).
    assert mock_mark.call_count == 0


def test_smoke_gate_not_wired_does_not_retry(tmp_path: Path) -> None:
    """An exit-5 gate_not_wired failure terminates without a retry."""
    orchestrator = _make_orchestrator(tmp_path)
    orchestrator._smoke_gate_max_retries = 3  # retries available, but unused
    worktree = _make_worktree(tmp_path)
    smoke = SmokeGates(
        after_wave=1, command="pytest -m x", expected_exit=0, timeout=5,
        exit5_is_hard_fail=True,
    )
    feature, _ = _make_feature([["TASK-001"], ["TASK-002"]], smoke=smoke)

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        stack.enter_context(patch.object(orchestrator, "_mark_wave_completed"))
        mock_execute_wave = stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[_succeeding_wave(1, ["TASK-001"])],
        ))
        mock_run_smoke = stack.enter_context(patch(
            "guardkit.orchestrator.feature_orchestrator.run_smoke_gate",
            side_effect=[_smoke(passed=False, gate_not_wired=True)],
        ))
        results = orchestrator._wave_phase(feature, worktree)

    assert mock_execute_wave.call_count == 1   # no retry on gate_not_wired
    assert mock_run_smoke.call_count == 1
    assert len(results) == 1


def test_smoke_pass_marks_wave_completed(tmp_path: Path) -> None:
    """C1: a wave whose tasks pass AND whose smoke passes is marked completed."""
    orchestrator = _make_orchestrator(tmp_path)
    worktree = _make_worktree(tmp_path)
    smoke = SmokeGates(after_wave=1, command="python3 mod.py", expected_exit=0, timeout=5)
    feature, _ = _make_feature([["TASK-001"]], smoke=smoke)

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        mock_mark = stack.enter_context(
            patch.object(orchestrator, "_mark_wave_completed")
        )
        stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[_succeeding_wave(1, ["TASK-001"])],
        ))
        stack.enter_context(patch(
            "guardkit.orchestrator.feature_orchestrator.run_smoke_gate",
            side_effect=[_smoke(passed=True)],
        ))
        orchestrator._wave_phase(feature, worktree)

    mock_mark.assert_called_once()
    assert mock_mark.call_args.args[1] == 1  # wave_number


def test_smoke_fail_does_not_mark_wave_completed(tmp_path: Path) -> None:
    """C1: a wave whose tasks pass but whose smoke fails is NOT marked completed.

    This is the state-corruption hazard the Phase 2.5 review caught: marking a
    wave completed before its smoke gate has passed would let a resume skip an
    unverified wave.
    """
    orchestrator = _make_orchestrator(tmp_path)
    orchestrator._smoke_gate_max_retries = 0  # terminate immediately on fail
    worktree = _make_worktree(tmp_path)
    smoke = SmokeGates(after_wave=1, command="python3 mod.py", expected_exit=0, timeout=5)
    feature, _ = _make_feature([["TASK-001"]], smoke=smoke)

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        mock_mark = stack.enter_context(
            patch.object(orchestrator, "_mark_wave_completed")
        )
        stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[_succeeding_wave(1, ["TASK-001"])],
        ))
        stack.enter_context(patch(
            "guardkit.orchestrator.feature_orchestrator.run_smoke_gate",
            side_effect=[_smoke(passed=False)],
        ))
        orchestrator._wave_phase(feature, worktree)

    mock_mark.assert_not_called()


def test_failing_smoke_stops_feature_build(tmp_path: Path) -> None:
    """A failing smoke command after wave 1 must block wave 2 and preserve worktree.

    TASK-AB-COACHRUNPARITY01 (N1): pinned to the no-retry mode
    (``_smoke_gate_max_retries = 0``), which is the legacy immediate-terminate
    contract this test was written for. With retries disabled a smoke failure
    terminates after a single wave execution, exactly as before the
    bounded-feedback-retry feature landed. The retry path is exercised by the
    dedicated retry tests below.
    """
    orchestrator = _make_orchestrator(tmp_path)
    orchestrator._smoke_gate_max_retries = 0  # no-retry mode (legacy behaviour)
    worktree = _make_worktree(tmp_path)
    smoke = SmokeGates(after_wave=1, command="exit 1", expected_exit=0, timeout=5)
    feature, task_map = _make_feature(
        [["TASK-001", "TASK-002"], ["TASK-003"]],
        smoke=smoke,
    )

    # Stub all side-effecting dependencies: bootstrap, preflight, wave exec,
    # feature-file writes, and the smoke subprocess itself. Only the wave-gate
    # control flow is under test.
    failing_smoke = SmokeGateResult(
        passed=False,
        exit_code=1,
        stdout="",
        stderr="boom",
        timed_out=False,
        command="exit 1",
        timeout=5,
        after_wave=1,
    )

    with (
        patch.object(orchestrator, "_preflight_check"),
        patch.object(orchestrator, "_pre_init_graphiti"),
        patch.object(orchestrator, "_bootstrap_environment"),
        patch.object(orchestrator, "_mark_wave_completed"),
        patch.object(
            orchestrator,
            "_execute_wave",
            side_effect=[
                _succeeding_wave(1, ["TASK-001", "TASK-002"]),
                _succeeding_wave(2, ["TASK-003"]),
            ],
        ) as mock_execute_wave,
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
            side_effect=lambda f, tid: task_map.get(tid),
        ),
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature",
        ),
        patch(
            "guardkit.orchestrator.feature_orchestrator.run_smoke_gate",
            return_value=failing_smoke,
        ) as mock_run_smoke,
    ):
        results = orchestrator._wave_phase(feature, worktree)

    # Wave 1 ran, wave 2 did NOT.
    assert mock_execute_wave.call_count == 1, (
        "Wave 2 must not start after a smoke-gate failure"
    )
    assert len(results) == 1
    assert results[0].wave_number == 1

    # Smoke gate fired exactly once (after wave 1), not per task.
    assert mock_run_smoke.call_count == 1
    (called_config, *_), called_kwargs = mock_run_smoke.call_args
    assert called_config is smoke
    assert called_kwargs["wave_number"] == 1
    assert Path(str(called_kwargs["cwd"])) == Path(worktree.path)

    # Result attached to the wave result for the final summary (AC).
    assert results[0].smoke_gate_result is failing_smoke
    assert results[0].smoke_gate_result.passed is False


def test_failing_smoke_marks_feature_failed(tmp_path: Path) -> None:
    """A smoke failure produces feature status=failed in the final result.

    Without this, a smoke-gate-only failure (all tasks Coach-approved)
    would fall through to ``status=paused`` in the default branch, which
    hides the regression the smoke gate was supposed to catch.
    """
    from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrationResult

    orchestrator = _make_orchestrator(tmp_path)
    worktree = _make_worktree(tmp_path)
    smoke = SmokeGates(after_wave=1, command="exit 1", expected_exit=0, timeout=5)
    feature, _ = _make_feature(
        [["TASK-001"], ["TASK-002"]],
        smoke=smoke,
    )
    # Make feature.tasks a real list of length 2 so len() works in _finalize_phase
    feature.tasks = [feature.tasks[0], feature.tasks[1]]

    failed_wave = WaveExecutionResult(
        wave_number=1,
        task_ids=["TASK-001"],
        results=[
            TaskExecutionResult(
                task_id="TASK-001",
                success=True,
                total_turns=1,
                final_decision="approved",
            )
        ],
        all_succeeded=True,
        smoke_gate_result=SmokeGateResult(
            passed=False,
            exit_code=1,
            stdout="",
            stderr="",
            timed_out=False,
            command="exit 1",
            timeout=5,
            after_wave=1,
        ),
    )

    with (
        patch.object(orchestrator, "_display_summary"),
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature",
        ),
    ):
        result: FeatureOrchestrationResult = orchestrator._finalize_phase(
            feature, [failed_wave], worktree
        )

    assert result.status == "failed"
    assert result.success is False
    assert result.error is not None
    assert "smoke" in result.error.lower()
