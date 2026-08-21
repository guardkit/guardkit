"""Proof that a finished build actually runs the repository's start-up checks.

Plain words: after the last wave of a build, GuardKit should try to load and
assemble the thing it just built, using the list the repository declares in
``.guardkit/seam-checks.yaml``. These tests prove:

1. the call really happens, once, after the last wave (not per wave);
2. a declared check that is genuinely broken is reported in readable words;
3. by default that report changes nothing — the build is not failed — and it
   only fails the build when the operator sets the documented flag;
4. a declaration the build itself wrote is never run at all, so a build cannot
   hand GuardKit a command line to execute on its behalf.

``_execute_wave`` is stubbed so the tests are fast and involve no AI agent.

WHERE THIS FILE LIVES, AND WHY IT MATTERS
-----------------------------------------
Do not move this file under ``tests/integration/``. Everything collected from
there is auto-marked ``integration`` (``tests/integration/conftest.py``) and
then skipped unless ``--run-integration`` is passed (``tests/knowledge/
conftest.py``). The command this repository's CI actually runs
(``.github/workflows/tests.yml``: ``python -m pytest tests/ ...``) does not
pass that flag, so a proof placed there is silently skipped and would go green
forever while proving nothing — which is the exact failure this whole gate
exists to catch. ``tests/orchestrator/`` is collected and run by that command,
alongside ``test_boot_smoke_gate.py``.
"""

from __future__ import annotations

import subprocess
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

#: A declaration whose single check runs a command line. Used to prove that a
#: declaration written during the build is inert: if it were honoured, this
#: file would appear in the working copy.
MARKER_FILENAME = "the-build-made-guardkit-run-this.txt"
COMMAND_DECLARATION = f"""
version: 1
boot_smoke:
  - id: runs-a-command-line
    kind: command
    target: touch {MARKER_FILENAME}
    expected_exit: 0
"""


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")


def _commit_everything(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-m", message)


def _write_broken_composition(root: Path) -> None:
    """A composition root that forgets an argument its own class requires.

    ``create_service`` builds ``VoiceService`` without the ``audio_client``
    argument that class requires — the composition blows up the moment anything
    actually calls it, while every unit test that replaces ``VoiceService``
    with a stand-in stays green.
    """
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


def _declare_broken_seam(root: Path) -> None:
    """Commit a start-up check, and break the thing it checks.

    The declaration is COMMITTED before the build: that is the only copy
    GuardKit reads, so this is what a real repository looks like to the gate.
    """
    _init_repo(root)
    _write(root, ".guardkit/seam-checks.yaml", DECLARATION)
    _write_broken_composition(root)
    _commit_everything(root, "declare start-up checks")


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


def _pass_the_wiring_gate(
    wave_number: int,
    task_ids: List[str],
    feature,
    worktree: Worktree,
    wave_result: WaveExecutionResult,
):
    """Stand-in for the wiring gate that hands the wave back unchanged.

    Its parameters mirror the real method's by name, and it is installed with
    ``autospec=True``, so it is bound against the real signature — a stand-in
    that accepted anything would hide exactly the kind of drift this whole
    gate exists to catch.
    """
    return MagicMock(final_wave_result=wave_result, terminate=False)


def _common_patches(orchestrator):
    """The side-effecting dependencies every wave-phase test must stub."""
    return (
        patch.object(orchestrator, "_preflight_check"),
        patch.object(orchestrator, "_bootstrap_environment"),
        patch.object(
            orchestrator,
            "_run_post_wave_wiring_gate",
            autospec=True,
            side_effect=_pass_the_wiring_gate,
        ),
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
# 2 + 3. A broken declared check is reported, and is advisory by default
# ---------------------------------------------------------------------------


def _run_wave_phase(
    tmp_path: Path,
    feature=None,
    orchestrator: FeatureOrchestrator = None,
    mark_waves_for_real: bool = False,
) -> List[WaveExecutionResult]:
    orchestrator = orchestrator or _make_orchestrator(tmp_path)
    worktree = _make_worktree(tmp_path)
    feature = feature if feature is not None else _make_feature([["TASK-001"]])

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        if not mark_waves_for_real:
            stack.enter_context(patch.object(orchestrator, "_mark_wave_completed"))
        stack.enter_context(patch.object(
            orchestrator, "_execute_wave",
            side_effect=[_succeeding_wave(1, ["TASK-001"])],
        ))
        return orchestrator._wave_phase(feature, worktree)


def test_broken_declared_check_is_reported_but_does_not_fail_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    _declare_broken_seam(tmp_path)
    monkeypatch.delenv(boot_smoke_gate.BLOCKING_ENV_VAR, raising=False)

    with caplog.at_level("INFO", logger="guardkit.orchestrator.feature_orchestrator"):
        wave_results = _run_wave_phase(tmp_path)

    log = caplog.text
    assert "composition-root-constructs" in log
    assert "FAILED" in log
    assert boot_smoke_gate.BLOCKING_ENV_VAR in log, (
        "the report must name the flag that makes failures blocking"
    )
    # Advisory: nothing about the build's own result changed.
    assert wave_results[-1].smoke_gate_result is None


def test_broken_declared_check_fails_the_build_when_the_flag_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare_broken_seam(tmp_path)
    monkeypatch.setenv(boot_smoke_gate.BLOCKING_ENV_VAR, "1")

    wave_results = _run_wave_phase(tmp_path)

    gate_result = wave_results[-1].smoke_gate_result
    assert gate_result is not None
    assert gate_result.passed is False
    assert "composition-root-constructs" in gate_result.stderr
    # The operator sees a command string that says what ran and why it mattered.
    assert "start-up checks" in gate_result.command
    assert boot_smoke_gate.BLOCKING_ENV_VAR in gate_result.command


def test_a_blocked_build_does_not_leave_the_last_wave_recorded_as_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Otherwise a resume would skip the wave, and so skip the failed checks."""
    _declare_broken_seam(tmp_path)
    monkeypatch.setenv(boot_smoke_gate.BLOCKING_ENV_VAR, "1")
    feature = _make_feature([["TASK-001"]])

    _run_wave_phase(tmp_path, feature=feature, mark_waves_for_real=True)

    assert feature.execution.completed_waves == []


# ---------------------------------------------------------------------------
# 4. A declaration the build wrote itself is never run
# ---------------------------------------------------------------------------


def test_a_declaration_written_during_the_build_is_never_executed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    """The build agent writes the check list mid-build; GuardKit must ignore it.

    A ``kind: command`` entry names a command line that GuardKit runs. If the
    build's own copy of the file were honoured, the build could make GuardKit
    run anything. The command declared here creates a file; the proof is that
    the file does not exist afterwards.
    """
    _init_repo(tmp_path)
    _write(tmp_path, "README.md", "a repository with no start-up checks\n")
    _commit_everything(tmp_path, "no start-up checks declared")

    # ...and now the build writes one, exactly as a Player agent could.
    _write(tmp_path, ".guardkit/seam-checks.yaml", COMMAND_DECLARATION)
    monkeypatch.setenv(boot_smoke_gate.BLOCKING_ENV_VAR, "1")

    with caplog.at_level("INFO", logger="guardkit.orchestrator.feature_orchestrator"):
        wave_results = _run_wave_phase(tmp_path)

    assert not (tmp_path / MARKER_FILENAME).exists(), (
        "a declaration written during the build must not be executed"
    )
    assert wave_results[-1].smoke_gate_result is None
    assert "NOTHING in it was run" in caplog.text


# ---------------------------------------------------------------------------
# 5. What the operator actually sees
# ---------------------------------------------------------------------------


#: A declared check whose target does not exist in this repository at all, so
#: the checker reports "did not run" rather than pass or fail.
UNRESOLVABLE_DECLARATION = """
version: 1
boot_smoke:
  - id: nope
    kind: construct
    target: nosuchpackage.main:build
    expect_type: nosuchpackage.main:Thing
"""


def test_the_printed_report_keeps_the_verdict_in_square_brackets(
    tmp_path: Path, capsys
) -> None:
    """Square brackets are text here, not styling.

    The report writes verdicts as ``[did not run]``. The console library reads
    square brackets as style tags and silently deletes anything it does not
    recognise, which would take the verdict off the operator's screen.
    """
    _init_repo(tmp_path)
    _write(tmp_path, ".guardkit/seam-checks.yaml", UNRESOLVABLE_DECLARATION)
    _commit_everything(tmp_path, "declare a check whose target is absent")

    orchestrator = _make_orchestrator(tmp_path)
    orchestrator.quiet = False
    _run_wave_phase(tmp_path, orchestrator=orchestrator)

    printed = capsys.readouterr().out
    assert "[did not run]" in printed, printed


# ---------------------------------------------------------------------------
# 6. When the checks are deliberately not run
# ---------------------------------------------------------------------------


def _wave_with_failed_smoke_gate(wave_number: int) -> WaveExecutionResult:
    wave = _succeeding_wave(wave_number, ["TASK-001"])
    wave.smoke_gate_result = MagicMock(passed=False)
    return wave


def test_a_build_that_stopped_early_does_not_get_start_up_checks(
    tmp_path: Path,
) -> None:
    orchestrator = _make_orchestrator(tmp_path)
    feature = _make_feature([["TASK-001"], ["TASK-002"]])

    reason = orchestrator._boot_smoke_skip_reason(
        feature, [_succeeding_wave(1, ["TASK-001"])]
    )

    assert reason == "the build stopped after wave 1 of 2"


def test_a_build_whose_smoke_gate_already_failed_does_not_get_start_up_checks(
    tmp_path: Path,
) -> None:
    orchestrator = _make_orchestrator(tmp_path)
    feature = _make_feature([["TASK-001"]])

    reason = orchestrator._boot_smoke_skip_reason(
        feature, [_wave_with_failed_smoke_gate(1)]
    )

    assert reason == "a smoke gate already failed this build"


def test_a_build_with_no_waves_at_all_does_not_get_start_up_checks(
    tmp_path: Path,
) -> None:
    orchestrator = _make_orchestrator(tmp_path)
    feature = _make_feature([["TASK-001"]])

    assert orchestrator._boot_smoke_skip_reason(feature, []) == "no wave ran"


def test_a_finished_green_build_does_get_start_up_checks(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)
    feature = _make_feature([["TASK-001"]])

    assert orchestrator._boot_smoke_skip_reason(
        feature, [_succeeding_wave(1, ["TASK-001"])]
    ) is None
