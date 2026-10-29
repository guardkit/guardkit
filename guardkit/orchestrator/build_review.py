"""The build reviewer checks the change against the code (29 October 2026).

Rich, 29 October 2026: "I expect it's more of a 'paperwork' reviewer than an
actual coach reviewing what has been implemented", then "please proceed with
rebuilding the builder coach reviewer as per your plan" (the build reviewer
design of 29 October 2026).

The reviewer used to be one model call with no tools that read the project's
documents in full and the builder's own report, and never the change. Now:

1. A read-only look-up pass (``AgentInvoker._invoke_coach_gather``) is given
   the change itself, computed here by git from the task's starting commit,
   and answers five questions against the change and the code, each finding
   with ``path:line``. Its tools only read (no shell: the project's check has
   already run and its result is in the input) and are bounded by the shared
   tool limit (40 tool-using model turns, then an answer).
2. A smaller verdict call turns those findings into issues that carry their
   pattern and location.
3. Located findings of the five kinds get ONE repair turn: they become the
   builder's next-turn feedback, the next review checks them first, and after
   that the turn is approved whatever remains. Nothing is refused on a
   reviewer finding. ``GUARDKIT_REVIEW_REPAIR_TURN=0`` turns the repair turn
   off.
4. What the final review leaves (at most ten findings) is written to the
   feature's build review notes, which Forge shows on the merge card as
   advice.

Everything here is plain code: no model is called from this module.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

#: The five questions' findings. A located one (``path:line``) gets the repair
#: turn; every one left at the end is advice on the merge card.
FINDING_PATTERNS: tuple[str, ...] = (
    "NOT_IMPLEMENTED",
    "NOT_TESTED",
    "CALLERS_NOT_UPDATED",
    "STUB",
    "OUTSIDE_TASK",
)
#: Advice only, never sent back: a criterion that conflicts with a project
#: document.
ADVICE_PATTERNS: tuple[str, ...] = ("CRITERION_CONFLICT",)

#: The look-up pass's tool request: read and search only, so the harness
#: builds its read-only graph (read_file, ls, grep, glob and the code tools).
LOOKUP_TOOLS: tuple[str, ...] = ("Read", "Search", "Grep", "Glob")

#: How much of the change goes into the look-up prompt; the whole change is
#: written where the reviewer can read it.
DIFF_PROMPT_CHARS = 40_000

#: Findings written to the build review notes for the merge card.
MAX_LEFTOVERS = 10

#: The setting that turns the repair turn off (the replay's "off" arm and the
#: way back).
REPAIR_TURN_ENV = "GUARDKIT_REVIEW_REPAIR_TURN"
_OFF_VALUES = frozenset({"0", "false", "no", "off"})

#: Keys on the reviewer's record (``coach_turn_N.json``).
REPAIR_KEY = "review_repair"
LEFTOVERS_KEY = "review_leftovers"

#: The feature's build review notes, beside the code-checks summary, in the
#: folder the runner exports.
NOTES_RELATIVE_PATH = Path(".guardkit") / "autobuild-private" / "build_review_notes.json"

_LOCATION = re.compile(r"\S+:\d+")
_COACH_TURN_FILE = re.compile(r"^coach_turn_(\d+)\.json$")


def repair_turn_enabled() -> bool:
    """Whether a located finding gets the one repair turn (on unless set off)."""
    raw = os.environ.get(REPAIR_TURN_ENV)
    return raw is None or raw.strip().lower() not in _OFF_VALUES


# ---------------------------------------------------------------------------
# The change, from git
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewChange:
    """The change the reviewer is shown.

    ``text`` is the whole diff (empty when it could not be made), ``path``
    where the whole diff was written (``None`` when it was not), ``note`` a
    plain sentence when either failed.
    """

    text: str
    path: Optional[Path]
    base: Optional[str]
    note: str = ""


def change_since(worktree: Path, base: str) -> str:
    """``git diff --find-renames`` from ``base`` to the worktree as it is now.

    Tracked and untracked files are both included (ignored ones are not),
    through a TEMPORARY index, so the worktree's own index is never written.
    GuardKit's own records are left out, as the checkpoint commit leaves them
    out. Raises ``RuntimeError`` with a plain sentence when git fails.
    """
    from guardkit.lib.project_git import run_git
    from guardkit.orchestrator.worktree_checkpoints import CHECKPOINT_EXCLUDE_PATHSPECS

    worktree = Path(worktree)
    scratch = Path(tempfile.mkdtemp(prefix="guardkit-review-index-"))
    try:
        index = scratch / "index"
        found = run_git(["-C", str(worktree), "rev-parse", "--git-path", "index"], timeout=30)
        if found.returncode == 0:
            real = Path(found.stdout.strip())
            if not real.is_absolute():
                real = worktree / real
            if real.is_file():
                # A copy only so git can skip re-reading unchanged files; the
                # real index is read, never written.
                shutil.copyfile(real, index)
        env = {"GIT_INDEX_FILE": str(index)}
        add = run_git(
            ["-C", str(worktree), "add", "-A", "--", ".", *CHECKPOINT_EXCLUDE_PATHSPECS],
            env=env,
            timeout=120,
        )
        if add.returncode != 0:
            raise RuntimeError("git add into a temporary index failed")
        diff = run_git(
            [
                "-C", str(worktree), "diff", "--cached", "--find-renames",
                "--no-color", "--no-ext-diff", base, "--", ".",
                *CHECKPOINT_EXCLUDE_PATHSPECS,
            ],
            env=env,
            timeout=120,
        )
        if diff.returncode != 0:
            raise RuntimeError(f"git diff from {base[:12]} failed")
        return str(diff.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def diff_path(task_id: str, turn: int, worktree: Path) -> Path:
    """Where the whole diff of a review is written.

    The task's private folder (``TaskArtifactPaths.private_artifact_path``):
    for a build worktree it is outside the worktree, in the main checkout's
    ``.guardkit/autobuild-private``, so no checkpoint commit can take it; for
    a run in the repository itself it is inside, in a folder the checkpoint
    commit always leaves out. The reviewer's read-only backend reads absolute
    paths as they are (only writes are confined), so its ``read_file``
    reaches it either way.
    """
    from guardkit.orchestrator.paths import TaskArtifactPaths

    return TaskArtifactPaths.private_artifact_path(
        task_id, f"review_diff_turn_{turn}.diff", Path(worktree)
    )


def write_change(task_id: str, turn: int, worktree: Path, base: Optional[str]) -> ReviewChange:
    """The change for this review, written whole beside the review. Never raises."""
    if not base:
        return ReviewChange(
            "", None, None,
            "The task's starting commit is not known, so the change could not be shown.",
        )
    try:
        text = change_since(Path(worktree), base)
    except Exception as exc:  # noqa: BLE001 — the review goes on without it
        logger.warning("[%s] Turn %s: the change could not be read: %s", task_id, turn, exc)
        return ReviewChange("", None, base, f"The change could not be read ({exc}).")
    path = diff_path(task_id, turn, Path(worktree))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — the prompt still carries its part
        logger.warning("[%s] Turn %s: the change could not be written: %s", task_id, turn, exc)
        return ReviewChange(text, None, base, f"The whole change could not be written ({exc}).")
    return ReviewChange(text, path, base)


# ---------------------------------------------------------------------------
# The look-up prompt
# ---------------------------------------------------------------------------


def _change_section(change: ReviewChange) -> str:
    lines = ["## The change", ""]
    if not change.text:
        if change.note:
            lines.append(change.note)
        else:
            lines.append(
                f"The builder changed nothing since the task's starting commit "
                f"({(change.base or '')[:12]})."
            )
        lines.append(
            "Read the files the builder's file lists name, and look up the rest."
        )
        return "\n".join(lines)
    shown = change.text[:DIFF_PROMPT_CHARS]
    lines.append(
        f"What changed from the task's starting commit ({(change.base or '')[:12]}) to the "
        "builder's work now, by git (`git diff --find-renames`): deletions and renames are "
        "included, so a removed or renamed name shows here with its old spelling."
    )
    if change.path is not None:
        if len(change.text) > len(shown):
            lines.append(
                f"It is cut here at {len(shown):,} of {len(change.text):,} characters. The "
                f"whole change is in {change.path}: read the rest with read_file, using "
                "offset and limit to page through it."
            )
        else:
            lines.append(f"The same change is in {change.path}.")
    elif len(change.text) > len(shown):
        lines.append(
            f"It is cut here at {len(shown):,} of {len(change.text):,} characters "
            f"({change.note or 'the whole change could not be written'}); read the "
            "files it names for the rest."
        )
    lines.extend(["", "```diff", shown.rstrip("\n"), "```"])
    return "\n".join(lines)


def _builder_notes(player_report: Dict[str, Any]) -> Dict[str, Any]:
    """The builder's concerns, what it says remains, and git's file lists."""
    notes: Dict[str, Any] = {}
    for key in (
        "concerns",
        "requirements_remaining",
        "files_created",
        "files_modified",
    ):
        value = (player_report or {}).get(key)
        if value:
            notes[key] = value
    return notes


def render_builder_notes(player_report: Dict[str, Any]) -> str:
    """The builder's notes as JSON, or a plain sentence when there are none."""
    notes = _builder_notes(player_report)
    if not notes:
        return "The builder's report has no concerns, nothing remaining and no file lists."
    return json.dumps(notes, indent=2)


def _finding_line(finding: Dict[str, Any]) -> str:
    pattern = str(finding.get("pattern") or "").strip()
    location = str(finding.get("location") or "").strip()
    description = str(finding.get("description") or "").strip()
    return f"- {pattern} {location}: {description}".rstrip()


def build_lookup_prompt(
    *,
    task_id: str,
    turn: int,
    requirements: str,
    acceptance_criteria: Optional[Sequence[Dict[str, str]]],
    change: ReviewChange,
    check_section: str,
    player_report: Dict[str, Any],
    sent_back: Sequence[Dict[str, Any]] = (),
    document_paths: Sequence[str] = (),
) -> str:
    """The look-up pass's prompt: the task, the change, the check, the
    builder's notes, and the five questions."""
    criteria = ""
    if acceptance_criteria:
        criteria = "\n## Acceptance criteria\n\n" + "\n".join(
            f"- **{c['id']}**: {c['text']}" for c in acceptance_criteria
        ) + "\n"
    repair = ""
    if sent_back:
        repair = (
            "\n## Findings the builder was sent back to fix\n\n"
            "Check each of these first. Report again any that is not fixed, with its place "
            "in the code now; do not report one that is fixed.\n\n"
            + "\n".join(_finding_line(f) for f in sent_back)
            + "\n"
        )
    documents = ""
    if document_paths:
        documents = (
            "\n## The project's documents\n\n"
            "The project declares these documents. Read the part of one a question needs; "
            "do not read them all.\n\n"
            + "\n".join(f"- {path}" for path in document_paths)
            + "\n"
        )
    return f"""You review one builder turn of a software task before it is accepted. You do not change \
anything: you look up what the five questions below need, in the change and the code, and report \
what is wrong, so the builder can fix it once and the person approving the build can see what is left.

Task ID: {task_id}
Turn: {turn}

## The task

{requirements}
{criteria}
{_change_section(change)}

## The project's check

The project's own check has already run on this turn's code; its result is below. Where its output \
says "no parts yet", or it ran no test, the check tested nothing.

{check_section or "No check result was recorded for this turn."}

## The builder's notes

Its concerns, what it says remains, and the files git saw it create and change:

{render_builder_notes(player_report)}
{repair}{documents}
## The five questions

Answer these in order. Each names the finding you report when the answer is no.

1. **Is every acceptance criterion done?** Find the code that does each one. When none does, \
report `NOT_IMPLEMENTED`.
2. **Is each criterion tested, by a test the project's check runs?** Find the test that exercises \
it and check the project's check runs that test. When no test does, or the check does not run it \
(its output above says what ran), report `NOT_TESTED`. When the project's check (the declared \
test command and any script it calls, for example scripts/check.sh) does not reach the folder this \
task changed, report `NOT_TESTED` at the line of the check file that should reach it, so the builder \
wires it in.
3. **Were the callers and tests updated?** For each function, type, field, route or setting the \
change changes, renames or removes, find what uses it, by its old name too. When a caller or test \
was not changed to match, report `CALLERS_NOT_UPDATED`.
4. **Is anything a stub?** A placeholder, a hard-coded answer, a test that skips itself, or an \
error swallowed in the change: report `STUB`.
5. **Is anything outside the task?** A change the task does not ask for and the builder gave no \
reason for (base images, deploy files, CI, work the plan put off): report `OUTSIDE_TASK`.

These are not findings: that something was "not independently verified"; a missing receipt or \
evidence file; the builder's report and its bookkeeping; a protected file the builder rightly left \
alone. When an acceptance criterion conflicts with a project document, report it once as \
`CRITERION_CONFLICT`: it is advice, never sent back.

## How to look things up

Your tools only read the task's worktree as it is now (read_file, ls, grep, glob, code_search, \
code_outline, code_pattern, and code_references when offered). There is no shell: the project's \
check has already run.

- Look up only what one of the five questions needs. Do not explore.
- Never make the same call twice. If an answer was empty, check it once another way.
- `code_references` finds every use of a name as the compiler sees it. 'unsupported' or \
'tool_error' is not evidence of no uses: use code_search in literal mode.
- There is a limit on tool calls. When it is reached the tools are taken away and you are asked \
for your answer: give it from what you have found.

## Your answer

Plain text, one line per finding, each with its place in the code and one plain sentence:

PATTERN path/to/file:line: what is wrong, and what the task or the code says instead.

Report each problem once. When the five questions find nothing, write NO FINDINGS. Do not write a \
JSON verdict: a second step writes it from your lines.
"""


# ---------------------------------------------------------------------------
# Findings from the verdict
# ---------------------------------------------------------------------------


_WRITTEN_FINDING = re.compile(
    r"^\s*(?P<pattern>[A-Z_]+)\s+(?P<location>\S+:\d+)\s*:?\s*(?P<text>.*)$", re.S
)


def _normalised(issue: Any) -> Any:
    """An issue with its pattern and location, read from a description
    written as ``PATTERN path:line: sentence`` when it has no ``pattern`` (the
    v4 contract's findings carry only that text)."""
    if not isinstance(issue, dict) or issue.get("pattern"):
        return issue
    match = _WRITTEN_FINDING.match(str(issue.get("description") or ""))
    if match is None or match.group("pattern") not in FINDING_PATTERNS + ADVICE_PATTERNS:
        return issue
    return {
        **issue,
        "pattern": match.group("pattern"),
        "location": issue.get("location") or match.group("location"),
        "description": match.group("text").strip(),
    }


def _pattern_of(issue: Dict[str, Any]) -> str:
    return str(issue.get("pattern") or "").strip().upper()


def is_located(issue: Any) -> bool:
    """A finding of the five kinds with a ``path:line`` place."""
    issue = _normalised(issue)
    return (
        isinstance(issue, dict)
        and _pattern_of(issue) in FINDING_PATTERNS
        and bool(_LOCATION.search(str(issue.get("location") or "")))
    )


def located_findings(issues: Iterable[Any]) -> List[Dict[str, Any]]:
    """The verdict's located findings of the five kinds, in its order."""
    return [dict(_normalised(issue)) for issue in issues if is_located(issue)]


def _note(issue: Dict[str, Any]) -> Dict[str, str]:
    return {
        "pattern": _pattern_of(issue),
        "location": str(issue.get("location") or "").strip(),
        "description": str(issue.get("description") or "").strip(),
    }


def leftovers(issues: Iterable[Any]) -> List[Dict[str, str]]:
    """What a final review leaves for the merge card: its findings of the five
    kinds and its advice, at most :data:`MAX_LEFTOVERS`."""
    kept = [
        _note(issue)
        for issue in map(_normalised, issues)
        if isinstance(issue, dict)
        and _pattern_of(issue) in FINDING_PATTERNS + ADVICE_PATTERNS
    ]
    return kept[:MAX_LEFTOVERS]


def repair_issues(findings: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The located findings as the builder's next-turn feedback issues."""
    issues = []
    for finding in findings:
        note = _note(finding)
        issue: Dict[str, Any] = {
            "type": "review_finding",
            "severity": "major",
            "pattern": note["pattern"],
            "location": note["location"],
            "description": f"{note['pattern']} at {note['location']}: {note['description']}",
        }
        suggestion = str(finding.get("suggestion") or "").strip()
        if suggestion:
            issue["suggestion"] = suggestion
        issues.append(issue)
    return issues


# ---------------------------------------------------------------------------
# The feature's build review notes
# ---------------------------------------------------------------------------


def repair_findings_sent(task_private_dir: Path, before_turn: int) -> Optional[List[Dict[str, Any]]]:
    """The findings an earlier review of this task sent back for its repair
    turn, read from the task's own records, or ``None`` when none did.

    Codex review R2 (29 October 2026): the "one repair turn" limit must hold
    across a resume, so it is read from the reviews this task has recorded
    (``coach_turn_N.json`` with ``review_repair`` set), not only from the
    process's memory. Only turns before ``before_turn`` are read: those
    records are this build's own (each turn writes its own record over any
    older one of the same number). Never raises.
    """
    try:
        for path in sorted(Path(task_private_dir).glob("coach_turn_*.json")):
            match = _COACH_TURN_FILE.match(path.name)
            if match is None or int(match.group(1)) >= before_turn:
                continue
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(record, dict) and record.get(REPAIR_KEY) is True:
                issues = record.get("issues")
                found = []
                for issue in issues if isinstance(issues, list) else []:
                    if not (isinstance(issue, dict) and is_located(issue)):
                        continue
                    note = _note(issue)
                    # repair_issues wrote "PATTERN at place: sentence".
                    note["description"] = note["description"].removeprefix(
                        f"{note['pattern']} at {note['location']}: "
                    )
                    found.append(note)
                return found
    except Exception as exc:  # noqa: BLE001
        logger.debug("No repair record read in %s: %s", task_private_dir, exc)
    return None


def latest_review(task_private_dir: Path) -> Optional[Path]:
    """The task's last ``coach_turn_N.json``, or ``None``. Never raises."""
    best: Optional[Path] = None
    best_turn = -1
    try:
        for path in Path(task_private_dir).glob("coach_turn_*.json"):
            match = _COACH_TURN_FILE.match(path.name)
            if match and int(match.group(1)) > best_turn:
                best_turn, best = int(match.group(1)), path
    except Exception as exc:  # noqa: BLE001
        logger.debug("build review notes: no review found in %s: %s", task_private_dir, exc)
    return best


def write_feature_notes(
    feature_id: str, task_ids: Sequence[str], root: Path
) -> Optional[Path]:
    """Write what each task's final review left, at most ten in all. Never raises.

    Into ``<root>/.guardkit/autobuild-private/build_review_notes.json``,
    beside the code-checks summary, where the runner exports it for Forge's
    merge card.
    """
    try:
        from guardkit.orchestrator.paths import TaskArtifactPaths

        notes: List[Dict[str, str]] = []
        total = 0
        for task_id in task_ids:
            found = latest_review(TaskArtifactPaths.task_private_dir(task_id, Path(root)))
            if found is None:
                continue
            try:
                record = json.loads(found.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            left = record.get(LEFTOVERS_KEY) if isinstance(record, dict) else None
            if not isinstance(left, list):
                continue
            for item in left:
                if not isinstance(item, dict):
                    continue
                total += 1
                if len(notes) < MAX_LEFTOVERS:
                    notes.append({"task_id": task_id, **{k: str(v) for k, v in item.items()}})
        path = Path(root) / NOTES_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"feature": feature_id, "notes": notes, "total": total}, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
        return path
    except Exception as exc:  # noqa: BLE001 — notes never fail a build
        logger.warning("The build review notes could not be written: %s", exc)
        return None


__all__ = [
    "ADVICE_PATTERNS",
    "DIFF_PROMPT_CHARS",
    "FINDING_PATTERNS",
    "LEFTOVERS_KEY",
    "LOOKUP_TOOLS",
    "MAX_LEFTOVERS",
    "NOTES_RELATIVE_PATH",
    "REPAIR_KEY",
    "REPAIR_TURN_ENV",
    "ReviewChange",
    "build_lookup_prompt",
    "change_since",
    "diff_path",
    "is_located",
    "latest_review",
    "leftovers",
    "located_findings",
    "render_builder_notes",
    "repair_findings_sent",
    "repair_issues",
    "repair_turn_enabled",
    "write_change",
    "write_feature_notes",
]
