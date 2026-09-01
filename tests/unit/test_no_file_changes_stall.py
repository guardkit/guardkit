"""Tests for TASK-AB-NOCHANGE01 — the build can now say "nothing happened".

Two real builds in the 2026-08-30 architecture exam ended the same way and
neither said so:

* **FEAT-245E / TASK-245E-002** — the generator hit a rule it could not
  satisfy (the architecture record forbade the only route to the data the
  task needed). No legal edit existed.
* **FEAT-B0EF / TASK-B0EF-002** — the task asked for filtering that was
  already in the file. Nothing needed doing.

In both, the generator claimed it had modified files that ``git status``
showed unchanged, turn after turn. The deterministic honesty check caught the
false claim every single turn (``claim_audit_unmodified``, severity
``should_fix``, advisory — it correctly never rejected the turn), the loop ran
to its turn limit, and the build reported ``max_turns_exceeded``: the symptom,
not the cause. About 25 minutes of wall clock and a failed build each time.

Both failures are reconstructed here as fixtures.

What is covered
---------------
1. Three turns with no file changes and a reviewer still asking for changes
   end as ``unrecoverable_stall`` with the new ``no_file_changes_stall``
   sub-type — never ``max_turns_exceeded`` — and the message names what the
   reviewer last asked for.
2. Zero changes with the reviewer's own test run green completes the task.
3. Zero changes with that run red — or absent, or skipped because the task has
   no tests of its own — stalls; it never completes.
4. One quiet turn followed by a turn with real changes is not a stall: the
   window must not fire early.
5. A build with changes every turn is untouched, and so is a turn history
   recorded before the measurement existed (``files_changed_this_turn=None``).
6. The git measurement itself: it sees real edits, ignores the build's own
   bookkeeping files, and reports "unknown" rather than "nothing" when git
   cannot answer.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    FAILURE_CATEGORY_MAP,
    STALL_CLASSIFICATION_THRESHOLD,
    STALL_COACH_AGENT_INVOCATIONS,
    STALL_ENVIRONMENT,
    STALL_FEEDBACK_GENERIC,
    STALL_NO_FILE_CHANGES,
    TurnRecord,
    _coach_first_issue_description,
    _turn_changed_no_files,
    _worktree_change_snapshot,
    classify_stall,
    count_changed_paths,
)


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------

#: What the reviewer kept asking for on FEAT-B0EF TASK-B0EF-002 — the task
#: whose filtering was already implemented.
B0EF_ASK = (
    "Acceptance criterion AC-002 is not met: add domain filtering to the "
    "distinct-domain count endpoint so callers can limit results by domain."
)

#: What the reviewer kept asking for on FEAT-245E TASK-245E-002 — the task
#: with no legal move available.
E245_ASK = (
    "The analytics feature must read user data, but the architecture record "
    "forbids importing another feature's internals. Route the read through a "
    "public interface."
)


def _player_claiming_edits(
    turn: int, task_id: str = "TASK-B0EF-002"
) -> AgentInvocationResult:
    """A Player report claiming edits that git shows never happened.

    This is the exact shape of the two real failures: the report names files,
    the worktree is untouched, and the honesty check raises an advisory
    ``claim_audit_unmodified`` record every turn without rejecting the turn.
    """
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=True,
        report={
            "files_modified": ["app/features/users/crud.py"],
            "files_created": [],
            "tests_passed": True,
            "test_count": 12,
        },
        duration_seconds=180.0,
        error=None,
    )


def _coach_asking_for_changes(
    turn: int,
    ask: str = B0EF_ASK,
    task_id: str = "TASK-B0EF-002",
    validation_results: Optional[Dict[str, Any]] = None,
) -> AgentInvocationResult:
    report: Dict[str, Any] = {
        "decision": "feedback",
        "feedback": f"Not yet: {ask}",
        "issues": [
            {
                "severity": "must_fix",
                "category": "missing_requirement",
                "description": ask,
            },
            {
                "severity": "should_fix",
                "category": "claim_audit",
                "claim_type": "claim_audit_unmodified",
                "description": (
                    "Player claimed file app/features/users/crud.py but "
                    "'git status --porcelain' shows no change for it."
                ),
            },
        ],
    }
    if validation_results is not None:
        report["validation_results"] = validation_results
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report=report,
        duration_seconds=40.0,
        error=None,
    )


def _turn(
    turn: int,
    files_changed: Optional[int],
    ask: str = B0EF_ASK,
    decision: str = "feedback",
    task_id: str = "TASK-B0EF-002",
    validation_results: Optional[Dict[str, Any]] = None,
) -> TurnRecord:
    coach = _coach_asking_for_changes(
        turn, ask=ask, task_id=task_id, validation_results=validation_results
    )
    return TurnRecord(
        turn=turn,
        player_result=_player_claiming_edits(turn, task_id=task_id),
        coach_result=coach,
        decision=decision,
        feedback=coach.report["feedback"],
        timestamp=f"2026-08-30T14:0{turn}:00Z",
        files_changed_this_turn=files_changed,
    )


def _independent_tests(
    *,
    tests_passed: bool,
    signal_absent: bool = False,
    test_command: str = "pytest tests/features/users/test_crud.py",
) -> Dict[str, Any]:
    return {
        "validation_results": {
            "independent_tests": {
                "tests_passed": tests_passed,
                "signal_absent": signal_absent,
                "test_command": test_command,
                "test_output_summary": "12 passed in 1.8s",
            }
        }
    }


class _FakeWorktreeManager:
    def __init__(self, worktrees_dir: Path) -> None:
        self.worktrees_dir = worktrees_dir


def _orchestrator(tmp_path: Path) -> AutoBuildOrchestrator:
    worktrees_dir = tmp_path / ".guardkit" / "worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    return AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=10,
        worktree_manager=_FakeWorktreeManager(worktrees_dir),
        enable_context=False,
    )


# ---------------------------------------------------------------------------
# 1. The two real failures now stop early and say why
# ---------------------------------------------------------------------------


class TestTheTwoRealFailures:
    def test_b0ef_already_done_case_classifies_as_no_file_changes(self):
        """FEAT-B0EF: three quiet turns, reviewer still asking. New sub-type."""
        history = [_turn(t, 0) for t in (1, 2, 3)]
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert STALL_NO_FILE_CHANGES in classification.co_fires
        assert classification.decision_label == STALL_NO_FILE_CHANGES
        assert classification.decision_subtype == STALL_NO_FILE_CHANGES

    def test_245e_no_legal_move_case_classifies_the_same_way(self):
        """FEAT-245E: same signature, different cause. Same sub-type."""
        history = [
            _turn(t, 0, ask=E245_ASK, task_id="TASK-245E-002")
            for t in (2, 3, 4)
        ]
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert classification.decision_label == STALL_NO_FILE_CHANGES

    def test_loop_would_stop_at_the_threshold_not_at_max_turns(self, tmp_path):
        """The detector fires exactly at the window, not one turn early."""
        orch = _orchestrator(tmp_path)
        history: List[TurnRecord] = []
        fired_at = None
        for t in range(1, 9):
            history.append(_turn(t, 0))
            if orch._is_no_file_change_stalled(history):
                fired_at = t
                break
        assert fired_at == STALL_CLASSIFICATION_THRESHOLD

    def test_new_subtype_is_in_the_failure_category_map(self):
        assert FAILURE_CATEGORY_MAP[STALL_NO_FILE_CHANGES] == "other"

    def test_new_subtype_is_never_a_top_level_decision(self):
        """The top-level label stays ``unrecoverable_stall`` for consumers."""
        history = [_turn(t, 0) for t in (1, 2, 3)]
        assert classify_stall(history, "max_turns_exceeded") is None
        assert classify_stall(history, "approved") is None


# ---------------------------------------------------------------------------
# 2. The message a person reads
# ---------------------------------------------------------------------------


class TestTheMessage:
    def test_message_says_no_files_changed_and_for_how_many_turns(
        self, tmp_path
    ):
        orch = _orchestrator(tmp_path)
        history = [_turn(t, 0) for t in (3, 4, 5)]
        message = orch._no_file_change_stall_message("TASK-B0EF-002", history)
        assert "changed no files" in message
        assert "3 turns running" in message
        assert "turns 3, 4 and 5" in message

    def test_message_quotes_what_the_reviewer_last_asked_for(self, tmp_path):
        orch = _orchestrator(tmp_path)
        history = [_turn(t, 0) for t in (1, 2, 3)]
        message = orch._no_file_change_stall_message("TASK-B0EF-002", history)
        assert "add domain filtering" in message

    def test_message_offers_both_explanations_and_picks_neither(
        self, tmp_path
    ):
        orch = _orchestrator(tmp_path)
        history = [_turn(t, 0) for t in (1, 2, 3)]
        message = orch._no_file_change_stall_message("TASK-B0EF-002", history)
        assert "the work is already there" in message
        assert "cannot be done as written" in message
        assert "cannot tell" in message

    def test_message_names_the_task_and_preserves_the_worktree(self, tmp_path):
        orch = _orchestrator(tmp_path)
        history = [_turn(t, 0) for t in (1, 2, 3)]
        message = orch._no_file_change_stall_message("TASK-B0EF-002", history)
        assert "TASK-B0EF-002" in message
        assert "Worktree preserved for inspection." in message

    def test_message_survives_a_turn_with_no_readable_issue(self, tmp_path):
        orch = _orchestrator(tmp_path)
        history = [_turn(t, 0) for t in (1, 2)]
        bare = TurnRecord(
            turn=3,
            player_result=_player_claiming_edits(3),
            coach_result=AgentInvocationResult(
                task_id="TASK-B0EF-002",
                turn=3,
                agent_type="coach",
                success=True,
                report={"decision": "feedback"},
                duration_seconds=1.0,
                error=None,
            ),
            decision="feedback",
            feedback=None,
            timestamp="2026-08-30T14:03:00Z",
            files_changed_this_turn=0,
        )
        history.append(bare)
        message = orch._no_file_change_stall_message("TASK-B0EF-002", history)
        assert "no readable description" in message

    def test_summary_renderer_uses_the_new_message(self, tmp_path):
        orch = _orchestrator(tmp_path)
        history = [_turn(t, 0) for t in (1, 2, 3)]
        details = orch._build_summary_details(history, "unrecoverable_stall")
        assert STALL_NO_FILE_CHANGES in details
        assert "changed no files" in details
        assert "add domain filtering" in details
        # The generic "review task_type classification" hint must not appear:
        # it blames the task's metadata for something that never happened.
        assert "Review task_type classification" not in details

    def test_first_issue_description_is_trimmed(self):
        long_ask = "x" * 500
        record = _turn(1, 0, ask=long_ask)
        text = _coach_first_issue_description(record, max_chars=50)
        assert text is not None
        assert len(text) == 50


# ---------------------------------------------------------------------------
# 3. The window must not fire early, and must not fire on old histories
# ---------------------------------------------------------------------------


class TestTheWindowDoesNotFireEarly:
    def test_one_quiet_turn_then_a_turn_with_changes_is_not_a_stall(
        self, tmp_path
    ):
        orch = _orchestrator(tmp_path)
        history = [_turn(1, 0), _turn(2, 4)]
        assert orch._is_no_file_change_stalled(history) is False
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert STALL_NO_FILE_CHANGES not in classification.co_fires

    def test_two_quiet_turns_are_not_yet_a_stall(self, tmp_path):
        orch = _orchestrator(tmp_path)
        history = [_turn(1, 0), _turn(2, 0)]
        assert orch._is_no_file_change_stalled(history) is False

    def test_a_change_inside_the_window_breaks_it(self, tmp_path):
        orch = _orchestrator(tmp_path)
        history = [_turn(1, 0), _turn(2, 1), _turn(3, 0), _turn(4, 0)]
        assert orch._is_no_file_change_stalled(history) is False

    def test_an_approved_turn_never_joins_the_window(self, tmp_path):
        orch = _orchestrator(tmp_path)
        history = [
            _turn(1, 0),
            _turn(2, 0),
            _turn(3, 0, decision="approve"),
        ]
        assert orch._is_no_file_change_stalled(history) is False

    def test_a_normal_build_with_changes_every_turn_is_unaffected(
        self, tmp_path
    ):
        orch = _orchestrator(tmp_path)
        history = [_turn(1, 7), _turn(2, 3), _turn(3, 2)]
        assert orch._is_no_file_change_stalled(history) is False
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert classification.decision_label == STALL_FEEDBACK_GENERIC
        details = orch._build_summary_details(history, "unrecoverable_stall")
        assert "Review task_type classification" in details

    def test_an_unmeasured_turn_is_unknown_not_zero(self, tmp_path):
        """A history recorded before the measurement existed cannot stall."""
        orch = _orchestrator(tmp_path)
        history = [_turn(t, None) for t in (1, 2, 3)]
        assert orch._is_no_file_change_stalled(history) is False
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert STALL_NO_FILE_CHANGES not in classification.co_fires

    def test_one_unmeasured_turn_breaks_an_otherwise_quiet_window(
        self, tmp_path
    ):
        orch = _orchestrator(tmp_path)
        history = [_turn(1, 0), _turn(2, None), _turn(3, 0)]
        assert orch._is_no_file_change_stalled(history) is False

    def test_predicate_rejects_non_integers_and_booleans(self):
        assert _turn_changed_no_files(_turn(1, 0)) is True
        assert _turn_changed_no_files(_turn(1, 1)) is False
        assert _turn_changed_no_files(_turn(1, None)) is False
        weird = _turn(1, 0)
        object.__setattr__(weird, "files_changed_this_turn", False)
        assert _turn_changed_no_files(weird) is False


# ---------------------------------------------------------------------------
# 4. Precedence with the existing sub-types
# ---------------------------------------------------------------------------


class TestPrecedence:
    def test_no_file_changes_takes_the_primary_label_over_agent_invocations(
        self,
    ):
        """If nothing was written, that is the thing to report first."""
        history = []
        for t in (1, 2, 3):
            coach = AgentInvocationResult(
                task_id="TASK-B0EF-002",
                turn=t,
                agent_type="coach",
                success=True,
                report={
                    "decision": "feedback",
                    "feedback": "Invoke the specialists.",
                    "issues": [
                        {
                            "severity": "must_fix",
                            "category": "agent_invocations_violation",
                            "description": "Phases 4 and 5 were not invoked",
                            "missing_phases": ["4", "5"],
                            "expected_phases": 2,
                            "actual_invocations": 0,
                        }
                    ],
                },
                duration_seconds=1.0,
                error=None,
            )
            history.append(
                TurnRecord(
                    turn=t,
                    player_result=_player_claiming_edits(t),
                    coach_result=coach,
                    decision="feedback",
                    feedback="Invoke the specialists.",
                    timestamp=f"2026-08-30T14:0{t}:00Z",
                    files_changed_this_turn=0,
                )
            )
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert classification.decision_label == STALL_NO_FILE_CHANGES
        assert STALL_COACH_AGENT_INVOCATIONS in classification.co_fires

    def test_environment_stall_still_fires_when_files_did_change(self):
        """The environment sub-type's own precedence gate is untouched."""
        history = []
        for t in (1, 2, 3):
            coach = AgentInvocationResult(
                task_id="TASK-ENV-001",
                turn=t,
                agent_type="coach",
                success=True,
                report={
                    "decision": "feedback",
                    "feedback": "Independent tests failed (infrastructure).",
                    "validation_results": {
                        "quality_gates": {"all_gates_passed": True},
                        "independent_tests": {"tests_passed": False},
                    },
                    "issues": [
                        {
                            "severity": "must_fix",
                            "category": "test_verification",
                            "description": "Infrastructure failure",
                            "failure_classification": "infrastructure",
                            "failure_confidence": "high",
                        }
                    ],
                },
                duration_seconds=1.0,
                error=None,
            )
            history.append(
                TurnRecord(
                    turn=t,
                    player_result=_player_claiming_edits(t),
                    coach_result=coach,
                    decision="feedback",
                    feedback="Independent tests failed (infrastructure).",
                    timestamp=f"2026-08-30T14:0{t}:00Z",
                    files_changed_this_turn=3,
                )
            )
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert STALL_ENVIRONMENT in classification.co_fires
        assert STALL_NO_FILE_CHANGES not in classification.co_fires


# ---------------------------------------------------------------------------
# 5. "Already done" completes — and only on the checks the generator
#    cannot reach
# ---------------------------------------------------------------------------


class TestAlreadyDoneCompletes:
    def test_zero_changes_with_green_independent_tests_completes(
        self, tmp_path
    ):
        orch = _orchestrator(tmp_path)
        record = _turn(
            1, 0, validation_results=_independent_tests(tests_passed=True)[
                "validation_results"
            ]
        )
        receipt = orch._already_implemented_receipt(record)
        assert receipt is not None
        assert "already present" in receipt
        assert "changed no files" in receipt
        assert "pytest tests/features/users/test_crud.py" in receipt

    def test_receipt_reaches_the_summary(self, tmp_path):
        orch = _orchestrator(tmp_path)
        record = _turn(
            1, 0, validation_results=_independent_tests(tests_passed=True)[
                "validation_results"
            ]
        )
        orch._already_implemented_receipt_text = (
            orch._already_implemented_receipt(record)
        )
        details = orch._build_summary_details([record], "approved")
        assert "already present" in details
        assert "nothing to review in the diff" in details

    def test_a_normal_approval_summary_is_unchanged(self, tmp_path):
        orch = _orchestrator(tmp_path)
        record = _turn(1, 5, decision="approve")
        details = orch._build_summary_details([record], "approved")
        assert "Coach approved implementation after 1 turn(s)." in details
        assert "already present" not in details

    def test_zero_changes_with_red_tests_does_not_complete(self, tmp_path):
        orch = _orchestrator(tmp_path)
        record = _turn(
            1, 0, validation_results=_independent_tests(tests_passed=False)[
                "validation_results"
            ]
        )
        assert orch._already_implemented_receipt(record) is None

    def test_zero_changes_with_an_absent_test_signal_does_not_complete(
        self, tmp_path
    ):
        """An oracle that never reported is UNKNOWN, never a pass."""
        orch = _orchestrator(tmp_path)
        vr = _independent_tests(tests_passed=True, signal_absent=True)
        record = _turn(1, 0, validation_results=vr["validation_results"])
        assert orch._already_implemented_receipt(record) is None

    def test_zero_changes_with_a_skipped_run_does_not_complete(self, tmp_path):
        """No tests belong to this task, so nothing ran. Not a completion.

        ``IndependentTestResult.skipped()`` records ``tests_passed=True`` with
        ``signal_absent=False`` and the placeholder command ``"skipped"``. If
        that read as green, any task whose tests were never written could
        complete by the generator simply doing nothing.
        """
        orch = _orchestrator(tmp_path)
        vr = _independent_tests(tests_passed=True, test_command="skipped")
        record = _turn(1, 0, validation_results=vr["validation_results"])
        assert orch._already_implemented_receipt(record) is None

    def test_zero_changes_with_no_detected_test_command_does_not_complete(
        self, tmp_path
    ):
        orch = _orchestrator(tmp_path)
        vr = _independent_tests(
            tests_passed=True,
            test_command="<no test command declared or detected>",
        )
        record = _turn(1, 0, validation_results=vr["validation_results"])
        assert orch._already_implemented_receipt(record) is None

    def test_zero_changes_with_no_verification_block_does_not_complete(
        self, tmp_path
    ):
        orch = _orchestrator(tmp_path)
        record = _turn(1, 0)
        assert orch._already_implemented_receipt(record) is None

    def test_changes_with_green_tests_is_an_ordinary_turn(self, tmp_path):
        """The completion path is only ever reached with zero changes."""
        orch = _orchestrator(tmp_path)
        record = _turn(
            1, 2, validation_results=_independent_tests(tests_passed=True)[
                "validation_results"
            ]
        )
        assert orch._already_implemented_receipt(record) is None

    def test_an_unmeasured_turn_never_completes_this_way(self, tmp_path):
        orch = _orchestrator(tmp_path)
        record = _turn(
            1, None, validation_results=_independent_tests(tests_passed=True)[
                "validation_results"
            ]
        )
        assert orch._already_implemented_receipt(record) is None

    def test_the_generators_own_gates_are_not_consulted(self, tmp_path):
        """``quality_gates`` comes from the generator's own results file.

        A green quality-gates block with no independent test run must not
        complete the task — that is precisely the claim the generator can
        write for itself.
        """
        orch = _orchestrator(tmp_path)
        record = _turn(
            1,
            0,
            validation_results={
                "quality_gates": {
                    "tests_passed": True,
                    "all_gates_passed": True,
                },
                "tests_passed": True,
            },
        )
        assert orch._already_implemented_receipt(record) is None

    def test_a_failed_reviewer_invocation_never_completes(self, tmp_path):
        orch = _orchestrator(tmp_path)
        coach = AgentInvocationResult(
            task_id="TASK-B0EF-002",
            turn=1,
            agent_type="coach",
            success=False,
            report=_independent_tests(tests_passed=True),
            duration_seconds=1.0,
            error="SDK timeout",
        )
        record = TurnRecord(
            turn=1,
            player_result=_player_claiming_edits(1),
            coach_result=coach,
            decision="error",
            feedback=None,
            timestamp="2026-08-30T14:01:00Z",
            files_changed_this_turn=0,
        )
        assert orch._already_implemented_receipt(record) is None


# ---------------------------------------------------------------------------
# 6. The git measurement itself
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "worktree"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "app.py").write_text("print('hello')\n")
    _git(root, "add", "app.py")
    _git(root, "commit", "-qm", "initial")
    return root


class TestTheGitMeasurement:
    def test_a_turn_that_changes_nothing_measures_zero(self, repo):
        before = _worktree_change_snapshot(repo)
        after = _worktree_change_snapshot(repo)
        assert count_changed_paths(before, after) == 0

    def test_editing_a_tracked_file_is_seen(self, repo):
        before = _worktree_change_snapshot(repo)
        (repo / "app.py").write_text("print('hello')\nprint('world')\n")
        after = _worktree_change_snapshot(repo)
        assert count_changed_paths(before, after) == 1

    def test_a_second_edit_to_an_already_changed_file_is_still_seen(
        self, repo
    ):
        (repo / "app.py").write_text("print('one')\n")
        before = _worktree_change_snapshot(repo)
        (repo / "app.py").write_text("print('one')\nprint('two')\n")
        after = _worktree_change_snapshot(repo)
        assert count_changed_paths(before, after) == 1

    def test_a_new_file_is_seen(self, repo):
        before = _worktree_change_snapshot(repo)
        (repo / "extra.py").write_text("x = 1\n")
        after = _worktree_change_snapshot(repo)
        assert count_changed_paths(before, after) == 1

    def test_a_deleted_file_is_seen(self, repo):
        before = _worktree_change_snapshot(repo)
        (repo / "app.py").unlink()
        after = _worktree_change_snapshot(repo)
        assert count_changed_paths(before, after) == 1

    def test_the_builds_own_bookkeeping_does_not_count_as_work(self, repo):
        """The build writes its own records every turn; they are not work."""
        before = _worktree_change_snapshot(repo)
        book = repo / ".guardkit" / "autobuild" / "TASK-B0EF-002"
        book.mkdir(parents=True)
        (book / "player_turn_1.json").write_text("{}")
        (book / "coach_turn_1.json").write_text("{}")
        task_dir = repo / "tasks" / "in_progress"
        task_dir.mkdir(parents=True)
        (task_dir / "TASK-B0EF-002.md").write_text("# task\n")
        after = _worktree_change_snapshot(repo)
        assert count_changed_paths(before, after) == 0

    def test_the_leavings_of_a_test_run_do_not_count_as_work(self, repo):
        """The generator runs tests inside its own turn.

        A repository that does not gitignore ``.coverage`` or ``__pycache__``
        would otherwise make every silent turn look busy, and the stall would
        never fire.
        """
        before = _worktree_change_snapshot(repo)
        (repo / ".coverage").write_text("junk")
        (repo / "coverage.json").write_text("{}")
        cache = repo / "app" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "app.cpython-312.pyc").write_bytes(b"\x00")
        pytest_cache = repo / ".pytest_cache" / "v" / "cache"
        pytest_cache.mkdir(parents=True)
        (pytest_cache / "lastfailed").write_text("{}")
        htmlcov = repo / "htmlcov"
        htmlcov.mkdir()
        (htmlcov / "index.html").write_text("<html></html>")
        after = _worktree_change_snapshot(repo)
        assert count_changed_paths(before, after) == 0

    def test_real_work_alongside_test_leavings_is_still_seen(self, repo):
        before = _worktree_change_snapshot(repo)
        (repo / ".coverage").write_text("junk")
        (repo / "app.py").write_text("print('changed')\n")
        after = _worktree_change_snapshot(repo)
        assert count_changed_paths(before, after) == 1

    def test_a_missing_worktree_measures_unknown_not_zero(self, tmp_path):
        assert _worktree_change_snapshot(tmp_path / "nope") is None

    def test_a_non_git_directory_measures_unknown_not_zero(self, tmp_path):
        plain = tmp_path / "plain"
        plain.mkdir()
        assert _worktree_change_snapshot(plain) is None

    def test_an_absent_snapshot_makes_the_count_unknown(self, repo):
        snapshot = _worktree_change_snapshot(repo)
        assert count_changed_paths(None, snapshot) is None
        assert count_changed_paths(snapshot, None) is None
        assert count_changed_paths(None, None) is None


# ---------------------------------------------------------------------------
# 7. The loop itself: both real failures, end to end through _loop_phase
# ---------------------------------------------------------------------------


class _StubWorktree:
    def __init__(self, path: Path) -> None:
        self.task_id = "TASK-B0EF-002"
        self.path = path
        self.branch_name = "autobuild/TASK-B0EF-002"
        self.base_branch = "main"


def _loop_orchestrator(tmp_path: Path) -> AutoBuildOrchestrator:
    from unittest.mock import MagicMock

    orch = _orchestrator(tmp_path)
    orch.max_turns = 10
    orch.enable_checkpoints = False
    orch._progress_display = MagicMock()
    orch._agent_invoker = None
    return orch


def _run_loop(orch, turns: List[TurnRecord], tmp_path: Path):
    """Drive ``_loop_phase`` with a scripted sequence of turn records."""
    sequence = iter(turns)

    def _fake_execute_turn(*args, **kwargs):
        return next(sequence)

    orch._execute_turn = _fake_execute_turn  # type: ignore[assignment]
    return orch._loop_phase(
        task_id="TASK-B0EF-002",
        requirements="Filter distinct email domains by count",
        acceptance_criteria=["AC-001", "AC-002"],
        worktree=_StubWorktree(tmp_path),
    )


class TestTheLoopStopsAndSaysWhy:
    def test_three_quiet_turns_end_the_loop_as_a_stall_not_max_turns(
        self, tmp_path, caplog
    ):
        """The FEAT-B0EF / FEAT-245E signature, driven through the real loop.

        Before this change the loop ran all ten turns and reported
        ``max_turns_exceeded``. Now it stops at three.
        """
        orch = _loop_orchestrator(tmp_path)
        turns = [_turn(t, 0) for t in range(1, 11)]
        with caplog.at_level("ERROR"):
            history, decision = _run_loop(orch, turns, tmp_path)
        assert decision == "unrecoverable_stall"
        assert decision != "max_turns_exceeded"
        assert len(history) == STALL_CLASSIFICATION_THRESHOLD
        logged = "\n".join(r.getMessage() for r in caplog.records)
        assert "changed no files" in logged
        assert "add domain filtering" in logged

    def test_the_result_carries_the_new_subtype(self, tmp_path):
        orch = _loop_orchestrator(tmp_path)
        turns = [_turn(t, 0) for t in range(1, 11)]
        history, decision = _run_loop(orch, turns, tmp_path)
        classification = classify_stall(history, decision)
        assert classification is not None
        assert classification.decision_label == STALL_NO_FILE_CHANGES

    def test_a_quiet_turn_then_real_work_keeps_the_loop_running(
        self, tmp_path
    ):
        """One quiet turn must not end the build."""
        orch = _loop_orchestrator(tmp_path)
        turns = [
            _turn(1, 0),
            _turn(2, 3),
            _turn(3, 2, decision="approve"),
        ]
        history, decision = _run_loop(orch, turns, tmp_path)
        assert decision == "approved"
        assert len(history) == 3

    def test_a_normal_build_reaches_max_turns_exactly_as_before(
        self, tmp_path
    ):
        """Changes every turn, reviewer never satisfied — unchanged path."""
        orch = _loop_orchestrator(tmp_path)
        orch.max_turns = 4
        turns = [
            _turn(t, 2, ask=f"Issue number {t}") for t in range(1, 5)
        ]
        history, decision = _run_loop(orch, turns, tmp_path)
        assert decision == "max_turns_exceeded"
        assert len(history) == 4

    def test_zero_changes_with_green_tests_completes_the_loop(self, tmp_path):
        """FEAT-B0EF as it should have ended: done, on the first quiet turn."""
        orch = _loop_orchestrator(tmp_path)
        green = _independent_tests(tests_passed=True)["validation_results"]
        turns = [_turn(t, 0, validation_results=green) for t in range(1, 11)]
        history, decision = _run_loop(orch, turns, tmp_path)
        assert decision == "approved"
        assert len(history) == 1
        assert orch._already_implemented_receipt_text is not None
        assert "already present" in orch._already_implemented_receipt_text

    def test_zero_changes_with_red_tests_stalls_and_never_completes(
        self, tmp_path
    ):
        """FEAT-245E: no legal move, tests red. Stall, not completion."""
        orch = _loop_orchestrator(tmp_path)
        red = _independent_tests(tests_passed=False)["validation_results"]
        turns = [
            _turn(t, 0, ask=E245_ASK, validation_results=red)
            for t in range(1, 11)
        ]
        history, decision = _run_loop(orch, turns, tmp_path)
        assert decision == "unrecoverable_stall"
        assert len(history) == STALL_CLASSIFICATION_THRESHOLD
        assert orch._already_implemented_receipt_text is None

    def test_zero_changes_with_a_skipped_test_run_stalls(self, tmp_path):
        """No tests of its own means no completion — the important one.

        Otherwise a task whose tests were never written could be completed by
        a generator that simply did nothing.
        """
        orch = _loop_orchestrator(tmp_path)
        skipped = _independent_tests(
            tests_passed=True, test_command="skipped"
        )["validation_results"]
        turns = [
            _turn(t, 0, validation_results=skipped) for t in range(1, 11)
        ]
        history, decision = _run_loop(orch, turns, tmp_path)
        assert decision == "unrecoverable_stall"
        assert orch._already_implemented_receipt_text is None


# ---------------------------------------------------------------------------
# 8. The reviewer's own test command reaches the completion check
# ---------------------------------------------------------------------------


class TestTheTestCommandIsCarriedThrough:
    """``_merge_evidence_test_signal_into_report`` must carry the command.

    The pass/absent pair alone cannot tell a real green run from a SKIPPED
    one, and a skipped run is recorded as ``tests_passed=True``. Without the
    command the completion path would have no way to refuse a task that has
    no tests of its own.
    """

    def _bundle(self, *, test_command: str, tests_passed: bool = True):
        from unittest.mock import Mock

        from guardkit.orchestrator.quality_gates.coach_evidence import (
            CoachEvidenceBundle,
        )
        from guardkit.orchestrator.quality_gates.coach_validator import (
            IndependentTestResult,
        )

        return CoachEvidenceBundle(
            honesty=Mock(),
            quality_gates=None,
            independent_tests=IndependentTestResult(
                tests_passed=tests_passed,
                test_command=test_command,
                test_output_summary="12 passed in 1.8s",
                duration_seconds=1.8,
            ),
        )

    def test_a_real_command_is_merged_and_completes(self, tmp_path):
        orch = _orchestrator(tmp_path)
        report: Dict[str, Any] = {"decision": "feedback", "issues": []}
        orch._merge_evidence_test_signal_into_report(
            report, self._bundle(test_command="pytest tests/test_users.py")
        )
        independent = report["validation_results"]["independent_tests"]
        assert independent["test_command"] == "pytest tests/test_users.py"
        record = _turn(1, 0, validation_results=report["validation_results"])
        assert orch._already_implemented_receipt(record) is not None

    def test_a_skipped_command_is_merged_and_refused(self, tmp_path):
        orch = _orchestrator(tmp_path)
        report: Dict[str, Any] = {"decision": "feedback", "issues": []}
        orch._merge_evidence_test_signal_into_report(
            report, self._bundle(test_command="skipped")
        )
        independent = report["validation_results"]["independent_tests"]
        assert independent["test_command"] == "skipped"
        assert independent["tests_passed"] is True
        record = _turn(1, 0, validation_results=report["validation_results"])
        assert orch._already_implemented_receipt(record) is None

    def test_the_merge_still_does_not_clobber_an_existing_value(
        self, tmp_path
    ):
        orch = _orchestrator(tmp_path)
        report: Dict[str, Any] = {
            "decision": "feedback",
            "validation_results": {
                "independent_tests": {"test_command": "already here"}
            },
        }
        orch._merge_evidence_test_signal_into_report(
            report, self._bundle(test_command="pytest -q")
        )
        assert (
            report["validation_results"]["independent_tests"]["test_command"]
            == "already here"
        )


class TestTheAskSkipsTheHonestyRecord:
    """The honesty advisory must not be quoted back as "what was asked for".

    On both real failures the reviewer's issue list led with the deterministic
    ``claim_audit_unmodified`` record — "the generator claimed a file it did
    not change". That is the fact the message's first line already states;
    quoting it as the request would be circular and would bury the real ask.
    """

    def test_the_claim_audit_record_is_passed_over(self):
        coach = AgentInvocationResult(
            task_id="TASK-B0EF-002",
            turn=1,
            agent_type="coach",
            success=True,
            report={
                "decision": "feedback",
                "issues": [
                    {
                        "severity": "should_fix",
                        "category": "claim_audit",
                        "description": (
                            "Player claimed file crud.py but git shows no "
                            "change for it."
                        ),
                    },
                    {
                        "severity": "must_fix",
                        "category": "missing_requirement",
                        "description": B0EF_ASK,
                    },
                ],
            },
            duration_seconds=1.0,
            error=None,
        )
        record = TurnRecord(
            turn=1,
            player_result=_player_claiming_edits(1),
            coach_result=coach,
            decision="feedback",
            feedback="Not yet",
            timestamp="2026-08-30T14:01:00Z",
            files_changed_this_turn=0,
        )
        text = _coach_first_issue_description(record)
        assert text is not None
        assert "add domain filtering" in text
        assert "claimed file" not in text

    def test_an_honesty_record_alone_is_still_better_than_nothing(self):
        coach = AgentInvocationResult(
            task_id="TASK-B0EF-002",
            turn=1,
            agent_type="coach",
            success=True,
            report={
                "decision": "feedback",
                "issues": [
                    {
                        "severity": "should_fix",
                        "category": "honesty",
                        "description": "Claimed work that did not land.",
                    }
                ],
            },
            duration_seconds=1.0,
            error=None,
        )
        record = TurnRecord(
            turn=1,
            player_result=_player_claiming_edits(1),
            coach_result=coach,
            decision="feedback",
            feedback="Not yet",
            timestamp="2026-08-30T14:01:00Z",
            files_changed_this_turn=0,
        )
        assert (
            _coach_first_issue_description(record)
            == "Claimed work that did not land."
        )
