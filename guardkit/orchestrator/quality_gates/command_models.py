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

    If the worktree contains a ``.venv/bin`` directory, returns an
    environment dict with that directory prepended to PATH. Otherwise
    returns None (inherit parent environment).

    Parameters
    ----------
    worktree_path : Path
        Path to the git worktree.

    Returns
    -------
    Optional[Dict[str, str]]
        Environment dict with modified PATH, or None.
    """
    venv_bin = worktree_path / ".venv" / "bin"
    if venv_bin.is_dir():
        env = os.environ.copy()
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
        return env
    return None


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
