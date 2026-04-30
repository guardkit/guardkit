"""wave_overlap_detector.py — plan-time source-file overlap check (TASK-FIX-A7B3).

Purpose
-------
Detect whether multiple tasks scheduled into the same parallel-execution wave
edit overlapping source files. Fires from inside ``generate_feature_yaml.py``
after :func:`build_parallel_groups` produces the wave layout, before the
feature YAML is written. Sibling of TASK-FIX-A7B2's runtime safety net in
``coach_validator._detect_source_file_contention``.

The most common collision — and the one that broke FEAT-70A4 in the sibling
study-tutor repo — is two tasks both writing step definitions to a shared
``features/<slug>/test_<slug>.py`` glue module. The runtime defence catches
the conflict after both Players have committed inconsistent state to the
shared branch; this plan-time defence prevents the conflict from being
scheduled in the first place.

Inference is best-effort, from task-description prose only. Inputs:

* Explicit code-block paths (backtick-quoted file paths in description / ACs).
* ``## Files Likely To Change`` section, if present.
* Seam-test / BDD glue references — paths under ``features/<slug>/test_<slug>.py``
  matched directly OR inferred when a task names ``features/<slug>/<x>.feature``
  alongside step-definition language.

Out of scope: static analysis of source-file imports to discover transitive
edits, and cross-wave overlap (cross-wave edits are sequential by construction).

Architectural shape
-------------------
Pure functions over plain data. The module owns:

* :func:`infer_task_files` — derive a per-task edit set from prose.
* :func:`compute_wave_overlaps` — pairwise overlap detection within each wave.
* :func:`serialize_overlapping_groups` — split offending parallel groups into
  sequential follow-on entries, when ``--auto-serialise-overlap`` is set.
* :func:`format_overlap_warning_summary` — stdout banner mirroring the
  AC-linter's :func:`format_warning_summary` shape.

Mirrors the producer-runs-check pattern of ``ac_linter`` and the
BDD-oracle / smoke-gates nudges already wired into ``generate_feature_yaml.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Mapping, Sequence, Set, Tuple

__all__ = [
    "OverlapWarning",
    "infer_task_files",
    "compute_wave_overlaps",
    "serialize_overlapping_groups",
    "format_overlap_warning_summary",
    "warnings_to_dict",
]


# --- Inference patterns -----------------------------------------------------

# Conservative: only path-like strings ending in known source extensions count.
# Catches things like:
#   features/foo/test_foo.py
#   features/foo.feature
#   src/auth/login.py
#   tests/unit/test_x.py
#   guardkit/orchestrator/quality_gates/coach_validator.py
# Excludes leading punctuation; allows backticks/quotes/parens around the path
# via the boundary characters in the surrounding match.
# Order matters: Python regex alternation is leftmost-first, so longer
# extensions must precede shorter prefixes (``tsx`` before ``ts``,
# ``jsx`` before ``js``, ``yaml`` before ``yml``, ``csproj`` before ``cs``).
# Otherwise the regex commits to the short prefix and drops the trailing
# character (``app/bar.tsx`` → ``app/bar.ts``).
_PATH_EXTENSIONS = (
    "feature",
    "csproj",
    "yaml",
    "tsx",
    "jsx",
    "json",
    "toml",
    "yml",
    "py",
    "ts",
    "js",
    "cs",
    "md",
    "sql",
    "rb",
    "go",
)
_PATH_RE = re.compile(
    r"(?P<path>[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+\.(?:" + "|".join(_PATH_EXTENSIONS) + r"))"
)

# A wildcard glob form like ``features/*/test_*.py`` should NOT be inferred as
# a literal edit path — it's a description of a *class* of files. We strip
# anything containing ``*`` before merging into the edit set.
_GLOB_RE = re.compile(r"[*?]")

# Phrases that suggest the task touches the BDD glue module for a given
# feature slug, even if the task description names only the ``.feature`` file
# explicitly. Matched case-insensitively; presence of any one of these in
# combination with a ``features/<slug>/...`` reference triggers the AC-006
# inference for ``features/<slug>/test_<slug>.py``.
_BDD_GLUE_HINTS = (
    "step definition",
    "step definitions",
    "step_def",
    "step_defs",
    "stepdef",
    "stepdefs",
    "bdd glue",
    "glue module",
    "glue file",
    "@given",
    "@when",
    "@then",
    "pytest-bdd",
    "scenarios(",
)

# A ``.feature`` file under ``features/<slug>/...`` or ``features/<slug>.feature``.
# Captures ``<slug>`` so we can derive the conventional glue file
# ``features/<slug>/test_<slug>.py``. This convention matches the FEAT-70A4
# study-tutor failure mode (TASK-FIX-A7B2 §Notes).
_FEATURE_SLUG_RE = re.compile(r"features/(?P<slug>[A-Za-z0-9_-]+)(?:/[^/\s]+)?\.feature")

# A ``## Files Likely To Change`` section heading. Markdown ATX-style only;
# the task template GuardKit ships uses this heading verbatim.
_FILES_SECTION_RE = re.compile(
    r"(?im)^[ \t]*#{1,6}[ \t]*Files\s+Likely\s+To\s+Change[ \t]*$"
)


# --- Public dataclass --------------------------------------------------------

@dataclass(frozen=True)
class OverlapWarning:
    """A single intra-wave overlap finding.

    Two or more tasks within ``wave_index`` (1-based for human display) edit
    the file set ``files``. ``task_ids`` is sorted for stable output.
    """

    wave_index: int
    task_ids: Tuple[str, ...]
    files: Tuple[str, ...]

    def to_dict(self) -> Dict[str, object]:
        return {
            "wave_index": self.wave_index,
            "task_ids": list(self.task_ids),
            "files": list(self.files),
        }


# --- Inference --------------------------------------------------------------

def _gather_text(task: Mapping[str, object]) -> str:
    """Concatenate task fields that may carry path mentions.

    Inspects ``name``, ``description``, and any iterable ``acceptance_criteria``.
    Order doesn't matter — downstream uses set semantics.
    """
    parts: List[str] = []
    for key in ("name", "title", "description"):
        value = task.get(key)
        if isinstance(value, str):
            parts.append(value)
    acs = task.get("acceptance_criteria")
    if isinstance(acs, (list, tuple)):
        for item in acs:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, Mapping):
                # Some upstream paths pass ACs as dicts with ``text`` fields.
                text = item.get("text") or item.get("description") or ""
                if isinstance(text, str):
                    parts.append(text)
    return "\n".join(parts)


def _extract_paths(text: str) -> Set[str]:
    """Find concrete file-path mentions in ``text``.

    Strips wildcard globs and trims trailing punctuation that the regex may
    grab when paths appear at the end of a sentence (e.g. ``foo.py.``).
    """
    paths: Set[str] = set()
    for match in _PATH_RE.finditer(text):
        candidate = match.group("path").rstrip(".,;:)")
        if not candidate:
            continue
        if _GLOB_RE.search(candidate):
            # Glob patterns describe a class of files, not a specific edit.
            continue
        paths.add(candidate)
    return paths


def _has_bdd_glue_hint(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _BDD_GLUE_HINTS)


def _infer_bdd_glue_paths(text: str) -> Set[str]:
    """Add ``features/<slug>/test_<slug>.py`` for every referenced ``.feature`` slug.

    Per AC-006, only fires when the task description carries one of the
    BDD-glue hint phrases. Without that gate, a task that merely cites a
    ``.feature`` file as documentation would get a phantom glue edit.
    """
    if not _has_bdd_glue_hint(text):
        return set()
    inferred: Set[str] = set()
    for match in _FEATURE_SLUG_RE.finditer(text):
        slug = match.group("slug")
        if slug:
            inferred.add(f"features/{slug}/test_{slug}.py")
    return inferred


def infer_task_files(task: Mapping[str, object]) -> FrozenSet[str]:
    """Derive a best-effort source-file edit set from a task's prose.

    Combines explicit path mentions across name/description/ACs with the
    AC-006 BDD-glue inference. Pure function; safe to call repeatedly.

    Returns a :class:`frozenset` so callers can use it as a dict value
    without worrying about accidental mutation.
    """
    text = _gather_text(task)
    if not text.strip():
        return frozenset()

    paths = _extract_paths(text)
    paths.update(_infer_bdd_glue_paths(text))
    return frozenset(paths)


# --- Overlap detection ------------------------------------------------------

def compute_wave_overlaps(
    parallel_groups: Sequence[Sequence[str]],
    task_files: Mapping[str, FrozenSet[str]],
) -> List[OverlapWarning]:
    """Return one :class:`OverlapWarning` per wave that has intra-wave overlap.

    Multiple tasks in the same wave that share *any* file aggregate into a
    single warning per wave — the warning lists every task in that wave that
    contributed to a non-empty pairwise intersection, plus the union of the
    intersecting files. This matches the runtime contention message format
    in ``coach_validator._detect_source_file_contention``: report the wave,
    the colliding peers, and the files at fault.

    Waves with ``len(tasks) <= 1`` are skipped (AC-002). Tasks with no
    inferred files are skipped silently (no false positives on disjoint or
    unparseable plans, AC-005).
    """
    warnings: List[OverlapWarning] = []

    for wave_index_zero, group in enumerate(parallel_groups):
        if len(group) <= 1:
            continue

        # Pairwise intersections, accumulated into a per-wave bucket.
        offending_tasks: Set[str] = set()
        offending_files: Set[str] = set()

        for i, task_a in enumerate(group):
            files_a = task_files.get(task_a, frozenset())
            if not files_a:
                continue
            for task_b in group[i + 1:]:
                files_b = task_files.get(task_b, frozenset())
                if not files_b:
                    continue
                shared = files_a & files_b
                if shared:
                    offending_tasks.add(task_a)
                    offending_tasks.add(task_b)
                    offending_files.update(shared)

        if offending_tasks:
            warnings.append(
                OverlapWarning(
                    wave_index=wave_index_zero + 1,
                    task_ids=tuple(sorted(offending_tasks)),
                    files=tuple(sorted(offending_files)),
                )
            )

    return warnings


# --- Auto-serialise ---------------------------------------------------------

def serialize_overlapping_groups(
    parallel_groups: Sequence[Sequence[str]],
    overlaps: Sequence[OverlapWarning],
) -> Tuple[List[List[str]], List[str]]:
    """Split offending parallel groups into sequential follow-on entries.

    For each wave flagged by ``overlaps``, the offending tasks are pulled
    out and each is given its own follow-on wave. This is the only split
    shape that actually breaks the parallel conflict — keeping multiple
    offenders together in a single follow-on wave preserves the same
    file-write race that triggered the warning.

    Non-offending peers stay in the original wave (its position is preserved).
    Original task order is preserved within both the kept-wave and the
    follow-on series, so dependency wiring remains deterministic.

    Returns ``(new_groups, info_notes)`` — ``info_notes`` describes each
    split for the caller to print under ``--auto-serialise-overlap``.
    """
    if not overlaps:
        return [list(g) for g in parallel_groups], []

    overlap_by_wave: Dict[int, OverlapWarning] = {w.wave_index: w for w in overlaps}
    new_groups: List[List[str]] = []
    info_notes: List[str] = []

    for wave_index_zero, group in enumerate(parallel_groups):
        wave_index = wave_index_zero + 1
        warning = overlap_by_wave.get(wave_index)
        if warning is None:
            new_groups.append(list(group))
            continue

        offenders_set = set(warning.task_ids)
        kept = [t for t in group if t not in offenders_set]
        # Preserve original task order within the offender bucket so the
        # split is reproducible — sorted task_ids on the warning are for
        # display only.
        offenders_in_order = [t for t in group if t in offenders_set]

        if kept:
            new_groups.append(kept)
        # Each offender gets its own sequential follow-on wave. For 2 offenders
        # this produces ``[A], [B]`` ("two sequential entries", per AC-003);
        # for 3+ offenders the same shape generalises naturally.
        for offender in offenders_in_order:
            new_groups.append([offender])

        info_notes.append(
            f"Wave {wave_index}: split off {', '.join(offenders_in_order)} "
            f"into {len(offenders_in_order)} sequential follow-on wave(s) "
            f"due to file overlap on {', '.join(warning.files)}"
        )

    return new_groups, info_notes


# --- Formatting -------------------------------------------------------------

_BANNER = "Wave overlap (plan-time) check"


def format_overlap_warning_summary(
    warnings: Sequence[OverlapWarning],
    *,
    auto_serialise: bool = False,
) -> str:
    """Render the stdout banner for the producer callsite.

    Mirrors the shape of :func:`ac_linter.format_warning_summary` so the
    feature-plan stdout transcript reads consistently. When
    ``auto_serialise=True``, the banner notes that the planner already
    rewrote the wave layout — otherwise it tells the user how to opt in.
    """
    if not warnings:
        return ""

    lines: List[str] = []
    lines.append(f"⚠️  {_BANNER}: {len(warnings)} wave(s) with file overlap")
    for warning in warnings:
        lines.append(
            f"   Wave {warning.wave_index}: {', '.join(warning.task_ids)} "
            f"share file(s) {', '.join(warning.files)}"
        )

    if auto_serialise:
        lines.append("")
        lines.append(
            "   --auto-serialise-overlap was set: offending tasks moved to a "
            "follow-on sequential wave."
        )
    else:
        lines.append("")
        lines.append(
            "   These tasks are scheduled to run in parallel but appear to "
            "edit the same file(s)."
        )
        lines.append(
            "   Re-run with --auto-serialise-overlap to split the offending "
            "wave automatically, or restructure dependencies."
        )

    return "\n".join(lines)


def warnings_to_dict(warnings: Iterable[OverlapWarning]) -> List[Dict[str, object]]:
    """Serialise warnings for the optional ``wave_overlap_warnings`` YAML block."""
    return [w.to_dict() for w in warnings]
