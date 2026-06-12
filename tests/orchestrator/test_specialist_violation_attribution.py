"""TASK-FIX-SPECVIOL01 — orchestrator-injected specialist-violation records
must not be attributed to Player honesty.

Regression suite for the FEAT-C332 run-2 TASK-QAWE-002 false-red
(2026-06-12): the ``test-orchestrator`` specialist hung, the orchestrator
injected ``source: "orchestrator"`` failure records and a
``validation=violation`` block into ``task_work_results.json``, and the
deterministic honesty path rejected the turn with
``partial_honesty_abort`` — attributing substrate noise to the Player.

Forensics showed the ``must_fix`` discrepancy actually fired from the
claim-audit gate: the Player's honest promise carried a **comma-joined**
``test_file`` string naming two existing tracked test files it *ran*
(not authored). The whole string was audited as one path → absent from
disk → "fabricated" critical → abort.

Acceptance criteria pinned here:

* AC-001/AC-003 — the FEAT-C332 run-2 shape (injected violation records +
  honest Player claims incl. the comma-joined run-claim) does NOT produce
  ``partial_honesty_abort``; evidence gathering proceeds.
* AC-002 — the substrate failure surfaces as an attributed advisory
  (``category: "specialist_substrate"``) naming the specialist and the
  hang error; never silently dropped.
* AC-004 — genuine Player test-claim fabrication (no specialist injection
  in scope) still short-circuits with ``partial_honesty_abort``.
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


TASK_ID = "TASK-QAWE-002"

HANG_ERROR = "hang detected (no model activity for 150s)"


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _init_worktree(path: Path) -> None:
    _git("init", "-q", "--initial-branch=main", cwd=path)
    _git("config", "user.email", "t@t", cwd=path)
    _git("config", "user.name", "t", cwd=path)
    # Existing test suites the Player legitimately *ran* (run-claims).
    tests_dir = path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_evidence.py").write_text("def test_a(): assert True\n")
    (tests_dir / "test_validator.py").write_text("def test_b(): assert True\n")
    _git("add", "-A", cwd=path)
    _git("commit", "-q", "-m", "base", cwd=path)


def _injected_specialist_invocations() -> list:
    """agent_invocations as written by
    ``AgentInvoker._inject_specialist_records_into_task_work_results``
    after the FEAT-C332 run-2 hang: Phase 4 failed (watchdog), Phase 5
    skipped."""
    return [
        {
            "phase": "4",
            "agent": "test-orchestrator",
            "status": "failed",
            "source": "orchestrator",
            "error": HANG_ERROR,
        },
        {
            "phase": "5",
            "agent": "code-reviewer",
            "status": "skipped",
            "source": "orchestrator",
            "error": "specialist_results.json missing phase_5 block",
        },
    ]


def _run2_task_work_results(worktree: Path) -> dict:
    """Synthetic task_work_results reproducing the run-2 turn-1 shape:
    honest Player file claims + orchestrator-injected violation records +
    a comma-joined run-claim in completion_promises[*].test_file."""
    # Honest Player write, present on disk and unstaged.
    impl = worktree / "guardkit_mod.py"
    impl.write_text("VALUE = 1\n")
    return {
        "task_id": TASK_ID,
        "quality_gates": {
            "all_passed": True,
            "tests_run": 25,
            "tests_failed": 0,
            "coverage_met": True,
            "line_coverage": 0.85,
            "branch_coverage": 0.78,
        },
        "code_review": {"score": 80},
        "plan_audit": {"status": "passed", "violations": 0, "severity": "low"},
        "files_modified": [],
        "files_created": ["guardkit_mod.py"],
        "tests_written": [],
        "completion_promises": [
            {
                "criterion_id": "AC-018",
                "criterion_text": "existing suites green.",
                "status": "complete",
                "evidence": "Ran both existing suites; all green.",
                "test_file": (
                    "tests/test_evidence.py, tests/test_validator.py"
                ),
                "implementation_files": [],
            }
        ],
        "agent_invocations": _injected_specialist_invocations(),
        "agent_invocations_validation": {
            "status": "violation",
            "expected_phases": 3,
            "actual_invocations": 1,
            "missing_phases": ["4", "5"],
            "violation_message": "PROTOCOL VIOLATION: missing phases 4, 5",
        },
    }


def _write_results(worktree: Path, results: dict) -> None:
    results_dir = worktree / ".guardkit" / "autobuild" / TASK_ID
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(json.dumps(results))


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    _init_worktree(tmp_path)
    return tmp_path


def _gather(worktree: Path):
    validator = CoachValidator(str(worktree), task_id=TASK_ID)
    stub_tests = IndependentTestResult(
        tests_passed=True,
        test_command="pytest (stubbed)",
        test_output_summary="stub",
        duration_seconds=0.0,
    )
    with patch.object(
        CoachValidator, "run_independent_tests", return_value=stub_tests
    ):
        return validator.gather_evidence(
            task_id=TASK_ID,
            turn=1,
            task={
                "acceptance_criteria": ["AC-018 existing suites green"],
                "task_type": "feature",
                "description": "run-2 reproducer",
            },
        )


class TestSpecialistViolationNotPlayerDishonesty:
    """AC-001 / AC-003: the run-2 shape no longer aborts honesty."""

    def test_run2_shape_does_not_partial_honesty_abort(
        self, worktree: Path
    ) -> None:
        _write_results(worktree, _run2_task_work_results(worktree))

        bundle = _gather(worktree)

        assert bundle.gathering_status != "partial_honesty_abort", (
            "Orchestrator-injected specialist records + an honest "
            "comma-joined run-claim must not be read as Player dishonesty"
        )
        # Evidence gathering proceeded past honesty: gates were consulted.
        assert bundle.quality_gates is not None
        # No critical honesty discrepancies were recorded.
        critical = [
            d for d in bundle.honesty.discrepancies
            if d.severity == "critical"
        ]
        assert critical == []

    def test_substrate_failure_surfaces_as_attributed_advisory(
        self, worktree: Path
    ) -> None:
        """AC-002: the specialist hang is surfaced, attributed to the
        substrate, and names the specialist and the error."""
        _write_results(worktree, _run2_task_work_results(worktree))

        bundle = _gather(worktree)

        substrate = [
            i for i in bundle.advisory_issues
            if i.get("category") == "specialist_substrate"
        ]
        assert len(substrate) >= 1, (
            "Specialist substrate failure must never be silently dropped"
        )
        hang = [
            i for i in substrate
            if i["details"].get("agent") == "test-orchestrator"
        ]
        assert len(hang) == 1
        assert hang[0]["severity"] == "should_fix"
        assert HANG_ERROR in hang[0]["description"]
        assert "not a Player honesty issue" in hang[0]["description"]
        # The benignly-synthesized "skipped" Phase 5 record does NOT
        # advise — only genuine failures (hang/crash) do. The
        # phase-absence signal for skips is the agent-invocations
        # advisory's job.
        skipped = [
            i for i in substrate
            if i["details"].get("status") == "skipped"
        ]
        assert skipped == []


class TestGenuineFabricationStillShortCircuits:
    """AC-004: real Player test-claim fabrication keeps the abort."""

    def test_fabricated_test_file_still_aborts(self, worktree: Path) -> None:
        results = _run2_task_work_results(worktree)
        # No specialist injection in scope; the Player fabricates a test
        # file claim outright.
        results["agent_invocations"] = []
        results["agent_invocations_validation"] = {"status": "passed"}
        results["completion_promises"][0]["test_file"] = (
            "tests/test_never_written.py"
        )
        _write_results(worktree, results)

        bundle = _gather(worktree)

        assert bundle.gathering_status == "partial_honesty_abort"
        critical = [
            d for d in bundle.honesty.discrepancies
            if d.severity == "critical"
        ]
        assert len(critical) == 1
        assert critical[0].claim_type == "claim_audit"
        assert "tests/test_never_written.py" in critical[0].player_claim
