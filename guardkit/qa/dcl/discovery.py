"""DCL artifact discovery (Phase D, design §1 / D1).

The ``dcl`` track's analogue of the BDD tag scan
(:func:`guardkit.orchestrator.quality_gates.bdd_runner.find_feature_files_with_tag`,
bdd_runner.py:227): a cheap text scan for a ``@task:<TASK-ID>`` marker inside a
``.dcl`` file's comments. ``.dcl`` capabilities live at
``features/<slug>/<slug>.dcl`` and carry a ``// @task:TASK-ID`` comment line
(design §1); discovery walks ``features/`` recursively.

This lives in the ``dcl`` package, NOT in ``bdd_runner.py`` — the Gherkin chain
is never modified (design §0.1). ``bdd_runner.py`` stays byte-for-byte untouched.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

__all__ = ["find_dcl_files_with_tag", "task_tag"]

#: Dotdirs and vendored dirs are skipped — the same exclusions the BDD scan uses
#: so a vendored ``.dcl`` shipped with a third-party package is never mistaken
#: for a project capability.
_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {"node_modules", "__pycache__", "site-packages"}
)


def task_tag(task_id: str) -> str:
    """The literal marker a ``.dcl`` carries to bind itself to a task."""
    return f"@task:{task_id}"


def find_dcl_files_with_tag(features_dir: Path, tag: str) -> List[Path]:
    """Return ``.dcl`` files containing the literal ``tag`` string.

    The check is a cheap text scan, not a DCL parse — if ``tag`` (e.g.
    ``@task:TASK-STAT-001``) appears anywhere in the file we treat it as a
    candidate; the compile gate + derivation do the real work downstream. This
    mirrors :func:`find_feature_files_with_tag` exactly.

    Recursive discovery over ``features/<slug>/<slug>.dcl``. Dotdirs (``.venv``,
    ``.git``, ...) and known vendored dirs (``node_modules``, ``__pycache__``,
    ``site-packages``) are excluded.
    """
    matches: List[Path] = []
    if not features_dir.is_dir():
        return matches
    for fp in sorted(features_dir.rglob("*.dcl")):
        rel_parts = fp.relative_to(features_dir).parts
        if any(
            part.startswith(".") or part in _EXCLUDED_DIR_NAMES
            for part in rel_parts
        ):
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.debug("Could not read %s: %s", fp, exc)
            continue
        if tag in text:
            matches.append(fp)
    return matches
