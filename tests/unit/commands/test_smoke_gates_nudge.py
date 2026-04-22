"""Tests for installer/core/commands/lib/smoke_gates_nudge.py (TASK-FP-NDG2).

Covers the four AC branches (2 x wave-count x smoke-key-presence):

- Notice fires when feature YAML lacks ``smoke_gates:`` AND has >= 2 waves.
- Notice does not fire when ``smoke_gates:`` is present (even if minimal).
- Notice does not fire for single-wave features.
- Notice is suppressible via ``quiet=True``.

Plus defensive branches (missing file, malformed YAML, non-mapping root,
missing ``orchestration`` block) — the helper must never be the reason
``/feature-plan`` surfaces a traceback.
"""

from pathlib import Path

import pytest

from installer.core.commands.lib.smoke_gates_nudge import (
    check_smoke_gates_activation,
)


_TWO_WAVE_NO_SMOKE = """\
id: FEAT-T100
name: Example feature
description: Two waves, no smoke_gates configured
orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002, TASK-003]
  estimated_duration_minutes: 30
  recommended_parallel: 2
"""

_TWO_WAVE_WITH_SMOKE = """\
id: FEAT-T101
name: Example feature
description: Two waves with smoke_gates block
smoke_gates:
  after_wave_1:
    - python -c "import example"
orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002]
  estimated_duration_minutes: 30
  recommended_parallel: 2
"""

_TWO_WAVE_EMPTY_SMOKE = """\
id: FEAT-T102
name: Example feature
description: Two waves with smoke_gates present but null
smoke_gates:
orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002]
  estimated_duration_minutes: 30
  recommended_parallel: 2
"""

_ONE_WAVE_NO_SMOKE = """\
id: FEAT-T103
name: Single wave feature
description: Documentation-only, one wave
orchestration:
  parallel_groups:
    - [TASK-001, TASK-002]
  estimated_duration_minutes: 10
  recommended_parallel: 2
"""

_ONE_WAVE_WITH_SMOKE = """\
id: FEAT-T104
name: Single wave with smoke_gates
description: Honour author's config regardless of wave count
smoke_gates:
  after_wave_1:
    - pytest tests/smoke -x
orchestration:
  parallel_groups:
    - [TASK-001]
  estimated_duration_minutes: 10
  recommended_parallel: 1
"""

_THREE_WAVES_NO_SMOKE = """\
id: FEAT-T105
name: Three wave feature
description: Larger feature, no smoke_gates
orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002]
    - [TASK-003]
  estimated_duration_minutes: 60
  recommended_parallel: 2
"""


@pytest.fixture
def yaml_path(tmp_path: Path) -> Path:
    """Path to a feature YAML that does not yet exist (caller writes body)."""
    return tmp_path / "FEAT-T.yaml"


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# AC 1: Notice fires when feature YAML lacks smoke_gates AND has >= 2 waves
# ---------------------------------------------------------------------------


def test_returns_notice_when_two_waves_without_smoke_gates(
    yaml_path: Path,
) -> None:
    _write(yaml_path, _TWO_WAVE_NO_SMOKE)
    result = check_smoke_gates_activation(yaml_path)

    assert result is not None
    assert "Feature-level smoke gates (R3) not configured" in result
    assert "2 waves" in result  # actual wave count interpolated
    assert "smoke_gates:" in result  # copy-pasteable example
    assert "after_wave_1:" in result
    assert "after_wave_2:" in result
    assert "feature-plan.md" in result  # canonical doc pointer


def test_returns_notice_reports_actual_wave_count(yaml_path: Path) -> None:
    _write(yaml_path, _THREE_WAVES_NO_SMOKE)
    result = check_smoke_gates_activation(yaml_path)

    assert result is not None
    assert "3 waves" in result


# ---------------------------------------------------------------------------
# AC 2: Notice does not fire when smoke_gates: is present (even if minimal)
# ---------------------------------------------------------------------------


def test_returns_none_when_smoke_gates_configured(yaml_path: Path) -> None:
    _write(yaml_path, _TWO_WAVE_WITH_SMOKE)
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_smoke_gates_key_present_but_null(
    yaml_path: Path,
) -> None:
    # "even if minimal" — author has signalled awareness with just the key.
    _write(yaml_path, _TWO_WAVE_EMPTY_SMOKE)
    assert check_smoke_gates_activation(yaml_path) is None


# ---------------------------------------------------------------------------
# AC 3: Notice does not fire for single-wave features
# ---------------------------------------------------------------------------


def test_returns_none_for_single_wave_without_smoke_gates(
    yaml_path: Path,
) -> None:
    _write(yaml_path, _ONE_WAVE_NO_SMOKE)
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_for_single_wave_with_smoke_gates(
    yaml_path: Path,
) -> None:
    _write(yaml_path, _ONE_WAVE_WITH_SMOKE)
    assert check_smoke_gates_activation(yaml_path) is None


# ---------------------------------------------------------------------------
# AC 4: Notice is suppressible via quiet=True
# ---------------------------------------------------------------------------


def test_quiet_suppresses_notice_when_would_fire(yaml_path: Path) -> None:
    _write(yaml_path, _TWO_WAVE_NO_SMOKE)
    assert check_smoke_gates_activation(yaml_path, quiet=True) is None


def test_quiet_is_noop_when_single_wave(yaml_path: Path) -> None:
    _write(yaml_path, _ONE_WAVE_NO_SMOKE)
    assert check_smoke_gates_activation(yaml_path, quiet=True) is None


# ---------------------------------------------------------------------------
# Defensive: helper must never surface a traceback
# ---------------------------------------------------------------------------


def test_returns_none_when_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.yaml"
    assert check_smoke_gates_activation(missing) is None


def test_returns_none_when_yaml_is_malformed(yaml_path: Path) -> None:
    _write(yaml_path, ":\n  - [this is not: valid yaml\n")
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_yaml_root_is_not_mapping(yaml_path: Path) -> None:
    _write(yaml_path, "- just\n- a\n- list\n")
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_orchestration_missing(yaml_path: Path) -> None:
    _write(
        yaml_path,
        "id: FEAT-T\nname: No orchestration block\n",
    )
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_parallel_groups_missing(yaml_path: Path) -> None:
    _write(
        yaml_path,
        "id: FEAT-T\nname: Orchestration without parallel_groups\n"
        "orchestration:\n  recommended_parallel: 2\n",
    )
    assert check_smoke_gates_activation(yaml_path) is None


def test_returns_none_when_parallel_groups_not_a_list(yaml_path: Path) -> None:
    _write(
        yaml_path,
        "id: FEAT-T\nname: Malformed parallel_groups\n"
        "orchestration:\n  parallel_groups: not-a-list\n",
    )
    assert check_smoke_gates_activation(yaml_path) is None
