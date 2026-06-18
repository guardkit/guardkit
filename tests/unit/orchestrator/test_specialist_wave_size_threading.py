"""TASK-AB-NPDET01 — wave_size threading into the deterministic Phase-4 runner.

The non-Python whole-suite guard (run the suite only in a single-task wave)
is a no-op unless the REAL wave size reaches the CoachValidator the deterministic
runner constructs. Before this task the runner constructed CoachValidator without
wave_size, so it always believed wave_size=1. These tests pin the threading hop
by hop: invoke_test_orchestrator -> _run_deterministic_phase_4 -> CoachValidator.
"""

import asyncio
from unittest.mock import MagicMock

from guardkit.orchestrator import specialist_invocations as si
from guardkit.orchestrator.quality_gates.coach_validator import IndependentTestResult


def test_run_deterministic_phase_4_threads_wave_size_into_coach_validator(
    tmp_path, monkeypatch
):
    """_run_deterministic_phase_4(wave_size=N) must construct CoachValidator
    with wave_size=N — otherwise the parallel-wave guard never fires."""
    captured = {}

    class _FakeCoachValidator:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run_independent_tests(self, **kwargs):
            return IndependentTestResult(
                tests_passed=True,
                test_command="dotnet test",
                test_output_summary="ok",
                duration_seconds=0.1,
            )

    # _run_deterministic_phase_4 lazily imports CoachValidator from the module,
    # so patching the module attribute is picked up at call time.
    monkeypatch.setattr(
        "guardkit.orchestrator.quality_gates.coach_validator.CoachValidator",
        _FakeCoachValidator,
    )

    invoker = MagicMock()
    invoker._venv_python = None

    block = si._run_deterministic_phase_4(
        worktree_path=tmp_path,
        task_id="TASK-X",
        agent_invoker=invoker,
        sdk_timeout=300,
        turn=1,
        wave_size=3,
    )

    assert captured.get("wave_size") == 3
    assert block is not None and block["status"] == "passed"


def test_run_deterministic_phase_4_defaults_wave_size_to_one(tmp_path, monkeypatch):
    """Back-compat: omitting wave_size constructs CoachValidator with wave_size=1."""
    captured = {}

    class _FakeCoachValidator:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run_independent_tests(self, **kwargs):
            return IndependentTestResult(
                tests_passed=True,
                test_command="dotnet test",
                test_output_summary="ok",
                duration_seconds=0.1,
            )

    monkeypatch.setattr(
        "guardkit.orchestrator.quality_gates.coach_validator.CoachValidator",
        _FakeCoachValidator,
    )
    invoker = MagicMock()
    invoker._venv_python = None

    si._run_deterministic_phase_4(
        worktree_path=tmp_path,
        task_id="TASK-X",
        agent_invoker=invoker,
        sdk_timeout=300,
        turn=1,
    )
    assert captured.get("wave_size") == 1


def test_invoke_test_orchestrator_forwards_wave_size_to_deterministic_runner(
    tmp_path, monkeypatch
):
    """invoke_test_orchestrator(wave_size=N) must forward wave_size=N into
    _run_deterministic_phase_4."""
    (tmp_path / ".guardkit" / "autobuild" / "TASK-X").mkdir(parents=True)
    captured = {}

    def _fake_det(**kwargs):
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

    monkeypatch.setenv("GUARDKIT_PHASE4_TEST_EXECUTION", "subprocess")
    monkeypatch.setattr(si, "_run_deterministic_phase_4", _fake_det)

    invoker = MagicMock()
    result = asyncio.run(
        si.invoke_test_orchestrator(
            worktree_path=tmp_path,
            task_id="TASK-X",
            sdk_timeout=300,
            agent_invoker=invoker,
            turn=1,
            wave_size=4,
        )
    )

    assert captured.get("wave_size") == 4
    assert result.status == "passed"
