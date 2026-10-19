"""Turn a bare file name in a task document into the one real path it means.

A task document's ``## Files to Create`` / ``## Files to Modify`` sections are
meant to hold repository-relative paths, but some of them carry a bare name as
well: the fix-task writer (``installer/core/lib/review_parser.py``) picks up
every backticked file name in a recommendation, so a recommendation that
names a file in full and later by its bare name (an invented example: "fix
`apps/shelf/src/Shelf.tsx`" and then "`Shelf.tsx` line 12") declares both
``apps/shelf/src/Shelf.tsx`` and ``Shelf.tsx``. The plan audit then looked
for the bare name at the top of the repository, did not find it, and refused
every turn of a repair task in build FEAT-D31F with "2 missing file(s)" while
the builder had edited exactly the right files.

The rule here is deliberately narrow:

* a name with a folder in it is left alone;
* a name that is a file at the top of the repository is left alone;
* a bare name that matches exactly one file in the repository (tracked, or
  new and not ignored) becomes that file's path;
* a bare name that matches two or more files stays as it is and is reported
  as ambiguous, so it still counts as missing - an ambiguous name must never
  pass silently;
* a bare name that matches nothing stays as it is, and is missing as before.

Nothing here assumes a language or a project layout: the only question asked
is which repository files carry that name.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from guardkit.lib.project_git import run_git

logger = logging.getLogger(__name__)


@dataclass
class BareNameResolution:
    """What happened to the bare names in one declared list."""

    paths: List[str] = field(default_factory=list)
    resolved: Dict[str, str] = field(default_factory=dict)
    ambiguous: Dict[str, List[str]] = field(default_factory=dict)


def is_bare_name(entry: str) -> bool:
    """True when ``entry`` names a file without any folder."""
    return "/" not in entry and "\\" not in entry


def repository_files(worktree_path: Path) -> Optional[List[str]]:
    """Every file git knows of or would add: tracked, plus new and not ignored.

    ``None`` when git could not answer, so the caller resolves nothing rather
    than guessing.
    """
    try:
        done = run_git(
            ["ls-files", "-co", "--exclude-standard"],
            cwd=worktree_path,
            check=False,
            timeout=30,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
        logger.warning("listing repository files failed (%s); bare names stay as written", exc)
        return None
    if done.returncode != 0:
        return None
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]


def resolve_bare_names(
    declared: Optional[Sequence[str]],
    *,
    worktree_path: Path,
    candidates: Iterable[str],
    excluded: Optional[Callable[[str], bool]] = None,
) -> Optional[BareNameResolution]:
    """Resolve the bare names in one declared list against ``candidates``.

    ``declared`` of ``None`` (the section is absent) stays ``None``: no claim
    was made, so none is invented. The returned ``paths`` keep the declared
    order with duplicates removed, so ``apps/shelf/src/Shelf.tsx`` declared
    once in full and once as ``Shelf.tsx`` is one planned file.
    """
    if declared is None:
        return None

    by_name: Dict[str, List[str]] = {}
    for candidate in candidates:
        if excluded is not None:
            try:
                if excluded(candidate):
                    continue
            except Exception:  # noqa: BLE001 - a broken filter keeps the file
                pass
        by_name.setdefault(PurePosixPath(candidate).name, []).append(candidate)

    result = BareNameResolution()
    for entry in declared:
        chosen = entry
        if is_bare_name(entry) and not (worktree_path / entry).exists():
            matches = sorted(set(by_name.get(entry, [])))
            if len(matches) == 1:
                chosen = matches[0]
                result.resolved[entry] = chosen
            elif len(matches) > 1:
                result.ambiguous[entry] = matches
        if chosen not in result.paths:
            result.paths.append(chosen)
    return result
