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
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
import yaml

from guardkit.models.task_types import TaskType, get_profile
from guardkit.orchestrator import specialist_invocations as si
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.coach_narrative_reconciler import DETERMINISTIC_SOURCE
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.failing_test_feedback import (
    FAILING_TESTS_SHOWN,
    FAILING_TESTS_TEXT_BUDGET,
    MUST_FIX_ITEM_LIMIT,
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
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain


TASK_ID = "TASK-FTP-002"
FAILING = (
    "tests/test_settings.py::TestTheDefaultAddress::"
    "test_nothing_set_gives_the_in_memory_default"
)


# ---------------------------------------------------------------------------
# Fixtures modelled on the FEAT-895D records
# ---------------------------------------------------------------------------


def _phase_4_failed(names: List[str]) -> Dict[str, Any]:
    """specialist_results.json's phase_4 block for a whole-suite red run.

    Shaped like the FEAT-895D record, which was written before the test phase
    recorded ``failing_tests``; only ``new_failing_tests`` names the failure.
    """
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
            "What the test run said: AssertionError: a != b. "
            f"1 failing test: {FAILING}."
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

    def test_multi_line_failure_text_is_kept_whole_and_bounded(self) -> None:
        """Test output under a must-fix issue is often several lines, only
        the first of them indented; all of it belongs to the item."""
        text = (
            f"- {MUST_FIX_MARKER}Test failure in the items area:\n"
            "  >       assert response.status_code == 404\n"
            "E       assert 500 == 404\n"
            "E        +  where 500 = <Response>.status_code\n"
            "- an advisory\n"
            f"- {MUST_FIX_MARKER}" + "x" * 5000 + "\n"
            "\n"
            "Command failures this turn: none worth reporting"
        )
        items = must_fix_items(text)
        assert items[0] == (
            "Test failure in the items area:\n"
            ">       assert response.status_code == 404\n"
            "E       assert 500 == 404\n"
            "E        +  where 500 = <Response>.status_code"
        )
        assert len(items) == 2
        assert len(items[1]) == MUST_FIX_ITEM_LIMIT
        assert "Command failures" not in items[1]


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
            "Tests did not pass during task-work execution. "
            "What the test run said: Error detail: "
        )
        assert issue["description"].endswith(
            "1 newly failing test (not failing before this build started): "
            f"{FAILING}."
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
    assert "honesty record" not in first

    # And the feedback file the Player reads lists it under must_fix, and
    # only it: no coverage must-fix from a run whose tests failed.
    feedback_path = invoker._write_coach_feedback(TASK_ID, 2, text)
    written = json.loads(feedback_path.read_text())
    assert written["must_fix"], "must_fix must not be empty"
    assert FAILING in written["must_fix"][0]["issue"]
    assert not any(
        "Coverage" in item["issue"] for item in written["must_fix"]
    )
    assert "Coverage threshold not met" not in text


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


# ---------------------------------------------------------------------------
# A test phase that ran and failed is not "missing evidence"
# ---------------------------------------------------------------------------


def _substrate_advisories(tmp_path: Path, phase_4: Dict[str, Any]) -> List[Dict[str, Any]]:
    results_path = _seed(tmp_path, phase_4, True)
    AgentInvoker(worktree_path=tmp_path)._inject_specialist_records_into_task_work_results(
        TASK_ID
    )
    results = json.loads(results_path.read_text())
    validator = CoachValidator(str(tmp_path), task_id=TASK_ID)
    return [
        a for a in validator._compute_specialist_failure_advisories(results)
        if a["category"] == "specialist_substrate"
    ]


def test_a_failed_test_run_is_not_reported_as_missing_evidence(
    tmp_path: Path,
) -> None:
    """FEAT-895D's turns carried "did not produce evidence ... not a Player
    honesty issue" for a test phase that ran 1027 tests and saw one fail. That
    told the Player the failure was not its problem."""
    assert _substrate_advisories(tmp_path, _phase_4_failed([FAILING])) == []


def test_a_failed_run_that_named_no_tests_is_still_evidence(tmp_path: Path) -> None:
    """A run of the task's own tests reports counts but no names; it still
    ran and failed."""
    phase_4 = _phase_4_failed([])
    phase_4["tests_failed"] = 2
    assert _substrate_advisories(tmp_path, phase_4) == []


@pytest.mark.parametrize(
    "phase_4",
    [
        {
            "status": "failed",
            "duration_seconds": 300.0,
            "error": "hang detected (no model activity for 162s)",
            "tests_run": 0,
            "tests_failed": 0,
        },
        {
            "status": "failed",
            "error": "absent test signal (deterministic Phase 4): no tests ran",
            "signal_absent": True,
            "tests_run": 0,
            "tests_failed": 0,
        },
    ],
    ids=["hung", "absent"],
)
def test_a_test_phase_that_left_nothing_is_still_reported(
    tmp_path: Path, phase_4: Dict[str, Any]
) -> None:
    """Where the phase really did not run or left nothing behind, the
    warning is still right and still emitted."""
    advisories = _substrate_advisories(tmp_path, phase_4)
    assert len(advisories) == 1
    assert "did not produce evidence" in advisories[0]["description"]


# ---------------------------------------------------------------------------
# Coverage is not judged from a failed test run
# ---------------------------------------------------------------------------


def _gate_issues(tmp_path: Path, results: Dict[str, Any]) -> List[Dict[str, Any]]:
    validator = CoachValidator(str(tmp_path), task_id=TASK_ID)
    gates = validator.verify_quality_gates(
        results, profile=get_profile(TaskType.FEATURE)
    )
    return validator._feedback_from_gates(
        TASK_ID, 1, gates, results, task_type="feature"
    ).issues, gates


def test_a_failed_test_run_gives_no_coverage_must_fix(tmp_path: Path) -> None:
    """The FEAT-895D shape: the Player's report claimed everything passed,
    the test phase ran and one test failed, and the merge marked coverage as
    not met. The coder is told about the failing test, not about coverage;
    the gate itself still fails."""
    results_path = _seed(tmp_path, _phase_4_failed([FAILING]), True)
    AgentInvoker(worktree_path=tmp_path)._inject_specialist_records_into_task_work_results(
        TASK_ID
    )
    results = json.loads(results_path.read_text())
    assert results["quality_gates"]["coverage_met"] is False

    issues, gates = _gate_issues(tmp_path, results)
    categories = [i["category"] for i in issues]
    assert "test_failure" in categories
    assert "coverage" not in categories
    assert gates.coverage_met is False
    assert gates.all_gates_passed is False


def test_a_real_coverage_shortfall_is_still_reported(tmp_path: Path) -> None:
    """Tests passed and the measured coverage is below the threshold: the
    coverage must-fix is exactly as before."""
    results = {
        "task_id": TASK_ID,
        "quality_gates": {
            "tests_passing": True, "tests_passed": 12, "tests_failed": 0,
            "coverage": 62.5, "line_coverage": 62.5,
            "coverage_met": False, "all_passed": True,
        },
    }
    issues, _ = _gate_issues(tmp_path, results)
    coverage = [i for i in issues if i["category"] == "coverage"]
    assert len(coverage) == 1
    assert coverage[0]["severity"] == "must_fix"
    assert coverage[0]["description"] == "Coverage threshold not met"
    assert coverage[0]["details"]["line_coverage"] == 62.5


def test_a_planted_ran_and_failed_flag_is_removed_by_the_merge(
    tmp_path: Path,
) -> None:
    """The flag that silences the coverage line is the merge's, rebuilt from
    the test phase's own record every turn; one written into the Player's
    report does not survive a passing test phase."""
    results_path = _seed(tmp_path, {
        "status": "passed", "duration_seconds": 5.0, "error": None,
        "tests_run": 12, "tests_failed": 0,
    }, True)
    data = json.loads(results_path.read_text())
    data["quality_gates"]["test_phase_ran_and_failed"] = True
    results_path.write_text(json.dumps(data))
    AgentInvoker(worktree_path=tmp_path)._inject_specialist_records_into_task_work_results(
        TASK_ID
    )
    qg = json.loads(results_path.read_text())["quality_gates"]
    assert "test_phase_ran_and_failed" not in qg


# ---------------------------------------------------------------------------
# Through the real test phase: red baselines, no baseline, own-test runs
# ---------------------------------------------------------------------------

_LEG_TASK = "TASK-LEG-0002"
_LEG_FEATURE = "FEAT-LEG2"
_INHERITED = "tests/test_orders.py::test_totals"
_NEW = "tests/test_users.py::test_delete_twice"
_TWO_RED = (
    f"FAILED {_NEW} - AssertionError: deleted twice\n"
    f"FAILED {_INHERITED} - AssertionError\n"
    "2 failed, 3 passed in 1.20s\n"
)


def _leg_repo(tmp_path: Path) -> tuple:
    root = tmp_path / "target-repo"
    worktree = root / ".guardkit" / "worktrees" / _LEG_TASK
    worktree.mkdir(parents=True)
    return root, worktree


def _declare_suite(root: Path, worktree: Path, output: str, exit_code: int) -> None:
    """A declared ``bash qa/run-suite.sh`` that prints ``output``."""
    cfg = root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"test": "bash qa/run-suite.sh"}}),
        encoding="utf-8",
    )
    snapshot_task_toolchain(_LEG_TASK, worktree, root)
    qa = worktree / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"echo {line!r}" for line in output.splitlines())
    script = qa / "run-suite.sh"
    script.write_text(f"#!/bin/sh\n{body}\nexit {exit_code}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)


def _red_baseline(worktree: Path, failing: List[str]) -> None:
    path = worktree / ".guardkit" / "autobuild" / _LEG_FEATURE / "baseline.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "command": "bash qa/run-suite.sh",
        "expected_exit": 0,
        "passed": False,
        "exit_code": 1,
        "failing_node_ids": failing,
        "failing_count": len(failing),
        "timestamp": "2026-10-08T00:00:00",
    }), encoding="utf-8")


def _player_claimed_green(worktree: Path, files: List[str]) -> Path:
    TaskArtifactPaths.ensure_autobuild_dir(_LEG_TASK, worktree)
    path = TaskArtifactPaths.task_work_results_path(_LEG_TASK, worktree)
    path.write_text(json.dumps({
        "task_id": _LEG_TASK,
        "completed": True,
        "task_type": "feature",
        "files_modified": files,
        "files_created": [],
        "quality_gates": {
            "tests_passing": True, "tests_passed": 5, "tests_failed": 0,
            "coverage": 91.0, "coverage_met": True, "all_passed": True,
        },
        "code_review": {"score": 90},
    }), encoding="utf-8")
    return path


def _run_test_phase(worktree: Path) -> Dict[str, Any]:
    invoker = MagicMock()
    invoker._venv_python = None
    block = si._run_deterministic_phase_4(
        worktree_path=worktree,
        task_id=_LEG_TASK,
        agent_invoker=invoker,
        sdk_timeout=120,
        turn=1,
    )
    assert block is not None
    autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(_LEG_TASK, worktree)
    (autobuild_dir / "specialist_results.json").write_text(
        json.dumps({"phase_4": block})
    )
    return block


def _next_turn_must_fix(worktree: Path, results_path: Path):
    """Merge, gates, gate feedback, replacement, text, feedback file."""
    invoker = AgentInvoker(worktree_path=worktree)
    invoker._inject_specialist_records_into_task_work_results(_LEG_TASK)
    results = json.loads(results_path.read_text())
    validator = CoachValidator(str(worktree), task_id=_LEG_TASK)
    gates = validator.verify_quality_gates(
        results, profile=get_profile(TaskType.FEATURE)
    )
    assert gates.all_gates_passed is False
    gate_feedback = validator._feedback_from_gates(
        _LEG_TASK, 1, gates, results, task_type="feature"
    ).to_dict()
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="partial_gate_abort",
        quality_gates=gates,
        gate_feedback=gate_feedback,
    )
    decision: Dict[str, Any] = {
        "task_id": _LEG_TASK, "turn": 1, "decision": "feedback",
        "rationale": "Quality gates failed.",
        "issues": [{
            "type": "finding", "severity": "major",
            "description": 'gathering_status="partial_gate_abort"',
        }],
    }
    invoker._reconcile_incomplete_evidence_gathering(
        decision=decision,
        evidence_bundle=bundle,
        task_id=_LEG_TASK,
        turn=1,
        coach_output_path=worktree / "coach_turn_1.json",
    )
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    text = orchestrator._extract_feedback(decision)
    written = json.loads(
        invoker._write_coach_feedback(_LEG_TASK, 2, text).read_text()
    )
    return gates, text, [item["issue"] for item in written["must_fix"]]


def test_a_red_baseline_still_names_the_newly_failing_test(tmp_path: Path) -> None:
    """External review R1. One test was already failing before the build
    started; the task broke another; the Player claimed success. With a red
    baseline on record the count gate is deferred to the independent run,
    and the merge marks coverage as not met, so gathering stops before that
    run. The Player must still be told about the new failure, with the
    failure line, without a coverage line, and without the inherited test."""
    root, worktree = _leg_repo(tmp_path)
    _declare_suite(root, worktree, _TWO_RED, 1)
    _red_baseline(worktree, [_INHERITED])
    results_path = _player_claimed_green(worktree, ["app/users.py"])

    block = _run_test_phase(worktree)
    assert block["status"] == "failed"
    assert block["failing_tests"] == [_NEW]
    assert block["failing_tests_basis"] == "new since the base"

    gates, text, must_fix = _next_turn_must_fix(worktree, results_path)
    # The count gate really was deferred: this is the case under test.
    assert gates.tests_passed is True
    assert gates.coverage_met is False

    assert len(must_fix) == 1, must_fix
    assert _NEW in must_fix[0]
    assert "newly failing" in must_fix[0]
    assert (
        "What the test run said: tests failed (deterministic Phase 4): "
        "2 failed, 1 already failing on the base, 1 newly failing"
    ) in must_fix[0]
    assert _INHERITED not in must_fix[0]
    assert "Coverage" not in text
    assert _INHERITED not in text


def test_with_no_baseline_every_failing_test_is_named(tmp_path: Path) -> None:
    """External review R2, first case: a failed declared-suite run with
    nothing on record about the base still names what failed."""
    root, worktree = _leg_repo(tmp_path)
    _declare_suite(root, worktree, _TWO_RED, 1)
    results_path = _player_claimed_green(worktree, ["app/users.py"])

    block = _run_test_phase(worktree)
    assert block["status"] == "failed"
    assert sorted(block["failing_tests"]) == sorted([_NEW, _INHERITED])
    assert block["failing_tests_total"] == 2
    assert block["failing_tests_basis"] == "observed"

    _, _, must_fix = _next_turn_must_fix(worktree, results_path)
    assert must_fix[0].startswith(
        "Tests did not pass during task-work execution. What the test run said: "
    )
    assert "2 failing tests: " in must_fix[0]
    assert _NEW in must_fix[0] and _INHERITED in must_fix[0]


def test_a_run_of_the_tasks_own_tests_names_what_failed(tmp_path: Path) -> None:
    """External review R2, second case: nothing declared, so the test phase
    runs the task's own test file with the project's interpreter (a real
    pytest run here); its failing test is named."""
    root, worktree = _leg_repo(tmp_path)
    (worktree / "pyproject.toml").write_text("[project]\nname='x'\n")
    tests_dir = worktree / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_leg_0002_thing.py").write_text(
        "def test_ok():\n    pass\n\n"
        "def test_breaks():\n    assert 'a' == 'b'\n"
    )
    venv_python = worktree / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.symlink_to(sys.executable)
    results_path = _player_claimed_green(
        worktree, ["tests/test_leg_0002_thing.py"]
    )

    block = _run_test_phase(worktree)
    assert block["status"] == "failed"
    assert block["test_command_source"] != "repository toolchain declaration"
    assert block["failing_tests"] == [
        "tests/test_leg_0002_thing.py::test_breaks"
    ]
    assert block["failing_tests_basis"] == "observed"

    _, _, must_fix = _next_turn_must_fix(worktree, results_path)
    assert "tests/test_leg_0002_thing.py::test_breaks" in must_fix[0]


def test_a_tool_whose_output_names_no_test_is_said_so(tmp_path: Path) -> None:
    """A test tool whose output the factory cannot read names from: the
    Player is told that, not left with silence."""
    root, worktree = _leg_repo(tmp_path)
    _declare_suite(
        root, worktree, "suite: 1 case did not hold (orders/totals)\n", 1
    )
    results_path = _player_claimed_green(worktree, ["app/orders.py"])

    block = _run_test_phase(worktree)
    assert block["status"] == "failed"
    assert block["failing_tests"] == []

    _, _, must_fix = _next_turn_must_fix(worktree, results_path)
    assert "did not name its failing tests" in must_fix[0]


def test_long_test_names_never_push_out_the_failure_line(tmp_path: Path) -> None:
    """External review R3. Ten 220-character test IDs used to come before
    the failure line, and the 2,000-character read-back cut the item in the
    middle of a name, dropping the failure line altogether. Through the real
    gate feedback, feedback text and read-back: the failure line is kept,
    every listed name is whole, and the ones left out are counted."""
    stem = "tests/test_long.py::TestAVeryLongClassName::test_"
    names = [
        f"{stem}{i:02d}_" + "x" * (220 - len(stem) - 3) for i in range(10)
    ]
    assert all(len(n) == 220 for n in names)
    validator = CoachValidator(str(tmp_path), task_id=TASK_ID)
    results = {
        "task_id": TASK_ID,
        "quality_gates": {
            "tests_passing": False, "tests_passed": 3, "tests_failed": 10,
            "coverage_met": True, "all_passed": False,
            "failing_tests": names,
            "failing_tests_total": 10,
            "failing_tests_basis": "observed",
            "failure_summary": "AssertionError: expected 200, got 500",
            "test_phase_ran_and_failed": True,
        },
    }
    gates = validator.verify_quality_gates(
        results, profile=get_profile(TaskType.FEATURE)
    )
    report = validator._feedback_from_gates(
        TASK_ID, 1, gates, results, task_type="feature"
    ).to_dict()
    text = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)._extract_feedback(
        report
    )
    written = json.loads(
        AgentInvoker(worktree_path=tmp_path)
        ._write_coach_feedback(TASK_ID, 2, text)
        .read_text()
    )
    item = written["must_fix"][0]["issue"]

    assert len(item) <= MUST_FIX_ITEM_LIMIT
    assert item.startswith(
        "Tests did not pass during task-work execution. What the test run "
        "said: AssertionError: expected 200, got 500. 10 failing tests: "
    )
    listed_part = item.split("10 failing tests: ", 1)[1]
    assert listed_part.endswith(" more.")
    listed, _, omitted = listed_part.rpartition("; and ")
    listed_names = listed.split("; ")
    assert 0 < len(listed_names) < 10
    assert all(n in names for n in listed_names), "a name was cut"
    assert omitted == f"{10 - len(listed_names)} more."
    assert FAILING_TESTS_TEXT_BUDGET < MUST_FIX_ITEM_LIMIT
