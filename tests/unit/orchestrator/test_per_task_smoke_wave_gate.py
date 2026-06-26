"""Regression tests for per-task runtime-parity wave gating (TASK-FIX-PARITYWAVE01).

Defect (FEAT-HARV wave-2): the per-task runtime-parity check (a *preview* of the
post-wave smoke gate, TASK-AB-COACHRUNPARITY01 arm b) threaded the feature
``smoke_gates.command`` to the per-task Coach for EVERY single-task wave, with no
check on the gate's ``after_wave`` scope. FEAT-HARV declares
``smoke_gates: {after_wave: 3, command: "… memory harvest --dry-run"}``, so the
wave-2 library walker (TASK-HARV-003) was run against the ``memory`` CLI
subcommand — which does not exist until the wave-3 deliverable (TASK-HARV-005).
That produced a ran-and-failed exit-2 ``No such command 'memory'`` that
deterministically overrode approve→feedback and blocked the (otherwise complete,
45/45-green) walker every turn until ``max_turns_exceeded``.

The fix gates the per-task command on the SAME ``should_fire_for_wave`` scope as
the post-wave gate: ``FeatureOrchestrator._per_task_smoke_command`` returns
``(None, 0)`` (an absent signal / no-op per arm b's ran=False safety) for any
wave the post-wave gate would not fire on.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.smoke_gates import SmokeGates


_HARV_CMD = "python -m guardkit.cli.main memory harvest --dry-run"


def _feature(smoke_gates) -> SimpleNamespace:
    return SimpleNamespace(smoke_gates=smoke_gates)


class TestPerTaskSmokeWaveGate:
    def test_feat_harv_reproducer_wave2_is_absent(self) -> None:
        """The exact FEAT-HARV shape: after_wave=3 → wave 2 gets no parity
        command, so the cross-wave 'No such command memory' cannot fire."""
        feature = _feature(SmokeGates(after_wave=3, command=_HARV_CMD, expected_exit=0))
        assert FeatureOrchestrator._per_task_smoke_command(feature, 2) == (None, 0)

    def test_int_after_wave_fires_only_on_that_wave(self) -> None:
        feature = _feature(SmokeGates(after_wave=3, command=_HARV_CMD, expected_exit=0))
        assert FeatureOrchestrator._per_task_smoke_command(feature, 1) == (None, 0)
        assert FeatureOrchestrator._per_task_smoke_command(feature, 2) == (None, 0)
        assert FeatureOrchestrator._per_task_smoke_command(feature, 3) == (_HARV_CMD, 0)
        # After the gate's wave it does not fire again (matches the post-wave gate).
        assert FeatureOrchestrator._per_task_smoke_command(feature, 4) == (None, 0)

    def test_no_smoke_gates_is_always_absent(self) -> None:
        feature = _feature(None)
        for wave in (1, 2, 3):
            assert FeatureOrchestrator._per_task_smoke_command(feature, wave) == (None, 0)

    def test_after_wave_all_fires_every_wave(self) -> None:
        feature = _feature(SmokeGates(after_wave="all", command="pytest", expected_exit=0))
        for wave in (1, 2, 5):
            assert FeatureOrchestrator._per_task_smoke_command(feature, wave) == ("pytest", 0)

    def test_after_wave_list_fires_on_listed_waves(self) -> None:
        feature = _feature(SmokeGates(after_wave=[2, 3], command="pytest", expected_exit=0))
        assert FeatureOrchestrator._per_task_smoke_command(feature, 1) == (None, 0)
        assert FeatureOrchestrator._per_task_smoke_command(feature, 2) == ("pytest", 0)
        assert FeatureOrchestrator._per_task_smoke_command(feature, 3) == ("pytest", 0)

    def test_expected_exit_is_threaded_when_firing(self) -> None:
        feature = _feature(SmokeGates(after_wave=1, command="run", expected_exit=5))
        assert FeatureOrchestrator._per_task_smoke_command(feature, 1) == ("run", 5)
        # And not threaded (defaults to 0) when the gate does not fire.
        assert FeatureOrchestrator._per_task_smoke_command(feature, 2) == (None, 0)
