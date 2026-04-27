"""Validator behaviour for declarative tasks (TASK-ABSR-1357).

The agent-invocations validator at
``installer/core/commands/lib/agent_invocation_validator.py`` previously
hard-coded ``implement-only`` to 3 phases (Implementation, Testing, Code
Review). For ``task_type=declarative`` (Pydantic models, DTOs, settings,
constants — see ``guardkit/models/task_types.py``) the schema *is* the
implementation; there is no meaningful Phase-3 stack-specific specialist
to invoke. The advisory the gate produced was non-blocking but pollutted
Coach feedback strings with a "missing Phase 3" line the Player had no
way to act on.

These tests pin the new behaviour:

* Declarative tasks in implement-only mode expect 2 phases (``['4',
  '5']``), not 3.
* Aliases ``config`` and ``dto`` resolve to ``declarative`` (per
  ``TASK_TYPE_ALIASES``).
* All other workflow_mode / task_type combinations are unchanged
  (backward-compat).
* ``validate_agent_invocations`` is silent for a declarative implement-
  only task that recorded only Phase 4 + Phase 5; still raises when a
  required phase (e.g. Phase 4) is missing.

Coverage Target: declarative-suppression branches in
``get_expected_phases``, ``get_expected_phase_list``,
``identify_missing_phases`` and ``validate_agent_invocations``.
"""

from __future__ import annotations

import pytest

from installer.core.commands.lib.agent_invocation_tracker import (
    AgentInvocationTracker,
)
from installer.core.commands.lib.agent_invocation_validator import (
    ValidationError,
    get_expected_phase_list,
    get_expected_phases,
    identify_missing_phases,
    validate_agent_invocations,
)


def _completed_tracker(*phases: str) -> AgentInvocationTracker:
    """Build a tracker pre-populated with completed invocations.

    Mirrors the producer-side tracker construction in
    ``AgentInvoker._compute_agent_invocations_validation`` — populates
    ``invocations`` directly to avoid the stdout side-effect of
    ``record_invocation`` / ``mark_complete``.
    """
    tracker = AgentInvocationTracker()
    for phase in phases:
        tracker.invocations.append({
            "phase": phase,
            "agent": f"agent-{phase}",
            "phase_description": f"Phase {phase}",
            "agent_source": "unknown",
            "status": "completed",
        })
    return tracker


class TestGetExpectedPhasesDeclarative:
    """``get_expected_phases`` honours ``task_type=declarative``."""

    def test_get_expected_phases_declarative_implement_only_returns_two(self):
        # AC: implement-only + declarative → 2 (Testing + Code Review).
        assert get_expected_phases("implement-only", task_type="declarative") == 2

    def test_get_expected_phase_list_declarative_implement_only_returns_two_phases(
        self,
    ):
        # AC: implement-only + declarative → ['4', '5'].
        assert get_expected_phase_list(
            "implement-only", task_type="declarative"
        ) == ["4", "5"]

    @pytest.mark.parametrize("alias", ["config", "dto"])
    def test_alias_config_treated_as_declarative_in_validator(self, alias):
        # AC: TASK_TYPE_ALIASES (`config`, `dto` → `declarative`) honored.
        assert get_expected_phases("implement-only", task_type=alias) == 2
        assert get_expected_phase_list(
            "implement-only", task_type=alias
        ) == ["4", "5"]


class TestGetExpectedPhasesUnchanged:
    """All other combinations preserve today's behaviour (backward-compat)."""

    def test_get_expected_phases_other_combinations_unchanged(self):
        # No task_type → today's defaults.
        assert get_expected_phases("standard") == 5
        assert get_expected_phases("micro") == 3
        assert get_expected_phases("design-only") == 3
        assert get_expected_phases("implement-only") == 3
        assert get_expected_phases("direct") == 1

        # Non-declarative task_type → defaults.
        assert get_expected_phases("standard", task_type="feature") == 5
        assert get_expected_phases("implement-only", task_type="feature") == 3
        assert get_expected_phases("implement-only", task_type="bugfix") == 3

        # Declarative on non-implement-only modes → defaults (suppression
        # is scoped to implement-only — declarative tasks running in
        # standard mode still expect a Phase 3 specialist).
        assert get_expected_phases("standard", task_type="declarative") == 5
        assert get_expected_phases("micro", task_type="declarative") == 3
        assert (
            get_expected_phases("design-only", task_type="declarative") == 3
        )
        assert get_expected_phases("direct", task_type="declarative") == 1

        # Empty / unknown task_type → defaults.
        assert get_expected_phases("implement-only", task_type=None) == 3
        assert get_expected_phases("implement-only", task_type="") == 3
        assert get_expected_phases("implement-only", task_type="nonsense") == 3

    def test_get_expected_phase_list_other_combinations_unchanged(self):
        assert get_expected_phase_list("standard") == ["2", "2.5B", "3", "4", "5"]
        assert get_expected_phase_list("implement-only") == ["3", "4", "5"]
        assert get_expected_phase_list(
            "implement-only", task_type="feature"
        ) == ["3", "4", "5"]
        assert get_expected_phase_list(
            "standard", task_type="declarative"
        ) == ["2", "2.5B", "3", "4", "5"]


class TestAdvisorySilentForDeclarative:
    """End-to-end: declarative implement-only with [4, 5] → no advisory."""

    def test_advisory_silent_for_declarative_task_with_phase_4_and_5_only(self):
        # The producer wires task_type=declarative through to
        # validate_agent_invocations. With Phases 4 + 5 completed, the
        # validator must NOT raise — there's no Phase 3 to be missing.
        tracker = _completed_tracker("4", "5")

        # Pre-TASK-ABSR-1357 baseline: without task_type this would raise
        # because expected=3 and actual=2.
        with pytest.raises(ValidationError):
            validate_agent_invocations(tracker, "implement-only")

        # New behaviour: passing task_type='declarative' suppresses the
        # advisory.
        assert validate_agent_invocations(
            tracker, "implement-only", task_type="declarative"
        ) is True

        # And no missing phases reported for the declarative path.
        assert identify_missing_phases(
            tracker, "implement-only", task_type="declarative"
        ) == []

    def test_advisory_silent_for_alias_dto(self):
        tracker = _completed_tracker("4", "5")
        assert validate_agent_invocations(
            tracker, "implement-only", task_type="dto"
        ) is True


class TestAdvisoryStillFiresOnRealMissingPhase:
    """Suppression must NOT mask genuine quality-gate-equivalent failures."""

    def test_advisory_still_fires_for_declarative_task_missing_phase_4(self):
        # Only Phase 5 ran — Phase 4 (Testing) is genuinely missing. For a
        # declarative task the DECLARATIVE profile in
        # guardkit/models/task_types.py keeps tests_required=True (catches
        # import errors), so the advisory must still fire for missing
        # Phase 4.
        tracker = _completed_tracker("5")

        with pytest.raises(ValidationError) as exc_info:
            validate_agent_invocations(
                tracker, "implement-only", task_type="declarative"
            )

        assert "PROTOCOL VIOLATION" in str(exc_info.value)

        missing = identify_missing_phases(
            tracker, "implement-only", task_type="declarative"
        )
        missing_phases = {m["phase"] for m in missing}
        # Phase 4 must be flagged; Phase 3 must NOT be (declarative
        # suppression).
        assert "4" in missing_phases
        assert "3" not in missing_phases
        # Only Phase 4 is missing for declarative implement-only when
        # Phase 5 is present.
        assert missing_phases == {"4"}

    def test_advisory_still_fires_for_declarative_task_with_no_phases(self):
        # Empty tracker — no Phase 4, no Phase 5. Both must be flagged
        # missing; Phase 3 must NOT appear (declarative suppression).
        tracker = _completed_tracker()

        with pytest.raises(ValidationError):
            validate_agent_invocations(
                tracker, "implement-only", task_type="declarative"
            )

        missing = identify_missing_phases(
            tracker, "implement-only", task_type="declarative"
        )
        missing_phases = {m["phase"] for m in missing}
        assert missing_phases == {"4", "5"}


class TestBackwardCompatNoTaskType:
    """Existing call sites (no ``task_type`` arg) must behave as today."""

    def test_validate_agent_invocations_without_task_type_unchanged(self):
        # All 3 implement-only phases present → passes.
        tracker = _completed_tracker("3", "4", "5")
        assert validate_agent_invocations(tracker, "implement-only") is True

        # 2 phases present, no task_type → validator still raises (the
        # legacy contract — the suppression is opt-in via task_type).
        tracker_two = _completed_tracker("4", "5")
        with pytest.raises(ValidationError):
            validate_agent_invocations(tracker_two, "implement-only")

    def test_identify_missing_phases_without_task_type_unchanged(self):
        tracker = _completed_tracker("4", "5")
        missing = identify_missing_phases(tracker, "implement-only")
        assert {m["phase"] for m in missing} == {"3"}
