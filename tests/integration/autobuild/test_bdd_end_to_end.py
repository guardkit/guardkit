"""End-to-end integration tests for the BDD oracle (TASK-BDD-E8954).

Coverage Target: AC for TASK-BDD-E8954

Drives the full task-work writer + Coach validator path with a stubbed
pytest-bdd subprocess. Verifies that:

- A demo feature with one failing scenario produces specific bdd_results
  feedback when Coach validates the task.
- A task with no matching .feature file behaves identically to today
  (Coach approves without any bdd_results-related feedback).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unittest.mock import MagicMock, patch

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates import CoachValidator
from guardkit.orchestrator.quality_gates import bdd_runner
from guardkit.orchestrator.quality_gates.bdd_runner import (
    BDDResult,
    FailureDetail,
    PendingDetail,
)


_FAILING_FEATURE = """\
Feature: Login

  @task:TASK-001
  Scenario: User logs in with broken implementation
    Given a valid user
    When the user logs in
    Then the user is greeted
"""


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    (tmp_path / "features").mkdir()
    return tmp_path


def _write_feature(worktree: Path, name: str, body: str) -> Path:
    fp = worktree / "features" / name
    fp.write_text(body, encoding="utf-8")
    return fp


def _make_passing_results_data() -> dict:
    return {
        "tests_passed": 12,
        "tests_failed": 0,
        "coverage": 85.0,
        "quality_gates_passed": True,
        "files_modified": [],
        "files_created": [],
        "phases": {},
        "architectural_review": {"score": 82, "solid": 85, "dry": 80, "yagni": 82},
    }


_ACCEPTANCE = [
    "OAuth2 authentication flow",
    "Token generation",
    "Token refresh",
]


def _inject_requirements_met(results_file: Path) -> None:
    """Top up the file with requirements_met after the writer runs.

    The writer leaves requirements_met to the player report path; for these
    integration tests we want the requirements gate to pass so that the BDD
    gate (downstream) is actually exercised.
    """
    payload = json.loads(results_file.read_text())
    payload["requirements_met"] = list(_ACCEPTANCE)
    results_file.write_text(json.dumps(payload, indent=2))


def _make_invoker(worktree: Path) -> AgentInvoker:
    return AgentInvoker(worktree_path=worktree, max_turns_per_agent=5, sdk_timeout_seconds=60)


def test_feature_file_with_failing_scenario_causes_coach_feedback(worktree: Path, monkeypatch):
    """AC: feature file with one failing scenario → Coach rejects with bdd_results feedback."""
    _write_feature(worktree, "login.feature", _FAILING_FEATURE)

    # Stub the runner to return one failure (simulates a real assertion failure
    # without spawning pytest-bdd).
    fake_result = BDDResult(
        scenarios_passed=0,
        scenarios_failed=1,
        scenarios_pending=0,
        failures=[
            FailureDetail(
                feature_file="features/login.feature",
                scenario_name="User logs in with broken implementation",
                failing_step="Then the user is greeted",
                reason="AssertionError: assert 'Welcome' in 'Goodbye'",
            )
        ],
        pending=[],
        feature_files=["features/login.feature"],
        tag="@task:TASK-001",
    )
    monkeypatch.setattr(bdd_runner, "run_bdd_for_task", lambda *a, **k: fake_result)

    # 1. Player writes task_work_results.json (with bdd_results embedded).
    invoker = _make_invoker(worktree)
    results_file = invoker._write_task_work_results("TASK-001", _make_passing_results_data())
    _inject_requirements_met(results_file)
    payload = json.loads(results_file.read_text())
    assert payload["bdd_results"]["scenarios_failed"] == 1

    # 2. Coach reads the same file and rejects on the BDD gate.
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="15 passed in 1.45s",
            stderr="",
        )
        validator = CoachValidator(str(worktree))
        decision = validator.validate(
            "TASK-001",
            turn=1,
            task={"acceptance_criteria": list(_ACCEPTANCE)},
        )

    assert decision.decision == "feedback"
    bdd_issues = [i for i in decision.issues if i.get("category") == "bdd_failure"]
    assert len(bdd_issues) == 1
    issue = bdd_issues[0]
    assert issue["scenarios_failed"] == 1
    assert issue["feature_files"] == ["features/login.feature"]
    # Specific failure detail surfaces in the feedback.
    assert any(
        "User logs in with broken implementation" in summary
        for summary in issue["failure_examples"]
    )


def test_no_feature_file_behaves_as_today(worktree: Path, monkeypatch):
    """AC: task without matching .feature file behaves identically to today."""
    # No .feature file written → bdd_runner returns None → no bdd_results key.
    # We do NOT patch run_bdd_for_task; the real implementation must early-exit.

    invoker = _make_invoker(worktree)
    results_file = invoker._write_task_work_results("TASK-001", _make_passing_results_data())
    _inject_requirements_met(results_file)
    payload = json.loads(results_file.read_text())
    assert "bdd_results" not in payload

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="15 passed in 1.45s",
            stderr="",
        )
        validator = CoachValidator(str(worktree))
        decision = validator.validate(
            "TASK-001",
            turn=1,
            task={"acceptance_criteria": list(_ACCEPTANCE)},
        )

    assert decision.decision == "approve"
    bdd_issues = [
        i for i in decision.issues
        if i.get("category", "").startswith("bdd_")
    ]
    assert bdd_issues == []
