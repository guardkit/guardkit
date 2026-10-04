"""The short paragraph a finished build leaves in memory for later builds.

WHY THIS EXISTS (2026-10-04). A stored build outcome used to say only "AutoBuild
finished TASK-X in <working folder>: the coach approved the work after 1
turn(s)." Every later builder and reviewer searched memory with its task's
requirements text, and that sentence never scored close enough to pass the 0.5
line, against related and unrelated tasks alike. So memory was searched on
every turn and gave nothing back.

The facts a later builder needs were already in hand where the outcome is
written: the task's title, its feature, how it ended and why, what it was
asked to do, the files it changed and what the reviewer objected to. This
module writes those facts as one plain paragraph, at most 500 characters,
into the ``lessons`` field: the field the store searches and keeps.

Rules, all from the reviewed design and its measurement on real builds:

- Only facts already held at the seam. Nothing is guessed or added.
- The first paragraph of the requirements, at most 150 characters.
- Repository files only, at most five: absolute paths outside the working
  folder and ``.guardkit/`` paths are dropped.
- At most two distinct reviewer objections: the first line of each turn's
  feedback, at most 110 characters, with the turns it came up on.
- The failure reason at most 120 characters.
- The build's working folder is never named. Its prefix is taken off file
  names and objections, so no machine path is stored.
- A crash after an earlier outcome of the same build was recorded says which
  one it supersedes, in its own sentence, so the 120-character reason cap
  never cuts that off.

It is a pure function with no I/O, so the measurement scripts that justified
these limits can call this exact code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Sequence

MAX_PARAGRAPH_CHARS = 500
MAX_REQUIREMENTS_CHARS = 150
MAX_REASON_CHARS = 120
MAX_FILES = 5
MAX_OBJECTIONS = 2
MAX_OBJECTION_CHARS = 110


@dataclass(frozen=True)
class TurnFacts:
    """What one builder/reviewer turn left behind, as far as this paragraph cares."""

    turn: int
    files_changed: List[str] = field(default_factory=list)
    decision: Optional[str] = None
    feedback: Optional[str] = None


def turn_facts_from_record(record: Any) -> TurnFacts:
    """Read the parts of an orchestrator ``TurnRecord`` this paragraph uses.

    The builder's report names the files it modified and created; the turn
    record carries the reviewer's decision and feedback text.
    """
    player_result = getattr(record, "player_result", None)
    report = getattr(player_result, "report", None)
    if not isinstance(report, dict):
        report = {}
    files: List[str] = []
    for key in ("files_modified", "files_created"):
        value = report.get(key) or []
        if isinstance(value, (list, tuple)):
            files.extend(str(item) for item in value if isinstance(item, str))
    return TurnFacts(
        turn=getattr(record, "turn", 0),
        files_changed=files,
        decision=getattr(record, "decision", None),
        feedback=getattr(record, "feedback", None),
    )


def _strip_working_folders(text: str, working_folders: Sequence[str]) -> str:
    """Take every working-folder prefix off, so no machine path is stored.

    A folder matches only where its last path segment ends: "/x/build" is
    taken off "/x/build/a" (leaving "a") and stands alone as ".", but
    "/x/build-2/a" and "/x/build.v2" are other folders and are left alone.
    The longest folder goes first, so a worktree inside the repository is
    taken off whole rather than leaving its inner part behind.
    """
    folders = sorted(
        {str(folder).rstrip("/") for folder in working_folders} - {""},
        key=len,
        reverse=True,
    )
    for folder in folders:
        pattern = re.escape(folder) + r"(?:/|(?![\w-]|\.[\w-]))"
        text = re.sub(
            pattern, lambda m: "" if m.group(0).endswith("/") else ".", text
        )
    return text


def _first_paragraph(requirements: str) -> str:
    paragraph = requirements.strip().split("\n\n")[0].strip()
    return re.sub(r"\s+", " ", paragraph)[:300]


def _repository_files(turns: Sequence[TurnFacts], working_folders: Sequence[str]) -> List[str]:
    seen: List[str] = []
    for turn in turns:
        for name in turn.files_changed:
            name = _strip_working_folders(name, working_folders)
            if name.startswith("/") or name.startswith(".guardkit/") or name in seen:
                continue
            seen.append(name)
    return seen


def _objections(turns: Sequence[TurnFacts], working_folders: Sequence[str]) -> dict:
    """Each distinct objection's first line, with the turns it was raised on."""
    seen: dict = {}
    for turn in turns:
        if turn.decision != "feedback" or not turn.feedback:
            continue
        lines = [line.strip() for line in turn.feedback.split("\n") if line.strip()]
        if not lines:
            continue
        first = lines[0]
        if first.startswith("- "):
            first = first[2:].strip()
        first = _strip_working_folders(first, working_folders)[:MAX_OBJECTION_CHARS]
        seen.setdefault(first, []).append(turn.turn)
    return dict(list(seen.items())[:MAX_OBJECTIONS])


def compose_outcome_lessons(
    *,
    task_id: str,
    title: Optional[str],
    feature_id: Optional[str],
    success: bool,
    final_decision: str,
    error: Optional[str],
    requirements: Optional[str],
    turns: Iterable[TurnFacts],
    working_folders: Sequence[str] = (),
    supersedes: Optional[str] = None,
) -> str:
    """Write the outcome paragraph from the facts held when a build ends.

    Example (TASK-E592-002 as it would be stored):

        TASK-E592-002 "Implement analytics CRUD" (feature FEAT-E592): approved
        by the reviewer on turn 2. The task asked: Implement the database
        query for user creation counts. Files changed: src/users/__init__.py,
        src/users/analytics_crud.py. Reviewer objections: turn 1:
        Deterministic honesty record (...). Approved on turn 2 after these
        objections.
    """
    turns = list(turns)
    count = len(turns)
    title = (title or "").strip()
    head = task_id + (f' "{title}"' if title else "")
    if feature_id:
        head += f" (feature {feature_id})"

    if success:
        parts = [f"{head}: approved by the reviewer on turn {count}."]
    else:
        parts = [
            f"{head}: stopped without approval after {count} turn(s), "
            f'ending at "{final_decision}".'
        ]
        if supersedes:
            # A crash after an earlier terminal was already written down: two
            # records for one build, so this one says which it overtakes.
            parts.append(
                f'It crashed after the "{supersedes}" outcome had already been '
                "recorded, so this record supersedes that one."
            )
        if error:
            reason = _strip_working_folders(str(error), working_folders)
            parts.append(f"Reason: {reason[:MAX_REASON_CHARS]}")

    if requirements and requirements.strip():
        parts.append(
            f"The task asked: {_first_paragraph(requirements)[:MAX_REQUIREMENTS_CHARS]}"
        )

    files = _repository_files(turns, working_folders)
    if files:
        parts.append("Files changed: " + ", ".join(files[:MAX_FILES]) + ".")

    objections = _objections(turns, working_folders)
    if objections:
        parts.append(
            "Reviewer objections: "
            + "; ".join(
                f"turn {'/'.join(str(n) for n in raised_on)}: {text}"
                for text, raised_on in objections.items()
            )
            + "."
        )
        if success:
            parts.append(f"Approved on turn {count} after these objections.")

    return " ".join(parts)[:MAX_PARAGRAPH_CHARS]
