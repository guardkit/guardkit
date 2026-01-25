"""
Test Enforcement Resilience Module - Phase 4.5 resilience mechanisms.

Part of TASK-P45-f3a1: Add Phase 4.5 test enforcement resilience mechanisms.

This module provides defensive mechanisms for Phase 4.5 Test Enforcement Loop:
- Per-iteration timeout (60s default) to prevent runaway fix attempts
- Early exit with user guidance when errors are beyond auto-fix capability

Phases implemented:
- Phase 2: Per-Iteration Timeout (HIGH priority, Complexity 3/10)
- Phase 4: Early Exit with Guidance (HIGH priority, Complexity 4/10)

Phases deferred (per architectural review):
- Phase 1: Error Fingerprinting (implement if Phases 2&4 insufficient)
- Phase 3: Complexity Assessment (implement if Phases 2&4 insufficient)

Author: Claude (Anthropic)
Created: 2026-01-08
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
import time
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Max time per fix attempt (seconds)
MAX_ITERATION_SECONDS = 60

# Default max attempts before giving up
DEFAULT_MAX_ATTEMPTS = 3

# Recommendation codes for Phase45Result
class RecommendationCode:
    """Recommendation codes for Phase 4.5 results."""
    AUTO_FIX_SUCCEEDED = "AUTO_FIX_SUCCEEDED"
    ITERATION_TIMEOUT = "ITERATION_TIMEOUT"
    FIX_GENERATION_FAILED = "FIX_GENERATION_FAILED"
    MAX_ATTEMPTS_EXCEEDED = "MAX_ATTEMPTS_EXCEEDED"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FixResult:
    """
    Result of a single fix attempt.

    Attributes:
        success: Whether fix was applied successfully
        duration: Time taken in seconds
        changes_made: List of files modified
        error: Error message if fix failed
    """
    success: bool
    duration: float
    changes_made: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class Phase45Result:
    """
    Result of Phase 4.5 execution with resilience.

    Attributes:
        success: Whether all tests pass after fixes
        attempts: Number of fix attempts made
        recommendation: Recommendation code indicating exit reason
        guidance: User-friendly guidance message for next steps
        fix_results: List of FixResult objects from each attempt
    """
    success: bool
    attempts: int
    recommendation: str
    guidance: Optional[str] = None
    fix_results: List[FixResult] = field(default_factory=list)


# =============================================================================
# Phase 2: Per-Iteration Timeout
# =============================================================================

def attempt_fix_with_timeout(
    errors: str,
    iteration: int,
    fix_generator: Callable[[str], Dict[str, Any]],
    max_seconds: int = MAX_ITERATION_SECONDS
) -> Optional[FixResult]:
    """
    Attempt fix with per-iteration timeout.

    Applies a timeout to individual fix attempts to prevent runaway iterations
    that would waste the overall timeout budget.

    Args:
        errors: Test error output to analyze
        iteration: Current iteration number (1-indexed)
        fix_generator: Callable that generates and applies fix, returns dict with:
            - success: bool
            - files_modified: List[str]
            - error: Optional[str]
        max_seconds: Maximum seconds for this iteration (default: 60)

    Returns:
        FixResult if fix completed (success or failure), None if timeout exceeded

    Example:
        >>> def mock_fix(errors):
        ...     return {"success": True, "files_modified": ["config.py"]}
        >>> result = attempt_fix_with_timeout("Test failed", 1, mock_fix, 60)
        >>> result.success
        True
    """
    start_time = time.time()

    logger.info(f"Phase 4.5 Attempt {iteration}: Starting fix generation")

    try:
        # Generate and apply fix
        fix_result = fix_generator(errors)

        elapsed = time.time() - start_time

        # Check if we exceeded timeout
        if elapsed > max_seconds:
            logger.warning(
                f"Iteration {iteration} exceeded {max_seconds}s "
                f"({elapsed:.1f}s) - may be beyond auto-fix capability"
            )
            return None  # Signal timeout to caller

        files_modified = fix_result.get("files_modified", [])
        success = fix_result.get("success", False)
        error = fix_result.get("error")

        logger.info(
            f"Phase 4.5 Attempt {iteration}: Fix completed in {elapsed:.1f}s, "
            f"success={success}, files={len(files_modified)}"
        )

        return FixResult(
            success=success,
            duration=elapsed,
            changes_made=files_modified,
            error=error,
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Fix attempt {iteration} failed with exception: {e}")

        return FixResult(
            success=False,
            duration=elapsed,
            changes_made=[],
            error=str(e),
        )


# =============================================================================
# Phase 4: Early Exit with Guidance
# =============================================================================

def execute_phase_4_5_with_resilience(
    test_result: Dict[str, Any],
    fix_generator: Callable[[str], Dict[str, Any]],
    test_runner: Callable[[], Dict[str, Any]],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    max_iteration_seconds: int = MAX_ITERATION_SECONDS
) -> Phase45Result:
    """
    Execute Phase 4.5 with resilience mechanisms.

    Orchestrates the test enforcement loop with:
    - Per-iteration timeout (Phase 2)
    - Early exit with guidance (Phase 4)

    Args:
        test_result: Initial test result dict with:
            - passed: bool
            - output: str (error output)
            - test_count: int
            - failure_count: int
        fix_generator: Callable that generates and applies fix
        test_runner: Callable that runs tests and returns test_result dict
        max_attempts: Maximum fix attempts (default: 3)
        max_iteration_seconds: Timeout per attempt in seconds (default: 60)

    Returns:
        Phase45Result with success status, attempts count, recommendation,
        and user guidance

    Example:
        >>> def mock_fix(errors):
        ...     return {"success": True, "files_modified": ["test.py"]}
        >>> def mock_test():
        ...     return {"passed": True, "output": "", "test_count": 5}
        >>> result = execute_phase_4_5_with_resilience(
        ...     {"passed": False, "output": "Error"},
        ...     mock_fix, mock_test, max_attempts=3
        ... )
        >>> result.recommendation
        'AUTO_FIX_SUCCEEDED'
    """
    fix_results: List[FixResult] = []

    # If tests already pass, no work needed
    if test_result.get("passed", False):
        logger.info("Phase 4.5: Tests already passing, no fix needed")
        return Phase45Result(
            success=True,
            attempts=0,
            recommendation=RecommendationCode.AUTO_FIX_SUCCEEDED,
            guidance="All tests passing - no fix needed.",
            fix_results=[],
        )

    current_test_result = test_result

    for attempt in range(1, max_attempts + 1):
        logger.info(f"Phase 4.5 Attempt {attempt}/{max_attempts}")

        # Attempt fix with per-iteration timeout
        fix_result = attempt_fix_with_timeout(
            errors=current_test_result.get("output", ""),
            iteration=attempt,
            fix_generator=fix_generator,
            max_seconds=max_iteration_seconds,
        )

        # Handle timeout (None return)
        if fix_result is None:
            return Phase45Result(
                success=False,
                attempts=attempt,
                recommendation=RecommendationCode.ITERATION_TIMEOUT,
                guidance=(
                    f"Fix attempt {attempt} exceeded {max_iteration_seconds}s timeout.\n"
                    f"This suggests the error may be too complex for auto-fix.\n\n"
                    f"Recommended actions:\n"
                    f"1. Review the error output manually\n"
                    f"2. Check for library migration issues (e.g., Pydantic v2)\n"
                    f"3. Consider increasing --sdk-timeout if this is a legitimate slow operation"
                ),
                fix_results=fix_results,
            )

        fix_results.append(fix_result)

        # Handle fix generation failure
        if not fix_result.success:
            return Phase45Result(
                success=False,
                attempts=attempt,
                recommendation=RecommendationCode.FIX_GENERATION_FAILED,
                guidance=(
                    f"Fix generation failed on attempt {attempt}.\n"
                    f"Error: {fix_result.error}\n\n"
                    f"This may indicate:\n"
                    f"1. An unrecognized error pattern\n"
                    f"2. A complex multi-file issue\n"
                    f"3. Missing dependencies or configuration"
                ),
                fix_results=fix_results,
            )

        # Re-run tests
        logger.info(f"Phase 4.5 Attempt {attempt}: Re-running tests")
        current_test_result = test_runner()

        # Check if tests pass
        if current_test_result.get("passed", False):
            logger.info(f"Phase 4.5: Tests passing after {attempt} attempt(s)")
            return Phase45Result(
                success=True,
                attempts=attempt,
                recommendation=RecommendationCode.AUTO_FIX_SUCCEEDED,
                guidance=f"All tests passing after {attempt} fix attempt(s).",
                fix_results=fix_results,
            )

        logger.info(
            f"Phase 4.5 Attempt {attempt}: Tests still failing "
            f"({current_test_result.get('failure_count', '?')} failures)"
        )

    # Exhausted all attempts
    return Phase45Result(
        success=False,
        attempts=max_attempts,
        recommendation=RecommendationCode.MAX_ATTEMPTS_EXCEEDED,
        guidance=(
            f"All {max_attempts} auto-fix attempts exhausted.\n"
            f"Tests still failing after {max_attempts} iterations.\n\n"
            f"Recommended actions:\n"
            f"1. Review the test output and fix manually\n"
            f"2. Check if the error requires architectural changes\n"
            f"3. Consider splitting the task into smaller pieces"
        ),
        fix_results=fix_results,
    )


# =============================================================================
# Utility Functions
# =============================================================================

def format_phase_45_guidance(result: Phase45Result) -> str:
    """
    Format Phase 4.5 result guidance for display.

    Args:
        result: Phase45Result to format

    Returns:
        Formatted string for terminal display
    """
    lines = [
        "=" * 60,
        f"Phase 4.5 Result: {result.recommendation}",
        "=" * 60,
        f"Success: {'Yes' if result.success else 'No'}",
        f"Attempts: {result.attempts}",
    ]

    if result.fix_results:
        lines.append("")
        lines.append("Fix Attempt Summary:")
        for i, fix in enumerate(result.fix_results, 1):
            status = "✓" if fix.success else "✗"
            lines.append(f"  {i}. {status} {fix.duration:.1f}s - {len(fix.changes_made)} file(s)")

    if result.guidance:
        lines.append("")
        lines.append("Guidance:")
        for line in result.guidance.split("\n"):
            lines.append(f"  {line}")

    lines.append("=" * 60)

    return "\n".join(lines)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Constants
    "MAX_ITERATION_SECONDS",
    "DEFAULT_MAX_ATTEMPTS",
    "RecommendationCode",
    # Data classes
    "FixResult",
    "Phase45Result",
    # Core functions
    "attempt_fix_with_timeout",
    "execute_phase_4_5_with_resilience",
    # Utilities
    "format_phase_45_guidance",
]
