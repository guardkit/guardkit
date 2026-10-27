"""The worktree venv's ``bin`` for a project command's PATH.

Shared by the Coach's command runs (CoachValidator). (27 October 2026: the
runtime execution of acceptance-criteria commands that also lived here was
removed with the checks it fed.)
"""

from pathlib import Path
from typing import Tuple

from guardkit.orchestrator.environment_bootstrap import probe_worktree_venv


def venv_path_first(worktree_path: Path) -> Tuple[str, ...]:
    """The worktree venv's ``bin`` to put first on PATH, or nothing.

    Derives the ``bin`` directory from
    :func:`guardkit.orchestrator.environment_bootstrap.probe_worktree_venv`
    (the interpreter's ``.parent``), so the worktree venv layouts and their
    resolution order — current bootstrap ``.venv/bin`` first (the FFC6 eager
    worktree venv), legacy PEP 668 ``.guardkit/venv/bin`` second — have ONE
    owner (2026-07-04 review, FIX 4). The PATH prepend therefore agrees with
    the pinned pytest ``argv[0]`` by construction (``_resolve_venv_python``
    resolves the interpreter via the same probe).
    TASK-AB-RESUMEVENV01; supersedes the TASK-FIX-A7B1 ordering.

    Empty when neither venv interpreter exists — a ``bin`` dir with no
    ``python`` is not a usable venv.
    """
    interpreter = probe_worktree_venv(worktree_path)
    if interpreter is None:
        return ()
    return (str(interpreter.parent),)
