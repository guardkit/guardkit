"""Integration: the finished build actually runs the repository's start-up checks.

Plain words: after the last wave of a build, GuardKit should try to load and
assemble the thing it just built, using the list the repository declares in
``.guardkit/seam-checks.yaml``. These tests prove three things:

1. the call really happens, once, after the last wave (not per wave);
2. a declared seam that is genuinely broken is reported in readable words;
3. by default that report changes nothing — the build is not failed — and it
   only fails the build when the operator sets the documented flag.

``_execute_wave`` is stubbed so the tests are fast and involve no AI agent.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator import boot_smoke_gate
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.worktrees import Worktree


DECLARATION = """
version: 1
composition_roots:
  - path: app/main.py
boot_smoke:
  - id: composition-root-constructs
    kind: construct
    target: app.main:create_service
    expect_type: app.service:VoiceService
"""


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _declare_broken_seam(root: Path) -> None:
    """Declare a start-up check, and break the thing it checks.

    ``create_service`` builds ``VoiceService`` without the ``audio_client``
    argument that class requires — the composition blows up the moment anything
    actually calls it, while every unit test that replaces ``VoiceService``
    with a stand-in stays green.
    """
    _write(root, ".guardkit/seam-checks.yaml", DECLARATION)
    _write(root, "app/__init__.py", "")
    _write(
        root,
        "app/service.py",
        "class VoiceService:\n"
        "    def __init__(self, audio_client, cache=None):\n"
        "        self.audio_client = audio_client\n",
    )
    _write(
        root,
        "app/main.py",
        "from app.service import VoiceService\n"
        "def create_service():\n"
        "    return VoiceService(cache=None)\n",
    )


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


def _make_feature(task_ids_per_wave: List[List[str]]):
    feature = MagicMock()
    feature.id = "FEAT-TEST"
    feature.name = "Test Feature"
    feature.status = "in_progress"
    feature.smoke_gates = None  # no per-feature smoke gate in these tests
    # ``find_task`` is stubbed to hand this same object back, so the
    # per-task budget lookup reads it; a MagicMock is not a number.
    feature.estimated_minutes = None

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
    return feature


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


def _failing_wave(wave_number: int, task_ids: List[str]) -> WaveExecutionResult:
    return WaveExecutionResult(
        wave_number=wave_number,
        task_ids=task_ids,
        results=[
            TaskExecutionResult(
                task_id=tid, success=False, total_turns=1, final_decision="rejected"
            )
            for tid in task_ids
        ],
        all_succeeded=False,
    )


def _common_patches(orchestrator):
    """The side-effecting dependencies every wave-phase test must stub."""
    return (
        patch.object(orchestrator, "_preflight_check"),
        patch.object(orchestrator, "_bootstrap_environment"),
        patch.object(orchestrator, "_run_post_wave_wiring_gate",
                     side_effect=lambda w, t, f, wt, wr: MagicMock(
                         final_wave_result=wr, terminate=False)),
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
            side_effect=lambda f, tid: f,
        ),
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature",
        ),
    )


# ---------------------------------------------------------------------------
# 1. The call happens, once, after the last wave
# ---------------------------------------------------------------------------


def test_start_up_checks_run_once_after_the_final_wave(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)
    worktree = _make_worktree(tmp_path)
    feature = _make_feature([["TASK-001"], ["TASK-002"]])

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        stack.enter_context(patch.object(orchestrator, "_mark_wave_completed"))
        stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[
                _succeeding_wave(1, ["TASK-001"]),
                _succeeding_wave(2, ["TASK-002"]),
            ],
        ))
        spy = stack.enter_context(patch.object(
            orchestrator, "_run_final_wave_boot_smoke", return_value=None
        ))
        orchestrator._wave_phase(feature, worktree)

    assert spy.call_count == 1, "start-up checks must run once, after the last wave"


def test_start_up_checks_are_skipped_when_the_build_did_not_finish(
    tmp_path: Path,
) -> None:
    """A build that already failed explains its own red; no extra noise."""
    orchestrator = _make_orchestrator(tmp_path)
    worktree = _make_worktree(tmp_path)
    _declare_broken_seam(tmp_path)
    feature = _make_feature([["TASK-001"]])

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        stack.enter_context(patch.object(orchestrator, "_mark_wave_completed"))
        stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[_failing_wave(1, ["TASK-001"])],
        ))
        spy = stack.enter_context(patch(
            "guardkit.orchestrator.feature_orchestrator.run_final_wave_boot_smoke"
        ))
        orchestrator._wave_phase(feature, worktree)

    assert spy.call_count == 0


# ---------------------------------------------------------------------------
# 2 + 3. A broken declared seam is reported, and is advisory by default
# ---------------------------------------------------------------------------


def _run_wave_phase_over_broken_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blocking: bool
) -> List[WaveExecutionResult]:
    _declare_broken_seam(tmp_path)
    if blocking:
        monkeypatch.setenv(boot_smoke_gate.BLOCKING_ENV_VAR, "1")
    else:
        monkeypatch.delenv(boot_smoke_gate.BLOCKING_ENV_VAR, raising=False)

    orchestrator = _make_orchestrator(tmp_path)
    worktree = _make_worktree(tmp_path)
    feature = _make_feature([["TASK-001"]])

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        stack.enter_context(patch.object(orchestrator, "_mark_wave_completed"))
        stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[_succeeding_wave(1, ["TASK-001"])],
        ))
        return orchestrator._wave_phase(feature, worktree)


def test_broken_declared_seam_is_reported_but_does_not_fail_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    with caplog.at_level("INFO", logger="guardkit.orchestrator.feature_orchestrator"):
        wave_results = _run_wave_phase_over_broken_seam(
            tmp_path, monkeypatch, blocking=False
        )

    log = caplog.text
    assert "composition-root-constructs" in log
    assert "FAILED" in log
    assert boot_smoke_gate.BLOCKING_ENV_VAR in log, (
        "the report must name the flag that makes failures blocking"
    )
    # Advisory: nothing about the build's own result changed.
    assert wave_results[-1].smoke_gate_result is None


def test_broken_declared_seam_fails_the_build_when_the_flag_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The declaration must be committed before the build for blocking to apply.
    import subprocess

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=str(tmp_path), check=True,
                       capture_output=True)

    _declare_broken_seam(tmp_path)
    git("init", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    git("add", "-A")
    git("commit", "-m", "declare start-up checks")

    monkeypatch.setenv(boot_smoke_gate.BLOCKING_ENV_VAR, "1")
    orchestrator = _make_orchestrator(tmp_path)
    worktree = _make_worktree(tmp_path)
    feature = _make_feature([["TASK-001"]])

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        stack.enter_context(patch.object(orchestrator, "_mark_wave_completed"))
        stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[_succeeding_wave(1, ["TASK-001"])],
        ))
        wave_results = orchestrator._wave_phase(feature, worktree)

    gate_result = wave_results[-1].smoke_gate_result
    assert gate_result is not None
    assert gate_result.passed is False
    assert "composition-root-constructs" in gate_result.stderr
