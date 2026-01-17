"""Coach Verification module for validating Player claims.

This module provides the CoachVerifier class that cross-references Player's
self-reported claims against actual test results and filesystem state.

The verification process detects discrepancies between:
- Claimed test results vs actual test execution
- Claimed files vs filesystem reality
- Claimed test counts vs parsed output

This pattern is inspired by the "intellectual honesty" design principle,
ensuring the Coach can trust Player reports.
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Discrepancy:
    """A discrepancy between Player claim and reality.

    Attributes:
        claim_type: Type of claim ("test_result", "file_existence", "test_count")
        player_claim: What the Player reported
        actual_value: What was actually found
        severity: Severity level ("critical", "warning", "info")
    """

    claim_type: str
    player_claim: str
    actual_value: str
    severity: str  # "critical", "warning", "info"


@dataclass
class TestResult:
    """Result of running tests.

    Attributes:
        passed: Whether all tests passed
        test_count: Number of tests that passed
        output: Raw test output
    """

    passed: bool
    test_count: int
    output: str


@dataclass
class HonestyVerification:
    """Result of verifying Player claims.

    Attributes:
        verified: True if all claims were verified successfully
        discrepancies: List of found discrepancies
        honesty_score: Score from 0.0 to 1.0 (1.0 = fully honest)
    """

    verified: bool
    discrepancies: List[Discrepancy] = field(default_factory=list)
    honesty_score: float = 1.0


class CoachVerifier:
    """Verifies Player claims against reality.

    This class provides verification logic to cross-reference Player's
    self-reported claims against actual test results and filesystem state.

    Attributes:
        worktree_path: Path to the isolated git worktree

    Example:
        >>> verifier = CoachVerifier(Path(".guardkit/worktrees/TASK-001"))
        >>> result = verifier.verify_player_report(player_report)
        >>> if not result.verified:
        ...     print(f"Discrepancies found: {result.discrepancies}")
    """

    def __init__(self, worktree_path: Path):
        """Initialize CoachVerifier.

        Args:
            worktree_path: Path to the isolated git worktree
        """
        self.worktree_path = Path(worktree_path)
        self._cached_test_result: Optional[TestResult] = None

    def verify_player_report(self, player_report: Dict[str, Any]) -> HonestyVerification:
        """Verify all verifiable claims in Player report.

        Performs three types of verification:
        1. Test results - Run tests and compare with claimed results
        2. File existence - Check claimed files exist on filesystem
        3. Test count - Verify test count matches claimed summary

        Args:
            player_report: Player's report dictionary containing claims

        Returns:
            HonestyVerification with verification results
        """
        discrepancies: List[Discrepancy] = []

        # Clear cached test result for fresh verification
        self._cached_test_result = None

        # Verify test results
        test_disc = self._verify_test_results(player_report)
        if test_disc:
            discrepancies.extend(test_disc)

        # Verify file existence
        file_disc = self._verify_files_exist(player_report)
        if file_disc:
            discrepancies.extend(file_disc)

        # Verify test count
        count_disc = self._verify_test_count(player_report)
        if count_disc:
            discrepancies.extend(count_disc)

        # Calculate honesty score
        total_claims = self._count_verifiable_claims(player_report)
        critical_failures = len([d for d in discrepancies if d.severity == "critical"])
        honesty_score = 1.0 - (critical_failures / max(total_claims, 1))

        return HonestyVerification(
            verified=len(discrepancies) == 0,
            discrepancies=discrepancies,
            honesty_score=honesty_score,
        )

    def _verify_test_results(self, report: Dict[str, Any]) -> List[Discrepancy]:
        """Verify tests_passed claim against actual test run.

        Args:
            report: Player report dictionary

        Returns:
            List of discrepancies found (empty if verified)
        """
        discrepancies: List[Discrepancy] = []

        claimed_passed = report.get("tests_passed", False)
        claimed_run = report.get("tests_run", False)

        if not claimed_run:
            # Player claims tests weren't run - nothing to verify
            return discrepancies

        # Run tests independently
        actual_result = self._run_tests()

        if claimed_passed != actual_result.passed:
            discrepancies.append(
                Discrepancy(
                    claim_type="test_result",
                    player_claim=f"tests_passed: {claimed_passed}",
                    actual_value=f"tests_passed: {actual_result.passed}",
                    severity="critical",
                )
            )

        return discrepancies

    def _verify_files_exist(self, report: Dict[str, Any]) -> List[Discrepancy]:
        """Verify claimed files actually exist.

        Args:
            report: Player report dictionary

        Returns:
            List of discrepancies for missing files
        """
        discrepancies: List[Discrepancy] = []

        for file_list_key in ["files_created", "files_modified", "tests_written"]:
            claimed_files = report.get(file_list_key, [])

            for file_path in claimed_files:
                full_path = self.worktree_path / file_path
                if not full_path.exists():
                    discrepancies.append(
                        Discrepancy(
                            claim_type="file_existence",
                            player_claim=f"{file_list_key}: {file_path}",
                            actual_value="File does not exist",
                            severity="critical",
                        )
                    )

        return discrepancies

    def _verify_test_count(self, report: Dict[str, Any]) -> List[Discrepancy]:
        """Verify test count in summary matches actual.

        Args:
            report: Player report dictionary

        Returns:
            List of discrepancies for mismatched counts
        """
        discrepancies: List[Discrepancy] = []

        summary = report.get("test_output_summary", "")
        if not summary:
            return discrepancies

        # Extract claimed count from summary (e.g., "5 passed in 0.23s")
        claimed_count = self._extract_test_count(summary)
        if claimed_count is None:
            return discrepancies

        # Run tests and get actual count (use cached result if available)
        actual_result = self._run_tests()
        actual_count = actual_result.test_count

        if claimed_count != actual_count:
            discrepancies.append(
                Discrepancy(
                    claim_type="test_count",
                    player_claim=f"{claimed_count} tests",
                    actual_value=f"{actual_count} tests",
                    severity="warning",
                )
            )

        return discrepancies

    def _run_tests(self) -> TestResult:
        """Run tests in worktree and return result.

        Uses caching to avoid running tests multiple times in the same
        verification session.

        Returns:
            TestResult with execution results
        """
        # Return cached result if available
        if self._cached_test_result is not None:
            return self._cached_test_result

        # Detect test framework and run appropriate command
        try:
            result = subprocess.run(
                ["pytest", "--tb=no", "-q"],
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self._cached_test_result = TestResult(
                passed=result.returncode == 0,
                test_count=self._parse_pytest_count(result.stdout),
                output=result.stdout,
            )
        except FileNotFoundError:
            logger.warning("pytest not found, trying python -m pytest")
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", "--tb=no", "-q"],
                    cwd=self.worktree_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                self._cached_test_result = TestResult(
                    passed=result.returncode == 0,
                    test_count=self._parse_pytest_count(result.stdout),
                    output=result.stdout,
                )
            except Exception as e:
                logger.error(f"Failed to run tests: {e}")
                self._cached_test_result = TestResult(
                    passed=False, test_count=0, output=str(e)
                )
        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out after 120s")
            self._cached_test_result = TestResult(
                passed=False, test_count=0, output="Test execution timed out"
            )
        except Exception as e:
            logger.error(f"Failed to run tests: {e}")
            self._cached_test_result = TestResult(
                passed=False, test_count=0, output=str(e)
            )

        return self._cached_test_result

    def _extract_test_count(self, summary: str) -> Optional[int]:
        """Extract test count from summary string.

        Args:
            summary: Test output summary string (e.g., "5 passed in 0.23s")

        Returns:
            Number of passed tests, or None if not parseable
        """
        match = re.search(r"(\d+)\s+passed", summary)
        return int(match.group(1)) if match else None

    def _parse_pytest_count(self, output: str) -> int:
        """Parse test count from pytest output.

        Args:
            output: Raw pytest output

        Returns:
            Number of passed tests
        """
        match = re.search(r"(\d+)\s+passed", output)
        return int(match.group(1)) if match else 0

    def _count_verifiable_claims(self, report: Dict[str, Any]) -> int:
        """Count total verifiable claims in report.

        Args:
            report: Player report dictionary

        Returns:
            Number of verifiable claims
        """
        count = 0
        if report.get("tests_run"):
            count += 2  # tests_passed + test_count
        count += len(report.get("files_created", []))
        count += len(report.get("files_modified", []))
        count += len(report.get("tests_written", []))
        return max(count, 1)  # Avoid division by zero


def format_verification_context(verification: HonestyVerification) -> str:
    """Format verification results for inclusion in Coach prompt.

    Args:
        verification: HonestyVerification result

    Returns:
        Formatted string for prompt injection
    """
    lines = [
        "HONESTY VERIFICATION RESULTS:",
        "━" * 30,
        f"Honesty Score: {verification.honesty_score:.2f}",
        "",
    ]

    if verification.discrepancies:
        lines.append("DISCREPANCIES FOUND:")
        for disc in verification.discrepancies:
            severity_icon = "✗" if disc.severity == "critical" else "⚠"
            lines.append(f"  {severity_icon} [{disc.severity.upper()}] {disc.claim_type}")
            lines.append(f"    Player claimed: {disc.player_claim}")
            lines.append(f"    Actual value: {disc.actual_value}")
            lines.append("")
    else:
        lines.append("✓ All claims verified successfully")

    return "\n".join(lines)


__all__ = [
    "CoachVerifier",
    "Discrepancy",
    "HonestyVerification",
    "TestResult",
    "format_verification_context",
]
