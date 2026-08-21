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
    instructions = (
        Path(__file__).resolve().parents[2]
        / "installer"
        / "core"
        / "agents"
        / "autobuild-coach.md"
    ).read_text(encoding="utf-8")
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
    assert "2 wrote no test file" in output
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


def test_the_report_says_so_plainly_when_nothing_has_been_recorded(
    tmp_path: Path,
) -> None:
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    result = CliRunner().invoke(
        zero_test_report, ["--repo-root", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert (
        "No build has been recorded with missing or unrun tests."
        in result.output.replace("\n", " ")
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
    text = gate.coach_advisory_text(_fired_evidence())

    assert "NO TEST FILE WAS WRITTEN" in text
    assert "names no test file" in text
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
    assert "no test exists" in rows["TASK-ONE"]["branch_meaning"].lower()
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
    assert "1 wrote no test file" in output
    assert "1 claimed a passing quality gate while reporting that 0 tests ran" in output
    # ...listed separately...
    assert "NO TEST FILE — needs your ruling" in output
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

    assert "1 were recorded before the two situations were told apart" in output
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
