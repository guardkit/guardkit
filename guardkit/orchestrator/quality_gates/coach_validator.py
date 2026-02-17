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

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from guardkit.orchestrator.docker_fixtures import (
    get_container_name,
    get_env_exports,
    get_start_commands,
    is_known_service,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.models.task_types import TaskType, QualityGateProfile, get_profile

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

# Task type aliases for backward compatibility with legacy task_type values
# See: TASK-REV-FMT2 for analysis of legacy values in codebase
TASK_TYPE_ALIASES: Dict[str, TaskType] = {
    "implementation": TaskType.FEATURE,
    "bug-fix": TaskType.FEATURE,
    "bug_fix": TaskType.FEATURE,
    "benchmark": TaskType.TESTING,
    "research": TaskType.DOCUMENTATION,
}

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
    decision: Literal["approve", "feedback"]
    quality_gates: Optional[QualityGateStatus] = None
    independent_tests: Optional[IndependentTestResult] = None
    requirements: Optional[RequirementsValidation] = None
    issues: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    context_used: Optional[str] = None
    approved_without_independent_tests: bool = False

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

    # Ambiguous infrastructure patterns (feedback only, not conditional approval)
    _INFRA_AMBIGUOUS: List[str] = [
        "ModuleNotFoundError",
        "ImportError",
        "No module named",
    ]

    def __init__(
        self,
        worktree_path: str,
        test_command: Optional[str] = None,
        test_timeout: int = 300,
        task_id: Optional[str] = None,
        coach_test_execution: str = "sdk",
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
        """
        self.worktree_path = Path(worktree_path)
        self.test_command = test_command
        self.test_timeout = test_timeout
        self.task_id = task_id
        self._coach_test_execution = coach_test_execution

        logger.debug(f"CoachValidator initialized for worktree: {worktree_path}, task_id: {task_id}")

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
            profile = get_profile(task_type)
            logger.info(f"Using quality gate profile for task type: {task_type.value}")
        except ValueError as e:
            logger.error(f"Failed to resolve task type: {e}")
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
            )

        # 1. Read task-work quality gate results
        task_work_results = self.read_quality_gate_results(task_id)

        if "error" in task_work_results:
            logger.warning(f"Task-work results not found for {task_id}")
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

        # 2. Verify quality gates passed with profile
        gates_status = self.verify_quality_gates(
            task_work_results, profile=profile, skip_arch_review=skip_arch_review
        )

        if not gates_status.all_gates_passed:
            logger.info(f"Quality gates failed for {task_id}: {gates_status}")
            return self._feedback_from_gates(
                task_id=task_id,
                turn=turn,
                gates=gates_status,
                task_work_results=task_work_results,
                context_used=context,
            )

        # 3. Independent test verification (trust but verify)
        # Skip independent tests for task types that don't require tests (e.g., scaffolding)
        if not profile.tests_required:
            test_result = IndependentTestResult(
                tests_passed=True,
                test_command="skipped",
                test_output_summary="Independent test verification skipped (tests_required=False)",
                duration_seconds=0.0,
            )
            logger.info(f"Independent test verification skipped for {task_id} (tests_required=False)")
        else:
            test_result = self.run_independent_tests(
                task_work_results=task_work_results,
                task=task,
            )

        conditional_approval = False
        if not test_result.tests_passed:
            failure_class, failure_confidence = self._classify_test_failure(test_result.raw_output)
            logger.warning(
                f"Independent test verification failed for {task_id} "
                f"(classification={failure_class}, confidence={failure_confidence})"
            )

            # Conditional approval for high-confidence infrastructure failures
            # when task declares requires_infrastructure and Docker is unavailable
            requires_infra = task.get("requires_infrastructure", [])
            docker_available = task.get("_docker_available", True)

            conditional_approval = (
                failure_class == "infrastructure"
                and failure_confidence == "high"
                and bool(requires_infra)
                and not docker_available
                and gates_status.all_gates_passed
            )

            if conditional_approval:
                logger.warning(
                    f"Conditional approval for {task_id}: infrastructure failure "
                    f"with declared deps {requires_infra}, Docker unavailable. "
                    f"Continuing to requirements check."
                )
                # Fall through to requirements check with conditional flag set
            else:
                if failure_class == "infrastructure":
                    description = (
                        "Tests failed due to infrastructure/environment issues "
                        "(not code defects). Remediation options: "
                        "(1) Add mock fixtures for external services, "
                        "(2) Use SQLite for test database, "
                        "(3) Mark integration tests with @pytest.mark.integration "
                        "and exclude via -m 'not integration'"
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
                    issues=[{
                        "severity": "must_fix",
                        "category": "test_verification",
                        "description": description,
                        "test_output": test_result.test_output_summary,
                        "failure_classification": failure_class,
                        "failure_confidence": failure_confidence,
                    }],
                    rationale=rationale,
                    context_used=context,
                )

        # 4. Validate requirements satisfaction
        requirements = self.validate_requirements(task, task_work_results, turn=turn)

        if not requirements.all_criteria_met:
            logger.info(f"Requirements not met for {task_id}: missing {requirements.missing}")
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                quality_gates=gates_status,
                independent_tests=test_result,
                requirements=requirements,
                issues=[{
                    "severity": "must_fix",
                    "category": "missing_requirement",
                    "description": f"Not all acceptance criteria met",
                    "missing_criteria": requirements.missing,
                }],
                rationale=f"Missing {len(requirements.missing)} acceptance criteria: {', '.join(requirements.missing)}",
                context_used=context,
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
                issues=zero_test_issues,
                rationale=(
                    "Zero-test anomaly detected: quality gates reported as passed but "
                    "no tests were executed. Tests are required for this task type. "
                    "Please write and run tests before resubmitting."
                ),
                context_used=context,
            )

        # 5.5. Check for seam test recommendations (soft gate, non-blocking)
        seam_test_issues = self._check_seam_test_recommendation(
            task_work_results, profile
        )

        # Combine all non-blocking issues
        all_issues = zero_test_issues + seam_test_issues

        # 6. All checks passed - approve
        if conditional_approval:
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
            violations = plan_audit.get("violations", 0)
            plan_audit_passed = violations == 0
            logger.debug(f"Extracted plan_audit_passed={plan_audit_passed} (violations={violations})")

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

        start_time = time.time()
        prompt = f"Run the following test command and report the output:\n\n```bash\n{test_cmd}\n```\n\nProvide the full test output."

        try:
            options = ClaudeAgentOptions(
                cwd=str(self.worktree_path),
                allowed_tools=["Bash"],
                permission_mode="bypassPermissions",
                max_turns=1,
                model="claude-haiku-4-5-20251001",
            )

            collected_text: List[str] = []
            bash_output: Optional[str] = None
            bash_is_error: Optional[bool] = None

            async with asyncio.timeout(self.test_timeout):
                async for message in query(prompt=prompt, options=options):
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
        except (CLINotFoundError, ProcessError, CLIJSONDecodeError, Exception) as e:
            duration = time.time() - start_time
            logger.error(f"SDK coach test execution failed: {e}")
            raise

    def run_independent_tests(
        self,
        task_work_results: Optional[Dict[str, Any]] = None,
        task: Optional[Dict[str, Any]] = None,
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

        Returns
        -------
        IndependentTestResult
            Result of independent test execution
        """
        # Determine test command (pass task_id and results for task-specific filtering)
        test_cmd = self.test_command or self._detect_test_command(
            self.task_id, task_work_results=task_work_results
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
            # SDK-first dispatch (GAP-FIX #9): use asyncio bridge to call async SDK method
            if self._coach_test_execution == "sdk":
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
                    logger.warning(
                        f"SDK test execution failed, falling back to subprocess: {e}"
                    )
                    # Fall through to subprocess path below

            # Subprocess path (default for coach_test_execution="subprocess" or SDK fallback)
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

        # Fast-fail path for synthetic reports (TASK-ASF-006)
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
                    logger.warning("  matching_strategy: promises (synthetic)")
                    logger.warning("  _synthetic: True")
                return validation
            # No promises on synthetic report — all criteria unmet
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
            requirements_met = task_work_results.get("requirements_met", [])
            validation = self._match_by_text(acceptance_criteria, requirements_met)

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
            task_id = task_work_results.get("task_id", "")
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

        return []

    def _match_by_promises(
        self,
        acceptance_criteria: List[str],
        completion_promises: List[Dict[str, Any]],
    ) -> RequirementsValidation:
        """
        Match acceptance criteria to Player completion promises by criterion ID.

        Each acceptance criterion at index *i* maps to ``AC-{i+1:03d}``.
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
        # Build promise map: criterion_id -> promise dict
        promise_map: Dict[str, Dict[str, Any]] = {}
        for p in completion_promises:
            cid = p.get("criterion_id", "")
            if cid:
                promise_map[cid] = p

        criteria_results: List[CriterionResult] = []
        missing: List[str] = []

        for i, criterion_text in enumerate(acceptance_criteria):
            criterion_id = f"AC-{i+1:03d}"
            promise = promise_map.get(criterion_id)

            if promise and promise.get("status") == "complete":
                result_str = "verified"
                evidence = promise.get(
                    "evidence",
                    f"Player completed {criterion_id}",
                )
            elif promise and promise.get("status") == "partial":
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

        return cleaned

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
        words = text.lower().split()

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
        3. Keyword overlap (>=70% similarity)

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
        # Strip prefixes and normalize requirements_met
        stripped_met = [self._strip_criterion_prefix(r) for r in requirements_met]
        normalized_met = {r.lower().strip() for r in stripped_met}

        criteria_results: List[CriterionResult] = []
        missing: List[str] = []

        for i, criterion_text in enumerate(acceptance_criteria):
            criterion_id = f"AC-{i+1:03d}"

            # Strip prefix from criterion
            stripped_criterion = self._strip_criterion_prefix(criterion_text)
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

                            # Calculate Jaccard similarity
                            intersection = criterion_keywords & met_keywords
                            union = criterion_keywords | met_keywords

                            if union:
                                score = len(intersection) / len(union)
                                if score > best_match_score:
                                    best_match_score = score
                                    best_match_text = met_text

                        # Accept if similarity >= 70%
                        if best_match_score >= 0.70:
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
                and "No completion promise" in promise_cr.evidence
            ):
                # Only upgrade criteria that had NO promise at all.
                # If the Player explicitly marked a criterion as "incomplete",
                # trust that over a text match.
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
        criteria_results = []
        for i, criterion_text in enumerate(acceptance_criteria):
            criterion_id = f"AC-{i+1:03d}"
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

        Converts task IDs like "TASK-FHA-002" to "task_fha_002" for
        matching against test file naming conventions.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-FHA-002")

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
    ) -> Optional[str]:
        """
        Auto-detect the test command based on project files.

        When task_id is provided, attempts to find task-specific test files
        using two sources in priority order:
        1. Primary: Extract test files from task_work_results (already in memory)
        2. Fallback: Task-ID glob pattern on disk

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

    def _detect_tests_from_results(
        self, task_work_results: Dict[str, Any]
    ) -> Optional[str]:
        """
        Primary test detection: find test files from task_work_results.

        Extracts test files (matching ``test_*.py`` or ``*_test.py``) from
        the files_created/files_modified lists in task_work_results. Only
        returns files that actually exist in the worktree.

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Task-work results dict containing files_created and files_modified

        Returns
        -------
        Optional[str]
            pytest command targeting discovered test files, or None
        """
        test_files = []
        for file_list_key in ("files_created", "files_modified"):
            for filepath in task_work_results.get(file_list_key, []):
                normalized = self._normalize_to_relative(filepath)
                basename = Path(normalized).name
                if basename.startswith("test_") and basename.endswith(".py"):
                    full_path = self.worktree_path / normalized
                    if full_path.exists():
                        test_files.append(str(normalized))
                elif basename.endswith("_test.py"):
                    full_path = self.worktree_path / normalized
                    if full_path.exists():
                        test_files.append(str(normalized))

        if not test_files:
            logger.debug("No test files found in task_work_results")
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

    def _classify_test_failure(self, test_output: Optional[str]) -> Tuple[str, str]:
        """Classify a test failure as infrastructure or code with confidence.

        Checks high-confidence patterns first. If any high-confidence pattern
        matches, returns high confidence regardless of ambiguous matches.

        Parameters
        ----------
        test_output : Optional[str]
            Raw test stdout+stderr output

        Returns
        -------
        Tuple[str, str]
            ``("infrastructure", "high")`` if high-confidence pattern matches,
            ``("infrastructure", "ambiguous")`` if only ambiguous pattern matches,
            ``("code", "n/a")`` otherwise
        """
        if not test_output:
            logger.debug(f"[{self.task_id}] _classify_test_failure: no output → ('code', 'n/a')")
            return ("code", "n/a")
        output_lower = test_output.lower()
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

    def _build_approval_rationale(
        self,
        test_result: IndependentTestResult,
        gates_status: QualityGateStatus,
        task_work_results: Dict[str, Any],
        profile: QualityGateProfile,
        context: Optional[str] = None,
        conditional_approval: bool = False,
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
            True if this approval is conditional due to infrastructure test failure

        Returns
        -------
        str
            Accurate rationale message
        """
        parts = ["All quality gates passed."]

        if conditional_approval:
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
        )

    def _feedback_from_gates(
        self,
        task_id: str,
        turn: int,
        gates: QualityGateStatus,
        task_work_results: Dict[str, Any],
        context_used: Optional[str] = None,
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

        Returns
        -------
        CoachValidationResult
            Feedback result with gate-specific issues
        """
        issues = []

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
            issues.append({
                "severity": "should_fix",
                "category": "plan_audit",
                "description": "Plan audit detected violations",
                "details": {
                    "violations": plan_audit.get("violations", 0),
                },
            })

        return CoachValidationResult(
            task_id=task_id,
            turn=turn,
            decision="feedback",
            quality_gates=gates,
            independent_tests=None,
            requirements=None,
            issues=issues,
            rationale=f"{len(issues)} quality gate(s) failed",
            context_used=context_used,
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
