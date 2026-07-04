"""
Shared models and constants for command execution verification.

This module contains types and constants shared between the AutoBuild
orchestrator and CoachValidator for runtime command execution of
acceptance criteria (TASK-CRV-537E, TASK-RFX-7C63).

Extracted to avoid circular imports between autobuild.py and
coach_validator.py.
"""

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardkit.orchestrator.environment_bootstrap import probe_worktree_venv
from guardkit.orchestrator.quality_gates.command_failure_classifier import (
    CommandFailureRecord,
)

# Sentinel path fragment that must appear in any directory used as cwd for
# subprocess.run().  This ensures commands never execute against the base repo.
WORKTREE_SENTINEL: str = ".guardkit/worktrees/"

# Per-command timeout (seconds).
COMMAND_TIMEOUT_SECONDS: int = 60

# Aggregate timeout across all command criteria per turn (seconds).
COMMAND_TOTAL_TIMEOUT_SECONDS: int = 180

# Pattern to detect bare ``pip`` commands that should be normalised to
# ``sys.executable -m pip`` so the correct Python environment is used
# regardless of which ``pip`` shim appears first on PATH.
_PIP_CMD_RE: re.Pattern = re.compile(r"^pip(\s|$)")


def _assert_worktree_path(path: Path) -> None:
    """Defensive check: never execute commands outside a worktree.

    Raises
    ------
    RuntimeError
        If *path* does not contain the worktree sentinel.
    """
    resolved = str(path.resolve())
    if WORKTREE_SENTINEL not in resolved:
        raise RuntimeError(
            f"Refusing to execute commands outside worktree. "
            f"Path '{resolved}' does not contain '{WORKTREE_SENTINEL}'"
        )


def normalise_pip_command(cmd: str) -> str:
    """Normalise bare ``pip`` to ``sys.executable -m pip``.

    Ensures the worktree's Python environment is used instead of a
    potentially broken Homebrew shim (VID-001 class fix).

    Parameters
    ----------
    cmd : str
        Command string to normalise.

    Returns
    -------
    str
        Normalised command string.
    """
    if _PIP_CMD_RE.match(cmd):
        return f"{sys.executable} -m pip{cmd[3:]}"
    return cmd


def build_venv_env(worktree_path: Path) -> Optional[Dict[str, str]]:
    """Build environment dict with virtualenv PATH prepended.

    Derives the ``bin`` directory from
    :func:`guardkit.orchestrator.environment_bootstrap.probe_worktree_venv`
    (the interpreter's ``.parent``), so the worktree venv layouts and their
    resolution order — current bootstrap ``.venv/bin`` first (the FFC6 eager
    worktree venv), legacy PEP 668 ``.guardkit/venv/bin`` second — have ONE
    owner (2026-07-04 review, FIX 4; previously this helper hand-listed the
    same layouts). The PATH prepend therefore agrees with the pinned pytest
    ``argv[0]`` by construction (``_resolve_venv_python`` resolves the
    interpreter via the same probe; a divergent order here would PATH-prepend
    a DIFFERENT venv than the one pytest runs under).
    TASK-AB-RESUMEVENV01; supersedes the TASK-FIX-A7B1 ordering, which
    predated the FFC6 ``.venv`` layout.

    Returns None when neither venv interpreter exists (inherit parent
    environment) — a ``bin`` dir with no ``python`` is not a usable venv.

    Parameters
    ----------
    worktree_path : Path
        Path to the git worktree.

    Returns
    -------
    Optional[Dict[str, str]]
        Environment dict with modified PATH, or None.
    """
    interpreter = probe_worktree_venv(worktree_path)
    if interpreter is None:
        return None

    env = os.environ.copy()
    env["PATH"] = str(interpreter.parent) + os.pathsep + env.get("PATH", "")
    return env


@dataclass(frozen=True)
class CommandExecutionResult:
    """Result of executing a single command_execution acceptance criterion.

    Captures the full execution context for a runtime command criterion,
    providing structured visibility into pass/fail status, output, and timing.
    Foundation for Phase 2 failure classification (TASK-RFX-528E).
    """

    criterion_text: str
    extracted_command: str
    passed: bool
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    elapsed_seconds: float = 0.0
    timed_out: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON persistence."""
        return {
            "criterion_text": self.criterion_text,
            "extracted_command": self.extracted_command,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "stdout": self.stdout[:500],
            "stderr": self.stderr[:500],
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "timed_out": self.timed_out,
        }


@dataclass
class CommandVerificationResult:
    """Aggregate result of command criteria verification (TASK-RFX-7C63).

    Groups per-command results with classified failures and lists of
    criteria texts that passed (for ``requirements_addressed`` injection).
    """

    results: List[CommandExecutionResult] = field(default_factory=list)
    failures: List[CommandFailureRecord] = field(default_factory=list)
    passed_criteria: List[str] = field(default_factory=list)
