"""TASK-ABFIX-012 — gather_evidence populates independent_test_classification.

The LIVE Coach path is ``gather_evidence`` → ``CoachEvidenceBundle`` → deterministic
guards in ``AgentInvoker`` (NOT the legacy ``validate()``). This test pins that the
substrate-vs-code verdict is COMPUTED in ``gather_evidence`` and carried on the
bundle, ONLY for a RAN-AND-FAILED independent test run — never for a passing run and
never for an ABSENT signal (an absent signal must never manufacture a code verdict;
``.claude/rules/absence-of-failure-is-not-success.md``).

Mirrors the worktree fixture of ``test_coach_evidence_bundle.py``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


@pytest.fixture(autouse=True)
def _pin_sdk_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")


def _init_git_worktree(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t"], check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "t"], check=True, capture_output=True,
    )


def _passing_results() -> dict:
    return {
        "task_id": "TASK-FMDR-004",
        "quality_gates": {
            "all_passed": True,
            "tests_run": 9,
            "tests_passed": 9,
            "tests_failed": 0,
            "coverage_met": True,
            "line_coverage": 0.85,
            "branch_coverage": 0.78,
        },
        "code_review": {"score": 80, "solid_score": 85, "dry_score": 78, "yagni_score": 82},
        "plan_audit": {"status": "passed", "violations": 0, "severity": "low"},
        "files_modified": [],
        "files_created": [],
        # Empty so the honesty verifier has no claimed-but-absent file to flag —
        # the independent test run is patched, so no real test file is needed.
        "tests_written": [],
    }


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    _init_git_worktree(tmp_path)
    results_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-FMDR-004"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(json.dumps(_passing_results()))
    return tmp_path


_TESTING_TASK = {
    "acceptance_criteria": ["AC-001 the runbook tests pass"],
    "task_type": "testing",
    "description": "add runbook status tests",
}

_CODE_FAIL_OUTPUT = (
    "FAILED tests/test_runbook.py::test_status\n"
    "E   AttributeError: 'RunbookStore' object has no attribute 'get_runbook_by_id'\n"
    "5 failed, 4 passed in 0.42s"
)


def _failed(signal_absent: bool = False, output: str = _CODE_FAIL_OUTPUT) -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=False,
        test_command="pytest tests/test_runbook.py -v",
        test_output_summary=output[:200],
        duration_seconds=0.42,
        raw_output=output,
        signal_absent=signal_absent,
    )


def _passed() -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=True,
        test_command="pytest tests/test_runbook.py -v",
        test_output_summary="9 passed",
        duration_seconds=0.4,
        raw_output="9 passed in 0.4s",
        signal_absent=False,
    )


def test_classification_populated_for_ran_and_failed(worktree: Path) -> None:
    """A TESTING task whose independent run RAN and FAILED gets a ('code', ...) verdict."""
    validator = CoachValidator(str(worktree), task_id="TASK-FMDR-004")
    with patch.object(CoachValidator, "run_independent_tests", return_value=_failed()):
        bundle = validator.gather_evidence(task_id="TASK-FMDR-004", turn=1, task=_TESTING_TASK)
    assert bundle.gathering_status == "complete"
    assert bundle.independent_test_classification is not None
    assert bundle.independent_test_classification.failure_class == "code"
    # The verdict reaches coach_turn_N.json verbatim (the bundle is serialised).
    assert bundle.to_dict()["independent_test_classification"]["failure_class"] == "code"


def test_classification_none_when_absent_signal(worktree: Path) -> None:
    """An ABSENT independent signal must NOT manufacture a code verdict."""
    validator = CoachValidator(str(worktree), task_id="TASK-FMDR-004")
    with patch.object(
        CoachValidator, "run_independent_tests",
        return_value=_failed(signal_absent=True, output="psql: command not found"),
    ):
        bundle = validator.gather_evidence(task_id="TASK-FMDR-004", turn=1, task=_TESTING_TASK)
    assert bundle.independent_test_classification is None


def test_classification_none_when_tests_passed(worktree: Path) -> None:
    validator = CoachValidator(str(worktree), task_id="TASK-FMDR-004")
    with patch.object(CoachValidator, "run_independent_tests", return_value=_passed()):
        bundle = validator.gather_evidence(task_id="TASK-FMDR-004", turn=1, task=_TESTING_TASK)
    assert bundle.independent_test_classification is None
