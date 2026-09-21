"""One summary of what the code checks did, from records shaped like the kept ones.

Plain words. Each task's review already saved what the code checks said. The
check after each group of tasks saved nothing at all. So at merge time nobody
could tell "the checks found nothing" from "the checks never looked" — and
those two read the same on a card.

These tests use records shaped exactly like the ones the 19 September build
left behind: a task whose ``files_authored`` list is empty with no marker (so
nothing was ever recorded about what it wrote), beside a task whose checks ran
and named a real finding. The two acceptance cases the design asks for are the
last two tests: a named finding reaches the summary, and incomplete checking
reaches the summary.

Corrected 21 September 2026 after a second model drove this against the kept
records. Those records hold ``null`` under a check's name, not the shape the
file-list repair produces, and every ``null`` was being read as "it had
nothing to do" — so a build nothing had looked at came out as nought not
checked. The absence tests below are that correction, and the two acceptance
cases now run on kept-shaped records.

Nothing here is a gate. Every function under test swallows its own errors, and
the last test drives that.
"""

from __future__ import annotations

import json
from pathlib import Path

from guardkit.orchestrator.code_checks import (
    CHECK_NAMES,
    STATE_DOES_NOT_APPLY,
    STATE_FOUND_SOMETHING,
    STATE_KIND_NOT_SUPPORTED,
    STATE_NOT_CHECKED,
    STATE_RAN_FOUND_NOTHING,
    SUMMARY_RELATIVE_PATH,
    absence_reading,
    build_code_checks_summary,
    group_record,
    latest_review_record,
    read_code_checks_summary,
    summarise_check,
    summarise_task,
    write_code_checks_summary,
)


# ---------------------------------------------------------------------------
# Records shaped like the kept ones
# ---------------------------------------------------------------------------

#: What a check that ran and found nothing leaves behind.
CLEAN = {"status": "complete", "ran": True, "findings": []}

#: What a check leaves behind when it found something. The shape is the real
#: one: a pattern, the file and the symbol.
FINDING = {
    "status": "complete",
    "ran": True,
    "findings": [
        {
            "pattern": "UNWIRED_PATH",
            "file": "src/users/service.py",
            "lineno": 88,
            "symbol": "get_user_creation_counts_per_day",
        }
    ],
}

#: What every check leaves behind when the builder's file list was never
#: recorded — the 19 September shape, findings ``None`` and not ``[]``.
NOT_CHECKED = {
    "status": "not_checked",
    "ran": False,
    "findings": None,
    "reason": "not checked: the builder's file list was not recorded",
}

#: What the checks say on a kind of project they do not cover.
NOT_SUPPORTED = {
    "status": "unsupported_stack",
    "ran": False,
    "findings": [],
    "skip_reason": "no dialect for the detected language",
}


#: What EVERY check leaves behind when its analyser was not installed, or
#: when it stopped on the way: nothing at all. The kept 19 September records
#: are this shape — ``"wiring": null`` beside the kind of task it was.
ANALYSER_DID_NOT_RUN = {
    "task_type": "feature",
    "wiring": None,
    "mocked_seam": None,
    "stub_scan": None,
    "coverage": None,
}

#: The same absence on a kind of task the checks never look at.
A_KIND_THE_CHECKS_SKIP = dict(ANALYSER_DID_NOT_RUN, task_type="declarative")


def _kept_task_results(*, files: list | None, tracked: bool, shell: int = 0) -> dict:
    record: dict = {"task_id": "TASK-001", "files_created": ["src/users/service.py"]}
    if files is not None:
        record["files_authored"] = files
        if tracked:
            record["files_authored_tracking"] = "tracked"
    record["shell_command_tool_uses"] = shell
    return record


# ---------------------------------------------------------------------------
# 1. The five states, one check at a time
# ---------------------------------------------------------------------------


def test_a_check_that_ran_and_found_nothing() -> None:
    assert summarise_check(CLEAN)["state"] == STATE_RAN_FOUND_NOTHING


def test_a_check_that_found_something_names_the_file_and_the_name() -> None:
    summary = summarise_check(FINDING)
    assert summary["state"] == STATE_FOUND_SOMETHING
    assert summary["finding_count"] == 1
    assert summary["findings"][0]["file"] == "src/users/service.py"
    assert summary["findings"][0]["name"] == "get_user_creation_counts_per_day"


def test_a_check_that_was_not_checked_carries_its_reason() -> None:
    summary = summarise_check(NOT_CHECKED)
    assert summary["state"] == STATE_NOT_CHECKED
    assert "file list was not recorded" in summary["reason"]
    assert summary["findings"] == []


def test_a_check_that_said_it_had_nothing_to_look_at_does_not_apply() -> None:
    """Its own word for it, in the record. That is an honest absence."""
    assert (
        summarise_check({"status": "skipped_no_targets", "findings": []})["state"]
        == STATE_DOES_NOT_APPLY
    )


def test_an_absence_nothing_explains_is_not_checked() -> None:
    """The correction of 21 September, and the rule of this whole module.

    An entry that is ``None`` is what a check leaves behind when it declined
    AND what it leaves behind when its analyser was never there. Read alone,
    it cannot be called either, so it is "not checked" — never a word that
    counts it as done.
    """
    summary = summarise_check(None)
    assert summary["state"] == STATE_NOT_CHECKED
    assert summary["reason"]


def test_an_absence_the_record_does_explain_keeps_its_honest_word() -> None:
    reading = {"state": STATE_DOES_NOT_APPLY, "reason": "nothing to look at"}
    summary = summarise_check(None, absence=reading)
    assert summary["state"] == STATE_DOES_NOT_APPLY
    assert summary["reason"] == "nothing to look at"


def test_a_kind_of_project_the_check_does_not_cover() -> None:
    summary = summarise_check(NOT_SUPPORTED)
    assert summary["state"] == STATE_KIND_NOT_SUPPORTED
    assert summary["reason"]


def test_a_check_that_stopped_on_its_own_error_is_not_checked() -> None:
    summary = summarise_check({"status": "error", "findings": [], "ran": False})
    assert summary["state"] == STATE_NOT_CHECKED


def test_the_word_clean_is_never_the_answer_to_an_absent_signal() -> None:
    """The one rule this module exists for."""
    for block in (None, NOT_CHECKED, NOT_SUPPORTED, {"status": "error"}, "rubbish"):
        assert summarise_check(block)["state"] != STATE_RAN_FOUND_NOTHING


# ---------------------------------------------------------------------------
# 1b. Two corrections of 21 September 2026 (after the Stage C re-check)
# ---------------------------------------------------------------------------


def test_a_task_check_that_read_only_part_of_its_input_says_how_much() -> None:
    """The per-task half now says what the group half has always said.

    It ran, and it found nothing IN WHAT IT COULD READ. The part it could not
    read was covered by nothing, and the count of it used to be thrown away —
    so a check that had read one file in three came out of here as "ran and
    found nothing" with no number beside it at all.
    """
    summary = summarise_check(
        {
            "status": "parse_degraded",
            "ran": True,
            "findings": [],
            "degraded_files": ["a/one", "a/two"],
        }
    )
    assert summary["state"] == STATE_RAN_FOUND_NOTHING
    assert summary["inputs_not_read"] == 2
    assert "could not be read" in summary["reason"]
    assert "2" in summary["reason"]


def test_a_partly_read_task_check_that_found_something_keeps_both() -> None:
    summary = summarise_check(
        dict(FINDING, status="parse_degraded", degraded_files=["a/one"])
    )
    assert summary["state"] == STATE_FOUND_SOMETHING
    assert summary["finding_count"] == 1
    assert summary["inputs_not_read"] == 1


def test_a_check_that_read_everything_carries_no_count() -> None:
    assert summarise_check(CLEAN)["inputs_not_read"] is None
    assert summarise_check(FINDING)["inputs_not_read"] is None
    assert summarise_check(None)["inputs_not_read"] is None


def test_a_status_word_this_summary_does_not_know_is_not_checked() -> None:
    """It used to fall through the mapping and land on "found nothing".

    A skip word nobody here knows says nothing about whether the check looked
    at anything, so it cannot be read as either answer — and "not checked" is
    the only honest one. The word itself is the reason, so whoever reads the
    record can see which word it was.
    """
    summary = summarise_check(
        {"status": "skipped_no_composition_root", "ran": False, "findings": []}
    )
    assert summary["state"] == STATE_NOT_CHECKED
    assert "skipped_no_composition_root" in summary["reason"]


def test_an_unknown_word_never_throws_away_what_the_check_did_name() -> None:
    summary = summarise_check(dict(FINDING, status="a_word_from_nowhere"))
    assert summary["state"] == STATE_NOT_CHECKED
    assert summary["finding_count"] == 1
    assert summary["findings"][0]["name"] == "get_user_creation_counts_per_day"


def test_an_unknown_word_keeps_the_check_s_own_reason_when_it_gave_one() -> None:
    summary = summarise_check(
        {
            "status": "a_word_from_nowhere",
            "skip_reason": "the thing it needed was not there",
            "findings": [],
        }
    )
    assert summary["state"] == STATE_NOT_CHECKED
    assert summary["reason"] == "the thing it needed was not there"


def test_no_word_at_all_is_not_checked_and_never_a_clean_run() -> None:
    """A check that recorded findings but no word saying whether it ran.

    Nothing says it looked at anything, so it cannot read as "ran and found
    nothing" (coordinator's review, 21 September 2026).
    """
    for block in ({"findings": []}, {"status": "", "findings": []}, {"status": None, "findings": []}):
        summary = summarise_check(block)
        assert summary["state"] == STATE_NOT_CHECKED
        assert summary["state"] != STATE_RAN_FOUND_NOTHING
        assert "no word" in summary["reason"]


def test_every_entry_is_the_same_shape_as_the_group_half_s() -> None:
    """One field, one name, one meaning, on both halves of the record."""
    for block in (None, CLEAN, FINDING, NOT_CHECKED, NOT_SUPPORTED, "rubbish"):
        assert "inputs_not_read" in summarise_check(block)
    assert "inputs_not_read" in group_record(1, state=STATE_NOT_CHECKED)


# ---------------------------------------------------------------------------
# 2. One task's row
# ---------------------------------------------------------------------------


def test_a_task_with_no_kept_review_is_not_checked_never_clean() -> None:
    row = summarise_task("TASK-001", review_record=None, task_results=None)
    assert row["review_record_kept"] is False
    for name in CHECK_NAMES:
        assert row["checks"][name]["state"] == STATE_NOT_CHECKED


def test_a_task_row_says_whether_the_file_list_was_recorded() -> None:
    kept = summarise_task(
        "TASK-001",
        review_record={"wiring": NOT_CHECKED},
        task_results=_kept_task_results(files=[], tracked=False, shell=37),
    )
    assert kept["file_list_recorded"] is False
    assert kept["shell_command_count"] == 37

    tracked = summarise_task(
        "TASK-002",
        review_record={"wiring": CLEAN},
        task_results=_kept_task_results(files=["a.py"], tracked=True, shell=2),
    )
    assert tracked["file_list_recorded"] is True

    legacy = summarise_task(
        "TASK-003",
        review_record={"wiring": CLEAN},
        task_results={"task_id": "TASK-003"},
    )
    assert legacy["file_list_recorded"] is None
    assert legacy["file_list_note"]


def test_a_check_absent_from_a_kept_review_is_not_checked() -> None:
    row = summarise_task(
        "TASK-001", review_record={"wiring": CLEAN}, task_results=None
    )
    assert row["checks"]["wiring"]["state"] == STATE_RAN_FOUND_NOTHING
    assert row["checks"]["stub_scan"]["state"] == STATE_NOT_CHECKED


# ---------------------------------------------------------------------------
# 2b. What an absence means, read off the record (corrected 21 September)
# ---------------------------------------------------------------------------


def test_a_kind_of_task_the_checks_skip_reads_as_does_not_apply() -> None:
    reading = absence_reading(A_KIND_THE_CHECKS_SKIP, None)
    assert reading["state"] == STATE_DOES_NOT_APPLY
    assert "declarative" in reading["reason"]

    row = summarise_task("TASK-001", review_record=A_KIND_THE_CHECKS_SKIP)
    assert all(
        check["state"] == STATE_DOES_NOT_APPLY for check in row["checks"].values()
    )


def test_a_task_that_wrote_no_file_reads_as_does_not_apply() -> None:
    """The list WAS recorded and it is empty, so there was nothing to read."""
    reading = absence_reading(
        ANALYSER_DID_NOT_RUN, _kept_task_results(files=[], tracked=True)
    )
    assert reading["state"] == STATE_DOES_NOT_APPLY
    assert "no file" in reading["reason"]


def test_an_analyser_that_was_not_there_reads_as_not_checked() -> None:
    """The case the second model drove: nothing else about the task is amiss.

    The file list was recorded and names a file, the kind of task is one the
    checks do look at, and every check is still absent. Only one thing
    explains that: the check did not run.
    """
    results = _kept_task_results(files=["src/users/service.py"], tracked=True)
    assert absence_reading(ANALYSER_DID_NOT_RUN, results)["state"] == STATE_NOT_CHECKED

    row = summarise_task(
        "TASK-DEMO-001", review_record=ANALYSER_DID_NOT_RUN, task_results=results
    )
    summary = build_code_checks_summary(
        feature_id="FEAT-DEMO", tasks=[row], groups=[]
    )
    assert all(
        check["state"] == STATE_NOT_CHECKED for check in row["checks"].values()
    )
    assert summary["tasks_with_something_not_checked"] == 1
    assert summary["tasks_not_checked"] == ["TASK-DEMO-001"]


def test_a_record_that_never_had_a_file_list_cannot_explain_an_absence() -> None:
    """Every task of the kept 19 September build is this shape."""
    reading = absence_reading(ANALYSER_DID_NOT_RUN, {"task_id": "TASK-001"})
    assert reading["state"] == STATE_NOT_CHECKED


def test_the_last_review_of_a_task_is_the_one_read(tmp_path: Path) -> None:
    """Turn 10 comes after turn 9, as a number and not as a word."""
    for turn in (1, 2, 9, 10):
        (tmp_path / f"coach_evidence_turn_{turn}.json").write_text(
            json.dumps({"turn": turn}), encoding="utf-8"
        )
    (tmp_path / "coach_evidence_turn_notanumber.json").write_text("{}", encoding="utf-8")

    found = latest_review_record(tmp_path)
    assert found is not None and found.name == "coach_evidence_turn_10.json"
    assert latest_review_record(tmp_path / "nothing-here") is None


# ---------------------------------------------------------------------------
# 3. The group rows
# ---------------------------------------------------------------------------


def test_a_group_the_gate_could_not_look_at_is_not_checked() -> None:
    row = group_record(
        3,
        state=STATE_NOT_CHECKED,
        reason="not checked: the builder's file list was not recorded",
        tasks_without_a_file_list=["TASK-002", "TASK-004"],
    )
    assert row["group"] == 3
    assert row["state"] == STATE_NOT_CHECKED
    assert row["tasks_without_a_file_list"] == ["TASK-002", "TASK-004"]
    assert row["finding_count"] == 0


def test_a_group_with_a_finding_names_it() -> None:
    row = group_record(4, state=STATE_FOUND_SOMETHING, findings=FINDING["findings"])
    assert row["finding_count"] == 1
    assert row["findings"][0]["name"] == "get_user_creation_counts_per_day"
    assert row["inputs_not_read"] is None


def test_a_group_check_that_read_only_part_of_its_input_says_how_much() -> None:
    """It ran and found nothing IN WHAT IT COULD READ. The rest is not that."""
    row = group_record(
        5,
        state=STATE_RAN_FOUND_NOTHING,
        reason="some of what it was given could not be read (2 of them)",
        inputs_not_read=2,
    )
    assert row["inputs_not_read"] == 2
    assert group_record(5, state=STATE_RAN_FOUND_NOTHING)["inputs_not_read"] is None


# ---------------------------------------------------------------------------
# 4. The whole summary, and the two acceptance cases
# ---------------------------------------------------------------------------


def _summary_from_kept_records() -> dict:
    """The 19 September shape: one task nothing looked at, one with a finding.

    The first task's record is the one the build really left: no entry at all
    under any check's name, and no file list to explain it. The second is that
    same build with its file list filled in, which is when the checks ran and
    named something. The third is a kind of task the checks never look at, and
    it must not be counted as unchecked.
    """
    tasks = [
        summarise_task(
            "TASK-DBE3-002",
            review_record=dict(ANALYSER_DID_NOT_RUN),
            task_results=_kept_task_results(files=None, tracked=False, shell=12),
        ),
        summarise_task(
            "TASK-DBE3-004",
            review_record={
                "wiring": FINDING,
                "mocked_seam": CLEAN,
                "stub_scan": CLEAN,
                "coverage": CLEAN,
            },
            task_results=_kept_task_results(
                files=["src/users/service.py"], tracked=True, shell=25
            ),
        ),
        summarise_task(
            "TASK-DBE3-005",
            review_record=dict(A_KIND_THE_CHECKS_SKIP),
            task_results=_kept_task_results(files=None, tracked=False),
        ),
    ]
    groups = [
        group_record(
            4,
            state=STATE_NOT_CHECKED,
            reason="not checked: the builder's file list was not recorded",
            tasks_without_a_file_list=["TASK-DBE3-002"],
        )
    ]
    return build_code_checks_summary(
        feature_id="FEAT-DBE3", tasks=tasks, groups=groups
    )


def test_a_named_finding_reaches_the_summary() -> None:
    """Acceptance case one: the wrong build with its file list filled in."""
    summary = _summary_from_kept_records()

    assert summary["finding_count"] == 1
    named = summary["tasks"][1]["checks"]["wiring"]["findings"][0]
    assert named["name"] == "get_user_creation_counts_per_day"
    assert named["file"] == "src/users/service.py"


def test_incomplete_checking_reaches_the_summary() -> None:
    """Acceptance case two: the wrong build exactly as it was kept."""
    summary = _summary_from_kept_records()

    assert summary["tasks_with_something_not_checked"] == 1
    assert summary["tasks_not_checked"] == ["TASK-DBE3-002"]
    assert summary["shell_command_count"] == 37
    assert summary["groups"][0]["state"] == STATE_NOT_CHECKED
    # And the thing that must never happen: nothing here reads as a pass.
    not_checked_task = summary["tasks"][0]
    assert all(
        check["state"] == STATE_NOT_CHECKED
        for check in not_checked_task["checks"].values()
    )
    # The kind of task the checks never look at is an honest absence, and it
    # is not counted as something nobody checked.
    skipped_kind = summary["tasks"][2]
    assert all(
        check["state"] == STATE_DOES_NOT_APPLY
        for check in skipped_kind["checks"].values()
    )


def test_the_summary_is_written_and_read_back(tmp_path: Path) -> None:
    path = write_code_checks_summary(_summary_from_kept_records(), tmp_path)
    assert path == tmp_path / SUMMARY_RELATIVE_PATH
    assert read_code_checks_summary(tmp_path)["feature"] == "FEAT-DBE3"
    assert read_code_checks_summary(tmp_path / "nothing-here") is None


def test_the_kept_review_is_read_in_the_layout_a_real_build_has(
    tmp_path: Path,
) -> None:
    """The blocker a second model found by driving, on 21 September.

    Every ``FEAT-*`` build works in a worktree, and the per-task review
    records are kept OUTSIDE that worktree on purpose. The summariser found
    each record, then asked for its path relative to the worktree — which
    cannot be made — and the error threw the record away, so every task of
    every real build came out "no review record of this task was kept". No
    finding could ever reach a card. Here the records sit exactly where a real
    build leaves them.
    """
    from types import SimpleNamespace

    from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

    worktree = tmp_path / ".guardkit" / "worktrees" / "FEAT-X"
    worktree.mkdir(parents=True)
    private = tmp_path / ".guardkit" / "autobuild-private" / "TASK-X-001"
    private.mkdir(parents=True)
    (private / "coach_evidence_turn_1.json").write_text(
        json.dumps({"task_type": "feature", "wiring": FINDING}), encoding="utf-8"
    )
    results = tmp_path / ".guardkit" / "autobuild" / "TASK-X-001"
    results.mkdir(parents=True)
    (results / "task_work_results.json").write_text(
        json.dumps(_kept_task_results(files=["src/users/service.py"], tracked=True)),
        encoding="utf-8",
    )

    orchestrator = object.__new__(FeatureOrchestrator)
    orchestrator.repo_root = tmp_path
    orchestrator._group_code_check_records = []
    written = orchestrator._write_code_checks_summary(
        SimpleNamespace(id="FEAT-X", tasks=[SimpleNamespace(id="TASK-X-001")]),
        SimpleNamespace(path=str(worktree)),
    )

    assert written == worktree / SUMMARY_RELATIVE_PATH
    row = json.loads(written.read_text())["tasks"][0]
    assert row["review_record_kept"] is True
    assert row["review_record"], "the summary says where the record is"
    assert row["checks"]["wiring"]["state"] == STATE_FOUND_SOMETHING
    assert (
        row["checks"]["wiring"]["findings"][0]["name"]
        == "get_user_creation_counts_per_day"
    )
    assert row["file_list_recorded"] is True


def test_nothing_in_here_ever_raises(tmp_path: Path) -> None:
    """A build is never failed by a summary of itself."""
    assert summarise_check(object())["state"] == STATE_NOT_CHECKED
    assert summarise_task("TASK-X", review_record="rubbish", task_results=7)
    assert build_code_checks_summary(feature_id="F", tasks=["rubbish"], groups=[8])
    unwritable = tmp_path / "a-file"
    unwritable.write_text("not a directory", encoding="utf-8")
    assert write_code_checks_summary({"a": 1}, unwritable) is None
    (tmp_path / SUMMARY_RELATIVE_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / SUMMARY_RELATIVE_PATH).write_text("{not json", encoding="utf-8")
    assert read_code_checks_summary(tmp_path) is None
