"""When the quality gates fail, the Player is told which tests failed.

Modelled on build FEAT-895D (7 October 2026, trimmed and renamed). One test,
outside the task's own area, was failing. The test phase named it in
``specialist_results.json``. The Player never saw the name, for three
reasons, each pinned here:

1. The gate's own test-failure issue said only "Tests did not pass during
   task-work execution" — the names never left the test phase's record.
2. The gate's deterministic feedback was refused by the partial-gate-abort
   replacement, because the renderer had since added two coverage fields and
   the replacement demanded exactly five. The Player got the model's
   narrative instead: honesty warnings and nothing about the test.
3. The feedback text kept the first three issues in report order, so even a
   test-failure issue would have been cut behind three honesty warnings, and
   the feedback file's ``must_fix`` list was always empty for text feedback.

The tests drive the real merge, the real gate renderer, the real
replacement, the real feedback text and the real feedback file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from guardkit.models.task_types import TaskType, get_profile
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.coach_narrative_reconciler import DETERMINISTIC_SOURCE
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.failing_test_feedback import (
    FAILING_TESTS_SHOWN,
    MUST_FIX_MARKER,
    QG_FAILING_TESTS,
    QG_FAILURE_SUMMARY,
    describe_failing_tests,
    must_fix_items,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


TASK_ID = "TASK-FTP-002"
FAILING = (
    "tests/test_settings.py::TestTheDefaultAddress::"
    "test_nothing_set_gives_the_in_memory_default"
)


# ---------------------------------------------------------------------------
# Fixtures modelled on the FEAT-895D records
# ---------------------------------------------------------------------------


def _phase_4_failed(names: List[str]) -> Dict[str, Any]:
    """specialist_results.json's phase_4 block for a whole-suite red run."""
    return {
        "status": "failed",
        "duration_seconds": 82.3,
        "error": (
            "tests failed (deterministic Phase 4): 1 failed, 0 already "
            "failing on the base, 1 newly failing: " + ", ".join(names[:10])
        ),
        "tests_run": 1027,
        "tests_failed": len(names),
        "tests_skipped": 0,
        "test_command": "qa/run-suite.sh",
        "test_command_source": "repository toolchain declaration",
        "failures_total": len(names),
        "failures_inherited": 0,
        "failures_new": len(names),
        "new_failing_tests": list(names),
        "stale_base_entries": [],
        "coverage_pct": 0.0,
        "output_summary": (
            "Error detail:\n>           assert str(engine.url) == DEFAULT_URL\n"
            "E           AssertionError: assert 'memory%3A' == 'memory:'\n"
        ),
        "quality_gates_passed": False,
    }


def _seed(worktree: Path, phase_4: Dict[str, Any], narrative_green: bool) -> Path:
    TaskArtifactPaths.ensure_autobuild_dir(TASK_ID, worktree)
    results_path = TaskArtifactPaths.task_work_results_path(TASK_ID, worktree)
    results_path.write_text(json.dumps({
        "task_id": TASK_ID,
        "completed": True,
        "task_type": "feature",
        "files_modified": ["src/items/router.py"],
        "files_created": [],
        "quality_gates": {
            "tests_passing": narrative_green,
            "tests_passed": 1026,
            "tests_failed": 0 if narrative_green else 1,
            "coverage": 0.0,
            "coverage_met": False,
            "all_passed": narrative_green,
        },
    }, indent=2))
    autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(TASK_ID, worktree)
    (autobuild_dir / "specialist_results.json").write_text(
        json.dumps({"phase_4": phase_4}, indent=2)
    )
    return results_path


def _honesty_record(path: str) -> Dict[str, Any]:
    """One of the advisory honesty warnings that crowded out the test."""
    return {
        "severity": "should_fix",
        "category": "honesty",
        "description": (
            "Deterministic honesty record (claim_audit_unmodified, "
            f"severity=should_fix): Player claimed file {path}."
        ),
        "details": {
            "source": DETERMINISTIC_SOURCE,
            "claim_type": "claim_audit_unmodified",
            "severity": "should_fix",
        },
    }


# ---------------------------------------------------------------------------
# The shared wording
# ---------------------------------------------------------------------------


class TestTheWording:
    def test_one_name_and_the_failure_line(self) -> None:
        text = describe_failing_tests([FAILING], "AssertionError: a != b")
        assert text == (
            f"1 failing test: {FAILING}. "
            "What the test run said: AssertionError: a != b"
        )

    def test_names_are_bounded_and_the_full_count_is_said(self) -> None:
        names = [f"tests/t.py::test_{i}" for i in range(14)]
        text = describe_failing_tests(names, "")
        assert text.startswith("14 failing tests: ")
        assert f"tests/t.py::test_{FAILING_TESTS_SHOWN - 1}" in text
        assert f"tests/t.py::test_{FAILING_TESTS_SHOWN};" not in text
        assert text.endswith("; and 4 more.")

    def test_nothing_reported_says_nothing(self) -> None:
        assert describe_failing_tests([], None) == ""

    def test_must_fix_items_read_back_only_marked_lines(self) -> None:
        text = (
            f"- {MUST_FIX_MARKER}Tests did not pass:\n"
            "  • tests/a.py::test_x\n"
            "- an advisory\n"
            f"- {MUST_FIX_MARKER}Coverage threshold not met\n"
            "... and 2 more issues"
        )
        assert must_fix_items(text) == [
            "Tests did not pass:\n• tests/a.py::test_x",
            "Coverage threshold not met",
        ]

    def test_unmarked_text_gives_no_items(self) -> None:
        assert must_fix_items("- Edge case not covered") == []


# ---------------------------------------------------------------------------
# 1. The names reach the gate's own feedback
# ---------------------------------------------------------------------------


class TestTheNamesReachTheGate:
    @pytest.mark.parametrize("narrative_green", [True, False])
    def test_merge_copies_the_test_phase_names(
        self, tmp_path: Path, narrative_green: bool
    ) -> None:
        """Whether or not the Player's own story said green, the names the
        test phase reported are carried beside the gate's counts."""
        results_path = _seed(tmp_path, _phase_4_failed([FAILING]), narrative_green)
        AgentInvoker(worktree_path=tmp_path)._inject_specialist_records_into_task_work_results(
            TASK_ID
        )
        qg = json.loads(results_path.read_text())["quality_gates"]
        assert qg[QG_FAILING_TESTS] == [FAILING]
        assert qg[QG_FAILURE_SUMMARY].startswith("Error detail: > assert")
        assert "\n" not in qg[QG_FAILURE_SUMMARY]

    def test_a_later_pass_removes_the_names(self, tmp_path: Path) -> None:
        results_path = _seed(tmp_path, _phase_4_failed([FAILING]), True)
        invoker = AgentInvoker(worktree_path=tmp_path)
        invoker._inject_specialist_records_into_task_work_results(TASK_ID)
        (TaskArtifactPaths.ensure_autobuild_dir(TASK_ID, tmp_path)
         / "specialist_results.json").write_text(json.dumps({"phase_4": {
             "status": "passed", "duration_seconds": 5.0, "error": None,
             "tests_run": 1028, "tests_failed": 0,
         }}))
        invoker._inject_specialist_records_into_task_work_results(TASK_ID)
        qg = json.loads(results_path.read_text())["quality_gates"]
        assert QG_FAILING_TESTS not in qg
        assert QG_FAILURE_SUMMARY not in qg

    def test_an_absent_test_signal_names_nothing(self, tmp_path: Path) -> None:
        phase_4 = {
            "status": "failed",
            "error": "absent test signal (deterministic Phase 4): no tests ran",
            "signal_absent": True,
            "tests_run": 0,
            "tests_failed": 0,
        }
        results_path = _seed(tmp_path, phase_4, True)
        AgentInvoker(worktree_path=tmp_path)._inject_specialist_records_into_task_work_results(
            TASK_ID
        )
        qg = json.loads(results_path.read_text())["quality_gates"]
        assert QG_FAILING_TESTS not in qg

    def test_the_gate_issue_names_the_failing_test(self, tmp_path: Path) -> None:
        results_path = _seed(tmp_path, _phase_4_failed([FAILING]), True)
        AgentInvoker(worktree_path=tmp_path)._inject_specialist_records_into_task_work_results(
            TASK_ID
        )
        results = json.loads(results_path.read_text())
        validator = CoachValidator(str(tmp_path), task_id=TASK_ID)
        gates = validator.verify_quality_gates(
            results, profile=get_profile(TaskType.FEATURE)
        )
        assert gates.tests_passed is False

        feedback = validator._feedback_from_gates(
            TASK_ID, 1, gates, results, task_type="feature"
        )
        issue = next(i for i in feedback.issues if i["category"] == "test_failure")
        assert issue["severity"] == "must_fix"
        assert issue["description"].startswith(
            "Tests did not pass during task-work execution. 1 failing test: "
        )
        assert FAILING in issue["description"]
        assert "AssertionError" in issue["description"]
        assert issue["details"]["failing_tests"] == [FAILING]
        assert issue["details"]["failing_test_count"] == 1

    def test_without_names_the_issue_reads_as_before(self, tmp_path: Path) -> None:
        validator = CoachValidator(str(tmp_path), task_id=TASK_ID)
        results = {
            "task_id": TASK_ID,
            "quality_gates": {
                "tests_passing": False, "tests_passed": 3, "tests_failed": 1,
                "coverage_met": True, "all_passed": False,
            },
        }
        gates = validator.verify_quality_gates(
            results, profile=get_profile(TaskType.FEATURE)
        )
        feedback = validator._feedback_from_gates(
            TASK_ID, 1, gates, results, task_type="feature"
        )
        issue = next(i for i in feedback.issues if i["category"] == "test_failure")
        assert issue["description"] == "Tests did not pass during task-work execution"
        assert issue["details"] == {"failed_count": 1, "total_count": 4}


# ---------------------------------------------------------------------------
# 2 and 3. The gate's feedback replaces the narrative, and reaches must_fix
# ---------------------------------------------------------------------------


def test_the_failing_test_reaches_the_players_must_fix_list(tmp_path: Path) -> None:
    """End to end over the FEAT-895D shape."""
    results_path = _seed(tmp_path, _phase_4_failed([FAILING]), True)
    invoker = AgentInvoker(worktree_path=tmp_path)
    invoker._inject_specialist_records_into_task_work_results(TASK_ID)
    results = json.loads(results_path.read_text())

    # The real renderer, so the payload carries every field it really
    # writes — the two coverage fields included.
    validator = CoachValidator(str(tmp_path), task_id=TASK_ID)
    gates = validator.verify_quality_gates(
        results, profile=get_profile(TaskType.FEATURE)
    )
    gate_feedback = validator._feedback_from_gates(
        TASK_ID, 1, gates, results, task_type="feature"
    ).to_dict()
    assert "coverage_receipt" in gate_feedback["validation_results"]["quality_gates"]
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="partial_gate_abort",
        quality_gates=gates,
        gate_feedback=gate_feedback,
    )

    # What the model wrote on FEAT-895D turn 1: honesty warnings and a
    # finding that names only the gathering status.
    decision: Dict[str, Any] = {
        "task_id": TASK_ID,
        "turn": 1,
        "decision": "feedback",
        "rationale": "Quality gates failed.",
        "issues": [
            _honesty_record("src/db/session.py"),
            _honesty_record("src/items/crud.py"),
            _honesty_record("src/items/errors.py"),
            _honesty_record("src/items/schemas.py"),
            {
                "type": "finding",
                "severity": "major",
                "description": 'gathering_status="partial_gate_abort"',
            },
        ],
    }
    coach_path = tmp_path / "coach_turn_1.json"
    invoker._reconcile_incomplete_evidence_gathering(
        decision=decision,
        evidence_bundle=bundle,
        task_id=TASK_ID,
        turn=1,
        coach_output_path=coach_path,
    )

    # The gate's own feedback replaced the narrative, and is on disk.
    categories = [i.get("category") for i in decision["issues"]]
    assert "test_failure" in categories
    assert json.loads(coach_path.read_text())["issues"] == decision["issues"]

    # The narrative reconciler puts the honesty records back in front, as it
    # did on FEAT-895D. The test failure must still lead the Player's text.
    decision["issues"] = [
        _honesty_record("src/db/session.py"),
        _honesty_record("src/items/crud.py"),
        _honesty_record("src/items/errors.py"),
        *decision["issues"],
    ]
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    text = orchestrator._extract_feedback(decision)
    first = text.splitlines()[0]
    assert first.startswith(
        f"- {MUST_FIX_MARKER}Tests did not pass during task-work execution."
    )
    assert FAILING in first
    assert "honesty record" not in "\n".join(text.splitlines()[:3])

    # And the feedback file the Player reads lists it under must_fix.
    feedback_path = invoker._write_coach_feedback(TASK_ID, 2, text)
    written = json.loads(feedback_path.read_text())
    assert written["must_fix"], "must_fix must not be empty"
    assert FAILING in written["must_fix"][0]["issue"]


def test_a_payload_with_an_invented_gate_field_is_still_refused(
    tmp_path: Path,
) -> None:
    """Accepting the renderer's two coverage fields does not open the door
    to anything else: an unknown field still falls back to the fail-closed
    framing."""
    validator = CoachValidator(str(tmp_path), task_id=TASK_ID)
    results = {
        "task_id": TASK_ID,
        "quality_gates": {
            "tests_passing": False, "tests_passed": 3, "tests_failed": 1,
            "coverage_met": True, "all_passed": False,
        },
    }
    gates = validator.verify_quality_gates(
        results, profile=get_profile(TaskType.FEATURE)
    )
    gate_feedback = validator._feedback_from_gates(
        TASK_ID, 1, gates, results, task_type="feature"
    ).to_dict()
    gate_feedback["validation_results"]["quality_gates"]["invented"] = True
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="partial_gate_abort",
        quality_gates=gates,
        gate_feedback=gate_feedback,
    )
    decision: Dict[str, Any] = {
        "task_id": TASK_ID, "turn": 1, "decision": "feedback",
        "rationale": "r", "issues": [],
    }
    AgentInvoker(worktree_path=tmp_path)._reconcile_incomplete_evidence_gathering(
        decision=decision,
        evidence_bundle=bundle,
        task_id=TASK_ID,
        turn=1,
        coach_output_path=tmp_path / "coach_turn_1.json",
    )
    assert decision["issues"] == []
    assert decision["rationale"] == "r"


def test_a_mismatched_coverage_receipt_is_refused(tmp_path: Path) -> None:
    validator = CoachValidator(str(tmp_path), task_id=TASK_ID)
    results = {
        "task_id": TASK_ID,
        "quality_gates": {
            "tests_passing": False, "tests_passed": 3, "tests_failed": 1,
            "coverage_met": True, "all_passed": False,
        },
    }
    gates = validator.verify_quality_gates(
        results, profile=get_profile(TaskType.FEATURE)
    )
    gate_feedback = validator._feedback_from_gates(
        TASK_ID, 1, gates, results, task_type="feature"
    ).to_dict()
    gate_feedback["validation_results"]["quality_gates"]["coverage_receipt"] = {
        "command": "something else"
    }
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="partial_gate_abort",
        quality_gates=gates,
        gate_feedback=gate_feedback,
    )
    decision: Dict[str, Any] = {
        "task_id": TASK_ID, "turn": 1, "decision": "feedback",
        "rationale": "r", "issues": [],
    }
    AgentInvoker(worktree_path=tmp_path)._reconcile_incomplete_evidence_gathering(
        decision=decision,
        evidence_bundle=bundle,
        task_id=TASK_ID,
        turn=1,
        coach_output_path=tmp_path / "coach_turn_1.json",
    )
    assert decision["issues"] == []
