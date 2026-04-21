"""Wave-boundary tests for feature-level smoke gates (TASK-SMK-F703A).

The smoke gate MUST reuse the AutoBuild feature-mode wave definition
(topological level of ``tasks[].depends_on`` / ``tasks[].wave`` from
``FEAT-*.yaml``). Inventing a second wave concept would contradict the
task's non-goals; these tests pin that invariant.
"""

from __future__ import annotations

import inspect

from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.smoke_gates import should_fire_for_wave


def test_smoke_uses_existing_wave_definition() -> None:
    """``should_fire_for_wave`` must not derive waves from any source.

    It receives the wave number as a parameter and returns a decision.
    If this function ever starts accepting tasks, a feature, a dependency
    graph, or anything that lets it *compute* waves, it has drifted into
    territory the feature-plan already owns.

    This guard reads the function signature rather than running behaviour,
    because the failure mode we care about ("someone added wave discovery
    to the smoke gate") is a signature regression.
    """
    sig = inspect.signature(should_fire_for_wave)
    params = list(sig.parameters.keys())
    assert params == ["config", "wave_number"], (
        "should_fire_for_wave must take only (config, wave_number); it "
        "must not accept any source from which waves could be computed. "
        f"Got: {params}. See TASK-SMK-F703A guardrails."
    )

    config = SmokeGates(after_wave=1, command="true")

    # The function is a pure decision: same wave_number, same answer.
    # It cannot reach out for task graphs or feature orchestration.
    assert should_fire_for_wave(config, 1) is True
    assert should_fire_for_wave(config, 2) is False


def test_after_wave_1_fires_when_topological_level_1_approved() -> None:
    """``after_wave: 1`` fires when topological level 1 completes.

    Topological level == wave number in the feature-plan
    ``parallel_groups`` — the orchestrator iterates ``enumerate(groups, 1)``
    and passes that 1-indexed number to the smoke gate. This test asserts
    the smoke gate fires for ``wave_number=1`` regardless of wall-clock
    time or task count in the wave.
    """
    config = SmokeGates(after_wave=1, command="pytest")

    assert should_fire_for_wave(config, 1) is True
    assert should_fire_for_wave(config, 2) is False
    assert should_fire_for_wave(config, 3) is False


def test_after_wave_all_fires_every_wave() -> None:
    """``after_wave: all`` fires after every wave."""
    config = SmokeGates(after_wave="all", command="pytest")

    for wave in range(1, 6):
        assert should_fire_for_wave(config, wave) is True


def test_after_wave_list_fires_only_for_listed_waves() -> None:
    """``after_wave: [1, 3]`` fires after waves 1 and 3 only."""
    config = SmokeGates(after_wave=[1, 3], command="pytest")

    assert should_fire_for_wave(config, 1) is True
    assert should_fire_for_wave(config, 2) is False
    assert should_fire_for_wave(config, 3) is True
    assert should_fire_for_wave(config, 4) is False
