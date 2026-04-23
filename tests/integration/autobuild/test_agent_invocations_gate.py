"""End-to-end: agent_invocations gate on producer → Coach path.

TASK-FIX-RWOP1.3.1 wires ``validate_agent_invocations`` into
``AgentInvoker._write_task_work_results`` (producer) and makes
``CoachValidator`` reject turns where the producer recorded a protocol
violation. This test pins both sides of that wire:

1. Producer: result_data with only some phases completed → the on-disk
   ``task_work_results.json`` carries ``agent_invocations_validation``
   with ``status == "violation"`` and the missing phases named.
2. Coach: a results file with that violation block → ``CoachValidator``
   returns a feedback decision whose issues and rationale name the
   missing phases.

Without this wire the Player could emit any phase set (or none) and no
deterministic check would fire before Coach. See
``docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md``
Finding #4 and the TASK-FIX-3C9D fix-shape reference.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


TASK_ID = "TASK-RWOP131-TEST"


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Isolated worktree root for the producer-side writes."""
    return tmp_path


@pytest.fixture
def invoker(worktree: Path) -> AgentInvoker:
    return AgentInvoker(worktree_path=worktree)


def _phases(*completed: str) -> dict:
    """Build parser-shape phases dict with the given phases marked completed."""
    return {
        f"phase_{p}": {"detected": True, "completed": True, "text": f"Phase {p}"}
        for p in completed
    }


class TestProducerWritesViolationBlock:
    """Producer fold: missing phases → violation block on disk."""

    def test_missing_phases_marks_violation(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Only Phase 3 (Implementation) ran — Phases 4 (Testing) and 5
        # (Code Review) missing. Player's result_data looks complete-ish
        # but the invocation record doesn't match implement-only's
        # expected [3, 4, 5].
        result_data = {
            "phases": _phases("3"),
            "tests_passed": 5,
            "tests_failed": 0,
            "coverage": 85.0,
            "quality_gates_passed": True,
            "files_modified": [],
            "files_created": [],
        }

        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )

        assert results_path.exists()
        on_disk = json.loads(results_path.read_text())

        gate = on_disk.get("agent_invocations_validation")
        assert gate is not None, "validation block must be persisted"
        assert gate["status"] == "violation"
        assert gate["expected_phases"] == 3  # implement-only default
        assert gate["actual_invocations"] == 1
        assert set(gate["missing_phases"]) == {"4", "5"}
        assert "PROTOCOL VIOLATION" in gate["violation_message"]

    def test_all_phases_present_passes(
        self, invoker: AgentInvoker, worktree: Path
    ):
        result_data = {
            "phases": _phases("3", "4", "5"),
            "tests_passed": 5,
            "tests_failed": 0,
        }

        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )
        on_disk = json.loads(results_path.read_text())
        gate = on_disk["agent_invocations_validation"]
        assert gate["status"] == "passed"
        assert gate["actual_invocations"] == 3
        assert gate["missing_phases"] == []

    def test_empty_phases_records_no_data(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Fixture writes or pipeline failures with no phase evidence must
        # not be recorded as a violation — Coach would false-reject every
        # synthetic seed. `no_data` is the informational escape hatch.
        result_data = {"phases": {}, "tests_passed": 5, "tests_failed": 0}
        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )
        gate = json.loads(results_path.read_text())["agent_invocations_validation"]
        assert gate["status"] == "no_data"
        assert gate["actual_invocations"] == 0
        assert gate["missing_phases"] == []

    def test_validator_crash_records_validator_error(
        self, invoker: AgentInvoker, monkeypatch, worktree: Path
    ):
        # The gate is not supposed to block artefact emission. If the
        # validator itself raises, the producer records validator_error
        # and writes the file anyway.
        def _boom(*_args, **_kwargs):
            raise RuntimeError("simulated validator crash")

        monkeypatch.setattr(
            "guardkit.orchestrator.agent_invoker.validate_agent_invocations",
            _boom,
        )

        result_data = {"phases": _phases("3", "4", "5")}
        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )

        on_disk = json.loads(results_path.read_text())
        gate = on_disk["agent_invocations_validation"]
        assert gate["status"] == "validator_error"
        assert "simulated validator crash" in gate["violation_message"]


class TestCoachRejectsOnViolation:
    """Coach gate: violation block → feedback decision."""

    def _seed_results(self, worktree: Path, violation_block: dict) -> Path:
        """Put a canned task_work_results.json at the autobuild path."""
        TaskArtifactPaths.ensure_autobuild_dir(TASK_ID, worktree)
        results_path = TaskArtifactPaths.task_work_results_path(TASK_ID, worktree)
        results_path.write_text(
            json.dumps({
                "task_id": TASK_ID,
                "completed": True,
                "quality_gates": {
                    "tests_passing": True,
                    "tests_passed": 10,
                    "tests_failed": 0,
                    "coverage": 85.0,
                    "coverage_met": True,
                    "all_passed": True,
                },
                "files_modified": [],
                "files_created": [],
                "tests_written": [],
                "summary": "",
                "agent_invocations_validation": violation_block,
            })
        )
        return results_path

    def test_coach_rejects_violation_naming_missing_phases(
        self, worktree: Path
    ):
        # Player report missing code-reviewer (Phase 5) and test-agent
        # (Phase 4) — the scenario called out in the task's integration
        # test requirement.
        violation_block = {
            "status": "violation",
            "expected_phases": 3,
            "actual_invocations": 1,
            "missing_phases": ["4", "5"],
            "violation_message": "missing phases: Testing, Code Review",
        }
        self._seed_results(worktree, violation_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={"id": TASK_ID, "acceptance_criteria": ["trivial AC"]},
        )

        assert result.decision == "feedback"
        assert result.issues, "feedback decision must carry issues"

        categories = {i.get("category") for i in result.issues}
        assert "agent_invocations_violation" in categories

        # Feedback must name the missing phases so the Player can
        # correct course.
        joined = " ".join(
            i.get("description", "") for i in result.issues
        ) + " " + (result.rationale or "")
        assert "4" in joined and "5" in joined

    def test_coach_does_not_reject_on_passed_block(self, worktree: Path):
        passed_block = {
            "status": "passed",
            "expected_phases": 3,
            "actual_invocations": 3,
            "missing_phases": [],
            "violation_message": None,
        }
        self._seed_results(worktree, passed_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={"id": TASK_ID, "acceptance_criteria": ["trivial AC"]},
        )

        # Whatever else Coach does (quality gates, independent tests),
        # it must NOT be rejecting for agent_invocations_violation.
        if result.decision == "feedback":
            categories = {i.get("category") for i in (result.issues or [])}
            assert "agent_invocations_violation" not in categories

    def test_coach_does_not_reject_on_validator_error(self, worktree: Path):
        # validator_error is NOT a blocker — the validator's own failure
        # shouldn't stop Coach from evaluating the rest.
        error_block = {
            "status": "validator_error",
            "expected_phases": None,
            "actual_invocations": None,
            "missing_phases": [],
            "violation_message": "RuntimeError: boom",
        }
        self._seed_results(worktree, error_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={"id": TASK_ID, "acceptance_criteria": ["trivial AC"]},
        )

        if result.decision == "feedback":
            categories = {i.get("category") for i in (result.issues or [])}
            assert "agent_invocations_violation" not in categories
