"""Feature-level smoke gates between autobuild waves.

Implements TASK-SMK-F703A. A smoke gate is a single subprocess invocation
run inside the feature's shared worktree after a specified wave completes.
Exit code mismatch halts the feature build, preserves the worktree, and
leaves the result in the final summary for human triage.

The module deliberately does NOT compute wave boundaries — it receives
the wave number from the orchestrator, which already owns the canonical
wave definition (``parallel_groups`` in ``FEAT-*.yaml``). Inventing a
second wave concept here would contradict the task's non-goals.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from guardkit.orchestrator.feature_loader import SmokeGates

logger = logging.getLogger(__name__)


@dataclass
class SmokeGateResult:
    """Outcome of a single smoke-gate invocation.

    Attributes
    ----------
    passed : bool
        True if subprocess exit code equals ``config.expected_exit`` and
        the command did not time out.
    exit_code : int
        Actual exit code from the subprocess. ``-1`` indicates a timeout
        (no real exit code was observed).
    stdout : str
        Captured standard output (may be empty on timeout).
    stderr : str
        Captured standard error (may be empty on timeout).
    timed_out : bool
        True if the subprocess hit ``config.timeout`` before completing.
    command : str
        The command that was executed (echo of ``config.command``).
    timeout : int
        The timeout value used (echo of ``config.timeout``).
    after_wave : int
        The wave number after which this gate was invoked. Useful for
        the final summary and tests that assert placement.
    """

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    command: str
    timeout: int
    after_wave: int


def should_fire_for_wave(config: SmokeGates, wave_number: int) -> bool:
    """Decide whether the configured smoke gate should fire after ``wave_number``.

    The orchestrator already knows which wave just completed (from
    ``enumerate(parallel_groups)``). This function only matches that index
    against the configuration — it never computes wave boundaries itself.

    Parameters
    ----------
    config : SmokeGates
        Smoke gate configuration from ``FEAT-*.yaml``.
    wave_number : int
        1-indexed wave number that just completed.

    Returns
    -------
    bool
        True if the smoke gate should fire after this wave.
    """
    after = config.after_wave
    if after == "all":
        return True
    if isinstance(after, int):
        return after == wave_number
    if isinstance(after, list):
        return wave_number in after
    return False


def _decode(stream: object) -> str:
    """Decode a subprocess stdout/stderr stream (may be bytes, str, or None)."""
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace")
    return str(stream)


def run_smoke_gate(
    config: SmokeGates,
    cwd: Path,
    wave_number: int,
) -> SmokeGateResult:
    """Execute a smoke gate and return a structured result.

    The subprocess is run with shell=True so operators can write natural
    commands (e.g. ``pytest features/FEAT-X.feature -q``). ``cwd`` is the
    feature's shared worktree — NOT the main repo — so the gate sees the
    in-progress implementation produced by the preceding wave.

    Parameters
    ----------
    config : SmokeGates
        Validated smoke gate configuration.
    cwd : Path
        Working directory for the subprocess. Expected to be the shared
        worktree path (``.guardkit/worktrees/FEAT-X/``).
    wave_number : int
        1-indexed wave number that just completed. Recorded in the result
        for the final summary.

    Returns
    -------
    SmokeGateResult
        Structured outcome. ``passed`` is True iff the exit code matches
        ``config.expected_exit`` AND no timeout occurred.
    """
    logger.info(
        "Running smoke gate after wave %d: %s (cwd=%s, timeout=%ds, expected_exit=%d)",
        wave_number,
        config.command,
        cwd,
        config.timeout,
        config.expected_exit,
    )

    try:
        proc = subprocess.run(
            config.command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=config.timeout,
        )
    except subprocess.TimeoutExpired as exc:
        logger.warning(
            "Smoke gate timed out after %ds: %s", config.timeout, config.command
        )
        return SmokeGateResult(
            passed=False,
            exit_code=-1,
            stdout=_decode(exc.stdout),
            stderr=_decode(exc.stderr),
            timed_out=True,
            command=config.command,
            timeout=config.timeout,
            after_wave=wave_number,
        )

    passed = proc.returncode == config.expected_exit
    if passed:
        logger.info(
            "Smoke gate passed after wave %d (exit=%d)", wave_number, proc.returncode
        )
    else:
        logger.warning(
            "Smoke gate failed after wave %d (exit=%d, expected=%d)",
            wave_number,
            proc.returncode,
            config.expected_exit,
        )

    return SmokeGateResult(
        passed=passed,
        exit_code=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        timed_out=False,
        command=config.command,
        timeout=config.timeout,
        after_wave=wave_number,
    )
