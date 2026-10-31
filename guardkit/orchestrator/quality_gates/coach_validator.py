"""
Coach validator for lightweight task-work result validation.

This module provides the CoachValidator class that validates Player's
implementation by reading task-work quality gate results rather than
reimplementing the quality gates inside Coach.

Architecture:
    Implements Option D (per TASK-REV-0414): 100% code reuse by reading
    task-work quality gate outputs instead of reimplementing validation.

    Validation Flow:
    1. Read task-work results from .guardkit/autobuild/{task_id}/task_work_results.json
    2. Verify quality gates passed (tests, coverage, arch review, plan audit)
    3. Run independent test verification (trust but verify)
    4. Validate requirements satisfaction
    5. Return approve/feedback decision

Example:
    >>> from guardkit.orchestrator.quality_gates import CoachValidator
    >>>
    >>> validator = CoachValidator("/path/to/worktree")
    >>> result = validator.validate(
    ...     task_id="TASK-001",
    ...     turn=1,
    ...     task={"acceptance_criteria": ["OAuth2 flow", "Token refresh"]}
    ... )
    >>>
    >>> if result.decision == "approve":
    ...     print("Coach approved implementation")
"""

import hashlib
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
from contextlib import aclosing
from dataclasses import dataclass, replace as dataclass_replace
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
)

from guardkit.lib.pytest_summary import parse_pytest_summary
from guardkit.orchestrator.coach_verification import _resolve_venv_python
from guardkit.orchestrator import evidence_repos as evidence_repos_lib
from guardkit.orchestrator.evidence_repos import EvidenceRepo, EvidenceTestResult
from guardkit.orchestrator.quality_gates.stack_test_execution import (
    StackTestProfile,
    classify_absent_for_stack,
    detect_stack_profile,
    overlay_declared_profile,
)
from guardkit.orchestrator.launch_declaration import (
    load_launch_declaration,
    load_launch_snapshot,
    main_checkout_root,
)
from guardkit.orchestrator.project_command_env import (
    minimal_environment_note,
    project_command_environment,
)
from guardkit.orchestrator.toolchain_declaration import (
    ComponentToolchain,
    DeclaredPart,
    ToolchainDeclaration,
    parts_for_files,
    resolve_component_cwd,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
    IndependentTestClassification,
    RuntimeParityResult,
)
from guardkit.orchestrator.docker_fixtures import (
    fixture_owner,
    get_container_name,
    get_env_exports,
    get_port_command,
    get_start_commands,
    is_known_service,
    parse_port_output,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.run_evidence import (
    CommandEvidence,
    EvidenceRequest,
    request_from_declaration,
    start_command_evidence,
)
from guardkit.models.task_types import TaskType, get_profile, TASK_TYPE_ALIASES

# TASK-HMIG-006.3: Coach's independent SDK invocation dispatches through
# the HarnessAdapter substrate seam established by TASK-HMIG-006 (Player
# path) and TASK-HMIG-006.2 (cross-repo helper migration). Importing at
# module top matches the Player path convention in
# ``agent_invoker.py:71-77`` and makes ``select_harness`` a stable patch
# target for tests under ``coach_validator.select_harness``.
from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
    ToolResultEvent,
    select_harness,
)
from guardkit.orchestrator.harness.selector import DEFAULT_HARNESS
from guardkit.orchestrator.sdk_utils import check_assistant_message_error
from guardkit.orchestrator import process_group
from guardkit.lib.project_git import run_git

# Coach architecture-context integration (TASK-SC-009) was retired in the
# fleet-memory cutover (FEAT-MEM-09): build_coach_context was never invoked and
# was built on the now-removed graphiti planning stack.

logger = logging.getLogger(__name__)

# Optional open() flags, read directly from os (not through getattr) so the
# launch guard sees os used only through its attributes; 0 where absent.
try:
    _O_NOFOLLOW = os.O_NOFOLLOW
except AttributeError:  # pragma: no cover - not on every platform
    _O_NOFOLLOW = 0
try:
    _O_NONBLOCK = os.O_NONBLOCK
except AttributeError:  # pragma: no cover - not on every platform
    _O_NONBLOCK = 0

# TASK-ABFIX-011: default per-test pytest-timeout (seconds) the Coach injects
# into its isolated pytest run so a single hanging test is marked FAILED while
# the others still run, instead of consuming the whole subprocess budget and
# yielding ``tests_run=0``. Generous by design — the Coach runs focused
# per-task suites, so a test exceeding 60s is almost certainly hung, not slow.
# Operator-tunable via ``GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS``; injection is
# triple-gated (operator flag, Python stack, plugin-resolvable). See
# ``.claude/rules/stack-plugin-architecture.md`` and
# ``.claude/rules/absence-of-failure-is-not-success.md``.
_DEFAULT_COACH_PER_TEST_TIMEOUT_S = 60

# TASK-AB-COACHSUBPROC01 (2026-07-04): single source of truth for the Coach's
# independent test-execution default — flipped "sdk" -> "subprocess". The SDK
# "environment parity" path failed with the opaque exit-1 "Fatal error in
# message reader" on essentially 100% of invocations across every repo,
# machine and vintage in the 2026 retro corpus (2026-07-04 xref §5 item 15);
# every verdict actually came from the subprocess fallback, so each Coach turn
# paid one doomed SDK attempt. The SDK path stays in-repo as an explicit
# opt-in (config `autobuild.coach.test_execution: sdk` or env
# `GUARDKIT_COACH_TEST_EXECUTION=sdk`) for the open diagnosis tasks
# (TASK-REV-COSE, TASK-FIX-A7B7). Mirrors the ``selector.py::DEFAULT_HARNESS``
# cutover shape: permanent rollback = change this one constant back to "sdk".
DEFAULT_COACH_TEST_EXECUTION = "subprocess"

# Env override for the Coach test-execution mode. Precedence mirrors the
# TASK-AB-PERTASKFG01 ``GUARDKIT_PHASE4_TEST_EXECUTION`` pattern:
# env > config (``autobuild.coach.test_execution``) > default.
COACH_TEST_EXECUTION_ENV = "GUARDKIT_COACH_TEST_EXECUTION"

_VALID_COACH_TEST_EXECUTION_MODES = ("subprocess", "sdk")


def resolve_coach_test_execution(config_value: Optional[str] = None) -> str:
    """Resolve the Coach independent test-execution mode.

    Precedence: ``GUARDKIT_COACH_TEST_EXECUTION`` env var > *config_value*
    (``.guardkit/config.yaml`` ``autobuild.coach.test_execution``) >
    :data:`DEFAULT_COACH_TEST_EXECUTION`. Read at call time (not import time)
    so tests and operators can flip it per-invocation. An unrecognised value
    at either tier logs a WARNING and that tier is ignored (falls through to
    the next tier), so an invalid value can never select a mode by accident.

    Logs the active mode and its provenance (env/config/default) at INFO —
    called once per :class:`CoachValidator` init, so operators can see which
    execution path the Coach will use and where the decision came from
    (display-must-derive-from-enforcement-source: the logged value IS the
    value the validator consumes, not a proxy).

    Parameters
    ----------
    config_value : Optional[str]
        The raw ``autobuild.coach.test_execution`` value from
        ``.guardkit/config.yaml``, or None when unset.

    Returns
    -------
    str
        ``"subprocess"`` or ``"sdk"``.
    """
    mode: Optional[str] = None
    source = "default"

    env_raw = os.environ.get(COACH_TEST_EXECUTION_ENV)
    if env_raw is not None and env_raw.strip():
        candidate = env_raw.strip().lower()
        if candidate in _VALID_COACH_TEST_EXECUTION_MODES:
            mode, source = candidate, "env"
        else:
            logger.warning(
                "Invalid %s=%r (expected one of %s); ignoring env override.",
                COACH_TEST_EXECUTION_ENV,
                env_raw,
                _VALID_COACH_TEST_EXECUTION_MODES,
            )

    if mode is None and config_value is not None and str(config_value).strip():
        candidate = str(config_value).strip().lower()
        if candidate in _VALID_COACH_TEST_EXECUTION_MODES:
            mode, source = candidate, "config"
        else:
            logger.warning(
                "Invalid autobuild.coach.test_execution=%r in "
                ".guardkit/config.yaml (expected one of %s); "
                "falling back to default %r.",
                config_value,
                _VALID_COACH_TEST_EXECUTION_MODES,
                DEFAULT_COACH_TEST_EXECUTION,
            )

    if mode is None:
        mode = DEFAULT_COACH_TEST_EXECUTION

    logger.info(
        "Coach test execution mode: %s (source: %s; "
        "%s > autobuild.coach.test_execution > default %r) "
        "[TASK-AB-COACHSUBPROC01]",
        mode,
        source,
        COACH_TEST_EXECUTION_ENV,
        DEFAULT_COACH_TEST_EXECUTION,
    )
    return mode



def _checker_env(
    validator: "CoachValidator",
    *,
    additions: Optional[Dict[str, str]] = None,
    path_first: Sequence[str] = (),
    fixtures: bool = False,
    main_checkout: bool = False,
) -> Dict[str, str]:
    """The environment one of the checker's project commands runs with,
    built from nothing (see ``CoachValidator._project_env`` for what each
    argument adds). A module-level function, so the process-launch guard can
    rely on it (a method could be overridden); the methods delegate here."""
    return project_command_environment(
        validator.worktree_path,
        validator._launch_declaration(main_checkout),
        additions=validator._command_additions(additions, fixtures),
        path_first=path_first,
    )


def _checker_declared_env(validator: "CoachValidator") -> Dict[str, str]:
    """The checker's declared-command environment, with the test-service URLs."""
    return _checker_env(validator, fixtures=True)


# ============================================================================
# Data Models
# ============================================================================


def _combined_output_tail(
    stdout: Optional[str], stderr: Optional[str], bound: int = 2000
) -> Optional[str]:
    """Combined stdout+stderr tail for ``RuntimeParityResult.output_tail``.

    2026-07-04 code review (runtime-parity stdout gap): pytest writes its
    ``FAILED <nodeid>`` short-summary lines to STDOUT, so a stderr-only tail
    hides the failing-test names from the per-task parity guard's evidence
    extraction. Joins stdout first, then stderr (mirroring
    ``feature_orchestrator._build_smoke_feedback``'s combined_output), each
    stream bounded to its last *bound* chars. Returns ``None`` when neither
    stream produced output — consumers then fall back to ``stderr_tail``.
    """
    parts = [
        part.rstrip()[-bound:]
        for part in (stdout, stderr)
        if part and part.rstrip()
    ]
    return "\n".join(parts) or None


#: The kinds of command run record the independent check makes (repair 7),
#: and what each one's execution root is, in plain words.
EVIDENCE_WORKTREE = "independent suite (worktree)"
EVIDENCE_SDK = "independent suite (through the SDK, in the worktree)"
EVIDENCE_ORACLE = "behavioural oracle"
EVIDENCE_ROOT_DESCRIPTIONS = {
    EVIDENCE_WORKTREE: "the build worktree",
    EVIDENCE_SDK: "the build worktree (the command was run by an SDK agent)",
    EVIDENCE_ORACLE: "the build worktree",
}


@dataclass
class IndependentTestResult:
    """
    Result of independent test verification.

    Attributes
    ----------
    tests_passed : bool
        Whether tests passed when run independently
    test_command : str
        Command used to run tests
    test_output_summary : str
        Summary of test output
    duration_seconds : float
        Time taken to run tests
    raw_output : Optional[str]
        Full stdout+stderr from test execution, used for failure classification
    signal_absent : bool
        ``True`` when the independent-test oracle did NOT produce a verdict —
        the run timed out or failed at the transport layer (SDK timeout, SDK
        API error, subprocess/isolated-test timeout, or generic execution
        error) before pytest could report a pass/fail. This is distinct from
        "ran and failed" (``tests_passed=False`` with ``signal_absent=False``):
        an absent signal means the trust-but-verify leg never completed.
        ``tests_passed`` is always ``False`` when ``signal_absent`` is ``True``
        so the result can never read as a pass. An absent signal sends
        nothing back (27 October 2026).
    tests_skipped : Optional[int]
        Advisory pytest ``skipped`` count from the independent run. Tri-state:
        ``None`` = not parsed / unknown (never coerced to ``0``), ``0`` = the
        summary parsed cleanly with zero skips, ``N`` = N tests skipped. A
        skipped test is an ABSENT verdict, not a pass — a nonzero count may
        indicate missing optional extras in the worktree venv silently
        under-testing the deliverable. Advisory ONLY: no gate or verdict
        branch reads this field; it is surfaced to the Coach (evidence
        bundle / prompt) and the operator (``coach_turn_N.json``) for
        visibility.
    resolved_interpreter : Optional[str]
        The Python interpreter the independent pytest run was actually pinned
        to (``_pytest_interpreter()`` — the bootstrap venv when resolved,
        else ``sys.executable``). ``None`` when no interpreter-pinned run
        happened (non-pytest command, SDK/PATH execution, skipped run).
        Forensic evidence ONLY (TASK-AB-RESUMEVENV01 AC-003): no gate or
        verdict branch reads it — it makes the "which interpreter did the
        verifier actually run?" post-mortem a one-grep answer instead of a
        reproduction session (FEAT-ABL-005 run 4).
    """

    tests_passed: bool
    test_command: str
    test_output_summary: str
    duration_seconds: float
    raw_output: Optional[str] = None
    signal_absent: bool = False
    # TASK-AB-SKIPVIS01: advisory skip-count visibility. None = unknown, never
    # 0-coerced; never joins any verdict / turn-rejecting / stall logic.
    tests_skipped: Optional[int] = None
    # TASK-AB-RESUMEVENV01: forensic interpreter evidence. None = no pinned
    # run; never read by any verdict / gate / stall logic.
    resolved_interpreter: Optional[str] = None
    # THE CHECK COULD NOT RUN (2026-09-11). "The check ran and the result is
    # bad" and "the check could not run" are different outcomes and must never
    # share a code path. ``True`` means nothing was verified because the check
    # could not START — the command was not runnable where it was asked to
    # run. It is an ESTATE fault, never the builder's: it is never put in the
    # builder's feedback as something to fix, it can never let a quality gate
    # report a pass, and it is reported to the operator's log and the turn's
    # receipt in plain words. ``signal_absent`` stays ``True`` alongside it so
    # every existing "absence is never a pass" guard still holds.
    check_could_not_run: bool = False
    # One plain sentence for the operator: the command, the directory it was
    # asked to run in, and what was missing. Never shown to the builder.
    check_could_not_run_detail: Optional[str] = None
    # The command's own exit status, when it ran as a subprocess (12 October
    # 2026). ``None`` when there was none to read (the agent-shell path, a
    # timeout, a skipped run). Read only by ``failure_receipt`` below.
    exit_code: Optional[int] = None

    # WHAT THE CHECK RAN AGAINST (repair 7, 2026-10-12): one record per
    # command run for this check, in order. Each names the real execution root, its
    # source before and after, the declared environment inventory and the
    # raw container events of the interval (see ``run_evidence``). Receipt
    # evidence only: no gate, verdict or feedback branch reads it.
    run_evidence: Optional[Dict[str, Any]] = None
    # One record per part whose tests ran for this check (31 October 2026):
    # its name, folder, command and outcome ("passed", "failed", "could not
    # run"). ``None`` when no part ran. Receipt evidence only.
    parts: Optional[List[Dict[str, Any]]] = None

    def failure_receipt(self) -> Optional[Dict[str, Any]]:
        """This run's own failure facts, for the Player's feedback.

        ``None`` unless the run really ran and failed: a pass, an absent
        signal and a check that could not run are never described as a
        failure to fix. Otherwise the command, its exit status and the first
        failing lines of its output (``failing_test_feedback``), so the
        Player is told what THIS turn's run said whatever the reviewer's prose
        says (build 7010, 12 October 2026).
        """
        if self.tests_passed or self.signal_absent or self.check_could_not_run:
            return None
        from guardkit.orchestrator.failing_test_feedback import (
            first_failing_lines,
        )

        return {
            "command": self.test_command,
            "exit_code": self.exit_code,
            "failing_lines": first_failing_lines(
                self.raw_output or self.test_output_summary
            ),
        }

    # ------------------------------------------------------------------
    # TASK-AB-REVIEWCLEAN01 (item 3): outcome-shape factories. The advisory
    # ``tests_skipped`` and forensic ``resolved_interpreter`` fields were
    # hand-populated at ~16 construction sites; a site that forgot one
    # silently dropped evidence. These three classmethods own the population
    # per outcome shape so it cannot be omitted:
    #   - from_run: a run that PRODUCED OUTPUT — derives ``tests_skipped``
    #     from that output (impossible to forget); pass/fail is the caller's.
    #   - absent:   an ABSENT signal (timeout / transport / substrate gap) —
    #     ``tests_passed=False``, ``signal_absent=True``, ``tests_skipped=None``
    #     (nothing to parse). ``resolved_interpreter`` optional (subprocess
    #     shapes carry it; SDK-transport shapes do not).
    #   - skipped:  the task changed no declared part, so nothing ran. Not a
    #               pass (31 October 2026): ``tests_passed`` is False and the
    #               signal is absent, so no record reads it as tested.
    # ------------------------------------------------------------------

    @classmethod
    def from_run(
        cls,
        *,
        tests_passed: bool,
        test_command: str,
        test_output_summary: str,
        duration_seconds: float,
        output: Optional[str],
        resolved_interpreter: Optional[str],
        signal_absent: bool = False,
        exit_code: Optional[int] = None,
    ) -> "IndependentTestResult":
        """A run that produced ``output``. Derives the advisory skip count
        from ``output`` so it can never be silently omitted."""
        return cls(
            tests_passed=tests_passed,
            test_command=test_command,
            test_output_summary=test_output_summary,
            duration_seconds=duration_seconds,
            raw_output=output,
            signal_absent=signal_absent,
            tests_skipped=parse_pytest_summary(output).skipped,
            resolved_interpreter=resolved_interpreter,
            exit_code=exit_code,
        )

    @classmethod
    def absent(
        cls,
        *,
        test_command: str,
        test_output_summary: str,
        duration_seconds: float,
        raw_output: Optional[str] = None,
        resolved_interpreter: Optional[str] = None,
    ) -> "IndependentTestResult":
        """An ABSENT signal — the oracle never produced a verdict (timeout,
        SDK transport error, host-substrate gap). Never a pass; no skip
        count to parse."""
        return cls(
            tests_passed=False,
            test_command=test_command,
            test_output_summary=test_output_summary,
            duration_seconds=duration_seconds,
            raw_output=raw_output,
            signal_absent=True,
            tests_skipped=None,
            resolved_interpreter=resolved_interpreter,
        )

    @classmethod
    def could_not_run(
        cls,
        *,
        test_command: str,
        detail: str,
        duration_seconds: float,
        raw_output: Optional[str] = None,
        resolved_interpreter: Optional[str] = None,
    ) -> "IndependentTestResult":
        """THE CHECK COULD NOT RUN — nothing about the builder's work was
        measured, because the command could not start where it was asked to
        start.

        A different outcome from "ran and failed", and from a run that started
        and then produced nothing (a timeout): this one is an estate fault.
        ``detail`` is the operator's plain sentence — the command, the
        directory, and what was missing. ``signal_absent`` is ``True`` as
        well, so every existing guard that refuses to read an absent signal as
        a pass keeps working unchanged.
        """
        return cls(
            tests_passed=False,
            test_command=test_command,
            test_output_summary=detail,
            duration_seconds=duration_seconds,
            raw_output=raw_output,
            signal_absent=True,
            tests_skipped=None,
            resolved_interpreter=resolved_interpreter,
            check_could_not_run=True,
            check_could_not_run_detail=detail,
        )

    @classmethod
    def skipped(
        cls,
        *,
        test_output_summary: str,
        test_command: str = "skipped",
        duration_seconds: float = 0.0,
    ) -> "IndependentTestResult":
        """Nothing to run: the task changed no declared part.

        Never a pass (after-task check redesign, 31 October 2026): it used to
        read ``tests_passed=True``, so tasks that wrote tests were recorded as
        tested when nothing ran. It sends nothing back either.
        """
        return cls(
            tests_passed=False,
            test_command=test_command,
            test_output_summary=test_output_summary,
            duration_seconds=duration_seconds,
            signal_absent=True,
        )


def _folder_fingerprint(folder: Path) -> str:
    """A fingerprint of the files directly in ``folder`` (not subfolders):
    each name with its content, or its link target for a symbolic link."""
    digest = hashlib.sha256()
    try:
        entries = sorted(folder.iterdir(), key=lambda e: e.name)
    except OSError:
        return ""
    for entry in entries:
        try:
            if entry.is_symlink():
                body = ("link:" + os.readlink(entry)).encode("utf-8", "surrogateescape")
            elif entry.is_file():
                body = entry.read_bytes()
            else:
                continue
        except OSError:
            body = b"<unreadable>"
        digest.update(entry.name.encode("utf-8", "surrogateescape") + b"\0")
        digest.update(hashlib.sha256(body).digest())
    return digest.hexdigest()


def _part_outcome(result: IndependentTestResult) -> str:
    if result.check_could_not_run or result.signal_absent:
        return "could not run"
    return "passed" if result.tests_passed else "failed"


def combine_part_results(
    runs: Sequence[Tuple[Any, IndependentTestResult]],
) -> IndependentTestResult:
    """One result from the runs of each changed part (31 October 2026).

    ``runs`` pairs each part (a ``DeclaredPart``) with its run. A part that
    ran and failed wins: the result is a failure, so the task goes back to
    the builder with that part's output. Otherwise a part that could not run
    (would not start, timed out, gave no test signal, declared nothing) makes
    the result "the check could not run", naming the part and its command:
    nothing was measured, and it is not the builder's to fix. Only when every
    part ran and passed is the result a pass. ``parts`` records each part's
    outcome.
    """
    records = [
        {
            "part": part.name,
            "folder": part.cwd,
            "command": result.test_command,
            "outcome": _part_outcome(result),
        }
        for part, result in runs
    ]
    failed = [(p, r) for p, r in runs if _part_outcome(r) == "failed"]
    not_run = [(p, r) for p, r in runs if _part_outcome(r) == "could not run"]
    duration = sum(r.duration_seconds for _, r in runs)

    def joined_command(items: Sequence[Tuple[Any, IndependentTestResult]]) -> str:
        if len(items) == 1:
            return items[0][1].test_command
        return " ; ".join(f"{r.test_command} (in {p.cwd})" for p, r in items)

    if failed:
        if len(failed) == 1:
            result = dataclass_replace(failed[0][1])
        else:
            result = IndependentTestResult(
                tests_passed=False,
                test_command=joined_command(failed),
                test_output_summary="\n\n".join(
                    f"Part {p.name} ({p.cwd}): {r.test_output_summary}"
                    for p, r in failed
                ),
                duration_seconds=duration,
                raw_output="\n\n".join(
                    f"=== part {p.name} ({p.cwd}): {r.test_command}\n"
                    f"{r.raw_output or r.test_output_summary}"
                    for p, r in failed
                ),
                exit_code=failed[0][1].exit_code,
                resolved_interpreter=failed[0][1].resolved_interpreter,
            )
    elif not_run:
        detail = "The check could not run: " + "; ".join(
            f"part {p.name} (`{r.test_command}` in {p.cwd}): "
            f"{r.check_could_not_run_detail or r.test_output_summary}"
            for p, r in not_run
        )
        result = IndependentTestResult.could_not_run(
            test_command=joined_command(not_run),
            detail=detail,
            duration_seconds=duration,
            raw_output="\n\n".join(r.raw_output for _, r in not_run if r.raw_output)
            or None,
        )
    elif len(runs) == 1:
        result = dataclass_replace(runs[0][1])
    else:
        result = IndependentTestResult(
            tests_passed=True,
            test_command=joined_command(runs),
            test_output_summary="\n".join(
                f"Part {p.name} ({p.cwd}): {r.test_output_summary}" for p, r in runs
            ),
            duration_seconds=duration,
            raw_output="\n\n".join(r.raw_output for _, r in runs if r.raw_output)
            or None,
        )
    evidence = [
        record
        for _, r in runs
        for record in ((r.run_evidence or {}).get("runs") or [])
    ]
    result.run_evidence = {"runs": evidence} if evidence else None
    result.parts = records
    return result


# The words ``_test_command_source`` carries when the command came from the
# repository's own ``.guardkit/config.yaml`` rather than from a guess. One
# spelling, set in one place and read in one place, so nothing downstream has
# to match a string it invented.
DECLARED_COMMAND_SOURCE = "repository toolchain declaration"


# ============================================================================
# Coach Validator
# ============================================================================


class CoachValidator:
    """
    Lightweight Coach that validates task-work results.

    This class does NOT reimplement quality gates - it reads task-work outputs
    and performs independent verification before making approve/feedback decision.

    Validation Flow
    ---------------
    1. Read task-work results from JSON file
    2. Verify all quality gates passed
    3. Run independent test verification (trust but verify)
    4. Validate requirements satisfaction
    5. Return approve if all checks pass, feedback otherwise

    Attributes
    ----------
    worktree_path : Path
        Path to the git worktree
    test_command : Optional[str]
        Command to run tests (auto-detected or specified)
    test_timeout : int
        Timeout for test execution in seconds

    Example
    -------
    >>> validator = CoachValidator("/path/to/worktree")
    >>> result = validator.validate("TASK-001", 1, {"acceptance_criteria": [...]})
    >>> print(f"Decision: {result.decision}")
    """

    # Quality gate thresholds (match task-work)
    ARCH_REVIEW_THRESHOLD = 60
    # Default profile for backward compatibility
    DEFAULT_PROFILE = get_profile(TaskType.FEATURE)

    # High-confidence infrastructure patterns (safe for conditional approval)
    _INFRA_HIGH_CONFIDENCE: List[str] = [
        # Connection/network errors
        "ConnectionRefusedError",
        "ConnectionError",
        "Connection refused",
        "could not connect to server",
        # Database drivers
        "OperationalError",
        "psycopg2",
        "psycopg",
        "asyncpg",
        "sqlalchemy.exc.OperationalError",
        "django.db.utils.OperationalError",
        "pymongo.errors.ServerSelectionTimeoutError",
        "redis.exceptions.ConnectionError",
    ]

    # SDK API error patterns — the LLM backend rejected the request (wrong model
    # name, invalid parameters, rate limits, etc.).  These are NOT code defects.
    _SDK_API_ERROR_PATTERNS: List[str] = [
        "SDK API error",
        "invalid_request",
        "invalid_request_error",
        "AssistantMessage.error",
    ]

    # Ambiguous infrastructure patterns (feedback only, not conditional approval)
    _INFRA_AMBIGUOUS: List[str] = [
        "ModuleNotFoundError",
        "ImportError",
        "No module named",
    ]

    # Known service-client libraries whose absence indicates a missing dependency
    # install (not a code defect). ModuleNotFoundError for these is promoted to
    # high confidence.
    # NOTE: psycopg2 is intentionally excluded — projects using asyncpg may
    # accidentally import psycopg2, which is a Player code-choice error, not an
    # infrastructure failure.  Classifying it as ("infrastructure", "high") gave
    # the Player wrong advice (mock fixtures / SQLite) instead of telling them to
    # remove the wrong import.
    _KNOWN_SERVICE_CLIENT_LIBS: List[str] = [
        "asyncpg",
        "pymongo",
        "redis",
        "psycopg",
        "sqlalchemy",
        "motor",
        "aioredis",
        "cassandra",
    ]

    # TASK-ABFIX-012: stack-agnostic HOST-SUBSTRATE gap signals. A test command
    # that could not run because a host tool is missing (the command itself, or a
    # tool a test shells out to — e.g. psql/docker/dotnet/npm/node). Routed to
    # ("infrastructure", "high") in ``_classify_test_failure`` AND to
    # ``signal_absent=True`` in ``run_independent_tests`` (via
    # ``_is_host_substrate_gap``), so a substrate-blocked TESTING task surfaces as
    # ABSENT / feedback (bounded by max_turns) — never a code-class block (the
    # false-red ABFIX-010 prevents) and never a false pass
    # (absence-of-failure-is-not-success). Stack-agnostic shell vocabulary, not
    # Python-specific. NOTE: the bare ": not found" / "no such file or directory"
    # idioms are intentionally EXCLUDED — they false-match legitimate code
    # failures ("key: not found", a test asserting FileNotFoundError), which would
    # mis-route a real bug to infrastructure and re-open a false-green. The
    # definitive rc-126/127 signal in ``_is_host_substrate_gap`` covers those.
    _HOST_SUBSTRATE_MISSING_PATTERNS: List[str] = [
        "command not found",
        "executable file not found",
        "is not recognized as an internal or external command",
    ]

    # TASK-ABFIX-012: high-confidence OWN-CODE-BUG signals. A genuine Python
    # exception token in a TESTING task's own test output is a deterministic code
    # defect — a filesystem race (the contention ABFIX-005 amnesties) surfaces as
    # import / collection errors, not a clean AssertionError/AttributeError. Used
    # ONLY to neutralise the parallel-wave ``parallel_contention`` amnesty for
    # TESTING: a token match returns ("code", "high") regardless of wave_size, so a
    # real assertion failure is rejected in BOTH single and parallel waves. (Single
    # waves already classify ("code", "n/a") via the natural fallback, which the
    # guard also blocks.)
    _CODE_FAILURE_HIGH_CONFIDENCE: List[str] = [
        "assertionerror",
        "attributeerror",
        "has no attribute",
        "nameerror",
        "is not defined",
        "typeerror",
    ]

    def __init__(
        self,
        worktree_path: str,
        test_command: Optional[str] = None,
        test_timeout: Optional[int] = None,  # TS-lane D.1b: declaration-aware
        task_id: Optional[str] = None,
        coach_test_execution: Optional[str] = None,
        matching_strategy: str = "auto",
        wave_size: int = 1,
        turn: int = 1,
        model_name: Optional[str] = None,
        coach_model_name: Optional[str] = None,  # TASK-FIX-COACHBUDG01
        venv_python: Optional[str] = None,  # TASK-FIX-COACHPYENV
        evidence_repos: Optional[List["EvidenceRepo"]] = None,  # TASK-AB-XREPOEV01
        smoke_command: Optional[str] = None,  # TASK-AB-COACHRUNPARITY01 (arm b)
        smoke_expected_exit: int = 0,  # TASK-AB-COACHRUNPARITY01 (arm b)
        security_command: Optional[str] = None,  # the secrets check, when on
        feature_check_repair: Optional[Any] = None,  # whole-feature repair round
        toolchain: Optional["ToolchainDeclaration"] = None,  # TS-lane D.1b
        baseline_commit: Optional[str] = None,  # the task's starting commit
    ):
        """
        Initialize CoachValidator.

        Parameters
        ----------
        worktree_path : str
            Path to the git worktree where validation should execute
        test_command : Optional[str]
            Command to run tests. If None, auto-detects based on project.
        test_timeout : Optional[int]
            Timeout for test execution in seconds. ``None`` (default) resolves
            via the repo's snapshotted ``toolchain.test_timeout`` declaration
            (TS-lane D.1b), else 300s — the historic hardcoded value, so a
            repo with no declaration is unchanged. An explicit int always wins.
        task_id : Optional[str]
            Task identifier for task-specific test filtering in shared worktrees.
            When provided, test detection will first look for task-specific test
            files before falling back to running the full test suite.
        coach_test_execution : Optional[str]
            Test execution mode: "subprocess" (default,
            TASK-AB-COACHSUBPROC01) uses subprocess.run() directly with the
            venv-pinned interpreter; "sdk" (opt-in — see the open diagnosis
            tasks TASK-REV-COSE / TASK-FIX-A7B7) runs pytest through the
            Claude Agent SDK Bash tool for environment parity, with the
            subprocess path as fallback. None (default) resolves via
            :func:`resolve_coach_test_execution` (env
            ``GUARDKIT_COACH_TEST_EXECUTION`` > default). Callers that read
            ``.guardkit/config.yaml`` resolve
            ``resolve_coach_test_execution(config_value)`` before
            constructing. An explicit value is authoritative (validated, but
            never env-overridden) so pinned callers like the deterministic
            Phase-4 runner (``specialist_invocations.py``,
            TASK-AB-PERTASKFG01: never an LLM turn) cannot be flipped by the
            Coach env lever.
        matching_strategy : str
            Text matching strategy for acceptance criteria verification.
            ``"text"``: strict Jaccard threshold (70%), ``"semantic"``: lower
            threshold (50%) with fuzzy keyword prefix matching for local/vLLM
            backends, ``"auto"`` (default): resolves to ``"semantic"`` when
            ``ANTHROPIC_BASE_URL`` points to a non-Anthropic endpoint, otherwise
            ``"text"``.  Can also be set via ``GUARDKIT_MATCHING_STRATEGY`` env var.
        wave_size : int
            Number of tasks in the current wave (default: 1). When >1 the
            failure classification is more lenient for contention-related
            errors; it only shapes the words the builder is sent.
        model_name : Optional[str]
            Orchestrator-configured model name to thread through to the harness
            for SDK-based Coach test execution. Used as a fallback when the
            ``GUARDKIT_COACH_TEST_MODEL`` env var is not set. Mirrors the model
            threading precedent set by TASK-FIX-LGFM2 / TASK-FIX-MODELPLUMB in
            ``AgentInvoker``. Without this, the LangGraph harness receives
            ``model=None`` for ``role='coach_test'`` and falls back to subprocess
            (TASK-FIX-LGFM3 / F12).
        venv_python : Optional[str]
            Path to the bootstrap venv Python interpreter Coach should run its
            independent tests under (typically ``BootstrapResult.venv_python``
            threaded from the feature orchestrator). When set, the SDK and
            subprocess test paths pin pytest to this interpreter instead of the
            host ``which pytest`` / ``sys.executable``. Resolution follows
            :func:`guardkit.orchestrator.coach_verification._resolve_venv_python`.
            Without it, Coach could validate against the wrong interpreter
            (TASK-FIX-COACHPYENV — sibling of the TASK-FIX-7A05 CoachVerifier fix).
            WORKTREE tests only: this interpreter is never threaded into
            sibling ``evidence_repos`` tests (TASK-FIX-SIBTESTENV01).
        evidence_repos : Optional[List[EvidenceRepo]]
            Declared sibling repos whose independent tests the Coach runs
            (TASK-AB-XREPOEV01 AC-002). When a repo carries a ``test_command``,
            :meth:`run_evidence_repo_tests` executes it in that repo under the
            repo's OWN interpreter (TASK-FIX-SIBTESTENV01 — never the guardkit
            worktree venv); results reach the evidence bundle and a
            ran-and-failed (or declared-but-unrunnable) suite blocks the turn.
            Default None -> no sibling-repo test execution.
        toolchain : Optional[ToolchainDeclaration]
            The repo's declared toolchain block (TS-lane D.1b). ``None``
            (default) loads the PRE-TURN-1 SNAPSHOT for ``task_id`` — never
            the live ``<worktree>/.guardkit/config.yaml``, which sits inside
            the tree the Player edits (design §B.4). No snapshot ⇒ no
            declaration ⇒ the detection ladder runs exactly as it did before.
        baseline_commit : Optional[str]
            The commit the task started from (``TaskWorkScope.baseline_commit``).
            The files changed since it decide which parts' tests run
            (after-task check redesign, 31 October 2026). ``None`` falls back
            to the files the builder's report lists.
        """
        self.worktree_path = Path(worktree_path)
        self.test_command = test_command
        self.task_id = task_id
        # Service URLs (e.g. DATABASE_URL) of the fixtures THIS validator
        # started. Given to its own test subprocesses only, never written to
        # os.environ, so a parallel task's teardown cannot remove them and a
        # parallel task never sees them (concurrent builds, 2026-10-03).
        self._fixture_env: Dict[str, str] = {}
        # TS-lane D.1b: THE DECLARATION. Resolved from the pre-turn-1 snapshot
        # so a Player turn cannot rewrite its own test command mid-build. An
        # explicitly-passed declaration (tests, callers that already hold one)
        # wins; otherwise the snapshot; otherwise absent.
        self._toolchain: Optional["ToolchainDeclaration"] = toolchain
        if self._toolchain is None and task_id:
            from guardkit.orchestrator.toolchain_declaration import (
                load_toolchain_snapshot,
            )

            self._toolchain = load_toolchain_snapshot(task_id, self.worktree_path)
        if self._toolchain is not None:
            logger.info(
                "CoachValidator honouring the repo's declared toolchain "
                "(test=%r, test_timeout=%ss, components=%s)",
                self._toolchain.test,
                self._toolchain.test_timeout,
                self._toolchain.component_names or "none",
            )
        # ---- the part whose tests are about to run ------------------------
        # Set by ``_use_part`` for each changed part in turn (after-task check
        # redesign, 31 October 2026): ``None`` for the root component, else
        # the component's or pattern part's commands with their ``cwd``.
        self._baseline_commit: Optional[str] = baseline_commit
        self._component: Optional[str] = None
        self._component_toolchain: Optional["ComponentToolchain"] = None
        # Explicit caller value > the part's declared timeout > the root
        # block's > the historic 300s.
        self._explicit_test_timeout: Optional[int] = test_timeout
        self.test_timeout = self._timeout_for_part()
        # Set by ``_detect_test_command`` when the part declares no test
        # command: ``run_independent_tests`` reports that the check could not
        # run, naming what is missing. GuardKit never guesses a command.
        self._detection_absence: Optional[str] = None
        # Where the command about to run came from, in ordinary words. Set by
        # ``_detect_test_command``. Never read by any verdict rule.
        self._test_command_source: Optional[str] = None
        # TASK-AB-COACHSUBPROC01: None -> resolve env > default (subprocess);
        # resolve_coach_test_execution logs the active mode + provenance once
        # per init. An explicit value is authoritative (validated with safe
        # degrade, never env-overridden — protects pinned callers like the
        # deterministic Phase-4 runner).
        if coach_test_execution is None:
            coach_test_execution = resolve_coach_test_execution()
        elif coach_test_execution not in _VALID_COACH_TEST_EXECUTION_MODES:
            # 2026-07-04 code review: an INVALID explicit value is not a pin —
            # delegate to the standard env > default resolution instead of
            # jumping straight to the default, so a valid
            # GUARDKIT_COACH_TEST_EXECUTION override still applies (mirrors
            # resolve_coach_test_execution's invalid-tier fall-through). Only
            # a VALID explicit value stays authoritative over env.
            logger.warning(
                "Invalid coach_test_execution=%r (expected one of %s); "
                "delegating to %s > default resolution.",
                coach_test_execution,
                _VALID_COACH_TEST_EXECUTION_MODES,
                COACH_TEST_EXECUTION_ENV,
            )
            coach_test_execution = resolve_coach_test_execution()
        else:
            logger.debug(
                "Coach test execution mode: %s (source: caller)",
                coach_test_execution,
            )
        self._coach_test_execution = coach_test_execution
        # TASK-FIX-COACHPYENV: resolve the interpreter Coach runs independent
        # tests under. Prefers the explicit bootstrap venv, then a filesystem
        # recovery probing ``<worktree>/.venv/bin/python`` (current bootstrap
        # layout) and legacy ``<worktree>/.guardkit/venv/bin/python``
        # (TASK-AB-RESUMEVENV01), else None (PATH pytest / sys.executable for
        # non-Python projects). Reuses the helper already battle-tested for
        # CoachVerifier (TASK-FIX-7A05) so the two Coach verification surfaces
        # resolve interpreters identically.
        # The interpreter is used only by the opt-in SDK test path and the
        # declared behavioural oracle's records. A worktree without one is
        # never a reason the check cannot run: the declared command runs as
        # declared (31 October 2026; it used to stop a project whose root held
        # a Python marker file but no venv, whatever it declared).
        self._configured_venv_python: Optional[str] = venv_python
        self._venv_python: Optional[Path] = _resolve_venv_python(
            self.worktree_path, venv_python, in_autobuild_context=False
        )
        if venv_python and (
            self._venv_python is None
            or str(self._venv_python) != str(Path(venv_python))
        ):
            # AC-4 mismatch guard: a bootstrap interpreter was configured but
            # the resolved interpreter differs (stale path / disappeared venv).
            # Loud WARNING — Coach is about to verify against a DIFFERENT
            # interpreter than the bootstrap installed packages into, which is
            # exactly the run-9 spurious-failure shape.
            logger.warning(
                "Coach test interpreter MISMATCH: configured bootstrap venv "
                "%s but resolved to %s. Independent tests may run under the "
                "wrong interpreter (TASK-FIX-COACHPYENV).",
                venv_python,
                self._venv_python if self._venv_python is not None else
                "PATH pytest / sys.executable",
            )
        elif self._venv_python is not None:
            logger.info(
                "CoachValidator pinning independent-test interpreter to %s",
                self._venv_python,
            )
        # TASK-FIX-LGFM3: orchestrator model threaded through for SDK test
        # execution path; falls back to None when caller didn't supply one.
        self._model_name: Optional[str] = model_name
        # TASK-FIX-COACHBUDG01 (2026-06-06): per-role Coach override. When
        # non-None, takes precedence over _model_name for the coach_test
        # path (consumed by _get_coach_test_model). Lets the operator
        # route Coach SDK test execution to the same Coach-specific model
        # (gemma4:26b) the Player↔Coach loop uses.
        self._coach_model_name: Optional[str] = coach_model_name
        # TASK-AB-XREPOEV01 (AC-002): declared sibling repos whose tests the
        # Coach runs independently. Empty -> no sibling test execution.
        self._evidence_repos: List[EvidenceRepo] = list(evidence_repos or [])
        # TASK-AB-COACHRUNPARITY01 (arm b): the feature smoke command (the
        # deliverable's real runtime entry point). When set AND wave_size == 1,
        # gather_evidence runs it and records a RuntimeParityResult so a
        # "passes pytest but does not run" deliverable is caught pre-approval.
        # None -> no per-task runtime-parity check.
        self.smoke_command: Optional[str] = smoke_command
        # Exit code that counts as a clean standalone run for the parity check.
        # Threaded from the feature's smoke_gates.expected_exit so the per-task
        # check agrees with the post-wave gate (default 0).
        self.smoke_expected_exit: int = smoke_expected_exit
        # The secrets check's command (security_check.security_check_command),
        # built before the task's first turn; None when the check is not on.
        self.security_command: Optional[str] = security_command
        # A whole-feature repair round's ``FeatureCheckRepair`` (18 October
        # 2026), threaded beside ``smoke_command``. When set, gather_evidence
        # runs the project's declared whole-feature check once on this turn's
        # code (single-task waves only) and records it with the attempt that
        # started the round. None on every other turn -> nothing runs.
        self.feature_check_repair: Optional[Any] = feature_check_repair
        self.wave_size = max(1, int(wave_size))
        # TASK-AB-NPDET01: the non-Python stack test-execution profile resolved
        # by ``_detect_test_command`` for THIS run (None when no stack row
        # matches and the declaration overlays nothing). ``run_independent_tests`` reads it to classify
        # absence stack-awarely (missing toolchain / zero-test => signal_absent).
        self._active_stack_profile: Optional[StackTestProfile] = None
        # TASK-ABFIX-011: cached result of the pytest-timeout availability probe
        # against the pinned interpreter (``None`` = not yet probed). The pinned
        # interpreter is fixed per validator instance, so one probe per instance
        # is sufficient and is shared across all three pytest injection sites.
        self._pytest_timeout_available_cache: Optional[bool] = None
        # TASK-DIAG-F4A2: Turn number for sdk_debug preservation paths.
        # Default 1 keeps backwards-compat for callers that don't pass it.
        self._turn = max(1, int(turn))
        # Resolve matching strategy: constructor arg > env var > "auto"
        _VALID_STRATEGIES = ("auto", "text", "semantic")
        env_strategy = os.environ.get("GUARDKIT_MATCHING_STRATEGY", "").lower()
        if matching_strategy not in _VALID_STRATEGIES:
            logger.warning(
                "Unrecognised matching_strategy %r, falling back to 'auto'",
                matching_strategy,
            )
            matching_strategy = "auto"
        if matching_strategy != "auto":
            self._matching_strategy = matching_strategy
        elif env_strategy in ("text", "semantic"):
            self._matching_strategy = env_strategy
        else:
            self._matching_strategy = "auto"

        logger.debug(
            f"CoachValidator initialized for worktree: {worktree_path}, "
            f"task_id: {task_id}, wave_size: {self.wave_size}"
        )

    @property
    def is_parallel(self) -> bool:
        """Return True when this Coach is running in a parallel wave (wave_size > 1)."""
        return self.wave_size > 1

    def _get_coach_test_model(self) -> Optional[str]:
        """Return the model for Coach SDK test invocations, or None to use CLI default.

        Resolution order:
        1. ``GUARDKIT_COACH_TEST_MODEL`` env var (operator override — e.g.
           claude-haiku-4-5-20251001 for cost reduction on the real Anthropic API).
        2. Orchestrator-supplied ``coach_model_name`` (TASK-FIX-COACHBUDG01):
           per-role Coach override (e.g. ``gemma4:26b`` while Player stays on
           ``qwen36-workhorse`` — TASK-HMIG-013). Takes precedence over the
           generic ``model_name`` for this Coach-specific path.
        3. Orchestrator-supplied ``model_name`` (TASK-FIX-LGFM3): same value
           threaded into ``AgentInvoker.select_harness`` calls. Without this
           fallback, the LangGraph harness receives ``model=None`` for
           ``role='coach_test'`` and the SDK path errors out (F12).
        4. ``None`` (harness uses CLI default).
        """
        import os
        env_model = os.environ.get("GUARDKIT_COACH_TEST_MODEL") or None
        if env_model is not None:
            return env_model
        if self._coach_model_name is not None:
            return self._coach_model_name
        return self._model_name

    def _resolve_task_type(self, task: Dict[str, Any]) -> TaskType:
        """
        Resolve task type from task metadata with alias support and fallback to default.

        Supports legacy task_type values through TASK_TYPE_ALIASES mapping.
        Logs info message when alias is used for transparency.

        Parameters
        ----------
        task : Dict[str, Any]
            Task data including optional task_type field

        Returns
        -------
        TaskType
            Resolved task type

        Raises
        ------
        ValueError
            If task_type is specified but invalid (not in enum or aliases)
        """
        task_type_str = task.get("task_type")

        if task_type_str is None:
            # No task_type specified - use default (feature)
            logger.debug("No task_type specified, defaulting to FEATURE profile")
            return TaskType.FEATURE

        # Try to parse as valid TaskType enum first
        try:
            task_type = TaskType(task_type_str)
            logger.debug(f"Resolved task_type from metadata: {task_type.value}")
            return task_type
        except ValueError:
            # Check aliases before raising error
            if task_type_str in TASK_TYPE_ALIASES:
                aliased_type = TASK_TYPE_ALIASES[task_type_str]
                logger.info(
                    f"Using task_type alias: '{task_type_str}' → '{aliased_type.value}' "
                    f"(update task frontmatter to use '{aliased_type.value}' directly)"
                )
                return aliased_type

            # Not a valid enum value or alias - raise error
            logger.error(f"Invalid task_type value: {task_type_str}")
            raise ValueError(
                f"Invalid task_type value: {task_type_str}. "
                f"Must be one of: {', '.join(t.value for t in TaskType)} "
                f"or valid alias: {', '.join(TASK_TYPE_ALIASES.keys())}"
            ) from None

    def gather_evidence(
        self,
        task_id: str,
        turn: int,
        task: Dict[str, Any],
        skip_arch_review: bool = False,
        context: Optional[str] = None,
    ) -> CoachEvidenceBundle:
        """Run the project's own checks for this turn and package the results.

        The reviewer (the LLM Coach) reads the bundle; its verdict is advice
        (27 October 2026). The turn is sent back only by what the project's
        own runs report: the tests of the parts the task changed
        (``independent_tests``, see :meth:`run_changed_parts`), the
        feature's declared smoke command (``runtime_parity``), the declared
        behavioural check (``behavioural_oracle``) and, in a whole-feature
        repair round, the project's whole-feature check. Nothing the Player
        wrote about its work is checked here. Never raises.

        ``skip_arch_review`` and ``context`` are accepted for the caller's
        signature and not used.
        """
        try:
            task_type = self._resolve_task_type(task)
        except ValueError as exc:
            logger.warning(
                "gather_evidence: %s; using the feature profile.", exc,
            )
            task_type = TaskType.FEATURE
        profile = get_profile(task_type)
        profile_name = getattr(profile, "name", None) or task_type.value

        # OPERATOR_HANDOFF: no evidence to gather.
        if task_type == TaskType.OPERATOR_HANDOFF:
            return CoachEvidenceBundle(
                gathering_status="complete",
                task_type=task_type.value,
                profile_name=profile_name,
            )

        task_work_results = self.read_quality_gate_results(task_id)
        if "error" in task_work_results:
            logger.info(
                "gather_evidence: no task-work results for %s (%s); the "
                "project's checks run without them.",
                task_id, task_work_results.get("error"),
            )
            task_work_results = {}

        gathering_status = "complete"
        gathering_error: Optional[str] = None

        # The tests of the parts this task changed, whatever its task type
        # (after-task check redesign, 31 October 2026).
        test_result: Optional[IndependentTestResult]
        try:
            test_result = self.run_changed_parts(
                task_work_results=task_work_results,
                task=task,
                turn=turn,
            )
        except Exception as exc:  # noqa: BLE001 — gathering never raises
            logger.error(
                "gather_evidence: the changed parts' tests raised: %s", exc,
            )
            test_result = None
            gathering_status = "partial_exception"
            gathering_error = f"independent_tests_exception: {exc}"

        if test_result is not None and test_result.check_could_not_run:
            logger.warning(
                "%s turn %s: the project's tests could not be run: %s",
                task_id,
                turn,
                test_result.check_could_not_run_detail
                or test_result.test_output_summary,
            )

        # The feature's declared smoke command, and in a whole-feature repair
        # round the project's whole-feature check.
        runtime_parity = self._gather_runtime_parity()
        whole_feature_check = self._gather_whole_feature_check()
        security_check = self._gather_security_check()

        # The declared behavioural check.
        behavioural_oracle_dict: Optional[Dict[str, Any]] = None
        try:
            behavioural_oracle_dict = self._produce_behavioural_oracle(task=task)
        except Exception as exc:  # noqa: BLE001 — gathering never raises
            logger.warning(
                "gather_evidence: behavioural-oracle raised %s; "
                "behavioural_oracle field left as None.",
                exc.__class__.__name__,
            )

        # What kind of failure a red run looks like; it only shapes the words
        # the Player is sent.
        independent_test_classification: Optional[IndependentTestClassification] = None
        if (
            test_result is not None
            and test_result.tests_passed is False
            and test_result.signal_absent is False
        ):
            fc, conf = self._classify_test_failure(
                test_result.raw_output,
                requires_infrastructure=(
                    task.get("requires_infrastructure") if task else None
                ),
                task_type=task_type.value,
            )
            independent_test_classification = IndependentTestClassification(
                failure_class=fc,
                confidence=conf,
                raw_output_excerpt=(test_result.raw_output or "")[-500:],
            )

        return CoachEvidenceBundle(
            gathering_status=gathering_status,
            gathering_error=gathering_error,
            independent_tests=test_result,
            independent_test_classification=independent_test_classification,
            task_type=task_type.value,
            profile_name=profile_name,
            behavioural_oracle=behavioural_oracle_dict,
            runtime_parity=runtime_parity,
            security_check=security_check,
            whole_feature_check=whole_feature_check,
        )

    # ------------------------------------------------------------------
    # The tests of the parts a task changed (31 October 2026)
    # ------------------------------------------------------------------

    def _timeout_for_part(self) -> int:
        if self._explicit_test_timeout is not None:
            return self._explicit_test_timeout
        if self._component_toolchain is not None:
            return self._component_toolchain.test_timeout
        if self._toolchain is not None:
            return self._toolchain.test_timeout
        return 300

    def _use_part(self, part: Optional[DeclaredPart]) -> None:
        """Make ``part`` the one the next run uses (``None``: the root)."""
        toolchain = part.toolchain if part is not None else None
        self._component = part.name if toolchain is not None else None
        self._component_toolchain = toolchain
        self.test_timeout = self._timeout_for_part()

    def _files_changed_since(self, commit: str) -> Optional[List[str]]:
        """The product files changed in the worktree since ``commit``
        (committed or not, created, changed or deleted), or ``None`` when git
        cannot say. Factory records are left out, as the task's own change
        list leaves them out."""
        from guardkit.orchestrator.task_work_scope import _product

        try:
            diff = run_git(
                ["diff", "--no-renames", "--name-only", "-z", commit],
                cwd=self.worktree_path,
                timeout=60,
            )
            untracked = run_git(
                ["ls-files", "--others", "--exclude-standard", "-z"],
                cwd=self.worktree_path,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Could not list the task's changed files: %s", exc)
            return None
        if diff.returncode != 0 or untracked.returncode != 0:
            return None
        names = (diff.stdout or "").split("\0") + (untracked.stdout or "").split("\0")
        return sorted({n for n in names if n and _product(n)})

    def _changed_files(
        self, task_work_results: Optional[Dict[str, Any]]
    ) -> Tuple[List[str], str]:
        """The files this task changed, and where the list came from.

        From git, since the task's starting commit. The builder's report is
        read only when that commit is not known or git cannot answer.
        """
        if self._baseline_commit:
            listed = self._files_changed_since(self._baseline_commit)
            if listed is not None:
                return listed, (
                    f"git, since the task's starting commit "
                    f"{self._baseline_commit[:10]}"
                )
        reported: set = set()
        for key in ("files_created", "files_modified", "files_deleted"):
            for name in (task_work_results or {}).get(key) or []:
                path = Path(str(name))
                if path.is_absolute():
                    try:
                        path = path.relative_to(self.worktree_path)
                    except ValueError:
                        continue
                if str(path) not in ("", "."):
                    reported.add(path.as_posix())
        return sorted(reported), "the builder's report"

    #: Where each part's last install is remembered (the folder's dependency
    #: files' fingerprint), per worktree, outside the worktree.
    _PART_INSTALLS_RECORD = "part-installs"

    def _part_installs_path(self) -> Path:
        return (
            TaskArtifactPaths.task_private_dir(
                self._PART_INSTALLS_RECORD, self.worktree_path
            )
            / "installs.json"
        )

    def _install_part_if_due(
        self, part: DeclaredPart
    ) -> Optional[IndependentTestResult]:
        """Run a component's or pattern part's declared ``install`` when due.

        Due the first time the part is tested in this worktree, and again only
        when its dependency files have changed since: the files directly in
        the part's folder (no subfolders), fingerprinted by name and content.
        GuardKit names no file; whatever a project keeps there counts. The
        install runs in the part's folder as the argument list the text
        splits into, with the part's ``install_timeout``. The root component
        is installed by the build's own bootstrap and is not run here.

        Returns ``None`` when nothing was due or the install succeeded, and
        "the check could not run" (naming the part and the install) when it
        failed, timed out or could not start (31 October 2026).
        """
        toolchain = part.toolchain
        if toolchain is None or not toolchain.install:
            return None
        command = toolchain.install

        def could_not_run(why: str) -> IndependentTestResult:
            return IndependentTestResult.could_not_run(
                test_command=command,
                detail=f"the declared install (`{command}`) for part {part.name} {why}",
                duration_seconds=0.0,
            )

        try:
            folder = resolve_component_cwd(self.worktree_path, toolchain.cwd)
        except ValueError as exc:
            return could_not_run(f"was not run: {exc}")
        key = f"{self.worktree_path.resolve()}::{toolchain.cwd}"
        record_path = self._part_installs_path()
        try:
            records = json.loads(record_path.read_text(encoding="utf-8"))
            if not isinstance(records, dict):
                records = {}
        except (OSError, ValueError):
            records = {}
        if records.get(key) == _folder_fingerprint(folder):
            return None
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            return could_not_run(f"could not be split into arguments ({exc})")
        if not argv:
            return could_not_run("is empty")
        logger.info(
            "Installing part %s before its tests: %s (in %s)",
            part.name, command, toolchain.cwd,
        )
        try:
            done = process_group.run_project_command(
                argv,
                cwd=str(folder),
                capture_output=True,
                text=True,
                timeout=toolchain.install_timeout,
                env=_checker_declared_env(self),
            )
        except subprocess.TimeoutExpired:
            return could_not_run(
                f"ran out of its {toolchain.install_timeout} seconds"
            )
        except OSError as exc:
            return could_not_run(
                f"could not start: {exc.strerror or type(exc).__name__}"
            )
        if done.returncode != 0:
            tail = ((done.stderr or "") + (done.stdout or "")).strip()[-600:]
            return could_not_run(
                f"failed (exit {done.returncode}): {tail or '(no output)'}"
            )
        records[key] = _folder_fingerprint(folder)
        try:
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not remember the install of part %s: %s", part.name, exc)
        return None

    def run_changed_parts(
        self,
        task_work_results: Optional[Dict[str, Any]] = None,
        task: Optional[Dict[str, Any]] = None,
        turn: Optional[int] = None,
    ) -> IndependentTestResult:
        """Run the declared tests of each part this task changed, once each.

        The parts come from the task's changed files
        (:func:`toolchain_declaration.parts_for_files`, matched in the
        worktree now, commands from the pinned declaration). The results are
        combined by :func:`combine_part_results`: a failure wins over a part
        that could not run, which wins over a pass. A task that changed no
        part has nothing to run (:meth:`IndependentTestResult.skipped`, never
        a pass). A caller-supplied ``test_command`` runs alone, as before.
        """
        if self.test_command:
            return self.run_independent_tests(
                task_work_results=task_work_results, task=task, turn=turn
            )
        files, source = self._changed_files(task_work_results)
        parts = parts_for_files(self._toolchain, self.worktree_path, files)
        if not parts:
            logger.info(
                "%s: the %d changed file(s) (from %s) are in no declared part; "
                "no tests to run.",
                self.task_id, len(files), source,
            )
            return IndependentTestResult.skipped(
                test_output_summary=(
                    f"No tests to run: the {len(files)} file(s) this task "
                    f"changed (from {source}) are in no declared part."
                ),
            )
        logger.info(
            "%s: running the tests of %d changed part(s) (%s), from %s.",
            self.task_id, len(parts), ", ".join(p.name for p in parts), source,
        )
        runs: List[Tuple[DeclaredPart, IndependentTestResult]] = []
        try:
            for part in parts:
                self._use_part(part)
                not_installed = self._install_part_if_due(part)
                if not_installed is not None:
                    runs.append((part, not_installed))
                    continue
                runs.append(
                    (
                        part,
                        self.run_independent_tests(
                            task_work_results=task_work_results,
                            task=task,
                            turn=turn,
                        ),
                    )
                )
        finally:
            self._use_part(None)
        return combine_part_results(runs)

    def _gather_whole_feature_check(self) -> Optional[Dict[str, Any]]:
        """This Coach turn's run of the whole-feature check, or ``None``.

        ``None`` outside a whole-feature repair round. Otherwise the record
        from ``feature_check.whole_feature_check_record``: the check is run at
        most once here, through the feature orchestrator's own attempt runner,
        and only on a single-task wave. Never raises.
        """
        repair = self.feature_check_repair
        if repair is None:
            return None
        try:
            from guardkit.orchestrator.feature_check import (
                whole_feature_check_record,
            )

            return whole_feature_check_record(repair, wave_size=self.wave_size)
        except Exception as exc:  # noqa: BLE001 — evidence never breaks gathering
            logger.warning(
                "gather_evidence: the whole-feature check record failed: %s",
                type(exc).__name__,
            )
            return None

    def _gather_security_check(self) -> Optional[Dict[str, Any]]:
        """Run the secrets check on this turn's changes, or ``None`` when it is off.

        The command exits 1 only for a confirmed secret, and prints the lines that
        hold one. A run that could not start or ran out of time is recorded as
        not run. Never raises.
        """
        if not self.security_command:
            return None
        from guardkit.orchestrator.security_check import RULE_TIMEOUT_SECONDS

        command = self.security_command
        try:
            proc = process_group.run_project_command(
                command,
                shell=True,
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                timeout=RULE_TIMEOUT_SECONDS,
                env=_checker_env(self),
            )
        except Exception as exc:  # noqa: BLE001 — a check that cannot run is not run
            logger.warning("Secrets check did not run: %s", exc)
            return {"ran": False, "passed": False, "command": command,
                    "skipped_reason": str(exc)}
        return {
            "ran": True,
            "passed": proc.returncode == 0,
            "command": command,
            "exit_code": proc.returncode,
            "output_tail": _combined_output_tail(proc.stdout, proc.stderr),
        }

    def _gather_runtime_parity(self) -> Optional["RuntimeParityResult"]:
        """Run the deliverable's runtime entry point (TASK-AB-COACHRUNPARITY01, arm b).

        Returns ``None`` when no smoke command was threaded (older callers /
        feature with no smoke gate). Returns a ``RuntimeParityResult`` with
        ``ran=False`` (and a ``skipped_reason``) when the check is intentionally
        skipped (parallel wave) or the runner itself errors — an ABSENT signal
        that never blocks and never counts as a pass
        (``absence-of-failure-is-not-success.md``). Returns ``ran=True`` with
        ``passed`` reflecting a clean (exit 0) standalone run otherwise.

        Guard: runs only on a single-task wave (``wave_size == 1``). On a
        multi-task wave the deliverable may not run standalone until peers
        finish, so a per-task smoke run would false-fail; those waves rely on
        the feature-level post-wave smoke gate instead.
        """
        if not self.smoke_command:
            return None

        command = self.smoke_command
        if self.wave_size > 1:
            return RuntimeParityResult(
                ran=False,
                passed=False,
                command=command,
                skipped_reason="parallel_wave",
            )

        try:
            # Built from nothing (13 October 2026), with the main checkout's
            # ``launch:`` block as the smoke gate reads it, and the bootstrap
            # venv first on PATH so a bare ``python`` / ``pytest`` in the smoke
            # command resolves to the right interpreter (mirrors
            # smoke_gates.run_smoke_gate's venv handling).
            env = _checker_env(self,
                path_first=self._venv_bin_first(), main_checkout=True
            )
            proc = process_group.run_project_command(
                command,
                shell=True,
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                timeout=self.test_timeout,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            timeout_stderr = (
                exc.stderr.decode() if isinstance(exc.stderr, bytes)
                else exc.stderr
            ) or ""
            timeout_stdout = (
                exc.stdout.decode() if isinstance(exc.stdout, bytes)
                else exc.stdout
            ) or ""
            stderr_tail = "\n".join(
                timeout_stderr.rstrip().splitlines()[-40:]
            )
            logger.warning(
                "Runtime-parity check timed out after %ss: %s",
                self.test_timeout, command,
            )
            # NOTE: ran=True on timeout is operator-pinned
            # (TASK-AB-COACHRUNPARITY01: a smoke entry point that starts and
            # hangs is a real deliverable defect). output_tail is additive
            # evidence only — verdict/timeout semantics unchanged.
            return RuntimeParityResult(
                ran=True,
                passed=False,
                command=command,
                exit_code=None,
                expected_exit=self.smoke_expected_exit,
                timed_out=True,
                stderr_tail=stderr_tail,
                output_tail=_combined_output_tail(timeout_stdout, timeout_stderr),
            )
        except Exception as exc:  # noqa: BLE001 — runner errors are ABSENT, not fail
            logger.warning(
                "Runtime-parity check runner error for %s: %s", command, exc,
            )
            return RuntimeParityResult(
                ran=False,
                passed=False,
                command=command,
                skipped_reason=f"runner_error: {exc}",
            )

        stderr_tail = "\n".join(
            (proc.stderr or "").rstrip().splitlines()[-40:]
        )
        passed = proc.returncode == self.smoke_expected_exit
        if passed:
            logger.info("Runtime-parity check passed: %s", command)
        else:
            logger.warning(
                "Runtime-parity check FAILED (exit=%d, expected=%d): %s\n"
                "stderr (tail):\n%s",
                proc.returncode, self.smoke_expected_exit, command,
                stderr_tail or "(empty)",
            )
        return RuntimeParityResult(
            ran=True,
            passed=passed,
            command=command,
            exit_code=proc.returncode,
            expected_exit=self.smoke_expected_exit,
            timed_out=False,
            stderr_tail=stderr_tail,
            # 2026-07-04 code review: pytest FAILED summaries live on stdout;
            # carry the combined tail so the parity guard can name the failing
            # tests (stderr_tail semantics untouched — additive only).
            output_tail=_combined_output_tail(proc.stdout, proc.stderr),
        )

    # ------------------------------------------------------------------
    # L4 behavioural-oracle producer (TASK-QAV-006)
    # ------------------------------------------------------------------

    def _produce_behavioural_oracle(
        self,
        task: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run the declared behavioural check and return its result.

        The task's ``behavioural_oracle.command``, when declared, is run
        through the shell in the worktree root. The exit code is the verdict;
        a timeout counts as ran-and-failed; a command that could not start,
        or no check at all, returns ``None``. (A file named
        ``tests/acceptance/*_roundtrip.py`` used to be run with pytest ahead
        of the declaration; that guess is gone, 31 October 2026.)
        """
        command = self._extract_command(task)
        if not command:
            return None
        logger.info(
            "gather_evidence: executing behavioural_oracle.command: %s",
            command,
        )
        return self._run_shell_command(command, task)

    @staticmethod
    def _oracle_declaration(
        task: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Normalise the ``behavioural_oracle`` declaration to a plain dict.

        Three accepted shapes, all equivalent:

        * ``behavioural_oracle: "npm test"``            (string shortcut)
        * ``behavioural_oracle: {command: "npm test"}`` (raw mapping)
        * a :class:`~guardkit.orchestrator.feature_loader.BehaviouralOracle`
          model instance (TS-lane D.1a — the schema-validated shape that the
          feature path threads down)

        Returns ``None`` when nothing is declared, which is the absence path
        and must stay byte-identical to the pre-D.1a behaviour.
        """
        if not task:
            return None
        bo = task.get("behavioural_oracle")
        if bo is None:
            return None
        if isinstance(bo, str):
            return {"command": bo} if bo else None
        if isinstance(bo, dict):
            return dict(bo)
        # Pydantic model (BehaviouralOracle) or any object exposing
        # ``.command``. Duck-typed on purpose: coach_validator must not
        # import feature_loader (feature_loader already imports downwards).
        allowed = ("command", "expected_exit", "timeout")
        model_dump = getattr(bo, "model_dump", None)
        if callable(model_dump):
            raw = model_dump(exclude_none=True)
            declaration = {key: raw[key] for key in allowed if key in raw}
        else:
            declaration = {
                key: getattr(bo, key)
                for key in allowed
                if getattr(bo, key, None) is not None
            }
        command = declaration.get("command")
        if not isinstance(command, str) or not command:
            return None
        return declaration

    def _extract_command(
        self, task: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Extract the behavioural_oracle.command from task YAML.

        Supports ``behavioural_oracle: {command: ...}``,
        ``behavioural_oracle: "..."`` (string shortcut) and a
        ``BehaviouralOracle`` model instance (TS-lane D.1a).

        Args:
            task: The task YAML dict.

        Returns:
            The command string, or ``None`` if not declared.
        """
        declaration = self._oracle_declaration(task)
        if declaration is None:
            return None
        command = declaration.get("command")
        return command if isinstance(command, str) and command else None

    def _run_shell_command(
        self,
        command: str,
        task: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Execute a shell command as the behavioural oracle.

        Runs via ``subprocess.run(shell=True)`` with ``cwd`` set to the
        worktree root, in the project-command environment built from nothing
        (``project_command_env``), never the factory's own.

        Args:
            command: The shell command string to execute.
            task: The task YAML dict (used for provenance naming).

        Returns:
            A dict with the oracle result shape, or ``None`` on failure.
        """
        # TS-lane D.1a: a schema-validated declaration may pin its own
        # bounded timeout and its own success exit code. Absent both, the
        # historical behaviour is unchanged: GUARDKIT_ORACLE_TIMEOUT (300s)
        # and "passes iff exit 0".
        declaration = self._oracle_declaration(task) or {}
        declared_timeout = declaration.get("timeout")
        if isinstance(declared_timeout, (int, float)) and declared_timeout > 0:
            timeout_seconds = float(declared_timeout)
        else:
            timeout_seconds = float(
                os.environ.get("GUARDKIT_ORACLE_TIMEOUT", "300")
            )
        declared_exit = declaration.get("expected_exit")
        if isinstance(declared_exit, int) and not isinstance(declared_exit, bool):
            expected_exit = declared_exit
        else:
            expected_exit = 0
        provenance = f"yaml_command:{command}"

        start_time = time.time()
        oracle_evidence: Dict[str, Any] = {}  # repair 7
        try:
            env = _checker_env(self)
            proc = self._run_recorded(
                command,
                evidence=(EVIDENCE_ORACLE, self.worktree_path, None),
                record_into=oracle_evidence,
                shell=True,
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.time() - start_time
            stdout = (
                exc.stdout.decode() if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            ) or ""
            stderr = (
                exc.stderr.decode() if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            ) or ""
            output_tail = _combined_output_tail(stdout, stderr)
            logger.warning(
                "gather_evidence: behavioural-oracle command timed out after "
                "%.1fs (command: %s). Treating as ran-and-failed.",
                duration, command,
            )
            return {
                "status": "ran",
                "passed": False,
                "command": command,
                "exit_code": None,
                "duration": duration,
                "timed_out": True,
                "output_tail": output_tail,
                "provenance": provenance,
                "run_evidence": oracle_evidence,
            }
        except Exception as exc:
            logger.warning(
                "gather_evidence: behavioural-oracle command failed to start "
                "(command: %s): %s. Treating as absent.",
                command, exc,
            )
            return None

        duration = time.time() - start_time
        # LAW (design §B.4): the exit code IS the verdict. Stdout parsing is
        # advisory only and may never decide green.
        passed = proc.returncode == expected_exit
        output_tail = _combined_output_tail(proc.stdout, proc.stderr)

        if passed:
            logger.info(
                "gather_evidence: behavioural-oracle command passed "
                "(command: %s, exit_code=%d, duration=%.1fs).",
                command, proc.returncode, duration,
            )
        else:
            logger.warning(
                "gather_evidence: behavioural-oracle command FAILED "
                "(command: %s, exit_code=%d, expected_exit=%d, "
                "duration=%.1fs).",
                command, proc.returncode, expected_exit, duration,
            )

        return {
            "status": "ran",
            "passed": passed,
            "command": command,
            "exit_code": proc.returncode,
            "duration": duration,
            "timed_out": False,
            "output_tail": output_tail,
            "provenance": provenance,
            "run_evidence": oracle_evidence,
        }

    def _execute_oracle(
        self,
        cmd: list,
        oracle_rel: str,
        timeout_seconds: float,
        path_first: Sequence[str],
        oracle_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Execute an oracle subprocess and return its result.

        Shared logic for running the subprocess and handling all outcome
        branches (pass, fail, timeout, failed-to-start).

        Args:
            cmd: The command to execute.
            oracle_rel: Relative path of the oracle (for logging/provenance).
            timeout_seconds: Maximum execution time.
            path_first: Folders put in front of PATH (the bootstrap venv's
                ``bin``); the environment itself is built from nothing.
            oracle_type: Human-readable type label ("python" or "command").

        Returns:
            A dict with the oracle result shape, or ``None`` on failure.
        """
        start_time = time.time()
        oracle_evidence: Dict[str, Any] = {}  # repair 7
        try:
            env = _checker_env(self, path_first=path_first)
            proc = self._run_recorded(
                cmd,
                evidence=(EVIDENCE_ORACLE, self.worktree_path, None),
                record_into=oracle_evidence,
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.time() - start_time
            stdout = (
                exc.stdout.decode() if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            ) or ""
            stderr = (
                exc.stderr.decode() if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            ) or ""
            output_tail = _combined_output_tail(stdout, stderr)
            logger.warning(
                "gather_evidence: behavioural-oracle timed out after %.1fs "
                "(%s: %s). Treating as ran-and-failed.",
                duration, oracle_type, oracle_rel,
            )
            return {
                "status": "ran",
                "passed": False,
                "oracle_path" if oracle_type == "python" else "command": oracle_rel,
                "exit_code": None,
                "duration": duration,
                "timed_out": True,
                "output_tail": output_tail,
                "provenance": "independent" if oracle_type == "python" else f"yaml_command:{oracle_rel}",
                "run_evidence": oracle_evidence,
            }
        except Exception as exc:
            logger.warning(
                "gather_evidence: behavioural-oracle failed to start "
                "(%s: %s): %s. Treating as absent.",
                oracle_type, oracle_rel, exc,
            )
            return None

        duration = time.time() - start_time
        passed = proc.returncode == 0
        output_tail = _combined_output_tail(proc.stdout, proc.stderr)

        if passed:
            logger.info(
                "gather_evidence: behavioural-oracle passed (%s: %s, "
                "duration=%.1fs).",
                oracle_type, oracle_rel, duration,
            )
        else:
            logger.warning(
                "gather_evidence: behavioural-oracle FAILED (%s: %s, "
                "exit_code=%d, duration=%.1fs).",
                oracle_type, oracle_rel, proc.returncode, duration,
            )

        return {
            "status": "ran",
            "passed": passed,
            "oracle_path" if oracle_type == "python" else "command": oracle_rel,
            "exit_code": proc.returncode,
            "duration": duration,
            "timed_out": False,
            "output_tail": output_tail,
            "provenance": "independent" if oracle_type == "python" else f"yaml_command:{oracle_rel}",
            "run_evidence": oracle_evidence,
        }

    def read_quality_gate_results(self, task_id: str) -> Dict[str, Any]:
        """
        Read quality gate results from task-work execution.

        Looks for results in the standard location:
        `.guardkit/autobuild/{task_id}/task_work_results.json`

        Parameters
        ----------
        task_id : str
            Task identifier

        Returns
        -------
        Dict[str, Any]
            Task-work results, or dict with "error" key if not found
        """
        results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
        logger.debug(f"Looking for task_work_results at: {results_path}")

        if not results_path.exists():
            logger.warning(f"task_work_results.json not found at {results_path}")
            logger.debug(f"Worktree path: {self.worktree_path}")
            logger.debug(f"Task ID: {task_id}")
            return {"error": f"Task-work results not found at {results_path}"}

        try:
            with open(results_path) as f:
                results = json.load(f)
            logger.debug(f"Successfully loaded task_work_results from {results_path}")
            return results
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse task-work results: {e}")
            return {"error": f"Failed to parse task-work results: {e}"}
        except Exception as e:
            logger.error(f"Failed to read task-work results: {e}")
            return {"error": f"Failed to read task-work results: {e}"}

    def run_evidence_repo_tests(self) -> List[EvidenceTestResult]:
        """Run independent tests in every declared sibling repo (AC-002).

        Trust-but-verify for sibling-repo deliverables: each declared repo's
        ``test_command`` runs in that repo's root under that repo's OWN
        interpreter (explicit ``interpreter:`` field, else the sibling's
        ``.venv``, else verbatim via shell — resolved per-repo by
        ``evidence_repos._resolve_repo_interpreter``). The guardkit worktree
        venv (``self._venv_python``) is deliberately NOT threaded here: it
        cannot import the sibling's dependency set, so pinning sibling tests
        to it produced a guaranteed-broken mis-environmented oracle
        (TASK-FIX-SIBTESTENV01, the FEAT-10AC run-2 false-red). Returns one
        :class:`EvidenceTestResult` per declared repo (empty list when no
        sibling repos are declared). The orchestrator attaches these to the
        evidence bundle and blocks the turn on a failed/unrunnable suite via
        :func:`evidence_repos.evidence_repo_tests_blocking_reason`.
        """
        if not self._evidence_repos:
            return []
        results = evidence_repos_lib.run_all_repo_tests(
            self._evidence_repos,
            timeout=self.test_timeout,
        )
        for r in results:
            logger.info(
                "Evidence-repo tests for %s: ran=%s passed=%s rc=%s",
                r.repo_name,
                r.ran,
                r.passed,
                r.returncode,
            )
        return results

    @staticmethod
    def _extract_content_text(content) -> str:
        """Extract text from ToolResultBlock.content (str | list[dict] | None)."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(item.get("text", str(item)))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(content)

    # TASK-FIX-COACHTRES01 (heuristic precision): the pytest result summary
    # line, e.g. ``==== 15 passed in 2.75s ====`` /
    # ``==== 1 failed, 14 passed in 0.3s ====`` / ``==== 2 errors in 1.0s ====``.
    # Wrapped in ``=`` runs and ending in ``in <float>s``; the body carries the
    # real per-outcome counts.
    _PYTEST_SUMMARY_RE = re.compile(
        r"^=+\s+(?P<body>.*?\b(?:passed|failed|error|errors|skipped|xfailed|"
        r"xpassed|no tests ran)\b.*?)\s+in\s+[\d.]+\s*s\b.*?=*\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    @classmethod
    def _verdict_from_pytest_summary(cls, output_text: str) -> Optional[bool]:
        """Derive pass/fail from the pytest summary line, not substring scan.

        TASK-FIX-COACHTRES01. The capture fix surfaces the *real* pytest output
        to the SDK-path determination — but the legacy heuristic scanned the
        WHOLE output for the substrings ``"error"`` / ``"failed"`` /
        ``"failure"``, which false-positives on a *passing* run whose verbose
        test names or ``--cov`` file paths contain those words (e.g. a passing
        ``test_..._displays_error`` or a covered ``*_error_messages.py``). That
        is the FEAT-HARV TASK-HARV-006 false-block: ``15 passed in 2.75s`` read
        as a failure because two unrelated ``"error"`` substrings appeared.

        The pytest *summary line* carries only the real counts, so parse that.

        Returns
        -------
        Optional[bool]
            ``True``  — a passing summary (>=1 passed, zero failed/errored).
            ``False`` — a failing summary (>=1 failed or errored).
            ``None``  — no pytest summary line found (e.g. narration-only or a
                        truncated capture), so the caller falls back to the
                        legacy substring heuristic / absent handling.
        """
        if not output_text:
            return None
        matches = list(cls._PYTEST_SUMMARY_RE.finditer(output_text))
        if not matches:
            return None
        body = matches[-1].group("body").lower()
        # Any non-zero failed/errored count is a fail, regardless of passes.
        if re.search(r"\b[1-9]\d*\s+(?:failed|error|errors)\b", body):
            return False
        if re.search(r"\b[1-9]\d*\s+passed\b", body):
            return True
        # Only skipped / xfailed / "no tests ran" — not a clear pass; defer.
        return None

    async def _run_tests_via_sdk(self, test_cmd: str) -> IndependentTestResult:
        """Run tests via the harness substrate seam (TASK-HMIG-006.3).

        Dispatches through :func:`select_harness` so ``GUARDKIT_HARNESS``
        routes Coach's independent verification through the SDK or
        LangGraph substrate consistently with the Player path migrated
        in TASK-HMIG-006/006.2. Coach-specific orchestrator concerns
        (``allowed_tools=["Bash"]``, ``max_turns=1``,
        ``permission_mode="bypassPermissions"``, ``self.test_timeout``)
        remain orchestrator-side per AC-002.

        The method name retains the historical ``_via_sdk`` suffix so
        callers (``run_independent_tests`` at line ~2867) need no
        change; the dispatch is now harness-agnostic.

        Parameters
        ----------
        test_cmd : str
            Shell command to run tests

        Returns
        -------
        IndependentTestResult
            Result of test execution via the substrate seam.
        """
        import asyncio
        import time

        # ``select_harness``, harness event types, ``AgentInvocationError``,
        # and ``check_assistant_message_error`` are imported at module top
        # (TASK-HMIG-006.3) so ``coach_validator.select_harness`` is a
        # stable patch target. ``asyncio`` / ``time``
        # remain method-local to preserve the historic lazy-import shape
        # for the rest of the method body.

        def _sdk_env_overrides(prepend: str, venv_bin: Optional[str]) -> Dict[str, str]:
            """PYTHONPATH/PATH for this one harness call (Step D, TASK-FIX-COACHPYENV).

            The worktree root is prepended to ``PYTHONPATH`` and, when a
            bootstrap venv is resolved, its ``bin`` to ``PATH``, so a bare
            ``pytest``/``python`` the tests shell out to resolves inside the
            bootstrap environment. These used to be swapped into
            ``os.environ`` around ``harness.invoke()``; parallel wave tasks run
            in threads of one process, so another task's swap or restore could
            leak into this run (or this worktree into theirs). They are now
            handed to the harness explicitly (``env=``), which the SDK merges
            over the inherited environment for its own subprocess only.
            """
            current = os.environ.get("PYTHONPATH", "")
            overrides = {
                "PYTHONPATH": f"{prepend}:{current}" if current else prepend
            }
            if venv_bin:
                path = os.environ.get("PATH", "")
                overrides["PATH"] = (
                    f"{venv_bin}{os.pathsep}{path}" if path else venv_bin
                )
            return overrides

        start_time = time.time()
        # TASK-FIX-COACHPYENV: pin the interpreter in the command the Bash tool
        # runs so it cannot resolve a stray PATH ``pytest`` (the run-9 Python
        # 3.14 framework-pytest mismatch). No-op when no venv is resolved.
        sdk_test_cmd = self._pin_pytest_command(test_cmd)
        if sdk_test_cmd != test_cmd:
            logger.info(
                "Coach SDK test command pinned to bootstrap interpreter: %s",
                sdk_test_cmd,
            )
        # 2026-07-04 code review: record the pinned interpreter as forensic
        # evidence on the SDK-path results too (the subprocess/isolated runners
        # already do — TASK-AB-RESUMEVENV01 AC-003). Only when the pin actually
        # fired: an unpinned SDK run resolves ``pytest`` via the Bash tool's
        # PATH, so the probe interpreter would not match the run — honest
        # ``None`` there.
        sdk_resolved_interpreter = (
            self._resolved_interpreter_for(test_cmd)
            if sdk_test_cmd != test_cmd
            else None
        )
        prompt = (
            f"Run the following test command and report the output:\n\n"
            f"```bash\n{sdk_test_cmd}\n```\n\nProvide the full test output."
        )

        # TASK-HMIG-006.5: Restore sdk_debug preservation for the Coach
        # test path. Pre-migration (TASK-DIAG-F4A2), the SDK call site
        # invoked ``_sdk_preserve_prompt`` / ``_sdk_preserve_event``
        # under ``GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1`` so incident
        # analysis of coach test-run failures had a quoted artefact
        # trail under ``sdk_debug/turn_<n>/coach/test_run/``. The
        # HMIG-006.3 migration dropped those calls because the harness
        # substrate seam owns the message stream and no harness-level
        # hook existed. The preservation is re-introduced here against
        # the synthesised options-shaped snapshot below so the
        # diagnostic surface mirrors the pre-migration shape; the
        # harness dispatch boundary itself (AC-001/AC-002 of HMIG-006.3)
        # is untouched. Zero overhead when the env var is unset
        # (``preserve_prompt`` short-circuits and ``preserve_event``
        # becomes a no-op against ``debug_dir=None``).
        from guardkit.orchestrator.sdk_debug import (
            preserve_prompt as _sdk_preserve_prompt,
            preserve_event as _sdk_preserve_event,
        )

        try:
            # Use GUARDKIT_COACH_TEST_MODEL env var if set, otherwise CLI default
            model = self._get_coach_test_model()
            worktree_str = str(self.worktree_path)
            logger.debug(f"Coach harness PYTHONPATH prepend: {worktree_str}")

            # Synthesise the diagnostic options snapshot the
            # pre-migration ``ClaudeAgentOptions`` would have produced.
            # The post-migration harness owns its own option assembly;
            # this record captures Coach's intent (what the substrate
            # was asked to run with) rather than the substrate's
            # realisation. ``GUARDKIT_HARNESS`` is included so the
            # post-mortem can distinguish SDK vs. LangGraph runs.
            _sdk_options_snapshot = {
                "cwd": str(self.worktree_path),
                "allowed_tools": ["Bash"],
                "permission_mode": "bypassPermissions",
                "max_turns": 1,
                "model": model,
                "harness": os.environ.get("GUARDKIT_HARNESS", DEFAULT_HARNESS),
                "pythonpath_prepend": worktree_str,
                "sdk_timeout_seconds": self.test_timeout,
            }
            _sdk_debug_dir = _sdk_preserve_prompt(
                workspace_root=self.worktree_path,
                task_id=self.task_id or "unknown",
                turn=self._turn,
                role="coach_test",
                prompt=prompt,
                options=_sdk_options_snapshot,
            )

            collected_text: List[str] = []
            bash_output: Optional[str] = None
            bash_is_error: Optional[bool] = None
            api_error: Optional[str] = None

            venv_bin = (
                str(self._venv_python.parent)
                if self._venv_python is not None
                else None
            )
            harness = select_harness(
                sdk_timeout_seconds=self.test_timeout,
                allowed_tools=["Bash"],
                permission_mode="bypassPermissions",
                max_turns=1,
                model=model,
                cwd=self.worktree_path,
                env=_sdk_env_overrides(worktree_str, venv_bin),
                # 19 October 2026: the checker's test run gets the checker's
                # own shell folders, never the builder's (LangGraph only; the
                # selector compares the role only with "player" otherwise).
                harness_role="coach",
            )

            async with asyncio.timeout(self.test_timeout):
                # TASK-FIX-LGACLOSE: finalise the harness async generator on
                # every exit (incl. timeout/cancel) via aclosing() so no
                # orphaned async_generator_athrow survives interpreter shutdown.
                # HEAD recorded before and after this shell-capable agent
                # (build 0D7C, 12 October 2026); evidence only.
                from guardkit.orchestrator.head_identity import (
                    observe_invocation,
                )

                async with aclosing(
                    observe_invocation(
                        harness.invoke(
                            prompt=prompt,
                            role="coach_test",
                            tools=["Bash"],
                            cwd=self.worktree_path,
                            timeout_seconds=self.test_timeout,
                        ),
                        self.worktree_path,
                        role="coach test runner",
                        task_id=self.task_id,
                        turn=self._turn,
                    )
                ) as _harness_stream:
                    async for event in _harness_stream:
                        # TASK-HMIG-006.5: record every harness event
                        # the loop consumes. ``preserve_event`` is a
                        # no-op when ``_sdk_debug_dir`` is None
                        # (env var unset), so this is zero-cost in
                        # production.
                        _sdk_preserve_event(_sdk_debug_dir, event)
                        if isinstance(event, AssistantMessageEvent):
                            # API-error short-circuit mirrors the Player
                            # dispatch in agent_invoker._invoke_with_role.
                            # Only the SDK harness sets ``event.raw``;
                            # other substrates have raw=None and this
                            # check is a no-op there.
                            if event.raw is not None:
                                err = check_assistant_message_error(event.raw)
                                if err:
                                    api_error = err
                                    break
                            collected_text.append(event.text)
                        elif isinstance(event, ToolResultEvent):
                            # NOTE (TASK-HMIG-006.3, Architectural review
                            # Concern 4): the current SDK harness does NOT
                            # yield ToolResultEvent — sdk_harness.py only
                            # handles AssistantMessage / ResultMessage /
                            # ToolUseEvent. On the SDK path bash_is_error
                            # therefore stays None and the heuristic
                            # branch below is the effective pass/fail
                            # determination. This branch is live for any
                            # future harness that yields ToolResultEvent
                            # (e.g. a variant that walks UserMessage
                            # content) and preserves the pre-migration
                            # tri-state contract:
                            #   is_error=True  -> bash_is_error=True (tool errored)
                            #   is_error=False -> bash_is_error=None (heuristic)
                            # The False->None mapping is intentional:
                            # is_error=False means "tool ran cleanly" not
                            # "tests passed", so we let the heuristic
                            # branch decide from the output text.
                            content = event.content
                            if isinstance(content, str):
                                bash_output = content
                            else:
                                bash_output = self._extract_content_text(content)
                            bash_is_error = True if event.is_error else None
                        elif isinstance(event, ResultMessageEvent):
                            break

            duration = time.time() - start_time

            if api_error is not None:
                logger.error(f"SDK API error during coach test execution: {api_error}")
                # TASK-FIX-COACHTESTTO: transport-layer failure — the oracle
                # never produced a verdict. ABSENT, not a fail.
                return IndependentTestResult.absent(
                    test_command=test_cmd,
                    test_output_summary=f"SDK API error: {api_error}",
                    duration_seconds=duration,
                    raw_output=f"SDK API error: {api_error}",
                )

            # Determine pass/fail from bash_is_error and output. Branches
            # below are unchanged from pre-migration: output assembly is
            # substrate-agnostic; only the source of bash_is_error /
            # bash_output / collected_text changed.
            if bash_is_error is True:
                output_text = bash_output or "\n".join(collected_text) or "No output"
                summary = self._summarize_test_output(output_text)
                logger.debug(
                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
                )
                # TASK-ABFIX-012: a missing host tool ("command not found") makes
                # this an ABSENT signal (the oracle could not run), not a Player
                # test failure. No subprocess return code is available on the SDK
                # path, so match the explicit shell strings.
                substrate_absent = self._is_host_substrate_gap(None, output_text)
                if substrate_absent:
                    logger.warning(
                        "[TASK-ABFIX-012] SDK independent test oracle hit a "
                        "host-substrate gap (missing host tool) — absent signal, "
                        "not a test failure. cmd=%s",
                        test_cmd,
                    )
                return IndependentTestResult.from_run(
                    tests_passed=False,
                    test_command=test_cmd,
                    test_output_summary=summary,
                    duration_seconds=duration,
                    output=output_text,
                    signal_absent=substrate_absent,
                    resolved_interpreter=sdk_resolved_interpreter,
                )
            elif bash_is_error is False:
                # NOTE (TASK-HMIG-006.3 code-review nit): this branch is
                # unreachable in the current implementation because the
                # ToolResultEvent handler above maps ``is_error=False``
                # to ``bash_is_error=None`` (heuristic path). Retained
                # unchanged from pre-migration per the implementation
                # plan; it activates only if a future harness yields
                # tri-state ``is_error`` semantics (e.g. by emitting
                # ``bash_is_error = False`` directly here from a custom
                # branch). Removing it would silently break that future
                # extension, so the branch stays live but documented.
                output_text = bash_output or "\n".join(collected_text) or "No output"
                summary = self._summarize_test_output(output_text)
                logger.debug(
                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
                )
                return IndependentTestResult.from_run(
                    tests_passed=True,
                    test_command=test_cmd,
                    test_output_summary=summary,
                    duration_seconds=duration,
                    output=output_text,
                    resolved_interpreter=sdk_resolved_interpreter,
                )
            else:
                # GAP-FIX #7: is_error is None — parse output text
                output_text = bash_output or "\n".join(collected_text) or "No output"
                summary = self._summarize_test_output(output_text)
                logger.debug(
                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
                )
                # TASK-ABFIX-012: a host-substrate gap ("command not found") is an
                # ABSENT signal — short-circuit before the pass/fail heuristic so a
                # missing host tool is never read as a Player test failure or pass.
                if self._is_host_substrate_gap(None, output_text):
                    logger.warning(
                        "[TASK-ABFIX-012] SDK independent test oracle (heuristic "
                        "branch) hit a host-substrate gap — absent signal, not a "
                        "test failure. cmd=%s",
                        test_cmd,
                    )
                    return IndependentTestResult.absent(
                        test_command=test_cmd,
                        test_output_summary=summary,
                        duration_seconds=duration,
                        raw_output=output_text,
                    )
                # TASK-FIX-COACHTRES01: prefer the pytest summary line (real
                # counts) over the substring scan, which false-positives on a
                # passing run whose verbose test names / --cov file paths
                # contain "error"/"failed" (the FEAT-HARV TASK-HARV-006
                # false-block: "15 passed" mis-read as a failure because a
                # passing test_..._displays_error and a covered
                # *_error_messages.py path matched). Only fall back to the
                # legacy substring heuristic when no summary line is present.
                summary_verdict = self._verdict_from_pytest_summary(output_text)
                if summary_verdict is not None:
                    return IndependentTestResult.from_run(
                        tests_passed=summary_verdict,
                        test_command=test_cmd,
                        test_output_summary=summary,
                        duration_seconds=duration,
                        output=output_text,
                        resolved_interpreter=sdk_resolved_interpreter,
                    )
                # Heuristic fallback: check for failure indicators in output
                lower = output_text.lower()
                has_failure = any(
                    indicator in lower
                    for indicator in ["failed", "error", "errors", "failure"]
                )
                has_success = any(
                    indicator in lower
                    for indicator in ["passed", "ok", "success"]
                )
                tests_passed = has_success and not has_failure
                return IndependentTestResult.from_run(
                    tests_passed=tests_passed,
                    test_command=test_cmd,
                    test_output_summary=summary,
                    duration_seconds=duration,
                    output=output_text,
                    resolved_interpreter=sdk_resolved_interpreter,
                )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"SDK coach test execution timed out after {self.test_timeout}s")
            # TASK-FIX-COACHTESTTO: the oracle did not complete — ABSENT,
            # not a real pass/fail verdict.
            return IndependentTestResult.absent(
                test_command=test_cmd,
                test_output_summary=f"SDK test execution timed out after {self.test_timeout}s",
                duration_seconds=duration,
                raw_output=f"Timeout after {self.test_timeout}s",
            )
        except AgentInvocationError as e:
            # TASK-HMIG-006.3 D-4: the harness normalises
            # CLINotFoundError / ProcessError / CLIJSONDecodeError /
            # MessageParseError into a single AgentInvocationError
            # (sdk_harness.py). The diagnostic info (exit_code, stderr,
            # error_class) is preserved inside the exception message
            # string. ``run_independent_tests``'s generic catch reads
            # type(e).__name__ for log formatting and falls back to
            # subprocess, so behavioural parity is preserved; the only
            # observable change is the logged error_class value.
            logger.error(
                f"SDK coach test execution failed "
                f"(error_class=AgentInvocationError): {e}"
            )
            raise
        except Exception as e:
            # Catch-all retained for non-harness failures (e.g.
            # context-manager errors restoring PYTHONPATH). Preserves
            # the pre-migration log shape.
            logger.error(
                f"SDK coach test execution failed "
                f"(error_class={type(e).__name__}): {e}"
            )
            raise

    def _is_custom_api_base(self) -> bool:
        """Return True when ANTHROPIC_BASE_URL points to a non-Anthropic endpoint (e.g. vLLM)."""
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        return bool(base_url) and "api.anthropic.com" not in base_url

    def _is_langgraph_harness(self) -> bool:
        """Return True when ``GUARDKIT_HARNESS`` selects the LangGraph substrate.

        TASK-FIX-COACHTESTTO. Under the LangGraph harness the SDK-path
        independent-test run (``_run_tests_via_sdk``) is dispatched as a
        one-turn LLM agent invocation: the (typically local) coach-test model
        is asked to call the ``Bash`` tool, run pytest, and report. That whole
        turn is bounded by ``self.test_timeout`` (300s). With a slow local
        model the turn never completes within budget and the trust-but-verify
        leg times out on every task (run-19, FEAT-AOF). The deterministic
        subprocess path runs the *same* pinned interpreter in the *same*
        worktree in seconds with no model in the loop, so under LangGraph we
        force subprocess.

        This is the LangGraph-substrate complement to ``_is_custom_api_base``:
        the latter disables the SDK path when ``ANTHROPIC_BASE_URL`` points at
        a non-Anthropic endpoint, but the LangGraph harness configures its
        model endpoint through the LangGraph/OpenAI-compatible channel rather
        than ``ANTHROPIC_BASE_URL``, so ``_is_custom_api_base`` does not catch
        it. See ``docs/state/TASK-FIX-COACHTESTTO/diagnosis.md``.
        """
        return (
            os.environ.get("GUARDKIT_HARNESS", DEFAULT_HARNESS).strip().lower()
            == "langgraph"
        )

    def _pytest_interpreter(self) -> str:
        """Return the interpreter Coach should run pytest under.

        TASK-FIX-COACHPYENV: prefer the resolved bootstrap venv interpreter so
        independent tests run in the same environment the Player's packages were
        installed into. Falls back to ``sys.executable`` (the orchestrator
        interpreter) for non-Python projects / no-venv recovery — never bare
        ``pytest`` from PATH, which is what produced the run-9 Python-3.14
        framework-pytest mismatch.
        """
        return str(self._venv_python) if self._venv_python is not None else sys.executable

    def _resolved_interpreter_for(self, test_cmd: str) -> Optional[str]:
        """The interpreter an interpreter-pinned run of ``test_cmd`` uses.

        TASK-AB-RESUMEVENV01 (AC-003): recorded on
        :class:`IndependentTestResult.resolved_interpreter` as forensic
        evidence. Only pytest-shaped commands are pinned to
        ``_pytest_interpreter()`` by the subprocess/isolated runners; a
        non-pytest command runs via ``shell=True`` with no interpreter pin,
        so ``None`` (unknown) is the honest value there.
        """
        if test_cmd.startswith("pytest"):
            return self._pytest_interpreter()
        return None

    def _pin_pytest_command(self, test_cmd: str) -> str:
        """Rewrite a bare ``pytest …`` command to pin the bootstrap interpreter.

        TASK-FIX-COACHPYENV: the SDK test path hands ``test_cmd`` to a Bash tool,
        which resolves ``pytest`` via PATH. Rewriting to
        ``<venv_python> -m pytest …`` makes the Bash subprocess invoke the exact
        interpreter regardless of PATH ordering. No-op when no venv is resolved
        or the command is not a bare ``pytest`` invocation.
        """
        if self._venv_python is None:
            # No pinned venv: the Bash tool resolves ``pytest`` via PATH, so the
            # probe interpreter (sys.executable) would not match the run
            # interpreter — skip both the pin and the --timeout injection here.
            return test_cmd
        # TASK-ABFIX-011: append a gated per-test --timeout to the pinned string.
        # Only the venv-pinned branches reach here, so the probe interpreter
        # (self._pytest_interpreter()) matches the interpreter that runs.
        timeout_suffix = ""
        timeout_argv = self._pytest_timeout_argv()
        if timeout_argv:
            timeout_suffix = " " + " ".join(timeout_argv)
        if test_cmd.startswith("pytest "):
            return f"{self._pytest_interpreter()} -m {test_cmd}{timeout_suffix}"
        if test_cmd == "pytest":
            return f"{self._pytest_interpreter()} -m pytest{timeout_suffix}"
        return test_cmd

    def _held_back_note(self) -> str:
        """Which settings a project command's environment held back, by name
        only (``project_command_env.minimal_environment_note``); empty when
        the environment cannot be built, which the failure already says."""
        try:
            return minimal_environment_note(_checker_declared_env(self))
        except OSError:
            return ""

    def _venv_bin_first(self) -> Tuple[str, ...]:
        """The bootstrap venv's ``bin`` to put first on PATH, when known."""
        if self._venv_python is None:
            return ()
        return (str(Path(self._venv_python).parent),)

    def _project_env(
        self,
        *,
        additions: Optional[Dict[str, str]] = None,
        path_first: Sequence[str] = (),
        fixtures: bool = False,
        main_checkout: bool = False,
    ) -> Dict[str, str]:
        """The environment one of the checker's project commands runs with.

        Built from nothing by ``project_command_env.project_command_environment``
        (design ``factory-project-commands-without-factory-credentials``,
        13 October 2026): the factory's credentials never reach the project's
        tests, oracle, smoke or criteria commands. The declaration is the
        task's pinned ``launch:`` block (or, with ``main_checkout``, the main
        checkout's block, for the commands the smoke gate also runs).

        The factory's own additions for one command:

        * ``fixtures`` — the URLs of the test services this validator started
          (:meth:`_start_infrastructure_containers`), for the test commands;
        * ``additions`` — anything else the caller is promised.

        Raises ``LaunchEnvironmentError`` (an ``OSError``) when the command
        cannot be given its environment; every caller treats that as "the
        command could not start".
        """
        return _checker_env(
            self,
            additions=additions,
            path_first=path_first,
            fixtures=fixtures,
            main_checkout=main_checkout,
        )

    def _launch_declaration(self, main_checkout: bool) -> Any:
        """The task's pinned ``launch:`` block, or the main checkout's."""
        if main_checkout:
            return load_launch_declaration(main_checkout_root(self.worktree_path))
        return load_launch_snapshot(getattr(self, "task_id", None), self.worktree_path)

    def _command_additions(
        self,
        additions: Optional[Dict[str, str]],
        fixtures: bool,
    ) -> Dict[str, str]:
        """The factory's own additions for one of the checker's commands."""
        adds: Dict[str, str] = {}
        if fixtures:
            adds.update(getattr(self, "_fixture_env", {}) or {})
        adds.update(additions or {})
        return adds

    # ------------------------------------------------------------------
    # TASK-ABFIX-011: gated per-test pytest-timeout injection
    # ------------------------------------------------------------------
    # A single hanging test otherwise consumes the whole Coach subprocess budget
    # and yields ``tests_run=0`` (no per-test attribution). Injecting
    # ``--timeout N --timeout-method signal`` marks the *specific* hung test
    # FAILED while the others still run (``signal`` lets the session continue;
    # ``thread`` would ``os._exit``-kill it). Injection is TRIPLE-gated so it can
    # never become the harness-wide false-fail an *unconditional* ``--timeout``
    # would be (returncode-4 ``unrecognized arguments`` on any project lacking the
    # plugin — the already-reverted FEAT-FMDR-003 regression, replayed
    # harness-wide). Since 31 October 2026 only the opt-in SDK test path
    # injects it (``_pin_pytest_command``); a declared command run by the
    # subprocess path is never rewritten.

    def _pytest_timeout_injection_enabled(self) -> bool:
        """Master gate for per-test ``--timeout`` injection (all three must hold).

        1. operator flag — ``GUARDKIT_COACH_PYTEST_TIMEOUT`` not in
           ``{0, false, off, no}`` (escape hatch; default enabled);
        2. Python stack — ``self._active_stack_profile is None`` (a non-Python
           profile means a non-pytest ``whole_suite_command``; never inject a
           Python-only arg — ``.claude/rules/stack-plugin-architecture.md``);
        3. plugin resolvable in the pinned interpreter (cached probe).
        """
        flag = os.environ.get("GUARDKIT_COACH_PYTEST_TIMEOUT", "").strip().lower()
        if flag in ("0", "false", "off", "no"):
            return False
        if self._active_stack_profile is not None:
            return False
        return self._pytest_timeout_available()

    def _pytest_timeout_available(self) -> bool:
        """Cached: is ``pytest-timeout`` importable in the pinned interpreter?"""
        if self._pytest_timeout_available_cache is None:
            self._pytest_timeout_available_cache = self._probe_pytest_timeout()
        return self._pytest_timeout_available_cache

    def _probe_pytest_timeout(self) -> bool:
        """Probe whether ``pytest_timeout`` is importable where Coach runs pytest.

        When the pinned interpreter is the orchestrator's own
        (``self._venv_python is None`` → ``sys.executable``) the check is
        in-process (``importlib.util.find_spec`` — no subprocess, so it does not
        perturb the many tests that patch ``subprocess.run``). When a distinct
        bootstrap venv is pinned, the plugin must be probed *in that interpreter*,
        so a tiny out-of-process ``find_spec`` is run. Any failure (non-zero exit,
        timeout, OSError) returns ``False`` — fail toward NO injection, never a
        spurious ``--timeout``.
        """
        import importlib.util

        interpreter = self._pytest_interpreter()
        if interpreter == sys.executable:
            return importlib.util.find_spec("pytest_timeout") is not None
        try:
            proc = process_group.run_project_command(
                [
                    interpreter,
                    "-c",
                    "import importlib.util, sys; "
                    "sys.exit(0 if importlib.util.find_spec('pytest_timeout') "
                    "else 1)",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                env=_checker_env(self),
            )
            return proc.returncode == 0
        except Exception as exc:  # subprocess error / timeout / OSError
            logger.debug(
                "pytest-timeout probe failed for %s (%s); not injecting --timeout",
                interpreter,
                exc,
            )
            return False

    def _per_test_timeout_seconds(self) -> int:
        """Per-test timeout (seconds). Env override, else the module default."""
        raw = os.environ.get("GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS")
        if raw:
            try:
                value = int(raw)
                if value > 0:
                    return value
                logger.warning(
                    "GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS=%r is not positive; "
                    "using default %ss",
                    raw,
                    _DEFAULT_COACH_PER_TEST_TIMEOUT_S,
                )
            except ValueError:
                logger.warning(
                    "GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS=%r is not an int; "
                    "using default %ss",
                    raw,
                    _DEFAULT_COACH_PER_TEST_TIMEOUT_S,
                )
        return _DEFAULT_COACH_PER_TEST_TIMEOUT_S

    def _pytest_timeout_method(self) -> str:
        """``--timeout-method``: ``signal`` (default) or ``thread``.

        ``signal`` raises inside the hung test and lets the session CONTINUE, so
        the other tests still run and report verdicts — the per-test attribution
        the AC requires. ``thread`` dumps tracebacks then ``os._exit``-kills the
        session (the others never report), so it is not the default. The alarm
        fires only once a test exceeds the deadline, so a healthy asyncio test
        (event loop on the main thread) is never spuriously interrupted (empirically
        validated, constraint 5). Operator override:
        ``GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD``.
        """
        method = (
            os.environ.get("GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD", "")
            .strip()
            .lower()
        )
        if method in ("signal", "thread"):
            return method
        return "signal"

    def _pytest_timeout_argv(self) -> List[str]:
        """argv fragment injecting a gated per-test ``--timeout``, or ``[]``.

        Shared by all three pytest construction sites (SDK pin, isolated/parallel
        subprocess, standard subprocess) so the gate logic cannot drift between
        them — the recurring "Nth-injection-site" lesson of the absence-of-failure
        rule family.
        """
        if not self._pytest_timeout_injection_enabled():
            return []
        return [
            "--timeout",
            str(self._per_test_timeout_seconds()),
            "--timeout-method",
            self._pytest_timeout_method(),
        ]

    # ---- what the check ran against (repair 7, 2026-10-12) ---------------
    #
    # Every command this validator runs for its independent check is
    # recorded by ``run_evidence``: the real execution root (the worktree),
    # its source just before and just after, the declared environment
    # inventory, and the raw container events of the interval. Recording
    # NEVER changes a verdict, and every capture error is written into the
    # record, never raised.

    _run_evidence_log: Optional[List[Dict[str, Any]]] = None
    _run_evidence_turn: Optional[int] = None

    def run_independent_tests(
        self,
        task_work_results: Optional[Dict[str, Any]] = None,
        task: Optional[Dict[str, Any]] = None,
        turn: Optional[int] = None,
    ) -> IndependentTestResult:
        """Run the independent check, and record what it ran against.

        The check itself is :meth:`_run_independent_tests_unrecorded`,
        unchanged. This adds the run records it produced to the result's
        ``run_evidence`` and touches nothing else.
        """
        self._run_evidence_log = []
        self._run_evidence_turn = turn
        try:
            result = self._run_independent_tests_unrecorded(
                task_work_results=task_work_results, task=task, turn=turn
            )
            runs = list(self._run_evidence_log or [])
        finally:
            self._run_evidence_log = None
        if runs and isinstance(result, IndependentTestResult):
            # Set on the result itself (not a copy): the result a caller is
            # handed is the very object the check produced.
            try:
                result.run_evidence = {"runs": runs}
            except Exception as exc:  # noqa: BLE001 — evidence never fails a check
                logger.warning("Could not attach the run evidence: %s", exc)
        return result

    def _evidence_request(self, kind: str) -> "EvidenceRequest":
        return request_from_declaration(
            kind,
            getattr(self, "_toolchain", None),
            component=getattr(self, "_component_toolchain", None),
            component_name=getattr(self, "_component", None),
            task=getattr(self, "task_id", None),
            turn=getattr(self, "_run_evidence_turn", None),
        )

    def _begin_run_evidence(
        self,
        kind: str,
        command: Any,
        execution_root: Path,
        origin: Optional[Dict[str, Any]],
        cwd: Optional[str],
        env: Optional[Dict[str, str]],
    ) -> "CommandEvidence":
        """Start one command's record. Never raises."""
        try:
            request = self._evidence_request(kind)
        except Exception:  # noqa: BLE001
            request = None
        try:
            pinned = load_launch_snapshot(
                getattr(self, "task_id", None), self.worktree_path
            )
            declared = pinned.settings if pinned is not None else ()
        except Exception:  # noqa: BLE001 — evidence never fails a check
            declared = ()
        return start_command_evidence(
            request,
            command=command,
            execution_root=execution_root,
            cwd=cwd,
            env=env,
            execution_root_is=EVIDENCE_ROOT_DESCRIPTIONS.get(kind, kind),
            origin=origin,
            declared_settings=declared,
        )

    def _keep_run_evidence(self, evidence: "CommandEvidence") -> None:
        """Finish one command's record and keep it for this check."""
        try:
            record = evidence.finish()
        except Exception as exc:  # noqa: BLE001
            record = {"capture_errors": [f"{type(exc).__name__}: {exc}"]}
        if self._run_evidence_log is None:
            self._run_evidence_log = []
        self._run_evidence_log.append(record)

    def _run_recorded(
        self,
        args: Any,
        *,
        evidence: Tuple[str, Path, Any],
        record_into: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        """Run one project command, with the command recorded.

        The command is run with ``process_group.run_project_command``: the
        same arguments, results and exceptions as ``subprocess.run``, but in
        a process group of its own, so a timeout ends everything the command
        started, not only the shell (13 October 2026). The record is made
        around it and kept whether the command returns, times out or fails to
        start. With ``record_into`` the record is written into that dict (the
        caller's own receipt) instead of this check's list of runs.
        """
        kind, execution_root, origin = evidence
        record = self._begin_run_evidence(
            kind, args, Path(execution_root), origin, kwargs.get("cwd"), env=kwargs.get("env")
        )
        try:
            return process_group.run_project_command(args, **kwargs)
        finally:
            if record_into is None:
                self._keep_run_evidence(record)
            else:
                try:
                    record_into.update(record.finish())
                except Exception as exc:  # noqa: BLE001
                    record_into["capture_errors"] = [f"{type(exc).__name__}: {exc}"]

    def _run_independent_tests_unrecorded(
        self,
        task_work_results: Optional[Dict[str, Any]] = None,
        task: Optional[Dict[str, Any]] = None,
        turn: Optional[int] = None,
    ) -> IndependentTestResult:
        """
        Run the active part's declared test command (see ``_use_part``).

        Parameters
        ----------
        task_work_results : Optional[Dict[str, Any]]
            Task-work results dict. Not read here; kept for the callers.
        task : Optional[Dict[str, Any]]
            Task data dict. When provided, ``requires_infrastructure`` is read
            from task frontmatter and Docker containers are started before test
            execution and stopped afterwards.
        turn : Optional[int]
            Current turn number (1-based), for the run records.

        Returns
        -------
        IndependentTestResult
            Result of independent test execution
        """
        # The active part's declared command (or a caller-supplied one).
        if self.test_command:
            test_cmd = self.test_command
            self._test_command_source = "caller-supplied test command"
        else:
            test_cmd = self._detect_test_command()

        # No declared command for this part: the check could not run, and
        # says what is missing. GuardKit never guesses one (31 October 2026).
        if test_cmd is None:
            return IndependentTestResult.could_not_run(
                test_command="<nothing declared>",
                detail=self._detection_absence or "nothing declared",
                duration_seconds=0.0,
            )

        # Infrastructure lifecycle for tasks with requires_infrastructure
        requires_infra: List[str] = []
        if task is not None:
            ri = task.get("requires_infrastructure")
            if isinstance(ri, list):
                requires_infra = ri

        infra_started = False
        if requires_infra:
            if self._is_docker_available():
                self._start_infrastructure_containers(requires_infra)
                infra_started = True
            else:
                logger.warning(
                    "requires_infrastructure=%s declared but Docker is unavailable. "
                    "Running tests without infrastructure — classification will "
                    "determine appropriate fallback.",
                    requires_infra,
                )

        try:
            # Force subprocess path for infrastructure-dependent tasks (TASK-REV-CB30 R5).
            # The SDK path runs `pytest` via a Bash tool prompt, which resolves the
            # pytest binary via PATH.  On machines with multiple Python installations
            # (e.g. Framework Python + Homebrew Python on macOS), PATH may resolve to
            # a different Python than the one the bootstrap installed packages into,
            # causing ModuleNotFoundError at test collection time.
            # The subprocess path uses sys.executable, bypassing PATH entirely.
            #
            # TASK-FIX-COACHTESTTO: also force subprocess under the LangGraph
            # harness. The SDK path runs pytest through a one-turn LLM agent
            # invocation; under LangGraph (typically a slow local coach-test
            # model) that turn blows past self.test_timeout (300s) and the
            # trust-but-verify leg times out on every task (run-19). The
            # subprocess path runs the same pinned interpreter in seconds with
            # no model in the loop. _is_custom_api_base() does not catch this
            # because LangGraph configures its endpoint outside ANTHROPIC_BASE_URL.
            # Per-component seam: the SDK path hands the command to a one-turn
            # LLM with ``cwd=self.worktree_path`` baked into the harness call,
            # and threading a component directory through the harness is a
            # wider interface change than this lane earns. A component task
            # therefore RUNS ON THE SUBPROCESS PATH — deterministic, and the
            # only path where the component cwd is honoured. Said out loud
            # below rather than silently producing a root-directory run.
            component_pinned_subprocess = self._component_toolchain is not None
            use_sdk = (
                self._coach_test_execution == "sdk"
                and not requires_infra
                and not component_pinned_subprocess
                and not self._is_custom_api_base()
                and not self._is_langgraph_harness()
            )
            if component_pinned_subprocess and self._coach_test_execution == "sdk":
                logger.warning(
                    "Component %r selected: forcing the SUBPROCESS test path. "
                    "The SDK path runs with the worktree root as cwd and would "
                    "run %r in the wrong directory.",
                    self._component,
                    test_cmd,
                )

            # SDK-first dispatch (GAP-FIX #9): use asyncio bridge to call async SDK method
            if use_sdk:
                logger.info(f"Running independent tests via SDK (environment parity): {test_cmd}")
                try:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    sdk_evidence = self._begin_run_evidence(
                        EVIDENCE_SDK, test_cmd, self.worktree_path, None, None, env=None
                    )
                    try:
                        result = loop.run_until_complete(self._run_tests_via_sdk(test_cmd))
                    finally:
                        self._keep_run_evidence(sdk_evidence)
                    logger.info(
                        f"SDK independent tests {'passed' if result.tests_passed else 'failed'} "
                        f"in {result.duration_seconds:.1f}s"
                    )
                    return result
                except Exception as e:
                    # TASK-FIX-7A09: Surface the SDK transport failure
                    # shape instead of the opaque {e}. ProcessError (the
                    # observed shape in forge-run-3) carries .exit_code
                    # and .stderr; all exception types carry a class
                    # name. Structured logging lets the summary-layer
                    # classifier (TASK-FIX-7A02, TASK-FIX-7A07) route
                    # transport-level failures in future incidents
                    # without string-matching the opaque prefix.
                    error_class = type(e).__name__
                    exit_code = getattr(e, "exit_code", None)
                    stderr_val = getattr(e, "stderr", None)
                    stderr_head = (
                        stderr_val[:500]
                        if isinstance(stderr_val, str) and stderr_val
                        else None
                    )
                    parts = [f"error_class={error_class}"]
                    if exit_code is not None:
                        parts.append(f"exit_code={exit_code}")
                    ctx = ", ".join(parts)
                    msg = (
                        f"SDK test execution failed ({ctx}), "
                        f"falling back to subprocess."
                    )
                    if stderr_head:
                        msg += f" stderr: {stderr_head}"
                    logger.warning(msg)
                    # Fall through to subprocess path below

            # Subprocess path (default for coach_test_execution="subprocess", SDK fallback,
            # or infrastructure-dependent tasks forced to subprocess by TASK-REV-CB30 R5)
            if requires_infra and self._coach_test_execution == "sdk":
                logger.info(
                    f"Running independent tests via subprocess (infra-pinned, "
                    f"sys.executable={sys.executable}): {test_cmd}"
                )
            else:
                logger.info(f"Running independent tests via subprocess: {test_cmd}")
            start_time = time.time()

            try:
                # The declared command runs exactly as declared, through the
                # shell, in the part's folder, with an explicit environment
                # (design §B.5). GuardKit does not rewrite it: no pinned
                # interpreter, no injected flags (31 October 2026).
                result = self._run_recorded(
                    test_cmd,
                    evidence=(EVIDENCE_WORKTREE, self.worktree_path, None),
                    shell=True,
                    cwd=str(self._component_run_cwd(self.worktree_path)),
                    capture_output=True,
                    text=True,
                    timeout=self.test_timeout,
                    env=_checker_declared_env(self),
                )

                duration = time.time() - start_time
                tests_passed = result.returncode == 0

                # Summarize output (truncate if too long)
                output = result.stdout or result.stderr or "No output"
                summary = self._summarize_test_output(output)
                if not tests_passed:
                    # Names only, never values: which settings the factory
                    # held back from this command (13 October 2026).
                    summary = f"{summary}\n{self._held_back_note()}"

                signal_absent = False
                # TASK-AB-NPDET01: a non-Python deterministic run classifies
                # absence stack-awarely on BOTH the success and failure branch —
                # the exit-0 zero-test guard. A runner that exits 0 having
                # executed ZERO tests (go ``[no test files]`` only; dotnet
                # "No test is available"; npm "no test specified") is an ABSENT
                # signal (UNKNOWN), never a pass; a missing toolchain (exit 127 /
                # "command not found") is ABSENT, never a Player test failure.
                if self._active_stack_profile is not None:
                    stack_combined = (result.stdout or "") + (result.stderr or "")
                    if classify_absent_for_stack(
                        self._active_stack_profile,
                        result.returncode,
                        stack_combined,
                    ):
                        signal_absent = True
                        tests_passed = False  # IndependentTestResult invariant
                        logger.warning(
                            "Non-Python independent test oracle did not run "
                            "(stack=%s, returncode=%s) — absent signal, not a "
                            "test failure. cmd=%s",
                            self._active_stack_profile.stack,
                            result.returncode,
                            test_cmd,
                        )
                elif not tests_passed:
                    # A missing program (exit 126 or 127, or the shell's own
                    # "command not found") means the command could not run.
                    # No other reading of the output is applied: a declared
                    # command that ran and exited non-zero failed (31 October
                    # 2026, no framework-shaped readings).
                    combined = (result.stdout or "") + (result.stderr or "")
                    if self._is_host_substrate_gap(result.returncode, combined):
                        signal_absent = True
                        logger.warning(
                            "Independent test command could not run "
                            "(returncode=%s) — not a test failure. cmd=%s",
                            result.returncode,
                            test_cmd,
                        )

                logger.info(
                    f"Independent tests "
                    f"{'passed' if tests_passed else ('absent' if signal_absent else 'failed')} "
                    f"in {duration:.1f}s"
                )

                return IndependentTestResult.from_run(
                        tests_passed=tests_passed,
                        test_command=test_cmd,
                        test_output_summary=summary,
                        duration_seconds=duration,
                        output=(result.stdout or "") + (result.stderr or ""),
                        signal_absent=signal_absent,
                        resolved_interpreter=self._resolved_interpreter_for(
                            test_cmd
                        ),
                        exit_code=result.returncode,
                    )

            except subprocess.TimeoutExpired:
                duration = time.time() - start_time
                logger.error(f"Test execution timed out after {self.test_timeout}s")
                # TASK-FIX-COACHTESTTO: timeout — oracle did not complete.
                return IndependentTestResult.absent(
                        test_command=test_cmd,
                        test_output_summary=(
                            f"Test execution timed out after "
                            f"{self.test_timeout}s"
                        ),
                        duration_seconds=duration,
                        resolved_interpreter=self._resolved_interpreter_for(
                            test_cmd
                        ),
                    )
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Test execution failed: {e}")
                # TASK-FIX-COACHTESTTO: execution error before any verdict.
                return IndependentTestResult.absent(
                        test_command=test_cmd,
                        test_output_summary=f"Test execution failed: {e}",
                        duration_seconds=duration,
                        resolved_interpreter=self._resolved_interpreter_for(
                            test_cmd
                        ),
                    )

        finally:
            if infra_started:
                self._stop_infrastructure_containers(requires_infra)

    def _is_docker_available(self) -> bool:
        """Check if Docker daemon is reachable.

        Runs ``docker info`` with a 5-second timeout. Returns True if the
        command succeeds (exit code 0), False otherwise.
        """
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _start_infrastructure_containers(self, services: List[str]) -> Dict[str, str]:
        """Start this task's own Docker container for each declared service.

        Uses recipes from :mod:`guardkit.orchestrator.docker_fixtures`. The
        container is named for the build (``GUARDKIT_RUN_OWNER``) and this
        task, the engine chooses its host port, and the port is read back
        with ``docker port``. Unknown services are logged as warnings and
        skipped.

        The service URLs (e.g. ``DATABASE_URL``) are NOT written to
        :data:`os.environ`: parallel tasks share that, so one task's URL would
        reach another task's tests and one task's teardown would remove
        another's. They are kept on this validator and passed explicitly to
        its test subprocesses (:meth:`_pytest_env`,
        :meth:`_declared_command_env`).

        Args:
            services: List of service names (e.g., ``["postgresql", "redis"]``)

        Returns:
            The service URLs to give this task's test subprocesses.
        """
        owner = fixture_owner(self.task_id)
        for service in services:
            if not is_known_service(service):
                logger.warning("Unknown infrastructure service %r, skipping.", service)
                continue
            logger.info("Starting Docker container for service: %s", service)
            commands = get_start_commands(service, owner)
            for cmd in commands:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(self.worktree_path),
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0 and "docker rm" not in cmd:
                    logger.warning(
                        "Docker setup command exited %d for service %r: %r\nstderr: %s",
                        result.returncode,
                        service,
                        cmd,
                        result.stderr,
                    )
            port_result = subprocess.run(
                get_port_command(service, owner),
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
            )
            host_port = parse_port_output(getattr(port_result, "stdout", None))
            if host_port is None:
                logger.warning(
                    "Could not read the published port of %s for service %r; "
                    "its URL is not set. docker port said: %r",
                    get_container_name(service, owner),
                    service,
                    getattr(port_result, "stderr", ""),
                )
                continue
            env_vars = get_env_exports(service, host_port=host_port)
            self._fixture_env.update(env_vars)
            for key, value in env_vars.items():
                logger.info("Test environment for %s: %s=%s", self.task_id, key, value)
        return dict(self._fixture_env)

    def _stop_infrastructure_containers(self, services: List[str]) -> None:
        """Tear down this task's own Docker container for each declared service.

        Runs ``docker rm -f -v <container_name>`` for each known service,
        releasing its disposable anonymous volumes. Named volumes are retained.
        Only this task's containers are named, so a parallel task's fixtures
        keep running. Unknown services are silently skipped. Errors during
        teardown are logged but do not raise.

        Args:
            services: List of service names (e.g., ``["postgresql", "redis"]``)
        """
        owner = fixture_owner(self.task_id)
        for service in services:
            if not is_known_service(service):
                continue
            container_name = get_container_name(service, owner)
            logger.info("Stopping Docker container: %s", container_name)
            try:
                subprocess.run(
                    ["docker", "rm", "-f", "-v", container_name],
                    capture_output=True,
                    cwd=str(self.worktree_path),
                )
            except Exception as e:
                logger.warning(
                    "Failed to stop container %s: %s", container_name, e
                )
        self._fixture_env.clear()

    @staticmethod
    def _strip_criterion_prefix(text: str) -> str:
        """
        Strip common criterion prefixes from text.

        Removes markdown checkbox prefixes (- [ ], - [x ]), bullet points (* ),
        and numbered prefixes (1. , 2) , 1) ). Does NOT strip AC-N: / AC-NNN:
        labels — that is :meth:`_extract_ac_id`'s responsibility, and stripping
        them here prevented the extractor from running (TASK-GK-CV-001 — the
        strip consumed ``AC-1: ...`` so ``_extract_ac_id`` saw bare prose,
        returned ``None``, and callers fell back to zero-padded ``AC-NNN``
        keys that missed Player-emitted ``AC-N`` lookup keys).

        Parameters
        ----------
        text : str
            Text to clean

        Returns
        -------
        str
            Cleaned text without bullet/checkbox/numbered prefix. AC labels
            (if any) are preserved for downstream :meth:`_extract_ac_id`.
        """
        # Strip leading/trailing whitespace first
        cleaned = text.strip()

        # Strip markdown checkbox prefixes: "- [ ] ", "- [x] "
        if cleaned.startswith("- [ ] "):
            cleaned = cleaned[6:].strip()
        elif cleaned.startswith("- [x] "):
            cleaned = cleaned[6:].strip()
        # Strip bullet points: "* "
        elif cleaned.startswith("* "):
            cleaned = cleaned[2:].strip()
        # Strip numbered prefixes: "1. ", "2) ", "1) "
        else:
            # Check for numbered prefix pattern
            i = 0
            while i < len(cleaned) and cleaned[i].isdigit():
                i += 1
            if i > 0 and i < len(cleaned):
                # Found digits, check for ". " or ") "
                if cleaned[i:i+2] == ". " or cleaned[i:i+2] == ") ":
                    cleaned = cleaned[i+2:].strip()

        return cleaned

    # close-the-loop 2026-08-14: a *bare* markdown checkbox marker, i.e. the
    # ``[ ] `` / ``[x] `` / ``[X] `` that is left behind when the ``- ``
    # bullet has already been stripped somewhere upstream. Requires trailing
    # whitespace so only a real checkbox marker is consumed.
    _BARE_CHECKBOX_PREFIX_RE = re.compile(r'^\[[ xX]\]\s+')

    # A simple, all-numeric acceptance-criterion ID: ``AC-1``, ``AC-01``,
    # ``AC-001``. Compound IDs (``AC-LOAD-01``) deliberately do not match —
    # only the numeric tail's zero-padding is normalised.
    _NUMERIC_AC_ID_RE = re.compile(r"^AC-0*(\d+)$", re.IGNORECASE)

    @staticmethod
    def _extract_ac_id(cleaned: str) -> Tuple[str, Optional[str]]:
        """
        Extract an acceptance-criterion ID from criterion text (TASK-CVAC-001).

        Recognises four formats:

        1. ``**AC-LOAD-01** — text``  (markdown bold + compound + em-dash)
        2. ``**AC-001** — text``      (markdown bold + simple + em-dash)
        3. ``AC-LOAD-01: text``       (compound + colon, no bold)
        4. ``AC-001: text``           (simple + colon, no bold)

        Separators accepted: ``:`` (colon), ``—`` (em-dash, U+2014),
        and ``-`` (hyphen). The ID body matches ``AC`` followed by one or
        more dash-separated alphanumeric uppercase segments.

        Parameters
        ----------
        cleaned : str
            Criterion text. Typically input is post-``_strip_criterion_prefix``
            (checkbox/bullet/numbered prefix already removed). Tolerates
            leading whitespace.

        Returns
        -------
        tuple[str, Optional[str]]
            ``(text_without_id_prefix, extracted_id)`` when an AC ID is
            matched. ``(cleaned, None)`` when no AC ID is matched (the
            input is preserved unchanged).

        Notes
        -----
        Conservative on edge cases:

        - Unmatched bold marker (e.g. ``**AC-LOAD-01: text`` with only an
          opening ``**``) does not match — the regex requires a paired
          closing ``**`` for the bold form.
        - Plain prose mentioning an AC ID without a separator (e.g.
          ``**AC-LOAD-01** is implemented``) does not match — a separator
          (``:``, em-dash, or hyphen) is required.
        """
        work = cleaned.lstrip()

        # Try markdown-bold-wrapped IDs first (more specific).
        m = re.match(
            r'^\*\*(AC(?:-[A-Z0-9]+)+)\*\*\s*[:—\-]\s*', work,
        )
        if m:
            return work[m.end():], m.group(1)

        # Plain compound or simple IDs with explicit separator.
        m = re.match(
            r'^(AC(?:-[A-Z0-9]+)+)\s*[:—\-]\s*', work,
        )
        if m:
            return work[m.end():], m.group(1)

        return cleaned, None

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _detect_test_command(self) -> Optional[str]:
        """The active part's declared test command, or ``None``.

        Only a declared command is run (after-task check redesign, 31 October
        2026): the part's ``test`` from the pinned declaration. With none,
        :attr:`_detection_absence` says what is missing; GuardKit never
        guesses a command. Records where the command came from in
        :attr:`_test_command_source`.
        """
        self._test_command_source = None
        self._active_stack_profile = None
        self._detection_absence = None
        declared = self._declared_test_command()
        if declared is None:
            self._detection_absence = self._describe_detection_absence()
            logger.error(self._detection_absence)
            return None
        self._active_stack_profile = self._declared_stack_profile(declared)
        self._test_command_source = (
            f"{DECLARED_COMMAND_SOURCE} (part {self._component!r})"
            if self._component
            else DECLARED_COMMAND_SOURCE
        )
        logger.info(
            "Test command for %s from the pinned declaration%s: %s",
            self.task_id,
            f" (part {self._component!r}, in {self._component_toolchain.cwd})"
            if self._component_toolchain is not None
            else "",
            declared,
        )
        return declared

    def test_command_source(self) -> Optional[str]:
        """Where the last chosen test command came from, in plain words.

        ``None`` before any command has been chosen, or when no command could
        be found at all.
        """
        return self._test_command_source

    # ------------------------------------------------------------------
    # TS-lane D.1b — the declaration's three helpers
    # ------------------------------------------------------------------

    def _declared_test_command(self) -> Optional[str]:
        """The active part's declared ``test`` command, or ``None``.

        Reads ONLY the pre-turn-1 snapshot resolved in ``__init__`` (design
        §B.4) — never the live ``<worktree>/.guardkit/config.yaml``, which the
        Player can edit. The active part is a component or pattern part
        (its own ``test``) or the root component (the top-level ``test``).
        """
        if self._component_toolchain is not None:
            return self._component_toolchain.test or None
        if self._toolchain is None:
            return None
        return self._toolchain.test or None

    # ---- B9 Lane C: a claim becomes a verdict only on corroboration ------

    #: Where Lane D's feature-level verifier writes its receipt, relative to
    #: the worktree. Read defensively: an absent or unreadable file is simply
    #: NO corroboration — never an error, and never a pass.
    FEATURE_CHECK_RECEIPT_RELPATH = (
        Path(".guardkit") / "autobuild-private" / "feature_check.json"
    )

    # ---- the per-component seam ------------------------------------------

    def _component_run_cwd(self, base: Path) -> Path:
        """Resolve the directory a declared command runs in, under ``base``.

        Returns ``base`` UNCHANGED whenever no component is active — which is
        every task in every repo that has not opted in, so the execution paths
        below are byte-equivalent for them. When a component IS active its
        repo-relative ``cwd:`` is applied under ``base`` (the worktree), with
        the containment re-check that
        catches a symlink no schema can see.

        A containment failure RAISES after a loud error rather than degrading
        to ``base``: silently relocating a refused run to the worktree root
        would execute the component's command against the wrong product. The
        raise is caught by ``run_independent_tests`` and becomes an ABSENT (UNKNOWN) result — never a pass, never a Player
        test failure.

        Raises
        ------
        ValueError
            If the component's ``cwd`` resolves outside ``base``.
        """
        if self._component_toolchain is None:
            return base
        try:
            resolved = resolve_component_cwd(base, self._component_toolchain.cwd)
        except ValueError as exc:
            logger.error(
                "Component %r declares a cwd that escapes the worktree (%s) — "
                "REFUSING to relocate the run; the declared command will not "
                "be executed against the intended directory.",
                self._component,
                exc,
            )
            raise
        if not resolved.is_dir():
            logger.error(
                "Component %r declares cwd=%r, which does not exist under %s. "
                "The declared command cannot run in the directory the repo "
                "named — this is an instrument fault, not a test failure.",
                self._component,
                self._component_toolchain.cwd,
                base,
            )
        return resolved

    def _declared_stack_profile(self, command: str) -> Optional[StackTestProfile]:
        """Overlay the declaration onto the matching stack row, if any.

        Returns ``None`` for the common Python case (no marker row matched and
        the declaration overrides no classifier field), which is precisely what
        keeps a repo declaring ``pytest …`` byte-identical to today: no stack
        profile ⇒ the existing pytest absence classifier still applies.
        """
        if self._toolchain is None:
            return None
        # Per-component seam: a component's markers live in the component's
        # own directory, and a component's classifier overlay is the
        # component's — never the root block's.
        source: "ComponentToolchain | ToolchainDeclaration" = (
            self._component_toolchain
            if self._component_toolchain is not None
            else self._toolchain
        )
        try:
            marker_root = self._component_run_cwd(self.worktree_path)
        except ValueError:
            marker_root = self.worktree_path
        return overlay_declared_profile(
            detect_stack_profile(marker_root),
            command=command,
            absent_substrings=source.absent_substrings,
            ran_marker_regex=source.ran_marker_regex,
            requires_ran_marker=source.requires_ran_marker,
        )

    def _declared_command_env(self) -> Dict[str, str]:
        """Environment for a declared / non-pytest test command (design §B.5).

        Built from nothing (13 October 2026, :meth:`_project_env`): ``PATH``
        from this process, a private ``HOME`` and ``TMPDIR``, the locale and
        proxy settings, the project's declared ``launch:`` settings and
        scratch folders, and the test-service URLs. Never the factory's
        credentials. The resolution rule stays explicit:

        * commands run with the worktree as ``cwd``;
        * they inherit the daemon's ``PATH``, and nothing else resolves them.

        The daemon's PATH is pinned in a systemd unit that never sees nvm, so
        ``node`` resolves only because the D.0 estate fence puts
        ``~/.local/bin/{node,npm,npx}`` symlinks (pointing at a pinned version)
        on that already-present PATH. **NEVER bake an ``nvm`` source into this
        executor**: systemd user units do not source login-shell rc files, and
        an executor that reaches for one is unreproducible and invisible. The
        runtime is a property of the estate, not of the builder.

        The URLs of the test services this validator started are added on top
        (see :meth:`_start_infrastructure_containers`).
        """
        return _checker_declared_env(self)

    def _describe_detection_absence(self) -> str:
        """The plain sentence for a part with no declared test command."""
        where = (
            f"part {self._component!r} (folder {self._component_toolchain.cwd})"
            if self._component_toolchain is not None
            else "the root of the project"
        )
        state = (
            "no `toolchain:` block is pinned for this task"
            if self._toolchain is None
            else f"the pinned `toolchain:` block declares no `test:` for {where}"
        )
        return (
            f"nothing declared: {state}. GuardKit runs only the commands a "
            "project declares in .guardkit/config.yaml (`toolchain.test`, a "
            "component's `test`, or a `parts:` entry's `test`)."
        )

    def _is_host_substrate_gap(
        self, returncode: Optional[int], combined_output: str
    ) -> bool:
        """Return True when a test run could not execute due to a missing host tool.

        TASK-ABFIX-012. Stack-agnostic: a shell return code of 126 (found but not
        executable) or 127 (command not found), or one of the explicit
        ``_HOST_SUBSTRATE_MISSING_PATTERNS`` shell-error strings in the captured
        output. Deliberately does NOT match a bare "No such file or directory" or
        ": not found" (a pytest test legitimately asserting FileNotFoundError, or
        a "key: not found" message, would false-match and mis-route a real code
        bug to infrastructure → false-green) — only the definitive rc 126/127
        signal and the unambiguous shell strings, which a normal pytest assertion
        does not emit.

        A host-substrate gap is an ABSENT signal (the oracle could not run); the
        caller routes it to ``signal_absent=True`` so it surfaces as feedback
        bounded by ``max_turns`` — never a Player code failure (the false-red
        ABFIX-010 prevents) and never a pass
        (``absence-of-failure-is-not-success.md``).
        """
        if returncode in (126, 127):
            return True
        low = (combined_output or "").lower()
        return any(p in low for p in self._HOST_SUBSTRATE_MISSING_PATTERNS)

    def _classify_test_failure(
        self,
        test_output: Optional[str],
        requires_infrastructure: Optional[List[str]] = None,
        task_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Classify a test failure as infrastructure or code with confidence.

        Checks ModuleNotFoundError first to prevent false high-confidence hits
        from service-client library names appearing as substrings in
        ``_INFRA_HIGH_CONFIDENCE`` (e.g. "No module named 'psycopg2'" would
        otherwise match the "psycopg2" entry before we can determine whether
        the import is a valid infra dep or a wrong library choice).

        Parameters
        ----------
        test_output : Optional[str]
            Raw test stdout+stderr output
        requires_infrastructure : Optional[List[str]]
            Infrastructure services declared by the task (e.g. ["postgresql"]).
            When provided, a missing module that is *not* in
            ``_KNOWN_SERVICE_CLIENT_LIBS`` is classified as a code error
            (wrong library choice) rather than ambiguous.

        Returns
        -------
        Tuple[str, str]
            ``("infrastructure", "high")`` if high-confidence pattern matches,
            ``("infrastructure", "ambiguous")`` if only ambiguous pattern matches,
            ``("code", "high")`` if bootstrap context reveals a wrong lib choice,
            ``("parallel_contention", "high")`` if running in a parallel wave and
            the failure looks like a code error that could be caused by concurrent
            worktree mutations (TASK-ABFIX-005),
            ``("code", "n/a")`` otherwise
        """
        if not test_output:
            if self.is_parallel:
                logger.debug(
                    f"[{self.task_id}] _classify_test_failure: no output, parallel wave "
                    f"→ ('parallel_contention', 'high')"
                )
                return ("parallel_contention", "high")
            logger.debug(f"[{self.task_id}] _classify_test_failure: no output → ('code', 'n/a')")
            return ("code", "n/a")
        output_lower = test_output.lower()
        # Check for pytest collection errors FIRST (exit code 2).
        # These occur when pytest cannot import a test file, before any test runs.
        # Must run before ModuleNotFoundError check to avoid misclassification.
        _COLLECTION_ERROR_PATTERNS = ("errors during collection", "error collecting")
        for pattern in _COLLECTION_ERROR_PATTERNS:
            if pattern in output_lower:
                logger.debug(
                    f"[{self.task_id}] _classify_test_failure: collection error pattern"
                    f" matched '{pattern}' → ('collection_error', 'high')"
                )
                return ("collection_error", "high")
        # Check ModuleNotFoundError FIRST, before _INFRA_HIGH_CONFIDENCE patterns,
        # to avoid service-client library names (e.g. "psycopg2") in the error
        # message triggering a false high-confidence infrastructure classification.
        if "modulenotfounderror" in output_lower and "no module named" in output_lower:
            match = re.search(r"no module named '([^']+)'", test_output, re.IGNORECASE)
            if match:
                missing_module = match.group(1).split(".")[0]
                if missing_module in self._KNOWN_SERVICE_CLIENT_LIBS:
                    logger.debug(
                        f"[{self.task_id}] _classify_test_failure: known service-client lib"
                        f" '{missing_module}' missing → ('infrastructure', 'high')"
                    )
                    return ("infrastructure", "high")
                # Module is not a known service-client lib.
                # If the task declares infrastructure requirements, this is a
                # code error (wrong library choice, e.g. psycopg2 instead of asyncpg).
                if requires_infrastructure:
                    logger.debug(
                        f"[{self.task_id}] _classify_test_failure: unknown module"
                        f" '{missing_module}' missing with bootstrap context"
                        f" → ('code', 'high')"
                    )
                    return ("code", "high")
                logger.debug(
                    f"[{self.task_id}] _classify_test_failure: unknown module"
                    f" '{missing_module}' missing (no context) → ('infrastructure', 'ambiguous')"
                )
                return ("infrastructure", "ambiguous")
        # Check SDK API error patterns BEFORE general infra patterns.
        # These indicate the LLM backend rejected the request (wrong model name,
        # rate limits, etc.) — not a Player code defect.
        for pattern in self._SDK_API_ERROR_PATTERNS:
            if pattern.lower() in output_lower:
                logger.debug(
                    f"[{self.task_id}] _classify_test_failure: SDK API error pattern"
                    f" matched '{pattern}' → ('sdk_api_error', 'high')"
                )
                return ("sdk_api_error", "high")
        # TASK-ABFIX-012: a HOST-SUBSTRATE gap (missing host tool) is
        # high-confidence infrastructure. Checked BEFORE the is_parallel
        # reclassification below so a substrate miss in a parallel wave is never
        # amnestied as parallel_contention, and never classified as a code-class
        # block — a substrate gap is the environment's problem, not the Player's.
        for pattern in self._HOST_SUBSTRATE_MISSING_PATTERNS:
            if pattern in output_lower:
                logger.debug(
                    f"[{self.task_id}] _classify_test_failure: host-substrate "
                    f"pattern matched '{pattern}' → ('infrastructure', 'high')"
                )
                return ("infrastructure", "high")
        for pattern in self._INFRA_HIGH_CONFIDENCE:
            if pattern.lower() in output_lower:
                logger.debug(
                    f"[{self.task_id}] _classify_test_failure: high-confidence pattern matched"
                    f" '{pattern}' → ('infrastructure', 'high')"
                )
                return ("infrastructure", "high")
        for pattern in self._INFRA_AMBIGUOUS:
            if pattern.lower() in output_lower:
                logger.debug(
                    f"[{self.task_id}] _classify_test_failure: ambiguous pattern matched"
                    f" '{pattern}' → ('infrastructure', 'ambiguous')"
                )
                return ("infrastructure", "ambiguous")
        # TASK-ABFIX-012: for a TESTING task, a genuine own-code exception token
        # (AssertionError / AttributeError / NameError / TypeError) is the task's
        # OWN bug, not transient parallel contention. Classify it ("code", "high")
        # REGARDLESS of wave_size so it is rejected in BOTH single and parallel
        # waves — neutralising the wave_size swing that lets the
        # parallel_contention amnesty (below) approve a real assertion failure.
        # Failures WITHOUT such a token still fall through to the amnesty, so
        # genuine cross-task contention (import / collection races, which do NOT
        # produce a clean exception token) is preserved.
        if (task_type or "").lower() == "testing":
            for pattern in self._CODE_FAILURE_HIGH_CONFIDENCE:
                if pattern in output_lower:
                    logger.debug(
                        f"[{self.task_id}] _classify_test_failure: TESTING own-code "
                        f"token matched '{pattern}' → ('code', 'high') "
                        f"(wave_size={self.wave_size}, swing neutralised)"
                    )
                    return ("code", "high")
        # TASK-ABFIX-005: In a parallel wave, a code failure might be caused by
        # concurrent worktree mutations (e.g. another task partially writing
        # __init__.py). Reclassify as parallel_contention to allow conditional
        # approval when all Player quality gates passed.
        if self.is_parallel:
            logger.debug(
                f"[{self.task_id}] _classify_test_failure: no pattern matched, "
                f"parallel wave (wave_size={self.wave_size}) "
                f"→ ('parallel_contention', 'high')"
            )
            return ("parallel_contention", "high")
        logger.debug(f"[{self.task_id}] _classify_test_failure: no pattern matched → ('code', 'n/a')")
        return ("code", "n/a")

    def _summarize_test_output(self, output: str, max_length: int = 1000) -> str:
        """
        Summarize test output for reporting.

        Parameters
        ----------
        output : str
            Full test output
        max_length : int
            Maximum length of summary

        Returns
        -------
        str
            Summarized output including error context when present
        """
        # Extract last lines which usually contain summary
        lines = output.strip().split("\n")

        # Error/traceback patterns to detect
        error_patterns = [
            "Error:", "ERRORS", "ImportError", "ModuleNotFoundError",
            "ConnectionRefusedError", "OperationalError", "E   ",
            "FileNotFoundError", "ConnectionError", "TypeError",
            "ValueError", "AttributeError", "KeyError",
        ]

        # Scan forward for the FIRST error/traceback line
        error_context_lines = []
        for i, line in enumerate(lines):
            if any(pat in line for pat in error_patterns):
                # Capture 1 line before and 3 lines after the error line
                start = max(0, i - 1)
                end = min(len(lines), i + 4)
                error_context_lines = lines[start:end]
                break

        # Look for common test summary patterns (last 20 lines, up to 5 lines)
        summary_lines = []
        for line in reversed(lines[-20:]):  # Check last 20 lines
            if any(keyword in line.lower() for keyword in [
                "passed", "failed", "error", "skipped",
                "success", "failure", "ok", "tests"
            ]):
                summary_lines.insert(0, line.strip())
                if len(summary_lines) >= 5:
                    break

        # Build combined output: error context + result summary
        parts = []
        if error_context_lines:
            parts.append("Error detail:\n" + "\n".join(error_context_lines))
        if summary_lines:
            parts.append("Result:\n" + "\n".join(summary_lines))
        elif not error_context_lines:
            # Fallback to last few lines only when no error context and no summary
            parts.append("\n".join(lines[-3:]))

        summary = "\n".join(parts) if parts else "\n".join(lines[-3:])

        # Truncate if needed
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        return summary

    # R1 DE-WIRE (Rich 08-14): _check_bdd_results (TASK-BDD-E8954) removed
    # with its gate — nothing produces bdd_results any more.

    # R1 DE-WIRE (Rich 08-14): _check_bdd_authoring_sweep
    # (TASK-AB-BDDAUTHOR01) removed with its gate and autobuild's
    # _bdd_authoring_sweep_gate — nothing produces bdd_authoring_sweep.

# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "CoachValidator",
    "IndependentTestResult",
    "TASK_TYPE_ALIASES",
]
