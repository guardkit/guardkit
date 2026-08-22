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

import asyncio
import fcntl
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from guardkit.orchestrator import zero_test_gate as gate
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.models.task_types import TaskType, get_profile


# ===========================================================================
# Helpers
# ===========================================================================


@pytest.fixture(autouse=True)
def _ledger_stays_in_the_temporary_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep every test in this file out of the real durable ledger.

    The ledger deliberately lives OUTSIDE the repository, under the user's
    home directory (see the zero_test_gate module docstring and D-OBS-4). A
    test suite that wrote there would pollute a real measurement, so every
    test in this file redirects it.
    """
    monkeypatch.setenv(gate.ZERO_TEST_ROOT_ENV_VAR, str(tmp_path / "durable"))


def _flat(output: str) -> str:
    """Report text as one line, free of the console's box drawing.

    The summary panel wraps to the terminal width and puts a border character
    at each end of every line, so a sentence in it is never contiguous in the
    raw output. Assertions read this instead.
    """
    for border in "\u2502\u256d\u256e\u2570\u256f\u2500\u250f\u2513\u2517\u251b\u2501\u2503":
        output = output.replace(border, " ")
    return " ".join(output.split())


def _durable_ledger(tmp_path: Path, repo_name: str = "repo") -> Path:
    """Where a given repository's ledger lands while these tests run."""
    return tmp_path / "durable" / repo_name / gate.ZERO_TEST_QUEUE_FILENAME


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


def _coach_instructions() -> str:
    """The written instructions the live (language-model) Coach is installed with."""
    return (
        Path(__file__).resolve().parents[2]
        / "installer"
        / "core"
        / "agents"
        / "autobuild-coach.md"
    ).read_text(encoding="utf-8")


def _fired_evidence(**overrides) -> dict:
    evidence = {
        "fired": True,
        "branch": gate.BRANCH_NO_TEST_FILE,
        "branch_meaning": gate.BRANCH_MEANINGS[gate.BRANCH_NO_TEST_FILE],
        "counts_toward_promotion": True,
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
        "claimed_all_passed": True,
        "claimed_tests_passed": 0,
        "claimed_coverage": None,
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
    # The same mapping carries the blocking flag AND the ledger location, so
    # no test can write into the real one under the user's home directory.
    env = {gate.ZERO_TEST_ROOT_ENV_VAR: str(tmp_path / "durable"), **env}

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
    # Labelled, on the real path, by the real rule.
    assert bundle.zero_test["branch"] == gate.BRANCH_NO_TEST_FILE
    assert bundle.zero_test["counts_toward_promotion"] is True
    # And it survives serialisation into the Coach's prompt / turn record.
    assert bundle.to_dict()["zero_test"]["fired"] is True
    assert bundle.to_dict()["zero_test"]["branch"] == gate.BRANCH_NO_TEST_FILE


def test_the_live_coach_path_labels_the_second_branch_too(tmp_path: Path) -> None:
    """The same real ``gather_evidence`` run, on a turn whose tests exist.

    Nothing is mocked here except the Coach's own test runner. The Player
    wrote a real test file, it is on disk, and the report still claims a
    passing quality gate with zero tests executed — so the rule fires on its
    second branch and must be labelled as such all the way onto the bundle.
    """
    worktree = _worktree(tmp_path)
    (worktree / "src" / "auth.py").write_text("# code\n")
    (worktree / "tests" / "test_auth.py").write_text("def test_x(): pass\n")
    results_dir = worktree / ".guardkit" / "autobuild" / "TASK-ZT-001"
    (results_dir / "task_work_results.json").write_text(
        json.dumps(_branch_two_report())
    )

    # The Coach's own run happened and reported a failure — so it is neither
    # the "found nothing" result that defines branch one, nor the genuine
    # pass that suppresses the rule outright.
    ran_and_failed = IndependentTestResult(
        tests_passed=False,
        test_command="pytest tests/test_auth.py",
        test_output_summary="1 failed",
        duration_seconds=0.1,
    )
    validator = _validator(worktree)
    with patch.object(
        validator, "run_independent_tests", return_value=ran_and_failed
    ):
        bundle = validator.gather_evidence(
            task_id="TASK-ZT-001",
            turn=1,
            task={"acceptance_criteria": [], "task_type": "feature"},
            skip_arch_review=True,
        )

    assert bundle.gathering_status == "complete", bundle.gathering_error
    assert bundle.zero_test["fired"] is True
    assert bundle.zero_test["branch"] == gate.BRANCH_TESTS_NOT_EXECUTED
    assert bundle.zero_test["any_test_file_on_disk"] is True
    assert bundle.zero_test["counts_toward_promotion"] is False


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
    instructions = _coach_instructions()
    assert "When the Tests Are Missing — or Were Never Run" in instructions
    # BOTH branches, told apart. An instruction file that described only one
    # of them would leave the model applying branch one's remedy ("write a
    # test") to branch two's problem (tests exist; the claim is unsupported).
    assert "NO TEST FILE WAS WRITTEN" in instructions
    assert "THE REPORT SAYS NO TEST RAN" in instructions
    assert gate.BRANCH_NO_TEST_FILE in instructions
    assert gate.BRANCH_TESTS_NOT_EXECUTED in instructions
    assert "It does not mean tests are missing" in instructions


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
    assert not _durable_ledger(tmp_path).exists()


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
    assert not _durable_ledger(tmp_path).exists()


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


def test_the_ledger_lives_outside_the_repository_entirely(
    tmp_path: Path,
) -> None:
    """Not in the worktree, and not in the repository either.

    A worktree is deleted when a feature is archived, and anything untracked
    inside the repository is deleted by ``git clean -fdx``. The measurement is
    the deliverable, so it lives outside both — see D-OBS-4 in the module
    docstring.
    """
    _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(),
        env={},
    )
    repo_root = tmp_path / "repo"
    worktree = repo_root / ".guardkit" / "worktrees" / "FEAT-ZT99"

    ledger = _durable_ledger(tmp_path)
    assert ledger.is_file()
    assert repo_root not in ledger.parents, (
        "the ledger is inside the repository, where git clean -fdx deletes it"
    )
    assert worktree not in ledger.parents
    # Nothing is written to the old in-tree location any more.
    assert not (repo_root / gate.LEGACY_IN_TREE_QUEUE).exists()


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
    ledger = gate.ledger_path_for(tmp_path)
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

    ledger = gate.ledger_path_for(tmp_path)
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
    output = _flat(result.output)
    # Half one: the count, answered by the machine.
    assert "2 had no test found" in output
    assert "the Coach approved 2 of them anyway" in output
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
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
        ledger = gate.ledger_path_for(tmp_path / name)
        ledger.parent.mkdir(parents=True, exist_ok=True)
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
    assert "2 recorded turn(s)" in result.output
    assert "TASK-G" in result.output
    assert "TASK-F" in result.output


def test_the_report_says_so_plainly_when_the_ledger_is_there_and_empty(
    tmp_path: Path,
) -> None:
    """A clean bill of health — and the ONLY case that earns one.

    The ledger exists, so the report really did look at the place builds
    write to, and really did find nothing there.
    """
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    ledger = gate.ledger_path_for(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("")

    result = CliRunner().invoke(
        zero_test_report, ["--repo-root", str(tmp_path)]
    )
    output = _flat(result.output)
    assert result.exit_code == 0
    assert "No build has been recorded with missing or unrun tests." in output
    assert "The ledger exists and is empty" in output
    assert "NO LEDGER FILE EXISTS" not in output


def test_no_ledger_at_all_is_never_reported_as_a_clean_result(
    tmp_path: Path,
) -> None:
    """"Found nothing" and "nothing to find" are different, and must read so.

    This is the instrument's own disease: a check that answers a narrower
    question than it appears to. Someone runs the report, sees a clean
    result, and concludes that no build skipped its tests — when in fact no
    ledger was ever opened. It must say which of the two happened.
    """
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    assert not gate.ledger_path_for(tmp_path).exists()

    result = CliRunner().invoke(
        zero_test_report, ["--repo-root", str(tmp_path)]
    )
    output = _flat(result.output)

    assert result.exit_code == 0
    assert "NO LEDGER FILE EXISTS" in output
    assert "not a clean result" in output
    assert "No build has been recorded" not in output, (
        "a missing ledger was reported as a clean bill of health — the exact "
        "fault this instrument exists to catch"
    )


def test_the_report_can_emit_the_raw_rows(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    ledger = gate.ledger_path_for(tmp_path)
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


# ===========================================================================
# 7. THE TWO BRANCHES
#
# The underlying rule fires for two different reasons and labels both the
# same. Before this section existed, the sentence shown to the Coach and the
# row written to the ledger asserted branch one's facts about BOTH — which is
# flatly false for branch two, and corrupts the one number the whole
# instrument exists to produce.
# ===========================================================================


def _branch_one_report() -> dict:
    """A turn that wrote no test at all: nothing named, nothing found."""
    return _results(files_created=["docs/guide.md"], files_modified=["README.md"])


def _branch_two_report() -> dict:
    """A turn that DID write a test, whose report claims a pass with 0 tests run."""
    return _results(
        tests_written=["tests/test_auth.py"],
        files_created=["tests/test_auth.py", "src/auth.py"],
    )


def test_branch_one_is_labelled_when_no_test_file_was_written(
    tmp_path: Path,
) -> None:
    """The rule's first branch: the Player named none, the search found none."""
    worktree = _worktree(tmp_path)
    (worktree / "src" / "auth.py").write_text("# code, no tests\n")

    evidence = gate.evaluate_zero_test(
        _validator(worktree),
        task_work_results=_branch_one_report(),
        profile=_feature_profile(),
        independent_tests=_skipped_independent_run(),
        task_id="TASK-ZT-001",
    )

    assert evidence["fired"] is True
    assert evidence["branch"] == gate.BRANCH_NO_TEST_FILE
    # The label is tied to what the REAL rule said, so reordering the rule's
    # branches turns this red instead of silently mislabelling every row.
    assert evidence["description"].startswith("No task-specific tests found")
    assert evidence["counts_toward_promotion"] is True


def test_branch_two_is_labelled_when_the_report_claims_a_pass_with_no_test_run(
    tmp_path: Path,
) -> None:
    """The rule's second branch — and the proof the old sentence was false.

    Everything here is the opposite of branch one: a test file was named, it
    exists on disk, and the Coach's independent run is not the "found
    nothing" result. The rule still fires, because the Player's report claims
    every quality gate passed while reporting that zero tests executed.
    """
    worktree = _worktree(tmp_path)
    (worktree / "tests" / "test_auth.py").write_text("def test_x(): pass\n")

    evidence = gate.evaluate_zero_test(
        _validator(worktree),
        task_work_results=_branch_two_report(),
        profile=_feature_profile(),
        independent_tests=None,
        task_id="TASK-ZT-001",
    )

    assert evidence["fired"] is True
    assert evidence["branch"] == gate.BRANCH_TESTS_NOT_EXECUTED
    assert evidence["description"].startswith(
        "Quality gates reported as passed"
    )
    # THE FALSIFIER for the old blended wording: it claimed that none of the
    # turn's files "is a test file that exists on disk". Here one is.
    assert evidence["any_test_file_on_disk"] is True
    assert evidence["test_files_on_disk"] == ["tests/test_auth.py"]
    # And the claim itself is recorded, because it is the whole finding.
    assert evidence["claimed_all_passed"] is True
    assert evidence["claimed_tests_passed"] == 0


def test_only_the_no_test_file_branch_feeds_the_promotion_measurement(
    tmp_path: Path,
) -> None:
    """Branch two cannot answer "did this change need a test?", so it is out.

    A ``tests_not_executed`` turn has not been shown to lack a test — tests
    may exist and may have been written that very turn. Counting it would put
    turns that are not test-free into the rate that decides whether this check
    is ever allowed to block a build.
    """
    worktree = _worktree(tmp_path)
    (worktree / "tests" / "test_auth.py").write_text("def test_x(): pass\n")

    branch_two = gate.evaluate_zero_test(
        _validator(worktree),
        task_work_results=_branch_two_report(),
        profile=_feature_profile(),
        independent_tests=None,
        task_id="TASK-ZT-001",
    )

    assert branch_two["counts_toward_promotion"] is False
    assert gate.COUNTS_TOWARD_PROMOTION == gate.BRANCH_NO_TEST_FILE
    assert gate.counts_toward_promotion({"branch": gate.BRANCH_NO_TEST_FILE})
    assert not gate.counts_toward_promotion(
        {"branch": gate.BRANCH_TESTS_NOT_EXECUTED}
    )
    # A row recorded before the branches were told apart is not guessed at.
    assert not gate.counts_toward_promotion({"task_id": "TASK-OLD"})


def test_the_branch_two_advisory_never_claims_that_no_test_was_written() -> None:
    """The sentence the Coach reads must be true of the branch that fired.

    Telling the Coach "no test file was written" about a turn whose tests
    exist sends it to ask for the wrong fix, and makes the receipt — and so
    the report, and so the promotion decision — describe something that did
    not happen.
    """
    evidence = _fired_evidence(
        branch=gate.BRANCH_TESTS_NOT_EXECUTED,
        branch_meaning=gate.BRANCH_MEANINGS[gate.BRANCH_TESTS_NOT_EXECUTED],
        counts_toward_promotion=False,
        tests_written=["tests/test_auth.py"],
        test_files_on_disk=["tests/test_auth.py"],
        any_test_file_on_disk=True,
        independent_test_command=None,
    )

    text = gate.coach_advisory_text(evidence)

    assert "NO TEST FILE WAS WRITTEN" not in text
    assert "found no task-specific test" not in text
    assert "THE REPORT SAYS NO TEST RAN" in text
    assert "1 test file(s) named by this turn DO exist on disk" in text
    assert "not a report of missing tests" in text
    assert "does NOT block" in text


def test_the_branch_one_advisory_says_only_what_is_true_of_branch_one() -> None:
    """The turn that really wrote nothing gets the flat statement.

    ``claimed_test_files`` empty means nothing anywhere in the report — not
    just in ``tests_written`` — is a file the Coach recognises as a test. That
    is the only shape of branch one about which "no test file was written"
    can be said.
    """
    text = gate.coach_advisory_text(_fired_evidence())

    assert "NO TEST FILE WAS WRITTEN" in text
    assert "lists nothing under tests_written" in text
    assert "is a file the Coach recognises as a test" in text
    assert "found no task-specific test to execute" in text
    assert "does NOT block" in text


def test_the_receipt_records_which_branch_fired(tmp_path: Path) -> None:
    """So the two are never conflated by anything reading the ledger."""
    _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(),
        env={},
        task_id="TASK-ONE",
    )
    _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(
            branch=gate.BRANCH_TESTS_NOT_EXECUTED,
            branch_meaning=gate.BRANCH_MEANINGS[gate.BRANCH_TESTS_NOT_EXECUTED],
            counts_toward_promotion=False,
        ),
        env={},
        task_id="TASK-TWO",
    )

    rows = {row["task_id"]: row for row in gate.read_receipts(tmp_path / "repo")}
    assert rows["TASK-ONE"]["branch"] == gate.BRANCH_NO_TEST_FILE
    assert rows["TASK-ONE"]["counts_toward_promotion"] is True
    assert rows["TASK-TWO"]["branch"] == gate.BRANCH_TESTS_NOT_EXECUTED
    assert rows["TASK-TWO"]["counts_toward_promotion"] is False
    # Each row explains itself to a reader who has never seen this module.
    assert "no test was found" in rows["TASK-ONE"]["branch_meaning"].lower()
    assert "may well exist" in rows["TASK-TWO"]["branch_meaning"].lower()


def test_a_blocked_branch_two_turn_is_not_told_to_write_a_test(
    tmp_path: Path,
) -> None:
    """Even the blocking message must match the branch that fired."""
    decision, _ = _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(
            branch=gate.BRANCH_TESTS_NOT_EXECUTED,
            branch_meaning=gate.BRANCH_MEANINGS[gate.BRANCH_TESTS_NOT_EXECUTED],
            counts_toward_promotion=False,
        ),
        env={gate.BLOCKING_ENV_VAR: "1"},
    )

    assert decision["decision"] == "feedback"
    assert "No test file was written" not in decision["rationale"]
    assert "zero tests ran" in decision["rationale"]
    assert "Run the tests and report the real counts" in decision["rationale"]
    assert decision["issues"][0]["details"]["branch"] == (
        gate.BRANCH_TESTS_NOT_EXECUTED
    )


# ===========================================================================
# 8. THE REPORT KEEPS THEM APART
# ===========================================================================


def _write_ledger(root: Path, rows: list) -> None:
    ledger = gate.ledger_path_for(root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _receipt(evidence: dict, task_id: str, **overrides) -> dict:
    row = gate.build_receipt(
        evidence=evidence,
        task_id=task_id,
        turn=1,
        feature_id="FEAT-1",
        repo="repo",
        repo_path="/x",
        coach_decision="approve",
        blocking=False,
        overridden=False,
    )
    row.update(overrides)
    return row


def test_the_report_keeps_the_two_situations_apart(tmp_path: Path) -> None:
    """They are different situations and Rich will rule on them differently."""
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    _write_ledger(
        tmp_path,
        [
            _receipt(_fired_evidence(), "TASK-NOTEST"),
            _receipt(
                _fired_evidence(
                    branch=gate.BRANCH_TESTS_NOT_EXECUTED,
                    counts_toward_promotion=False,
                    tests_written=["tests/test_auth.py"],
                    test_files_on_disk=["tests/test_auth.py"],
                    any_test_file_on_disk=True,
                ),
                "TASK-UNRUN",
            ),
        ],
    )

    output = _flat(
        CliRunner()
        .invoke(zero_test_report, ["--repo-root", str(tmp_path)])
        .output
    )

    # Counted separately...
    assert "1 had no test found" in output
    assert "1 claimed a passing quality gate while reporting that 0 tests ran" in output
    # ...listed separately...
    assert "NO TEST FOUND — needs your ruling" in output
    assert "REPORT CLAIMED A PASS WITH NO TEST RUN" in output
    # ...and only the first feeds the number the promotion decision rests on.
    assert "The promotion measurement is the first group only" in output
    assert "Of those 1, you have ruled" in output
    assert "1 still needs your ruling" in output
    assert "not part of the promotion measurement" in output
    assert "Do not rule these test-free" in output


def test_the_report_surfaces_the_fields_needed_to_spot_a_wrong_row(
    tmp_path: Path,
) -> None:
    """A person must be able to adjudicate a row without leaving the report.

    Whether a test file exists on disk, and what the Player actually claimed,
    are exactly the fields that expose a mis-attributed row — so they are on
    the default output, not behind ``--json``.
    """
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    _write_ledger(
        tmp_path,
        [
            _receipt(
                _fired_evidence(
                    files_created=["src/auth.py"],
                    files_modified=["docs/auth.md"],
                    tests_written=["tests/test_auth.py"],
                    test_files_on_disk=["tests/test_auth.py"],
                    any_test_file_on_disk=True,
                    claimed_tests_passed=0,
                    claimed_coverage=91.4,
                ),
                "TASK-ODD",
            )
        ],
    )

    output = _flat(
        CliRunner()
        .invoke(zero_test_report, ["--repo-root", str(tmp_path)])
        .output
    )

    assert "test file on disk : yes tests/test_auth.py" in output
    assert "tests named : tests/test_auth.py" in output
    assert (
        "player claimed : all_passed=True, tests_passed=0, coverage=91.4"
        in output
    )
    assert "created : src/auth.py" in output
    assert "modified : docs/auth.md" in output


def test_rows_recorded_before_the_branches_existed_are_not_guessed_at(
    tmp_path: Path,
) -> None:
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    legacy = _receipt(_fired_evidence(), "TASK-OLD")
    legacy.pop("branch")
    _write_ledger(tmp_path, [legacy])

    output = _flat(
        CliRunner()
        .invoke(zero_test_report, ["--repo-root", str(tmp_path)])
        .output
    )

    assert "1 was recorded before the two situations were told apart" in output
    assert "excluded from the promotion measurement" in output


# ===========================================================================
# 9. THE PRODUCTION WIRING
#
# Everything above calls _apply_zero_test_guard directly. None of it would
# notice if invoke_coach — the real Coach path a build takes — stopped calling
# it. And because this check is ADVISORY, a dropped call site has NO
# build-visible symptom: the instrument would simply stop measuring, silently,
# forever. These two tests are the only thing standing between that and a
# ledger that quietly stays empty. Modelled on
# tests/orchestrator/test_boot_smoke_wiring.py, which pins its own single
# wiring line the same way.
# ===========================================================================


def _wired_invoker(worktree: Path) -> AgentInvoker:
    """An AgentInvoker able to run a whole ``invoke_coach`` turn with no model.

    Mirrors ``tests/orchestrator/test_coach_gather_bfull.py::_make_invoker``.
    """
    from unittest.mock import MagicMock

    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)
    invoker._verify_player_claims = MagicMock(
        return_value=SimpleNamespace(
            verified=True, honesty_score=1.0, discrepancies=[]
        )
    )
    return invoker


def _verdict_events(task_id: str, decision: str = "approve"):
    """A harness event stream carrying a schema-valid fenced JSON verdict."""
    from guardkit.orchestrator.harness import (
        AssistantMessageEvent,
        ResultMessageEvent,
    )

    verdict = (
        "Reasoning prose.\n\n```json\n"
        f'{{"task_id": "{task_id}", "turn": 1, "decision": "{decision}", '
        '"rationale": "deterministic test verdict"}\n```'
    )
    return (
        None,
        [AssistantMessageEvent(text=verdict), ResultMessageEvent(session_id=None)],
    )


def _run_a_real_coach_turn(invoker: AgentInvoker, task_id: str):
    async def _stub_model_call(**_kwargs):
        return _verdict_events(task_id)

    invoker._invoke_with_role = _stub_model_call
    return asyncio.run(
        invoker.invoke_coach(
            task_id=task_id,
            turn=1,
            requirements="reqs",
            player_report={"files_modified": []},
            evidence_bundle=CoachEvidenceBundle(
                honesty=HonestyVerification(
                    verified=True,
                    discrepancies=[],
                    honesty_score=1.0,
                    resolved_paths=[],
                ),
                gathering_status="complete",
                zero_test=_fired_evidence(),
            ),
        )
    )


def test_invoke_coach_really_calls_the_zero_test_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The production Coach path must reach the guard. Nothing else proves it.

    Delete, comment out, or misplace the ``self._apply_zero_test_guard(...)``
    call in ``AgentInvoker.invoke_coach`` and this test goes red. Without it,
    that deletion is invisible: no test fails, no build changes, and the
    measurement silently stops.
    """
    monkeypatch.delenv(gate.BLOCKING_ENV_VAR, raising=False)
    invoker = _wired_invoker(_worktree(tmp_path))

    with patch.object(
        invoker, "_apply_zero_test_guard", autospec=True
    ) as guard:
        result = _run_a_real_coach_turn(invoker, "TASK-WIRED-001")

    assert result.success is True
    assert guard.call_count == 1, (
        "invoke_coach did not call the zero-test guard — the advisory check "
        "is disconnected and would record nothing, with no other symptom"
    )
    passed = guard.call_args.kwargs
    assert passed["task_id"] == "TASK-WIRED-001"
    assert passed["turn"] == 1
    assert passed["decision"]["decision"] == "approve"
    assert passed["evidence_bundle"].zero_test["fired"] is True


def test_a_real_invoke_coach_turn_records_a_ledger_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same wiring, proven by its effect rather than by a stand-in.

    A spy proves the call happens; this proves the call does its job all the
    way to the durable ledger, through the real ``invoke_coach``.
    """
    monkeypatch.delenv(gate.BLOCKING_ENV_VAR, raising=False)
    invoker = _wired_invoker(_worktree(tmp_path))

    result = _run_a_real_coach_turn(invoker, "TASK-WIRED-002")

    assert result.success is True
    rows = gate.read_receipts(tmp_path / "repo")
    assert [row["task_id"] for row in rows] == ["TASK-WIRED-002"]
    assert rows[0]["branch"] == gate.BRANCH_NO_TEST_FILE
    # Advisory: the verdict the Coach reached is untouched, and recorded.
    assert rows[0]["coach_decision"] == "approve"
    assert rows[0]["decision_overridden"] is False


# ===========================================================================
# 10. THE LEDGER SURVIVES ORDINARY HOUSEKEEPING
#
# The measurement IS the deliverable. Decision of Record D-OBS-4 (2026-07-09)
# put the durable home for .guardkit artifacts outside the repository for
# exactly this reason: in-tree artifacts are one copy on one machine with no
# git recovery.
# ===========================================================================


def test_git_clean_fdx_does_not_delete_the_ledger(tmp_path: Path) -> None:
    """The housekeeping command that used to wipe this measurement."""
    repo_root = tmp_path / "repo"
    _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(),
        env={},
    )
    ledger = _durable_ledger(tmp_path)
    assert ledger.is_file()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo_root, check=True,
                   capture_output=True)
    # A control file: if this survives, the clean did not really run and the
    # test would be proving nothing.
    control = repo_root / "untracked-control.txt"
    control.write_text("delete me\n")
    subprocess.run(["git", "clean", "-fdx"], cwd=repo_root, check=True,
                   capture_output=True)

    assert not control.exists(), "git clean -fdx did not run; test proves nothing"
    assert ledger.is_file(), (
        "git clean -fdx deleted the ledger — the measurement is destructible"
    )
    assert json.loads(ledger.read_text().splitlines()[0])["task_id"] == (
        "TASK-ZT-001"
    )


def test_the_default_ledger_home_is_outside_every_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no override set, the ledger still lands outside the repo tree."""
    monkeypatch.delenv(gate.ZERO_TEST_ROOT_ENV_VAR, raising=False)
    repo_root = tmp_path / "some-repo"
    repo_root.mkdir()

    ledger = gate.ledger_path_for(repo_root)

    assert repo_root not in ledger.parents
    assert ledger.parent == gate.ZERO_TEST_HOME / "some-repo"
    assert str(gate.ZERO_TEST_HOME).startswith(str(Path.home()))


def test_rows_written_to_the_old_in_tree_path_are_still_read(
    tmp_path: Path,
) -> None:
    """Moving the ledger must not silently drop what was already recorded."""
    repo_root = tmp_path / "repo"
    old = repo_root / gate.LEGACY_IN_TREE_QUEUE
    old.parent.mkdir(parents=True)
    old.write_text(json.dumps({"task_id": "TASK-RECORDED-EARLIER"}) + "\n")

    _run_guard(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        evidence=_fired_evidence(),
        env={},
    )

    task_ids = [row["task_id"] for row in gate.read_receipts(repo_root)]
    assert "TASK-RECORDED-EARLIER" in task_ids
    assert "TASK-ZT-001" in task_ids

    # And the report names the old file too, so a person can find the row it
    # is asking them to rule on.
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    output = _flat(
        CliRunner()
        .invoke(zero_test_report, ["--repo-root", str(repo_root)])
        .output
    )
    assert str(repo_root / gate.LEGACY_IN_TREE_QUEUE) in output


# ===========================================================================
# 11. CONCURRENT BUILDS
#
# Eleven autobuild worktrees were live against this one repository when this
# was written, and they all append to its single ledger. Two finishing a turn
# together must not splice one line into another: a dropped row is a silently
# wrong measurement.
# ===========================================================================


#: A standalone program that appends to the ledger, used to run several REAL
#: concurrent writers. Separate processes, because that is what production
#: is: many autobuild worktrees, each its own process, one ledger. The module
#: is loaded straight from its file so the child starts in a few milliseconds
#: and every writer really is racing the others.
_APPENDER = """
import importlib.util, json, os, sys, time
from pathlib import Path

spec = importlib.util.spec_from_file_location("ztg", sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules["ztg"] = module  # required before exec_module; see importlib docs
spec.loader.exec_module(module)

ledger, writer, count, go = Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5]
while not os.path.exists(go):
    time.sleep(0.005)
for index in range(count):
    record = {"task_id": "TASK-%s-%d" % (writer, index), "padding": "x" * 20000}
    module._append_line_atomically(ledger, json.dumps(record, sort_keys=True) + chr(10))
"""


def test_concurrent_appends_do_not_lose_or_splice_rows(tmp_path: Path) -> None:
    """Eight real processes, one ledger, every row intact.

    Records are padded past the operating system's file-buffer size on
    purpose. A buffered text-mode append — what this code used to do — flushes
    a record that large in several separate writes, and another process's
    bytes land in between, destroying both rows. That is what makes this a
    real test rather than a formality.
    """
    ledger = gate.ledger_path_for(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    program = tmp_path / "appender.py"
    program.write_text(_APPENDER)
    go = tmp_path / "go"
    writers, per_writer = 8, 10

    children = [
        subprocess.Popen(
            [
                sys.executable,
                str(program),
                str(Path(gate.__file__)),
                str(ledger),
                str(writer),
                str(per_writer),
                str(go),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for writer in range(writers)
    ]
    go.write_text("start")  # release them all at once
    for child in children:
        _, err = child.communicate(timeout=60)
        assert child.returncode == 0, err.decode()

    lines = [line for line in ledger.read_text().splitlines() if line.strip()]
    assert len(lines) == writers * per_writer, (
        f"expected {writers * per_writer} rows, found {len(lines)} — rows were "
        "lost or spliced by concurrent appends"
    )
    task_ids = set()
    for number, line in enumerate(lines, start=1):
        try:
            task_ids.add(json.loads(line)["task_id"])
        except ValueError as exc:  # pragma: no cover - only on a real defect
            pytest.fail(
                f"ledger line {number} was spliced and will not parse: {exc}"
            )
    assert len(task_ids) == writers * per_writer, "rows were overwritten"


def test_a_short_write_cannot_truncate_a_row(tmp_path: Path) -> None:
    """The kernel may accept fewer bytes than offered; the row must survive.

    ``os.write`` is allowed to write only part of what it is given. If the
    append stopped there, the ledger would hold half a row — which is a
    dropped row, and a silently wrong measurement. Here the operating system
    is made to accept seven bytes at a time.
    """
    ledger = tmp_path / "queue.jsonl"
    real_write = os.write

    def stingy_write(fd: int, data: bytes) -> int:
        return real_write(fd, data[:7])

    line = json.dumps({"task_id": "TASK-SHORT", "pad": "z" * 500}) + "\n"
    with patch.object(os, "write", side_effect=stingy_write):
        gate._append_line_atomically(ledger, line)

    assert ledger.read_text() == line, "the row was truncated by a short write"


def test_the_append_serialises_writers_with_an_exclusive_lock(
    tmp_path: Path,
) -> None:
    """One writer at a time — the guarantee, tested rather than assumed.

    A race between real processes may or may not reproduce on any given run,
    so this tests the mechanism directly: while this test holds the ledger's
    lock, an append must not complete; once released, it must.
    """
    ledger = tmp_path / "queue.jsonl"
    ledger.touch()
    finished = threading.Event()

    def append_one() -> None:
        gate._append_line_atomically(
            ledger, json.dumps({"task_id": "TASK-BLOCKED"}) + "\n"
        )
        finished.set()

    holder = os.open(ledger, os.O_WRONLY | os.O_APPEND)
    try:
        fcntl.flock(holder, fcntl.LOCK_EX)
        writer = threading.Thread(target=append_one)
        writer.start()
        assert not finished.wait(timeout=0.5), (
            "the append completed while another writer held the lock — "
            "concurrent builds are not serialised and rows can be spliced"
        )
    finally:
        fcntl.flock(holder, fcntl.LOCK_UN)
        os.close(holder)

    assert finished.wait(timeout=5), "the append never completed after unlock"
    writer.join(timeout=5)
    assert json.loads(ledger.read_text())["task_id"] == "TASK-BLOCKED"


def test_every_recorded_row_survives_a_reader_running_at_the_same_time(
    tmp_path: Path,
) -> None:
    """Reading the ledger while builds append must never see a partial row."""
    ledger = gate.ledger_path_for(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    seen_bad = []

    def keep_reading() -> None:
        while not stop.is_set():
            for row in gate.read_receipts(tmp_path):
                if "task_id" not in row:
                    seen_bad.append(row)

    reader = threading.Thread(target=keep_reading)
    reader.start()
    try:
        for index in range(40):
            gate._append_line_atomically(
                ledger,
                json.dumps({"task_id": f"TASK-{index}", "pad": "y" * 20_000})
                + "\n",
            )
    finally:
        stop.set()
        reader.join()

    assert seen_bad == []
    assert len(gate.read_receipts(tmp_path)) == 40


# ===========================================================================
# 12. THE WORDING OF BRANCH ONE MUST BE TRUE OF EVERY TURN THAT REACHES IT
#
# The rule reads ``tests_written`` and nothing else. A Player may name a test
# file under ``files_created`` / ``files_modified`` — the rule's own
# remediation text tells it to — and the rule will not see it. Separately, the
# Coach's search that reports ``"skipped"`` only ever collects PYTHON tests,
# so it also comes up empty for a test in another language, a test excluded
# from collection, and pytest-bdd glue.
#
# Every combination of those reaches branch one on a turn whose report DOES
# name a real, present test file. The tests below build those turns for real
# and run the real rule over them: no mocked rule, no hand-made "skipped"
# result, no hand-written evidence dict.
# ===========================================================================


def _real_branch_one_evidence(worktree: Path, results: dict) -> dict:
    """Run the REAL rule and the REAL independent test run over one turn.

    Nothing here is stubbed. ``run_independent_tests`` walks its whole
    detection ladder against the files actually on disk, and
    ``evaluate_zero_test`` calls ``CoachValidator._check_zero_test_anomaly``
    itself. What comes back is what a live build would have produced.
    """
    validator = CoachValidator(str(worktree), task_id="TASK-ZT-001")
    independent = validator.run_independent_tests(
        task_work_results=results, task=None, turn=1
    )
    assert independent.test_command == "skipped", (
        "this turn did not reach branch one; the detection ladder found "
        f"{independent.test_command!r} to run"
    )
    evidence = gate.evaluate_zero_test(
        validator,
        task_work_results=results,
        profile=_feature_profile(),
        independent_tests=independent,
        task_id="TASK-ZT-001",
        requirements=None,
    )
    assert evidence["fired"] is True
    assert evidence["branch"] == gate.BRANCH_NO_TEST_FILE
    return evidence


@pytest.mark.parametrize(
    "test_file, description",
    [
        ("src/widget.test.ts", "a TypeScript test — the search collects only Python"),
        ("src/widget_test.go", "a Go test — likewise invisible to the search"),
        ("tests/Widget/Tests/WidgetTests.cs", "a .NET test — likewise"),
    ],
)
def test_branch_one_never_claims_no_test_file_when_the_report_names_one(
    tmp_path: Path, test_file: str, description: str
) -> None:
    """The sentence must be true of THIS turn, not of the branch's name.

    Each of these is a real turn: the Player wrote a test, listed it under
    ``files_created``, and left ``tests_written`` empty. The rule fires
    because it only ever reads ``tests_written``, and the Coach's search
    reports ``skipped`` because it only ever collects Python. Telling the
    Coach "the Player's report names no test file" would be a plain
    falsehood, and it is what the previous wording said.
    """
    worktree = _worktree(tmp_path)
    written = worktree / test_file
    written.parent.mkdir(parents=True, exist_ok=True)
    written.write_text("// a test\n")
    results = _results(files_created=["src/widget.src", test_file])

    evidence = _real_branch_one_evidence(worktree, results)

    assert evidence["tests_written"] == []
    assert evidence["claimed_test_files"] == [test_file], description
    assert evidence["test_files_on_disk"] == [test_file]

    text = gate.coach_advisory_text(evidence)
    assert "NO TEST FILE WAS WRITTEN" not in text, (
        f"branch one told the Coach no test file was written, but {test_file} "
        "is named in the report and present on disk"
    )
    assert "names no test file" not in text
    assert "NO TEST RAN, AND NONE WAS LISTED AS WRITTEN" in text
    assert "lists nothing under tests_written" in text
    assert "DOES name 1 file(s) that look like tests" in text
    assert test_file in text
    assert "1 exist(s) on disk" in text
    assert "does NOT block" in text


def test_branch_one_is_honest_about_a_python_test_excluded_from_collection(
    tmp_path: Path,
) -> None:
    """The same falsehood, reachable without leaving Python.

    A root ``conftest.py`` carrying ``collect_ignore_glob`` tells pytest not
    to collect a path. The Coach's detection honours it, so a perfectly
    ordinary ``test_*.py`` written this turn leaves the search with nothing to
    run — and the rule, reading only ``tests_written``, fires.
    """
    worktree = _worktree(tmp_path)
    (worktree / "conftest.py").write_text('collect_ignore_glob = ["tests/wip/*"]\n')
    (worktree / "tests" / "wip").mkdir(parents=True, exist_ok=True)
    (worktree / "tests" / "wip" / "test_widget.py").write_text(
        "def test_widget():\n    assert True\n"
    )
    results = _results(
        files_created=["src/widget.py", "tests/wip/test_widget.py"]
    )

    evidence = _real_branch_one_evidence(worktree, results)
    text = gate.coach_advisory_text(evidence)

    assert evidence["test_files_on_disk"] == ["tests/wip/test_widget.py"]
    assert "NO TEST FILE WAS WRITTEN" not in text
    assert "tests/wip/test_widget.py" in text
    assert "Open the named file(s) before you judge." in text


def test_branch_one_still_says_no_test_was_written_when_none_was(
    tmp_path: Path,
) -> None:
    """The control. A genuinely test-free turn must still be named as one.

    Without this, the fix above could be "never say it" — which would lose
    the finding the instrument exists to make.
    """
    worktree = _worktree(tmp_path)
    (worktree / "docs").mkdir(parents=True, exist_ok=True)
    (worktree / "docs" / "guide.md").write_text("# guide\n")
    results = _results(files_created=["docs/guide.md"])

    evidence = _real_branch_one_evidence(worktree, results)
    text = gate.coach_advisory_text(evidence)

    assert evidence["claimed_test_files"] == []
    assert "NO TEST FILE WAS WRITTEN" in text
    assert "is a file the Coach recognises as a test" in text
    assert "NO TEST RAN, AND NONE WAS LISTED AS WRITTEN" not in text


def test_the_branch_meaning_stamped_on_every_row_is_true_of_the_branch() -> None:
    """The receipt carries this sentence; a report months later reads it.

    It must not assert the thing the rule never checked.
    """
    meaning = gate.BRANCH_MEANINGS[gate.BRANCH_NO_TEST_FILE]

    assert "tests-written list is empty" in meaning
    assert "named no test file" not in meaning
    assert "created/modified lists" in meaning


def test_the_coachs_instructions_do_not_claim_the_turn_produced_no_test() -> None:
    """The Coach's standing instructions said it too, in its own words.

    The advisory line and the instructions are read together, so fixing one
    and leaving the other still leaves a false statement in front of the
    model.
    """
    text = _coach_instructions()

    assert "So this turn produced no test." not in text
    assert "the Player's own report names no test file" not in text
    assert "NO TEST RAN, AND NONE WAS LISTED AS WRITTEN" in text
    assert "reads `tests_written` and nothing else" in text
    assert "only collects Python tests" in text


def test_the_report_flags_a_row_that_names_a_test_the_rule_never_read(
    tmp_path: Path,
) -> None:
    """A person ruling on rows must not rule this one test-free by mistake.

    The card looks identical to a turn that wrote nothing — same branch, same
    empty ``tests_written``. The only thing separating them is a file list the
    rule does not consult, so the report has to put it on the card.
    """
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    ledger = gate.ledger_path_for(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(
            {
                "repo": "repo",
                "task_id": "TASK-TS",
                "turn": 1,
                "branch": gate.BRANCH_NO_TEST_FILE,
                "coach_decision": "approve",
                "files_created": ["src/widget.ts", "src/widget.test.ts"],
                "files_modified": [],
                "tests_written": [],
                "claimed_test_files": ["src/widget.test.ts"],
                "test_files_on_disk": ["src/widget.test.ts"],
                "legitimately_test_free": None,
            }
        )
        + "\n"
    )

    result = CliRunner().invoke(
        zero_test_report, ["--repo-root", str(tmp_path)]
    )
    output = _flat(result.output)

    assert result.exit_code == 0
    assert "CHECK BEFORE RULING" in output
    assert "names 1 test file(s) outside tests_written" in output
    assert "src/widget.test.ts" in output
    assert "on disk" in output


# ===========================================================================
# 13. THE READING COMMAND MUST NOT ANSWER A NARROWER QUESTION THAN IT READS
#
# A build keys its rows by the repository it is building. The report used to
# key its lookup by whatever directory the person happened to be standing in,
# so running it one level down found nothing — and said so in green. That is
# the instrument's own disease sitting inside the instrument.
#
# Both sides now go through one function, ``resolve_repo_root``, so they
# cannot drift apart again.
# ===========================================================================


def _a_real_repository(tmp_path: Path) -> Path:
    """An actual git repository, because the resolver looks for a real one."""
    repo = tmp_path / "myrepo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True
    )
    return repo


def _one_recorded_row(repo: Path, task_id: str = "TASK-A") -> None:
    """Write one row the way a real build writes it: keyed by the repository."""
    build_worktree = repo / ".guardkit" / "worktrees" / "FEAT-X"
    build_worktree.mkdir(parents=True, exist_ok=True)
    record = gate.build_receipt(
        evidence=_fired_evidence(),
        task_id=task_id,
        turn=1,
        feature_id="FEAT-X",
        repo=repo.name,
        repo_path=str(repo),
        coach_decision="approve",
        blocking=False,
        overridden=False,
    )
    gate.write_receipt(
        record,
        worktree_path=build_worktree,
        repo_root=repo,
        task_id=task_id,
        turn=1,
    )


def test_the_report_finds_the_rows_from_anywhere_inside_the_repository(
    tmp_path: Path,
) -> None:
    """Root, subdirectory, build worktree, linked worktree — one answer.

    Run from a subdirectory, the old command looked in a directory named
    after that subdirectory, found nothing, and printed a clean result.
    Someone would have concluded no build had skipped its tests.
    """
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    repo = _a_real_repository(tmp_path)
    _one_recorded_row(repo)

    deep = repo / "guardkit" / "cli"
    deep.mkdir(parents=True)
    build_worktree = repo / ".guardkit" / "worktrees" / "FEAT-X"

    for where in (repo, deep, build_worktree):
        result = CliRunner().invoke(
            zero_test_report, ["--repo-root", str(where)]
        )
        output = _flat(result.output)
        assert result.exit_code == 0
        assert "1 recorded turn(s)" in output, (
            f"the report found nothing when run from {where} — the row is in "
            f"{gate.ledger_path_for(repo)}"
        )
        assert "TASK-A" in output
        assert "NO LEDGER FILE EXISTS" not in output


def test_read_and_write_resolve_the_same_key_by_construction(
    tmp_path: Path,
) -> None:
    """Not "both remember to resolve" — the same function, one call each.

    If the two sides ever compute the key separately again, this goes red for
    every path that is not already a repository root.
    """
    repo = _a_real_repository(tmp_path)
    deep = repo / "a" / "b" / "c"
    deep.mkdir(parents=True)
    build_worktree = repo / ".guardkit" / "worktrees" / "FEAT-X"
    build_worktree.mkdir(parents=True)

    written_key = gate.ledger_path_for(repo)
    for reader_stood_in in (repo, deep, build_worktree):
        assert gate.ledger_path_for(reader_stood_in) == written_key
        assert gate.resolve_repo_root(reader_stood_in) == repo.resolve()


def test_a_linked_git_worktree_reports_its_repositorys_rows(
    tmp_path: Path,
) -> None:
    """A lane worktree made by ``git worktree add`` is not its own repository.

    Its ``.git`` is a file pointing back into the main checkout. Keyed on its
    own directory name it would report an empty ledger — in a directory
    named after the lane, which no build has ever written to.
    """
    repo = _a_real_repository(tmp_path)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit",
         "-q", "--allow-empty", "-m", "first"],
        cwd=str(repo), check=True, capture_output=True,
    )
    lane = tmp_path / "lane-worktree"
    subprocess.run(
        ["git", "worktree", "add", "-q", "--detach", str(lane)],
        cwd=str(repo), check=True, capture_output=True,
    )
    _one_recorded_row(repo)

    assert gate.resolve_repo_root(lane) == repo.resolve()
    assert len(gate.read_receipts(lane)) == 1


def test_read_ledger_says_whether_it_found_a_ledger_at_all(
    tmp_path: Path,
) -> None:
    """Zero rows has two causes and the caller is told which.

    This is what stops a report printing a clean bill when it simply did not
    look in the right place.
    """
    absent = gate.read_ledger(tmp_path)
    assert absent.rows == []
    assert absent.any_ledger_file is False
    assert absent.paths_read == []

    ledger = gate.ledger_path_for(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("")

    empty = gate.read_ledger(tmp_path)
    assert empty.rows == []
    assert empty.any_ledger_file is True
    assert empty.paths_read == [ledger]


# ===========================================================================
# 14. ADJUDICATION GOES IN ITS OWN FILE
#
# The ledger's lock serialises BUILDS against builds. Nothing serialises a
# build's append against a person with the file open in an editor, and
# whoever saves last silently destroys the other's work.
# ===========================================================================


def test_a_ruling_never_touches_the_file_builds_append_to(
    tmp_path: Path,
) -> None:
    repo = _a_real_repository(tmp_path)
    _one_recorded_row(repo)
    ledger = gate.ledger_path_for(repo)
    before = ledger.read_bytes()

    gate.record_ruling(
        repo_root=repo,
        task_id="TASK-A",
        turn=1,
        legitimately_test_free=True,
        note="documentation only",
    )

    assert ledger.read_bytes() == before, (
        "recording a ruling rewrote the ledger — a concurrent build's append "
        "can be lost that way"
    )
    assert gate.rulings_path_for(repo).is_file()
    assert gate.rulings_path_for(repo) != ledger


def test_the_report_joins_rulings_onto_the_rows_they_rule_on(
    tmp_path: Path,
) -> None:
    repo = _a_real_repository(tmp_path)
    _one_recorded_row(repo)

    assert gate.read_receipts(repo)[0]["legitimately_test_free"] is None

    gate.record_ruling(
        repo_root=repo, task_id="TASK-A", turn=1, legitimately_test_free=True
    )
    ruled = gate.read_receipts(repo)[0]
    assert ruled["legitimately_test_free"] is True
    assert ruled["ruled_at"]


def test_changing_your_mind_is_a_second_ruling_not_an_edit(
    tmp_path: Path,
) -> None:
    repo = _a_real_repository(tmp_path)
    _one_recorded_row(repo)

    gate.record_ruling(
        repo_root=repo, task_id="TASK-A", turn=1, legitimately_test_free=True
    )
    gate.record_ruling(
        repo_root=repo,
        task_id="TASK-A",
        turn=1,
        legitimately_test_free=False,
        note="on reflection this was a behaviour change",
    )

    ruled = gate.read_receipts(repo)[0]
    assert ruled["legitimately_test_free"] is False
    assert ruled["ruling_note"] == "on reflection this was a behaviour change"


def test_a_ruling_and_a_concurrent_build_both_survive(tmp_path: Path) -> None:
    """The failure the separate file exists to prevent, run for real.

    A person rules on a row while a build finishes a turn. Under the old
    shape both wrote the same file and one of the two was lost. Here neither
    can be: they are different files.
    """
    repo = _a_real_repository(tmp_path)
    _one_recorded_row(repo, task_id="TASK-A")

    ruling_done = threading.Event()

    def rule() -> None:
        gate.record_ruling(
            repo_root=repo,
            task_id="TASK-A",
            turn=1,
            legitimately_test_free=True,
        )
        ruling_done.set()

    person = threading.Thread(target=rule)
    person.start()
    _one_recorded_row(repo, task_id="TASK-B")  # a build, at the same moment
    person.join()

    assert ruling_done.is_set()
    rows = {row["task_id"]: row for row in gate.read_receipts(repo)}
    assert set(rows) == {"TASK-A", "TASK-B"}, (
        "a build's row and a person's ruling collided and one was lost"
    )
    assert rows["TASK-A"]["legitimately_test_free"] is True
    assert rows["TASK-B"]["legitimately_test_free"] is None


def test_a_hand_written_ruling_already_in_the_ledger_is_still_honoured(
    tmp_path: Path,
) -> None:
    """Nobody's earlier work is discarded by moving rulings to their own file."""
    ledger = gate.ledger_path_for(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(
            {
                "repo": "repo",
                "task_id": "TASK-OLD",
                "turn": 1,
                "branch": gate.BRANCH_NO_TEST_FILE,
                "legitimately_test_free": True,
            }
        )
        + "\n"
    )

    assert gate.read_receipts(tmp_path)[0]["legitimately_test_free"] is True


def test_the_ruling_command_works_from_a_subdirectory(tmp_path: Path) -> None:
    """The write side of adjudication resolves the repository the same way."""
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_rule

    repo = _a_real_repository(tmp_path)
    _one_recorded_row(repo)
    deep = repo / "guardkit" / "cli"
    deep.mkdir(parents=True)

    result = CliRunner().invoke(
        zero_test_rule,
        ["--task", "TASK-A", "--turn", "1", "--test-free",
         "--repo-root", str(deep)],
    )

    assert result.exit_code == 0, result.output
    assert gate.read_receipts(repo)[0]["legitimately_test_free"] is True


# ===========================================================================
# 15. THE TWO SMALL ONES
# ===========================================================================


@pytest.mark.parametrize(
    "count, expected",
    [(1, "1 was recorded"), (2, "2 were recorded")],
)
def test_the_report_counts_to_one_correctly(
    tmp_path: Path, count: int, expected: str
) -> None:
    """A human-facing surface that cannot count to one is not trusted.

    The neighbouring sentence in the same panel already agrees with its verb.
    """
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    ledger = gate.ledger_path_for(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        "".join(
            json.dumps({"repo": "repo", "task_id": f"TASK-{n}", "turn": 1})
            + "\n"
            for n in range(count)
        )
    )

    result = CliRunner().invoke(
        zero_test_report, ["--repo-root", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert expected in _flat(result.output)


def test_the_report_asks_the_promotion_rule_rather_than_repeating_it(
    tmp_path: Path,
) -> None:
    """One rule, one implementation, one caller.

    ``counts_toward_promotion`` decides what the measurement counts. The
    report used to re-implement the same filter inline, so a change to one
    copy would silently disagree with the other. Narrow the exported rule and
    the report must narrow with it; that is what this asserts.
    """
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    ledger = gate.ledger_path_for(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(
            {
                "repo": "repo",
                "task_id": "TASK-A",
                "turn": 1,
                "branch": gate.BRANCH_NO_TEST_FILE,
                "coach_decision": "approve",
            }
        )
        + "\n"
    )

    # Narrow the ONE exported rule. A report that consults it narrows with
    # it; a report carrying its own copy of the filter does not notice.
    with patch.object(
        gate, "counts_toward_promotion", return_value=False
    ) as shared_rule:
        result = CliRunner().invoke(
            zero_test_report, ["--repo-root", str(tmp_path)]
        )

    assert result.exit_code == 0
    assert shared_rule.called, (
        "the report did not consult zero_test_gate.counts_toward_promotion — "
        "it is deciding what the measurement counts on its own"
    )
    assert "0 had no test found" in _flat(result.output), (
        "the report still counted the row after the shared promotion rule "
        "rejected it — there is a second copy of the rule inline"
    )


def test_the_ruling_command_refuses_a_verdict_it_was_not_given(
    tmp_path: Path,
) -> None:
    """A forgotten flag must not file the opposite ruling.

    ``--test-free/--not-test-free`` is a boolean pair, and click does not
    enforce ``required`` on those: omit both and it hands the body ``False``,
    which reads as "this change should have had a test". That verdict would
    go into the promotion measurement having never been made by anyone.
    """
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_rule

    repo = _a_real_repository(tmp_path)
    _one_recorded_row(repo)

    result = CliRunner().invoke(
        zero_test_rule, ["--task", "TASK-A", "--turn", "1",
                         "--repo-root", str(repo)]
    )

    assert result.exit_code == 1
    assert "--test-free or --not-test-free" in _flat(result.output)
    assert not gate.rulings_path_for(repo).exists()
    assert gate.read_receipts(repo)[0]["legitimately_test_free"] is None


def test_a_ruling_against_a_row_that_is_not_there_is_refused(
    tmp_path: Path,
) -> None:
    """A mistyped identifier must not become a ruling that joins to nothing.

    Left unchecked it is invisible twice over: the row it was meant for still
    reads as needing a ruling, and the ruling itself is never shown.
    """
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_rule

    repo = _a_real_repository(tmp_path)
    _one_recorded_row(repo, task_id="TASK-A")

    result = CliRunner().invoke(
        zero_test_rule, ["--task", "TASK-TYPO", "--turn", "1", "--test-free",
                         "--repo-root", str(repo)]
    )

    assert result.exit_code == 1
    assert "No recorded turn matches TASK-TYPO turn 1" in _flat(result.output)
    assert not gate.rulings_path_for(repo).exists()


def test_a_ruling_joins_a_row_recorded_before_the_repo_field_existed(
    tmp_path: Path,
) -> None:
    """The join key is (task, turn) — the repository is already the directory.

    An older row carries no ``repo``. Keying the join on one would leave that
    row unruleable: the ruling would be written and never shown, and the row
    would go on asking for a decision that had already been made.
    """
    ledger = gate.ledger_path_for(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(
            {
                "task_id": "TASK-OLD",
                "turn": 1,
                "branch": gate.BRANCH_NO_TEST_FILE,
                "legitimately_test_free": None,
            }
        )
        + "\n"
    )

    gate.record_ruling(
        repo_root=tmp_path,
        task_id="TASK-OLD",
        turn=1,
        legitimately_test_free=True,
    )

    assert gate.read_receipts(tmp_path)[0]["legitimately_test_free"] is True
