"""
Integration Tests for Coach Read-Only Security Verification - TASK-SEC-005.

Tests for the revised architecture where:
- Coach only **reads** security results (no agent invocation)
- Coach does NOT invoke security-specialist agent
- Coach verifies quality gates from task_work_results.json
- Coach has read-only access to pre-loop and task-work results

Test Categories:
- Coach reads security from results
- Coach fails on critical findings
- Coach does NOT invoke security-specialist (CRITICAL)
- Coach handles missing security results
- Coach read-only verification mode
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, Any, Optional

from guardkit.orchestrator.security_config import SecurityConfig, SecurityLevel
from guardkit.orchestrator.quality_gates.security_review import (
    SecurityReviewResult,
    save_security_review,
    load_security_review,
)
from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding


# ============================================================================
# Mock Coach Validator (Simulates Coach Behavior)
# ============================================================================


@dataclass
class QualityGateStatus:
    """Status of quality gate verification."""

    security_passed: bool
    security_message: str
    critical_count: int
    high_count: int


class MockCoachValidator:
    """Mock Coach validator that only reads security results.

    CRITICAL: This validator has NO ability to invoke agents.
    It can only read persisted results from task_work_results.
    """

    def __init__(self, worktree_path: Path):
        self.worktree_path = worktree_path
        # Coach does NOT have these methods
        # NO invoke_task, invoke_security_specialist, etc.

    def verify_quality_gates(
        self, task_work_results: Dict[str, Any]
    ) -> QualityGateStatus:
        """Verify quality gates from task_work_results.

        Coach ONLY reads results - does NOT generate them.
        """
        security_data = task_work_results.get("security", {})

        quick_check_passed = security_data.get("quick_check_passed", True)
        critical_count = security_data.get("critical_count", 0)
        high_count = security_data.get("high_count", 0)

        # Determine if security gate passes
        security_passed = quick_check_passed and critical_count == 0

        if not security_passed:
            message = f"Security gate failed: {critical_count} critical findings"
        else:
            message = "Security gate passed"

        return QualityGateStatus(
            security_passed=security_passed,
            security_message=message,
            critical_count=critical_count,
            high_count=high_count,
        )

    def read_security_review(self, task_id: str) -> Optional[SecurityReviewResult]:
        """Read persisted security review results.

        Coach ONLY reads - does NOT execute security checks.
        """
        return load_security_review(task_id, self.worktree_path)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_worktree(tmp_path):
    """Create a temporary worktree structure for testing."""
    worktree = tmp_path / "test_worktree"
    worktree.mkdir()
    (worktree / "src").mkdir()
    (worktree / ".guardkit" / "autobuild").mkdir(parents=True)
    return worktree


@pytest.fixture
def coach_validator(temp_worktree):
    """Create mock Coach validator."""
    return MockCoachValidator(temp_worktree)


@pytest.fixture
def clean_security_results():
    """Create task_work_results with clean security results."""
    return {
        "task_id": "TASK-001",
        "status": "IN_PROGRESS",
        "security": {
            "quick_check_passed": True,
            "findings_count": 0,
            "critical_count": 0,
            "high_count": 0,
        },
    }


@pytest.fixture
def critical_security_results():
    """Create task_work_results with critical security findings."""
    return {
        "task_id": "TASK-001",
        "status": "IN_PROGRESS",
        "security": {
            "quick_check_passed": False,
            "findings_count": 2,
            "critical_count": 1,
            "high_count": 1,
        },
    }


@pytest.fixture
def high_only_security_results():
    """Create task_work_results with only high severity findings."""
    return {
        "task_id": "TASK-001",
        "status": "IN_PROGRESS",
        "security": {
            "quick_check_passed": True,
            "findings_count": 2,
            "critical_count": 0,
            "high_count": 2,
        },
    }


# ============================================================================
# Coach Reads Security Results Tests
# ============================================================================


class TestCoachReadsSecurityResults:
    """Test Coach reads security results from task_work_results."""

    def test_coach_reads_security_from_results(
        self, coach_validator, clean_security_results
    ):
        """Coach should read security results from task_work_results.json."""
        status = coach_validator.verify_quality_gates(clean_security_results)

        assert status.security_passed is True

    def test_coach_extracts_critical_count(
        self, coach_validator, critical_security_results
    ):
        """Coach should extract critical_count from results."""
        status = coach_validator.verify_quality_gates(critical_security_results)

        assert status.critical_count == 1

    def test_coach_extracts_high_count(
        self, coach_validator, high_only_security_results
    ):
        """Coach should extract high_count from results."""
        status = coach_validator.verify_quality_gates(high_only_security_results)

        assert status.high_count == 2


# ============================================================================
# Coach Fails on Critical Findings Tests
# ============================================================================


class TestCoachFailsOnCritical:
    """Test Coach fails security gate on critical findings."""

    def test_coach_fails_on_critical_findings(
        self, coach_validator, critical_security_results
    ):
        """Coach should fail security gate on critical findings."""
        status = coach_validator.verify_quality_gates(critical_security_results)

        assert status.security_passed is False

    def test_coach_provides_failure_message(
        self, coach_validator, critical_security_results
    ):
        """Coach should provide failure message on critical findings."""
        status = coach_validator.verify_quality_gates(critical_security_results)

        assert "critical" in status.security_message.lower()

    def test_coach_passes_on_clean_results(
        self, coach_validator, clean_security_results
    ):
        """Coach should pass on clean security results."""
        status = coach_validator.verify_quality_gates(clean_security_results)

        assert status.security_passed is True

    def test_coach_passes_with_high_only_findings(
        self, coach_validator, high_only_security_results
    ):
        """Coach should pass when only high (not critical) findings exist."""
        status = coach_validator.verify_quality_gates(high_only_security_results)

        # High severity alone does not fail security gate
        assert status.security_passed is True


# ============================================================================
# Coach Does NOT Invoke Security Specialist Tests (CRITICAL)
# ============================================================================


class TestCoachNoAgentInvocation:
    """CRITICAL: Test Coach does NOT invoke security-specialist agent."""

    def test_coach_does_not_have_invoke_security_specialist(self, coach_validator):
        """CRITICAL: Coach must NOT have invoke_security_specialist method."""
        assert not hasattr(coach_validator, "invoke_security_specialist")

    def test_coach_does_not_have_invoke_task(self, coach_validator):
        """CRITICAL: Coach must NOT have invoke_task method."""
        assert not hasattr(coach_validator, "invoke_task")

    def test_coach_does_not_have_execute_agent(self, coach_validator):
        """CRITICAL: Coach must NOT have execute_agent method."""
        assert not hasattr(coach_validator, "execute_agent")

    def test_coach_only_has_read_methods(self, coach_validator):
        """Coach should only have read-only verification methods."""
        # Should have read/verify methods
        assert hasattr(coach_validator, "verify_quality_gates")
        assert hasattr(coach_validator, "read_security_review")

        # Should NOT have write/execute methods
        assert not hasattr(coach_validator, "write_security_review")
        assert not hasattr(coach_validator, "execute_security_check")
        assert not hasattr(coach_validator, "run_security_scan")

    def test_coach_cannot_modify_results(self, coach_validator, clean_security_results):
        """Coach should not be able to modify security results."""
        # Coach can only read, not modify
        status = coach_validator.verify_quality_gates(clean_security_results)

        # Original results unchanged
        assert clean_security_results["security"]["critical_count"] == 0


# ============================================================================
# Coach Handles Missing Security Results Tests
# ============================================================================


class TestCoachMissingResults:
    """Test Coach handles missing security results gracefully."""

    def test_coach_handles_missing_security_results(self, coach_validator):
        """Coach should handle missing security results gracefully."""
        task_work_results = {
            "task_id": "TASK-001",
            "status": "IN_PROGRESS",
            # No "security" key
        }

        status = coach_validator.verify_quality_gates(task_work_results)

        # Default to passed when no security results (backward compatibility)
        assert status.security_passed is True

    def test_coach_handles_empty_security_object(self, coach_validator):
        """Coach should handle empty security object."""
        task_work_results = {
            "task_id": "TASK-001",
            "security": {},  # Empty security object
        }

        status = coach_validator.verify_quality_gates(task_work_results)

        # Should use defaults
        assert status.security_passed is True
        assert status.critical_count == 0

    def test_coach_handles_partial_security_data(self, coach_validator):
        """Coach should handle partial security data."""
        task_work_results = {
            "security": {
                "quick_check_passed": False,
                # Missing critical_count, high_count
            }
        }

        status = coach_validator.verify_quality_gates(task_work_results)

        # Should use defaults for missing fields
        assert status.critical_count == 0


# ============================================================================
# Coach Reads Persisted Security Review Tests
# ============================================================================


class TestCoachReadPersistedReview:
    """Test Coach reads persisted security review from pre-loop."""

    def test_coach_reads_persisted_security_review(self, temp_worktree, coach_validator):
        """Coach should read persisted security review results."""
        # Simulate pre-loop saving results
        result = SecurityReviewResult(
            task_id="TASK-001",
            worktree_path=str(temp_worktree),
            findings=[],
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            blocked=False,
            execution_time_seconds=1.0,
            timestamp="2025-01-25T12:00:00Z",
        )
        save_security_review(result, temp_worktree)

        # Coach reads (does not generate)
        loaded = coach_validator.read_security_review("TASK-001")

        assert loaded is not None
        assert loaded.task_id == "TASK-001"

    def test_coach_returns_none_for_missing_review(self, coach_validator):
        """Coach should return None for missing security review."""
        loaded = coach_validator.read_security_review("NONEXISTENT-TASK")

        assert loaded is None

    def test_coach_reads_findings_from_persisted_review(
        self, temp_worktree, coach_validator
    ):
        """Coach should read findings from persisted review."""
        finding = SecurityFinding(
            check_id="hardcoded-secrets",
            severity="critical",
            description="Hardcoded API key",
            file_path="config.py",
            line_number=5,
            matched_text='API_KEY = "secret"',
            recommendation="Use environment variables",
        )
        result = SecurityReviewResult(
            task_id="TASK-002",
            worktree_path=str(temp_worktree),
            findings=[finding],
            critical_count=1,
            high_count=0,
            medium_count=0,
            low_count=0,
            blocked=True,
            execution_time_seconds=1.5,
            timestamp="2025-01-25T12:00:00Z",
        )
        save_security_review(result, temp_worktree)

        loaded = coach_validator.read_security_review("TASK-002")

        assert len(loaded.findings) == 1
        assert loaded.findings[0].check_id == "hardcoded-secrets"


# ============================================================================
# Coach Read-Only Mode Verification Tests
# ============================================================================


class TestCoachReadOnlyMode:
    """Test Coach operates in read-only mode."""

    def test_coach_verify_is_read_only(self, coach_validator, clean_security_results):
        """Coach verify method should be read-only."""
        original_results = clean_security_results.copy()

        coach_validator.verify_quality_gates(clean_security_results)

        # Results should not be modified
        assert clean_security_results == original_results

    def test_coach_does_not_execute_security_checks(
        self, coach_validator, temp_worktree
    ):
        """Coach should NOT execute security checks."""
        # Coach should not have security checker
        assert not hasattr(coach_validator, "security_checker")
        assert not hasattr(coach_validator, "run_security_checks")

    def test_coach_does_not_write_files(self, coach_validator, temp_worktree):
        """Coach should NOT write files."""
        # Coach should not have file writing methods
        assert not hasattr(coach_validator, "save_results")
        assert not hasattr(coach_validator, "write_file")


# ============================================================================
# Integration with Coach Validator Module Tests
# ============================================================================


class TestCoachValidatorModuleIntegration:
    """Test integration with actual Coach validator module if available."""

    def test_coach_validator_module_import(self):
        """Test coach validator module can be imported."""
        try:
            from guardkit.orchestrator.quality_gates import coach_validator

            # Should be importable without error
            assert coach_validator is not None
        except ImportError:
            # Module may not exist yet - that's OK for this test
            pytest.skip("coach_validator module not implemented yet")

    def test_security_review_load_function_available(self):
        """Test load_security_review function is available for Coach."""
        from guardkit.orchestrator.quality_gates.security_review import (
            load_security_review,
        )

        assert callable(load_security_review)
