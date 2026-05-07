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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    HonestyVerification,
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
    """

    tests_passed: bool
    test_command: str
    test_output_summary: str
    duration_seconds: float
    raw_output: Optional[str] = None


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
        """
        self.worktree_path = Path(worktree_path)
        self.test_command = test_command
        self.test_timeout = test_timeout
        self.task_id = task_id
        self._coach_test_execution = coach_test_execution
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
            Player's task_work_results.json payload. Reads ``files_created``
            and ``files_modified`` to determine this task's edit set.

        Returns
        -------
        Dict[str, frozenset[str]]
            Map from peer task id to set of overlapping file paths. Empty when
            no peer edits overlap, when this task has no recorded edits, or
            when no peer snapshot was supplied.
        """
        if not self._peer_changed_files:
            return {}
        own = set(task_work_results.get("files_created", []) or [])
        own.update(task_work_results.get("files_modified", []) or [])
        if not own:
            return {}
        own_normalised = {str(f) for f in own if f}
        overlaps: Dict[str, frozenset] = {}
        for peer_id, peer_files in self._peer_changed_files.items():
            shared = peer_files & own_normalised
            if shared:
                overlaps[peer_id] = frozenset(shared)
        return overlaps

    def _get_coach_test_model(self) -> Optional[str]:
        """Return the model for Coach SDK test invocations, or None to use CLI default.

        When set, GUARDKIT_COACH_TEST_MODEL allows operators to use a different
        model for Coach test execution (e.g. claude-haiku-4-5-20251001 to reduce
        cost on the real Anthropic API) while the CLI default works with vLLM.
        """
        import os
        return os.environ.get("GUARDKIT_COACH_TEST_MODEL") or None

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
        """Run tests via Claude Agent SDK Bash tool for environment parity.

        Uses the SDK to execute the test command inside a Claude Code session,
        ensuring the same shell environment (PATH, conda/venv activation, etc.)
        as the Player agent used during implementation.

        Parameters
        ----------
        test_cmd : str
            Shell command to run tests

        Returns
        -------
        IndependentTestResult
            Result of test execution via SDK
        """
        import asyncio
        import time

        try:
            from claude_agent_sdk import (
                query,
                ClaudeAgentOptions,
                AssistantMessage,
                UserMessage,
                ToolResultBlock,
                CLINotFoundError,
                ProcessError,
                CLIJSONDecodeError,
            )
        except ImportError as e:
            logger.warning(f"Claude Agent SDK not available for coach test execution: {e}")
            raise

        from guardkit.orchestrator.sdk_utils import check_assistant_message_error

        # TASK-FIX-7A09: MessageParseError is raised by the SDK's internal
        # parser when it hits a message type it doesn't recognise (e.g.
        # rate_limit_event on a newer API than the installed SDK knows
        # about). The class lives in the private _errors module because it
        # is not part of claude_agent_sdk.__all__. Graceful-fallback import
        # mirrors agent_invoker.py:2174 so test fixtures that mock
        # claude_agent_sdk as a MagicMock do not crash on the _errors
        # submodule.
        try:
            from claude_agent_sdk._errors import MessageParseError
        except ImportError:
            class MessageParseError(Exception):  # type: ignore[no-redef]
                """Sentinel when SDK does not expose _errors submodule."""
                pass

        start_time = time.time()
        prompt = f"Run the following test command and report the output:\n\n```bash\n{test_cmd}\n```\n\nProvide the full test output."

        try:
            # Use GUARDKIT_COACH_TEST_MODEL env var if set, otherwise CLI default
            model = self._get_coach_test_model()

            # Fix: ensure worktree root has priority on PYTHONPATH to avoid
            # stale .pth files from previous editable installs polluting sys.path
            current_pythonpath = os.environ.get("PYTHONPATH", "")
            worktree_str = str(self.worktree_path)
            new_pythonpath = f"{worktree_str}:{current_pythonpath}" if current_pythonpath else worktree_str
            logger.debug(f"Coach SDK PYTHONPATH: {new_pythonpath}")

            options_kwargs = dict(
                cwd=str(self.worktree_path),
                allowed_tools=["Bash"],
                permission_mode="bypassPermissions",
                max_turns=1,
                env={**os.environ, "PYTHONPATH": new_pythonpath},
            )
            if model is not None:
                options_kwargs["model"] = model
            options = ClaudeAgentOptions(**options_kwargs)

            # TASK-DIAG-F4A2: Preserve coach independent-test prompt + stream
            # under sdk_debug/turn_<n>/coach/test_run/ when
            # GUARDKIT_AUTOBUILD_PRESERVE_DEBUG is set. No-op otherwise.
            from guardkit.orchestrator.sdk_debug import (
                preserve_prompt as _sdk_preserve_prompt,
                preserve_event as _sdk_preserve_event,
            )
            _sdk_debug_dir = _sdk_preserve_prompt(
                workspace_root=self.worktree_path,
                task_id=self.task_id or "unknown",
                turn=self._turn,
                role="coach_test",
                prompt=prompt,
                options=options,
            )

            collected_text: List[str] = []
            bash_output: Optional[str] = None
            bash_is_error: Optional[bool] = None

            # TASK-FIX-7A09: Mirror the per-message defensive stream
            # iteration from agent_invoker._invoke_with_role
            # (TASK-FIX-7A03) onto the Coach independent-test SDK path.
            # Parse-type exceptions on individual messages
            # (MessageParseError from the SDK's internal parser hitting
            # an unknown message type; ValueError from "Unsupported
            # plugin type" etc.) are logged and skipped so one bad
            # message does not abort the whole test-verification turn.
            # Transport-level exceptions (ProcessError,
            # CLIJSONDecodeError, CLINotFoundError) are NOT caught here
            # — they bubble through to the outer except cascade where
            # their structured diagnostic info (exit_code, stderr) is
            # surfaced to the caller.
            unparseable_count = 0
            async with asyncio.timeout(self.test_timeout):
                gen = query(prompt=prompt, options=options)
                gen_iter = gen.__aiter__()
                while True:
                    try:
                        message = await gen_iter.__anext__()
                    except StopAsyncIteration:
                        break
                    except (MessageParseError, ValueError) as parse_err:
                        unparseable_count += 1
                        logger.warning(
                            f"TASK-FIX-7A09: Skipping unparseable SDK "
                            f"message in coach test stream "
                            f"(error_class="
                            f"{type(parse_err).__name__}): {parse_err}"
                        )
                        continue

                    # TASK-DIAG-F4A2: Preserve event to JSONL (no-op if disabled)
                    _sdk_preserve_event(_sdk_debug_dir, message)

                    err = check_assistant_message_error(message)
                    if err:
                        duration = time.time() - start_time
                        logger.error(f"SDK API error during coach test execution: {err}")
                        return IndependentTestResult(
                            tests_passed=False,
                            test_command=test_cmd,
                            test_output_summary=f"SDK API error: {err}",
                            duration_seconds=duration,
                            raw_output=f"SDK API error: {err}",
                        )

                    if isinstance(message, AssistantMessage):
                        from claude_agent_sdk import TextBlock
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                collected_text.append(block.text)
                    elif isinstance(message, UserMessage):
                        # GAP-FIX #4: Extract Bash tool results from UserMessage
                        if hasattr(message, 'content') and isinstance(message.content, list):
                            for block in message.content:
                                if isinstance(block, ToolResultBlock):
                                    block_text = self._extract_content_text(block.content)
                                    if block_text:
                                        bash_output = block_text
                                    # GAP-FIX #6/#7: Three-way is_error handling
                                    is_err = getattr(block, 'is_error', None)
                                    if is_err is True:
                                        bash_is_error = True
                                    elif is_err is False:
                                        bash_is_error = False
                                    # None: parse output text to determine pass/fail

            if unparseable_count > 0:
                logger.warning(
                    f"TASK-FIX-7A09: coach test stream completed with "
                    f"{unparseable_count} unparseable message(s) dropped"
                )

            duration = time.time() - start_time

            # Determine pass/fail from bash_is_error and output
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
            )
        # TASK-FIX-7A09: Split the former catch-all into explicit handlers
        # so transport-level failures carry structured diagnostic info
        # (exit_code, stderr, error_class) through to the fallback log in
        # run_independent_tests. The original exceptions are re-raised
        # untouched — ProcessError already carries .exit_code and .stderr,
        # CLIJSONDecodeError carries .line and .original_error — so the
        # caller can introspect type/attributes without string-matching.
        except CLINotFoundError as e:
            duration = time.time() - start_time
            logger.error(
                f"SDK coach test execution failed "
                f"(error_class=CLINotFoundError): {e}"
            )
            raise
        except ProcessError as e:
            duration = time.time() - start_time
            stderr_val = getattr(e, "stderr", None)
            stderr_head = stderr_val[:500] if isinstance(stderr_val, str) else None
            logger.error(
                f"SDK coach test execution failed "
                f"(error_class=ProcessError, "
                f"exit_code={getattr(e, 'exit_code', None)}, "
                f"stderr_head={stderr_head!r}): {e}"
            )
            raise
        except CLIJSONDecodeError as e:
            duration = time.time() - start_time
            logger.error(
                f"SDK coach test execution failed "
                f"(error_class=CLIJSONDecodeError): {e}"
            )
            raise
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"SDK coach test execution failed "
                f"(error_class={type(e).__name__}): {e}"
            )
            raise

    def _is_custom_api_base(self) -> bool:
        """Return True when ANTHROPIC_BASE_URL points to a non-Anthropic endpoint (e.g. vLLM)."""
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        return bool(base_url) and "api.anthropic.com" not in base_url

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
                    cmd = [sys.executable, "-m", "pytest"] + parts[1:]
                    result = subprocess.run(
                        cmd,
                        cwd=str(tmpdir_path),
                        capture_output=True,
                        text=True,
                        timeout=self.test_timeout,
                        env=os.environ,
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
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[TASK-ABFIX-005] Isolated test execution failed: {e}")
            return IndependentTestResult(
                tests_passed=False,
                test_command=test_cmd,
                test_output_summary=f"Isolated test execution failed: {e}",
                duration_seconds=duration,
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
        # Interpreter consistency diagnostic (TASK-REV-CB30 R7)
        import shutil
        which_pytest = shutil.which("pytest")
        logger.info(
            "Test execution environment: sys.executable=%s, "
            "which pytest=%s, coach_test_execution=%s",
            sys.executable,
            which_pytest,
            self._coach_test_execution,
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
            use_sdk = (
                self._coach_test_execution == "sdk"
                and not requires_infra
                and not self._is_custom_api_base()
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
                    cmd = [sys.executable, "-m", "pytest"] + parts[1:]
                    result = subprocess.run(
                        cmd,
                        cwd=str(self.worktree_path),
                        capture_output=True,
                        text=True,
                        timeout=self.test_timeout,
                        env=os.environ,
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
                )
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Test execution failed: {e}")
                return IndependentTestResult(
                    tests_passed=False,
                    test_command=test_cmd,
                    test_output_summary=f"Test execution failed: {e}",
                    duration_seconds=duration,
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
        and numbered prefixes (1. , 2) , 1) ).

        Parameters
        ----------
        text : str
            Text to clean

        Returns
        -------
        str
            Cleaned text without prefix
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

        # Strip AC-NNN: prefixes (e.g., "AC-001: Some text")
        ac_match = re.match(r'^AC-\d+:\s*', cleaned)
        if ac_match:
            cleaned = cleaned[ac_match.end():].strip()

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

        Used by:
        - TASK-AB-FIX-INVAB1 AC-004: tightening the "No completion promise"
          hybrid-fallback branch to require the named path to exist on disk.
        - TASK-AB-FIX-INVAB1 AC-005: plan_audit ``skipped`` escalation when
          AC names a missing source file.
        """
        if not criterion_text:
            return []
        primary = re.findall(r"[\w./\-]+\.\w{1,5}", criterion_text)
        backtick = re.findall(r"`([^`]+\.[a-zA-Z]+)`", criterion_text)
        double_q = re.findall(r'"([^"]+\.[a-zA-Z]+)"', criterion_text)
        single_q = re.findall(r"'([^']+\.[a-zA-Z]+)'", criterion_text)
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
                files_str = " ".join(
                    str(f.relative_to(self.worktree_path)) for f in sorted(unique_files)
                )
                logger.info(f"Task-specific tests detected for {task_id}: {len(unique_files)} file(s)")
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
                            files_str = " ".join(sorted(test_files))
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
                        files_str = " ".join(sorted(promise_test_files))
                        logger.info(
                            f"Found test files via completion_promises for "
                            f"{task_id}: {len(promise_test_files)} file(s)"
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
            for f in failures[:5]:
                scenario = f.get("scenario_name", "<unknown>")
                step = f.get("failing_step", "")
                reason = f.get("reason", "")
                summary = f"{scenario}"
                if step:
                    summary += f" — step: {step}"
                if reason:
                    summary += f" — {reason[:160]}"
                failure_summaries.append(summary)

            blocking.append({
                "severity": "must_fix",
                "category": "bdd_failure",
                "description": (
                    f"BDD oracle: {scenarios_failed} scenario(s) failed "
                    f"during pytest-bdd execution. "
                    f"Implementation does not satisfy the Gherkin specification."
                ),
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
            total = verifier._count_verifiable_claims(task_work_results)
            critical = sum(1 for d in discrepancies if d.severity == "critical")
            return HonestyVerification(
                verified=len(discrepancies) == 0,
                discrepancies=discrepancies,
                honesty_score=1.0 - (critical / max(total, 1)),
                resolved_paths=list(verifier._resolved_paths),
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
        """
        critical = [d for d in honesty.discrepancies if d.severity == "critical"]
        demote = (
            len(critical) == 1
            and critical[0].claim_type == "file_existence"
        )
        severity = "should_fix" if demote else "must_fix"
        issues: List[Dict[str, Any]] = []
        for d in critical:
            issues.append(
                {
                    "severity": severity,
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
        return issues

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
