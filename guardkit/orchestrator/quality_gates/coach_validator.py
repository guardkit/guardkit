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

import ast
import fnmatch
import json
import logging
import os
import re
import stat
import subprocess
import sys
import time
from contextlib import aclosing, contextmanager
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

from guardkit.lib.pytest_argv import isolated_basetemp
from guardkit.lib.pytest_summary import parse_pytest_summary
from guardkit.orchestrator.coach_verification import InterpreterResolutionError, _resolve_venv_python
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
    CONFIG_RELATIVE_PATH,
    ComponentToolchain,
    ToolchainDeclaration,
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
    mark_copy_stability,
    originating_worktree_identity,
    request_from_declaration,
    start_command_evidence,
)
from guardkit.orchestrator.baseline import (
    BASELINE_FAILED,
    BASELINE_UNMEASURED,
    NO_BASELINE_COMPARISON,
    baseline_diff_enabled,
    compute_charged_failures,
    failing_node_ids,
    load_known_failure_ids,
    read_baseline_from_worktree,
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



def _worktree_venv_bin(worktree_path: Path) -> Tuple[str, ...]:
    """The worktree venv's ``bin`` to put first on PATH, or nothing."""
    from guardkit.orchestrator.quality_gates.command_models import venv_path_first

    return venv_path_first(worktree_path)


def _checker_env(
    validator: "CoachValidator",
    *,
    additions: Optional[Dict[str, str]] = None,
    path_first: Sequence[str] = (),
    fixtures: bool = False,
    git_ceiling: Optional[Path] = None,
    main_checkout: bool = False,
) -> Dict[str, str]:
    """The environment one of the checker's project commands runs with,
    built from nothing (see ``CoachValidator._project_env`` for what each
    argument adds). A module-level function, so the process-launch guard can
    rely on it (a method could be overridden); the methods delegate here."""
    return project_command_environment(
        validator.worktree_path,
        validator._launch_declaration(main_checkout),
        additions=validator._command_additions(additions, fixtures, git_ceiling),
        path_first=path_first,
    )


def _checker_pytest_env(
    validator: "CoachValidator", git_ceiling: Optional[Path] = None
) -> Dict[str, str]:
    """The checker's pytest-run environment: the worktree venv's ``bin``
    first on PATH and this task's test-service URLs."""
    return _checker_env(
        validator,
        path_first=_worktree_venv_bin(validator.worktree_path),
        fixtures=True,
        git_ceiling=git_ceiling,
    )


def _checker_declared_env(
    validator: "CoachValidator", git_ceiling: Optional[Path] = None
) -> Dict[str, str]:
    """The checker's declared-command environment, with the test-service URLs."""
    return _checker_env(validator, fixtures=True, git_ceiling=git_ceiling)


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
EVIDENCE_ISOLATED = "independent suite (isolated copy)"
EVIDENCE_WORKTREE = "independent suite (worktree)"
EVIDENCE_SDK = "independent suite (through the SDK, in the worktree)"
EVIDENCE_ORACLE = "behavioural oracle"
EVIDENCE_ROOT_DESCRIPTIONS = {
    EVIDENCE_ISOLATED: (
        "an isolated copy of the build worktree, without Git metadata; the "
        "originating worktree's identity at copy time is recorded separately"
    ),
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
    # Set when an isolated (parallel-wave) attempt could not start and the
    # check was run in the real worktree instead — the same run a wave of one
    # uses. Records THAT it fell back and WHY. Receipt evidence only: no gate,
    # verdict or feedback branch reads it.
    isolation_fallback_reason: Optional[str] = None
    # Most isolated-copy failures may retry in the worktree. A required
    # project-configuration snapshot failure sets this false so the command
    # never runs against mutable configuration after isolation was refused.
    allow_worktree_fallback: bool = True
    # The command's own exit status, when it ran as a subprocess (12 October
    # 2026). ``None`` when there was none to read (the agent-shell path, a
    # timeout, a skipped run). Read only by ``failure_receipt`` below.
    exit_code: Optional[int] = None

    # WHAT THE CHECK RAN AGAINST (repair 7, 2026-10-12): one record per
    # command run for this check, in order — the isolated attempt and its
    # worktree fallback are two. Each names the real execution root, its
    # source before and after, the declared environment inventory and the
    # raw container events of the interval (see ``run_evidence``). Receipt
    # evidence only: no gate, verdict or feedback branch reads it.
    run_evidence: Optional[Dict[str, Any]] = None

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
    #   - skipped:  tests not required for this task type — no advisory fields.
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
        allow_worktree_fallback: bool = True,
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
            allow_worktree_fallback=allow_worktree_fallback,
        )

    @classmethod
    def skipped(
        cls,
        *,
        test_output_summary: str,
        test_command: str = "skipped",
        duration_seconds: float = 0.0,
    ) -> "IndependentTestResult":
        """Tests not required for this task type — no run, no advisory
        fields."""
        return cls(
            tests_passed=True,
            test_command=test_command,
            test_output_summary=test_output_summary,
            duration_seconds=duration_seconds,
        )


# The words ``_test_command_source`` carries when the command came from the
# repository's own ``.guardkit/config.yaml`` rather than from a guess. One
# spelling, set in one place and read in one place, so nothing downstream has
# to match a string it invented.
DECLARED_COMMAND_SOURCE = "repository toolchain declaration"


@dataclass(frozen=True)
class SuiteComparedToBase:
    """A whole-suite run read against what the base branch was ALREADY failing.

    RICH'S SECOND RULING, 2026-09-09: "zero net-new", never "all green". No
    real repository is all green — forge's suite carries about thirty base
    failures, guardkit's eleven to fourteen, all triaged and stable — so a
    leg that demanded a green suite would fail on every red repository for
    ever, and a leg that cannot tell new red from old red teaches everybody
    to ignore red.

    Nothing here is a new mechanism. The base's failing set comes from the
    two places the estate already keeps it (``guardkit.orchestrator.baseline``
    reads both, and the Coach's own gate already subtracts them):

    * the build's MEASURED baseline — the wave-0 probe ran the suite once on
      this branch's base, before any task touched it, and cached the result
      in ``.guardkit/autobuild/<feature>/baseline.json``;
    * the repository's own KNOWN-FAILURE LEDGER, ``qa/known-failures.yaml``,
      whose own words are "every suite run is compared against THIS ledger,
      not against 'all green'".

    Fields
    ------
    failures_total
        How many tests failed in this run.
    inherited
        How many of those the base was already failing (forgiven).
    new_failures
        The ones this leg is charged for — named, and ONLY these, because a
        red leg naming twenty failures of which nineteen are inherited is a
        leg nobody reads.
    stale_base_entries
        Tests the base was failing that did NOT fail here. Never a failure:
        one plain line saying the record has gone stale in the good
        direction.
    base_known
        Always ``True``. A comparison exists ONLY when the base's failing set
        could be established; when it could not, there is no comparison at
        all and the run's own red stands, whole. The field is kept because a
        record that forgives a failure should say on the face of it that the
        base was known.
    base_source
        Where it came from, in ordinary words, for the record.
    passes
        The leg's verdict: no new failures, and the run visibly did work.
    note
        One plain sentence a person can read in the leg's record.
    """

    failures_total: int
    inherited: int
    new_failures: List[str]
    stale_base_entries: List[str]
    base_known: bool
    base_source: str
    passes: bool
    note: str


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
        basetemp_context: Optional[str] = None,  # TASK-AB-BASETEMP01
        in_autobuild_context: bool = False,  # WS3-S1 Q1 SPLIT (hard-abort)
        toolchain: Optional["ToolchainDeclaration"] = None,  # TS-lane D.1b
        component: Optional[str] = None,  # per-component seam
        effective_concurrency: Optional[int] = None,
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
            Number of tasks executing in parallel in the current wave (default: 1).
            When >1, the Coach runs independent tests in an isolated temp directory
            to prevent spurious failures from concurrent worktree mutations, and
            applies more lenient failure classification for contention-related errors.
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
        basetemp_context : Optional[str]
            Attribution label for the per-run pytest ``--basetemp`` isolation
            (TASK-AB-BASETEMP01). When set (e.g. ``"phase4"`` from the
            deterministic Phase-4 runner in ``specialist_invocations.py``),
            it overrides the per-path defaults (``"coach-independent"`` for
            the standard subprocess run, ``"coach-isolated"`` for the
            parallel-wave snapshot run) so a leaked tmp dir names the caller.
            The label is combined with ``task_id`` in the directory prefix.
        toolchain : Optional[ToolchainDeclaration]
            The repo's declared toolchain block (TS-lane D.1b). ``None``
            (default) loads the PRE-TURN-1 SNAPSHOT for ``task_id`` — never
            the live ``<worktree>/.guardkit/config.yaml``, which sits inside
            the tree the Player edits (design §B.4). No snapshot ⇒ no
            declaration ⇒ the detection ladder runs exactly as it did before.
        component : Optional[str]
            The task's ``component:`` selector (per-component seam). ``None``
            (the default, and every task in every repo today) means THE ROOT
            BLOCK — today's semantics, byte-unchanged. A name resolves that
            component's ``test:`` and runs it with the component's ``cwd:``.
            A name the pinned declaration does not define NEVER falls back to
            the root block: it becomes a loud INSTRUMENT FAULT (ABSENT /
            UNKNOWN), because running the backend suite as the verdict on an
            ``app/`` task is exactly the false signal this seam removes.
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
        # ---- the per-component seam --------------------------------------
        # The task's selector, resolved ONCE against the pinned declaration.
        # ``_component_absence`` is set (and the resolution left None) when the
        # task named a component the declaration does not define — the ladder
        # must NOT then quietly run the root command.
        self._component: Optional[str] = component
        self._component_toolchain: Optional["ComponentToolchain"] = None
        self._component_absence: Optional[str] = None
        if component:
            self._component_toolchain = (
                self._toolchain.component(component)
                if self._toolchain is not None
                else None
            )
            if self._component_toolchain is None:
                self._component_absence = self._describe_component_absence(component)
                logger.error(self._component_absence)
            else:
                logger.info(
                    "CoachValidator resolved task component %r: test=%r cwd=%r "
                    "test_timeout=%ss",
                    component,
                    self._component_toolchain.test,
                    self._component_toolchain.cwd,
                    self._component_toolchain.test_timeout,
                )
        # Explicit caller value > the RESOLVED component's declared timeout >
        # the root block's > the historic 300s.
        if test_timeout is not None:
            self.test_timeout = test_timeout
        elif self._component_toolchain is not None:
            self.test_timeout = self._component_toolchain.test_timeout
        elif self._toolchain is not None:
            self.test_timeout = self._toolchain.test_timeout
        else:
            self.test_timeout = 300
        # TS-lane D.1b: set by ``_detect_test_command`` when the ENTIRE ladder
        # came up empty. Replaces the deleted unconditional pytest default —
        # ``run_independent_tests`` turns it into a LOUD ABSENT signal
        # (UNKNOWN), never a silent guess and never a pass.
        self._detection_absence: Optional[str] = None
        # Where the command about to run came from, in ordinary words
        # ("repository toolchain declaration", "task-specific test files
        # detected in the worktree", ...). Set by ``_detect_test_command``;
        # read by the work leg so a red leg can say WHICH command ran and why
        # that one. Never read by any verdict rule.
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
        # WS3-S1 Q1 SPLIT (Rich 2026-07-09): inside an autobuild run a Python
        # project that resolves no worktree venv is a HARD-ABORT — a wrong
        # interpreter poisons every downstream Coach verdict (the DD4F-shaped
        # soft-fail). Interactive CLI callers keep the default (False =
        # warn-and-fallback). The distinction is an EXPLICIT flag, not a
        # heuristic. See coach_verification._resolve_venv_python.
        self._in_autobuild_context = in_autobuild_context
        self._configured_venv_python: Optional[str] = venv_python
        # Step 2 (26 October 2026, GKT-120): a Python worktree with no
        # interpreter is no longer a hard abort. The independent test run
        # reports "could not run" with the remediation as its sentence, which
        # reaches the reviewer as advice; nothing runs under the wrong
        # interpreter.
        self._interpreter_problem: Optional[str] = None
        try:
            self._venv_python: Optional[Path] = _resolve_venv_python(
                self.worktree_path,
                venv_python,
                in_autobuild_context=in_autobuild_context,
            )
        except InterpreterResolutionError as exc:
            self._interpreter_problem = str(exc)
            self._venv_python = None
            logger.warning("Advice, not a stop: %s", exc)
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
        # TASK-AB-BASETEMP01: caller-supplied attribution label for the per-run
        # pytest --basetemp; None -> per-path defaults (see _basetemp_context).
        self._basetemp_context: Optional[str] = basetemp_context
        self.wave_size = max(1, int(wave_size))
        self.effective_concurrency: Optional[int] = (
            int(effective_concurrency)
            if effective_concurrency is not None
            else None
        )
        # Set for the length of one check when an isolated (parallel-wave)
        # attempt could not START and the check is being run in the real
        # worktree instead. Read and cleared by
        # ``_after_isolation_fallback``; ``None`` at every other moment.
        self._isolation_fallback: Optional[IndependentTestResult] = None
        # TASK-AB-NPDET01: the non-Python stack test-execution profile resolved
        # by ``_detect_test_command`` for THIS run (None for Python / no match /
        # parallel-wave deferral). ``run_independent_tests`` reads it to classify
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

    @property
    def test_isolation_concurrency(self) -> int:
        """Concurrency used only for independent-test snapshot selection."""
        if self.effective_concurrency is not None:
            return self.effective_concurrency
        return self.wave_size

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
        own runs report: its required tests (``independent_tests``), the
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

        # The project's tests.
        test_result: Optional[IndependentTestResult]
        if not profile.tests_required:
            test_result = IndependentTestResult.skipped(
                test_output_summary=(
                    f"Independent test verification skipped "
                    f"(tests not required for {task_type.value} tasks)"
                ),
            )
        else:
            try:
                test_result = self.run_independent_tests(
                    task_work_results=task_work_results,
                    task=task,
                    turn=turn,
                )
                # Failures a measured baseline shows were already there are
                # not this task's.
                test_result = self._apply_baseline_diff(
                    test_result, task_work_results
                )
            except Exception as exc:  # noqa: BLE001 — gathering never raises
                logger.error(
                    "gather_evidence: run_independent_tests raised: %s", exc,
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

        Discovery by artefact presence: a file matching
        ``tests/acceptance/*_roundtrip.py`` under the worktree root is run
        with pytest. Otherwise the task's ``behavioural_oracle.command``, when
        declared, is run through the shell in the worktree root. The exit code
        is the verdict; a timeout counts as ran-and-failed; a command that
        could not start, or no check at all, returns ``None``.
        """
        oracle_files = sorted(
            self.worktree_path.glob("tests/acceptance/*_roundtrip.py")
        )
        if oracle_files:
            return self._produce_python_oracle(oracle_files)

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

    def _produce_python_oracle(
        self,
        oracle_files: List[Path],
    ) -> Optional[Dict[str, Any]]:
        """Run the Python roundtrip oracle and return its result."""
        oracle_path = oracle_files[0]
        logger.info(
            "gather_evidence: discovered behavioural-oracle artefact at %s",
            oracle_path,
        )
        oracle_rel = str(oracle_path.relative_to(self.worktree_path))
        timeout_seconds = float(
            os.environ.get("GUARDKIT_ORACLE_TIMEOUT", "300")
        )
        interpreter = self._pytest_interpreter()
        cmd = [interpreter, "-m", "pytest", str(oracle_path)]
        return self._execute_oracle(
            cmd, oracle_rel, timeout_seconds, self._venv_bin_first(), "python",
        )

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

    # ------------------------------------------------------------------
    # Baseline diff (red-baseline retro, L12 item 2)
    # ------------------------------------------------------------------

    def _baseline_context(self):
        """Load (once) the measured baseline + F2 ledger IDs for this worktree.

        Returns ``(baseline_result_or_None, ledger_id_set)``. The measured
        baseline is the session-scoped observation written by the wave-0 probe
        (``read_baseline_from_worktree``); the ledger is the human-curated
        ``qa/known-failures.yaml`` (READ-ONLY). Cached on the instance; both
        fail open to ``None`` / ``set()``.
        """
        cached = getattr(self, "_baseline_ctx_cache", "unset")
        if cached != "unset":
            return cached
        baseline = None
        ledger: set = set()
        try:
            baseline = read_baseline_from_worktree(self.worktree_path)
            ledger = load_known_failure_ids(self.worktree_path)
        except Exception as exc:  # noqa: BLE001 — fail open, diff stays inert
            logger.debug("baseline diff: context load failed: %s", exc)
        self._baseline_ctx_cache = (baseline, ledger)
        return self._baseline_ctx_cache

    def _baseline_diff_active(self) -> bool:
        """Whether the baseline diff should act: flag ON + a red baseline exists.

        A GREEN baseline (or no baseline.json / diff disabled) leaves every
        gate byte-identical to today — the diff only ever suppresses charges
        for failures already-red before wave 1.
        """
        if not baseline_diff_enabled():
            return False
        baseline, ledger = self._baseline_context()
        # Only named failures from a measured baseline can excuse anything;
        # an unmeasured one (did not pass, named nothing) excuses nothing.
        has_baseline_reds = (
            baseline is not None and baseline.state == BASELINE_FAILED
        )
        return has_baseline_reds or bool(ledger)

    def _authored_test_files(self, task_work_results: Dict[str, Any]) -> list:
        """Worktree-relative files the current task touched (created/modified).

        Used to RE-CHARGE a baseline/ledger failure whose test file the task
        itself worked on — a task cannot hide behind the baseline for a test
        it was meant to fix (the retro's fixed-then-still-red constraint). The
        broad touched-union is deliberate here: it re-charges MORE, which is
        the safe (against-false-green) direction.
        """
        files: set = set()
        for key in ("files_authored", "files_created", "files_modified"):
            for f in task_work_results.get(key) or []:
                if isinstance(f, str) and f.strip():
                    files.add(f.strip())
        return sorted(files)

    def _apply_baseline_diff(
        self,
        test_result: "IndependentTestResult",
        task_work_results: Dict[str, Any],
    ) -> "IndependentTestResult":
        """Suppress a ran-and-failed verdict whose failures are ALL pre-existing.

        Red-baseline retro (L12 item 2). When the independent run failed
        (``tests_passed is False``, signal present) and every observed failing
        node ID is in ``measured baseline ∪ F2 ledger`` — minus any whose test
        file the current task authored — the failures are not attributable to
        this task, so the verdict is flipped to a pass annotated with the
        attribution. Otherwise the result is returned UNCHANGED.

        Fail CLOSED: an absent signal is never flipped; if no failing node IDs
        parse (non-pytest stack output) the charge stands; any exception leaves
        the original verdict intact.

        IT SAYS WHY IT DID NOT ACT (2026-09-13). Every path out of here used to
        be silent except the one that suppressed something, so a build where
        this never fired looked identical to a build where it was never
        reached. FEAT-19C4 stalled for five turns on six failures the ledger
        already forgave, and the whole question — which of the four early
        returns was taken — could not be answered from the receipt at all; the
        only record was inside a sandbox that could not be opened. A check that
        cannot say what it did is not a check anybody can trust, so each exit
        now names itself once per turn at INFO, beside the one that already
        spoke.
        """
        try:
            if test_result.signal_absent or test_result.tests_passed is not False:
                # Nothing to forgive: either the run never produced a verdict
                # (never flipped, by design) or it already passed.
                logger.info(
                    "baseline diff: not applicable (signal_absent=%s, "
                    "tests_passed=%s) — nothing to forgive",
                    test_result.signal_absent,
                    test_result.tests_passed,
                )
                return test_result
            if not self._baseline_diff_active():
                baseline, ledger = self._baseline_context()
                logger.info(
                    "baseline diff: INERT — no red base on record, so every "
                    "failure stands (measured baseline: %s; ledger entries: "
                    "%d; kill-switch GUARDKIT_AUTOBUILD_BASELINE_DIFF: %s)",
                    "absent"
                    if baseline is None
                    else (
                        "green" if baseline.passed
                        else (
                            NO_BASELINE_COMPARISON
                            if baseline.state == BASELINE_UNMEASURED
                            else "red"
                        )
                    ),
                    len(ledger),
                    "on" if baseline_diff_enabled() else "OFF",
                )
                return test_result
            observed = failing_node_ids(test_result.raw_output)
            if not observed:
                # Could not identify the failures → cannot safely attribute.
                logger.info(
                    "baseline diff: could not read a single failing test id "
                    "out of the run's output (%d characters of it), so no "
                    "failure can be attributed to the base and every one of "
                    "them stands",
                    len(test_result.raw_output or ""),
                )
                return test_result
            baseline, ledger = self._baseline_context()
            baseline_ids = baseline.failing_node_ids if baseline else []
            charged = compute_charged_failures(
                observed_node_ids=observed,
                baseline_node_ids=baseline_ids,
                ledger_ids=ledger,
                authored_test_files=self._authored_test_files(task_work_results),
            )
            if charged:
                # At least one genuine regression → leave the failure standing.
                # WHICH ones, and whether they are charged because the base
                # never had them or because this task touched their test file
                # (the re-charge rule above) — without that distinction a
                # forgiven-looking build and a re-charged one read the same.
                authored = self._authored_test_files(task_work_results)
                known = set(baseline_ids) | set(ledger)
                recharged = [n for n in charged if n in known]
                genuinely_new = [n for n in charged if n not in known]
                logger.info(
                    "baseline diff: NOT applied — %d failure(s) charged to "
                    "this task (%d newly failing; %d the base already had but "
                    "re-charged because this task touched their test file). "
                    "Charged: %s. Files this task is recorded as touching: %s",
                    len(charged),
                    len(genuinely_new),
                    len(recharged),
                    ", ".join(charged[:20]),
                    ", ".join(authored[:20]) or "(none recorded)",
                )
                return test_result
            attributed = sorted(set(observed))
            # Name only the record(s) that actually covered these failures. A
            # baseline that measured nothing, or one that named none of them,
            # is never credited (reliability repair 2, 12 October 2026).
            by_baseline = set(baseline_ids)
            used_baseline = any(n in by_baseline for n in attributed)
            used_ledger = any(
                n in ledger and n not in by_baseline for n in attributed
            )
            sources_words = " and ".join(
                words
                for words, used in (
                    ("the measured baseline", used_baseline),
                    (
                        "the repository's known-failure ledger "
                        "(qa/known-failures.yaml)",
                        used_ledger,
                    ),
                )
                if used
            )
            summary = (
                f"Independent tests: {len(attributed)} failure(s) attributed to "
                f"{sources_words} (pre-existing before wave 1, "
                f"not this task): {', '.join(attributed)}. No regressions "
                f"introduced by this task (GUARDKIT_AUTOBUILD_BASELINE_DIFF)."
            )
            logger.info(
                "baseline diff: suppressed %d pre-existing failure(s) as "
                "environmental (no task regression): %s",
                len(attributed), attributed,
            )
            # THE EVIDENCE MUST NOT READ AS A LIE (2026-09-13).
            # Flipping the verdict and leaving the run's output untouched puts
            # "tests passed" next to "12 failed" in the same bundle with
            # nothing joining them, and the reviewer — rightly — refuses to
            # believe it. FEAT-C2BA was refused on exactly that wording twice
            # ('independent_tests.tests_passed=true but
            # independent_tests.raw_output shows "12 failed"'), on turns where
            # the builder had done everything asked of it. So the output keeps
            # every byte it had and gains one plain line at the top saying why
            # a pass and a red run are both true.
            preface = (
                "NOTE FOR THE REVIEWER: this run is reported as PASSED even "
                f"though the output below shows {len(attributed)} failing "
                "test(s). Every one of them was ALREADY failing on this "
                f"branch's base before any task touched it ({sources_words}), "
                "and none is in a file this task authored. They are "
                "not this task's failures and there is nothing in them for "
                "the builder to fix. Zero net-new is the bar, not all-green.\n"
                "---\n"
            )
            return dataclass_replace(
                test_result,
                tests_passed=True,
                test_output_summary=summary,
                raw_output=preface + (test_result.raw_output or ""),
            )
        except Exception as exc:  # noqa: BLE001 — fail closed to the real verdict
            # At INFO, not DEBUG: a build runs at INFO, so at DEBUG this said
            # nothing where it mattered and the failure looked like a decision.
            logger.info(
                "baseline diff: could not run (%s: %s) — the verdict is left "
                "exactly as the test run reported it",
                type(exc).__name__,
                exc,
            )
            return test_result

    # ------------------------------------------------------------------
    # The work leg's verdict on a whole declared suite: ZERO NET-NEW
    # ------------------------------------------------------------------

    def base_failing_tests(self) -> Tuple[bool, List[str], str]:
        """What the branch's BASE was already failing, and how we know.

        Returns ``(base_known, failing_ids, source_in_plain_words)``.

        Two sources, both of which already existed and are already read
        together by :meth:`_baseline_context` — this method only says, out
        loud, WHICH of them answered, because a leg that forgives a failure
        must be able to say on whose word it forgave it:

        1. **The build's measured baseline.** The wave-0 probe ran the suite
           once on this branch's base, before wave 1, and wrote
           ``.guardkit/autobuild/<feature>/baseline.json``. This is the
           "establish the base's failing set by running the command once and
           cache it for the build" answer — already built, so this lane did
           not build a second one.
        2. **The repository's known-failure ledger**, ``qa/known-failures.yaml``
           — the human-triaged list. A ledger that EXISTS and is empty is
           knowledge too: it says the base is green.

        The merge door asks the same question at the other end of the
        journey and takes its answer as ``--baseline-json``, "the list of
        tests the target branch was already failing". It reads exactly the
        ``baseline.json`` shape source 1 writes, so the two doors are
        reading one record, not two.

        ``base_known`` is ``False`` only when neither is present — an
        unmeasured baseline (it did not pass and named no failing test) counts
        as not present, and the words then say no baseline comparison was
        possible. Nothing is then forgiven: :meth:`compare_suite_against_base` makes no comparison
        at all, the run's own red stands in full, and the record says in
        plain words that nothing was on record. That is the fail-closed
        direction, and it is the same verdict the Coach's own gate reaches in
        the same state, so the leg and the Coach still agree.
        """
        measured, ledger = self._baseline_context()
        sources: List[str] = []
        ids: List[str] = []
        # An UNMEASURED baseline (it did not pass and named no failing test —
        # an import or collection error, say) is not knowledge of the base:
        # it is never offered as a source, so a comparison is never claimed
        # against it (reliability repair 2, 12 October 2026).
        unmeasured = (
            measured is not None and measured.state == BASELINE_UNMEASURED
        )
        if measured is not None and not unmeasured:
            ids.extend(measured.failing_node_ids)
            sources.append(
                "the build's measured baseline (the wave-0 run on this "
                "branch's base, before any task touched it)"
            )
        ledger_exists = False
        try:
            ledger_exists = (
                Path(self.worktree_path) / "qa" / "known-failures.yaml"
            ).exists()
        except OSError:  # pragma: no cover - defensive
            ledger_exists = bool(ledger)
        if ledger_exists:
            ids.extend(sorted(ledger))
            sources.append(
                "the repository's known-failure ledger "
                "(qa/known-failures.yaml)"
            )
        if not sources:
            if unmeasured:
                return (
                    False,
                    [],
                    f"{NO_BASELINE_COMPARISON}, and there is no "
                    "qa/known-failures.yaml",
                )
            return (
                False,
                [],
                "nothing on record: no measured baseline and no "
                "qa/known-failures.yaml",
            )
        # De-duplicate, first-seen order.
        seen: set = set()
        unique: List[str] = []
        for node in ids:
            if node not in seen:
                seen.add(node)
                unique.append(node)
        return True, unique, " and ".join(sources)

    def compare_suite_against_base(
        self,
        test_result: "IndependentTestResult",
        task_work_results: Optional[Dict[str, Any]] = None,
    ) -> Optional[SuiteComparedToBase]:
        """Read a whole-suite result as "what is NEW", not "is it all green".

        Rich's ruling of 2026-09-09, second half. The bar is ZERO NET-NEW: a
        failure the base already had is not this leg's failure, and the leg
        passes when every failure it saw is one of those. Only the failures
        OUTSIDE that set are named.

        Returns ``None`` when the question does not arise — an absent signal
        (never forgiven, never a pass), or output whose failing test names
        could not be read at all (a non-pytest stack: the plain exit-code
        rule stands and the failure stands with it).

        THE ENTIRELY-RED CASE, deliberately not forgiven. If a run collapses
        — the database never came up, a conftest failed to import, every test
        errored — then "every failure is in the base's list" can be true by
        accident and would forgive a suite that proved nothing. So
        forgiveness also requires that the run VISIBLY DID WORK: at least one
        test passed. A run where nothing passed is reported red with that
        said in words.

        THE BASE-UNKNOWN CASE, also not forgiven. When neither the measured
        baseline nor the ledger exists, nothing is known about the base, and
        an absence of knowledge is not evidence of innocence: forgiving on
        the strength of "we do not know" would forgive every failure of a red
        suite — including a test this very task wrote, because the only thing
        naming the task's own files is ``task_work_results.json``, which is
        itself often missing or incomplete. So no comparison is made at all
        (``None``), the plain exit-code rule stands, and the run's red stands
        with it. The Coach's own gate reaches the same verdict in the same
        state — it charges every failure when neither source answered — so
        the leg and the Coach still agree, which is the whole reason this
        deterministic phase exists. A repository that wants its base's
        failures subtracted here records them: the wave-0 baseline, or its
        own ``qa/known-failures.yaml`` ledger.
        """
        if not baseline_diff_enabled():
            # The operator's existing kill switch
            # (``GUARDKIT_AUTOBUILD_BASELINE_DIFF=0``) turns off every
            # subtraction in a build, this one included: every failure is
            # then charged, as it was before any of this existed.
            logger.info(
                "zero-net-new: skipped, the baseline diff is turned off "
                "(GUARDKIT_AUTOBUILD_BASELINE_DIFF)"
            )
            return None
        if test_result.signal_absent or test_result.tests_passed is not False:
            return None
        observed = failing_node_ids(test_result.raw_output)
        if not observed:
            return None

        base_known, base_ids, base_source = self.base_failing_tests()

        if not base_known:
            # FAIL CLOSED. Nothing is on record about the base, so there is
            # nothing to subtract and no comparison to make: this method
            # returns None and the run's own red stands, whole. A verdict
            # needs positive evidence, which is the same reason the
            # entirely-red run below is not forgiven either.
            logger.info(
                "zero-net-new: no comparison made — %s. Every failure in "
                "this run is charged (fail closed).",
                base_source,
            )
            return None

        # The estate's own subtraction, unchanged:
        # observed - (measured baseline union ledger), plus anything in a
        # test file this task itself authored (a task cannot hide behind
        # the base for a test it was meant to fix).
        authored = self._authored_test_files(task_work_results or {})
        measured, ledger = self._baseline_context()
        new_failures = compute_charged_failures(
            observed_node_ids=observed,
            baseline_node_ids=measured.failing_node_ids if measured else [],
            ledger_ids=ledger,
            authored_test_files=authored,
        )
        stale = [node for node in base_ids if node not in set(observed)]

        # Forgiveness needs POSITIVE evidence that the run did work: at
        # least one test actually passed. No such evidence (nothing passed,
        # or no counts readable at all) means no forgiveness — fail closed.
        summary = parse_pytest_summary(test_result.raw_output)
        something_passed = bool(summary.parsed and (summary.passed or 0) > 0)

        failures_total = len(observed)
        inherited = failures_total - len(new_failures)
        passes = not new_failures and something_passed

        if not something_passed and not new_failures:
            note = (
                f"{failures_total} test(s) failed and nothing passed (no "
                f"test is on record as having passed in this run). Every "
                f"failure may be on the base's list, but a run in which "
                f"nothing passed proves nothing, so it is not forgiven: "
                f"this leg is red. Check that the suite could actually run."
            )
        elif passes:
            note = (
                f"{failures_total} test(s) failed, all {inherited} of them "
                f"already failing on the base — nothing new. Forgiven on the "
                f"word of {base_source}."
            )
        else:
            note = (
                f"{failures_total} test(s) failed: {inherited} the base "
                f"already had, {len(new_failures)} newly failing."
            )
        if stale:
            note += (
                f" {len(stale)} test(s) recorded as failing on the base did "
                f"not fail here — the record has gone stale in the good "
                f"direction (or this command did not select them)."
            )

        logger.info(
            "zero-net-new: %d failed, %d inherited, %d new (base from %s)",
            failures_total,
            inherited,
            len(new_failures),
            base_source,
        )
        return SuiteComparedToBase(
            failures_total=failures_total,
            inherited=inherited,
            new_failures=list(new_failures),
            stale_base_entries=list(stale),
            base_known=base_known,
            base_source=base_source,
            passes=passes,
            note=note,
        )

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

    # Directories to skip when copying worktree for isolated test execution.
    _ISOLATION_SKIP_DIRS: set = {
        ".git", "__pycache__", ".guardkit", ".venv", "venv", "node_modules",
        ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", "*.egg-info",
    }

    # Of the entries the copy does not carry, these two are never linked to
    # either: version control, and guardkit's own state for this build (which
    # contains the worktrees themselves). Everything else the copy skipped is
    # linked back to the real thing, so a command that needs it can reach it.
    # A bootstrap-created environment that lives INSIDE guardkit's own state
    # directory is reached individually — see
    # ``_paths_the_snapshot_must_reach``.
    _ISOLATION_NEVER_LINK: set = {".git", ".guardkit"}

    # Name stem of the isolated copy. The copy itself is called
    # ``guardkit-coach-iso-<random>``; the folder that holds it carries the
    # same name with a leading dot.
    _ISOLATION_COPY_PREFIX = "guardkit-coach-iso-"

    @contextmanager
    def _isolated_copy_location(self):
        """Make an empty folder for the isolated copy, beside the worktree.

        Yields ``(copy_dir, holder_dir)``. The copy goes into ``copy_dir``;
        ``holder_dir`` is the folder around it, which is removed afterwards.

        WHERE IT LIVES, AND WHY. The copy sits in the worktree's parent
        directory, not in the system temp folder. A test command can hand a
        path inside the copy to another program that does not share this
        process's view of the files — a container engine bind-mounting
        ``<copy>/probe.py`` is the case that broke (FEAT-FFEC and FEAT-78F7,
        3 October 2026): the engine ran on another machine, could not see this
        process's ``/tmp``, made an empty folder in place of the file, and the
        test failed before it reached the code. Whatever can see the worktree
        at its path can, in every layout we run, also see the folder that
        holds it, so the copy is visible wherever the worktree is.

        It is never inside the worktree being tested, so it can never appear
        as a change to that worktree. The holder carries a ``.gitignore``
        that ignores everything (itself included), so if the parent folder
        belongs to a git checkout the copy does not show up there either.
        This does not depend on the worktree being a git worktree; a plain
        directory works the same.

        If the parent folder cannot take a new folder (read-only, or the
        worktree is the filesystem root), the copy falls back to the system
        temp folder, as before, and says so in the log.

        Cleanup is ``_remove_isolated_copy``: the copy first, and the ignore
        file only once nothing is left.
        """
        import tempfile

        holder: Optional[Path] = None
        parent = Path(os.path.abspath(str(self.worktree_path))).parent
        if parent != Path(os.path.abspath(str(self.worktree_path))):
            try:
                holder = Path(
                    tempfile.mkdtemp(
                        prefix="." + self._ISOLATION_COPY_PREFIX, dir=str(parent)
                    )
                )
            except OSError as exc:
                logger.warning(
                    "Could not make the isolated copy beside the worktree in "
                    "%s (%s); using the system temp folder instead. A test "
                    "that hands a path inside the copy to a program on "
                    "another machine (a container engine, say) may not find "
                    "it there.",
                    parent,
                    exc,
                )
        if holder is None:
            holder = Path(
                tempfile.mkdtemp(prefix="." + self._ISOLATION_COPY_PREFIX)
            )

        copy_dir = holder / holder.name.lstrip(".")
        try:
            (holder / ".gitignore").write_text("*\n", encoding="utf-8")
            copy_dir.mkdir()
            yield copy_dir, holder
        finally:
            self._remove_isolated_copy(holder, copy_dir=copy_dir)

    @staticmethod
    def _remove_isolated_copy(holder: Path, *, copy_dir: Path) -> None:
        """Remove the copy, then its holder — but keep the ignore file if
        anything survives.

        ORDER MATTERS. The copy goes first. Only when it is completely gone
        are the holder's ``.gitignore`` and the holder removed. If a test
        left something this process cannot delete (a root-owned folder a
        container wrote into, say), the holder and its ignore-everything
        ``.gitignore`` stay, so the leftovers never become visible to git in
        a checkout that holds the worktree's parent and cannot block a
        clean-tree check. Leftovers are logged, never raised: they must not
        turn a finished check into "could not run".
        """
        import shutil

        def _report(_func, path, exc) -> None:
            logger.warning(
                "Could not remove %s while cleaning up the isolated copy: %s",
                path,
                exc,
            )

        def _open_up(root: Path) -> None:
            # One bounded pass, top down: make every folder in the copy that
            # this process owns writable and traversable before it is
            # entered, so read-only and unreadable folders the test left
            # (nested ones included) can be emptied. Never through a symlink:
            # the copy links back to real things in the worktree (a
            # bootstrap environment, say), and chmod follows links.
            # Folders this process does not own fail chmod quietly here and
            # are reported by the removal below.
            def _chmod_dir(p: str) -> None:
                if os.path.islink(p):
                    return
                try:
                    os.chmod(p, stat.S_IRWXU)
                except OSError:
                    pass

            if not root.is_dir() or root.is_symlink():
                return
            _chmod_dir(str(root))
            for dirpath, dirnames, _files in os.walk(str(root)):
                for name in dirnames:
                    _chmod_dir(os.path.join(dirpath, name))

        if copy_dir.exists() or copy_dir.is_symlink():
            _open_up(copy_dir)
            shutil.rmtree(str(copy_dir), onexc=_report)

        if copy_dir.exists() or copy_dir.is_symlink():
            # Something survived: keep (and re-assert) the protection.
            try:
                (holder / ".gitignore").write_text("*\n", encoding="utf-8")
            except OSError as exc:
                logger.warning(
                    "Could not restore %s over the isolated copy's leftovers: "
                    "%s",
                    holder / ".gitignore",
                    exc,
                )
            logger.warning(
                "The isolated copy could not be removed completely; what is "
                "left stays in %s, which ignores everything in it so git "
                "never sees it. Remove it by hand when convenient.",
                holder,
            )
            return

        try:
            others = [p.name for p in holder.iterdir() if p.name != ".gitignore"]
            if others:
                # Something was put beside the copy, outside it. Leave it
                # under the ignore file rather than expose it.
                logger.warning(
                    "Left the isolated copy's holder %s in place: it still "
                    "holds %s, which the copy's cleanup does not own.",
                    holder,
                    ", ".join(sorted(others)),
                )
                return
            (holder / ".gitignore").unlink(missing_ok=True)
            holder.rmdir()
        except OSError as exc:
            logger.warning(
                "Could not remove the isolated copy's holder %s: %s", holder, exc
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
        git_ceiling: Optional[Path] = None,
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
        * ``git_ceiling`` — ``GIT_CEILING_DIRECTORIES`` for a run inside the
          isolated copy. The copy deliberately has no ``.git``; beside the
          worktree, the folder above it can belong to a git checkout (the
          build's own clone), and a ``git`` command in the test suite would
          otherwise act on that checkout. Set to the holder, git behaves as
          it did in the system temp folder: no repository here;
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
            git_ceiling=git_ceiling,
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
        git_ceiling: Optional[Path],
    ) -> Dict[str, str]:
        """The factory's own additions for one of the checker's commands."""
        adds: Dict[str, str] = {}
        if fixtures:
            adds.update(getattr(self, "_fixture_env", {}) or {})
        if git_ceiling is not None:
            adds["GIT_CEILING_DIRECTORIES"] = str(git_ceiling)
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
    # harness-wide). Defence-in-depth: a mis-fired injection (plugin vanished
    # between probe and run) degrades to ``signal_absent=True`` via
    # ``_is_pytest_timeout_usage_error``, which ABFIX-010 carries as ``None``
    # (fed back), never a counted Player failure. Fail toward feedback.

    @staticmethod
    def _is_pytest_timeout_usage_error(returncode: int, combined_output: str) -> bool:
        """True iff a pytest run failed because ``--timeout`` was unrecognised.

        pytest exits ``4`` (usage error) with ``unrecognized arguments:
        --timeout`` when the plugin is absent. That means our gated injection
        mis-fired — the oracle produced NO verdict on the Player's code, so it is
        an ABSENT signal, not a Player test failure (constraint 3,
        ``.claude/rules/absence-of-failure-is-not-success.md``). The match is
        deliberately narrow so it can never mask a genuine exit-1 failure, which
        reports a test summary and never ``unrecognized arguments``.
        """
        return (
            returncode == 4
            and "unrecognized arguments" in combined_output
            and "--timeout" in combined_output
        )

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

    def _basetemp_run_context(self, default_label: str) -> str:
        """Attribution label for the per-run pytest ``--basetemp`` dir.

        TASK-AB-BASETEMP01: composes ``<task_id>-<label>`` so a leaked dir
        under system tmp is attributable to its task and call site. A
        caller-supplied ``basetemp_context`` (e.g. ``"phase4"`` from the
        deterministic Phase-4 runner) overrides the per-path default.
        """
        label = self._basetemp_context or default_label
        if self.task_id:
            return f"{self.task_id}-{label}"
        return label

    def _paths_the_snapshot_must_reach(self) -> List[Path]:
        """What the declared test command needs that a file copy does not carry.

        ASK WHAT BUILT IT, NEVER GUESS THE DIRECTORY. There is no directory
        name that is right for every repository: guess ``.venv`` and the same
        build in a TypeScript repository is missing ``node_modules``; guess
        both and a Go repository is missing its module cache. So nothing here
        is guessed. Two things are asked, and both already know the answer for
        THIS repository:

        * guardkit's environment bootstrap, which created this build's
          environment and records where it put it
          (``environment_bootstrap.bootstrap_created_paths``);
        * the copy itself — an entry it did not carry is, by definition, an
          entry the command cannot reach in the copy.

        A repository whose bootstrap created nothing (a stack that needs no
        per-build environment) yields nothing from the first ask, and behaves
        exactly as it did before this existed.

        Returns
        -------
        List[Path]
            Existing paths in the real worktree, each to be linked into the
            snapshot at the same relative position.
        """
        reach: List[Path] = []

        def _add(path: Path) -> None:
            if path not in reach and path != self.worktree_path:
                reach.append(path)

        # Ask #1: the bootstrap that built this build's environment.
        try:
            from guardkit.orchestrator.environment_bootstrap import (
                bootstrap_created_paths,
            )

            for created in bootstrap_created_paths(self.worktree_path):
                _add(created)
        except Exception as exc:  # noqa: BLE001 — asking must never break a run
            logger.warning(
                "Could not ask the environment bootstrap what it created for "
                "%s (%s); the copy carries only what it copied.",
                self.worktree_path,
                exc,
            )

        # Ask #2: what the copy left behind. Version control and guardkit's
        # own state stay behind deliberately.
        try:
            for item in self.worktree_path.iterdir():
                if item.name in self._ISOLATION_NEVER_LINK:
                    continue
                if item.name in self._ISOLATION_SKIP_DIRS or item.name.endswith(
                    ".egg-info"
                ):
                    _add(item)
        except OSError as exc:
            logger.warning(
                "Could not list %s while working out what the isolated copy "
                "must reach: %s",
                self.worktree_path,
                exc,
            )

        return reach

    def _reach_into_snapshot(
        self, snapshot_root: Path, paths: List[Path]
    ) -> List[str]:
        """Link *paths* into *snapshot_root* at the same relative positions.

        Linking rather than copying: an environment can be gigabytes, and
        nothing in a parallel wave edits it — the contention this snapshot
        exists to defend against is peers editing SOURCE files, which are
        copied.

        Returns the relative paths that were linked, for the operator's log.
        """
        linked: List[str] = []
        for real in paths:
            try:
                relative = real.relative_to(self.worktree_path)
            except ValueError:
                continue
            destination = snapshot_root / relative
            if destination.exists() or destination.is_symlink():
                continue
            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.symlink_to(real, target_is_directory=real.is_dir())
                linked.append(str(relative))
            except OSError as exc:
                logger.warning(
                    "Could not carry %s into the isolated copy: %s",
                    relative,
                    exc,
                )
        return linked

    def _copy_project_config_into_snapshot(
        self, snapshot_root: Path
    ) -> Optional[str]:
        """Copy the optional project config as independent regular bytes.

        ``None`` means either success or genuine absence. A returned string
        is a plain failure reason; the caller refuses worktree fallback before
        the project command starts.
        """
        source = self.worktree_path / CONFIG_RELATIVE_PATH
        relative = str(CONFIG_RELATIVE_PATH)

        try:
            source.lstat()
        except (FileNotFoundError, NotADirectoryError):
            return None
        except OSError as exc:
            return (
                f"project configuration {relative} could not be looked up "
                f"({type(exc).__name__}: {exc})"
            )

        source_fd: Optional[int] = None
        try:
            # Follow a source symlink, as the declaration loaders do, but a
            # pipe/device must never block or be accepted as configuration.
            source_fd = os.open(source, os.O_RDONLY | _O_NONBLOCK)
        except (FileNotFoundError, NotADirectoryError):
            # A dangling source link is absent to the strict and non-strict
            # declaration loaders, so it is absent here too.
            return None
        except OSError as exc:
            return (
                f"project configuration {relative} could not be opened "
                f"({type(exc).__name__}: {exc})"
            )

        try:
            opened = os.fstat(source_fd)
            if not stat.S_ISREG(opened.st_mode):
                return (
                    f"project configuration {relative} is not a regular "
                    "file when opened"
                )
            payload = bytearray()
            while True:
                chunk = os.read(source_fd, 1024 * 1024)
                if not chunk:
                    break
                payload.extend(chunk)
        except OSError as exc:
            return (
                f"project configuration {relative} could not be read "
                f"({type(exc).__name__}: {exc})"
            )
        finally:
            if source_fd is not None:
                try:
                    os.close(source_fd)
                except OSError:
                    pass

        destination_dir = snapshot_root / CONFIG_RELATIVE_PATH.parent
        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            directory_info = destination_dir.lstat()
        except OSError as exc:
            return (
                f"project configuration {relative} could not create or "
                f"inspect its snapshot directory ({type(exc).__name__}: {exc})"
            )
        if not stat.S_ISDIR(directory_info.st_mode):
            return (
                f"project configuration {relative} snapshot directory is "
                "not a real directory"
            )

        destination = snapshot_root / CONFIG_RELATIVE_PATH
        destination_fd: Optional[int] = None
        try:
            destination_fd = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_NOFOLLOW,
                stat.S_IMODE(opened.st_mode) or stat.S_IRUSR,
            )
            remaining = memoryview(payload)
            while remaining:
                written = os.write(destination_fd, remaining)
                if written <= 0:
                    raise OSError("write returned no progress")
                remaining = remaining[written:]
        except OSError as exc:
            return (
                f"project configuration {relative} could not be written to "
                f"the isolated snapshot ({type(exc).__name__}: {exc})"
            )
        finally:
            if destination_fd is not None:
                try:
                    os.close(destination_fd)
                except OSError:
                    pass
        return None

    @staticmethod
    def _command_runs_pytest(test_cmd: str) -> bool:
        """True when the declared command actually invokes pytest.

        NOTHING HERE MAY ASSUME PYTHON. Exit code 5 means "collected no
        tests" to pytest and nothing at all to anybody else: to ``go test``
        or to a shell wrapper it is simply a non-zero exit, which usually
        means the checks FAILED. Reading a Go wrapper's exit 5 as "the check
        could not run" would hide a genuine red behind an estate fault and
        tell the operator something untrue about a command that has no
        opinion about Python. So the pytest-shaped readings below are asked
        only of a pytest-shaped command.

        Matches pytest as a word in the command — ``pytest -q``,
        ``python -m pytest``, ``uv run pytest``, ``/path/to/pytest`` — and
        nothing else. ``make test``, ``./scripts/test.sh``, ``go test ./...``
        and ``npm test`` are all not pytest-shaped, whatever they run
        underneath, because from here they are opaque.
        """
        for token in (test_cmd or "").replace(";", " ").replace("&", " ").split():
            stripped = token.strip("\"'")
            if stripped == "pytest" or stripped.endswith("/pytest"):
                return True
        return False

    def _absence_from_run(
        self,
        returncode: Optional[int],
        combined_output: str,
        tests_passed: bool,
        test_cmd: str,
    ) -> Optional[str]:
        """Why this run produced NO verdict, or ``None`` when it produced one.

        Every branch here is a run that never told us anything about the
        builder's code. A run that exits cleanly having executed nothing is
        one of them: unknown is not a pass.

        These are the same conditions the worktree run applies inline, in the
        same order, stated once so the isolated copy cannot drift away from
        them — the recurring "Nth-injection-site" lesson of the
        absence-of-failure rule family. The worktree run is deliberately left
        calling its own inline copy: a single-task wave must stay exactly what
        it is today, proved by its existing tests, and this lane changes only
        the parallel-wave path.

        Two kinds of reading live here and they are kept apart, because on
        this path a "could not run" ends the turn with nothing for the
        builder:

        * the stack-agnostic ones — the command could not be STARTED at all
          (exit 126 or 127, or one of the shell's own missing-tool
          sentences). True of any command in any language, so they are asked
          of every command;
        * the pytest-shaped ones — exit code 5, a conftest import error, a
          collection error, a rejected ``--timeout``. These are readings of
          pytest's own vocabulary, so they are asked only when the command
          really invokes pytest (see ``_command_runs_pytest``). A declared
          shell wrapper or a ``go test`` line keeps its own meaning for the
          same exit codes, and a genuine red stays the builder's to fix.
        """
        if self._active_stack_profile is not None:
            if classify_absent_for_stack(
                self._active_stack_profile,
                returncode,
                combined_output,
            ):
                return (
                    f"the run reported no tests for the declared stack "
                    f"({self._active_stack_profile.stack}), exit code "
                    f"{returncode}"
                )
            return None
        if tests_passed:
            return None
        if self._command_runs_pytest(test_cmd):
            if "No module named pytest" in combined_output:
                return (
                    "the test runner itself was not installed where the "
                    "command ran"
                )
            if returncode == 5:
                return "the command collected no tests at all"
            if (
                "ImportError while loading conftest" in combined_output
                or "errors during collection" in combined_output
                or "error collecting" in combined_output
            ):
                return (
                    "the suite could not be loaded, so no test ran (a missing "
                    "dependency where the command ran)"
                )
            if self._is_pytest_timeout_usage_error(returncode, combined_output):
                return (
                    "the per-test timeout option was rejected, so no test ran "
                    "(the timeout plugin was missing where the command ran)"
                )
        if self._is_host_substrate_gap(returncode, combined_output):
            return (
                f"the command could not be executed where it was asked to run "
                f"(exit code {returncode}) — something it needs was not there"
            )
        return None

    # ------------------------------------------------------------------
    # THE RULE: a check that could not run is not a check that failed
    # ------------------------------------------------------------------
    # "The check ran and the result is bad" and "the check could not run" are
    # different outcomes, and they never share a code path. A check that could
    # not run is an ESTATE fault:
    #
    #   1. it is NEVER put in the builder's feedback as something to fix —
    #      not as a must-fix, not as an observation, not as a record of
    #      honesty. The builder did not cause it and cannot fix it, and on
    #      2026-09-11 a build handed one to the coder five turns running until
    #      the coder deleted two working functions trying to satisfy it;
    #   2. it can NEVER let a quality gate report the check as passed. The
    #      gate says UNKNOWN, which is not a pass — the same false receipt as
    #      an image that verifies green carrying yesterday's code;
    #   3. it IS reported, in plain words, naming the command, the directory
    #      it ran in and what was missing, to the operator's log and the
    #      turn's receipt.
    # ------------------------------------------------------------------

    def _worktree_run_said_nothing(
        self,
        result: "IndependentTestResult",
        worktree_returncode: Optional[int],
    ) -> bool:
        """Did the worktree run really fail to say anything about the code?

        Only asked after an isolated attempt could not start, because only
        there does the answer END THE TURN with nothing for the builder. That
        is why the question is asked again here rather than taken from the
        worktree run's own inline reading.

        THE INLINE READING IS NOT SAFE TO END A TURN ON. The worktree run
        classifies absence with its own copy of the pytest vocabulary
        whenever no stack profile is declared: exit code 5 as "collected no
        tests", the words "errors during collection" as "the suite could not
        load". Those are true of pytest and of nothing else. A repository
        that declares a shell wrapper — ``qa/run-suite.sh`` — gets that
        vocabulary applied to a script that has no opinion about Python, and
        exit 5 there usually means the checks FAILED. Honouring it would
        erase a genuine red, clear the builder's real must-fixes and tell the
        operator that nothing ran while quoting the five things that failed.
        The same wrong answer would come back for ``go test`` and for
        ``npm test``.

        So only a command that could not START counts here: the
        stack-agnostic reading (exit 126 or 127, or one of the shell's own
        missing-tool sentences, ``_is_host_substrate_gap``), and, for a
        command that really invokes pytest, the test runner itself missing
        where it ran. Everything else is what a wave of one would report. A
        red stays the builder's, and the receipt simply records that the
        check fell back.

        A run that started and reported no tests — pytest exit 5, a stack's
        "no tests" phrase, a declared absence phrase, an exit 0 with no test
        count recognised — stays an absent signal, exactly as a wave of one
        reports it: never a pass, and the Coach and the builder see it. Ending
        the turn as an estate fault instead made a wave of two worse than a
        wave of one, and stopped a whole feature on a project check that
        passed but ran no tests the stack profile recognises (23 October
        2026). The isolated copy still asks the wider ``_absence_from_run``
        question, so such a run there still falls back to the worktree.

        ``worktree_returncode`` is ``None`` when the command never completed
        at all — a timeout, or a failure before any exit code existed. There
        is no exit code to misread there and nothing was verified either way,
        so it stays what it is: the check could not run.
        """
        if result.check_could_not_run:
            return True
        if not result.signal_absent:
            return False
        if worktree_returncode is None:
            return True
        if worktree_returncode == 0:
            return False
        return self._is_host_substrate_gap(
            worktree_returncode, result.raw_output or ""
        ) or (
            self._command_runs_pytest(result.test_command)
            and "No module named pytest" in (result.raw_output or "")
        )

    def _after_isolation_fallback(
        self,
        result: "IndependentTestResult",
        *,
        worktree_returncode: Optional[int],
    ) -> "IndependentTestResult":
        """Close out a check that fell back from the isolated copy.

        No-op unless an isolated attempt could not start this turn. When one
        did:

        * the worktree run started — keep its result, and record on the
          receipt that it fell back and why. A red is a red and an absent
          signal is an absent signal: each reaches the builder exactly as a
          wave of one would have delivered it;
        * the command could not start in the worktree either (or never
          finished) — the turn ends as an estate fault, naming the command,
          both directories and what was missing, in the operator's log and on
          the receipt.

        Which of the two it is comes from ``_worktree_run_said_nothing``, not
        from the worktree run's own inline reading. ``worktree_returncode``
        is required, not defaulted, so a future caller cannot silently lose
        the fence and start ending turns on a misread exit code again.
        """
        isolated = self._isolation_fallback
        self._isolation_fallback = None
        if isolated is None:
            return result

        reason = isolated.check_could_not_run_detail or (
            "the isolated copy could not start the check"
        )
        if self._worktree_run_said_nothing(result, worktree_returncode):
            detail = (
                f"The check could not run anywhere. Command: "
                f"{result.test_command}. In an isolated copy of the worktree: "
                f"{reason} In the worktree itself ({self.worktree_path}): "
                f"{result.test_output_summary}"
            )
            logger.error("%s", detail)
            return IndependentTestResult.could_not_run(
                test_command=result.test_command,
                detail=detail,
                duration_seconds=result.duration_seconds,
                raw_output=result.raw_output,
                resolved_interpreter=result.resolved_interpreter,
            )

        if result.signal_absent:
            outcome = "an absent signal, exactly as a wave of one would report"
        elif result.tests_passed:
            outcome = "passed"
        else:
            outcome = "failed"
        logger.info(
            "The check ran in the worktree after the isolated copy could not "
            "start it, and the result is the builder's to read (%s).",
            outcome,
        )
        return dataclass_replace(result, isolation_fallback_reason=reason)

    def _run_isolated_tests(self, test_cmd: str) -> "IndependentTestResult":
        """
        Run tests in an isolated copy of the worktree (Option B: copy).

        Copies the worktree to a folder beside it (see
        ``_isolated_copy_location`` for where and why — not the system temp
        folder), excluding large/irrelevant directories, and runs tests
        there. This prevents spurious failures caused by concurrent mutations
        from other tasks running in the same parallel wave.

        Parameters
        ----------
        test_cmd : str
            Test command to run (e.g. ``"pytest tests/test_foo.py -v --tb=short"``)

        Returns
        -------
        IndependentTestResult
            Result of isolated test execution
        """
        import shutil

        start_time = time.time()
        logger.info(
            f"[TASK-ABFIX-005] Running isolated tests (wave_size={self.wave_size}): {test_cmd}"
        )

        try:
            with self._isolated_copy_location() as (tmpdir_path, holder):
                # Repair 7: who the copy came from, at the moment of copying.
                copied_from = self._originating_identity_for_copy()

                # Copy worktree snapshot, skipping large/irrelevant directories
                for item in self.worktree_path.iterdir():
                    dest = tmpdir_path / item.name
                    if item.name in self._ISOLATION_SKIP_DIRS or item.name.endswith(".egg-info"):
                        continue
                    try:
                        if item.is_dir():
                            shutil.copytree(
                                str(item),
                                str(dest),
                                ignore=shutil.ignore_patterns(
                                    "__pycache__", "*.pyc", "*.pyo",
                                    ".pytest_cache", ".mypy_cache",
                                ),
                            )
                        else:
                            shutil.copy2(str(item), str(dest))
                    except (OSError, shutil.Error) as copy_err:
                        logger.warning(
                            f"[TASK-ABFIX-005] Skipping {item.name} during isolation copy: {copy_err}"
                        )

                config_copy_error = self._copy_project_config_into_snapshot(
                    tmpdir_path
                )
                if config_copy_error is not None:
                    duration = time.time() - start_time
                    detail = (
                        f"The check could not run. Command: {test_cmd}. "
                        f"Directory: {self._component_run_cwd(tmpdir_path)} "
                        f"(an isolated copy of the worktree). What was "
                        f"missing: {config_copy_error}."
                    )
                    logger.error("%s", detail)
                    return IndependentTestResult.could_not_run(
                        test_command=test_cmd,
                        detail=detail,
                        duration_seconds=duration,
                        resolved_interpreter=self._resolved_interpreter_for(
                            test_cmd
                        ),
                        allow_worktree_fallback=False,
                    )

                logger.info(
                    f"[TASK-ABFIX-005] Worktree snapshot created at {tmpdir_path}"
                )
                # Repair 7: did the worktree hold still while it was copied?
                copied_from = self._copy_stability(copied_from)

                # THE COPY IS NOT ENOUGH. The copy carries the source files;
                # the declared test command also needs whatever guardkit's
                # bootstrap built for this build, which the copy deliberately
                # does not duplicate. Ask what built it, never guess the
                # directory — see ``_paths_the_snapshot_must_reach``.
                linked = self._reach_into_snapshot(
                    tmpdir_path, self._paths_the_snapshot_must_reach()
                )
                if linked:
                    logger.info(
                        "The isolated copy can reach what the test command "
                        "needs: %s",
                        ", ".join(linked),
                    )

                # Run tests in the isolated copy
                if test_cmd.startswith("pytest"):
                    parts = test_cmd.split()
                    # TASK-FIX-COACHPYENV: pin pytest to the bootstrap venv
                    # interpreter, never sys.executable / PATH pytest.
                    # TASK-ABFIX-011: append a gated per-test --timeout so a hung
                    # test on a PARALLEL wave is named-FAILED, not tests_run=0
                    # (the easy-to-miss 4th injection site — ABFIX-010 GAP 3).
                    # TASK-AB-BASETEMP01: the tempdir COPY isolates the CWD but
                    # NOT pytest's basetemp — that is still the shared per-user
                    # /tmp/pytest-of-<user> default, which two concurrent loops
                    # on one host race. Inject a unique --basetemp (a
                    # pre-existing --basetemp in the command wins; the dir is
                    # best-effort removed after the run).
                    with isolated_basetemp(
                        self._basetemp_run_context("coach-isolated"),
                        parts[1:],
                    ) as basetemp_argv:
                        cmd = (
                            [self._pytest_interpreter(), "-m", "pytest"]
                            + parts[1:]
                            + self._pytest_timeout_argv()
                            + basetemp_argv
                        )
                        result = self._run_recorded(
                            cmd,
                            evidence=(EVIDENCE_ISOLATED, tmpdir_path, copied_from),
                            cwd=str(self._component_run_cwd(tmpdir_path)),
                            capture_output=True,
                            text=True,
                            timeout=self.test_timeout,
                            env=_checker_pytest_env(self, git_ceiling=holder),
                        )
                else:
                    # Per-component seam: the isolated copy is a copy of the
                    # WHOLE worktree, so the component's directory exists
                    # inside it at the same relative path. Without this the
                    # parallel-wave oracle would run the component's command
                    # at the copy's root — the same wrong-directory failure the
                    # standard path was fixed for.
                    result = self._run_recorded(
                        test_cmd,
                        evidence=(EVIDENCE_ISOLATED, tmpdir_path, copied_from),
                        shell=True,
                        cwd=str(self._component_run_cwd(tmpdir_path)),
                        capture_output=True,
                        text=True,
                        timeout=self.test_timeout,
                        env=_checker_declared_env(self, git_ceiling=holder),
                    )

                duration = time.time() - start_time
                tests_passed = result.returncode == 0
                output = result.stdout or result.stderr or "No output"
                summary = self._summarize_test_output(output)

                # DID THIS RUN SAY ANYTHING AT ALL? ``_absence_from_run``
                # states the conditions once: a command that could not be
                # executed at all (asked of every command, in any language),
                # and — only when the command really invokes pytest — a
                # missing runner, a suite that could not load, a rejected
                # timeout option. None of them is a verdict on the builder's
                # code, and in the isolated copy every one of them means the
                # copy could not start the check. The turn then falls back to
                # the real worktree (see ``run_independent_tests``), which is
                # the run a wave of one already uses. Anything else — a
                # wrapper script exiting 5 because five checks failed, say —
                # is a verdict, and stays the builder's to fix.
                combined = (result.stdout or "") + (result.stderr or "")
                could_not_start = self._absence_from_run(
                    result.returncode, combined, tests_passed, test_cmd
                )
                if could_not_start is not None:
                    detail = (
                        f"The check could not run. Command: {test_cmd}. "
                        f"Directory: {self._component_run_cwd(tmpdir_path)} "
                        f"(an isolated copy of the worktree). What was missing: "
                        f"{could_not_start}."
                    )
                    logger.error("%s", detail)
                    return IndependentTestResult.could_not_run(
                        test_command=test_cmd,
                        detail=detail,
                        duration_seconds=duration,
                        raw_output=combined,
                        resolved_interpreter=self._resolved_interpreter_for(
                            test_cmd
                        ),
                    )

                logger.info(
                    f"[TASK-ABFIX-005] Isolated tests "
                    f"{'passed' if tests_passed else 'failed'} "
                    f"in {duration:.1f}s"
                )

                # ``combined`` is byte-identical to raw_output here (both are
                # stdout+stderr); from_run derives tests_skipped from it.
                return IndependentTestResult.from_run(
                    tests_passed=tests_passed,
                    test_command=test_cmd,
                    test_output_summary=summary,
                    duration_seconds=duration,
                    output=(result.stdout or "") + (result.stderr or ""),
                    signal_absent=False,
                    resolved_interpreter=self._resolved_interpreter_for(test_cmd),
                    exit_code=result.returncode,
                )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"[TASK-ABFIX-005] Isolated test execution timed out after {self.test_timeout}s")
            # TASK-FIX-COACHTESTTO: timeout — oracle did not complete.
            return IndependentTestResult.absent(
                test_command=test_cmd,
                test_output_summary=f"Isolated test execution timed out after {self.test_timeout}s",
                duration_seconds=duration,
                resolved_interpreter=self._resolved_interpreter_for(test_cmd),
            )
        except Exception as e:
            duration = time.time() - start_time
            # The copy, or the command's own start, went wrong before any
            # verdict existed: the check COULD NOT RUN in the isolated copy,
            # so the turn falls back to the real worktree.
            detail = (
                f"The check could not run. Command: {test_cmd}. Directory: an "
                f"isolated copy of {self.worktree_path}. What was missing: "
                f"the copy could not be prepared or the command could not be "
                f"started ({e})."
            )
            logger.error("%s", detail)
            return IndependentTestResult.could_not_run(
                test_command=test_cmd,
                detail=detail,
                duration_seconds=duration,
                resolved_interpreter=self._resolved_interpreter_for(test_cmd),
            )

    # ---- what the check ran against (repair 7, 2026-10-12) ---------------
    #
    # Every command this validator runs for its independent check is
    # recorded by ``run_evidence``: the real execution root (the worktree, or
    # the isolated copy that has no ``.git``), its source just before and just
    # after, the declared environment inventory, and the raw container events
    # of the interval. Recording NEVER changes a verdict: the command itself
    # is run exactly as before by ``subprocess.run``, and every capture error
    # is written into the record, never raised.

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
        ``run_evidence`` (one per command: an isolated attempt and its
        worktree fallback are two) and touches nothing else.
        """
        problem = getattr(self, "_interpreter_problem", None)
        if problem:
            return IndependentTestResult.could_not_run(
                test_command="the project's test command",
                detail=problem,
                duration_seconds=0.0,
                allow_worktree_fallback=False,
            )
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

    def _copy_stability(
        self, at_start: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Take the identity again after copying and say whether it held."""
        try:
            return mark_copy_stability(at_start, self._originating_identity_for_copy())
        except Exception as exc:  # noqa: BLE001 — evidence never fails a check
            record = dict(at_start or {})
            record["stable_during_copy"] = f"not known (capture error: {exc})"
            return record

    def _originating_identity_for_copy(self) -> Optional[Dict[str, Any]]:
        """The worktree's HEAD and temporary-index tree, taken as it is copied."""
        try:
            return originating_worktree_identity(self.worktree_path)
        except Exception as exc:  # noqa: BLE001 — evidence never fails a check
            return {"status": f"not recorded: capture error ({exc})"}

    def _run_independent_tests_unrecorded(
        self,
        task_work_results: Optional[Dict[str, Any]] = None,
        task: Optional[Dict[str, Any]] = None,
        turn: Optional[int] = None,
    ) -> IndependentTestResult:
        """
        Run tests independently to verify Player's report.

        This is a "trust but verify" check - we run the tests ourselves
        to ensure the Player's reported results are accurate.

        Parameters
        ----------
        task_work_results : Optional[Dict[str, Any]]
            Task-work results dict (already loaded in memory). Passed through
            to _detect_test_command for primary test file detection.
        task : Optional[Dict[str, Any]]
            Task data dict. When provided, ``requires_infrastructure`` is read
            from task frontmatter and Docker containers are started before test
            execution and stopped afterwards.
        turn : Optional[int]
            Current turn number (1-based). When provided, enables the quinary
            fallback in ``_detect_test_command`` that scans prior player turn
            reports to find test files created in earlier turns.

        Returns
        -------
        IndependentTestResult
            Result of independent test execution
        """
        # Interpreter consistency diagnostic (TASK-REV-CB30 R7;
        # TASK-FIX-COACHPYENV adds resolved_interpreter so post-mortems can
        # confirm Coach ran under the bootstrap venv, not host PATH pytest).
        import shutil
        which_pytest = shutil.which("pytest")
        logger.info(
            "Test execution environment: sys.executable=%s, "
            "which pytest=%s, coach_test_execution=%s, "
            "resolved_interpreter=%s",
            sys.executable,
            which_pytest,
            self._coach_test_execution,
            self._pytest_interpreter(),
        )

        # Determine test command (pass task_id and results for task-specific filtering)
        #
        # ONE COMMAND, TWO CALLERS. This method is the single place a test
        # command is chosen inside a build. The work leg's deterministic
        # Phase-4 runner
        # (``specialist_invocations._run_deterministic_phase_4``) calls it, and
        # so does the Coach's own independent verification. They therefore run
        # the SAME command by construction — which is the whole reason the
        # deterministic phase exists, and why a repository's declared command
        # cannot be honoured on one side of that pair and guessed on the other.
        if self.test_command:
            test_cmd = self.test_command
            self._test_command_source = "caller-supplied test command"
        else:
            test_cmd = self._detect_test_command(
                self.task_id, task_work_results=task_work_results, turn=turn
            )

        # If test_cmd is None, it means task-specific filtering was requested
        # but no matching tests were found. Skip verification in this case.
        if test_cmd is None:
            # TS-lane D.1b: the deleted pytest default's replacement. When the
            # WHOLE ladder came up empty (no declaration, no marker), this is
            # an instrument fault — surfaced as ABSENT (UNKNOWN), which can
            # never read as a pass. The narrower "this task wrote no tests in a
            # shared worktree" case below is unchanged.
            if self._detection_absence:
                return IndependentTestResult.absent(
                    test_command="<no test command declared or detected>",
                    test_output_summary=self._detection_absence,
                    duration_seconds=0.0,
                )
            logger.info(f"No task-specific tests found for {self.task_id}, skipping independent verification")
            return IndependentTestResult.skipped(
                test_output_summary=f"No task-specific tests found for {self.task_id}, skipping independent verification",
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

            # Parallel wave isolation (TASK-ABFIX-005): run tests in temp directory
            # snapshot to prevent spurious failures from concurrent worktree mutations.
            # Applied when wave_size > 1 and not using SDK (SDK already runs in isolation).
            if self.test_isolation_concurrency > 1 and not use_sdk:
                logger.info(
                    "[TASK-ABFIX-005] Concurrent test execution detected "
                    f"(wave_size={self.wave_size}, "
                    f"effective_concurrency={self.effective_concurrency}), "
                    f"running tests in an isolated copy beside the worktree"
                )
                isolated = self._run_isolated_tests(test_cmd)
                if not isolated.check_could_not_run:
                    return isolated
                if not isolated.allow_worktree_fallback:
                    return isolated
                # THE FALLBACK. A wave of one already runs this check in the
                # real worktree and it works; a wave of two must not be worse
                # than a wave of one. The isolated copy could not start the
                # check, so run it where a wave of one runs it, and record
                # plainly that it fell back and why. Only if THAT cannot run
                # either does the turn end as an estate fault
                # (``_after_isolation_fallback``).
                logger.warning(
                    "The isolated copy could not start the check, so it will "
                    "run in the worktree instead — the same run a single-task "
                    "wave uses. %s",
                    isolated.check_could_not_run_detail,
                )
                self._isolation_fallback = isolated

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
                # For Python/pytest commands, use sys.executable to eliminate PATH ambiguity.
                # This ensures the same interpreter as the orchestrator process is used,
                # avoiding discrepancies when the shell resolves `python3` via PATH.
                if test_cmd.startswith("pytest"):
                    parts = test_cmd.split()
                    # TASK-FIX-COACHPYENV: pin pytest to the bootstrap venv
                    # interpreter, never sys.executable / PATH pytest.
                    # TASK-ABFIX-011: append a gated per-test --timeout (no-op
                    # unless Python stack + pytest-timeout resolvable).
                    # TASK-AB-BASETEMP01: inject a unique --basetemp under the
                    # system temp dir so concurrent loops on one host cannot
                    # race pytest's shared /tmp/pytest-of-<user> default (a
                    # pre-existing --basetemp in the command wins; the dir is
                    # best-effort removed after the run).
                    with isolated_basetemp(
                        self._basetemp_run_context("coach-independent"),
                        parts[1:],
                    ) as basetemp_argv:
                        cmd = (
                            [self._pytest_interpreter(), "-m", "pytest"]
                            + parts[1:]
                            + self._pytest_timeout_argv()
                            + basetemp_argv
                        )
                        result = self._run_recorded(
                            cmd,
                            evidence=(EVIDENCE_WORKTREE, self.worktree_path, None),
                            cwd=str(self._component_run_cwd(self.worktree_path)),
                            capture_output=True,
                            text=True,
                            timeout=self.test_timeout,
                            env=_checker_pytest_env(self),
                        )
                else:
                    # TS-lane D.1b (design §B.5): the declared / non-pytest
                    # command runs with the WORKTREE as cwd and an EXPLICIT
                    # environment. See ``_declared_command_env``.
                    #
                    # Per-component seam: when the task selected a component,
                    # the cwd is the component's declared directory instead —
                    # ``flutter test`` needs the package root, and ``cd app &&
                    # …`` inside the command string is invisible to the
                    # snapshot reader and to anyone auditing the receipt.
                    # ``_component_run_cwd`` returns the worktree UNCHANGED
                    # when no component is active.
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

                # TASK-FIX-BSEXTRAS01 (absence-of-failure-is-not-success):
                # distinguish "the oracle ran and the Player's tests failed"
                # from "the oracle never ran". When the pinned interpreter has
                # no pytest (``python -m pytest`` → "No module named pytest")
                # or pytest collected zero tests (exit code 5), there is NO
                # signal about the Player's work — it must surface as
                # signal_absent (UNKNOWN), never a Player test failure.
                # Narrowly scoped to the runner itself: a Player test importing
                # a missing *app* module ("No module named myapp") still fails
                # as a real defect.
                signal_absent = False
                # TASK-AB-NPDET01: a non-Python deterministic run classifies
                # absence stack-awarely on BOTH the success and failure branch —
                # the exit-0 zero-test guard. A runner that exits 0 having
                # executed ZERO tests (go ``[no test files]`` only; dotnet
                # "No test is available"; npm "no test specified") is an ABSENT
                # signal (UNKNOWN), never a pass; a missing toolchain (exit 127 /
                # "command not found") is ABSENT, never a Player test failure.
                # The pytest classifier below is left byte-for-byte (the
                # TASK-AB-PERTASKFG01 fix) and stays the path when no non-Python
                # stack profile is active (``_active_stack_profile is None``).
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
                    combined = (result.stdout or "") + (result.stderr or "")
                    runner_absent = "No module named pytest" in combined
                    no_tests_collected = result.returncode == 5
                    # TASK-AB-PERTASKFG01 fix #4 (absence-of-failure-is-not-success):
                    # a conftest/collection import failure means pytest could not
                    # even load the suite, so ZERO tests executed — the oracle
                    # produced NO verdict on the Player's code. That is an ABSENT
                    # signal (the test framework / its deps could not load, e.g. a
                    # missing pytest_asyncio / app dep in the bootstrap venv —
                    # exit code 2/4, not 5), NOT a Player test failure. Without
                    # this, the conftest ModuleNotFoundError was mis-recorded as
                    # "ran-and-failed" (signal_absent=False) and sent the Player
                    # after an environment error. A Player *test* that imports a missing app
                    # module still surfaces as a real failure: those report a test
                    # summary and exit 1, not a collection error.
                    collection_failed = (
                        "ImportError while loading conftest" in combined
                        or "errors during collection" in combined
                        or "error collecting" in combined
                    )
                    # TASK-ABFIX-011 (constraint 3, defence-in-depth): if our
                    # gated --timeout injection ever mis-fires (plugin vanished
                    # between probe and run), pytest exits rc-4 'unrecognized
                    # arguments: --timeout' having run ZERO tests. That is an
                    # ABSENT signal (ABFIX-010 carries it as None, fed back), never
                    # a counted Player failure — fail toward feedback. The match is
                    # narrow, so a genuine exit-1 test failure is never masked.
                    timeout_usage_error = self._is_pytest_timeout_usage_error(
                        result.returncode, combined
                    )
                    # TASK-ABFIX-012: a missing host tool (the test command itself,
                    # or a tool a test shells out to — rc 126/127 or a shell
                    # "command not found") means the oracle could not run. ABSENT
                    # signal (routes through the existing absent guard → feedback,
                    # bounded by max_turns), never a Player test failure (the
                    # false-red ABFIX-010 prevents).
                    host_substrate_gap = self._is_host_substrate_gap(
                        result.returncode, combined
                    )
                    if (
                        runner_absent
                        or no_tests_collected
                        or collection_failed
                        or timeout_usage_error
                        or host_substrate_gap
                    ):
                        signal_absent = True
                        logger.warning(
                            "Independent test oracle did not run "
                            "(returncode=%s, runner-absent=%s/no-tests-collected=%s"
                            "/collection-failed=%s/timeout-usage-error=%s"
                            "/host-substrate-gap=%s) — "
                            "treating as absent signal, not a test failure. cmd=%s",
                            result.returncode,
                            runner_absent,
                            no_tests_collected,
                            collection_failed,
                            timeout_usage_error,
                            host_substrate_gap,
                            test_cmd,
                        )

                logger.info(
                    f"Independent tests "
                    f"{'passed' if tests_passed else ('absent' if signal_absent else 'failed')} "
                    f"in {duration:.1f}s"
                )

                return self._after_isolation_fallback(
                    IndependentTestResult.from_run(
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
                    ),
                    # The command completed and has an exit code, so a
                    # fallback close-out can re-ask what that exit code
                    # really means for THIS command before ending a turn on
                    # it.
                    worktree_returncode=result.returncode,
                )

            except subprocess.TimeoutExpired:
                duration = time.time() - start_time
                logger.error(f"Test execution timed out after {self.test_timeout}s")
                # TASK-FIX-COACHTESTTO: timeout — oracle did not complete.
                return self._after_isolation_fallback(
                    IndependentTestResult.absent(
                        test_command=test_cmd,
                        test_output_summary=(
                            f"Test execution timed out after "
                            f"{self.test_timeout}s"
                        ),
                        duration_seconds=duration,
                        resolved_interpreter=self._resolved_interpreter_for(
                            test_cmd
                        ),
                    ),
                    # No exit code exists: the command never finished.
                    worktree_returncode=None,
                )
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Test execution failed: {e}")
                # TASK-FIX-COACHTESTTO: execution error before any verdict.
                return self._after_isolation_fallback(
                    IndependentTestResult.absent(
                        test_command=test_cmd,
                        test_output_summary=f"Test execution failed: {e}",
                        duration_seconds=duration,
                        resolved_interpreter=self._resolved_interpreter_for(
                            test_cmd
                        ),
                    ),
                    # No exit code exists: the command never ran to an end.
                    worktree_returncode=None,
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

    @staticmethod
    def _is_test_file_path(path: str) -> bool:
        """Heuristic: does ``path`` look like a test-file path?

        Recognises the test-file conventions enumerated in AC-006:
        - Python: ``test_*.py`` (pytest) and ``*_test.py``
        - Go: ``*_test.go``
        - C#/.NET: ``Tests/*.cs`` (path component "Tests")
        - JS/TS: ``*.test.ts`` / ``*.test.js`` / ``*.spec.ts`` / ``*.spec.js``
        """
        name = Path(path).name
        if name.startswith("test_") and name.endswith(".py"):
            return True
        if name.endswith("_test.py"):
            return True
        if name.endswith("_test.go"):
            return True
        if name.endswith(".test.ts") or name.endswith(".test.js"):
            return True
        if name.endswith(".spec.ts") or name.endswith(".spec.js"):
            return True
        # .NET Tests/*.cs
        parts = Path(path).parts
        if any(p == "Tests" for p in parts) and name.endswith(".cs"):
            return True
        return False

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _task_id_to_pattern_prefix(self, task_id: str) -> str:
        """
        Convert task ID to a pattern-matching prefix.

        Converts task IDs like "TASK-XXX-YYYY" to "task_xxx_yyyy" for
        matching against test file naming conventions.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-XXX-YYYY")

        Returns
        -------
        str
            Lowercase underscore-separated pattern prefix
        """
        return task_id.replace("-", "_").lower()

    def _find_first_checkpoint_parent(self) -> Optional[str]:
        """
        Find the parent commit of the first checkpoint for cumulative diff.

        Reads the checkpoints.json file to get the first checkpoint's commit hash,
        then returns the parent commit hash (commit~1). This is used for cumulative
        git diff to find test files created in earlier turns.

        Returns
        -------
        Optional[str]
            Parent commit hash, or None if checkpoints file not found or invalid
        """
        if not self.task_id:
            return None

        try:
            checkpoints_file = (
                self.worktree_path / ".guardkit" / "autobuild"
                / self.task_id / "checkpoints.json"
            )

            if not checkpoints_file.exists():
                logger.debug(f"No checkpoints file found at {checkpoints_file}")
                return None

            data = json.loads(checkpoints_file.read_text())
            checkpoints = data.get("checkpoints", [])

            if not checkpoints:
                logger.debug("Checkpoints file exists but contains no checkpoints")
                return None

            first_commit = checkpoints[0].get("commit_hash")
            if not first_commit:
                logger.debug("First checkpoint has no commit_hash")
                return None

            # Get parent commit (commit~1)
            result = run_git(
                ["rev-parse", f"{first_commit}~1"],
                cwd=str(self.worktree_path),
                timeout=10,
            )

            if result.returncode != 0:
                logger.debug(f"Failed to get parent commit for {first_commit}")
                return None

            return result.stdout.strip()

        except Exception as e:
            logger.debug(f"Error finding first checkpoint parent: {e}")
            return None

    def _detect_test_command(
        self,
        task_id: Optional[str] = None,
        task_work_results: Optional[Dict[str, Any]] = None,
        turn: Optional[int] = None,
    ) -> Optional[str]:
        """Choose the test command, and record where the choice came from.

        The choosing itself is :meth:`_detect_test_command_ladder`, unchanged.
        This wrapper exists only so every caller gets
        :attr:`_test_command_source` filled in alongside the command — the
        work leg puts it in the Phase-4 record so a person reading a red leg
        can see which command ran and why that one.
        """
        self._test_command_source = None
        command = self._detect_test_command_ladder(
            task_id, task_work_results=task_work_results, turn=turn
        )
        if command is not None and self._test_command_source is None:
            # A rung that did not name itself: everything below the
            # declaration is a detection from the files in the worktree.
            self._test_command_source = (
                "detected from the worktree (task-specific test files or "
                "stack markers)"
            )
        return command

    def ran_the_repository_declaration(self) -> bool:
        """Whether the last chosen test command came from the repository's own
        declaration rather than from a guess.

        The work leg asks this before it judges a run by ZERO NET-NEW: a
        declared command is normally the repository's WHOLE suite, and only a
        whole-suite run can be red for somebody else's defect. A run of the
        task's own test files is judged exactly as it always was — every
        failure in it belongs to this task.
        """
        return bool(
            self._test_command_source
            and self._test_command_source.startswith(DECLARED_COMMAND_SOURCE)
        )

    def test_command_source(self) -> Optional[str]:
        """Where the last chosen test command came from, in plain words.

        ``None`` before any command has been chosen, or when no command could
        be found at all.
        """
        return self._test_command_source

    def _detect_test_command_ladder(
        self,
        task_id: Optional[str] = None,
        task_work_results: Optional[Dict[str, Any]] = None,
        turn: Optional[int] = None,
    ) -> Optional[str]:
        """
        Auto-detect the test command based on project files.

        When task_id is provided, attempts to find task-specific test files
        using sources in priority order:
        1. Primary: Extract test files from task_work_results (already in memory)
        2. Secondary: Task-ID glob pattern on disk
        3. Tertiary: Cumulative git diff from task's first checkpoint
        4. Quaternary: Extract test files from completion_promises
        5. Quinary: Scan prior player_turn_N.json reports for accumulated test files

        If no task-specific tests are found and task_id was provided,
        returns None to signal that independent verification should be skipped.
        This is essential for shared worktrees where parallel tasks may have
        tests with unmet dependencies.

        Parameters
        ----------
        task_id : Optional[str]
            Task identifier for task-specific test filtering. If provided,
            the method will search for test files matching the task ID
            pattern. If no matching tests found, returns None to skip
            verification (prevents running all tests from parallel tasks).
        task_work_results : Optional[Dict[str, Any]]
            Task-work results dict (already loaded in memory). Used as
            primary source for test file detection via files_created
            and files_modified lists.
        turn : Optional[int]
            Current turn number (1-based). When provided, enables the quinary
            fallback that scans prior player_turn_N.json files to find test
            files accumulated from earlier turns. On iterative fix turns the
            Player modifies source files without re-creating the test file, so
            files_created/files_modified in the current results will not contain
            the test file.

        Returns
        -------
        Optional[str]
            Detected test command, or None if task_id was provided but no
            task-specific tests were found (signals to skip verification)
        """
        # TASK-AB-NPDET01: clear any stack profile from a prior call on a reused
        # validator; only the non-Python registry branch below sets it.
        self._active_stack_profile = None
        # TS-lane D.1b: same discipline for the loud-absence marker.
        self._detection_absence = None

        # ---- the per-component seam: the FIRST rung, and the only one -----
        # A task that names a component has told us which product it is
        # working on. Its component's declared command is THE oracle — the
        # Python task-specific rungs below must not pre-empt it (they would
        # judge Dart work with whatever ``.py`` files happened to be touched),
        # and the marker ladder must not follow it (that is the guess this
        # declaration replaces). A task WITHOUT a component never enters here,
        # so every existing repo's ladder is byte-unchanged.
        if self._component:
            if self._component_absence is not None:
                self._detection_absence = self._component_absence
                logger.error(self._detection_absence)
                return None
            declared = self._declared_test_command()
            if declared is None:
                self._detection_absence = self._describe_detection_absence()
                logger.error(self._detection_absence)
                return None
            self._active_stack_profile = self._declared_stack_profile(declared)
            self._test_command_source = (
                f"{DECLARED_COMMAND_SOURCE} (component {self._component!r})"
            )
            logger.info(
                "Test command for %s from the DECLARED component %r "
                "(.guardkit/config.yaml `toolchain.components.%s.test`, pinned "
                "pre-turn-1): %s [cwd=%s]",
                task_id or self.task_id,
                self._component,
                self._component,
                declared,
                self._component_toolchain.cwd,
            )
            return declared

        # ---- THE REPOSITORY'S OWN DECLARATION — above every guess --------
        #
        # RICH'S RULING, 2026-09-09: a leg runs what the repository declares.
        #
        # This rung used to sit BELOW the task-specific ladder, so a task that
        # had written a test file of its own was judged by a bare
        # ``pytest <that file>`` even in a repository that had said, in
        # ``.guardkit/config.yaml``, exactly how its tests are to be run. On
        # api_test that declaration is ``qa/run-suite.sh``, which stands up a
        # throwaway PostgreSQL, runs the suite against it and takes it down.
        # The consequence was a fork: a database test failed inside the work
        # leg and passed at the merge-ready checkpoint, which has always
        # honoured the declaration. Twenty-six attempts at one fix journey
        # died in that fork.
        #
        # WHAT IT COSTS, said plainly: a declared command is usually the
        # repository's WHOLE suite, where the old guess ran only the task's
        # own tests. So a leg can now go red for a defect somebody else left
        # behind, and in a parallel wave a sibling task's failure lands on
        # this task's leg. That is the price of running what the repository
        # declared, and it is the same price the merge-ready checkpoint has
        # always charged. The declaration is not a guess; the ladder below it
        # is. A repository that declares nothing reaches the next line with
        # everything exactly as it was.
        #
        # ONE RULE, ONE READER: the command comes from the pre-turn-1 snapshot
        # of the repository's ``toolchain:`` block, parsed by
        # ``toolchain_declaration.load_toolchain_declaration`` — the same
        # parse the merge check reads through
        # ``completion_verification.declared_toolchain_test_command``. The
        # snapshot, not the live file, because the live file sits inside the
        # tree the model edits (design §B.4): a model that could rewrite its
        # own test command could green itself.
        declared = self._declared_test_command()
        if declared is not None:
            self._active_stack_profile = self._declared_stack_profile(declared)
            self._test_command_source = DECLARED_COMMAND_SOURCE
            logger.info(
                "Test command%s from the repo's DECLARED toolchain "
                "(.guardkit/config.yaml `toolchain.test`, pinned pre-turn-1): "
                "%s%s",
                f" for {task_id}" if task_id else "",
                declared,
                " [parallel wave: declaration honoured, no specialist "
                "hand-off]" if self.is_parallel else "",
            )
            return declared

        # Try task-specific filtering first (for shared worktrees)
        if task_id:
            # Primary: extract test files from task_work_results (already in memory)
            if task_work_results:
                cmd = self._detect_tests_from_results(task_work_results)
                if cmd:
                    return cmd

            # Fallback: task-ID glob pattern on disk (recursive)
            task_prefix = self._task_id_to_pattern_prefix(task_id)
            # Pattern: tests/**/test_{task_prefix}*.py (recursive into subdirectories)
            pattern = f"tests/**/test_{task_prefix}*.py"

            logger.debug(f"Searching for task-specific tests: pattern={pattern}")
            matching_files = list(self.worktree_path.glob(pattern))

            if matching_files:
                # Deduplicate and convert to relative paths
                unique_files = list(set(matching_files))
                rel_files = [
                    str(f.relative_to(self.worktree_path)) for f in sorted(unique_files)
                ]
                # Drop pytest-bdd glue files (TASK-FIX-CC-BDD).
                rel_files = self._filter_bdd_glue_files(rel_files)
                if rel_files:
                    files_str = " ".join(rel_files)
                    logger.info(
                        f"Task-specific tests detected for {task_id}: "
                        f"{len(rel_files)} file(s)"
                    )
                    logger.debug(f"Test files: {files_str}")
                    return f"pytest {files_str} -v --tb=short"

            # No task-specific tests found via any method
            logger.info(
                f"No task-specific tests found for {task_id}, skipping independent verification. "
                f"Glob pattern tried: {pattern}"
            )

            # Tertiary fallback: cumulative git diff from task's first checkpoint
            # to HEAD. This finds test files created in any previous turn that
            # are now invisible because checkpoint commits moved HEAD forward.
            # Safe for shared worktrees: only includes files changed during
            # THIS task's checkpoint range.
            try:
                first_parent = self._find_first_checkpoint_parent()
                if first_parent:
                    diff_result = run_git(
                        ["diff", "--name-only", first_parent, "HEAD"],
                        cwd=str(self.worktree_path),
                        timeout=10,
                    )
                    if diff_result.returncode == 0:
                        changed_files = diff_result.stdout.strip().split("\n")
                        test_files = [
                            f for f in changed_files
                            if f.strip() and (
                                (Path(f).name.startswith("test_") and f.endswith(".py"))
                                or f.endswith("_test.py")
                            ) and (self.worktree_path / f).exists()
                        ]
                        if test_files:
                            # Drop pytest-bdd glue files (TASK-FIX-CC-BDD).
                            test_files = self._filter_bdd_glue_files(
                                sorted(test_files)
                            )
                        if test_files:
                            files_str = " ".join(test_files)
                            logger.info(
                                f"Found test files via cumulative diff for "
                                f"{task_id}: {len(test_files)} file(s)"
                            )
                            return f"pytest {files_str} -v --tb=short"
            except Exception as e:
                logger.debug(f"Cumulative diff fallback failed: {e}")

            # Quaternary fallback: extract test files from completion_promises.
            # When the Player references test files in completion_promises
            # (e.g., pre-existing test files from scaffolding tasks), those
            # files may not appear in files_created/files_modified or git diff
            # because the Player didn't create or modify them this turn.
            if task_work_results:
                try:
                    promises = task_work_results.get("completion_promises", [])
                    promise_test_files = set()
                    for promise in promises:
                        test_file = promise.get("test_file")
                        if test_file and isinstance(test_file, str):
                            p = Path(test_file)
                            if (
                                (p.name.startswith("test_") and p.name.endswith(".py"))
                                or p.name.endswith("_test.py")
                            ) and (self.worktree_path / test_file).exists():
                                promise_test_files.add(test_file)

                    if promise_test_files:
                        # Drop pytest-bdd glue files (TASK-FIX-CC-BDD).
                        promise_files_filtered = self._filter_bdd_glue_files(
                            sorted(promise_test_files)
                        )
                        if promise_files_filtered:
                            files_str = " ".join(promise_files_filtered)
                            logger.info(
                                f"Found test files via completion_promises for "
                                f"{task_id}: {len(promise_files_filtered)} file(s)"
                            )
                            return f"pytest {files_str} -v --tb=short"
                except Exception as e:
                    logger.debug(f"Completion promises test extraction failed: {e}")

            # Quinary fallback: scan prior player_turn_N.json reports for
            # accumulated test files (TASK-FIX-70F3).
            # On iterative fix turns (turn >= 2), the Player modifies source
            # files but does not re-create or re-modify the test file, so
            # files_created/files_modified in the current results won't include
            # it. Prior player reports *do* contain the test file in their
            # files_created/files_modified, making them the reliable source of
            # accumulated test file knowledge across turns.
            # Accumulation is per-task (task_id required) to avoid bleeding
            # between tasks sharing a worktree.
            if turn and self.task_id:
                for prev_turn in range(turn - 1, 0, -1):
                    prev_path = TaskArtifactPaths.player_report_path(
                        self.task_id, prev_turn, self.worktree_path
                    )
                    if prev_path.exists():
                        try:
                            prior_results = json.loads(prev_path.read_text())
                            cmd = self._detect_tests_from_results(prior_results)
                            if cmd:
                                logger.info(
                                    "Test files found via player_turn_%d.json for %s",
                                    prev_turn,
                                    self.task_id,
                                )
                                return cmd
                        except Exception as e:
                            logger.debug(
                                f"Failed to read player_turn_{prev_turn}.json: {e}"
                            )

            # TASK-AB-NPDET01: no Python task-specific tests were found. Before
            # deferring to the LLM ``test-orchestrator`` specialist (the
            # historic non-Python path, which can hang on a tool-call-shy model),
            # try a deterministic non-Python whole-suite command (dotnet/npm/go).
            #
            # TS-lane D.1b: THE DECLARATION WINS — over the marker guess
            # below, and in PARALLEL WAVES TOO. It is now settled one rung
            # higher still (above the task-specific ladder, at the top of this
            # method, on Rich's 2026-09-09 ruling), so anything reaching here
            # has no declaration at all and the marker guess is all there is.
            #
            # GUARD: a whole-suite command runs SIBLING tasks' tests too, so in a
            # parallel wave it would attribute their failures to this task
            # (false-red). Only take over when this is a SINGLE-task wave
            # (``not self.is_parallel``); a parallel wave returns None below and
            # keeps today's LLM-specialist fallback. Mirrors the runtime-parity
            # ``wave_size > 1`` deferral.
            if not self.is_parallel:
                profile = detect_stack_profile(self.worktree_path)
                if profile is not None:
                    self._active_stack_profile = profile
                    logger.info(
                        "No Python task-specific tests for %s; running "
                        "deterministic %s suite: %s",
                        task_id,
                        profile.stack,
                        profile.whole_suite_command,
                    )
                    return profile.whole_suite_command
            elif detect_stack_profile(self.worktree_path) is not None:
                logger.info(
                    "Non-Python stack detected for %s but wave_size>1 "
                    "(parallel wave); deferring to the test-orchestrator "
                    "specialist to avoid running sibling tasks' tests.",
                    task_id,
                )

            return None

        # TS-lane D.1b: the DECLARATION outranks every marker guess below
        # it — and is now read at the top of this method, above the
        # task-specific ladder too, so a repository reaching this line has
        # declared nothing and the marker guesses are all there is.

        # Fallback to original detection logic
        # Check for Python projects
        if (self.worktree_path / "pytest.ini").exists():
            return "pytest tests/ -v --tb=short"
        if (self.worktree_path / "pyproject.toml").exists():
            return "pytest tests/ -v --tb=short"
        if (self.worktree_path / "requirements.txt").exists():
            return "pytest tests/ -v --tb=short"

        # Check for Node.js projects
        if (self.worktree_path / "package.json").exists():
            return "npm test"

        # Check for .NET projects
        csproj_files = list(self.worktree_path.glob("*.csproj"))
        if csproj_files:
            return "dotnet test"

        # TS-lane D.1b: THE PYTEST DEFAULT IS DELETED.
        #
        # This was the last unconditional stack assumption on the verdict path
        # ("Could not detect project type, defaulting to pytest" →
        # ``pytest tests/ -v --tb=short``). In a repo with no pytest it ran a
        # command that could not possibly produce a verdict, and the shrug went
        # into the log at WARNING while the build carried on.
        #
        # It is replaced by a LOUD ABSENCE, not by a quieter guess: an
        # instrument fault naming the missing declaration and every rung of the
        # ladder that came up empty. ``run_independent_tests`` turns this into
        # ``signal_absent`` (UNKNOWN) — never a pass, never a Player test
        # failure (``absence-of-failure-is-not-success.md``).
        self._detection_absence = self._describe_detection_absence()
        logger.error(self._detection_absence)
        return None

    # ------------------------------------------------------------------
    # TS-lane D.1b — the declaration's three helpers
    # ------------------------------------------------------------------

    def _declared_test_command(self) -> Optional[str]:
        """Return the declared ``test`` command for THIS TASK, or ``None``.

        Reads ONLY the pre-turn-1 snapshot resolved in ``__init__`` (design
        §B.4) — never the live ``<worktree>/.guardkit/config.yaml``, which the
        Player can edit.

        THE TASK'S COMPONENT IS RESOLVED FIRST. A task that named a component
        gets that component's ``test:`` and nothing else; a task that named
        none gets the root block, exactly as before the components field
        existed.

        THE MERGE CHECK'S TWIN. ``completion_verification`` asks the same
        question of a merge target through
        ``declared_toolchain_test_command`` / ``resolve_verify_command``, and
        both roads end at the one parser,
        ``toolchain_declaration.load_toolchain_declaration``. They differ in
        WHICH copy of the file they read, and deliberately: the merge check
        reads the merged repository, while this reads the pre-turn-1 snapshot,
        because the worktree copy is inside the tree the model edits. If the
        rule ever needs changing, change it in the parser — never twice.
        """
        if self._component_toolchain is not None:
            return self._component_toolchain.test or None
        if self._component:
            # Named-but-undeclared: never the root command (see __init__).
            return None
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
        repo-relative ``cwd:`` is applied under ``base`` (the worktree, or the
        parallel-wave isolated copy of it), with the containment re-check that
        catches a symlink no schema can see.

        A containment failure RAISES after a loud error rather than degrading
        to ``base``: silently relocating a refused run to the worktree root
        would execute the component's command against the wrong product. The
        raise is caught by ``run_independent_tests`` / ``_run_isolated_tests``
        and becomes an ABSENT (UNKNOWN) result — never a pass, never a Player
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

    def _describe_component_absence(self, component: str) -> str:
        """The loud message for a task naming an undeclared component."""
        declared = (
            ", ".join(self._toolchain.component_names)
            if self._toolchain is not None and self._toolchain.component_names
            else "<none>"
        )
        root_state = (
            "no `toolchain:` block is pinned for this task"
            if self._toolchain is None
            else "the pinned `toolchain:` block declares no such component"
        )
        return (
            f"INSTRUMENT FAULT: task {self.task_id or 'this run'} selects "
            f"`component: {component}` but {root_state}. Declared components: "
            f"{declared}.\n"
            "The oracle is ABSENT (UNKNOWN) — this is NOT a test failure and "
            "NOT a pass. The root `test:` command is DELIBERATELY NOT used as "
            "a fallback: judging one component's work with another's suite is "
            "the false verdict this seam exists to remove.\n"
            "FIX: declare the component, or correct the task's `component:` "
            "key.\n"
            "  # <repo>/.guardkit/config.yaml\n"
            "  toolchain:\n"
            "    components:\n"
            f"      {component}:\n"
            '        cwd:  "app"\n'
            '        test: "flutter test"'
        )

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

    def _declared_command_env(
        self, git_ceiling: Optional[Path] = None
    ) -> Dict[str, str]:
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
        return _checker_declared_env(self, git_ceiling)

    def _describe_detection_absence(self) -> str:
        """Build the actionable message for the deleted pytest default.

        Names the missing declaration FIRST (it is the fix), then every rung
        of the detection ladder that came up empty, so the reader never has to
        reconstruct what was tried.
        """
        # Per-component seam: a selected-but-testless component gets its own
        # message and STOPS — the ladder below is about the root component and
        # naming its empty rungs here would suggest a fallback that must never
        # happen.
        if self._component and self._component_toolchain is not None:
            return (
                "INSTRUMENT FAULT: no test command could be resolved for "
                f"{self.task_id or 'this run'} in {self.worktree_path}. "
                "The independent-test oracle is ABSENT (UNKNOWN) — this is NOT "
                "a test failure and NOT a pass.\n"
                f"  1. DECLARATION: the task selects `component: "
                f"{self._component}` (cwd={self._component_toolchain.cwd!r}) "
                "and that component declares no `test:` command.\n"
                "  2. The root `test:` is NOT used as a fallback, by design — "
                "one component's suite is not a verdict on another's work.\n"
                "FIX: declare the component's own test command, e.g.\n"
                "  # <repo>/.guardkit/config.yaml\n"
                "  toolchain:\n"
                "    components:\n"
                f"      {self._component}:\n"
                f'        cwd:  "{self._component_toolchain.cwd}"\n'
                '        test: "flutter test"'
            )
        declared_state = (
            "no `toolchain:` block found in <repo>/.guardkit/config.yaml"
            if self._toolchain is None
            else "a `toolchain:` block exists but declares no `test:` command"
        )
        return (
            "INSTRUMENT FAULT: no test command could be resolved for "
            f"{self.task_id or 'this run'} in {self.worktree_path}. "
            "The independent-test oracle is ABSENT (UNKNOWN) — this is NOT a "
            "test failure and NOT a pass.\n"
            f"  1. DECLARATION: {declared_state}.\n"
            "  2. Python markers: no pytest.ini, no pyproject.toml, no "
            "requirements.txt at the worktree root.\n"
            "  3. Node marker: no package.json at the worktree root.\n"
            "  4. .NET marker: no *.csproj at the worktree root.\n"
            "FIX: declare the command the repo actually uses, e.g.\n"
            "  # <repo>/.guardkit/config.yaml\n"
            "  toolchain:\n"
            '    test: "npm test"\n'
            "(Until TS-lane D.1b this fell through to "
            '`pytest tests/ -v --tb=short` with a logged shrug, which ran a '
            "command the repo may not even have. A guessed oracle is worse "
            "than a named absence.)"
        )

    def _load_collect_ignore_glob(self) -> List[str]:
        """Load ``collect_ignore_glob`` patterns from the root ``conftest.py``.

        Uses AST parsing so the file is never executed. Returns an empty list
        when the file does not exist, contains no ``collect_ignore_glob``
        assignment, or cannot be parsed.

        Returns
        -------
        List[str]
            Glob patterns identical to those pytest would use for exclusion.
        """
        conftest = self.worktree_path / "conftest.py"
        if not conftest.exists():
            return []
        try:
            tree = ast.parse(conftest.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            logger.debug("Could not parse conftest.py; skipping collect_ignore_glob")
            return []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "collect_ignore_glob":
                    if isinstance(node.value, ast.List):
                        patterns = []
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                patterns.append(elt.value)
                        return patterns
        return []

    def _detect_tests_from_results(
        self, task_work_results: Dict[str, Any]
    ) -> Optional[str]:
        """
        Primary test detection: find test files from task_work_results.

        Extracts test files (matching ``test_*.py`` or ``*_test.py``) from
        the files_created/files_modified lists in task_work_results. Only
        returns files that actually exist in the worktree. Files matching
        any ``collect_ignore_glob`` pattern from the root ``conftest.py``
        are excluded so they are not passed as explicit pytest arguments
        (which would bypass pytest's automatic exclusion).

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Task-work results dict containing files_created and files_modified

        Returns
        -------
        Optional[str]
            pytest command targeting discovered test files, or None
        """
        ignore_patterns = self._load_collect_ignore_glob()

        test_files = []
        for file_list_key in ("files_created", "files_modified"):
            for filepath in task_work_results.get(file_list_key, []):
                normalized = self._normalize_to_relative(filepath)
                basename = Path(normalized).name
                if (basename.startswith("test_") and basename.endswith(".py")) or basename.endswith("_test.py"):
                    full_path = self.worktree_path / normalized
                    if full_path.exists():
                        test_files.append(str(normalized))

        if not test_files:
            logger.debug("No test files found in task_work_results")
            return None

        # Filter files matching collect_ignore_glob patterns (fnmatch, same as pytest)
        if ignore_patterns:
            filtered = []
            for tf in test_files:
                matched = any(fnmatch.fnmatch(tf, pat) for pat in ignore_patterns)
                if matched:
                    pattern = next(pat for pat in ignore_patterns if fnmatch.fnmatch(tf, pat))
                    logger.debug(
                        f"Excluding test file '{tf}' (matches collect_ignore_glob pattern '{pattern}')"
                    )
                else:
                    filtered.append(tf)
            test_files = filtered

        if not test_files:
            logger.debug("All detected test files were excluded by collect_ignore_glob")
            return None

        # Drop pytest-bdd glue files (TASK-FIX-CC-BDD); they require
        # task-tag-scoped execution via run_bdd_for_task, not unscoped pytest.
        test_files = self._filter_bdd_glue_files(test_files)
        if not test_files:
            logger.debug(
                "All detected test files were pytest-bdd glue; "
                "deferring to run_bdd_for_task / bdd_results gate"
            )
            return None

        # Deduplicate and build command
        unique_files = sorted(set(test_files))
        files_str = " ".join(unique_files)
        logger.info(
            f"Task-specific tests detected via task_work_results: "
            f"{len(unique_files)} file(s)"
        )
        logger.debug(f"Test files (from task_work_results): {files_str}")
        return f"pytest {files_str} -v --tb=short"

    def _normalize_to_relative(self, filepath: str) -> str:
        """Normalize a filepath to be relative to the worktree.

        Handles both absolute paths (strips worktree prefix) and
        relative paths (returned as-is).
        """
        p = Path(filepath)
        if p.is_absolute():
            try:
                return str(p.relative_to(self.worktree_path))
            except ValueError:
                return filepath
        return filepath

    def _filter_bdd_glue_files(self, test_files: List[str]) -> List[str]:
        """Drop pytest-bdd glue files from the independent_tests pytest cmd.

        Defect: an unscoped ``pytest <files>`` invocation that includes
        pytest-bdd glue collects every scenario in the matching ``.feature``
        file, including scenarios tagged for downstream peer tasks. Their
        unbound steps surface as ``FAILED``, the ``tests_passed`` /
        ``scenarios_failed > 0`` gates fire, and the Coach rejects on a
        deterministic, retry-immune signal. See TASK-FIX-CC-BDD and the
        FEAT-39E1 post-mortem.

        R1 DE-WIRE (Rich 08-14): the tag-scoped BDD oracle that used to own
        glue execution is removed — nothing executes glue at all now. This
        filter STAYS so the independent-tests command never collects
        pytest-bdd glue (unscoped collection would newly EXECUTE scenarios,
        exactly what R1 removes). The glue heuristic is inlined below so
        bdd_runner.py is left unreferenced until R2 deletes both together.

        Parameters
        ----------
        test_files : List[str]
            Test file paths relative to ``self.worktree_path``.

        Returns
        -------
        List[str]
            ``test_files`` with pytest-bdd glue removed (preserves order).
        """
        plain: List[str] = []
        excluded: List[str] = []
        for tf in test_files:
            full = self.worktree_path / tf
            if self._is_bdd_glue_file(full):
                excluded.append(tf)
            else:
                plain.append(tf)
        if excluded:
            logger.info(
                "TASK-FIX-CC-BDD: Excluded %d pytest-bdd glue file(s) from "
                "independent_tests pytest cmd; BDD execution is retired "
                "(R1 de-wire). Excluded: %s",
                len(excluded),
                excluded,
            )
        return plain

    @staticmethod
    def _is_bdd_glue_file(file_path: Any) -> bool:
        """Return True when the file appears to be pytest-bdd glue.

        R1 DE-WIRE (Rich 08-14): inlined from ``bdd_runner.is_bdd_glue_file``
        so the retired ``bdd_runner.py`` module is unreferenced from
        production code (R2 deletes it). Detection is a cheap text scan for
        pytest-bdd v8 import signatures: ``from pytest_bdd import``,
        ``import pytest_bdd``, or ``pytest_bdd.scenarios(``. Returns
        ``False`` for missing files, non-``.py`` files, and files that
        cannot be read.
        """
        try:
            p = Path(file_path)
        except (TypeError, ValueError):
            return False
        if not p.is_file() or p.suffix != ".py":
            return False
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        return (
            "pytest_bdd.scenarios(" in text
            or "from pytest_bdd import" in text
            or "import pytest_bdd" in text
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
