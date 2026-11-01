"""The reviewer is shown the feature's other tasks (experiment, 31 October 2026).

In a recorded experiment the reviewer sent back good builder turns for work the
feature's plan gives to a later task of the same feature ("no test runs this
code" when a later task wires the project's check). The look-up prompt now
carries, as plain information, each other task's ID, title, document path, file
lists and acceptance criteria (at most ``OTHER_TASKS_PROMPT_CHARS`` in all,
shared fairly), and one rule: work the plan gives to another task is not a
reason to send the turn back. Nothing here refuses or checks anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.orchestrator import build_review
from guardkit.orchestrator.agent_invoker import AgentInvoker

_PLANNED = "tasks/backlog/feat-x"


def _task(
    root: Path, folder: str, task_id: str, title: str, criteria: str, files: str = "- `src/a.go`"
) -> Path:
    path = root / folder / f"{task_id}-some-name.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {task_id}\ntitle: \"{title}\"\nfeature_id: FEAT-X1\n---\n\n"
        f"Do the thing.\n\n## Background\n\nLong story.\n\n"
        f"## Files to Modify\n\n{files}\n\n"
        f"## Acceptance Criteria\n\n{criteria}\n\n"
        "```sh\n# not a heading\n```\n\n"
        "## Implementation Notes\n\n- not shown\n",
        encoding="utf-8",
    )
    return path


def _feature(root: Path) -> None:
    for number, title in ((1, "Create the module"), (2, "Write the code"),
                          (3, "Wire the root check"), (10, "Tenth task")):
        _task(root, _PLANNED, f"TASK-X1-{number:03d}", title, f"- criterion of task {number}")
    # A stale copy in another folder; the plan names the backlog one.
    _task(root, "tasks/design_approved", "TASK-X1-003", "Stale copy", "- stale criterion")
    # Another feature's task and an ad-hoc file are left out.
    _task(root, "tasks/backlog", "TASK-Y2-001", "Other feature", "- not this feature")
    (root / "tasks" / "backlog" / "TASK-X1-README.md").write_text("notes\n")
    plan = root / ".guardkit" / "features" / "FEAT-X1.yaml"
    plan.parent.mkdir(parents=True)
    plan.write_text(
        "id: FEAT-X1\ntasks:\n"
        + "".join(
            f"  - id: TASK-X1-{n:03d}\n    file_path: \"{_PLANNED}/TASK-X1-{n:03d}-some-name.md\"\n"
            for n in (1, 2, 3, 10)
        ),
        encoding="utf-8",
    )


def _invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


def _verdict_prompt(worktree: Path, task_id: str) -> str:
    return _invoker(worktree)._build_coach_prompt(
        task_id, 1, "do the thing", {}, acceptance_criteria=None, evidence_bundle=None,
        gather_findings="NOT_TESTED scripts/check.sh:3: the check does not reach the package.",
    )


def _lookup_prompt(worktree: Path, task_id: str) -> str:
    return _invoker(worktree)._build_coach_gather_prompt(
        task_id=task_id, turn=1, requirements="do the thing", player_report={},
        evidence_bundle=None, acceptance_criteria=None,
        change=build_review.ReviewChange("", None, "a" * 40),
    )


def test_the_other_tasks_are_found_and_summarised_without_this_task(tmp_path: Path) -> None:
    _feature(tmp_path)
    tasks = build_review.other_tasks(tmp_path, "TASK-X1-002")
    assert [t.task_id for t in tasks] == ["TASK-X1-001", "TASK-X1-003", "TASK-X1-010"]
    wire = tasks[1]
    assert wire.title == "Wire the root check"
    assert wire.path == f"{_PLANNED}/TASK-X1-003-some-name.md"
    assert "**Files to Modify**" in wire.excerpt and "`src/a.go`" in wire.excerpt
    assert "**Acceptance Criteria**" in wire.excerpt
    assert "criterion of task 3" in wire.excerpt
    assert "# not a heading" in wire.excerpt
    # Only the file lists and the criteria are shown.
    assert "Long story" not in wire.excerpt and "not shown" not in wire.excerpt

    prompt = _lookup_prompt(tmp_path, "TASK-X1-002")
    assert "## The feature's other tasks" in prompt
    assert "This task is one of 4 in feature FEAT-X1." in prompt
    assert "### TASK-X1-003: Wire the root check" in prompt
    assert "criterion of task 2" not in prompt
    assert "stale criterion" not in prompt and "not this feature" not in prompt
    # The section comes before the five questions.
    assert prompt.index("## The feature's other tasks") < prompt.index("## The five questions")


def test_the_rule_is_in_the_instructions_when_other_tasks_are_shown(tmp_path: Path) -> None:
    _feature(tmp_path)
    prompt = " ".join(_lookup_prompt(tmp_path, "TASK-X1-001").split())
    assert (
        "Work the plan gives to another task of this feature (see \"The feature's other "
        "tasks\" above) is not a reason to send this turn back: do not report it as a "
        "finding, and if it matters, mention it as advice on a line that starts `ADVICE`."
    ) in prompt
    assert (
        "A test this task's own acceptance criteria require, which the builder could write "
        "within this task's own files, is still this turn's work."
    ) in prompt
    assert prompt.index("Answer these in order.") < prompt.index("Work the plan gives")
    assert prompt.index("Work the plan gives") < prompt.index("1. **Is every acceptance")


def test_the_other_tasks_are_cut_fairly_to_the_limit(tmp_path: Path) -> None:
    long = "\n".join(f"- criterion line {i} " + "x" * 80 for i in range(200))
    for number in (1, 2, 3):
        _task(tmp_path, "tasks/backlog", f"TASK-Z9-{number:03d}", f"Big {number}", long)
    _task(tmp_path, "tasks/backlog", "TASK-Z9-004", "Small", "- one short criterion")

    tasks = build_review.other_tasks(tmp_path, "TASK-Z9-005")
    section = build_review.render_other_tasks("TASK-Z9-005", tasks, limit=6_000)
    blocks = section.split("\n### ")[1:]
    assert len(blocks) == 4
    # The small task is whole; the big ones share the rest evenly and say so.
    assert "one short criterion" in blocks[3] and "[cut here" not in blocks[3]
    big = [len(b) for b in blocks[:3]]
    assert all("[cut here: the whole task is at the path above]" in b for b in blocks[:3])
    assert max(big) - min(big) < 100
    assert "Some are cut to fit" in section
    task_text = sum(len(b) for b in blocks)
    assert 5_000 < task_text <= 6_000 + 4 * len("### ")
    # The default limit bounds the whole section.
    full = build_review.render_other_tasks("TASK-Z9-005", tasks)
    assert len(full) < build_review.OTHER_TASKS_PROMPT_CHARS + 600


def test_no_other_task_adds_nothing(tmp_path: Path) -> None:
    baseline = _lookup_prompt(tmp_path, "TASK-X1-001")  # no tasks folder at all
    _task(tmp_path, "tasks/backlog", "TASK-X1-001", "Only task", "- alone")
    assert build_review.other_tasks(tmp_path, "TASK-X1-001") == []
    assert build_review.other_tasks_section(tmp_path, "TASK-X1-001") == ""
    assert build_review.other_tasks_section(None, "TASK-X1-001") == ""
    # A task ID without a feature part finds nothing and raises nothing.
    assert build_review.other_tasks(tmp_path, "TASK-FIX-GCW5") == []
    prompt = _lookup_prompt(tmp_path, "TASK-X1-001")
    assert prompt == baseline
    assert "The feature's other tasks" not in prompt
    assert "Work the plan gives" not in prompt


@pytest.mark.parametrize("contract", ["v4", "coachsplit"])
def test_the_verdict_call_is_given_the_other_tasks_and_the_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contract: str
) -> None:
    """The verdict call may add NOT_TESTED from the check result on its own,
    so it is given the same section and the rule; with no other task its
    prompt is unchanged."""
    monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", contract)
    baseline = _verdict_prompt(tmp_path / "empty", "TASK-X1-001")
    assert "The feature's other tasks" not in baseline
    assert "Work the plan gives" not in baseline

    _feature(tmp_path)
    prompt = _verdict_prompt(tmp_path, "TASK-X1-001")
    assert "## The feature's other tasks" in prompt
    assert "### TASK-X1-003: Wire the root check" in prompt
    flat = " ".join(prompt.split())
    assert (
        "do not keep or add a finding for it, including `NOT_TESTED` because the "
        "project's check does not yet reach this task's code (for example it says "
        "\"no parts yet\") when another task of this feature wires the check in."
    ) in flat
    assert (
        "A test this task's own acceptance criteria require, which the builder could write "
        "within this task's own files, is still this turn's work."
    ) in flat
    # The section after the look-up findings, the rule after the instructions
    # and before the decision format.
    assert prompt.index("## Look-up findings") < prompt.index("## The feature's other tasks")
    assert prompt.index("## The feature's other tasks") < prompt.index("## Your Responsibilities")
    assert prompt.index("## Your Responsibilities") < prompt.index("Work the plan gives")
    assert prompt.index("Work the plan gives") < prompt.index("## Decision Format")

    # Removing the other tasks gives back the unchanged prompt.
    for path in (tmp_path / "tasks").rglob("TASK-X1-*.md"):
        if not path.name.startswith("TASK-X1-001-"):
            path.unlink()
    assert _verdict_prompt(tmp_path, "TASK-X1-001") == baseline
