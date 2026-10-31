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
import time
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
from guardkit.orchestrator import evidence_repos as evidence_repos_lib
from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.launch_declaration import (
    load_launch_declaration,
    load_launch_snapshot,
    main_checkout_root,
)
from guardkit.orchestrator.project_command_env import (
    main_checkout_environment,
    minimal_environment_note,
    missing_program,
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
EVIDENCE_ORACLE = "behavioural oracle"
EVIDENCE_ROOT_DESCRIPTIONS = {
    EVIDENCE_WORKTREE: "the build worktree",
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
        resolved_interpreter: Optional[str] = None,
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


@dataclass(frozen=True)
class SiblingPart:
    """A declared sibling repository the task changed, as one part of the
    task's check (31 October 2026).

    Its result is combined with the task's own parts by
    :func:`combine_part_results`, so a sibling is judged exactly as a part
    is: a failure (a timeout included) goes back to the builder, a check that
    could not run stops the task, and only a pass allows approval.
    """

    name: str
    cwd: str
    repository: str


def _folder_fingerprint(folder: Path) -> str:
    """A fingerprint of the files git tracks directly in ``folder`` (not
    subfolders): each name with its content as it is on disk, or its link
    target for a symbolic link.

    Only tracked files count (31 October 2026), so what a build or a test
    run writes there (a ``tsconfig.tsbuildinfo``, a coverage or JUnit file)
    never makes the part's install due again. Empty when git cannot list the
    folder.
    """
    digest = hashlib.sha256()
    try:
        listed = run_git(["ls-files", "-z", "--", "."], cwd=folder, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return ""
    if listed.returncode != 0:
        return ""
    names = sorted(
        {n for n in (listed.stdout or "").split("\0") if n and "/" not in n}
    )
    for name in names:
        entry = folder / name
        try:
            if entry.is_symlink():
                body = ("link:" + os.readlink(entry)).encode("utf-8", "surrogateescape")
            elif entry.is_file():
                body = entry.read_bytes()
            else:
                body = b"<deleted>"
        except OSError:
            body = b"<unreadable>"
        digest.update(name.encode("utf-8", "surrogateescape") + b"\0")
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
    (would not start, gave no test signal, declared nothing, its install
    failed) makes
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
            **(
                {"repository": part.repository}
                if isinstance(part, SiblingPart)
                else {}
            ),
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

    # TASK-ABFIX-012: shell words for a missing host tool (psql, docker, npm).
    # They only shape the words the builder is sent (``_classify_test_failure``
    # labels such a failure "infrastructure"); since 31 October 2026 they never
    # turn a failed run into "no test signal": a declared command whose own
    # program is missing could not run (``missing_program``), and a tool
    # missing inside a running script is a failure. The bare ": not found" /
    # "no such file or directory" idioms are excluded: they match legitimate
    # code failures ("key: not found").
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
        matching_strategy: str = "auto",
        wave_size: int = 1,
        turn: int = 1,
        evidence_repos: Optional[List["EvidenceRepo"]] = None,  # TASK-AB-XREPOEV01
        smoke_command: Optional[str] = None,  # TASK-AB-COACHRUNPARITY01 (arm b)
        smoke_expected_exit: int = 0,  # TASK-AB-COACHRUNPARITY01 (arm b)
        security_command: Optional[str] = None,  # the secrets check, when on
        feature_check_repair: Optional[Any] = None,  # whole-feature repair round
        toolchain: Optional["ToolchainDeclaration"] = None,  # TS-lane D.1b
        baseline_commit: Optional[str] = None,  # the task's starting commit
        evidence_baselines: Optional[Dict[str, Optional[str]]] = None,
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
        evidence_repos : Optional[List[EvidenceRepo]]
            Declared sibling repos (TASK-AB-XREPOEV01 AC-002). A sibling the
            task changed is one more part of the task's check
            (:meth:`run_changed_parts`, 31 October 2026): its declared
            ``test_command`` runs as declared in its root, and its result is
            combined with the task's own parts. Default None -> no siblings.
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
        evidence_baselines : Optional[Dict[str, Optional[str]]]
            Each sibling repository's starting commit for this task, keyed by
            its root (``TaskWorkScope.repositories``). A sibling with files
            changed since it is tested; one whose starting commit is not
            known, or whose changes git cannot list, is tested too, since it
            cannot be shown to be unchanged (31 October 2026).
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
        # TASK-AB-XREPOEV01 (AC-002): declared sibling repos whose tests the
        # Coach runs independently. Empty -> no sibling test execution.
        self._evidence_repos: List[EvidenceRepo] = list(evidence_repos or [])
        self._evidence_baselines: Dict[str, Optional[str]] = {
            str(Path(root).resolve()): commit
            for root, commit in (evidence_baselines or {}).items()
        }
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

        # Every task type, an operator hand-over included, has the parts it
        # changed tested (31 October 2026): a task that changed no part has
        # nothing to run, and one that did cannot be approved untested.
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
        test_result: IndependentTestResult
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
            # Nothing was measured, so the task is not approved: the check
            # could not run (31 October 2026; it used to be recorded as no
            # result at all, and nothing stopped on that).
            test_result = IndependentTestResult.could_not_run(
                test_command="<the changed parts' tests>",
                detail=(
                    "the check could not run: "
                    f"{type(exc).__name__}: {exc}"
                ),
                duration_seconds=0.0,
            )
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

        # The sibling repositories' runs are parts of ``independent_tests``
        # (31 October 2026); their records are repeated here, where readers of
        # the bundle have always found them.
        sibling_records = [
            record
            for record in (getattr(test_result, "parts", None) or [])
            if isinstance(record, dict) and record.get("repository")
        ]

        return CoachEvidenceBundle(
            gathering_status=gathering_status,
            gathering_error=gathering_error,
            evidence_repo_tests=sibling_records,
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

    def _files_changed_since(
        self, commit: str, root: Optional[Path] = None
    ) -> Optional[List[str]]:
        """The product files changed in the worktree (or a sibling
        repository's ``root``) since ``commit`` (committed or not, created,
        changed or deleted), or ``None`` when git cannot say. Factory records
        are left out, as the task's own change list leaves them out."""
        from guardkit.orchestrator.task_work_scope import _product

        where = root if root is not None else self.worktree_path
        try:
            diff = run_git(
                ["diff", "--no-renames", "--name-only", "-z", commit],
                cwd=where,
                timeout=60,
            )
            untracked = run_git(
                ["ls-files", "--others", "--exclude-standard", "-z"],
                cwd=where,
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
        siblings = {repo.name for repo in self._evidence_repos}
        for key in ("files_created", "files_modified", "files_deleted"):
            for name in (task_work_results or {}).get(key) or []:
                qualified = evidence_repos_lib.split_qualified(str(name))
                if qualified is not None and qualified[0] in siblings:
                    continue  # a sibling's file: see _changed_siblings
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
        when its dependency files have changed since: the files git tracks
        directly in the part's folder (no subfolders), fingerprinted by name
        and content, so build and test outputs never count.
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
        siblings = self._changed_siblings()
        if not parts and not siblings:
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
            "%s: running the tests of %d changed part(s) (%s), from %s, and "
            "of %d changed sibling repositor%s.",
            self.task_id, len(parts), ", ".join(p.name for p in parts), source,
            len(siblings), "y" if len(siblings) == 1 else "ies",
        )
        runs: List[Tuple[Any, IndependentTestResult]] = []
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
            # A changed sibling repository is one more part, judged the same
            # way (31 October 2026): it used to be a separate gate that let a
            # timeout or a check that could not run through to approval.
            self._use_part(None)
            for repo in siblings:
                runs.append(
                    (
                        SiblingPart(
                            name=f"sibling repository {repo.name}",
                            cwd=str(repo.root),
                            repository=repo.name,
                        ),
                        self._run_sibling_tests(repo),
                    )
                )
        finally:
            self._use_part(None)
        return combine_part_results(runs)

    def _changed_siblings(self) -> List[EvidenceRepo]:
        """The declared sibling repositories this task changed, whose tests
        run with the task's own parts (31 October 2026).

        A sibling with product files changed since its starting commit is
        changed. One whose starting commit is not known, or whose changes git
        cannot list, is tested as well: it cannot be shown to be unchanged.
        """
        changed: List[EvidenceRepo] = []
        for repo in self._evidence_repos:
            baseline = self._evidence_baselines.get(str(Path(repo.root).resolve()))
            listed = (
                self._files_changed_since(baseline, root=Path(repo.root))
                if baseline
                else None
            )
            if listed is None:
                logger.info(
                    "%s: what changed in sibling repository %s is not known; "
                    "its tests run.",
                    self.task_id, repo.name,
                )
                changed.append(repo)
            elif listed:
                changed.append(repo)
        return changed

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
            # ``launch:`` block as the smoke gate reads it. The command runs as
            # declared: no interpreter put first on PATH (31 October 2026).
            env = _checker_env(self, main_checkout=True)
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

    def _run_sibling_tests(self, repo: EvidenceRepo) -> IndependentTestResult:
        """One declared sibling repository's tests, through the same path as
        the task's own parts (:meth:`_run_declared_command`), with the root's
        test time limit.

        Nothing is looked for or put first (31 October 2026): no sibling
        ``.venv`` is probed and no ``python`` or ``pytest`` command is
        rewritten. A repository that needs an interpreter names it in its
        ``test_command``; one that still declares ``interpreter:`` is told it
        is no longer applied. No declared command is "the check could not
        run: nothing declared", as for a part.
        """
        if repo.interpreter:
            detail = (
                f"sibling repository {repo.name} declares `interpreter: "
                f"{repo.interpreter}`, which GuardKit no longer applies "
                "(31 October 2026): the declared `test_command` runs exactly "
                "as written, so name the interpreter in it"
            )
            return IndependentTestResult.could_not_run(
                test_command=repo.test_command or "<nothing declared>",
                detail=detail,
                duration_seconds=0.0,
            )
        if not repo.test_command:
            return IndependentTestResult.could_not_run(
                test_command="<nothing declared>",
                detail=(
                    f"nothing declared: sibling repository {repo.name} "
                    "declares no `test_command`"
                ),
                duration_seconds=0.0,
            )
        return self._run_declared_command(repo.test_command, sibling=repo)

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
            return self._run_declared_command(test_cmd)
        finally:
            if infra_started:
                self._stop_infrastructure_containers(requires_infra)

    def _test_env_for(
        self, sibling: Optional[EvidenceRepo] = None
    ) -> Dict[str, str]:
        """The environment a declared test command runs with: the task's
        pinned ``launch:`` block with the test-service URLs, or a sibling
        repository's own checkout's block. Raises as the helper does."""
        if sibling is None:
            return _checker_declared_env(self)
        return main_checkout_environment(Path(sibling.root))

    def _held_back_note(self, sibling: Optional[EvidenceRepo] = None) -> str:
        """Which settings a project command's environment held back, by name
        only (``project_command_env.minimal_environment_note``); empty when
        the environment cannot be built, which the failure already says."""
        try:
            return minimal_environment_note(self._test_env_for(sibling))
        except OSError:
            return ""

    def _run_declared_command(
        self,
        test_cmd: str,
        sibling: Optional[EvidenceRepo] = None,
    ) -> IndependentTestResult:
        """Run one declared test command exactly as declared, and read its
        result (31 October 2026).

        The one path for the task's own repository (the active part, see
        ``_use_part``) and for a declared sibling repository (``sibling``):
        the command runs through the shell, unchanged, in the part's folder
        or the sibling's root, with an environment built from nothing
        (``project_command_env``: the declared ``launch:`` block, a private
        HOME and the short private TMPDIR), within ``self.test_timeout``.
        GuardKit does not rewrite it: no interpreter is looked for or put
        first, and no framework's idea of "a test ran" is applied.

        * its own program cannot be found, or it cannot start: the check
          could not run (not the builder's to fix);
        * it starts and does not finish within its limit: a failure sent to
          the builder;
        * otherwise its exit code is the verdict.

        The task's own repository uses its pinned ``launch:`` block and its
        run is recorded (``_run_recorded``); a sibling repository uses its own
        checkout's ``launch:`` block and is not recorded, because the record's
        declared inventory belongs to the task's repository.
        """
        if sibling is None:
            where = (
                f"part {self._component} (in {self._component_toolchain.cwd})"
                if self._component_toolchain is not None
                else "the root part"
            )
        else:
            where = f"sibling repository {sibling.name} (in {sibling.root})"
        logger.info("Running the declared tests of %s: %s", where, test_cmd)
        start_time = time.time()
        try:
            run_cwd = (
                self._component_run_cwd(self.worktree_path)
                if sibling is None
                else Path(sibling.root)
            )
            # The declared command's own program must exist, in the folder
            # or on its PATH; if not, the check could not run. A program
            # missing inside a script that started is the script failing,
            # sent to the builder.
            missing = missing_program(
                test_cmd, run_cwd, self._test_env_for(sibling)
            )
            if missing is not None:
                detail = f"`{test_cmd}` for {where} could not start: {missing}"
                logger.error("The check could not run: %s", detail)
                return IndependentTestResult.could_not_run(
                    test_command=test_cmd,
                    detail=detail,
                    duration_seconds=0.0,
                )
            if sibling is None:
                result = self._run_recorded(
                    test_cmd,
                    evidence=(EVIDENCE_WORKTREE, self.worktree_path, None),
                    shell=True,
                    cwd=str(run_cwd),
                    capture_output=True,
                    text=True,
                    timeout=self.test_timeout,
                    env=_checker_declared_env(self),
                )
            else:
                result = process_group.run_project_command(
                    test_cmd,
                    shell=True,
                    cwd=str(run_cwd),
                    capture_output=True,
                    text=True,
                    timeout=self.test_timeout,
                    env=main_checkout_environment(run_cwd),
                )
        except subprocess.TimeoutExpired:
            # A run that started and did not finish within its declared
            # limit is usually the code's doing (a hang, an endless loop,
            # tests too slow for the limit), so it is a failure the builder
            # is sent, not a check that could not run (31 October 2026: a
            # recorded TypeScript build's builder fixed exactly this on its
            # next turn, 27 October).
            duration = time.time() - start_time
            message = (
                f"The tests of {where} timed out: `{test_cmd}` did not "
                f"finish within its {self.test_timeout}-second limit "
                "(test_timeout). A run that does not finish is usually a "
                "hang, an endless loop or tests too slow for the limit; "
                "make the tests finish within it."
            )
            logger.error(message)
            return IndependentTestResult(
                tests_passed=False,
                test_command=test_cmd,
                test_output_summary=message,
                duration_seconds=duration,
                raw_output=message,
            )
        except Exception as e:  # noqa: BLE001 — nothing was measured
            # The command did not start (its folder escapes the worktree,
            # its environment could not be built, the process could not be
            # made): nothing was measured, so the check could not run.
            duration = time.time() - start_time
            logger.error(f"Test execution failed: {e}")
            return IndependentTestResult.could_not_run(
                test_command=test_cmd,
                detail=f"`{test_cmd}` for {where} could not start: {type(e).__name__}: {e}",
                duration_seconds=duration,
            )

        duration = time.time() - start_time
        tests_passed = result.returncode == 0

        # Summarize output (truncate if too long)
        output = result.stdout or result.stderr or "No output"
        summary = self._summarize_test_output(output)
        if not tests_passed:
            # Names only, never values: which settings the factory held back
            # from this command (13 October 2026).
            summary = f"{summary}\n{self._held_back_note(sibling)}"

        # The exit code is the verdict, 126 and 127 included: the command's
        # own program was found above, so a missing program is one inside the
        # script that ran (FEAT-8BB4's "eslint: not found"), which fails.
        logger.info(
            f"Independent tests {'passed' if tests_passed else 'failed'} "
            f"in {duration:.1f}s"
        )

        return IndependentTestResult.from_run(
            tests_passed=tests_passed,
            test_command=test_cmd,
            test_output_summary=summary,
            duration_seconds=duration,
            output=(result.stdout or "") + (result.stderr or ""),
            exit_code=result.returncode,
        )

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
        self._detection_absence = None
        declared = self._declared_test_command()
        if declared is None:
            self._detection_absence = self._describe_detection_absence()
            logger.error(self._detection_absence)
            return None
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
