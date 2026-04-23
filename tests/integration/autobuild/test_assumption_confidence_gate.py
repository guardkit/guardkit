"""End-to-end: assumption-confidence warn-mode gate (producer → Coach).

TASK-FIX-RWOP1.4a wires
``check_unconfirmed_low_confidence_assumptions`` into
``AgentInvoker._write_task_work_results`` (producer) and adds
``CoachValidator._check_unconfirmed_assumptions`` to surface the
resulting block as a non-blocking warning. This test pins both sides:

1. Producer: a worktree with ``features/**/_assumptions.yaml`` rows
   marked ``confidence: low`` without ``human_response: confirmed``
   → the on-disk ``task_work_results.json`` carries
   ``unconfirmed_low_confidence_assumptions`` with ``status == "warning"``
   and the offending rows named.
2. Coach: a results file with that warning block → ``CoachValidator``
   still approves (warn-mode, per TASK-FIX-RWOP1.4 Part A), but the
   approval's ``issues`` list names the rows so the human reviewing the
   merge can act on them.

Without this wire ``feature-spec.md:337``'s "Coach verifies
low-confidence assumptions" claim is runner-without-producer: no
deterministic check fires, and a cohort run with unresolved low-
confidence rows looks green despite an unreviewed premise.

See: ``docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md``
for the parent review; ``tasks/completed/TASK-FIX-3C9D/`` for R1 fix shape.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


TASK_ID = "TASK-RWOP14A-TEST"


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Isolated worktree root for producer writes and Coach reads."""
    return tmp_path


@pytest.fixture
def invoker(worktree: Path) -> AgentInvoker:
    return AgentInvoker(worktree_path=worktree)


def _write_assumptions(worktree: Path, feature_slug: str, body: str) -> Path:
    """Create features/{feature_slug}/_assumptions.yaml with the given body."""
    feature_dir = worktree / "features" / feature_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    path = feature_dir / "_assumptions.yaml"
    path.write_text(body)
    return path


_MIXED_FIXTURE = """\
feature: Document Upload
generated: "2026-04-23T00:00:00Z"
stack: python
review_required: true
assumptions:
  - id: ASSUM-001
    scenario: Upload limit respected
    assumption: Maximum file size is 50MB
    confidence: low
    basis: Common web default
    human_response: confirmed
  - id: ASSUM-002
    scenario: Type filter applied
    assumption: Allowed types are PDF, DOCX, PNG, JPG
    confidence: low
    basis: Document management convention
    human_response: deferred
"""

_ALL_CONFIRMED_FIXTURE = """\
feature: Document Upload
assumptions:
  - id: ASSUM-001
    scenario: Upload limit respected
    assumption: Maximum file size is 50MB
    confidence: low
    basis: Common web default
    human_response: confirmed
  - id: ASSUM-002
    scenario: Type filter applied
    assumption: Allowed types are PDF, DOCX only
    confidence: low
    basis: Overridden by human
    human_response: confirmed
"""


class TestProducerWritesWarningBlock:
    """Producer fold: _assumptions.yaml rows → warning block on disk."""

    def test_unconfirmed_low_confidence_row_flagged(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Minimum viable fixture per task spec: one confirmed low-conf row
        # and one unconfirmed low-conf row. The test asserts only the
        # unconfirmed row surfaces.
        _write_assumptions(worktree, "doc-upload", _MIXED_FIXTURE)

        result_data = {
            "phases": {
                f"phase_{p}": {"detected": True, "completed": True, "text": f"Phase {p}"}
                for p in ("3", "4", "5")
            },
            "tests_passed": 5,
            "tests_failed": 0,
        }
        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )

        on_disk = json.loads(results_path.read_text())
        block = on_disk.get("unconfirmed_low_confidence_assumptions")
        assert block is not None, "producer must persist the warning block"
        assert block["status"] == "warning"
        assert block["files_scanned"] == 1
        assert block["files_skipped"] == 0

        rows = block["unconfirmed"]
        assert len(rows) == 1, (
            "only ASSUM-002 (low + unconfirmed) should be flagged; "
            "ASSUM-001 (low + confirmed) should be cleared"
        )
        row = rows[0]
        assert row["id"] == "ASSUM-002"
        assert row["human_response"] == "deferred"
        assert row["file"].endswith("features/doc-upload/_assumptions.yaml")

    def test_all_confirmed_rows_empty_warning(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Inverse branch called out in the task spec: all low-conf rows
        # have human_response: confirmed → empty unconfirmed list.
        _write_assumptions(worktree, "doc-upload", _ALL_CONFIRMED_FIXTURE)

        result_data = {"phases": {}, "tests_passed": 1, "tests_failed": 0}
        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )

        block = json.loads(results_path.read_text())[
            "unconfirmed_low_confidence_assumptions"
        ]
        assert block["status"] == "ok"
        assert block["unconfirmed"] == []
        assert block["files_scanned"] == 1

    def test_no_assumptions_files_status_ok(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Tasks that don't touch features/ at all: the gate must not fire.
        result_data = {"phases": {}, "tests_passed": 1, "tests_failed": 0}
        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )

        block = json.loads(results_path.read_text())[
            "unconfirmed_low_confidence_assumptions"
        ]
        assert block["status"] == "ok"
        assert block["unconfirmed"] == []
        assert block["files_scanned"] == 0


class TestCoachEmitsWarningWithoutBlocking:
    """Coach gate: warning block → non-blocking issue attached to approval."""

    def _seed_results(
        self, worktree: Path, assumption_block: dict
    ) -> Path:
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
                "code_review": {"score": 85},
                "plan_audit": {"status": "skipped", "violations": 0},
                "files_modified": [],
                "files_created": [],
                "tests_written": [],
                "summary": "",
                # Seed requirements_met with the test's AC so the
                # requirements gate at coach_validator.py:884 passes and
                # Coach reaches the approval path where our warning rides.
                "requirements_met": ["trivial AC"],
                # agent_invocations gate must pass so we exercise the
                # approval path, not the feedback path.
                "agent_invocations_validation": {
                    "status": "passed",
                    "expected_phases": 3,
                    "actual_invocations": 3,
                    "missing_phases": [],
                    "violation_message": None,
                },
                "unconfirmed_low_confidence_assumptions": assumption_block,
            })
        )
        return results_path

    def test_warning_block_surfaces_as_non_blocking_issue(
        self, worktree: Path
    ):
        warning_block = {
            "status": "warning",
            "unconfirmed": [{
                "file": "features/doc-upload/_assumptions.yaml",
                "id": "ASSUM-002",
                "scenario": "Type filter applied",
                "assumption": "Allowed types are PDF, DOCX, PNG, JPG",
                "human_response": "deferred",
            }],
            "files_scanned": 1,
            "files_skipped": 0,
            "message": None,
        }
        self._seed_results(worktree, warning_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={
                "id": TASK_ID,
                "task_type": "scaffolding",
                "acceptance_criteria": ["trivial AC"],
            },
        )

        # Warn-mode: Coach approves. The warning rides along in issues.
        categories = {i.get("category") for i in (result.issues or [])}
        assert "unconfirmed_low_confidence_assumptions" in categories, (
            "Coach must surface the warning even on approval"
        )

        warning = next(
            i for i in result.issues
            if i.get("category") == "unconfirmed_low_confidence_assumptions"
        )
        assert warning["severity"] == "warning"
        assert "ASSUM-002" in warning["description"]
        assert warning["details"]["unconfirmed"][0]["id"] == "ASSUM-002"

    def test_ok_block_emits_no_warning(self, worktree: Path):
        ok_block = {
            "status": "ok",
            "unconfirmed": [],
            "files_scanned": 1,
            "files_skipped": 0,
            "message": None,
        }
        self._seed_results(worktree, ok_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={
                "id": TASK_ID,
                "task_type": "scaffolding",
                "acceptance_criteria": ["trivial AC"],
            },
        )

        categories = {i.get("category") for i in (result.issues or [])}
        assert "unconfirmed_low_confidence_assumptions" not in categories

    def test_checker_error_emits_no_warning(self, worktree: Path):
        # Producer self-reported fault must not surface as a spec warning —
        # the gate's own failure shouldn't be confused with a finding.
        error_block = {
            "status": "checker_error",
            "unconfirmed": [],
            "files_scanned": 0,
            "files_skipped": 0,
            "message": "RuntimeError: simulated",
        }
        self._seed_results(worktree, error_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={
                "id": TASK_ID,
                "task_type": "scaffolding",
                "acceptance_criteria": ["trivial AC"],
            },
        )

        categories = {i.get("category") for i in (result.issues or [])}
        assert "unconfirmed_low_confidence_assumptions" not in categories
