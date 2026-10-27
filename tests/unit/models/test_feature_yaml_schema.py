"""Schema tests for the optional ``smoke_gates`` key on FEAT-*.yaml.

Covers TASK-SMK-F703A acceptance criteria:
- feature YAML without ``smoke_gates`` loads unchanged
- since the cull (27 October 2026, GKT-034) the values are kept as written
  and a ``smoke_gates`` block that cannot be read is skipped
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    SmokeGates,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_feature_yaml(dir_path: Path, feature_id: str, body: str) -> Path:
    """Write a FEAT-*.yaml into ``dir_path`` and return its path."""
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{feature_id}.yaml"
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return path


_BASE_FEATURE = """\
id: FEAT-TEST
name: Test Feature
description: Baseline feature with no smoke_gates
tasks:
  - id: TASK-T1
    file_path: tasks/backlog/TASK-T1.md
  - id: TASK-T2
    file_path: tasks/backlog/TASK-T2.md
orchestration:
  parallel_groups:
    - [TASK-T1]
    - [TASK-T2]
  estimated_duration_minutes: 30
  recommended_parallel: 1
"""


# ---------------------------------------------------------------------------
# AC: feature YAML without smoke_gates loads unchanged
# ---------------------------------------------------------------------------


def test_smoke_gates_optional(tmp_path: Path) -> None:
    """Feature YAML with no ``smoke_gates`` key loads; field defaults to None."""
    features_dir = tmp_path / ".guardkit" / "features"
    _write_feature_yaml(features_dir, "FEAT-TEST", _BASE_FEATURE)

    feature = FeatureLoader.load_feature(
        "FEAT-TEST", repo_root=tmp_path, features_dir=features_dir
    )

    assert isinstance(feature, Feature)
    assert feature.smoke_gates is None, (
        "Features without a smoke_gates key must have smoke_gates=None "
        "so they run identically to today (zero-regression AC)."
    )


# ---------------------------------------------------------------------------
# The cull: values are kept; a block that cannot be read is skipped
# ---------------------------------------------------------------------------


def _load(tmp_path: Path, fragment: str) -> Feature:
    features_dir = tmp_path / ".guardkit" / "features"
    _write_feature_yaml(
        features_dir, "FEAT-TEST", _BASE_FEATURE + textwrap.dedent(fragment)
    )
    return FeatureLoader.load_feature(
        "FEAT-TEST", repo_root=tmp_path, features_dir=features_dir
    )


@pytest.mark.parametrize(
    "fragment, field, value",
    [
        ("smoke_gates:\n  after_wave: -1\n  command: pytest\n", "after_wave", -1),
        ("smoke_gates:\n  after_wave: 1\n  command: pytest\n  timeout: 0\n", "timeout", 0),
        ("smoke_gates:\n  after_wave: 1\n  command: pytest\n  timeout: 700\n", "timeout", 700),
        ("smoke_gates:\n  after_wave: []\n  command: pytest\n", "after_wave", []),
        ("smoke_gates:\n  after_wave: 1\n  command: pytest\n  unknown_key: oops\n", "command", "pytest"),
    ],
)
def test_smoke_gates_values_are_kept(tmp_path: Path, fragment, field, value) -> None:
    feature = _load(tmp_path, fragment)
    assert feature.smoke_gates is not None
    assert getattr(feature.smoke_gates, field) == value


@pytest.mark.parametrize(
    "fragment",
    [
        "smoke_gates:\n  after_wave: 1\n  command: \"\"\n",
        "smoke_gates:\n  after_wave: \"sometimes\"\n  command: pytest\n",
        "smoke_gates:\n  after_wave: 1\n",
    ],
    ids=["empty-command", "after-wave-invalid-string", "no-command"],
)
def test_smoke_gates_block_that_cannot_be_read_is_skipped(
    tmp_path: Path, fragment: str
) -> None:
    feature = _load(tmp_path, fragment)
    assert feature.smoke_gates is None
    assert [t.id for t in feature.tasks] == ["TASK-T1", "TASK-T2"]


# ---------------------------------------------------------------------------
# Valid smoke_gates shapes load correctly
# ---------------------------------------------------------------------------


def test_smoke_gates_after_wave_int(tmp_path: Path) -> None:
    """``after_wave: 1`` loads as an int."""
    features_dir = tmp_path / ".guardkit" / "features"
    # TASK-FPSG-005: pre-flight validates pytest positionals exist under
    # repo_root, so the feature file must really be on disk for this
    # int-handling test to load cleanly.
    feature_dir = tmp_path / "features"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "FEAT-TEST.feature").touch()
    body = _BASE_FEATURE + textwrap.dedent(
        """
        smoke_gates:
          after_wave: 1
          command: pytest features/FEAT-TEST.feature
        """
    )
    _write_feature_yaml(features_dir, "FEAT-TEST", body)

    feature = FeatureLoader.load_feature(
        "FEAT-TEST", repo_root=tmp_path, features_dir=features_dir
    )

    assert isinstance(feature.smoke_gates, SmokeGates)
    assert feature.smoke_gates.after_wave == 1
    assert feature.smoke_gates.command == "pytest features/FEAT-TEST.feature"
    assert feature.smoke_gates.expected_exit == 0
    assert feature.smoke_gates.timeout == 120  # default


def test_smoke_gates_after_wave_all(tmp_path: Path) -> None:
    """``after_wave: all`` loads as the literal string."""
    features_dir = tmp_path / ".guardkit" / "features"
    body = _BASE_FEATURE + textwrap.dedent(
        """
        smoke_gates:
          after_wave: all
          command: make smoke
          expected_exit: 0
          timeout: 60
        """
    )
    _write_feature_yaml(features_dir, "FEAT-TEST", body)

    feature = FeatureLoader.load_feature(
        "FEAT-TEST", repo_root=tmp_path, features_dir=features_dir
    )
    assert feature.smoke_gates is not None
    assert feature.smoke_gates.after_wave == "all"
    assert feature.smoke_gates.timeout == 60


def test_smoke_gates_after_wave_list(tmp_path: Path) -> None:
    """``after_wave: [1, 3]`` loads as a list of ints."""
    features_dir = tmp_path / ".guardkit" / "features"
    body = _BASE_FEATURE + textwrap.dedent(
        """
        smoke_gates:
          after_wave: [1, 3]
          command: scripts/smoke.sh
        """
    )
    _write_feature_yaml(features_dir, "FEAT-TEST", body)

    feature = FeatureLoader.load_feature(
        "FEAT-TEST", repo_root=tmp_path, features_dir=features_dir
    )
    assert feature.smoke_gates is not None
    assert feature.smoke_gates.after_wave == [1, 3]
