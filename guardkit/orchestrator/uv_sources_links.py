"""Links that let a worktree find a project's ``[tool.uv.sources]`` siblings.

Moved here unchanged from ``environment_bootstrap`` on 1 November 2026, when
GuardKit stopped inferring installs. This is not an install: it runs nothing
and chooses no command. A project whose ``pyproject.toml`` pins a sibling
folder by path (``nats-core = { path = "../nats-core" }``) resolves that path
from the worktree's own folder, which is ``.guardkit/worktrees/<id>/`` and not
the main checkout, so the project's declared install (``uv sync --frozen``)
would not find the sibling. These links put the sibling where the path looks.

It is still Python-shaped knowledge in central code. It is kept, not removed
with the inferred install, because the study tutor's declared install needs
it today (its ``[tool.uv.sources]`` pins ``../nats-core``); removing it is a
separate decision with that evidence.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def _resolve_uv_sources_symlinks(
    source_pyproject_path: Path,
    worktree_pyproject_path: Path,
) -> List[tuple[Path, Path]]:
    """
    Compute worktree symlinks needed to bridge ``[tool.uv.sources]`` paths
    between a source repo and its worktree checkout (TASK-FIX-AB61).

    uv resolves a path-typed source entry relative to the *pyproject's own
    directory*. When the worktree pyproject lives at a different filesystem
    location than the source pyproject, a sibling pin like
    ``foo = { path = "../foo" }`` resolves to two different absolute paths.
    This helper returns the ``(symlink_path, target_path)`` pairs that the
    orchestrator should pre-create so uv finds the same files from the
    worktree as it would from the source repo.

    Parameters
    ----------
    source_pyproject_path : Path
        Path to the source repo's ``pyproject.toml``.
    worktree_pyproject_path : Path
        Path to the worktree checkout's ``pyproject.toml``. Typically a
        descendant of ``<source>/.guardkit/worktrees/<feat>/``.

    Returns
    -------
    list[tuple[Path, Path]]
        Each tuple is ``(symlink_path, target_path)`` where
        ``symlink_path`` is where uv WILL look from the worktree, and
        ``target_path`` is where the file actually lives. Both are
        absolute, ``.resolve()``-d paths. Empty list when no
        ``[tool.uv.sources]`` table is present, when all entries are
        non-path-typed (``git``, ``index``, ``workspace``, ``url``), or
        when every path-typed entry already lives inside the worktree's
        own checkout.

    Notes
    -----
    Entries whose ``source_resolved`` does not exist are skipped with a
    warning rather than emitted — letting the bootstrap surface uv's own
    "Distribution not found" error is more informative than mocking up a
    broken symlink.
    """
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # type: ignore[import,no-redef]
        data = tomllib.loads(source_pyproject_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug(
            "Could not parse %s for uv-sources symlink resolution: %s",
            source_pyproject_path,
            exc,
        )
        return []

    sources = data.get("tool", {}).get("uv", {}).get("sources")
    if not isinstance(sources, dict) or not sources:
        return []

    source_dir = source_pyproject_path.parent
    worktree_dir = worktree_pyproject_path.parent

    symlinks: List[tuple[Path, Path]] = []
    for key, entry in sources.items():
        if not isinstance(entry, dict):
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            # Non-path-typed entries (git, index, workspace, url) need no
            # symlink. They're out of scope for AB61.
            continue

        # AB61 hardening (red-baseline retro 2026-07-08 / L12): do NOT
        # ``.resolve()`` THROUGH a pre-existing symlink at the intended link
        # location. The final component of ``worktree_dir / path_value`` is
        # the symlink this bootstrap manages; a stale/dangling link left there
        # by an earlier environment (e.g. a different ``$HOME``) would be
        # *followed* by a plain ``.resolve()`` into a foreign path, which the
        # creator then ``mkdir(parents=True)``'d — the run-0 ``Errno 45``
        # autofs crash class. Resolve the *parent* (real dirs + ``..``) but
        # keep the managed final component un-followed so the link location is
        # correct regardless of any stale link sitting there. The creator
        # (:func:`_create_worktree_uv_sources_symlinks`) then detects the
        # wrong/dangling link and replaces it.
        worktree_target = worktree_dir / path_value
        worktree_resolved = worktree_target.parent.resolve() / worktree_target.name
        source_resolved = (source_dir / path_value).resolve()

        if worktree_resolved == source_resolved:
            # Path points inside the worktree's own checkout — uv finds it
            # without help.
            continue

        if not source_resolved.exists():
            logger.warning(
                "uv-sources entry '%s' in %s points to %s which does not "
                "exist; skipping symlink creation. uv will surface its own "
                "'Distribution not found' error.",
                key,
                source_pyproject_path,
                source_resolved,
            )
            continue

        symlinks.append((worktree_resolved, source_resolved))

    return symlinks


def _create_worktree_uv_sources_symlinks(
    symlinks: List[tuple[Path, Path]],
) -> None:
    """
    Create the worktree symlinks computed by
    :func:`_resolve_uv_sources_symlinks` (TASK-FIX-AB61).

    Idempotent:

    * If the symlink path is already a symlink pointing at the correct
      target, leave it alone.
    * If the symlink path is a symlink pointing elsewhere, replace it.
    * If a non-symlink (real file or directory) already exists at the
      symlink path, log a warning and skip — the consuming repo may have
      a real directory there for another reason and silent overwrite
      would be destructive.

    Parameters
    ----------
    symlinks : list[tuple[Path, Path]]
        ``(symlink_path, target_path)`` pairs as returned by
        :func:`_resolve_uv_sources_symlinks`. Both paths must be
        absolute. Empty list is a no-op.

    Raises
    ------
    OSError
        If symlink creation itself fails (permission denied, target
        unreadable, parent directory creation failed). The caller is
        responsible for surfacing this with a hint that names the
        symlink path, target, and OS error.
    """
    for symlink_path, target_path in symlinks:
        if symlink_path.is_symlink():
            try:
                current = Path(os.readlink(symlink_path))
            except OSError as exc:
                logger.warning(
                    "Could not read existing symlink at %s: %s; replacing.",
                    symlink_path,
                    exc,
                )
                current = None
            if current is not None and current == target_path:
                logger.debug(
                    "uv-sources symlink already correct: %s -> %s",
                    symlink_path,
                    target_path,
                )
                continue
            symlink_path.unlink()
        elif symlink_path.exists():
            logger.warning(
                "Path %s exists and is not a symlink; skipping uv-sources "
                "symlink creation. Remove or relocate it to enable "
                "transparent sibling-source resolution from this worktree.",
                symlink_path,
            )
            continue

        symlink_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target_path, symlink_path)
        logger.debug(
            "Created uv-sources symlink: %s -> %s",
            symlink_path,
            target_path,
        )
