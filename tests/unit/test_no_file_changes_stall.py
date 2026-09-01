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
    _already_implemented_veto,
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


def _player_reporting_no_edits(
    turn: int, task_id: str = "TASK-B0EF-002"
) -> AgentInvocationResult:
    """An honest Player report: it wrote nothing, and it says so.

    The shape of a genuine "the work was already there" turn — no file is
    named, so the honesty check has nothing to contradict and raises no
    ``claim_audit_unmodified`` record.
    """
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=True,
        report={
            "files_modified": [],
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
    honesty_record: bool = True,
    criteria_verification: Optional[List[Dict[str, Any]]] = None,
    decision: str = "feedback",
) -> AgentInvocationResult:
    issues: List[Dict[str, Any]] = [
        {
            "severity": "must_fix",
            "category": "missing_requirement",
            "description": ask,
        },
    ]
    if honesty_record:
        issues.append(
            {
                "severity": "should_fix",
                "category": "claim_audit",
                "claim_type": "claim_audit_unmodified",
                "description": (
                    "Player claimed file app/features/users/crud.py but "
                    "'git status --porcelain' shows no change for it."
                ),
            }
        )
    report: Dict[str, Any] = {
        "decision": decision,
        "feedback": f"Not yet: {ask}",
        "issues": issues,
    }
    if criteria_verification is not None:
        report["criteria_verification"] = criteria_verification
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
    honesty_record: bool = True,
    criteria_verification: Optional[List[Dict[str, Any]]] = None,
) -> TurnRecord:
    coach = _coach_asking_for_changes(
        turn,
        ask=ask,
        task_id=task_id,
        validation_results=validation_results,
        honesty_record=honesty_record,
        criteria_verification=criteria_verification,
    )
    player = (
        _player_claiming_edits(turn, task_id=task_id)
        if honesty_record
        else _player_reporting_no_edits(turn, task_id=task_id)
    )
    return TurnRecord(
        turn=turn,
        player_result=player,
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




# ---------------------------------------------------------------------------
# 5b. "Already done" is refused whenever anything says the work is not done
#
#     Two ways a task could otherwise be marked finished with the work
#     genuinely missing:
#
#     (a) the reviewer says every acceptance criterion is unmet, the generator
#         writes nothing, and the receipt fires anyway because it only ever
#         looked at "zero changes + a green test run";
#     (b) the generator picks WHICH tests the completion check runs. Naming a
#         pre-existing, already-passing test file it never touched is enough
#         to produce a green run. The deterministic honesty check catches
#         exactly that turn (``claim_audit_unmodified``), so the receipt must
#         consult it.
# ---------------------------------------------------------------------------


def _criteria(*results: str) -> List[Dict[str, Any]]:
    """Per-criterion verdicts in the reviewer's own shape."""
    return [
        {
            "criterion_id": f"AC-{i + 1:03d}",
            "criterion_text": f"Criterion {i + 1}",
            "result": result,
            "status": result,
            "notes": "checked",
            "evidence": "checked",
        }
        for i, result in enumerate(results)
    ]


def _green() -> Dict[str, Any]:
    return _independent_tests(tests_passed=True)["validation_results"]




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







# ---------------------------------------------------------------------------
# 8. The reviewer's own test command reaches the completion check
# ---------------------------------------------------------------------------




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


class TestASameSizeEditIsStillAChange:
    """The line counts alone do not move for a one-line-for-one-line edit.

    Found by review, 2026-09-01: signing a tracked file with only
    ``git diff --numstat`` added/removed counts made three genuine consecutive
    edits measure as three turns of no progress, which would abort a healthy
    build as a stall. The file's size and timestamp close it.
    """

    def test_an_edit_that_keeps_the_line_counts_identical_is_seen(self, repo):
        (repo / "app.py").write_text("LIMIT = 30\n")
        first = _worktree_change_snapshot(repo)
        (repo / "app.py").write_text("LIMIT = 40\n")
        second = _worktree_change_snapshot(repo)
        assert count_changed_paths(first, second) == 1, (
            "a one-line-for-one-line edit must register as a change"
        )

    def test_three_such_edits_running_are_three_changes_not_a_stall(self, repo):
        counts = []
        (repo / "app.py").write_text("LIMIT = 30\n")
        snap = _worktree_change_snapshot(repo)
        for value in (40, 50, 60):
            (repo / "app.py").write_text(f"LIMIT = {value}\n")
            nxt = _worktree_change_snapshot(repo)
            counts.append(count_changed_paths(snap, nxt))
            snap = nxt
        assert counts == [1, 1, 1], f"healthy edits measured as {counts}"
