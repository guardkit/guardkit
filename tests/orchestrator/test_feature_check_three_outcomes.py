"""Three outcomes, two lists, and nothing unchecked ever recorded as passed.

Plain words. The project's finished-feature check used to have two answers:
it passed, or it failed. That hid a third thing that really happens — the
check COULD NOT RUN (nothing to run it on) — behind "failed", which sent a
builder off to repair a fault that was never there, and behind "blocked",
which refused a build over a check that never happened.

So (21 September 2026) there are three outcomes, each carried by name:

* **passed** — the command exits 0. Not entered into repair. Does not block.
* **failed** — it ran and exited non-zero, or timed out. Enters the bounded
  repair exactly as before, and still blocks.
* **could not run** — the project's own line of JSON says so, in so many
  words. Enters NEITHER: there is nothing for a builder to repair and nothing
  was proved. Every example goes on the not-checked list with the reason.

And two lists travel beside the outcome: what nothing looked at
(``not_checked``) and what the project observed (``observations``). Central
code carries both as text, caps them hard, and never reads, compares or
judges them.

THE FIXTURE IS NOT PYTHON, ON PURPOSE — it is the Makefile project from
``test_feature_check.py``, whose check is a shell script. No model is ever
called: ``_execute_wave`` is stubbed throughout.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardkit.orchestrator.feature_check import (
    COULD_NOT_RUN_WITHOUT_REASON,
    CUT_MARK,
    MAX_NOT_CHECKED_CARRIED,
    MAX_OBSERVATIONS,
    OBSERVATION_SIDE_LIMIT,
    RECEIPT_RELATIVE_PATH,
    FeatureCheckAttempt,
    FeatureCheckOutcome,
    completion_verdict,
    merge_not_checked,
    parse_project_check_line,
    update_feature_check_receipt,
)

from tests.orchestrator.test_feature_check import (  # noqa: E402
    SCENARIO_TITLE,
    _declaration,
    _make_feature,
    _make_project,
    _receipt,
    _run_build,
    _WaveRecorder,
    _write,
)


@pytest.fixture(autouse=True)
def _no_ambient_flags(monkeypatch: pytest.MonkeyPatch):
    """The estate's own env must not decide what these tests prove."""
    monkeypatch.delenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", raising=False)
    monkeypatch.delenv("GUARDKIT_QA_ENFORCE_TWIN_COVERAGE", raising=False)


def _line(**block: object) -> str:
    return json.dumps({"guardkit_feature_check": block})


def _check_script(body: str) -> str:
    return "#!/bin/sh\n" + body


def _project(tmp_path: Path, body: str, *, hurl_scenario: bool = False):
    """The Makefile project, with a check script this test wrote."""
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    _write(worktree, "qa/feature-check.sh", _check_script(body))
    feature = _make_feature(worktree, hurl_scenario=hurl_scenario)
    return repo_root, worktree, feature


# ---------------------------------------------------------------------------
# 1. The three-outcome table, row by row
# ---------------------------------------------------------------------------


def test_row_one_exit_zero_is_passed_and_enters_no_repair(tmp_path: Path) -> None:
    repo_root, worktree, feature = _project(
        tmp_path,
        f"echo '{_line(scenarios_covered=[SCENARIO_TITLE])}'\nexit 0\n",
    )
    recorder = _WaveRecorder(worktree)

    _, _, result = _run_build(repo_root, worktree, feature, recorder)

    assert recorder.feedback == [None], "no repair round was entered"
    receipt = _receipt(worktree)
    assert receipt["status"] == "passed"
    assert receipt["attempts"][-1]["outcome"] == "passed"
    assert receipt["scenarios_covered"] == [SCENARIO_TITLE]
    assert result.status == "completed"


def test_row_two_a_non_zero_exit_is_failed_and_enters_the_repair(
    tmp_path: Path,
) -> None:
    repo_root, worktree, feature = _project(
        tmp_path, "echo 'the surface answered with the wrong thing' >&2\nexit 1\n"
    )
    recorder = _WaveRecorder(worktree)

    _, _, result = _run_build(repo_root, worktree, feature, recorder)

    assert len(recorder.feedback) == 2, "one bounded repair round was entered"
    assert recorder.feedback[1] is not None
    receipt = _receipt(worktree)
    assert receipt["status"] == "failed"
    assert receipt["attempts"][-1]["outcome"] == "failed"
    assert result.status == "failed"


def test_row_two_a_timeout_is_failed_whatever_the_output_said(
    tmp_path: Path,
) -> None:
    """A command cut off part-way has not finished telling anyone anything."""
    repo_root, worktree = _make_project(
        tmp_path,
        declaration=_declaration("sh qa/feature-check.sh", timeout=1),
    )
    _write(
        worktree,
        "qa/feature-check.sh",
        _check_script(
            f"echo '{_line(could_not_run={'reason': 'never read'})}'\nsleep 30\n"
        ),
    )
    feature = _make_feature(worktree)
    recorder = _WaveRecorder(worktree)

    _, _, result = _run_build(repo_root, worktree, feature, recorder)

    receipt = _receipt(worktree)
    assert receipt["status"] == "failed"
    assert receipt["attempts"][-1]["outcome"] == "failed"
    assert receipt["attempts"][-1]["timed_out"] is True
    assert result.status == "failed"


def test_row_two_saying_nothing_and_exiting_non_zero_is_never_could_not_run(
    tmp_path: Path,
) -> None:
    """The project has to say it in so many words, or it is a failure."""
    repo_root, worktree, feature = _project(tmp_path, "exit 3\n")

    _, _, result = _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    receipt = _receipt(worktree)
    assert receipt["status"] == "failed"
    assert receipt["could_not_run_reason"] is None
    assert result.status == "failed"


def test_row_three_could_not_run_enters_no_repair_and_does_not_block(
    tmp_path: Path,
) -> None:
    repo_root, worktree, feature = _project(
        tmp_path,
        "echo '"
        + _line(could_not_run={"reason": "no container runtime on this machine"})
        + "'\nexit 1\n",
        hurl_scenario=True,
    )
    recorder = _WaveRecorder(worktree)

    _, _, result = _run_build(repo_root, worktree, feature, recorder)

    assert recorder.feedback == [None], (
        "a check that could not run sends nothing to a builder to repair"
    )
    receipt = _receipt(worktree)
    assert receipt["status"] == "could_not_run"
    assert receipt["attempts"][-1]["outcome"] == "could_not_run"
    assert "no container runtime" in receipt["could_not_run_reason"]
    assert result.status == "completed", "it does not block the build"
    assert result.success is True

    names = [e["name"] for e in receipt["not_checked"]]
    assert SCENARIO_TITLE in names, "every example goes on the not-checked list"
    # Every entry gives a reason. This example has two sources saying nothing
    # looked at it (the central guard named it first, then the check could not
    # run at all); the first reason is kept and the record still says, at the
    # top, why the check itself could not run.
    assert all(e["reason"] for e in receipt["not_checked"])
    assert receipt["scenarios_covered"] == []


def test_could_not_run_is_the_project_s_word_even_on_a_zero_exit(
    tmp_path: Path,
) -> None:
    repo_root, worktree, feature = _project(
        tmp_path,
        "echo '" + _line(could_not_run="nothing to run the check against") + "'\nexit 0\n",
    )

    _, _, result = _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    receipt = _receipt(worktree)
    assert receipt["status"] == "could_not_run"
    assert receipt["scenarios_covered"] == []
    assert result.status == "completed"


def test_could_not_run_with_no_reason_says_that_it_gave_none(tmp_path: Path) -> None:
    repo_root, worktree, feature = _project(
        tmp_path, "echo '" + _line(could_not_run=True) + "'\nexit 1\n"
    )

    _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    assert _receipt(worktree)["could_not_run_reason"] == COULD_NOT_RUN_WITHOUT_REASON


# ---------------------------------------------------------------------------
# 2. "Not checked" is never recorded as passed
# ---------------------------------------------------------------------------


def test_a_name_on_the_not_checked_list_is_never_on_the_covered_list(
    tmp_path: Path,
) -> None:
    """Even when the project itself prints it under both headings."""
    repo_root, worktree, feature = _project(
        tmp_path,
        "echo '"
        + _line(
            scenarios_covered=[SCENARIO_TITLE, "Another example"],
            not_checked=[{"name": SCENARIO_TITLE, "reason": "no check file for it"}],
        )
        + "'\nexit 0\n",
    )

    _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    receipt = _receipt(worktree)
    assert receipt["scenarios_covered"] == ["Another example"]
    assert [e["name"] for e in receipt["not_checked"]] == [SCENARIO_TITLE]


def test_the_guard_s_missing_list_reaches_the_record_without_blocking(
    tmp_path: Path,
) -> None:
    """The central guard reports and does not block; the names still travel.

    The project declares an example that wants a check file of its own and
    writes no such file. Nothing looked at that example, so it is named — and
    the build is not refused over it.
    """
    repo_root, worktree, feature = _project(
        tmp_path, "echo '" + _line(scenarios_covered=[]) + "'\nexit 0\n",
        hurl_scenario=True,
    )

    _, _, result = _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    receipt = _receipt(worktree)
    assert result.status == "completed"
    assert SCENARIO_TITLE in [e["name"] for e in receipt["not_checked"]]
    assert receipt["scenarios_covered"] == []


def test_finishing_the_record_removes_a_newly_not_checked_name_from_covered(
    tmp_path: Path,
) -> None:
    """The end-of-build caller's own rule, on a record already on disk."""
    path = tmp_path / RECEIPT_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"status": "passed", "scenarios_covered": ["A", "B"]}),
        encoding="utf-8",
    )

    written = update_feature_check_receipt(
        tmp_path,
        not_checked=[{"name": "a", "reason": "nothing looked at it"}],
        notes=["said once"],
    )

    assert written is not None
    data = json.loads(path.read_text())
    assert data["scenarios_covered"] == ["B"], "compared without regard to case"
    assert [e["name"] for e in data["not_checked"]] == ["a"]
    assert data["record_notes"] == ["said once"]


def test_finishing_a_record_that_is_not_there_never_raises(tmp_path: Path) -> None:
    assert update_feature_check_receipt(
        tmp_path, not_checked=[{"name": "x", "reason": "y"}]
    ) is None
    assert update_feature_check_receipt(tmp_path, not_checked=[]) is None


def test_merging_two_sources_keeps_one_entry_per_name(tmp_path: Path) -> None:
    merged = merge_not_checked(
        [{"name": "One", "reason": "first"}],
        [{"name": "one", "reason": "second"}, "Two", {"no": "name"}, 7],
    )
    assert merged == [
        {"name": "One", "reason": "first"},
        {"name": "Two", "reason": ""},
    ]


# ---------------------------------------------------------------------------
# 3. The caps, and what a malformed line does
# ---------------------------------------------------------------------------


def test_observations_are_capped_and_both_sides_are_cut_with_a_mark() -> None:
    long = "x" * (OBSERVATION_SIDE_LIMIT + 50)
    line = parse_project_check_line(
        _line(
            observations=[
                {"asked": long, "answered": long} for _ in range(MAX_OBSERVATIONS + 6)
            ]
        )
    )

    assert len(line.observations) == MAX_OBSERVATIONS
    assert line.observations_total == MAX_OBSERVATIONS + 6
    assert line.observations[0]["asked"].endswith(CUT_MARK)
    assert line.observations[0]["answered"].endswith(CUT_MARK)
    assert len(line.observations[0]["asked"]) == OBSERVATION_SIDE_LIMIT + len(CUT_MARK)
    assert any("observation" in note for note in line.notes)


def test_the_not_checked_list_is_capped_and_the_true_count_is_kept() -> None:
    line = parse_project_check_line(
        _line(
            not_checked=[
                {"name": f"example {i}", "reason": "no check file"}
                for i in range(MAX_NOT_CHECKED_CARRIED + 30)
            ]
        )
    )

    assert len(line.not_checked) == MAX_NOT_CHECKED_CARRIED
    assert line.not_checked_total == MAX_NOT_CHECKED_CARRIED + 30
    assert any(str(line.not_checked_total) in note for note in line.notes)


def test_anything_malformed_is_ignored_and_said_so() -> None:
    line = parse_project_check_line(
        _line(
            scenarios_covered="not a list",
            not_checked="not a list either",
            observations=[{"nothing": "useful"}, "a bare string", {"asked": "q"}],
            could_not_run=["neither"],
        )
    )

    assert line.scenarios_covered == []
    assert line.not_checked == []
    assert [o["asked"] for o in line.observations] == ["q"]
    assert line.could_not_run is False
    assert len(line.notes) == 4, line.notes


def test_a_line_that_is_not_json_is_ignored_and_said_so() -> None:
    line = parse_project_check_line("{guardkit_feature_check broken\nordinary output\n")
    assert line.scenarios_covered == []
    assert any("JSON" in note for note in line.notes)


def test_a_project_that_prints_no_line_at_all_says_nothing() -> None:
    line = parse_project_check_line("just some output\n")
    assert line.scenarios_covered == []
    assert line.not_checked == []
    assert line.observations == []
    assert line.could_not_run is False
    assert line.notes == []


def test_observations_reach_the_record_as_text(tmp_path: Path) -> None:
    repo_root, worktree, feature = _project(
        tmp_path,
        "echo '"
        + _line(
            scenarios_covered=[],
            observations=[
                {"asked": "the empty state", "answered": "[]"},
                {"asked": "after three records", "answered": "three rows"},
            ],
        )
        + "'\nexit 0\n",
    )

    _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    receipt = _receipt(worktree)
    assert receipt["observations"] == [
        {"asked": "the empty state", "answered": "[]"},
        {"asked": "after three records", "answered": "three rows"},
    ]
    assert receipt["observations_total"] == 2


# ---------------------------------------------------------------------------
# 4. The completion rule's own three answers
# ---------------------------------------------------------------------------


def _receipt_on_disk(worktree: Path, payload: dict) -> None:
    path = worktree / RECEIPT_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_the_rule_still_blocks_a_record_that_says_failed(tmp_path: Path) -> None:
    repo_root, worktree, feature = _project(tmp_path, "exit 0\n")
    _receipt_on_disk(worktree, {"status": "failed", "scenarios_covered": []})

    verdict = completion_verdict(
        repo_root=repo_root, worktree_root=worktree, feature=feature
    )
    assert verdict.blocks is True


def test_the_rule_does_not_block_a_record_that_says_could_not_run(
    tmp_path: Path,
) -> None:
    repo_root, worktree, feature = _project(tmp_path, "exit 0\n", hurl_scenario=True)
    _receipt_on_disk(
        worktree,
        {
            "status": "could_not_run",
            "could_not_run_reason": "no interpreter for the check",
            "scenarios_covered": [],
        },
    )

    verdict = completion_verdict(
        repo_root=repo_root, worktree_root=worktree, feature=feature
    )

    assert verdict.blocks is False
    assert [e["name"] for e in verdict.not_checked] == [SCENARIO_TITLE]
    assert verdict.not_checked[0]["reason"] == "no interpreter for the check"


def test_an_outcome_object_never_reports_a_not_checked_name_as_covered() -> None:
    outcome = FeatureCheckOutcome(
        feature_id="FEAT-TEST",
        status="passed",
        declared=True,
        attempts=[
            FeatureCheckAttempt(
                attempt=1,
                command="anything",
                candidate_sha="abc",
                passed=True,
                outcome="passed",
                scenarios_covered=["Kept", "Dropped"],
            )
        ],
        not_checked=[{"name": "dropped", "reason": "nothing looked at it"}],
    )
    assert outcome.scenarios_covered == ["Kept"]
    assert outcome.to_dict()["scenarios_covered"] == ["Kept"]


# ---------------------------------------------------------------------------
# 5. The summary of what the code checks did, written by the real build
# ---------------------------------------------------------------------------


def test_the_build_writes_the_code_checks_summary_beside_the_record(
    tmp_path: Path,
) -> None:
    """It lands in the folder the runner exports, and it says "not checked".

    This build kept no review of its one task, so there is nothing to say the
    checks ran. The summary says exactly that, and never "clean".
    """
    from guardkit.orchestrator.code_checks import (
        STATE_NOT_CHECKED,
        SUMMARY_RELATIVE_PATH,
    )

    repo_root, worktree, feature = _project(
        tmp_path, "echo '" + _line(scenarios_covered=[]) + "'\nexit 0\n"
    )

    _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    path = worktree / SUMMARY_RELATIVE_PATH
    assert path.parent == (worktree / RECEIPT_RELATIVE_PATH).parent
    summary = json.loads(path.read_text())
    assert summary["feature"] == "FEAT-TEST"
    assert summary["tasks"][0]["task"] == "TASK-001"
    assert summary["tasks_not_checked"] == ["TASK-001"]
    assert all(
        check["state"] == STATE_NOT_CHECKED
        for check in summary["tasks"][0]["checks"].values()
    )


def test_an_attempt_written_before_today_still_reads_as_two_outcomes() -> None:
    old = FeatureCheckAttempt(
        attempt=1, command="c", candidate_sha="s", passed=False
    )
    assert old.resolved_outcome == "failed"
    assert old.could_not_run is False
    assert old.to_dict()["outcome"] == "failed"
