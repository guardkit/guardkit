"""Scope-boundary tests for the task-level BDD oracle (TASK-BDD-E8954).

The runner is intentionally task-scoped. A whole-feature ``.feature`` file
that contains no ``@task:<TASK-ID>`` tag belongs to feature-level smoke
(TASK-SMK-F703A territory) and MUST NOT be picked up by R2.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import bdd_runner
from guardkit.orchestrator.quality_gates.bdd_runner import run_bdd_for_task


_FEATURE_LEVEL_NO_TAGS = """\
Feature: Whole-feature smoke

  Scenario: Visit homepage
    Given the app is up
    When the user visits the homepage
    Then they see the marketing copy

  Scenario: Visit pricing
    Given the app is up
    When the user visits pricing
    Then prices are listed
"""


_DIFFERENT_TASK_TAG = """\
Feature: Belongs to a different task

  @task:TASK-OTHER
  Scenario: Other task scenario
    Given some other context
    When something happens
    Then a different outcome
"""


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    (tmp_path / "features").mkdir()
    return tmp_path


def _write_feature(worktree: Path, name: str, body: str) -> Path:
    fp = worktree / "features" / name
    fp.write_text(body, encoding="utf-8")
    return fp


def test_feature_level_feature_not_run_by_bdd_runner(worktree: Path, monkeypatch):
    """AC: untagged whole-feature .feature is not picked up by R2."""
    _write_feature(worktree, "homepage.feature", _FEATURE_LEVEL_NO_TAGS)

    # Ensure pytest_bdd availability is irrelevant for this guard — discovery
    # must early-exit on tag absence regardless.
    monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
    invocations: list = []

    def spy(*args, **kwargs):
        invocations.append((args, kwargs))
        raise AssertionError("subprocess MUST NOT be invoked when no tags match")

    monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", spy)

    result = run_bdd_for_task("TASK-001", worktree)

    assert result is None
    assert invocations == []  # no subprocess call → no whole-feature run


def test_feature_with_other_task_tag_not_run(worktree: Path, monkeypatch):
    """A .feature tagged for a *different* task must not trigger this task's runner."""
    _write_feature(worktree, "other.feature", _DIFFERENT_TASK_TAG)

    monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
    invocations: list = []

    def spy(*args, **kwargs):
        invocations.append((args, kwargs))
        raise AssertionError("subprocess MUST NOT be invoked for foreign tags")

    monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", spy)

    result = run_bdd_for_task("TASK-001", worktree)

    assert result is None
    assert invocations == []
