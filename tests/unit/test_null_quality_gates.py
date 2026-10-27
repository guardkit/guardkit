"""
Unit tests for TASK-FIX-64EE: null test-signal handling for checkpoints.

Tests cover:
1. _extract_tests_passed() tri-state handling of null/absent test signals
   (UPDATED by TASK-FIX-CKPTTESTRED01: an absent verdict is UNKNOWN/None, not
   False — see .claude/rules/absence-of-failure-is-not-success.md)
2. No regression of TASK-FIX-CKPT fixes (quality_gates path, top-level fallback)

Coverage Target: >=85%
"""

from pathlib import Path
from unittest.mock import Mock

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator


# ============================================================================
# Fix 2: _extract_tests_passed() null coercion
# ============================================================================


class TestExtractTestsPassedNullCoercion:
    """Test _extract_tests_passed() tri-state handling of null/absent values.

    TASK-FIX-CKPTTESTRED01 supersedes TASK-FIX-64EE's ``None → False``
    coercion for the *absent-signal* case: an absent test verdict is now
    UNKNOWN (``None``), not a failure. A genuine ``False`` (oracle ran and
    failed) is unchanged.
    """

    def test_null_tests_passed_returns_none_unknown(self):
        """When quality_gates.tests_passed is None, returns None (UNKNOWN).

        Superseded behaviour: TASK-FIX-64EE coerced this to ``False`` so the
        checkpoint recorded ``tests: fail``. TASK-FIX-CKPTTESTRED01 treats an
        explicit ``None`` gate value as absent evidence (UNKNOWN), which the
        pollution detector excludes from the consecutive-failure tally. See
        ``.claude/rules/absence-of-failure-is-not-success.md``.
        """
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "quality_gates": {
                    "tests_passed": None,
                    "tests_run": True,
                },
            },
        }

        result = orchestrator._extract_tests_passed(turn_record)
        assert result is None

    def test_true_tests_passed_returns_true(self):
        """Regression: True values still work."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "quality_gates": {
                    "tests_passed": True,
                },
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is True

    def test_false_tests_passed_returns_false(self):
        """Regression: False values still work."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "quality_gates": {
                    "tests_passed": False,
                },
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is False

    def test_absent_independent_test_signal_returns_none_unknown(self):
        """The project's own run produced no verdict (``signal_absent``):
        UNKNOWN, never a failure (moved from the deleted
        test_zero_test_verifier_infrastructure.py, TASK-AB-ZEROTESTLOUD01 AC-005)."""
        orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "independent_tests": {
                    "tests_passed": False,
                    "signal_absent": True,
                },
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is None

    def test_ran_and_failed_independent_tests_return_false(self):
        """Negative control: the project's own run ran and failed."""
        orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "independent_tests": {
                    "tests_passed": False,
                    "signal_absent": False,
                },
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is False


# ============================================================================
# Regression: TASK-FIX-CKPT fixes preserved
# ============================================================================


class TestTaskFixCkptRegression:
    """Ensure TASK-FIX-CKPT fixes are not regressed."""

    def test_extract_tests_passed_reads_quality_gates_path(self):
        """TASK-FIX-CKPT: Primary path reads quality_gates.tests_passed."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "quality_gates": {
                    "tests_passed": True,
                    "tests_run": True,
                },
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is True

    def test_extract_tests_passed_falls_back_to_top_level(self):
        """TASK-FIX-CKPT: Fallback to top-level tests_passed."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        turn_record = Mock()
        turn_record.coach_result = Mock()
        turn_record.coach_result.success = True
        turn_record.coach_result.report = {
            "validation_results": {
                "tests_run": True,
                "tests_passed": True,
            },
        }

        assert orchestrator._extract_tests_passed(turn_record) is True
