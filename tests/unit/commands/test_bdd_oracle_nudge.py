"""Tests for installer/core/commands/lib/bdd_oracle_nudge.py (TASK-FP-NDG1).

Covers the three AC branches:
- Notice fires when features/*.feature exists with zero @task: tags.
- Notice does not fire when file has at least one @task: tag.
- Notice does not fire when no features/*.feature exists.

Plus:
- Suppression via quiet=True.
- Partial activation (one tagged, one untagged) is not flagged.
"""

from pathlib import Path

import pytest

from installer.core.commands.lib.bdd_oracle_nudge import (
    check_bdd_oracle_activation,
)


_UNTAGGED_FEATURE = """Feature: Sign in

  Scenario: User signs in with valid credentials
    Given a registered user
    When they submit correct credentials
    Then a session is created
"""

_TAGGED_FEATURE = """Feature: Sign in

  @key-example @task:TASK-XXX-001
  Scenario: User signs in with valid credentials
    Given a registered user
    When they submit correct credentials
    Then a session is created
"""


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Bare project root without a features/ directory."""
    return tmp_path


def _write_feature(project_root: Path, name: str, body: str) -> Path:
    features_dir = project_root / "features"
    features_dir.mkdir(exist_ok=True)
    feature_path = features_dir / name
    feature_path.write_text(body, encoding="utf-8")
    return feature_path


# ---------------------------------------------------------------------------
# Branch 1: no features/*.feature -> None
# ---------------------------------------------------------------------------


def test_returns_none_when_no_features_dir(project_root: Path) -> None:
    assert check_bdd_oracle_activation(project_root) is None


def test_returns_none_when_features_dir_is_empty(project_root: Path) -> None:
    (project_root / "features").mkdir()
    assert check_bdd_oracle_activation(project_root) is None


def test_returns_none_when_features_dir_has_no_feature_files(
    project_root: Path,
) -> None:
    features_dir = project_root / "features"
    features_dir.mkdir()
    (features_dir / "README.md").write_text("not a feature", encoding="utf-8")
    assert check_bdd_oracle_activation(project_root) is None


# ---------------------------------------------------------------------------
# Branch 2: .feature file with @task: tag -> None
# ---------------------------------------------------------------------------


def test_returns_none_when_feature_has_task_tag(project_root: Path) -> None:
    _write_feature(project_root, "sign_in.feature", _TAGGED_FEATURE)
    assert check_bdd_oracle_activation(project_root) is None


def test_returns_none_when_partial_activation(project_root: Path) -> None:
    # Partial activation (some tagged, some not) is intentionally OK — the
    # user is mid-tagging; don't spam further advice.
    _write_feature(project_root, "tagged.feature", _TAGGED_FEATURE)
    _write_feature(project_root, "untagged.feature", _UNTAGGED_FEATURE)
    assert check_bdd_oracle_activation(project_root) is None


# ---------------------------------------------------------------------------
# Branch 3: .feature file(s) exist, none tagged -> notice
# ---------------------------------------------------------------------------


def test_returns_notice_when_feature_missing_task_tag(project_root: Path) -> None:
    _write_feature(project_root, "sign_in.feature", _UNTAGGED_FEATURE)
    result = check_bdd_oracle_activation(project_root)

    assert result is not None
    assert "BDD oracle (R2) not activated" in result
    assert "@task:<TASK-ID>" in result
    assert "feature-spec.md" in result  # canonical docs pointer
    assert "@task:TASK-XXX-001" in result  # copy-pasteable example


def test_returns_notice_when_multiple_untagged_features(project_root: Path) -> None:
    _write_feature(project_root, "a.feature", _UNTAGGED_FEATURE)
    _write_feature(project_root, "b.feature", _UNTAGGED_FEATURE)
    assert check_bdd_oracle_activation(project_root) is not None


# ---------------------------------------------------------------------------
# Quiet suppression (AC: "suppressible via --no-questions or equivalent")
# ---------------------------------------------------------------------------


def test_quiet_suppresses_notice_when_would_fire(project_root: Path) -> None:
    _write_feature(project_root, "sign_in.feature", _UNTAGGED_FEATURE)
    assert check_bdd_oracle_activation(project_root, quiet=True) is None


def test_quiet_is_noop_when_no_features(project_root: Path) -> None:
    assert check_bdd_oracle_activation(project_root, quiet=True) is None
