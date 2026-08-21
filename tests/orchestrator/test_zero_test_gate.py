"""Tests for the advisory zero-test check on the live (language-model) Coach path.

WHAT IS BEING TESTED, for a reader who does not know this codebase
------------------------------------------------------------------
GuardKit builds software in a loop. A **Player** writes code; a **Coach** then
reviews the turn and decides approve / feedback / reject.

The rule-based (legacy) Coach has always refused to approve a turn in which the
Player wrote no test file. Since 2026-05-21 the default Coach is a language
model, and on that path the rule was never run and the model was never told the
fact. This module tests the change that closes that gap.

The change is deliberately **advisory**: it detects the case deterministically,
tells the model in words, and writes a durable record — but it does not stop
the build unless someone sets ``GUARDKIT_ZERO_TEST_BLOCKING``. The record is
the point: nobody yet knows how often a change legitimately needs no test (a
documentation edit, a rename, deleting dead code, a config change), and that
number is the whole decision about whether this should ever block.

The six things this file covers, in order:

1. it fires when no test file was written;
2. it stays silent when one was;
3. it is advisory by default — the verdict is untouched;
4. it blocks when the flag is set;
5. the receipt is written, with the fields a person needs to adjudicate it;
6. the guard against silent promotion — the flip is wired to the flag and to
   nothing else, so nobody can make this block without deciding to.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.orchestrator import zero_test_gate as gate
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.models.task_types import TaskType, get_profile


# ===========================================================================
# Helpers
# ===========================================================================


def _worktree(tmp_path: Path, task_id: str = "TASK-ZT-001") -> Path:
    """A worktree laid out the way a real build's worktree is."""
    worktree = tmp_path / "repo" / ".guardkit" / "worktrees" / "FEAT-ZT99"
    (worktree / ".guardkit" / "autobuild" / task_id).mkdir(parents=True, exist_ok=True)
    (worktree / "tests").mkdir(parents=True, exist_ok=True)
    (worktree / "src").mkdir(parents=True, exist_ok=True)
    return worktree


def _results(
    *,
    tests_written=None,
    files_created=None,
    files_modified=None,
    tests_passed_count: int = 0,
) -> dict:
    """A Player report shaped like the real ``task_work_results.json``."""
    return {
        "task_id": "TASK-ZT-001",
        "quality_gates": {
            "all_passed": True,
            "tests_passed": tests_passed_count,
            "tests_failed": 0,
            "coverage": None,
        },
        "files_created": list(files_created or []),
        "files_modified": list(files_modified or []),
        "tests_written": list(tests_written or []),
    }


def _validator(worktree: Path) -> CoachValidator:
    return CoachValidator(str(worktree), task_id="TASK-ZT-001")


def _skipped_independent_run() -> IndependentTestResult:
    """What the Coach's own test run reports when it found no tests to run."""
    return IndependentTestResult.skipped(
        test_output_summary="no task-specific tests found",
    )


def _feature_profile():
    return get_profile(TaskType.FEATURE)


def _fired_evidence(**overrides) -> dict:
    evidence = {
        "fired": True,
        "severity": "error",
        "category": gate.ANOMALY_CATEGORY,
        "description": "No task-specific tests found.",
        "detector": "CoachValidator._check_zero_test_anomaly",
        "tests_required": True,
        "profile_blocks_on_zero_tests": True,
        "files_created": ["docs/guide.md"],
        "files_modified": ["README.md"],
        "tests_written": [],
        "claimed_test_files": [],
        "test_files_on_disk": [],
        "any_test_file_on_disk": False,
        "independent_test_command": "skipped",
        "requirements_met": True,
        "evaluation_error": None,
    }
    evidence.update(overrides)
    return evidence


def _run_guard(
    tmp_path: Path,
    *,
    decision: dict,
    evidence,
    env: dict,
    task_id: str = "TASK-ZT-001",
    turn: int = 1,
) -> tuple[dict, Path]:
    """Run the guard against an un-``__init__``'d AgentInvoker.

    Returns the (mutated) decision and the repository root, so a caller can
    look for the ledger.
    """
    worktree = _worktree(tmp_path, task_id)
    repo_root = tmp_path / "repo"
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree

    bundle = CoachEvidenceBundle(honesty=None, zero_test=evidence)
    coach_output_path = worktree / ".guardkit" / "autobuild" / task_id / (
        f"coach_turn_{turn}.json"
    )
    coach_output_path.write_text(json.dumps(decision))

    invoker._apply_zero_test_guard(
        decision=decision,
        evidence_bundle=bundle,
        task_id=task_id,
        turn=turn,
        coach_output_path=coach_output_path,
        env=env,
    )
    return decision, repo_root


# ===========================================================================
# 1 + 2. Detection — fires with no test file, silent with one
# ===========================================================================


def test_the_same_rule_is_used_not_a_second_copy(tmp_path: Path) -> None:
    """Detection must delegate to the legacy rule, with the same arguments.

    If anyone reimplements the detection here instead of calling
    ``CoachValidator._check_zero_test_anomaly``, this goes red — which is the
    only thing keeping the rule-based Coach and the language-model Coach from
    slowly disagreeing about what "no tests" means.
    """
    validator = _validator(_worktree(tmp_path))
    profile = _feature_profile()
    independent = _skipped_independent_run()
    results = _results()

    with patch.object(
        validator, "_check_zero_test_anomaly", return_value=[]
    ) as legacy_rule:
        gate.evaluate_zero_test(
            validator,
            task_work_results=results,
            profile=profile,
            independent_tests=independent,
            task_id="TASK-ZT-001",
        )

    legacy_rule.assert_called_once_with(
        results,
        profile,
        independent_tests=independent,
        task_id="TASK-ZT-001",
    )


def test_fires_when_the_player_wrote_no_test_file(tmp_path: Path) -> None:
    worktree = _worktree(tmp_path)
    (worktree / "src" / "auth.py").write_text("# code, no tests\n")

    evidence = gate.evaluate_zero_test(
        _validator(worktree),
        task_work_results=_results(files_created=["src/auth.py"]),
        profile=_feature_profile(),
        independent_tests=_skipped_independent_run(),
        task_id="TASK-ZT-001",
    )

    assert evidence["fired"] is True
    assert evidence["severity"] == "error"
    assert evidence["any_test_file_on_disk"] is False
    assert evidence["files_created"] == ["src/auth.py"]


def test_silent_when_a_real_test_file_was_written(tmp_path: Path) -> None:
    """A test file that exists is found by the Coach's own run, so nothing fires.

    The Coach's independent verification reports a real command (not
    ``"skipped"``) when it found tests to run, and the legacy rule treats that
    as proof the turn is not test-free.
    """
    worktree = _worktree(tmp_path)
    (worktree / "tests" / "test_auth.py").write_text("def test_x(): pass\n")

    passing_run = IndependentTestResult(
        tests_passed=True,
        test_command="pytest tests/test_auth.py",
        test_output_summary="1 passed",
        duration_seconds=0.1,
    )
    evidence = gate.evaluate_zero_test(
        _validator(worktree),
        task_work_results=_results(
            tests_written=["tests/test_auth.py"],
            files_created=["tests/test_auth.py"],
            tests_passed_count=1,
        ),
        profile=_feature_profile(),
        independent_tests=passing_run,
        task_id="TASK-ZT-001",
    )

    assert evidence["fired"] is False
    assert evidence["any_test_file_on_disk"] is True
    assert evidence["test_files_on_disk"] == ["tests/test_auth.py"]


def test_silent_for_a_task_type_that_does_not_require_tests(
    tmp_path: Path,
) -> None:
    """Scaffolding tasks are not expected to carry tests; nothing fires."""
    evidence = gate.evaluate_zero_test(
        _validator(_worktree(tmp_path)),
        task_work_results=_results(files_created=["src/scaffold.py"]),
        profile=get_profile(TaskType.SCAFFOLDING),
        independent_tests=_skipped_independent_run(),
        task_id="TASK-ZT-001",
    )
    assert evidence["fired"] is False


def test_a_broken_rule_reports_nothing_rather_than_inventing_a_verdict(
    tmp_path: Path,
) -> None:
    """An instrument that cannot report must not manufacture a finding."""
    validator = _validator(_worktree(tmp_path))
    with patch.object(
        validator, "_check_zero_test_anomaly", side_effect=RuntimeError("boom")
    ):
        evidence = gate.evaluate_zero_test(
            validator,
            task_work_results=_results(),
            profile=_feature_profile(),
            independent_tests=_skipped_independent_run(),
            task_id="TASK-ZT-001",
        )
    assert evidence["fired"] is False
    assert "RuntimeError" in evidence["evaluation_error"]


# ===========================================================================
# The live path actually carries the field
# ===========================================================================


def test_the_live_coach_path_puts_the_answer_on_the_evidence_bundle(
    tmp_path: Path,
) -> None:
    """``gather_evidence`` — the live path — must populate ``zero_test``.

    Before this change the field did not exist and the rule was never run on
    this path at all.
    """
    worktree = _worktree(tmp_path)
    (worktree / "src" / "auth.py").write_text("# code, no tests\n")
    results_dir = worktree / ".guardkit" / "autobuild" / "TASK-ZT-001"
    (results_dir / "task_work_results.json").write_text(
        json.dumps(_results(files_created=["src/auth.py"]))
    )

    validator = _validator(worktree)
    with patch.object(
        validator, "run_independent_tests", return_value=_skipped_independent_run()
    ):
        bundle = validator.gather_evidence(
            task_id="TASK-ZT-001",
            turn=1,
            task={"acceptance_criteria": [], "task_type": "feature"},
            skip_arch_review=True,
        )

    assert bundle.gathering_status == "complete", bundle.gathering_error
    assert isinstance(bundle.zero_test, dict)
    assert bundle.zero_test["fired"] is True
    # And it survives serialisation into the Coach's prompt / turn record.
    assert bundle.to_dict()["zero_test"]["fired"] is True


def test_the_field_is_absent_when_gathering_stopped_early() -> None:
    """A bundle that never reached the check reports nothing, not "clean"."""
    assert CoachEvidenceBundle(honesty=None).zero_test is None


# ===========================================================================
# The Coach is told, in words
# ===========================================================================


def test_the_coach_is_told_in_plain_words_that_no_test_file_was_written() -> None:
    invoker = AgentInvoker.__new__(AgentInvoker)
    bundle = CoachEvidenceBundle(honesty=None, zero_test=_fired_evidence())

    section = invoker._render_evidence_bundle_section(bundle)

    assert "NO TEST FILE WAS WRITTEN" in section
    # It must say it does not block, so the model weighs it rather than obeying it.
    assert "does NOT block" in section


def test_nothing_is_said_to_the_coach_when_a_test_file_was_written() -> None:
    invoker = AgentInvoker.__new__(AgentInvoker)
    bundle = CoachEvidenceBundle(
        honesty=None, zero_test=_fired_evidence(fired=False)
    )
    assert "NO TEST FILE WAS WRITTEN" not in invoker._render_evidence_bundle_section(
        bundle
    )


def test_the_coachs_standing_instructions_mention_the_case() -> None:
    """The written instructions the Coach is installed with must cover it.

    The gap that prompted this work was not only that no rule fired — it was
    that the model's own instruction file never mentioned the case, so a
    reader could not tell whether the model had weighed it or never seen it.
    """
    instructions = (
        Path(__file__).resolve().parents[2]
        / "installer"
        / "core"
        / "agents"
        / "autobuild-coach.md"
    ).read_text(encoding="utf-8")
    assert "When the Player Wrote No Test File" in instructions
    assert "NO TEST FILE WAS WRITTEN" in instructions


# ===========================================================================
# 3 + 4. Advisory by default; blocking only when asked
# ===========================================================================


def test_blocking_is_off_unless_asked_for() -> None:
    assert gate.blocking_requested({}) is False
    assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: ""}) is False
    assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: "0"}) is False
    assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: "maybe"}) is False


def test_blocking_accepts_the_documented_values() -> None:
    for value in ("1", "true", "TRUE", "yes", "on"):
        assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: value}) is True


def test_advisory_by_default_an_approval_stands(tmp_path: Path) -> None:
    """The whole ruling: measure first. A fired check changes no verdict."""
    decision, _ = _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "looks fine", "issues": []},
        evidence=_fired_evidence(),
        env={},
    )
    assert decision["decision"] == "approve"
    assert decision["rationale"] == "looks fine"
    assert decision["issues"] == []


def test_it_blocks_when_the_flag_is_set(tmp_path: Path) -> None:
    decision, _ = _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "looks fine", "issues": []},
        evidence=_fired_evidence(),
        env={gate.BLOCKING_ENV_VAR: "1"},
    )
    assert decision["decision"] == "feedback"
    assert decision["issues"][0]["category"] == gate.ANOMALY_CATEGORY
    assert decision["issues"][0]["severity"] == "must_fix"
    assert decision["issues"][0]["details"]["overridden_decision"] == "approve"


def test_a_feedback_verdict_is_never_touched(tmp_path: Path) -> None:
    """Only an approval can be flipped; a Coach already asking for changes stands."""
    decision, _ = _run_guard(
        tmp_path,
        decision={"decision": "feedback", "rationale": "fix X", "issues": []},
        evidence=_fired_evidence(),
        env={gate.BLOCKING_ENV_VAR: "1"},
    )
    assert decision["decision"] == "feedback"
    assert decision["rationale"] == "fix X"


def test_nothing_happens_when_the_check_did_not_fire(tmp_path: Path) -> None:
    decision, repo_root = _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(fired=False),
        env={gate.BLOCKING_ENV_VAR: "1"},
    )
    assert decision["decision"] == "approve"
    assert not (repo_root / gate.ZERO_TEST_QUEUE).exists()


def test_nothing_happens_when_gathering_stopped_before_the_check(
    tmp_path: Path,
) -> None:
    decision, repo_root = _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=None,
        env={gate.BLOCKING_ENV_VAR: "1"},
    )
    assert decision["decision"] == "approve"
    assert not (repo_root / gate.ZERO_TEST_QUEUE).exists()


# ===========================================================================
# 5. The receipt
# ===========================================================================


def test_the_receipt_carries_what_a_person_needs_to_adjudicate_it(
    tmp_path: Path,
) -> None:
    _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(),
        env={},
    )
    repo_root = tmp_path / "repo"
    rows = gate.read_receipts(repo_root)

    assert len(rows) == 1
    row = rows[0]
    # Which build, which task, when, where.
    assert row["feature_id"] == "FEAT-ZT99"
    assert row["task_id"] == "TASK-ZT-001"
    assert row["turn"] == 1
    assert row["repo"] == "repo"
    assert row["recorded_at"]
    # What changed, and whether any test file exists.
    assert row["files_created"] == ["docs/guide.md"]
    assert row["files_modified"] == ["README.md"]
    assert row["any_test_file_on_disk"] is False
    # What the Coach decided anyway — the number that makes this worth reading.
    assert row["coach_decision"] == "approve"
    assert row["blocking_requested"] is False
    assert row["decision_overridden"] is False
    # The half only a person can fill in.
    assert row["legitimately_test_free"] is None


def test_the_receipt_is_also_written_beside_the_verdict(tmp_path: Path) -> None:
    """A person debugging ONE build looks in that build's own folder."""
    _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(),
        env={},
    )
    # The literal path is pinned here on purpose: a test that reads the same
    # constant the code writes would still pass if the constant moved.
    per_turn = (
        tmp_path
        / "repo"
        / ".guardkit"
        / "worktrees"
        / "FEAT-ZT99"
        / ".guardkit"
        / "autobuild"
        / "TASK-ZT-001"
        / "zero_test_turn_1.json"
    )
    assert per_turn.is_file()
    assert json.loads(per_turn.read_text())["task_id"] == "TASK-ZT-001"


def test_the_ledger_accumulates_across_turns(tmp_path: Path) -> None:
    """Advisory-first is worthless unless the measurement piles up."""
    for turn in (1, 2, 3):
        _run_guard(
            tmp_path,
            decision={"decision": "approve", "rationale": "fine", "issues": []},
            evidence=_fired_evidence(),
            env={},
            turn=turn,
        )
    rows = gate.read_receipts(tmp_path / "repo")
    assert [row["turn"] for row in rows] == [1, 2, 3]


def test_the_ledger_lives_at_the_repository_root_not_in_the_worktree(
    tmp_path: Path,
) -> None:
    """Worktrees are deleted when a feature is archived; the ledger must not be."""
    _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(),
        env={},
    )
    repo_root = tmp_path / "repo"
    worktree = repo_root / ".guardkit" / "worktrees" / "FEAT-ZT99"
    # Literal path, pinned deliberately (see the note above).
    assert (repo_root / ".guardkit" / "zero-test" / "queue.jsonl").is_file()
    assert not (worktree / gate.ZERO_TEST_QUEUE).exists()


def test_an_override_is_recorded_as_an_override(tmp_path: Path) -> None:
    _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(),
        env={gate.BLOCKING_ENV_VAR: "1"},
    )
    row = gate.read_receipts(tmp_path / "repo")[0]
    assert row["blocking_requested"] is True
    assert row["decision_overridden"] is True
    assert row["coach_decision"] == "approve"


def test_an_unwritable_ledger_never_breaks_the_build(tmp_path: Path) -> None:
    with patch.object(
        gate, "write_receipt", side_effect=OSError("read-only filesystem")
    ):
        decision, _ = _run_guard(
            tmp_path,
            decision={"decision": "approve", "rationale": "fine", "issues": []},
            evidence=_fired_evidence(),
            env={},
        )
    assert decision["decision"] == "approve"


def test_a_corrupt_ledger_line_is_skipped_not_fatal(tmp_path: Path) -> None:
    ledger = tmp_path / gate.ZERO_TEST_QUEUE
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps({"task_id": "TASK-A"}) + "\nnot json at all\n"
        + json.dumps({"task_id": "TASK-B"}) + "\n"
    )
    rows = gate.read_receipts(tmp_path)
    assert [row["task_id"] for row in rows] == ["TASK-A", "TASK-B"]


def test_no_ledger_means_no_rows(tmp_path: Path) -> None:
    assert gate.read_receipts(tmp_path) == []


# ===========================================================================
# 6. The guard against silent promotion
# ===========================================================================


def test_the_flip_is_wired_to_the_flag_and_to_nothing_else(
    tmp_path: Path,
) -> None:
    """Nobody may make this block without deciding to.

    The point of advisory-first is that promotion is a decision someone makes
    once the measurement exists. This test proves the verdict flip is
    controlled by ``blocking_requested`` — the one function that reads the
    flag — and by nothing else. If someone hardcodes the flip, or keys it off
    the finding's severity, or off the task profile's own
    ``zero_test_blocking``, the first half of this test goes red.
    """
    # The flag says no -> the verdict stands, even though the check fired at
    # severity "error" on a profile whose legacy setting blocks.
    with patch.object(gate, "blocking_requested", return_value=False):
        decision, _ = _run_guard(
            tmp_path / "off",
            decision={"decision": "approve", "rationale": "fine", "issues": []},
            evidence=_fired_evidence(
                severity="error", profile_blocks_on_zero_tests=True
            ),
            env={gate.BLOCKING_ENV_VAR: "1"},
        )
    assert decision["decision"] == "approve", (
        "the verdict flipped while the flag said advisory — this check has "
        "been silently promoted to a blocking gate"
    )

    # The flag says yes -> it flips. Proves the wiring is live, not dead code.
    with patch.object(gate, "blocking_requested", return_value=True):
        decision, _ = _run_guard(
            tmp_path / "on",
            decision={"decision": "approve", "rationale": "fine", "issues": []},
            evidence=_fired_evidence(),
            env={},
        )
    assert decision["decision"] == "feedback"


def test_the_real_process_environment_does_not_block_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no env argument at all, the live default is still advisory."""
    monkeypatch.delenv(gate.BLOCKING_ENV_VAR, raising=False)
    worktree = _worktree(tmp_path)
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    decision = {"decision": "approve", "rationale": "fine", "issues": []}
    coach_path = worktree / "coach_turn_1.json"
    coach_path.write_text(json.dumps(decision))

    invoker._apply_zero_test_guard(
        decision=decision,
        evidence_bundle=CoachEvidenceBundle(
            honesty=None, zero_test=_fired_evidence()
        ),
        task_id="TASK-ZT-001",
        turn=1,
        coach_output_path=coach_path,
    )

    assert decision["decision"] == "approve"


# ===========================================================================
# The reading instrument
# ===========================================================================


def test_the_report_answers_both_halves_of_the_promotion_question(
    tmp_path: Path,
) -> None:
    """One command: how many wrote no tests, and how many were legitimate."""
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    ledger = tmp_path / gate.ZERO_TEST_QUEUE
    ledger.parent.mkdir(parents=True)
    rows = [
        gate.build_receipt(
            evidence=_fired_evidence(),
            task_id="TASK-A",
            turn=1,
            feature_id="FEAT-1",
            repo="guardkit",
            repo_path="/x",
            coach_decision="approve",
            blocking=False,
            overridden=False,
        ),
        gate.build_receipt(
            evidence=_fired_evidence(),
            task_id="TASK-B",
            turn=1,
            feature_id="FEAT-2",
            repo="guardkit",
            repo_path="/x",
            coach_decision="approve",
            blocking=False,
            overridden=False,
        ),
    ]
    rows[1]["legitimately_test_free"] = True
    ledger.write_text("".join(json.dumps(r) + "\n" for r in rows))

    result = CliRunner().invoke(
        zero_test_report, ["--repo-root", str(tmp_path)]
    )

    assert result.exit_code == 0
    output = result.output
    # Half one: the count, answered by the machine.
    assert "2 turn(s) wrote no test file" in output
    assert "The Coach approved 2 of them anyway." in output
    # Half two: the rulings so far, and the short list still needing one.
    assert "1 legitimately test-free" in output
    assert "1 still needs your ruling" in output
    assert "TASK-A" in output
    assert "TASK-B" not in output  # already ruled on


def test_the_report_can_read_several_repositories_at_once(
    tmp_path: Path,
) -> None:
    """Builds run in more than one repository; each keeps its own ledger."""
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    for name, task in (("guardkit", "TASK-G"), ("forge", "TASK-F")):
        ledger = tmp_path / name / gate.ZERO_TEST_QUEUE
        ledger.parent.mkdir(parents=True)
        ledger.write_text(
            json.dumps(
                gate.build_receipt(
                    evidence=_fired_evidence(),
                    task_id=task,
                    turn=1,
                    feature_id="FEAT-1",
                    repo=name,
                    repo_path=str(tmp_path / name),
                    coach_decision="approve",
                    blocking=False,
                    overridden=False,
                )
            )
            + "\n"
        )

    result = CliRunner().invoke(
        zero_test_report,
        [
            "--repo-root",
            str(tmp_path / "guardkit"),
            "--repo-root",
            str(tmp_path / "forge"),
        ],
    )

    assert result.exit_code == 0
    assert "2 turn(s) wrote no test file" in result.output
    assert "TASK-G" in result.output
    assert "TASK-F" in result.output


def test_the_report_says_so_plainly_when_nothing_has_been_recorded(
    tmp_path: Path,
) -> None:
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    result = CliRunner().invoke(
        zero_test_report, ["--repo-root", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "No build has been recorded writing zero tests." in result.output


def test_the_report_can_emit_the_raw_rows(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    ledger = tmp_path / gate.ZERO_TEST_QUEUE
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps({"task_id": "TASK-A", "turn": 1}) + "\n")

    result = CliRunner().invoke(
        zero_test_report, ["--repo-root", str(tmp_path), "--json"]
    )
    assert result.exit_code == 0
    assert "TASK-A" in result.output


# ===========================================================================
# Small surfaces
# ===========================================================================


def test_a_build_outside_a_worktree_names_no_feature(tmp_path: Path) -> None:
    """Honest absence beats a guess when there is no worktree to read a name from."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = tmp_path
    assert invoker._zero_test_feature_id() is None


def test_evidence_survives_a_player_report_with_odd_file_lists(
    tmp_path: Path,
) -> None:
    """A malformed report must not crash the instrument."""
    validator = _validator(_worktree(tmp_path))
    results = _results()
    results["files_created"] = "not-a-list"
    results["files_modified"] = [None, 17, "src/ok.py"]

    evidence = gate.evaluate_zero_test(
        validator,
        task_work_results=results,
        profile=_feature_profile(),
        independent_tests=_skipped_independent_run(),
        task_id="TASK-ZT-001",
    )
    assert evidence["files_created"] == []
    assert evidence["files_modified"] == ["src/ok.py"]
