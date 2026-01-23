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
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.models.task_types import TaskType, QualityGateProfile, get_profile

logger = logging.getLogger(__name__)


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
    """

    tests_passed: bool
    test_command: str
    test_output_summary: str
    duration_seconds: float


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
    """

    criteria_total: int
    criteria_met: int
    all_criteria_met: bool
    missing: List[str] = field(default_factory=list)


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

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary for JSON serialization.

        Returns
        -------
        Dict[str, Any]
            Dictionary representation suitable for JSON
        """
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
            "issues": self.issues,
            "rationale": self.rationale,
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

    def __init__(
        self,
        worktree_path: str,
        test_command: Optional[str] = None,
        test_timeout: int = 300,
        task_id: Optional[str] = None,
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
        """
        self.worktree_path = Path(worktree_path)
        self.test_command = test_command
        self.test_timeout = test_timeout
        self.task_id = task_id

        logger.debug(f"CoachValidator initialized for worktree: {worktree_path}, task_id: {task_id}")

    def _resolve_task_type(self, task: Dict[str, Any]) -> TaskType:
        """
        Resolve task type from task metadata with fallback to default.

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
            If task_type is specified but invalid
        """
        task_type_str = task.get("task_type")

        if task_type_str is None:
            # No task_type specified - use default (feature)
            logger.debug("No task_type specified, defaulting to FEATURE profile")
            return TaskType.FEATURE

        # Validate task_type value
        try:
            task_type = TaskType(task_type_str)
            logger.debug(f"Resolved task_type from metadata: {task_type.value}")
            return task_type
        except ValueError as e:
            logger.error(f"Invalid task_type value: {task_type_str}")
            raise ValueError(
                f"Invalid task_type value: {task_type_str}. "
                f"Must be one of: {', '.join(t.value for t in TaskType)}"
            ) from e

    def validate(
        self,
        task_id: str,
        turn: int,
        task: Dict[str, Any],
        skip_arch_review: bool = False,
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
            test_result = self.run_independent_tests()

        if not test_result.tests_passed:
            logger.warning(f"Independent test verification failed for {task_id}")
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                quality_gates=gates_status,
                independent_tests=test_result,
                issues=[{
                    "severity": "must_fix",
                    "category": "test_verification",
                    "description": "Independent test verification failed",
                    "test_output": test_result.test_output_summary,
                }],
                rationale="Tests passed according to task-work but failed on independent verification",
            )

        # 4. Validate requirements satisfaction
        requirements = self.validate_requirements(task, task_work_results)

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
            )

        # 5. All checks passed - approve
        logger.info(f"Coach approved {task_id} turn {turn}")

        return CoachValidationResult(
            task_id=task_id,
            turn=turn,
            decision="approve",
            quality_gates=gates_status,
            independent_tests=test_result,
            requirements=requirements,
            issues=[],
            rationale="All quality gates passed. Independent verification confirmed. All acceptance criteria met.",
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
            tests_passed = quality_gates["all_passed"]
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

    def run_independent_tests(self) -> IndependentTestResult:
        """
        Run tests independently to verify Player's report.

        This is a "trust but verify" check - we run the tests ourselves
        to ensure the Player's reported results are accurate.

        Returns
        -------
        IndependentTestResult
            Result of independent test execution
        """
        # Determine test command (pass task_id for task-specific filtering)
        test_cmd = self.test_command or self._detect_test_command(self.task_id)

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

        logger.info(f"Running independent tests: {test_cmd}")
        start_time = time.time()

        try:
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

    def validate_requirements(
        self,
        task: Dict[str, Any],
        task_work_results: Dict[str, Any],
    ) -> RequirementsValidation:
        """
        Validate all requirements and acceptance criteria are met.

        Compares the task's acceptance criteria against the requirements
        reported as met by task-work.

        Parameters
        ----------
        task : Dict[str, Any]
            Task data including acceptance_criteria
        task_work_results : Dict[str, Any]
            Results from task-work execution

        Returns
        -------
        RequirementsValidation
            Validation result with met/missing criteria
        """
        acceptance_criteria = task.get("acceptance_criteria", [])
        requirements_met = task_work_results.get("requirements_met", [])

        # Normalize criteria for comparison (lowercase, strip whitespace)
        normalized_criteria = {c.lower().strip() for c in acceptance_criteria}
        normalized_met = {r.lower().strip() for r in requirements_met}

        # Find missing criteria
        missing = [
            c for c in acceptance_criteria
            if c.lower().strip() not in normalized_met
        ]

        criteria_met_count = len(acceptance_criteria) - len(missing)

        validation = RequirementsValidation(
            criteria_total=len(acceptance_criteria),
            criteria_met=criteria_met_count,
            all_criteria_met=len(missing) == 0,
            missing=missing,
        )

        logger.debug(
            f"Requirements validation: {criteria_met_count}/{len(acceptance_criteria)} met, "
            f"missing: {missing}"
        )

        return validation

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

    def _detect_test_command(self, task_id: Optional[str] = None) -> Optional[str]:
        """
        Auto-detect the test command based on project files.

        When task_id is provided, attempts to find task-specific test files
        first. If no task-specific tests are found and task_id was provided,
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

        Returns
        -------
        Optional[str]
            Detected test command, or None if task_id was provided but no
            task-specific tests were found (signals to skip verification)
        """
        # Try task-specific filtering first (for shared worktrees)
        if task_id:
            task_prefix = self._task_id_to_pattern_prefix(task_id)
            # Pattern: tests/test_{task_prefix}*.py (most common test organization)
            pattern = f"tests/test_{task_prefix}*.py"

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
            else:
                # No task-specific tests found - skip verification in this case
                # Running all tests would include tests from other parallel tasks
                logger.info(f"No task-specific tests found for {task_id}, skipping independent verification")
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

    def _summarize_test_output(self, output: str, max_length: int = 500) -> str:
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
            Summarized output
        """
        # Extract last lines which usually contain summary
        lines = output.strip().split("\n")

        # Look for common test summary patterns
        summary_lines = []
        for line in reversed(lines[-20:]):  # Check last 20 lines
            if any(keyword in line.lower() for keyword in [
                "passed", "failed", "error", "skipped",
                "success", "failure", "ok", "tests"
            ]):
                summary_lines.insert(0, line.strip())
                if len(summary_lines) >= 3:
                    break

        if summary_lines:
            summary = "\n".join(summary_lines)
        else:
            # Fallback to last few lines
            summary = "\n".join(lines[-3:])

        # Truncate if needed
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        return summary

    def _feedback_result(
        self,
        task_id: str,
        turn: int,
        issues: List[Dict[str, Any]],
        rationale: str,
        quality_gates: Optional[QualityGateStatus] = None,
        independent_tests: Optional[IndependentTestResult] = None,
        requirements: Optional[RequirementsValidation] = None,
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
        )

    def _feedback_from_gates(
        self,
        task_id: str,
        turn: int,
        gates: QualityGateStatus,
        task_work_results: Dict[str, Any],
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
            issues.append({
                "severity": "must_fix",
                "category": "test_failure",
                "description": "Tests did not pass during task-work execution",
                "details": {
                    "failed_count": quality_gates.get("tests_failed", 0),
                    "total_count": quality_gates.get("tests_passed", 0) + quality_gates.get("tests_failed", 0),
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


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "CoachValidator",
    "CoachValidationResult",
    "QualityGateStatus",
    "IndependentTestResult",
    "RequirementsValidation",
]
