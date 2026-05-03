"""CoachValidator awareness of the OPERATOR_HANDOFF task_type (TASK-FPTC-004).

Pins AC-FPTC-004-01 and AC-FPTC-004-04: a task with
``task_type: operator_handoff`` short-circuits ``CoachValidator.validate``
before any AC-matching machinery runs and returns a ``deferred`` outcome.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.models.task_types import TaskType
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidationResult,
    CoachValidator,
)


@pytest.fixture
def validator(tmp_path: Path) -> CoachValidator:
    """Create a CoachValidator pointed at a temporary worktree."""
    return CoachValidator(str(tmp_path))


class TestOperatorHandoffDeferredOutcome:
    """AC-FPTC-004-01 / AC-FPTC-004-04: operator_handoff returns deferred."""

    def test_operator_handoff_returns_deferred_decision(
        self, validator: CoachValidator
    ) -> None:
        """A task with ``task_type=operator_handoff`` returns decision=deferred."""
        task = {
            "id": "TASK-FPTC-OP-001",
            "task_type": "operator_handoff",
            "acceptance_criteria": [
                "AC-1: operator runs ./scripts/foo and observes 200 OK",
                "AC-2: registry shows the new entry within 30 seconds",
            ],
        }

        result = validator.validate(
            task_id="TASK-FPTC-OP-001",
            turn=1,
            task=task,
        )

        assert isinstance(result, CoachValidationResult)
        assert result.decision == "deferred"

    def test_operator_handoff_rationale_mentions_runtime_verification(
        self, validator: CoachValidator
    ) -> None:
        """The rationale matches the contract string used by TASK-FPTC-003."""
        task = {
            "id": "TASK-FPTC-OP-002",
            "task_type": "operator_handoff",
        }

        result = validator.validate(
            task_id="TASK-FPTC-OP-002",
            turn=1,
            task=task,
        )

        assert result.rationale == (
            "operator follow-up — runtime verification required"
        )

    def test_operator_handoff_skips_quality_gate_results_read(
        self, validator: CoachValidator
    ) -> None:
        """The skip branch must fire BEFORE ``read_quality_gate_results``.

        If the orchestrator skipped Player invocation (TASK-FPTC-003), the
        ``task_work_results.json`` file will not exist. The defensive
        Coach branch must not depend on it.
        """
        task = {
            "id": "TASK-FPTC-OP-003",
            "task_type": "operator_handoff",
        }

        with patch.object(
            CoachValidator, "read_quality_gate_results"
        ) as read_mock:
            result = validator.validate(
                task_id="TASK-FPTC-OP-003",
                turn=1,
                task=task,
            )

        assert result.decision == "deferred"
        read_mock.assert_not_called()

    def test_operator_handoff_skips_ac_matching_machinery(
        self, validator: CoachValidator
    ) -> None:
        """No AC-matching machinery is exercised for operator_handoff tasks.

        The deferred branch returns before ``validate_requirements``,
        ``verify_command_criteria``, ``_match_by_promises``,
        ``_match_by_text``, or ``_hybrid_fallback`` can run.
        """
        task = {
            "id": "TASK-FPTC-OP-004",
            "task_type": "operator_handoff",
            "acceptance_criteria": [
                "operator follows runbook step 1",
                "operator follows runbook step 2",
            ],
        }

        with patch.object(
            CoachValidator, "validate_requirements"
        ) as validate_reqs_mock, patch.object(
            CoachValidator, "verify_command_criteria"
        ) as verify_cmd_mock, patch.object(
            CoachValidator, "_match_by_promises"
        ) as match_promises_mock, patch.object(
            CoachValidator, "_match_by_text"
        ) as match_text_mock, patch.object(
            CoachValidator, "_hybrid_fallback"
        ) as hybrid_mock:
            result = validator.validate(
                task_id="TASK-FPTC-OP-004",
                turn=1,
                task=task,
            )

        assert result.decision == "deferred"
        validate_reqs_mock.assert_not_called()
        verify_cmd_mock.assert_not_called()
        match_promises_mock.assert_not_called()
        match_text_mock.assert_not_called()
        hybrid_mock.assert_not_called()

    def test_operator_handoff_result_has_no_validation_subresults(
        self, validator: CoachValidator
    ) -> None:
        """Quality gates / independent tests / requirements are all None."""
        task = {
            "id": "TASK-FPTC-OP-005",
            "task_type": "operator_handoff",
        }

        result = validator.validate(
            task_id="TASK-FPTC-OP-005",
            turn=2,
            task=task,
        )

        assert result.quality_gates is None
        assert result.independent_tests is None
        assert result.requirements is None
        assert result.issues == []
        assert result.task_id == "TASK-FPTC-OP-005"
        assert result.turn == 2

    def test_operator_handoff_via_taskype_enum_branch(
        self, validator: CoachValidator
    ) -> None:
        """The branch fires when task_type resolves to TaskType.OPERATOR_HANDOFF.

        Sanity check that the comparison uses enum identity (or equivalent
        string equality post-resolution), not raw frontmatter strings.
        """
        # ``_resolve_task_type`` will turn ``"operator_handoff"`` into
        # ``TaskType.OPERATOR_HANDOFF``. The branch in ``validate`` uses
        # ``task_type == TaskType.OPERATOR_HANDOFF`` so the comparison is
        # an enum-identity check.
        task = {
            "id": "TASK-FPTC-OP-006",
            "task_type": TaskType.OPERATOR_HANDOFF.value,
        }

        result = validator.validate(
            task_id="TASK-FPTC-OP-006",
            turn=1,
            task=task,
        )

        assert result.decision == "deferred"

    def test_operator_handoff_preserves_context_used(
        self, validator: CoachValidator
    ) -> None:
        """Optional ``context`` argument is propagated to the deferred result."""
        task = {
            "id": "TASK-FPTC-OP-007",
            "task_type": "operator_handoff",
        }

        result = validator.validate(
            task_id="TASK-FPTC-OP-007",
            turn=1,
            task=task,
            context="graphiti context blob",
        )

        assert result.decision == "deferred"
        assert result.context_used == "graphiti context blob"


class TestNonOperatorHandoffNotShortCircuited:
    """AC-FPTC-004-05: existing non-operator-handoff behaviour is preserved.

    The deferred branch must not change semantics for the other 8
    task types. We verify by patching the next step in the validation
    pipeline (``read_quality_gate_results``) and checking it is invoked
    for every non-operator-handoff task type.
    """

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
        """Every non-operator-handoff type proceeds past the deferred branch.

        Patches ``read_quality_gate_results`` to return an error so the
        validator short-circuits early without needing real
        ``task_work_results.json`` plumbing — but only AFTER the deferred
        branch has not fired.
        """
        task = {
            "id": f"TASK-NONOP-{task_type_str}",
            "task_type": task_type_str,
            "acceptance_criteria": ["AC-1: do the thing"],
        }

        with patch.object(
            CoachValidator,
            "read_quality_gate_results",
            return_value={"error": "stub"},
        ) as read_mock:
            result = validator.validate(
                task_id=f"TASK-NONOP-{task_type_str}",
                turn=1,
                task=task,
            )

        # Confirm the deferred branch did NOT fire ...
        assert result.decision != "deferred"
        # ... and that we proceeded into the regular validation pipeline.
        read_mock.assert_called_once()
