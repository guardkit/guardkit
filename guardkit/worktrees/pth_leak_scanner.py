"""
Detect dangling editable ``_editable_impl_*.pth`` references in known
parent venv roots before a worktree is removed.

This is Layer 3 (defense-in-depth) on top of TASK-FIX-FF61 (Layer 1):
even though FF61 makes parent-venv leaks impossible at write time, an
independent verification at the cleanup boundary is the prescribed
remediation for the *absence-of-failure-is-not-success* class of defect
(see ``.claude/rules/absence-of-failure-is-not-success.md``).

The scanner is **read-only**, **never raises**, and **never aborts
cleanup**. It only emits a warning per leak with a copy-pasteable
repair command.

See:
    - ``.claude/reviews/TASK-REV-FFC6-review-report.md`` (Sequence 6)
    - tasks/in_progress/autobuild-bootstrap-venv-isolation/
      TASK-FIX-FF62-feature-complete-detect-and-warn-on-pth-leak.md
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple


logger = logging.getLogger(__name__)


# ============================================================================
# Constants — narrow by design (see "Out Of Scope" in FF62 task file)
# ============================================================================

# Scan roots relative to repo_root. Future extensions (Conda, pyenv, asdf)
# are explicitly out of scope per the task description.
_SCAN_ROOTS: Tuple[str, ...] = (".venv", ".guardkit/venv")

# Glob within each scan root. Matches uv's editable-impl naming convention.
# NOTE: must NOT match generic .pth files (easy-install.pth, distribution
# .pth files), or every site-packages registration would warn.
_EDITABLE_IMPL_GLOB = "lib/python*/site-packages/_editable_impl_*.pth"

# One-line warning template (printed once per leaking .pth file).
# NOTE: deliberately uses "WARNING:" rather than a "[warning]" prefix so
# Rich's markup parser doesn't eat the leading token when console.print
# is the sink. See test_warns_but_does_not_abort.
_WARNING_TEMPLATE = (
    "WARNING: Editable install in {venv_root} points into worktree "
    "being removed:\n"
    "  {pth_file}\n"
    "  Repair: cd {repo_root} && uv pip install -e . --no-deps"
)


# ============================================================================
# Scanner
# ============================================================================


def find_pth_leaks(
    repo_root: Path,
    worktree_path: Path,
) -> List[Tuple[Path, str]]:
    """
    Return every editable ``_editable_impl_*.pth`` whose contents reference
    ``worktree_path`` under the known parent venv roots.

    Read-only. Never raises. Returns ``[]`` for any of:

    - ``repo_root`` does not exist
    - no scan-root subdirectory exists (e.g. pure Node project)
    - no ``_editable_impl_*.pth`` files found
    - all ``.pth`` files reference unrelated paths
    - the scan root is a symlink (not followed, per AC-009)
    - a ``.pth`` file is unreadable (permission error, decode error)

    Parameters
    ----------
    repo_root : Path
        Repository root containing ``.venv`` and/or ``.guardkit/venv``.
    worktree_path : Path
        The worktree about to be removed; its absolute string form is
        substring-matched against each ``.pth`` file's lines.

    Returns
    -------
    List[Tuple[Path, str]]
        ``(pth_file, matching_line)`` for each leak. Empty list if no
        leaks (including the all-error / all-missing cases).
    """
    leaks: List[Tuple[Path, str]] = []

    if not repo_root or not Path(repo_root).exists():
        return leaks

    # Resolve the worktree to an absolute path so substring-matching
    # against absolute .pth contents works regardless of caller cwd.
    try:
        needle = str(Path(worktree_path).resolve())
    except OSError:
        return leaks

    for scan_root in _SCAN_ROOTS:
        venv_dir = Path(repo_root) / scan_root

        # AC-009: do NOT follow symlinks. A symlinked .venv typically
        # points at a *different* repo's venv whose leaks we shouldn't
        # touch.
        try:
            if venv_dir.is_symlink():
                continue
            if not venv_dir.is_dir():
                continue
        except OSError:
            continue

        try:
            candidates = list(venv_dir.glob(_EDITABLE_IMPL_GLOB))
        except OSError:
            continue

        for pth_file in candidates:
            line = _first_matching_line(pth_file, needle)
            if line is not None:
                leaks.append((pth_file, line))

    return leaks


def _first_matching_line(pth_file: Path, needle: str) -> Optional[str]:
    """
    Return the first line in ``pth_file`` containing ``needle`` as a
    substring, or None if no match. Returns None on any read / decode
    error (file is treated as 'no leak') so the scanner stays quiet on
    permission and encoding edge cases.
    """
    try:
        contents = pth_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    for raw_line in contents.splitlines():
        if needle in raw_line:
            return raw_line
    return None


# ============================================================================
# Presenter
# ============================================================================


def warn_pth_leaks(
    repo_root: Path,
    worktree_path: Path,
    console: Optional[object] = None,
) -> int:
    """
    Print a one-block warning per leak found by ``find_pth_leaks``.

    Returns the leak count. Always returns ``0`` on internal error so
    that a buggy scanner can never abort the cleanup boundary.

    Parameters
    ----------
    repo_root : Path
        Repository root passed to the scanner.
    worktree_path : Path
        Worktree path passed to the scanner.
    console : Optional[object]
        Optional Rich ``Console``-like object exposing ``.print(...)``.
        When None, warnings go to ``sys.stderr`` via ``print``. Tests
        rely on the stderr-fallback path.

    Returns
    -------
    int
        Number of leaks reported. ``0`` when none found OR when an
        unexpected error occurred (the latter is logged at DEBUG).
    """
    try:
        leaks = find_pth_leaks(repo_root, worktree_path)
    except Exception as exc:  # noqa: BLE001 — defence-in-depth boundary
        logger.debug("find_pth_leaks raised, suppressing: %s", exc)
        return 0

    if not leaks:
        logger.debug(
            "pth-leak scan clean for worktree=%s under repo=%s",
            worktree_path,
            repo_root,
        )
        return 0

    repo_root_str = str(Path(repo_root).resolve()) if repo_root else "<repo>"

    for pth_file, _matching_line in leaks:
        # venv_root is the .venv (or .guardkit/venv) directory containing
        # the leaking .pth — derived from the .pth path so we don't have
        # to re-iterate _SCAN_ROOTS.
        venv_root = _venv_root_of(pth_file)
        message = _WARNING_TEMPLATE.format(
            venv_root=venv_root,
            pth_file=pth_file,
            repo_root=repo_root_str,
        )
        try:
            if console is not None and hasattr(console, "print"):
                # markup=False:  literal brackets in tmp_path or similar
                #                aren't re-interpreted as Rich tags.
                # soft_wrap=True: Rich must NOT insert line breaks at
                #                 terminal width — long .pth paths must
                #                 stay on one line so consumers (and the
                #                 byte-equality test in
                #                 test_warns_but_does_not_abort) can
                #                 grep them. Same rationale as
                #                 feature.py:163-169 (FPSG-004 / L3d).
                console.print(
                    message, style="yellow", markup=False, soft_wrap=True
                )
            else:
                print(message, file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — never abort cleanup
            logger.debug("warn_pth_leaks emit failed, suppressing: %s", exc)

    return len(leaks)


def _venv_root_of(pth_file: Path) -> Path:
    """
    Walk up from a ``.pth`` file to its enclosing venv root. The .pth
    lives at ``<venv>/lib/pythonX.Y/site-packages/_editable_impl_*.pth``,
    so the venv root is three parents up from site-packages.
    """
    try:
        return pth_file.parents[3]
    except IndexError:
        # Defensive: unexpected layout. Return parent so the message
        # still includes a meaningful path.
        return pth_file.parent


__all__ = ["find_pth_leaks", "warn_pth_leaks"]
