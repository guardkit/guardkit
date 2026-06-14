"""Unit tests for the smoke-feedback seed + builder (TASK-AB-COACHRUNPARITY01, arm a).

Covers the two arm-a units that do NOT need a full wave run:

1. ``AutoBuildOrchestrator._seed_feedback`` reaches the Player's turn-1
   ``previous_feedback`` (the carrier that turns a terminated smoke failure
   into a Player feedback round).
2. ``FeatureOrchestrator._build_smoke_feedback`` frames the failure as a
   runtime-parity defect and includes the command + stderr tail.

Coverage Target: >=85%
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, TurnRecord
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.smoke_gates import SmokeGateResult


# ============================================================================
# 1. seed_feedback -> turn-1 previous_feedback
# ============================================================================


def _approving_turn_record(turn: int) -> TurnRecord:
    """A TurnRecord whose decision exits _loop_phase as 'approved' on turn 1."""
    player_result = Mock()
    player_result.session_id = None
    player_result.error = None
    return TurnRecord(
        turn=turn,
        player_result=player_result,
        coach_result=None,
        decision="approve",
        feedback=None,
        timestamp="2026-06-14T00:00:00Z",
    )


@pytest.fixture
def _progress_display() -> Mock:
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    return display


def _make_orchestrator(seed_feedback, progress_display) -> AutoBuildOrchestrator:
    tmpdir = tempfile.mkdtemp()
    return AutoBuildOrchestrator(
        repo_root=Path(tmpdir),
        worktree_manager=Mock(),
        agent_invoker=Mock(),
        progress_display=progress_display,
        verbose=False,
        max_turns=3,
        sdk_timeout=900,
        enable_checkpoints=False,  # skip checkpoint-manager setup
        enable_perspective_reset=True,
        seed_feedback=seed_feedback,
    )


def test_seed_feedback_reaches_turn1_previous_feedback(_progress_display, tmp_path):
    """A fresh (non-resume) task with seed_feedback set passes it as turn-1 feedback."""
    orch = _make_orchestrator("SMOKE: ModuleNotFoundError", _progress_display)
    worktree = Mock()
    worktree.path = str(tmp_path)

    captured = {}

    def _fake_execute_turn(*args, **kwargs):
        captured["previous_feedback"] = kwargs.get("previous_feedback")
        return _approving_turn_record(kwargs.get("turn", 1))

    with patch.object(orch, "_execute_turn", side_effect=_fake_execute_turn):
        history, status = orch._loop_phase(
            task_id="TASK-TSJ-001",
            requirements="impl",
            acceptance_criteria=[],
            worktree=worktree,
        )

    assert status == "approved"
    assert captured["previous_feedback"] == "SMOKE: ModuleNotFoundError"


def test_seed_feedback_none_by_default(_progress_display, tmp_path):
    """No seed_feedback -> turn-1 previous_feedback is None (unchanged behaviour)."""
    orch = _make_orchestrator(None, _progress_display)
    worktree = Mock()
    worktree.path = str(tmp_path)

    captured = {}

    def _fake_execute_turn(*args, **kwargs):
        captured["previous_feedback"] = kwargs.get("previous_feedback")
        return _approving_turn_record(kwargs.get("turn", 1))

    with patch.object(orch, "_execute_turn", side_effect=_fake_execute_turn):
        orch._loop_phase(
            task_id="TASK-X",
            requirements="impl",
            acceptance_criteria=[],
            worktree=worktree,
        )

    assert captured["previous_feedback"] is None


# ============================================================================
# 2. _build_smoke_feedback
# ============================================================================


def _orchestrator(tmp_path) -> FeatureOrchestrator:
    return FeatureOrchestrator(
        repo_root=tmp_path,
        max_turns=1,
        worktree_manager=MagicMock(),
        quiet=True,
    )


def _feature_with_smoke() -> MagicMock:
    feature = MagicMock()
    feature.smoke_gates = SmokeGates(
        after_wave=1,
        command="pytest -k x && python3 mod.py",
        expected_exit=0,
        timeout=30,
    )
    return feature


def test_build_smoke_feedback_contains_command_and_stderr(tmp_path):
    orch = _orchestrator(tmp_path)
    feature = _feature_with_smoke()
    smoke_result = SmokeGateResult(
        passed=False,
        exit_code=1,
        stdout="",
        stderr="Traceback...\nModuleNotFoundError: No module named 'installer'",
        timed_out=False,
        command="pytest -k x && python3 mod.py",
        timeout=30,
        after_wave=1,
    )

    feedback = orch._build_smoke_feedback(smoke_result, feature)

    assert "RUNTIME-PARITY FAILURE" in feedback
    assert "pytest -k x && python3 mod.py" in feedback
    assert "ModuleNotFoundError" in feedback
    assert "exit=1" in feedback
    # Frames the "passes tests but does not run" defect explicitly.
    assert "does not run" in feedback.lower()


def test_build_smoke_feedback_handles_timeout(tmp_path):
    orch = _orchestrator(tmp_path)
    feature = _feature_with_smoke()
    smoke_result = SmokeGateResult(
        passed=False,
        exit_code=-1,
        stdout="",
        stderr="",
        timed_out=True,
        command="python3 mod.py",
        timeout=30,
        after_wave=1,
    )

    feedback = orch._build_smoke_feedback(smoke_result, feature)
    assert "timed out after 30s" in feedback
    # Empty stderr renders a placeholder, not a crash.
    assert "(empty)" in feedback
