"""Per-task runtime-parity command scope gating (TASK-FIX-PARITYWAVE01).

The per-task runtime-parity check (arm b of TASK-AB-COACHRUNPARITY01) is a
*preview* of the post-wave smoke gate. ``FeatureOrchestrator._execute_wave``
must only thread the feature ``smoke_gates.command`` into the per-task Coach
for waves where the post-wave smoke gate itself fires
(``should_fire_for_wave``). Otherwise a *later* wave's smoke command — whose
CLI subcommand does not exist until that wave's deliverable lands — is run as
a parity preview against an *earlier* wave's deliverable, producing an exit-2
``No such command`` the task cannot fix (FEAT-HARV wave-2 walker vs the wave-3
``memory harvest`` CLI).

These tests pin ``_per_task_smoke_command`` — the testable helper the gating
was extracted into — against every ``after_wave`` form.

Coverage Target: the gating helper, all after_wave forms + the FEAT-HARV
reproducer.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

# Harness-touching module: pin the SDK harness so importing the orchestrator on
# a machine where guardkitfactory + langchain are installed does not try to
# resolve the LangGraph substrate at import time (the
# ci-tests-yml-no-guardkitfactory hazard). The helper under test is a pure
# staticmethod, so the substrate choice is irrelevant to behaviour.
os.environ.setdefault("GUARDKIT_HARNESS", "sdk")

from guardkit.orchestrator.feature_loader import SmokeGates  # noqa: E402
from guardkit.orchestrator.feature_orchestrator import (  # noqa: E402
    FeatureOrchestrator,
)


def _feature(smoke_gates):
    """Minimal stand-in carrying only the attribute the helper reads."""
    return SimpleNamespace(smoke_gates=smoke_gates)


# ----------------------------------------------------------------------
# FEAT-HARV reproducer — the defect this task fixes
# ----------------------------------------------------------------------


def test_feat_harv_reproducer_after_wave_3_wave_2_is_absent() -> None:
    """after_wave=3: wave 2 yields (None, 0) so the wave-3 CLI never runs.

    The exact FEAT-HARV shape: smoke gate fires after wave 3 (the
    ``memory harvest`` CLI), wave 2 is the single-task library walker. The
    walker must NOT receive the wave-3 command as a parity preview.
    """
    feature = _feature(
        SmokeGates(
            after_wave=3,
            command="python -m guardkit.cli.main memory harvest --dry-run",
            expected_exit=0,
        )
    )
    assert FeatureOrchestrator._per_task_smoke_command(feature, 2) == (None, 0)


# ----------------------------------------------------------------------
# after_wave: int
# ----------------------------------------------------------------------


def test_int_form_fires_only_on_that_wave() -> None:
    feature = _feature(
        SmokeGates(after_wave=3, command="run-cli", expected_exit=0)
    )
    assert FeatureOrchestrator._per_task_smoke_command(feature, 1) == (None, 0)
    assert FeatureOrchestrator._per_task_smoke_command(feature, 2) == (None, 0)
    assert FeatureOrchestrator._per_task_smoke_command(feature, 3) == (
        "run-cli",
        0,
    )
    assert FeatureOrchestrator._per_task_smoke_command(feature, 4) == (None, 0)


# ----------------------------------------------------------------------
# after_wave: list
# ----------------------------------------------------------------------


def test_list_form_fires_on_each_listed_wave() -> None:
    feature = _feature(
        SmokeGates(after_wave=[1, 3], command="run-cli", expected_exit=0)
    )
    assert FeatureOrchestrator._per_task_smoke_command(feature, 1) == (
        "run-cli",
        0,
    )
    assert FeatureOrchestrator._per_task_smoke_command(feature, 2) == (None, 0)
    assert FeatureOrchestrator._per_task_smoke_command(feature, 3) == (
        "run-cli",
        0,
    )


# ----------------------------------------------------------------------
# after_wave: "all"
# ----------------------------------------------------------------------


def test_all_form_fires_every_wave() -> None:
    feature = _feature(
        SmokeGates(after_wave="all", command="run-cli", expected_exit=0)
    )
    for wave in (1, 2, 3, 7):
        assert FeatureOrchestrator._per_task_smoke_command(feature, wave) == (
            "run-cli",
            0,
        )


# ----------------------------------------------------------------------
# No smoke gate configured
# ----------------------------------------------------------------------


def test_no_smoke_gate_is_always_absent() -> None:
    feature = _feature(None)
    for wave in (1, 2, 3):
        assert FeatureOrchestrator._per_task_smoke_command(feature, wave) == (
            None,
            0,
        )


# ----------------------------------------------------------------------
# expected_exit threading
# ----------------------------------------------------------------------


def test_expected_exit_is_threaded_on_the_firing_wave() -> None:
    """A non-default expected_exit is returned verbatim on the firing wave."""
    feature = _feature(
        SmokeGates(after_wave=2, command="run-cli", expected_exit=5)
    )
    assert FeatureOrchestrator._per_task_smoke_command(feature, 2) == (
        "run-cli",
        5,
    )
    # Non-firing wave is still an absent no-op (expected_exit 0, command None).
    assert FeatureOrchestrator._per_task_smoke_command(feature, 1) == (None, 0)
