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


def test_a_check_with_nothing_to_do_does_not_apply() -> None:
    assert summarise_check(None)["state"] == STATE_DOES_NOT_APPLY
    assert (
        summarise_check({"status": "skipped_no_targets", "findings": []})["state"]
        == STATE_DOES_NOT_APPLY
    )


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


def test_a_check_absent_from_a_kept_review_does_not_apply() -> None:
    row = summarise_task(
        "TASK-001", review_record={"wiring": CLEAN}, task_results=None
    )
    assert row["checks"]["wiring"]["state"] == STATE_RAN_FOUND_NOTHING
    assert row["checks"]["stub_scan"]["state"] == STATE_DOES_NOT_APPLY


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


# ---------------------------------------------------------------------------
# 4. The whole summary, and the two acceptance cases
# ---------------------------------------------------------------------------


def _summary_from_kept_records() -> dict:
    """The 19 September shape: two tasks nothing looked at, one with a finding."""
    tasks = [
        summarise_task(
            "TASK-DBE3-002",
            review_record={name: NOT_CHECKED for name in CHECK_NAMES},
            task_results=_kept_task_results(files=[], tracked=False, shell=12),
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


def test_the_summary_is_written_and_read_back(tmp_path: Path) -> None:
    path = write_code_checks_summary(_summary_from_kept_records(), tmp_path)
    assert path == tmp_path / SUMMARY_RELATIVE_PATH
    assert read_code_checks_summary(tmp_path)["feature"] == "FEAT-DBE3"
    assert read_code_checks_summary(tmp_path / "nothing-here") is None


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
