"""
Tests for test_enforcement_resilience module.

Part of TASK-P45-f3a1: Add Phase 4.5 test enforcement resilience mechanisms.

Tests cover:
- FixResult dataclass
- Phase45Result dataclass
- attempt_fix_with_timeout() function (Phase 2)
- execute_phase_4_5_with_resilience() function (Phase 4)
- format_phase_45_guidance() utility

Author: Claude (Anthropic)
Created: 2026-01-08
"""

import pytest
import time
from unittest.mock import Mock, patch

from installer.core.commands.lib.test_enforcement_resilience import (
    FixResult,
    Phase45Result,
    RecommendationCode,
    MAX_ITERATION_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    attempt_fix_with_timeout,
    execute_phase_4_5_with_resilience,
    format_phase_45_guidance,
)


# =============================================================================
# FixResult Tests
# =============================================================================

class TestFixResult:
    """Tests for FixResult dataclass."""

    def test_fix_result_success(self):
        """Test successful fix result."""
        result = FixResult(
            success=True,
            duration=5.5,
            changes_made=["config.py", "test_config.py"],
        )
        assert result.success is True
        assert result.duration == 5.5
        assert len(result.changes_made) == 2
        assert result.error is None

    def test_fix_result_failure(self):
        """Test failed fix result."""
        result = FixResult(
            success=False,
            duration=2.0,
            changes_made=[],
            error="Fix generation failed: unknown pattern",
        )
        assert result.success is False
        assert result.duration == 2.0
        assert result.changes_made == []
        assert "unknown pattern" in result.error

    def test_fix_result_defaults(self):
        """Test FixResult default values."""
        result = FixResult(success=True, duration=1.0)
        assert result.changes_made == []
        assert result.error is None


# =============================================================================
# Phase45Result Tests
# =============================================================================

class TestPhase45Result:
    """Tests for Phase45Result dataclass."""

    def test_phase45_result_success(self):
        """Test successful Phase 4.5 result."""
        result = Phase45Result(
            success=True,
            attempts=2,
            recommendation=RecommendationCode.AUTO_FIX_SUCCEEDED,
            guidance="All tests passing after 2 fix attempts.",
        )
        assert result.success is True
        assert result.attempts == 2
        assert result.recommendation == "AUTO_FIX_SUCCEEDED"
        assert "2 fix attempts" in result.guidance

    def test_phase45_result_timeout(self):
        """Test timeout Phase 4.5 result."""
        result = Phase45Result(
            success=False,
            attempts=1,
            recommendation=RecommendationCode.ITERATION_TIMEOUT,
            guidance="Fix exceeded timeout",
        )
        assert result.success is False
        assert result.recommendation == "ITERATION_TIMEOUT"

    def test_phase45_result_max_attempts(self):
        """Test max attempts exceeded result."""
        result = Phase45Result(
            success=False,
            attempts=3,
            recommendation=RecommendationCode.MAX_ATTEMPTS_EXCEEDED,
        )
        assert result.recommendation == "MAX_ATTEMPTS_EXCEEDED"
        assert result.attempts == 3

    def test_phase45_result_with_fix_results(self):
        """Test Phase45Result with fix results list."""
        fix1 = FixResult(success=True, duration=5.0, changes_made=["a.py"])
        fix2 = FixResult(success=True, duration=3.0, changes_made=["b.py"])

        result = Phase45Result(
            success=True,
            attempts=2,
            recommendation=RecommendationCode.AUTO_FIX_SUCCEEDED,
            fix_results=[fix1, fix2],
        )
        assert len(result.fix_results) == 2
        assert result.fix_results[0].duration == 5.0

    def test_phase45_result_defaults(self):
        """Test Phase45Result default values."""
        result = Phase45Result(
            success=False,
            attempts=1,
            recommendation=RecommendationCode.FIX_GENERATION_FAILED,
        )
        assert result.guidance is None
        assert result.fix_results == []


# =============================================================================
# RecommendationCode Tests
# =============================================================================

class TestRecommendationCode:
    """Tests for RecommendationCode constants."""

    def test_all_codes_defined(self):
        """Verify all recommendation codes are defined."""
        assert RecommendationCode.AUTO_FIX_SUCCEEDED == "AUTO_FIX_SUCCEEDED"
        assert RecommendationCode.ITERATION_TIMEOUT == "ITERATION_TIMEOUT"
        assert RecommendationCode.FIX_GENERATION_FAILED == "FIX_GENERATION_FAILED"
        assert RecommendationCode.MAX_ATTEMPTS_EXCEEDED == "MAX_ATTEMPTS_EXCEEDED"


# =============================================================================
# Constants Tests
# =============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_max_iteration_seconds(self):
        """Test MAX_ITERATION_SECONDS is reasonable."""
        assert MAX_ITERATION_SECONDS == 60
        assert isinstance(MAX_ITERATION_SECONDS, int)

    def test_default_max_attempts(self):
        """Test DEFAULT_MAX_ATTEMPTS is reasonable."""
        assert DEFAULT_MAX_ATTEMPTS == 3
        assert isinstance(DEFAULT_MAX_ATTEMPTS, int)


# =============================================================================
# attempt_fix_with_timeout Tests (Phase 2)
# =============================================================================

class TestAttemptFixWithTimeout:
    """Tests for attempt_fix_with_timeout function."""

    def test_successful_fix_within_timeout(self):
        """Test fix that completes within timeout."""
        def mock_fix(errors):
            return {"success": True, "files_modified": ["config.py"]}

        result = attempt_fix_with_timeout(
            errors="Test failed: NameError",
            iteration=1,
            fix_generator=mock_fix,
            max_seconds=60,
        )

        assert result is not None
        assert result.success is True
        assert result.duration < 60
        assert "config.py" in result.changes_made
        assert result.error is None

    def test_fix_exceeds_timeout_returns_none(self):
        """Test fix that exceeds timeout returns None."""
        def slow_fix(errors):
            time.sleep(0.2)  # Simulate slow operation
            return {"success": True, "files_modified": ["config.py"]}

        result = attempt_fix_with_timeout(
            errors="Test failed",
            iteration=1,
            fix_generator=slow_fix,
            max_seconds=0.1,  # Very short timeout for test
        )

        assert result is None  # Timeout exceeded

    def test_fix_generator_failure(self):
        """Test fix generator that returns failure."""
        def failing_fix(errors):
            return {
                "success": False,
                "files_modified": [],
                "error": "Cannot parse error pattern",
            }

        result = attempt_fix_with_timeout(
            errors="Unknown error",
            iteration=1,
            fix_generator=failing_fix,
            max_seconds=60,
        )

        assert result is not None
        assert result.success is False
        assert result.error == "Cannot parse error pattern"
        assert result.changes_made == []

    def test_fix_generator_exception(self):
        """Test fix generator that raises exception."""
        def exception_fix(errors):
            raise ValueError("Unexpected error during fix")

        result = attempt_fix_with_timeout(
            errors="Test failed",
            iteration=1,
            fix_generator=exception_fix,
            max_seconds=60,
        )

        assert result is not None
        assert result.success is False
        assert "Unexpected error during fix" in result.error
        assert result.changes_made == []

    def test_fix_records_duration(self):
        """Test that fix duration is recorded accurately."""
        def timed_fix(errors):
            time.sleep(0.05)  # Small delay
            return {"success": True, "files_modified": ["a.py"]}

        result = attempt_fix_with_timeout(
            errors="Error",
            iteration=1,
            fix_generator=timed_fix,
            max_seconds=60,
        )

        assert result is not None
        assert result.duration >= 0.05
        assert result.duration < 1.0  # Sanity check

    def test_fix_handles_missing_files_modified(self):
        """Test fix handles missing files_modified key."""
        def minimal_fix(errors):
            return {"success": True}  # No files_modified

        result = attempt_fix_with_timeout(
            errors="Error",
            iteration=1,
            fix_generator=minimal_fix,
            max_seconds=60,
        )

        assert result is not None
        assert result.success is True
        assert result.changes_made == []

    def test_iteration_number_logged(self):
        """Test that iteration number is used in logging."""
        calls = []

        def tracking_fix(errors):
            calls.append(True)
            return {"success": True, "files_modified": []}

        result = attempt_fix_with_timeout(
            errors="Error",
            iteration=5,
            fix_generator=tracking_fix,
            max_seconds=60,
        )

        assert result is not None
        assert len(calls) == 1


# =============================================================================
# execute_phase_4_5_with_resilience Tests (Phase 4)
# =============================================================================

class TestExecutePhase45WithResilience:
    """Tests for execute_phase_4_5_with_resilience function."""

    def test_tests_already_passing(self):
        """Test early exit when tests already pass."""
        test_result = {"passed": True, "output": "", "test_count": 10}
        mock_fix = Mock()
        mock_test = Mock()

        result = execute_phase_4_5_with_resilience(
            test_result=test_result,
            fix_generator=mock_fix,
            test_runner=mock_test,
        )

        assert result.success is True
        assert result.attempts == 0
        assert result.recommendation == RecommendationCode.AUTO_FIX_SUCCEEDED
        mock_fix.assert_not_called()
        mock_test.assert_not_called()

    def test_fix_succeeds_first_attempt(self):
        """Test successful fix on first attempt."""
        test_result = {"passed": False, "output": "Error", "failure_count": 2}

        def mock_fix(errors):
            return {"success": True, "files_modified": ["config.py"]}

        test_call_count = [0]

        def mock_test():
            test_call_count[0] += 1
            return {"passed": True, "output": "", "test_count": 10}

        result = execute_phase_4_5_with_resilience(
            test_result=test_result,
            fix_generator=mock_fix,
            test_runner=mock_test,
        )

        assert result.success is True
        assert result.attempts == 1
        assert result.recommendation == RecommendationCode.AUTO_FIX_SUCCEEDED
        assert len(result.fix_results) == 1
        assert test_call_count[0] == 1

    def test_fix_succeeds_second_attempt(self):
        """Test successful fix on second attempt."""
        test_result = {"passed": False, "output": "Error", "failure_count": 2}

        fix_call_count = [0]

        def mock_fix(errors):
            fix_call_count[0] += 1
            return {"success": True, "files_modified": [f"fix_{fix_call_count[0]}.py"]}

        test_call_count = [0]

        def mock_test():
            test_call_count[0] += 1
            # First test run fails, second passes
            if test_call_count[0] == 1:
                return {"passed": False, "output": "Still error", "failure_count": 1}
            return {"passed": True, "output": "", "test_count": 10}

        result = execute_phase_4_5_with_resilience(
            test_result=test_result,
            fix_generator=mock_fix,
            test_runner=mock_test,
        )

        assert result.success is True
        assert result.attempts == 2
        assert result.recommendation == RecommendationCode.AUTO_FIX_SUCCEEDED
        assert len(result.fix_results) == 2

    def test_max_attempts_exceeded(self):
        """Test max attempts exhausted without success."""
        test_result = {"passed": False, "output": "Error", "failure_count": 5}

        def mock_fix(errors):
            return {"success": True, "files_modified": ["partial.py"]}

        def mock_test():
            return {"passed": False, "output": "Still failing", "failure_count": 3}

        result = execute_phase_4_5_with_resilience(
            test_result=test_result,
            fix_generator=mock_fix,
            test_runner=mock_test,
            max_attempts=3,
        )

        assert result.success is False
        assert result.attempts == 3
        assert result.recommendation == RecommendationCode.MAX_ATTEMPTS_EXCEEDED
        assert len(result.fix_results) == 3
        assert "exhausted" in result.guidance.lower()

    def test_iteration_timeout(self):
        """Test early exit on iteration timeout."""
        test_result = {"passed": False, "output": "Complex error", "failure_count": 8}

        def slow_fix(errors):
            time.sleep(0.2)  # Simulate slow operation
            return {"success": True, "files_modified": ["slow.py"]}

        mock_test = Mock()

        result = execute_phase_4_5_with_resilience(
            test_result=test_result,
            fix_generator=slow_fix,
            test_runner=mock_test,
            max_attempts=3,
            max_iteration_seconds=0.1,  # Very short for test
        )

        assert result.success is False
        assert result.attempts == 1
        assert result.recommendation == RecommendationCode.ITERATION_TIMEOUT
        assert "timeout" in result.guidance.lower()
        mock_test.assert_not_called()

    def test_fix_generation_failed(self):
        """Test early exit when fix generation fails."""
        test_result = {"passed": False, "output": "Unknown error type", "failure_count": 1}

        def failing_fix(errors):
            return {
                "success": False,
                "files_modified": [],
                "error": "Unrecognized error pattern",
            }

        mock_test = Mock()

        result = execute_phase_4_5_with_resilience(
            test_result=test_result,
            fix_generator=failing_fix,
            test_runner=mock_test,
        )

        assert result.success is False
        assert result.attempts == 1
        assert result.recommendation == RecommendationCode.FIX_GENERATION_FAILED
        assert "Unrecognized error pattern" in result.guidance
        mock_test.assert_not_called()

    def test_custom_max_attempts(self):
        """Test custom max_attempts parameter."""
        test_result = {"passed": False, "output": "Error"}

        def mock_fix(errors):
            return {"success": True, "files_modified": []}

        def mock_test():
            return {"passed": False, "output": "Still failing"}

        result = execute_phase_4_5_with_resilience(
            test_result=test_result,
            fix_generator=mock_fix,
            test_runner=mock_test,
            max_attempts=5,  # Custom value
        )

        assert result.attempts == 5
        assert len(result.fix_results) == 5

    def test_custom_iteration_timeout(self):
        """Test custom max_iteration_seconds parameter."""
        test_result = {"passed": False, "output": "Error"}

        def timed_fix(errors):
            time.sleep(0.05)
            return {"success": True, "files_modified": []}

        def mock_test():
            return {"passed": True, "output": ""}

        # With reasonable timeout, should succeed
        result = execute_phase_4_5_with_resilience(
            test_result=test_result,
            fix_generator=timed_fix,
            test_runner=mock_test,
            max_iteration_seconds=10,
        )

        assert result.success is True

    def test_guidance_contains_useful_info(self):
        """Test that guidance messages contain useful information."""
        test_result = {"passed": False, "output": "Error"}

        def mock_fix(errors):
            return {"success": True, "files_modified": []}

        def mock_test():
            return {"passed": False, "output": "Still failing"}

        result = execute_phase_4_5_with_resilience(
            test_result=test_result,
            fix_generator=mock_fix,
            test_runner=mock_test,
            max_attempts=2,
        )

        assert result.guidance is not None
        # Should contain actionable recommendations
        assert "Recommended" in result.guidance or "Review" in result.guidance


# =============================================================================
# format_phase_45_guidance Tests
# =============================================================================

class TestFormatPhase45Guidance:
    """Tests for format_phase_45_guidance function."""

    def test_format_success_result(self):
        """Test formatting successful result."""
        result = Phase45Result(
            success=True,
            attempts=1,
            recommendation=RecommendationCode.AUTO_FIX_SUCCEEDED,
            guidance="All tests passing.",
        )

        output = format_phase_45_guidance(result)

        assert "AUTO_FIX_SUCCEEDED" in output
        assert "Success: Yes" in output
        assert "Attempts: 1" in output

    def test_format_failure_result(self):
        """Test formatting failed result."""
        result = Phase45Result(
            success=False,
            attempts=3,
            recommendation=RecommendationCode.MAX_ATTEMPTS_EXCEEDED,
            guidance="All attempts exhausted.",
        )

        output = format_phase_45_guidance(result)

        assert "MAX_ATTEMPTS_EXCEEDED" in output
        assert "Success: No" in output
        assert "Attempts: 3" in output
        assert "exhausted" in output

    def test_format_with_fix_results(self):
        """Test formatting with fix results list."""
        fix1 = FixResult(success=True, duration=5.5, changes_made=["a.py", "b.py"])
        fix2 = FixResult(success=False, duration=2.0, changes_made=[], error="Failed")

        result = Phase45Result(
            success=False,
            attempts=2,
            recommendation=RecommendationCode.FIX_GENERATION_FAILED,
            fix_results=[fix1, fix2],
        )

        output = format_phase_45_guidance(result)

        assert "Fix Attempt Summary:" in output
        assert "5.5s" in output
        assert "2 file(s)" in output

    def test_format_multiline_guidance(self):
        """Test formatting multiline guidance."""
        result = Phase45Result(
            success=False,
            attempts=1,
            recommendation=RecommendationCode.ITERATION_TIMEOUT,
            guidance="Line 1\nLine 2\nLine 3",
        )

        output = format_phase_45_guidance(result)

        assert "Line 1" in output
        assert "Line 2" in output
        assert "Line 3" in output

    def test_format_no_guidance(self):
        """Test formatting with no guidance."""
        result = Phase45Result(
            success=True,
            attempts=0,
            recommendation=RecommendationCode.AUTO_FIX_SUCCEEDED,
            guidance=None,
        )

        output = format_phase_45_guidance(result)

        # Should still format without error
        assert "AUTO_FIX_SUCCEEDED" in output
        # Should not have Guidance section
        assert output.count("Guidance:") == 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the resilience module."""

    def test_full_workflow_single_fix(self):
        """Test complete workflow with single successful fix."""
        initial_test = {"passed": False, "output": "NameError: name 'foo'", "failure_count": 1}

        def fix_gen(errors):
            return {"success": True, "files_modified": ["module.py"]}

        def test_run():
            return {"passed": True, "output": "", "test_count": 5}

        result = execute_phase_4_5_with_resilience(
            test_result=initial_test,
            fix_generator=fix_gen,
            test_runner=test_run,
        )

        assert result.success is True
        assert result.attempts == 1

        # Format and verify output
        output = format_phase_45_guidance(result)
        assert "Success: Yes" in output

    def test_full_workflow_multiple_fixes(self):
        """Test complete workflow requiring multiple fixes."""
        initial_test = {"passed": False, "output": "Multiple errors", "failure_count": 5}

        fix_count = [0]

        def fix_gen(errors):
            fix_count[0] += 1
            return {"success": True, "files_modified": [f"fix{fix_count[0]}.py"]}

        test_count = [0]

        def test_run():
            test_count[0] += 1
            if test_count[0] < 3:
                return {"passed": False, "output": f"Error {3 - test_count[0]} remaining", "failure_count": 3 - test_count[0]}
            return {"passed": True, "output": "", "test_count": 10}

        result = execute_phase_4_5_with_resilience(
            test_result=initial_test,
            fix_generator=fix_gen,
            test_runner=test_run,
        )

        assert result.success is True
        assert result.attempts == 3
        assert len(result.fix_results) == 3

    def test_full_workflow_unfixable_error(self):
        """Test complete workflow with unfixable error."""
        initial_test = {"passed": False, "output": "Pydantic v2 migration error", "failure_count": 8}

        def fix_gen(errors):
            # Fix attempts succeed but don't solve the problem
            return {"success": True, "files_modified": ["attempted_fix.py"]}

        def test_run():
            # Same error persists
            return {"passed": False, "output": "Pydantic v2 migration error", "failure_count": 8}

        result = execute_phase_4_5_with_resilience(
            test_result=initial_test,
            fix_generator=fix_gen,
            test_runner=test_run,
            max_attempts=3,
        )

        assert result.success is False
        assert result.attempts == 3
        assert result.recommendation == RecommendationCode.MAX_ATTEMPTS_EXCEEDED

        # Format and verify guidance
        output = format_phase_45_guidance(result)
        assert "exhausted" in output.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
