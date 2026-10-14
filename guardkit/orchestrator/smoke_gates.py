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
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.launch_declaration import (
    load_launch_declaration,
    main_checkout_root,
)
from guardkit.orchestrator.project_command_env import (
    minimal_environment_note,
    project_command_environment,
)
from guardkit.orchestrator.run_evidence import (
    EvidenceRequest,
    start_command_evidence,
)

from guardkit.orchestrator import process_group

logger = logging.getLogger(__name__)

# pytest exit code for "no tests collected" — distinct from exit 1 (test
# failed). See https://docs.pytest.org/en/stable/reference/exit-codes.html
# We treat this as a configuration gap (gate not wired to a real test),
# not a code regression — see TASK-FIX-SG05 for rationale.
PYTEST_EXIT_NO_TESTS_COLLECTED = 5

# Hint surfaced when a gate matches zero tests, so post-mortems can
# immediately distinguish "marker typo" / "missing pytest registration"
# from a genuine test failure.
GATE_NOT_WIRED_HINT = (
    "Smoke gate matched 0 tests — verify that markers are registered in "
    "pyproject.toml and that at least one test carries the marker expression."
)


@dataclass
class SmokeGateResult:
    """Outcome of a single smoke-gate invocation.

    Attributes
    ----------
    passed : bool
        True if the gate did not block feature progress. For exit 0 this
        means the command succeeded; for exit 5 with
        ``exit5_is_hard_fail=False`` (default) this also stays True — see
        ``gate_not_wired`` below.
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
    gate_not_wired : bool
        True when pytest exit code 5 (no tests collected) was observed —
        the gate's marker expression matched zero tests. Distinct from a
        real test failure. By default the feature build continues with a
        warning; ``SmokeGates.exit5_is_hard_fail=True`` flips ``passed``
        to False so the build halts. (TASK-FIX-SG05)
    """

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    command: str
    timeout: int
    after_wave: int
    gate_not_wired: bool = False
    #: What the command ran against (repair 7): its execution root's source
    #: before and after, the declared environment inventory and the raw
    #: container events of the interval. Evidence only — never read by the
    #: pass/fail logic above.
    run_evidence: Optional[dict] = None
    #: True when the command was never started because its environment could
    #: not be built (no scratch folder, a malformed ``launch:`` block, a proxy
    #: carrying credentials). ``passed`` is False and ``stderr`` says why.
    could_not_start: bool = False


def _held_back_note(cwd: Path, declaration: object, path_first: tuple) -> str:
    """Which settings the smoke command's environment held back, by name
    only; empty when it cannot be built, which the failure already says."""
    try:
        return minimal_environment_note(
            project_command_environment(cwd, declaration, path_first=path_first)
        )
    except OSError:
        return ""


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
    venv_python: Optional[str] = None,
    evidence: Optional[EvidenceRequest] = None,
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
    venv_python : Optional[str]
        Path to the bootstrap venv interpreter (e.g.
        ``<worktree>/.guardkit/venv/bin/python``). When provided, that
        directory is put in front of PATH so a bare ``python`` in the smoke
        command resolves to the venv interpreter rather than failing on
        Ubuntu 24+ where only ``python3`` exists in system PATH
        (TASK-FIX-A7B1).

    The environment is built from nothing (``project_command_env``,
    13 October 2026), with the main checkout's ``launch:`` block, never this
    process's own with the factory's credentials. When it cannot be built
    the gate fails with the plain reason and the command does not run.
    evidence : Optional[EvidenceRequest]
        What the caller knows for the run record (repair 7): the kind of
        command, who is observing, and the project's declared environment
        inventory. A caller that passes nothing still gets a record, which
        says the inventory was not looked up.

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

    path_first = (str(Path(venv_python).parent),) if venv_python else ()
    if path_first:
        logger.debug(
            "Smoke gate PATH-prepended with bootstrap venv: %s", path_first[0]
        )
    try:
        declaration = load_launch_declaration(main_checkout_root(Path(cwd)))
        env = project_command_environment(
            Path(cwd), declaration, path_first=path_first
        )
    except OSError as exc:
        reason = f"the smoke command could not start: {exc}"
        logger.warning("Smoke gate after wave %d: %s", wave_number, reason)
        return SmokeGateResult(
            passed=False,
            exit_code=-1,
            stdout="",
            stderr=reason,
            timed_out=False,
            command=config.command,
            timeout=config.timeout,
            after_wave=wave_number,
            could_not_start=True,
        )

    # Repair 7: record what the command ran against. Never changes the run.
    record = start_command_evidence(
        evidence,
        command=config.command,
        execution_root=cwd,
        cwd=cwd,
        env=env,
        declared_settings=declaration.settings if declaration is not None else (),
    )
    try:
        proc = process_group.run_project_command(
            config.command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=config.timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        run_evidence = record.finish()
        # TASK-SGER-001: surface partial output captured before the gate was
        # killed. ``exc.stdout`` / ``exc.stderr`` carry whatever the
        # subprocess wrote before the timeout fired — useful when a gate
        # hangs partway through a multi-statement script.
        partial_stderr = _decode(exc.stderr)
        partial_stdout = _decode(exc.stdout)
        logger.warning(
            "Smoke gate timed out after %ds: %s\n"
            "stderr (partial):\n%s\n"
            "stdout (partial):\n%s",
            config.timeout,
            config.command,
            (partial_stderr or "(empty)").rstrip(),
            (partial_stdout or "(empty)").rstrip(),
        )
        return SmokeGateResult(
            passed=False,
            exit_code=-1,
            stdout=partial_stdout,
            stderr=partial_stderr,
            timed_out=True,
            command=config.command,
            timeout=config.timeout,
            after_wave=wave_number,
            run_evidence=run_evidence,
        )

    run_evidence = record.finish()

    # TASK-FIX-SG05: distinguish exit 5 (no tests collected — gate not wired)
    # from exit 1 (tests ran and failed — genuine regression). Without this
    # split, a marker typo or unregistered marker silently masquerades as a
    # feature failure and preserves the worktree under a misleading reason.
    matched_expected = proc.returncode == config.expected_exit
    gate_not_wired = (
        proc.returncode == PYTEST_EXIT_NO_TESTS_COLLECTED and not matched_expected
    )

    if matched_expected:
        passed = True
        logger.info(
            "Smoke gate passed after wave %d (exit=%d)", wave_number, proc.returncode
        )
    elif gate_not_wired and not config.exit5_is_hard_fail:
        # Soft-warn path: gate is unwired (config gap), not a regression.
        # Build continues; orchestrator surfaces a yellow warning.
        passed = True
        logger.warning(
            "Smoke gate unwired after wave %d (exit=5 — no tests collected); "
            "treating as config gap, not regression. %s",
            wave_number,
            GATE_NOT_WIRED_HINT,
        )
    elif gate_not_wired and config.exit5_is_hard_fail:
        # Hard-fail path: feature opted into strict enforcement.
        passed = False
        logger.warning(
            "Smoke gate unwired after wave %d (exit=5 — no tests collected); "
            "treating as hard failure (exit5_is_hard_fail=True). %s",
            wave_number,
            GATE_NOT_WIRED_HINT,
        )
    else:
        passed = False
        # TASK-SGER-001: surface captured stderr/stdout so the failure log is
        # self-diagnosing. The data is already on the CompletedProcess; without
        # this, operators see only "exit=X, expected=Y" and have to re-run the
        # gate by hand to learn what actually failed.
        logger.warning(
            "Smoke gate failed after wave %d (exit=%d, expected=%d)\n"
            "stderr:\n%s\n"
            "stdout:\n%s\n%s",
            wave_number,
            proc.returncode,
            config.expected_exit,
            (proc.stderr or "(empty)").rstrip(),
            (proc.stdout or "(empty)").rstrip(),
            _held_back_note(Path(cwd), declaration, path_first),
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
        gate_not_wired=gate_not_wired,
        run_evidence=run_evidence,
    )
