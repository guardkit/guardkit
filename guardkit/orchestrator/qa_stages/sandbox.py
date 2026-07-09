"""Throwaway sandbox for the mutation stage (WS2 B6, ST-05).

**Guardrail (binding):** mutations run in a THROWAWAY worktree, NEVER the task
branch. Every mutant is applied to a *fresh* materialized copy of the source
tree under a temp dir; the original working tree is never written. When the
source is a git repo we prefer ``git worktree add`` (cheap, honest isolation);
otherwise we ``copytree`` the source (excluding ``.git`` and the usual build
detritus). Either way the sandbox is removed on ``__exit__``.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Never copied into a sandbox — heavy, regenerable, or the VCS metadata itself.
_COPY_EXCLUDES = (
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".guardkit",
)


def _ignore(_dir: str, names: List[str]) -> set[str]:
    return {n for n in names if n in _COPY_EXCLUDES or n.endswith(".pyc")}


@dataclass
class MaterializedSandbox:
    """A single materialized copy of the source tree under a temp dir.

    ``path`` is the sandbox root; mutate files under it freely — it is discarded
    by :meth:`cleanup`. ``is_git`` records whether it is a real git worktree
    (so a git-backed mutation operator can ``git apply -R`` against it).
    """

    path: Path
    is_git: bool
    _worktree_of: Path | None = None
    _cleaned: bool = field(default=False, repr=False)

    def cleanup(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        if self._worktree_of is not None:
            # Detach the git worktree cleanly, then remove the dir.
            subprocess.run(
                ["git", "-C", str(self._worktree_of), "worktree", "remove",
                 "--force", str(self.path)],
                capture_output=True,
                check=False,
            )
        shutil.rmtree(self.path, ignore_errors=True)

    def __enter__(self) -> "MaterializedSandbox":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.cleanup()


class MutationSandbox:
    """Factory that materializes fresh throwaway copies of ``source_root``.

    Each call to :meth:`materialize` returns an independent copy — the campaign
    applies exactly one mutant per copy so mutants never interact.
    """

    def __init__(self, source_root: Path, *, prefer_git: bool = True) -> None:
        self.source_root = Path(source_root).resolve()
        if not self.source_root.is_dir():
            raise NotADirectoryError(f"source_root is not a directory: {self.source_root}")
        self._is_git_repo = prefer_git and self._detect_git(self.source_root)

    @staticmethod
    def _detect_git(root: Path) -> bool:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    def materialize(self) -> MaterializedSandbox:
        """Return a fresh throwaway copy of the source tree."""
        tmp = Path(tempfile.mkdtemp(prefix="guardkit-qa-mutate-"))
        if self._is_git_repo:
            dest = tmp / "wt"
            result = subprocess.run(
                ["git", "-C", str(self.source_root), "worktree", "add",
                 "--detach", str(dest)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return MaterializedSandbox(path=dest, is_git=True, _worktree_of=self.source_root)
            # git worktree failed (dirty index, submodule, etc.) — fall back to copy.
            shutil.rmtree(tmp, ignore_errors=True)
            tmp = Path(tempfile.mkdtemp(prefix="guardkit-qa-mutate-"))
        dest = tmp / "copy"
        shutil.copytree(self.source_root, dest, ignore=_ignore, symlinks=True)
        return MaterializedSandbox(path=dest, is_git=False)
