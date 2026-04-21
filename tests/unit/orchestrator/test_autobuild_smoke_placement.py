"""Placement tests for feature-level smoke gates (TASK-SMK-F703A).

Smoke gates run BETWEEN WAVES, not between tasks. Per-task smoke is the
per-task Coach with extra steps; the review that created this task
(TASK-REV-4D012 §6 R3) called out this scope boundary explicitly.

These tests pin that invariant against three ways it could regress:
1. A subprocess call bleeding into the per-task execution path.
2. The smoke gate being referenced inside ``_execute_task``.
3. The smoke gate firing once per task instead of once per wave.
"""

from __future__ import annotations

import inspect

from guardkit.orchestrator import feature_orchestrator, smoke_gates
from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.smoke_gates import should_fire_for_wave


def test_smoke_not_invoked_per_task() -> None:
    """The smoke-gate entrypoint must not appear in per-task execution.

    ``_execute_task`` delegates to ``AutoBuildOrchestrator`` for a single
    task's Player-Coach loop. If ``run_smoke_gate`` ever appears inside
    that path, the smoke gate has become per-task — which is exactly what
    TASK-SMK-F703A's non-goals reject.

    Reading source strings (rather than running the full orchestrator)
    keeps this test fast and deterministic: it catches the regression at
    the point the code is written.
    """
    execute_task_src = inspect.getsource(feature_orchestrator.FeatureOrchestrator._execute_task)

    forbidden = [
        "run_smoke_gate",
        "should_fire_for_wave",
        "smoke_gates",  # no reference to the schema field or module either
    ]
    for needle in forbidden:
        assert needle not in execute_task_src, (
            f"{needle!r} must not appear in _execute_task. Smoke gates "
            f"run between waves, not between tasks. See TASK-SMK-F703A "
            f"non-goals."
        )


def test_smoke_gate_module_does_not_import_autobuild_task_runner() -> None:
    """The smoke-gate module must not reach into per-task infrastructure.

    If ``smoke_gates.py`` imports the task-level AutoBuild runner, it
    has acquired the ability to intervene per task — a category error.
    """
    module_src = inspect.getsource(smoke_gates)

    forbidden = [
        "from guardkit.orchestrator.autobuild import",
        "AutoBuildOrchestrator",
    ]
    for needle in forbidden:
        assert needle not in module_src, (
            f"smoke_gates.py must not import {needle!r}. The smoke gate "
            f"is a between-wave subprocess, not a task orchestrator."
        )


def test_smoke_gate_hook_lives_in_wave_phase_only() -> None:
    """The smoke gate hook is wired in ``_wave_phase``, nowhere else.

    ``_wave_phase`` is the only place that knows the 1-indexed wave
    boundary from ``enumerate(parallel_groups, 1)``; that's the only
    coherent place the hook can live.
    """
    wave_phase_src = inspect.getsource(feature_orchestrator.FeatureOrchestrator._wave_phase)
    assert "run_smoke_gate" in wave_phase_src, (
        "_wave_phase must invoke run_smoke_gate after a wave completes."
    )
    assert "should_fire_for_wave" in wave_phase_src, (
        "_wave_phase must gate the smoke invocation on should_fire_for_wave."
    )


def test_smoke_gate_fires_once_per_matching_wave() -> None:
    """Given 3 tasks in wave 1 and ``after_wave: 1``, the gate fires once.

    This is a logical check on ``should_fire_for_wave`` semantics rather
    than a full orchestrator run: the decision function returns a bool
    for a single wave_number, so the orchestrator — which calls it once
    per completed wave — cannot fire twice on the same wave.
    """
    config = SmokeGates(after_wave=1, command="pytest")

    # The orchestrator calls should_fire_for_wave once per wave in the loop.
    # It cannot call it per task because _execute_task has no access to it.
    decisions = [should_fire_for_wave(config, wave) for wave in (1, 2)]
    assert decisions == [True, False]
