"""Tests for env-level BDD preflight in feature_validator (TASK-FIX-BDDM-2).

Coverage Target: >=90% (line + branch) on validate_feature_environment.

The function is a thin shell over bdd_runner's discovery and probe helpers.
We patch ``has_pytest_bdd`` (the only import-time side effect) and write
real ``.feature`` files into a tmp ``features/`` tree so the discovery half
exercises real code, while keeping the env probe deterministic.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pytest

from guardkit.orchestrator import feature_validator
from guardkit.orchestrator.feature_validator import (
    PreFlightValidationResult,
    validate_feature_environment,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureOrchestration,
    FeatureTask,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(task_id: str, file_path: str = "tasks/backlog/x.md") -> FeatureTask:
    return FeatureTask(
        id=task_id,
        name=task_id,
        file_path=Path(file_path),
        complexity=5,
    )


def _make_feature(tasks: List[FeatureTask]) -> Feature:
    return Feature(
        id="FEAT-BDDM",
        name="Test Feature",
        description="env preflight tests",
        tasks=tasks,
        orchestration=FeatureOrchestration(
            parallel_groups=[[t.id for t in tasks]],
        ),
    )


def _write_feature_file(repo_root: Path, name: str, body: str) -> Path:
    features_dir = repo_root / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    fp = features_dir / name
    fp.write_text(body, encoding="utf-8")
    return fp


def _patch_pytest_bdd(monkeypatch: pytest.MonkeyPatch, present: bool) -> List[Optional[str]]:
    """Patch ``bdd_runner.has_pytest_bdd`` and capture the executable arg.

    Returns the captured-arg list so tests can assert that the env probe
    was either invoked (with the expected interpreter path) or skipped.
    """
    captured: List[Optional[str]] = []

    def _fake_has_pytest_bdd(python_executable: Optional[str] = None) -> bool:
        captured.append(python_executable)
        return present

    from guardkit.orchestrator.quality_gates import bdd_runner

    monkeypatch.setattr(bdd_runner, "has_pytest_bdd", _fake_has_pytest_bdd)
    return captured


_TAGGED_FEATURE_TEMPLATE = """\
Feature: Sample

  @task:{task_id}
  Scenario: Sample scenario
    Given a valid setup
    When the user does something
    Then a result is observed
"""


_UNTAGGED_FEATURE = """\
Feature: Whole-feature smoke

  Scenario: Visit homepage
    Given the app is up
    When the user visits the homepage
    Then they see the marketing copy
"""


# ---------------------------------------------------------------------------
# Required AC tests
# ---------------------------------------------------------------------------


class TestNoTaggedScenariosSkipsPreflight:
    """AC1: feature with no @task: tags — no issue raised."""

    def test_no_tagged_scenarios_skips_preflight(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # Two real .feature files, neither tagged with @task:TASK-001.
        _write_feature_file(tmp_path, "homepage.feature", _UNTAGGED_FEATURE)
        _write_feature_file(
            tmp_path,
            "other.feature",
            _TAGGED_FEATURE_TEMPLATE.format(task_id="TASK-OTHER-002"),
        )
        feature = _make_feature([_make_task("TASK-001"), _make_task("TASK-002")])
        captured = _patch_pytest_bdd(monkeypatch, present=False)

        result = validate_feature_environment(feature, tmp_path)

        assert isinstance(result, PreFlightValidationResult)
        assert result.is_valid
        assert not result.has_errors
        assert not result.has_warnings
        # Lazy probe: no tagged file matches — has_pytest_bdd must NOT run.
        assert captured == []


class TestTaggedScenariosWithPytestBddPresentSkipsPreflight:
    """AC2: pytest-bdd present — tagged scenarios produce no issue."""

    def test_tagged_scenarios_with_pytest_bdd_present_skips_preflight(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        _write_feature_file(
            tmp_path,
            "login.feature",
            _TAGGED_FEATURE_TEMPLATE.format(task_id="TASK-001"),
        )
        feature = _make_feature([_make_task("TASK-001")])
        captured = _patch_pytest_bdd(monkeypatch, present=True)

        result = validate_feature_environment(feature, tmp_path)

        assert result.is_valid
        assert not result.has_errors
        # Probe ran exactly once (lazy probe), with default interpreter (None).
        assert captured == [None]


class TestTaggedScenariosWithoutPytestBddRaisesError:
    """AC3: the failing case from TASK-REV-BDDM — error emitted."""

    def test_tagged_scenarios_without_pytest_bdd_raises_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        _write_feature_file(
            tmp_path,
            "login.feature",
            _TAGGED_FEATURE_TEMPLATE.format(task_id="TASK-001"),
        )
        _write_feature_file(
            tmp_path,
            "signup.feature",
            _TAGGED_FEATURE_TEMPLATE.format(task_id="TASK-002"),
        )
        feature = _make_feature([_make_task("TASK-001"), _make_task("TASK-002")])
        captured = _patch_pytest_bdd(monkeypatch, present=False)

        result = validate_feature_environment(feature, tmp_path)

        assert not result.is_valid
        assert result.has_errors
        assert len(result.errors) == 1
        issue = result.errors[0]
        assert issue.severity == "error"
        assert issue.field == "environment"
        assert "TASK-001" in issue.task_id
        assert "TASK-002" in issue.task_id
        assert "pytest-bdd is not importable" in issue.message
        assert "R1" in issue.message  # cross-references TASK-FIX-BDDM-1
        # Lazy probe ran once even though two tasks matched.
        assert captured == [None]


class TestPreflightReportsSpecificPyprojectPathInSuggestion:
    """AC4: error suggestion mentions the actual pyproject path."""

    def test_preflight_reports_specific_pyproject_path_in_suggestion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        _write_feature_file(
            tmp_path,
            "login.feature",
            _TAGGED_FEATURE_TEMPLATE.format(task_id="TASK-001"),
        )
        feature = _make_feature([_make_task("TASK-001")])
        _patch_pytest_bdd(monkeypatch, present=False)

        result = validate_feature_environment(feature, tmp_path)

        assert result.has_errors
        suggestion = result.errors[0].suggestion or ""
        assert "pytest-bdd>=8.1,<9" in suggestion
        # The suggestion must name the actual pyproject path tied to the
        # repo root, not a hardcoded placeholder.
        expected_path = f"{tmp_path}/pyproject.toml"
        assert expected_path in suggestion


# ---------------------------------------------------------------------------
# Branch coverage / regression-safety
# ---------------------------------------------------------------------------


class TestEnvironmentPreflightEdgeCases:
    """Edge cases that round out branch coverage on the new function."""

    def test_no_features_dir_skips_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # No features/ directory exists — function returns immediately.
        feature = _make_feature([_make_task("TASK-001")])
        captured = _patch_pytest_bdd(monkeypatch, present=False)

        result = validate_feature_environment(feature, tmp_path)

        assert result.is_valid
        assert not result.has_errors
        assert captured == []  # never probed

    def test_truncates_affected_task_list_at_five(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # Six tasks, all tagged → display truncates to first five plus "...".
        tasks = [_make_task(f"TASK-{i:03d}") for i in range(1, 7)]
        for t in tasks:
            _write_feature_file(
                tmp_path,
                f"{t.id.lower()}.feature",
                _TAGGED_FEATURE_TEMPLATE.format(task_id=t.id),
            )
        feature = _make_feature(tasks)
        _patch_pytest_bdd(monkeypatch, present=False)

        result = validate_feature_environment(feature, tmp_path)

        assert result.has_errors
        displayed = result.errors[0].task_id
        # First five appear, the sixth is collapsed into "..."
        assert "TASK-001" in displayed
        assert "TASK-005" in displayed
        assert "TASK-006" not in displayed
        assert "..." in displayed
        assert "6 task(s)" in result.errors[0].message

    def test_passes_worktree_python_to_probe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # Custom interpreter path is forwarded verbatim to has_pytest_bdd.
        _write_feature_file(
            tmp_path,
            "login.feature",
            _TAGGED_FEATURE_TEMPLATE.format(task_id="TASK-001"),
        )
        feature = _make_feature([_make_task("TASK-001")])
        captured = _patch_pytest_bdd(monkeypatch, present=True)

        validate_feature_environment(
            feature, tmp_path, worktree_python="/opt/wt/bin/python"
        )

        assert captured == ["/opt/wt/bin/python"]


# ---------------------------------------------------------------------------
# Wiring smoke: name is exported and callable from the public module surface
# ---------------------------------------------------------------------------


def test_validate_feature_environment_is_module_attribute():
    """Light sanity check: the function lives at the documented import path."""
    assert callable(getattr(feature_validator, "validate_feature_environment", None))
