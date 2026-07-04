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


def _feature_with_smoke(command="python3 mod.py") -> MagicMock:
    feature = MagicMock()
    feature.smoke_gates = SmokeGates(
        after_wave=1,
        command=command,
        expected_exit=0,
        timeout=30,
    )
    return feature


def _smoke_result(**overrides) -> SmokeGateResult:
    defaults = dict(
        passed=False,
        exit_code=1,
        stdout="",
        stderr="Traceback...\nModuleNotFoundError: No module named 'installer'",
        timed_out=False,
        command="python3 mod.py",
        timeout=30,
        after_wave=1,
    )
    defaults.update(overrides)
    return SmokeGateResult(**defaults)


def test_build_smoke_feedback_contains_command_and_stderr(tmp_path):
    """Non-test-runner smoke command keeps the runs-standalone framing."""
    orch = _orchestrator(tmp_path)
    feature = _feature_with_smoke()
    smoke_result = _smoke_result()

    feedback = orch._build_smoke_feedback(smoke_result, feature)

    assert "RUNTIME-PARITY FAILURE" in feedback
    assert "python3 mod.py" in feedback
    assert "ModuleNotFoundError" in feedback
    assert "exit=1" in feedback
    # Frames the "passes tests but does not run" defect explicitly.
    assert "does not run" in feedback.lower()


def test_build_smoke_feedback_handles_timeout(tmp_path):
    orch = _orchestrator(tmp_path)
    feature = _feature_with_smoke()
    smoke_result = _smoke_result(
        exit_code=-1, stderr="", timed_out=True,
    )

    feedback = orch._build_smoke_feedback(smoke_result, feature)
    assert "timed out after 30s" in feedback
    # Empty stderr renders a placeholder, not a crash.
    assert "(empty)" in feedback


# ============================================================================
# 3. Conditional framing + stale-test attribution (TASK-AB-STALEATTRIB01)
# ============================================================================


_FAILED_LINE = "FAILED tests/unit/test_boundary.py::test_transient_state - AssertionError"


def _write_authored_record(worktree_root: Path, task_id: str, files) -> None:
    task_dir = worktree_root / ".guardkit" / "autobuild" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    import json

    (task_dir / "task_work_results.json").write_text(
        json.dumps({"files_authored": list(files)})
    )


def test_build_smoke_feedback_test_runner_frames_smoke_suite_failure(tmp_path):
    """A pytest smoke command gets the smoke-suite framing + failing tests named."""
    orch = _orchestrator(tmp_path)
    feature = _feature_with_smoke(command="pytest tests/unit -q")
    smoke_result = _smoke_result(
        command="pytest tests/unit -q",
        stdout=f"short test summary info\n{_FAILED_LINE}\n1 failed",
        stderr="",
    )

    feedback = orch._build_smoke_feedback(smoke_result, feature)

    assert "SMOKE-SUITE TEST FAILURE" in feedback
    assert "A test in the feature smoke suite FAILED under this task's changes" in feedback
    # Names the failing test node ID (retro item a — feedback never named it).
    assert "FAILED tests/unit/test_boundary.py::test_transient_state" in feedback
    # The runs-standalone import framing is NOT used for test-runner commands.
    assert "does not run" not in feedback.lower()
    assert "sys.path" not in feedback


def test_build_smoke_feedback_names_authoring_task_and_grants_permission(tmp_path):
    """Failing file authored by an earlier (non-wave) task -> attribution note."""
    orch = _orchestrator(tmp_path)
    feature = _feature_with_smoke(command="pytest tests/unit -q")
    _write_authored_record(
        tmp_path, "TASK-SMP-03", ["tests/unit/test_boundary.py"]
    )
    smoke_result = _smoke_result(
        command="pytest tests/unit -q",
        stdout=f"{_FAILED_LINE}\n",
        stderr="",
    )

    feedback = orch._build_smoke_feedback(
        smoke_result,
        feature,
        worktree_root=tmp_path,
        wave_task_ids=["TASK-SMP-04"],
    )

    assert "TASK-SMP-03" in feedback
    assert (
        "you may amend or delete that specific stale assertion in "
        "tests/unit/test_boundary.py only if it pins transient "
        "point-in-time scaffold state" in feedback.lower()
    )
    assert "change nothing else in that file" in feedback.lower()
    # The permission never licenses deleting a genuine regression guard.
    assert (
        "fix your implementation instead — do not delete it"
        in feedback.lower()
    )
    # The red framing stays — attribution is content, never suppression.
    assert "SMOKE-SUITE TEST FAILURE" in feedback


def test_build_smoke_feedback_attribution_fails_open(tmp_path):
    """Unmatched / ambiguous / wave-authored files leave the framing unchanged."""
    orch = _orchestrator(tmp_path)
    feature = _feature_with_smoke(command="pytest tests/unit -q")
    smoke_result = _smoke_result(
        command="pytest tests/unit -q",
        stdout=f"{_FAILED_LINE}\n",
        stderr="",
    )

    # (a) No records at all.
    fb = orch._build_smoke_feedback(
        smoke_result, feature, worktree_root=tmp_path,
        wave_task_ids=["TASK-SMP-04"],
    )
    assert "STALE-TEST ATTRIBUTION" not in fb

    # (b) Ambiguous: two other tasks authored the file.
    _write_authored_record(tmp_path, "TASK-SMP-02", ["tests/unit/test_boundary.py"])
    _write_authored_record(tmp_path, "TASK-SMP-03", ["tests/unit/test_boundary.py"])
    fb = orch._build_smoke_feedback(
        smoke_result, feature, worktree_root=tmp_path,
        wave_task_ids=["TASK-SMP-04"],
    )
    assert "STALE-TEST ATTRIBUTION" not in fb

    # (c) Authored by a current-wave task: its own framing stands.
    import shutil

    shutil.rmtree(tmp_path / ".guardkit")
    _write_authored_record(tmp_path, "TASK-SMP-04", ["tests/unit/test_boundary.py"])
    fb = orch._build_smoke_feedback(
        smoke_result, feature, worktree_root=tmp_path,
        wave_task_ids=["TASK-SMP-04"],
    )
    assert "STALE-TEST ATTRIBUTION" not in fb
    # The red signal itself is untouched in every fail-open case.
    assert "SMOKE-SUITE TEST FAILURE" in fb
