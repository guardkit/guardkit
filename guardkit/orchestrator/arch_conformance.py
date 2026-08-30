"""Watch where the code sits against the repo's own architecture rules, and write it down.

WHAT THIS IS, AND WHAT IT IS NOT (2026-08-30)
---------------------------------------------
A repository can write down how it is meant to be built — "database queries live in
crud.py", "one feature does not import another feature" — in
``docs/architecture-rules.yaml``, and ``guardkit.conformance`` reads that file and
reports every place the code sits somewhere the rule did not name.

This module is the first and smallest step of wiring that checker into the build: after
each Coach turn it runs the checker over the build worktree and writes the checker's
own facts-only report next to that turn's Coach verdict.

**Nothing reads the receipt.** It changes no Coach verdict, raises no issue for the
Player, appears on no card, and is read by nothing at merge time. There is no switch to
turn it on or off, because there is nothing to turn on. It writes one file and logs one
line. That is deliberately the whole of it: the design's ladder puts watching first, so
that the receipts exist to be looked at before anything is allowed to act on them.

WHAT IT COSTS A BUILD
---------------------
Almost nothing, and nothing at all in a repository that has not written a rules file.
The checker reads the rules file before it reads any source, so a repository without one
returns immediately and this writes one small receipt saying so. Most repositories in
this estate have no rules file yet; that must cost a build one receipt and no more.

Absence is recorded, never silent. A missing rules file produces the checker's own
honest "could not run" report — nothing was checked, which is not the same as clean.

IT NEVER BREAKS A BUILD
-----------------------
Everything here sits inside one try/except (the same discipline as the Hurl twin
coverage check and the QAV shadow). If the checker raises, or the receipt cannot be
written, this logs one warning and the build carries on exactly as it would have.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# The rules file this looks for in the build worktree. The checker owns the same
# constant; it is repeated here only so the log lines and the docstring above can name
# it without importing the checker at module load.
RULES_RELATIVE_PATH = "docs/architecture-rules.yaml"


def _receipt_path(worktree_path: Path, task_id: str, turn: int) -> Path:
    """Where this turn's receipt goes: beside the turn's Coach verdict.

    Uses the ``paths.py`` template so there is one place that knows the layout, with a
    literal fallback so an import quirk can never stop the receipt being written.
    """
    rel = ".guardkit/autobuild/{task_id}/arch_conformance_turn_{turn}.json"
    try:
        from guardkit.orchestrator.paths import TaskArtifactPaths

        return TaskArtifactPaths.arch_conformance_path(task_id, turn, Path(worktree_path))
    except Exception:  # noqa: BLE001 — an import quirk must not stop the receipt
        return Path(worktree_path) / rel.format(task_id=task_id, turn=turn)


def _relative_files(worktree_path: Path, changed_files: Optional[Iterable[str]]) -> list[str]:
    """The task's touched files as repository-relative POSIX paths.

    The Player reports the files it created and modified; some entries arrive absolute
    and some already relative. The checker compares them against paths it built with
    ``relative_to(repo).as_posix()``, so both shapes are put into that one shape here.
    Anything outside the worktree is dropped: a path this repository does not contain
    can never match a file the checker read.
    """
    root = Path(worktree_path).resolve()
    out: list[str] = []
    for entry in changed_files or []:
        if not entry:
            continue
        p = Path(str(entry))
        try:
            if p.is_absolute():
                rel = p.resolve().relative_to(root).as_posix()
            else:
                rel = p.as_posix().lstrip("./")
        except ValueError:
            continue  # not inside this worktree
        if rel:
            out.append(rel)
    return sorted(set(out))


def write_turn_receipt(
    worktree_path: Path,
    task_id: str,
    turn: int,
    changed_files: Optional[Iterable[str]] = None,
) -> tuple[Path, int]:
    """Run the checker over the worktree and write its report beside the Coach verdict.

    Returns the receipt path and the number of findings the report lists. Raises on any
    failure; ``observe_task_conformance`` is the caller that swallows those.

    SCOPE — changed files, when the Player has named any.
    The checker supports being narrowed to the files a change touched: every rule still
    runs over the whole source tree, so counts like "nine of the eleven other query
    sites are in crud.py" stay true, but only the findings in this task's own files are
    listed. That is the right scope here, because a build turn should be shown what this
    task did, not what the repository has always done. When the Player has named no
    files yet — the first turn of a task that has written nothing — narrowing to an
    empty list would report on nothing at all, so the whole tree is reported on instead
    and the receipt says which was done.
    """
    from guardkit.conformance import run, to_json

    worktree = Path(worktree_path)
    scope = _relative_files(worktree, changed_files)
    report = run(worktree, diff_scope=scope or None)
    if not scope:
        report.notes.append(
            "This task had named no changed files when this ran, so the whole source "
            "tree was reported on rather than a change within it.")

    payload = to_json(report)
    path = _receipt_path(worktree, task_id, turn)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path, len(payload.get("findings") or [])


def observe_task_conformance(
    worktree_path: Path,
    task_id: str,
    turn: int,
    changed_files: Optional[Iterable[str]] = None,
) -> Optional[Path]:
    """Write this turn's receipt. Never raises, never changes anything, logs one line.

    Returns the receipt path, or None if it could not be written — in which case one
    warning has been logged and the build is untouched.
    """
    try:
        path, findings = write_turn_receipt(
            worktree_path, task_id, turn, changed_files
        )
        logger.info(
            "Architecture rules receipt for %s turn %s: %s (%d finding(s); "
            "nothing reads this).",
            task_id,
            turn,
            path,
            findings,
        )
        return path
    except Exception as exc:  # noqa: BLE001 — this can never fail a build
        logger.warning(
            "Architecture rules check raised %s for %s turn %s; no receipt written "
            "and the build is untouched.",
            exc.__class__.__name__,
            task_id,
            turn,
        )
        return None
