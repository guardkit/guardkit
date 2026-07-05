"""Post-completion test verification for ``guardkit autobuild complete --verify``.

TASK-AB-VERIFYCLI01. R3 of the 2026-07-04 retro cross-reference showed
post-merge verification is a real aperture: ``after_wave: [2,3,4]`` left the
final waves ungated and ``tests/`` outside every gate, so nothing re-ran the
suite at completion. The slash-command workflow documented a ``--verify`` step
the Python CLI never implemented; this module is the ONE implementation both
entry points share (``cli-wrapper-shares-client-acquisition-path.md`` — a
CLI-only second implementation is exactly the divergence that rule documents).

Verification semantics (absence-of-failure-safe):

- ``passed`` requires POSITIVE evidence tests ran (``tests_run > 0``) on the
  runners this module understands: a pytest run must show a passed-count; a
  stack-profile run must not classify as absent. A runner that could not
  start, collected zero tests, or produced no evidence any test executed is
  ``unverified`` — never a pass (``absence-of-failure-is-not-success.md``).
  An operator-supplied CUSTOM command (``--verify-cmd`` / a non-pytest smoke
  command) is trusted on exit code alone — its output shape is unknowable
  here, matching the smoke-gate exit-code semantics.
- A timeout is ``failed`` (ran-and-hung is a real defect — the
  runtime-parity L3 precedent), never absent.
- The verification runs as a SUBPROCESS in the merge-target repo with the
  project's own interpreter/venv where one exists — not guardkit's — so a
  merged-in missing dependency cannot be masked by guardkit's environment
  (``namespace-hygiene.md``).
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from guardkit.orchestrator.quality_gates.stack_test_execution import (
    StackTestProfile,
    classify_absent_for_stack,
    detect_stack_profile,
)

logger = logging.getLogger(__name__)

__all__ = [
    "VerificationResult",
    "resolve_verify_command",
    "run_completion_verification",
]

# Full-suite verification needs more headroom than the 120s between-wave
# smoke default; 600s matches the smoke-gate schema's upper bound.
DEFAULT_VERIFY_TIMEOUT = 600

_ABSENT_RETURNCODES = frozenset({126, 127})

# pytest's "N passed" summary — the positive tests-ran evidence.
_PYTEST_PASSED_RE = re.compile(r"\b[1-9]\d*\s+passed\b")


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a post-completion verification run.

    ``status`` is the enforcement source every display line must derive from
    (``display-must-derive-from-enforcement-source-not-proxy.md``): "verified"
    output is only legitimate when ``status == "passed"``, never inferred
    from "the completion succeeded".
    """

    status: str  # "passed" | "failed" | "unverified"
    command: str
    cwd: str
    returncode: Optional[int]
    detail: str
    output_tail: str = ""


def _project_python(repo_root: Path) -> Optional[Path]:
    """Return the project's own venv interpreter, if one exists."""
    for candidate in (
        repo_root / ".venv" / "bin" / "python",
        repo_root / "venv" / "bin" / "python",
        repo_root / ".venv" / "Scripts" / "python.exe",
        repo_root / "venv" / "Scripts" / "python.exe",
    ):
        if candidate.exists():
            return candidate
    return None


def _looks_python(repo_root: Path) -> bool:
    return any(
        (repo_root / marker).exists()
        for marker in ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini")
    ) and (repo_root / "tests").is_dir()


def resolve_verify_command(
    repo_root: Path,
    smoke_command: Optional[str] = None,
    override: Optional[str] = None,
) -> Tuple[Optional[str], str, Optional[StackTestProfile]]:
    """Resolve the verification command for ``repo_root``.

    Precedence: explicit ``--verify-cmd`` override > the feature YAML's
    ``smoke_gates.command`` > a stack-aware default (venv-pinned pytest for
    Python; the ``stack_test_execution`` registry for .NET/JS-TS/Go).

    Returns ``(command, source, stack_profile)``; ``command`` is ``None``
    when no runner could be determined (the caller reports UNVERIFIED —
    never a pass).
    """
    if override:
        return override, "--verify-cmd override", None
    if smoke_command:
        return smoke_command, "feature smoke_gates.command", None
    if _looks_python(repo_root):
        python = _project_python(repo_root)
        if python is not None:
            return f'"{python}" -m pytest tests/', "python stack default (project venv)", None
        logger.warning(
            "TASK-AB-VERIFYCLI01: no project venv found at %s — falling back "
            "to PATH pytest, which may resolve from guardkit's environment",
            repo_root,
        )
        return "pytest tests/", "python stack default (PATH pytest)", None
    profile = detect_stack_profile(repo_root)
    if profile is not None:
        return (
            profile.whole_suite_command,
            f"{profile.stack} stack default",
            profile,
        )
    return None, "no test runner detected", None


def _classify_pytest(returncode: int, output: str) -> Tuple[str, str]:
    if returncode in _ABSENT_RETURNCODES:
        return "unverified", "test runner could not start"
    if returncode == 5:
        return "unverified", "zero tests collected (pytest exit 5)"
    if returncode == 4:
        return "unverified", "pytest usage error (exit 4)"
    if returncode == 0:
        match = _PYTEST_PASSED_RE.search(output)
        if match:
            return "passed", match.group(0)
        # Clean exit with no evidence any test ran — absent, never a pass.
        return "unverified", "clean exit but no evidence any test ran"
    return "failed", f"test run failed (exit {returncode})"


def _classify_stack(
    profile: StackTestProfile, returncode: int, output: str
) -> Tuple[str, str]:
    if classify_absent_for_stack(profile, returncode, output):
        return "unverified", f"{profile.stack} run produced no test verdict"
    if returncode == 0:
        return "passed", f"{profile.stack} suite passed"
    return "failed", f"{profile.stack} suite failed (exit {returncode})"


def _classify_custom(returncode: int) -> Tuple[str, str]:
    if returncode in _ABSENT_RETURNCODES:
        return "unverified", "verification command could not start"
    if returncode == 0:
        return "passed", "verification command exited 0"
    return "failed", f"verification command failed (exit {returncode})"


def run_completion_verification(
    repo_root: Path,
    command: Optional[str],
    source: str,
    stack_profile: Optional[StackTestProfile] = None,
    timeout: int = DEFAULT_VERIFY_TIMEOUT,
) -> VerificationResult:
    """Run the resolved verification command in the merge-target repo.

    Never raises: every outcome (including a missing command, a timeout, or a
    subprocess error) is a :class:`VerificationResult`. Only ``passed`` may
    ever be rendered as success.
    """
    cwd = str(repo_root)
    if not command:
        return VerificationResult(
            status="unverified",
            command="",
            cwd=cwd,
            returncode=None,
            detail=f"UNVERIFIED: {source}",
        )

    logger.info(
        "Post-completion verification (%s): %s (cwd=%s, timeout=%ds)",
        source,
        command,
        cwd,
        timeout,
    )
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        # Ran-and-hung is a genuine defect (runtime-parity L3 precedent):
        # a suite that hangs post-merge must block, never read as absent.
        stdout = exc.stdout or b""
        tail = stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else str(stdout)
        return VerificationResult(
            status="failed",
            command=command,
            cwd=cwd,
            returncode=None,
            detail=f"verification timed out after {timeout}s",
            output_tail=tail[-2000:],
        )
    except OSError as exc:
        return VerificationResult(
            status="unverified",
            command=command,
            cwd=cwd,
            returncode=None,
            detail=f"verification command could not start: {exc}",
        )

    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if stack_profile is not None:
        status, detail = _classify_stack(stack_profile, proc.returncode, output)
    elif "pytest" in command:
        status, detail = _classify_pytest(proc.returncode, output)
    else:
        status, detail = _classify_custom(proc.returncode)

    return VerificationResult(
        status=status,
        command=command,
        cwd=cwd,
        returncode=proc.returncode,
        detail=detail,
        output_tail=output[-2000:],
    )
