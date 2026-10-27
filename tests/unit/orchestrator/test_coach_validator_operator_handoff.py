"""CoachValidator awareness of the OPERATOR_HANDOFF task_type (TASK-FPTC-004).

A task with ``task_type: operator_handoff`` short-circuits
``CoachValidator.gather_evidence``: no project checks run, and the
``task_work_results.json`` file (which may not exist, because the Player was
skipped) is never read. Every other task type proceeds to the regular
evidence gathering.

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


class TestOperatorHandoffShortCircuit:
    """operator_handoff returns an empty, complete bundle."""

    def test_operator_handoff_returns_empty_bundle(
        self, validator: CoachValidator
    ) -> None:
        task = {
            "id": "TASK-FPTC-OP-001",
            "task_type": "operator_handoff",
            "acceptance_criteria": [
                "AC-1: operator runs ./scripts/foo and observes 200 OK",
                "AC-2: registry shows the new entry within 30 seconds",
            ],
        }

        bundle = validator.gather_evidence(
            task_id="TASK-FPTC-OP-001", turn=1, task=task
        )

        assert isinstance(bundle, CoachEvidenceBundle)
        assert bundle.gathering_status == "complete"
        assert bundle.task_type == TaskType.OPERATOR_HANDOFF.value
        assert bundle.independent_tests is None
        assert bundle.runtime_parity is None
        assert bundle.behavioural_oracle is None

    def test_operator_handoff_skips_results_read_and_test_run(
        self, validator: CoachValidator
    ) -> None:
        """The short-circuit fires BEFORE ``read_quality_gate_results``.

        If the orchestrator skipped Player invocation (TASK-FPTC-003), the
        ``task_work_results.json`` file will not exist.
        """
        task = {"id": "TASK-FPTC-OP-003", "task_type": "operator_handoff"}

        with patch.object(
            CoachValidator, "read_quality_gate_results"
        ) as read_mock, patch.object(
            CoachValidator, "run_independent_tests"
        ) as run_mock:
            bundle = validator.gather_evidence(
                task_id="TASK-FPTC-OP-003", turn=1, task=task
            )

        assert bundle.independent_tests is None
        read_mock.assert_not_called()
        run_mock.assert_not_called()


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
