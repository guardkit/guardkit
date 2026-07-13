"""Diff ingestion for the R-b code-review seat (S1, 2026-07-13).

Design source (binding): ``ai-transition/docs/factory-code-quality-seat-options-
2026-07.md`` — R-b build-lane sketch stage **S-1**. The options-paper receipt is
the frame for this module: today ``qa/enforcement.py:git_changed_paths`` yields
only changed *path sets*; **nothing reads an arbitrary ``git <range>`` into a
review payload** (diff hunks + surrounding context + changed-path metadata).
This module is that new piece — and only that piece.

Two invariants the paper pins:

- **Deterministic, no LLM.** This is a pure reader over ``git diff`` text. It
  never calls a model seat; it produces the structured payload a later stage
  (S-2/S-3) hands to the reviewer seat. Nothing here decides anything.
- **F14-shaped subject.** The review subject mirrors the pinned F14 schema's
  ``SubjectKind`` (``qa/formats/review_findings.py`` — ``tree`` / ``commit`` /
  ``merge``, LPA-18: an uncommitted working tree is a reviewable surface). The
  payload's ``subject_kind`` + ``ref`` map straight onto ``ReviewSubject``.

Honesty-to-state (``.claude/rules/absence-of-failure-is-not-success``): a git
invocation that *fails* (not a repo, bad ref) raises :class:`DiffIngestError`
loudly — it is never silently read as "no changes". An invocation that
*succeeds with empty output* is a legitimate empty payload (nothing changed),
distinct from a failure.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Literal, Optional, Sequence, Tuple

__all__ = [
    "DiffIngestError",
    "SubjectKind",
    "ChangeKind",
    "LineKind",
    "DiffLine",
    "DiffHunk",
    "FileDiff",
    "ReviewPayload",
    "parse_unified_diff",
    "ingest_working_tree",
    "ingest_commit",
    "ingest_merge",
    "ingest_range",
]

#: Mirrors F14 ``review_findings.SubjectKind`` (tree / commit / merge). A range
#: review (arbitrary ``base..head``) is classified ``commit`` — it reviews
#: committed history, the same F14 subject a single commit maps to.
SubjectKind = Literal["tree", "commit", "merge"]

#: How a file changed across the reviewed diff.
ChangeKind = Literal[
    "added", "modified", "deleted", "renamed", "copied", "type_changed"
]

#: A diff body line's role within a hunk.
LineKind = Literal["context", "added", "removed"]

#: Default surrounding-context lines requested from git (git's own default).
DEFAULT_CONTEXT_LINES = 3


class DiffIngestError(Exception):
    """A diff could not be produced or parsed — raised loudly, never swallowed.

    Carries the failing git argv + stderr (when the cause is git) so the caller
    surfaces a named finding rather than a fabricated empty review.
    """


# ---------------------------------------------------------------------------
# Structured payload (frozen dataclasses — a deterministic reader, not a
# persisted QA format; F14 is the persisted schema this feeds).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiffLine:
    """One body line of a hunk.

    ``old_lineno`` / ``new_lineno`` are the 1-based line numbers in the pre- and
    post-image; a line absent from one side (an add / a remove) carries ``None``
    for that side.
    """

    kind: LineKind
    content: str
    old_lineno: Optional[int]
    new_lineno: Optional[int]


@dataclass(frozen=True)
class DiffHunk:
    """One ``@@`` hunk: its ranges, the section heading, and its body lines."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    section_heading: str
    header: str
    lines: Tuple[DiffLine, ...]

    @property
    def added_lines(self) -> Tuple[DiffLine, ...]:
        return tuple(l for l in self.lines if l.kind == "added")

    @property
    def removed_lines(self) -> Tuple[DiffLine, ...]:
        return tuple(l for l in self.lines if l.kind == "removed")


@dataclass(frozen=True)
class FileDiff:
    """A single file's diff: change classification, metadata, and its hunks."""

    path: str
    old_path: Optional[str]
    change_kind: ChangeKind
    is_binary: bool
    old_mode: Optional[str]
    new_mode: Optional[str]
    similarity: Optional[int]
    hunks: Tuple[DiffHunk, ...]

    @property
    def additions(self) -> int:
        return sum(len(h.added_lines) for h in self.hunks)

    @property
    def deletions(self) -> int:
        return sum(len(h.removed_lines) for h in self.hunks)

    @property
    def is_rename(self) -> bool:
        return self.change_kind == "renamed"


@dataclass(frozen=True)
class ReviewPayload:
    """The structured review subject: what was reviewed + its per-file diffs.

    ``subject_kind`` + ``ref`` map directly onto F14 ``ReviewSubject`` (the
    reviewer seat records *what* it looked at). ``context_lines`` is the
    surrounding-context width the diff was cut with.
    """

    subject_kind: SubjectKind
    ref: str
    context_lines: int
    files: Tuple[FileDiff, ...]

    @property
    def changed_paths(self) -> Tuple[str, ...]:
        """Changed paths (new path, or old path for a delete) — sorted, unique.

        The richer sibling of ``enforcement.git_changed_paths`` (which yields a
        bare path set); here each path also has its hunks + metadata in
        ``files``.
        """
        return tuple(sorted({f.path for f in self.files}))

    @property
    def is_empty(self) -> bool:
        return not self.files

    @property
    def total_additions(self) -> int:
        return sum(f.additions for f in self.files)

    @property
    def total_deletions(self) -> int:
        return sum(f.deletions for f in self.files)


# ---------------------------------------------------------------------------
# Unified-diff parser (pure — takes text, returns FileDiffs; independently
# testable without a git process).
# ---------------------------------------------------------------------------

_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<heading>.*)$"
)


def _strip_prefix(path: str) -> Optional[str]:
    """Strip git's ``a/`` / ``b/`` diff prefix; ``/dev/null`` → ``None``.

    Quoted paths (git quotes paths with special chars) are unquoted at the
    boundary so callers always see the literal repo path.
    """
    path = path.strip()
    if path == "/dev/null":
        return None
    if path.startswith(('"',)) and path.endswith('"'):
        # git core.quotePath: octal-escaped, C-style quoted. Best-effort decode.
        inner = path[1:-1]
        try:
            path = inner.encode("latin-1", "backslashreplace").decode(
                "unicode_escape"
            )
        except (UnicodeDecodeError, ValueError):
            path = inner
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _finalise_hunk(
    header: str,
    old_start: int,
    old_count: int,
    new_start: int,
    new_count: int,
    heading: str,
    body: List[str],
) -> DiffHunk:
    lines: List[DiffLine] = []
    old_no = old_start
    new_no = new_start
    for raw in body:
        if raw.startswith("\\"):
            # "\ No newline at end of file" — annotation, not a content line.
            continue
        marker = raw[:1]
        content = raw[1:]
        if marker == "+":
            lines.append(DiffLine("added", content, None, new_no))
            new_no += 1
        elif marker == "-":
            lines.append(DiffLine("removed", content, old_no, None))
            old_no += 1
        else:
            # A context line (leading space) — or, defensively, an empty line
            # git emitted as a bare "" for a blank context row.
            lines.append(DiffLine("context", content, old_no, new_no))
            old_no += 1
            new_no += 1
    return DiffHunk(
        old_start=old_start,
        old_count=old_count,
        new_start=new_start,
        new_count=new_count,
        section_heading=heading.strip(),
        header=header,
        lines=tuple(lines),
    )


class _FileBuilder:
    """Mutable accumulator for one file's diff, sealed into a FileDiff."""

    def __init__(self) -> None:
        # Best-effort paths recovered from the "diff --git a/X b/Y" header —
        # the only path source for a mode-only change (no ---/+++ lines).
        self.header_old: Optional[str] = None
        self.header_new: Optional[str] = None
        self.old_path: Optional[str] = None
        self.new_path: Optional[str] = None
        # Whether a ---/+++ marker was seen (a marker may legitimately set the
        # path to None for /dev/null — distinct from "never mentioned").
        self.saw_old_marker: bool = False
        self.saw_new_marker: bool = False
        self.rename_from: Optional[str] = None
        self.rename_to: Optional[str] = None
        self.copy_from: Optional[str] = None
        self.copy_to: Optional[str] = None
        self.old_mode: Optional[str] = None
        self.new_mode: Optional[str] = None
        self.similarity: Optional[int] = None
        self.is_new: bool = False
        self.is_deleted: bool = False
        self.is_binary: bool = False
        self.hunks: List[DiffHunk] = []

    def _change_kind(self) -> ChangeKind:
        if self.is_new:
            return "added"
        if self.is_deleted:
            return "deleted"
        if self.rename_from is not None or self.rename_to is not None:
            return "renamed"
        if self.copy_from is not None or self.copy_to is not None:
            return "copied"
        # A pure mode/type change: modes present and differ, no content hunks.
        if (
            not self.hunks
            and self.old_mode is not None
            and self.new_mode is not None
            and self.old_mode != self.new_mode
        ):
            return "type_changed"
        return "modified"

    def seal(self) -> Optional[FileDiff]:
        if self.saw_old_marker:
            old = self.old_path
        else:
            old = self.rename_from or self.copy_from or self.header_old
        if self.saw_new_marker:
            new = self.new_path
        else:
            new = self.rename_to or self.copy_to or self.header_new
        # Primary path: the post-image path (new), falling back to old for a
        # delete. If neither surfaced, this builder held no real file.
        path = new if new is not None else old
        if path is None:
            return None
        return FileDiff(
            path=path,
            old_path=old,
            change_kind=self._change_kind(),
            is_binary=self.is_binary,
            old_mode=self.old_mode,
            new_mode=self.new_mode,
            similarity=self.similarity,
            hunks=tuple(self.hunks),
        )


def parse_unified_diff(text: str) -> Tuple[FileDiff, ...]:
    """Parse ``git diff`` unified output into per-file :class:`FileDiff` records.

    Pure and deterministic: it consumes the exact text ``git diff`` /
    ``git show --format=`` emit (default ``a/`` / ``b/`` prefixes) and never
    shells out. Handles adds, deletes, modifies, renames, copies, mode-only
    changes, and binary files; tolerant of a truncated final hunk.

    Empty / whitespace-only input → an empty tuple (a legitimate no-change
    diff, not an error).
    """
    lines = (text or "").splitlines()
    files: List[FileDiff] = []
    builder: Optional[_FileBuilder] = None

    # Open hunk state.
    h_header: Optional[str] = None
    h_old_start = h_old_count = h_new_start = h_new_count = 0
    h_heading = ""
    h_body: List[str] = []

    def _close_hunk() -> None:
        nonlocal h_header, h_body
        if builder is not None and h_header is not None:
            builder.hunks.append(
                _finalise_hunk(
                    h_header,
                    h_old_start,
                    h_old_count,
                    h_new_start,
                    h_new_count,
                    h_heading,
                    h_body,
                )
            )
        h_header = None
        h_body = []

    def _close_file() -> None:
        nonlocal builder
        _close_hunk()
        if builder is not None:
            sealed = builder.seal()
            if sealed is not None:
                files.append(sealed)
        builder = None

    for line in lines:
        if line.startswith("diff --git "):
            _close_file()
            builder = _FileBuilder()
            # Recover best-effort paths from "a/<old> b/<new>" (the sole path
            # source for a mode-only change). Unambiguous unless a path itself
            # contains " b/"; the ---/+++ lines override this when present.
            rest = line[len("diff --git "):]
            sep = rest.find(" b/")
            if rest.startswith("a/") and sep != -1:
                builder.header_old = _strip_prefix(rest[:sep])
                builder.header_new = _strip_prefix(rest[sep + 1:])
            continue
        if builder is None:
            # Preamble before the first file header (e.g. a stray blank) — skip.
            continue

        if h_header is not None:
            # Inside a hunk body (a "diff --git" line was already handled at the
            # top of the loop, so it cannot reach here). A new "@@" ends the
            # hunk and is reprocessed by the hunk-header branch below.
            if not line.startswith("@@"):
                # Body lines start with ' ', '+', '-', or '\'. Anything else
                # (e.g. the next file's metadata with no blank separator) closes
                # the hunk and is reprocessed as metadata below.
                if line[:1] in (" ", "+", "-", "\\") or line == "":
                    h_body.append(line)
                    continue
                _close_hunk()

        m = _HUNK_RE.match(line)
        if m is not None:
            _close_hunk()
            h_header = line
            h_old_start = int(m.group("old_start"))
            h_old_count = int(m.group("old_count") or 1)
            h_new_start = int(m.group("new_start"))
            h_new_count = int(m.group("new_count") or 1)
            h_heading = m.group("heading")
            h_body = []
            continue

        # --- File metadata lines ---
        if line.startswith("old mode "):
            builder.old_mode = line[len("old mode "):].strip()
        elif line.startswith("new mode "):
            builder.new_mode = line[len("new mode "):].strip()
        elif line.startswith("new file mode "):
            builder.is_new = True
            builder.new_mode = line[len("new file mode "):].strip()
        elif line.startswith("deleted file mode "):
            builder.is_deleted = True
            builder.old_mode = line[len("deleted file mode "):].strip()
        elif line.startswith("rename from "):
            builder.rename_from = _strip_prefix(line[len("rename from "):])
        elif line.startswith("rename to "):
            builder.rename_to = _strip_prefix(line[len("rename to "):])
        elif line.startswith("copy from "):
            builder.copy_from = _strip_prefix(line[len("copy from "):])
        elif line.startswith("copy to "):
            builder.copy_to = _strip_prefix(line[len("copy to "):])
        elif line.startswith("similarity index "):
            frac = line[len("similarity index "):].strip().rstrip("%")
            try:
                builder.similarity = int(frac)
            except ValueError:
                builder.similarity = None
        elif line.startswith("dissimilarity index "):
            pass  # informational; change_kind already covers it
        elif line.startswith("index "):
            # "index <old>..<new> <mode>" — a trailing mode means a plain modify
            # kept its mode; capture it if we have no explicit old/new mode.
            parts = line.split()
            if len(parts) == 3 and builder.old_mode is None:
                builder.old_mode = parts[2]
                builder.new_mode = parts[2]
        elif line.startswith("--- "):
            builder.old_path = _strip_prefix(line[len("--- "):])
            builder.saw_old_marker = True
        elif line.startswith("+++ "):
            builder.new_path = _strip_prefix(line[len("+++ "):])
            builder.saw_new_marker = True
        elif line.startswith("Binary files ") or line.startswith(
            "GIT binary patch"
        ):
            builder.is_binary = True
            if line.startswith("Binary files "):
                # "Binary files a/x and b/y differ" — recover the paths.
                mb = re.match(
                    r"^Binary files (?P<a>.+) and (?P<b>.+) differ$", line
                )
                if mb is not None:
                    a = _strip_prefix(mb.group("a"))
                    b = _strip_prefix(mb.group("b"))
                    if a is not None and builder.old_path is None:
                        builder.old_path = a
                        builder.saw_old_marker = True
                    if b is not None and builder.new_path is None:
                        builder.new_path = b
                        builder.saw_new_marker = True
        # Any other line (e.g. "\ No newline") outside a hunk is ignored.

    _close_file()
    return tuple(files)


# ---------------------------------------------------------------------------
# Git invocation (the impure edge — a thin, injectable runner).
# ---------------------------------------------------------------------------


def _default_git(
    repo_root: Path,
) -> Callable[[Sequence[str]], subprocess.CompletedProcess]:
    def _run(args: Sequence[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=60,
        )

    return _run


def _run_diff(
    repo_root: Path,
    diff_args: Sequence[str],
    *,
    context_lines: int,
    git_run: Optional[Callable[[Sequence[str]], subprocess.CompletedProcess]],
) -> str:
    """Run a ``git diff``-family command and return its stdout, or raise loudly.

    ``diff_args`` is the command past ``git`` (e.g. ``["diff", "HEAD"]`` or
    ``["show", "--format=", sha]``). ``--no-color`` and ``--unified=<n>`` are
    injected so output is stable and cut at the requested context width. A
    non-zero return code raises :class:`DiffIngestError` with argv + stderr —
    an unreadable subject is a named failure, never a faked empty review.
    """
    if context_lines < 0:
        raise DiffIngestError(f"context_lines must be >= 0, got {context_lines}")
    run = git_run or _default_git(repo_root)
    # Inject flags right after the subcommand so they bind to diff/show.
    args = [diff_args[0], "--no-color", f"--unified={context_lines}", *diff_args[1:]]
    try:
        proc = run(args)
    except (OSError, subprocess.SubprocessError) as exc:
        raise DiffIngestError(
            f"git {' '.join(args)} could not be run ({exc}) — is git installed "
            f"and {repo_root} a repository?"
        ) from exc
    if proc.returncode != 0:
        raise DiffIngestError(
            f"git {' '.join(args)} failed (exit {proc.returncode}): "
            f"{(proc.stderr or '').strip() or '<no stderr>'}"
        )
    return proc.stdout or ""


# ---------------------------------------------------------------------------
# The public ingestion surface — one constructor per F14 SubjectKind + range.
# ---------------------------------------------------------------------------

#: Working-tree scopes: all uncommitted vs HEAD / staged only / unstaged only.
TreeScope = Literal["all", "staged", "unstaged"]


def ingest_working_tree(
    repo_root: Path,
    *,
    scope: TreeScope = "all",
    context_lines: int = DEFAULT_CONTEXT_LINES,
    git_run: Optional[Callable[[Sequence[str]], subprocess.CompletedProcess]] = None,
) -> ReviewPayload:
    """Ingest the working tree as a reviewable subject (F14 ``tree``, LPA-18).

    ``scope``:
      - ``"all"``      — everything uncommitted vs HEAD (``git diff HEAD``): the
                         default "review my working tree".
      - ``"staged"``   — index vs HEAD (``git diff --cached``).
      - ``"unstaged"`` — working tree vs index (``git diff``).

    An empty result is a legitimate empty payload (a clean tree), not an error.
    """
    if scope == "all":
        diff_args: List[str] = ["diff", "HEAD"]
        ref = "working-tree (all uncommitted vs HEAD)"
    elif scope == "staged":
        diff_args = ["diff", "--cached"]
        ref = "working-tree (staged vs HEAD)"
    elif scope == "unstaged":
        diff_args = ["diff"]
        ref = "working-tree (unstaged vs index)"
    else:  # pragma: no cover - Literal guards this at type-check time
        raise DiffIngestError(f"unknown working-tree scope {scope!r}")
    text = _run_diff(
        repo_root, diff_args, context_lines=context_lines, git_run=git_run
    )
    return ReviewPayload(
        subject_kind="tree",
        ref=ref,
        context_lines=context_lines,
        files=parse_unified_diff(text),
    )


def ingest_commit(
    repo_root: Path,
    commit: str,
    *,
    context_lines: int = DEFAULT_CONTEXT_LINES,
    git_run: Optional[Callable[[Sequence[str]], subprocess.CompletedProcess]] = None,
) -> ReviewPayload:
    """Ingest a single commit's diff (F14 ``commit``).

    Uses ``git show --format=`` so a *root* commit (no parent) is handled — a
    ``<sha>^..<sha>`` range would fail there. ``--format=`` suppresses the
    commit message so only the diff is parsed.
    """
    if not commit or not commit.strip():
        raise DiffIngestError("commit ref must be a non-empty string")
    text = _run_diff(
        repo_root,
        ["show", "--format=", commit],
        context_lines=context_lines,
        git_run=git_run,
    )
    return ReviewPayload(
        subject_kind="commit",
        ref=commit,
        context_lines=context_lines,
        files=parse_unified_diff(text),
    )


def ingest_merge(
    repo_root: Path,
    merge: str,
    *,
    context_lines: int = DEFAULT_CONTEXT_LINES,
    git_run: Optional[Callable[[Sequence[str]], subprocess.CompletedProcess]] = None,
) -> ReviewPayload:
    """Ingest a merge commit as what it brought in vs its first parent (F14 ``merge``).

    Diffs ``<merge>^1..<merge>`` — the changes the merge introduced relative to
    the mainline (first-parent) side, i.e. the branch's contribution. This is
    the reviewable surface for a merge; a combined multi-parent diff is not what
    a reviewer reads.
    """
    if not merge or not merge.strip():
        raise DiffIngestError("merge ref must be a non-empty string")
    text = _run_diff(
        repo_root,
        ["diff", f"{merge}^1", merge],
        context_lines=context_lines,
        git_run=git_run,
    )
    return ReviewPayload(
        subject_kind="merge",
        ref=merge,
        context_lines=context_lines,
        files=parse_unified_diff(text),
    )


def ingest_range(
    repo_root: Path,
    base: str,
    head: Optional[str] = None,
    *,
    context_lines: int = DEFAULT_CONTEXT_LINES,
    git_run: Optional[Callable[[Sequence[str]], subprocess.CompletedProcess]] = None,
) -> ReviewPayload:
    """Ingest an arbitrary git range (F14 ``commit`` — reviews committed history).

    Two call shapes:
      - ``ingest_range(root, "main", "feature")`` → ``git diff main feature``.
      - ``ingest_range(root, "main..feature")``   → a single range expression
        (``..`` or ``...``) passed straight through to ``git diff``.

    The ``base``/``head`` pair and the single-expression form both resolve to
    one ``git diff`` invocation; the payload's ``ref`` records the human form.
    """
    if not base or not base.strip():
        raise DiffIngestError("range base must be a non-empty string")
    if head is not None and head.strip():
        diff_args = ["diff", base, head]
        ref = f"{base}..{head}"
    else:
        diff_args = ["diff", base]
        ref = base
    text = _run_diff(
        repo_root, diff_args, context_lines=context_lines, git_run=git_run
    )
    return ReviewPayload(
        subject_kind="commit",
        ref=ref,
        context_lines=context_lines,
        files=parse_unified_diff(text),
    )
