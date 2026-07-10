"""Task-level tracker audit — the declared-vs-inferred twin of ``feature_audit``.

WS3-S8a (see the WS3 autobuild-reliability scope doc §4 + §6 S8). The
feature-audit pattern (:mod:`guardkit.orchestrator.feature_audit`) reconciles a
feature YAML's *declared* status against the status *inferred* from its tasks.
This module does the equivalent for individual task files and adds the
dangling-reference class that the feature auditor cannot see.

Two independent signals are surfaced, both deterministic and both read-only —
the tool **reports, never fixes** (the per-repo sweeps do the fixing):

1. **Declared vs inferred status** for every ``tasks/**/TASK-*.md`` file.
   *Declared* = the frontmatter ``status`` field together with the ``tasks/``
   subtree the file physically sits in. *Inferred* = git evidence (commits
   referencing the task id, feature-YAML rollups). Divergences are the
   "completed but sitting in backlog / in_review" rot named in §4.

2. **Dangling references** — task ids referenced by feature YAMLs or source
   code that **no task file declares**. This is the class behind guardkit's
   red dead-task-id baseline (``TASK-FMDR-001`` / ``TASK-FIX-UVSRCDEP01`` /
   ``TASK-RBX-002``): the ids live only in ``docs/state/`` stubs and code
   references, with no owning task file under ``tasks/``.

There are **no LLM calls** — every verdict derives from the filesystem and
``git log``. The tool runs against *any* repo root so the eleven per-repo
sweep sessions can consume one machine-readable report each.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Status vocabulary
# ---------------------------------------------------------------------------

# ``tasks/<subtree>/`` directory names, grouped by whether the subtree implies
# the task is finished (terminal) or still open. Anything else is "other".
TERMINAL_SUBTREES: frozenset[str] = frozenset(
    {"completed", "cancelled", "obsolete", "archived", "review_complete"}
)
OPEN_SUBTREES: frozenset[str] = frozenset(
    {"backlog", "in_progress", "in_review", "design_approved", "blocked"}
)

# Frontmatter ``status:`` string values, normalised to the same two buckets.
# Hyphen/underscore/spacing variants are folded before lookup.
_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        "completed",
        "complete",
        "done",
        "cancelled",
        "canceled",
        "obsolete",
        "superseded",
        "archived",
        "review_complete",
        "closed",
        "merged",
    }
)
_OPEN_STATUSES: frozenset[str] = frozenset(
    {
        "backlog",
        "in_progress",
        "design_approved",
        "in_review",
        "blocked",
        "todo",
        "open",
        "ready",
        "planned",
        "pending",
    }
)

# Buckets.
TERMINAL = "terminal"
OPEN = "open"
OTHER = "other"

# Task-id shape. The ``TASK-`` prefix is always upper-case, but id *components*
# may be upper-case prefixes (REV, FIX), numeric (001), UPPER-case hashes
# (CB0F), or LOWER-case hex hashes (a3f8, 6d41) — guardkit's own generator
# emits lower-case hex. A naive upper-case-only regex (as used by the
# dead-task-id lint) truncates a lower-case-hash id to just its prefix, so we
# capture a broad candidate and then trim off any trailing lower-case *slug*
# words (id + "-do-a-thing" -> id). A slug word is what distinguishes an id
# boundary in filenames and ``file_path:`` YAML values.
# (Example ids below use the XXX placeholder form so this module's own
# docstrings do not self-report as dangling references.)
_CANDIDATE_RE = re.compile(
    r"\bTASK-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*(?:\.\d+(?:\.\d+)*)?"
)
_HEX_RE = re.compile(r"[0-9a-fA-F]+")
_ALNUM_RE = re.compile(r"[A-Za-z0-9]+")
_PLACEHOLDER_TOKENS = ("XXX", "YYY", "ZZZ", "NNN")

# Commit-subject shapes that indicate a task's work actually shipped. A bare
# reference in a commit *body* (e.g. a spec commit enumerating riders) is NOT
# treated as completion — only a subject that names the id with a
# conventional-completion type or an explicit completion verb.
_COMPLETION_TYPE_RE = re.compile(r"^(feat|fix|refactor|perf|revert)\b", re.IGNORECASE)
_COMPLETION_VERB_RE = re.compile(
    r"\b(complete[sd]?|completing|implement(?:s|ed|ing)?|"
    r"merge[sd]?|ship(?:s|ped|ping)?|land(?:s|ed|ing)?|"
    r"finaliz(?:e|es|ed|ing)|done|close[sd]?|resolv(?:e|es|ed))\b",
    re.IGNORECASE,
)

# Default globs (relative to repo root) scanned for *references* to task ids
# when detecting dangling references. Kept deliberately narrow: feature YAMLs
# (a plan pointing at a non-existent task is a real defect) and first-party
# source code — the dead-task-id-lint class, covering both the ``guardkit/``
# layout and the fleet's ``src/<pkg>/`` layout. The whole docs tree is
# intentionally excluded — it is full of legitimate historical prose about
# archived-then-pruned tasks. NOTE: illustrative ids in source docstrings
# (e.g. an ``outcome_id`` example) can surface as dangling; the ``referenced_by``
# list makes those trivial to recognise and dismiss during a sweep.
DEFAULT_REFERENCE_GLOBS: tuple[str, ...] = (
    ".guardkit/features/*.yaml",
    ".guardkit/features/*.yml",
    "guardkit/**/*.py",
    "src/**/*.py",
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TaskAuditRow:
    """Declared-vs-inferred audit for a single task file.

    Attributes:
        task_id: The task id (frontmatter ``id`` if present, else parsed from
            the filename).
        file: Repo-root-relative path to the task markdown file.
        subtree: The ``tasks/`` subtree the file sits in (e.g. ``backlog``).
        subtree_bucket: ``terminal`` / ``open`` / ``other`` for the subtree.
        frontmatter_status: The raw ``status`` field, or ``None`` if absent.
        declared_bucket: ``terminal`` / ``open`` / ``other`` — the bucket the
            tracker *claims* (frontmatter status if known, else the subtree).
        inferred_status: ``completed`` / ``unknown`` — from git + feature
            rollups. ``unknown`` means no positive completion evidence (never
            an assertion of not-done).
        inferred_evidence: Human-readable evidence strings behind
            ``inferred_status``.
        divergences: Divergence-class slugs that fired for this row (empty when
            the row is clean).
    """

    task_id: str
    file: str
    subtree: str
    subtree_bucket: str
    frontmatter_status: Optional[str]
    declared_bucket: str
    inferred_status: str
    inferred_evidence: List[str] = field(default_factory=list)
    divergences: List[str] = field(default_factory=list)

    @property
    def is_divergent(self) -> bool:
        return bool(self.divergences)


@dataclass
class DanglingReference:
    """A task id referenced somewhere but declared by no task file.

    Attributes:
        task_id: The referenced-but-undeclared task id.
        referenced_by: Repo-relative paths that mention the id.
        state_doc_exists: ``True`` when a ``docs/state/<id>*`` stub exists —
            i.e. there is state prose but no owning task file.
    """

    task_id: str
    referenced_by: List[str] = field(default_factory=list)
    state_doc_exists: bool = False


@dataclass
class TaskAuditReport:
    """The full task-audit result for a repo."""

    repo_root: str
    git_available: bool
    task_file_count: int
    rows: List[TaskAuditRow]
    dangling: List[DanglingReference]

    @property
    def divergent_rows(self) -> List[TaskAuditRow]:
        return [r for r in self.rows if r.is_divergent]

    @property
    def divergent_task_count(self) -> int:
        return len(self.divergent_rows)

    @property
    def dangling_count(self) -> int:
        return len(self.dangling)

    @property
    def total_divergences(self) -> int:
        """The single per-repo tracker-divergence count (target: 0)."""
        return self.divergent_task_count + self.dangling_count

    def divergence_breakdown(self) -> Dict[str, int]:
        """Count of rows per divergence class, plus a dangling total."""
        counts: Dict[str, int] = {}
        for row in self.rows:
            for slug in row.divergences:
                counts[slug] = counts.get(slug, 0) + 1
        if self.dangling:
            counts["dangling_reference"] = self.dangling_count
        return dict(sorted(counts.items()))

    def to_dict(self, include_clean_rows: bool = False) -> dict:
        """Serialise to a machine-readable dict (the sweep sessions' input)."""
        rows = self.rows if include_clean_rows else self.divergent_rows
        return {
            "generated_by": "guardkit task audit",
            "repo_root": self.repo_root,
            "git_available": self.git_available,
            "summary": {
                "task_files": self.task_file_count,
                "divergent_tasks": self.divergent_task_count,
                "dangling_references": self.dangling_count,
                "total_divergences": self.total_divergences,
                "by_divergence": self.divergence_breakdown(),
                "rows_included": "all" if include_clean_rows else "divergent_only",
            },
            "tasks": [
                {
                    "task_id": r.task_id,
                    "file": r.file,
                    "subtree": r.subtree,
                    "frontmatter_status": r.frontmatter_status,
                    "declared_bucket": r.declared_bucket,
                    "inferred_status": r.inferred_status,
                    "inferred_evidence": r.inferred_evidence,
                    "divergences": r.divergences,
                }
                for r in rows
            ],
            "dangling": [
                {
                    "task_id": d.task_id,
                    "referenced_by": d.referenced_by,
                    "state_doc_exists": d.state_doc_exists,
                }
                for d in self.dangling
            ],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalise_status(value: str) -> str:
    """Fold a frontmatter status string to a lookup key."""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _status_bucket(value: Optional[str]) -> str:
    """Map a frontmatter status string to ``terminal`` / ``open`` / ``other``."""
    if not value:
        return OTHER
    key = _normalise_status(value)
    if key in _TERMINAL_STATUSES:
        return TERMINAL
    if key in _OPEN_STATUSES:
        return OPEN
    return OTHER


def _subtree_bucket(subtree: str) -> str:
    """Map a ``tasks/`` subtree to ``terminal`` / ``open`` / ``other``."""
    if subtree in TERMINAL_SUBTREES:
        return TERMINAL
    if subtree in OPEN_SUBTREES:
        return OPEN
    return OTHER


def _id_is_placeholder(task_id: str) -> bool:
    """True for docstring placeholders (``TASK-XXX``) and digit-less prefixes."""
    body = task_id.removeprefix("TASK-")
    if any(token in body for token in _PLACEHOLDER_TOKENS):
        return True
    if not any(ch.isdigit() for ch in body):
        return True
    return False


def _component_is_id_part(seg: str) -> bool:
    """True when a ``-``-separated component belongs to an id, not a slug.

    Qualifying components: a purely numeric segment (``001``); an alnum segment
    carrying an upper-case letter (``REV``, ``CB0F``); a hex segment carrying a
    digit (``a3f8``, ``6d41``). A lower-case English slug word (``feature``,
    ``do``) qualifies for none of these and marks the id boundary.
    """
    if seg.isdigit():
        return True
    if _ALNUM_RE.fullmatch(seg) and any(c.isupper() for c in seg):
        return True
    if _HEX_RE.fullmatch(seg) and any(c.isdigit() for c in seg):
        return True
    return False


def _trim_candidate(candidate: str) -> str:
    """Trim a raw ``TASK-...`` candidate down to its id, dropping slug words."""
    subtask = ""
    if "." in candidate:
        candidate, _, tail = candidate.partition(".")
        subtask = f".{tail}"
    parts = candidate.split("-")  # ["TASK", "MP", "001", "do", "thing"]
    kept = [parts[0]]  # "TASK"
    trimmed = False
    for seg in parts[1:]:
        if _component_is_id_part(seg):
            kept.append(seg)
        else:
            trimmed = True
            break
    task_id = "-".join(kept)
    # A ``.N`` subtask suffix only belongs to a bare id (no slug was trimmed).
    if not trimmed:
        task_id += subtask
    return task_id


def _raw_candidates(text: str) -> List[str]:
    """Return the raw, un-trimmed ``TASK-...`` candidate strings in ``text``."""
    return [m.group(0) for m in _CANDIDATE_RE.finditer(text)]


def _boundary_prefixes(candidate: str):
    """Yield ``candidate`` and its shorter ``-``/``.`` boundary prefixes, longest first."""
    yield candidate
    for i in range(len(candidate) - 1, 0, -1):
        if candidate[i] in "-.":
            yield candidate[:i]


def _resolve_candidate(candidate: str, declared_ids: Set[str]) -> Optional[str]:
    """Resolve a raw candidate to a declared id it names, else ``None``.

    Grounds the ambiguous id/slug boundary in the authoritative declared-id set.
    Resolution is bidirectional at ``-``/``.`` boundaries so both id-styles work:

    * **forward** — ``TASK-XXX-001-do-thing`` resolves to a declared
      ``TASK-XXX-001`` (the task file carries the hash-form id; the reference
      trails a slug or subtask suffix);
    * **reverse** — a bare reference ``TASK-XXX-001`` resolves to a declared
      ``TASK-XXX-001-do-thing`` (the task file has no frontmatter ``id`` so its
      id is the full slug-bearing stem).

    Forward matches win over reverse; among reverse matches the shortest
    declared id wins (deterministic).
    """
    for prefix in _boundary_prefixes(candidate):
        if prefix in declared_ids:
            return prefix
    reverse = [
        d
        for d in declared_ids
        if d.startswith(candidate + "-") or d.startswith(candidate + ".")
    ]
    if reverse:
        return min(reverse, key=lambda d: (len(d), d))
    return None


def _read_frontmatter(path: Path) -> tuple[dict, bool]:
    """Read only the YAML frontmatter block of a markdown file.

    Lightweight (does not load the markdown body). Returns ``(data, malformed)``:
    ``data`` is ``{}`` when there is no ``---`` fence or the block cannot be
    parsed; ``malformed`` is ``True`` only when a fence is present but its YAML
    fails to parse (a genuine tracker-integrity defect, distinct from a file
    that simply has no frontmatter).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:  # pragma: no cover - unexpected I/O
        logger.warning("Could not read %s: %s", path, exc)
        return {}, False
    if not text.startswith("---"):
        return {}, False
    # Split on the fence; the frontmatter is between the first two ``---`` lines.
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return {}, False
    block = parts[0][len("---") :]
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        logger.debug("Malformed frontmatter in %s: %s", path, exc)
        return {}, True
    if not isinstance(data, dict):
        return {}, False
    return data, False


def _iter_task_files(repo_root: Path):
    """Yield every ``tasks/**/TASK-*.md`` path under the repo root."""
    tasks_root = repo_root / "tasks"
    if not tasks_root.is_dir():
        return
    for path in sorted(tasks_root.rglob("TASK-*.md")):
        if path.is_file():
            yield path


def _subtree_for(path: Path, tasks_root: Path) -> str:
    """Return the immediate ``tasks/`` subtree component for a task file."""
    rel = path.relative_to(tasks_root)
    return rel.parts[0] if len(rel.parts) > 1 else ""


# ---------------------------------------------------------------------------
# Git evidence
# ---------------------------------------------------------------------------

_UNIT = "\x1f"  # field separator
_REC = "\x1e"  # record separator


def _collect_git_completion(
    repo_root: Path, declared_ids: Set[str]
) -> tuple[bool, Dict[str, List[str]]]:
    """Map declared task id → completion-commit evidence via one ``git log`` pass.

    Returns ``(git_available, evidence)`` where ``evidence[id]`` is a list of
    ``"<short-sha> <subject>"`` strings for commits whose **subject** names the
    id with a conventional-completion type or completion verb. Candidate ids in
    the subject are resolved against ``declared_ids`` so a lower-case hash id is
    matched by identity, not by a fragile heuristic. A reference that appears
    only in a commit body is not counted as completion evidence.
    """
    evidence: Dict[str, List[str]] = {}
    try:
        proc = subprocess.run(
            [
                "git",
                "log",
                "--all",
                "--no-color",
                f"--format=%h{_UNIT}%s{_REC}",
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.info("git log unavailable in %s: %s", repo_root, exc)
        return False, evidence
    if proc.returncode != 0:
        logger.info("git log returned %s in %s", proc.returncode, repo_root)
        return False, evidence

    for record in proc.stdout.split(_REC):
        record = record.strip("\n")
        if not record or _UNIT not in record:
            continue
        short_sha, subject = record.split(_UNIT, 1)
        if not (_COMPLETION_TYPE_RE.search(subject) or _COMPLETION_VERB_RE.search(subject)):
            continue
        for candidate in _raw_candidates(subject):
            task_id = _resolve_candidate(candidate, declared_ids)
            if task_id is None:
                continue
            evidence.setdefault(task_id, [])
            entry = f"{short_sha} {subject.strip()}"
            if entry not in evidence[task_id]:
                evidence[task_id].append(entry)
    return True, evidence


# ---------------------------------------------------------------------------
# Feature-YAML rollups
# ---------------------------------------------------------------------------


def _collect_feature_completion(
    repo_root: Path, declared_ids: Set[str]
) -> Dict[str, List[str]]:
    """Map declared task id → feature-rollup evidence.

    A task id listed in a feature YAML whose ``status`` is terminal is inferred
    completed (evidence: ``"feature FEAT-X status=completed"``). The listed id is
    resolved against ``declared_ids`` so the evidence keys line up with task
    rows; ids the feature names but no task file declares are left for the
    dangling pass. Feature files are the same set the feature auditor reads.
    """
    evidence: Dict[str, List[str]] = {}
    feature_dir = repo_root / ".guardkit" / "features"
    if not feature_dir.is_dir():
        return evidence
    for yaml_path in sorted(feature_dir.glob("*.yaml")) + sorted(
        feature_dir.glob("*.yml")
    ):
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("Could not read feature YAML %s: %s", yaml_path, exc)
            continue
        if not isinstance(data, dict):
            continue
        feature_id = str(data.get("id", yaml_path.stem))
        status = str(data.get("status", ""))
        if _status_bucket(status) != TERMINAL:
            continue
        tasks = data.get("tasks", [])
        if not isinstance(tasks, (list, tuple)):
            continue
        for task in tasks:
            raw = task.get("id") if isinstance(task, dict) else task
            if not raw:
                continue
            task_id = _resolve_candidate(str(raw), declared_ids)
            if task_id is None:
                continue
            evidence.setdefault(task_id, [])
            entry = f"feature {feature_id} status={status}"
            if entry not in evidence[task_id]:
                evidence[task_id].append(entry)
    return evidence


# ---------------------------------------------------------------------------
# Dangling references
# ---------------------------------------------------------------------------


def _collect_references(
    repo_root: Path, globs: Sequence[str]
) -> Dict[str, Set[str]]:
    """Map every raw ``TASK-...`` candidate → the set of files that mention it.

    Raw candidates are resolved against the declared-id set by the caller;
    non-placeholder candidates only are kept.
    """
    references: Dict[str, Set[str]] = {}
    for pattern in globs:
        for path in sorted(repo_root.glob(pattern)):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = str(path.relative_to(repo_root))
            for candidate in _raw_candidates(text):
                if _id_is_placeholder(_trim_candidate(candidate)):
                    continue
                references.setdefault(candidate, set()).add(rel)
    return references


def _state_doc_exists(repo_root: Path, task_id: str) -> bool:
    """True when a ``docs/state/<id>*`` stub exists for the id."""
    state_root = repo_root / "docs" / "state"
    if not state_root.is_dir():
        return False
    return any(state_root.rglob(f"{task_id}*"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def audit_tasks(
    repo_root: Path,
    reference_globs: Optional[Sequence[str]] = None,
) -> TaskAuditReport:
    """Audit every task file under ``repo_root/tasks`` plus dangling references.

    Deterministic and read-only: no file under ``repo_root`` is modified.

    Parameters
    ----------
    repo_root:
        The repository to audit. Works against any repo root.
    reference_globs:
        Globs (repo-relative) scanned for task-id references when detecting
        dangling ids. Defaults to :data:`DEFAULT_REFERENCE_GLOBS`.

    Returns
    -------
    TaskAuditReport
    """
    repo_root = Path(repo_root)
    tasks_root = repo_root / "tasks"
    globs = tuple(reference_globs) if reference_globs is not None else DEFAULT_REFERENCE_GLOBS

    # First pass: index every declared task id. Frontmatter ``id`` is
    # authoritative; the filename-derived id is only a fallback for the (few)
    # files that lack one. The declared-id set then grounds every downstream
    # id resolution (git subjects, feature rollups, references).
    declared_files: Dict[str, List[Path]] = {}
    parsed: List[tuple[Path, str, dict, bool]] = []
    for path in _iter_task_files(repo_root):
        fm, malformed = _read_frontmatter(path)
        fm_id = str(fm.get("id", "")).strip()
        # Frontmatter id is authoritative. When absent, the full filename stem
        # is the fallback — it is unique per file, so slug-only names
        # (``TASK-DOC-api-reference`` vs ``TASK-DOC-changelog``) are NOT
        # collapsed into a phantom shared id. Bidirectional resolution still
        # matches a hash-form reference to such a stem.
        task_id = fm_id or path.stem
        if not task_id:
            continue
        declared_files.setdefault(task_id, []).append(path)
        parsed.append((path, task_id, fm, malformed))

    declared_ids: Set[str] = set(declared_files)

    git_available, git_evidence = _collect_git_completion(repo_root, declared_ids)
    feature_evidence = _collect_feature_completion(repo_root, declared_ids)

    rows: List[TaskAuditRow] = []
    for path, task_id, fm, malformed in parsed:
        subtree = _subtree_for(path, tasks_root)
        subtree_bucket = _subtree_bucket(subtree)
        raw_status = fm.get("status")
        fm_status = str(raw_status).strip() if raw_status is not None else None
        fm_bucket = _status_bucket(fm_status)
        declared_bucket = fm_bucket if fm_bucket != OTHER else subtree_bucket

        # Inferred status from git + feature rollups.
        evidence: List[str] = []
        evidence.extend(f"git: {e}" for e in git_evidence.get(task_id, []))
        evidence.extend(f"rollup: {e}" for e in feature_evidence.get(task_id, []))
        inferred_status = "completed" if evidence else "unknown"

        divergences: List[str] = []

        # (1) Frontmatter status and physical subtree disagree on terminal/open.
        if (
            fm_bucket != OTHER
            and subtree_bucket != OTHER
            and fm_bucket != subtree_bucket
        ):
            divergences.append("status_location_conflict")

        # (2) Tracker says open, but git/rollups show the work shipped.
        if declared_bucket == OPEN and inferred_status == "completed":
            divergences.append("inferred_completion_conflict")

        # (3) No status field at all — a tracker-integrity gap.
        if fm_status is None:
            divergences.append("missing_status")

        # (3b) A ``---`` fence exists but its YAML does not parse.
        if malformed:
            divergences.append("unparseable_frontmatter")

        # (4) Same id declared by more than one task file.
        if len(declared_files.get(task_id, [])) > 1:
            divergences.append("duplicate_task_file")

        rows.append(
            TaskAuditRow(
                task_id=task_id,
                file=str(path.relative_to(repo_root)),
                subtree=subtree,
                subtree_bucket=subtree_bucket,
                frontmatter_status=fm_status,
                declared_bucket=declared_bucket,
                inferred_status=inferred_status,
                inferred_evidence=evidence,
                divergences=divergences,
            )
        )

    # Dangling references: raw candidates referenced by features/code that
    # resolve to no declared task file. docs/state stubs do NOT count as
    # declaring (that is exactly the trio's failure mode). Unresolved candidates
    # are grouped by their trimmed display id so a slug-bearing ``file_path``
    # and a bare code reference to the same id collapse into one row.
    references = _collect_references(repo_root, globs)
    dangling_map: Dict[str, Set[str]] = {}
    for candidate, files in references.items():
        if _resolve_candidate(candidate, declared_ids) is not None:
            continue
        display_id = _trim_candidate(candidate)
        if len(display_id) <= len("TASK-"):
            continue
        dangling_map.setdefault(display_id, set()).update(files)

    dangling: List[DanglingReference] = [
        DanglingReference(
            task_id=display_id,
            referenced_by=sorted(dangling_map[display_id]),
            state_doc_exists=_state_doc_exists(repo_root, display_id),
        )
        for display_id in sorted(dangling_map)
    ]

    return TaskAuditReport(
        repo_root=str(repo_root),
        git_available=git_available,
        task_file_count=len(parsed),
        rows=rows,
        dangling=dangling,
    )
