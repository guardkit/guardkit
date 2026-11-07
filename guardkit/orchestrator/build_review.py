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
5. When every task completed, one last look (the same look-up pass and
   verdict, over the feature's whole change) checks those notes again
   against the finished code. Notes it reports again stay on the card; the
   others are only counted (Rich, 3 November 2026, decision 5).

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
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

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

#: How many notes the last look found no longer apply, and how many stay.
RECHECKED_KEY = "rechecked"

#: What runs at merge. The last look says it, and since 6 November 2026 so
#: does the per-task review's look-up (b1's stage-checks experiment: good turns
#: wrongly sent back fell from 11 of 12 to 6 of 12, with the same catches).
MERGE_CHECK_RULE = (
    "The project's full check (every part, and the root's own lint, format and "
    "type checks) runs once before the feature merges, not after each task, and "
    "the feature merges only when it passes: a check that only the full check runs "
    "is not missing, though an error you can see in the code still is."
)

#: The whole last look's time, fixed: with a task review's limits its two
#: calls and the verdict's retry could add over an hour to a feature. When it
#: runs out the notes stay as they were. 1800 s since 6 November 2026: the
#: look-up's 900 s plus the half again its answer gets (08e6eead) must fit.
LAST_LOOK_TIMEOUT_SECONDS = 1800

#: The last look's look-up pass gets most of that time: its answer usually
#: needs no verdict call. Out of a task review's slice (40% of its limit),
#: FEAT-FF29's look-up spent 590 s on look-ups and had too little left to
#: write its answer (replay, 5 November 2026).
LAST_LOOK_LOOKUP_SECONDS = 900

#: Whether a build runs the last look. Off until its replay keeps the true
#: notes: on 5 November 2026 it dropped 26 of 120 true notes across five
#: recorded cards and two versions, and only 8 of 42 notes that no longer
#: applied. The replay calls ``FeatureOrchestrator._last_look`` itself.
LAST_LOOK_IN_BUILDS = False

#: The look-up pass's instruction for findings it is asked to check again.
RECHECK_SENTENCE = (
    "Check each of these first. Report again any that is not fixed, with its place "
    "in the code now; do not report one that is fixed."
)

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


def _change_section(change: ReviewChange, whose: str = "task") -> str:
    lines = ["## The change", ""]
    if not change.text:
        if change.note:
            lines.append(change.note)
        else:
            lines.append(
                f"The builder changed nothing since the {whose}'s starting commit "
                f"({(change.base or '')[:12]})."
            )
        lines.append(
            "Read the files the builder's file lists name, and look up the rest."
        )
        return "\n".join(lines)
    shown = change.text[:DIFF_PROMPT_CHARS]
    lines.append(
        f"What changed from the {whose}'s starting commit ({(change.base or '')[:12]}) to the "
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


# ---------------------------------------------------------------------------
# The feature's other tasks
# ---------------------------------------------------------------------------


#: How much of the feature's other tasks goes into the look-up prompt, shared
#: fairly between them; each task's whole document is at the path shown.
OTHER_TASKS_PROMPT_CHARS = 12_000

#: What stays this turn's work whatever the other tasks plan.
_OWN_TEST_SENTENCE = (
    "A test this task's own acceptance criteria require, which the builder could write "
    "within this task's own files, is still this turn's work."
)

#: The look-up prompt's rule when the feature's other tasks are shown.
LATER_TASKS_RULE = (
    "Work the plan gives to another task of this feature (see \"The feature's other "
    "tasks\" above) is not a reason to send this turn back: do not report it as a "
    "finding, and if it matters, mention it as advice on a line that starts `ADVICE`. "
    + _OWN_TEST_SENTENCE
)

#: The verdict prompt's rule when the feature's other tasks are shown: the
#: same rule, for a step that writes findings rather than lines, and that may
#: otherwise add `NOT_TESTED` from the check result on its own.
VERDICT_LATER_TASKS_RULE = (
    "Work the plan gives to another task of this feature (see \"The feature's other "
    "tasks\" above) is not a reason to send this turn back: do not keep or add a "
    "finding for it, including `NOT_TESTED` because the project's check does not yet "
    "reach this task's code (for example it says \"no parts yet\") when another task "
    "of this feature wires the check in. "
    + _OWN_TEST_SENTENCE
)

_TASK_ID = re.compile(r"^TASK-(?P<feature>[A-Za-z0-9]+)-\d+$")
_HEADING = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")
#: The parts of a task document shown: its file lists and its criteria.
_EXCERPT_HEADINGS = ("files to", "acceptance criteria")
_CUT_MARK = "\n[cut here: the whole task is at the path above]"


@dataclass(frozen=True)
class OtherTask:
    """Another task of the feature: its ID, title, document path (relative to
    the worktree) and the excerpt shown (file lists and criteria)."""

    task_id: str
    title: str
    path: str
    excerpt: str


def _split_front_matter(text: str) -> tuple[str, str]:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[3:end], text[end + 4:].lstrip("\n")
    return "", text


def _task_title(front: str, body: str) -> str:
    match = re.search(r"^title:\s*(.+?)\s*$", front, re.M)
    if match:
        return match.group(1).strip("\"'")
    for line in body.splitlines():
        heading = _HEADING.match(line)
        if heading:
            return heading.group("title")
    return ""


def _task_excerpt(body: str) -> str:
    """The task's file lists and acceptance criteria, each section to the next
    heading of its level; the whole body when it has none of them."""
    parts: List[str] = []
    level = 0
    fenced = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        heading = None if fenced else _HEADING.match(line)
        if heading:
            depth = len(heading.group("hashes"))
            if level and depth <= level:
                level = 0
            title = heading.group("title").strip()
            if not level and title.lower().startswith(_EXCERPT_HEADINGS):
                level = depth
                parts.append(f"**{title}**")
                continue
        if level:
            parts.append(line)
    excerpt = "\n".join(parts).strip()
    return re.sub(r"\n{3,}", "\n\n", excerpt) if excerpt else body.strip()


def _plan_paths(worktree: Path, feature: str) -> Dict[str, str]:
    """Each task's document path in the feature's plan, ``{}`` when unread."""
    try:
        import yaml

        plan = yaml.safe_load(
            (worktree / ".guardkit" / "features" / f"FEAT-{feature}.yaml").read_text(
                encoding="utf-8"
            )
        )
        return {
            str(task["id"]): str(task["file_path"])
            for task in plan.get("tasks") or ()
            if isinstance(task, dict) and task.get("id") and task.get("file_path")
        }
    except Exception:  # noqa: BLE001 — the plan only picks between copies
        return {}


def other_tasks(worktree: Path, task_id: str) -> List[OtherTask]:
    """The feature's other tasks, read from the worktree's ``tasks/**`` as it
    is now (``TASK-<FEAT>-NNN-*.md``, the feature from the middle of the task
    ID), in task order, this task left out. A task found in more than one
    folder is read from the path the feature's plan gives, else the first.
    Never raises: ``[]`` when there are none or they cannot be read.
    """
    match = _TASK_ID.match(task_id or "")
    if match is None:
        return []
    feature = match.group("feature")
    worktree = Path(worktree)
    try:
        named = re.compile(rf"^(TASK-{re.escape(feature)}-\d+)(?:-.*)?\.md$")
        found: Dict[str, List[Path]] = {}
        for path in sorted((worktree / "tasks").rglob(f"TASK-{feature}-*.md")):
            name = named.match(path.name)
            if name and name.group(1) != task_id and path.is_file():
                found.setdefault(name.group(1), []).append(path)
        if not found:
            return []
        planned = _plan_paths(worktree, feature)
        tasks: List[OtherTask] = []
        for other in sorted(found, key=lambda t: int(t.rsplit("-", 1)[1])):
            copies = found[other]
            chosen = next(
                (p for p in copies if p.relative_to(worktree).as_posix() == planned.get(other)),
                copies[0],
            )
            front, body = _split_front_matter(chosen.read_text(encoding="utf-8"))
            tasks.append(OtherTask(
                other, _task_title(front, body), chosen.relative_to(worktree).as_posix(),
                _task_excerpt(body),
            ))
        return tasks
    except Exception as exc:  # noqa: BLE001 — the review goes on without them
        logger.warning("[%s] The feature's other tasks could not be read: %s", task_id, exc)
        return []


def _fair_shares(sizes: Sequence[int], total: int) -> List[int]:
    """Characters for each item: the smallest whole first, the rest split
    evenly, so no item is cut while a smaller one keeps unused room."""
    shares = [0] * len(sizes)
    left = total
    order = sorted(range(len(sizes)), key=lambda i: sizes[i])
    for done, index in enumerate(order):
        shares[index] = min(sizes[index], left // (len(order) - done))
        left -= shares[index]
    return shares


def _cut(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    room = max(0, limit - len(_CUT_MARK))
    kept = text[:room]
    newline = kept.rfind("\n")
    if newline > room // 2:
        kept = kept[:newline]
    return kept.rstrip() + _CUT_MARK


def render_other_tasks(
    task_id: str, tasks: Sequence[OtherTask], limit: int = OTHER_TASKS_PROMPT_CHARS
) -> str:
    """The look-up prompt's section on the feature's other tasks, at most
    ``limit`` characters of task text shared fairly; ``""`` when none."""
    if not tasks:
        return ""
    heads = [f"### {t.task_id}: {t.title}\n\n{t.path}\n\n" for t in tasks]
    blocks = [head + t.excerpt for head, t in zip(heads, tasks)]
    shares = _fair_shares([len(block) for block in blocks], limit)
    shown = [_cut(block, max(share, len(head) + len(_CUT_MARK)))
             for block, head, share in zip(blocks, heads, shares)]
    match = _TASK_ID.match(task_id or "")
    feature = f"feature FEAT-{match.group('feature')}" if match else "its feature"
    cut = any(len(s) < len(b) for s, b in zip(shown, blocks))
    return (
        "\n## The feature's other tasks\n\n"
        f"This task is one of {len(tasks) + 1} in {feature}. The plan gives "
        "the work below to the feature's other tasks: each one's title, document, the "
        "files it creates or changes and its acceptance criteria, read from the worktree."
        + (" Some are cut to fit; read the whole task at its path when a question needs it."
           if cut else "")
        + "\n\n"
        + "\n\n".join(s.rstrip() for s in shown)
        + "\n"
    )


def other_tasks_section(worktree: Optional[Path], task_id: str) -> str:
    """The section for this task's review, ``""`` when the feature has no
    other task in the worktree. Never raises."""
    if worktree is None:
        return ""
    tasks = other_tasks(Path(worktree), task_id)
    section = render_other_tasks(task_id, tasks)
    if section:
        logger.info(
            "[%s] The review is shown %d other tasks of its feature (%d characters).",
            task_id, len(tasks), len(section),
        )
    return section


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
    other_tasks: str = "",
) -> str:
    """The look-up pass's prompt: the task, the change, the check, the
    builder's notes, the feature's other tasks (``other_tasks_section``) when
    given, and the five questions."""
    criteria = ""
    if acceptance_criteria:
        criteria = "\n## Acceptance criteria\n\n" + "\n".join(
            f"- **{c['id']}**: {c['text']}" for c in acceptance_criteria
        ) + "\n"
    repair = ""
    if sent_back:
        repair = (
            "\n## Findings the builder was sent back to fix\n\n"
            f"{RECHECK_SENTENCE}\n\n"
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
    later_tasks_rule = f"\n\n{LATER_TASKS_RULE}" if other_tasks else ""
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

After each task the factory runs the declared tests of the parts this task changed; their result \
is below. Where its output says "no parts yet", or it ran no test, nothing was tested. \
{MERGE_CHECK_RULE}

{check_section or "No check result was recorded for this turn."}

## The builder's notes

Its concerns, what it says remains, and the files git saw it create and change:

{render_builder_notes(player_report)}
{repair}{documents}{other_tasks}
## The five questions

Answer these in order. Each names the finding you report when the answer is no.{later_tasks_rule}

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


_DIFF_HEADER = re.compile(r"^diff --git a/(\S+) b/(\S+)")


def notes_change(change: ReviewChange, notes: Sequence[Dict[str, Any]]) -> ReviewChange:
    """The parts of the feature's change for the files the notes name, with
    the other changed files listed after them. A whole feature's change runs
    far past what the prompt shows (FEAT-FF29: 307 KB, of which the first
    40,000 characters were shown, whatever files they held). The whole change
    stays at ``change.path``. The change as it is when no note names a file
    in it."""
    files = {_same_path(_file_of(note.get("location"))) for note in notes} - {""}
    sections: List[List[str]] = []
    for line in change.text.splitlines(keepends=True):
        if line.startswith("diff --git ") or not sections:
            sections.append([])
        sections[-1].append(line)
    kept, others = [], []
    for section in sections:
        header = _DIFF_HEADER.match(section[0])
        names = {_same_path(name) for name in header.groups()} if header else set()
        if any(_same_file(name, f) for name in names for f in files):
            kept.append("".join(section))
        elif header:
            others.append(header.group(2))
    if not kept:
        return change
    text = "".join(kept)
    if others:
        text += (
            f"\n# {len(others)} other changed files, not shown: " + ", ".join(others) + "\n"
        )
    return ReviewChange(text, change.path, change.base, change.note)


def build_last_look_prompt(
    feature_id: str, notes: Sequence[Dict[str, Any]], change: ReviewChange
) -> str:
    """The last look's look-up prompt: the build reviewer's notes, numbered,
    each answered against the finished feature's change to the files they
    name. Since 7 November 2026 it answers each note by its number instead of
    writing findings that were matched back to the notes: that matching lost
    26 of 120 true notes in the replay of 5 November."""
    listed = "\n".join(
        f"{n}. {_finding_line(note).removeprefix('- ')}" for n, note in enumerate(notes, 1)
    )
    focused = notes_change(change, notes)
    only = (
        "\n\nOnly the parts for the files the notes name are shown; the whole change is "
        "in the file named above."
        if focused is not change
        else ""
    )
    return f"""You take one last look at a finished feature before it is offered for merge. You do \
not change anything. While its tasks were built, the build reviewer left the notes below for the \
person approving the merge. Each was written when its task finished; later tasks may have changed \
the code since.

Feature: {feature_id}

{_change_section(focused, "feature")}{only}

## What runs at merge

{MERGE_CHECK_RULE} So a note that only says a check, lint or type check never ran is fixed.

## The notes to check

{listed}

Check only these notes: a new problem none of them names is not for this look.

## How to look things up

Your tools only read the feature's worktree as it is now (read_file, ls, grep, glob, code_search, \
code_outline, code_pattern, and code_references when offered). There is no shell.

- Look up only what a note needs. Do not explore.
- Never make the same call twice. There is a limit on tool calls; when it is reached, answer from \
what you have found.

## Your answer

Plain text, one line for every note, starting with its number, in one of two forms:

1 STILL TRUE path/to/file:line: what is still wrong
2 NO LONGER APPLIES: what settles it (the change that fixed it, or why it was never true)

A note is still true while the fault it describes is still in the code, whatever kind you would \
give it now. It no longer applies when you found the code that settles it, or when it only says a \
check never ran. When you cannot tell, answer STILL TRUE: a note kept by mistake costs the person \
approving a minute, a fault dropped by mistake reaches the merge.
"""


#: One answer of the last look: a note's number, then STILL TRUE or NO
#: LONGER APPLIES, allowing list marks, bold and dashes around them.
_LAST_LOOK_ANSWER = re.compile(
    r"^[\s*>#-]*(?:note\s*)?(\d+)[\s*_.):\u2013\u2014-]*(STILL\s+TRUE|NO\s+LONGER\s+APPLIES)\b",
    re.I | re.M,
)


def last_look_answers(text: Optional[str], count: int) -> Optional[Dict[int, bool]]:
    """Each answered note's number (1 to ``count``) and whether it is still
    true. A note answered both ways is still true. ``None`` when no note was
    answered by its number."""
    answers: Dict[int, bool] = {}
    for match in _LAST_LOOK_ANSWER.finditer(text or ""):
        number = int(match.group(1))
        if 1 <= number <= count:
            still = match.group(2).upper().startswith("STILL")
            answers[number] = answers.get(number, False) or still
    return answers or None


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


_LIST_MARK = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


def lookup_findings(text: Optional[str]) -> List[Dict[str, Any]]:
    """The look-up pass's own ``PATTERN path:line: sentence`` lines, as
    findings, for the merge card when the verdict gave nothing readable
    (TypeScript C, 3 November 2026: the verdict call spent its whole output
    allowance thinking, and the look-up's findings were dropped)."""
    found = []
    for line in (text or "").splitlines():
        issue = _normalised({"description": _LIST_MARK.sub("", line).strip()})
        if _pattern_of(issue):
            found.append(issue)
    return found


def lookup_answer(text: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    """The look-up pass's findings when its answer needs no verdict call: every
    line it wrote is a ``PATTERN path:line: sentence`` finding, or it wrote only
    NO FINDINGS (``[]``). ``None`` when anything else is there, which the
    verdict call then reads (b1's suggestion, 3 November 2026)."""
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if [line.strip().upper().rstrip(".") for line in lines] == ["NO FINDINGS"]:
        return []
    found = lookup_findings(text)
    return found if lines and len(found) == len(lines) else None


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


def _file_of(location: Any) -> str:
    """The file part of ``path:line`` (the line may have moved)."""
    text = str(location or "").strip()
    match = re.match(r"^(.+?):\d", text)
    return match.group(1) if match else text


def _same_path(path: str) -> str:
    """A file's path without a leading ``./`` or ``/``."""
    path = path.strip().strip("`")
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def _same_file(a: str, b: str) -> bool:
    """The same file, however the model spelt its path: relative, ``./``, or
    from the root of the machine (``/work/repo/src/a.ts`` is ``src/a.ts``)."""
    a, b = _same_path(a), _same_path(b)
    return bool(a and b) and (a == b or a.endswith("/" + b) or b.endswith("/" + a))


def _last_look(
    notes: List[Dict[str, str]], last_look: Callable[[List[Dict[str, str]]], Any]
) -> Optional[List[Dict[str, str]]]:
    """The notes the last look did not answer NO LONGER APPLIES (a note it
    left unanswered stays), or ``None`` when it answered no note by its
    number (the notes then stay as they are). Never raises."""
    why = "it answered no note by its number"
    try:
        found = last_look(notes)
        answers = last_look_answers(found, len(notes)) if isinstance(found, str) else None
    except Exception as exc:  # noqa: BLE001 — advice only
        answers, why = None, f"{type(exc).__name__}: {exc}"
    if answers is None:
        logger.warning(
            "The last look at the build reviewer's notes did not finish (%s); the "
            "notes are left as they were.", why,
        )
        return None
    return [note for n, note in enumerate(notes, 1) if answers.get(n, True)]


def write_feature_notes(
    feature_id: str,
    task_ids: Sequence[str],
    root: Path,
    last_look: Optional[Callable[[List[Dict[str, str]]], Any]] = None,
) -> Optional[Path]:
    """Write what each task's final review left, at most ten in all. Never raises.

    Into ``<root>/.guardkit/autobuild-private/build_review_notes.json``,
    beside the code-checks summary, where the runner exports it for Forge's
    merge card.

    ``last_look`` (when every task completed) is given the notes and returns
    the answer of one last look at the finished feature, a line per numbered
    note, or ``None``. Notes it answers NO LONGER APPLIES leave the card and
    are counted under ``rechecked``; the others stay. With no notes it is not
    called.
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
        record: Dict[str, Any] = {"feature": feature_id, "notes": notes, "total": total}
        kept = _last_look(notes, last_look) if notes and last_look is not None else None
        if kept is not None:
            dropped = len(notes) - len(kept)
            record.update(notes=kept, total=total - dropped)
            record[RECHECKED_KEY] = {"still_true": len(kept), "no_longer_apply": dropped}
        path = Path(root) / NOTES_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return path
    except Exception as exc:  # noqa: BLE001 — notes never fail a build
        logger.warning("The build review notes could not be written: %s", exc)
        return None


__all__ = [
    "ADVICE_PATTERNS",
    "DIFF_PROMPT_CHARS",
    "FINDING_PATTERNS",
    "LEFTOVERS_KEY",
    "LATER_TASKS_RULE",
    "LOOKUP_TOOLS",
    "MAX_LEFTOVERS",
    "MERGE_CHECK_RULE",
    "NOTES_RELATIVE_PATH",
    "OTHER_TASKS_PROMPT_CHARS",
    "OtherTask",
    "RECHECKED_KEY",
    "RECHECK_SENTENCE",
    "REPAIR_KEY",
    "REPAIR_TURN_ENV",
    "ReviewChange",
    "VERDICT_LATER_TASKS_RULE",
    "build_last_look_prompt",
    "build_lookup_prompt",
    "change_since",
    "diff_path",
    "is_located",
    "last_look_answers",
    "lookup_answer",
    "notes_change",
    "latest_review",
    "leftovers",
    "located_findings",
    "other_tasks",
    "other_tasks_section",
    "render_builder_notes",
    "render_other_tasks",
    "repair_findings_sent",
    "repair_issues",
    "repair_turn_enabled",
    "write_change",
    "write_feature_notes",
]
