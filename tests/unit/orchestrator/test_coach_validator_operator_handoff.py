"""CoachValidator awareness of the OPERATOR_HANDOFF task_type (TASK-FPTC-004).

A task with ``task_type: operator_handoff`` has its changed parts tested
like every other task type (31 October 2026: it used to skip the check, so a
part it changed went untested).

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.models.task_types import TaskType
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


@pytest.fixture
def validator(tmp_path: Path) -> CoachValidator:
    """Create a CoachValidator pointed at a temporary worktree."""
    return CoachValidator(str(tmp_path))


class TestOperatorHandoffIsTestedLikeAnyTask:
    """An operator hand-over no longer skips the check (31 October 2026).

    In a feature build the orchestrator defers these tasks without running
    the builder (TASK-FPTC-003), so they change nothing and have nothing to
    run. A single-task build did reach the Coach, which skipped the check, so
    a part the task changed went untested. Its changed parts are now tested
    like any other task's (tests/orchestrator/test_changed_parts_check.py
    runs one for real).
    """

    def test_operator_handoff_runs_the_changed_parts_check(
        self, validator: CoachValidator
    ) -> None:
        task = {"id": "TASK-FPTC-OP-003", "task_type": "operator_handoff"}
        ran = IndependentTestResult.skipped(test_output_summary="nothing changed")

        with patch.object(
            CoachValidator, "run_changed_parts", return_value=ran
        ) as run_mock:
            bundle = validator.gather_evidence(
                task_id="TASK-FPTC-OP-003", turn=1, task=task
            )

        run_mock.assert_called_once()
        assert bundle.task_type == TaskType.OPERATOR_HANDOFF.value
        assert bundle.independent_tests is ran

class TestNonOperatorHandoffNotShortCircuited:
    """Every other task type proceeds to the regular evidence gathering."""

    @pytest.mark.parametrize(
        "task_type_str",
        [
            "feature",
            "scaffolding",
            "infrastructure",
            "integration",
            "documentation",
            "testing",
            "refactor",
            "declarative",
        ],
    )
    def test_non_operator_handoff_proceeds_to_results_read(
        self,
        validator: CoachValidator,
        task_type_str: str,
    ) -> None:
        task = {
            "id": f"TASK-NONOP-{task_type_str}",
            "task_type": task_type_str,
            "acceptance_criteria": ["AC-1: do the thing"],
        }
        ran = IndependentTestResult(
            tests_passed=True,
            test_command="pytest",
            test_output_summary="1 passed",
            duration_seconds=0.1,
        )

        with patch.object(
            CoachValidator,
            "read_quality_gate_results",
            return_value={"error": "stub"},
        ) as read_mock, patch.object(
            CoachValidator, "run_independent_tests", return_value=ran
        ):
            bundle = validator.gather_evidence(
                task_id=f"TASK-NONOP-{task_type_str}", turn=1, task=task
            )

        read_mock.assert_called_once()
        assert bundle.task_type == task_type_str
        assert bundle.independent_tests is not None
