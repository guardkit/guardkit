"""When the project's required tests ran and failed, the Player is told which.

Since the cull (27 October 2026) the turn is sent back for failing tests only
through the project's own test run: the Coach's evidence run of the declared
test command (``CoachValidator.gather_evidence``), the required-suite guard
(``AgentInvoker._apply_independent_test_code_failure_guard``), the run's own
failure receipt copied into the report
(``AutoBuildOrchestrator._merge_evidence_test_signal_into_report``), the
Player's feedback text (``_turn_feedback_text``) and the feedback file
(``AgentInvoker._write_coach_feedback``). The quality-gate path that read the
test phase's record and the Player's report is gone, with its tests.

The tests here drive those real steps over a real declared test command.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any, Dict

import yaml

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.failing_test_feedback import (
    INDEPENDENT_FAILURE_OPENING,
    MUST_FIX_ITEM_LIMIT,
    MUST_FIX_MARKER,
    SUITE_RECEIPT_KEY,
    must_fix_items,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain


# ---------------------------------------------------------------------------
# Reading must-fix items back from the feedback text
# ---------------------------------------------------------------------------


class TestTheWording:
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
# Through the project's own test run
# ---------------------------------------------------------------------------

_TASK = "TASK-LEG-0002"
_NEW = "tests/test_users.py::test_delete_twice"
_OTHER = "tests/test_orders.py::test_totals"
_TWO_RED = (
    f"FAILED {_NEW} - AssertionError: deleted twice\n"
    f"FAILED {_OTHER} - AssertionError\n"
    "2 failed, 3 passed in 1.20s\n"
)


def _leg_repo(tmp_path: Path) -> tuple:
    root = tmp_path / "target-repo"
    worktree = root / ".guardkit" / "worktrees" / _TASK
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
    snapshot_task_toolchain(_TASK, worktree, root)
    qa = worktree / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"echo {line!r}" for line in output.splitlines())
    script = qa / "run-suite.sh"
    script.write_text(f"#!/bin/sh\n{body}\nexit {exit_code}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)


def _turn(worktree: Path) -> Dict[str, Any]:
    """One Coach turn over the real evidence run, with the reviewer approving.

    The task changed a file in the root part (the worktree is not a git
    checkout, so the builder's report names it), so the root's declared
    suite is what runs (31 October 2026)."""
    from guardkit.orchestrator.paths import TaskArtifactPaths

    results = TaskArtifactPaths.task_work_results_path(_TASK, worktree)
    results.parent.mkdir(parents=True, exist_ok=True)
    results.write_text(json.dumps({"files_modified": ["src/users.py"]}))
    bundle = CoachValidator(str(worktree), task_id=_TASK).gather_evidence(
        task_id=_TASK, turn=1, task={"acceptance_criteria": [], "task_type": "feature"},
    )
    invoker = AgentInvoker(worktree_path=worktree)
    decision: Dict[str, Any] = {
        "task_id": _TASK, "turn": 1, "decision": "approve", "issues": [],
        "rationale": "Looks complete.",
    }
    invoker._apply_independent_test_code_failure_guard(
        decision=decision,
        evidence_bundle=bundle,
        task_id=_TASK,
        turn=1,
        coach_output_path=worktree / "coach_turn_1.json",
    )
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orchestrator._merge_evidence_test_signal_into_report(decision, bundle)
    return {"bundle": bundle, "decision": decision, "invoker": invoker,
            "orchestrator": orchestrator}


def _player_reads(turn: Dict[str, Any]) -> tuple:
    text = turn["orchestrator"]._turn_feedback_text(turn["decision"], 1)
    written = json.loads(
        turn["invoker"]._write_coach_feedback(_TASK, 2, text).read_text()
    )
    return text, [item["issue"] for item in written["must_fix"]]


def test_a_red_declared_suite_sends_the_turn_back_naming_the_failing_tests(
    tmp_path: Path,
) -> None:
    root, worktree = _leg_repo(tmp_path)
    _declare_suite(root, worktree, _TWO_RED, 1)

    turn = _turn(worktree)

    independent = turn["bundle"].independent_tests
    assert independent.tests_passed is False and independent.signal_absent is False
    decision = turn["decision"]
    assert decision["decision"] == "feedback"
    assert decision["issues"][0]["category"] == "independent_test_code_failure"
    assert decision[SUITE_RECEIPT_KEY]["command"] == "bash qa/run-suite.sh"

    text, must_fix = _player_reads(turn)
    assert text.startswith(f"{INDEPENDENT_FAILURE_OPENING}1). ")
    assert "Command: bash qa/run-suite.sh" in text
    assert _NEW in text and _OTHER in text
    assert len(must_fix) == 1, must_fix
    assert "bash qa/run-suite.sh" in must_fix[0]
    assert _NEW in must_fix[0] and _OTHER in must_fix[0]
    assert len(must_fix[0]) <= MUST_FIX_ITEM_LIMIT


def test_a_tool_whose_output_names_no_test_still_sends_the_turn_back(
    tmp_path: Path,
) -> None:
    """A test tool whose output names no test: the Player is still told
    what the run said."""
    root, worktree = _leg_repo(tmp_path)
    _declare_suite(root, worktree, "suite: 1 case did not hold (orders/totals)\n", 1)

    turn = _turn(worktree)

    assert turn["decision"]["decision"] == "feedback"
    text, _must_fix = _player_reads(turn)
    assert "suite: 1 case did not hold (orders/totals)" in text


def test_a_green_declared_suite_leaves_the_approval_and_says_nothing(
    tmp_path: Path,
) -> None:
    root, worktree = _leg_repo(tmp_path)
    _declare_suite(root, worktree, "5 passed in 0.50s\n", 0)

    turn = _turn(worktree)

    assert turn["bundle"].independent_tests.tests_passed is True
    assert turn["decision"]["decision"] == "approve"
    assert SUITE_RECEIPT_KEY not in turn["decision"]
    assert INDEPENDENT_FAILURE_OPENING not in turn["orchestrator"]._turn_feedback_text(
        turn["decision"], 1
    )
