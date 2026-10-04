"""The outcome paragraph a finished build leaves in memory (2026-10-04).

The paragraph is built only from facts held when a build ends, and is capped
so that two to four earlier outcomes fit in a later turn's share of the
prompt. These tests pin the rules from the reviewed design.
"""

from __future__ import annotations

from types import SimpleNamespace

from guardkit.orchestrator.outcome_lessons import (
    MAX_PARAGRAPH_CHARS,
    TurnFacts,
    compose_outcome_lessons,
    turn_facts_from_record,
)

WORKTREE = "/srv/build/worktrees/FEAT-AB12"


def _compose(**overrides):
    facts = dict(
        task_id="TASK-AB12-002",
        title="Implement analytics CRUD",
        feature_id="FEAT-AB12",
        success=True,
        final_decision="approved",
        error=None,
        requirements="Implement the database query for user creation counts.\n\nMore detail.",
        turns=[TurnFacts(turn=1, files_changed=["src/users/crud.py"], decision="approve")],
        working_folders=(WORKTREE,),
    )
    facts.update(overrides)
    return compose_outcome_lessons(**facts)


def test_approved_on_turn_one():
    text = _compose()
    assert text == (
        'TASK-AB12-002 "Implement analytics CRUD" (feature FEAT-AB12): approved '
        "by the reviewer on turn 1. The task asked: Implement the database query "
        "for user creation counts. Files changed: src/users/crud.py."
    )


def test_approved_after_objections_merges_repeats():
    scratch = "- Player claimed file /tmp/verify.py. Actual: path absent\n- second issue"
    turns = [
        TurnFacts(1, ["src/a.py"], "feedback", scratch),
        TurnFacts(2, ["src/a.py"], "feedback", scratch),
        TurnFacts(3, ["src/b.py"], "approve", None),
    ]
    text = _compose(turns=turns)
    assert "approved by the reviewer on turn 3." in text
    assert "Files changed: src/a.py, src/b.py." in text
    # The same objection on two turns is named once, with both turns.
    assert "Reviewer objections: turn 1/2: Player claimed file /tmp/verify.py." in text
    assert text.count("Player claimed file") == 1
    assert "second issue" not in text  # only the first line of each turn
    assert text.endswith("Approved on turn 3 after these objections.")


def test_failed_with_a_reason():
    text = _compose(
        success=False,
        final_decision="unrecoverable_stall",
        error="Unrecoverable stall detected after 2 turn(s). " + "x" * 300,
        turns=[TurnFacts(1), TurnFacts(2)],
    )
    assert text.startswith(
        'TASK-AB12-002 "Implement analytics CRUD" (feature FEAT-AB12): stopped '
        'without approval after 2 turn(s), ending at "unrecoverable_stall". '
        "Reason: Unrecoverable stall detected after 2 turn(s)."
    )
    reason = text.split("Reason: ", 1)[1].split(" The task asked:")[0]
    assert len(reason) == 120
    assert "Approved on turn" not in text


def test_no_turns_at_all():
    text = _compose(
        success=False, final_decision="pre_loop_blocked", error=None, turns=[]
    )
    assert 'stopped without approval after 0 turn(s), ending at "pre_loop_blocked".' in text
    assert "Files changed" not in text
    assert "Reviewer objections" not in text


def test_cap_five_files_and_two_objections():
    turns = [
        TurnFacts(n, [f"src/file_{n}_{k}.py" for k in range(3)], "feedback", f"- objection {n} " + "y" * 200)
        for n in range(1, 5)
    ]
    text = _compose(turns=turns, requirements="")
    files = text.split("Files changed: ", 1)[1].split(".py.", 1)[0] + ".py"
    assert len(files.split(", ")) == 5
    assert "objection 1" in text and "objection 2" in text
    assert "objection 3" not in text
    assert len(text) <= MAX_PARAGRAPH_CHARS
    # Each objection line is cut to 110 characters.
    first = text.split("turn 1: ", 1)[1].split("; turn 2:", 1)[0]
    assert len(first) == 110


def test_whole_paragraph_is_capped_at_500():
    text = _compose(
        title="T" * 400,
        requirements="R" * 400,
        turns=[TurnFacts(1, ["src/" + "z" * 200 + ".py"], "approve")],
    )
    assert len(text) == MAX_PARAGRAPH_CHARS


def test_paths_outside_the_repository_are_dropped_and_working_folder_stripped():
    turns = [
        TurnFacts(
            1,
            [
                "/tmp/verify_e592.py",
                ".guardkit/autobuild/TASK-AB12-002/notes.md",
                f"{WORKTREE}/src/users/router.py",
                "src/users/router.py",
            ],
            "feedback",
            f"- Coverage failed in {WORKTREE}/src/users/router.py at line 4",
        ),
    ]
    text = _compose(
        turns=turns,
        success=False,
        final_decision="timeout",
        error=f"Command failed in {WORKTREE}",
    )
    assert "Files changed: src/users/router.py." in text
    assert "/tmp/verify_e592.py" not in text.split("Reviewer objections")[0]
    assert ".guardkit/" not in text
    assert WORKTREE not in text
    assert "/srv/build" not in text
    assert "Coverage failed in src/users/router.py at line 4" in text


def test_missing_title_falls_back_to_the_task_id():
    text = _compose(title=None)
    assert text.startswith("TASK-AB12-002 (feature FEAT-AB12): approved")
    assert '""' not in text


def test_empty_requirements_give_no_task_asked_sentence():
    assert "The task asked" not in _compose(requirements="")
    assert "The task asked" not in _compose(requirements="   \n  ")
    assert "The task asked" not in _compose(requirements=None)


def test_only_the_first_paragraph_of_the_requirements_up_to_150_characters():
    text = _compose(requirements="First   line\nstill first.\n\nSecond paragraph.")
    assert "The task asked: First line still first." in text
    assert "Second paragraph" not in text
    long = _compose(requirements="w" * 400)
    asked = long.split("The task asked: ", 1)[1].split(" Files changed:")[0]
    assert len(asked) == 150


def test_no_invented_fields():
    """Every word comes from the facts given: nothing about the folder, the
    approach, tests or anything else that was not handed in."""
    text = _compose(requirements="", turns=[TurnFacts(1, [], "approve")])
    assert text == (
        'TASK-AB12-002 "Implement analytics CRUD" (feature FEAT-AB12): approved '
        "by the reviewer on turn 1."
    )


def test_a_crash_names_the_outcome_it_supersedes():
    text = _compose(
        success=False,
        final_decision="crashed",
        error="Orchestration crashed: RuntimeError: finalize blew up",
        supersedes="qa_precondition_blocked",
        turns=[],
    )
    assert (
        'It crashed after the "qa_precondition_blocked" outcome had already been '
        "recorded, so this record supersedes that one."
    ) in text
    assert "Reason: Orchestration crashed: RuntimeError: finalize blew up" in text


def test_turn_facts_are_read_from_an_orchestrator_turn_record():
    record = SimpleNamespace(
        turn=2,
        player_result=SimpleNamespace(
            report={"files_modified": ["src/a.py"], "files_created": ["src/b.py"]}
        ),
        decision="feedback",
        feedback="- add tests",
    )
    facts = turn_facts_from_record(record)
    assert facts == TurnFacts(2, ["src/a.py", "src/b.py"], "feedback", "- add tests")


def test_turn_record_without_a_report_gives_no_files():
    record = SimpleNamespace(turn=1, player_result=None, decision="error", feedback=None)
    assert turn_facts_from_record(record).files_changed == []
