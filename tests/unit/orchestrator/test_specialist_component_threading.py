"""PHASE-4 COMPONENT THREADING — the Player's Phase-4 oracle follows the task.

The defect, stated once: a monorepo declares one toolchain per component
(study-tutor = ``uv run … pytest`` at the root, ``flutter test`` under
``app/``). The COACH's independent verification already resolves the task's
component. The PLAYER's Phase-4 block did not — the chain
``autobuild._execute_turn -> invoke_test_orchestrator ->
_run_deterministic_phase_4 -> CoachValidator`` dropped the selector, so an
``app`` task's Phase-4 narrative was produced by the ROOT oracle. Honestly
degraded, and named as such in a comment; these tests retire that comment.

Four things are pinned here:

1. **The selector survives every hop** — orchestrator turn -> specialist ->
   deterministic runner -> ``CoachValidator(component=…)``.
2. **The root path is byte-preserved** — omitting ``component`` constructs the
   validator with ``component=None``, i.e. exactly the pre-threading call.
3. **The oracle really changes** — with a real snapshot of the study-tutor
   shape, the component task's Phase-4 block reports the COMPONENT's command
   and a real subprocess records that it ran in ``app/``; the control still
   reports the root's, from the root.
4. **An ``sdk`` revert cannot outrun it** — the LLM specialist runs with the
   worktree root as cwd, so a named component FORCES the deterministic path
   (the same law ``CoachValidator.run_independent_tests`` already states).

Network-free and broker-free: the only subprocesses are ``pwd`` against a
temp directory.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from guardkit.orchestrator import specialist_invocations as si
from guardkit.orchestrator.quality_gates.coach_validator import IndependentTestResult
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain

_TASK_ID = "TASK-P4C-001"

# The study-tutor SHAPE (mirrors tests/orchestrator/test_per_component_toolchain.py):
# a Python root and a Flutter app under ``app/``, out of ONE declaration.
STUDY_TUTOR_SHAPE = {
    "test": "uv run --no-sync python -m pytest -q",
    "components": {
        "app": {
            "cwd": "app",
            "test": "flutter test",
            "install": "flutter pub get",
            "test_timeout": 900,
        },
    },
}


def _fake_coach_validator(captured: dict, *, passed: bool = True):
    """A CoachValidator stand-in that records its construction kwargs."""

    class _FakeCoachValidator:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run_independent_tests(self, **kwargs):
            return IndependentTestResult(
                tests_passed=passed,
                test_command="flutter test",
                test_output_summary="ok",
                duration_seconds=0.1,
            )

    return _FakeCoachValidator


def _patch_validator(monkeypatch, captured):
    """_run_deterministic_phase_4 imports CoachValidator lazily from the
    module, so patching the module attribute is picked up at call time."""
    monkeypatch.setattr(
        "guardkit.orchestrator.quality_gates.coach_validator.CoachValidator",
        _fake_coach_validator(captured),
    )


def _invoker():
    """An AgentInvoker stand-in carrying a RESOLVABLE interpreter.

    The deterministic runner constructs the validator with
    ``in_autobuild_context=True``, where an unresolved interpreter is a
    hard-abort by design (WS3-S1 Q1 SPLIT). Handing it this process's own
    interpreter keeps these tests about the component seam.
    """
    invoker = MagicMock()
    invoker._venv_python = sys.executable
    return invoker


# =========================================================================
# 1. Hop 3 — _run_deterministic_phase_4 -> CoachValidator
# =========================================================================


def test_deterministic_phase_4_threads_component_into_coach_validator(
    tmp_path, monkeypatch
):
    """_run_deterministic_phase_4(component="app") must construct
    CoachValidator with component="app" — otherwise the Player's Phase-4 block
    is the ROOT oracle's verdict on the app's work."""
    captured: dict = {}
    _patch_validator(monkeypatch, captured)

    block = si._run_deterministic_phase_4(
        worktree_path=tmp_path,
        task_id=_TASK_ID,
        agent_invoker=_invoker(),
        sdk_timeout=300,
        turn=1,
        component="app",
    )

    assert captured.get("component") == "app"
    assert block is not None and block["status"] == "passed"


def test_deterministic_phase_4_omits_component_by_default(tmp_path, monkeypatch):
    """BYTE-PRESERVED ROOT PATH: omitting component constructs the validator
    with component=None — the pre-threading call, unchanged. Every
    single-toolchain repo takes this branch."""
    captured: dict = {}
    _patch_validator(monkeypatch, captured)

    si._run_deterministic_phase_4(
        worktree_path=tmp_path,
        task_id=_TASK_ID,
        agent_invoker=_invoker(),
        sdk_timeout=300,
        turn=1,
    )

    assert captured.get("component") is None
    # The rest of the construction is unchanged alongside it.
    assert captured.get("wave_size") == 1
    assert captured.get("coach_test_execution") == "subprocess"
    assert captured.get("basetemp_context") == "phase4"


# =========================================================================
# 2. Hop 2 — invoke_test_orchestrator -> the deterministic runner
# =========================================================================


def _fake_det(captured: dict):
    def _inner(**kwargs):
        captured.update(kwargs)
        return {
            "status": "passed",
            "duration_seconds": 0.1,
            "error": None,
            "tests_run": 1,
            "tests_failed": 0,
            "coverage_pct": 0.0,
            "output_summary": "ok",
            "quality_gates_passed": True,
        }

    return _inner


def test_invoke_test_orchestrator_forwards_component(tmp_path, monkeypatch):
    """invoke_test_orchestrator(component="app") forwards component="app"."""
    (tmp_path / ".guardkit" / "autobuild" / _TASK_ID).mkdir(parents=True)
    captured: dict = {}
    monkeypatch.setenv("GUARDKIT_PHASE4_TEST_EXECUTION", "subprocess")
    monkeypatch.setattr(si, "_run_deterministic_phase_4", _fake_det(captured))

    result = asyncio.run(
        si.invoke_test_orchestrator(
            worktree_path=tmp_path,
            task_id=_TASK_ID,
            sdk_timeout=300,
            agent_invoker=MagicMock(),
            turn=1,
            component="app",
        )
    )

    assert captured.get("component") == "app"
    assert result.status == "passed"


def test_invoke_test_orchestrator_defaults_component_to_none(tmp_path, monkeypatch):
    """BYTE-PRESERVED ROOT PATH at the specialist hop too."""
    (tmp_path / ".guardkit" / "autobuild" / _TASK_ID).mkdir(parents=True)
    captured: dict = {}
    monkeypatch.setenv("GUARDKIT_PHASE4_TEST_EXECUTION", "subprocess")
    monkeypatch.setattr(si, "_run_deterministic_phase_4", _fake_det(captured))

    asyncio.run(
        si.invoke_test_orchestrator(
            worktree_path=tmp_path,
            task_id=_TASK_ID,
            sdk_timeout=300,
            agent_invoker=MagicMock(),
            turn=1,
        )
    )

    assert captured.get("component") is None


# =========================================================================
# 3. The sdk-mode pin — a component cannot be run from the worktree root
# =========================================================================


def test_sdk_mode_is_overridden_when_a_component_is_named(
    tmp_path, monkeypatch, caplog
):
    """GUARDKIT_PHASE4_TEST_EXECUTION=sdk hands the run to a one-turn LLM with
    the WORKTREE ROOT as cwd. A component task must still take the
    deterministic path — the only one that honours the component's cwd — and
    must say so. Mirrors CoachValidator's component_pinned_subprocess law."""
    (tmp_path / ".guardkit" / "autobuild" / _TASK_ID).mkdir(parents=True)
    captured: dict = {}
    monkeypatch.setenv("GUARDKIT_PHASE4_TEST_EXECUTION", "sdk")
    monkeypatch.setattr(si, "_run_deterministic_phase_4", _fake_det(captured))

    with caplog.at_level("WARNING"):
        result = asyncio.run(
            si.invoke_test_orchestrator(
                worktree_path=tmp_path,
                task_id=_TASK_ID,
                sdk_timeout=300,
                agent_invoker=MagicMock(),
                turn=1,
                component="app",
            )
        )

    assert captured.get("component") == "app", (
        "sdk mode must not route a component task to the root-cwd specialist"
    )
    assert result.status == "passed"
    assert any(
        "forcing the deterministic SUBPROCESS" in r.getMessage()
        and "'app'" in r.getMessage()
        for r in caplog.records
    ), "the override must be logged out loud, naming the component"


def test_sdk_mode_still_reaches_the_specialist_without_a_component(
    tmp_path, monkeypatch
):
    """BYTE-PRESERVED REVERT LEVER: with no component, ``sdk`` still bypasses
    the deterministic runner exactly as before."""
    (tmp_path / ".guardkit" / "autobuild" / _TASK_ID).mkdir(parents=True)
    called: dict = {}
    monkeypatch.setenv("GUARDKIT_PHASE4_TEST_EXECUTION", "sdk")
    monkeypatch.setattr(si, "_run_deterministic_phase_4", _fake_det(called))

    async def _fake_run_specialist(**kwargs):
        return si.SpecialistInvocationResult(
            specialist_name="test-orchestrator",
            phase="4",
            status="passed",
            duration_seconds=0.1,
            result_file=None,
            error=None,
        )

    monkeypatch.setattr(si, "run_specialist", _fake_run_specialist)

    asyncio.run(
        si.invoke_test_orchestrator(
            worktree_path=tmp_path,
            task_id=_TASK_ID,
            sdk_timeout=300,
            agent_invoker=MagicMock(),
            turn=1,
        )
    )

    assert called == {}, "sdk mode must still bypass the deterministic runner"


# =========================================================================
# 4. END TO END — the oracle really is the component's, at the component's cwd
# =========================================================================


@pytest.fixture
def repo(tmp_path):
    """Repo root + the worktree beneath it, with the ``app/`` component dir."""
    root = tmp_path / "study-tutor"
    worktree = root / ".guardkit" / "worktrees" / _TASK_ID
    worktree.mkdir(parents=True)
    (worktree / "app").mkdir()
    (worktree / "pyproject.toml").touch()
    (worktree / ".guardkit" / "autobuild" / _TASK_ID).mkdir(parents=True)
    return root, worktree


def _declare(root, worktree, block):
    cfg = root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": block}), encoding="utf-8"
    )
    snapshot_task_toolchain(_TASK_ID, worktree, root)


def test_the_component_task_gets_the_components_command_in_its_phase_4_block(repo):
    """No fake validator: a REAL snapshot of the study-tutor shape, and the
    Phase-4 block reports ``flutter test`` — the app's oracle, not the root's."""
    root, worktree = repo
    _declare(root, worktree, STUDY_TUTOR_SHAPE)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        block = si._run_deterministic_phase_4(
            worktree_path=worktree,
            task_id=_TASK_ID,
            agent_invoker=_invoker(),
            sdk_timeout=300,
            turn=1,
            component="app",
        )

    assert block is not None and block["status"] == "passed"
    assert mock_run.call_args.args[0] == "flutter test"
    assert mock_run.call_args.kwargs["cwd"] == str(worktree / "app")


def test_the_control_task_still_gets_the_root_command(repo):
    """The byte-unchanged half of the same experiment: SAME repo, SAME
    declaration, no component -> the root's command from the worktree root."""
    root, worktree = repo
    _declare(root, worktree, STUDY_TUTOR_SHAPE)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        block = si._run_deterministic_phase_4(
            worktree_path=worktree,
            task_id=_TASK_ID,
            agent_invoker=_invoker(),
            sdk_timeout=300,
            turn=1,
        )

    assert block is not None and block["status"] == "passed"
    assert mock_run.call_args.args[0] == "uv run --no-sync python -m pytest -q"
    assert mock_run.call_args.kwargs["cwd"] == str(worktree)


def test_a_real_subprocess_runs_phase_4_in_the_components_directory(repo):
    """THE MARKER FLIP: no mock. The Phase-4 command records the directory it
    was really executed in, and the marker lands in ``app/``."""
    root, worktree = repo
    _declare(
        root,
        worktree,
        {
            "test": "pwd > ran_here.txt",
            "components": {"app": {"cwd": "app", "test": "pwd > ran_here.txt"}},
        },
    )

    block = si._run_deterministic_phase_4(
        worktree_path=worktree,
        task_id=_TASK_ID,
        agent_invoker=_invoker(),
        sdk_timeout=300,
        turn=1,
        component="app",
    )

    assert block is not None and block["status"] == "passed"
    marker = worktree / "app" / "ran_here.txt"
    assert marker.exists(), "Phase 4 did not run in the component's directory"
    assert not (worktree / "ran_here.txt").exists()
    assert Path(marker.read_text().strip()).resolve() == (worktree / "app").resolve()


def test_the_control_really_runs_at_the_worktree_root(repo):
    """Same command, no component: the marker lands at the root."""
    root, worktree = repo
    _declare(
        root,
        worktree,
        {
            "test": "pwd > ran_here.txt",
            "components": {"app": {"cwd": "app", "test": "pwd > ran_here.txt"}},
        },
    )

    block = si._run_deterministic_phase_4(
        worktree_path=worktree,
        task_id=_TASK_ID,
        agent_invoker=_invoker(),
        sdk_timeout=300,
        turn=1,
    )

    assert block is not None and block["status"] == "passed"
    marker = worktree / "ran_here.txt"
    assert marker.exists()
    assert not (worktree / "app" / "ran_here.txt").exists()


def test_an_undeclared_component_is_a_loud_absence_never_the_root_oracle(repo):
    """A component the repo does not declare must NOT quietly re-run the root
    command. It is an instrument fault: signal_absent -> status="failed", so
    the #2 reconcile fires and Phase 5 is skipped. Absence is not success."""
    root, worktree = repo
    _declare(root, worktree, STUDY_TUTOR_SHAPE)

    with patch("subprocess.run") as mock_run:
        block = si._run_deterministic_phase_4(
            worktree_path=worktree,
            task_id=_TASK_ID,
            agent_invoker=_invoker(),
            sdk_timeout=300,
            turn=1,
            component="web",  # not declared
        )

    assert block is not None
    assert block["status"] == "failed"
    assert block.get("signal_absent") is True
    assert block.get("verifier_infrastructure") is True
    mock_run.assert_not_called()


# =========================================================================
# 5. Hop 1 — the orchestrator turn hands its component to the specialist
# =========================================================================


def _bare_orchestrator(worktree_path):
    """A minimal AutoBuildOrchestrator, mirroring the __new__-based helper in
    tests/unit/test_autobuild_timeout_budget.py — enough to reach the Phase-4
    call site inside ``_execute_turn`` without a real SDK or worktree."""
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    o = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    o.max_turns = 3
    o.resume = False
    o.repo_root = worktree_path
    o.enable_pre_loop = False
    o.enable_context = False
    o.ablation_mode = False
    o.enable_checkpoints = False
    o.rollback_on_pollution = False
    o._cancellation_event = None
    o._timeout_event = None
    o._task_timeout = None
    o._loop_start_time = None
    o._cumulative_source_files = set()
    o._cumulative_requirements_addressed = set()
    o.wave_size = 1
    o._wave_changed_files = None
    o._wave_files_lock = None
    o._turn_history = []
    o._feature_id = None
    o._max_criteria_passed = 0
    o._agent_invoker = Mock()
    o._agent_invoker._get_implementation_mode.return_value = "task-work"
    o._agent_invoker._inject_specialist_records_into_task_work_results = Mock()
    o._agent_invoker._calculate_sdk_timeout = Mock(return_value=1200)
    o._worktree_manager = Mock()
    o._checkpoint_manager = None
    o._last_player_context_status = None
    o._last_coach_context_status = None
    o.verbose = False
    o.perspective_reset_turns = []
    o._seed_feedback = None
    o._smoke_command = None
    o._smoke_expected_exit = 0
    o.sdk_timeout = 1200

    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    progress.console = Mock()
    progress.start_turn = Mock()
    progress.complete_turn = Mock()
    o._progress_display = progress
    return o


def _run_turn_capturing_phase4(tmp_path, component):
    """Drive ``_execute_turn`` far enough to reach the Phase-4 call and return
    the kwargs it handed ``invoke_test_orchestrator``."""
    from guardkit.orchestrator import specialist_invocations as _si
    from guardkit.orchestrator.agent_invoker import AgentInvocationResult
    from guardkit.worktrees import Worktree

    wt = Mock(spec=Worktree)
    wt.task_id = _TASK_ID
    wt.path = tmp_path / "worktree"
    wt.path.mkdir(exist_ok=True)
    wt.branch_name = f"autobuild/{_TASK_ID}"
    wt.base_branch = "main"

    o = _bare_orchestrator(tmp_path)
    captured: dict = {}

    async def _fake_phase4(**kwargs):
        captured.update(kwargs)
        r = Mock()
        r.status = "passed"
        return r

    async def _fake_phase5(**kwargs):
        return Mock()

    def _result(agent_type, report):
        return AgentInvocationResult(
            task_id=_TASK_ID,
            turn=1,
            agent_type=agent_type,
            success=True,
            report=report,
            duration_seconds=1.0,
            error=None,
        )

    with patch.object(
        o,
        "_invoke_player_safely",
        return_value=_result("player", {"files_changed": [], "tests_passed": True}),
    ), patch.object(
        o,
        "_invoke_coach_safely",
        return_value=_result("coach", {"decision": "approve", "feedback": "ok"}),
    ), patch.object(
        o, "_build_player_summary", return_value="ok"
    ), patch.object(
        _si, "invoke_test_orchestrator", side_effect=_fake_phase4
    ), patch.object(
        _si, "invoke_code_reviewer", side_effect=_fake_phase5
    ):
        o._execute_turn(
            turn=1,
            task_id=_TASK_ID,
            requirements="do stuff",
            worktree=wt,
            previous_feedback=None,
            component=component,
        )

    return captured


def test_execute_turn_hands_its_component_to_the_phase_4_specialist(tmp_path):
    """THE TOP HOP: the turn's already-validated component selector reaches
    invoke_test_orchestrator. Without this the other two hops are dead code."""
    captured = _run_turn_capturing_phase4(tmp_path, component="app")
    assert captured.get("component") == "app"


def test_execute_turn_passes_none_for_a_single_toolchain_repo(tmp_path):
    """BYTE-PRESERVED ROOT PATH at the top hop: no component -> None."""
    captured = _run_turn_capturing_phase4(tmp_path, component=None)
    assert captured.get("component") is None
    # ...alongside the wave_size hop it rides with, unchanged.
    assert captured.get("wave_size") == 1
