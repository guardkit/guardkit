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
    """

    tests_passed: bool
    coverage_met: bool
    arch_review_passed: bool
    plan_audit_passed: bool
    all_gates_passed: bool = field(init=False)

    def __post_init__(self):
        """Compute all_gates_passed from individual gate results."""
        self.all_gates_passed = all([
            self.tests_passed,
            self.coverage_met,
            self.arch_review_passed,
            self.plan_audit_passed,
        ])


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

    def __init__(
        self,
        worktree_path: str,
        test_command: Optional[str] = None,
        test_timeout: int = 300,
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
        """
        self.worktree_path = Path(worktree_path)
        self.test_command = test_command
        self.test_timeout = test_timeout

        logger.debug(f"CoachValidator initialized for worktree: {worktree_path}")

    def validate(
        self,
        task_id: str,
        turn: int,
        task: Dict[str, Any],
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

        Returns
        -------
        CoachValidationResult
            Complete validation result with decision
        """
        logger.info(f"Starting Coach validation for {task_id} turn {turn}")

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

        # 2. Verify quality gates passed
        gates_status = self.verify_quality_gates(task_work_results)

        if not gates_status.all_gates_passed:
            logger.info(f"Quality gates failed for {task_id}: {gates_status}")
            return self._feedback_from_gates(
                task_id=task_id,
                turn=turn,
                gates=gates_status,
                task_work_results=task_work_results,
            )

        # 3. Independent test verification (trust but verify)
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
        results_path = self.worktree_path / ".guardkit" / "autobuild" / task_id / "task_work_results.json"

        if not results_path.exists():
            logger.warning(f"Task-work results not found at {results_path}")
            return {"error": f"Task-work results not found at {results_path}"}

        try:
            with open(results_path) as f:
                results = json.load(f)
            logger.debug(f"Loaded task-work results from {results_path}")
            return results
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse task-work results: {e}")
            return {"error": f"Failed to parse task-work results: {e}"}
        except Exception as e:
            logger.error(f"Failed to read task-work results: {e}")
            return {"error": f"Failed to read task-work results: {e}"}

    def verify_quality_gates(self, task_work_results: Dict[str, Any]) -> QualityGateStatus:
        """
        Verify task-work quality gates passed.

        Checks the following gates from task-work results:
        - tests_passed: From Phase 4.5 test results
        - coverage_met: From Phase 4.5 coverage check
        - arch_review_passed: From Phase 5 code review (score >= 60)
        - plan_audit_passed: From Phase 5.5 plan audit (0 violations)

        Parameters
        ----------
        task_work_results : Dict[str, Any]
            Results from task-work execution

        Returns
        -------
        QualityGateStatus
            Status of all quality gates
        """
        # Extract test results
        test_results = task_work_results.get("test_results", {})
        tests_passed = test_results.get("all_passed", False)

        # Extract coverage results
        coverage = task_work_results.get("coverage", {})
        coverage_met = coverage.get("threshold_met", True)  # Default True if not present

        # Extract architectural review results
        code_review = task_work_results.get("code_review", {})
        arch_score = code_review.get("score", 0)
        arch_review_passed = arch_score >= self.ARCH_REVIEW_THRESHOLD

        # Extract plan audit results
        plan_audit = task_work_results.get("plan_audit", {})
        violations = plan_audit.get("violations", 0)
        plan_audit_passed = violations == 0

        status = QualityGateStatus(
            tests_passed=tests_passed,
            coverage_met=coverage_met,
            arch_review_passed=arch_review_passed,
            plan_audit_passed=plan_audit_passed,
        )

        logger.debug(
            f"Quality gate status: tests={tests_passed}, coverage={coverage_met}, "
            f"arch={arch_review_passed} (score={arch_score}), audit={plan_audit_passed}"
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
        # Determine test command
        test_cmd = self.test_command or self._detect_test_command()

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

    def _detect_test_command(self) -> str:
        """
        Auto-detect the test command based on project files.

        Returns
        -------
        str
            Detected test command
        """
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

        Parameters
        ----------
        task_id : str
            Task identifier
        turn : int
            Turn number
        gates : QualityGateStatus
            Quality gate status
        task_work_results : Dict[str, Any]
            Task-work results for additional context

        Returns
        -------
        CoachValidationResult
            Feedback result with gate-specific issues
        """
        issues = []

        if not gates.tests_passed:
            test_results = task_work_results.get("test_results", {})
            issues.append({
                "severity": "must_fix",
                "category": "test_failure",
                "description": "Tests did not pass during task-work execution",
                "details": {
                    "failed_count": test_results.get("failed", 0),
                    "total_count": test_results.get("total", 0),
                },
            })

        if not gates.coverage_met:
            coverage = task_work_results.get("coverage", {})
            issues.append({
                "severity": "must_fix",
                "category": "coverage",
                "description": "Coverage threshold not met",
                "details": {
                    "line_coverage": coverage.get("line", 0),
                    "branch_coverage": coverage.get("branch", 0),
                },
            })

        if not gates.arch_review_passed:
            code_review = task_work_results.get("code_review", {})
            issues.append({
                "severity": "must_fix",
                "category": "architectural",
                "description": f"Architectural review score below {self.ARCH_REVIEW_THRESHOLD}",
                "details": {
                    "score": code_review.get("score", 0),
                    "threshold": self.ARCH_REVIEW_THRESHOLD,
                },
            })

        if not gates.plan_audit_passed:
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
