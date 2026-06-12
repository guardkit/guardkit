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
import subprocess
import sys
import time
from contextlib import aclosing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    HonestyVerification,
    _resolve_venv_python,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.docker_fixtures import (
    get_container_name,
    get_env_exports,
    get_start_commands,
    is_known_service,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.phase_specialists import (
    PHASE_DESCRIPTIONS,
    detect_stack_template,
    render_missing_phase_list,
)
from guardkit.orchestrator.schemas import STATUS_ALIASES
from guardkit.models.task_types import TaskType, QualityGateProfile, get_profile, TASK_TYPE_ALIASES

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
from guardkit.orchestrator.sdk_utils import check_assistant_message_error

# Optional coach context integration (TASK-SC-009)
try:
    from guardkit.planning.coach_context_builder import build_coach_context
    from guardkit.knowledge.graphiti_client import get_graphiti
    ARCH_CONTEXT_AVAILABLE = True
except ImportError:
    ARCH_CONTEXT_AVAILABLE = False
    build_coach_context = None
    get_graphiti = None

logger = logging.getLogger(__name__)

# ============================================================================
# BDD Factory Bridge — wire guardkitfactory.bdd into the Coach evidence path
# ============================================================================
#
# TASK-BDDW-001: Replace the legacy pytest-hardcoded bdd_runner.py path in the
# Coach evidence path with guardkitfactory's plugin-discovery subsystem.
#
# The bridge uses a lazy import (try/except ImportError) so that
# ``pip install guardkit-py`` without the ``[autobuild]`` extra still works.
# When guardkitfactory is unavailable, the Coach falls back to the Player's
# self-reported ``bdd_results`` (legacy behaviour).
#
# Mapping: BDDRunResult (factory) → bundle.bdd dict (legacy shape)
#
#   BDDRunResult.scenarios_attempted  → bundle.bdd["scenarios_attempted"]
#   BDDRunResult.scenarios_passed     → bundle.bdd["scenarios_passed"]
#   BDDRunResult.scenarios_failed     → bundle.bdd["scenarios_failed"]
#   BDDRunResult.scenarios_pending    → bundle.bdd["scenarios_pending"]
#   BDDRunResult.failures             → bundle.bdd["failures"]
#   BDDRunResult.pending              → bundle.bdd["pending"]
#   BDDRunResult.feature_files        → bundle.bdd["feature_files"]
#
# Key contract: ``scenarios_attempted`` is non-Optional on BDDRunResult and
# must be preserved verbatim for the absence-of-failure gate. A value of 0
# means "no scenarios ran" (ABSENT SIGNAL), NOT "zero failures = pass".

# StackProfile values consumed by guardkitfactory.bdd.discover().
# Mapped from the worktree's project.template string.
_STACK_PROFILE_MAP: Dict[str, str] = {
    "python": "python",
    "fastapi-python": "python",
    "django-python": "python",
    "flask-python": "python",
    ".net": "dotnet",
    "aspnet-core": "dotnet",
    "csharp": "dotnet",
    "node-js": "javascript",
    "javascript": "javascript",
    "typescript": "javascript",
}
"""Mapping from ``project.template`` to ``StackProfile`` string."""


def _detect_stack_profile(workspace_root: Optional[Path]) -> Optional[str]:
    """Detect the stack profile from the worktree's template string.

    Parameters
    ----------
    workspace_root : Optional[Path]
        Root of the worktree. Used to find ``.claude/settings.json``.

    Returns
    -------
    Optional[str]
        A ``StackProfile``-compatible string (``"python"``, ``"dotnet"``,
        ``"javascript"``) or ``None`` when the template is unknown.
    """
    template = detect_stack_template(workspace_root)
    if template is None:
        return None
    return _STACK_PROFILE_MAP.get(template)


def _map_bdd_run_result_to_bundle(
    run_result: "BDDRunResult",
) -> Dict[str, Any]:
    """Map a ``BDDRunResult`` into the legacy ``bundle.bdd`` dict shape.

    Preserves ``scenarios_attempted`` verbatim — never coerces a missing key
    to 0. This is critical for the absence-of-failure gate: when
    ``scenarios_attempted == 0``, the Coach must treat it as ABSENT SIGNAL,
    not as a silent pass.

    Parameters
    ----------
    run_result : BDDRunResult
        Result from the factory BDD plugin.

    Returns
    -------
    Dict[str, Any]
        A dict with keys: ``scenarios_attempted``, ``scenarios_passed``,
        ``scenarios_failed``, ``scenarios_pending``, ``failures``,
        ``pending``, ``feature_files``.
    """
    # Import here to avoid circular import at module level.
    # BDDRunResult is imported lazily from guardkitfactory.
    from dataclasses import asdict

    failures = run_result.failures
    pending = run_result.pending

    # Convert FailureDetail/PendingDetail to dicts if they are dataclass instances.
    failure_dicts: List[Dict[str, Any]] = []
    for f in failures:
        if hasattr(f, "asdict") or hasattr(f, "_asdict"):
            failure_dicts.append(asdict(f))
        elif isinstance(f, dict):
            failure_dicts.append(f)
        else:
            failure_dicts.append({
                "scenario_name": getattr(f, "scenario_name", "<unknown>"),
                "failing_step": getattr(f, "failing_step", ""),
                "reason": getattr(f, "reason", ""),
            })

    pending_dicts: List[Dict[str, Any]] = []
    for p in pending:
        if hasattr(p, "asdict") or hasattr(p, "_asdict"):
            pending_dicts.append(asdict(p))
        elif isinstance(p, dict):
            pending_dicts.append(p)
        else:
            pending_dicts.append({
                "scenario_name": getattr(p, "scenario_name", "<unknown>"),
                "pending_step": getattr(p, "pending_step", ""),
            })

    return {
        "scenarios_attempted": run_result.scenarios_attempted,
        "scenarios_passed": run_result.scenarios_passed,
        "scenarios_failed": run_result.scenarios_failed,
        "scenarios_pending": run_result.scenarios_pending,
        "failures": failure_dicts,
        "pending": pending_dicts,
        "feature_files": list(run_result.feature_files),
    }


# Lazy import of guardkitfactory BDD plugin subsystem.
# The import is guarded so that ``pip install guardkit-py`` without
# ``[autobuild]`` still works — Coach falls back to Player-reported
# bdd_results when the factory is unavailable.
try:
    from guardkitfactory.bdd import (
        BDDRunResult,
        discover,
    )
    from guardkitfactory.bdd.plugin import StackProfile

    _FACTORY_AVAILABLE = True
except ImportError:
    BDDRunResult = None  # type: ignore[misc,assignment]
    discover = None  # type: ignore[misc,assignment]
    StackProfile = None  # type: ignore[misc,assignment]
    _FACTORY_AVAILABLE = False

# Module-level cache for the factory import status.
# Re-checked at runtime for each Coach invocation so that a late-installed
# guardkitfactory (e.g. via a post-gather pip install) is picked up.
_factory_available_cache: Optional[bool] = None


def _is_factory_available() -> bool:
    """Return True when the guardkitfactory BDD plugin subsystem is importable.

    Uses a module-level cache that is invalidated on each call to
    ``gather_evidence`` (see the ``_reset_factory_cache`` helper).
    """
    global _factory_available_cache
    if _factory_available_cache is not None:
        return _factory_available_cache
    _factory_available_cache = _FACTORY_AVAILABLE
    return _FACTORY_AVAILABLE


def _reset_factory_cache() -> None:
    """Invalidate the factory availability cache.

    Called at the start of each ``gather_evidence`` invocation so that
    a late-installed guardkitfactory is picked up on subsequent runs.
    """
    global _factory_available_cache
    _factory_available_cache = None


def _run_factory_bdd(
    worktree_path: Path,
    stack_profile: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Discover and run the BDD plugin for the given stack profile.

    Uses ``guardkitfactory.bdd.discover(stack_profile)`` to find the plugin,
    invokes it to get a ``BDDRunResult``, and maps the result into the legacy
    ``bundle.bdd`` dict shape.

    Parameters
    ----------
    worktree_path : Path
        Root of the worktree containing the BDD scenarios.
    stack_profile : Optional[str]
        Detected stack profile (``"python"``, ``"dotnet"``, ``"javascript"``).

    Returns
    -------
    Optional[Dict[str, Any]]
        A ``bundle.bdd``-shaped dict, or ``None`` when the factory is
        unavailable, the stack profile is unknown, or discovery fails.
    """
    if not _is_factory_available():
        logger.debug(
            "BDD factory bridge: guardkitfactory not available; "
            "falling back to Player-reported bdd_results.",
        )
        return None

    if stack_profile is None:
        logger.debug(
            "BDD factory bridge: no stack profile detected; "
            "falling back to Player-reported bdd_results.",
        )
        return None

    # Guard against StackProfile being None (factory not importable).
    if StackProfile is None:
        return None

    try:
        plugin = discover(stack_profile)
        if plugin is None:
            logger.debug(
                "BDD factory bridge: no plugin discovered for stack %s; "
                "falling back to Player-reported bdd_results.",
                stack_profile,
            )
            return None

        # Invoke the plugin to get BDDRunResult.
        # The plugin is responsible for running the scenarios and returning
        # a BDDRunResult with the counts-only contract.
        result = plugin.run(worktree_path)

        if result is None:
            logger.debug(
                "BDD factory bridge: plugin returned None for stack %s; "
                "falling back to Player-reported bdd_results.",
                stack_profile,
            )
            return None

        # Map BDDRunResult → bundle.bdd shape.
        return _map_bdd_run_result_to_bundle(result)

    except Exception as exc:  # noqa: BLE001 — BDD failures must not break evidence gathering
        logger.warning(
            "BDD factory bridge raised %s for stack %s; "
            "falling back to Player-reported bdd_results.",
            exc.__class__.__name__,
            stack_profile,
        )
        return None


# TASK-FIX-A7B4: Markers that satisfy a `## Seam Tests` block in a task
# description. Filename-based detection (the soft gate at
# ``_check_seam_test_recommendation``) tolerates "integration" too, but the
# blocking gate requires explicit marker decoration so a plain integration test
# can't silently satisfy a contract obligation. Match the established marker
# precedent: `seam`, `contract`, `boundary`.
_SEAM_PYTEST_MARKERS = ("seam", "contract", "boundary")

# Header pattern: any markdown header level (`#` to `######`) whose title is
# exactly "Seam Tests" (case-insensitive, trailing whitespace allowed). The
# closing `$` plus `re.MULTILINE` matches the header line in isolation so we
# don't false-trigger on prose like "## Seam Tests are useful because…".
_SEAM_TESTS_HEADER_RE = re.compile(
    r"^\s*#{1,6}\s+seam\s+tests\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_seam_tests_section(description: Optional[str]) -> Optional[str]:
    """Extract the body of a ``## Seam Tests`` markdown section.

    Returns the section body (everything between the ``## Seam Tests`` header
    and the next sibling-or-higher header, or EOF) when the section exists
    AND has non-whitespace content. Returns ``None`` for any of:

    * ``description`` is empty / None
    * No ``Seam Tests`` header is present
    * The header exists but the body is whitespace-only (empty stub block)

    The "non-empty body" rule is what TASK-FIX-A7B4 AC-001 calls "precise"
    detection: a developer who wants to acknowledge "no seam tests for this
    task" can leave the section empty (or omit it) without tripping the gate.
    """
    if not description:
        return None
    match = _SEAM_TESTS_HEADER_RE.search(description)
    if not match:
        return None
    # Find the level of the matched header so we know what closes the section.
    header_line = match.group(0)
    header_level = len(header_line.lstrip().split(" ", 1)[0])  # count of '#'

    # Body starts after the header line.
    body_start = match.end()
    rest = description[body_start:]
    # The section closes at the next header of equal-or-higher level.
    closing_re = re.compile(
        rf"^\s*#{{1,{header_level}}}\s+\S",
        re.MULTILINE,
    )
    close_match = closing_re.search(rest)
    body = rest[: close_match.start()] if close_match else rest
    if not body.strip():
        return None
    return body


# Stopwords for keyword extraction in fuzzy text matching
STOPWORDS = {
    "the", "and", "is", "or", "a", "an", "for", "with", "to", "in", "of",
    "from", "by", "on", "at", "that", "this", "are", "be", "do", "have",
    "has", "as", "if", "can", "will", "would", "could", "should", "may",
    "must", "was", "were", "been", "but", "not", "no", "all", "some",
    "any", "more", "most", "only", "than", "then", "there", "their",
    "who", "which", "when", "where", "how",
}

# ============================================================================
# Data Models
# ============================================================================


@dataclass
class QualityGateStatus:
    """
    Status of individual quality gates from task-work execution.

    Attributes
    ----------
    tests_passed : bool
        Whether all tests passed in Phase 4.5
    coverage_met : bool
        Whether coverage threshold was met
    arch_review_passed : bool
        Whether architectural review passed (score >= 60)
    plan_audit_passed : bool
        Whether plan audit had zero violations
    all_gates_passed : bool
        True only if ALL gates passed (computed)
    tests_required : bool
        Whether tests were required by task type profile
    coverage_required : bool
        Whether coverage was required by task type profile
    arch_review_required : bool
        Whether architectural review was required by task type profile
    plan_audit_required : bool
        Whether plan audit was required by task type profile
    """

    tests_passed: bool
    coverage_met: bool
    arch_review_passed: bool
    plan_audit_passed: bool
    tests_required: bool = True
    coverage_required: bool = True
    arch_review_required: bool = True
    plan_audit_required: bool = True
    all_gates_passed: bool = field(init=False)

    def __post_init__(self):
        """Compute all_gates_passed from individual gate results and requirements."""
        # Only check gates that are required
        required_gates = []
        if self.tests_required:
            required_gates.append(self.tests_passed)
        if self.coverage_required:
            required_gates.append(self.coverage_met)
        if self.arch_review_required:
            required_gates.append(self.arch_review_passed)
        if self.plan_audit_required:
            required_gates.append(self.plan_audit_passed)

        # All required gates must pass
        self.all_gates_passed = all(required_gates) if required_gates else True


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
        so the result can never read as a pass. The Coach's
        absence-of-failure guard (TASK-FIX-COACHTESTTO) treats an absent
        independent-test signal as ABSENT — surfaced as feedback, never
        approved on the Player's self-reported tests. See
        ``.claude/rules/absence-of-failure-is-not-success.md``.
    """

    tests_passed: bool
    test_command: str
    test_output_summary: str
    duration_seconds: float
    raw_output: Optional[str] = None
    signal_absent: bool = False


@dataclass
class CriterionResult:
    """
    Structured result for a single acceptance criterion.

    Attributes
    ----------
    criterion_id : str
        Unique identifier (e.g., "AC-001")
    criterion_text : str
        Full text of the acceptance criterion
    result : str
        Verification result: "verified", "rejected", or "pending"
    status : str
        Alias for result, used by _count_criteria_passed consumer
    evidence : str
        Summary of what was checked to determine the result
    """

    criterion_id: str
    criterion_text: str
    result: str  # "verified" | "rejected" | "pending"
    status: str  # same as result, for _count_criteria_passed compatibility
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "criterion_id": self.criterion_id,
            "criterion_text": self.criterion_text,
            "result": self.result,
            "status": self.status,
            "evidence": self.evidence,
            "notes": self.evidence,  # alias for _display_criteria_progress
        }


@dataclass
class RequirementsValidation:
    """
    Result of requirements satisfaction validation.

    Attributes
    ----------
    criteria_total : int
        Total acceptance criteria count
    criteria_met : int
        Number of criteria met
    all_criteria_met : bool
        True if all criteria are met
    missing : List[str]
        List of missing/unmet criteria
    criteria_results : List[CriterionResult]
        Per-criterion structured verification results
    """

    criteria_total: int
    criteria_met: int
    all_criteria_met: bool
    missing: List[str] = field(default_factory=list)
    criteria_results: List[CriterionResult] = field(default_factory=list)


@dataclass
class CoachValidationResult:
    """
    Complete result from Coach validation.

    Attributes
    ----------
    task_id : str
        Task identifier
    turn : int
        Turn number
    decision : Literal["approve", "feedback"]
        Coach's decision
    quality_gates : Optional[QualityGateStatus]
        Quality gate status (None if results not found)
    independent_tests : Optional[IndependentTestResult]
        Independent test verification result
    requirements : Optional[RequirementsValidation]
        Requirements validation result
    issues : List[Dict[str, Any]]
        List of issues if feedback
    rationale : str
        Explanation of decision
    """

    task_id: str
    turn: int
    decision: Literal["approve", "feedback", "deferred"]
    quality_gates: Optional[QualityGateStatus] = None
    independent_tests: Optional[IndependentTestResult] = None
    requirements: Optional[RequirementsValidation] = None
    issues: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    context_used: Optional[str] = None
    approved_without_independent_tests: bool = False
    is_configuration_error: bool = False
    environment_conditional_approval: bool = False
    # TASK-AB-FIX-INVAB1 AC-003: surface honesty verification result for
    # observability in coach_turn_N.json. None when verification was not
    # invoked (e.g. operator-handoff short-circuit, missing-results path).
    honesty_verification: Optional[HonestyVerification] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary for JSON serialization.

        Includes ``criteria_verification`` and ``acceptance_criteria_verification``
        fields consumed by ``_display_criteria_progress`` and ``_count_criteria_passed``
        in the AutoBuild orchestrator.

        Returns
        -------
        Dict[str, Any]
            Dictionary representation suitable for JSON
        """
        # Build per-criterion results from requirements validation
        criteria_verification: List[Dict[str, Any]] = []
        acceptance_criteria_results: List[Dict[str, Any]] = []
        if self.requirements and self.requirements.criteria_results:
            criteria_verification = [
                cr.to_dict() for cr in self.requirements.criteria_results
            ]
            acceptance_criteria_results = [
                cr.to_dict() for cr in self.requirements.criteria_results
            ]

        return {
            "task_id": self.task_id,
            "turn": self.turn,
            "decision": self.decision,
            "validation_results": {
                "quality_gates": {
                    "tests_passed": self.quality_gates.tests_passed,
                    "coverage_met": self.quality_gates.coverage_met,
                    "arch_review_passed": self.quality_gates.arch_review_passed,
                    "plan_audit_passed": self.quality_gates.plan_audit_passed,
                    "all_gates_passed": self.quality_gates.all_gates_passed,
                } if self.quality_gates else None,
                "independent_tests": {
                    "tests_passed": self.independent_tests.tests_passed,
                    "test_command": self.independent_tests.test_command,
                    "test_output_summary": self.independent_tests.test_output_summary,
                    "duration_seconds": self.independent_tests.duration_seconds,
                } if self.independent_tests else None,
                "requirements": {
                    "criteria_total": self.requirements.criteria_total,
                    "criteria_met": self.requirements.criteria_met,
                    "all_criteria_met": self.requirements.all_criteria_met,
                    "missing": self.requirements.missing,
                } if self.requirements else None,
            },
            # For _display_criteria_progress (autobuild.py:2555)
            "criteria_verification": criteria_verification,
            # For _count_criteria_passed (autobuild.py:2254)
            "acceptance_criteria_verification": {
                "criteria_results": acceptance_criteria_results,
            },
            "issues": self.issues,
            "rationale": self.rationale,
            "context_used": self.context_used,
            "approved_without_independent_tests": self.approved_without_independent_tests,
            "is_configuration_error": self.is_configuration_error,
            "environment_conditional_approval": self.environment_conditional_approval,
            # TASK-AB-FIX-INVAB1 AC-003: mirror the LLM Coach honesty schema
            # (verified, honesty_score, discrepancy_count) — see
            # installer/core/agents/autobuild-coach.md:165-184.
            "honesty_verification": (
                {
                    "verified": self.honesty_verification.verified,
                    "honesty_score": self.honesty_verification.honesty_score,
                    "discrepancy_count": len(
                        self.honesty_verification.discrepancies
                    ),
                    # TASK-FIX-1B4A (Layer 1): expose state_bridge identity
                    # resolutions for audit. Empty list when no resolutions
                    # occurred (typical case) or wiring was absent.
                    "resolved_paths": [
                        {
                            "claimed": rp.claimed,
                            "resolved_to": rp.resolved_to,
                            "task_id": rp.task_id,
                        }
                        for rp in self.honesty_verification.resolved_paths
                    ],
                }
                if self.honesty_verification is not None
                else None
            ),
        }


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

    def __init__(
        self,
        worktree_path: str,
        test_command: Optional[str] = None,
        test_timeout: int = 300,
        task_id: Optional[str] = None,
        coach_test_execution: str = "sdk",
        matching_strategy: str = "auto",
        wave_size: int = 1,
        turn: int = 1,
        peer_changed_files: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
        coach_model_name: Optional[str] = None,  # TASK-FIX-COACHBUDG01
        venv_python: Optional[str] = None,  # TASK-FIX-COACHPYENV
    ):
        """
        Initialize CoachValidator.

        Parameters
        ----------
        worktree_path : str
            Path to the git worktree where validation should execute
        test_command : Optional[str]
            Command to run tests. If None, auto-detects based on project.
        test_timeout : int
            Timeout for test execution in seconds (default: 300s)
        task_id : Optional[str]
            Task identifier for task-specific test filtering in shared worktrees.
            When provided, test detection will first look for task-specific test
            files before falling back to running the full test suite.
        coach_test_execution : str
            Test execution mode: "sdk" (default) uses Claude Agent SDK via Bash
            tool for environment parity; "subprocess" uses subprocess.run() directly.
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
        peer_changed_files : Optional[Dict[str, Iterable[str]]]
            Snapshot of files edited by other in-flight tasks in the same parallel
            wave, keyed by peer task id. When this Coach classifies a failure as
            ``parallel_contention`` (or as ``code`` in a parallel wave), it checks
            whether this task's own edits overlap with any peer's edits. Overlap
            means the failure is real source-file contention, not transient infra
            contention, so the conditional approval rule from TASK-ABFIX-005 must
            NOT fire — instead Coach returns feedback and the existing
            Player-Coach loop retries on the next turn (by which point peers have
            completed and the wave is naturally serialised). See TASK-FIX-A7B2.
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
        """
        self.worktree_path = Path(worktree_path)
        self.test_command = test_command
        self.test_timeout = test_timeout
        self.task_id = task_id
        self._coach_test_execution = coach_test_execution
        # TASK-FIX-COACHPYENV: resolve the interpreter Coach runs independent
        # tests under. Prefers the explicit bootstrap venv, then a filesystem
        # ``<worktree>/.guardkit/venv/bin/python`` recovery, else None (PATH
        # pytest / sys.executable for non-Python projects). Reuses the helper
        # already battle-tested for CoachVerifier (TASK-FIX-7A05) so the two
        # Coach verification surfaces resolve interpreters identically.
        self._configured_venv_python: Optional[str] = venv_python
        self._venv_python: Optional[Path] = _resolve_venv_python(
            self.worktree_path, venv_python
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
        self.wave_size = max(1, int(wave_size))
        # TASK-DIAG-F4A2: Turn number for sdk_debug preservation paths.
        # Default 1 keeps backwards-compat for callers that don't pass it.
        self._turn = max(1, int(turn))
        # TASK-FIX-A7B2: Wave-peer file-edit snapshot for source-file contention
        # detection. Normalised to ``Dict[str, frozenset[str]]`` so the overlap
        # check is a cheap set intersection.
        self._peer_changed_files: Dict[str, frozenset] = {}
        if peer_changed_files:
            for peer_id, files in peer_changed_files.items():
                if not peer_id or peer_id == self.task_id:
                    continue
                if not files:
                    continue
                self._peer_changed_files[peer_id] = frozenset(
                    str(f) for f in files if f
                )
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

    def _detect_source_file_contention(
        self,
        task_work_results: Dict[str, Any],
    ) -> Dict[str, frozenset]:
        """Detect source-file contention with in-flight peer tasks (TASK-FIX-A7B2).

        Returns a mapping ``peer_task_id -> frozenset[overlapping_file]`` for
        every peer that edited at least one file this task also edited within
        the same parallel wave. An empty mapping means there is no source-file
        contention — the failure is either genuinely transient (e.g. infra
        flakiness, partial __init__.py write race) or unrelated to peer edits,
        so the existing TASK-ABFIX-005 conditional approval path remains safe.

        A non-empty mapping means the parallel_contention is real source-file
        contention (e.g. two tasks writing conflicting step definitions to a
        shared BDD glue file). The TASK-ABFIX-005 isolation snapshot cannot
        defend against this case because the snapshot captures the
        already-corrupted shared file. Conditional approval would mask real
        correctness damage, so the caller must fall through to feedback and
        let the existing Player-Coach retry machinery serialise the next
        attempt (by which point peers have completed and the wave is
        effectively single-tasked).

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Player's task_work_results.json payload. Reads ``files_authored``
            (Player's explicit Write/Edit tool calls — TASK-FIX-CC-COND) when
            present, otherwise falls back to ``files_created`` /
            ``files_modified`` for compatibility with pre-files_authored
            artefacts.

        Returns
        -------
        Dict[str, frozenset[str]]
            Map from peer task id to set of overlapping file paths. Empty when
            no peer edits overlap, when this task has no recorded edits, or
            when no peer snapshot was supplied.

        Notes
        -----
        TASK-FIX-CC-COND: ``files_modified`` / ``files_created`` are
        unioned with worktree-wide ``git diff`` output by ``agent_invoker``
        before they reach this validator, so in shared-worktree parallel
        waves they include peer-task edits this task never authored. Using
        them as the contention input produced false-positive
        ``parallel_contention`` verdicts that blocked the conditional
        approval path the design relies on (see TASK-REV-CC40 finding F-3,
        FEAT-39E1 turn-2 evidence). ``files_authored`` is captured at the
        SDK Write/Edit boundary and is *not* enriched with git output, so
        it remains authoritative. The fallback is presence-based, not
        truthy-based: ``files_authored = []`` correctly means "this task
        authored nothing" and yields no contention, even when
        ``files_modified`` is contaminated.
        """
        if not self._peer_changed_files:
            return {}

        # TASK-FIX-CC-COND: prefer the Player's authored set when present.
        # Presence-based fallback: distinguish "field absent" (legacy
        # task_work_results.json from before files_authored existed) from
        # "field present, empty" (this task's Player did no Write/Edit).
        if "files_authored" in task_work_results:
            authored_raw = task_work_results.get("files_authored") or []
            own = {str(f) for f in authored_raw if f}
            source = "files_authored"
        else:
            legacy = set(task_work_results.get("files_created", []) or [])
            legacy.update(task_work_results.get("files_modified", []) or [])
            own = {str(f) for f in legacy if f}
            source = "legacy_files_modified"

        if not own:
            return {}

        overlaps: Dict[str, frozenset] = {}
        for peer_id, peer_files in self._peer_changed_files.items():
            shared = peer_files & own
            if shared:
                overlaps[peer_id] = frozenset(shared)

        if overlaps:
            # TASK-FIX-CC-COND bonus: structured-log line so future
            # false positives are diagnosable from logs alone. Records
            # both the authored set and the (possibly contaminated)
            # files_modified set so a reviewer can see at a glance
            # whether the overlap reflects real intent or legacy
            # fallback noise.
            logger.info(
                "Source-file contention detected (source=%s, overlaps=%s, "
                "files_authored=%s, files_modified=%s, files_created=%s)",
                source,
                {peer: sorted(files) for peer, files in overlaps.items()},
                sorted(task_work_results.get("files_authored", []) or []),
                sorted(task_work_results.get("files_modified", []) or []),
                sorted(task_work_results.get("files_created", []) or []),
            )
        return overlaps

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

    def validate(
        self,
        task_id: str,
        turn: int,
        task: Dict[str, Any],
        skip_arch_review: bool = False,
        context: Optional[str] = None,
    ) -> CoachValidationResult:
        """
        Main validation entry point.

        Validates Player's implementation by:
        1. Reading task-work quality gate results
        2. Verifying all gates passed
        3. Running independent test verification
        4. Checking requirements satisfaction

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        turn : int
            Current turn number (1-based)
        task : Dict[str, Any]
            Task data including acceptance_criteria
        skip_arch_review : bool
            If True, skip architectural review gate regardless of profile setting.
            Used for --implement-only mode where Phase 2.5B doesn't run.
            Default: False (enforce arch review per profile).

        Returns
        -------
        CoachValidationResult
            Complete validation result with decision
        """
        logger.info(f"Starting Coach validation for {task_id} turn {turn}")

        # Log context if provided
        if context:
            logger.debug(f"[Graphiti] Coach context provided: {len(context)} chars")

        # Resolve task type and get quality gate profile
        try:
            task_type = self._resolve_task_type(task)
        except ValueError as e:
            logger.error(f"Failed to resolve task type: {e}")
            # honesty_verification omitted (defaults to None): _verify_honesty
            # has not yet been called on this short-circuit path (TASK-FIX-7E3F).
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                issues=[{
                    "severity": "must_fix",
                    "category": "invalid_task_type",
                    "description": str(e),
                }],
                rationale=f"Invalid task type: {e}",
                context_used=context,
                is_configuration_error=True,
            )

        # Operator handoff: defensive skip branch (TASK-FPTC-004 AC-01).
        # Operator-handoff tasks have runtime-shaped acceptance criteria
        # that no automated check can verify (e.g. "operator runs X
        # against the deployed service and inspects Y"). The feature
        # orchestrator (TASK-FPTC-003) is responsible for short-circuiting
        # dispatch BEFORE Coach is invoked — this branch is a paranoid
        # second line of defence that exits cleanly without exercising
        # any AC-matching machinery if the orchestrator-level skip is
        # bypassed for any reason. The "deferred" outcome shape mirrors
        # what feature_orchestrator records, so TASK-FPTC-005's
        # feature-complete summary sees consistent records.
        if task_type == TaskType.OPERATOR_HANDOFF:
            logger.info(
                f"Coach skipping operator_handoff task {task_id} turn {turn}: "
                f"runtime verification deferred to operator."
            )
            # honesty_verification omitted (defaults to None): _verify_honesty
            # has not yet been called on this operator-handoff short-circuit
            # path (TASK-FIX-7E3F).
            return CoachValidationResult(
                task_id=task_id,
                turn=turn,
                decision="deferred",
                quality_gates=None,
                independent_tests=None,
                requirements=None,
                issues=[],
                rationale="operator follow-up — runtime verification required",
                context_used=context,
            )

        profile = get_profile(task_type)
        logger.info(f"Using quality gate profile for task type: {task_type.value}")

        # 1. Read task-work quality gate results
        task_work_results = self.read_quality_gate_results(task_id)

        if "error" in task_work_results:
            logger.warning(
                f"Task-work results for {task_id} contain error: "
                f"{task_work_results.get('error', 'unknown')}"
            )
            # honesty_verification omitted (defaults to None): _verify_honesty
            # has not yet been called on this missing-results short-circuit
            # path (TASK-FIX-7E3F).
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                issues=[{
                    "severity": "must_fix",
                    "category": "missing_results",
                    "description": task_work_results["error"],
                }],
                rationale="Task-work quality gate results not found",
                context_used=context,
            )

        # 1.4. Adversarial honesty verification (TASK-AB-FIX-INVAB1 AC-002).
        #
        # Restores the original Player–Coach adversarial property on the
        # deterministic Coach path. Option D (TASK-REV-0414) introduced
        # CoachValidator as the primary Coach but did not wire in
        # CoachVerifier — the existing-but-disconnected honesty verifier
        # documented in installer/core/agents/autobuild-coach.md:141-203.
        #
        # The verifier checks Player claims against worktree state:
        # - files_created / files_modified / tests_written exist on disk
        # - completion_promises[*].implementation_files exist when status=complete
        #
        # When critical discrepancies exist, gates are not consulted at all
        # — Player feedback names the specific claim/actual disagreement so
        # the next turn can correct course. Honest reports produce zero
        # discrepancies (no behavioural change for compliant Players).
        #
        # Test verification (CoachVerifier._verify_test_results) is
        # deliberately skipped here because run_independent_tests below
        # already runs an authoritative independent pytest pass — running
        # it twice would double the Coach's wall-clock cost.
        honesty_verification = self._verify_honesty(task_work_results)
        honesty_issues = self._honesty_issues_from(honesty_verification)
        # TASK-FIX-1B4B Layer 2: only ``must_fix`` honesty issues
        # short-circuit gate evaluation. ``should_fix`` issues (a single
        # path-only ``file_existence`` discrepancy demoted by
        # ``_honesty_issues_from``) ride along to the final result so
        # the Player still sees them in feedback while the rest of the
        # gates run.
        honesty_must_fix = [
            i for i in honesty_issues if i["severity"] == "must_fix"
        ]
        honesty_should_fix = [
            i for i in honesty_issues if i["severity"] == "should_fix"
        ]
        if honesty_must_fix:
            logger.warning(
                f"Honesty verification produced {len(honesty_must_fix)} "
                f"critical issue(s) for {task_id}; short-circuiting "
                f"gate evaluation."
            )
            return CoachValidationResult(
                task_id=task_id,
                turn=turn,
                decision="feedback",
                quality_gates=None,
                independent_tests=None,
                requirements=None,
                issues=honesty_must_fix,
                rationale=(
                    f"{len(honesty_must_fix)} honesty discrepancy/discrepancies. "
                    f"Adversarial verification overrode gate evaluation."
                ),
                context_used=context,
                honesty_verification=honesty_verification,
            )

        # 1.45. AC-cited missing test files (TASK-AB-FIX-INVAB1 AC-006).
        #
        # If an acceptance criterion names a specific test file (e.g.
        # ``tests/test_login.py``) and that file does not exist on disk,
        # the independent-test gate would silently fall back to the
        # existing-test set and report green. Surface the gap as a
        # ``must_fix`` issue so the Coach short-circuits with feedback
        # rather than running a smaller-scope pytest invocation that can
        # only return false-greens.
        ac_missing_tests = self._detect_ac_cited_missing_test_files(
            task.get("acceptance_criteria", [])
        )
        if ac_missing_tests:
            logger.warning(
                f"AC-cited missing test files for {task_id}: "
                f"{ac_missing_tests}. Short-circuiting before "
                f"run_independent_tests."
            )
            return CoachValidationResult(
                task_id=task_id,
                turn=turn,
                decision="feedback",
                quality_gates=None,
                independent_tests=None,
                requirements=None,
                issues=honesty_should_fix + [{
                    "severity": "must_fix",
                    "category": "acceptance_criteria",
                    "description": (
                        f"AC names test file(s) that don't exist on disk: "
                        f"{', '.join(ac_missing_tests)}. The independent-"
                        f"test gate cannot run honestly while AC-cited "
                        f"tests are absent."
                    ),
                    "details": {"missing_test_files": ac_missing_tests},
                }],
                rationale=(
                    f"{len(ac_missing_tests)} AC-cited test file(s) "
                    f"missing on disk; gate cannot run honestly."
                ),
                context_used=context,
                honesty_verification=honesty_verification,
            )

        # 1.5. Agent-invocations gate (TASK-FIX-RWOP1.3.1, TASK-REV-F6E1 F3c).
        #
        # AgentInvoker._write_task_work_results folds
        # validate_agent_invocations into the producer path and persists the
        # verdict under "agent_invocations_validation".
        #
        # Pre-F3c (RWOP1.3.1 → forge-run-6): a "violation" status caused this
        # method to early-return with feedback, short-circuiting positions
        # 2–4 (quality_gates, independent_tests, AC verification). The
        # consequence — observed across forge-run-3/4/5/6 — was that the
        # Coach never once ran AC verification when the gate fired, so
        # the recent BDD-AC bridge work could not actually deliver its
        # quality signal.
        #
        # Post-F3c: a "violation" is captured as a non-blocking advisory
        # (severity=warning, category=agent_invocations_advisory) and
        # threaded into the issues list of whatever decision the
        # outcome-based gates produce. The Player still sees the process
        # observation ("you should invoke X via Task tool") so structural
        # drift toward Player-inline implementation stays visible — but
        # the gate no longer prevents the outcome-checks from running.
        #
        # Stall classifiers that match `category == "agent_invocations_violation"`
        # (autobuild stall sub-typing) intentionally no longer trigger:
        # this gate stops being a stall driver. Promote back to blocker
        # only after evidence shows the advisory-mode signal is being
        # systematically ignored AND that absence correlates with quality
        # drops in AC verification. See
        # docs/reviews/forge-run-6-fix-or-revert/TASK-REV-F6E1-decision-report.md
        # § Revision 3 for the diagnostic and rationale.
        agent_invocations_advisory: Optional[Dict[str, Any]] = None
        agent_invocations_validation = task_work_results.get(
            "agent_invocations_validation"
        )
        if (
            isinstance(agent_invocations_validation, dict)
            and agent_invocations_validation.get("status") == "violation"
        ):
            raw_missing = agent_invocations_validation.get("missing_phases") or []
            # The validator may emit missing_phases either as a list of phase
            # IDs or as a list of {"phase": "...", "description": "..."} dicts.
            # Normalise to a flat list of phase IDs for downstream formatting.
            missing_phases: List[str] = []
            if raw_missing and isinstance(raw_missing[0], dict):
                missing_phases = [
                    str(m.get("phase", ""))
                    for m in raw_missing
                    if m.get("phase")
                ]
            else:
                missing_phases = [str(m) for m in raw_missing]
            missing_phases_sorted = sorted(missing_phases)
            missing_phases_str = (
                ", ".join(missing_phases_sorted)
                if missing_phases_sorted
                else "unknown"
            )
            # TASK-FIX-7A07 AC-3: Build a phase-with-description rendering and
            # resolve the stack-specific Phase-3 specialist name so the
            # Player's next turn has actionable guidance on *which*
            # sub-agent to invoke via the Task tool.
            missing_phases_with_names = ", ".join(
                f"{p} ({PHASE_DESCRIPTIONS.get(p, 'Unknown')})"
                for p in missing_phases_sorted
            ) if missing_phases_sorted else "unknown"
            stack_template = detect_stack_template(self.worktree_path)
            # TASK-GK-PROF-001: thread the worktree root so Phase-3 resolution
            # consults the *installed* specialist set, not the legacy
            # stack→specialist map. When the stack's profile-default isn't
            # installed (e.g. langchain-deepagents-orchestrator ships
            # langchain-tool-decorator-specialist, not python-api-specialist),
            # this downgrades the advisory to informational instead of naming
            # an agent the operator doesn't have.
            specialist_lines = render_missing_phase_list(
                missing_phases_sorted,
                stack_template=stack_template,
                workspace_root=self.worktree_path,
            )
            specialist_block = "\n".join(f"- {line}" for line in specialist_lines)
            expected_phases_val = agent_invocations_validation.get(
                "expected_phases"
            )
            actual_invocations_val = agent_invocations_validation.get(
                "actual_invocations"
            )
            expected_str = (
                str(expected_phases_val)
                if expected_phases_val is not None
                else "?"
            )
            actual_str = (
                str(actual_invocations_val)
                if actual_invocations_val is not None
                else "?"
            )
            logger.info(
                f"Agent-invocations advisory for {task_id}: "
                f"missing phases {missing_phases_str} "
                f"(non-blocking; outcome gates will run)"
            )
            advisory_description = (
                f"Advisory (non-blocking): task-work produced a report with "
                f"{actual_str} of {expected_str} expected agent invocations. "
                f"Missing phases: {missing_phases_with_names}. "
                f"Consider invoking these agents via the Task tool to "
                f"strengthen stack-specific quality:\n{specialist_block}"
            )
            agent_invocations_advisory = {
                "severity": "warning",
                "category": "agent_invocations_advisory",
                "description": advisory_description,
                "details": {
                    "missing_phases": missing_phases_sorted,
                    "expected_phases": expected_phases_val,
                    "actual_invocations": actual_invocations_val,
                },
            }

        # F3c helper: prepend the advisory to any issues list so process
        # observations ride along with whatever outcome-based decision
        # downstream gates produce. ``honesty_should_fix`` rides the
        # same channel (TASK-FIX-1B4B Layer 2): a single demoted
        # path-only honesty discrepancy surfaces in feedback while the
        # rest of the gates evaluate normally.
        advisory_issues: List[Dict[str, Any]] = (
            [agent_invocations_advisory]
            if agent_invocations_advisory is not None
            else []
        )
        advisory_issues.extend(honesty_should_fix)

        # 2. Verify quality gates passed with profile
        gates_status = self.verify_quality_gates(
            task_work_results, profile=profile, skip_arch_review=skip_arch_review
        )

        # Validate requirements ahead of the gate-fail short-circuit so
        # gate-failure results carry criteria_met (TASK-GK-CR-001). This
        # is a pure read over task / task_work_results / the player report
        # — no side effects, idempotent. The same value is reused on the
        # all-gates-passed path below, so the call happens exactly once.
        requirements = self.validate_requirements(task, task_work_results, turn=turn)

        if not gates_status.all_gates_passed:
            logger.info(f"Quality gates failed for {task_id}: {gates_status}")
            return self._feedback_from_gates(
                task_id=task_id,
                turn=turn,
                gates=gates_status,
                task_work_results=task_work_results,
                context_used=context,
                extra_issues=advisory_issues,
                honesty_verification=honesty_verification,
                requirements=requirements,
            )

        # 3. Independent test verification (trust but verify)
        # Skip independent tests for task types that don't require tests (e.g., scaffolding)
        if not profile.tests_required:
            test_result = IndependentTestResult(
                tests_passed=True,
                test_command="skipped",
                test_output_summary=(
                    f"Independent test verification skipped "
                    f"(tests not required for {task_type.value} tasks)"
                ),
                duration_seconds=0.0,
            )
            logger.info(
                f"Independent test verification skipped for {task_id} "
                f"(tests not required for {task_type.value} tasks)"
            )
        else:
            test_result = self.run_independent_tests(
                task_work_results=task_work_results,
                task=task,
                turn=turn,
            )

        conditional_approval = False
        environment_conditional_approval = False
        failure_class = None
        if not test_result.tests_passed:
            failure_class, failure_confidence = self._classify_test_failure(
                test_result.raw_output,
                requires_infrastructure=task.get("requires_infrastructure") if task else None,
            )
            logger.warning(
                f"Independent test verification failed for {task_id} "
                f"(classification={failure_class}, confidence={failure_confidence})"
            )

            # Conditional approval for high-confidence infrastructure failures
            # when task declares requires_infrastructure and Docker is unavailable
            requires_infra = task.get("requires_infrastructure", [])
            docker_available = task.get("_docker_available", True)

            logger.info(
                "conditional_approval check: failure_class=%s, confidence=%s, "
                "requires_infra=%s, docker_available=%s, all_gates_passed=%s, "
                "wave_size=%s",
                failure_class,
                failure_confidence,
                requires_infra,
                docker_available,
                gates_status.all_gates_passed,
                self.wave_size,
            )

            # TASK-ABSR-2468: belt-and-braces clause for environment-class
            # ambiguous infrastructure failures (ImportError /
            # ModuleNotFoundError without service-client context) when the
            # worktree's bootstrap install is observably broken and all
            # Player gates passed. Pairs with the bootstrap_failure_mode
            # smart default from TASK-ABSR-A1B2: when a user opts into
            # ``warn`` mode and ships on a half-installed venv, this clause
            # prevents the feedback-stall trapdoor from firing on what is
            # purely an environment problem.
            environment_conditional_approval = (
                failure_class == "infrastructure"
                and failure_confidence == "ambiguous"
                and gates_status.all_gates_passed
                and not requires_infra
                and self._bootstrap_likely_broken(task)
            )

            # TASK-FIX-A7B2: Detect source-file contention with peer wave tasks.
            # The TASK-ABFIX-005 conditional approval for parallel_contention /
            # parallel-code failures assumes the contention is transient
            # infrastructure (e.g. partial __init__.py write race) that a retry
            # in isolation can clear. When two parallel tasks edit the SAME
            # source file (e.g. shared BDD glue), the contention is real
            # source-level damage — both tasks committed inconsistent state to
            # the shared branch BEFORE either snapshot was taken, so the
            # isolation snapshot captures the already-corrupted file. Granting
            # conditional approval in that case masks the corruption and the
            # failure surfaces only at wave-2 verification.
            #
            # When overlap is detected, fall through to feedback so the
            # existing Player-Coach retry machinery serialises the next
            # attempt — by which point peers have completed and the wave is
            # effectively single-tasked, eliminating the contention.
            source_file_contention_overlaps: Dict[str, frozenset] = {}
            is_parallel_contention_class = (
                failure_class == "parallel_contention"
                or (failure_class == "code" and self.is_parallel)
            )
            if is_parallel_contention_class and self._peer_changed_files:
                source_file_contention_overlaps = (
                    self._detect_source_file_contention(task_work_results)
                )

            conditional_approval = (
                failure_class == "infrastructure"
                and failure_confidence == "high"
                and bool(requires_infra)
                and not docker_available
                and gates_status.all_gates_passed
            ) or (
                failure_class == "collection_error"
                and gates_status.all_gates_passed
            ) or (
                # TASK-ABFIX-005: Grant conditional approval for contention-related
                # failures in a parallel wave when all Player quality gates passed.
                # "parallel_contention" is set by _classify_test_failure() when
                # wave_size > 1 and the failure looks like it could be contention.
                # TASK-FIX-A7B2: Only when no source-file overlap with peers.
                failure_class == "parallel_contention"
                and gates_status.all_gates_passed
                and not source_file_contention_overlaps
            ) or (
                # TASK-ABFIX-005: Also grant conditional approval for any "code"
                # failure in a parallel wave (recommendation 3b from TASK-REV-A17A).
                # The failure might be a false positive caused by concurrent mutations.
                # TASK-FIX-A7B2: Only when no source-file overlap with peers.
                failure_class == "code"
                and self.is_parallel
                and gates_status.all_gates_passed
                and not source_file_contention_overlaps
            ) or environment_conditional_approval

            if conditional_approval:
                if environment_conditional_approval:
                    logger.warning(
                        f"Conditional approval for {task_id}: environment-class "
                        f"infrastructure failure ({failure_class}/{failure_confidence}) "
                        f"on a known-broken bootstrap; all Player gates passed. "
                        f"Marking approved with environment flag."
                    )
                elif failure_class == "collection_error":
                    logger.warning(
                        f"Conditional approval for {task_id}: test collection errors in "
                        f"independent verification, all Player gates passed. "
                        f"Continuing to requirements check."
                    )
                elif failure_class == "parallel_contention":
                    logger.warning(
                        f"Conditional approval for {task_id}: parallel contention failure "
                        f"(wave_size={self.wave_size}), all Player gates passed. "
                        f"Continuing to requirements check."
                    )
                elif failure_class == "code" and self.is_parallel:
                    logger.warning(
                        f"Conditional approval for {task_id}: code failure in parallel wave "
                        f"(wave_size={self.wave_size}), all Player gates passed. "
                        f"Continuing to requirements check."
                    )
                else:
                    logger.warning(
                        f"Conditional approval for {task_id}: infrastructure failure "
                        f"with declared deps {requires_infra}, Docker unavailable. "
                        f"Continuing to requirements check."
                    )
                # Fall through to requirements check with conditional flag set
            else:
                # Check for psycopg2/asyncpg mismatch before falling back to
                # generic infrastructure feedback (TASK-FIX-4415).
                if self._is_psycopg2_asyncpg_mismatch(test_result.raw_output, task):
                    description = (
                        "ModuleNotFoundError for 'psycopg2' — this project uses "
                        "asyncpg. Remove `import psycopg2` from your code and use "
                        "asyncpg-compatible database patterns instead."
                    )
                    rationale = (
                        "Tests failed because psycopg2 was imported in an asyncpg "
                        "project"
                    )
                elif (
                    is_parallel_contention_class
                    and source_file_contention_overlaps
                ):
                    # TASK-FIX-A7B2: Source-file contention with at least one
                    # peer in the same wave. Name the overlapping files so the
                    # Player can resolve the conflict on retry. The retry will
                    # be naturally serialised — by the time the Player runs
                    # its next turn, peers have completed and the wave is
                    # effectively single-tasked.
                    error_output = (test_result.test_output_summary or "").strip()
                    if len(error_output) > 500:
                        error_output = error_output[:497] + "..."
                    overlap_lines = []
                    for peer_id in sorted(source_file_contention_overlaps):
                        files = sorted(source_file_contention_overlaps[peer_id])
                        overlap_lines.append(
                            f"  - {peer_id}: {', '.join(files)}"
                        )
                    overlap_block = "\n".join(overlap_lines)
                    base = (
                        f"Tests failed due to source-file contention with peer "
                        f"task(s) in this parallel wave (wave_size={self.wave_size}). "
                        f"Both this task and the peer(s) below edited the same "
                        f"source file(s); the resulting shared-branch state is "
                        f"inconsistent and an isolation-snapshot retry cannot "
                        f"recover it. Resolve the conflict on the next turn — "
                        f"by then the peer(s) will have completed and the wave "
                        f"is effectively serialised.\n"
                        f"Overlapping files by peer:\n{overlap_block}\n"
                        f"Test command: {test_result.test_command}."
                    )
                    description = (
                        f"{base} Error detail: {error_output}"
                        if error_output
                        else base
                    )
                    rationale = (
                        "Tests failed due to source-file contention with peer "
                        "wave tasks (real correctness damage, not transient "
                        "infra contention) — see TASK-FIX-A7B2"
                    )
                elif failure_class == "parallel_contention":
                    error_output = (test_result.test_output_summary or "").strip()
                    if len(error_output) > 500:
                        error_output = error_output[:497] + "..."
                    base = (
                        f"Tests failed due to likely parallel wave contention "
                        f"(wave_size={self.wave_size}). Another task may have "
                        f"concurrently modified shared files (e.g. __init__.py) "
                        f"during Coach independent verification. "
                        f"Test command: {test_result.test_command}."
                    )
                    description = (
                        f"{base} Error detail: {error_output}"
                        if error_output
                        else base
                    )
                    rationale = (
                        "Tests failed due to likely parallel wave contention, "
                        "not code defects"
                    )
                elif failure_class in ("infrastructure", "collection_error"):
                    error_output = (test_result.test_output_summary or "").strip()
                    if len(error_output) > 500:
                        error_output = error_output[:497] + "..."
                    base = (
                        "Tests failed due to infrastructure/environment issues "
                        f"(not code defects). Test command: {test_result.test_command}. "
                        "Remediation options: "
                        "(1) Add mock fixtures for external services, "
                        "(2) Use SQLite for test database, "
                        "(3) Mark integration tests with @pytest.mark.integration "
                        "and exclude via -m 'not integration'."
                    )
                    description = (
                        f"{base} Error detail: {error_output}"
                        if error_output
                        else base
                    )
                    rationale = (
                        "Tests failed due to infrastructure/environment issues, "
                        "not code defects"
                    )
                else:
                    description = "Independent test verification failed"
                    rationale = (
                        "Tests passed according to task-work but failed on "
                        "independent verification"
                    )

                return self._feedback_result(
                    task_id=task_id,
                    turn=turn,
                    quality_gates=gates_status,
                    independent_tests=test_result,
                    issues=advisory_issues + [{
                        "severity": "must_fix",
                        "category": "test_verification",
                        "description": description,
                        "test_output": test_result.test_output_summary,
                        "failure_classification": failure_class,
                        "failure_confidence": failure_confidence,
                    }],
                    rationale=rationale,
                    context_used=context,
                    honesty_verification=honesty_verification,
                )

        # 4. Validate requirements satisfaction (already hoisted above —
        # see TASK-GK-CR-001).
        if not requirements.all_criteria_met:
            logger.info(f"Requirements not met for {task_id}: missing {requirements.missing}")
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                quality_gates=gates_status,
                independent_tests=test_result,
                requirements=requirements,
                issues=advisory_issues + [{
                    "severity": "must_fix",
                    "category": "missing_requirement",
                    "description": f"Not all acceptance criteria met",
                    "missing_criteria": requirements.missing,
                }],
                rationale=f"Missing {len(requirements.missing)} acceptance criteria: {', '.join(requirements.missing)}",
                context_used=context,
                honesty_verification=honesty_verification,
            )

        # 5. Check for blocking zero-test anomaly before approval
        zero_test_issues = self._check_zero_test_anomaly(
            task_work_results, profile, independent_tests=test_result,
            task_id=task_id,
        )
        has_blocking_zero_test = any(
            issue.get("severity") == "error" for issue in zero_test_issues
        )

        if has_blocking_zero_test:
            logger.info(f"Coach rejected {task_id} turn {turn}: zero-test anomaly (blocking)")
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                quality_gates=gates_status,
                independent_tests=test_result,
                requirements=requirements,
                issues=advisory_issues + zero_test_issues,
                rationale=(
                    "Zero-test anomaly detected: quality gates reported as passed but "
                    "no tests were executed. Tests are required for this task type. "
                    "Please write and run tests before resubmitting."
                ),
                context_used=context,
                honesty_verification=honesty_verification,
            )

        # 5.5. Check for seam test recommendations (soft gate, non-blocking)
        seam_test_issues = self._check_seam_test_recommendation(
            task_work_results, profile
        )

        # 5.6. Validate consumer_context format constraints (soft gate, non-blocking)
        consumer_context_issues = self._validate_consumer_context(
            task, task_work_results
        )

        # 5.65. Unconfirmed low-confidence assumptions (TASK-FIX-RWOP1.4a).
        # Warn-mode gate: feature-spec.md:337 says Coach verifies
        # low-confidence assumptions before accepting a spec. The producer
        # (AgentInvoker._write_task_work_results) writes the block;
        # here we surface it as a non-blocking warning so the human
        # reviewing the merge sees it. Escalation to block-mode is a
        # separate task driven by evidence that warn-mode is being ignored.
        assumption_issues = self._check_unconfirmed_assumptions(
            task_work_results
        )

        # 5.7. BDD oracle gate (TASK-BDD-E8954): when present in task_work_results,
        # scenarios_failed > 0 blocks approval. scenarios_pending is informational
        # and surfaces in feedback without blocking — see bdd_runner module docstring
        # for the three-state model and rationale for not collapsing pending into
        # failed.
        bdd_blocking, bdd_non_blocking = self._check_bdd_results(task_work_results)
        if bdd_blocking:
            logger.info(
                f"Coach rejected {task_id} turn {turn}: bdd_results.scenarios_failed > 0"
            )
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                quality_gates=gates_status,
                independent_tests=test_result,
                requirements=requirements,
                issues=advisory_issues + bdd_blocking + bdd_non_blocking,
                rationale=(
                    "BDD scenarios failed: "
                    f"{task_work_results.get('bdd_results', {}).get('scenarios_failed', 0)} "
                    "scenario(s) reported assertion failure during pytest-bdd execution."
                ),
                context_used=context,
                honesty_verification=honesty_verification,
            )

        # 5.8. Seam tests blocking gate (TASK-FIX-A7B4).
        # Distinct from the soft `_check_seam_test_recommendation` above:
        # this gate fires only when the task description itself contains a
        # non-empty `## Seam Tests` section AND the Player wrote zero tests
        # carrying @pytest.mark.{seam,contract,boundary}. Detected before
        # approval, after the BDD blocker, so the rest of this turn's gates
        # have already filtered out lower-quality failure modes.
        seam_blocking = self._check_seam_tests_implemented(task, task_work_results)
        if seam_blocking:
            logger.info(
                f"Coach rejected {task_id} turn {turn}: "
                "task description specifies seam tests but Player wrote none"
            )
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                quality_gates=gates_status,
                independent_tests=test_result,
                requirements=requirements,
                issues=advisory_issues + seam_blocking,
                rationale=(
                    "Seam tests gate: task description specifies a "
                    "non-empty `## Seam Tests` section but no "
                    "@pytest.mark.{seam,contract,boundary} tests were "
                    "written. Implement the seam test stub before "
                    "resubmitting."
                ),
                context_used=context,
                honesty_verification=honesty_verification,
            )

        # Combine all non-blocking issues. The agent_invocations advisory
        # (F3c) rides along here on the approval path so the Player still
        # sees the process observation even when outcome gates approve.
        all_issues = (
            advisory_issues
            + zero_test_issues
            + seam_test_issues
            + consumer_context_issues
            + assumption_issues
            + bdd_non_blocking
        )

        # 6. All checks passed - approve
        if conditional_approval:
            if failure_class == "collection_error":
                logger.warning(
                    f"Coach conditionally approved {task_id} turn {turn}: "
                    f"test collection errors in independent verification, all gates passed"
                )
            else:
                logger.warning(
                    f"Coach conditionally approved {task_id} turn {turn}: "
                    f"infrastructure-dependent, independent tests skipped"
                )
        else:
            logger.info(f"Coach approved {task_id} turn {turn}")

        # Build accurate rationale based on actual verification status
        rationale = self._build_approval_rationale(
            test_result=test_result,
            gates_status=gates_status,
            task_work_results=task_work_results,
            profile=profile,
            context=context,
            conditional_approval=conditional_approval,
            failure_class=failure_class,
            environment_conditional_approval=environment_conditional_approval,
        )

        return CoachValidationResult(
            task_id=task_id,
            turn=turn,
            decision="approve",
            quality_gates=gates_status,
            independent_tests=test_result,
            requirements=requirements,
            issues=all_issues,
            rationale=rationale,
            context_used=context,
            approved_without_independent_tests=conditional_approval,
            environment_conditional_approval=environment_conditional_approval,
            honesty_verification=honesty_verification,
        )

    def gather_evidence(
        self,
        task_id: str,
        turn: int,
        task: Dict[str, Any],
        skip_arch_review: bool = False,
        context: Optional[str] = None,
    ) -> CoachEvidenceBundle:
        """Gather structured evidence for the LLM Coach (TASK-HMIG-008R Part A).

        Runs the same deterministic gathering pipeline the legacy
        ``validate()`` method uses internally, but packages the results into a
        :class:`CoachEvidenceBundle` instead of applying decision logic. The
        LLM Coach reads this bundle (rendered as JSON into the Coach prompt by
        ``_build_coach_prompt``) plus the honesty result and makes the final
        approve/feedback decision per the Block adversarial-cooperation paper.

        The pipeline aborts early under three conditions, leaving downstream
        fields as ``None`` and setting ``bundle.gathering_status`` so the
        Coach's absence-of-failure guards know to treat the ``None`` fields
        as ABSENT SIGNAL:

        * Pre-evidence error (invalid task type, missing task_work_results,
          or an unexpected exception in a gathering helper) →
          ``"partial_exception"`` with a human-readable cause in
          ``bundle.gathering_error``.
        * Honesty verification produced ``must_fix`` discrepancies →
          ``"partial_honesty_abort"``. Gates and independent tests are not
          run because the legacy decision tree would have short-circuited
          here too — the LLM Coach reaches the same conclusion by reading
          ``bundle.honesty.discrepancies``.
        * Quality gates failed → ``"partial_gate_abort"``. Independent
          tests / requirements validation are not run. The LLM Coach
          reaches a feedback decision by reading ``bundle.quality_gates``.

        Per the Phase 2.5 architectural review and §3 "Exception handling
        for gather_evidence" in the implementation plan, this method MUST
        NOT raise to its caller. Wrapping inner helper exceptions in a
        ``partial_exception`` bundle prevents an exception fallback to
        ``validate()`` from re-activating the primary decision path that
        falsifier #1 ("CoachValidator.validate() for the decision is GONE")
        requires to be gone. ``GUARDKIT_COACH_LEGACY=1`` remains the sole
        operator-controlled mechanism for re-activating ``validate()``.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., ``"TASK-001"``). Used to read
            ``task_work_results.json`` from the standard autobuild path and
            to wire state-bridge identity resolution into the honesty
            verifier (TASK-FIX-1B4A Layer 1).
        turn : int
            Current turn number (1-based). Passed to
            ``validate_requirements`` and ``run_independent_tests``.
        task : Dict[str, Any]
            Task data dict. Must contain ``acceptance_criteria`` and may
            contain ``task_type``, ``requires_infrastructure``,
            ``_docker_available``, ``consumer_context``, ``description``.
        skip_arch_review : bool, optional
            If ``True``, the architectural-review gate is skipped regardless
            of the profile setting. Used for ``--implement-only`` mode where
            Phase 2.5B did not run. Default: ``False``.
        context : Optional[str], optional
            Optional Graphiti / coach context string. Not currently consumed
            by gather_evidence itself; threaded through for symmetry with
            ``validate()``'s signature so the legacy shim (when AC-003 is
            completed in a follow-up) can pass it forward.

        Returns
        -------
        CoachEvidenceBundle
            Populated evidence bundle. Always returned; never raises.
        """
        default_honest = HonestyVerification(verified=True)

        # ------------------------------------------------------------------
        # Pre-evidence: resolve task type. Mirrors validate() lines 821-838.
        # ------------------------------------------------------------------
        try:
            task_type = self._resolve_task_type(task)
        except ValueError as exc:
            logger.error(
                "gather_evidence: failed to resolve task type: %s", exc
            )
            return CoachEvidenceBundle(
                honesty=default_honest,
                gathering_status="partial_exception",
                gathering_error=f"invalid_task_type: {exc}",
            )

        try:
            profile = get_profile(task_type)
        except Exception as exc:  # noqa: BLE001 — defensive; get_profile is total
            logger.error(
                "gather_evidence: failed to load profile for %s: %s",
                task_type, exc,
            )
            return CoachEvidenceBundle(
                honesty=default_honest,
                gathering_status="partial_exception",
                gathering_error=f"missing_profile: {exc}",
                task_type=task_type.value,
            )

        profile_name = getattr(profile, "name", None) or task_type.value

        # OPERATOR_HANDOFF: no evidence to gather. The legacy validate() returns
        # decision="deferred" here; gather_evidence reports a clean status so
        # the LLM Coach prompt sees an empty bundle with the task_type marker.
        # The Part B / Part C wiring is responsible for short-circuiting the
        # Coach invocation for operator-handoff tasks at the autobuild layer
        # (the same place the legacy validate() returned deferred).
        if task_type == TaskType.OPERATOR_HANDOFF:
            logger.info(
                "gather_evidence: skipping evidence collection for "
                "operator_handoff task %s (runtime verification deferred to "
                "operator)", task_id,
            )
            return CoachEvidenceBundle(
                honesty=default_honest,
                gathering_status="complete",
                task_type=task_type.value,
                profile_name=profile_name,
            )

        # ------------------------------------------------------------------
        # Pre-evidence: read task_work_results. Mirrors validate() lines 875-895.
        # ------------------------------------------------------------------
        task_work_results = self.read_quality_gate_results(task_id)
        if "error" in task_work_results:
            logger.warning(
                "gather_evidence: task-work results missing for %s: %s",
                task_id, task_work_results.get("error", "unknown"),
            )
            return CoachEvidenceBundle(
                honesty=default_honest,
                gathering_status="partial_exception",
                gathering_error=(
                    f"missing_results: {task_work_results.get('error', 'unknown')}"
                ),
                task_type=task_type.value,
                profile_name=profile_name,
            )

        # ------------------------------------------------------------------
        # 1. Honesty verification. Mirrors validate() lines 918-952.
        # ------------------------------------------------------------------
        try:
            honesty = self._verify_honesty(task_work_results)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "gather_evidence: _verify_honesty raised unexpectedly: %s", exc,
            )
            return CoachEvidenceBundle(
                honesty=default_honest,
                gathering_status="partial_exception",
                gathering_error=f"honesty_exception: {exc}",
                task_type=task_type.value,
                profile_name=profile_name,
            )

        honesty_issues = self._honesty_issues_from(honesty)
        honesty_must_fix = [
            i for i in honesty_issues if i["severity"] == "must_fix"
        ]
        honesty_should_fix = [
            i for i in honesty_issues if i["severity"] == "should_fix"
        ]

        # Layer-2 demotion hint for the LLM Coach. Mirrors the structural
        # condition inside _honesty_issues_from (lines 5456-5460): a single
        # critical file_existence discrepancy that was Layer-1-resolved (via
        # state_bridge.canonical_path_for) is demoted from must_fix to
        # should_fix. Surface that hint structurally so the LLM Coach can
        # apply absence-of-failure guard #4 without re-deriving the demotion.
        severity_recommendations: List[Dict[str, str]] = []
        critical_discrepancies = [
            d for d in honesty.discrepancies if d.severity == "critical"
        ]
        non_audit_critical = [
            d for d in critical_discrepancies
            if d.claim_type != "claim_audit"
        ]
        if (
            len(non_audit_critical) == 1
            and non_audit_critical[0].claim_type == "file_existence"
        ):
            severity_recommendations.append({
                "recommendation": (
                    "A single file_existence discrepancy was suppressed by "
                    "Layer-1 identity resolution (state_bridge "
                    "canonical_path_for). Treat as should_fix, not must_fix. "
                    "Continue AC evaluation."
                ),
                "rule": (
                    "path-string-mismatch-is-not-dishonesty "
                    "(Layer 2 demotion)"
                ),
            })

        # Advisory issues: agent-invocations advisory (F3c) + Layer-2 honesty
        # should_fix issues. Both ride along with the final decision (approve
        # or feedback) and are surfaced to the Player so process observations
        # remain visible. Pre-computed here so the LLM Coach can read them
        # without re-deriving from raw fields.
        advisory_issues: List[Dict[str, Any]] = []
        agent_invocations_advisory = (
            self._compute_agent_invocations_advisory(task_work_results)
        )
        if agent_invocations_advisory is not None:
            advisory_issues.append(agent_invocations_advisory)
        advisory_issues.extend(honesty_should_fix)

        # Honesty short-circuit: don't run downstream gathering. Legacy
        # validate() also short-circuits here.
        if honesty_must_fix:
            logger.warning(
                "gather_evidence: honesty produced %d must_fix issue(s) "
                "for %s; downstream gathering skipped.",
                len(honesty_must_fix), task_id,
            )
            return CoachEvidenceBundle(
                honesty=honesty,
                gathering_status="partial_honesty_abort",
                severity_recommendations=severity_recommendations,
                advisory_issues=advisory_issues,
                task_type=task_type.value,
                profile_name=profile_name,
            )

        # ------------------------------------------------------------------
        # 2. Quality gates. Mirrors validate() lines 1130-1132.
        # ------------------------------------------------------------------
        try:
            gates = self.verify_quality_gates(
                task_work_results,
                profile=profile,
                skip_arch_review=skip_arch_review,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "gather_evidence: verify_quality_gates raised: %s", exc,
            )
            return CoachEvidenceBundle(
                honesty=honesty,
                gathering_status="partial_exception",
                gathering_error=f"quality_gates_exception: {exc}",
                severity_recommendations=severity_recommendations,
                advisory_issues=advisory_issues,
                task_type=task_type.value,
                profile_name=profile_name,
            )

        # Build the evidence dict slices the LLM Coach reads.
        quality_gates_raw = task_work_results.get("quality_gates")
        if not isinstance(quality_gates_raw, dict):
            quality_gates_raw = {}

        coverage_details: Dict[str, Any] = {
            "coverage_met": quality_gates_raw.get("coverage_met"),
            "line_coverage": quality_gates_raw.get("line_coverage"),
            "branch_coverage": quality_gates_raw.get("branch_coverage"),
            "line_threshold": quality_gates_raw.get("line_threshold"),
            "branch_threshold": quality_gates_raw.get("branch_threshold"),
            "coverage_required": gates.coverage_required,
        }

        tests_dict: Dict[str, Any] = {
            "tests_passed": gates.tests_passed,
            "tests_required": gates.tests_required,
            "tests_run": quality_gates_raw.get("tests_run"),
            "tests_failed": quality_gates_raw.get("tests_failed"),
            "all_passed": quality_gates_raw.get("all_passed"),
            "requires_infrastructure": task.get("requires_infrastructure"),
        }

        plan_audit_raw = task_work_results.get("plan_audit")
        plan_audit_dict: Optional[Dict[str, Any]] = (
            plan_audit_raw if isinstance(plan_audit_raw, dict) else None
        )

        code_review_raw = task_work_results.get("code_review")
        arch_review_dict: Optional[Dict[str, Any]] = None
        if isinstance(code_review_raw, dict):
            arch_review_dict = {
                "score": code_review_raw.get("score"),
                "threshold": getattr(profile, "arch_review_threshold", 60),
                "passed": gates.arch_review_passed,
                "required": gates.arch_review_required,
            }
            # Surface any sub-scores the producer wrote (solid/dry/yagni).
            for sub in ("solid_score", "dry_score", "yagni_score"):
                if sub in code_review_raw:
                    arch_review_dict[sub] = code_review_raw[sub]

        # ------------------------------------------------------------------
        # BDD evidence. TASK-BDDW-001: wire factory BDD plugin discovery
        # into the Coach evidence path.
        #
        # Priority:
        #   1. Factory discovery (guardkitfactory.bdd.discover) — if available
        #      and stack profile is known, run the BDD plugin and map the
        #      result into bundle.bdd shape.
        #   2. Player-reported bdd_results — legacy fallback when the factory
        #      is unavailable, the stack is unknown, or discovery fails.
        # ------------------------------------------------------------------
        _reset_factory_cache()

        bdd_raw = task_work_results.get("bdd_results")
        bdd_dict: Optional[Dict[str, Any]] = None

        if bdd_raw is not None and isinstance(bdd_raw, dict):
            # Player already produced BDD results — use them as-is.
            bdd_dict = bdd_raw
        elif _is_factory_available():
            # Factory is available but Player didn't produce results.
            # Attempt independent discovery via the factory plugin.
            stack_profile = _detect_stack_profile(self.worktree_path)
            factory_result = _run_factory_bdd(self.worktree_path, stack_profile)
            if factory_result is not None:
                bdd_dict = factory_result
                logger.info(
                    "gather_evidence: BDD evidence from factory plugin "
                    "(stack=%s, scenarios_attempted=%s).",
                    stack_profile,
                    factory_result.get("scenarios_attempted"),
                )
            else:
                logger.debug(
                    "gather_evidence: factory BDD discovery returned None; "
                    "bdd field left as absent signal.",
                )
        else:
            # Factory unavailable — bdd_dict stays None (absent signal).
            logger.debug(
                "gather_evidence: guardkitfactory not available; "
                "Player-reported bdd_results were empty; "
                "bdd field left as absent signal.",
            )

        # Quality-gate-failure short-circuit. Legacy validate() also
        # short-circuits here via _feedback_from_gates.
        if not gates.all_gates_passed:
            logger.info(
                "gather_evidence: quality gates failed for %s; downstream "
                "(requirements, independent tests) skipped.", task_id,
            )
            return CoachEvidenceBundle(
                honesty=honesty,
                gathering_status="partial_gate_abort",
                quality_gates=gates,
                coverage_details=coverage_details,
                plan_audit=plan_audit_dict,
                bdd=bdd_dict,
                arch_review=arch_review_dict,
                tests=tests_dict,
                severity_recommendations=severity_recommendations,
                advisory_issues=advisory_issues,
                task_type=task_type.value,
                profile_name=profile_name,
            )

        # ------------------------------------------------------------------
        # 3. Requirements validation. Mirrors validate() line 1139.
        # Hoisted ahead of independent-test in the legacy path; preserved
        # here for the same reason — cheaper, idempotent.
        # ------------------------------------------------------------------
        try:
            requirements = self.validate_requirements(
                task, task_work_results, turn=turn
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "gather_evidence: validate_requirements raised: %s", exc,
            )
            return CoachEvidenceBundle(
                honesty=honesty,
                gathering_status="partial_exception",
                gathering_error=f"requirements_exception: {exc}",
                quality_gates=gates,
                coverage_details=coverage_details,
                plan_audit=plan_audit_dict,
                bdd=bdd_dict,
                arch_review=arch_review_dict,
                tests=tests_dict,
                severity_recommendations=severity_recommendations,
                advisory_issues=advisory_issues,
                task_type=task_type.value,
                profile_name=profile_name,
            )

        # ------------------------------------------------------------------
        # 4. Independent tests. Mirrors validate() lines 1156-1175.
        # ------------------------------------------------------------------
        if not profile.tests_required:
            test_result: IndependentTestResult = IndependentTestResult(
                tests_passed=True,
                test_command="skipped",
                test_output_summary=(
                    f"Independent test verification skipped "
                    f"(tests not required for {task_type.value} tasks)"
                ),
                duration_seconds=0.0,
            )
            logger.info(
                "gather_evidence: independent test verification skipped for "
                "%s (tests not required for %s tasks)",
                task_id, task_type.value,
            )
        else:
            try:
                test_result = self.run_independent_tests(
                    task_work_results=task_work_results,
                    task=task,
                    turn=turn,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "gather_evidence: run_independent_tests raised: %s", exc,
                )
                return CoachEvidenceBundle(
                    honesty=honesty,
                    gathering_status="partial_exception",
                    gathering_error=f"independent_tests_exception: {exc}",
                    quality_gates=gates,
                    coverage_details=coverage_details,
                    plan_audit=plan_audit_dict,
                    bdd=bdd_dict,
                    arch_review=arch_review_dict,
                    tests=tests_dict,
                    requirements=requirements,
                    severity_recommendations=severity_recommendations,
                    advisory_issues=advisory_issues,
                    task_type=task_type.value,
                    profile_name=profile_name,
                )

        return CoachEvidenceBundle(
            honesty=honesty,
            gathering_status="complete",
            quality_gates=gates,
            coverage_details=coverage_details,
            plan_audit=plan_audit_dict,
            bdd=bdd_dict,
            arch_review=arch_review_dict,
            tests=tests_dict,
            independent_tests=test_result,
            requirements=requirements,
            severity_recommendations=severity_recommendations,
            advisory_issues=advisory_issues,
            task_type=task_type.value,
            profile_name=profile_name,
        )

    def _compute_agent_invocations_advisory(
        self, task_work_results: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Compute the non-blocking agent-invocations advisory issue.

        Extracted from ``validate()`` lines 1028-1126 (TASK-FIX-RWOP1.3.1 /
        TASK-REV-F6E1 F3c) for reuse by ``gather_evidence()`` (TASK-HMIG-008R
        Part A). Returns ``None`` when no advisory is needed.

        The logic mirrors the inline computation in ``validate()``: a
        ``"violation"`` status in ``task_work_results['agent_invocations_validation']``
        produces a ``severity == "warning"`` advisory naming the missing
        phases and recommending stack-specific specialists. ``"passed"``,
        ``"validator_error"``, and ``"no_data"`` statuses are not advised
        on — they ride through without comment.
        """
        agent_invocations_validation = task_work_results.get(
            "agent_invocations_validation"
        )
        if not (
            isinstance(agent_invocations_validation, dict)
            and agent_invocations_validation.get("status") == "violation"
        ):
            return None

        raw_missing = agent_invocations_validation.get("missing_phases") or []
        missing_phases: List[str] = []
        if raw_missing and isinstance(raw_missing[0], dict):
            missing_phases = [
                str(m.get("phase", ""))
                for m in raw_missing
                if m.get("phase")
            ]
        else:
            missing_phases = [str(m) for m in raw_missing]
        missing_phases_sorted = sorted(missing_phases)
        missing_phases_with_names = ", ".join(
            f"{p} ({PHASE_DESCRIPTIONS.get(p, 'Unknown')})"
            for p in missing_phases_sorted
        ) if missing_phases_sorted else "unknown"

        stack_template = detect_stack_template(self.worktree_path)
        specialist_lines = render_missing_phase_list(
            missing_phases_sorted,
            stack_template=stack_template,
            workspace_root=self.worktree_path,
        )
        specialist_block = "\n".join(
            f"- {line}" for line in specialist_lines
        )

        expected_phases_val = agent_invocations_validation.get("expected_phases")
        actual_invocations_val = agent_invocations_validation.get("actual_invocations")
        expected_str = (
            str(expected_phases_val) if expected_phases_val is not None else "?"
        )
        actual_str = (
            str(actual_invocations_val)
            if actual_invocations_val is not None
            else "?"
        )

        return {
            "severity": "warning",
            "category": "agent_invocations_advisory",
            "description": (
                f"Advisory (non-blocking): task-work produced a report with "
                f"{actual_str} of {expected_str} expected agent invocations. "
                f"Missing phases: {missing_phases_with_names}. "
                f"Consider invoking these agents via the Task tool to "
                f"strengthen stack-specific quality:\n{specialist_block}"
            ),
            "details": {
                "missing_phases": missing_phases_sorted,
                "expected_phases": expected_phases_val,
                "actual_invocations": actual_invocations_val,
            },
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

    def verify_quality_gates(
        self,
        task_work_results: Dict[str, Any],
        profile: Optional[QualityGateProfile] = None,
        skip_arch_review: bool = False,
    ) -> QualityGateStatus:
        """
        Verify task-work quality gates passed.

        Checks the following gates from task-work results, respecting the quality
        gate profile which determines which gates are required for the task type:
        - tests_passed: From Phase 4.5 test results
        - coverage_met: From Phase 4.5 coverage check
        - arch_review_passed: From Phase 5 code review (score >= threshold)
        - plan_audit_passed: From Phase 5.5 plan audit (0 violations)

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Results from task-work execution
        profile : Optional[QualityGateProfile]
            Quality gate profile for task type. If None, uses FEATURE profile
            (backward compatible with existing calls without profile parameter).
        skip_arch_review : bool
            If True, skip architectural review gate regardless of profile setting.
            Used for --implement-only mode where Phase 2.5B doesn't run.
            Default: False (enforce arch review per profile).

        Returns
        -------
        QualityGateStatus
            Status of all quality gates with requirement flags
        """
        # Use default profile for backward compatibility
        if profile is None:
            profile = self.DEFAULT_PROFILE
        # Log input structure and profile for debugging
        logger.debug(f"task_work_results keys: {list(task_work_results.keys())}")
        logger.debug(f"quality_gates content: {task_work_results.get('quality_gates', 'NOT_FOUND')}")
        logger.debug(f"code_review content: {task_work_results.get('code_review', 'NOT_FOUND')}")
        logger.debug(f"plan_audit content: {task_work_results.get('plan_audit', 'NOT_FOUND')}")
        logger.debug(
            f"Profile requirements: tests={profile.tests_required}, "
            f"coverage={profile.coverage_required}, "
            f"arch_review={profile.arch_review_required}, "
            f"plan_audit={profile.plan_audit_required}"
        )

        # Read from quality_gates object (what writer actually creates)
        quality_gates = task_work_results.get("quality_gates", {})

        # Test results - use all_passed if present, otherwise check tests_failed
        # If tests not required by profile, default to True (skip gate)
        if not profile.tests_required:
            tests_passed = True
            logger.debug("Tests not required per task type profile, skipping")
        elif "all_passed" in quality_gates:
            all_passed_value = quality_gates["all_passed"]
            if all_passed_value is None:
                # Player session didn't reach quality gate evaluation (e.g. exhausted SDK turns)
                # Fall through to tests_failed check for partial data
                if "tests_failed" in quality_gates:
                    tests_failed_count = quality_gates["tests_failed"]
                    tests_passed = tests_failed_count == 0
                    logger.debug(
                        f"all_passed is null, falling back to tests_failed={tests_failed_count}, "
                        f"tests_passed={tests_passed}"
                    )
                else:
                    tests_passed = False
                    logger.debug("all_passed is null and no tests_failed data, defaulting to False")
            else:
                tests_passed = all_passed_value
                logger.debug(f"Extracted tests_passed={tests_passed} from quality_gates.all_passed")
        elif "tests_failed" in quality_gates:
            # If we have test counts, check if any failed
            tests_failed = quality_gates["tests_failed"]
            tests_passed = tests_failed == 0
            logger.debug(f"Extracted tests_passed={tests_passed} from quality_gates.tests_failed={tests_failed}")
        else:
            # No quality_gates data at all - assume failure
            tests_passed = False
            logger.debug("No tests_passed or tests_failed found in quality_gates, defaulting to False")

        # Coverage - read from quality_gates.coverage_met
        # If coverage not required by profile, default to True (skip gate)
        if not profile.coverage_required:
            coverage_met = True
            logger.debug("Coverage not required per task type profile, skipping")
        else:
            # Handle None explicitly: treat as "not measured" = pass (same as coverage not required)
            coverage_met_value = quality_gates.get("coverage_met")
            coverage_met = coverage_met_value if coverage_met_value is not None else True
            logger.debug(f"Extracted coverage_met={coverage_met} from quality_gates.coverage_met (raw={coverage_met_value})")

        # Architectural review - may be in separate code_review field or not present
        # If arch review not required by profile OR skip_arch_review=True, default to True (skip gate)
        if skip_arch_review:
            arch_review_passed = True
            logger.debug("Architectural review skipped (skip_arch_review=True, implement-only mode)")
        elif not profile.arch_review_required:
            arch_review_passed = True
            logger.debug("Architectural review not required per task type profile, skipping")
        else:
            code_review = task_work_results.get("code_review", {})
            arch_score = code_review.get("score", 0)  # Default to 0 if not present
            arch_review_passed = arch_score >= profile.arch_review_threshold
            logger.debug(
                f"Extracted arch_review_passed={arch_review_passed} "
                f"(score={arch_score}, threshold={profile.arch_review_threshold})"
            )

        # Plan audit - separate field
        # If plan audit not required by profile, default to True (skip gate)
        if not profile.plan_audit_required:
            plan_audit_passed = True
            logger.debug("Plan audit not required per task type profile, skipping")
        else:
            plan_audit = task_work_results.get("plan_audit", {})
            # TASK-FIX-RWOP1.3.2: the producer writes a status-typed block
            # (passed | violation | skipped | auditor_error). "skipped"
            # means no plan on disk — don't fail the gate on absent data.
            # "auditor_error" means the deterministic auditor itself crashed;
            # non-blocking for the same reason validator_error is
            # non-blocking on the agent_invocations gate — a gate failing
            # to run is not evidence of a task failing. severity == "high"
            # is the new authoritative block signal; the legacy violations
            # count is preserved as a back-compat OR-gate for fixtures and
            # older Player reports that don't emit severity.
            plan_audit_status = plan_audit.get("status")
            severity = plan_audit.get("severity")
            violations = plan_audit.get("violations", 0)

            if plan_audit_status in ("skipped", "auditor_error"):
                plan_audit_passed = True
                logger.debug(
                    f"Plan audit status={plan_audit_status} — treated as pass "
                    f"(non-blocking informational status)"
                )
            elif severity == "high":
                plan_audit_passed = False
                logger.debug(
                    f"Plan audit rejected: severity=high "
                    f"(violations={violations}, status={plan_audit_status})"
                )
            else:
                plan_audit_passed = violations == 0
                logger.debug(
                    f"Extracted plan_audit_passed={plan_audit_passed} "
                    f"(violations={violations}, severity={severity}, "
                    f"status={plan_audit_status})"
                )

        # Determine effective arch_review_required (False if skip_arch_review=True)
        effective_arch_review_required = profile.arch_review_required and not skip_arch_review

        status = QualityGateStatus(
            tests_passed=tests_passed,
            coverage_met=coverage_met,
            arch_review_passed=arch_review_passed,
            plan_audit_passed=plan_audit_passed,
            tests_required=profile.tests_required,
            coverage_required=profile.coverage_required,
            arch_review_required=effective_arch_review_required,
            plan_audit_required=profile.plan_audit_required,
        )

        # Log final decision at INFO level for visibility
        logger.info(
            f"Quality gate evaluation complete: "
            f"tests={status.tests_passed} (required={status.tests_required}), "
            f"coverage={status.coverage_met} (required={status.coverage_required}), "
            f"arch={status.arch_review_passed} (required={status.arch_review_required}), "
            f"audit={status.plan_audit_passed} (required={status.plan_audit_required}), "
            f"ALL_PASSED={status.all_gates_passed}"
        )

        return status

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
        from contextlib import contextmanager

        # ``select_harness``, harness event types, ``AgentInvocationError``,
        # and ``check_assistant_message_error`` are imported at module top
        # (TASK-HMIG-006.3) so ``coach_validator.select_harness`` is a
        # stable patch target. ``asyncio`` / ``time`` / ``contextmanager``
        # remain method-local to preserve the historic lazy-import shape
        # for the rest of the method body.

        @contextmanager
        def _patched_pythonpath(prepend: str):
            """Scope PYTHONPATH mutation to harness.invoke() (Step D).

            ``ClaudeSDKHarness`` does not accept an ``env=`` kwarg
            (sdk_harness.py:130-158); adding one would widen the
            harness interface for a Coach-only concern (ISP). Mutating
            ``os.environ`` in a tight scope lets the SDK subprocess
            inherit PYTHONPATH naturally. The single-coach-turn-per-
            worktree invariant makes this process-global side effect
            acceptable; do not lift this helper to a module-level
            utility without reconsidering thread-safety.
            """
            original = os.environ.get("PYTHONPATH")
            current = os.environ.get("PYTHONPATH", "")
            new = f"{prepend}:{current}" if current else prepend
            os.environ["PYTHONPATH"] = new
            try:
                yield
            finally:
                if original is None:
                    os.environ.pop("PYTHONPATH", None)
                else:
                    os.environ["PYTHONPATH"] = original

        @contextmanager
        def _patched_path(venv_bin: Optional[str]):
            """Scope a venv-bin PATH prepend to harness.invoke (TASK-FIX-COACHPYENV).

            Defence-in-depth companion to the ``-m pytest`` interpreter pin: the
            SDK harness spawns a Bash subprocess that inherits ``os.environ``, so
            prepending the bootstrap venv ``bin`` here means even a bare
            ``pytest``/``python`` the tests shell out to resolves inside the
            bootstrap environment, not the host Python 3.14 framework. No-op when
            no venv is resolved. Same single-coach-turn-per-worktree invariant as
            ``_patched_pythonpath`` makes this process-global mutation acceptable.
            """
            if not venv_bin:
                yield
                return
            original = os.environ.get("PATH")
            current = os.environ.get("PATH", "")
            os.environ["PATH"] = (
                f"{venv_bin}{os.pathsep}{current}" if current else venv_bin
            )
            try:
                yield
            finally:
                if original is None:
                    os.environ.pop("PATH", None)
                else:
                    os.environ["PATH"] = original

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
                "harness": os.environ.get("GUARDKIT_HARNESS", "sdk"),
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
            with _patched_pythonpath(worktree_str), _patched_path(venv_bin):
                harness = select_harness(
                    sdk_timeout_seconds=self.test_timeout,
                    allowed_tools=["Bash"],
                    permission_mode="bypassPermissions",
                    max_turns=1,
                    model=model,
                    cwd=self.worktree_path,
                )

                async with asyncio.timeout(self.test_timeout):
                    # TASK-FIX-LGACLOSE: finalise the harness async generator on
                    # every exit (incl. timeout/cancel) via aclosing() so no
                    # orphaned async_generator_athrow survives interpreter shutdown.
                    async with aclosing(
                        harness.invoke(
                            prompt=prompt,
                            role="coach_test",
                            tools=["Bash"],
                            cwd=self.worktree_path,
                            timeout_seconds=self.test_timeout,
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
                return IndependentTestResult(
                    tests_passed=False,
                    test_command=test_cmd,
                    test_output_summary=f"SDK API error: {api_error}",
                    duration_seconds=duration,
                    raw_output=f"SDK API error: {api_error}",
                    # TASK-FIX-COACHTESTTO: transport-layer failure — the
                    # oracle never produced a verdict. ABSENT, not a fail.
                    signal_absent=True,
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
                return IndependentTestResult(
                    tests_passed=False,
                    test_command=test_cmd,
                    test_output_summary=summary,
                    duration_seconds=duration,
                    raw_output=output_text,
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
                return IndependentTestResult(
                    tests_passed=True,
                    test_command=test_cmd,
                    test_output_summary=summary,
                    duration_seconds=duration,
                    raw_output=output_text,
                )
            else:
                # GAP-FIX #7: is_error is None — parse output text
                output_text = bash_output or "\n".join(collected_text) or "No output"
                summary = self._summarize_test_output(output_text)
                logger.debug(
                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
                )
                # Heuristic: check for failure indicators in output
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
                return IndependentTestResult(
                    tests_passed=tests_passed,
                    test_command=test_cmd,
                    test_output_summary=summary,
                    duration_seconds=duration,
                    raw_output=output_text,
                )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"SDK coach test execution timed out after {self.test_timeout}s")
            return IndependentTestResult(
                tests_passed=False,
                test_command=test_cmd,
                test_output_summary=f"SDK test execution timed out after {self.test_timeout}s",
                duration_seconds=duration,
                raw_output=f"Timeout after {self.test_timeout}s",
                # TASK-FIX-COACHTESTTO: the oracle did not complete — ABSENT,
                # not a real pass/fail verdict.
                signal_absent=True,
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
            os.environ.get("GUARDKIT_HARNESS", "sdk").strip().lower()
            == "langgraph"
        )

    def _resolve_matching_strategy(self) -> str:
        """Resolve effective matching strategy to ``'text'`` or ``'semantic'``.

        When configured as ``'auto'``, returns ``'semantic'`` if
        ``ANTHROPIC_BASE_URL`` points to a non-Anthropic endpoint (e.g. vLLM),
        otherwise ``'text'``.
        """
        if self._matching_strategy == "auto":
            is_custom = self._is_custom_api_base()
            effective = "semantic" if is_custom else "text"
            logger.info(
                "Matching strategy auto-resolved to '%s' (custom_api=%s)",
                effective,
                is_custom,
            )
            return effective
        return self._matching_strategy

    # Directories to skip when copying worktree for isolated test execution.
    _ISOLATION_SKIP_DIRS: set = {
        ".git", "__pycache__", ".guardkit", ".venv", "venv", "node_modules",
        ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", "*.egg-info",
    }

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

    def _pin_pytest_command(self, test_cmd: str) -> str:
        """Rewrite a bare ``pytest …`` command to pin the bootstrap interpreter.

        TASK-FIX-COACHPYENV: the SDK test path hands ``test_cmd`` to a Bash tool,
        which resolves ``pytest`` via PATH. Rewriting to
        ``<venv_python> -m pytest …`` makes the Bash subprocess invoke the exact
        interpreter regardless of PATH ordering. No-op when no venv is resolved
        or the command is not a bare ``pytest`` invocation.
        """
        if self._venv_python is None:
            return test_cmd
        if test_cmd.startswith("pytest "):
            return f"{self._pytest_interpreter()} -m {test_cmd}"
        if test_cmd == "pytest":
            return f"{self._pytest_interpreter()} -m pytest"
        return test_cmd

    def _pytest_env(self) -> Dict[str, str]:
        """Environment for subprocess pytest runs, with venv bin on PATH.

        TASK-FIX-COACHPYENV: pinning ``argv[0]`` to the venv interpreter is the
        load-bearing fix; prepending the venv ``bin`` to PATH is defence-in-depth
        so any nested ``python``/console-script the tests shell out to also
        resolves inside the bootstrap environment. Falls back to the parent
        environment when no venv exists.
        """
        from guardkit.orchestrator.quality_gates.command_models import (
            build_venv_env,
        )

        return build_venv_env(self.worktree_path) or dict(os.environ)

    def _run_isolated_tests(self, test_cmd: str) -> "IndependentTestResult":
        """
        Run tests in an isolated temporary directory (Option B: tempdir copy).

        Copies the worktree to a temp directory, excluding large/irrelevant
        directories, and runs tests there.  This prevents spurious failures
        caused by concurrent mutations from other tasks running in the same
        parallel wave.

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
        import tempfile

        start_time = time.time()
        logger.info(
            f"[TASK-ABFIX-005] Running isolated tests (wave_size={self.wave_size}): {test_cmd}"
        )

        try:
            with tempfile.TemporaryDirectory(prefix="guardkit-coach-iso-") as tmpdir:
                tmpdir_path = Path(tmpdir)

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

                logger.info(
                    f"[TASK-ABFIX-005] Worktree snapshot created at {tmpdir_path}"
                )

                # Run tests in the isolated copy
                if test_cmd.startswith("pytest"):
                    parts = test_cmd.split()
                    # TASK-FIX-COACHPYENV: pin pytest to the bootstrap venv
                    # interpreter, never sys.executable / PATH pytest.
                    cmd = [self._pytest_interpreter(), "-m", "pytest"] + parts[1:]
                    result = subprocess.run(
                        cmd,
                        cwd=str(tmpdir_path),
                        capture_output=True,
                        text=True,
                        timeout=self.test_timeout,
                        env=self._pytest_env(),
                    )
                else:
                    result = subprocess.run(
                        test_cmd,
                        shell=True,
                        cwd=str(tmpdir_path),
                        capture_output=True,
                        text=True,
                        timeout=self.test_timeout,
                    )

                duration = time.time() - start_time
                tests_passed = result.returncode == 0
                output = result.stdout or result.stderr or "No output"
                summary = self._summarize_test_output(output)

                logger.info(
                    f"[TASK-ABFIX-005] Isolated tests {'passed' if tests_passed else 'failed'} "
                    f"in {duration:.1f}s"
                )

                return IndependentTestResult(
                    tests_passed=tests_passed,
                    test_command=test_cmd,
                    test_output_summary=summary,
                    duration_seconds=duration,
                    raw_output=(result.stdout or "") + (result.stderr or ""),
                )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"[TASK-ABFIX-005] Isolated test execution timed out after {self.test_timeout}s")
            return IndependentTestResult(
                tests_passed=False,
                test_command=test_cmd,
                test_output_summary=f"Isolated test execution timed out after {self.test_timeout}s",
                duration_seconds=duration,
                # TASK-FIX-COACHTESTTO: timeout — oracle did not complete.
                signal_absent=True,
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[TASK-ABFIX-005] Isolated test execution failed: {e}")
            return IndependentTestResult(
                tests_passed=False,
                test_command=test_cmd,
                test_output_summary=f"Isolated test execution failed: {e}",
                duration_seconds=duration,
                # TASK-FIX-COACHTESTTO: execution error before any verdict.
                signal_absent=True,
            )

    def run_independent_tests(
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
        test_cmd = self.test_command or self._detect_test_command(
            self.task_id, task_work_results=task_work_results, turn=turn
        )

        # If test_cmd is None, it means task-specific filtering was requested
        # but no matching tests were found. Skip verification in this case.
        if test_cmd is None:
            logger.info(f"No task-specific tests found for {self.task_id}, skipping independent verification")
            return IndependentTestResult(
                tests_passed=True,
                test_command="skipped",
                test_output_summary=f"No task-specific tests found for {self.task_id}, skipping independent verification",
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
            use_sdk = (
                self._coach_test_execution == "sdk"
                and not requires_infra
                and not self._is_custom_api_base()
                and not self._is_langgraph_harness()
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
                    result = loop.run_until_complete(self._run_tests_via_sdk(test_cmd))
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
            if self.is_parallel and not use_sdk:
                logger.info(
                    f"[TASK-ABFIX-005] Parallel wave detected (wave_size={self.wave_size}), "
                    f"running tests in isolated temp directory"
                )
                return self._run_isolated_tests(test_cmd)

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
                    cmd = [self._pytest_interpreter(), "-m", "pytest"] + parts[1:]
                    result = subprocess.run(
                        cmd,
                        cwd=str(self.worktree_path),
                        capture_output=True,
                        text=True,
                        timeout=self.test_timeout,
                        env=self._pytest_env(),
                    )
                else:
                    result = subprocess.run(
                        test_cmd,
                        shell=True,
                        cwd=str(self.worktree_path),
                        capture_output=True,
                        text=True,
                        timeout=self.test_timeout,
                    )

                duration = time.time() - start_time
                tests_passed = result.returncode == 0

                # Summarize output (truncate if too long)
                output = result.stdout or result.stderr or "No output"
                summary = self._summarize_test_output(output)

                logger.info(
                    f"Independent tests {'passed' if tests_passed else 'failed'} "
                    f"in {duration:.1f}s"
                )

                return IndependentTestResult(
                    tests_passed=tests_passed,
                    test_command=test_cmd,
                    test_output_summary=summary,
                    duration_seconds=duration,
                    raw_output=(result.stdout or "") + (result.stderr or ""),
                )

            except subprocess.TimeoutExpired:
                duration = time.time() - start_time
                logger.error(f"Test execution timed out after {self.test_timeout}s")
                return IndependentTestResult(
                    tests_passed=False,
                    test_command=test_cmd,
                    test_output_summary=f"Test execution timed out after {self.test_timeout}s",
                    duration_seconds=duration,
                    # TASK-FIX-COACHTESTTO: timeout — oracle did not complete.
                    signal_absent=True,
                )
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Test execution failed: {e}")
                return IndependentTestResult(
                    tests_passed=False,
                    test_command=test_cmd,
                    test_output_summary=f"Test execution failed: {e}",
                    duration_seconds=duration,
                    # TASK-FIX-COACHTESTTO: execution error before any verdict.
                    signal_absent=True,
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

    def _start_infrastructure_containers(self, services: List[str]) -> None:
        """Start Docker containers for each declared infrastructure service.

        Uses recipes from :mod:`guardkit.orchestrator.docker_fixtures`.
        Unknown services are logged as warnings and skipped.
        Environment variables (e.g., DATABASE_URL) are set in the current
        process via :func:`os.environ`.

        Args:
            services: List of service names (e.g., ``["postgresql", "redis"]``)
        """
        for service in services:
            if not is_known_service(service):
                logger.warning("Unknown infrastructure service %r, skipping.", service)
                continue
            logger.info("Starting Docker container for service: %s", service)
            commands = get_start_commands(service)
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
            # Set environment variables for test execution
            env_vars = get_env_exports(service)
            for key, value in env_vars.items():
                os.environ[key] = value
                logger.info("Set %s=%s", key, value)

    def _stop_infrastructure_containers(self, services: List[str]) -> None:
        """Tear down Docker containers for each declared infrastructure service.

        Runs ``docker rm -f <container_name>`` for each known service.
        Unknown services are silently skipped. Errors during teardown
        are logged but do not raise.

        Args:
            services: List of service names (e.g., ``["postgresql", "redis"]``)
        """
        for service in services:
            if not is_known_service(service):
                continue
            container_name = get_container_name(service)
            logger.info("Stopping Docker container: %s", container_name)
            try:
                subprocess.run(
                    ["docker", "rm", "-f", container_name],
                    capture_output=True,
                    cwd=str(self.worktree_path),
                )
            except Exception as e:
                logger.warning(
                    "Failed to stop container %s: %s", container_name, e
                )
            # Clean up environment variables
            env_vars = get_env_exports(service)
            for key in env_vars:
                os.environ.pop(key, None)

    def validate_requirements(
        self,
        task: Dict[str, Any],
        task_work_results: Dict[str, Any],
        turn: Optional[int] = None,
    ) -> RequirementsValidation:
        """
        Validate all requirements and acceptance criteria are met.

        Uses two matching strategies in priority order:

        1. **ID-based matching** via ``completion_promises`` from the Player
           report (``player_turn_N.json``). Each promise has a ``criterion_id``
           (e.g. ``AC-001``) and ``status`` (``complete``/``incomplete``).
           This is the preferred strategy because IDs are exact.

        2. **Text matching** via ``requirements_met`` from
           ``task_work_results.json``. Falls back to this when no
           completion promises are available (legacy path).

        Parameters
        ----------
        task : Dict[str, Any]
            Task data including acceptance_criteria
        task_work_results : Dict[str, Any]
            Results from task-work execution
        turn : Optional[int]
            Current turn number. When provided, reads the Player report
            from ``player_turn_{turn}.json`` to extract completion promises.

        Returns
        -------
        RequirementsValidation
            Validation result with met/missing criteria and per-criterion results
        """
        acceptance_criteria = task.get("acceptance_criteria", [])

        # Criteria classifier routing (TASK-CRV-412F): classify criteria and
        # route file_content through existing paths; exclude command_execution
        # (Path D, TASK-CRV-537E) and skip manual criteria from the threshold.
        # Graceful fallback: if classifier errors, all criteria use existing paths.
        try:
            from guardkit.orchestrator.quality_gates.criteria_classifier import (
                classify_acceptance_criteria,
            )
            _clf = classify_acceptance_criteria(acceptance_criteria)
            for _c in _clf.file_content_criteria:
                logger.debug(
                    "criteria-classifier: FILE_CONTENT (confidence=%.2f): %.80s",
                    _c.confidence,
                    _c.text,
                )
            for _c in _clf.command_criteria:
                logger.debug(
                    "criteria-classifier: COMMAND_EXECUTION excluded (confidence=%.2f): %.80s",
                    _c.confidence,
                    _c.text,
                )
            for _c in _clf.manual_criteria:
                logger.debug(
                    "criteria-classifier: MANUAL skipped (confidence=%.2f): %.80s",
                    _c.confidence,
                    _c.text,
                )
            if _clf.command_criteria or _clf.manual_criteria:
                logger.debug(
                    "criteria-classifier: routing %d file_content, "
                    "%d command_execution (excluded), %d manual (skipped) of %d total",
                    len(_clf.file_content_criteria),
                    len(_clf.command_criteria),
                    len(_clf.manual_criteria),
                    _clf.total_count,
                )
                acceptance_criteria = [_c.text for _c in _clf.file_content_criteria]
        except Exception as _clf_err:
            logger.debug(
                "criteria-classifier: classification error, falling through: %s",
                _clf_err,
            )

        # Synthetic report path (TASK-ASF-006, TASK-FIX-ASPF-006)
        is_synthetic = task_work_results.get("_synthetic", False)
        if is_synthetic:
            logger.info(
                "Synthetic report detected — using file-existence verification"
            )
            # Load promises (may be from file-existence generation)
            completion_promises = self._load_completion_promises(
                task_work_results, turn
            )
            if completion_promises:
                validation = self._match_by_promises(
                    acceptance_criteria, completion_promises
                )
                # Hybrid fallback for synthetic path (TASK-FIX-ASPF-006):
                # If promises don't cover all criteria, try text matching
                # against requirements_addressed (same logic as normal path).
                if not validation.all_criteria_met:
                    requirements_addressed = task_work_results.get(
                        "requirements_addressed",
                        task_work_results.get("requirements_met", []),
                    )
                    if requirements_addressed:
                        validation = self._hybrid_fallback(
                            validation, acceptance_criteria, requirements_addressed
                        )
                        logger.info(
                            "Synthetic path: applied hybrid fallback with "
                            "%d requirements_addressed entries",
                            len(requirements_addressed),
                        )
                # Always log criteria verification at DEBUG level (TASK-FIX-54F6)
                logger.debug(
                    "Criteria verification %d/%d (synthetic) - completion_promises: %s",
                    validation.criteria_met,
                    validation.criteria_total,
                    completion_promises,
                )
                for cr in validation.criteria_results:
                    logger.debug(
                        "  %s [%s]: %.80s - %s",
                        cr.criterion_id,
                        cr.result,
                        cr.criterion_text,
                        cr.evidence,
                    )
                # Diagnostic logging for 0/N on synthetic path (TASK-ACR-003)
                if validation.criteria_met == 0 and validation.criteria_total > 0:
                    logger.warning(
                        "Criteria verification 0/%d - diagnostic dump:",
                        validation.criteria_total,
                    )
                    for ac in acceptance_criteria:
                        logger.warning("  AC text: %.100s", ac)
                    logger.warning(
                        "  completion_promises: %s", completion_promises
                    )
                    logger.warning("  matching_strategy: promises+hybrid (synthetic)")
                    logger.warning("  _synthetic: True")
                return validation

            # No promises on synthetic report — try text matching fallback
            # before giving up (TASK-FIX-ASPF-006).
            requirements_addressed = task_work_results.get(
                "requirements_addressed",
                task_work_results.get("requirements_met", []),
            )
            if requirements_addressed:
                logger.info(
                    "Synthetic report has no promises but has %d "
                    "requirements_addressed — using text matching",
                    len(requirements_addressed),
                )
                return self._match_by_text(
                    acceptance_criteria, requirements_addressed
                )

            # No promises AND no requirements_addressed — all criteria unmet
            logger.warning(
                "Synthetic report has no completion_promises — "
                "all criteria marked unmet"
            )
            # Diagnostic dump for 0/N on synthetic with no promises (TASK-ACR-003)
            logger.warning(
                "Criteria verification 0/%d - diagnostic dump:",
                len(acceptance_criteria),
            )
            for ac in acceptance_criteria:
                logger.warning("  AC text: %.100s", ac)
            logger.warning("  completion_promises: (empty)")
            logger.warning("  requirements_met: (not used - synthetic path)")
            logger.warning("  matching_strategy: synthetic (no promises)")
            logger.warning("  _synthetic: True")
            return self._build_all_unmet(acceptance_criteria)

        # Normal path: promises first, then text fallback
        # Strategy 1: ID-based matching via completion_promises (preferred)
        completion_promises = self._load_completion_promises(
            task_work_results, turn
        )
        if completion_promises:
            strategy = "promises"
            validation = self._match_by_promises(acceptance_criteria, completion_promises)

            # Hybrid fallback (TASK-REV-E719 Fix 2): for criteria rejected due to
            # missing promises, try text matching against requirements_addressed.
            # This handles cases where the Player wrote fewer promises than criteria
            # (e.g., criteria parser inflation, SDK turn exhaustion).
            if not validation.all_criteria_met:
                requirements_addressed = task_work_results.get(
                    "requirements_addressed",
                    task_work_results.get("requirements_met", []),
                )
                if requirements_addressed:
                    validation = self._hybrid_fallback(
                        validation, acceptance_criteria, requirements_addressed
                    )
                    strategy = "hybrid"
        else:
            # Strategy 2: Legacy text matching via requirements_met (fallback)
            strategy = "text"
            requirements_met = task_work_results.get(
                "requirements_addressed",
                task_work_results.get("requirements_met", []),
            )
            validation = self._match_by_text(acceptance_criteria, requirements_met)

        # Always log criteria verification at DEBUG level (TASK-FIX-54F6)
        logger.debug(
            "Criteria verification %d/%d - matching_strategy: %s",
            validation.criteria_met,
            validation.criteria_total,
            strategy,
        )
        logger.debug(
            "  requirements_met: %s",
            task_work_results.get(
                "requirements_addressed",
                task_work_results.get("requirements_met", []),
            ),
        )
        if completion_promises:
            logger.debug("  completion_promises: %s", completion_promises)
        for cr in validation.criteria_results:
            logger.debug(
                "  %s [%s]: %.80s - %s",
                cr.criterion_id,
                cr.result,
                cr.criterion_text,
                cr.evidence,
            )

        # Diagnostic logging for 0/N results (TASK-ACR-003)
        if validation.criteria_met == 0 and validation.criteria_total > 0:
            logger.warning(
                "Criteria verification 0/%d - diagnostic dump:",
                validation.criteria_total,
            )
            for ac in acceptance_criteria:
                logger.warning("  AC text: %.100s", ac)
            logger.warning(
                "  requirements_met: %s",
                requirements_met if strategy == "text" else "(not used)",
            )
            logger.warning(
                "  completion_promises: %s",
                completion_promises if strategy == "promises" else "(not used)",
            )
            logger.warning("  matching_strategy: %s", strategy)
            logger.warning("  _synthetic: %s", is_synthetic)

        return validation

    def verify_command_criteria(
        self,
        acceptance_criteria: List[str],
        per_command_timeout: int = 60,
        total_timeout: int = 180,
    ) -> "CommandVerificationResult":
        """Execute command_execution acceptance criteria in the worktree.

        Classifies *acceptance_criteria* via the criteria classifier, runs each
        extracted command via ``subprocess.run()`` in ``self.worktree_path``,
        and returns structured results with classified failures.

        This method owns all runtime command verification logic, providing
        cleaner separation of concerns (TASK-RFX-7C63). The orchestrator
        delegates here and handles report injection separately.

        Parameters
        ----------
        acceptance_criteria : List[str]
            Raw acceptance criteria text from the task.
        per_command_timeout : int
            Per-command timeout in seconds (default: 60).
        total_timeout : int
            Aggregate timeout across all commands in seconds (default: 180).

        Returns
        -------
        CommandVerificationResult
            Aggregate result with per-command results, classified failures,
            and passed criteria texts.
        """
        from guardkit.orchestrator.quality_gates.command_models import (
            CommandExecutionResult,
            CommandVerificationResult,
            _assert_worktree_path,
            normalise_pip_command,
            build_venv_env,
        )
        from guardkit.orchestrator.quality_gates.criteria_classifier import (
            classify_acceptance_criteria as _classify,
        )
        from guardkit.orchestrator.quality_gates.command_failure_classifier import (
            classify_command_failure,
            CommandFailureRecord,
        )

        verification = CommandVerificationResult()

        classification = _classify(acceptance_criteria)
        command_criteria = classification.command_criteria

        if not command_criteria:
            return verification

        logger.info(
            "verify_command_criteria: %d command_execution criteria detected",
            len(command_criteria),
        )

        _assert_worktree_path(self.worktree_path)

        env = build_venv_env(self.worktree_path)
        if env is not None:
            # The first PATH entry is what build_venv_env prepended —
            # either ``.guardkit/venv/bin`` (bootstrap) or ``.venv/bin``
            # (legacy). Log the actual value so post-mortems can tell
            # which interpreter Coach verified against.
            prepended = env["PATH"].split(os.pathsep, 1)[0]
            logger.info("Prepended virtualenv PATH: %s", prepended)

        elapsed_total = 0.0
        for criterion in command_criteria:
            if not criterion.extracted_command:
                continue

            if elapsed_total >= total_timeout:
                logger.warning(
                    "Aggregate command timeout reached (%.0fs >= %ds), "
                    "skipping remaining criteria",
                    elapsed_total,
                    total_timeout,
                )
                break

            try:
                cmd = normalise_pip_command(criterion.extracted_command)
                if cmd != criterion.extracted_command:
                    logger.info(
                        "Normalized 'pip' to '%s -m pip'",
                        sys.executable,
                    )

                start = time.monotonic()
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(self.worktree_path),
                    capture_output=True,
                    text=True,
                    timeout=per_command_timeout,
                    env=env,
                )
                elapsed = time.monotonic() - start
                elapsed_total += elapsed

                passed = proc.returncode == 0
                verification.results.append(
                    CommandExecutionResult(
                        criterion_text=criterion.text,
                        extracted_command=cmd,
                        passed=passed,
                        exit_code=proc.returncode,
                        stdout=(proc.stdout or "")[:500],
                        stderr=(proc.stderr or "")[:500],
                        elapsed_seconds=elapsed,
                        timed_out=False,
                    )
                )

                if passed:
                    verification.passed_criteria.append(criterion.text)
                    logger.info(
                        "Runtime criterion verified: %s", criterion.text[:80]
                    )
                else:
                    logger.warning(
                        "Runtime criterion failed (exit %d): %s\nstderr: %s",
                        proc.returncode,
                        criterion.text[:80],
                        proc.stderr[:200] if proc.stderr else "",
                    )
                    failure_class = classify_command_failure(
                        returncode=proc.returncode,
                        stderr=proc.stderr or "",
                        stdout=proc.stdout or "",
                        command=cmd,
                    )
                    verification.failures.append(
                        CommandFailureRecord(
                            command=cmd,
                            criterion_text=criterion.text,
                            returncode=proc.returncode,
                            stderr=(proc.stderr or "")[:500],
                            stdout=(proc.stdout or "")[:500],
                            classification=failure_class,
                        )
                    )
                    logger.info(
                        "Command failure classified as '%s': %s",
                        failure_class,
                        criterion.text[:80],
                    )

            except subprocess.TimeoutExpired:
                elapsed_total += per_command_timeout
                verification.results.append(
                    CommandExecutionResult(
                        criterion_text=criterion.text,
                        extracted_command=criterion.extracted_command or "",
                        passed=False,
                        exit_code=None,
                        stdout="",
                        stderr="",
                        elapsed_seconds=float(per_command_timeout),
                        timed_out=True,
                    )
                )
                logger.warning(
                    "Runtime criterion timed out (%ds): %s",
                    per_command_timeout,
                    criterion.text[:80],
                )
                verification.failures.append(
                    CommandFailureRecord(
                        command=criterion.extracted_command or "",
                        criterion_text=criterion.text,
                        returncode=None,
                        stderr="",
                        stdout="",
                        classification="transient",
                        timed_out=True,
                    )
                )

        return verification

    def _load_completion_promises(
        self,
        task_work_results: Dict[str, Any],
        turn: Optional[int],
    ) -> List[Dict[str, Any]]:
        """
        Load completion promises from available sources.

        Checks ``task_work_results`` first, then falls back to reading
        the Player report file (``player_turn_{turn}.json``).

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Results from task-work execution
        turn : Optional[int]
            Current turn number

        Returns
        -------
        List[Dict[str, Any]]
            List of completion promise dicts, or empty list if unavailable
        """
        # Check task_work_results first (may be injected by direct mode writer)
        promises = task_work_results.get("completion_promises", [])
        if promises:
            return promises

        # Try reading from Player report on disk
        if turn is not None:
            task_id = task_work_results.get("task_id", "") or self.task_id or ""
            if task_id:
                try:
                    player_path = TaskArtifactPaths.player_report_path(
                        task_id, turn, self.worktree_path
                    )
                    if player_path.exists():
                        player_data = json.loads(player_path.read_text())
                        promises = player_data.get("completion_promises", [])
                        if promises:
                            logger.debug(
                                f"Loaded {len(promises)} completion promises "
                                f"from {player_path.name}"
                            )
                            return promises
                except Exception as e:
                    logger.debug(f"Could not read Player report for promises: {e}")

                # Scan backward through prior turns to recover promises (TASK-FIX-AE7E)
                if turn > 1:
                    for prev_turn in range(turn - 1, 0, -1):
                        try:
                            prev_path = TaskArtifactPaths.player_report_path(
                                task_id, prev_turn, self.worktree_path
                            )
                            if prev_path.exists():
                                prev_data = json.loads(prev_path.read_text())
                                prev_promises = prev_data.get("completion_promises", [])
                                if prev_promises:
                                    logger.info(
                                        "No completion_promises in current turn — "
                                        "recovered from player_turn_%d.json (%d promises)",
                                        prev_turn,
                                        len(prev_promises),
                                    )
                                    return prev_promises
                        except (json.JSONDecodeError, IOError):
                            pass

        return []

    def _match_by_promises(
        self,
        acceptance_criteria: List[str],
        completion_promises: List[Dict[str, Any]],
    ) -> RequirementsValidation:
        """
        Match acceptance criteria to Player completion promises by criterion ID.

        Acceptance criteria carrying a natural label (e.g. ``**AC-LOAD-01**``
        or ``AC-LOAD-01:``) match against promises emitted with that same
        label. Unlabelled criteria fall back to index-based IDs of the form
        ``AC-{i+1:03d}`` (TASK-CVAC-001 — preserves backwards compatibility
        with task definitions that have no AC IDs in the markdown).
        A criterion is verified when a matching promise has status ``complete``.

        Parameters
        ----------
        acceptance_criteria : List[str]
            Acceptance criteria text from the task
        completion_promises : List[Dict[str, Any]]
            Completion promises from the Player report

        Returns
        -------
        RequirementsValidation
            Structured validation result
        """
        # Pre-extract natural-label IDs from criteria markdown (TASK-CVAC-001).
        # Each entry parallels acceptance_criteria[i]; ``None`` when the
        # criterion has no extractable AC ID and the index-based fallback
        # should be used.
        extracted_ids: List[Optional[str]] = []
        for criterion_text in acceptance_criteria:
            cleaned = self._strip_criterion_prefix(criterion_text)
            _, extracted_id = self._extract_ac_id(cleaned)
            extracted_ids.append(extracted_id)

        # Build promise map: criterion_id -> promise dict
        # TASK-CVAC-002: Also key each promise by the AC ID extracted from
        # its ``criterion_text`` field, when that differs from the explicit
        # ``criterion_id``. This makes Coach robust to Player still emitting
        # index-based ``criterion_id`` (e.g. ``AC-001``) for criteria whose
        # markdown carries a natural label (e.g. ``**AC-SEED-01** — text``).
        # ``setdefault`` semantics: explicit ``criterion_id`` wins when both
        # keys would map to a promise, so promises that already use the
        # natural label directly are unaffected.
        promise_map: Dict[str, Dict[str, Any]] = {}
        # Maps fallback-key -> the promise's original ``criterion_id`` (used
        # only for the diagnostic log emitted at lookup time).
        fallback_origins: Dict[str, str] = {}
        for p in completion_promises:
            cid = p.get("criterion_id") or p.get("ac_id", "")
            if cid:
                promise_map[cid] = p
            text_id: Optional[str] = None
            criterion_text_field = p.get("criterion_text")
            if criterion_text_field:
                cleaned_text = self._strip_criterion_prefix(
                    criterion_text_field
                )
                # FEAT-FD32 reproducer: Player commonly emits a half-stripped
                # bold marker in ``criterion_text`` (``AC-SEED-01** — text``)
                # because the field travels through several
                # markdown-flattening hops on the way out of SDK Claude.
                # ``_extract_ac_id`` is deliberately strict about unmatched
                # ``**`` (TASK-CVAC-001 contract — see
                # ``test_unmatched_bold_marker``), so we collapse stray
                # ``**`` here before extraction. This widens recovery
                # without weakening ``_extract_ac_id``'s caller contract.
                normalized_text = cleaned_text.replace("**", "")
                _, text_id = self._extract_ac_id(normalized_text)
            if text_id and text_id != cid and text_id not in promise_map:
                promise_map[text_id] = p
                fallback_origins[text_id] = cid

        criteria_results: List[CriterionResult] = []
        missing: List[str] = []

        for i, criterion_text in enumerate(acceptance_criteria):
            criterion_id = extracted_ids[i] or f"AC-{i+1:03d}"
            promise = promise_map.get(criterion_id)

            # TASK-CVAC-002: Surface contract drift when Coach's lookup
            # succeeded only via the criterion_text fallback. Operators can
            # grep these to identify Player-prompt versions still emitting
            # index-based IDs against natural-label criteria.
            if promise and criterion_id in fallback_origins:
                logger.debug(
                    "%s: matched via criterion_text fallback "
                    "(promise.criterion_id=%r, extracted_text_id=%r)",
                    criterion_id,
                    fallback_origins[criterion_id],
                    criterion_id,
                )

            raw_status = promise.get("status", "") if promise else ""
            normalized_status = STATUS_ALIASES.get(raw_status, raw_status)
            if promise and normalized_status == "complete":
                result_str = "verified"
                evidence = promise.get(
                    "evidence",
                    f"Player completed {criterion_id}",
                )
            elif promise and normalized_status == "partial":
                # TASK-ACR-004: Treat partial as verified with lower confidence
                result_str = "verified"
                evidence_type = promise.get("evidence_type", "unknown")
                base_evidence = promise.get(
                    "evidence",
                    f"Player partially completed {criterion_id}",
                )
                evidence = (
                    f"[Partial confidence - {evidence_type}] {base_evidence}"
                )
            else:
                result_str = "rejected"
                if promise:
                    evidence = (
                        f"Promise status: {promise.get('status', 'unknown')}"
                    )
                else:
                    evidence = f"No completion promise for {criterion_id}"
                missing.append(criterion_text)

            # Log per-criterion matching result at DEBUG level (TASK-FIX-54F6)
            if result_str == "verified" and promise:
                promise_status = promise.get("status", "unknown")
                confidence = 1.0 if promise_status == "complete" else 0.8
                logger.debug(
                    "%s: Matched via promises (status: %s, confidence: %.2f)",
                    criterion_id,
                    promise_status,
                    confidence,
                )

            criteria_results.append(CriterionResult(
                criterion_id=criterion_id,
                criterion_text=criterion_text,
                result=result_str,
                status=result_str,
                evidence=evidence,
            ))

        criteria_met_count = len(acceptance_criteria) - len(missing)

        validation = RequirementsValidation(
            criteria_total=len(acceptance_criteria),
            criteria_met=criteria_met_count,
            all_criteria_met=len(missing) == 0,
            missing=missing,
            criteria_results=criteria_results,
        )

        logger.debug(
            f"Requirements validation (promises): "
            f"{criteria_met_count}/{len(acceptance_criteria)} met, "
            f"missing: {missing}"
        )

        return validation

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
    def _extract_keywords(text: str) -> set:
        """
        Extract keywords from text for fuzzy matching.

        Extracts meaningful keywords by:
        1. Splitting on whitespace
        2. Converting to lowercase
        3. Filtering words <= 3 characters
        4. Filtering stopwords
        5. Filtering non-alphanumeric words

        Parameters
        ----------
        text : str
            Text to extract keywords from

        Returns
        -------
        set
            Set of extracted keywords
        """
        # Split on whitespace and lowercase
        words = [w for w in re.split(r'[^a-zA-Z0-9_]+', text.lower()) if w]

        # Filter and extract keywords
        keywords = set()
        for word in words:
            # Skip short words
            if len(word) <= 3:
                continue
            # Skip stopwords
            if word in STOPWORDS:
                continue
            # Keep only words with at least one alphabetic character
            if any(c.isalpha() for c in word):
                keywords.add(word)

        return keywords

    @staticmethod
    def _strip_markdown_formatting(text: str) -> str:
        """Strip backticks and quotes from text for comparison.

        Strips: ` (backtick), " (double quote), ' (single quote), \u201c \u201d (smart quotes)
        Does NOT strip: _ (underscore) — significant in identifiers like log_level
        """
        return re.sub(r'[`"\'\u201c\u201d]', '', text)

    @staticmethod
    def _fuzzy_keyword_intersection(
        criterion_keywords: set,
        met_keywords: set,
    ) -> set:
        """Compute keyword intersection with prefix-based fuzzy matching.

        In addition to exact keyword matches, counts two keywords as matching
        when one is a prefix of the other and both are at least 5 characters
        long.  This handles stemming-like cases (e.g. ``"implement"`` vs
        ``"implementation"``) without an external NLP library.

        Returns the augmented intersection set (superset of exact intersection).
        """
        intersection = set(criterion_keywords & met_keywords)
        unmatched_criterion = criterion_keywords - intersection
        unmatched_met = met_keywords - intersection

        for ck in list(unmatched_criterion):
            if len(ck) < 5:
                continue
            for mk in list(unmatched_met):
                if len(mk) < 5:
                    continue
                # Match when they share a 5-char prefix (handles stemming
                # variants like "implement" / "implementation")
                if ck.startswith(mk[:5]) or mk.startswith(ck[:5]):
                    intersection.add(ck)
                    unmatched_met = unmatched_met - {mk}
                    break

        return intersection

    def _match_by_text(
        self,
        acceptance_criteria: List[str],
        requirements_met: List[str],
    ) -> RequirementsValidation:
        """
        Match acceptance criteria to requirements_met by normalized text.

        Legacy matching strategy. Used when completion promises are not
        available (e.g. older task-work results).

        Uses three matching strategies in order:
        1. Exact match (normalized text)
        2. Substring containment
        3. Keyword overlap (threshold depends on matching strategy)

        The Jaccard threshold is 70 % in ``text`` mode and 50 % in
        ``semantic`` mode.  Semantic mode additionally uses fuzzy prefix
        matching via :meth:`_fuzzy_keyword_intersection`.

        Parameters
        ----------
        acceptance_criteria : List[str]
            Acceptance criteria text from the task
        requirements_met : List[str]
            Requirements reported as met by the Player

        Returns
        -------
        RequirementsValidation
            Structured validation result
        """
        effective_strategy = self._resolve_matching_strategy()
        keyword_threshold = 0.50 if effective_strategy == "semantic" else 0.70

        # Pre-extract natural-label AC IDs from criteria markdown (TASK-CVAC-001).
        extracted_ids: List[Optional[str]] = []
        for criterion_text in acceptance_criteria:
            pre_cleaned = self._strip_criterion_prefix(criterion_text)
            _, extracted_id = self._extract_ac_id(pre_cleaned)
            extracted_ids.append(extracted_id)

        # Strip prefixes and normalize requirements_met
        stripped_met = [self._strip_criterion_prefix(r) for r in requirements_met]
        stripped_met = [self._strip_markdown_formatting(r) for r in stripped_met]
        normalized_met = {r.lower().strip() for r in stripped_met}

        criteria_results: List[CriterionResult] = []
        missing: List[str] = []

        for i, criterion_text in enumerate(acceptance_criteria):
            criterion_id = extracted_ids[i] or f"AC-{i+1:03d}"

            # Strip prefix from criterion (also strips compound AC ID
            # prefix when present, so the matching text is the
            # description body alone).
            stripped_criterion = self._strip_criterion_prefix(criterion_text)
            stripped_criterion, _ = self._extract_ac_id(stripped_criterion)
            stripped_criterion = self._strip_markdown_formatting(stripped_criterion)
            normalized = stripped_criterion.lower().strip()

            result_str = "rejected"
            evidence = "Not found in Player requirements_met"
            strategy = None
            confidence = 0.0

            # Strategy 1: Exact match
            if normalized in normalized_met:
                result_str = "verified"
                evidence = f"Matched in Player requirements_met: '{criterion_text}'"
                strategy = "exact"
                confidence = 1.0
            else:
                # Strategy 2: Substring containment
                for met_text in stripped_met:
                    normalized_met_text = met_text.lower().strip()
                    # Check if criterion is contained in requirement or vice versa
                    if normalized in normalized_met_text or normalized_met_text in normalized:
                        result_str = "verified"
                        evidence = f"Substring match with '{met_text}'"
                        strategy = "substring"
                        confidence = 0.9
                        break

                # Strategy 3: Keyword overlap
                if result_str == "rejected":
                    criterion_keywords = self._extract_keywords(stripped_criterion)

                    # Only try keyword matching if we have keywords
                    if criterion_keywords:
                        best_match_score = 0.0
                        best_match_text = None

                        for met_text in stripped_met:
                            met_keywords = self._extract_keywords(met_text)

                            # Skip if no keywords in requirement
                            if not met_keywords:
                                continue

                            # Calculate Jaccard similarity (with fuzzy prefix
                            # matching in semantic mode)
                            if effective_strategy == "semantic":
                                intersection = self._fuzzy_keyword_intersection(
                                    criterion_keywords, met_keywords,
                                )
                            else:
                                intersection = criterion_keywords & met_keywords
                            union = criterion_keywords | met_keywords

                            if union:
                                score = len(intersection) / len(union)
                                if score > best_match_score:
                                    best_match_score = score
                                    best_match_text = met_text

                        if best_match_score >= keyword_threshold:
                            result_str = "verified"
                            evidence = f"Keyword overlap match ({best_match_score:.0%} similarity) with '{best_match_text}'"
                            strategy = "keyword"
                            confidence = best_match_score

            # Log the strategy used for successful matches
            if result_str == "verified" and strategy:
                logger.debug(f"{criterion_id}: Matched via {strategy} (confidence: {confidence:.2f})")

            # Add to missing list if not verified
            if result_str == "rejected":
                missing.append(criterion_text)

            criteria_results.append(CriterionResult(
                criterion_id=criterion_id,
                criterion_text=criterion_text,
                result=result_str,
                status=result_str,
                evidence=evidence,
            ))

        criteria_met_count = len(acceptance_criteria) - len(missing)

        validation = RequirementsValidation(
            criteria_total=len(acceptance_criteria),
            criteria_met=criteria_met_count,
            all_criteria_met=len(missing) == 0,
            missing=missing,
            criteria_results=criteria_results,
        )

        logger.debug(
            f"Requirements validation (text): "
            f"{criteria_met_count}/{len(acceptance_criteria)} met, "
            f"missing: {missing}"
        )

        return validation

    def _extract_paths_from_ac_text(self, criterion_text: str) -> List[str]:
        """Extract file-path-shaped tokens from AC criterion text.

        Mirrors the regex used by ``synthetic_report.generate_file_existence_promises``
        for parity, plus the backtick / quoted variants. Returns a deduplicated
        list (insertion order preserved) of path-shaped strings; glob patterns
        (paths containing ``*``) are filtered out — only literal paths are
        eligible for disk-existence checks.

        Quoted content (backticks, single quotes, double quotes) that contains
        whitespace is treated as a *command line* rather than a single path
        (TASK-AB-006). For example, ``` `pytest tests/foo.py` ``` is split on
        whitespace and each token is independently checked against the path
        regex; the ``pytest`` runner prefix and any flags drop out and only
        ``tests/foo.py`` is kept. Pytest node-ID suffixes (``::test_name``)
        are stripped from every quoted token so that ``pytest
        tests/foo.py::test_bar`` and ``tests/foo.py::TestC::test_x`` both
        yield ``tests/foo.py`` rather than the unrunnable composite. Without
        this tokenisation step the over-captured command line would fail
        disk-existence under :py:meth:`_detect_ac_cited_missing_test_files`
        and short-circuit the independent-test gate even though the cited
        test file is in fact present (the FG-004 stall pattern that motivated
        this fix).

        Used by:
        - TASK-AB-FIX-INVAB1 AC-004: tightening the "No completion promise"
          hybrid-fallback branch to require the named path to exist on disk.
        - TASK-AB-FIX-INVAB1 AC-005: plan_audit ``skipped`` escalation when
          AC names a missing source file.
        - TASK-AB-FIX-INVAB1 AC-006 (via :py:meth:`_detect_ac_cited_missing_test_files`):
          the AC-cited-missing-test-files honesty gate.
        """
        if not criterion_text:
            return []
        primary = re.findall(r"[\w./\-]+\.\w{1,5}", criterion_text)
        backtick_raw = re.findall(r"`([^`]+\.[a-zA-Z]+)`", criterion_text)
        double_q_raw = re.findall(r'"([^"]+\.[a-zA-Z]+)"', criterion_text)
        single_q_raw = re.findall(r"'([^']+\.[a-zA-Z]+)'", criterion_text)

        # TASK-AB-006: tokenise whitespace-bearing quoted content as a
        # command line so a runner prefix (`pytest`, `python -m pytest`,
        # …) and flags don't end up smuggled into the path candidate.
        # Also strip pytest node-ID suffixes (``::test_name``) from every
        # quoted token so the bare file path is what gets disk-checked.
        # Bare-token quoted content (``path/to/file.py``) is preserved
        # verbatim modulo the node-ID strip — the original behaviour that
        # `path/to/file.py` is captured from `` `path/to/file.py` `` is
        # unchanged.
        path_token_re = re.compile(r"[\w./\-]+\.\w{1,5}")

        def _expand_quoted(quoted_chunks: List[str]) -> List[str]:
            expanded: List[str] = []
            for chunk in quoted_chunks:
                if any(c.isspace() for c in chunk):
                    for tok in chunk.split():
                        tok = tok.split("::", 1)[0]
                        if path_token_re.fullmatch(tok):
                            expanded.append(tok)
                else:
                    expanded.append(chunk.split("::", 1)[0])
            return expanded

        backtick = _expand_quoted(backtick_raw)
        double_q = _expand_quoted(double_q_raw)
        single_q = _expand_quoted(single_q_raw)

        out: List[str] = []
        seen: set = set()
        for p in primary + backtick + double_q + single_q:
            if "*" in p:
                continue
            if p not in seen:
                out.append(p)
                seen.add(p)
        return out

    def _ac_text_paths_all_exist_on_disk(self, criterion_text: str) -> bool:
        """Return True iff the AC text either names no paths or all named paths exist.

        Used by TASK-AB-FIX-INVAB1 AC-004's tightening of ``_hybrid_fallback``.
        Path-free ACs trivially "exist" — the helper is permissive in that
        case so legitimate text-fallback verification still works.
        """
        paths = self._extract_paths_from_ac_text(criterion_text)
        if not paths:
            return True
        for p in paths:
            if not (self.worktree_path / p).exists():
                return False
        return True

    def _detect_ac_cited_missing_test_files(
        self, acceptance_criteria: List[str]
    ) -> List[str]:
        """Return AC-cited test-file paths that don't exist on disk.

        Implements TASK-AB-FIX-INVAB1 AC-006: when an AC names a specific
        test file (path matching ``test_*.py`` / ``*_test.py`` Python
        conventions, plus equivalents per stack), that file must exist
        on disk. Otherwise the independent-test gate would silently run
        a smaller-scope test set and report green.

        Path extraction is delegated to
        :py:meth:`_extract_paths_from_ac_text`, which (per TASK-AB-006)
        treats whitespace-bearing quoted content as a command line and
        tokenises out the runner / flags. In practice this means:

        - ``pytest tests/foo.py`` / ``pytest -v tests/foo.py`` /
          ``python -m pytest tests/foo.py`` are all reduced to
          ``tests/foo.py`` for disk-existence checks.
        - ``pytest tests/foo.py::test_bar`` strips the node-ID suffix
          and checks ``tests/foo.py``.
        - **Non-pytest runners** with no path-shaped argument
          (``npm test``, ``dotnet test --filter Category=Unit``,
          ``cargo test``) yield no path candidates and therefore raise
          no AC-006 missing-file findings — the gate is silent for those
          shapes by design. Stacks that need disk-existence verification
          for non-pytest runners must cite the test file path explicitly
          in the AC text (e.g. ``AC-x: tests in tests/Suite.cs pass``)
          rather than relying on the runner command alone.
        """
        missing: List[str] = []
        seen: set = set()
        for ac in acceptance_criteria or []:
            for path in self._extract_paths_from_ac_text(ac):
                if not self._is_test_file_path(path):
                    continue
                if path in seen:
                    continue
                seen.add(path)
                if not (self.worktree_path / path).exists():
                    missing.append(path)
        return missing

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

    def _hybrid_fallback(
        self,
        promise_validation: RequirementsValidation,
        acceptance_criteria: List[str],
        requirements_addressed: List[str],
    ) -> RequirementsValidation:
        """
        Re-evaluate rejected criteria using text matching as fallback (TASK-REV-E719).

        When promise-based matching rejects criteria (no matching promise), this
        method gives them a second chance via text matching against
        ``requirements_addressed``. Criteria already verified by promises are
        kept as-is.

        Parameters
        ----------
        promise_validation : RequirementsValidation
            Initial validation from ``_match_by_promises()``
        acceptance_criteria : List[str]
            Acceptance criteria text from the task
        requirements_addressed : List[str]
            Requirements reported as addressed by the Player

        Returns
        -------
        RequirementsValidation
            Merged validation with text fallback applied to rejected criteria
        """
        # Run text matching against requirements_addressed
        text_validation = self._match_by_text(acceptance_criteria, requirements_addressed)

        # Merge: keep promise results for verified criteria,
        # upgrade rejected criteria if text matching verifies them
        merged_results: List[CriterionResult] = []
        merged_missing: List[str] = []
        upgraded_count = 0

        for promise_cr, text_cr in zip(
            promise_validation.criteria_results,
            text_validation.criteria_results,
        ):
            if promise_cr.result == "verified":
                merged_results.append(promise_cr)
            elif (
                text_cr.result == "verified"
                and promise_cr.result == "rejected"
                and "No completion promise" in promise_cr.evidence
                and self._ac_text_paths_all_exist_on_disk(
                    promise_cr.criterion_text
                )
            ):
                # Upgrade criteria only when the Player wrote no
                # completion promise at all (TASK-REV-E719 Fix 2 covers
                # the legitimate SDK-turn-exhaustion case). The
                # "Promise status: incomplete" upgrade branch was
                # removed (TASK-AB-FIX-INVAB1 AC-004): an incomplete
                # promise is the deterministic verifier's ground truth
                # and Player-self-reported text must not overrule it.
                #
                # The "No completion promise" branch is further
                # tightened (TASK-AB-FIX-INVAB1 AC-004): when the AC
                # text names a file path, that file must exist on disk
                # before Player text fallback may verify the criterion.
                upgraded_count += 1
                merged_results.append(CriterionResult(
                    criterion_id=text_cr.criterion_id,
                    criterion_text=text_cr.criterion_text,
                    result="verified",
                    status="verified",
                    evidence=f"[Text fallback] {text_cr.evidence}",
                ))
            else:
                merged_results.append(promise_cr)
                merged_missing.append(promise_cr.criterion_text)

        criteria_met = len(acceptance_criteria) - len(merged_missing)

        if upgraded_count > 0:
            logger.info(
                f"Hybrid fallback upgraded {upgraded_count} criteria "
                f"via text matching against requirements_addressed"
            )

        return RequirementsValidation(
            criteria_total=len(acceptance_criteria),
            criteria_met=criteria_met,
            all_criteria_met=len(merged_missing) == 0,
            missing=merged_missing,
            criteria_results=merged_results,
        )

    def _build_all_unmet(
        self,
        acceptance_criteria: List[str],
    ) -> RequirementsValidation:
        """
        Build validation result with all criteria marked unmet (fast-fail).

        Used for synthetic reports that have no completion_promises and cannot
        provide evidence for criteria satisfaction (TASK-ASF-006).

        Parameters
        ----------
        acceptance_criteria : List[str]
            Acceptance criteria text from the task

        Returns
        -------
        RequirementsValidation
            Validation result with all criteria rejected
        """
        # Pre-extract natural-label AC IDs from criteria markdown (TASK-CVAC-001)
        extracted_ids: List[Optional[str]] = []
        for criterion_text in acceptance_criteria:
            cleaned = self._strip_criterion_prefix(criterion_text)
            _, extracted_id = self._extract_ac_id(cleaned)
            extracted_ids.append(extracted_id)

        criteria_results = []
        for i, criterion_text in enumerate(acceptance_criteria):
            criterion_id = extracted_ids[i] or f"AC-{i+1:03d}"
            criteria_results.append(CriterionResult(
                criterion_id=criterion_id,
                criterion_text=criterion_text,
                result="rejected",
                status="rejected",
                evidence=(
                    "Synthetic report — no file-existence promises available"
                ),
            ))

        return RequirementsValidation(
            criteria_total=len(acceptance_criteria),
            criteria_met=0,
            all_criteria_met=False,
            missing=list(acceptance_criteria),
            criteria_results=criteria_results,
        )

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
            result = subprocess.run(
                ["git", "rev-parse", f"{first_commit}~1"],
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
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
                    diff_result = subprocess.run(
                        ["git", "diff", "--name-only", first_parent, "HEAD"],
                        cwd=str(self.worktree_path),
                        capture_output=True, text=True, timeout=10,
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

            return None

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

        # Default to pytest
        logger.warning("Could not detect project type, defaulting to pytest")
        return "pytest tests/ -v --tb=short"

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

        Fix: BDD verification is delegated to ``run_bdd_for_task`` (already
        task-tag scoped via ``-m @task:<TASK-ID>``). The Player-side
        ``_run_bdd_oracle`` runs it once per turn and writes ``bdd_results``
        into ``task_work_results``; the Coach's separate ``bdd_results``
        gate (``_check_bdd_results``) enforces ``scenarios_failed == 0``.
        Removing BDD glue files from the independent_tests pytest cmd does
        not weaken verification — it just stops double-running the same
        scenarios without the tag scope.

        Parameters
        ----------
        test_files : List[str]
            Test file paths relative to ``self.worktree_path``.

        Returns
        -------
        List[str]
            ``test_files`` with pytest-bdd glue removed (preserves order).
        """
        from .bdd_runner import is_bdd_glue_file

        plain: List[str] = []
        excluded: List[str] = []
        for tf in test_files:
            full = self.worktree_path / tf
            if is_bdd_glue_file(full):
                excluded.append(tf)
            else:
                plain.append(tf)
        if excluded:
            logger.info(
                "TASK-FIX-CC-BDD: Excluded %d pytest-bdd glue file(s) from "
                "independent_tests pytest cmd; task-tag scoping is enforced "
                "via run_bdd_for_task / bdd_results gate. Excluded: %s",
                len(excluded),
                excluded,
            )
        return plain

    def _classify_test_failure(
        self,
        test_output: Optional[str],
        requires_infrastructure: Optional[List[str]] = None,
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

    def _is_psycopg2_asyncpg_mismatch(
        self,
        test_output: Optional[str],
        task: Optional[Dict] = None,
    ) -> bool:
        """Return True when psycopg2 is missing in an asyncpg project.

        Identifies the case where the Player imported psycopg2 in a project
        that uses asyncpg as the database driver.  The specific check avoids
        false positives for projects that genuinely need psycopg2.

        Parameters
        ----------
        test_output : Optional[str]
            Raw test stdout+stderr output
        task : Optional[Dict]
            Task data dict. When provided, ``requires_infrastructure`` and
            ``bootstrap_packages`` are checked for asyncpg signals.

        Returns
        -------
        bool
            True only when psycopg2 is the missing module AND asyncpg (or
            sqlalchemy[asyncio]) is in the project's bootstrap packages.
        """
        if not test_output or not task:
            return False
        output_lower = test_output.lower()
        if "modulenotfounderror" not in output_lower or "no module named" not in output_lower:
            return False
        match = re.search(r"no module named '([^']+)'", test_output, re.IGNORECASE)
        if not match:
            return False
        missing_module = match.group(1).split(".")[0]
        if missing_module != "psycopg2":
            return False
        # Check if the project declares asyncpg as a dependency
        _ASYNCPG_SIGNALS = {"asyncpg", "sqlalchemy[asyncio]"}
        bootstrap = set(task.get("requires_infrastructure") or []) | set(
            task.get("bootstrap_packages") or []
        )
        return bool(bootstrap & _ASYNCPG_SIGNALS)

    def _bootstrap_likely_broken(
        self, task: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Return True if the worktree bootstrap state file reports failure.

        Reads ``<worktree>/.guardkit/bootstrap_state.json`` (written by
        :class:`environment_bootstrap.EnvironmentBootstrap`). Conservative
        default: returns False on missing file, parse errors, non-dict
        payloads, or ``success: True`` — never approve when the bootstrap
        state is unknown.

        Parameters
        ----------
        task : Optional[Dict[str, Any]]
            Task metadata. Currently unused; accepted for forward
            compatibility and signature symmetry with sibling predicate
            helpers (``_is_psycopg2_asyncpg_mismatch``).

        Returns
        -------
        bool
            True only when ``bootstrap_state.json`` exists, parses as a
            JSON object, and reports ``success: False``.
        """
        state_file = self.worktree_path / ".guardkit" / "bootstrap_state.json"
        try:
            if not state_file.exists():
                return False
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(data, dict):
            return False
        return data.get("success") is False

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

    def _build_approval_rationale(
        self,
        test_result: IndependentTestResult,
        gates_status: QualityGateStatus,
        task_work_results: Dict[str, Any],
        profile: QualityGateProfile,
        context: Optional[str] = None,
        conditional_approval: bool = False,
        failure_class: Optional[str] = None,
        environment_conditional_approval: bool = False,
    ) -> str:
        """
        Build an accurate rationale message for approval based on actual verification status.

        Parameters
        ----------
        test_result : IndependentTestResult
            Result of independent test verification
        gates_status : QualityGateStatus
            Quality gate status
        task_work_results : Dict[str, Any]
            Task-work results
        profile : QualityGateProfile
            Quality gate profile for task type
        context : Optional[str]
            Architecture context string if available
        conditional_approval : bool
            True if this approval is conditional due to infrastructure or collection error
        failure_class : Optional[str]
            Classification of the test failure when conditional_approval is True

        Returns
        -------
        str
            Accurate rationale message
        """
        parts = ["All quality gates passed."]

        if conditional_approval:
            if environment_conditional_approval:
                parts.append(
                    "Independent tests failed with environment-class infrastructure error "
                    "(ImportError/ModuleNotFoundError) on a known-broken bootstrap. "
                    "All Player quality gates passed. Conditionally approved with "
                    "environment flag — independent tests skipped."
                )
            elif failure_class == "collection_error":
                parts.append(
                    "Conditionally approved — test collection errors in independent verification. "
                    "All Player quality gates passed."
                )
            else:
                parts.append(
                    "Independent tests failed due to high-confidence infrastructure dependency "
                    "(Docker unavailable). Task declares required infrastructure. "
                    "Conditionally approved — independent tests skipped."
                )
        elif test_result.test_command == "skipped":
            if not profile.tests_required:
                parts.append("Tests not required for this task type.")
            else:
                parts.append("Independent verification skipped: no task-specific tests found.")
        else:
            parts.append("Independent verification confirmed.")

        parts.append("All acceptance criteria met.")

        # Add context info if provided
        if context:
            parts.append(f"Architecture context: {len(context)} chars provided.")

        return " ".join(parts)

    def _check_zero_test_anomaly(
        self,
        task_work_results: Dict[str, Any],
        profile: QualityGateProfile,
        independent_tests: Optional["IndependentTestResult"] = None,
        task_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Check for zero-test anomaly: all_passed=true with no tests actually executed.

        Returns an error (blocking) or warning (non-blocking) issue based on
        profile.zero_test_blocking when a task reports quality gates as passed
        but has zero test execution and no coverage data.

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Task-work results
        profile : QualityGateProfile
            Quality gate profile for task type
        independent_tests : Optional[IndependentTestResult]
            Result of independent test verification. If tests were independently
            verified as passing, the zero-test anomaly is a data quality issue
            in the results writer, not a real missing-tests problem.

        Returns
        -------
        List[Dict[str, Any]]
            List containing a warning issue if anomaly detected, empty otherwise
        """
        if not profile.tests_required:
            return []

        # Defense-in-depth: if independent test verification confirmed tests pass,
        # the zero-test anomaly is a results-writer data quality issue, not a real
        # missing-tests problem. Skip the anomaly check.
        # Note: "skipped" means no task-specific tests were found (vacuous pass) —
        # that should NOT override the anomaly, since no tests were actually run.
        if (
            independent_tests
            and independent_tests.tests_passed
            and independent_tests.test_command != "skipped"
        ):
            return []

        # Check for project-wide pass masking zero task-specific tests:
        # Player created no tests AND independent verification found no task-specific tests.
        # The project-wide suite may pass (tests_passed_count > 0) but this task
        # contributes zero test coverage.
        tests_written = task_work_results.get("tests_written", [])
        if (
            len(tests_written) == 0
            and independent_tests
            and independent_tests.test_command == "skipped"
        ):
            severity = "error" if profile.zero_test_blocking else "warning"
            log_func = logger.error if profile.zero_test_blocking else logger.warning
            log_func(
                "Zero-test anomaly: no task-specific tests created (tests_written=[]) "
                "and independent verification skipped (no task-specific test files found). "
                "Project-wide test suite may pass but task contributes zero test coverage."
            )
            task_prefix = self._task_id_to_pattern_prefix(task_id) if task_id else "<task_prefix>"
            glob_pattern = f"tests/**/test_{task_prefix}*.py"
            return [{
                "severity": severity,
                "category": "zero_test_anomaly",
                "description": (
                    f"No task-specific tests found. Coach searched:\n"
                    f"  1. task_work_results files_created/files_modified for test_*.py files\n"
                    f"  2. Glob pattern: {glob_pattern}\n"
                    f"Please ensure test files are listed in your task_work_results "
                    f"files_created or files_modified arrays, OR name them "
                    f"to match the pattern test_{task_prefix}*.py"
                ),
            }]

        quality_gates = task_work_results.get("quality_gates", {})
        all_passed = quality_gates.get("all_passed")
        tests_passed_count = quality_gates.get("tests_passed", 0) or 0
        coverage = quality_gates.get("coverage")

        if all_passed is True and tests_passed_count == 0 and coverage is None:
            severity = "error" if profile.zero_test_blocking else "warning"
            log_func = logger.error if profile.zero_test_blocking else logger.warning
            log_func(
                f"Zero-test anomaly: all_passed=true but tests_passed=0 and coverage=null. "
                f"Player may have reported quality gates as passed without running tests."
            )
            return [{
                "severity": severity,
                "category": "zero_test_anomaly",
                "description": (
                    "Quality gates reported as passed but no tests were executed "
                    "(tests_passed=0, coverage=null). Player may not have run tests."
                ),
            }]

        return []

    def _check_bdd_results(
        self,
        task_work_results: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Inspect ``task_work_results['bdd_results']`` for the BDD oracle gate.

        Implements the three-state model from TASK-BDD-E8954:

        * ``scenarios_failed > 0``  → blocking ``must_fix`` issue (Coach rejects).
        * ``scenarios_pending > 0`` → non-blocking informational issue (Coach
          surfaces it as actionable work but does NOT reject on pending alone).
        * Absent ``bdd_results`` key → no gate active, returns ``([], [])``.

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Parsed contents of ``task_work_results.json``.

        Returns
        -------
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]
            ``(blocking_issues, non_blocking_issues)`` — both lists may be empty.
        """
        bdd_results = task_work_results.get("bdd_results")
        if not bdd_results:
            return [], []

        scenarios_failed = int(bdd_results.get("scenarios_failed", 0) or 0)
        scenarios_pending = int(bdd_results.get("scenarios_pending", 0) or 0)
        scenarios_passed = int(bdd_results.get("scenarios_passed", 0) or 0)
        failures = bdd_results.get("failures", []) or []
        pending = bdd_results.get("pending", []) or []
        feature_files = bdd_results.get("feature_files", []) or []

        blocking: List[Dict[str, Any]] = []
        non_blocking: List[Dict[str, Any]] = []

        if scenarios_failed > 0:
            failure_summaries: List[str] = []
            reason_bullets: List[str] = []
            for f in failures[:5]:
                scenario = f.get("scenario_name", "<unknown>")
                step = f.get("failing_step", "")
                reason = (f.get("reason") or "").strip()
                summary = f"{scenario}"
                if step:
                    summary += f" — step: {step}"
                if reason:
                    summary += f" — {reason[:160]}"
                failure_summaries.append(summary)

                # TASK-AB-003: surface the per-failure reason as a bullet in
                # the description so the Player feedback (which renders only
                # `description`) carries the actual exception class+message
                # and traceback frame, not just the generic "Implementation
                # does not satisfy the Gherkin specification" prose.
                if reason:
                    bullet_reason = reason
                    if len(bullet_reason) > 400:
                        bullet_reason = bullet_reason[:397] + "..."
                    bullet = f"- {scenario}: {bullet_reason}"
                else:
                    bullet = f"- {scenario}"
                reason_bullets.append(bullet)

            description_parts: List[str] = [
                f"BDD oracle: {scenarios_failed} scenario(s) failed "
                f"during pytest-bdd execution."
            ]
            if reason_bullets:
                description_parts.append("Per-failure details:")
                description_parts.extend(reason_bullets)
            else:
                description_parts.append(
                    "Implementation does not satisfy the Gherkin specification."
                )
            description = "\n".join(description_parts)

            blocking.append({
                "severity": "must_fix",
                "category": "bdd_failure",
                "description": description,
                "scenarios_failed": scenarios_failed,
                "scenarios_passed": scenarios_passed,
                "scenarios_pending": scenarios_pending,
                "feature_files": feature_files,
                "failure_examples": failure_summaries,
            })

        if scenarios_pending > 0:
            pending_summaries: List[str] = []
            for p in pending[:5]:
                scenario = p.get("scenario_name", "<unknown>")
                step = p.get("pending_step", "")
                summary = f"{scenario}"
                if step:
                    summary += f" — implement: {step}"
                pending_summaries.append(summary)

            non_blocking.append({
                "severity": "should_fix",
                "category": "bdd_pending",
                "description": (
                    f"BDD oracle: {scenarios_pending} scenario(s) reference "
                    f"step definitions that are not yet implemented. "
                    f"These do NOT block approval but should be implemented "
                    f"to make the scenarios runnable."
                ),
                "scenarios_pending": scenarios_pending,
                "feature_files": feature_files,
                "pending_examples": pending_summaries,
            })

        return blocking, non_blocking

    def _validate_consumer_context(
        self,
        task: Dict[str, Any],
        task_work_results: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Validate that produced artifacts match consumer_context format constraints.

        For each consumer_context entry, finds the artifact value in the worktree
        (docker-compose files, .env files) and checks whether the value matches
        the format_note constraint via string pattern matching.

        This is framework-agnostic: the Coach does NOT know what asyncpg or
        SQLAlchemy means. It only checks whether the artifact value string-matches
        the format_note.

        Parameters
        ----------
        task : Dict[str, Any]
            Task data including optional consumer_context list
        task_work_results : Dict[str, Any]
            Results from task-work execution

        Returns
        -------
        List[Dict[str, Any]]
            List of warning issues for format mismatches (non-blocking)
        """
        consumer_context = task.get("consumer_context", [])
        if not consumer_context:
            return []

        issues = []
        for entry in consumer_context:
            if not isinstance(entry, dict):
                continue

            artifact_name = entry.get("consumes", "")
            format_note = entry.get("format_note", "")
            consumer_task = entry.get("task", "")

            if not artifact_name or not format_note:
                continue

            # Attempt to find the artifact value
            artifact_value = self._find_artifact_value(artifact_name)

            if artifact_value is None:
                logger.debug(
                    f"consumer_context: artifact '{artifact_name}' not found, "
                    "skipping validation"
                )
                continue

            # String pattern matching against format_note
            if not self._format_note_matches(artifact_value, format_note):
                issues.append({
                    "severity": "consider",
                    "category": "consumer_context_mismatch",
                    "description": (
                        f"Format mismatch for '{artifact_name}': "
                        f"value '{artifact_value}' does not match format constraint "
                        f"'{format_note}' (consumer: {consumer_task})"
                    ),
                })

        return issues

    def _find_artifact_value(self, artifact_name: str) -> Optional[str]:
        """
        Locate an artifact value by name in the worktree.

        Searches for environment variable definitions in:
        - docker-compose.yml / docker-compose.yaml
        - .env files (.env, .env.test, .env.docker)

        Parameters
        ----------
        artifact_name : str
            Name of the artifact (e.g., "DATABASE_URL")

        Returns
        -------
        Optional[str]
            The artifact value if found, None otherwise
        """
        worktree = Path(self.worktree_path)

        # Search docker-compose files
        for compose_name in ["docker-compose.yml", "docker-compose.yaml"]:
            compose_path = worktree / compose_name
            if compose_path.exists():
                try:
                    content = compose_path.read_text()
                    pattern = rf'{re.escape(artifact_name)}\s*[=:]\s*["\']?([^"\'\n#]+)'
                    match = re.search(pattern, content)
                    if match:
                        return match.group(1).strip()
                except OSError:
                    continue

        # Search .env files
        for env_name in [".env", ".env.test", ".env.docker"]:
            env_path = worktree / env_name
            if env_path.exists():
                try:
                    content = env_path.read_text()
                    pattern = rf'^{re.escape(artifact_name)}\s*=\s*(.+)$'
                    match = re.search(pattern, content, re.MULTILINE)
                    if match:
                        return match.group(1).strip().strip("'\"")
                except OSError:
                    continue

        return None

    def _format_note_matches(self, artifact_value: str, format_note: str) -> bool:
        """
        Check if artifact value matches format_note constraint via string pattern matching.

        Extracts identifiable tokens from format_note (URL patterns containing +,
        ://, or dialect prefixes) and checks if they appear in the artifact value.

        This is deliberately framework-agnostic — no knowledge of SQLAlchemy,
        asyncpg, etc. is embedded. The format_note itself carries the specifics.

        Parameters
        ----------
        artifact_value : str
            The actual artifact value found
        format_note : str
            The format constraint from consumer_context

        Returns
        -------
        bool
            True if artifact value appears to match the format constraint
        """
        # Extract technical tokens from format_note
        # Look for URL-like patterns: +asyncpg://, postgresql+asyncpg://, +asyncpg
        url_patterns = re.findall(
            r'[a-z]+\+[a-z]+://|[a-z]+://|\+[a-z]+', format_note.lower()
        )
        if url_patterns:
            return any(
                pattern in artifact_value.lower() for pattern in url_patterns
            )

        # Fallback: no recognisable pattern extracted — cannot validate, assume OK
        logger.debug(
            f"format_note '{format_note}' has no extractable URL pattern, "
            "skipping match"
        )
        return True

    def _check_seam_test_recommendation(
        self,
        task_work_results: Dict[str, Any],
        profile: QualityGateProfile,
    ) -> List[Dict[str, Any]]:
        """
        Check for missing seam tests when recommended for cross-boundary features.

        This is a soft gate (warning only, not blocking) that notes when a task
        type that typically crosses technology boundaries lacks seam tests.

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Task-work results containing tests_written and implementation details
        profile : QualityGateProfile
            Quality gate profile for task type

        Returns
        -------
        List[Dict[str, Any]]
            List containing a warning issue if seam tests are recommended but
            not found, empty otherwise
        """
        # Only check if seam tests are recommended for this task type
        if not profile.seam_tests_recommended:
            return []

        # Check if any seam tests were written
        tests_written = task_work_results.get("tests_written", [])

        # Look for seam test patterns in test files
        seam_test_patterns = ["seam", "contract", "boundary", "integration"]
        has_seam_tests = any(
            any(pattern in test_file.lower() for pattern in seam_test_patterns)
            for test_file in tests_written
        )

        if not has_seam_tests and tests_written:
            # Tests exist but no seam tests detected
            logger.info(
                "Seam test recommendation: no seam/contract/boundary tests detected "
                f"for cross-boundary feature. Tests written: {tests_written}"
            )
            return [{
                "severity": "consider",
                "category": "seam_test_recommendation",
                "description": (
                    "No seam tests detected for cross-boundary feature. "
                    "Consider adding seam/contract/boundary tests to validate "
                    "technology boundary interactions. This is a recommendation, "
                    "not a blocking gate."
                ),
            }]

        return []

    def _check_seam_tests_implemented(
        self,
        task: Dict[str, Any],
        task_work_results: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """TASK-FIX-A7B4: Block when ``## Seam Tests`` was specified but unimplemented.

        Distinct from ``_check_seam_test_recommendation`` (a soft, profile-driven
        suggestion). This gate is explicit-contract-driven:

        * The task description carries an authoritative ``## Seam Tests``
          markdown block with code stubs (typically authored by ``/task-create``
          or ``/feature-plan`` for cross-task contracts).
        * The Player is expected to materialise those stubs as
          ``@pytest.mark.seam`` (or ``contract``/``boundary``) tests in the
          worktree.
        * If the section is non-empty in the task description but no tests
          carrying one of those markers are visible in the Player's
          ``tests_written`` files, Coach blocks the turn.

        The detection is precise so existing tasks aren't retroactively broken:

        * No ``## Seam Tests`` header → no gate (returns ``[]``).
        * Header present but body is whitespace-only → no gate.
        * Header + non-empty body + at least one marker-decorated test in
          the worktree → no gate (the contract is honoured).
        * Header + non-empty body + zero marker-decorated tests → blocking
          ``must_fix`` issue.

        Marker matching reads the actual file content under ``self.worktree_path``
        rather than the soft gate's filename heuristic. A file named
        ``test_integration_api.py`` that contains no ``@pytest.mark.seam`` /
        ``contract`` / ``boundary`` decorator does NOT satisfy the contract —
        the AC says "tests collected with the marker", not "any test that
        sounds boundary-ish".
        """
        description = task.get("description")
        section = _extract_seam_tests_section(description)
        if section is None:
            return []

        tests_written = task_work_results.get("tests_written", []) or []
        marker_test_count = self._count_seam_marker_tests(tests_written)

        if marker_test_count > 0:
            return []

        # Build the feedback payload. AC-005 requires the message to point at
        # the stub in the task description so the Player has a concrete
        # follow-up. We surface a short snippet (up to ~400 chars) of the
        # section body — enough to identify the stubs without flooding the
        # turn artifact.
        section_snippet = section.strip()
        if len(section_snippet) > 400:
            section_snippet = section_snippet[:400].rstrip() + "…"

        marker_list = ", ".join(f"@pytest.mark.{m}" for m in _SEAM_PYTEST_MARKERS)
        logger.info(
            "Seam tests gate: task description has a non-empty ## Seam Tests "
            "section but no %s tests were written (tests_written=%s)",
            marker_list,
            tests_written,
        )
        return [{
            "severity": "must_fix",
            "category": "seam_tests_unimplemented",
            "description": (
                "Task description specifies a `## Seam Tests` section but no "
                f"tests carrying {marker_list} markers were written. "
                "Implement the seam test stub from the task description "
                "(below) as a marker-decorated test in the worktree before "
                "resubmitting.\n\n"
                "Stub from task description:\n"
                "----------\n"
                f"{section_snippet}\n"
                "----------"
            ),
        }]

    def _count_seam_marker_tests(self, tests_written: List[str]) -> int:
        """Count tests in ``tests_written`` decorated with a seam-class marker.

        Reads each file relative to ``self.worktree_path`` and counts
        occurrences of ``@pytest.mark.seam`` / ``contract`` / ``boundary``.
        Files that don't exist or aren't readable are silently skipped — the
        gate is generous: a single positive sighting in any file is enough
        to satisfy the contract. We don't try to assert that the markers
        reference the task's modules; that's a deeper analysis the AC
        explicitly de-scopes ("tolerate any of seam/contract/boundary
        markers").
        """
        if not tests_written:
            return 0

        marker_pattern = re.compile(
            r"@pytest\.mark\.(?:" + "|".join(_SEAM_PYTEST_MARKERS) + r")\b"
        )
        count = 0
        for rel_path in tests_written:
            if not rel_path or not isinstance(rel_path, str):
                continue
            try:
                # Allow absolute paths but treat relative paths as
                # worktree-rooted. Path("/abs") joined with anything ignores
                # the prefix when the joined path is absolute, so this
                # handles both shapes.
                candidate = self.worktree_path / rel_path
                if not candidate.is_file():
                    continue
                content = candidate.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue
            count += len(marker_pattern.findall(content))
        return count

    def _check_unconfirmed_assumptions(
        self,
        task_work_results: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """TASK-FIX-RWOP1.4a: surface unconfirmed low-confidence assumptions.

        Reads the ``unconfirmed_low_confidence_assumptions`` block written
        by ``AgentInvoker._write_task_work_results`` (producer) and, if it
        names any rows, returns a single non-blocking warning issue naming
        the rows. Warn-mode: Coach still approves the turn; the warning
        rides along so the human reviewing the merge can act on it.

        Empty ``unconfirmed`` list, ``status: "ok"``, a missing block, or
        a ``status: "checker_error"`` producer fault all return ``[]`` —
        the gate never blocks on its own bookkeeping.

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Full task-work results dict loaded from disk.

        Returns
        -------
        List[Dict[str, Any]]
            One warning issue when unconfirmed rows exist, otherwise
            an empty list.
        """
        block = task_work_results.get("unconfirmed_low_confidence_assumptions")
        if not isinstance(block, dict):
            return []

        if block.get("status") != "warning":
            # "ok" means no unconfirmed rows; "checker_error" is producer
            # self-reported — neither should surface a spec warning.
            return []

        unconfirmed = block.get("unconfirmed") or []
        if not unconfirmed:
            return []

        row_count = len(unconfirmed)
        # Keep the description terse; put the full row list in details so
        # the human reviewer can navigate to the YAML without re-parsing
        # the JSON.
        row_ids = [r.get("id", "unknown") for r in unconfirmed]
        logger.info(
            "Unconfirmed low-confidence assumptions: %d row(s) across %d file(s). "
            "IDs: %s",
            row_count,
            block.get("files_scanned", 0),
            ", ".join(row_ids),
        )
        return [{
            "severity": "warning",
            "category": "unconfirmed_low_confidence_assumptions",
            "description": (
                f"{row_count} low-confidence assumption(s) in features/**/"
                f"_assumptions.yaml have no 'human_response: confirmed' entry. "
                f"feature-spec.md:337 says the Coach verifies these before "
                f"accepting a spec — please review before merging. "
                f"Unconfirmed IDs: {', '.join(row_ids)}."
            ),
            "details": {
                "files_scanned": block.get("files_scanned", 0),
                "unconfirmed": unconfirmed,
            },
        }]

    def _verify_honesty(
        self, task_work_results: Dict[str, Any]
    ) -> HonestyVerification:
        """Run CoachVerifier honesty checks against the Player report.

        Filesystem-only verification: file existence (files_created /
        files_modified / tests_written) and completion-promise file
        existence. Test-result verification is deliberately skipped — the
        deterministic Coach path runs ``run_independent_tests`` later in
        ``validate()`` which is the authoritative pass.

        Restores TASK-AB-FIX-INVAB1 AC-002 wiring. Never raises: returns
        a default-honest verification on any unexpected failure so the
        deterministic gate path keeps running.
        """
        try:
            # TASK-FIX-1B4A (Layer 1): wire identity-based path resolution so
            # a Player-reported pre-move task path is recognised when
            # state_bridge has moved the file mid-turn. Falls back to
            # exact-match behaviour when task_id is unknown.
            state_bridge = None
            if self.task_id:
                from guardkit.tasks.state_bridge import TaskStateBridge

                state_bridge = TaskStateBridge(
                    self.task_id,
                    self.worktree_path,
                    in_autobuild_context=True,
                )
            verifier = CoachVerifier(
                self.worktree_path,
                task_id=self.task_id,
                state_bridge=state_bridge,
            )
            discrepancies = []
            discrepancies.extend(verifier._verify_files_exist(task_work_results))
            discrepancies.extend(
                verifier._verify_completion_promises_files_exist(task_work_results)
            )
            # TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT: detect the FEAT-39E1 class
            # of silent loss — Player-created files that exist on disk but
            # are gitignored (or sparse-filtered, etc.) so the per-turn
            # checkpoint commit drops them. Pair-with-attempted-count
            # semantics from absence-of-failure-is-not-success.md guard the
            # implicit "git add error count == 0" gate against zero-attempted
            # false-greens.
            discrepancies.extend(
                verifier._verify_claims_were_staged(task_work_results)
            )
            total = verifier._count_verifiable_claims(task_work_results)
            critical = sum(1 for d in discrepancies if d.severity == "critical")
            # TASK-FIX-IGNR AC-2: track should_fix discrepancies separately
            # so the gate can ride them along to feedback without counting
            # them toward the honesty_score. The motivating case is
            # ``claim_audit_gitignored`` — file is on disk, .gitignore is
            # the bug, and turn-rejecting on it produces the FEAT-39E1
            # adversarial blow-up.
            should_fix = sum(
                1 for d in discrepancies if d.severity == "should_fix"
            )
            return HonestyVerification(
                verified=len(discrepancies) == 0,
                discrepancies=discrepancies,
                honesty_score=1.0 - (critical / max(total, 1)),
                resolved_paths=list(verifier._resolved_paths),
                should_fix_count=should_fix,
            )
        except Exception as exc:  # noqa: BLE001 — never block gates on verifier crash
            logger.warning(
                "CoachVerifier raised during honesty check: %s. "
                "Treating as honest to avoid blocking gate evaluation.",
                exc,
            )
            return HonestyVerification(
                verified=True, discrepancies=[], honesty_score=1.0
            )

    def _honesty_issues_from(
        self, honesty: HonestyVerification
    ) -> List[Dict[str, Any]]:
        """Translate critical Discrepancies into honesty issue dicts.

        Only ``critical`` severities become honesty issues; warnings and
        info-level discrepancies are recorded on the result via
        ``honesty_verification`` but do not block gate evaluation.

        Most critical discrepancies become ``must_fix`` issues that
        short-circuit gate evaluation. The exception (TASK-FIX-1B4B
        Layer 2) is a single ``file_existence``-only critical
        discrepancy: it is demoted to ``should_fix`` so the discrepancy
        surfaces in feedback as advisory while gate evaluation
        continues. Multiple ``file_existence`` discrepancies,
        ``promise_file_existence`` (FEAT-6CC5 sophisticated-lie
        pattern), and content-claim discrepancies (``test_result``,
        ``test_count``) retain ``must_fix`` and short-circuit.

        ``claim_audit`` discrepancies (TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT,
        sibling of TASK-AB-FIX-INVAB1's ``honesty`` category) are emitted
        with ``category: "claim_audit"`` instead of ``"honesty"``, are
        ``must_fix``, and are excluded from the FEAT-FFC3 single-
        discrepancy demotion above. The class they cover — Player claims
        about files that did not actually land in the per-turn checkpoint
        commit — is a different defect shape than the FFC3 ghost-path
        case the demotion was added for, and a single dropped path is
        enough signal to reject the turn.

        ``claim_audit_gitignored`` discrepancies (TASK-FIX-IGNR) are the
        narrow non-fabrication subset of the above: the Player-authored
        file *is* on disk, but a ``.gitignore`` rule silently filtered
        it out of the would-be-staged set. These are emitted as
        ``should_fix`` advisory issues — same ``category: "claim_audit"``
        so dashboards still bucket them with the gate, but they ride
        along to feedback rather than short-circuiting evaluation. AC-6
        appends a rebase hint to the description when the matched rule's
        source is the project-root ``.gitignore`` (the most common
        recoverable case: the rule was already fixed on ``main`` and the
        worktree just needs to rebase).
        """
        critical = [d for d in honesty.discrepancies if d.severity == "critical"]
        # Partition: claim_audit discrepancies have their own category and
        # never participate in the FEAT-FFC3 single-discrepancy demotion.
        non_audit = [d for d in critical if d.claim_type != "claim_audit"]
        audit = [d for d in critical if d.claim_type == "claim_audit"]
        # TASK-FIX-IGNR: the gitignored subset is should_fix and never
        # short-circuits. Pulled separately from the critical list and
        # supplemented from honesty.discrepancies (severity == should_fix).
        gitignored = [
            d for d in honesty.discrepancies
            if d.claim_type == "claim_audit_gitignored"
            and d.severity == "should_fix"
        ]
        # TASK-FIX-PCN: the tracked-but-unmodified subset is also
        # should_fix advisory (defence-in-depth for the agent_invoker-side
        # filter at _strip_orchestrator_managed_paths). The claimed path
        # is tracked in git but porcelain shows no change for it — most
        # commonly because the Player report writer swept an
        # orchestrator-managed path (e.g. .guardkit/autobuild/<TASK-ID>/...)
        # into files_modified. Surfaces as a warning so the operator can
        # see the noise without the gate collapsing.
        unmodified = [
            d for d in honesty.discrepancies
            if d.claim_type == "claim_audit_unmodified"
            and d.severity == "should_fix"
        ]
        demote = (
            len(non_audit) == 1
            and non_audit[0].claim_type == "file_existence"
        )
        severity_for_non_audit = "should_fix" if demote else "must_fix"

        issues: List[Dict[str, Any]] = []
        for d in non_audit:
            issues.append(
                {
                    "severity": severity_for_non_audit,
                    "category": "honesty",
                    "description": (
                        f"Honesty verification failed: Player claim disagrees "
                        f"with worktree state. Claim: {d.player_claim}. "
                        f"Actual: {d.actual_value}."
                    ),
                    "details": {
                        "claim_type": d.claim_type,
                        "player_claim": d.player_claim,
                        "actual_value": d.actual_value,
                    },
                }
            )
        for d in audit:
            # TASK-FIX-CAUD-J6F1 AC-002: drop the speculative "most
            # common cause is an unanchored .gitignore rule" tail.
            # The verifier's actual_value already carries the probe
            # results (path_exists / gitignore_match / tracked) so
            # the operator sees the checked facts rather than a guess.
            # The previous wording sent the J6F1 review chasing
            # hypothesis 1 for a non-trivial amount of time even though
            # check-ignore had explicitly returned "no rule matched".
            issues.append(
                {
                    "severity": "must_fix",
                    "category": "claim_audit",
                    "description": (
                        f"Checkpoint claim audit failed: Player claimed a "
                        f"file that 'git add -A' would not stage. "
                        f"{d.player_claim}. {d.actual_value} Investigate "
                        f"before approving the turn."
                    ),
                    "details": {
                        "claim_type": d.claim_type,
                        "player_claim": d.player_claim,
                        "actual_value": d.actual_value,
                    },
                }
            )
        for d in gitignored:
            description = (
                f"Player-claimed file is on disk but matched a "
                f".gitignore rule, so the per-turn checkpoint commit "
                f"silently dropped it. {d.player_claim}. "
                f"{d.actual_value}"
            )
            # AC-6: when the matching rule lives in the project-root
            # ``.gitignore`` (rule source has no directory prefix), the
            # most common recoverable shape is "rule already fixed on
            # main, worktree just needs to rebase". Surface that hint.
            if self._ignore_rule_is_project_root(d.ignore_rule):
                description += (
                    " Hint: rebase the worktree onto main if the "
                    ".gitignore was fixed there."
                )
            issues.append(
                {
                    "severity": "should_fix",
                    "category": "claim_audit",
                    "description": description,
                    "details": {
                        "claim_type": d.claim_type,
                        "player_claim": d.player_claim,
                        "actual_value": d.actual_value,
                        "ignore_rule": d.ignore_rule,
                    },
                }
            )
        # TASK-FIX-PCN: surface tracked-but-unmodified path claims as
        # should_fix advisory issues. Same ``category: "claim_audit"``
        # bucket so dashboards group them with sibling claim-audit shapes,
        # but they ride along to feedback rather than short-circuiting
        # gate evaluation. Most common cause is the Player report writer
        # sweeping an orchestrator-managed path into files_modified;
        # the Player-side filter at _strip_orchestrator_managed_paths
        # is the load-bearing fix and this branch is defence-in-depth.
        for d in unmodified:
            issues.append(
                {
                    "severity": "should_fix",
                    "category": "claim_audit",
                    "description": (
                        f"Player-claimed file is tracked in git but "
                        f"'git status --porcelain' shows no change for "
                        f"it — the Player likely swept an orchestrator-"
                        f"managed path into files_modified. "
                        f"{d.player_claim}. {d.actual_value}"
                    ),
                    "details": {
                        "claim_type": d.claim_type,
                        "player_claim": d.player_claim,
                        "actual_value": d.actual_value,
                    },
                }
            )
        return issues

    @staticmethod
    def _ignore_rule_is_project_root(ignore_rule: Optional[str]) -> bool:
        """Return True when ``ignore_rule`` was matched against the project-
        root ``.gitignore`` (TASK-FIX-IGNR AC-6).

        ``git check-ignore -v --no-index`` formats matched rules as
        ``<source>:<linenum>:<pattern>``. The source path is relative to
        the worktree root. A rule from the project-root ``.gitignore``
        therefore has source ``.gitignore`` exactly (no directory
        prefix). Rules from nested ``.gitignore`` files (e.g.
        ``src/.gitignore``) have a directory in the source — those are
        not the rebase-fixable case the hint targets, so we return False.
        """
        if not ignore_rule:
            return False
        source = ignore_rule.split(":", 1)[0]
        return source == ".gitignore"

    def _feedback_result(
        self,
        task_id: str,
        turn: int,
        issues: List[Dict[str, Any]],
        rationale: str,
        quality_gates: Optional[QualityGateStatus] = None,
        independent_tests: Optional[IndependentTestResult] = None,
        requirements: Optional[RequirementsValidation] = None,
        context_used: Optional[str] = None,
        is_configuration_error: bool = False,
        honesty_verification: Optional[HonestyVerification] = None,
    ) -> CoachValidationResult:
        """
        Create a feedback result.

        Parameters
        ----------
        task_id : str
            Task identifier
        turn : int
            Turn number
        issues : List[Dict[str, Any]]
            List of issues found
        rationale : str
            Explanation of feedback
        quality_gates : Optional[QualityGateStatus]
            Quality gate status if available
        independent_tests : Optional[IndependentTestResult]
            Test verification result if available
        requirements : Optional[RequirementsValidation]
            Requirements validation if available

        Returns
        -------
        CoachValidationResult
            Feedback result
        """
        return CoachValidationResult(
            task_id=task_id,
            turn=turn,
            decision="feedback",
            quality_gates=quality_gates,
            independent_tests=independent_tests,
            requirements=requirements,
            issues=issues,
            rationale=rationale,
            context_used=context_used,
            is_configuration_error=is_configuration_error,
            honesty_verification=honesty_verification,
        )

    def _feedback_from_gates(
        self,
        task_id: str,
        turn: int,
        gates: QualityGateStatus,
        task_work_results: Dict[str, Any],
        context_used: Optional[str] = None,
        extra_issues: Optional[List[Dict[str, Any]]] = None,
        honesty_verification: Optional[HonestyVerification] = None,
        requirements: Optional["RequirementsValidation"] = None,
    ) -> CoachValidationResult:
        """
        Create feedback result from failed quality gates.

        Generates feedback that clearly indicates which gates failed and which
        were skipped (optional per task type profile).

        Parameters
        ----------
        task_id : str
            Task identifier
        turn : int
            Turn number
        gates : QualityGateStatus
            Quality gate status with requirement flags
        task_work_results : Dict[str, Any]
            Task-work results for additional context
        extra_issues : Optional[List[Dict[str, Any]]]
            Issues to prepend to the gate-derived issues list. Used by
            F3c to thread the agent_invocations advisory through gate
            failures so process observations ride along with outcome
            feedback.
        honesty_verification : Optional[HonestyVerification]
            Honesty verification result if available
        requirements : Optional[RequirementsValidation]
            Requirements validation result. When the gate-fail short-circuit
            fires, this is populated by the hoisted call in ``validate(...)``
            so downstream consumers (autobuild stall detector) can read
            ``criteria_met`` even when gates fail (TASK-GK-CR-001).

        Returns
        -------
        CoachValidationResult
            Feedback result with gate-specific issues
        """
        issues: List[Dict[str, Any]] = list(extra_issues) if extra_issues else []

        # Extract from quality_gates for test details
        quality_gates = task_work_results.get("quality_gates", {})

        # Only report failures for required gates
        if gates.tests_required and not gates.tests_passed:
            # Detect incomplete session (all_passed is null, no test counts)
            all_passed_value = quality_gates.get("all_passed")
            tests_passed_count = quality_gates.get("tests_passed", 0) or 0
            tests_failed_count = quality_gates.get("tests_failed", 0) or 0
            if all_passed_value is None and tests_passed_count == 0 and tests_failed_count == 0:
                issues.append({
                    "severity": "must_fix",
                    "category": "test_failure",
                    "description": (
                        "Quality gate evaluation was not completed — the Player session "
                        "may have exhausted SDK turns before reaching Phase 4.5. "
                        "Focus on completing implementation within fewer SDK turns."
                    ),
                    "details": {
                        "failed_count": 0,
                        "total_count": 0,
                        "incomplete_session": True,
                    },
                })
            else:
                issues.append({
                    "severity": "must_fix",
                    "category": "test_failure",
                    "description": "Tests did not pass during task-work execution",
                    "details": {
                        "failed_count": tests_failed_count,
                        "total_count": tests_passed_count + tests_failed_count,
                    },
                })

        if gates.coverage_required and not gates.coverage_met:
            issues.append({
                "severity": "must_fix",
                "category": "coverage",
                "description": "Coverage threshold not met",
                "details": {
                    "line_coverage": quality_gates.get("coverage", 0),
                    "branch_coverage": quality_gates.get("branch_coverage", 0),
                },
            })

        if gates.arch_review_required and not gates.arch_review_passed:
            code_review = task_work_results.get("code_review", {})
            issues.append({
                "severity": "must_fix",
                "category": "architectural",
                "description": f"Architectural review score below threshold",
                "details": {
                    "score": code_review.get("score", 0),
                    "threshold": code_review.get("score", 0) >= 60 and 60 or code_review.get("score", 0),
                },
            })

        if gates.plan_audit_required and not gates.plan_audit_passed:
            plan_audit = task_work_results.get("plan_audit", {})
            # TASK-FIX-RWOP1.3.2: name the deterministic auditor's findings
            # in feedback so the Player's next turn can correct course.
            # Description is escalated to must_fix when severity == "high"
            # (the producer-side block signal); lower severities keep the
            # historical should_fix so legacy violations-only paths behave
            # unchanged.
            severity = plan_audit.get("severity")
            extra_files = plan_audit.get("extra_files") or []
            missing_files = plan_audit.get("missing_files") or []
            extra_modifications = plan_audit.get("extra_modifications") or []
            missing_modifications = plan_audit.get("missing_modifications") or []
            extra_deps = plan_audit.get("extra_dependencies") or []
            issue_severity = "must_fix" if severity == "high" else "should_fix"
            parts: List[str] = ["Plan audit detected"]
            if severity:
                parts.append(f"{severity}-severity")
            parts.append("discrepancies")
            if extra_files:
                preview = ", ".join(extra_files[:3])
                if len(extra_files) > 3:
                    preview += f", ... (+{len(extra_files) - 3} more)"
                parts.append(f"— {len(extra_files)} extra file(s): {preview}")
            if missing_files:
                preview = ", ".join(missing_files[:3])
                if len(missing_files) > 3:
                    preview += f", ... (+{len(missing_files) - 3} more)"
                parts.append(f"— {len(missing_files)} missing file(s): {preview}")
            if extra_modifications:
                preview = ", ".join(extra_modifications[:3])
                if len(extra_modifications) > 3:
                    preview += f", ... (+{len(extra_modifications) - 3} more)"
                parts.append(
                    f"— {len(extra_modifications)} unplanned modification(s): {preview}"
                )
            if missing_modifications:
                preview = ", ".join(missing_modifications[:3])
                if len(missing_modifications) > 3:
                    preview += f", ... (+{len(missing_modifications) - 3} more)"
                parts.append(
                    f"— {len(missing_modifications)} unmodified planned file(s): {preview}"
                )
            if extra_deps:
                preview = ", ".join(extra_deps[:3])
                parts.append(f"— extra dep(s): {preview}")

            issues.append({
                "severity": issue_severity,
                "category": "plan_audit",
                "description": " ".join(parts),
                "details": {
                    "status": plan_audit.get("status"),
                    "severity": severity,
                    "violations": plan_audit.get("violations", 0),
                    "extra_files": extra_files,
                    "missing_files": missing_files,
                    "extra_modifications": extra_modifications,
                    "missing_modifications": missing_modifications,
                    "extra_dependencies": extra_deps,
                    "missing_dependencies": plan_audit.get(
                        "missing_dependencies"
                    ) or [],
                    "loc_variance_pct": plan_audit.get("loc_variance_pct"),
                    "discrepancies_count": plan_audit.get(
                        "discrepancies_count", 0
                    ),
                },
            })

        # TASK-GK-CR-001 regression guard: gate-fail path must never flip
        # the decision or the all_gates_passed flag. Use a real exception
        # rather than `assert` so the invariant survives `python -O`.
        if gates.all_gates_passed:
            raise ValueError(
                "_feedback_from_gates called but all_gates_passed is True; "
                "this is a programming error — decision must remain 'feedback'."
            )

        return CoachValidationResult(
            task_id=task_id,
            turn=turn,
            decision="feedback",
            quality_gates=gates,
            independent_tests=None,
            requirements=requirements,
            issues=issues,
            rationale=f"{len(issues)} quality gate(s) failed",
            context_used=context_used,
            honesty_verification=honesty_verification,
        )

    def save_decision(self, result: CoachValidationResult) -> Path:
        """
        Save Coach decision to JSON file.

        Saves to: `.guardkit/autobuild/{task_id}/coach_turn_{turn}.json`

        Parameters
        ----------
        result : CoachValidationResult
            Validation result to save

        Returns
        -------
        Path
            Path to saved decision file
        """
        decision_dir = self.worktree_path / ".guardkit" / "autobuild" / result.task_id
        decision_dir.mkdir(parents=True, exist_ok=True)

        decision_path = decision_dir / f"coach_turn_{result.turn}.json"

        with open(decision_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)

        logger.info(f"Saved Coach decision to {decision_path}")
        return decision_path

    # ========================================================================
    # Security Review Verification (Read-Only)
    # ========================================================================

    def verify_security_review(
        self,
        task_id: str,
    ) -> Optional["SecurityReviewResult"]:
        """
        Verify security review results in read-only mode.

        Reads the persisted security review results from Phase 2.5C without
        re-running the security checks. This is a "trust but verify" pattern
        where Coach validates that the security review was executed and
        examines its results.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")

        Returns
        -------
        Optional[SecurityReviewResult]
            The persisted security review result, or None if not found

        Note
        ----
        This method is READ-ONLY. It does NOT re-run security checks.
        The security review was already executed during pre-loop Phase 2.5C.
        Coach simply reads the persisted results for verification.

        Example
        -------
        >>> validator = CoachValidator("/path/to/worktree")
        >>> result = validator.verify_security_review("TASK-001")
        >>> if result and result.blocked:
        ...     print(f"Security blocked: {result.critical_count} critical findings")
        """
        from guardkit.orchestrator.quality_gates.security_review import (
            load_security_review,
            SecurityReviewResult,
        )

        logger.debug(f"Verifying security review for {task_id} (read-only)")

        result = load_security_review(task_id, self.worktree_path)

        if result is None:
            logger.warning(f"No security review found for {task_id}")
            return None

        logger.info(
            f"Security review verified for {task_id}: "
            f"critical={result.critical_count}, high={result.high_count}, "
            f"blocked={result.blocked}"
        )

        return result

    def get_security_validation_issues(
        self,
        task_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get validation issues from security review for Coach decision.

        Reads the persisted security review and converts findings into
        validation issues that can be included in CoachValidationResult.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")

        Returns
        -------
        List[Dict[str, Any]]
            List of validation issues for security findings:
            - severity: "must_fix" for critical, "should_fix" for high,
                       "consider" for medium/low
            - category: "security"
            - description: Finding description
            - details: Full finding details

        Example
        -------
        >>> validator = CoachValidator("/path/to/worktree")
        >>> issues = validator.get_security_validation_issues("TASK-001")
        >>> for issue in issues:
        ...     print(f"{issue['severity']}: {issue['description']}")
        """
        from guardkit.orchestrator.quality_gates.security_review import (
            load_security_review,
        )

        issues: List[Dict[str, Any]] = []

        result = load_security_review(task_id, self.worktree_path)

        if result is None:
            # No security review found - not necessarily an error
            logger.debug(f"No security review found for {task_id}")
            return issues

        # Convert findings to validation issues
        for finding in result.findings:
            # Determine severity level for Coach
            if finding.severity == "critical":
                severity = "must_fix"
            elif finding.severity == "high":
                severity = "should_fix"
            else:
                severity = "consider"

            issues.append({
                "severity": severity,
                "category": "security",
                "description": f"[{finding.check_id}] {finding.description}",
                "details": {
                    "check_id": finding.check_id,
                    "file_path": finding.file_path,
                    "line_number": finding.line_number,
                    "matched_text": finding.matched_text,
                    "recommendation": finding.recommendation,
                },
            })

        # Add summary issue if there are critical findings
        if result.critical_count > 0:
            issues.insert(0, {
                "severity": "must_fix",
                "category": "security_summary",
                "description": (
                    f"Security review found {result.critical_count} critical finding(s). "
                    f"Task is BLOCKED until resolved."
                ),
                "details": {
                    "critical_count": result.critical_count,
                    "high_count": result.high_count,
                    "medium_count": result.medium_count,
                    "low_count": result.low_count,
                    "blocked": result.blocked,
                },
            })
        elif result.high_count > 0:
            issues.insert(0, {
                "severity": "should_fix",
                "category": "security_summary",
                "description": (
                    f"Security review found {result.high_count} high-severity finding(s). "
                    f"Consider addressing before completion."
                ),
                "details": {
                    "critical_count": result.critical_count,
                    "high_count": result.high_count,
                    "medium_count": result.medium_count,
                    "low_count": result.low_count,
                    "blocked": result.blocked,
                },
            })

        return issues


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "CoachValidator",
    "CoachValidationResult",
    "CriterionResult",
    "QualityGateStatus",
    "IndependentTestResult",
    "RequirementsValidation",
    "TASK_TYPE_ALIASES",
]
