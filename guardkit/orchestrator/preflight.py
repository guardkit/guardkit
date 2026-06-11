"""Preflight existence check for feature task ``## Files to Modify`` paths.

Catches task-author typos at feature-load time (≤1s) instead of letting them
burn 25-35 minutes per occurrence at Player turn 4-5 via the plan-audit gate.

The check is target-repo agnostic: it operates on the guardkit task-file
convention (``## Files to Modify`` / ``## Files to Create`` sections defined
by ``PlanMarkdownParser``) using inputs already passed into
``FeatureOrchestrator``: ``feature.tasks``, ``repo_root``, ``worktree_path``.

See TASK-GK-PR-001 for design rationale.
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from installer.core.commands.lib.plan_markdown_parser import PlanMarkdownParser

logger = logging.getLogger(__name__)

__all__ = [
    "INDEXED_EXTENSIONS",
    "EXCLUDED_PATH_FRAGMENTS",
    "PreflightTypo",
    "PreflightTypoError",
    "preflight_validate",
]


# Multi-language source extensions indexed for fuzzy-match suggestions.
# Held as a module-level constant so a target repo can extend it without
# touching the algorithm. Extending to additional languages is a follow-up
# (see TASK-GK-PR-001 "Out of Scope").
INDEXED_EXTENSIONS = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".cs",
    ".go",
    ".java",
    ".rb",
    ".rs",
)

# Path fragments excluded from the on-disk index. Avoid double-indexing
# nested worktrees, virtualenvs, and build/cache artefacts.
EXCLUDED_PATH_FRAGMENTS = (
    "/.venv/",
    "/__pycache__/",
    "/.git/",
    "/node_modules/",
    "/dist/",
    "/build/",
    "/.guardkit/worktrees/",
)

@dataclass
class PreflightTypo:
    """A declared path that does not resolve to an existing file on disk.

    Attributes
    ----------
    task_id : str
        The task that declared the path (e.g. ``"TASK-XXX-YYYY"``).
    line : int
        Absolute line number within the task markdown file (1-indexed).
        ``0`` if the line could not be resolved (defensive default).
    declared_path : str
        The path string as it appears under ``## Files to Modify`` /
        ``## Files to Create``.
    suggestions : List[str]
        Up to three closest on-disk matches from ``difflib.get_close_matches``
        with ``cutoff=0.5``. Empty list if no close matches were found.
    kind : str
        Either ``"modify"`` (for ``## Files to Modify``) or ``"create"`` (for
        ``## Files to Create``). Determines how the typo is reported.
    """

    task_id: str
    line: int
    declared_path: str
    suggestions: List[str] = field(default_factory=list)
    kind: str = "modify"


class PreflightTypoError(Exception):
    """Raised when ``preflight_strict=True`` and modify-axis typos are found.

    The exception's ``typos`` attribute carries the full list of offending
    declarations so callers can render a richer report than the formatted
    message alone.
    """

    def __init__(self, typos: List[PreflightTypo]):
        self.typos = typos
        super().__init__(self._format(typos))

    @staticmethod
    def _format(typos: List[PreflightTypo]) -> str:
        lines = ["Preflight detected task-author typos in `## Files to Modify`:"]
        for t in typos:
            lines.append(f"  TYPO in {t.task_id} line {t.line}:")
            lines.append(f"    declared: {t.declared_path}")
            if t.suggestions:
                lines.append("    closest matches (top 3):")
                for s in t.suggestions:
                    lines.append(f"      - {s}")
            else:
                lines.append("    no close matches found on disk")
        return "\n".join(lines)


def _build_file_index(
    repo_root: Path, worktree_path: Optional[Path]
) -> List[str]:
    """Scan ``repo_root`` and ``worktree_path`` for source files.

    Returns relative-to-root path strings for fuzzy matching. Both roots
    are scanned (paths from each are expressed relative to their own
    root) so a fuzzy match can hit either tree.
    """
    indexed: List[str] = []
    seen_roots: List[Path] = []
    for root in (repo_root, worktree_path):
        if root is None:
            continue
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if not resolved.exists():
            continue
        # Skip duplicate root (e.g. when worktree_path == repo_root)
        if any(resolved == r for r in seen_roots):
            continue
        seen_roots.append(resolved)
        for p in resolved.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix not in INDEXED_EXTENSIONS:
                continue
            s = str(p)
            if any(frag in s for frag in EXCLUDED_PATH_FRAGMENTS):
                continue
            try:
                indexed.append(str(p.relative_to(resolved)))
            except ValueError:
                # File outside the resolved root (shouldn't happen with rglob)
                continue
    return indexed


def _path_exists(
    declared: str, repo_root: Path, worktree_path: Optional[Path]
) -> bool:
    """Return ``True`` if ``declared`` resolves under either root."""
    if (repo_root / declared).exists():
        return True
    if worktree_path is not None and (worktree_path / declared).exists():
        return True
    return False


def _strip_path_from_item(item: str) -> str:
    """Return just the path part of a ``_extract_list_section`` item.

    ``PlanMarkdownParser._extract_list_section`` returns items in two shapes:
    - ``"path/to/file.py"`` (clean path)
    - ``"path/to/file.py - description"`` (path + dash-separated description)

    This helper trims the description suffix and any whitespace so the
    declared path can be probed against the filesystem.
    """
    # Split on " - " (space-dash-space) to remove descriptions; preserves
    # paths like "name-with-dash.py".
    return item.split(" - ", 1)[0].strip()


def _find_line_number(body: str, declared: str) -> int:
    """Find the 1-indexed line number where ``declared`` appears in ``body``.

    Used purely for diagnostic reporting. Returns ``0`` if the path
    cannot be located (defensive — the bullet line should always be in
    the body since we extracted it from there).
    """
    for idx, line in enumerate(body.splitlines(), start=1):
        if declared in line:
            return idx
    return 0


def preflight_validate(
    feature,
    repo_root: Path,
    worktree_path: Optional[Path],
    strict: bool = False,
) -> List[PreflightTypo]:
    """Validate every queued task's ``## Files to Modify`` block against disk.

    For every task in ``feature.tasks``:

    - Each path declared under ``## Files to Modify`` must exist either at
      ``repo_root / path`` or at ``worktree_path / path``. If neither
      resolves, a :class:`PreflightTypo` with kind ``"modify"`` is added
      to the result list with ``difflib`` suggestions against the actual
      on-disk tree.

    - Each path declared under ``## Files to Create`` must NOT exist
      (else the "to-create" semantics is wrong). If it does, a WARNING
      log line is emitted; the typo list is unchanged. (Create-axis
      issues never abort, by design — they may be legitimate re-runs in
      preserved worktrees.)

    Parameters
    ----------
    feature
        A :class:`guardkit.orchestrator.feature_loader.Feature` instance.
        Imported lazily / structurally to avoid circular imports.
    repo_root : Path
        Repository root. Required.
    worktree_path : Path or None
        Optional worktree root. If ``None``, only ``repo_root`` is probed.
    strict : bool
        When ``True`` and the modify-axis typo list is non-empty, raise
        :class:`PreflightTypoError` instead of returning. When ``False``
        (default), log each typo at WARNING level and return the list
        for caller introspection.

    Returns
    -------
    List[PreflightTypo]
        Modify-axis typos found. Empty when no problems detected.

    Raises
    ------
    PreflightTypoError
        If ``strict=True`` and one or more modify-axis typos were found.
    """
    file_index = _build_file_index(repo_root, worktree_path)
    parser = PlanMarkdownParser()

    typos: List[PreflightTypo] = []
    for task in feature.tasks:
        task_path = repo_root / task.file_path
        if not task_path.exists() or not task_path.is_file():
            continue
        try:
            content = task_path.read_text(encoding="utf-8")
        except OSError:
            continue

        # Strip frontmatter so line numbers in error messages match the
        # body where the bullet appears. We still report the absolute
        # line in the body; readers cross-reference by section, not
        # by editor-line number, so body-relative is the correct frame.
        body = _strip_frontmatter(content)

        for kind, section_pattern in (
            ("modify", r"## Files to Modify\s*\n(.*?)(?=\n##|\Z)"),
            ("create", r"## Files to Create\s*\n(.*?)(?=\n##|\Z)"),
        ):
            items = parser._extract_list_section(body, section_pattern)
            for item in items:
                declared = _strip_path_from_item(item)
                if not declared:
                    continue
                # Only probe paths whose extension we index. Skip prose
                # bullets like "(Possibly) src/foo.py — new module".
                if not declared.endswith(INDEXED_EXTENSIONS):
                    continue
                # Reject paths with parenthetical / leading non-path
                # tokens (the bullet body is "(Possibly) src/foo.py").
                if " " in declared or declared.startswith(("(", "[")):
                    continue
                exists = _path_exists(declared, repo_root, worktree_path)
                if kind == "modify" and not exists:
                    suggestions = difflib.get_close_matches(
                        declared, file_index, n=3, cutoff=0.5
                    )
                    typos.append(
                        PreflightTypo(
                            task_id=task.id,
                            line=_find_line_number(body, declared),
                            declared_path=declared,
                            suggestions=suggestions,
                            kind=kind,
                        )
                    )
                elif kind == "create" and exists:
                    logger.warning(
                        "%s declares ## Files to Create: %s, but file "
                        "already exists on disk. Is this a re-run of a "
                        "previous attempt? Player will treat as no-op or "
                        "rewrite.",
                        task.id,
                        declared,
                    )

    if typos:
        if strict:
            raise PreflightTypoError(typos)
        for t in typos:
            logger.warning(
                "TYPO in %s ## Files to Modify (line %d): declared %s "
                "not on disk under repo_root or worktree_path. "
                "Closest match(es): %s. plan-audit will fire on turn 1; "
                "consider correcting before --resume.",
                t.task_id,
                t.line,
                t.declared_path,
                ", ".join(t.suggestions) or "(none)",
            )
    return typos


def _strip_frontmatter(content: str) -> str:
    """Return the markdown body with YAML frontmatter removed.

    Frontmatter is delimited by ``---`` lines. If the document does not
    start with a frontmatter block, the content is returned unchanged.
    """
    if not content.startswith("---"):
        return content
    try:
        end_idx = content.index("\n---", 3)
    except ValueError:
        return content
    return content[end_idx + len("\n---") :].lstrip("\n")
