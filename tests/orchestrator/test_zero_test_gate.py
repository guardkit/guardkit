"""Tests for the zero-test observation recorder on the language-model Coach path.

WHAT IS BEING TESTED, for a reader who does not know this codebase
------------------------------------------------------------------
GuardKit builds software in a loop. A **Player** writes code; a **Coach** then
reviews the turn and decides approve / feedback / reject.

The rule-based (legacy) Coach has always run a rule,
``CoachValidator._check_zero_test_anomaly``, and refused to approve turns it
fires on. Since 2026-05-21 the default Coach is a language model, and on that
path the rule was never run at all. The change under test runs the same rule
there and **writes down what it observed**.

It states no conclusion, and neither do these tests. Four earlier rounds tried
to word a sentence saying what a build had or had not done; a reviewer refuted
each one. The sentences are gone. What is left, and what is tested here, is:

1. the same rule is used — not a second copy of it;
2. the observations recorded are the ones the code can actually establish, and
   "looked at and not accepted" is kept apart from "never looked at";
3. it records and changes nothing, unless ``GUARDKIT_ZERO_TEST_BLOCKING`` is
   set;
4. the durable ledger survives ordinary housekeeping and concurrent builds;
5. the reading and writing sides resolve the same repository;
6. the report prints values, states how each was established, and counts rows;
7. **the production wiring** — the one call site, pinned by name, because a
   recorder that is disconnected has no other symptom.
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
    test suite that wrote there would pollute a real record, so every test in
    this file redirects it.
    """
    monkeypatch.setenv(gate.ZERO_TEST_ROOT_ENV_VAR, str(tmp_path / "durable"))


def _flat(output: str) -> str:
    """Report text as one line, free of the console's box drawing.

    The summary panel wraps to the terminal width and puts a border character
    at each end of every line, so a sentence in it is never contiguous in the
    raw output. Assertions read this instead.
    """
    for border in "│╭╮╰╯─┏┓┗┛━┃":
        output = output.replace(border, " ")
    return " ".join(output.split())


def _report(*args: str) -> str:
    """Run ``guardkit autobuild zero-test-report`` and return its flat output."""
    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    return _flat(CliRunner().invoke(zero_test_report, list(args)).output)


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


def _fired_observation(**overrides) -> dict:
    """An observation dict shaped exactly like ``evaluate_zero_test`` returns."""
    observation = {
        "rule": "CoachValidator._check_zero_test_anomaly",
        "rule_fired": True,
        "rule_severity": "error",
        "rule_error": None,
        "category": gate.ANOMALY_CATEGORY,
        "report_tests_written": [],
        "report_files_created": ["docs/guide.md"],
        "report_files_modified": ["README.md"],
        "recogniser": gate.RECOGNISER,
        "recogniser_available": True,
        "recogniser_conventions": list(gate.CONVENTION_LABELS),
        "names_matching_a_convention": [],
        "names_examined_by_recogniser": ["docs/guide.md", "README.md"],
        "names_not_examined_by_recogniser": [],
        "disk_lookup_performed": True,
        "matching_names_found_on_disk": [],
        "independent_test_run_command": "skipped",
        "report_quality_gates_all_passed": True,
        "report_quality_gates_tests_passed": 0,
        "report_quality_gates_coverage": None,
        "report_requirements_all_criteria_met": True,
    }
    observation.update(overrides)
    return observation


def _real_observation(worktree: Path, results: dict) -> dict:
    """Run the REAL rule and the REAL independent test run over one turn.

    Nothing here is stubbed. ``run_independent_tests`` walks its whole
    detection ladder against the files actually on disk, and
    ``evaluate_zero_test`` calls ``CoachValidator._check_zero_test_anomaly``
    itself. What comes back is what a live build would have produced.
    """
    validator = _validator(worktree)
    independent = validator.run_independent_tests(
        task_work_results=results, task=None, turn=1
    )
    observation = gate.evaluate_zero_test(
        validator,
        task_work_results=results,
        profile=_feature_profile(),
        independent_tests=independent,
        task_id="TASK-ZT-001",
        requirements=None,
    )
    assert observation["rule_fired"] is True
    return observation


def _run_recorder(
    tmp_path: Path,
    *,
    decision: dict,
    observation,
    env: dict,
    task_id: str = "TASK-ZT-001",
    turn: int = 1,
) -> tuple[dict, Path]:
    """Run the recorder against an un-``__init__``'d AgentInvoker.

    Returns the (possibly mutated) decision and the repository root, so a
    caller can look for the ledger.
    """
    worktree = _worktree(tmp_path, task_id)
    repo_root = tmp_path / "repo"
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    # The same mapping carries the blocking flag AND the ledger location, so
    # no test can write into the real one under the user's home directory.
    env = {gate.ZERO_TEST_ROOT_ENV_VAR: str(tmp_path / "durable"), **env}

    bundle = CoachEvidenceBundle(honesty=None, zero_test=observation)
    coach_output_path = worktree / ".guardkit" / "autobuild" / task_id / (
        f"coach_turn_{turn}.json"
    )
    coach_output_path.write_text(json.dumps(decision))

    invoker._record_zero_test_observation(
        decision=decision,
        evidence_bundle=bundle,
        task_id=task_id,
        turn=turn,
        coach_output_path=coach_output_path,
        env=env,
    )
    return decision, repo_root


# ===========================================================================
# 1. Detection — the same rule, not a second copy of it
# ===========================================================================


def test_the_same_rule_is_used_not_a_second_copy(tmp_path: Path) -> None:
    """Delegation, proven by interception.

    If this module ever grows its own detection, the two Coach paths can
    disagree about the same turn. Patching the legacy method must therefore
    change what this module reports.
    """
    validator = _validator(_worktree(tmp_path))

    with patch.object(
        validator, "_check_zero_test_anomaly", return_value=[]
    ) as rule:
        observation = gate.evaluate_zero_test(
            validator,
            task_work_results=_results(),
            profile=_feature_profile(),
            independent_tests=_skipped_independent_run(),
            task_id="TASK-ZT-001",
        )

    assert rule.call_count == 1
    assert observation["rule_fired"] is False
    assert observation["rule"] == "CoachValidator._check_zero_test_anomaly"


def test_it_fires_when_the_legacy_rule_fires(tmp_path: Path) -> None:
    worktree = _worktree(tmp_path)
    (worktree / "docs").mkdir(parents=True, exist_ok=True)
    (worktree / "docs" / "guide.md").write_text("# guide\n")

    observation = _real_observation(worktree, _results(files_created=["docs/guide.md"]))

    assert observation["rule_fired"] is True
    assert observation["rule_severity"] in {"error", "warning"}


def test_it_is_silent_when_a_test_was_written_and_ran(tmp_path: Path) -> None:
    """The control: a turn the rule does not fire on records nothing."""
    worktree = _worktree(tmp_path)
    (worktree / "tests" / "test_zt_001_widget.py").write_text(
        "def test_widget():\n    assert True\n"
    )
    results = _results(
        tests_written=["tests/test_zt_001_widget.py"], tests_passed_count=1
    )
    validator = _validator(worktree)

    observation = gate.evaluate_zero_test(
        validator,
        task_work_results=results,
        profile=_feature_profile(),
        independent_tests=validator.run_independent_tests(
            task_work_results=results, task=None, turn=1
        ),
        task_id="TASK-ZT-001",
    )

    assert observation["rule_fired"] is False


def test_it_is_silent_for_a_task_type_that_does_not_require_tests(
    tmp_path: Path,
) -> None:
    """Scaffolding tasks are not expected to carry tests; nothing fires."""
    observation = gate.evaluate_zero_test(
        _validator(_worktree(tmp_path)),
        task_work_results=_results(files_created=["src/scaffold.py"]),
        profile=get_profile(TaskType.SCAFFOLDING),
        independent_tests=_skipped_independent_run(),
        task_id="TASK-ZT-001",
    )

    assert observation["rule_fired"] is False


def test_a_broken_rule_records_the_breakage_rather_than_a_verdict(
    tmp_path: Path,
) -> None:
    """An instrument that cannot report must not manufacture a report."""
    validator = _validator(_worktree(tmp_path))

    with patch.object(
        validator, "_check_zero_test_anomaly", side_effect=RuntimeError("boom")
    ):
        observation = gate.evaluate_zero_test(
            validator,
            task_work_results=_results(),
            profile=_feature_profile(),
            independent_tests=_skipped_independent_run(),
            task_id="TASK-ZT-001",
        )

    assert observation["rule_fired"] is False
    assert observation["rule_error"] == "RuntimeError: boom"


# ===========================================================================
# 2. The observation reaches the language-model Coach's evidence bundle
# ===========================================================================


def test_the_live_coach_path_puts_the_observation_on_the_bundle(
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
    assert bundle.zero_test["rule_fired"] is True
    assert bundle.zero_test["report_files_created"] == ["src/auth.py"]
    # And it survives serialisation into the Coach's prompt / turn record.
    assert bundle.to_dict()["zero_test"]["rule_fired"] is True


def test_the_field_is_absent_when_gathering_stopped_early() -> None:
    """Partial returns carry no observation, exactly as the legacy path does."""
    assert CoachEvidenceBundle(honesty=None).zero_test is None


# ===========================================================================
# 3. It records and changes nothing — unless asked
# ===========================================================================


def test_blocking_is_off_unless_asked_for() -> None:
    assert gate.blocking_requested({}) is False
    assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: ""}) is False
    assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: "no"}) is False


def test_blocking_accepts_the_documented_values() -> None:
    for value in ("1", "true", "TRUE", "yes", "on"):
        assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: value}) is True


def test_an_approval_stands_by_default(tmp_path: Path) -> None:
    decision, _ = _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={},
    )

    assert decision["decision"] == "approve"
    assert decision["rationale"] == "fine"


def test_it_changes_the_verdict_when_the_flag_is_set(tmp_path: Path) -> None:
    decision, _ = _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={gate.BLOCKING_ENV_VAR: "1"},
    )

    assert decision["decision"] == "feedback"
    assert decision["issues"][0]["category"] == gate.ANOMALY_CATEGORY


def test_a_feedback_verdict_is_never_touched(tmp_path: Path) -> None:
    decision, _ = _run_recorder(
        tmp_path,
        decision={"decision": "feedback", "rationale": "already", "issues": []},
        observation=_fired_observation(),
        env={gate.BLOCKING_ENV_VAR: "1"},
    )

    assert decision["decision"] == "feedback"
    assert decision["rationale"] == "already"


def test_nothing_is_recorded_when_the_rule_did_not_fire(tmp_path: Path) -> None:
    decision, repo_root = _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(rule_fired=False),
        env={},
    )

    assert decision["decision"] == "approve"
    assert gate.read_rows(repo_root) == []


def test_nothing_is_recorded_when_gathering_stopped_before_the_rule(
    tmp_path: Path,
) -> None:
    decision, repo_root = _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=None,
        env={},
    )

    assert decision["decision"] == "approve"
    assert gate.read_rows(repo_root) == []


def test_the_verdict_change_is_wired_to_the_flag_and_to_nothing_else(
    tmp_path: Path,
) -> None:
    """Nobody can promote this to a blocker by accident.

    The rule fires on every one of these turns. Only the flag may decide
    whether the verdict changes — not the severity, not the task profile.
    """
    for severity in ("error", "warning"):
        decision, _ = _run_recorder(
            tmp_path,
            decision={"decision": "approve", "rationale": "fine", "issues": []},
            observation=_fired_observation(rule_severity=severity),
            env={},
            task_id=f"TASK-FLAG-{severity}",
        )
        assert decision["decision"] == "approve", (
            f"a {severity} observation changed the verdict with "
            f"{gate.BLOCKING_ENV_VAR} unset"
        )


def test_the_real_process_environment_does_not_block_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With ``env=None`` the real environment is read — and it must be off."""
    monkeypatch.delenv(gate.BLOCKING_ENV_VAR, raising=False)
    worktree = _worktree(tmp_path)
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    decision = {"decision": "approve", "rationale": "fine", "issues": []}
    coach_output_path = (
        worktree / ".guardkit" / "autobuild" / "TASK-ZT-001" / "coach_turn_1.json"
    )
    coach_output_path.write_text(json.dumps(decision))

    invoker._record_zero_test_observation(
        decision=decision,
        evidence_bundle=CoachEvidenceBundle(
            honesty=None, zero_test=_fired_observation()
        ),
        task_id="TASK-ZT-001",
        turn=1,
        coach_output_path=coach_output_path,
    )

    assert decision["decision"] == "approve"


# ===========================================================================
# 4. The recorded row — the observations, and nothing else
# ===========================================================================


def test_the_row_carries_the_observations_and_where_they_came_from(
    tmp_path: Path,
) -> None:
    """Every field a person reads, present and named for what it is."""
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(
            report_tests_written=["tests/test_widget.py"],
            names_matching_a_convention=[
                {"name": "tests/test_widget.py", "conventions": ["test_*.py"]}
            ],
        ),
        env={},
    )

    row = json.loads(_durable_ledger(tmp_path).read_text().splitlines()[0])

    assert row["schema"] == "zero_test_observation/1"
    assert row["task_id"] == "TASK-ZT-001"
    assert row["turn"] == 1
    assert row["worktree_dir"] == "FEAT-ZT99"
    assert row["repo"] == "repo"
    assert row["coach_decision"] == "approve"
    assert row["blocking_env_var"] == gate.BLOCKING_ENV_VAR
    assert row["blocking_env_var_set"] is False
    assert row["decision_changed_by_this_instrument"] is False
    assert row["report_tests_written"] == ["tests/test_widget.py"]
    assert row["names_matching_a_convention"] == [
        {"name": "tests/test_widget.py", "conventions": ["test_*.py"]}
    ]
    assert row["recogniser"] == gate.RECOGNISER
    assert row["recorded_at"]


def test_no_field_on_a_row_states_a_conclusion(tmp_path: Path) -> None:
    """The structural bar, checked against the code rather than a wordlist.

    Four rounds died wording a conclusion. There is now nowhere to put one:
    every key on a row either names its source (``report:``, ``recogniser``,
    ``rule``), identifies the build, or is one of the observations
    :func:`gate.observation_lines` renders. A key outside that set is a new
    surface, and a new surface is where the next false sentence goes.
    """
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={},
    )
    row = json.loads(_durable_ledger(tmp_path).read_text().splitlines()[0])

    permitted = {
        # identity of the build the row came from
        "schema", "recorded_at", "repo", "repo_path", "worktree_dir",
        "task_id", "turn",
        # what the rule is, and what it returned
        "rule", "rule_fired", "rule_severity", "rule_error", "category",
        # what the Player's report said
        "report_tests_written", "report_files_created", "report_files_modified",
        "report_quality_gates_all_passed", "report_quality_gates_tests_passed",
        "report_quality_gates_coverage", "report_requirements_all_criteria_met",
        # what the recogniser did
        "recogniser", "recogniser_available", "recogniser_conventions",
        "names_matching_a_convention", "names_examined_by_recogniser",
        "names_not_examined_by_recogniser",
        # what the disk lookup and the independent run did
        "disk_lookup_performed", "matching_names_found_on_disk",
        "independent_test_run_command",
        # what happened to the verdict
        "coach_decision", "blocking_env_var", "blocking_env_var_set",
        "decision_changed_by_this_instrument",
    }
    assert set(row) - permitted == set(), (
        "a row grew a field that is not an observation, an identity or a "
        "record of what the rule returned"
    )


def test_the_row_is_also_written_beside_the_coachs_own_verdict(
    tmp_path: Path,
) -> None:
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={},
    )

    receipt = _worktree(tmp_path) / gate.ZERO_TEST_RECEIPT.format(
        task_id="TASK-ZT-001", turn=1
    )
    assert receipt.is_file()
    assert json.loads(receipt.read_text())["task_id"] == "TASK-ZT-001"


def test_the_ledger_accumulates_across_turns(tmp_path: Path) -> None:
    for turn in (1, 2, 3):
        _run_recorder(
            tmp_path,
            decision={"decision": "approve", "rationale": "fine", "issues": []},
            observation=_fired_observation(),
            env={},
            turn=turn,
        )

    assert [row["turn"] for row in gate.read_rows(tmp_path / "repo")] == [1, 2, 3]


def test_a_changed_verdict_is_recorded_as_changed(tmp_path: Path) -> None:
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={gate.BLOCKING_ENV_VAR: "1"},
    )

    row = gate.read_rows(tmp_path / "repo")[0]
    assert row["coach_decision"] == "approve"
    assert row["blocking_env_var_set"] is True
    assert row["decision_changed_by_this_instrument"] is True


def test_the_message_sent_to_the_player_is_the_observations(
    tmp_path: Path,
) -> None:
    """The one surface a model reads. It hands over values, not a conclusion.

    Every line after the opening sentence is a ``label: value`` pair from
    :func:`gate.observation_lines`, so there is no prose here to go stale or
    to overstate what was seen.
    """
    decision, _ = _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={gate.BLOCKING_ENV_VAR: "1"},
    )

    rationale = decision["rationale"]
    assert gate.BLOCKING_ENV_VAR in rationale
    for label, _value in gate.observation_lines(_fired_observation()):
        assert f"{label}:" in rationale, f"the Player is not shown {label!r}"


def test_an_unwritable_ledger_never_breaks_the_build(tmp_path: Path) -> None:
    with patch.object(
        gate, "_append_line_atomically", side_effect=OSError("read-only")
    ):
        decision, _ = _run_recorder(
            tmp_path,
            decision={"decision": "approve", "rationale": "fine", "issues": []},
            observation=_fired_observation(),
            env={},
        )

    assert decision["decision"] == "approve"


def test_a_corrupt_ledger_line_is_skipped_not_fatal(tmp_path: Path) -> None:
    ledger = gate.ledger_path_for(tmp_path / "repo")
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text('{"task_id": "TASK-A"}\nnot json at all\n{"task_id": "TASK-B"}\n')

    assert [row["task_id"] for row in gate.read_rows(tmp_path / "repo")] == [
        "TASK-A",
        "TASK-B",
    ]


def test_no_ledger_means_no_rows(tmp_path: Path) -> None:
    assert gate.read_rows(tmp_path / "never-written") == []


# ===========================================================================
# 5. THE RECOGNITION FACTS, AT THE EDGES, AGAINST REAL FILES
#
# This is where four rounds of false sentences came from. The recogniser
# ``CoachValidator._is_test_file_path`` knows six naming conventions across
# five languages, and the Coach's own test run is pytest. A test in any other
# form is invisible to both. Nothing is stubbed below: real files, the real
# rule, the real detection ladder — and what is asserted is that the recorded
# observations describe the LOOKING, never the world.
# ===========================================================================


def test_the_conventions_recorded_are_the_ones_the_recogniser_accepts(
    tmp_path: Path,
) -> None:
    """The attribution table cannot claim more than the recogniser does.

    ``KNOWN_TEST_CONVENTIONS`` says which convention an accepted name fits.
    The decision itself is always the recogniser's, so the table must agree
    with it on every example it names — otherwise a row would carry a
    convention label the recogniser never honours.
    """
    for label, example, _predicate in gate.KNOWN_TEST_CONVENTIONS:
        assert CoachValidator._is_test_file_path(example), (
            f"the table records the convention {label!r}, but the real "
            f"recogniser rejects its example {example!r}"
        )
        assert label in gate.conventions_matching(example)
    assert gate.CONVENTION_LABELS == tuple(
        label for label, _example, _predicate in gate.KNOWN_TEST_CONVENTIONS
    )


def test_a_name_the_recogniser_rejects_is_attributed_no_convention() -> None:
    assert CoachValidator._is_test_file_path("src/widget.py") is False
    assert gate.conventions_matching("src/widget.py") == []


@pytest.mark.parametrize(
    "test_file, convention",
    [
        ("src/widget.test.ts", "*.test.ts / *.test.js"),
        ("src/widget_test.go", "*_test.go"),
        ("tests/Widget/Tests/WidgetTests.cs", "*.cs under a Tests/ directory"),
    ],
)
def test_a_named_test_the_pytest_run_cannot_execute_is_recorded_as_named(
    tmp_path: Path, test_file: str, convention: str
) -> None:
    """A real turn: the Player wrote a test the Coach's run cannot execute.

    It listed the file under ``files_created`` and left ``tests_written``
    empty, so the rule fires. The recogniser DOES accept the name, so the row
    records the name and the convention it fits — the reader can see for
    themselves that a test is named here.
    """
    worktree = _worktree(tmp_path)
    written = worktree / test_file
    written.parent.mkdir(parents=True, exist_ok=True)
    written.write_text("// a test\n")

    observation = _real_observation(
        worktree, _results(files_created=["src/widget.src", test_file])
    )

    assert observation["report_tests_written"] == []
    assert observation["names_matching_a_convention"] == [
        {"name": test_file, "conventions": [convention]}
    ]
    assert observation["matching_names_found_on_disk"] == [test_file]
    assert observation["independent_test_run_command"] == "skipped"


@pytest.mark.parametrize(
    "test_file, content, description",
    [
        (
            "spec/widget_spec.rb",
            "describe 'widget' do\n  it 'works' do\n  end\nend\n",
            "Ruby RSpec — no convention here matches *_spec.rb",
        ),
        (
            "src/test/java/WidgetTest.java",
            "class WidgetTest { @Test void works() {} }\n",
            "a JUnit test — Java is not in the recogniser at all",
        ),
        (
            "tests/widget.sh",
            "#!/bin/sh\nexit 0\n",
            "a shell test script — nothing recognises it",
        ),
        (
            "features/widget.feature",
            "Feature: widget\n  Scenario: works\n",
            "a Gherkin feature file — nothing recognises it",
        ),
        (
            "src/widget_tests.rs",
            "#[cfg(test)]\nmod tests { #[test] fn works() {} }\n",
            "a Rust test module — nothing recognises it",
        ),
    ],
)
def test_a_test_in_a_form_nothing_recognises_is_recorded_as_examined_not_rejected(
    tmp_path: Path, test_file: str, content: str, description: str
) -> None:
    """THE CASE THAT SANK EVERY EARLIER ROUND, built for real and read.

    Each of these is a genuine test file, written this turn, present on disk,
    and invisible to both the recogniser and the pytest run. The row must show
    that the name was looked at and not accepted — a fact about the looking —
    and must record nothing about whether the turn has a test, because there
    is no field left in which to record it.
    """
    worktree = _worktree(tmp_path)
    written = worktree / test_file
    written.parent.mkdir(parents=True, exist_ok=True)
    written.write_text(content)

    observation = _real_observation(
        worktree, _results(files_created=["src/widget.py", test_file])
    )

    assert observation["names_matching_a_convention"] == [], description
    assert test_file in observation["names_examined_by_recogniser"]
    assert observation["names_not_examined_by_recogniser"] == []
    # The reader is shown the name itself, so the file the check cannot see is
    # still in front of them.
    lines = dict(gate.observation_lines(observation))
    assert test_file in lines[gate.LABEL_FILES_CREATED]


def test_a_python_test_excluded_from_collection_is_still_recorded_as_named(
    tmp_path: Path,
) -> None:
    """The same trap, reachable without leaving Python.

    A root ``conftest.py`` carrying ``collect_ignore_glob`` tells pytest not
    to collect a path. The Coach's detection honours it, so a perfectly
    ordinary ``test_*.py`` written this turn leaves the run with nothing to
    execute — and the rule, reading only ``tests_written``, fires.
    """
    worktree = _worktree(tmp_path)
    (worktree / "conftest.py").write_text('collect_ignore_glob = ["tests/wip/*"]\n')
    (worktree / "tests" / "wip").mkdir(parents=True, exist_ok=True)
    (worktree / "tests" / "wip" / "test_widget.py").write_text(
        "def test_widget():\n    assert True\n"
    )

    observation = _real_observation(
        worktree, _results(files_created=["src/widget.py", "tests/wip/test_widget.py"])
    )

    assert observation["matching_names_found_on_disk"] == ["tests/wip/test_widget.py"]
    assert observation["independent_test_run_command"] == "skipped"


def test_a_documentation_only_turn_records_the_same_kind_of_fact(
    tmp_path: Path,
) -> None:
    """The control. Removing the conclusions must not remove the observations.

    Without this, "record nothing" would pass every test above and lose the
    finding the instrument exists to make.
    """
    worktree = _worktree(tmp_path)
    (worktree / "docs").mkdir(parents=True, exist_ok=True)
    (worktree / "docs" / "guide.md").write_text("# guide\n")

    observation = _real_observation(worktree, _results(files_created=["docs/guide.md"]))

    assert observation["rule_fired"] is True
    assert observation["report_tests_written"] == []
    assert observation["names_examined_by_recogniser"] == ["docs/guide.md"]
    assert observation["names_matching_a_convention"] == []
    assert observation["names_not_examined_by_recogniser"] == []
    assert observation["independent_test_run_command"] == "skipped"


def test_a_name_the_recogniser_never_saw_is_kept_apart_from_one_it_rejected(
    tmp_path: Path,
) -> None:
    """"Not accepted" and "never looked at" are different facts.

    If the recogniser is missing or raises on a name, that name goes into
    ``names_not_examined_by_recogniser`` — never into the list of names it
    looked at. Collapsing the two is how the instrument came to say something
    about a file nothing had inspected.
    """

    class _NoRecogniser:
        """A validator whose recogniser is absent — the degenerate case."""

        worktree_path = None
        _is_test_file_path = None

        def _check_zero_test_anomaly(self, *_args, **_kwargs):
            return [
                {
                    "severity": "warning",
                    "category": gate.ANOMALY_CATEGORY,
                    "description": "irrelevant to this module",
                }
            ]

    observation = gate.evaluate_zero_test(
        _NoRecogniser(),
        task_work_results=_results(files_created=["src/widget.py"]),
        profile=_feature_profile(),
        independent_tests=_skipped_independent_run(),
        task_id="TASK-ZT-001",
    )

    assert observation["recogniser_available"] is False
    assert observation["names_examined_by_recogniser"] == []
    assert observation["names_not_examined_by_recogniser"] == ["src/widget.py"]
    assert observation["disk_lookup_performed"] is False


def test_a_name_the_recogniser_raised_on_is_not_counted_as_examined(
    tmp_path: Path,
) -> None:
    class _AngryRecogniser:
        worktree_path = None

        @staticmethod
        def _is_test_file_path(path):
            raise ValueError(f"cannot read {path}")

        def _check_zero_test_anomaly(self, *_args, **_kwargs):
            return [{"severity": "warning", "category": gate.ANOMALY_CATEGORY}]

    observation = gate.evaluate_zero_test(
        _AngryRecogniser(),
        task_work_results=_results(files_created=["src/widget.py"]),
        profile=_feature_profile(),
        independent_tests=_skipped_independent_run(),
        task_id="TASK-ZT-001",
    )

    assert observation["names_examined_by_recogniser"] == []
    assert observation["names_not_examined_by_recogniser"] == ["src/widget.py"]


def test_a_disk_lookup_that_did_not_happen_is_recorded_as_not_happening(
    tmp_path: Path,
) -> None:
    """Never "absent" when nothing looked. The report must say so too."""

    class _NoWorktree:
        worktree_path = None
        _is_test_file_path = staticmethod(CoachValidator._is_test_file_path)

        def _check_zero_test_anomaly(self, *_args, **_kwargs):
            return [{"severity": "warning", "category": gate.ANOMALY_CATEGORY}]

    observation = gate.evaluate_zero_test(
        _NoWorktree(),
        task_work_results=_results(files_created=["tests/test_widget.py"]),
        profile=_feature_profile(),
        independent_tests=_skipped_independent_run(),
        task_id="TASK-ZT-001",
    )

    assert observation["names_matching_a_convention"] == [
        {"name": "tests/test_widget.py", "conventions": ["test_*.py"]}
    ]
    assert observation["disk_lookup_performed"] is False
    assert observation["matching_names_found_on_disk"] == []
    assert dict(gate.observation_lines(observation))[gate.LABEL_ON_DISK] == (
        "not looked for (no worktree path was recorded)"
    )


def test_an_odd_player_report_never_breaks_the_recording(tmp_path: Path) -> None:
    """A Player report is untrusted input; it must not crash the recorder."""
    validator = _validator(_worktree(tmp_path))
    results = {
        "task_id": "TASK-ZT-001",
        "quality_gates": "not a dict at all",
        "files_created": "not-a-list",
        "files_modified": [None, 7, "src/widget.py"],
        "tests_written": [],
    }

    observation = gate.evaluate_zero_test(
        validator,
        task_work_results=results,
        profile=_feature_profile(),
        independent_tests=_skipped_independent_run(),
        task_id="TASK-ZT-001",
    )

    assert observation["report_files_created"] == []
    assert observation["report_files_modified"] == ["src/widget.py"]
    assert observation["report_quality_gates_all_passed"] is None


# ===========================================================================
# 6. Every field a reader sees is explained, in the report, by the code
# ===========================================================================


def test_every_rendered_field_states_how_it_was_established() -> None:
    """The provenance legend and the row labels are one list, not two copies.

    A row line whose label the legend does not explain is a value with no
    stated source, which is precisely what this instrument must not print.
    """
    explained = {label for label, _how in gate.FIELD_PROVENANCE}
    rendered = {label for label, _value in gate.observation_lines(_fired_observation())}

    assert rendered == explained
    for _label, how in gate.FIELD_PROVENANCE:
        assert how.strip(), "a field is listed with no statement of its source"


def test_the_provenance_names_the_recogniser_and_its_whole_reach() -> None:
    """A reader must be able to see how narrow "matched" is, from the report."""
    how = dict(gate.FIELD_PROVENANCE)[gate.LABEL_MATCHING]

    assert gate.RECOGNISER in how
    for label in gate.CONVENTION_LABELS:
        assert label in how, f"the report never tells a reader about {label!r}"
    assert "pytest" in dict(gate.FIELD_PROVENANCE)[gate.LABEL_INDEPENDENT_RUN]


def test_a_field_a_row_never_carried_is_not_shown_as_an_empty_one() -> None:
    """"Nothing was written down" and "this came back empty" are different.

    A row written under an older shape of this record does not carry the
    fields below. Rendering those as ``(none)`` would put an observation on
    the page that nothing ever made — the same class of defect as the
    sentences this instrument had removed, one layer down.
    """
    absent = dict(gate.observation_lines({}))
    for label in (
        gate.LABEL_TESTS_WRITTEN,
        gate.LABEL_FILES_CREATED,
        gate.LABEL_FILES_MODIFIED,
        gate.LABEL_MATCHING,
        gate.LABEL_EXAMINED,
        gate.LABEL_NOT_EXAMINED,
        gate.LABEL_ON_DISK,
        gate.LABEL_INDEPENDENT_RUN,
        gate.LABEL_QUALITY_GATES,
        gate.LABEL_CRITERIA,
        gate.LABEL_SEVERITY,
        gate.LABEL_DECISION,
    ):
        assert absent[label] == gate.NOT_RECORDED, (
            f"{label!r} was rendered as an observation on a row that never "
            "carried it"
        )

    # And a field that IS there and holds nothing says so, distinctly.
    present = dict(
        gate.observation_lines(
            {
                "report_tests_written": [],
                "names_matching_a_convention": [],
                "matching_names_found_on_disk": [],
                "report_quality_gates_all_passed": True,
            }
        )
    )
    assert present[gate.LABEL_TESTS_WRITTEN] == "(none)"
    assert present[gate.LABEL_MATCHING] == "(none)"
    assert present[gate.LABEL_ON_DISK] == "(none)"
    assert "all_passed=True" in present[gate.LABEL_QUALITY_GATES]


# ===========================================================================
# 7. The ledger survives ordinary housekeeping
#
# Decision of Record D-OBS-4 (2026-07-09) put the durable home for .guardkit
# artifacts outside the repository for exactly this reason: in-tree artifacts
# are one copy on one machine with no git recovery.
# ===========================================================================


def test_git_clean_fdx_does_not_delete_the_ledger(tmp_path: Path) -> None:
    """The housekeeping command that used to wipe this record."""
    repo_root = tmp_path / "repo"
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={},
    )
    ledger = _durable_ledger(tmp_path)
    assert ledger.is_file()

    subprocess.run(
        ["git", "init", "-b", "main"], cwd=repo_root, check=True, capture_output=True
    )
    # A control file: if this survives, the clean did not really run and the
    # test would be proving nothing.
    control = repo_root / "untracked-control.txt"
    control.write_text("delete me\n")
    subprocess.run(
        ["git", "clean", "-fdx"], cwd=repo_root, check=True, capture_output=True
    )

    assert not control.exists(), "git clean -fdx did not run; test proves nothing"
    assert ledger.is_file(), "git clean -fdx deleted the ledger"
    assert json.loads(ledger.read_text().splitlines()[0])["task_id"] == "TASK-ZT-001"


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
    old.write_text(json.dumps({"task_id": "TASK-RECORDED-EARLIER", "turn": 1}) + "\n")

    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={},
    )

    task_ids = [row["task_id"] for row in gate.read_rows(repo_root)]
    assert "TASK-RECORDED-EARLIER" in task_ids
    assert "TASK-ZT-001" in task_ids
    # And the report names the old file too, so a person can find the row.
    assert str(repo_root / gate.LEGACY_IN_TREE_QUEUE) in _report(
        "--repo-root", str(repo_root)
    )


# ===========================================================================
# 8. CONCURRENT BUILDS
#
# Eleven autobuild worktrees were live against this one repository when this
# was written, and they all append to its single ledger. Two finishing a turn
# together must not splice one line into another: a dropped row is a silently
# wrong record.
# ===========================================================================


#: A standalone program that appends to the ledger, used to run several REAL
#: concurrent writers. Separate processes, because that is what production is:
#: many autobuild worktrees, each its own process, one ledger.
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
    bytes land in between, destroying both rows.
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
            pytest.fail(f"ledger line {number} was spliced and will not parse: {exc}")
    assert len(task_ids) == writers * per_writer, "rows were overwritten"


def test_a_short_write_cannot_truncate_a_row(tmp_path: Path) -> None:
    """The kernel may accept fewer bytes than offered; the row must survive.

    ``os.write`` is allowed to write only part of what it is given. If the
    append stopped there, the ledger would hold half a row. Here the operating
    system is made to accept seven bytes at a time.
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
            for row in gate.read_rows(tmp_path):
                if "task_id" not in row:
                    seen_bad.append(row)

    reader = threading.Thread(target=keep_reading)
    reader.start()
    try:
        for index in range(40):
            gate._append_line_atomically(
                ledger,
                json.dumps({"task_id": f"TASK-{index}", "pad": "y" * 20_000}) + "\n",
            )
    finally:
        stop.set()
        reader.join()

    assert seen_bad == []
    assert len(gate.read_rows(tmp_path)) == 40


# ===========================================================================
# 9. ONE RESOLVER FOR READING AND WRITING
#
# These used to answer the question separately: a build keyed its rows by the
# repository it was building, the report by whatever directory the reader
# stood in. Run the report one level down and it found nothing.
# ===========================================================================


def test_read_and_write_resolve_the_same_key_by_construction(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    worktree = repo_root / ".guardkit" / "worktrees" / "FEAT-ZT99"
    worktree.mkdir(parents=True)
    (repo_root / "sub" / "dir").mkdir(parents=True)

    assert gate.resolve_repo_root(worktree) == repo_root
    assert gate.ledger_path_for(worktree) == gate.ledger_path_for(repo_root)
    assert gate.resolve_repo_root(repo_root) == repo_root  # idempotent


def test_the_report_finds_the_rows_from_anywhere_inside_the_repository(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={},
    )
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=repo_root, check=True, capture_output=True
    )
    deep = repo_root / "guardkit" / "orchestrator"
    deep.mkdir(parents=True, exist_ok=True)

    assert "TASK-ZT-001" in _report("--repo-root", str(deep))


def test_a_linked_git_worktree_reports_its_repositorys_rows(
    tmp_path: Path,
) -> None:
    """A lane worktree must read the repository's rows, not its own empty set."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    linked = tmp_path / "lane-worktree"
    linked.mkdir()
    (linked / ".git").write_text(
        f"gitdir: {repo_root}/.git/worktrees/lane-worktree\n"
    )

    assert gate.resolve_repo_root(linked) == repo_root
    assert gate.ledger_path_for(linked) == gate.ledger_path_for(repo_root)


def test_read_ledger_says_whether_it_found_a_ledger_at_all(
    tmp_path: Path,
) -> None:
    """"No file" and "an empty file" are different facts, handed to the caller."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    nothing = gate.read_ledger(repo_root)
    assert nothing.any_ledger_file is False
    assert nothing.rows == []

    ledger = gate.ledger_path_for(repo_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("")

    empty = gate.read_ledger(repo_root)
    assert empty.any_ledger_file is True
    assert empty.rows == []


# ===========================================================================
# 10. The report — values, provenance, counts. No verdict.
# ===========================================================================


def test_the_report_prints_each_value_and_how_it_was_established(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(
            report_files_created=["docs/guide.md"],
            names_matching_a_convention=[
                {"name": "tests/test_widget.py", "conventions": ["test_*.py"]}
            ],
        ),
        env={},
    )

    output = _report("--repo-root", str(repo_root))

    assert "1 row(s) recorded" in output
    for label, _how in gate.FIELD_PROVENANCE:
        assert label in output, f"the report never shows {label!r}"
    assert gate.RECOGNISER in output
    assert "docs/guide.md" in output
    assert "tests/test_widget.py [test_*.py]" in output
    assert "TASK-ZT-001" in output


def test_every_count_the_report_prints_names_what_it_counted(
    tmp_path: Path,
) -> None:
    """A count of facts is a fact — as long as the heading says which fact."""
    repo_root = tmp_path / "repo"
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={},
        task_id="TASK-COUNT-1",
    )
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(
            report_tests_written=["tests/test_widget.py"],
            names_matching_a_convention=[
                {"name": "tests/test_widget.py", "conventions": ["test_*.py"]}
            ],
            matching_names_found_on_disk=["tests/test_widget.py"],
        ),
        env={},
        task_id="TASK-COUNT-2",
    )

    output = _report("--repo-root", str(repo_root))

    assert "2 row(s) recorded" in output
    for heading, predicate in gate.OBSERVATION_COUNTS:
        assert _flat(heading) in output, f"a count is printed without {heading!r}"
    rows = gate.read_rows(repo_root)
    counts = {
        heading: sum(1 for row in rows if predicate(row))
        for heading, predicate in gate.OBSERVATION_COUNTS
    }
    assert counts["the report's tests_written list was recorded and was empty"] == 1
    assert (
        counts[f"at least one name accepted by {gate.RECOGNISER} was found on disk"]
        == 1
    )
    assert counts['the Coach decision recorded was "approve"'] == 2


def test_a_row_that_never_carried_a_field_is_counted_in_no_total() -> None:
    """No count may absorb a row that has nothing to say about its question.

    A row recorded under an older shape of this record carries none of the
    observation fields. Every predicate must be False for it, so it lands in
    no total — rather than being silently counted as an observation of
    emptiness that nothing ever made.
    """
    old_shape = {
        "schema": "zero_test_receipt/3",
        "task_id": "TASK-OLD",
        "turn": 1,
        "recognised_test_files": ["tests/test_a.py"],
        "tests_written": [],
        "files_created": ["docs/x.md"],
    }

    landed_in = [
        heading
        for heading, predicate in gate.OBSERVATION_COUNTS
        if predicate(old_shape)
    ]

    assert landed_in == [], (
        "a row carrying none of the observation fields was counted under "
        f"{landed_in}"
    )


def test_the_report_distinguishes_an_empty_ledger_from_no_ledger(
    tmp_path: Path,
) -> None:
    """Two different facts, and the report must not print one as the other."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    absent = _report("--repo-root", str(repo_root))
    assert "No ledger file exists" in absent
    assert "0 rows recorded" not in absent

    ledger = gate.ledger_path_for(repo_root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("")

    empty = _report("--repo-root", str(repo_root))
    assert "0 rows recorded" in empty
    assert "exist and hold no rows" in empty
    assert "No ledger file exists" not in empty
    # And it says what an empty ledger does and does not cover.
    assert "A row is written only when" in empty


def test_the_report_can_read_several_repositories_at_once(
    tmp_path: Path,
) -> None:
    for name in ("alpha", "beta"):
        ledger = tmp_path / "durable" / name / gate.ZERO_TEST_QUEUE_FILENAME
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(
            json.dumps({"task_id": f"TASK-{name.upper()}", "turn": 1, "repo": name})
            + "\n"
        )
        (tmp_path / name).mkdir(parents=True, exist_ok=True)

    output = _report(
        "--repo-root", str(tmp_path / "alpha"), "--repo-root", str(tmp_path / "beta")
    )

    assert "2 row(s) recorded" in output
    assert "TASK-ALPHA" in output
    assert "TASK-BETA" in output


def test_the_report_can_emit_the_raw_rows(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _run_recorder(
        tmp_path,
        decision={"decision": "approve", "rationale": "fine", "issues": []},
        observation=_fired_observation(),
        env={},
    )

    from click.testing import CliRunner

    from guardkit.cli.autobuild import zero_test_report

    result = CliRunner().invoke(
        zero_test_report, ["--repo-root", str(repo_root), "--json"]
    )

    assert '"task_id"' in result.output
    assert "TASK-ZT-001" in result.output


def test_a_build_outside_a_worktree_records_no_worktree_directory(
    tmp_path: Path,
) -> None:
    """An honest absence, not a guessed identifier."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = tmp_path / "plain-checkout"

    assert invoker._zero_test_worktree_dir() is None


# ===========================================================================
# 11. THE PRODUCTION WIRING
#
# Everything above calls _record_zero_test_observation directly. None of it
# would notice if invoke_coach — the real Coach path a build takes — stopped
# calling it. And because this records rather than blocks, a dropped call site
# has NO build-visible symptom: the instrument would simply stop recording,
# silently, forever. These two tests are the only thing standing between that
# and a ledger that quietly stays empty. Modelled on
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
        return_value=SimpleNamespace(verified=True, honesty_score=1.0, discrepancies=[])
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
                zero_test=_fired_observation(),
            ),
        )
    )


def test_invoke_coach_really_calls_the_zero_test_recorder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The production Coach path must reach the recorder. Nothing else proves it.

    Delete, comment out, or misplace the
    ``self._record_zero_test_observation(...)`` call in
    ``AgentInvoker.invoke_coach`` and this test goes red. Without it, that
    deletion is invisible: no test fails, no build changes, and the recording
    silently stops.
    """
    monkeypatch.delenv(gate.BLOCKING_ENV_VAR, raising=False)
    invoker = _wired_invoker(_worktree(tmp_path))

    with patch.object(
        invoker, "_record_zero_test_observation", autospec=True
    ) as recorder:
        result = _run_a_real_coach_turn(invoker, "TASK-WIRED-001")

    assert result.success is True
    assert recorder.call_count == 1, (
        "invoke_coach did not call the zero-test recorder — the instrument is "
        "disconnected and would record nothing, with no other symptom"
    )
    passed = recorder.call_args.kwargs
    assert passed["task_id"] == "TASK-WIRED-001"
    assert passed["turn"] == 1
    assert passed["decision"]["decision"] == "approve"
    assert passed["evidence_bundle"].zero_test["rule_fired"] is True


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
    rows = gate.read_rows(tmp_path / "repo")
    assert [row["task_id"] for row in rows] == ["TASK-WIRED-002"]
    # It records, and leaves the verdict alone.
    assert rows[0]["coach_decision"] == "approve"
    assert rows[0]["decision_changed_by_this_instrument"] is False


def test_the_observation_adds_no_prose_to_the_coach_prompt(tmp_path: Path) -> None:
    """The surface that was removed stays removed — pinned by property.

    An earlier version appended a sentence about this check to the Coach's
    prompt. Four rounds could not make that sentence true, so it was deleted
    along with the module function that produced it. The model still gets the
    observations, as fields inside the evidence bundle; what it must not get
    is prose about them.

    Stated as a property rather than as a forbidden phrase: whether the rule
    fired or was never reached, everything the prompt says AROUND the evidence
    bundle must be identical. Any sentence added about this check — however
    worded — breaks that equality.
    """
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = _worktree(tmp_path)

    def _around_the_bundle(zero_test) -> str:
        rendered = invoker._render_evidence_bundle_section(
            CoachEvidenceBundle(
                honesty=None, gathering_status="complete", zero_test=zero_test
            )
        )
        head, _, tail = rendered.partition("</evidence_bundle>")
        return head.partition("<evidence_bundle>")[0] + tail

    assert _around_the_bundle(_fired_observation()) == _around_the_bundle(None)
    assert not hasattr(gate, "coach_advisory_text"), (
        "the function that produced the removed prompt sentence is back"
    )
