"""CoachValidator.gather_evidence returns a populated CoachEvidenceBundle.

Since the cull of 27 October 2026 the bundle carries only the project's own
check results (independent tests, runtime parity, the whole-feature check,
the secrets check, the behavioural oracle and a failure classification of a
red run). These tests pin the shape and the never-raise contract:

* A passing-turn fixture yields ``gathering_status == "complete"`` and a
  JSON-serialisable bundle carrying the resolved task type and profile.
* Missing task-work results are treated as ``{}``: the project's checks
  still run and the bundle is complete.
* An unknown task type uses the feature profile.
* An exception while running the project's tests produces
  ``gathering_status == "partial_exception"`` with a populated
  ``gathering_error`` rather than raising to the caller.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
    GatheringStatus,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _init_git_worktree(path: Path) -> None:
    """Minimal git init so the validator can construct without raising."""
    subprocess.run(
        ["git", "init", "-q"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t"], check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "t"], check=True, capture_output=True,
    )


def _passing_task_work_results() -> dict:
    """Return a task_work_results dict where every gate passes."""
    return {
        "task_id": "TASK-X",
        "quality_gates": {
            "all_passed": True,
            "tests_run": 12,
            "tests_failed": 0,
        },
        "files_modified": [],
        "files_created": [],
        "tests_written": [],
    }


def _write_results(worktree: Path, task_id: str, results: dict) -> None:
    results_dir = worktree / ".guardkit" / "autobuild" / task_id
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(json.dumps(results))


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A git worktree with a passing-turn fixture written."""
    _init_git_worktree(tmp_path)
    _write_results(tmp_path, "TASK-X", _passing_task_work_results())
    return tmp_path


def _gather(worktree: Path, task_id: str = "TASK-X", **task_fields) -> CoachEvidenceBundle:
    task = {
        "acceptance_criteria": ["AC-001"],
        "task_type": "feature",
        "description": "x",
    }
    task.update(task_fields)
    validator = CoachValidator(str(worktree), task_id=task_id)
    return validator.gather_evidence(task_id=task_id, turn=1, task=task)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestGatherEvidenceHappyPath:
    def test_returns_coach_evidence_bundle(self, worktree: Path) -> None:
        assert isinstance(_gather(worktree), CoachEvidenceBundle)

    def test_gathering_status_complete_for_passing_turn(self, worktree: Path) -> None:
        bundle = _gather(worktree)
        assert bundle.gathering_status == "complete"
        assert bundle.gathering_error is None

    def test_task_type_and_profile_populated(self, worktree: Path) -> None:
        bundle = _gather(worktree)
        assert bundle.task_type == "feature"
        assert bundle.profile_name is not None

    def test_the_project_tests_were_looked_for(self, worktree: Path) -> None:
        """A feature task requires tests, so the independent run happened
        (here it finds nothing to run) and its result is on the bundle."""
        bundle = _gather(worktree)
        assert bundle.independent_tests is not None

    def test_bundle_is_json_serialisable(self, worktree: Path) -> None:
        """The bundle is rendered into the Coach prompt as JSON."""
        bundle = _gather(worktree)
        payload = json.dumps(bundle.to_dict(), default=str)
        assert '"gathering_status":' in payload
        assert '"independent_tests":' in payload
        assert '"behavioural_oracle":' in payload


# ---------------------------------------------------------------------------
# gather_evidence MUST NOT raise
# ---------------------------------------------------------------------------


class TestGatherEvidenceNeverRaises:
    def test_missing_results_are_treated_as_empty(self, tmp_path: Path) -> None:
        _init_git_worktree(tmp_path)
        # No task_work_results.json written.
        bundle = _gather(tmp_path, task_id="TASK-MISSING")
        assert bundle.gathering_status == "complete"
        assert bundle.gathering_error is None
        assert bundle.independent_tests is not None

    def test_unknown_task_type_uses_the_feature_profile(self, tmp_path: Path) -> None:
        _init_git_worktree(tmp_path)
        bundle = _gather(tmp_path, task_id="TASK-Y", task_type="not_a_real_task_type")
        assert bundle.gathering_status == "complete"
        assert bundle.task_type == "feature"

    def test_a_raising_test_run_returns_partial_exception(self, worktree: Path) -> None:
        with patch.object(
            CoachValidator,
            "run_independent_tests",
            side_effect=RuntimeError("runner exploded"),
        ):
            bundle = _gather(worktree)
        assert bundle.gathering_status == "partial_exception"
        assert "runner exploded" in (bundle.gathering_error or "")
        # Recorded as "the check could not run", so the task stops instead
        # of being approved untested (1 November 2026; it was None).
        assert bundle.independent_tests.check_could_not_run is True
        assert "runner exploded" in bundle.independent_tests.check_could_not_run_detail

    def test_operator_handoff_runs_the_check_like_any_task(self, tmp_path: Path) -> None:
        """Operator-handoff tasks no longer skip the check (1 November 2026):
        here nothing is declared, so it says the check could not run."""
        _init_git_worktree(tmp_path)
        bundle = _gather(
            tmp_path,
            task_id="TASK-OPS",
            task_type="operator_handoff",
            acceptance_criteria=["operator runs X"],
        )
        assert bundle.gathering_status == "complete"
        assert bundle.task_type == "operator_handoff"
        assert bundle.independent_tests.check_could_not_run is True
        assert "nothing declared" in bundle.independent_tests.check_could_not_run_detail
        assert bundle.behavioural_oracle is None


# ---------------------------------------------------------------------------
# Type / API surface checks
# ---------------------------------------------------------------------------


class TestBundleTypeSurface:
    """Structural assertions that protect against silent schema drift."""

    def test_fields(self) -> None:
        from dataclasses import fields

        names = {f.name for f in fields(CoachEvidenceBundle)}
        assert names == {
            "gathering_status",
            "gathering_error",
            "independent_tests",
            "independent_test_classification",
            "behavioural_oracle",
            "runtime_parity",
            "security_check",
            "whole_feature_check",
            "evidence_repo_tests",
            "task_type",
            "profile_name",
        }

    def test_gathering_status_literal_values(self) -> None:
        assert GatheringStatus.__args__ == ("complete", "partial_exception")
