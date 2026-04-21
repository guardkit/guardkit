"""Schema tests for the optional ``smoke_gates`` key on FEAT-*.yaml.

Covers TASK-SMK-F703A acceptance criteria:
- feature YAML without ``smoke_gates`` loads unchanged
- malformed ``smoke_gates`` raises ``SchemaValidationError`` before
  ``/feature-build`` starts
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureParseError,
    SchemaValidationError,
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
# AC: malformed smoke_gates raises SchemaValidationError
# ---------------------------------------------------------------------------


_MALFORMED_CASES = [
    pytest.param(
        """
        smoke_gates:
          after_wave: -1
          command: pytest
        """,
        id="negative-after-wave",
    ),
    pytest.param(
        """
        smoke_gates:
          after_wave: 1
          command: ""
        """,
        id="empty-command",
    ),
    pytest.param(
        """
        smoke_gates:
          after_wave: 1
          command: pytest
          timeout: 0
        """,
        id="timeout-below-floor",
    ),
    pytest.param(
        """
        smoke_gates:
          after_wave: 1
          command: pytest
          timeout: 700
        """,
        id="timeout-above-cap",
    ),
    pytest.param(
        """
        smoke_gates:
          after_wave: "sometimes"
          command: pytest
        """,
        id="after-wave-invalid-string",
    ),
    pytest.param(
        """
        smoke_gates:
          after_wave: []
          command: pytest
        """,
        id="after-wave-empty-list",
    ),
    pytest.param(
        """
        smoke_gates:
          after_wave: 1
          command: pytest
          unknown_key: oops
        """,
        id="unknown-key-forbidden",
    ),
]


@pytest.mark.parametrize("yaml_fragment", _MALFORMED_CASES)
def test_smoke_gates_malformed_raises(tmp_path: Path, yaml_fragment: str) -> None:
    """Malformed smoke_gates raises SchemaValidationError before /feature-build."""
    features_dir = tmp_path / ".guardkit" / "features"
    body = _BASE_FEATURE + textwrap.dedent(yaml_fragment)
    _write_feature_yaml(features_dir, "FEAT-TEST", body)

    with pytest.raises(SchemaValidationError):
        FeatureLoader.load_feature(
            "FEAT-TEST", repo_root=tmp_path, features_dir=features_dir
        )


def test_schema_validation_error_is_feature_parse_error() -> None:
    """SchemaValidationError must be a FeatureParseError subclass.

    Existing code that catches FeatureParseError (the broader schema-parse
    exception) should continue to work unchanged when smoke_gates validation
    fails. Otherwise the failure escapes the existing error-handling layer.
    """
    assert issubclass(SchemaValidationError, FeatureParseError)


# ---------------------------------------------------------------------------
# Valid smoke_gates shapes load correctly
# ---------------------------------------------------------------------------


def test_smoke_gates_after_wave_int(tmp_path: Path) -> None:
    """``after_wave: 1`` loads as an int."""
    features_dir = tmp_path / ".guardkit" / "features"
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
