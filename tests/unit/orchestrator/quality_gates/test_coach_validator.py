"""CoachValidator BDD oracle gate tests (TASK-BDD-E8954).

Validates Coach behaviour for the ``bdd_results`` gate added in
TASK-BDD-E8954. The gate enforces the three-state model from the task spec:

- ``scenarios_failed > 0``  → reject (must_fix ``bdd_failure``)
- ``scenarios_pending > 0`` → approve **with feedback** (should_fix
                              ``bdd_pending``); MUST NOT block on pending alone
- ``bdd_results`` absent    → no gate active (back-compat: identical to today)

The broader CoachValidator test suite remains in
``tests/unit/test_coach_validator.py``. This file exists at the path named
in the AC for direct discoverability.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator
from guardkit.orchestrator.quality_gates.coach_validator import IndependentTestResult


# ---------------------------------------------------------------------------
# Fixtures (mirror those from the broader CoachValidator suite — copied here
# to keep this file self-contained per AC: it must be runnable in isolation)
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_worktree(tmp_path):
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree):
    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
    results_dir.mkdir(parents=True)
    return results_dir


def _make_task_work_results(bdd_block: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A passing baseline task_work_results, optionally with bdd_results attached."""
    results: Dict[str, Any] = {
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": 15,
            "tests_failed": 0,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": True,
        },
        "code_review": {"score": 82, "solid": 85, "dry": 80, "yagni": 82},
        "plan_audit": {"violations": 0, "file_count_match": True},
        "requirements_met": [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
    }
    if bdd_block is not None:
        results["bdd_results"] = bdd_block
    return results


def _make_task() -> Dict[str, Any]:
    return {
        "acceptance_criteria": [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
    }


def _write(results_dir: Path, results: Dict[str, Any]) -> Path:
    results_path = results_dir / "task_work_results.json"
    results_path.write_text(json.dumps(results, indent=2))
    return results_path


# ---------------------------------------------------------------------------
# AC tests — names match those listed in TASK-BDD-E8954 acceptance criteria
# ---------------------------------------------------------------------------


def test_bdd_failure_rejects(tmp_worktree, task_work_results_dir):
    """AC: Coach rejects when ``bdd_results.scenarios_failed > 0``."""
    _write(
        task_work_results_dir,
        _make_task_work_results({
            "scenarios_passed": 1,
            "scenarios_failed": 1,
            "scenarios_pending": 0,
            "failures": [
                {
                    "feature_file": "features/login.feature",
                    "scenario_name": "User logs in",
                    "failing_step": "Then the user is greeted",
                    "reason": "AssertionError: assert 'Welcome' in 'Goodbye'",
                }
            ],
            "pending": [],
            "feature_files": ["features/login.feature"],
            "tag": "@task:TASK-001",
        }),
    )

    # Independent verification passes — only the BDD gate must reject.
    # Isolate the BDD gate: the (incidental) independent-test run is routed
    # through select_harness, which under GUARDKIT_HARNESS=sdk hits the SDK
    # harness (unmockable via subprocess.run) and would derail before the BDD
    # gate. Mock it to a passing result so this test exercises ONLY the
    # bdd_results gate, harness-agnostically. The bdd_failure issue still comes
    # from the real _check_bdd_results reading the real bdd_results.
    with patch("subprocess.run") as mock_run, patch.object(
        CoachValidator,
        "run_independent_tests",
        return_value=IndependentTestResult(
            tests_passed=True,
            test_command="pytest",
            test_output_summary="15 passed in 1.45s",
            duration_seconds=1.45,
        ),
    ):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="15 passed in 1.45s",
            stderr="",
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _make_task())

    assert result.decision == "feedback"
    bdd_failure_issues = [i for i in result.issues if i.get("category") == "bdd_failure"]
    assert len(bdd_failure_issues) == 1
    assert bdd_failure_issues[0]["severity"] == "must_fix"
    assert bdd_failure_issues[0]["scenarios_failed"] == 1
    assert "BDD scenarios failed" in result.rationale


def test_bdd_pending_approves_with_feedback(tmp_worktree, task_work_results_dir):
    """AC: pending alone does NOT block; surfaces as ``should_fix`` feedback only."""
    _write(
        task_work_results_dir,
        _make_task_work_results({
            "scenarios_passed": 1,
            "scenarios_failed": 0,
            "scenarios_pending": 2,
            "failures": [],
            "pending": [
                {
                    "feature_file": "features/signup.feature",
                    "scenario_name": "User signs up",
                    "pending_step": "When the user signs up",
                },
                {
                    "feature_file": "features/signup.feature",
                    "scenario_name": "User confirms email",
                    "pending_step": "Then a confirmation email is sent",
                },
            ],
            "feature_files": ["features/signup.feature"],
            "tag": "@task:TASK-001",
        }),
    )

    # Isolate the BDD gate: the (incidental) independent-test run is routed
    # through select_harness, which under GUARDKIT_HARNESS=sdk hits the SDK
    # harness (unmockable via subprocess.run) and would derail before the BDD
    # gate. Mock it to a passing result so this test exercises ONLY the
    # bdd_results gate, harness-agnostically. The bdd_failure issue still comes
    # from the real _check_bdd_results reading the real bdd_results.
    with patch("subprocess.run") as mock_run, patch.object(
        CoachValidator,
        "run_independent_tests",
        return_value=IndependentTestResult(
            tests_passed=True,
            test_command="pytest",
            test_output_summary="15 passed in 1.45s",
            duration_seconds=1.45,
        ),
    ):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="15 passed in 1.45s",
            stderr="",
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _make_task())

    # Pending alone MUST NOT block approval.
    assert result.decision == "approve"
    # ...but pending items MUST surface in feedback as actionable work.
    bdd_pending_issues = [i for i in result.issues if i.get("category") == "bdd_pending"]
    assert len(bdd_pending_issues) == 1
    assert bdd_pending_issues[0]["severity"] == "should_fix"
    assert bdd_pending_issues[0]["scenarios_pending"] == 2


def test_bdd_results_absent_is_silent_skip(tmp_worktree, task_work_results_dir):
    """No ``bdd_results`` key → gate inactive (back-compat: identical to today)."""
    _write(task_work_results_dir, _make_task_work_results(bdd_block=None))

    # Isolate the BDD gate: the (incidental) independent-test run is routed
    # through select_harness, which under GUARDKIT_HARNESS=sdk hits the SDK
    # harness (unmockable via subprocess.run) and would derail before the BDD
    # gate. Mock it to a passing result so this test exercises ONLY the
    # bdd_results gate, harness-agnostically. The bdd_failure issue still comes
    # from the real _check_bdd_results reading the real bdd_results.
    with patch("subprocess.run") as mock_run, patch.object(
        CoachValidator,
        "run_independent_tests",
        return_value=IndependentTestResult(
            tests_passed=True,
            test_command="pytest",
            test_output_summary="15 passed in 1.45s",
            duration_seconds=1.45,
        ),
    ):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="15 passed in 1.45s",
            stderr="",
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _make_task())

    assert result.decision == "approve"
    bdd_issues = [
        i for i in result.issues if i.get("category", "").startswith("bdd_")
    ]
    assert bdd_issues == []


def test_bdd_failure_and_pending_both_surfaced(tmp_worktree, task_work_results_dir):
    """When both present: failure blocks; pending also surfaces in feedback."""
    _write(
        task_work_results_dir,
        _make_task_work_results({
            "scenarios_passed": 0,
            "scenarios_failed": 1,
            "scenarios_pending": 1,
            "failures": [
                {
                    "feature_file": "features/x.feature",
                    "scenario_name": "Real bug",
                    "failing_step": "Then something",
                    "reason": "AssertionError",
                }
            ],
            "pending": [
                {
                    "feature_file": "features/x.feature",
                    "scenario_name": "Future scenario",
                    "pending_step": "When something future",
                }
            ],
            "feature_files": ["features/x.feature"],
            "tag": "@task:TASK-001",
        }),
    )

    # Isolate the BDD gate from the harness-routed independent-test run
    # (see test_bdd_failure_rejects for the rationale).
    with patch("subprocess.run") as mock_run, patch.object(
        CoachValidator,
        "run_independent_tests",
        return_value=IndependentTestResult(
            tests_passed=True,
            test_command="pytest",
            test_output_summary="ok",
            duration_seconds=1.0,
        ),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _make_task())

    assert result.decision == "feedback"
    categories = {i.get("category") for i in result.issues}
    assert "bdd_failure" in categories
    assert "bdd_pending" in categories


# ---------------------------------------------------------------------------
# TASK-GK-CR-001 — gate-fail path must populate `requirements`
# ---------------------------------------------------------------------------


def _make_gate_fail_results(
    completion_promises: Optional[List[Dict[str, Any]]] = None,
    requirements_addressed: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Construct a task_work_results dict that forces the quality-gate
    fail short-circuit in ``CoachValidator.validate``.

    ``tests_failed=2`` and ``all_passed=False`` flip ``tests_passed=False``
    in ``QualityGateStatus``, so the gate-fail branch fires before any
    independent test verification or AC matching runs.
    """
    results: Dict[str, Any] = {
        "quality_gates": {
            "tests_passing": False,
            "tests_passed": 13,
            "tests_failed": 2,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": False,
        },
        "code_review": {"score": 82, "solid": 85, "dry": 80, "yagni": 82},
        "plan_audit": {"violations": 0, "file_count_match": True},
    }
    if completion_promises is not None:
        results["completion_promises"] = completion_promises
    if requirements_addressed is not None:
        results["requirements_addressed"] = requirements_addressed
    return results


def _six_ac_task() -> Dict[str, Any]:
    return {
        "acceptance_criteria": [
            "AC-001: User can register with email",
            "AC-002: User can log in with credentials",
            "AC-003: User can request password reset",
            "AC-004: User can update profile",
            "AC-005: User can view session history",
            "AC-006: User can sign out cleanly",
        ],
    }


def _three_ac_task() -> Dict[str, Any]:
    return {
        "acceptance_criteria": [
            "AC-001: alpha bravo charlie delta",
            "AC-002: echo foxtrot golf hotel",
            "AC-003: india juliet kilo lima",
        ],
    }


class TestFeedbackFromGatesRequirements:
    """TASK-GK-CR-001: gate-fail short-circuit must thread requirements
    through ``_feedback_from_gates`` so the autobuild stall detector can
    read ``criteria_met`` even when gates fail."""

    def test_gate_fail_with_completion_promises_populates_requirements(
        self, tmp_worktree, task_work_results_dir
    ):
        """6 ACs, 6 completion_promises all complete, gate fails:
        requirements is populated and criteria_met == 6."""
        promises = [
            {
                "criterion_id": f"AC-{i+1:03d}",
                "status": "complete",
                "evidence": f"Implemented AC-{i+1:03d}",
            }
            for i in range(6)
        ]
        _write(
            task_work_results_dir,
            _make_gate_fail_results(completion_promises=promises),
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, _six_ac_task())

        assert result.decision == "feedback"
        assert result.quality_gates is not None
        assert result.quality_gates.all_gates_passed is False
        assert result.requirements is not None
        assert result.requirements.criteria_met == 6
        assert result.requirements.criteria_total == 6

    def test_gate_fail_with_requirements_addressed_text_fallback(
        self, tmp_worktree, task_work_results_dir
    ):
        """No promises; requirements_addressed text-matches 2 of 3 ACs.
        Gate fails: requirements is populated and criteria_met >= 1."""
        # Two of the three criteria are mirrored verbatim; the third is
        # absent so the legacy text matcher will reject it.
        requirements_addressed = [
            "AC-001: alpha bravo charlie delta",
            "AC-002: echo foxtrot golf hotel",
        ]
        _write(
            task_work_results_dir,
            _make_gate_fail_results(
                requirements_addressed=requirements_addressed
            ),
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, _three_ac_task())

        assert result.decision == "feedback"
        assert result.requirements is not None
        assert result.requirements.criteria_met >= 1
        assert result.requirements.criteria_total == 3

    def test_gate_fail_with_no_promises_no_text_returns_zero_criteria_met(
        self, tmp_worktree, task_work_results_dir
    ):
        """No completion_promises, no requirements_addressed.
        Gate fails: validate_requirements still returns a non-None
        RequirementsValidation with criteria_met == 0. This is the
        documented behaviour — _count_criteria_passed is unchanged
        downstream and reads zero exactly as before."""
        _write(task_work_results_dir, _make_gate_fail_results())

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, _three_ac_task())

        assert result.decision == "feedback"
        assert result.requirements is not None
        assert result.requirements.criteria_met == 0
        assert result.requirements.criteria_total == 3

    def test_gate_fail_decision_remains_feedback_with_full_criteria_met(
        self, tmp_worktree, task_work_results_dir
    ):
        """Critical regression guard: even with criteria_met maxed, the
        gate-fail short-circuit must keep ``decision == 'feedback'``.
        ``all_gates_passed`` is the sole gate on the decision field."""
        promises = [
            {
                "criterion_id": f"AC-{i+1:03d}",
                "status": "complete",
                "evidence": f"Implemented AC-{i+1:03d}",
            }
            for i in range(6)
        ]
        _write(
            task_work_results_dir,
            _make_gate_fail_results(completion_promises=promises),
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate("TASK-001", 1, _six_ac_task())

        assert result.decision == "feedback"
        assert result.requirements is not None
        assert result.requirements.criteria_met == 6

    def test_validate_requirements_called_once_per_validate_invocation_on_gate_fail(
        self, tmp_worktree, task_work_results_dir
    ):
        """Guard against future re-introduction of a duplicate
        ``validate_requirements`` call between the hoist site and the
        old line-1369 site. With gates failing, the gate-fail branch
        must short-circuit and exactly one call must have been made."""
        promises = [
            {
                "criterion_id": f"AC-{i+1:03d}",
                "status": "complete",
            }
            for i in range(6)
        ]
        _write(
            task_work_results_dir,
            _make_gate_fail_results(completion_promises=promises),
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            validator = CoachValidator(str(tmp_worktree))
            with patch.object(
                validator,
                "validate_requirements",
                wraps=validator.validate_requirements,
            ) as spy:
                result = validator.validate("TASK-001", 1, _six_ac_task())

        assert result.decision == "feedback"
        assert spy.call_count == 1
